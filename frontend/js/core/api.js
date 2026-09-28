// Client for the Reality AI engine. All numbers shown by a simulation come from these calls.

export class EngineError extends Error {}

export async function simulate(domain, name, args = {}, signal) {
  let response;
  try {
    response = await fetch("simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain, name, args }),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new EngineError("Cannot reach the Reality AI engine. Is the server running?");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map((d) => d.msg).join("; ")
      : response.statusText;
    throw new EngineError(message);
  }
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
  const r = await fetch("health");
  if (!r.ok) throw new Error("unhealthy");
  return r.json();
}
