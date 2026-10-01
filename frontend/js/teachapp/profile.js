// The teacher's own panel: profile, password, this month's teaching and saved lessons. Works on a phone too.
import { el } from "../core/ui.js";
import { api, history, toast, when } from "../core/session.js";

const LABEL = { board: "Board sessions", experiment: "Experiments opened", lesson_saved: "Lessons saved", file_shown: "Files shown",
  video: "Videos played", equation: "Equations built", listen: "Spoken commands" };

export default {
  title: "Profile",
  mount(root, _params, me) {
    const t = me.teacher;
    const name = el("input", { value: t.name, maxlength: 120, "aria-label": "Name" });
    const subject = el("input", { value: t.subject, maxlength: 60, placeholder: "e.g. Physics", "aria-label": "Subject" });
    const phone = el("input", { value: t.phone, maxlength: 20, inputmode: "tel", placeholder: "Optional", "aria-label": "Phone" });
    const field = (label, input) => el("label", { class: "ta-field" }, el("span", {}, label), input);
    const profile = el("form", { class: "panel ta-form", onsubmit: async (e) => {
      e.preventDefault();
      try { await api("/api/teach/me", { method: "PATCH", body: { name: name.value, subject: subject.value, phone: phone.value } }); toast("Profile saved."); }
      catch (err) { toast(err.message, "error"); }
    } },
    el("h3", {}, "Your profile"),
    field("Name", name), field("Subject", subject), field("Phone", phone),
    el("dl", { class: "ta-facts" }, el("dt", {}, "Username"), el("dd", {}, t.username), el("dt", {}, "Email"), el("dd", {}, t.email),
      el("dt", {}, "School"), el("dd", {}, t.school_name)),
    el("button", { type: "submit", class: "btn primary" }, "Save profile"));

    const cur = el("input", { type: "password", autocomplete: "current-password", "aria-label": "Current password" });
    const nw = el("input", { type: "password", autocomplete: "new-password", minlength: 8, "aria-label": "New password" });
    const pw = el("form", { class: "panel ta-form", onsubmit: async (e) => {
      e.preventDefault();
      try { await api("/api/auth/password", { method: "POST", body: { current_password: cur.value, new_password: nw.value } }); cur.value = nw.value = ""; toast("Password changed."); }
      catch (err) { toast(err.message, "error"); }
    } }, el("h3", {}, "Password"), field("Current password", cur), field("New password (8+ characters)", nw),
    el("button", { type: "submit", class: "btn" }, "Change password"));

    const usage = el("section", { class: "panel" }, el("h3", {}, "Your last 30 days"), el("p", { class: "muted small" }, "Loading…"));
    const lessons = el("section", { class: "panel" }, el("h3", {}, "Saved lessons"), el("p", { class: "muted small" }, "Loading…"));
    root.append(el("div", { class: "ta-head" }, el("h1", {}, `Hello, ${t.name.split(" ")[0]}`),
      el("p", { class: "muted" }, `${t.subject || "Teacher"} · ${t.school_name}`)),
    el("div", { class: "ta-grid" }, el("div", { class: "ta-col" }, usage, lessons), el("div", { class: "ta-col" }, profile, pw)));

    api("/api/teach/me/usage").then((u) => {
      const rows = Object.entries(LABEL).map(([k, label]) => el("div", { class: "ta-stat" }, el("b", {}, String(u.last_30_days[k] || 0)), el("span", {}, label)));
      usage.replaceChildren(el("h3", {}, "Your last 30 days"), el("div", { class: "ta-stats" }, rows),
        u.recent_experiments.length ? el("p", { class: "muted small" }, "Recently opened: ", ...u.recent_experiments.map((id) => el("a", { class: "chip", href: `#/teach/${id}` }, id))) : "");
    }).catch((err) => usage.replaceChildren(el("h3", {}, "Your last 30 days"), el("p", { class: "muted small" }, err.message)));

    history.list({ kind: "lesson", limit: 20 }).then((r) => {
      const items = r.items || r.runs || [];
      lessons.replaceChildren(el("h3", {}, "Saved lessons"), ...(items.length ? items.map((s) => el("a", { class: "ta-lesson",
        href: s.sim_id === "board" ? `#/board?lesson=${s.id}` : `#/teach/${s.sim_id}?lesson=${s.id}` }, el("b", {}, s.title), el("small", {}, when(s.updated_at || s.created_at))))
        : [el("p", { class: "muted small" }, "Press Save on the board or in an experiment to keep a lesson here.")]));
    }).catch((err) => lessons.replaceChildren(el("h3", {}, "Saved lessons"), el("p", { class: "muted small" }, err.message)));
  },
};
