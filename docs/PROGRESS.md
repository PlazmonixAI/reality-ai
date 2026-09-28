# Progress log

## 2026-09-28 — Phase 0 (scaffold)
- FastAPI app with `/health`, `/tools`, `/simulate`
- Tool registry with `@tool` decorator
- Reference tool `mathematics.solve_equation` (sympy)
- Agent layer placeholders for Phase 6
- Tests passing
- **Next:** Phase 1 — Mathematics core

## 2026-09-28 — Phase 1 (mathematics core)
- Symbolic calculus (`calculus.py`): `differentiate`, `integrate` (indefinite + definite, numeric fallback when no closed form), `limit` (one/two-sided, ±oo), `series`
- Linear algebra (`linear_algebra.py`): `solve_linear_system` (exact, or least-squares for non-square), `eigen` (complex-aware), `determinant`
- ODEs (`ode.py`): `solve_ode` — first-order systems with named variables and parameters via scipy `solve_ivp`
- Numerical (`numerical.py`): `find_root` (Brent on a bracket / Newton from a guess), `optimize` (BFGS / bounded L-BFGS-B, min or max)
- New `app/core/parsing.py`: shared expression parser. Blocks attribute access, dunders and builtins, and only recognises a whitelist of math functions/constants so names like `N`, `S`, `gamma` stay plain variables. `solve_equation` now uses it.
- 65 tests passing
- **Next:** Phase 2 — Orbital mechanics
- **Known issues:** errors that are not `ValueError`/`TypeError` (e.g. sympy `NotImplementedError`, heavy symbolic work with no timeout) still surface as 500s — handle in Phase 7. `E` and `I` mean Euler's number and the imaginary unit in expressions.
