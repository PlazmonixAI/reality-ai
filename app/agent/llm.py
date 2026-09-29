"""OpenAI-compatible chat client (NVIDIA NIM, Groq or xAI) with multi-key pooling and rotation.

- Keys come from the provider's *_API_KEYS variable (comma-separated). Requests start from the next key in round-robin order.
- 429, 5xx, timeouts and network errors put that key on a cool-down (honouring Retry-After) and the request
  moves on to the next key, with exponential backoff once every key has been tried.
- 401/403 disable a key for the life of the process. Other 4xx errors are the caller's fault and are raised.
- Providers are configured in app/config.py (LLM_PROVIDER); all speak the OpenAI chat-completions API.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

import httpx

RETRYABLE = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """The LLM could not produce a response."""


class NoKeysError(LLMError):
    """No NIM API keys are configured (or all were rejected)."""


class NIMClient:
    def __init__(
        self,
        keys: list[str],
        base_url: str,
        model: str,
        *,
        timeout: float = 60.0,
        max_attempts: int | None = None,
        backoff: float = 0.5,
        max_backoff: float = 8.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        keys_env: str = "NIM_API_KEYS",
    ):
        self.keys_env = keys_env
        self.keys = [k for k in keys if k]
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_attempts = max_attempts or max(3, 2 * len(self.keys))
        self.backoff, self.max_backoff = backoff, max_backoff
        self._sleep, self._clock = sleep, clock
        self._http = httpx.Client(timeout=timeout, transport=transport)
        self._lock = threading.Lock()
        self._next = 0
        self._cooldown: dict[int, float] = {}  # key index → time when usable again
        self._disabled: set[int] = set()

    # -- key pool ---------------------------------------------------------------------------
    def _pick(self) -> tuple[int, float]:
        """Next usable key (round robin) and how long to wait before it is ready."""
        with self._lock:
            live = [i for i in range(len(self.keys)) if i not in self._disabled]
            if not live:
                raise NoKeysError(f"no usable API keys (set {self.keys_env}; rejected keys are disabled)")
            now = self._clock()
            order = [(self._next + j) % len(self.keys) for j in range(len(self.keys))]
            order = [i for i in order if i in live]
            ready = [i for i in order if self._cooldown.get(i, 0) <= now]
            chosen = ready[0] if ready else min(order, key=lambda i: self._cooldown.get(i, 0))
            self._next = (chosen + 1) % len(self.keys)
            return chosen, max(0.0, self._cooldown.get(chosen, 0) - now)

    def _cool(self, i: int, seconds: float) -> None:
        with self._lock:
            self._cooldown[i] = self._clock() + seconds

    def status(self) -> dict[str, Any]:
        now = self._clock()
        return {"keys": len(self.keys), "disabled": len(self._disabled),
                "cooling": sum(1 for i, t in self._cooldown.items() if t > now and i not in self._disabled)}

    # -- requests ---------------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = "auto",
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Return the assistant message dict ({role, content, tool_calls?}) of the first choice."""
        if not self.keys:
            raise NoKeysError(f"the AI representative is not configured: set {self.keys_env}")
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        last = "no attempt made"
        for attempt in range(self.max_attempts):
            i, wait = self._pick()
            if wait > 0:
                self._sleep(min(wait, self.max_backoff))
            try:
                r = self._http.post(f"{self.base_url}/chat/completions", json=payload,
                                    headers={"Authorization": f"Bearer {self.keys[i]}", "Accept": "application/json"})
            except httpx.HTTPError as exc:  # timeout, connection reset, DNS...
                last = f"network error: {exc.__class__.__name__}"
                self._cool(i, self._delay(attempt))
                continue
            if r.status_code == 200:
                try:
                    return r.json()["choices"][0]["message"]
                except (ValueError, KeyError, IndexError) as exc:
                    raise LLMError(f"unexpected LLM response: {exc}") from None
            if r.status_code in (401, 403):
                with self._lock:
                    self._disabled.add(i)
                last = f"key {i + 1} rejected ({r.status_code})"
                continue
            if r.status_code in RETRYABLE:
                last = f"HTTP {r.status_code}"
                self._cool(i, self._retry_after(r) or self._delay(attempt))
                continue
            raise LLMError(f"LLM request failed with HTTP {r.status_code}: {r.text[:300]}")
        raise LLMError(f"LLM request failed after {self.max_attempts} attempts ({last})")

    def _delay(self, attempt: int) -> float:
        return min(self.max_backoff, self.backoff * 2 ** (attempt // max(1, len(self.keys))))

    @staticmethod
    def _retry_after(r: httpx.Response) -> float | None:
        try:
            return max(0.0, float(r.headers.get("retry-after", "")))
        except ValueError:
            return None

    def close(self) -> None:
        self._http.close()


OpenAICompatibleClient = NIMClient  # the same client serves every configured provider
