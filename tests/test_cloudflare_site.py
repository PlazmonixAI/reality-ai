"""The pre-launch Cloudflare site builds: only the main page is live, everything else says Coming soon, /test is private."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cloudflare" / "public"


def test_build_prelaunch_site():
    r = subprocess.run([sys.executable, "scripts/build_cloudflare_site.py"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    index = (OUT / "index.html").read_text()
    assert 'href="/login"' not in index and 'href="/signup"' not in index and "/app/" not in index
    assert 'id="waitlist"' in index and "/static/waitlist.js" in index and "site.js" not in index
    soon = (OUT / "404.html").read_text()
    assert "Coming soon" in soon and "noindex" in soon
    assert "noindex" in (OUT / "test" / "index.html").read_text()
    assert "Disallow: /test" in (OUT / "robots.txt").read_text()
    assert not (OUT / "login.html").exists() and not (OUT / "legal").exists()
    cfg = json.loads((ROOT / "cloudflare" / "site.config.json").read_text())
    assert ('"' + cfg["waitlist_endpoint"] + '"') in (OUT / "static" / "waitlist.js").read_text()
    assert "{{" not in index + soon


def test_seo_files():
    """Search engines get a sitemap, robots.txt pointing at it, and a main page with canonical, social and JSON-LD tags."""
    import re
    subprocess.run([sys.executable, "scripts/build_cloudflare_site.py"], cwd=ROOT, check=True, capture_output=True)
    site = "https://" + json.loads((ROOT / "cloudflare" / "site.config.json").read_text())["domain"]
    robots = (OUT / "robots.txt").read_text()
    assert f"Sitemap: {site}/sitemap.xml" in robots and "Disallow: /api/" in robots
    import xml.etree.ElementTree as ET
    locs = [e.text for e in ET.parse(OUT / "sitemap.xml").iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert locs == [f"{site}/"]
    index = (OUT / "index.html").read_text()
    assert index.count("<title>") == 1 and index.count('name="description"') == 1
    assert f'<link rel="canonical" href="{site}/">' in index and f'content="{site}/static/brand/og-image.jpg"' in index
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', index, re.S).group(1))
    assert {g["@type"] for g in ld["@graph"]} >= {"Organization", "WebSite", "SoftwareApplication"}
    assert not re.findall(r'<img src="/static/img/[^"]+" alt=""', index)  # every content picture is described
    for f in ("og-image.jpg", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        assert (OUT / "static" / "brand" / f).exists()
    assert "\u2014" not in index and "—" not in index


def test_test_area_needs_a_password():
    mw = (ROOT / "cloudflare" / "functions" / "test" / "_middleware.js").read_text()
    assert "TEST_USERNAME" in mw and "TEST_PASSWORD" in mw and "status: 401" in mw and "status: 503" in mw
