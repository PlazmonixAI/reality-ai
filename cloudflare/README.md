# Reality ASM on Cloudflare (pre-launch site)

What visitors get now:
- **`/`**: the main page. Every "Join" button leads to the waitlist form ("Kindly leave your email").
- **Any other address** (`/login`, `/app`, `/terms`, ...): a "Coming soon" page with the same email form.
- **`/test`**: a private page for the team, behind a username and password.

The site is plain files in `cloudflare/public`, rebuilt from the real landing page with
`python scripts/build_cloudflare_site.py`. Commit the rebuilt files before deploying.

## Put it on Cloudflare Pages
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
4. **Custom domains** > add your domain (and `www` if you like). Cloudflare sets up DNS and HTTPS.

## Settings (`cloudflare/site.config.json`)
| Key | What it does |
|---|---|
| `domain` | Your domain, e.g. `realityasm.com` (adds the canonical link) |
| `contact_email` | Shown on the pages |
| `waitlist_endpoint` | Empty: the email form is a placeholder that only says thank you and **stores nothing**. Set it to `https://<your Render app>/api/waitlist` to keep the emails (they appear on the app's Beta admin page). |
| `beta_app_url` | The Render app's address, shown on /test as "Open the beta app" |

After changing it, run `python scripts/build_cloudflare_site.py`, commit, and push; Cloudflare redeploys by itself.
