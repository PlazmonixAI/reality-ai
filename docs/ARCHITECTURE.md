# Architecture

```
Browser simulator (frontend/, served at /)
     │  POST /simulate  → animate & plot the returned arrays
     ▼
User question
     │
     ▼
POST /ask ──► AI Representative (app/agent/representative.py)
                 │  uses NIM LLM (app/agent/llm.py) with tool-calling
                 ▼
            Tool Registry (app/core/registry.py)
                 │
   ┌─────────────┼──────────────┐
   ▼             ▼              ▼
mathematics   physics       chemistry
(sympy/scipy) (numpy/scipy) (numpy/scipy)
                 │
                 ▼
     Result dict {result, units, assumptions}
                 │
                 ▼
   Representative explains result to the user
```

## Endpoints
- `GET /health` — liveness check
- `GET /tools` — list all registered tools (grouped by domain)
- `POST /simulate` — run one tool directly: `{"domain": "...", "name": "...", "args": {...}}`
- `POST /ask` — natural-language question → agent (Phase 7)
- `GET /` — the interactive simulator (static files from `frontend/`)

## Key decisions
- Tools are pure Python functions; they never call the LLM. This keeps them testable and deterministic.
- The simulator is a thin client: it calls tools through `/simulate` (debounced, latest-request-wins), then animates the plot-ready arrays the tools return. No physics is re-implemented in JavaScript.
- Frontend has no build step or npm dependencies, so it ships with the Python app and works offline.
- The registry is the single source of truth: API listing, direct simulation and LLM tool schemas all come from it.
- NVIDIA NIM is the only LLM provider, using an OpenAI-compatible API and a pool of keys that rotates on rate limits.
