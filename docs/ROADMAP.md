# Reality AI — Build Roadmap

Scope: Physics, Chemistry and Mathematics. Biology is out of scope.

One session = one phase. Keep each session tightly scoped.
Deadline for cloud-session credits: **Nov 5, 2026, 1:29 PM IST**.

## Phase 0 — Scaffold ✅
- [x] FastAPI app, `/health`, tool registry, `/tools`, `/simulate` endpoint
- [x] Reference tool: `mathematics.solve_equation`
- [x] Test setup

## Phase 1 — Mathematics core ✅
- [x] Symbolic: differentiate, integrate (definite + indefinite), limits, series expansion
- [x] Linear algebra: solve linear systems, eigenvalues/eigenvectors, determinant
- [x] ODE solver: numerically solve initial value problems (scipy `solve_ivp`)
- [x] Numerical root finding and optimization (scipy)
- [x] Tests for all of the above

## Phase 2 — Physics: Orbital mechanics (flagship) ✅
- [x] Circular/escape velocity, orbital period (Kepler's 3rd law)
- [x] Hohmann transfer: delta-v for both burns + transfer time
- [x] Two-body orbit propagation (state vectors over time)
- [x] Orbital elements <-> state vectors conversion
- [x] Simple n-body propagation (e.g. Earth-Moon-spacecraft)
- [x] Plot-ready output (arrays of positions) for a future frontend
- [x] Tests (e.g. LEO→GEO Hohmann ≈ 3.9 km/s total)

## Phase 3 — Physics: Propulsion + classical ✅
- [x] Tsiolkovsky rocket equation (solve for any variable)
- [x] Multi-stage rocket delta-v + simple staging optimization
- [x] Thrust-to-weight, burn time, mass flow from Isp
- [x] Projectile motion with/without drag
- [x] Simple harmonic / damped oscillator
- [x] Tests

## Phase 4 — Chemistry ✅
- [x] Molar mass from formula, stoichiometry
- [x] Ideal gas law (solve for any variable)
- [x] Reaction kinetics: zero/first/second order, half-life, Arrhenius
- [x] Chemical equilibrium (Kc/Kp, ICE-table solver)
- [x] pH / pOH for strong and weak acids/bases
- [x] Tests

## Phase 5 — AI representative
- [ ] NIM client with multi-key rotation + retry on 429/5xx (`app/agent/llm.py`)
- [ ] Convert registry tools into OpenAI-style tool schemas
- [ ] Agent loop: question → tool call(s) → execute → explain (`app/agent/representative.py`)
- [ ] `POST /ask` endpoint
- [ ] Tests with a mocked LLM (no real API calls in tests)

## Phase 6 — Polish
- [ ] Consistent error handling (bad input → clear 422 messages)
- [ ] Input validation ranges (no negative masses, etc.)
- [ ] README examples for every domain
- [ ] Full test pass + coverage check
