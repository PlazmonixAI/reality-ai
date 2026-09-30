"""Accounts, sessions, protected engine and app files, history isolation, flight-state signatures."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.platform import auth
from tests.helpers import new_client

pytestmark = pytest.mark.real_auth


def fresh():
    auth.signup_limit.reset()
    auth.login_ip_limit.reset()
    auth.login_email_limit.reset()
    return TestClient(app)


def test_engine_and_app_need_a_session():
    c = fresh()
    assert c.post("/simulate", json={"domain": "mathematics", "name": "differentiate", "args": {"expression": "x**2"}}).status_code == 401
    assert c.get("/tools").status_code == 401
    assert c.post("/ask", json={"question": "hi"}).status_code == 401
    r = c.get("/app/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("/login")
    assert c.get("/app/js/main.js").status_code == 401
    assert c.get("/app/js/sims/spaceflight.js").status_code == 401
    # public pages stay public
    for page in ("/", "/login", "/signup", "/terms", "/privacy", "/cookies", "/acceptable-use"):
        assert c.get(page).status_code == 200, page
    assert c.get("/health").json()["status"] == "ok"


def test_api_docs_are_off():
    c = fresh()
    assert c.get("/openapi.json").status_code == 404
    assert c.get("/docs").status_code == 404


def test_signup_login_logout_cycle():
    c = fresh()
    r = c.post("/api/auth/signup", json={"name": "  Grace  Hopper ", "email": "Grace@Example.com", "password": "compiler-1952",
                                         "accept_terms": True})
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["email"] == "grace@example.com" and user["name"] == "Grace Hopper"
    assert "password_hash" not in user
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert c.get("/api/auth/me").json()["user"]["id"] == user["id"]
    assert c.post("/simulate", json={"domain": "mathematics", "name": "differentiate",
                                     "args": {"expression": "x**3", "variable": "x"}}).json()["result"] == "3*x**2"
    assert c.get("/app/js/main.js").status_code == 200
    assert c.post("/api/auth/logout").status_code == 200
    assert c.get("/api/auth/me").status_code == 401
    # wrong password, then right one
    assert c.post("/api/auth/login", json={"email": "grace@example.com", "password": "nope-nope-nope"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "GRACE@example.com", "password": "compiler-1952"}).status_code == 200
    assert c.get("/api/auth/me").status_code == 200


def test_signup_validation():
    c = fresh()
    base = {"name": "A", "email": "a@example.com", "password": "long-enough-pw", "accept_terms": True}
    assert c.post("/api/auth/signup", json={**base, "accept_terms": False}).status_code == 422
    assert c.post("/api/auth/signup", json={**base, "email": "not-an-email"}).status_code == 422
    assert c.post("/api/auth/signup", json={**base, "password": "short"}).status_code == 422
    assert c.post("/api/auth/signup", json={**base, "password": "aaaaaaaaaaaa"}).status_code == 422
    assert c.post("/api/auth/signup", json=base).status_code == 201
    assert fresh().post("/api/auth/signup", json=base).status_code == 409  # duplicate email


def test_unknown_email_and_wrong_password_look_the_same():
    c = fresh()
    a = c.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever-123"})
    assert a.status_code == 401 and a.json()["detail"] == "Email or password is incorrect."


def test_login_rate_limit():
    c = fresh()
    codes = [c.post("/api/auth/login", json={"email": "ghost2@example.com", "password": "x" * 10}).status_code for _ in range(8)]
    assert codes[-1] == 429


def test_cross_site_post_is_blocked():
    c, _ = new_client()
    r = c.post("/api/history", json={"kind": "sim", "title": "x"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_security_headers():
    r = fresh().get("/")
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_password_change_signs_out_other_sessions():
    a, user = new_client()
    b = TestClient(app)
    auth.login_ip_limit.reset()
    assert b.post("/api/auth/login", json={"email": user["email"], "password": "orbit-2026-ok"}).status_code == 200
    assert a.post("/api/auth/password", json={"current_password": "wrong", "new_password": "new-orbit-2027"}).status_code == 403
    assert a.post("/api/auth/password", json={"current_password": "orbit-2026-ok", "new_password": "new-orbit-2027"}).status_code == 200
    assert a.get("/api/auth/me").status_code == 200
    assert b.get("/api/auth/me").status_code == 401


def test_history_is_private_and_editable():
    a, _ = new_client("A")
    b, _ = new_client("B")
    r = a.post("/api/history", json={"kind": "flight", "sim_id": "spaceflight", "title": "First orbit",
                                     "payload": {"parts": [{"part": "capsule"}]}, "summary": {"status": "orbit"}})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert a.get(f"/api/history/{rid}").json()["payload"]["parts"][0]["part"] == "capsule"
    assert b.get(f"/api/history/{rid}").status_code == 404
    assert b.delete(f"/api/history/{rid}").status_code == 404
    assert b.get("/api/history").json()["items"] == []
    assert a.patch(f"/api/history/{rid}", json={"starred": True, "title": "Orbit #1"}).json()["title"] == "Orbit #1"
    listing = a.get("/api/history?kind=flight").json()
    assert listing["items"][0]["starred"] and listing["counts"] == {"flight": 1}
    assert a.post("/api/history", json={"kind": "bogus", "title": "x"}).status_code == 422
    assert a.post("/api/history", json={"kind": "sim", "title": "big", "payload": {"x": "a" * 700_000}}).status_code == 413
    assert a.delete(f"/api/history/{rid}").status_code == 200
    assert a.get(f"/api/history/{rid}").status_code == 404


def test_export_and_delete_account():
    c, user = new_client()
    c.post("/api/history", json={"kind": "sim", "title": "Pendulum", "payload": {"a": 1}})
    data = c.get("/api/account/export").json()
    assert data["user"]["email"] == user["email"] and data["history"][0]["payload"] == {"a": 1}
    assert c.request("DELETE", "/api/account", json={"confirm": "wrong"}).status_code == 403
    assert c.request("DELETE", "/api/account", json={"confirm": "orbit-2026-ok"}).status_code == 200
    assert c.get("/api/auth/me").status_code == 401
    auth.login_ip_limit.reset()
    assert fresh().post("/api/auth/login", json={"email": user["email"], "password": "orbit-2026-ok"}).status_code == 401


def test_invite_codes(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "beta_invite_codes", "ORBIT-42")
    c = fresh()
    body = {"name": "Inv", "email": "inv@example.com", "password": "invite-pass-1", "accept_terms": True}
    assert c.post("/api/auth/signup", json=body).status_code == 403
    assert c.post("/api/auth/signup", json={**body, "invite_code": "ORBIT-42"}).status_code == 201
    assert c.get("/api/auth/config").json()["invite_required"] is True


def test_flight_states_are_signed_and_tampering_is_detected():
    c, _ = new_client()
    parts = [{"part": "engine_booster"}, {"part": "tank_m"}, {"part": "probe"}]
    r = c.post("/simulate", json={"domain": "physics", "name": "rocket_launch_state", "args": {"parts": parts}}).json()
    assert r["verified"] and r["signature"]
    state, sig = r["result"], r["signature"]
    step = c.post("/simulate", json={"domain": "physics", "name": "rocket_flight", "signature": sig,
                                     "args": {"state": state, "parts": parts, "throttle": 1.0, "dt": 1.0}}).json()
    assert step["verified"] and step["signature"]
    forged = {**step["result"]["state"], "y": step["result"]["state"]["y"] + 500_000}
    bad = c.post("/simulate", json={"domain": "physics", "name": "rocket_flight", "signature": step["signature"],
                                    "args": {"state": forged, "parts": parts, "dt": 1.0}}).json()
    assert bad["verified"] is False and "signature" not in bad
    # a signature can't be moved to a different rocket
    other = c.post("/simulate", json={"domain": "physics", "name": "rocket_flight", "signature": step["signature"],
                                      "args": {"state": step["result"]["state"], "parts": parts + [{"part": "nose"}], "dt": 1.0}})
    assert other.json()["verified"] is False


def test_signature_survives_a_browser_round_trip():
    """Browsers print 6378137.0 as 6378137; the signature must not care."""
    import json
    from app.platform.security import check, sign
    state = {"y": 6378137.0, "stage": 0, "props": [411000.0, 1.5], "landed": True}
    sig = sign("flight", state)
    browser = json.loads(json.dumps(state).replace("6378137.0", "6378137").replace("411000.0", "411000"))
    assert check("flight", browser, sig)
    assert not check("flight", {**browser, "y": 6378138}, sig)
