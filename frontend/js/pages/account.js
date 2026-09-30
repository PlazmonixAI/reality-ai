// Account settings: profile, password, data download, sign out, delete account.
import { el } from "../core/ui.js";
import { api, currentUser, signOut, toast, confirmBox } from "../core/session.js";

export default {
  title: "Account",
  mount(root) {
    const wrap = el("div", { class: "narrow" }, el("div", { class: "page-head" }, el("h1", {}, "Account settings")));
    root.append(wrap);
    currentUser(true).then((u) => {
      const name = el("input", { class: "text-input", value: u.name, maxlength: 60, autocomplete: "name" });
      const profile = el("form", { class: "card-box" }, el("h3", {}, "Profile"),
        el("label", { class: "field-label" }, "Name"), name,
        el("label", { class: "field-label" }, "Email"), el("input", { class: "text-input", value: u.email, disabled: true }),
        el("p", { class: "muted small" }, `Member since ${new Date(u.created_at * 1000).toLocaleDateString(undefined, { dateStyle: "long" })}${u.google ? " · signs in with Google" : ""}`),
        el("button", { class: "btn primary", type: "submit" }, "Save"));
      profile.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await api("/api/account", { method: "PATCH", body: { name: name.value } }); toast("Profile saved."); currentUser(true); }
        catch (err) { toast(err.message, "error"); }
      });

      const cur = el("input", { class: "text-input", type: "password", autocomplete: "current-password" });
      const nw = el("input", { class: "text-input", type: "password", autocomplete: "new-password", minlength: 8 });
      const nw2 = el("input", { class: "text-input", type: "password", autocomplete: "new-password" });
      const pw = el("form", { class: "card-box" }, el("h3", {}, u.has_password ? "Change password" : "Set a password"),
        u.has_password ? [el("label", { class: "field-label" }, "Current password"), cur] : el("p", { class: "muted small" }, "Add a password to sign in with email as well as Google."),
        el("label", { class: "field-label" }, "New password"), nw, el("label", { class: "field-label" }, "Repeat new password"), nw2,
        el("p", { class: "muted small" }, "Changing it signs you out on every other device."),
        el("button", { class: "btn primary", type: "submit" }, "Update password"));
      pw.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (nw.value !== nw2.value) { toast("The two new passwords don't match.", "error"); return; }
        try { await api("/api/auth/password", { method: "POST", body: { current_password: cur.value, new_password: nw.value } }); pw.reset(); toast("Password updated."); }
        catch (err) { toast(err.message, "error"); }
      });

      const data = el("div", { class: "card-box" }, el("h3", {}, "Your data"),
        el("p", { class: "muted small" }, "Download everything we store about you: profile, history, company, spacecraft, photos and challenge progress, as a JSON file."),
        el("button", { class: "btn", type: "button", onclick: async () => {
          try {
            const d = await api("/api/account/export");
            const a = el("a", { href: URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" })), download: "reality-asm-data.json" });
            document.body.append(a); a.click(); a.remove();
          } catch (err) { toast(err.message, "error"); }
        } }, "Download my data"),
        el("button", { class: "btn", type: "button", onclick: () => signOut() }, "Sign out"));

      const confirm = el("input", { class: "text-input", type: u.has_password ? "password" : "email", placeholder: u.has_password ? "Your password" : "Your email address" });
      const danger = el("form", { class: "card-box danger-box" }, el("h3", {}, "Delete account"),
        el("p", { class: "muted small" }, "This removes your account, history, company, fleet and photos right away. It can't be undone."),
        el("label", { class: "field-label" }, u.has_password ? "Confirm with your password" : "Type your email to confirm"), confirm,
        el("button", { class: "btn primary danger", type: "submit" }, "Delete my account"));
      danger.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!(await confirmBox("Delete your account?", "Everything you've saved will be gone for good.", "Delete forever", true))) return;
        try { await api("/api/account", { method: "DELETE", body: { confirm: confirm.value } }); location.href = "/"; }
        catch (err) { toast(err.message, "error"); }
      });
      wrap.append(profile, pw, data, danger);
    });
  },
};
