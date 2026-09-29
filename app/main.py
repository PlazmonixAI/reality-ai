from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import app.modules  # noqa: F401  (registers all tools)
from app.agent import representative
from app.agent.llm import LLMError, NIMClient, NoKeysError
from app.config import settings
from app.core import runner
from app.core.registry import get_tool, list_tools

app = FastAPI(title="Reality ASM", version="0.1.0",
              description="Reality ASM (Advanced Simulation Machine): Plazmonix AI's physics, chemistry and mathematics research-simulation engine")


class SimulateRequest(BaseModel):
    domain: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"status": "ok", "service": "reality-asm", "tools": len(list_tools())}


@app.get("/tools")
def tools():
    grouped: dict[str, list[dict]] = {}
    for t in list_tools():
        grouped.setdefault(t.domain, []).append({"name": t.name, "description": t.description})
    return grouped


@app.post("/simulate")
def simulate(req: SimulateRequest):
    try:
        t = get_tool(req.domain, req.name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        return {"tool": t.key, **runner.run(t, req.args, timeout=settings.tool_timeout_s)}
    except runner.ToolInputError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001 - a bug in a tool: report it as JSON, not a bare 500 page
        raise HTTPException(status_code=500, detail=f"internal error in {t.key}: {e.__class__.__name__}: {e}")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    context: dict[str, Any] | None = None  # snapshot of the simulation on screen (sim id, title, recent engine calls)


_client: NIMClient | None = None


def get_llm_client() -> NIMClient:
    """One shared NIM client so the key rotation state is kept across requests."""
    global _client
    if _client is None:
        _client = NIMClient(settings.key_list, settings.base_url, settings.model, keys_env=settings.keys_env)
    return _client


@app.get("/llm/status")
def llm_status():
    """Which LLM provider/model the AI representative uses and whether keys are configured (never the keys)."""
    try:
        return {"provider": settings.provider, "model": settings.model, "configured": bool(settings.key_list),
                "keys": len(settings.key_list), "keys_env": settings.keys_env}
    except ValueError as e:
        return {"provider": settings.llm_provider, "configured": False, "error": str(e)}


@app.post("/ask")
def ask(req: AskRequest, client=Depends(get_llm_client)):
    """Answer a research question in natural language using the engine's tools (NVIDIA NIM)."""
    try:
        return representative.ask(req.question, client, history=req.history, context=req.context)
    except NoKeysError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# Interactive simulator UI (plain HTML/JS, no build step). Mounted last so API routes win.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
