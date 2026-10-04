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
- [x] Charged particle in E/B fields (Lorentz force, cyclotron)
- [x] Collisions lab (1D/2D, elastic/inelastic, momentum)
- [x] Forces & motion on a ramp with friction
- [x] Energy skate park (track energy conservation)
- [x] Rotational dynamics: torque, moment of inertia, rolling
- [x] Double pendulum & chaos
- [x] Coupled oscillators & normal modes
- [x] Driven damped oscillator & resonance curves
- [x] Buoyancy & density; fluid pressure; Bernoulli flow
- [x] Doppler effect & sound
- [x] Heat conduction (1D heat equation, Crank–Nicolson); 2D still to do
- [x] Thermodynamic cycles: Carnot, Otto, Diesel on a PV diagram
- [x] Blackbody radiation (Planck, Wien, Stefan–Boltzmann)
- [x] Photoelectric effect
- [x] Hydrogen atom energy levels & spectra (Bohr / Rydberg)
- [x] Quantum particle in a box / tunnelling (1D Schrödinger)
- [x] Radioactive decay chains & half-life
- [x] Special relativity: time dilation, length contraction, twin paradox
- [x] Kepler's laws (equal areas, T² ∝ a³); multi-planet n-body view still to do
- [x] Orbital perturbations (J2 precession, sun-synchronous orbits, drag decay)

**Chemistry**
- [x] Build an atom / isotopes & atomic mass
- [x] Molecule shapes (VSEPR geometry)
- [x] Balancing chemical equations (interactive)
- [x] Reactants, products & leftovers (limiting reagent visual)
- [x] Molarity & dilution
- [x] Acid–base titration curves (strong/weak, indicators)
- [x] Buffers & Henderson–Hasselbalch
- [x] Polyprotic acids & speciation diagrams
- [x] Beer–Lambert law (spectrophotometer)
- [x] Electrochemistry: galvanic cells & the Nernst equation
- [x] Real gases (van der Waals) vs ideal
- [x] Vapour pressure & boiling point (Clausius–Clapeyron)
- [x] States of matter & full P–T phase diagrams (triple point, sublimation, critical point)
- [x] Colligative properties
- [x] Reaction mechanisms & energy profiles (catalysts)
- [x] Radiometric dating

**Mathematics**
- [x] Unit circle & trigonometric graphs
- [x] Fourier series & signal synthesis
- [x] Taylor series approximation explorer
- [x] Riemann sums & numerical integration
- [x] Slope fields & ODE solution curves; phase portraits
- [x] Vector addition & dot/cross products
- [x] 2D linear transformations & eigenvectors
- [x] Complex numbers & the complex plane
- [x] Conic sections; polar and parametric curves
- [x] Probability distributions & the central limit theorem
- [x] Monte Carlo estimation (π, integrals)
- [x] Least-squares regression & curve fitting
- [x] Newton's method & root-finding visualiser
- [x] Fractals (Mandelbrot / Julia sets)
- [x] Graph theory: shortest paths (Dijkstra, Bellman–Ford) & minimum spanning trees

## Phase 7 — AI representative
- [x] NIM client with multi-key rotation + retry on 429/5xx (`app/agent/llm.py`)
- [x] Convert registry tools into OpenAI-style tool schemas
- [x] Agent loop: question → tool call(s) → execute → explain (`app/agent/representative.py`)
- [x] `POST /ask` endpoint
- [x] Tests with a mocked LLM (no real API calls in tests)
- [x] Ask page in the simulator UI (`#/ask`) showing each tool call and its computed result

## Phase 8 — Polish
- [x] Consistent error handling (bad input → clear 422 messages; tool bugs → JSON 500)
- [x] Input validation ranges (no negative masses, etc.) + signature type checks, NaN/inf rejection, fuzz test over all tools
- [x] README examples for every domain
- [x] Full test pass + coverage check (93 % line coverage)
- [x] Time limits for open-ended symbolic tools (forked child process, killed after `TOOL_TIMEOUT_S`)

