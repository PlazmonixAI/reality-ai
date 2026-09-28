# CLAUDE.md — Build brief for Claude Code

You are building **Reality AI**, the Physics, Chemistry and Mathematics research-simulation engine of Plazmonix AI.
Biology is out of scope: do not add biology tools.
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
- **Out of scope for now:** MongoDB/persistence, auth. Do not build these.
- **Frontend (simulator UI)** lives in `frontend/`: plain HTML/CSS/ES-module JavaScript + Canvas, no build step and no npm dependencies. FastAPI serves it at `/`.
- **Simulations never invent physics in the browser.** Every number a sim shows must come from an engine tool via `POST /simulate`; the browser only animates, interpolates and draws those results. If a sim needs a new number, add a tested backend tool first.
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

## How to add an interactive simulation
1. Make sure the backend tools it needs exist and are tested (add them first if not).
2. Create `frontend/js/sims/<name>.js` exporting `default { mount(root) { ...; return cleanup; } }`. Use the shared kit in `frontend/js/core/` (`simLayout`, controls in `ui.js`, `createStage`/`View` in `stage.js`, `LineGraph`, `Player`, `liveRequest`/`simulate` in `api.js`).
3. Register it in `frontend/js/sims/index.js` (id, domain, title, blurb, SVG card art, lazy `load`).
4. Graph colours: `--series-1/2/3` only, at most three series per graph, a legend for 2+ series, hover tooltips on graphs.
5. `tests/test_frontend.py` checks the module exists, parses, and only calls registered tools. Also open it in a browser (Playwright is available) and check there are no console errors.
Always parse user-supplied expressions with `app/core/parsing.py` (`parse_expression`, `parse_equation`, `symbol`) — never `sympify`/`eval` on raw input.

## End of every session
- Run `pytest` and make sure it's green.
- Tick the finished items in `docs/ROADMAP.md`.
- Add a short dated entry to `docs/PROGRESS.md` (what was built, what's next, known issues).
- Open a PR with a clear summary.
