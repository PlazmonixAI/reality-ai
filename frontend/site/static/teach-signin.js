// ASM Teach sign-in: choose schools or private institutions, then school admin (username or Google) or teacher.
const $ = (s, r = document) => r.querySelector(s);
const msg = $("[data-msg]");
const say = (text, ok = false) => { msg.textContent = text || ""; msg.className = `msg${text ? (ok ? " show ok" : " show error") : ""}`; };

async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), credentials: "same-origin" });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.");
  return data;
}

function show(step) {
  document.querySelectorAll("[data-step]").forEach((s) => { s.hidden = s.dataset.step !== step; });
  const first = $(`[data-step="${step}"] input`);
  if (first) setTimeout(() => first.focus(), 30);
}

function route() {
  say("");
  const params = new URLSearchParams(location.search);
  if (params.get("step") === "setup" && !location.hash) return setup();
  const step = location.hash.replace("#", "") || "choose";
  show(["choose", "school", "admin", "signup", "teacher"].includes(step) ? step : "choose");
}

async function setup() {
  show("setup");
  try {
    const r = await fetch("/api/teach/google/pending", { credentials: "same-origin" });
    if (!r.ok) throw new Error();
    const g = await r.json();
    $("[data-google-email]").textContent = g.email;
    const f = $("[data-teach-setup]");
    if (g.name && !f.school_name.value) f.school_name.value = g.name;
  } catch {
    history.replaceState(null, "", "/teach#signup");
    route();
    say("Your Google check has expired. Continue with Google again.");
  }
}

// Google is optional on a server; hide the buttons when it is not set up
fetch("/api/auth/config").then((r) => r.json()).then((c) => {
  if (!c.google) {
    document.querySelectorAll("[data-google-teach]").forEach((a) => { a.hidden = true; });
    document.querySelectorAll(".divider").forEach((d) => { d.hidden = true; });
    $("[data-google-off]").hidden = false;
  }
}).catch(() => {});

document.querySelectorAll("[data-teach-login]").forEach((form) => form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = form.querySelector("button[type=submit]");
  if (!form.username.value.trim() || !form.password.value) { say("Enter your username and password."); return; }
  btn.disabled = true; say("");
  try {
    const r = await post("/api/teach/login", { username: form.username.value.trim(), password: form.password.value,
      role: form.dataset.teachLogin, remember: form.remember.checked });
    location.assign(r.next);
  } catch (err) { say(err.message); btn.disabled = false; }
}));

const setupForm = $("[data-teach-setup]");
const agree = setupForm.accept_terms, create = setupForm.querySelector("button[type=submit]");
agree.addEventListener("change", () => { create.disabled = !agree.checked; });
setupForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = setupForm;
  if (!agree.checked) { say("Please agree to the ASM Teach Terms and Privacy Policy first."); return; }
  if (f.password.value !== f.confirm.value) { say("The two passwords don't match."); return; }
  create.disabled = true; say("");
  try {
    const r = await post("/api/teach/school/signup", { school_name: f.school_name.value, city: f.city.value, username: f.username.value,
      password: f.password.value, accept_terms: true });
    location.assign(r.next);
  } catch (err) { say(err.message); create.disabled = false; }
});

if (new URLSearchParams(location.search).get("error") === "google") {
  history.replaceState(null, "", "/teach#admin");
  setTimeout(() => say("Google sign-in did not finish. Please try again."), 0);
}
window.addEventListener("hashchange", route);
route();
