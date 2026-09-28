# Reality ASM — Build Roadmap

Scope: Physics, Chemistry and Mathematics, with an interactive simulator. Biology is out of scope.

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

## Phase 5 — Simulator frontend (batch 1) ✅
- [x] Frontend served by FastAPI at `/` (plain JS + Canvas, no build step), gallery + hash router
- [x] Shared kit: engine client with debounced latest-wins requests, controls, HiDPI canvas + pan/zoom, graphs with hover, playback bar
- [x] New engine tools for the visuals: `evaluate_function`, `pendulum`, `maxwell_boltzmann`, oscillator energy arrays
- [x] 12 simulations: Projectile Motion, Gravity & Orbits, Hohmann Transfer, Earth–Moon Voyage, Masses & Springs, Pendulum Lab, Rocket Lab, Gas Properties, Reaction Rates, pH Scale, Chemical Equilibrium, Calculus Grapher
- [x] Tests: UI served, every sim module exists/parses, sims only call registered tools

## Phase 6 — Simulation catalogue (batches 2+)
Goal: cover the standard simulations taught and used worldwide in physics, chemistry and mathematics.
Each one needs its engine tool(s) with textbook-checked tests first, then the interactive sim.

**Physics**
- [x] Waves on a string / standing waves
- [x] Wave interference & double slit
- [x] Geometric optics: lenses & mirrors (ray tracing)
- [x] Refraction & Snell's law, total internal reflection
- [x] DC circuit construction (Kirchhoff solver)
- [x] RC / RL / RLC circuits (transients, resonance)
- [x] Coulomb's law & electric field lines / equipotentials
- [x] Magnetic fields, Faraday's law & induction
- [ ] Charged particle in E/B fields (Lorentz force, cyclotron)
- [x] Collisions lab (1D/2D, elastic/inelastic, momentum)
- [x] Forces & motion on a ramp with friction
- [x] Energy skate park (track energy conservation)
- [ ] Rotational dynamics: torque, moment of inertia, rolling
- [ ] Double pendulum & chaos
- [ ] Coupled oscillators & normal modes
- [ ] Driven damped oscillator & resonance curves
- [ ] Buoyancy & density; fluid pressure; Bernoulli flow
- [ ] Doppler effect & sound
- [ ] Heat conduction (1D/2D heat equation)
- [ ] Thermodynamic cycles: Carnot, Otto, Diesel on a PV diagram
- [ ] Blackbody radiation (Planck, Wien, Stefan–Boltzmann)
- [ ] Photoelectric effect
- [ ] Hydrogen atom energy levels & spectra (Bohr / Rydberg)
- [ ] Quantum particle in a box / tunnelling (1D Schrödinger)
- [ ] Radioactive decay chains & half-life
- [ ] Special relativity: time dilation, length contraction, twin paradox
- [ ] Kepler's laws & solar system n-body
- [ ] Orbital perturbations (J2 precession, drag decay)

**Chemistry**
- [x] Build an atom / isotopes & atomic mass
- [x] Molecule shapes (VSEPR geometry)
- [ ] Balancing chemical equations (interactive)
- [ ] Reactants, products & leftovers (limiting reagent visual)
- [ ] Molarity & dilution
- [x] Acid–base titration curves (strong/weak, indicators)
- [x] Buffers & Henderson–Hasselbalch
- [ ] Polyprotic acids & speciation diagrams
- [x] Beer–Lambert law (spectrophotometer)
- [ ] Electrochemistry: galvanic cells & the Nernst equation
- [ ] Real gases (van der Waals) vs ideal
- [ ] States of matter & phase diagrams (Clausius–Clapeyron)
- [ ] Colligative properties
- [ ] Reaction mechanisms & energy profiles (catalysts)
- [ ] Radiometric dating

**Mathematics**
- [x] Unit circle & trigonometric graphs
- [x] Fourier series & signal synthesis
- [ ] Taylor series approximation explorer
- [ ] Riemann sums & numerical integration
- [x] Slope fields & ODE solution curves; phase portraits
- [x] Vector addition & dot/cross products
- [ ] 2D linear transformations & eigenvectors
- [ ] Complex numbers & the complex plane
- [ ] Conic sections; polar and parametric curves
- [x] Probability distributions & the central limit theorem
- [ ] Monte Carlo estimation (π, integrals)
- [ ] Least-squares regression & curve fitting
- [ ] Newton's method & root-finding visualiser
- [ ] Fractals (Mandelbrot / Julia sets)
- [ ] Graph theory: shortest paths

## Phase 7 — AI representative
- [ ] NIM client with multi-key rotation + retry on 429/5xx (`app/agent/llm.py`)
- [ ] Convert registry tools into OpenAI-style tool schemas
- [ ] Agent loop: question → tool call(s) → execute → explain (`app/agent/representative.py`)
- [ ] `POST /ask` endpoint
- [ ] Tests with a mocked LLM (no real API calls in tests)

## Phase 8 — Polish
- [ ] Consistent error handling (bad input → clear 422 messages)
- [ ] Input validation ranges (no negative masses, etc.)
- [ ] README examples for every domain
- [ ] Full test pass + coverage check
