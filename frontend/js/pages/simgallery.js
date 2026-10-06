// The simulations gallery, shared by Reality ASM and ASM Teach: Physics, Chemistry and Mathematics at the top,
// the physics topics underneath, the most powerful simulations first, and search.
import { SIMS, DOMAINS, SUBJECTS, sectionOf, FEATURED, rankOf } from "../sims/index.js";
import { el } from "../core/ui.js";
import { mountAiPanel } from "../core/aichat.js";
import { clearRecentCalls } from "../core/api.js";
import { playerKeys } from "../core/player.js";

let query = "";
const store = (k, v) => { try { if (v === undefined) return sessionStorage.getItem(k) || ""; sessionStorage.setItem(k, v); } catch { /* private mode */ } return v ?? ""; };
const visible = () => SIMS.filter((s) => !s.hidden);
const inSubject = (s, subj) => subj.shelves.includes(sectionOf(s));

/** Render the gallery into root. href(id) gives each card's link; intro is the line under the title. */
export function simGallery(root, { href = (id) => `#/sim/${id}`, intro = "" } = {}) {
  let subject = store("sims.subject"), shelf = store("sims.shelf");
  if (!SUBJECTS.some((s) => s.id === subject)) subject = "";
  const search = el("input", { class: "search", type: "search", placeholder: "Search simulations", value: query, "aria-label": "Search simulations" });
  const tabs = el("div", { class: "subject-tabs", role: "tablist", "aria-label": "Subjects" });
  const shelves = el("div", { class: "shelf-tabs", role: "tablist", "aria-label": "Topics" });
  const sections = el("div");
  const card = (s) => el("a", { class: "card", href: href(s.id) },
    el("div", { class: "card-art", html: s.art }),
    el("div", { class: "card-body" }, el("h3", {}, s.title), el("p", {}, s.blurb)));
  const tab = (id, label, n) => el("button", { type: "button", role: "tab", class: `subject-tab${subject === id ? " on" : ""}`, "aria-selected": String(subject === id),
    onclick: () => { subject = id; shelf = ""; store("sims.subject", id); store("sims.shelf", ""); draw(); } }, label, el("span", { class: "count" }, String(n)));

  function draw() {
    tabs.replaceChildren(tab("", "All", visible().length), ...SUBJECTS.map((s) => tab(s.id, s.label, visible().filter((x) => inSubject(x, s)).length)));
    const subj = SUBJECTS.find((s) => s.id === subject);
    shelves.hidden = !subj || subj.shelves.length < 2;
    if (subj && subj.shelves.length > 1) {
      shelves.replaceChildren(...[{ id: "", label: `All ${subj.label.toLowerCase()}` }, ...DOMAINS.filter((d) => subj.shelves.includes(d.id))].map((d) =>
        el("button", { type: "button", role: "tab", class: `chip${shelf === d.id ? " on" : ""}`, "aria-selected": String(shelf === d.id),
          onclick: () => { shelf = d.id; store("sims.shelf", d.id); draw(); } },
          d.label, el("span", { class: "count" }, String(d.id ? visible().filter((s) => sectionOf(s) === d.id).length : visible().filter((s) => inSubject(s, subj)).length)))));
    }
    const q = query.trim().toLowerCase();
    const match = (s) => !q || `${s.title} ${s.blurb}`.toLowerCase().includes(q);
    sections.replaceChildren();
    if (!subject && !q) {  // the most powerful simulations first, from every subject
      const top = FEATURED.map((id) => SIMS.find((s) => s.id === id)).filter(Boolean);
      sections.append(el("h2", { class: "domain-title featured-title" }, "Most powerful", el("span", { class: "count" }, `${top.length}`)),
        el("p", { class: "muted small featured-note" }, "The Universe Map, space flight, quantum physics, chemistry and mathematics: the deepest simulations first."),
        el("div", { class: "cards featured" }, top.map(card)));
    }
    for (const subj of SUBJECTS) {
      if (subject && subject !== subj.id) continue;
      const block = [];
      for (const d of DOMAINS.filter((x) => subj.shelves.includes(x.id))) {
        if (shelf && shelf !== d.id) continue;
        const sims = visible().filter((s) => sectionOf(s) === d.id && match(s)).sort((x, y) => rankOf(x) - rankOf(y));
        if (!sims.length) continue;
        if (subj.shelves.length > 1) block.push(el("h3", { class: "shelf-title" }, d.label, el("span", { class: "count" }, `${sims.length}`)));
        block.push(el("div", { class: "cards" }, sims.map(card)));
      }
      if (!block.length) continue;
      sections.append(el("h2", { class: "domain-title subject-title" }, subj.label), ...block);
    }
    if (!sections.children.length) sections.append(el("p", { class: "empty" }, "No simulations match your search."));
  }
  search.addEventListener("input", () => { query = search.value; draw(); });
  draw();
  root.append(el("div", { class: "gallery" },
    el("div", { class: "hero" }, el("h1", {}, "Simulations"), intro ? el("p", {}, intro) : ""),
    tabs, shelves, search, sections));
}

/** Mount one simulation with its AI analyst panel. Returns a cleanup function. */
export async function mountSim(page, sim, params = {}) {
  clearRecentCalls();
  const mod = await sim.load();
  const simCleanup = mod.default.mount(page, params) || null;
  const aiCleanup = mountAiPanel(page, sim);
  const keysCleanup = playerKeys(page); // Space, R, arrows and [ ] for any simulation with a playback bar
  return () => { keysCleanup(); aiCleanup(); simCleanup?.(); };
}
