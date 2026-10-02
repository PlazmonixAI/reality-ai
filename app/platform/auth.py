"""Accounts and sessions: sign up, sign in (email + password, or Google when configured), sign out, password
change and reset, profile, data export and account deletion.

Sessions are random tokens in an HttpOnly, SameSite=Lax cookie; only their SHA-256 is stored. Every
state-changing endpoint takes JSON, so a cross-site form can't forge it, and the Origin header is checked too."""
from __future__ import annotations

import base64
import json
import logging
import re
import smtplib
import threading
import urllib.parse
from email.message import EmailMessage
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.platform import db
from app.platform.security import (DUMMY_HASH, RateLimiter, hash_password, new_token, token_hash, verify_password)

log = logging.getLogger("reality.auth")
router = APIRouter(prefix="/api", tags=["account"])

COOKIE = "rasm_session"
TERMS_VERSION = "2026-09-30"
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$")

login_ip_limit = RateLimiter(20, per=60)
login_email_limit = RateLimiter(6, per=60)
signup_limit = RateLimiter(5, per=600)
forgot_limit = RateLimiter(3, per=600)
feedback_limit = RateLimiter(10, per=3600)


# ---------------------------------------------------------------- helpers
def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


def public_user(row) -> dict[str, Any]:
    return {"id": row["id"], "email": row["email"], "name": row["name"], "created_at": row["created_at"],
            "google": bool(row["google_sub"]), "has_password": bool(row["password_hash"]),
            "admin": row["email"].lower() in settings.admins}


def _clean_email(email: str) -> str:
    e = email.strip().lower()
    if not EMAIL_RE.match(e):
        raise HTTPException(422, "Enter a valid email address.")
    return e


def _check_password(password: str, email: str = "") -> None:
    if len(password) < 8:
        raise HTTPException(422, "Use at least 8 characters for your password.")
    if len(password) > 200:
        raise HTTPException(422, "That password is too long (200 characters max).")
    if email and password.lower() == email.lower():
        raise HTTPException(422, "Your password can't be your email address.")
    if len(set(password)) < 4:
        raise HTTPException(422, "That password is too easy to guess.")


def _clean_name(name: str) -> str:
    n = " ".join(name.split())
    if not 1 <= len(n) <= 60:
        raise HTTPException(422, "Your name should be 1 to 60 characters.")
    return n


def start_session(response: Response, user_id: str, request: Request, remember: bool = True) -> None:
    token = new_token()
    days = settings.session_days if remember else 1
    t = db.now()
    with db.connect() as conn:
        conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at, user_agent) VALUES (?,?,?,?,?)",
                     (token_hash(token), user_id, t, t + days * 86400, request.headers.get("user-agent", "")[:200]))
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (t, user_id))
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (t,))
    response.set_cookie(COOKIE, token, max_age=days * 86400 if remember else None, httponly=True, samesite="lax",
                        secure=settings.cookie_secure, path="/")


def session_user(token: str | None):
    if not token:
        return None
    with db.connect() as conn:
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
            (token_hash(token), db.now())).fetchone()


def optional_user(request: Request):
    return session_user(request.cookies.get(COOKIE))


def current_user(request: Request) -> dict[str, Any]:
    row = optional_user(request)
    if row is None:
        raise HTTPException(401, "Please sign in to continue.")
    return public_user(row)


def _send_mail(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_host:
        return False

    def go():
        try:
            msg = EmailMessage()
            msg["From"] = settings.smtp_from or settings.smtp_user
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
                s.starttls()
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_password)
                s.send_message(msg)
        except Exception as e:  # noqa: BLE001 - mail is best effort; never break the request
            log.warning("could not send mail to %s: %s", to, e)

    threading.Thread(target=go, daemon=True).start()
    return True


def _base_url(request: Request) -> str:
    return settings.public_base_url.rstrip("/") or str(request.base_url).rstrip("/")


# ---------------------------------------------------------------- models
class SignupIn(BaseModel):
    name: str = Field(max_length=120)
    email: str = Field(max_length=254)
    password: str = Field(max_length=400)
    accept_terms: bool = False
    invite_code: str = Field(default="", max_length=80)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=400)
    remember: bool = True


class PasswordIn(BaseModel):
    current_password: str = Field(default="", max_length=400)
    new_password: str = Field(max_length=400)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=400)


