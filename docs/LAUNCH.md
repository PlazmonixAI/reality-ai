# Beta and launch plan

| Date (IST) | What happens |
|---|---|
| **20 Oct 2026, 00:00** | **Public beta opens.** realityasm.com changes "Join the waitlist" to "Join the beta" (links to app.realityasm.com/signup); the app's test gate opens by itself (`TEST_GATE_UNTIL`). |
| **4 Nov 2026, 00:00** | **Main app launch.** The site and the app's landing page change "beta" wording to "Get started". |

Both switches are in code and need no deploy on the day:
- Website: `cloudflare/site.config.json` (`beta_opens`, `launch`) read by `cloudflare/src/waitlist.js`. Change a date there,
  run `python scripts/build_cloudflare_site.py`, commit and push.
- App: `TEST_GATE_UNTIL` (default `2026-10-20T00:00:00+05:30`) in `app/config.py`; the launch wording in `frontend/site/static/site.js`.

## Before 20 October (beta): owner tasks on Render and Cloudflare
These cannot be done from the code. Without the first one, beta testers lose their accounts.
- [ ] **Keep the data.** Render free plan has no disk: every restart wipes the SQLite database (accounts, history,
      companies). Move the service to the **Starter** plan, add a **Disk** (1 GB, mount path `/var/data`) and set
      `DATABASE_PATH=/var/data/reality.db`. Starter also stops the 15-minute sleep.
- [ ] Render environment: `OWNER_EMAIL`, `OWNER_PASSWORD`, `PUBLIC_BASE_URL=https://app.realityasm.com`,
      `SECRET_KEY` (long random), the AI keys (`LLM_PROVIDER` and `NIM_API_KEYS` / `GROQ_API_KEYS` / `XAI_API_KEYS`),
      `WAITLIST_ORIGINS=https://realityasm.com`. Leave `BETA_INVITE_CODES` empty for an open beta.
- [ ] Google sign-in: add `https://app.realityasm.com/api/auth/google/callback` as an authorised redirect URI.
- [ ] Uptime: cron-job.org on `https://reality-ai.onrender.com/health` every 5 minutes (the GitHub keep-alive also runs).
- [ ] Waitlist: download `/test/waitlist.csv` from realityasm.com on 19 October and send the beta email on the 20th
      (draft below).
- [ ] Try it as a new user on a phone and a laptop: sign up, open the Universe Map, a lab, the Space Program, Ask AI,
      ASM Teach as a teacher. Send feedback from the menu to check it reaches the Beta admin page.

## During the beta (20 Oct to 3 Nov)
- Read the Beta admin page daily (sign-ups, feedback, usage). Fix what testers report; small, tested changes only.
- Freeze new features from **1 November**; only fixes until launch.

## Before 4 November (launch)
- [ ] Decide pricing for launch (ASM Teach for schools: see `docs/PRICING.md`) and whether sign-up stays free.
- [ ] Back up the database (download `/var/data/reality.db` from the Render shell) the night before.
- [ ] Final bug sweep: every simulation and page in a browser, `pytest` green.
- [ ] Launch posts ready (LinkedIn, Instagram, the school contacts).

## Beta email draft (to the waitlist, 20 October)
Subject: The Reality ASM beta is open

Hello,

You asked us to tell you when Reality ASM opens. It's open today.

Make a free account at https://app.realityasm.com/signup and try the Universe Map, the chemistry lab, the maths sandbox
and the space program. Every number you see is calculated by our engine.

It's a beta, so some things will break. Use "Send feedback" in the menu and tell us what you find. The full launch is on
4 November.

Thank you for waiting with us.
Subham Agarwal
Plazmonix AI
