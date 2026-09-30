"""Build the static pre-launch site for Cloudflare Pages into cloudflare/public.

Only the main page is live. Every other path shows "Coming soon" (Cloudflare Pages serves 404.html for unknown
paths). /test is a private area behind a username and password (see cloudflare/functions/test/_middleware.js).
Settings come from cloudflare/site.config.json:
  domain             your domain, e.g. realityasm.com (used for canonical links)
  contact_email      shown on the page
  waitlist_endpoint  empty = the waitlist form is a dummy that only says thank you; set it to
                     https://<render app>/api/waitlist to store emails in the Render backend
  beta_app_url       where the /test page sends testers (the Render app), e.g. https://app.realityasm.com

Run:  python scripts/build_cloudflare_site.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "frontend" / "site"
CF = ROOT / "cloudflare"
OUT = CF / "public"


def main() -> None:
    cfg = json.loads((CF / "site.config.json").read_text())
    email = cfg.get("contact_email") or "support@plazmonix.ai"
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "static").mkdir(parents=True)
    for d in ("brand", "fonts", "img"):
        shutil.copytree(SITE / "static" / d, OUT / "static" / d)
    shutil.copy(SITE / "static" / "site.css", OUT / "static" / "site.css")
    shutil.copy(CF / "src" / "prelaunch.css", OUT / "static" / "prelaunch.css")
    js = (CF / "src" / "waitlist.js").read_text().replace("__WAITLIST_ENDPOINT__", cfg.get("waitlist_endpoint", ""))
    (OUT / "static" / "waitlist.js").write_text(js)

    # --- main page: the real landing page, with every sign-in / sign-up link turned into the waitlist
    html = (SITE / "index.html").read_text()
    form = (CF / "src" / "waitlist-form.html").read_text()
    swaps = [
        ('<a class="btn btn-ghost" href="/login">Sign in</a>\n        <a class="btn btn-primary" href="/signup">Join the beta</a>',
         '<a class="btn btn-primary" href="#waitlist">Join the waitlist</a>'),
        ('<a class="btn btn-primary" href="/signup" data-signed-out>Create a free account</a>\n            <a class="btn btn-primary" href="/app/" data-signed-in hidden>Open the app</a>',
         '<a class="btn btn-primary" href="#waitlist">Join the waitlist</a>'),
        ('<p class="hero-note">Free during the beta. Works in any modern browser, no install.</p>',
         '<p class="hero-note">The public beta opens soon. Leave your email and we\'ll let you know first.</p>'),
        ('<h2>Join the beta</h2>\n        <p class="sub">It\'s free while we test. Tell us what breaks, what\'s confusing and what you want next.</p>',
         '<h2>Join the waitlist</h2>\n        <p class="sub">Kindly leave your email. We\'ll write once, when the public beta opens.</p>'),
        ('<a class="btn btn-primary" href="/signup" data-signed-out>Create your account</a>\n          <a class="btn btn-primary" href="/app/" data-signed-in hidden>Open the app</a>\n          <a class="btn btn-ghost" href="/about">About the project</a>',
         form),
        ('<script type="module" src="/static/site.js"></script>', '<script type="module" src="/static/waitlist.js"></script>'),
        ('<link rel="stylesheet" href="/static/site.css">', '<link rel="stylesheet" href="/static/site.css">\n  <link rel="stylesheet" href="/static/prelaunch.css">'),
        ("{{CONTACT_EMAIL}}", email),
    ]
    for old, new in swaps:
        if old not in html:
            raise SystemExit(f"landing page changed; update build_cloudflare_site.py (missing: {old[:60]!r})")
        html = html.replace(old, new)
    if cfg.get("domain"):
        html = html.replace("<title>", f'<link rel="canonical" href="https://{cfg["domain"]}/">\n  <title>', 1)
    (OUT / "index.html").write_text(html)

    # --- everything else: coming soon, and the private test area
    for name in ("404.html",):
        (OUT / name).write_text((CF / "src" / "coming-soon.html").read_text().replace("{{CONTACT_EMAIL}}", email))
    (OUT / "test").mkdir()
    import re
    test = (CF / "src" / "test.html").read_text().replace("{{BETA_APP_URL}}", cfg.get("beta_app_url", "")).replace("{{CONTACT_EMAIL}}", email)
    drop = "data-noapp" if cfg.get("beta_app_url") else "data-app"  # show the link, or the note that it's coming
    test = re.sub(rf'\s*<p[^>]*{drop}>.*?</p>', "", test, flags=re.S)
    (OUT / "test" / "index.html").write_text(test)
    shutil.copy(CF / "src" / "_headers", OUT / "_headers")
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /test\n")
    print(f"built {OUT.relative_to(ROOT)} ({sum(1 for _ in OUT.rglob('*') if _.is_file())} files)")


if __name__ == "__main__":
    main()
