"""Password hashing, session tokens, request signing and rate limiting (standard library only)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict

from app.platform.db import secret_key

# scrypt parameters (n=2^14, r=8, p=1: ~16 MB, a few tens of ms per hash)
_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return "scrypt${}${}${}${}${}".format(_N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    try:
        _, n, r, p, salt, dk = stored.split("$")
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                             dklen=len(base64.b64decode(dk)))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, base64.b64decode(dk))


# A hash computed once so that logins for unknown emails take as long as real ones
DUMMY_HASH = hash_password(secrets.token_hex(8))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sign(purpose: str, value) -> str:
    """HMAC of a JSON value, bound to a purpose so a signature for one thing can't be replayed as another."""
    return hmac.new(secret_key(), purpose.encode() + b"\x00" + canonical(value), hashlib.sha256).hexdigest()


def check(purpose: str, value, signature: str | None) -> bool:
    if not signature or not isinstance(signature, str):
        return False
    try:
        return hmac.compare_digest(sign(purpose, value), signature)
    except (TypeError, ValueError):
        return False


class RateLimiter:
    """Token bucket per key: `rate` requests per `per` seconds with a burst of `burst`."""

    def __init__(self, rate: float, per: float = 1.0, burst: float | None = None):
        self.rate = rate / per
        self.burst = burst if burst is not None else rate
        self._state: dict[str, tuple[float, float]] = defaultdict(lambda: (self.burst, time.monotonic()))
        self._lock = threading.Lock()

    def allow(self, key: str, cost: float = 1.0) -> bool:
        with self._lock:
            tokens, last = self._state[key]
            t = time.monotonic()
            tokens = min(self.burst, tokens + (t - last) * self.rate)
            ok = tokens >= cost
            self._state[key] = (tokens - cost if ok else tokens, t)
            if len(self._state) > 50_000:  # forget idle keys
                self._state.clear()
            return ok

    def reset(self) -> None:
        with self._lock:
            self._state.clear()
