// Cloudflare Pages Function: username and password in front of /test (HTTP Basic auth).
// Set TEST_USERNAME and TEST_PASSWORD in the Pages project: Settings > Environment variables (as secrets).
// If they're missing, the test area stays closed.
const enc = new TextEncoder();

async function same(a, b) { // compare via SHA-256 so the time taken doesn't reveal the password
  const [x, y] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(a)), crypto.subtle.digest("SHA-256", enc.encode(b))]);
  const u = new Uint8Array(x), v = new Uint8Array(y);
  let diff = 0;
  for (let i = 0; i < u.length; i++) diff |= u[i] ^ v[i];
  return diff === 0;
}

export async function onRequest(context) {
  const { TEST_USERNAME: user, TEST_PASSWORD: pass } = context.env;
  if (!user || !pass) return new Response("The test area isn't set up yet.", { status: 503, headers: { "Cache-Control": "no-store" } });
  const header = context.request.headers.get("Authorization") || "";
  if (header.startsWith("Basic ")) {
    let decoded = "";
    try { decoded = atob(header.slice(6)); } catch { /* bad header */ }
    const i = decoded.indexOf(":");
    if (i > 0 && (await same(decoded.slice(0, i), user)) && (await same(decoded.slice(i + 1), pass))) {
      const res = await context.next();
      const out = new Response(res.body, res);
      out.headers.set("Cache-Control", "no-store");
      out.headers.set("X-Robots-Tag", "noindex, nofollow");
      return out;
    }
  }
  return new Response("Sign in to the Reality ASM test area.", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Reality ASM test area", charset="UTF-8"', "Cache-Control": "no-store" },
  });
}
