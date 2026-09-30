"""SQLite storage for the web app: users, sessions, saved history, space companies and their fleets.

One file, no server to run. Each call opens a short-lived connection (SQLite handles the locking), which keeps
things simple under uvicorn's thread pool. Rows that hold structured data store it as JSON text."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT,
    google_sub TEXT UNIQUE,
    created_at REAL NOT NULL,
    terms_version TEXT NOT NULL,
    last_login_at REAL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    sim_id TEXT,
    title TEXT NOT NULL,
    payload TEXT NOT NULL,
    summary TEXT NOT NULL,
    starred INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_user ON runs(user_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS companies (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    founded_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS spacecraft (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    spec TEXT NOT NULL,
    orbit TEXT NOT NULL,
    epoch REAL NOT NULL,
    propellant REAL NOT NULL,
    status TEXT NOT NULL,
    log TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS spacecraft_user ON spacecraft(user_id);
CREATE TABLE IF NOT EXISTS photos (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    spacecraft_id TEXT NOT NULL REFERENCES spacecraft(id) ON DELETE CASCADE,
    taken_at REAL NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS photos_user ON photos(user_id, taken_at DESC);
CREATE TABLE IF NOT EXISTS challenge_progress (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge_id TEXT NOT NULL,
    completed_at REAL NOT NULL,
    evidence TEXT NOT NULL,
    PRIMARY KEY (user_id, challenge_id)
);
"""

_init_lock = threading.Lock()
_initialised: set[str] = set()


def db_path() -> Path:
    return Path(os.environ.get("REALITY_DATABASE_PATH") or settings.database_path)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)  # autocommit; explicit BEGIN for multi-step writes
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init(path: Path | None = None) -> None:
    path = path or db_path()
    key = str(path.resolve()) if path.exists() else str(path)
    with _init_lock:
        if key in _initialised and path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = _connect(path)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
        finally:
            conn.close()
        _initialised.add(str(path.resolve()))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    init(path)
    conn = _connect(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12).replace('-', 'x').replace('_', 'y')}"


def now() -> float:
    return time.time()


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def loads(text: str | None) -> Any:
    return json.loads(text) if text else None


_secret_lock = threading.Lock()
_secret: bytes | None = None


def secret_key() -> bytes:
    """The server secret: SECRET_KEY if set, else a random key stored beside the database so it survives restarts."""
    global _secret
    with _secret_lock:
        if _secret is None:
            if settings.secret_key:
                _secret = settings.secret_key.encode()
            else:
                f = db_path().parent / "secret.key"
                f.parent.mkdir(parents=True, exist_ok=True)
                if not f.exists():
                    f.write_text(secrets.token_hex(32))
                    try:
                        f.chmod(0o600)
                    except OSError:
                        pass
                _secret = f.read_text().strip().encode()
        return _secret
