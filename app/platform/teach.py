"""ASM Teach accounts: schools, teachers, the school admin panel, teachers' files and usage.

A school signs up with its Google account (Google has already verified the email, so we never send codes), then sets
a username and password and accepts the ASM Teach terms. The school admin adds teachers with a username and password.
Both sign in at /teach. Each school admin and teacher is backed by an internal row in `users`, so a session is an
ordinary session: experiments, the AI co-teacher and saved lessons work exactly as they do elsewhere. The platform
only stores accounts and files; it never computes physics.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, Field

from app.platform import db
from app.platform.auth import (TERMS_VERSION, _check_password, _clean_email, _clean_name, client_ip, current_user,
                               start_session)
from app.platform.security import DUMMY_HASH, RateLimiter, check, hash_password, sign, verify_password

router = APIRouter(prefix="/api/teach", tags=["asm-teach"])

TEACH_TERMS_VERSION = "2026-10-01"
GOOGLE_COOKIE = "asm_teach_google"
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MAX_TEACHERS = 500
MAX_FILE = 25 * 1024 * 1024
MAX_STORAGE = 300 * 1024 * 1024
FILE_TYPES = {  # extension -> MIME type; anything else is refused
    "pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
    "gif": "image/gif", "mp4": "video/mp4", "webm": "video/webm",
    "ppt": "application/vnd.ms-powerpoint", "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "doc": "application/msword", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
OFFICE = {"ppt", "pptx", "doc", "docx"}
EVENT_KINDS = {"experiment", "lesson_saved", "board", "file_shown", "video", "equation", "listen"}

TABLES = """
CREATE TABLE IF NOT EXISTS teach_schools (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT '',
    google_email TEXT NOT NULL UNIQUE,
    google_sub TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    terms_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teach_teachers (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    school_id TEXT NOT NULL REFERENCES teach_schools(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS teach_teachers_school ON teach_teachers(school_id);
CREATE TABLE IF NOT EXISTS teach_files (
    id TEXT PRIMARY KEY,
    teacher_id TEXT NOT NULL REFERENCES teach_teachers(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    ext TEXT NOT NULL,
    size INTEGER NOT NULL,
    data BLOB NOT NULL,
    pdf BLOB,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS teach_files_teacher ON teach_files(teacher_id, created_at DESC);
CREATE TABLE IF NOT EXISTS teach_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id TEXT NOT NULL REFERENCES teach_schools(id) ON DELETE CASCADE,
    teacher_id TEXT REFERENCES teach_teachers(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    ref TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS teach_events_school ON teach_events(school_id, created_at);
"""
db.SCHEMA += TABLES  # created with the rest of the schema on first connect

login_ip_limit = RateLimiter(20, per=60)
login_name_limit = RateLimiter(6, per=60)
signup_limit = RateLimiter(5, per=600)
upload_limit = RateLimiter(30, per=600)


# ---------------------------------------------------------------- who is signed in
def _role(user_id: str) -> tuple[str, Any] | tuple[None, None]:
    with db.connect() as conn:
        s = conn.execute("SELECT * FROM teach_schools WHERE user_id = ?", (user_id,)).fetchone()
        if s:
            return "school", s
        t = conn.execute("SELECT t.*, s.name AS school_name FROM teach_teachers t JOIN teach_schools s ON s.id = t.school_id "
                         "WHERE t.user_id = ?", (user_id,)).fetchone()
        if t:
            return "teacher", t
    return None, None


def school_admin(user=Depends(current_user)):
    role, row = _role(user["id"])
    if role != "school":
        raise HTTPException(403, "Only the school's admin account can do this.")
    return row


def teacher(user=Depends(current_user)):
    role, row = _role(user["id"])
    if role != "teacher":
        raise HTTPException(403, "Sign in with a teacher account to use this.")
    if not row["active"]:
        raise HTTPException(403, "This teacher account has been paused by the school.")
    return row


def _clean_username(name: str) -> str:
    u = name.strip().lower()
    if not USERNAME_RE.match(u):
        raise HTTPException(422, "Usernames are 3 to 32 characters: letters, digits, dot, dash or underscore, starting with a letter or digit.")
    return u


def _username_free(conn, username: str) -> bool:
    return not (conn.execute("SELECT 1 FROM teach_schools WHERE username = ?", (username,)).fetchone()
                or conn.execute("SELECT 1 FROM teach_teachers WHERE username = ?", (username,)).fetchone())


def _shadow_user(conn, kind: str, name: str, password: str) -> str:
    """The internal account behind a school admin or a teacher (never shown, never used to sign in by email)."""
    uid = db.new_id("usr")
    conn.execute("INSERT INTO users (id, email, name, password_hash, created_at, terms_version) VALUES (?,?,?,?,?,?)",
                 (uid, f"{uid}@{kind}.asm-teach.internal", name, hash_password(password), db.now(), TERMS_VERSION))
    return uid


def _event(school_id: str, teacher_id: str | None, kind: str, ref: str = "") -> None:
    with db.connect() as conn:
        conn.execute("INSERT INTO teach_events (school_id, teacher_id, kind, ref, created_at) VALUES (?,?,?,?,?)",
                     (school_id, teacher_id, kind, ref[:120], db.now()))


# ---------------------------------------------------------------- Google step of school sign-up
def google_pending(claims: dict) -> str:
    """Signed, short-lived proof that Google verified this email (set as a cookie by the Google callback)."""
    data = {"email": claims["email"].lower(), "sub": claims["sub"], "name": claims.get("name") or "", "exp": int(time.time()) + 1800}
    raw = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    return f"{raw}.{sign('teach-google', data)}"


def read_google_pending(value: str | None) -> dict | None:
    if not value or "." not in value:
        return None
    raw, sig = value.rsplit(".", 1)
    try:
        data = json.loads(base64.urlsafe_b64decode(raw.encode()))
    except (ValueError, TypeError):
        return None
    if not check("teach-google", data, sig) or data.get("exp", 0) < time.time():
        return None
    return data


def google_school_login(claims: dict, request: Request, response: Response) -> str:
    """Called by the Google callback in school mode: an existing school is signed in; a new one goes to set-up."""
    with db.connect() as conn:
        s = conn.execute("SELECT * FROM teach_schools WHERE google_sub = ?", (claims["sub"],)).fetchone()
    if s:
        start_session(response, s["user_id"], request)
        return "/teach/app#/admin"
    from app.config import settings
    response.set_cookie(GOOGLE_COOKIE, google_pending(claims), max_age=1800, httponly=True, samesite="lax",
                        secure=settings.cookie_secure, path="/api/teach")
    return "/teach?step=setup"


@router.get("/google/pending")
def pending(request: Request):
    data = read_google_pending(request.cookies.get(GOOGLE_COOKIE))
    if not data:
        raise HTTPException(404, "Start with “Continue with Google” first.")
    return {"email": data["email"], "name": data["name"]}


class SchoolSignupIn(BaseModel):
    school_name: str = Field(max_length=120)
    city: str = Field(default="", max_length=80)
    username: str = Field(max_length=40)
    password: str = Field(max_length=200)
    accept_terms: bool = False


@router.post("/school/signup", status_code=201)
def school_signup(body: SchoolSignupIn, request: Request, response: Response):
    if not signup_limit.allow(client_ip(request)):
        raise HTTPException(429, "Too many sign-ups from this network. Try again in a few minutes.")
    g = read_google_pending(request.cookies.get(GOOGLE_COOKIE))
    if not g:
        raise HTTPException(401, "Your Google check has expired. Continue with Google again.")
    if not body.accept_terms:
        raise HTTPException(422, "Please agree to the ASM Teach Terms and Privacy Policy to create the school account.")
    name = " ".join(body.school_name.split())
    if not 2 <= len(name) <= 120:
        raise HTTPException(422, "Enter the school's name.")
    username = _clean_username(body.username)
    _check_password(body.password, username)
    with db.transaction() as conn:
        if conn.execute("SELECT 1 FROM teach_schools WHERE google_sub = ? OR google_email = ?", (g["sub"], g["email"])).fetchone():
            raise HTTPException(409, "This Google account already has a school. Sign in instead.")
        if not _username_free(conn, username):
            raise HTTPException(409, "That username is taken. Try another.")
        uid = _shadow_user(conn, "school", name, body.password)
        sid = db.new_id("sch")
        conn.execute("INSERT INTO teach_schools (id, user_id, name, city, google_email, google_sub, username, created_at, terms_version) "
                     "VALUES (?,?,?,?,?,?,?,?,?)", (sid, uid, name, " ".join(body.city.split())[:80], g["email"], g["sub"],
                                                    username, db.now(), TEACH_TERMS_VERSION))
    start_session(response, uid, request)
    response.delete_cookie(GOOGLE_COOKIE, path="/api/teach")
    return {"role": "school", "next": "/teach/app#/admin"}


# ---------------------------------------------------------------- sign in (school admin or teacher)
class LoginIn(BaseModel):
    username: str = Field(max_length=60)
    password: str = Field(max_length=200)
    role: str = Field(default="teacher", pattern="^(school|teacher)$")
    remember: bool = True


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    username = body.username.strip().lower()
    if not login_ip_limit.allow(client_ip(request)) or not login_name_limit.allow(username):
        raise HTTPException(429, "Too many attempts. Wait a minute and try again.")
    table = "teach_schools" if body.role == "school" else "teach_teachers"
    with db.connect() as conn:
        row = conn.execute(f"SELECT x.*, u.password_hash FROM {table} x JOIN users u ON u.id = x.user_id "  # noqa: S608 (fixed names)
                           "WHERE x.username = ?", (username,)).fetchone()
    if row is None:
        verify_password(body.password, DUMMY_HASH)
        raise HTTPException(401, "Username or password is incorrect.")
    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Username or password is incorrect.")
    if body.role == "teacher" and not row["active"]:
        raise HTTPException(403, "This account has been paused by your school. Ask your school admin.")
    start_session(response, row["user_id"], request, body.remember)
    if body.role == "teacher":
        _event(row["school_id"], row["id"], "board", "sign-in")
    return {"role": body.role, "next": "/teach/app#/admin" if body.role == "school" else "/teach/app#/board"}


@router.get("/me")
def me(user=Depends(current_user)):
    role, row = _role(user["id"])
    if role is None:
        raise HTTPException(403, "This is not an ASM Teach account.")
    if role == "school":
        return {"role": "school", "school": _school_out(row)}
    with db.connect() as conn:
        used = conn.execute("SELECT COALESCE(SUM(size),0) FROM teach_files WHERE teacher_id = ?", (row["id"],)).fetchone()[0]
    return {"role": "teacher", "teacher": {**_teacher_out(row), "school_name": row["school_name"], "storage_used": used,
                                           "storage_limit": MAX_STORAGE}}


def _school_out(s) -> dict[str, Any]:
    return {"id": s["id"], "name": s["name"], "city": s["city"], "google_email": s["google_email"], "username": s["username"],
            "created_at": s["created_at"]}


def _teacher_out(t) -> dict[str, Any]:
    return {"id": t["id"], "name": t["name"], "email": t["email"], "username": t["username"], "subject": t["subject"],
            "phone": t["phone"], "active": bool(t["active"]), "created_at": t["created_at"]}


# ---------------------------------------------------------------- school admin panel
@router.get("/school")
def school_overview(school=Depends(school_admin)):
    since = db.now() - 30 * 86400
    with db.connect() as conn:
        rows = conn.execute("SELECT t.*, u.last_login_at FROM teach_teachers t JOIN users u ON u.id = t.user_id "
                            "WHERE t.school_id = ? ORDER BY t.created_at", (school["id"],)).fetchall()
        usage = {r["teacher_id"]: r for r in conn.execute(
            "SELECT teacher_id, SUM(kind='experiment') AS experiments, SUM(kind='lesson_saved') AS lessons, "
            "SUM(kind='board') AS sessions, SUM(kind IN ('file_shown','video')) AS media, MAX(created_at) AS last_active "
            "FROM teach_events WHERE school_id = ? AND created_at > ? GROUP BY teacher_id", (school["id"], since)).fetchall()}
        files = {r["teacher_id"]: r for r in conn.execute(
            "SELECT f.teacher_id, COUNT(*) AS n, SUM(f.size) AS bytes FROM teach_files f JOIN teach_teachers t ON t.id = f.teacher_id "
            "WHERE t.school_id = ? GROUP BY f.teacher_id", (school["id"],)).fetchall()}
        top = conn.execute("SELECT ref, COUNT(*) AS n FROM teach_events WHERE school_id = ? AND kind = 'experiment' AND created_at > ? "
                           "GROUP BY ref ORDER BY n DESC LIMIT 8", (school["id"], since)).fetchall()
    teachers = []
    for t in rows:
        u, f = usage.get(t["id"]), files.get(t["id"])
        teachers.append({**_teacher_out(t), "last_login_at": t["last_login_at"],
                         "usage_30d": {k: int((u[k] if u else 0) or 0) for k in ("experiments", "lessons", "sessions", "media")},
                         "last_active": u["last_active"] if u else None, "files": int(f["n"]) if f else 0})
    return {"school": _school_out(school), "teachers": teachers,
            "top_experiments": [{"id": r["ref"], "count": r["n"]} for r in top]}


class TeacherIn(BaseModel):
    name: str = Field(max_length=120)
    email: str = Field(max_length=254)
    username: str = Field(max_length=40)
    password: str = Field(max_length=200)
    subject: str = Field(default="", max_length=60)


@router.post("/teachers", status_code=201)
def add_teacher(body: TeacherIn, school=Depends(school_admin)):
    name, email, username = _clean_name(body.name), _clean_email(body.email), _clean_username(body.username)
    _check_password(body.password, username)
    with db.transaction() as conn:
        if conn.execute("SELECT COUNT(*) FROM teach_teachers WHERE school_id = ?", (school["id"],)).fetchone()[0] >= MAX_TEACHERS:
            raise HTTPException(422, f"A school can have up to {MAX_TEACHERS} teacher accounts.")
        if not _username_free(conn, username):
            raise HTTPException(409, "That username is taken. Try another.")
        if conn.execute("SELECT 1 FROM teach_teachers WHERE school_id = ? AND email = ?", (school["id"], email)).fetchone():
            raise HTTPException(409, "A teacher with this email is already in your school.")
        uid = _shadow_user(conn, "teacher", name, body.password)
        tid = db.new_id("tch")
        conn.execute("INSERT INTO teach_teachers (id, user_id, school_id, name, email, username, subject, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (tid, uid, school["id"], name, email, username, " ".join(body.subject.split())[:60], db.now()))
        row = conn.execute("SELECT * FROM teach_teachers WHERE id = ?", (tid,)).fetchone()
    return {"teacher": _teacher_out(row)}


class TeacherPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    subject: str | None = Field(default=None, max_length=60)
    active: bool | None = None
    password: str | None = Field(default=None, max_length=200)


def _own_teacher(conn, school_id: str, teacher_id: str):
    row = conn.execute("SELECT * FROM teach_teachers WHERE id = ? AND school_id = ?", (teacher_id, school_id)).fetchone()
    if row is None:
        raise HTTPException(404, "No such teacher in your school.")
    return row


@router.patch("/teachers/{teacher_id}")
def update_teacher(teacher_id: str, body: TeacherPatch, school=Depends(school_admin)):
    with db.transaction() as conn:
        t = _own_teacher(conn, school["id"], teacher_id)
        if body.name is not None:
            conn.execute("UPDATE teach_teachers SET name = ? WHERE id = ?", (_clean_name(body.name), t["id"]))
        if body.subject is not None:
            conn.execute("UPDATE teach_teachers SET subject = ? WHERE id = ?", (" ".join(body.subject.split())[:60], t["id"]))
        if body.password is not None:
            _check_password(body.password, t["username"])
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), t["user_id"]))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (t["user_id"],))  # signed out everywhere
        if body.active is not None:
            conn.execute("UPDATE teach_teachers SET active = ? WHERE id = ?", (int(body.active), t["id"]))
            if not body.active:
                conn.execute("DELETE FROM sessions WHERE user_id = ?", (t["user_id"],))
        row = conn.execute("SELECT * FROM teach_teachers WHERE id = ?", (t["id"],)).fetchone()
    return {"teacher": _teacher_out(row)}


@router.delete("/teachers/{teacher_id}", status_code=204)
def remove_teacher(teacher_id: str, school=Depends(school_admin)):
    with db.transaction() as conn:
        t = _own_teacher(conn, school["id"], teacher_id)
        conn.execute("DELETE FROM users WHERE id = ?", (t["user_id"],))  # cascades to the teacher, sessions, lessons, files
    return Response(status_code=204)


# ---------------------------------------------------------------- the teacher's own profile ("my panel")
class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    subject: str | None = Field(default=None, max_length=60)
    phone: str | None = Field(default=None, max_length=20)


@router.patch("/me")
def update_me(body: ProfileIn, t=Depends(teacher)):
    with db.connect() as conn:
        if body.name is not None:
            n = _clean_name(body.name)
            conn.execute("UPDATE teach_teachers SET name = ? WHERE id = ?", (n, t["id"]))
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (n, t["user_id"]))
        if body.subject is not None:
            conn.execute("UPDATE teach_teachers SET subject = ? WHERE id = ?", (" ".join(body.subject.split())[:60], t["id"]))
        if body.phone is not None:
            p = re.sub(r"[^\d+ -]", "", body.phone)[:20]
            conn.execute("UPDATE teach_teachers SET phone = ? WHERE id = ?", (p, t["id"]))
        row = conn.execute("SELECT * FROM teach_teachers WHERE id = ?", (t["id"],)).fetchone()
    return {"teacher": _teacher_out(row)}


@router.get("/me/usage")
def my_usage(t=Depends(teacher)):
    since = db.now() - 30 * 86400
    with db.connect() as conn:
        rows = conn.execute("SELECT kind, COUNT(*) AS n FROM teach_events WHERE teacher_id = ? AND created_at > ? GROUP BY kind",
                            (t["id"], since)).fetchall()
        recent = conn.execute("SELECT ref, MAX(created_at) AS at FROM teach_events WHERE teacher_id = ? AND kind = 'experiment' "
                              "GROUP BY ref ORDER BY at DESC LIMIT 8", (t["id"],)).fetchall()
    return {"last_30_days": {r["kind"]: r["n"] for r in rows}, "recent_experiments": [r["ref"] for r in recent]}


class EventIn(BaseModel):
    kind: str = Field(max_length=20)
    ref: str = Field(default="", max_length=120)


@router.post("/events", status_code=204)
def record_event(body: EventIn, t=Depends(teacher)):
    if body.kind not in EVENT_KINDS:
        raise HTTPException(422, "Unknown event")
    _event(t["school_id"], t["id"], body.kind, body.ref)
    return Response(status_code=204)


# ---------------------------------------------------------------- teachers' files (their PPTs, PDFs, pictures, clips)
def office_to_pdf(data: bytes, ext: str) -> bytes | None:
    """Convert a PowerPoint or Word file to PDF with LibreOffice when the server has it; None otherwise."""
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"in.{ext}"
        src.write_bytes(data)
        try:
            subprocess.run([exe, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", tmp, str(src)],
                           check=True, timeout=120, capture_output=True, env={"HOME": tmp, "PATH": "/usr/bin:/bin"})
        except (subprocess.SubprocessError, OSError):
            return None
        out = Path(tmp) / "in.pdf"
        return out.read_bytes() if out.is_file() else None


def _file_out(f) -> dict[str, Any]:
    return {"id": f["id"], "name": f["name"], "ext": f["ext"], "size": f["size"], "created_at": f["created_at"],
            "type": FILE_TYPES[f["ext"]], "viewable_pdf": f["ext"] == "pdf" or bool(f["has_pdf"])}


@router.get("/files")
def list_files(t=Depends(teacher)):
    with db.connect() as conn:
        rows = conn.execute("SELECT id, name, ext, size, created_at, pdf IS NOT NULL AS has_pdf FROM teach_files "
                            "WHERE teacher_id = ? ORDER BY created_at DESC", (t["id"],)).fetchall()
    return {"files": [_file_out(r) for r in rows]}


@router.post("/files", status_code=201)
async def upload_file(request: Request, name: str, t=Depends(teacher)):
    """The file is the raw request body (no multipart), its name in ?name=."""
    if not upload_limit.allow(t["id"]):
        raise HTTPException(429, "Too many uploads at once. Wait a few minutes.")
    clean = re.sub(r"[^\w .()\-]", "_", name.strip())[:120] or "file"
    ext = clean.rsplit(".", 1)[-1].lower() if "." in clean else ""
    if ext not in FILE_TYPES:
        raise HTTPException(422, "Upload a PDF, PowerPoint, Word, image (PNG, JPG, WebP, GIF) or video (MP4, WebM) file.")
    data = await request.body()
    if not data:
        raise HTTPException(422, "That file is empty.")
    if len(data) > MAX_FILE:
        raise HTTPException(413, "Files can be up to 25 MB.")
    with db.connect() as conn:
        used = conn.execute("SELECT COALESCE(SUM(size),0) FROM teach_files WHERE teacher_id = ?", (t["id"],)).fetchone()[0]
    if used + len(data) > MAX_STORAGE:
        raise HTTPException(413, "Your file space (300 MB) is full. Delete an old file first.")
    pdf = office_to_pdf(data, ext) if ext in OFFICE else None
    fid = db.new_id("fil")
    with db.connect() as conn:
        conn.execute("INSERT INTO teach_files (id, teacher_id, name, ext, size, data, pdf, created_at) VALUES (?,?,?,?,?,?,?,?)",
                     (fid, t["id"], clean, ext, len(data), data, pdf, db.now()))
        row = conn.execute("SELECT id, name, ext, size, created_at, pdf IS NOT NULL AS has_pdf FROM teach_files WHERE id = ?", (fid,)).fetchone()
    return {"file": _file_out(row), "converted": pdf is not None}


@router.get("/files/{file_id}")
def get_file(file_id: str, as_pdf: bool = False, download: bool = False, t=Depends(teacher)):
    with db.connect() as conn:
        f = conn.execute("SELECT * FROM teach_files WHERE id = ? AND teacher_id = ?", (file_id, t["id"])).fetchone()
    if f is None:
        raise HTTPException(404, "File not found")
    if as_pdf and f["pdf"] is not None:
        body, mime, fname = f["pdf"], "application/pdf", f["name"].rsplit(".", 1)[0] + ".pdf"
    else:
        body, mime, fname = f["data"], FILE_TYPES[f["ext"]], f["name"]
    disp = "attachment" if download else "inline"
    safe = re.sub(r'["\\\r\n]', "_", fname)
    # Shown inside ASM Teach's own frames, so allow same-origin framing for these responses only
    return RawResponse(bytes(body), media_type=mime, headers={
        "Content-Disposition": f'{disp}; filename="{safe}"', "Cache-Control": "private, max-age=3600",
        "X-Frame-Options": "SAMEORIGIN", "Content-Security-Policy": "frame-ancestors 'self'"})


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: str, t=Depends(teacher)):
    with db.connect() as conn:
        n = conn.execute("DELETE FROM teach_files WHERE id = ? AND teacher_id = ?", (file_id, t["id"])).rowcount
    if not n:
        raise HTTPException(404, "File not found")
    return Response(status_code=204)
