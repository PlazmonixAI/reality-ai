import base64
import gzip
import hashlib
import hmac
import json
import logging
import math
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

import app.modules  # noqa: F401  (registers all tools)
from app.agent import representative
from app.agent.llm import LLMError, NIMClient, NoKeysError
from app.config import settings
from app.core import runner
from app.core.registry import get_tool, list_tools
from app.platform import admin, auth, company, challenges, db, history, teach, waitlist
from app.platform.auth import current_user, session_user
from app.platform.security import RateLimiter, check, sign

log = logging.getLogger("reality")

app = FastAPI(title="Reality ASM", version="0.9.0-beta",
              description="Reality ASM (Advanced Simulation Machine): physics, chemistry and mathematics simulations",
              docs_url="/docs" if settings.enable_api_docs else None, redoc_url=None,
              openapi_url="/openapi.json" if settings.enable_api_docs else None)

_PRECOMPRESSED = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".woff2", ".mp4", ".webm")


class CompressText:
    """gzip for JSON, HTML, JS and CSS; images and video are already compressed, so they pass straight through."""
    def __init__(self, app):
        self.app, self.gz = app, GZipMiddleware(app, minimum_size=1024, compresslevel=5)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not scope.get("path", "").lower().endswith(_PRECOMPRESSED):
            return await self.gz(scope, receive, send)
        return await self.app(scope, receive, send)


app.add_middleware(CompressText)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
SITE_DIR = FRONTEND_DIR / "site"

simulate_limit = RateLimiter(settings.simulate_rate_per_s, per=1.0, burst=settings.simulate_rate_per_s * 4)
ask_limit = RateLimiter(settings.ask_rate_per_min, per=60.0)


