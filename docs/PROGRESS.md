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

## 2026-09-28 — Phase 6, batch 5 (mathematics)
- New engine tools: `trig_exact` (exact unit-circle values via sympy), `fourier_series` (coefficients by the midpoint rule, partial sums, RMS error), `slope_field`, `phase_portrait` (direction field, trajectories, equilibria classified by Jacobian eigenvalues), `vector_operations`, `probability_distribution`, `sample_means` (central limit theorem)
- New sims: Unit Circle & Trig, Fourier Series (with harmonic spectrum), Slope Fields & Phase Portraits (click to add curves), Vector Addition (drag vectors), Probability & the CLT
- Verified: exact trig for special angles, square/sawtooth/triangle/x² coefficients, Gibbs overshoot ≈ 1.179, y′ = x − y exact solution, Lotka–Volterra saddle + centre, six linear equilibrium types, harmonic trajectory is a circle, binomial interval probability, 68 % rule, CLT spread σ/√n; 392 tests passing
- Also this session: logo design prompt written (see chat); product renamed to Reality ASM
- **Next:** Phase 6 batch 6 — more mathematics (Taylor series, Riemann sums, complex plane, linear transformations, Newton's method) or physics (thermodynamic cycles, blackbody, photoelectric effect)
- **Known issues:** phase-portrait equilibria are found numerically inside the visible window only

## 2026-09-28 — Phase 6, batch 6 (mathematics II)
- Working autonomously at the user's request (no check-ins between batches)
- New engine tools: `taylor_approximation`, `riemann_sum` (left/right/midpoint/trapezoid/Simpson vs quad), `newton_method` (iterates + tangents, cycle/divergence detection, observed order), `complex_numbers` (polar forms, product/quotient, n-th roots), `linear_transform_2d` (determinant, eigenvectors, type, transformed grid)
- New sims: Taylor Series, Riemann Sums (with convergence-rate plot), Complex Plane, Linear Transformations, Newton's Method; shared `frontend/js/sims/plotkit.js` for axes/curves
- Verified: sin Taylor coefficients and Lagrange bound, rules on x² exact values, midpoint error ∝ 1/n², √2 quadratic convergence, double-root linear convergence, the classic 0 ↔ 1 Newton cycle, 4th roots of 1 + i, rotation/reflection/shear/singular classification; 411 tests passing
- **Next:** Phase 6 batch 7 — modern & thermal physics (heat-engine cycles, blackbody, photoelectric effect, hydrogen spectrum, radioactive decay, special relativity)

## 2026-09-28 — Phase 6, batch 7 (modern & thermal physics)
- New engine tools: `blackbody` (Planck spectrum, Wien peak, σT⁴, visible fraction), `photoelectric` (K_max, stopping voltage, threshold, I–V curve), `hydrogen_spectrum` (Bohr levels, all lines up to n_max with series names, reduced-mass Rydberg), `radioactive_decay` (exact Bateman chain via matrix exponential), `special_relativity` (γ, rapidity, dilation, contraction, energies, twin trip), `heat_engine_cycle` (Carnot/Otto/Diesel, net work by ∮P dV vs textbook efficiency)
- New sims: Heat Engines (animated PV loop + piston), Blackbody Spectrum (vs the Sun, apparent colour), Photoelectric Effect (tube, battery, I–V graph), Hydrogen Atom (level diagram, Bohr orbits, spectrum strip), Radioactive Decay (400-atom grid, C-14 / I-131 / Co-60 / custom chain), Special Relativity (twin-paradox clocks, γ curve)
- Verified: Stefan–Boltzmann constant, Wien peak for the Sun, Planck integral = σT⁴, H-α 656.47 nm / Lyman-α 121.57 nm / H-β 486.27 nm, Bateman vs analytic two-member chain, γ = 5/3 at 0.8c and the 10-yr / 6-yr twin trip, muon lifetime dilation, Carnot/Otto/Diesel efficiencies from the enclosed area; 428 tests passing
- **Next:** Phase 6 batch 8 — chemistry (molarity & dilution, electrochemistry/Nernst, van der Waals, Clausius–Clapeyron, reaction energy profiles)
- **Known issues:** photoelectron animation is illustrative (the numbers come from the engine); decay presets are two-member chains

## 2026-09-28 — Phase 6, batch 8 (chemistry II)
- New engine tools: `molarity_dilution` (molar mass from the formula, C1V1 = C2V2, optional solubility limit), `galvanic_cell` (E°, Nernst E, ΔG, K, E vs log Q for 12 textbook electrodes), `van_der_waals` (isotherms, critical point, Maxwell equal-area tie line, phase and lever rule), `vapor_pressure` (Clausius–Clapeyron, boiling point at any pressure, Trouton), `reaction_profile` (barriers, Arrhenius rates, catalytic speed-up, Maxwell–Boltzmann fraction above Ea)
- New sims: Molarity & Dilution, Galvanic Cells (animated electron flow, voltmeter), Real Gases (PV isotherms with coexistence dome and cylinder), Vapour Pressure & Boiling (pot, thermometer, places from sea level to Everest), Reaction Energy Profile (with log-scale energy distribution)
- Verified: 0.2 M CuSO4, Daniell cell 1.10 V / ΔG° −212.3 kJ/mol / log K 37.2, Nernst 59.16 mV/decade, CO2 critical point 304 K / 74 bar, vdW Pr_sat = 0.647 at Tr = 0.9 and a numerically equal-area tie line, water boils at ~71 °C on Everest, Trouton for benzene, catalyst speed-up e^(ΔEa/RT) ≈ 2.4×10⁴ with unchanged K; 452 tests passing
- **Next:** Phase 6 batch 9 — physics (driven oscillator resonance, coupled oscillators, double pendulum, Lorentz force/cyclotron, Doppler effect)
- **Known issues:** Clausius–Clapeyron uses constant ΔH_vap (water at 25 °C comes out ~3.7 kPa vs 3.17 kPa real); galvanic cells use metal/ion couples only

## 2026-09-28 — Phase 6, batch 9 (oscillations, fields, sound)
- New engine tools: `driven_oscillator` (steady amplitude/phase, Q, resonance curve, full transient trajectory), `coupled_oscillators` (normal modes via K v = ω² M v, exact modal-superposition motion), `double_pendulum` (DOP853 at 1e-11, twin run, Lyapunov estimate, energy drift), `charged_particle` (Lorentz force: cyclotron frequency, Larmor radius, pitch, E×B drift), `doppler_effect` (approach/recede pitch, Mach cone, drive-by with wavefront emissions and supersonic boom)
- New sims: Resonance, Coupled Oscillators (beats, mode starts), Double Pendulum & Chaos (twin + log separation), Charges in E & B Fields (auto-scaled view), Doppler Effect (wavefronts, drive-by pitch, supersonic branches)
- Verified: amplitude F0/(bω0) and 90° lag at resonance, exact half-power frequencies (bandwidth b/m), simulated steady amplitude, ω = √(k/m), √(3k/m) modes, complete beat transfer, 3-mass chain 2√(k/m) sin(nπ/8), double-pendulum slow mode (2 − √2) g/l, chaos vs calm, proton cyclotron 15.25 MHz/T and circle radius, electron helix pitch, E×B drift = E/B, Doppler 440 Hz textbook cases, Mach 2 cone 30°, drive-by limits and boom time; 470 tests passing
- **Next:** Phase 6 batch 10 — maths (conics/polar/parametric, least squares, Monte Carlo, fractals, shortest paths) or remaining physics (rotation, fluids, heat conduction, quantum box, Kepler)
- **Known issues:** Lorentz-force model is non-relativistic (v < 0.1 c); Doppler assumes still air

## 2026-09-28 — Phase 6, batch 10 (mathematics III)
- New engine tools: `plane_curve` (parametric/polar, exact-derivative arc length, Green's-theorem area), `conic_section` (general quadratic → type, centre/vertex, rotation, axes, eccentricity, foci, asymptotes, directrix, branches), `least_squares_fit` (linear/polynomial/exponential/power/logarithmic with standard errors, R², residuals), `monte_carlo` (π darts and integrals with SE and convergence), `fractal` (Mandelbrot/Julia smooth escape counts, base64 uint16 image), `shortest_path` (Dijkstra / Bellman–Ford with negative-cycle detection), `minimum_spanning_tree` (Kruskal)
- New sims: Conic Sections, Parametric & Polar Curves (tracing), Least-Squares Fitting (click/drag points, residual bars), Monte Carlo (hit/miss darts, error vs N), Fractal Explorer (click to zoom, pick Julia c), Shortest Paths & Spanning Trees (animated Dijkstra/Kruskal on a road map)
- Graph kit fix: bar width now uses the smallest gap between x values (unsorted x drew 1-px bars)
- Verified: circle/cardioid/astroid/rose/cycloid lengths and areas, ellipse x²/9 + y²/4 foci ±√5, rotated ellipse points satisfy the equation, xy = 1 (e = √2, 45°), y = x² focus (0, ¼), Anscombe I (a = 3.00, b = 0.500, R² = 0.667), exact polynomial/exponential/power/log recovery, π and ∫x² within 4 SE with SE ∝ 1/√N, Mandelbrot area ≈ 1.507 and symmetry, Julia(0) = unit disk, CLRS Dijkstra/Bellman–Ford/MST (37) examples; 491 tests passing
- **Next:** Phase 6 batch 11 — remaining physics (rotation/rolling, buoyancy/Bernoulli, heat conduction, quantum box/tunnelling, Kepler/solar system) and chemistry (balancing game, limiting reagent, polyprotic acids, colligative properties, radiometric dating)
- **Known issues:** Mandelbrot area is a pixel-count estimate; fractal zoom is limited by double precision (~1e-13 width)

## 2026-09-28 — Phase 6, batch 11 (rotation, fluids, heat, quantum, Kepler)
- New engine tools: `rolling_race` (I = k m R², rolling vs slipping with the μ limit, energy split), `buoyancy` (Archimedes), `pipe_flow` (continuity + Bernoulli with height, cavitation flag), `heat_conduction` (1D Crank–Nicolson, fixed or insulated ends, 7 materials), `quantum_well` (infinite exact; finite and harmonic by finite differences), `quantum_tunnelling` (exact rectangular-barrier T, transfer-matrix |ψ|²), `kepler_orbit` (Kepler's equation, vis-viva, equal-area sectors)
- New sims: Rolling Race, Buoyancy, Fluid Flow (Bernoulli), Heat Conduction, Quantum Wells, Quantum Tunnelling, Kepler's Laws
- Verified: a = g sin θ/(1 + k) for sphere/cylinder/shell/hoop and finish order, 2/7 rotational share, slipping threshold; iceberg 917/1025 submerged, wood half-submerged, iron apparent weight; Venturi Δp = ½ρ(v₂² − v₁²) and ρgh; sine mode decays as e^(−α(π/L)²t), linear steady state, insulated rod conserves heat; electron in 1 nm box 0.376 eV and n² ladder, ħω(n + ½), finite-well roots of the transcendental equations (4 states), exact T with T + R = 1 and resonant T = 1; Earth/Halley periods and speeds, equal areas, T²/a³ = 1; 508 tests passing
- **Next:** Phase 6 batch 12 — chemistry (balancing game, limiting reagent, polyprotic acids, colligative properties, radiometric dating); then Phase 7 (AI representative via NVIDIA NIM)
- **Known issues:** heat conduction is 1D only; finite wells use a finite-difference grid (≈0.2 % accuracy)

## 2026-09-28 — Phase 6, batch 12 (chemistry III)
- New engine tools: `check_balance` (atom and charge tally for proposed coefficients, smallest-set check, correct answer), `acid_speciation` (α fractions of every protonation state vs pH, pH of the pure acid by charge balance), `colligative_properties` (ΔTb, ΔTf, Raoult vapour pressure, osmotic pressure; 4 solvents), `radiometric_dating` (C-14, K-Ar with branching, U-Pb, Rb-Sr; age range from measurement error); `stoichiometry` gained `whole_reactions` for molecule counting
- New sims: Balancing Equations (±coefficient steppers, CPK molecules, atom tally bars), Reactants & Leftovers (before/after boxes), Polyprotic Acids (100-dot beaker + fractions graph), Colligative Properties (liquid range bars, ΔT vs solute), Radiometric Dating (400-atom grid, decay/growth curves)
- Shared helper `frontend/js/sims/atomdraw.js`: CPK molecule drawing and pretty formulas (subscripts, superscript charges)
- Verified: propane and Cu/Ag⁺ balancing incl. charge, phosphoric α crossovers at each pKa and H₂PO₄⁻ max ≈ 0.994, pH of 0.1 M H₃PO₄ and acetic acid, bicarbonate at pH 8.3, 1 m NaCl ΔTf = 3.72 K, sucrose −1.86 °C, glucose Π ≈ 2.44 atm, C-14 two half-lives = 11 460 y, U-Pb D/P = 1 → 4.468 Gyr, K-Ar branching; 519 tests passing
- **Next:** Phase 7 — AI representative (NVIDIA NIM client with key rotation, tool schemas, agent loop, `POST /ask`, mocked tests) and an Ask panel in the UI
- **Known issues:** colligative model is ideal (real salts have i slightly below the ideal value)

## 2026-09-28 — Phase 7: AI representative (NVIDIA NIM)
- `app/agent/llm.py`: synchronous NIM client (OpenAI-compatible `/chat/completions`) with a pooled key list from `NIM_API_KEYS`: round-robin start key, 429/5xx/network errors cool a key down (honouring Retry-After) and move on, exponential backoff once all keys were tried, 401/403 disable a key, other 4xx raise. Transport and sleep are injectable for tests
- `app/agent/tool_schemas.py`: every registry tool → OpenAI function schema from its signature and type hints (`domain__name`); TF-IDF keyword ranker sends only the ~12 most relevant tools per question (105 tools would bloat every request)
- `app/agent/representative.py`: system prompt (never invent numbers, SI units, explain assumptions/limits), tool-call loop (≤4 rounds, then a forced final answer), tool errors fed back so the model can fix arguments, results compacted (long arrays summarised) before reaching the LLM, full trace returned
- `POST /ask` → `{answer, tool_calls, model, rounds}`; 503 without keys, 502 on LLM failure, 422 on bad input
- UI: "Ask AI" page (`#/ask`) with example questions, chat bubbles and expandable tool-call cards (args, result, units, assumptions)
- Tests: 19 new (rotation on 429/503, Retry-After, key disabling, give-up with backoff, network errors, 400 raise, schemas valid for all tools, tool selection, agent loop with real tool execution, error recovery, max rounds, /ask with a mocked LLM, 503 without keys) — no real API calls; verified end to end in a browser against a local mock NIM server
- **Next:** Phase 8 polish (consistent 422s, timeouts for heavy symbolic work, README examples per domain), 2D heat equation, multi-planet n-body view, J2/drag perturbations
- **Known issues:** keyword tool selection can miss tools for unusual phrasing (the model then says it has no fitting tool); streaming responses not implemented

## 2026-09-28 — Phase 8: polish (errors, validation, time limits, docs)
- `app/core/runner.py`: every tool call (from `/simulate` and from the AI agent) is checked against the tool's signature — unknown/missing arguments list the valid ones, wrong types and NaN/∞ are rejected with a clear message — then errors are mapped consistently: bad or unsolvable input → HTTP 422, genuine tool bugs → JSON 500 naming the tool
- Symbolic tools (`symbolic=True`: solve, differentiate, integrate, limit, series, linear systems, eigen, determinant, ODE, exact trig, Taylor) run in a forked child process killed after `TOOL_TIMEOUT_S` (default 20 s), so a pathological expression can't hang a worker
- Fuzzing every tool with negative/zero/huge/NaN inputs found and fixed: a hang (NaN into an ODE integrator), a crash on unbalanced brackets (now a clear parse error), and a real bug — a pure-resistor DC circuit in `rlc_circuit` crashed; a fast fuzz test now guards all 105 tools
- README: API examples for every domain (verified), `/ask` usage; CLAUDE.md documents `symbolic=True` and the error convention
- 549 tests passing, 93 % line coverage; all 72 sims re-checked in the browser (340 engine calls, no errors)
- **Next:** 2D heat equation, multi-planet n-body view, J2/drag orbital perturbations; streaming answers for /ask

## 2026-09-28 — Phase 6, batch 13 (orbital perturbations, phase diagrams) — catalogue complete
- New engine tools: `j2_precession` (secular RAAN/perigee rates, sun-synchronous and critical inclinations, numerical two-body + J2 propagation confirming the drift), `orbital_decay` (orbit-averaged drag with a static exponential atmosphere or constant density, lifetime to 100 km), `phase_diagram` (water and CO₂: sublimation, vaporisation to the critical point, melting line, phase at any T and P)
- New sims: J2 Precession (3D orbit plane turning, Sun direction for sun-synchronous orbits), Orbital Decay (spacecraft presets, altitude vs time), Phase Diagrams (log-P map with click-to-set state and a particle box)
- Verified: ISS node drift −5.0°/day (numerical within 1 %), 800 km sun-synchronous inclination 98.6° with exactly 360°/year drift, frozen perigee at 63.4°, polar orbits don't precess, constant-density decay matches the closed form √a(t) = √a₀ − kt/2; water melts at 273.15 K at 1 atm with slope −13.5 MPa/K, vapour pressure at 25 °C within 2 % of steam tables, CO₂ sublimes at 194.7 K (ΔH_sub ≈ 26.1 kJ/mol); 559 tests passing
- Every roadmap item is now ticked: 108 tools, 75 simulations
- **Next ideas:** 2D heat equation, multi-planet solar-system view, streaming `/ask` answers, more substances for phase diagrams

## 2026-09-29 — Phase 9: Solar System 3D, Spaceflight Lab, AI analyst on every sim
- Engine: `solar_system` (JPL Standish elements 1800–2050, Moon series, IAU rotation/pole models, facts, orbit paths, time tracks), `rocket_parts`, `rocket_design`, `rocket_launch_state`, `rocket_flight` (2D flight with gravity, pressure-dependent thrust, rotating-atmosphere drag, staging, parachute, landing/crash, orbit prediction) — 23 new tests incl. Horizons positions, axial tilts, a scripted launch that reaches orbit, terminal velocity and parachute landings
- Solar System 3D sim: three.js r170 vendored (MIT) with an import map; NASA-derived Earth maps (4K day/night/clouds), planet textures from public repos (see `frontend/assets/textures/CREDITS.md`); positions/spin/tilt all from the engine, browser interpolates between engine samples
- Spaceflight Lab sim: builder (palette, stacking, templates, stage Δv/TWR) and flight (HUD, throttle, rotate/SAS, stage, chute, time warp, map)
- AI analyst panel on every simulation: recent engine calls are compacted in `api.js` and sent as context to `/ask`; the sim's own tools are always offered to the model
- LLM providers: `LLM_PROVIDER=nim|groq|xai` with pooled keys; `/llm/status` (never exposes keys). Groq is ready to switch on once keys are added
- **Known issues:** proxy blocked the Solar System Scope texture site, so some planet maps are 1K; replacing files in `frontend/assets/textures` with 2K–8K maps upgrades them. Spaceflight is 2D and single-body (no transfers yet)

## 2026-09-29 — Phase 9b: the whole Solar System and the observable Universe
- Engine (6 new tools, 18 new tests, 602 passing): `planet_moons` (28 major moons from JPL-derived mean elements; Galilean moons match astronomy-engine's L1.2 theory within ~1° over 26 years), `minor_bodies` (dwarf planets, asteroids, centaurs, comets with tracks; Halley's 1986 perihelion reproduced), `asteroid_belt` (statistical main belt with Kirkwood gaps at the Jupiter resonances, L4/L5 trojans, Kuiper belt with 3:2 plutinos at 39.4 AU), `star_catalog` (18k HYG stars, B−V temperatures, blackbody sRGB colours), `milky_way` (structural model + bulge/disc/NFW rotation curve: 229 km/s and a 218-Myr galactic year at the Sun; real globular clusters), `galaxy_catalog` (~11k galaxies with measured distances, Hubble-law speeds), `cosmology` (Friedmann/ΛCDM, Planck 2018: age 13.79 Gyr, D_C(z=1) = 3395 Mpc, observable radius 46.2 Gly)
- Data: `scripts/build_space_catalogs.py` rebuilds `app/data/space/` (≈1.8 MB) from Celestia Content (GPL-2.0-or-later) and HYG v4.1 (CC BY-SA 4.0)
- Solar System 3D: new shader set (normal-mapped lunar-Lambert/Lambert lighting, ring shadows both ways, atmospheres for Venus/Mars/Titan/giants, animated Sun), textures for every planet and major moon (Celestia/NASA, licences in CREDITS.md), tidally locked moons facing their planets, comet tails, belts, and a sky drawn from real stars + the Milky Way model
- Scale ladder (Solar System → Stars → Milky Way → Galaxies → Universe) with seamless zoom between levels; new "Universe Explorer" card (78 sims, 120 tools)
- NASA web sites (nasa.gov, ssd.jpl.nasa.gov) are blocked by this environment's network policy; data came from NASA's GitHub mirror, Celestia and HYG instead
- **Next:** constellation lines, exoplanets in the Stars view, Earth→Moon transfers in Spaceflight Lab, connect real Groq keys
- **Known issues:** moon and small-body orbits are fixed ellipses (no perturbations), so Phobos/Deimos phases and comets far from their element epochs drift; the galaxy catalogue stops at ~2 billion ly; comet tail length/brightness is a visual cue only; `sun`, `pluto` and `uranus` textures have unverified licences

## 2026-09-29 — Phase 9c: rocketry v2 (engines, designers, fairings, the Moon)
- Parts: 11 engines in four size classes modelled on real engines (small: Spark, Hopper, Nudge; medium: Sparrow, Cryo-V; large: Kestrel, Kestrel-V, Cryo-2; heavy: Condor, Titan, Colossus), tank XS, payload fairings S/M/XL, interstages S/M, six example satellites (CubeSat, Earth observation, navigation, GEO comsat with apogee engine, space telescope, lunar orbiter)
- New tools: `rocket_engine_design` (ideal-rocket nozzle model with calibrated propellant data: Merlin, RD-180, RS-25, Raptor, RL10 and Aestus Isp within 3 %; flow separation, sizes, mass, nozzle contour), `satellite_design` (mass, Δv, power, eclipse, battery depth of discharge), `lunar_transfer` (patched conics: TLI 3.13 km/s, 4.98 days, 114° lead, LOI, landing)
- `rocket_design`/`rocket_flight` accept `custom_parts` (user-designed engines and satellites), warn about missing fairings/interstages and vacuum nozzles at sea level, and give a mission Δv budget (LEO, GEO, lunar orbit, Moon landing, Mars)
- Flight: Earth flights include the moving Moon (restricted three-body in the Earth frame), telemetry switches to the Moon inside its sphere of influence, lunar landings/lift-offs, fairing jettison, exposed-engine drag, a trans-lunar-injection window planner, numerical trajectory prediction with the closest lunar pass, and a "start in low orbit" option. Tests fly a full LEO → lunar orbit mission (~2.5 days) through the tool
- Spaceflight Lab UI: palette by engine class, engine designer (live nozzle drawing, thrust vs altitude) and satellite designer saving to "My designs", fairing cutaway in the builder and peel-away on jettison, interstage shrouds, map view with the Moon, its sphere of influence and a ghost Moon at the predicted encounter, HUD with TLI window and encounter, drag-to-pan
- 618 tests passing (123 tools, 78 simulations)
- **Next:** 3D flight view, Mars transfers with the Sun's gravity, a manoeuvre-node planner, docking
- **Known issues:** flight is planar (no inclination changes); tanks are propellant-agnostic; the Moon's orbit is circular and coplanar

## 2026-09-29 — Phase 9d: Spaceflight Lab joins the Solar System
- `rocket_launch_state(date, site_longitude_deg)`: Earth flights are tied to the real sky — the pad sits at a real spaceport (Kourou, Sriharikota, Cape Canaveral, Baikonur, Wenchang; projected onto the equatorial flight plane), the model Moon starts at the real Moon's right ascension (JPL elements), and Earth's rotation follows the IAU prime meridian
- `rocket_flight` returns `view3d` (equatorial J2000): craft, pointing, Moon, predicted path, lunar encounter, Earth rotation angle and Sun direction at mission time; a test checks the pad, the Moon and the rotation against the ephemeris
- New 3D flight view (`frontend/js/space/flight3d.js`, shared sky in `space/sky.js`): the Solar System's textured Earth (day/night, clouds, atmosphere) and normal-mapped Moon at true scale, real star sky and Milky Way, the rocket with its flown trail and predicted trajectory, the Moon's sphere of influence and a ghost Moon at the predicted pass; camera focus on rocket, Earth or Moon
- Links: 🚀 in the Solar System launches a mission on the date it shows; ☉ SOLAR SYSTEM in the 3D flight view opens the Solar System on the mission date
- 619 tests passing
- **Known issues:** flights stay in the equatorial plane (real sites are projected onto the equator; the Moon's ±28° declination is flattened)

## 2026-09-30: Phase 10, the full-stack web app for the beta
- Platform (`app/platform/`): SQLite storage, accounts and sessions (scrypt, HttpOnly cookies, Origin check, rate limits), history API, space company API, challenges API. `/simulate`, `/ask`, `/tools` and `/app/*` need a session; `/docs` is off unless enabled; CSP and security headers on every response. Flight states are HMAC-signed so challenge results and fleet deployments can be trusted.
- Engine: parallel staging with strap-on boosters (design Δv and flight, solid boosters can't be throttled), 13 real vehicles and 10 real satellites (`vehicle_data.py`, `launch_vehicle_catalog`, `launch_vehicle_performance`, `launch_azimuth`), satellite orbits in real time (`satellite_track` with J2 and drag, `satellite_manoeuvre`, `satellite_imaging`, `orbit_from_parameters`), interplanetary missions (`interplanetary_porkchop`, `interplanetary_mission`: Lambert solver matches Curtis example 5.2; Mars 2026 window C3 ≈ 9 to 10 km²/s²), time to apoapsis and periapsis in flight telemetry.
- Frontend: public site in `frontend/site/` (landing, auth pages, legal pages, 404, cookie notice); app at `/app/` with navigation, account menu, Home, History, Account, Challenges and Mission Control pages; Spaceflight Lab with real rockets, booster drawing and exhaust, autosave and resume, save design, deploy to fleet, challenge banner with automatic checks, pause, quick save and load, warp to apsides and a keyboard help panel; Save button on every simulation.
- Brand from the new logo (SVG mark, favicon, light variant), IBM Plex fonts, em dashes and emojis removed from UI copy, AI analyst told to write plainly.
- 697 tests passing; every simulation and app page opens in the browser without console errors.
- **Fixed on the way:** Greenwich sidereal time in the fleet model (IAU W is measured from RA 90°, so GMST = W + 90°); signatures now survive the browser's number formatting.
- **Known issues:** the Spaceflight Lab still flies in a plane (inclination is chosen when a satellite is deployed); satellite photos use NASA GIBS imagery in the browser (250 m at best), so very sharp cameras show their footprint and resolution correctly but the picture is limited by the imagery; the static atmosphere ignores solar activity; SQLite on Render needs a persistent disk.
- **Next:** email verification, probes and fleet shown in the 3D Solar System, inclined ascents.

## 2026-09-30 (later): closing the history loop, probes in the Solar System, feedback
- Ask AI conversations save themselves to the history and reopen with their engine cards; the AI-not-configured message no longer mentions server settings.
- Solar System: "Save this view" (date, scale, speed, selected body) and reopening from the history; your company's probes appear on their Lambert transfer arcs at the date shown, and their labels open Mission Control on that probe.
- Send feedback from the account menu (stored in a `feedback` table, included in the data export, listed in the Privacy Policy).
- Beta admin page (`#/admin`, `/api/admin/overview`) for the emails in `ADMIN_EMAILS`: account and usage counts, feedback, challenge completions, newest accounts.
- **Next:** email verification, inclined ascents.

## 2026-09-30 (evening): pre-launch site for Cloudflare
- `cloudflare/`: static site for Cloudflare Pages built from the real landing page by `scripts/build_cloudflare_site.py`. Only `/` is live; every other address serves a "Coming soon" page (Cloudflare's 404.html); all "Join" buttons go to a waitlist form (placeholder until `waitlist_endpoint` is set); `/test` is guarded by a Pages Function asking for `TEST_USERNAME`/`TEST_PASSWORD`. Checked with wrangler: `/` 200, other paths show Coming soon, `/test` 401 without and 200 with the right password.
- Backend: `POST /api/waitlist` (form or JSON, CORS only for `WAITLIST_ORIGINS`, rate limited, stored in a `waitlist` table and listed on the admin page with "Copy all emails"); optional private-testing gate for the whole Render app (`TEST_GATE_USERNAME`/`TEST_GATE_PASSWORD`, `/health` stays open).

## 2026-09-30 (night): ASM Teach
- New part of the app at `#/teach`: 281 Class 9 to 12 experiments (140 physics, 64 chemistry, 77 maths), each a derivation, law, practical or graph from the syllabus. Chapters follow NCERT; CBSE, ICSE and state boards are mapped and ICSE-only topics (machines, calorimetry, banking, mole concept) are tagged.
- Engine (`app/modules/teach/`): experiments are data (inputs, formulas, graphs, equations, steps) parsed with the shared safe parser and compiled with numpy. Tools: `teach.catalog`, `teach.experiment`, `teach.practice`, `teach.recognize` (symbolic, time-limited). `log10` added to the shared parser.
- Classroom view: 20 kinds of picture (ray diagrams, circuits, pendulum, spring, waves, gas, pH beaker, Bohr atom, vectors, incline, decay, prism, lever, solids and more), graph, results, equations, derivation, readings table, practice with checked answers, AI co-teacher with teaching prompts, projector mode, whiteboard beside or over the experiment, lessons saved to the history.
- Home and landing page now lead with physics and ASM Teach; spaceflight is one feature among several. Cloudflare pre-launch site rebuilt.
- 761 tests passing (58 new, including 36 textbook values); the library and 34 classroom scenes open in the browser without console errors.
- **Known issues:** the board reads typed equations, not handwriting; symbols must match the textbook's letters; some graphs near a pole (lens at u = f) show a vertical line at the asymptote.
- **Next:** handwriting on the board, assignments, Hindi interface, board-specific chapter names.

## 2026-10-03 (evening): Virtual Chemistry Lab (sandbox)
- Engine (`app/modules/chemistry/labbench.py`): `chemistry.lab_catalog` (shelf: 44 chemicals with concentrations, 8 kinds of glassware, the reactions) and `chemistry.lab_step` (advance a bench of vessels by dt after add, pour and empty actions). 64 reactions balanced by the shared balancer: metals with water and acids, neutralisation, carbonates, precipitation, displacement, dissolving (CuSO₄ warms, NH₄Cl and KNO₃ cool), permanganate with Fe²⁺, H₂O₂ with MnO₂, thiosulphate, ammonia preparation, heating solids (blue vitriol, green vitriol, limestone, copper carbonate, lead nitrate, permanganate), iron and sulphur, burning magnesium, sulphur and copper in air. Heat from standard enthalpies of formation (Hess's law), energy balance with burner and room losses, boiling at 100 °C, gases escape with volume and test, pH from strong and weak acids/bases and buffers, indicator colours from the pH, solution colour and precipitates.
- UI (`frontend/js/sims/labbench.js`): shelf (chemicals and equipment), a bench of six places, tap or drag to add, drag one vessel onto another to pour, burner Off/Low/Medium/High, burette over a flask with a tap and a reading, time ×1/×5/×20, a lab notebook with observations, balanced equations, ΔH and gas tests. In ASM as a chemistry simulation and in ASM Teach as the Lab page.
- Tests: tests/test_chemistry_labbench.py (atoms conserved in every reaction, ΔH by Hess's law, neutralisation −55.8 kJ/mol and its temperature rise, sodium gives 0.005 mol H₂ and pH 13, PbI₂ mass from the limiting reagent, marble gives all its CO₂, boiling, cooling on dissolving, dehydration of blue vitriol, pH of standard solutions and a buffer, permanganate decolourised, pouring).
- Next: a measuring pipette and a dropper with exact drops, gas jars connected by a delivery tube (CO₂ into limewater from another vessel), flame tests for metal ions.

## 2026-10-03 (later): Class 12 practicals and the board paper choice
- ASM Teach board: plain, grid, lined or dotted board (remembered and saved with lessons); pen, highlighter, eraser, colours, size, undo, clear and pages in a side bar.
- 23 Class 12 practicals and activities from the NCERT laboratory manuals. Physics: resistivity of a wire, laws of combination with the metre bridge, internal resistance with the potentiometer, galvanometer resistance and figure of merit, AC mains frequency with a sonometer, concave mirror and convex lens by the u-v method, convex mirror and concave lens using a convex lens, glass slab with a travelling microscope, refractive index of a liquid, Zener regulator. Chemistry: enthalpy of neutralisation and of dissolution, thiosulphate kinetics, Daniell cell against concentration, paper chromatography, preparing Mohr's salt and acetanilide (yields). Maths: mean value theorem, area between a line and a parabola, integration by parts, skew lines. Each has textbook checks in tests/test_teach.py.
- Library: 308 experiments (physics 152, chemistry 75, maths 81).
- Qualitative practicals (salt analysis, functional group tests, colloids) are left for the chemistry sandbox lab, where reactions can be seen rather than computed from a formula.

## 2026-10-03: Volumetric analysis practicals in ASM Teach
- Four new practicals under "Volumetric Analysis (Practical)": KMnO₄ against oxalic acid and KMnO₄ against Mohr's salt (Coursework 4), NaOH against oxalic acid and HCl against sodium carbonate (Coursework 2). Each takes the mass weighed, the flask volume, the pipetted volume and the concordant burette reading, and computes the standard solution's molarity, the unknown's molarity (n₁M₁V₁ = n₂M₂V₂ with the electrons or H⁺ per formula unit) and its strength in g/L, with the balanced equation and the derivation.
- New "titration" classroom picture: a burette on a stand over a conical flask; the titrant runs in to the engine's end-point reading and the flask changes colour (KMnO₄ pale pink, phenolphthalein pink, methyl orange yellow to orange-red).
- Graph titles keep chemical formulas as written (KMnO₄, not kmno₄). 285 experiments in the library.

## 2026-10-02 (evening): Spaceflight Lab fixes from testing
- Solid bodies: the 3D flight view keeps the camera outside the Earth and the Moon, and the Solar System keeps it outside every planet and moon (not only the one in focus).
- Steering: a tap on ‹ or › turns the rocket 1°, holding turns it at 20° a second; Q / E nudge 1° from the keyboard; the panel shows the angle from vertical.
- Launch pad: a lattice service tower and a wider pad drawn as part of the ground, so they stay behind at lift-off.
- Builder: tapping a part adds it above the selected part; parts can be dragged up and down on the rocket, or dragged from the list onto it; a + beside each stage attaches side boosters (two at a time, one each side), with a count, a stage switch and remove. Three generic side boosters (two solid, one liquid) join the real ones; boosters and their flames sit beside the widest part of their stage.
- Gravity was checked: with the engines off the rocket stays on the pad; after cut-off gravity and drag slow it at about 10 m/s per second.
- Next: free placement of any part on the sides (radial tanks and engines need engine support), symmetry choices (3 or 4 boosters around the core).
- Later the same day: flight layout reworked (telemetry along the bottom, steering pad top left, throttle lever on the left); a stage chooser beside STAGE separates one or several stages at once, and tapping a stage on the rocket offers to separate it; camera button with Follow, Launch view (a fixed camera at the pad that zooms out to keep the rocket in frame) and On the rocket (3D, beside the rocket looking down past the tail); covers fit what they cover (nose, decoupler and interstage take the width below, fairings fit the payload with a tapered base for wide payloads, conical adapters where stacked parts change width); a satellite or probe put on top gets a decoupler and a fitted fairing. Fixed: the 3D prediction line failed after the 3D view had been closed.

## 2026-10-02 (later): owner account from host settings
- OWNER_EMAIL and OWNER_PASSWORD (Render environment, never in the code) create that account on startup if it is missing, so the team signs in at /login without signing up. An existing account and its password are left alone. Test in tests/test_platform_auth.py.
- Automatic sign-in from the /test desk was considered and left out: every app page still needs a normal sign-in.
- The same owner email and password open ASM Teach: on startup the owner gets a "Plazmonix AI" school in which the owner's account is the first teacher; the ASM Teach sign-in accepts the email as school admin or teacher. The school panel can't pause, re-password or remove the owner's account.

## 2026-10-02: /test team desk
- /test (behind TEST_USERNAME / TEST_PASSWORD) is now a team desk: status cards for the website, robots.txt and sitemap, waitlist storage and the Render backend (checked server-side through /health, via the new /test/status.json); waitlist totals (all, 24 hours, 7 days), the latest ten sign-ups and the CSV; a launch checklist kept in the browser; links to Cloudflare, GitHub, Render, Search Console, Bing, PageSpeed, the rich results test and a share preview.
- New waitlist entries store their date, country and page as KV metadata so the desk can list them without one read per email.
- Next: set beta_app_url once the backend is live on Render; the backend card and the app buttons then work.

## 2026-10-01 (night): search engine set-up for realityasm.com
- The pre-launch build (scripts/build_cloudflare_site.py) now writes sitemap.xml (the main page and its pictures), a robots.txt that points to it and keeps /test and /api out, and site.webmanifest.
- The main page gets a search title and description, canonical link, robots directives, Open Graph and Twitter cards with a 1200x630 share picture, app icons, and JSON-LD for Plazmonix AI, the website, Reality ASM and ASM Teach. Gallery pictures have alt text.
- The Worker is named reality-asm to match the Cloudflare dashboard (Workers Builds rejected the old name).
- Next: verify the domain in Google Search Console and Bing Webmaster Tools and submit the sitemap; redirect www to the bare domain; the landing page's Saturn screenshot still shows the old Solar System time bar.

## 2026-10-01 (evening): ASM Teach as a separate product with school and teacher accounts
- The landing page has two doors: Open ASM (simulations, Spaceflight, Solar System, Mission Control) and Open ASM Teach. ASM Teach left the ASM navigation and lives at /teach (sign-in) and /teach/app.
- Accounts (app/platform/teach.py): schools sign up through Google (the existing OAuth client, in a "teach" mode; Google proves the email, a signed 30-minute cookie carries it to set-up), then choose a username and password and must tick the ASM Teach Terms (frontend/site/legal/teach-terms.html). School admins add teachers with username and password; usernames share one namespace. Each school admin and teacher is backed by an internal users row, so sessions, /simulate, the AI and saved lessons work unchanged.
- Admin panel: teacher table with 30-day usage, pause/resume (signs the teacher out), new password (signs out everywhere), remove (deletes account, lessons and files), most used experiments. Teacher panel: profile, password, usage, saved lessons; responsive for phones.
- Teacher board: the whiteboard fills the screen; a rail opens suggested experiments (from equations written on the board and from listen mode), the Equation Lab, YouTube (privacy-enhanced embed), web windows (with an open-in-new-tab fallback for sites that refuse framing), the teacher's files in movable windows, the AI co-teacher (only when tapped) and Save. The board autosaves locally and saves as a lesson.
- Files: PDF, PPT/PPTX, DOC/DOCX, images, MP4/WebM up to 25 MB, 300 MB per teacher, stored in SQLite; Office files become PDF when LibreOffice (Impress/Writer) is on the server. Served with frame-ancestors 'self' so they open inside ASM Teach only.
- Tests: tests/test_platform_teach.py (sign-up needs Google proof and terms, roles, isolation between schools, pausing, files, Google callback in school mode). Browser run through sign-up, admin, teacher board, files, profile and a phone viewport with no console errors.
- Known limits: YouTube search opens youtube.com in a new tab (in-app search would need a YouTube API key); some websites refuse to be shown inside other pages; Render's Python runtime has no LibreOffice.

## 2026-10-01 (later): Equation Lab and listen mode for ASM Teach
- `teach.explore` (app/modules/teach/explore.py): the board builds any equation. It proves identities with a chain of rewrites plus random-point checks, flags statements that can never hold (sin²x + cos²x = 2, 2 + 2 = 5), solves over the reals with general solutions (sin x = 1/2), explains a missing real solution by the range of the function (sin x = 2), studies y = f(x) (derivative, zeros, turning points, period, domain), draws implicit curves by marching squares and names conics, draws z = f(x, y) as contours, checks physics formulas for dimensional consistency (F = mv is rejected; T in PV = nRT is read as temperature) and turns them into live formulas, and balances or rejects chemical equations. Board notation such as sin x, sinx, sin²x and sin^2 x is understood.
- `teach.listen` (app/modules/teach/listen.py): one spoken sentence becomes an experiment with values or an Equation Lab equation. Indian classroom phrasing is handled ("into" multiplies, "by" divides, "root" covers the rest of the term), case is restored from the textbook equations, units are converted (cm to m, g to kg) and values clamped.
- UI: Equation Lab card on the library reader and in the board reader; Listen button in the library and classroom (browser speech recognition, en-IN), one listener across pages. Both tools are also available to the AI co-teacher.
- Tests: tests/test_teach_explore.py, tests/test_teach_listen.py (813 passing overall). Checked in the browser with a simulated microphone, no console errors.
- Next: Hindi listen mode, calculus notation in the Equation Lab, handwriting recognition.

## 2026-10-01: Coursework, black hole and singularity, quantum dynamics, promo videos
- Solar System: the time controls are now a mission clock panel at the top left (ISO date, a rate slider, Forward/Hold/Now), and the tools moved to a row along the bottom, so the layout no longer resembles other planetarium apps.
- ASM Teach now shows Coursework 1 to 4 instead of classes, and no board names, so it reads as one library for every syllabus (UI, landing page, deck).
- New tools: `physics.black_hole` (horizon, photon sphere, ISCO, Hawking temperature and lifetime, clock rate, escape speed, tidal stretch, Kretschmann curvature, proper time to fall to r = 0), `physics.black_hole_light` (null geodesics; exact deflection integral gives 1.75" at the Sun's limb), `physics.black_hole_orbit` (timelike geodesics, precession, plunging), `physics.wave_packet` (split-step Schrödinger solver: barrier, step, well, double barrier, trap), `physics.quantum_oscillator`, `physics.rabi_oscillation`.
- New simulations: Black Hole & Singularity, Quantum Wave Packets, Quantum Harmonic Oscillator, Spin & Rabi Oscillations (82 in total).
- Promo videos for physics, the Spaceflight Lab and the Solar System, made from frame-by-frame recordings of the app (fake browser clock, 30 fps) in the reel's design.
- 771 tests passing.
