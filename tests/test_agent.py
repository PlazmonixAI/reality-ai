"""AI representative: NIM client rotation, tool schemas, agent loop and /ask — all with a mocked LLM."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.modules  # noqa: F401
from app.agent.llm import LLMError, NIMClient, NoKeysError
from app.agent.representative import ask, compact, run_tool
from app.agent.tool_schemas import function_name, select_tools, tool_for_function, tool_schema
from app.core.registry import list_tools
from app.main import app, get_llm_client

OK = {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}


def make_client(handler, keys=("k1", "k2", "k3"), **kw):
    sleeps = []
    c = NIMClient(list(keys), "https://nim.test/v1", "test-model", transport=httpx.MockTransport(handler),
                  sleep=sleeps.append, **kw)
    return c, sleeps


# --- NIM client ----------------------------------------------------------------------------------

def test_request_shape_and_auth():
    seen = []

    def handler(req):
        seen.append((req.url.path, req.headers["authorization"], json.loads(req.content)))
        return httpx.Response(200, json=OK)

    c, _ = make_client(handler)
    tools = [{"type": "function", "function": {"name": "f", "parameters": {"type": "object", "properties": {}}}}]
    assert c.chat([{"role": "user", "content": "q"}], tools=tools)["content"] == "hi"
    path, auth, body = seen[0]
    assert path == "/v1/chat/completions" and auth == "Bearer k1"
    assert body["model"] == "test-model" and body["tools"] == tools and body["tool_choice"] == "auto"
    # Round robin: the next request starts with the next key
    c.chat([{"role": "user", "content": "q"}])
    assert seen[1][1] == "Bearer k2" and "tools" not in seen[1][2]


def test_rotates_on_429_and_5xx():
    calls = []

    def handler(req):
        key = req.headers["authorization"][7:]
        calls.append(key)
        if key == "k1":
            return httpx.Response(429, headers={"retry-after": "3"})
        if key == "k2":
            return httpx.Response(503)
        return httpx.Response(200, json=OK)

    c, sleeps = make_client(handler)
    assert c.chat([{"role": "user", "content": "q"}])["content"] == "hi"
    assert calls == ["k1", "k2", "k3"] and sleeps == []
    assert c.status()["cooling"] == 2


def test_disables_rejected_keys():
    calls = []

    def handler(req):
        key = req.headers["authorization"][7:]
        calls.append(key)
        return httpx.Response(401) if key == "bad" else httpx.Response(200, json=OK)

    c, _ = make_client(handler, keys=("bad", "good"))
    c.chat([{"role": "user", "content": "q"}])
    c.chat([{"role": "user", "content": "q"}])
    c.chat([{"role": "user", "content": "q"}])
    assert calls == ["bad", "good", "good", "good"] and c.status()["disabled"] == 1
    only_bad, _ = make_client(lambda req: httpx.Response(403), keys=("x",))
    with pytest.raises(NoKeysError):
        only_bad.chat([{"role": "user", "content": "q"}])


def test_gives_up_after_attempts_and_backs_off():
    c, sleeps = make_client(lambda req: httpx.Response(500), keys=("a", "b"), max_attempts=5)
    with pytest.raises(LLMError, match="after 5 attempts"):
        c.chat([{"role": "user", "content": "q"}])
    assert len(sleeps) >= 2  # waited once every key was cooling down


def test_network_errors_and_bad_requests():
    state = {"n": 0}

    def flaky(req):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ConnectTimeout("boom", request=req)
        return httpx.Response(200, json=OK)

    c, _ = make_client(flaky)
    assert c.chat([{"role": "user", "content": "q"}])["content"] == "hi"
    c2, _ = make_client(lambda req: httpx.Response(400, text="bad tool schema"))
    with pytest.raises(LLMError, match="HTTP 400"):
        c2.chat([{"role": "user", "content": "q"}])
    with pytest.raises(NoKeysError):
        NIMClient([], "https://nim.test/v1", "m").chat([{"role": "user", "content": "q"}])


# --- tool schemas & selection ------------------------------------------------------------------

def test_every_tool_has_a_valid_schema():
    for t in list_tools():
        s = tool_schema(t)["function"]
        assert s["name"] == function_name(t) and len(s["name"]) <= 64 and "." not in s["name"]
        props, req = s["parameters"]["properties"], s["parameters"]["required"]
        assert set(req) <= set(props)
        json.dumps(s)  # serialisable
        assert tool_for_function(s["name"]) is t


def test_schema_types():
    t = tool_for_function("physics__hohmann_transfer")
    p = tool_schema(t)["function"]["parameters"]
    assert p["properties"]["alt1"] == {"type": "number"} and p["required"] == []  # r1/r2 or alt1/alt2, all optional
    lsq = tool_schema(tool_for_function("mathematics__least_squares_fit"))["function"]["parameters"]
    assert lsq["properties"]["x"] == {"type": "array", "items": {"type": "number"}}
    assert lsq["properties"]["model"] == {"type": "string", "default": "linear"}
    assert set(lsq["required"]) == {"x", "y"}


@pytest.mark.parametrize("question,expected", [
    ("How much delta-v to go from LEO to GEO?", "physics.hohmann_transfer"),
    ("What is the pH of 0.1 M acetic acid?", "chemistry.ph"),
    ("Integrate x^2 sin(x)", "mathematics.integrate"),
    ("Date a bone with 30% of its carbon-14 left", "chemistry.radiometric_dating"),
    ("Escape velocity of Earth", "physics.escape_velocity"),
])
def test_selection_finds_the_right_tool(question, expected):
    assert expected in [t.key for t in select_tools(question, 5)]


# --- agent loop ------------------------------------------------------------------------------

class ScriptedLLM:
    """Replays assistant messages and records what it was sent."""

    model = "scripted"

    def __init__(self, replies):
        self.replies, self.sent = list(replies), []

    def chat(self, messages, tools=None, tool_choice="auto", **kw):
        self.sent.append({"messages": [dict(m) for m in messages], "tools": tools, "tool_choice": tool_choice})
        return self.replies.pop(0)


def tool_call(name, args, id_="c1"):
    return {"role": "assistant", "content": "", "tool_calls": [{"id": id_, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_agent_runs_real_tool_and_explains():
    llm = ScriptedLLM([
        tool_call("physics__escape_velocity", {"body": "earth", "altitude": 0}),
        {"role": "assistant", "content": "About 11.2 km/s."},
    ])
    out = ask("What is Earth's escape velocity?", llm)
    assert out["answer"] == "About 11.2 km/s." and out["rounds"] == 2
    step = out["tool_calls"][0]
    assert step["tool"] == "physics.escape_velocity" and step["ok"]
    # The tool result (a real computation) went back to the LLM as a tool message
    tool_msg = llm.sent[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert "11" in tool_msg["content"]
    assert llm.sent[0]["messages"][0]["role"] == "system" and llm.sent[0]["tools"]


def test_agent_reports_tool_errors_and_retries():
    llm = ScriptedLLM([
        tool_call("chemistry__radiometric_dating", {"system": "C-14"}),  # missing measurement → error
        tool_call("chemistry__radiometric_dating", {"system": "C-14", "fraction_remaining": 0.25}, "c2"),
        {"role": "assistant", "content": "About 11,460 years."},
    ])
    out = ask("Date a bone with 25% C-14 left", llm)
    assert [s["ok"] for s in out["tool_calls"]] == [False, True]
    assert out["tool_calls"][1]["result"]["result"]["age_years"] == pytest.approx(11460)
    assert "error" in json.loads(llm.sent[1]["messages"][-1]["content"])


def test_agent_stops_after_max_rounds():
    llm = ScriptedLLM([tool_call("physics__escape_velocity", {"body": "earth", "altitude": 0}, f"c{i}") for i in range(2)]
                      + [{"role": "assistant", "content": "done"}])
    out = ask("escape velocity", llm, max_rounds=2)
    assert out["answer"] == "done" and len(out["tool_calls"]) == 2
    assert llm.sent[-1]["tool_choice"] == "none"


def test_unknown_tool_and_bad_arguments():
    assert run_tool("nope__nothing", "{}")[2]["error"].startswith("unknown tool")
    assert "could not parse" in run_tool("physics__escape_velocity", "{not json")[2]["error"]
    assert "error" in run_tool("physics__escape_velocity", {"wrong_arg": 1})[2]


def test_compact_summarises_long_arrays():
    c = compact({"x": list(range(100)), "y": 3.14159265358979, "s": "a" * 1000, "nested": [[1, 2], [3, 4]]})
    assert c["x"] == {"n": 100, "first": 0, "last": 99, "min": 0, "max": 99}
    assert c["y"] == 3.14159 and len(c["s"]) < 500 and c["nested"] == [[1, 2], [3, 4]]


# --- /ask endpoint -----------------------------------------------------------------------------

def test_ask_endpoint_with_mocked_llm():
    llm = ScriptedLLM([tool_call("physics__escape_velocity", {"body": "earth", "altitude": 0}), {"role": "assistant", "content": "11.2 km/s"}])
    app.dependency_overrides[get_llm_client] = lambda: llm
    try:
        r = TestClient(app).post("/ask", json={"question": "Earth escape velocity?"})
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "11.2 km/s" and body["tool_calls"][0]["tool"] == "physics.escape_velocity"


def test_ask_endpoint_without_keys_is_503():
    app.dependency_overrides[get_llm_client] = lambda: NIMClient([], "https://nim.test/v1", "m")
    try:
        r = TestClient(app).post("/ask", json={"question": "hi"})
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert r.status_code == 503 and "NIM_API_KEYS" in r.json()["detail"]
    assert TestClient(app).post("/ask", json={"question": ""}).status_code == 422


# --- providers and simulation context -------------------------------------------------------

def test_provider_settings(monkeypatch):
    from app.config import Settings
    s = Settings(llm_provider="groq", groq_api_keys="g1, g2", _env_file=None)
    assert s.base_url == "https://api.groq.com/openai/v1" and s.model == "llama-3.3-70b-versatile"
    assert s.key_list == ["g1", "g2"] and s.keys_env == "GROQ_API_KEYS"
    x = Settings(llm_provider="xai", xai_api_keys="k", llm_model="grok-custom", _env_file=None)
    assert x.base_url == "https://api.x.ai/v1" and x.model == "grok-custom"
    n = Settings(_env_file=None)
    assert n.provider == "nim" and n.key_list == []
    with pytest.raises(ValueError):
        _ = Settings(llm_provider="gemini", _env_file=None).provider


def test_llm_status_never_leaks_keys():
    body = TestClient(app).get("/llm/status").json()
    assert {"provider", "model", "configured"} <= set(body) and not any("nvapi" in str(v) or "gsk_" in str(v) for v in body.values())


def test_context_reaches_the_model_and_adds_the_sims_tools():
    llm = ScriptedLLM([{"role": "assistant", "content": "The rocket is in orbit."}])
    ctx = {"sim_id": "spaceflight", "title": "Spaceflight Lab",
           "recent": [{"domain": "physics", "name": "rocket_flight", "args": {"throttle": 1}, "result": {"telemetry": {"altitude": 185000.0, "speed": list(range(50))}}}]}
    out = ask("What is happening?", llm, context=ctx)
    assert out["answer"] == "The rocket is in orbit."
    msgs = llm.sent[0]["messages"]
    assert msgs[1]["role"] == "system" and "Spaceflight Lab" in msgs[1]["content"] and "185000" in msgs[1]["content"]
    assert '"n": 50' in msgs[1]["content"]  # long arrays are summarised
    assert "physics__rocket_flight" in [t["function"]["name"] for t in llm.sent[0]["tools"]]


def test_ask_endpoint_accepts_context():
    llm = ScriptedLLM([{"role": "assistant", "content": "ok"}])
    app.dependency_overrides[get_llm_client] = lambda: llm
    try:
        r = TestClient(app).post("/ask", json={"question": "Explain", "context": {"title": "Solar System 3D", "recent": []}})
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert r.status_code == 200 and "Solar System 3D" in llm.sent[0]["messages"][1]["content"]