# ---------------------------------------------------------------- security middleware
def _importmap_hash() -> str:
    """CSP hashes for the inline import maps of the app and the ASM Teach app (three.js for 3D views)."""
    hashes = []
    for page in ("index.html", "teach.html"):
        try:
            html = (FRONTEND_DIR / page).read_text()
        except OSError:
            continue
        m = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
        if m:
            hashes.append("'sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode() + "'")
    return " ".join(hashes)


CSP = ("default-src 'self'; script-src 'self' " + _importmap_hash() + "; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob: https://gibs.earthdata.nasa.gov; font-src 'self'; connect-src 'self'; "
       "worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
       "form-action 'self' https://accounts.google.com")


def _gate_ok(request: Request) -> bool:
    """Private-testing gate: when TEST_GATE_USERNAME/PASSWORD are set, every page needs them (HTTP Basic)."""
    if not (settings.test_gate_username and settings.test_gate_password):
        return True
    if request.url.path in ("/health", "/api/waitlist"):
        return True
    header = request.headers.get("authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    return hmac.compare_digest(user, settings.test_gate_username) & hmac.compare_digest(pw, settings.test_gate_password)


@app.middleware("http")
async def security(request: Request, call_next):
    if not _gate_ok(request):
        return Response("Reality ASM is in private testing.", status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="Reality ASM testing", charset="UTF-8"'})
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path != "/api/waitlist":
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if origin and origin != "null" and re.sub(r"^https?://", "", origin) != host:
            return JSONResponse({"detail": "Cross-site request blocked"}, status_code=403)
    response = await call_next(request)
    h = response.headers
    h.setdefault("Content-Security-Policy", CSP)
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if settings.cookie_secure:
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.include_router(auth.router)
app.include_router(history.router)
app.include_router(company.router)
app.include_router(challenges.router)
app.include_router(admin.router)
app.include_router(waitlist.router)
app.include_router(teach.router)

try:  # the owner's account from OWNER_EMAIL / OWNER_PASSWORD, so it signs in without a sign-up
    auth.ensure_owner_account()
    teach.ensure_owner_school()
except HTTPException as e:
    log.warning("owner account not created: %s", e.detail)
except Exception:  # noqa: BLE001 (a broken database must not stop the app from starting; /health reports it)
    log.exception("owner account not created")


# ---------------------------------------------------------------- engine API (signed-in users only)
class SimulateRequest(BaseModel):
    domain: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    signature: str | None = None  # flight states come back signed; send the signature with the next step


def _database_state() -> str:
    try:
        with db.connect() as conn:
            conn.execute("SELECT 1 FROM users LIMIT 1").fetchall()
        return f"ok (temporary: {db.storage_note})" if db.storage_note else "ok"
    except Exception as e:  # noqa: BLE001 (reported, not raised: the engine still works without the database)
        return f"{type(e).__name__}: {str(e)[:160]}"


@app.api_route("/health", methods=["GET", "HEAD"])  # uptime monitors often send HEAD
def health():
    return {"status": "ok", "service": "reality-asm", "tools": len(list_tools()), "database": _database_state(),
            "owner_account": "set" if settings.owner_email and settings.owner_password else "not set"}


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": f"Server error ({type(exc).__name__}). The details are in the server log."}, status_code=500)


@app.get("/tools")
def tools(user=Depends(current_user)):
    grouped: dict[str, list[dict]] = {}
    for t in list_tools():
        grouped.setdefault(t.domain, []).append({"name": t.name, "description": t.description})
    return grouped


FLIGHT_TOOLS = {"physics.rocket_launch_state", "physics.rocket_flight"}

# Catalogue tools whose answer depends only on their arguments (no clock, no randomness without a fixed seed).
# Their results are large (1 to 2 MB of JSON), so each one is computed, encoded and gzipped once and kept.
CATALOGUE_TOOLS = {"physics.galaxy_catalog", "physics.milky_way", "physics.star_catalog", "physics.sky_atlas", "physics.cosmology",
                   "physics.asteroid_belt"}  # the belt sample is seeded; the map asks for it once per day
_catalogue_cache: dict[str, tuple[bytes, bytes]] = {}
_catalogue_lock = threading.Lock()
CATALOGUE_CACHE_SIZE = 24
CATALOGUE_CACHE_BYTES = 48 * 1024 * 1024  # memory budget for the cache (the free server has 512 MB)
CATALOGUE_MAX_ENTRY = 12 * 1024 * 1024  # a result bigger than this is sent but not kept


def _json_bytes(out: dict) -> bytes:
    """Encode a tool result straight to JSON. FastAPI's generic encoder walks every number first, which takes
    over a second for a few MB of results; tool results are plain lists and numbers, so json can do it directly."""
    try:
        return json.dumps(out, separators=(",", ":"), allow_nan=False).encode()
    except (TypeError, ValueError):  # numpy scalars, or NaN/infinity, which JSON cannot carry: send them as null
        return json.dumps(_finite(jsonable_encoder(out)), separators=(",", ":"), allow_nan=False).encode()


def _finite(x):
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_finite(v) for v in x]
    return x


def catalogue_response(domain: str, name: str, args: dict, accept_encoding: str) -> Response:
    key = f"{domain}.{name}:" + json.dumps(args, sort_keys=True, separators=(",", ":"))
    hit = _catalogue_cache.get(key)
    if hit is None:
        body = _json_bytes(run_tool(domain, name, args))
        hit = (body, gzip.compress(body, 6))
        if len(body) + len(hit[1]) <= CATALOGUE_MAX_ENTRY:
            with _catalogue_lock:
                _catalogue_cache.pop(key, None)
                size = lambda: sum(len(a) + len(b) for a, b in _catalogue_cache.values())  # noqa: E731
                while _catalogue_cache and (len(_catalogue_cache) >= CATALOGUE_CACHE_SIZE
                                            or size() + len(body) + len(hit[1]) > CATALOGUE_CACHE_BYTES):
                    _catalogue_cache.pop(next(iter(_catalogue_cache)))  # oldest first
                _catalogue_cache[key] = hit
    if "gzip" in accept_encoding:
        return Response(hit[1], media_type="application/json", headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
    return Response(hit[0], media_type="application/json")


# The Universe Map asks for these on every visit: prepare them while the server starts, off the request path
UNIVERSE_MAP_CALLS = [
    ("galaxy_catalog", {"max_distance_mly": 6000, "limit": 25000, "include_redshift": True}),
    ("milky_way", {"n_points": 40000}),
    ("star_catalog", {"max_magnitude": 6.5, "nearby_ly": 100, "frame": "ecliptic"}),
    ("sky_atlas", {"frame": "ecliptic"}),
    ("cosmology", {"z": 1}),
]


def _belt_call() -> tuple[str, dict]:  # same arguments as the Universe Map, for today (UTC)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00.000Z")
    return ("asteroid_belt", {"date": day, "n_main": 4500, "n_trojans": 1100, "n_kuiper": 2600, "n_hilda": 500, "n_nea": 260,
                              "n_scattered": 700, "n_oort": 2500, "samples_per_orbit": 16})


def warm_catalogues() -> None:
    for name, args in [_belt_call(), *UNIVERSE_MAP_CALLS]:
        try:
            catalogue_response("physics", name, args, "")
        except Exception:  # noqa: BLE001 (warming is best effort; a real request reports any error)
            log.exception("could not prepare %s", name)


def flight_seal(user_id: str, state: dict, args: dict) -> str:
    """Signature over a flight state and the rocket it belongs to, so challenges can trust a reported flight."""
    return sign("flight", {"u": user_id, "s": state, "p": args.get("parts"), "c": args.get("custom_parts") or {}})


def run_tool(domain: str, name: str, args: dict) -> dict:
    try:
        t = get_tool(domain, name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        return {"tool": t.key, **runner.run(t, args, timeout=settings.tool_timeout_s)}
    except runner.ToolInputError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001 - a bug in a tool: report it as JSON, not a bare 500 page
        log.exception("tool %s failed", t.key)
        raise HTTPException(status_code=500, detail=f"internal error in {t.key}: {e.__class__.__name__}")


@app.post("/simulate")
def simulate(req: SimulateRequest, request: Request, user=Depends(current_user)):
    if not simulate_limit.allow(user["id"]):
        raise HTTPException(429, "Too many engine calls at once. Slow down a little.")
    key = f"{req.domain}.{req.name}"
    if key in CATALOGUE_TOOLS:
        return catalogue_response(req.domain, req.name, req.args, request.headers.get("accept-encoding", ""))
    out = run_tool(req.domain, req.name, req.args)
    if key in FLIGHT_TOOLS and isinstance(out.get("result"), dict):
        # A launch starts a verified flight; each step stays verified only if it continues a verified state
        trusted = key == "physics.rocket_launch_state" or (
            isinstance(req.args.get("state"), dict) and check_flight(user["id"], req.args["state"], req.args, req.signature))
        state = out["result"] if key == "physics.rocket_launch_state" else out["result"].get("state")
        out["verified"] = bool(trusted)
        if trusted and isinstance(state, dict):
            out["signature"] = flight_seal(user["id"], state, req.args)
    return Response(_json_bytes(out), media_type="application/json")


def check_flight(user_id: str, state: dict, args: dict, signature: str | None) -> bool:
    return check("flight", {"u": user_id, "s": state, "p": args.get("parts"), "c": args.get("custom_parts") or {}}, signature)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)
    context: dict[str, Any] | None = None  # snapshot of the simulation on screen (sim id, title, recent engine calls)


_client: NIMClient | None = None


def get_llm_client() -> NIMClient:
    """One shared client so the key rotation state is kept across requests."""
    global _client
    if _client is None:
        _client = NIMClient(settings.key_list, settings.base_url, settings.model, keys_env=settings.keys_env)
    return _client


@app.get("/llm/status")
def llm_status(user=Depends(current_user)):
    """Whether the AI representative is configured (never the keys)."""
    try:
        return {"provider": settings.provider, "model": settings.model, "configured": bool(settings.key_list)}
    except ValueError as e:
        return {"provider": settings.llm_provider, "configured": False, "error": str(e)}


@app.post("/ask")
def ask(req: AskRequest, client=Depends(get_llm_client), user=Depends(current_user)):
    """Answer a research question in natural language using the engine's tools."""
    if not ask_limit.allow(user["id"]):
        raise HTTPException(429, "You're asking faster than the AI can keep up. Wait a moment and try again.")
    try:
        return representative.ask(req.question, client, history=req.history, context=req.context)
    except NoKeysError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------- public site
PAGES = {"": "index.html", "login": "login.html", "signup": "signup.html", "forgot": "forgot.html", "reset": "reset.html",
         "terms": "legal/terms.html", "privacy": "legal/privacy.html", "cookies": "legal/cookies.html",
         "acceptable-use": "legal/acceptable-use.html", "about": "about.html", "teach-terms": "legal/teach-terms.html"}


def _page(name: str) -> HTMLResponse:
    html = (SITE_DIR / PAGES[name]).read_text()
    html = html.replace("{{CONTACT_EMAIL}}", settings.contact_email).replace("{{TERMS_VERSION}}", auth.TERMS_VERSION)
    html = html.replace("{{TEACH_TERMS_VERSION}}", teach.TEACH_TERMS_VERSION)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse("/static/brand/favicon.svg", status_code=301)


@app.get("/", include_in_schema=False)
def landing():
    return _page("")


# ---------------------------------------------------------------- ASM Teach (its own sign-in and app, separate from ASM)
TEACH_CSP = CSP.replace("default-src 'self';", "default-src 'self'; frame-src 'self' https:; media-src 'self' blob:;")


@app.get("/teach", include_in_schema=False)
def teach_signin(request: Request):
    user = session_user(request.cookies.get(auth.COOKIE))
    if user is not None and teach._role(user["id"])[0] is not None:
        return RedirectResponse("/teach/app", status_code=302)
    html = (SITE_DIR / "teach.html").read_text().replace("{{CONTACT_EMAIL}}", settings.contact_email)
    return HTMLResponse(html.replace("{{TEACH_TERMS_VERSION}}", teach.TEACH_TERMS_VERSION), headers={"Cache-Control": "no-cache"})


@app.get("/teach/app", include_in_schema=False)
def teach_app(request: Request):
    user = session_user(request.cookies.get(auth.COOKIE))
    if user is None or teach._role(user["id"])[0] is None:
        return RedirectResponse("/teach", status_code=302)
    return FileResponse(FRONTEND_DIR / "teach.html", headers={"Cache-Control": "no-cache", "Content-Security-Policy": TEACH_CSP})


@app.get("/{page}", include_in_schema=False)
def site_page(page: str, request: Request):
    if page not in PAGES:
        raise HTTPException(404)
    if page in ("login", "signup") and session_user(request.cookies.get(auth.COOKIE)) is not None:
        return RedirectResponse("/app/", status_code=302)
    return _page(page)


if (SITE_DIR / "static").is_dir():
    app.mount("/static", StaticFiles(directory=SITE_DIR / "static"), name="static")


# ---------------------------------------------------------------- the app itself (signed-in users only)
@app.get("/app", include_in_schema=False)
def app_root():
    return RedirectResponse("/app/", status_code=301)


@app.get("/app/{path:path}", include_in_schema=False)
def app_files(path: str, request: Request):
    if session_user(request.cookies.get(auth.COOKIE)) is None:
        if path in ("", "index.html"):
            return RedirectResponse("/login?next=/app/", status_code=302)
        raise HTTPException(401, "Please sign in to continue.")
    target = (FRONTEND_DIR / (path or "index.html")).resolve()
    if target.is_dir():
        target = target / "index.html"
    if (FRONTEND_DIR not in target.parents) or SITE_DIR in target.parents or target == SITE_DIR or not target.is_file():
        raise HTTPException(404)
    heavy = "/assets/" in f"/{path}" or path.startswith("vendor/")
    return FileResponse(target, headers={"Cache-Control": "private, max-age=86400" if heavy else "no-cache"})


@app.exception_handler(404)
async def not_found(request: Request, exc):
    detail = getattr(exc, "detail", None) or "Not found"
    if request.method == "GET" and "text/html" in request.headers.get("accept", "") and (SITE_DIR / "404.html").is_file():
        return HTMLResponse((SITE_DIR / "404.html").read_text(), status_code=404)
    return JSONResponse({"detail": detail}, status_code=404)


threading.Thread(target=warm_catalogues, daemon=True, name="warm-catalogues").start()
