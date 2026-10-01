# Reality ASM on Cloudflare (pre-launch site)

What visitors get now:
- **`/`**: the main page. Every "Join" button leads to the waitlist form ("Kindly leave your email").
- **Any other address** (`/login`, `/app`, `/terms`, ...): a "Coming soon" page with the same email form.
- **`/test`**: a private page for the team, behind a username and password.

The site is plain files in `cloudflare/public`, rebuilt from the real landing page with
`python scripts/build_cloudflare_site.py`. Commit the rebuilt files before deploying.

## Put it on Cloudflare Workers (the way Plazmonix AI deploys)
`wrangler.jsonc` at the repository root and `cloudflare/worker.js` make the site a Worker with static assets. The Worker
reuses the code in `functions/` for the waitlist and the /test password; every other page is a plain file.
1. Workers & Pages > Create > Import a repository > `PlazmonixAI/reality-ai`.
2. Project name: `plazmonixai-reality-asm` (the same as `name` in `wrangler.jsonc`). Build command: empty.
   Deploy command: `npx wrangler deploy`. Leave the root/path as the repository root.
3. Deploy. Wrangler creates the `WAITLIST` KV namespace on the first deploy.
4. Worker > Settings > Variables and Secrets > add `TEST_USERNAME` and `TEST_PASSWORD` as **Secret** (secrets survive
   redeploys). Until both exist, /test stays closed.
5. Worker > Settings > Domains & Routes > add your domain.

## Or put it on Cloudflare Pages
1. Cloudflare dashboard > **Workers & Pages** > **Create** > **Pages** > **Connect to Git**, and pick this repository.
2. Build settings:
   - Framework preset: **None**
   - Build command: *(leave empty)*
   - Build output directory: **`public`**
   - Root directory (advanced): **`cloudflare`** (so the `functions/` folder that guards `/test` is picked up)
3. **Settings > Environment variables** (Production), add as **encrypted** values:
   - `TEST_USERNAME`: the username for /test
   - `TEST_PASSWORD`: a long password (share it only with testers)
   Redeploy after adding them. Until both exist, /test stays closed.
4. **Waitlist storage**: Workers & Pages > **KV** > Create a namespace (e.g. `reality-asm-waitlist`). Then in the
   Pages project: **Settings > Bindings > Add > KV namespace**, variable name **`WAITLIST`**, pick that namespace,
   and redeploy. Emails are then saved by `functions/api/waitlist.js`; download them at **`/test/waitlist.csv`**
   (behind the /test password). Without the binding the form shows "That didn't go through".
5. **Custom domains** > add your domain (and `www` if you like). Cloudflare sets up DNS and HTTPS.

## Settings (`cloudflare/site.config.json`)
| Key | What it does |
|---|---|
| `domain` | Your domain, e.g. `realityasm.com` (adds the canonical link) |
| `contact_email` | Shown on the pages |
| `waitlist_endpoint` | `/api/waitlist` (default): emails go to Cloudflare KV (step 4). Later you can point it at `https://<your Render app>/api/waitlist` so they land on the app's Beta admin page. Empty: a placeholder that **stores nothing**. |
| `beta_app_url` | The Render app's address, shown on /test as "Open the beta app" |

After changing it, run `python scripts/build_cloudflare_site.py`, commit, and push; Cloudflare redeploys by itself.
