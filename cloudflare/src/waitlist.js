// Pre-launch waitlist. The endpoint comes from waitlist_endpoint in cloudflare/site.config.json: "/api/waitlist"
// stores emails in Cloudflare KV (functions/api/waitlist.js); empty makes the form a placeholder that stores nothing.
const ENDPOINT = "__WAITLIST_ENDPOINT__";
const BETA_OPENS = "__BETA_OPENS__", LAUNCH = "__LAUNCH__", APP = "__APP_URL__", BETA_DAY = "__BETA_DAY__";
const EMAIL = /^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$/;

document.querySelectorAll("form[data-waitlist]").forEach((form) => {
  const input = form.querySelector("input[type=email]");
  const msg = form.querySelector(".wl-msg");
  const btn = form.querySelector("button");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = input.value.trim();
    if (!EMAIL.test(email)) { msg.textContent = "Kindly enter a valid email address."; msg.className = "wl-msg error"; input.focus(); return; }
    btn.disabled = true;
    try {
      if (ENDPOINT) {
        const body = new URLSearchParams({ email, source: location.pathname });
        const r = await fetch(ENDPOINT, { method: "POST", body });
        if (!r.ok) throw new Error();
      }
      form.classList.add("done");
      msg.textContent = BETA_DAY ? `Thank you. We'll email you on ${BETA_DAY}, when the public beta opens.` : "Thank you. We'll email you when the public beta opens.";
      msg.className = "wl-msg ok";
      input.value = "";
    } catch {
      msg.textContent = "That didn't go through. Please try again in a moment.";
      msg.className = "wl-msg error";
    } finally { btn.disabled = false; }
  });
});

// The page changes by itself on the dates in site.config.json: on beta day every "Join" button leads to sign-up in the
// app, and on launch day the words change from "beta" to "get started". Nothing needs to be rebuilt on the day.
(function phase() {
  const now = Date.now(), at = (iso) => (iso && !iso.startsWith("__") ? Date.parse(iso) : NaN);
  const open = at(BETA_OPENS) <= now, live = at(LAUNCH) <= now;
  // the dates section: what is coming, what is open now
  const tag = (key, text, cls) => document.querySelectorAll(`[data-when="${key}"]`).forEach((e) => { e.textContent = text; e.classList.add(cls); });
  if (live) { tag("beta", "Ran 20 Oct to 3 Nov", "done"); tag("launch", "Open now", "open"); }
  else if (open) tag("beta", "Open now", "open");
  if (!APP || APP.startsWith("__") || !(open || live)) return;
  const signup = `${APP}/signup`, cta = live ? "Get started" : "Join the beta";
  const set = (key, text) => document.querySelectorAll(`[data-phase="${key}"]`).forEach((e) => { e.textContent = text; });
  document.querySelectorAll('a[href="#waitlist"]').forEach((a) => {
    a.href = signup;
    if (a.classList.contains("btn")) a.textContent = cta;
  });
  set("eyebrow", live ? "Now open to everyone" : "Public beta");
  set("note", live ? "Free to start. Works in any modern browser, no install." : "The public beta is open and free while we test. Works in any modern browser, no install.");
  set("title", live ? "Get started" : "Join the beta");
  set("sub", live ? "Make a free account and open the universe, the labs and the space program in your browser."
    : "It's free while we test. Tell us what breaks, what's confusing and what you want next.");
  set("cs-title", live ? "This page is not here, but Reality ASM is." : "This page is not here, but the public beta is open.");
  set("cs-lede", "Make a free account and start in the app.");
  set("dates-note", live ? "Reality ASM is open to everyone. Make a free account and start." : "The beta is open now. Make a free account and start.");
  document.querySelectorAll('a[href="/#waitlist"]').forEach((a) => a.remove()); // the form below becomes the button
  document.querySelectorAll("form[data-waitlist]").forEach((form) => {
    const go = document.createElement("a");
    go.className = "btn btn-primary"; go.href = signup; go.textContent = cta;
    form.replaceWith(go);
  });
})();