## Phase 9 — Flagship simulators & AI analyst
- [x] Ephemeris tool: real planet/Moon positions for any date (JPL elements), IAU spin and pole orientation
- [x] Solar System 3D (three.js): realistic textures, Earth day/night shader, clouds, atmospheres, rings, time controls, info panel
- [x] Rocketry engine: parts catalogue, staged design analysis, 2D flight integrator (thrust, drag, staging, landing, orbits)
- [x] Spaceflight Lab: rocket builder + flight view with HUD, throttle, SAS, staging, time warp and map view
- [x] AI analyst panel on every simulation (sim context sent to `/ask`)
- [x] Multi-provider LLM config (NVIDIA NIM, Groq, xAI) with key rotation; `/llm/status`
- [ ] Connect real Groq keys and tune the prompts with live answers
- [x] Moons of Jupiter/Saturn, asteroid belt and comets in the 3D view (29 moons, dwarf planets, asteroids, comets with tails, main belt/trojans/Kuiper belt)
- [x] Realistic rendering for every body: normal maps, ring shadows, atmospheres, Celestia/NASA textures for all major moons
- [x] Universe scale ladder: real stars (HYG), Milky Way model with rotation curve, ~11,000 real galaxies, ΛCDM observable universe (`star_catalog`, `milky_way`, `galaxy_catalog`, `cosmology`)
- [ ] Constellation lines and exoplanet systems in the Stars view
- [ ] Deeper-survey galaxies (beyond ~2 billion ly) if an openly licensed catalogue can be bundled
- [x] Transfers between bodies: the Moon moves and pulls in Earth flights (restricted three-body), lunar orbit, landing and lift-off, TLI window planner
- [x] Engine classes (small/medium/large/heavy), payload fairings, interstages, example satellites
- [x] Engine designer (`rocket_engine_design`) and satellite designer (`satellite_design`) whose designs fly as custom parts
- [x] Rocket flight in 3D, connected to the Solar System: real launch date and site, real Moon/Sun/Earth rotation, true-scale Earth–Moon view, links both ways
- [x] Mars, Venus, Jupiter and Saturn transfers with the Sun's gravity (Lambert solver, porkchop plots, probes in Mission Control)
- [ ] Inclined (3D) ascent trajectories in the Spaceflight Lab

## Phase 10: Full-stack web app (beta)
- [x] Accounts: sign up, sign in, sign out, password change and reset (SMTP optional), Google sign-in (optional), invite codes, data export, account deletion
- [x] Sessions in HttpOnly cookies, scrypt passwords, rate limits, CSP and security headers, API docs off in production
- [x] Engine, AI and app files behind sign-in; HMAC-signed flight states
- [x] Saved history for flights (autosave and resume), designs, missions, photos, simulation snapshots and challenges
- [x] Public site: landing page, Terms, Privacy, Cookies, Acceptable Use, About, 404; cookie notice
- [x] Brand: logo mark and favicon, ink and ember colours, IBM Plex fonts; UI copy without em dashes or emojis
- [x] Real launch vehicles (ISRO, NASA, SpaceX, ESA, Roscosmos, CNSA, Rocket Lab) with strap-on boosters (parallel staging) and a payload check against published figures
- [x] Real satellites with instruments (Cartosat-3, EOS-05, EOS-04, Landsat 9, Sentinel-2A, WorldView-3, INSAT-3DS, Starlink, GPS III, Hubble)
- [x] Space company: launch service, fleet in real time (J2 drift, drag decay, re-entry), thruster burns, camera photos, deep-space probes
- [x] Challenge mode (10 missions checked on the server) and sandbox
- [x] Spaceflight Lab: pause, quick save and load, warp to apoapsis and periapsis, keyboard help, deploy satellites to the fleet
- [x] Render deployment files (`render.yaml`, `.env.example`)
- [ ] Email verification on sign-up
- [x] Show the user's probes inside the 3D Solar System (along their transfer arcs, on any date)
- [x] In-app beta feedback, saved AI conversations, saved Solar System views
- [x] Beta admin page (sign-ups, usage, feedback)
- [ ] Shared mission gallery

