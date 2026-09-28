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
