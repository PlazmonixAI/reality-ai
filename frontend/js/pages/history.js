// History: everything the user saved, with filters and actions to open, continue, star, rename or delete.
import { el } from "../core/ui.js";
import { history, when, toast, confirmBox, promptBox } from "../core/session.js";

export const KIND_LABEL = { flight: "Flight", design: "Rocket design", mission: "Mission", photo: "Photo", sim: "Simulation",
  space_view: "Space view", ask: "Question", challenge: "Challenge" };
const TABS = [["", "All"], ["flight", "Flights"], ["design", "Designs"], ["mission", "Missions"], ["photo", "Photos"],
  ["sim", "Simulations"], ["challenge", "Challenges"], ["ask", "Questions"]];

export function openLink(r) {
  switch (r.kind) {
    case "flight": return `#/sim/spaceflight?resume=${r.id}`;
    case "design": return `#/sim/spaceflight?design=${r.id}`;
    case "mission": return r.sim_id === "company" ? `#/company?run=${r.id}` : `#/sim/spaceflight?plan=${r.id}`;
    case "photo": return `#/company?run=${r.id}`;
    case "challenge": return "#/challenges";
    case "ask": return `#/ask?saved=${r.id}`;
    case "space_view": return `#/sim/solarsystem?view=${r.id}`;
    default: return r.sim_id ? `#/sim/${r.sim_id}?snapshot=${r.id}` : "#/history";
  }
}
const ACTION = { flight: "Continue", design: "Open", mission: "Open", photo: "View", sim: "Open", ask: "Open", challenge: "View", space_view: "Open" };

function summaryText(r) {
  const s = r.summary || {};
  const bits = [];
  if (s.status) bits.push(s.status);
  if (s.altitude !== undefined) bits.push(`${Math.round(s.altitude / 1000).toLocaleString()} km`);
  if (s.mission_time !== undefined) bits.push(`T+${Math.round(s.mission_time / 60)} min`);
  if (s.delta_v !== undefined) bits.push(`Δv ${Math.round(s.delta_v).toLocaleString()} m/s`);
  if (s.resolution !== undefined) bits.push(`${s.resolution < 10 ? s.resolution.toFixed(2) : Math.round(s.resolution)} m resolution`);
  if (s.c3 !== undefined) bits.push(`C3 ${s.c3.toFixed(1)} km²/s²`);
  if (s.message) bits.push(s.message);
  if (s.tools) bits.push(s.tools.map((t) => t.replace(/_/g, " ")).join(", "));
  return bits.join(" · ");
}

export default {
  title: "History",
  mount(root, params) {
    let kind = params.kind || "", q = "", starred = false, items = [], more = false, counts = {};
    const list = el("div", { class: "hist-list" });
    const tabs = el("div", { class: "tabs", role: "tablist" });
    const search = el("input", { class: "search", type: "search", placeholder: "Search by title", "aria-label": "Search history" });
    const starBtn = el("button", { class: "btn", type: "button", "aria-pressed": "false" }, "Starred only");
    const moreBtn = el("button", { class: "btn", type: "button", hidden: true }, "Load more");
    root.append(el("div", { class: "narrow" },
      el("div", { class: "page-head" }, el("h1", {}, "History"),
        el("p", { class: "muted" }, "Every flight, mission, photo and snapshot you've saved. Flights save themselves as you fly; open one to carry on from the same moment.")),
      tabs, el("div", { class: "hist-tools" }, search, starBtn), list, moreBtn));

    const drawTabs = () => tabs.replaceChildren(...TABS.map(([k, label]) => {
      const n = k ? counts[k] || 0 : Object.values(counts).reduce((a, b) => a + b, 0);
      return el("button", { class: `tab${k === kind ? " on" : ""}`, type: "button", role: "tab", "aria-selected": String(k === kind),
        onclick: () => { kind = k; load(); } }, label, el("span", { class: "count" }, String(n)));
    }));

    function row(r) {
      const star = el("button", { class: `icon-btn star${r.starred ? " on" : ""}`, type: "button", title: r.starred ? "Unstar" : "Star", "aria-label": "Star" }, r.starred ? "★" : "☆");
      star.addEventListener("click", async () => { try { r.starred = !r.starred; await history.update(r.id, { starred: r.starred }); star.textContent = r.starred ? "★" : "☆"; star.classList.toggle("on", r.starred); } catch (e) { toast(e.message, "error"); } });
      const rename = el("button", { class: "btn small", type: "button" }, "Rename");
      rename.addEventListener("click", async () => {
        const t = await promptBox("Rename", "Title", r.title);
        if (!t) return;
        try { await history.update(r.id, { title: t }); r.title = t; title.textContent = t; } catch (e) { toast(e.message, "error"); }
      });
      const del = el("button", { class: "btn small danger-text", type: "button" }, "Delete");
      del.addEventListener("click", async () => {
        if (!(await confirmBox("Delete from history?", `"${r.title}" will be removed for good.`, "Delete", true))) return;
        try { await history.remove(r.id); node.remove(); counts[r.kind]--; drawTabs(); } catch (e) { toast(e.message, "error"); }
      });
      const title = el("b", {}, r.title);
      const node = el("div", { class: "hist-row" },
        star,
        el("div", { class: "hist-main" }, el("div", {}, el("span", { class: `kind k-${r.kind}` }, KIND_LABEL[r.kind] || r.kind), title),
          el("small", {}, [summaryText(r), when(r.updated_at)].filter(Boolean).join(" · "))),
        el("div", { class: "hist-actions" }, el("a", { class: "btn primary small", href: openLink(r) }, ACTION[r.kind] || "Open"), rename, del));
      return node;
    }

    async function load(append = false) {
      try {
        const before = append && items.length ? items[items.length - 1].updated_at : undefined;
        const res = await history.list({ kind, q, starred, before, limit: 40 });
        items = append ? items.concat(res.items) : res.items;
        more = res.more; counts = res.counts;
        drawTabs();
        if (!append) list.replaceChildren();
        list.append(...res.items.map(row));
        if (!items.length) list.replaceChildren(el("div", { class: "empty-state" }, el("b", {}, "Nothing here yet"),
          el("p", {}, kind === "flight" ? "Launch a rocket in the Spaceflight Lab; the flight is saved as you go." : "Save something and it will show up here.")));
        moreBtn.hidden = !more;
      } catch (e) { list.replaceChildren(el("p", { class: "muted" }, e.message)); }
    }
    let t = 0;
    search.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { q = search.value.trim(); load(); }, 250); });
    starBtn.addEventListener("click", () => { starred = !starred; starBtn.setAttribute("aria-pressed", String(starred)); starBtn.classList.toggle("on", starred); load(); });
    moreBtn.addEventListener("click", () => load(true));
    load();
  },
};
