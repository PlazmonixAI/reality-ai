# Reality ASM — Advanced Simulation Machine

Reality ASM (Advanced Simulation Machine) is Plazmonix AI's research-simulation engine for Physics, Chemistry and Mathematics.
An AI representative (LLM via NVIDIA NIM) understands a research question, routes it to the right simulation tool, runs it, and explains the result.

Built by Plazmonix AI (a Velostra Aerospace company).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add NVIDIA NIM keys
uvicorn app.main:app --reload
pytest
```

Open **http://localhost:8000** for the interactive simulator, or http://localhost:8000/docs for the API.

## Simulator
PhET-style interactive simulations in `frontend/` (plain JavaScript + Canvas, no build step). Every number on screen comes from the engine's tools; the browser only animates the results.

| Physics | Chemistry | Mathematics |
|---|---|---|
| Projectile Motion · Gravity & Orbits · Hohmann Transfer · Earth–Moon Voyage · Masses & Springs · Pendulum Lab · Rocket Lab · Waves on a String · Wave Interference · Lenses & Mirrors · Bending Light · Circuit Builder · Charges & Fields · Collisions Lab · Forces on a Ramp · Energy Skate Park · RC/RL/RLC Circuits · Faraday's Law · Heat Engines · Blackbody Spectrum · Photoelectric Effect · Hydrogen Atom · Radioactive Decay · Special Relativity · Resonance · Coupled Oscillators · Double Pendulum & Chaos · Charges in E & B Fields · Doppler Effect · Rolling Race · Buoyancy · Fluid Flow (Bernoulli) · Heat Conduction · Quantum Wells · Quantum Tunnelling · Kepler's Laws · J2 Precession · Orbital Decay | Gas Properties · Reaction Rates · pH Scale · Chemical Equilibrium · Acid–Base Titration · Buffers · Beer's Law Lab · Molecule Shapes · Build an Atom · Molarity & Dilution · Galvanic Cells · Real Gases · Vapour Pressure & Boiling · Reaction Energy Profile · Balancing Equations · Reactants & Leftovers · Polyprotic Acids · Colligative Properties · Radiometric Dating · Phase Diagrams | Calculus Grapher · Unit Circle & Trig · Fourier Series · Slope Fields & Phase Portraits · Vector Addition · Probability & the CLT · Taylor Series · Riemann Sums · Complex Plane · Linear Transformations · Newton's Method · Conic Sections · Parametric & Polar Curves · Least-Squares Fitting · Monte Carlo · Fractal Explorer · Shortest Paths & Spanning Trees |

## API examples
`POST /simulate` runs one tool; `GET /tools` lists all of them with descriptions. Inputs are SI unless a tool says
otherwise, and every result carries `units` and `assumptions`. Bad input returns HTTP 422 with a clear message
(unknown/missing/mistyped arguments, NaN, impossible values); open-ended symbolic work is time-limited.

```bash
# Mathematics — exact integral
curl -s localhost:8000/simulate -H 'content-type: application/json' \
  -d '{"domain":"mathematics","name":"integrate","args":{"expression":"x**2*sin(x)","lower":0,"upper":"pi"}}'

# Physics — LEO → GEO Hohmann transfer (≈ 3.89 km/s)
curl -s localhost:8000/simulate -H 'content-type: application/json' \
  -d '{"domain":"physics","name":"hohmann_transfer","args":{"alt1":300000,"alt2":35786000}}'

# Physics — electron tunnelling through a 2 eV, 0.5 nm barrier
curl -s localhost:8000/simulate -H 'content-type: application/json' \
  -d '{"domain":"physics","name":"quantum_tunnelling","args":{"energy_ev":1,"barrier_ev":2,"width_nm":0.5}}'

# Chemistry — limiting reagent and yield
curl -s localhost:8000/simulate -H 'content-type: application/json' \
  -d '{"domain":"chemistry","name":"stoichiometry","args":{"equation":"H2 + O2 -> H2O","masses":{"H2":4,"O2":16}}}'

# Chemistry — Daniell cell with the Nernst equation
curl -s localhost:8000/simulate -H 'content-type: application/json' \
  -d '{"domain":"chemistry","name":"galvanic_cell","args":{"anode":"Zn","cathode":"Cu","anode_concentration":0.01}}'
```

## Ask the AI representative
Open **http://localhost:8000/#/ask** (or `POST /ask`). The representative (NVIDIA NIM, tool-calling) picks the relevant
engine tools, runs them and explains the result; each answer lists the tool calls and their computed outputs.

```bash
# .env — comma-separated keys are pooled and rotated (429/5xx cool a key down, 401/403 disable it)
NIM_API_KEYS=nvapi-...,nvapi-...
NIM_MODEL=meta/llama-3.1-70b-instruct

curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "How much delta-v to go from a 300 km LEO to GEO?"}'
# → {"answer": "...about 3.89 km/s...", "tool_calls": [{"tool": "physics.hohmann_transfer", "args": {...}, "result": {...}}], ...}
```

Without keys `/ask` returns 503; the simulations and `/simulate` work regardless.

## Docs
- `CLAUDE.md` – rules and brief for Claude Code
- `docs/ROADMAP.md` – session-by-session build plan
- `docs/ARCHITECTURE.md` – how the system fits together
- `docs/PROGRESS.md` – what is done so far
