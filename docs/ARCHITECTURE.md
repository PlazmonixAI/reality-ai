# Architecture

```
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
- `POST /ask` — natural-language question → agent (Phase 5)

## Key decisions
- Tools are pure Python functions; they never call the LLM. This keeps them testable and deterministic.
- The registry is the single source of truth: API listing, direct simulation and LLM tool schemas all come from it.
- NVIDIA NIM is the only LLM provider, using an OpenAI-compatible API and a pool of keys that rotates on rate limits.
