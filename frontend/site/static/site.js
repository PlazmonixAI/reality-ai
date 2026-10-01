// Public site: cookie notice, signed-in state in the nav, and the account forms.
const $ = (s, r = document) => r.querySelector(s);

async function api(path, body, method = "POST") {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined, credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg.replace(/^Value error, /, "")).join(" ") : "Something went wrong. Try again.");
  }
  return data;
}

function nextUrl() {
  const n = new URLSearchParams(location.search).get("next") || "/app/";
  return n.startsWith("/") && !n.startsWith("//") ? n : "/app/";
}

function show(el, text, kind = "error") {
  el.textContent = text;
  el.className = `msg show ${kind}`;
}

// ---- cookie notice (we only set an essential session cookie, so this informs rather than asks)
(function cookieNotice() {
  let seen = false;
  try { seen = localStorage.getItem("rasm.cookie-notice") === "1"; } catch { seen = true; }
  if (seen) return;
  const box = document.createElement("div");
  box.className = "cookie show";
  box.setAttribute("role", "region");
  box.setAttribute("aria-label", "Cookie notice");
  box.innerHTML = `<p>We use one essential cookie to keep you signed in, and nothing for ads or tracking. <a href="/cookies">Cookie policy</a></p>
    <div class="row"><button class="btn btn-primary" type="button">Got it</button></div>`;
  box.querySelector("button").addEventListener("click", () => { try { localStorage.setItem("rasm.cookie-notice", "1"); } catch { /* private mode */ } box.remove(); });
  document.body.append(box);
})();

// ---- nav: swap "Sign in / Join" for "Open the app" when signed in
(async function navState() {
  const slot = $("[data-auth-slot]");
  if (!slot) return;
  try {
    const r = await fetch("/api/auth/session", { credentials: "same-origin" });
    const { user } = r.ok ? await r.json() : {};
    if (user) {
      slot.innerHTML = "";
      const a = document.createElement("a");
      a.className = "btn btn-primary";
      a.href = "/app/";
      a.textContent = `Open the app`;
      a.title = `Signed in as ${user.email}`;
      slot.append(a);
      document.querySelectorAll("[data-signed-out]").forEach((n) => { n.hidden = true; });
      document.querySelectorAll("[data-signed-in]").forEach((n) => { n.hidden = false; });
    }
  } catch { /* offline: keep the default buttons */ }
})();

// ---- forms
async function authConfig() {
  try { return await (await fetch("/api/auth/config")).json(); } catch { return {}; }
}

const forms = {
  async login(form, msg) {
    const f = new FormData(form);
    await api("/api/auth/login", { email: f.get("email"), password: f.get("password"), remember: f.get("remember") === "on" });
    location.href = nextUrl();
  },
  async signup(form, msg) {
    const f = new FormData(form);
    if (String(f.get("password")) !== String(f.get("confirm"))) throw new Error("The two passwords don't match.");
    await api("/api/auth/signup", { name: f.get("name"), email: f.get("email"), password: f.get("password"),
      accept_terms: f.get("terms") === "on", invite_code: f.get("invite") || "" });
    location.href = nextUrl();
  },
  async forgot(form, msg) {
    const f = new FormData(form);
    const r = await api("/api/auth/forgot", { email: f.get("email") });
    const cfg = await authConfig();
    form.reset();
    show(msg, r.email_enabled
      ? "If that email has an account, a reset link is on its way. It works for one hour."
      : `Password reset by email isn't switched on yet during the beta. Write to ${cfg.contact_email || "us"} from the address you signed up with and we'll help you get back in.`, "info");
  },
  async reset(form, msg) {
    const f = new FormData(form);
    if (String(f.get("password")) !== String(f.get("confirm"))) throw new Error("The two passwords don't match.");
    const token = new URLSearchParams(location.search).get("token") || "";
    await api("/api/auth/reset", { token, password: f.get("password") });
    location.href = "/app/";
  },
};

document.querySelectorAll("form[data-form]").forEach((form) => {
  const msg = form.querySelector(".msg");
  const btn = form.querySelector("button[type=submit]");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    msg.className = "msg";
    btn.disabled = true;
    const label = btn.textContent;
    btn.textContent = "Please wait…";
    try { await forms[form.dataset.form](form, msg); }
    catch (err) { show(msg, err.message); }
    finally { btn.disabled = false; btn.textContent = label; }
  });
});

(async function authExtras() {
  if (!$("form[data-form]")) return;
  const cfg = await authConfig();
  if (cfg.google) document.querySelectorAll("[data-google]").forEach((n) => { n.hidden = false; n.href = `/api/auth/google/start?next=${encodeURIComponent(nextUrl())}`; });
  if (cfg.invite_required) document.querySelectorAll("[data-invite]").forEach((n) => { n.hidden = false; n.querySelector("input").required = true; });
  const err = new URLSearchParams(location.search).get("error");
  const msg = $("form[data-form] .msg");
  if (err === "google" && msg) show(msg, "Google sign-in didn't complete. Try again, or use your email and password.");
  if (err === "invite" && msg) show(msg, "The beta is invite-only right now. Sign up with an invite code first.");
})();
