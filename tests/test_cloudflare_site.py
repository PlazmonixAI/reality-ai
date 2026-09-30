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


def test_test_area_needs_a_password():
    mw = (ROOT / "cloudflare" / "functions" / "test" / "_middleware.js").read_text()
    assert "TEST_USERNAME" in mw and "TEST_PASSWORD" in mw and "status: 401" in mw and "status: 503" in mw
