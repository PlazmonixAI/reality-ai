// Account, history and company API client for the app pages (the engine itself is in api.js).
import { el } from "./ui.js";

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

function toLogin() {
  location.href = `/login?next=${encodeURIComponent("/app/" + location.hash)}`;
}

export async function api(path, { method = "GET", body, signal } = {}) {
  let res;
  try {
    res = await fetch(path, { method, signal, credentials: "same-origin",
      headers: body !== undefined ? { "Content-Type": "application/json" } : {}, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }
  if (res.status === 401) { toLogin(); throw new ApiError("Please sign in again.", 401); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new ApiError(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => `${x.loc?.slice(-1)[0] ?? ""}: ${x.msg}`).join("; ") : `Request failed (${res.status})`, res.status);
  }
  return data;
}

let userPromise = null;
export const currentUser = (fresh = false) => { if (fresh || !userPromise) userPromise = api("/api/auth/me").then((r) => r.user); return userPromise; };

export async function signOut() {
  try { await api("/api/auth/logout", { method: "POST" }); } finally { location.href = "/"; }
}

// History ---------------------------------------------------------------
export const history = {
  list: (params = {}) => api(`/api/history?${new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "" && v !== false))}`),
  get: (id) => api(`/api/history/${id}`),
  create: (entry) => api("/api/history", { method: "POST", body: entry }),
  update: (id, patch) => api(`/api/history/${id}`, { method: "PATCH", body: patch }),
  remove: (id) => api(`/api/history/${id}`, { method: "DELETE" }),
};

// Small UI helpers shared by the pages ------------------------------------
export function toast(message, kind = "info") {
  let box = document.querySelector(".toasts");
  if (!box) { box = el("div", { class: "toasts", role: "status", "aria-live": "polite" }); document.body.append(box); }
  const t = el("div", { class: `toast ${kind}` }, message);
  box.append(t);
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 300); }, kind === "error" ? 6000 : 3500);
}

export function when(ts) {
  const d = new Date(ts * 1000), now = Date.now(), s = (now - d.getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 7 * 86400) return `${Math.floor(s / 86400)} d ago`;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
}

export function confirmBox(title, text, okLabel = "Confirm", danger = false) {
  return new Promise((resolve) => {
    const close = (v) => { wrap.remove(); resolve(v); };
    const wrap = el("div", { class: "modal-back", onclick: (e) => { if (e.target === wrap) close(false); } },
      el("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title },
        el("h3", {}, title), el("p", {}, text),
        el("div", { class: "modal-actions" },
          el("button", { class: "btn", type: "button", onclick: () => close(false) }, "Cancel"),
          el("button", { class: `btn primary${danger ? " danger" : ""}`, type: "button", onclick: () => close(true) }, okLabel))));
    document.body.append(wrap);
    wrap.querySelector(".primary").focus();
  });
}

export function promptBox(title, label, value = "", okLabel = "Save") {
  return new Promise((resolve) => {
    const input = el("input", { class: "text-input", value, maxlength: 140 });
    const close = (v) => { wrap.remove(); resolve(v); };
    const wrap = el("div", { class: "modal-back", onclick: (e) => { if (e.target === wrap) close(null); } },
      el("form", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title, onsubmit: (e) => { e.preventDefault(); close(input.value.trim() || null); } },
        el("h3", {}, title), el("label", { class: "field-label" }, label), input,
        el("div", { class: "modal-actions" },
          el("button", { class: "btn", type: "button", onclick: () => close(null) }, "Cancel"),
          el("button", { class: "btn primary", type: "submit" }, okLabel))));
    document.body.append(wrap);
    input.focus(); input.select();
  });
}
