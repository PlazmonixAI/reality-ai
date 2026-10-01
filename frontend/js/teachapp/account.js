// The school account: details and the admin password.
import { el } from "../core/ui.js";
import { api, toast, when } from "../core/session.js";

export default {
  title: "School account",
  mount(root, _params, me) {
    const s = me.school;
    const cur = el("input", { type: "password", autocomplete: "current-password", "aria-label": "Current password" });
    const nw = el("input", { type: "password", autocomplete: "new-password", minlength: 8, "aria-label": "New password" });
    const field = (label, input) => el("label", { class: "ta-field" }, el("span", {}, label), input);
    root.append(
      el("div", { class: "ta-head" }, el("h1", {}, "School account"), el("p", { class: "muted" }, s.name)),
      el("div", { class: "ta-grid" },
        el("section", { class: "panel" }, el("h3", {}, "Details"),
          el("dl", { class: "ta-facts" }, el("dt", {}, "School"), el("dd", {}, s.name), el("dt", {}, "City"), el("dd", {}, s.city || "–"),
            el("dt", {}, "Admin username"), el("dd", {}, s.username), el("dt", {}, "Google account"), el("dd", {}, s.google_email),
            el("dt", {}, "Created"), el("dd", {}, when(s.created_at))),
          el("p", { class: "muted small" }, "You can also sign in with the school's Google account. To close the school account, write to us from it."),
          el("p", {}, el("a", { class: "link", href: "/teach-terms", target: "_blank" }, "ASM Teach Terms"), " · ", el("a", { class: "link", href: "/privacy", target: "_blank" }, "Privacy Policy"))),
        el("form", { class: "panel ta-form", onsubmit: async (e) => {
          e.preventDefault();
          try { await api("/api/auth/password", { method: "POST", body: { current_password: cur.value, new_password: nw.value } }); cur.value = nw.value = ""; toast("Password changed."); }
          catch (err) { toast(err.message, "error"); }
        } }, el("h3", {}, "Admin password"), field("Current password", cur), field("New password (8+ characters)", nw),
        el("button", { type: "submit", class: "btn primary" }, "Change password"))));
  },
};
