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

## 2026-09-28 — Phase 2 (orbital mechanics)
- `physics/bodies.py`: GM and radius for Sun, Mercury–Saturn and the Moon; tools accept `body` or a custom `mu`, and `radius` or `altitude`
- `physics/orbital.py`: `circular_velocity`, `escape_velocity`, `orbital_period` (Kepler III, both directions), `hohmann_transfer` (both burns, total, time, transfer orbit)
- `physics/elements.py`: `elements_to_state` / `state_to_elements` (Curtis Alg. 4.2/4.5; elliptic + hyperbolic, handles circular/equatorial edge cases)
- `physics/propagation.py`: `propagate_two_body` (surface-impact detection) and `propagate_n_body` (any bodies, `earth_moon` preset with spacecraft given relative to Earth, collision detection); both return plot-ready trajectory arrays and energy-drift checks
- Verified against Curtis Ex. 4.3 and 4.7, LEO→GEO Hohmann = 3.893 km/s, Earth→Mars Hohmann, Kepler's equation, sidereal month; 100 tests passing
- **Next:** Phase 3 — Propulsion + classical mechanics
- **Known issues:** no J2/drag/SRP perturbations; no plane-change or bi-elliptic manoeuvres; parabolic orbits unsupported in `elements_to_state`; n-body trajectories for long runs can be large (capped at 10,000 points)

## 2026-09-28 — Phase 3 (propulsion + classical mechanics)
- `physics/propulsion.py`: `rocket_equation` (solves for any one of delta-v, Isp/exhaust velocity, initial or final mass), `multi_stage_delta_v` (per-stage breakdown), `optimize_staging` (Lagrange-multiplier minimum lift-off mass for a target delta-v), `thrust_parameters` (mass flow, T/W, burn time)
- `physics/classical.py`: `projectile_motion` (closed-form in vacuum; quadratic drag via solve_ivp with ground detection, terminal velocity), `harmonic_oscillator` (exact solutions for undamped/under/critically/over-damped, Q factor, energy)
- Verified: rocket equation round-trips, hand-computed two-stage rocket, staging optimum = brute-force optimum, vacuum range formulas, analytic max height with drag, terminal velocity, all oscillator regimes vs numerical ODE; 139 tests passing
- **Next:** Phase 4 — Chemistry
- **Known issues:** delta-v figures are ideal (no gravity/drag losses); projectile drag uses constant air density and Cd; oscillator has no external driving force

## 2026-09-28 — Phase 4 (chemistry)
- `chemistry/formula.py` + `periodic_table.py`: formula parser (nested brackets, hydrates, ion charges, states) and IUPAC atomic weights for all 118 elements
- `chemistry/stoichiometry.py`: `molar_mass` (with mass-% composition), `balance_equation` (atoms + charge, via null space), `stoichiometry` (limiting reagent, theoretical yields, excess left)
- `chemistry/gas.py`: `ideal_gas_law` (solve for any of P, V, n, T in SI, with atm/bar/L/°C conversions)
- `chemistry/kinetics.py`: `reaction_kinetics` (orders 0/1/2, [A](t) or time-to-reach, half-life, decay curve), `arrhenius` (k from A/Ea/T, or two-point solve for k2, T2 or Ea)
- `chemistry/equilibrium.py`: `equilibrium_ice` (any stoichiometry, Kc or Kp, solids/liquids excluded; stays accurate for K from 1e-30 to 1e30), `kc_kp_convert`
- `chemistry/acid_base.py`: `ph` for strong/weak monoprotic acids and bases, exact with water autoionisation (1e-8 M HCl -> 6.98)
- 216 tests passing
- **Next:** Phase 5 — Biology
- **Known issues:** pH assumes 25 °C and ideal solutions; polyprotic acids and buffers not yet supported; chemistry uses conventional units (g, g/mol, mol/L, bar) and says so in each `units` field
