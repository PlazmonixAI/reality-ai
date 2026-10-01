// Admin (beta team only): sign-ups, activity, challenge completions and feedback.
import { el } from "../core/ui.js";
import { api, when } from "../core/session.js";

const LABELS = { users: "Accounts", users_7d: "New this week", active_24h: "Signed in today", saved_items: "Saved items",
  flights: "Flights", companies: "Companies", spacecraft: "Spacecraft", photos: "Photos", challenges_done: "Challenges done", feedback: "Feedback", waitlist: "Waitlist" };

export default {
  title: "Admin",
  mount(root) {
    const wrap = el("div", { class: "wide" }, el("div", { class: "page-head" }, el("h1", {}, "Beta admin"),
      el("p", { class: "muted" }, "Who signed up, what they use, and what they told you.")));
    root.append(wrap);
    api("/api/admin/overview").then((d) => {
      const table = (head, rows) => el("div", { class: "admin-table" }, el("table", {},
        el("thead", {}, el("tr", {}, ...head.map((h) => el("th", {}, h)))), el("tbody", {}, ...rows)));
      wrap.append(
        el("div", { class: "admin-stats" }, ...Object.entries(d.stats).map(([k, v]) => el("div", { class: "stat-box" }, el("b", {}, v.toLocaleString()), el("span", {}, LABELS[k] || k)))),
        el("h2", { class: "section-title" }, `Feedback (${d.feedback.length})`),
        d.feedback.length ? table(["When", "From", "Page", "Message"], d.feedback.map((f) => el("tr", {},
          el("td", { class: "nowrap" }, when(f.created_at)), el("td", {}, f.name || "deleted account", el("br"), el("small", { class: "muted" }, f.email || "")),
          el("td", { class: "mono" }, f.page || ""), el("td", { class: "msg" }, f.message))))
          : el("p", { class: "muted" }, "No feedback yet."),
        el("h2", { class: "section-title" }, `Waitlist (${d.waitlist.length})`,
          d.waitlist.length ? el("button", { class: "btn small", type: "button", onclick: (e) => {
            navigator.clipboard?.writeText(d.waitlist.map((w) => w.email).join("\n")).then(() => { e.target.textContent = "Copied"; });
          } }, "Copy all emails") : ""),
        d.waitlist.length ? table(["Email", "Joined", "From page"], d.waitlist.map((w) => el("tr", {},
          el("td", {}, w.email), el("td", { class: "nowrap" }, when(w.created_at)), el("td", { class: "mono" }, w.source || ""))))
          : el("p", { class: "muted" }, "Nobody on the waitlist yet."),
        el("h2", { class: "section-title" }, "Challenges completed"),
        d.challenges.length ? table(["Challenge", "Players"], d.challenges.map((c) => el("tr", {}, el("td", {}, c.challenge_id.replace(/_/g, " ")), el("td", {}, String(c.n)))))
          : el("p", { class: "muted" }, "None yet."),
        el("h2", { class: "section-title" }, "Newest accounts"),
        table(["Name", "Email", "Joined", "Last sign-in"], d.recent_users.map((u) => el("tr", {},
          el("td", {}, u.name), el("td", {}, u.email), el("td", { class: "nowrap" }, when(u.created_at)), el("td", { class: "nowrap" }, u.last_login_at ? when(u.last_login_at) : "never")))));
    }).catch((e) => wrap.append(el("p", { class: "muted" }, e.message)));
  },
};