class FeedbackIn(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    page: str = Field(default="", max_length=200)


class ProfileIn(BaseModel):
    name: str = Field(max_length=120)


class DeleteIn(BaseModel):
    confirm: str = Field(max_length=400)  # the password, or the email for accounts made with Google


# ---------------------------------------------------------------- routes
@router.get("/auth/config")
def auth_config():
    return {"google": bool(settings.google_client_id and settings.google_client_secret),
            "invite_required": bool(settings.invite_codes), "password_reset_email": bool(settings.smtp_host),
            "contact_email": settings.contact_email, "terms_version": TERMS_VERSION}


def ensure_owner_account() -> str | None:
    """Create the account named by OWNER_EMAIL / OWNER_PASSWORD (set on the host, never in the code) if it doesn't
    exist yet. It signs in like any other account; an existing account, and its password, are left as they are."""
    if not (settings.owner_email and settings.owner_password):
        return None
    email = _clean_email(settings.owner_email)
    _check_password(settings.owner_password, email)
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            return None
        uid = db.new_id("usr")
        conn.execute("INSERT INTO users (id, email, name, password_hash, created_at, terms_version) VALUES (?,?,?,?,?,?)",
                     (uid, email, "Plazmonix AI", hash_password(settings.owner_password), db.now(), TERMS_VERSION))
    log.info("created the owner account %s", email)
    return uid


@router.post("/auth/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response):
    if not signup_limit.allow(client_ip(request)):
        raise HTTPException(429, "Too many sign-ups from this network. Try again in a few minutes.")
    if not body.accept_terms:
        raise HTTPException(422, "Please accept the Terms and Privacy Policy to create an account.")
    if settings.invite_codes and body.invite_code.strip() not in settings.invite_codes:
        raise HTTPException(403, "That invite code isn't valid. The beta is invite-only for now.")
    email, name = _clean_email(body.email), _clean_name(body.name)
    _check_password(body.password, email)
    uid = db.new_id("usr")
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(409, "There's already an account with that email. Try signing in.")
        conn.execute("INSERT INTO users (id, email, name, password_hash, created_at, terms_version) VALUES (?,?,?,?,?,?)",
                     (uid, email, name, hash_password(body.password), db.now(), TERMS_VERSION))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    start_session(response, uid, request)
    return {"user": public_user(row)}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    if not login_ip_limit.allow(client_ip(request)) or not login_email_limit.allow(email):
        raise HTTPException(429, "Too many attempts. Wait a minute and try again.")
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        verify_password(body.password, DUMMY_HASH)  # same timing as a real check
        raise HTTPException(401, "Email or password is incorrect.")
    if not row["password_hash"]:
        raise HTTPException(401, "This account uses Google sign-in. Use the Google button, or reset your password.")
    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    start_session(response, row["id"], request, body.remember)
    return {"user": public_user(row)}


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        with db.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/session")
def session(request: Request):
    """The signed-in user, or null (never an error), for pages that just want to know."""
    row = optional_user(request)
    return {"user": public_user(row) if row else None}


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return {"user": user}


@router.post("/auth/password")
def change_password(body: PasswordIn, request: Request, response: Response, user=Depends(current_user)):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    if row["password_hash"] and not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(403, "Your current password is incorrect.")
    _check_password(body.new_password, row["email"])
    with db.connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.new_password), user["id"]))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))  # sign out everywhere else
    start_session(response, user["id"], request)
    return {"ok": True}


@router.post("/auth/forgot")
def forgot(body: ForgotIn, request: Request):
    if not forgot_limit.allow(client_ip(request)):
        raise HTTPException(429, "Too many requests. Try again in a few minutes.")
    email = body.email.strip().lower()
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if row and settings.smtp_host:
            token = new_token()
            conn.execute("INSERT INTO password_resets (token_hash, user_id, expires_at) VALUES (?,?,?)",
                         (token_hash(token), row["id"], db.now() + 3600))
            link = f"{_base_url(request)}/reset?token={urllib.parse.quote(token)}"
            _send_mail(email,"Reset your Reality ASM password",
                              f"Someone asked to reset the password for your Reality ASM account.\n\n"
                              f"Open this link within an hour to choose a new one:\n{link}\n\n"
                              f"If it wasn't you, ignore this email. Your password stays the same.\n")
    # Same answer whether or not the account exists
    return {"ok": True, "email_enabled": bool(settings.smtp_host)}


@router.post("/auth/reset")
def reset(body: ResetIn, request: Request, response: Response):
    with db.connect() as conn:
        row = conn.execute("SELECT r.*, u.email FROM password_resets r JOIN users u ON u.id = r.user_id "
                           "WHERE r.token_hash = ? AND r.used = 0 AND r.expires_at > ?",
                           (token_hash(body.token), db.now())).fetchone()
    if row is None:
        raise HTTPException(400, "This reset link has expired or was already used. Ask for a new one.")
    _check_password(body.password, row["email"])
    with db.connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), row["user_id"]))
        conn.execute("UPDATE password_resets SET used = 1 WHERE token_hash = ?", (token_hash(body.token),))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["user_id"],))
    start_session(response, row["user_id"], request)
    return {"ok": True}


@router.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, request: Request, user=Depends(current_user)):
    """Beta feedback from inside the app (read it from the feedback table)."""
    if not feedback_limit.allow(user["id"]):
        raise HTTPException(429, "Thanks, we've got a lot from you this hour. Try again a bit later.")
    with db.connect() as conn:
        conn.execute("INSERT INTO feedback (id, user_id, created_at, page, message, user_agent) VALUES (?,?,?,?,?,?)",
                     (db.new_id("fb"), user["id"], db.now(), body.page.strip()[:200], body.message.strip(),
                      request.headers.get("user-agent", "")[:200]))
    return {"ok": True}


