# CLAUDE.md — Reality AI (build brief for Claude Code)

You are building **Reality AI**, the PCMB (Physics, Chemistry, Mathematics, Biology) research-simulation engine of **Plazmonix AI** (a Velostra Aerospace company).

This repo starts with **only this file**. Your first job is Phase 0: create the whole project scaffold described below. After that, build one phase per session.

At the start of every session: read this file and `docs/PROGRESS.md` (once it exists), then work on the next unfinished phase.

---

## 1. What Reality AI does
1. A user asks a research question in natural language (e.g. "How much delta-v to go from LEO to GEO?").
2. The **AI representative** (LLM via NVIDIA NIM, tool-calling) picks the right simulation tool(s) and arguments.
3. The tool runs real numerical/symbolic computation (numpy / scipy / sympy).
4. The representative explains the result with units, assumptions and limitations.

## 2. Hard rules
- **Real implementations only.** No stubs, no fake numbers. Every tool must actually compute its answer.
- **Every tool gets tests** in `tests/`, checked against known textbook values (tolerance-based asserts).
- **SI units internally.** Every tool result includes a `units` field.
- **LLM provider: NVIDIA NIM only** (OpenAI-compatible API) with multi-key pooling/rotation from `NIM_API_KEYS`. Do **not** add Gemini or any other provider.
- Tools never call the LLM. Only the agent layer talks to the LLM.
- Stack: Python 3.11+, FastAPI, pydantic v2, pydantic-settings, numpy, scipy, sympy, httpx, pytest.
- **Out of scope for now:** frontend, MongoDB/persistence, auth. Do not build these.
- Prefer small, surgical edits to existing files over rewriting whole files.
- Keep dependencies minimal; flag any new heavy library in the PR description.
- Tests must never make real LLM API calls (mock them).

## 3. Target project structure
```
reality-ai/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   ├── ARCHITECTURE.md
│   └── PROGRESS.md
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # pydantic-settings (NIM keys, base URL, model)
│   ├── core/
│   │   └── registry.py      # @tool decorator + registry
│   ├── agent/
│   │   ├── llm.py           # NIM client with key rotation
│   │   └── representative.py# agent loop
│   └── modules/
│       ├── __init__.py      # imports all domains so tools register
│       ├── mathematics/
│       ├── physics/
│       ├── chemistry/
│       └── biology/
└── tests/
```

## 4. Architecture
```
User question → POST /ask → AI Representative (NIM tool-calling)
                                  │
                           Tool Registry
          ┌──────────────┬────────┴───────┬──────────────┐
     mathematics      physics         chemistry        biology
                                  │
                 {result, units, assumptions}
                                  │
                 Representative explains to user
```

**Endpoints**
- `GET /health` → `{"status": "ok", "service": "reality-ai", "tools": <count>}`
- `GET /tools` → all registered tools grouped by domain
- `POST /simulate` → run one tool directly: `{"domain": "...", "name": "...", "args": {...}}`; 404 for unknown tool, 422 for bad args
- `POST /ask` → natural-language question → agent (Phase 6)

**Key decisions**
- Tools are pure Python functions: testable and deterministic.
- The registry is the single source of truth: `/tools`, `/simulate` and the LLM tool schemas all come from it.

## 5. How to add a simulation tool
1. Write a typed function with a docstring in `app/modules/<domain>/<topic>.py`.
2. Return `{"result": ..., "units": ..., "assumptions": [...]}`.
3. Register it with `@tool(domain=..., name=..., description=...)` from `app/core/registry.py`.
4. Import the file in `app/modules/<domain>/__init__.py`.
5. Add tests in `tests/test_<domain>_<topic>.py`.
6. Run `pytest`; everything must pass.

## 6. Environment variables (`.env.example`)
```
NIM_API_KEYS=nvapi-key1,nvapi-key2
NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NIM_MODEL=meta/llama-3.1-70b-instruct
```

---

## 7. Roadmap (one phase per session)
Cloud-session credit deadline: **Nov 5, 2026, 1:29 PM IST**.

### Phase 0 — Scaffold
- [ ] Create every file/folder in section 3 (README, requirements, .env.example, .gitignore, docs)
- [ ] `app/config.py`, `app/core/registry.py` (`@tool`, `get_tool`, `list_tools`, duplicate-key check)
- [ ] `app/main.py` with `/health`, `/tools`, `/simulate`
- [ ] Reference tool `mathematics.solve_equation` (sympy) following section 5
- [ ] Placeholder docstrings only in `app/agent/` (built in Phase 6)
- [ ] Tests: health, tools listing, solve_equation (`x**2 - 4 = 0` → `-2, 2`), unknown tool → 404

### Phase 1 — Mathematics core
- [ ] Symbolic: differentiate, integrate (definite + indefinite), limits, series expansion
- [ ] Linear algebra: linear systems, eigenvalues/eigenvectors, determinant
- [ ] ODE initial value problems (scipy `solve_ivp`)
- [ ] Numerical root finding and optimization
- [ ] Tests

### Phase 2 — Physics: Orbital mechanics (flagship)
- [ ] Circular/escape velocity, orbital period (Kepler's 3rd law)
- [ ] Hohmann transfer: both burn delta-v's + transfer time
- [ ] Two-body orbit propagation (state vectors over time)
- [ ] Orbital elements ↔ state vectors
- [ ] Simple n-body propagation (e.g. Earth–Moon–spacecraft)
- [ ] Plot-ready position arrays in outputs
- [ ] Tests (e.g. LEO→GEO Hohmann total ≈ 3.9 km/s)

### Phase 3 — Physics: Propulsion + classical
- [ ] Tsiolkovsky rocket equation (solve for any variable)
- [ ] Multi-stage delta-v + simple staging optimization
- [ ] Thrust-to-weight, burn time, mass flow from Isp
- [ ] Projectile motion with/without drag
- [ ] Simple harmonic / damped oscillator
- [ ] Tests

### Phase 4 — Chemistry
- [ ] Molar mass from formula, stoichiometry
- [ ] Ideal gas law (solve for any variable)
- [ ] Reaction kinetics: 0/1/2 order, half-life, Arrhenius
- [ ] Equilibrium (Kc/Kp, ICE-table solver)
- [ ] pH/pOH for strong and weak acids/bases
- [ ] Tests

### Phase 5 — Biology
- [ ] Exponential and logistic population growth
- [ ] Lotka–Volterra predator–prey
- [ ] SIR epidemic model
- [ ] Michaelis–Menten enzyme kinetics
- [ ] Hardy–Weinberg equilibrium
- [ ] Tests

### Phase 6 — AI representative
- [ ] NIM client: rotate keys, retry on 429/5xx, support `tools` (`app/agent/llm.py`)
- [ ] Convert registry tools to OpenAI-style tool schemas
- [ ] Agent loop: question → tool call(s) → execute → explain (`app/agent/representative.py`)
- [ ] `POST /ask` endpoint
- [ ] Tests with a mocked LLM

### Phase 7 — Polish
- [ ] Consistent error handling and clear 422 messages
- [ ] Input validation (no negative masses, etc.)
- [ ] README examples for every domain
- [ ] Full test pass

---

## 8. End of every session
- Run `pytest`; it must be green.
- Tick finished items in section 7 of this file.
- Add a dated entry to `docs/PROGRESS.md`: what was built, what's next, known issues.
- Open a PR with a clear summary.
