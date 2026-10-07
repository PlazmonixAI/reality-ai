"""Build the static pre-launch site for Cloudflare Pages into cloudflare/public.

Only the main page is live. Every other path shows "Coming soon" (Cloudflare Pages serves 404.html for unknown
paths). /test is a private area behind a username and password (see cloudflare/functions/test/_middleware.js).
Settings come from cloudflare/site.config.json:
  domain             your domain, e.g. realityasm.com (used for canonical links)
  contact_email      shown on the page
  waitlist_endpoint  empty = the waitlist form is a dummy that only says thank you; set it to
                     https://<render app>/api/waitlist to store emails in the Render backend
  beta_app_url       the Render app, e.g. https://app.realityasm.com: the /test team desk links to it and checks its /health
  beta_opens         when the public beta opens (ISO time, IST), e.g. 2026-10-20T00:00:00+05:30
  launch             when the main app launches, e.g. 2026-11-04T00:00:00+05:30
                     From those moments the page switches by itself (waitlist.js): "Join the beta", then "Get started",
                     with every button pointing at beta_app_url/signup. No rebuild is needed on the day.

Run:  python scripts/build_cloudflare_site.py
"""
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "frontend" / "site"
CF = ROOT / "cloudflare"
OUT = CF / "public"


def nice_day(iso: str) -> str:  # "2026-10-20T00:00:00+05:30" -> "20 October 2026"
    if not iso:
        return ""
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {d.strftime('%B')} {d.year}"


def when(day: str) -> str:
    return f"on {day}" if day else "soon"


def main() -> None:
    cfg = json.loads((CF / "site.config.json").read_text())
    email = cfg.get("contact_email") or "contact@plazmonixai.in"
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "static").mkdir(parents=True)
    for d in ("brand", "fonts", "img"):
        shutil.copytree(SITE / "static" / d, OUT / "static" / d)
    shutil.copy(SITE / "static" / "site.css", OUT / "static" / "site.css")
    shutil.copy(CF / "src" / "prelaunch.css", OUT / "static" / "prelaunch.css")
    for name in ("apple-touch-icon.png", "icon-192.png", "icon-512.png", "og-image.jpg"):
        shutil.copy(CF / "src" / name, OUT / "static" / "brand" / name)
    beta_opens, launch = cfg.get("beta_opens", ""), cfg.get("launch", "")
    beta_day = nice_day(beta_opens)
    js = (CF / "src" / "waitlist.js").read_text().replace("__WAITLIST_ENDPOINT__", cfg.get("waitlist_endpoint", ""))
    js = (js.replace("__BETA_OPENS__", beta_opens).replace("__LAUNCH__", launch)
          .replace("__APP_URL__", cfg.get("beta_app_url", "").rstrip("/")).replace("__BETA_DAY__", beta_day))
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
         f'<p class="hero-note" data-phase="note">The public beta opens {when(beta_day)}. Leave your email and we\'ll let you know first.</p>'),
        ('<h2>Join the beta</h2>\n        <p class="sub">It\'s free while we test. Tell us what breaks, what\'s confusing and what you want next.</p>',
         f'<h2 data-phase="title">Join the waitlist</h2>\n        <p class="sub" data-phase="sub">Kindly leave your email. We\'ll write once, {when(beta_day)}, when the public beta opens.</p>'),
        ('<span class="eyebrow">Public beta</span>', f'<span class="eyebrow" data-phase="eyebrow">{"Beta opens " + beta_day if beta_day else "Public beta"}</span>'),
        ('<a class="btn btn-primary" href="/signup" data-signed-out>Create your account</a>\n          <a class="btn btn-primary" href="/app/" data-signed-in hidden>Open the app</a>\n          <a class="btn btn-ghost" href="/about">About the project</a>',
         form),
        ('<script type="module" src="/static/site.js"></script>', '<script type="module" src="/static/waitlist.js"></script>'),
        ('<link rel="stylesheet" href="/static/site.css">', '<link rel="stylesheet" href="/static/site.css">\n  <link rel="stylesheet" href="/static/prelaunch.css">'),
        ('<a class="door" href="/app/">', '<a class="door" href="#waitlist">'),
        ('<a class="door teach" href="/teach">', '<a class="door teach" href="#waitlist">'),
        ("{{CONTACT_EMAIL}}", email),
    ]
    for old, new in swaps:
        if old not in html:
            raise SystemExit(f"landing page changed; update build_cloudflare_site.py (missing: {old[:60]!r})")
        html = html.replace(old, new)
    # gallery pictures get their caption as alt text, so image search can read them
    html = re.sub(r'<img src="([^"]+)" alt="" loading="lazy"><figcaption>([^<]+)</figcaption>',
                  r'<img src="\1" alt="\2, a Reality ASM simulation" loading="lazy"><figcaption>\2</figcaption>', html)
    domain = cfg.get("domain")
    if domain:
        html = seo_head(html, f"https://{domain}", email)
    (OUT / "index.html").write_text(html)

    # --- everything else: coming soon, and the private test area
    for name in ("404.html",):
        (OUT / name).write_text((CF / "src" / "coming-soon.html").read_text().replace("{{CONTACT_EMAIL}}", email))
    (OUT / "test").mkdir()
    test = (CF / "src" / "test.html").read_text().replace("{{BETA_APP_URL}}", cfg.get("beta_app_url", "").rstrip("/")).replace("{{CONTACT_EMAIL}}", email)
    drop = "data-noapp" if cfg.get("beta_app_url") else "data-app"  # show the link, or the note that it's coming
    test = re.sub(rf'\s*<p[^>]*{drop}>.*?</p>', "", test, flags=re.S)
    (OUT / "test" / "index.html").write_text(test)
    shutil.copy(CF / "src" / "hub.js", OUT / "test" / "hub.js")
    (OUT / "test" / "config.json").write_text(json.dumps({"beta_app_url": cfg.get("beta_app_url", "").rstrip("/")}) + "\n")
    shutil.copy(CF / "src" / "_headers", OUT / "_headers")
    robots = "User-agent: *\nAllow: /\nDisallow: /test\nDisallow: /api/\n"
    if domain:
        robots += f"\nSitemap: https://{domain}/sitemap.xml\n"
        (OUT / "sitemap.xml").write_text(sitemap(f"https://{domain}"))
    (OUT / "robots.txt").write_text(robots)
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": "Reality ASM", "short_name": "Reality ASM", "start_url": "/", "display": "browser",
        "background_color": "#0B1526", "theme_color": "#0B1526",
        "icons": [{"src": "/static/brand/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/brand/icon-512.png", "sizes": "512x512", "type": "image/png"}]}, indent=2) + "\n")
    print(f"built {OUT.relative_to(ROOT)} ({sum(1 for _ in OUT.rglob('*') if _.is_file())} files)")


