// School admin panel: add teachers with a username and password, pause, reset or remove them, and see how ASM Teach
// is used across the school.
import { el } from "../core/ui.js";
import { api, toast, confirmBox, promptBox, when } from "../core/session.js";

export default {
  title: "Teachers",
  mount(root, _params, me) {
    const s = me.school;
    const stats = el("div", { class: "ta-stats" });
    const table = el("div", { class: "ta-tablewrap" }, el("p", { class: "muted small" }, "Loading teachers…"));
    const top = el("section", { class: "panel" });
    const f = {
      name: el("input", { maxlength: 120, required: true, autocomplete: "off" }), email: el("input", { type: "email", maxlength: 254, required: true, autocomplete: "off" }),
      username: el("input", { maxlength: 32, required: true, autocomplete: "off", placeholder: "e.g. asha.rao" }),
      password: el("input", { type: "text", minlength: 8, required: true, autocomplete: "off" }), subject: el("input", { maxlength: 60, placeholder: "Physics" }),
    };
    const field = (label, input) => el("label", { class: "ta-field" }, el("span", {}, label), input);
    const suggest = () => {  // a readable starting password the admin can hand over
      const words = ["prism", "orbit", "vector", "proton", "lens", "atom", "graph", "pulley", "quark", "joule"];
      f.password.value = `${words[Math.floor(Math.random() * words.length)]}-${words[Math.floor(Math.random() * words.length)]}-${Math.floor(10 + Math.random() * 89)}`;
    };
    suggest();
    f.name.addEventListener("input", () => {
      if (!f.username.dataset.touched) f.username.value = f.name.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, ".").replace(/^\.+|\.+$/g, "").slice(0, 32);
    });
    f.username.addEventListener("input", () => { f.username.dataset.touched = "1"; });
    const add = el("form", { class: "panel ta-form", onsubmit: async (e) => {
      e.preventDefault();
      try {
        const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v.value]));
        const r = await api("/api/teach/teachers", { method: "POST", body });
        toast(`${r.teacher.name} can now sign in as “${r.teacher.username}”.`);
        Object.values(f).forEach((i) => { i.value = ""; }); delete f.username.dataset.touched; suggest();
        load();
      } catch (err) { toast(err.message, "error"); }
    } },
    el("h3", {}, "Add a teacher"),
    field("Full name", f.name), field("Email", f.email), field("Username", f.username),
    field("Starting password", el("div", { class: "ta-row" }, f.password, el("button", { type: "button", class: "btn small", onclick: suggest }, "New"))),
    field("Subject", f.subject),
    el("p", { class: "muted small" }, "Give the teacher their username and password. They sign in at /teach as a Teacher and can change the password in their profile."),
    el("button", { type: "submit", class: "btn primary" }, "Add teacher"));

    root.append(
      el("div", { class: "ta-head" }, el("h1", {}, s.name), el("p", { class: "muted" }, `${s.city ? `${s.city} · ` : ""}School admin · ${s.google_email}`)),
      stats,
      el("div", { class: "ta-grid wide-first" }, el("div", { class: "ta-col" }, el("section", { class: "panel" }, el("h3", {}, "Teachers"), table), top),
        el("div", { class: "ta-col" }, add)));

    async function load() {
      let data;
      try { data = await api("/api/teach/school"); } catch (err) { table.replaceChildren(el("p", { class: "muted small" }, err.message)); return; }
      const ts = data.teachers;
      const sum = (k) => ts.reduce((a, t) => a + t.usage_30d[k], 0);
      const activeMonth = ts.filter((t) => t.last_active).length;
      stats.replaceChildren(
        el("div", { class: "ta-stat" }, el("b", {}, String(ts.length)), el("span", {}, "teacher accounts")),
        el("div", { class: "ta-stat" }, el("b", {}, String(activeMonth)), el("span", {}, "used ASM Teach this month")),
        el("div", { class: "ta-stat" }, el("b", {}, String(sum("experiments"))), el("span", {}, "experiments opened, 30 days")),
        el("div", { class: "ta-stat" }, el("b", {}, String(sum("lessons"))), el("span", {}, "lessons saved, 30 days")));
      if (!ts.length) { table.replaceChildren(el("p", { class: "muted" }, "No teachers yet. Add your first teacher on the right.")); }
      else table.replaceChildren(el("table", { class: "ice ta-table" },
        el("thead", {}, el("tr", {}, ["Teacher", "Username", "Subject", "Last 30 days", "Last seen", ""].map((h) => el("th", {}, h)))),
        el("tbody", {}, ts.map(row))));
      top.replaceChildren(el("h3", {}, "Most used experiments, 30 days"), ...(data.top_experiments.length
        ? [el("ol", { class: "ta-top" }, data.top_experiments.map((x) => el("li", {}, el("span", {}, x.id), el("b", {}, String(x.count)))))]
        : [el("p", { class: "muted small" }, "Appears once teachers open experiments.")]));
    }

    function row(t) {
      const u = t.usage_30d;
      return el("tr", { class: t.active ? "" : "paused" },
        el("td", {}, el("b", {}, t.name), el("br"), el("small", { class: "muted" }, t.email)),
        el("td", { class: "mono" }, t.username),
        el("td", {}, t.subject || "–"),
        el("td", {}, `${u.sessions} sessions · ${u.experiments} experiments · ${u.lessons} lessons · ${t.files} files`),
        el("td", {}, t.active ? (t.last_login_at ? when(t.last_login_at) : "never") : "paused"),
        el("td", { class: "ta-actions" },
          el("button", { type: "button", class: "btn small", onclick: async () => {
            const pw = await promptBox(`New password for ${t.name}`, "New password (8+ characters)", "", "Set password");
            if (!pw) return;
            try { await api(`/api/teach/teachers/${t.id}`, { method: "PATCH", body: { password: pw } }); toast(`Password changed. ${t.name} is signed out everywhere.`); }
            catch (err) { toast(err.message, "error"); }
          } }, "Password"),
          el("button", { type: "button", class: "btn small", onclick: async () => {
            try { await api(`/api/teach/teachers/${t.id}`, { method: "PATCH", body: { active: !t.active } }); load(); }
            catch (err) { toast(err.message, "error"); }
          } }, t.active ? "Pause" : "Resume"),
          el("button", { type: "button", class: "btn small danger", onclick: async () => {
            if (!(await confirmBox(`Remove ${t.name}?`, "Their account, saved lessons and files are deleted. This can't be undone.", "Remove", true))) return;
            try { await api(`/api/teach/teachers/${t.id}`, { method: "DELETE" }); load(); } catch (err) { toast(err.message, "error"); }
          } }, "Remove")));
    }

    load();
  },
};
