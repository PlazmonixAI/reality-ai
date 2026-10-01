"""ASM Teach accounts: school sign-up through Google, terms, school admin panel, teacher accounts, files and usage."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.platform import auth, teach

pytestmark = pytest.mark.real_auth

GOOGLE = {"email": "Office@VikashSchool.example", "sub": "google-sub-123", "name": "Vikash School"}


def fresh():
    for lim in (auth.signup_limit, auth.login_ip_limit, auth.login_email_limit, teach.login_ip_limit, teach.login_name_limit,
                teach.signup_limit, teach.upload_limit):
        lim.reset()
    return TestClient(app)


def school_client(sub="google-sub-123", email="office@vikashschool.example", username="vikash.admin"):
    c = fresh()
    c.cookies.set(teach.GOOGLE_COOKIE, teach.google_pending({"email": email, "sub": sub, "name": "Vikash"}), path="/api/teach")
    r = c.post("/api/teach/school/signup", json={"school_name": "Vikash Group of Institutions", "city": "Bargarh",
                                                 "username": username, "password": "board-and-chalk-1", "accept_terms": True})
    assert r.status_code == 201, r.text
    return c


def test_teach_pages_are_separate_and_gated():
    c = fresh()
    assert c.get("/teach").status_code == 200
    r = c.get("/teach/app", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/teach"
    assert c.get("/api/teach/me").status_code == 401


def test_school_signup_needs_google_and_terms():
    c = fresh()
    body = {"school_name": "Vikash", "username": "vikash", "password": "board-and-chalk-1", "accept_terms": True}
    assert c.post("/api/teach/school/signup", json=body).status_code == 401  # no Google proof
    c.cookies.set(teach.GOOGLE_COOKIE, "forged.value", path="/api/teach")
    assert c.post("/api/teach/school/signup", json=body).status_code == 401
    c.cookies.set(teach.GOOGLE_COOKIE, teach.google_pending(GOOGLE), path="/api/teach")
    assert c.get("/api/teach/google/pending").json()["email"] == "office@vikashschool.example"
    assert c.post("/api/teach/school/signup", json={**body, "accept_terms": False}).status_code == 422
    assert c.post("/api/teach/school/signup", json={**body, "username": "x"}).status_code == 422
    r = c.post("/api/teach/school/signup", json=body)
    assert r.status_code == 201 and r.json()["role"] == "school"
    me = c.get("/api/teach/me").json()
    assert me["role"] == "school" and me["school"]["google_email"] == "office@vikashschool.example"
    assert c.get("/teach/app", follow_redirects=False).status_code == 200
    # the same Google account cannot make a second school
    c2 = fresh()
    c2.cookies.set(teach.GOOGLE_COOKIE, teach.google_pending(GOOGLE), path="/api/teach")
    assert c2.post("/api/teach/school/signup", json={**body, "username": "vikash2"}).status_code == 409


def test_expired_google_proof_is_refused():
    data = teach.google_pending(GOOGLE)
    assert teach.read_google_pending(data)["sub"] == "google-sub-123"
    raw, sig = data.rsplit(".", 1)
    assert teach.read_google_pending(raw + "." + "0" * len(sig)) is None


def test_school_admin_adds_teachers_and_teachers_sign_in():
    s = school_client(sub="s-2", email="a@school2.example", username="school2")
    r = s.post("/api/teach/teachers", json={"name": "Asha Rao", "email": "asha@school2.example", "username": "asha.rao",
                                            "password": "pendulum-swings", "subject": "Physics"})
    assert r.status_code == 201, r.text
    tid = r.json()["teacher"]["id"]
    assert s.post("/api/teach/teachers", json={"name": "Dup", "email": "d@x.example", "username": "asha.rao",
                                               "password": "pendulum-swings"}).status_code == 409
    assert s.post("/api/teach/teachers", json={"name": "Dup", "email": "d@x.example", "username": "school2",
                                               "password": "pendulum-swings"}).status_code == 409  # shared namespace
    overview = s.get("/api/teach/school").json()
    assert [t["username"] for t in overview["teachers"]] == ["asha.rao"]

    t = fresh()
    assert t.post("/api/teach/login", json={"username": "asha.rao", "password": "wrong-password", "role": "teacher"}).status_code == 401
    assert t.post("/api/teach/login", json={"username": "asha.rao", "password": "pendulum-swings", "role": "school"}).status_code == 401
    r = t.post("/api/teach/login", json={"username": "Asha.Rao", "password": "pendulum-swings", "role": "teacher"})
    assert r.status_code == 200 and r.json()["next"].endswith("#/board")
    me = t.get("/api/teach/me").json()
    assert me["role"] == "teacher" and me["teacher"]["school_name"] == "Vikash Group of Institutions"
    # a teacher session works with the engine like any session, but not with the admin panel
    assert t.post("/simulate", json={"domain": "teach", "name": "catalog", "args": {}}).status_code == 200
    assert t.get("/api/teach/school").status_code == 403
    assert t.post("/api/teach/teachers", json={"name": "X", "email": "x@x.example", "username": "xx1", "password": "abcdefgh1"}).status_code == 403
    # usage reaches the school's panel
    assert t.post("/api/teach/events", json={"kind": "experiment", "ref": "p11-pendulum"}).status_code == 204
    assert t.post("/api/teach/events", json={"kind": "nonsense"}).status_code == 422
    row = next(x for x in s.get("/api/teach/school").json()["teachers"] if x["id"] == tid)
    assert row["usage_30d"]["experiments"] == 1 and row["usage_30d"]["sessions"] == 1
    assert s.get("/api/teach/school").json()["top_experiments"] == [{"id": "p11-pendulum", "count": 1}]

    # pausing a teacher signs them out and blocks sign-in
    assert s.patch(f"/api/teach/teachers/{tid}", json={"active": False}).json()["teacher"]["active"] is False
    assert t.get("/api/teach/me").status_code == 401
    assert fresh().post("/api/teach/login", json={"username": "asha.rao", "password": "pendulum-swings", "role": "teacher"}).status_code == 403
    s.patch(f"/api/teach/teachers/{tid}", json={"active": True, "password": "new-pendulum-9"})
    t2 = fresh()
    assert t2.post("/api/teach/login", json={"username": "asha.rao", "password": "new-pendulum-9", "role": "teacher"}).status_code == 200
    # another school cannot touch this teacher
    other = school_client(sub="s-3", email="b@school3.example", username="school3")
    assert other.patch(f"/api/teach/teachers/{tid}", json={"active": False}).status_code == 404
    assert other.delete(f"/api/teach/teachers/{tid}").status_code == 404
    # removing the teacher removes the account
    assert s.delete(f"/api/teach/teachers/{tid}").status_code == 204
    assert t2.get("/api/teach/me").status_code == 401


def test_school_admin_signs_in_with_username():
    school_client(sub="s-4", email="c@school4.example", username="school4")
    c = fresh()
    r = c.post("/api/teach/login", json={"username": "school4", "password": "board-and-chalk-1", "role": "school"})
    assert r.status_code == 200 and r.json()["next"].endswith("#/admin")
    assert c.get("/api/teach/school").status_code == 200


def test_teacher_profile_and_files():
    s = school_client(sub="s-5", email="d@school5.example", username="school5")
    s.post("/api/teach/teachers", json={"name": "Ravi", "email": "ravi@school5.example", "username": "ravi5",
                                        "password": "chalk-dust-77", "subject": "Maths"})
    t = fresh()
    t.post("/api/teach/login", json={"username": "ravi5", "password": "chalk-dust-77", "role": "teacher"})
    assert t.patch("/api/teach/me", json={"phone": "+91 79783 79593", "subject": "Mathematics"}).json()["teacher"]["subject"] == "Mathematics"
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    r = t.post("/api/teach/files?name=circle diagram.png", content=png, headers={"content-type": "image/png"})
    assert r.status_code == 201, r.text
    fid = r.json()["file"]["id"]
    assert t.post("/api/teach/files?name=virus.exe", content=b"MZ").status_code == 422
    assert t.post("/api/teach/files?name=empty.pdf", content=b"").status_code == 422
    files = t.get("/api/teach/files").json()["files"]
    assert files[0]["name"] == "circle diagram.png" and files[0]["type"] == "image/png"
    got = t.get(f"/api/teach/files/{fid}")
    assert got.status_code == 200 and got.content == png and got.headers["x-frame-options"] == "SAMEORIGIN"
    # files are private to their teacher
    s.post("/api/teach/teachers", json={"name": "Other", "email": "o@school5.example", "username": "other5", "password": "chalk-dust-78"})
    o = fresh()
    o.post("/api/teach/login", json={"username": "other5", "password": "chalk-dust-78", "role": "teacher"})
    assert o.get(f"/api/teach/files/{fid}").status_code == 404
    assert o.delete(f"/api/teach/files/{fid}").status_code == 404
    assert t.delete(f"/api/teach/files/{fid}").status_code == 204
    assert t.get("/api/teach/files").json()["files"] == []


def test_office_files_convert_to_pdf_when_libreoffice_is_present(monkeypatch):
    monkeypatch.setattr(teach, "office_to_pdf", lambda data, ext: b"%PDF-1.4 converted")
    s = school_client(sub="s-6", email="e@school6.example", username="school6")
    s.post("/api/teach/teachers", json={"name": "Meera", "email": "m@school6.example", "username": "meera6", "password": "slides-and-pdfs"})
    t = fresh()
    t.post("/api/teach/login", json={"username": "meera6", "password": "slides-and-pdfs", "role": "teacher"})
    r = t.post("/api/teach/files?name=Optics lesson.pptx", content=b"PK\x03\x04 fake pptx")
    assert r.status_code == 201 and r.json()["converted"] and r.json()["file"]["viewable_pdf"]
    fid = r.json()["file"]["id"]
    pdf = t.get(f"/api/teach/files/{fid}?as_pdf=true")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    assert t.get(f"/api/teach/files/{fid}").content.startswith(b"PK")


def test_google_callback_in_school_mode(monkeypatch):
    """The Google callback hands a new school to set-up, and signs an existing school straight in."""
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "cid")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    import base64
    import json

    class Fake:
        def __init__(self, claims):
            self.claims = claims

        def raise_for_status(self):
            pass

        def json(self):
            body = base64.urlsafe_b64encode(json.dumps(self.claims).encode()).decode().rstrip("=")
            return {"id_token": f"x.{body}.y"}

    claims = {"aud": "cid", "email_verified": True, "email": "head@newschool.example", "sub": "g-new", "name": "New School"}
    monkeypatch.setattr(auth.httpx, "post", lambda *a, **k: Fake(claims))
    c = fresh()
    r = c.get("/api/auth/google/start?mode=teach", follow_redirects=False)
    state = r.headers["location"].split("state=")[1].split("&")[0]
    r = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/teach?step=setup"
    assert c.get("/api/teach/google/pending").json()["email"] == "head@newschool.example"
    assert c.post("/api/teach/school/signup", json={"school_name": "New School", "username": "newschool", "password": "brand-new-pass",
                                                    "accept_terms": True}).status_code == 201
    # next time the same Google account signs straight in to the admin panel
    c2 = fresh()
    r = c2.get("/api/auth/google/start?mode=teach", follow_redirects=False)
    state = r.headers["location"].split("state=")[1].split("&")[0]
    r = c2.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert r.headers["location"] == "/teach/app#/admin"
    assert c2.get("/api/teach/me").json()["role"] == "school"
