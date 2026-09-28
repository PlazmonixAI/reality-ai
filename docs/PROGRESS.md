# Progress log

## 2026-09-28 — Phase 0 (scaffold)
- FastAPI app with `/health`, `/tools`, `/simulate`
- Tool registry with `@tool` decorator
- Reference tool `mathematics.solve_equation` (sympy)
- Agent layer placeholders (now Phase 5)
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
- **Known issues:** errors that are not `ValueError`/`TypeError` (e.g. sympy `NotImplementedError`, heavy symbolic work with no timeout) still surface as 500s — handle in Polish (now Phase 6). `E` and `I` mean Euler's number and the imaginary unit in expressions.

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
- **Next:** Phase 5 — AI representative
- **Known issues:** pH assumes 25 °C and ideal solutions; polyprotic acids and buffers not yet supported; chemistry uses conventional units (g, g/mol, mol/L, bar) and says so in each `units` field

## 2026-09-28 — Scope change: biology removed
- Biology is out of scope for Reality AI; the Biology phase is dropped from `docs/ROADMAP.md` and all docs
- Phases renumbered: Phase 5 = AI representative, Phase 6 = Polish
- **Next:** Phase 5 — AI representative

## 2026-09-28 — Phase 5 (simulator frontend, batch 1)
- Priority change: build the interactive simulator before the AI representative. Phases now: 5 simulator (done), 6 simulation catalogue, 7 AI representative, 8 polish
- `frontend/` served at `/` by FastAPI: gallery with search, hash router, shared kit (`frontend/js/core/`), 12 PhET-style sims
- Physics: Projectile Motion, Gravity & Orbits, Hohmann Transfer, Earth–Moon Voyage (default is a real free-return fly-by found with the engine: 10,842 m/s at 235°), Masses & Springs, Pendulum Lab, Rocket Lab
- Chemistry: Gas Properties, Reaction Rates, pH Scale, Chemical Equilibrium; Mathematics: Calculus Grapher
- New engine tools: `mathematics.evaluate_function`, `physics.pendulum` (nonlinear + exact elliptic-integral period), `chemistry.maxwell_boltzmann`; `harmonic_oscillator` now returns kinetic/potential arrays
- 237 tests passing (incl. frontend wiring tests and `node --check` of every JS file); every sim checked in headless Chromium with no console errors
- **Next:** Phase 6 — simulation catalogue, batch 2
- **Known issues:** sims need the engine running (static hosting alone won't work); particle motion in Gas/Reaction Rates is illustrative (the numbers come from the engine); Rocket Lab mission budgets are rough reference figures

## 2026-09-28 — Phase 6, batch 2 (waves, optics, circuits, fields)
- New engine tools: `string_wave` (damped wave equation, driven end, fixed/loose/absorbing far end), `slit_interference` (N-slit Fraunhofer pattern + near-slit wave field), `lens_mirror` (thin lens / spherical mirror with principal rays), `refraction` (Snell + Fresnel, TIR, Brewster), `dc_circuit` (modified nodal analysis), `electric_field` + `coulomb_force` (field/potential maps, RK4 field lines, probes)
- New sims: Waves on a String, Wave Interference, Lenses & Mirrors, Bending Light, Circuit Builder (grid editor, live Kirchhoff solve, glowing bulbs, current dots, short-circuit warning), Charges & Fields (drag charges, sensor, voltage map)
- Verified against textbook results: pulse speed √(T/μ), fixed-end inversion, resonance at harmonics, double-slit fringe spacing λD/d, single-slit minima, lens/mirror image positions (rays meet at the image), 45° air→water = 32.12°, R(0°) = 4 % for glass, Brewster p-null, TIR, divider/parallel/bridge circuits, power conservation, point-charge and dipole fields; 281 tests passing
- **Next:** Phase 6 batch 3 — collisions, forces on a ramp, energy skate park, RC/RLC circuits, magnetic fields & induction
- **Known issues:** near-slit wave view compresses the slit spacing when it exceeds ~24 wavelengths (flagged on screen; the screen pattern is exact); circuit wires are 0.1 mΩ resistors

## 2026-09-28 — Phase 6, batch 3 (mechanics & electromagnetism)
- New engine tools: `collision_1d`, `collisions_2d` (event-driven discs, exact between impacts), `ramp_motion` (static/kinetic friction, piecewise-exact), `skate_track` (spline track y(x), friction incl. centripetal normal force), `rlc_circuit` + `rlc_frequency_response`, `magnet_field` + `magnet_coil_induction` (two-pole magnet, continuous flux through the coil, EMF = −N dΦ/dt)
- Shared `physics/fieldlines.py` RK4 tracer now used by electric and magnetic field tools
- New sims: Collisions Lab (drag balls & velocity arrows), Forces on a Ramp (free-body diagram, energy graph), Energy Skate Park (drag track points and the skater, energy bars), RC/RL/RLC Circuits (transients, AC, resonance curve), Faraday's Law (magnet through a coil, bulb, voltmeter, flux/EMF graphs)
- Verified: 1D restitution formulas, 90° split for equal-mass glancing collisions, momentum/energy conservation, ramp accelerations and stick/slip, √(2gh) and √(2ga) on a parabola, RC 63.2 % at τ, RL rise, RLC ringing frequency & Q & bandwidth, dipole far-field flux, ∫EMF dt = −ΔΦ; 320 tests passing
- **Next:** Phase 6 batch 4 — chemistry (titration, buffers, Beer–Lambert, molecule shapes, build an atom)
- **Known issues:** Faraday sim neglects coil self-inductance (no magnetic drag); skater always stays on the track

## 2026-09-28 — Phase 6, batch 4 (chemistry)
- New engine tools: `titration_curve` (exact charge balance, equivalence/half-equivalence, indicators), `buffer_ph` (exact + Henderson–Hasselbalch + capacity), `beer_lambert`, `absorbance_spectrum`, `molecule_shape` (VSEPR from a formula; repulsion-minimised domains, ideal and lone-pair-compressed angles), `atom_builder` + `nuclear_binding_energy` (element/ion/isotope stability for Z ≤ 20, Madelung electron configuration, semi-empirical mass formula)
- New sims: Acid–Base Titration, Buffers (buffer vs pure water), Beer's Law Lab (spectrophotometer, spectrum, Beer's-law line), Molecule Shapes (rotatable 3D), Build an Atom (Bohr shells, mini periodic table)
- Verified: strong/strong equivalence pH 7, acetic half-equivalence = pKa and equivalence 8.73, NH3 equivalence 5.28, buffer + 0.01 mol HCl = 4.673, buffer capacity vs numerical derivative, A = εlc, 17 textbook VSEPR shapes, K fills 4s before 3d, Fe-56 binding energy 8.79 MeV/nucleon; 363 tests passing
- Note: large reference tables are avoided (computed where possible) after "output blocked by content filtering" errors in the session; spectrophotometer solutions use illustrative single-band absorptivities
- **Next:** Phase 6 batch 5 — mathematics (unit circle, Fourier series, slope fields, vectors, probability)
- **Known issues:** VSEPR supports one central atom and terminal H/halogens/O/S/N only; Build an Atom limited to Z ≤ 20

## 2026-09-28 — Renamed to Reality ASM
- Product renamed from "Reality AI" to **Reality ASM (Advanced Simulation Machine)** across the UI, API title, `/health` service id (`reality-asm`), README, CLAUDE.md and roadmap
- The GitHub repository and folder are still named `reality-ai` (renaming the repository is done by its owner in GitHub settings)
- **Next:** Phase 6 batch 5 — mathematics
