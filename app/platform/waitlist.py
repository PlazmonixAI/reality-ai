"""Pre-launch waitlist: the Cloudflare site posts an email here (form-encoded or JSON) from an allowed origin."""
from __future__ import annotations

import json
import re
import urllib.parse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.platform import db
from app.platform.auth import EMAIL_RE, client_ip
from app.platform.security import RateLimiter

router = APIRouter(prefix="/api", tags=["waitlist"])
limit = RateLimiter(10, per=3600)


def cors_headers(request: Request) -> dict[str, str]:
    origin = (request.headers.get("origin") or "").rstrip("/")
    if origin and origin in settings.waitlist_origin_set:
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400", "Vary": "Origin"}
    return {}


@router.options("/waitlist", include_in_schema=False)
def waitlist_preflight(request: Request):
    return Response(status_code=204, headers=cors_headers(request))


@router.post("/waitlist", status_code=201)
async def join_waitlist(request: Request):
    headers = cors_headers(request)
    origin = request.headers.get("origin")
    host = request.headers.get("host", "")
    if origin and not headers and re.sub(r"^https?://", "", origin) != host:
        raise HTTPException(403, "This site can't add to the waitlist.")
    if not limit.allow(client_ip(request)):
        return JSONResponse({"detail": "Too many sign-ups from this network. Try again later."}, status_code=429, headers=headers)
    raw = (await request.body())[:2000].decode("utf-8", "replace")
    try:
        data = json.loads(raw) if "json" in request.headers.get("content-type", "") else dict(urllib.parse.parse_qsl(raw))
    except ValueError:
        data = {}
    email = str(data.get("email", "")).strip().lower()
    if not EMAIL_RE.match(email):
        return JSONResponse({"detail": "Kindly enter a valid email address."}, status_code=422, headers=headers)
    with db.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO waitlist (email, created_at, source) VALUES (?,?,?)",
                     (email, db.now(), str(data.get("source", ""))[:100]))
    return JSONResponse({"ok": True}, status_code=201, headers=headers)
