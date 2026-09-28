from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import app.modules  # noqa: F401  (registers all tools)
from app.core.registry import get_tool, list_tools

app = FastAPI(title="Reality AI", version="0.1.0",
              description="Plazmonix AI's PCMB research-simulation engine")


class SimulateRequest(BaseModel):
    domain: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"status": "ok", "service": "reality-ai", "tools": len(list_tools())}


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
        return {"tool": t.key, **t.func(**req.args)}
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
