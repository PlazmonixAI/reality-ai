"""Admin page for the beta: sign-ups, activity and feedback. Only for emails listed in ADMIN_EMAILS."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.platform import db
from app.platform.auth import current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


def admin_user(user=Depends(current_user)):
    if user["email"].lower() not in settings.admins:
        raise HTTPException(403, "This page is for the Reality ASM team.")
    return user


@router.get("/overview")
def overview(user=Depends(admin_user)):
    now = time.time()
    with db.connect() as conn:
        one = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
        stats = {
            "users": one("SELECT COUNT(*) FROM users"),
            "users_7d": one("SELECT COUNT(*) FROM users WHERE created_at > ?", now - 7 * 86400),
            "active_24h": one("SELECT COUNT(*) FROM users WHERE last_login_at > ?", now - 86400),
            "saved_items": one("SELECT COUNT(*) FROM runs"),
            "flights": one("SELECT COUNT(*) FROM runs WHERE kind = 'flight'"),
            "companies": one("SELECT COUNT(*) FROM companies"),
            "spacecraft": one("SELECT COUNT(*) FROM spacecraft"),
            "photos": one("SELECT COUNT(*) FROM photos"),
            "challenges_done": one("SELECT COUNT(*) FROM challenge_progress"),
            "feedback": one("SELECT COUNT(*) FROM feedback"),
            "waitlist": one("SELECT COUNT(*) FROM waitlist"),
        }
        recent = [dict(r) for r in conn.execute(
            "SELECT name, email, created_at, last_login_at FROM users ORDER BY created_at DESC LIMIT 50")]
        feedback = [dict(r) for r in conn.execute(
            "SELECT f.created_at, f.page, f.message, f.user_agent, u.name, u.email FROM feedback f "
            "LEFT JOIN users u ON u.id = f.user_id ORDER BY f.created_at DESC LIMIT 200")]
        challenges = [dict(r) for r in conn.execute(
            "SELECT challenge_id, COUNT(*) AS n FROM challenge_progress GROUP BY challenge_id ORDER BY n DESC")]
        waiting = [dict(r) for r in conn.execute("SELECT email, created_at, source FROM waitlist ORDER BY created_at DESC")]
    return {"stats": stats, "recent_users": recent, "feedback": feedback, "challenges": challenges, "waitlist": waiting}
