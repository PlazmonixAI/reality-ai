from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "reality-asm"


def test_health_answers_head_for_uptime_monitors():
    r = client.head("/health")
    assert r.status_code == 200


def test_tools_listing():
    r = client.get("/tools")
    assert "mathematics" in r.json()


def test_simulate_solve_equation():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "solve_equation",
        "args": {"equation": "x**2 - 4 = 0", "variable": "x"},
    })
    assert r.status_code == 200
    assert sorted(r.json()["result"]) == ["-2", "2"]


def test_unknown_tool():
    r = client.post("/simulate", json={"domain": "physics", "name": "nope"})
    assert r.status_code == 404


def test_simulate_differentiate():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "differentiate",
        "args": {"expression": "x**3", "variable": "x"},
    })
    assert r.status_code == 200
    assert r.json()["result"] == "3*x**2"


def test_simulate_bad_args_422():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "determinant", "args": {"matrix": [[1, 2, 3]]},
    })
    assert r.status_code == 422


def test_simulate_unsafe_expression_422():
    r = client.post("/simulate", json={
        "domain": "mathematics", "name": "solve_equation",
        "args": {"equation": "().__class__"},
    })
    assert r.status_code == 422


def test_catalogue_tools_are_cached_and_gzipped():
    body = {"domain": "physics", "name": "cosmology", "args": {"z": 2}}
    a = client.post("/simulate", json=body, headers={"Accept-Encoding": "gzip"})
    b = client.post("/simulate", json=body, headers={"Accept-Encoding": "gzip"})
    assert a.status_code == b.status_code == 200
    assert a.headers.get("content-encoding") == "gzip"
    assert a.json() == b.json()
    assert a.json()["tool"] == "physics.cosmology" and a.json()["units"]
    # the cached answer matches a fresh computation
    from app.core.registry import get_tool
    assert a.json()["result"] == get_tool("physics", "cosmology").func(z=2)["result"]
    # bad input still becomes a 422, not a cached error
    assert client.post("/simulate", json={"domain": "physics", "name": "cosmology", "args": {"z": "x"}}).status_code == 422


def test_large_json_is_compressed():
    r = client.get("/tools", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200 and r.headers.get("content-encoding") == "gzip"


def test_catalogue_cache_stays_within_its_memory_budget():
    import app.main as m
    for z in (0.5, 1.5, 2.5, 3.5):
        assert client.post("/simulate", json={"domain": "physics", "name": "cosmology", "args": {"z": z}}).status_code == 200
    assert len(m._catalogue_cache) <= m.CATALOGUE_CACHE_SIZE
    assert sum(len(a) + len(b) for a, b in m._catalogue_cache.values()) <= m.CATALOGUE_CACHE_BYTES


def test_non_finite_numbers_are_sent_as_null():
    import json as _json
    from app.main import _json_bytes
    assert _json.loads(_json_bytes({"a": float("nan"), "b": [1.0, float("inf")]})) == {"a": None, "b": [1.0, None]}


def test_owner_account_is_an_admin(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "owner_email", " Owner@Example.com ")
    monkeypatch.setattr(settings, "admin_emails", "a@example.com")
    assert settings.admins == {"owner@example.com", "a@example.com"}