## Phase 11: ASM Teach (the classroom product)
- [x] Curriculum catalogue: 308 experiments across Class 9 to 12 physics, chemistry and maths, chapters following NCERT, with ICSE and state board topics tagged (`app/modules/teach/`)
- [x] Engine tools `teach.catalog`, `teach.experiment` (outputs, swept graphs, equations, derivation), `teach.practice` (questions with engine-computed answers, choices and working), `teach.recognize` (reads an equation from the board and matches experiments, rearranges it)
- [x] Classroom view: live picture, graph, inputs, results, equations, derivation, observation table (readings, CSV), practice, AI co-teacher, projector mode
- [x] Whiteboard beside the experiment or drawn over it: pen, highlighter, eraser, colours, pages, undo, typed equations read by the engine
- [x] Lessons saved to the history (inputs, board pages, readings) and reopened
- [ ] Handwriting recognition on the board (today the board reads typed equations)
- [ ] Class assignments and teacher reports
- [ ] Hindi and regional language interface
- [ ] Offline classroom mode
- [x] Library shown as Coursework 1 to 4 instead of classes and boards, so it reads as one library for every syllabus
- [x] Equation Lab (`teach.explore`): any equation is built from the mathematics, not looked up. Identities proved step by step, impossible statements caught with the reason, exact solutions (general solutions for trigonometry), function study, implicit curves and conics, z = f(x, y) contours, dimensional checks for physics formulas with live sliders, chemical equations balanced or rejected
- [x] Listen mode (`teach.listen`): the teacher speaks, ASM Teach follows. Spoken maths ("T equals 2 pi root L by g", "into", "by"), topics and values ("length 2 metres") open the experiment with those values or build the equation; browser speech recognition, no extra libraries
- [ ] Listen mode in Hindi (speech recognition hi-IN plus spoken Hindi maths)
- [x] ASM Teach as its own product at /teach: sign-in for schools (private institutions marked coming soon); school admins sign up with Google, set a username and password and accept the ASM Teach Terms; teachers sign in with the username and password the school gives them
- [x] School admin panel: add, pause, reset and remove teachers; usage per teacher (sessions, experiments, lessons, media) and the most used experiments
- [x] Teacher board: full-width whiteboard with a folding tool rail (suggested experiments from the board and speech, Equation Lab, YouTube, web windows, the teacher's own files, listen mode, AI co-teacher only when tapped, save lesson)
- [x] Teacher files (PDF, slides, pictures, video) with per-teacher storage; slides converted to PDF where LibreOffice is installed
- [x] Teacher profile panel (works on phones): profile, password, usage, saved lessons
- [ ] Private institutions sign-up
- [ ] Files on object storage instead of SQLite once schools upload a lot
- [ ] Equation Lab for calculus notation (d/dx, ∫) and differential equations

## Phase 12: Relativity and quantum dynamics
- [x] Schwarzschild black hole: radii, clocks, curvature, tidal stretch, light bending, orbits, fall to the singularity
- [x] Time-dependent Schrödinger solver for wave packets; quantum harmonic oscillator; Rabi oscillations on the Bloch sphere
- [ ] Rotating (Kerr) black hole and an accretion disc image
- [ ] Two-dimensional wave packets (double slit)

- [x] Virtual Chemistry Lab (sandbox): shelf of 40+ chemicals and glassware, burner, burette; engine tool `chemistry.lab_step` with 64 balanced reactions, Hess's-law heat, boiling, gases with their tests, pH and indicators; in ASM and as the Lab page in ASM Teach
- [x] Lab sandbox, full shelf: concentrated acids, test reagents, qualitative-analysis reactions, delivery tube, gas jar, filtering, litmus, pH paper, splints, flame tests, evaporating to crystals
- [x] ASM Teach real-life pictures (worlds) for every number-only experiment, computed by the engine
- [x] ASM Teach inputs take any value (outside the slider range too), with notes and a widened graph
- [x] Simulations gallery shelves (quantum, space, relativity and nuclear separate from physics)
- [x] Space Program: Build and fly plus Mission Control in one place
- [x] Phone layout for the app shell, gallery, Teach and the Space Program
- [x] Worlds for the 21 maths graph experiments (roller coaster, Ferris wheel, dish, orbits, colony, tank)
- [x] Type-any-value on every simulation slider
