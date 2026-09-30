"""Saved history: every flight, design, mission plan, simulation snapshot and question a user keeps, so they can
come back tomorrow and open, continue or repeat it."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.platform import db
from app.platform.auth import current_user

router = APIRouter(prefix="/api/history", tags=["history"])

KINDS = {"flight", "design", "mission", "sim", "space_view", "photo", "ask", "challenge"}
MAX_PAYLOAD = 600_000  # bytes of JSON per entry
MAX_ENTRIES = 3000


class RunIn(BaseModel):
    kind: str
    title: str = Field(min_length=1, max_length=140)
    sim_id: str | None = Field(default=None, max_length=60)
    payload: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


class RunPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    payload: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    starred: bool | None = None


def _row(r, full: bool = False) -> dict[str, Any]:
    out = {"id": r["id"], "kind": r["kind"], "sim_id": r["sim_id"], "title": r["title"], "summary": db.loads(r["summary"]),
           "starred": bool(r["starred"]), "created_at": r["created_at"], "updated_at": r["updated_at"]}
    if full:
        out["payload"] = db.loads(r["payload"])
    return out


def _encode(value: dict, what: str) -> str:
    try:
        text = db.dumps(value)
    except (TypeError, ValueError):
        raise HTTPException(422, f"{what} must be plain JSON with finite numbers") from None
    if len(text) > MAX_PAYLOAD:
        raise HTTPException(413, f"{what} is too large to save ({len(text) // 1000} kB; the limit is {MAX_PAYLOAD // 1000} kB)")
    return text


def save_run(user_id: str, kind: str, title: str, payload: dict, summary: dict, sim_id: str | None = None) -> str:
    """Store a history entry from server code (e.g. a challenge completion)."""
    rid, t = db.new_id("run"), db.now()
    with db.connect() as conn:
        conn.execute("INSERT INTO runs (id, user_id, kind, sim_id, title, payload, summary, created_at, updated_at) "
                     "VALUES (?,?,?,?,?,?,?,?,?)", (rid, user_id, kind, sim_id, title[:140], db.dumps(payload), db.dumps(summary), t, t))
    return rid


@router.get("")
def list_runs(kind: str | None = None, q: str | None = None, starred: bool = False, limit: int = 50, before: float | None = None,
              user=Depends(current_user)):
    limit = max(1, min(200, limit))
    sql, args = "SELECT * FROM runs WHERE user_id = ?", [user["id"]]
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    if q:
        sql += " AND title LIKE ?"
        args.append(f"%{q.strip()[:60]}%")
    if starred:
        sql += " AND starred = 1"
    if before:
        sql += " AND updated_at < ?"
        args.append(before)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit + 1)
    with db.connect() as conn:
        rows = conn.execute(sql, args).fetchall()
        counts = {r["kind"]: r["n"] for r in conn.execute(
            "SELECT kind, COUNT(*) AS n FROM runs WHERE user_id = ? GROUP BY kind", (user["id"],))}
    return {"items": [_row(r) for r in rows[:limit]], "more": len(rows) > limit, "counts": counts}


@router.post("", status_code=201)
def create_run(body: RunIn, user=Depends(current_user)):
    if body.kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {', '.join(sorted(KINDS))}")
    payload, summary = _encode(body.payload, "payload"), _encode(body.summary, "summary")
    with db.connect() as conn:
        (n,) = conn.execute("SELECT COUNT(*) FROM runs WHERE user_id = ?", (user["id"],)).fetchone()
        if n >= MAX_ENTRIES:
            raise HTTPException(409, f"You have {MAX_ENTRIES} saved items. Delete some old ones to save more.")
        rid, t = db.new_id("run"), db.now()
        conn.execute("INSERT INTO runs (id, user_id, kind, sim_id, title, payload, summary, created_at, updated_at) "
                     "VALUES (?,?,?,?,?,?,?,?,?)", (rid, user["id"], body.kind, body.sim_id, body.title, payload, summary, t, t))
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (rid,)).fetchone()
    return _row(row)


def _get(conn, rid: str, uid: str):
    row = conn.execute("SELECT * FROM runs WHERE id = ? AND user_id = ?", (rid, uid)).fetchone()
    if row is None:
        raise HTTPException(404, "Not found in your history")
    return row


@router.get("/{rid}")
def get_run(rid: str, user=Depends(current_user)):
    with db.connect() as conn:
        return _row(_get(conn, rid, user["id"]), full=True)


@router.patch("/{rid}")
def update_run(rid: str, body: RunPatch, user=Depends(current_user)):
    sets, args = [], []
    if body.title is not None:
        sets.append("title = ?")
        args.append(body.title)
    if body.payload is not None:
        sets.append("payload = ?")
        args.append(_encode(body.payload, "payload"))
    if body.summary is not None:
        sets.append("summary = ?")
        args.append(_encode(body.summary, "summary"))
    if body.starred is not None:
        sets.append("starred = ?")
        args.append(int(body.starred))
    with db.connect() as conn:
        _get(conn, rid, user["id"])
        if sets:
            if body.payload is not None or body.summary is not None:
                sets.append("updated_at = ?")
                args.append(db.now())
            conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE id = ? AND user_id = ?", (*args, rid, user["id"]))
        return _row(_get(conn, rid, user["id"]))


@router.delete("/{rid}")
def delete_run(rid: str, user=Depends(current_user)):
    with db.connect() as conn:
        _get(conn, rid, user["id"])
        conn.execute("DELETE FROM runs WHERE id = ? AND user_id = ?", (rid, user["id"]))
    return {"ok": True}
