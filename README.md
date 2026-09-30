# Reality ASM: Advanced Simulation Machine

Reality ASM is a research-simulation engine for physics, chemistry and mathematics, by Subham Agarwal and Plazmonix AI.
It is now a full web app: public site, accounts, saved history, a space company that runs in real time, challenge
missions, the Spaceflight Lab with real launch vehicles, the Solar System and 78 simulations. An AI analyst
(NVIDIA NIM, Groq or xAI) explains results using the engine's tools.

Built by Plazmonix AI (a Velostra Aerospace company).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional locally: add LLM keys, leave COOKIE_SECURE=false for http://localhost
uvicorn app.main:app --reload
pytest
```

Open **http://localhost:8000**, create an account, and you're in the app at `/app/`.

## The web app

| Where | What |
|---|---|
| `/` | Public landing page, sign in and sign up, Terms, Privacy, Cookies, Acceptable Use, About |
| `/app/` | The app (signed-in users only): home, simulations, Spaceflight Lab, Mission Control, Challenges, History, Ask AI, Account |
| `/api/auth/*`, `/api/account` | Sign up and in (email + password; Google if configured), sessions, password change and reset, data export, account deletion |
| `/api/history` | Saved flights, designs, missions, photos, simulation snapshots (open, continue, star, rename, delete) |
| `/api/company` | Space company: launch service on real rockets, fleet in real time (drag decay, J2), burns, camera photos, deep-space probes |
| `/api/challenges` | Ten missions checked on the server |
| `/simulate`, `/ask`, `/tools` | The engine and the AI analyst (signed-in users only, rate limited) |

**Security:** passwords hashed with scrypt; sessions are random tokens in HttpOnly, SameSite=Lax cookies (only their
hash is stored); JSON-only writes plus an Origin check against cross-site requests; strict Content Security Policy
and security headers; rate limits on sign-in, sign-up, the engine and the AI; `/docs` and `/openapi.json` are off
unless `ENABLE_API_DOCS=true`. The simulation code runs only on the server; the app's JavaScript is served only to
signed-in users. Flight states are HMAC-signed, so challenges and fleet deployment only accept flights the engine
actually produced.

**Storage:** a single SQLite file (`DATABASE_PATH`). Back it up by copying the file.

## ASM Teach
The classroom part of the app, at `/app/#/teach`: 281 Class 9 to 12 physics, chemistry and maths experiments (derivations, laws,
practicals and graphs), mapped to NCERT, CBSE, ICSE and state boards. Each one has a live picture, a graph, the equations and
derivation, an observation table, practice questions with engine-computed answers, an AI co-teacher and a whiteboard that reads
typed equations. Lessons save to the history. Engine tools: `teach.catalog`, `teach.experiment`, `teach.practice`, `teach.recognize`.

```bash
curl -b cookies.txt -X POST localhost:8000/simulate -H 'Content-Type: application/json' \
  -d '{"domain":"teach","name":"experiment","args":{"experiment_id":"p11-pendulum","values":{"L":1}}}'
```

## Pre-launch site on Cloudflare

`cloudflare/` holds a static version of the landing page for Cloudflare Pages: only the main page is live, every other
address shows "Coming soon", the "Join" buttons collect emails for the waitlist, and `/test` is a private page behind
a username and password. See `cloudflare/README.md`.

## Deploying on Render

1. Create a Web Service from this repo (or use `render.yaml` as a Blueprint). Build: `pip install -r requirements.txt`.
   Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips '*'`.
2. Attach a **persistent disk** at `/var/data` and set `DATABASE_PATH=/var/data/reality.db`. Without a disk, Render
   wipes the database on every deploy or restart.
3. In **Environment**, set `SECRET_KEY` (long random), `COOKIE_SECURE=true`, `PUBLIC_BASE_URL`, `CONTACT_EMAIL`, and the
   LLM keys (`LLM_PROVIDER` + `NIM_API_KEYS` / `GROQ_API_KEYS` / `XAI_API_KEYS`). Optional: `BETA_INVITE_CODES`, `ADMIN_EMAILS` (who can open the beta admin page),
   `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`, `SMTP_*` for password-reset email. All variables are listed in `.env.example`.
   No secrets live in the repository.

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

## Flagship sims
- **Solar System 3D** (`#/sim/solarsystem`) — the real Solar System on any date 1800–2050: planets, 29 moons, dwarf planets, asteroids, comets and the asteroid/Kuiper belts, all positioned by the engine; realistic rendering (normal maps, ring shadows, atmospheres, Earth day/night with clouds) and a sky of real stars.
- **Universe Explorer** (`#/sim/universe`) — the same view's scale ladder: nearby stars (HYG catalogue), the Milky Way (model + rotation curve), ~11,000 real galaxies and the ΛCDM observable universe out to the cosmic microwave background. Scroll to zoom seamlessly between scales.
- **Spaceflight Lab** (`#/sim/spaceflight`) — design your own engines (nozzle thermodynamics) and satellites (power/eclipse budget), build a rocket from 11 engines in four size classes, tanks, interstages, fairings and satellites (engine-computed Δv/TWR and mission budget), then fly it from a real spaceport on a real date: ascent, orbit, fairing jettison, a trans-lunar injection with the Moon's real gravity, lunar orbit and landing — in a 2D view, a map, or a true-scale 3D view of the Earth and Moon linked to the Solar System sim.
- **AI analyst** on every simulation — a side panel that explains what's on screen using the sim's latest engine data.

## Ask the AI representative
Open **http://localhost:8000/#/ask** (or `POST /ask`). The representative (NVIDIA NIM, tool-calling) picks the relevant
engine tools, runs them and explains the result; each answer lists the tool calls and their computed outputs.

```bash
# .env — pick a provider; comma-separated keys are pooled and rotated (429/5xx cool a key down, 401/403 disable it)
LLM_PROVIDER=groq            # nim | groq | xai
GROQ_API_KEYS=gsk_...,gsk_...
# LLM_MODEL=llama-3.3-70b-versatile   (optional override)

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
