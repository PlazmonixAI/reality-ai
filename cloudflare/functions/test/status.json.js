// Team status for the /test page: waitlist numbers and whether the Render backend answers. Lives under /test, so the
// same username and password protect it. The backend address comes from /test/config.json (written by the build from
// beta_app_url in cloudflare/site.config.json).
const json = (body) => new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });

async function waitlist(kv) {
  if (!kv) return { bound: false };
  const rows = [];
  let cursor;
  do {
    const page = await kv.list({ prefix: "email:", cursor });
    rows.push(...page.keys);
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  // newer entries carry their details as key metadata; older ones are read one by one (at most 50)
  let reads = 0;
  const people = await Promise.all(rows.map(async (k) => {
    if (k.metadata) return { email: k.name.slice(6), ...k.metadata };
    if (reads++ >= 50) return { email: k.name.slice(6) };
    return { email: k.name.slice(6), ...JSON.parse((await kv.get(k.name)) || "{}") };
  }));
  people.sort((a, b) => String(b.at || "").localeCompare(String(a.at || "")));
  const day = Date.now() - 864e5, week = Date.now() - 7 * 864e5;
  const since = (t) => people.filter((p) => p.at && Date.parse(p.at) >= t).length;
  return { bound: true, count: people.length, last_24h: since(day), last_7d: since(week),
           latest: people.slice(0, 10).map(({ email, at, country, source }) => ({ email, at: at || "", country: country || "", source: source || "" })) };
}

async function backend(url) {
  if (!url) return { configured: false };
  const t0 = Date.now();
  try {
    const res = await fetch(new URL("/health", url), { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(8000) });
    const body = res.ok ? await res.json().catch(() => ({})) : {};
    return { configured: true, url, ok: res.ok && body.status === "ok", status: res.status, tools: body.tools ?? null, ms: Date.now() - t0 };
  } catch (err) {
    return { configured: true, url, ok: false, error: String(err && err.name === "TimeoutError" ? "No answer in 8 s (Render may be waking up)" : err), ms: Date.now() - t0 };
  }
}

export async function onRequestGet({ request, env }) {
  let cfg = {};
  try {
    const res = env.ASSETS ? await env.ASSETS.fetch(new URL("/test/config.json", request.url)) : null;
    if (res && res.ok) cfg = await res.json();
  } catch { /* no config */ }
  const [w, b] = await Promise.all([waitlist(env.WAITLIST), backend(cfg.beta_app_url)]);
  return json({ checked_at: new Date().toISOString(), waitlist: w, backend: b });
}
