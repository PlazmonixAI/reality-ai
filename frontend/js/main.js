// App shell: gallery of simulations and a hash router (#/sim/<id>).
import { SIMS, DOMAINS } from "./sims/index.js";
import { el } from "./core/ui.js";
import { health } from "./core/api.js";
import { mountAsk } from "./ask.js";
import { mountAiPanel } from "./core/aichat.js";
import { clearRecentCalls } from "./core/api.js";

const app = document.getElementById("app");
const crumb = document.getElementById("crumb");
let cleanup = null;
let query = "";

async function route() {
  try { cleanup?.(); } catch (e) { console.error(e); }
  cleanup = null;
  app.replaceChildren();
  const m = location.hash.match(/^#\/sim\/([\w-]+)/);
  const sim = m && SIMS.find((s) => s.id === m[1]);
  if (sim) await openSim(sim);
  else if (location.hash.startsWith("#/ask")) { crumb.textContent = "/ Ask"; document.title = "Ask · Reality ASM"; mountAsk(app); }
  else renderGallery();
  window.scrollTo(0, 0);
}

function renderGallery() {
  crumb.textContent = "";
  document.title = "Reality ASM";
  const search = el("input", { class: "search", type: "search", placeholder: "Search simulations…", value: query, "aria-label": "Search simulations" });
  const sections = el("div");
  const draw = () => {
    const q = query.trim().toLowerCase();
    sections.replaceChildren();
    for (const d of DOMAINS) {
      const sims = SIMS.filter((s) => s.domain === d.id && (!q || `${s.title} ${s.blurb}`.toLowerCase().includes(q)));
      if (!sims.length) continue;
      sections.append(
        el("h2", { class: "domain-title" }, d.label, el("span", { class: "count" }, `${sims.length}`)),
        el("div", { class: "cards" }, sims.map((s) => el("a", { class: "card", href: `#/sim/${s.id}` },
          el("div", { class: "card-art", html: s.art }),
          el("div", { class: "card-body" }, el("h3", {}, s.title), el("p", {}, s.blurb))))),
      );
    }
    if (!sections.children.length) sections.append(el("p", { class: "empty" }, "No simulations match your search."));
  };
  search.addEventListener("input", () => { query = search.value; draw(); });
  draw();
  app.append(el("div", { class: "gallery" },
    el("div", { class: "hero" },
      el("h1", {}, "Interactive simulations"),
      el("p", {}, "Every number on screen is computed by the Reality ASM engine — real numerical and symbolic physics, chemistry and mathematics, animated in your browser.")),
    search, sections));
}

async function openSim(sim) {
  crumb.textContent = `/ ${sim.title}`;
  document.title = `${sim.title} · Reality ASM`;
  const page = el("div", { class: "sim-page" });
  app.append(page);
  try {
    clearRecentCalls();
    const mod = await sim.load();
    const simCleanup = mod.default.mount(page) || null;
    const aiCleanup = mountAiPanel(page, sim);
    cleanup = () => { aiCleanup(); simCleanup?.(); };
  } catch (err) {
    console.error(err);
    page.append(el("p", { class: "empty" }, `Could not load this simulation: ${err.message}`));
  }
}

async function checkEngine() {
  const badge = document.getElementById("api-status");
  const dot = badge.querySelector(".status-dot");
  try {
    const h = await health();
    dot.className = "status-dot ok";
    badge.lastChild.textContent = `engine · ${h.tools} tools`;
  } catch {
    dot.className = "status-dot down";
    badge.lastChild.textContent = "engine offline";
  }
}

window.addEventListener("hashchange", route);
route();
checkEngine();
