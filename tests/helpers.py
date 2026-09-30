"""Shared helpers for platform tests."""
import itertools

from fastapi.testclient import TestClient

from app.main import app
from app.platform import auth

_n = itertools.count()


def new_client(name: str = "Ada") -> tuple[TestClient, dict]:
    """A client signed in as a brand-new user."""
    auth.signup_limit.reset()
    c = TestClient(app)
    email = f"user{next(_n)}_{id(c)}@example.com"
    r = c.post("/api/auth/signup", json={"name": name, "email": email, "password": "orbit-2026-ok", "accept_terms": True})
    assert r.status_code == 201, r.text
    return c, r.json()["user"]
