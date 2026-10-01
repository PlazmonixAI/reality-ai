"""Pre-launch waitlist (called from the Cloudflare site) and the private-testing gate."""
import base64

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.platform import db, waitlist

pytestmark = pytest.mark.real_auth


def test_waitlist_from_the_cloudflare_site(monkeypatch):
    monkeypatch.setattr(settings, "waitlist_origins", "https://realityasm.example")
    waitlist.limit.reset()
    c = TestClient(app)
    pre = c.options("/api/waitlist", headers={"Origin": "https://realityasm.example", "Access-Control-Request-Method": "POST"})
    assert pre.status_code == 204 and pre.headers["access-control-allow-origin"] == "https://realityasm.example"
    r = c.post("/api/waitlist", content="email=Friend%40Example.com&source=%2F",
               headers={"Origin": "https://realityasm.example", "Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 201 and r.headers["access-control-allow-origin"] == "https://realityasm.example"
    again = c.post("/api/waitlist", json={"email": "friend@example.com"}, headers={"Origin": "https://realityasm.example"})
    assert again.status_code == 201  # no duplicate, no error
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM waitlist WHERE email = 'friend@example.com'").fetchone()[0] == 1
    bad = c.post("/api/waitlist", json={"email": "nope"}, headers={"Origin": "https://realityasm.example"})
    assert bad.status_code == 422
    evil = c.post("/api/waitlist", json={"email": "a@b.com"}, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403 and "access-control-allow-origin" not in evil.headers


def test_private_testing_gate(monkeypatch):
    monkeypatch.setattr(settings, "test_gate_username", "team")
    monkeypatch.setattr(settings, "test_gate_password", "launch-2026")
    c = TestClient(app)
    assert c.get("/").status_code == 401
    assert c.get("/health").status_code == 200  # Render's health check still works
    good = "Basic " + base64.b64encode(b"team:launch-2026").decode()
    bad = "Basic " + base64.b64encode(b"team:wrong").decode()
    assert c.get("/", headers={"Authorization": bad}).status_code == 401
    assert c.get("/", headers={"Authorization": good}).status_code == 200
