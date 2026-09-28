# CLAUDE.md — Build brief for Claude Code

You are building **Reality AI**, the PCMB research-simulation engine of Plazmonix AI.
Read this file, then `docs/ROADMAP.md` and `docs/PROGRESS.md`, before doing anything.

## What Reality AI does
1. A user asks a research question in natural language (e.g. "How much delta-v to go from LEO to GEO?").
2. The **AI representative** (LLM via NVIDIA NIM, tool-calling) picks the right simulation tool(s) and arguments.
3. The tool runs real numerical/symbolic computation (numpy / scipy / sympy).
4. The representative explains the result with units, assumptions and limits.

## Hard rules
- **Real implementations only.** No stubs, no fake numbers, no `return 42`. Every tool must compute its answer.
- **Every tool gets tests** in `tests/`, checked against known textbook values (tolerance-based asserts).
- **SI units everywhere** internally. Every tool result includes a `units` field.
- **LLM provider: NVIDIA NIM only** (OpenAI-compatible API) with multi-key pooling/rotation from `NIM_API_KEYS`. Do **not** add Gemini or any other provider.
- Tools must never call the LLM. Only the agent layer talks to the LLM.
- Stack: Python 3.11+, FastAPI, pydantic v2, numpy, scipy, sympy, httpx, pytest.
- **Out of scope for now:** frontend, MongoDB/persistence, auth. Do not build these.
- Prefer small, surgical edits to existing files over rewriting whole files.
- Keep dependencies minimal; ask (in the PR description) before adding a new heavy library.

## How to add a simulation tool
1. Write a plain function in `app/modules/<domain>/<topic>.py`, with typed args and a docstring.
2. Return a dict: `{"result": ..., "units": ..., "assumptions": [...]}`.
3. Register it with the `@tool(domain=..., name=..., description=...)` decorator from `app/core/registry.py`.
4. Add an import line for the file in `app/modules/__init__.py` so it registers on startup. (Domain folders are namespace packages — no `__init__.py` needed.)
5. Add tests in `tests/test_<domain>_<topic>.py`.
6. Run `pytest` — everything must pass before you finish.

See `app/modules/mathematics/algebra.py` for the reference example.

## End of every session
- Run `pytest` and make sure it's green.
- Tick the finished items in `docs/ROADMAP.md`.
- Add a short dated entry to `docs/PROGRESS.md` (what was built, what's next, known issues).
- Open a PR with a clear summary.
