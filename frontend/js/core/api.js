// Client for the Reality ASM engine. All numbers shown by a simulation come from these calls.

export class EngineError extends Error {}

// The latest engine calls of the open simulation (compacted), so the AI analyst can see what is on screen.
const RECENT = [];
function compactValue(v, depth = 0) {
  if (typeof v === "number") return Number.isFinite(v) ? +v.toPrecision(6) : v;
  if (Array.isArray(v)) {
    if (v.length > 12) {
      const nums = v.filter((x) => typeof x === "number");
      if (nums.length === v.length) return { n: v.length, first: compactValue(v[0]), last: compactValue(v[v.length - 1]), min: compactValue(Math.min(...nums)), max: compactValue(Math.max(...nums)) };
      return [...v.slice(0, 4).map((x) => compactValue(x, depth + 1)), `… ${v.length - 4} more`];
    }
    return v.map((x) => compactValue(x, depth + 1));
  }
  if (v && typeof v === "object") {
    if (depth > 4) return "{…}";
    const out = {};
    for (const [k, x] of Object.entries(v)) if (k !== "image") out[k] = compactValue(x, depth + 1);
    return out;
  }
  if (typeof v === "string" && v.length > 300) return v.slice(0, 300) + "…";
  return v;
}
function remember(domain, name, args, data) {
  // Keep the newest call per tool (a sim may call the same tool many times a second)
  const i = RECENT.findIndex((c) => c.domain === domain && c.name === name);
  if (i >= 0) RECENT.splice(i, 1);
  const { tool, ...rest } = data;
  RECENT.push({ domain, name, args: compactValue(args), result: compactValue(rest), at: new Date().toISOString() });
  while (RECENT.length > 8) RECENT.shift();
}
export const recentCalls = () => RECENT.slice();
export const clearRecentCalls = () => { RECENT.length = 0; };

export async function simulate(domain, name, args = {}, signal, extra = {}) {
  let response;
  try {
    response = await fetch("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain, name, args, ...extra }),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new EngineError("Can't reach the Reality ASM engine. Check your connection and try again.");
  }
  if (response.status === 401) {
    location.href = location.pathname.startsWith("/teach") ? "/teach" : `/login?next=${encodeURIComponent("/app/" + location.hash)}`;
    throw new EngineError("Please sign in again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map((d) => d.msg).join("; ")
      : response.statusText;
    throw new EngineError(message);
  }
  try { remember(domain, name, args, data); } catch { /* never break a sim over bookkeeping */ }
  return data;
}

/**
 * Debounced, latest-wins request runner. Call the returned function whenever inputs change;
 * only the newest request's result is delivered, older in-flight requests are aborted.
 */
export function liveRequest(compute, { onResult, onError, onBusy, delay = 120 } = {}) {
  let timer = null;
  let controller = null;
  let seq = 0;
  const run = () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      controller?.abort();
      controller = new AbortController();
      const mine = ++seq;
      onBusy?.(true);
      try {
        const result = await compute(controller.signal);
        if (mine === seq) onResult?.(result);
      } catch (err) {
        if (err.name !== "AbortError" && mine === seq) onError?.(err);
      } finally {
        if (mine === seq) onBusy?.(false);
      }
    }, delay);
  };
  run.cancel = () => { clearTimeout(timer); controller?.abort(); };
  return run;
}

export async function health() {
  const r = await fetch("/health");
  if (!r.ok) throw new Error("unhealthy");
  return r.json();
}