@router.patch("/account")
def update_profile(body: ProfileIn, user=Depends(current_user)):
    name = _clean_name(body.name)
    with db.connect() as conn:
        conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))
    return {"user": {**user, "name": name}}


@router.get("/account/export")
def export_account(user=Depends(current_user)):
    """Everything we store about the signed-in user, as JSON (privacy: right of access and portability)."""
    with db.connect() as conn:
        def rows(sql):
            return [dict(r) for r in conn.execute(sql, (user["id"],)).fetchall()]
        out = {"user": user, "history": rows("SELECT * FROM runs WHERE user_id = ?"),
               "company": rows("SELECT * FROM companies WHERE user_id = ?"),
               "spacecraft": rows("SELECT * FROM spacecraft WHERE user_id = ?"),
               "photos": rows("SELECT * FROM photos WHERE user_id = ?"),
               "challenges": rows("SELECT * FROM challenge_progress WHERE user_id = ?"),
               "feedback": rows("SELECT created_at, page, message FROM feedback WHERE user_id = ?"),
               "sessions": rows("SELECT created_at, expires_at, user_agent FROM sessions WHERE user_id = ?")}
    for group in ("history", "spacecraft", "photos", "challenges"):
        for r in out[group]:
            for k in ("payload", "summary", "spec", "orbit", "log", "data", "evidence"):
                if isinstance(r.get(k), str):
                    try:
                        r[k] = json.loads(r[k])
                    except ValueError:
                        pass
    return out


@router.delete("/account")
def delete_account(body: DeleteIn, response: Response, user=Depends(current_user)):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        ok = verify_password(body.confirm, row["password_hash"]) if row["password_hash"] else \
            body.confirm.strip().lower() == row["email"]
        if not ok:
            raise HTTPException(403, "That doesn't match. Enter your password (or your email for Google accounts).")
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


# ---------------------------------------------------------------- Google sign-in (only when configured)
@router.get("/auth/google/start")
def google_start(request: Request, next: str = "/app/", mode: str = ""):
    if not (settings.google_client_id and settings.google_client_secret):
        raise HTTPException(404, "Google sign-in isn't set up on this server.")
    state = new_token()
    redirect = f"{_base_url(request)}/api/auth/google/callback"
    q = urllib.parse.urlencode({"client_id": settings.google_client_id, "redirect_uri": redirect, "response_type": "code",
                                "scope": "openid email profile", "state": state, "prompt": "select_account"})
    resp = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{q}", status_code=302)
    safe_next = next if next.startswith("/") and not next.startswith("//") else "/app/"
    resp.set_cookie("rasm_oauth", f"{state}|{safe_next}|{'teach' if mode == 'teach' else ''}", max_age=600, httponly=True, samesite="lax",
                    secure=settings.cookie_secure, path="/api/auth/google")
    return resp


@router.get("/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = ""):
    saved = request.cookies.get("rasm_oauth", "")
    want, _, rest = saved.partition("|")
    nxt, _, mode = rest.partition("|")
    fail = "/teach?error=google" if mode == "teach" else "/login?error=google"
    if not code or not state or state != want:
        return RedirectResponse(fail, status_code=302)
    try:
        r = httpx.post("https://oauth2.googleapis.com/token", timeout=15, data={
            "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "redirect_uri": f"{_base_url(request)}/api/auth/google/callback", "grant_type": "authorization_code"})
        r.raise_for_status()
        # The ID token came straight from Google's token endpoint over TLS, so its claims can be read directly
        payload = r.json()["id_token"].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except Exception as e:  # noqa: BLE001
        log.warning("google sign-in failed: %s", e)
        return RedirectResponse(fail, status_code=302)
    if claims.get("aud") != settings.google_client_id or not claims.get("email_verified"):
        return RedirectResponse(fail, status_code=302)
    if mode == "teach":  # ASM Teach school sign-up / sign-in: Google only proves the school's email
        from app.platform.teach import google_school_login
        resp = RedirectResponse("/teach", status_code=302)
        resp.headers["location"] = google_school_login(claims, request, resp)
        resp.delete_cookie("rasm_oauth", path="/api/auth/google")
        return resp
    email, sub = claims["email"].lower(), claims["sub"]
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = ? OR email = ?", (sub, email)).fetchone()
        if row is None:
            if settings.invite_codes:
                return RedirectResponse("/signup?error=invite", status_code=302)
            uid = db.new_id("usr")
            conn.execute("INSERT INTO users (id, email, name, google_sub, created_at, terms_version) VALUES (?,?,?,?,?,?)",
                         (uid, email, _clean_name(claims.get("name") or email.split("@")[0]), sub, db.now(), TERMS_VERSION))
        else:
            uid = row["id"]
            if not row["google_sub"]:
                conn.execute("UPDATE users SET google_sub = ? WHERE id = ?", (sub, uid))
    resp = RedirectResponse(nxt or "/app/", status_code=302)
    start_session(resp, uid, request)
    resp.delete_cookie("rasm_oauth", path="/api/auth/google")
    return resp