TITLE = "Reality ASM · 3D Universe Map with every galaxy and constellation"
DESCRIPTION = ("Fly through the universe in one 3D map: planets on any date, 12,000 stars, all 88 constellations, 3,800 "
               "planetary systems, the Milky Way and 11,000 named galaxies to the edge of the observable universe. Plus physics, "
               "chemistry and maths simulations and ASM Teach for schools. Built in India by Plazmonix AI.")
KEYWORDS = ("universe map, 3D universe map, interactive universe map, galaxy map, map of the galaxies, constellation map, 3D star map, "
            "solar system 3D, observable universe, Andromeda galaxy, Milky Way map, exoplanet map, physics simulations, "
            "chemistry virtual lab, maths graphing sandbox, rocket simulator, PSLV, ASM Teach, Reality ASM, Plazmonix AI")


def seo_head(html: str, site: str, email: str) -> str:
    """Title, description, canonical, social cards and structured data (JSON-LD) for the main page."""
    html = re.sub(r"\s*<title>.*?</title>", "", html, count=1, flags=re.S)
    html = re.sub(r'\s*<meta (name="description"|property="og:[a-z:_]+") content="[^"]*">', "", html)
    org = {"@type": "Organization", "@id": f"{site}/#org", "name": "Plazmonix AI", "url": "https://plazmonixai.com",
           "email": email, "logo": f"{site}/static/brand/icon-512.png",
           "address": {"@type": "PostalAddress", "addressLocality": "Rourkela", "addressRegion": "Odisha", "addressCountry": "IN"}}
    data = {"@context": "https://schema.org", "@graph": [
        org,
        {"@type": "WebSite", "@id": f"{site}/#website", "url": f"{site}/", "name": "Reality ASM", "inLanguage": "en-IN",
         "publisher": {"@id": f"{site}/#org"}},
        {"@type": "WebPage", "@id": f"{site}/#page", "url": f"{site}/", "name": TITLE, "description": DESCRIPTION,
         "isPartOf": {"@id": f"{site}/#website"}, "primaryImageOfPage": f"{site}/static/brand/og-image.jpg",
         "about": [{"@type": "Thing", "name": n} for n in ("Universe", "Galaxy", "Constellation", "Solar System", "Milky Way", "Exoplanet")]},
        {"@type": "SoftwareApplication", "name": "Reality ASM Universe Map", "url": f"{site}/#universe", "applicationCategory": "EducationalApplication",
         "applicationSubCategory": "Astronomy", "operatingSystem": "Any modern web browser", "image": f"{site}/static/img/uv_galaxies_named.jpg",
         "publisher": {"@id": f"{site}/#org"},
         "description": "One continuous 3D map from the Solar System to the edge of the observable universe: planets and moons on any "
                        "date, 12,000 real stars, all 88 constellations joined to their stars in 3D (with Hindi names), 3,800 exoplanet "
                        "systems, the Milky Way with 6,500 open clusters, 11,000 galaxies with their common names, galaxy clusters, "
                        "superclusters, great walls, voids and the most distant objects known, placed by redshift.",
         "featureList": ["Five scales in one map: Solar System, stars, Milky Way, galaxies, observable universe",
                         "88 constellations with lines, names, Hindi names and boundaries, each switchable in Settings",
                         "11,000 galaxies, the famous ones named: Andromeda, Triangulum, Whirlpool, Sombrero, Pinwheel, Centaurus A",
                         "3,800 planetary systems from the Open Exoplanet Catalogue", "Distances from redshift with Planck 2018 cosmology"]},
        {"@type": "SoftwareApplication", "name": "Reality ASM", "url": f"{site}/", "applicationCategory": "EducationalApplication",
         "operatingSystem": "Any modern web browser", "image": f"{site}/static/brand/og-image.jpg", "publisher": {"@id": f"{site}/#org"},
         "description": "A simulation engine for physics, chemistry and mathematics. Every number is computed by tested engine tools "
                        "with SI units and stated assumptions; an AI analyst explains the results.",
         "featureList": ["The Universe Map: Solar System, stars, constellations, Milky Way and 11,000 named galaxies in one 3D map",
                         "83 interactive simulations split into physics, chemistry and mathematics",
                         "Virtual chemistry lab with 72 chemicals, lift-and-pour glassware and gas cylinders",
                         "Maths sandbox: functions, equations, inequalities, polar and parametric curves with roots and turning points",
                         "Space Program with 13 real launch vehicles including PSLV, LVM3 and Falcon 9",
                         "AI analyst that explains every result"]},
        {"@type": "SoftwareApplication", "name": "ASM Teach", "url": f"{site}/#teach", "applicationCategory": "EducationalApplication",
         "operatingSystem": "Any modern web browser", "publisher": {"@id": f"{site}/#org"},
         "audience": {"@type": "EducationalAudience", "educationalRole": "teacher"},
         "description": "A separate classroom app for schools: every senior school derivation and practical in physics, chemistry and maths "
                        "as a live experiment, plus the Universe Map, the chemistry and maths sandboxes and every Reality ASM simulation. "
                        "Write an equation and it is built from the mathematics; wrong equations are flagged."},
    ]}
    tags = f"""<title>{TITLE}</title>
  <meta name="description" content="{DESCRIPTION}">
  <meta name="keywords" content="{KEYWORDS}">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
  <link rel="canonical" href="{site}/">
  <meta name="theme-color" content="#0B1526">
  <link rel="apple-touch-icon" href="/static/brand/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Reality ASM">
  <meta property="og:locale" content="en_IN">
  <meta property="og:url" content="{site}/">
  <meta property="og:title" content="{TITLE}">
  <meta property="og:description" content="{DESCRIPTION}">
  <meta property="og:image" content="{site}/static/brand/og-image.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="The Reality ASM Universe Map: named galaxies, clusters and superclusters around the Milky Way">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{TITLE}">
  <meta name="twitter:description" content="{DESCRIPTION}">
  <meta name="twitter:image" content="{site}/static/brand/og-image.jpg">
  <script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>
"""
    return html.replace("</head>", "  " + tags + "</head>", 1)


def sitemap(site: str) -> str:
    """The one live page, with its pictures, dated by the last commit that changed it."""
    try:
        day = subprocess.run(["git", "log", "-1", "--format=%cs", "--", "frontend/site/index.html", "cloudflare/src"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        day = ""
    images = "".join(f"\n    <image:image><image:loc>{site}/static/img/{p.name}</image:loc></image:image>"
                     for p in sorted((OUT / "static" / "img").glob("*.jpg")) if f"/static/img/{p.name}" in (OUT / "index.html").read_text())
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>{site}/</loc>
    <lastmod>{day or date.today().isoformat()}</lastmod>{images}
  </url>
</urlset>
"""


if __name__ == "__main__":
    main()
