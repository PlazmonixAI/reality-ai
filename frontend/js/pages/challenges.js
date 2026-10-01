// Challenge mode: missions with goals the server checks. Sandbox is everything else in the app.
import { el } from "../core/ui.js";
import { api, toast, when } from "../core/session.js";

const LEVEL = { 1: "Starter", 2: "Intermediate", 3: "Advanced" };

export default {
  title: "Challenges",
  mount(root) {
    const grid = el("div", { class: "ch-grid" });
    const progress = el("div", { class: "ch-progress" });
    root.append(el("div", { class: "wide" },
      el("div", { class: "page-head" }, el("h1", {}, "Challenges"),
        el("p", { class: "muted" }, "Missions with a clear goal. The server checks each one from the engine's own results, so edited flights don't count. Everything else in the app is sandbox: do what you like.")),
      progress, grid));
    const load = () => api("/api/challenges").then((d) => {
      progress.replaceChildren(el("div", { class: "meter" }, el("i", { style: `width:${(d.completed / d.total) * 100}%` })),
        el("span", {}, `${d.completed} of ${d.total} complete`));
      grid.replaceChildren(...d.challenges.map((c) => {
        const result = el("p", { class: "ch-result" });
        const start = c.where === "lab"
          ? el("a", { class: "btn primary", href: `#/sim/spaceflight?challenge=${c.id}${c.template ? `&template=${c.template}` : ""}` }, c.completed_at ? "Fly it again" : "Start mission")
          : el("a", { class: "btn primary", href: `#/company?challenge=${c.id}` }, "Open Mission Control");
        const check = c.where === "company" ? el("button", { class: "btn", type: "button", onclick: async () => {
          check.disabled = true;
          try {
            const r = await api(`/api/challenges/${c.id}/submit`, { method: "POST", body: {} });
            result.textContent = r.message; result.className = `ch-result ${r.passed ? "ok" : "no"}`;
            if (r.passed) { toast(`Challenge complete: ${c.title}`); load(); }
          } catch (e) { toast(e.message, "error"); } finally { check.disabled = false; }
        } }, "Check my fleet") : "";
        return el("article", { class: `ch-card${c.completed_at ? " done" : ""}` },
          el("div", { class: "ch-top" }, el("span", { class: `lvl l${c.level}` }, LEVEL[c.level]),
            c.completed_at ? el("span", { class: "done-badge" }, `Done ${when(c.completed_at)}`) : ""),
          el("h3", {}, c.title), el("p", { class: "ch-goal" }, c.goal), el("p", { class: "muted small" }, c.briefing),
          el("details", {}, el("summary", {}, "Hint"), el("p", { class: "small" }, c.hint)),
          el("div", { class: "ch-actions" }, start, check), result);
      }));
    }).catch((e) => grid.replaceChildren(el("p", { class: "muted" }, e.message)));
    load();
  },
};
