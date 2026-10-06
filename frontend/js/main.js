// App shell: navigation, account menu and a hash router.
//   #/                 home dashboard            #/sims            all simulations
//   #/sim/<id>?…       one simulation            #/company         Mission Control (space company)
//   #/challenges       challenge missions        #/history         saved work
//   #/account          account settings          #/ask             ask the AI
import { SIMS } from "./sims/index.js";
import { simGallery, mountSim } from "./pages/simgallery.js";
import { el } from "./core/ui.js";
import { health, recentCalls } from "./core/api.js";
import { mountAsk } from "./ask.js";
import { currentUser, signOut, history, toast, feedbackBox } from "./core/session.js";

const app = document.getElementById("app");
const crumb = document.getElementById("crumb");
let cleanup = null;

const PAGES = {
  home: () => import("./pages/home.js"),
  company: () => import("./pages/company.js"),
  challenges: () => import("./pages/challenges.js"),
  history: () => import("./pages/history.js"),
  account: () => import("./pages/account.js"),
  admin: () => import("./pages/admin.js"),
};

export function parseHash() {
  const [path, qs = ""] = location.hash.replace(/^#/, "").split("?");
  return { path: path || "/", params: Object.fromEntries(new URLSearchParams(qs)) };
}

// Phones: the main menu folds behind a button and closes after each choice
const navToggle = document.getElementById("nav-toggle"), nav = document.getElementById("app-nav");
navToggle?.addEventListener("click", () => { const open = !document.body.classList.contains("nav-open"); document.body.classList.toggle("nav-open", open); navToggle.setAttribute("aria-expanded", String(open)); });
nav?.addEventListener("click", (e) => { if (e.target.closest("a")) { document.body.classList.remove("nav-open"); navToggle?.setAttribute("aria-expanded", "false"); } });

function setActive(route) {
  document.querySelectorAll("#app-nav a").forEach((a) => a.classList.toggle("on", a.dataset.route === route));
}

async function route() {
  document.body.classList.remove("nav-open");
  try { cleanup?.(); } catch (e) { console.error(e); }
  cleanup = null;
  app.replaceChildren();
  const { path, params } = parseHash();
  const simMatch = path.match(/^\/sim\/([\w-]+)/);
  const sim = simMatch && SIMS.find((s) => s.id === simMatch[1]);
  crumb.textContent = "";
  if (sim) { setActive(["spaceflight", "solarsystem"].includes(sim.id) ? sim.id : sim.id === "universe" ? "solarsystem" : "sims"); await openSim(sim, params); }
  else if (path.startsWith("/ask")) { setActive("ask"); crumb.textContent = ""; document.title = "Ask AI · Reality ASM"; mountAsk(app, params); }
  else if (path.startsWith("/sims")) { setActive("sims"); renderGallery(); }
  else {
    const name = path.replace(/^\//, "").split("/")[0] || "home";
    const load = PAGES[name] || PAGES.home;
    setActive(name === "company" ? "spaceflight" : PAGES[name] ? name : "home");  // Mission Control lives inside the Space Program
    const page = el("div", { class: "page" });
    app.append(page);
    try {
      const mod = await load();
      document.title = `${mod.default.title || "Home"} · Reality ASM`;
      cleanup = mod.default.mount(page, params) || null;
    } catch (err) {
      console.error(err);
      page.append(el("p", { class: "empty" }, `Could not open this page: ${err.message}`));
    }
  }
  window.scrollTo(0, 0);
}

function renderGallery() {
  document.title = "Simulations · Reality ASM";
  simGallery(app, { intro: "Every number on screen is computed by the Reality ASM engine: real numerical and symbolic physics, chemistry and maths, animated in your browser." });
}

async function openSim(sim, params) {
  crumb.textContent = sim.title;
  document.title = `${sim.title} · Reality ASM`;
  const page = el("div", { class: "sim-page" });
  app.append(page);
  try {
    const simCleanup = await mountSim(page, sim, params);
    const saveCleanup = ["spaceflight", "solarsystem"].includes(sim.id) ? () => {} : mountSnapshot(page, sim, params); // those two save their own state
    cleanup = () => { saveCleanup(); simCleanup(); };
  } catch (err) {
    console.error(err);
    page.append(el("p", { class: "empty" }, `Could not load this simulation: ${err.message}`));
  }
}

// "Save to history" for any simulation: stores the engine calls on screen (inputs and results), and shows a saved
// snapshot again when opened from the history.
function mountSnapshot(page, sim, params) {
  const btn = el("button", { class: "save-tab", type: "button", title: "Save what's on screen to your history" }, "Save");
  btn.addEventListener("click", async () => {
    const calls = recentCalls();
    if (!calls.length) { toast("Run the simulation first; there's nothing computed to save yet."); return; }
    btn.disabled = true;
    try {
      const inputs = calls.map((c) => c.args);
      await history.create({ kind: "sim", sim_id: sim.id, title: `${sim.title}, ${new Date().toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}`,
        payload: { calls }, summary: { tools: calls.map((c) => c.name), inputs: inputs.slice(-1)[0] || {} } });
      toast("Saved to your history.");
    } catch (e) { toast(e.message, "error"); } finally { btn.disabled = false; }
  });
  page.append(btn);
  let panel = null;
  if (params.snapshot) {
    history.get(params.snapshot).then((run) => {
      panel = el("aside", { class: "snapshot" },
        el("div", { class: "snapshot-head" }, el("b", {}, "Saved snapshot"), el("small", {}, new Date(run.created_at * 1000).toLocaleString()),
          el("button", { class: "ai-x", type: "button", "aria-label": "Close snapshot", onclick: () => panel.remove() }, "×")),
        el("p", { class: "note" }, "The inputs and results the engine computed when you saved this. Set the same inputs to run it again."),
        ...(run.payload.calls || []).map((c) => el("details", { class: "tool-card", open: true },
          el("summary", {}, c.name.replace(/_/g, " ")),
          el("pre", { class: "snap-pre" }, `inputs  ${JSON.stringify(c.args, null, 1).slice(0, 1200)}\nresult  ${JSON.stringify(c.result, null, 1).slice(0, 1600)}`))));
      page.append(panel);
    }).catch((e) => toast(e.message, "error"));
  }
  return () => { btn.remove(); panel?.remove(); };
}

async function account() {
  const box = document.getElementById("account");
  try {
    const user = await currentUser();
    const initials = user.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
    const menu = el("div", { class: "account-menu", role: "menu" },
      el("div", { class: "account-who" }, el("b", {}, user.name), el("small", {}, user.email)),
      el("a", { href: "#/account", role: "menuitem" }, "Account settings"),
      el("a", { href: "#/history", role: "menuitem" }, "My history"),
      el("button", { type: "button", role: "menuitem", onclick: () => feedbackBox() }, "Send feedback"),
      user.admin ? el("a", { href: "#/admin", role: "menuitem" }, "Beta admin") : "",
      el("a", { href: "/terms", target: "_blank", role: "menuitem" }, "Terms and privacy"),
      el("button", { type: "button", role: "menuitem", onclick: () => signOut() }, "Sign out"));
    const btn = el("button", { class: "avatar", type: "button", "aria-haspopup": "menu", "aria-label": `Account: ${user.name}` }, initials);
    btn.addEventListener("click", (e) => { e.stopPropagation(); box.classList.toggle("open"); });
    document.addEventListener("click", () => box.classList.remove("open"));
    menu.addEventListener("click", (e) => { if (e.target.closest("a,button")) box.classList.remove("open"); });
    box.replaceChildren(btn, menu);
  } catch { /* api() already redirects to sign-in */ }
}

async function checkEngine() {
  const badge = document.getElementById("api-status");
  const dot = badge.querySelector(".status-dot");
  try {
    const h = await health();
    dot.className = "status-dot ok";
    badge.lastChild.textContent = `${h.tools} tools`;
  } catch {
    dot.className = "status-dot down";
    badge.lastChild.textContent = "engine offline";
  }
}

window.addEventListener("hashchange", route);
account();
route();
checkEngine();
