# Reality AI

Reality AI is Plazmonix AI's research-simulation engine for Physics, Chemistry, Mathematics and Biology (PCMB).
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

Open http://localhost:8000/docs for the API.

## Docs
- `CLAUDE.md` – rules and brief for Claude Code
- `docs/ROADMAP.md` – session-by-session build plan
- `docs/ARCHITECTURE.md` – how the system fits together
- `docs/PROGRESS.md` – what is done so far
