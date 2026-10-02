// Cloudflare Pages Function: keeps waitlist emails in a KV namespace bound as WAITLIST.
// Bind it in the Pages project: Settings > Bindings > KV namespace, variable name WAITLIST.
const EMAIL = /^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$/;

export async function onRequestPost({ request, env }) {
  if (!env.WAITLIST) return new Response("The waitlist isn't set up yet.", { status: 503 });
  let email = "", source = "";
  try {
    const form = await request.formData();
    email = String(form.get("email") || "").trim().toLowerCase();
    source = String(form.get("source") || "").slice(0, 120);
  } catch { /* not a form */ }
  if (!EMAIL.test(email)) return new Response("Kindly enter a valid email address.", { status: 422 });
  const key = `email:${email}`;
  if (!(await env.WAITLIST.get(key))) {
    const entry = { at: new Date().toISOString(), country: request.cf?.country || "", source };
    await env.WAITLIST.put(key, JSON.stringify({ email, ...entry }), { metadata: entry });  // metadata lets /test list without extra reads
  }
  return new Response("ok", { headers: { "Cache-Control": "no-store" } });
}

export const onRequest = () => new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
