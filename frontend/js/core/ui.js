// Small DOM toolkit for simulation control panels.
import { fmt } from "./format.js";

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

let uid = 0;
const nextId = (p) => `${p}-${++uid}`;

/** Standard three-area simulation layout: scene (canvas), side (controls), bottom (player / graphs). */
export function simLayout(root) {
  const scene = el("div", { class: "sim-scene" });
  const side = el("aside", { class: "sim-side" });
  const bottom = el("div", { class: "sim-bottom" });
  const layout = el("div", { class: "sim-layout" }, scene, side, bottom);
  root.append(layout);
  const status = el("div", { class: "scene-status", role: "status", "aria-live": "polite" });
  scene.append(status);
  let busyTimer = null;
  return {
    scene, side, bottom,
    /** Show a transient "computing" indicator (delayed so fast responses don't flicker). */
    busy(on) {
      clearTimeout(busyTimer);
      if (on) {
        busyTimer = setTimeout(() => {
          if (!status.classList.contains("error")) { status.textContent = "Computing…"; status.classList.add("show"); }
        }, 250);
      } else if (!status.classList.contains("error")) status.classList.remove("show");
    },
    error(message) {
      status.textContent = message;
      status.classList.add("show", "error");
    },
    clearError() { status.classList.remove("show", "error"); },
  };
}

export function panel(title, ...children) {
  return el("section", { class: "panel" }, title ? el("h4", {}, title) : null, ...children);
}

/**
 * Slider with label and live value. With log=true the slider moves in log10 space.
 * format(v) customises the displayed value.
 */
export function slider({ label, min, max, step = "any", value, unit = "", log = false, digits = 3, format, onInput }) {
  const id = nextId("s");
  const toPos = (v) => (log ? Math.log10(v) : v);
  const fromPos = (p) => (log ? 10 ** p : p);
  const input = el("input", {
    type: "range", id,
    min: toPos(min), max: toPos(max),
    step: log ? "any" : step,
    value: toPos(value),
  });
  const out = el("output", { for: id });
  const show = (v) => { out.textContent = format ? format(v) : `${fmt(v, digits)}${unit ? " " + unit : ""}`; };
  const api = {
    root: el("div", { class: "control" }, el("div", { class: "control-head" }, el("label", { for: id }, label), out), input),
    get value() { return fromPos(Number(input.value)); },
    set(v, { silent = true } = {}) {
      input.value = toPos(v); show(api.value);
      if (!silent) onInput?.(api.value);
    },
    setRange(lo, hi) {
      input.min = toPos(lo); input.max = toPos(hi);
      show(api.value);
    },
    disable(flag) { input.disabled = flag; api.root.style.opacity = flag ? 0.5 : 1; },
  };
  input.addEventListener("input", () => { show(api.value); onInput?.(api.value); });
  show(value);
  return api;
}

export function select({ label, options, value, onChange }) {
  const id = nextId("sel");
  const sel = el("select", { id }, options.map((o) => el("option", { value: o.value }, o.label)));
  sel.value = value ?? options[0].value;
  sel.addEventListener("change", () => onChange?.(sel.value));
  return {
    root: el("div", { class: "control" }, label ? el("div", { class: "control-head" }, el("label", { for: id }, label)) : null, sel),
    get value() { return sel.value; },
    set(v) { sel.value = v; },
  };
}

/** Segmented button group (radio-like). */
export function segmented({ label, options, value, onChange }) {
  let current = value ?? options[0].value;
  const buttons = options.map((o) => el("button", {
    type: "button", "aria-pressed": String(o.value === current),
    class: o.value === current ? "on" : "",
    onclick: () => { api.set(o.value); onChange?.(o.value); },
  }, o.label));
  const api = {
    root: el("div", { class: "control" }, label ? el("div", { class: "control-head" }, el("label", {}, label)) : null,
      el("div", { class: "seg", role: "group", "aria-label": label || "" }, buttons)),
    get value() { return current; },
    set(v) {
      current = v;
      buttons.forEach((b, i) => {
        const on = options[i].value === v;
        b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on));
      });
    },
  };
  return api;
}

export function checkbox({ label, value = false, onChange }) {
  const input = el("input", { type: "checkbox" });
  input.checked = value;
  input.addEventListener("change", () => onChange?.(input.checked));
  return {
    root: el("div", { class: "control" }, el("label", { class: "check" }, input, label)),
    get value() { return input.checked; },
    set(v) { input.checked = v; },
  };
}

export function textInput({ label, value = "", mono = false, placeholder = "", onChange }) {
  const id = nextId("t");
  const input = el("input", { type: "text", id, value, placeholder, class: mono ? "mono" : "", spellcheck: "false" });
  input.addEventListener("input", () => onChange?.(input.value));
  return {
    root: el("div", { class: "control" }, el("div", { class: "control-head" }, el("label", { for: id }, label)), input),
    get value() { return input.value; },
    set(v) { input.value = v; },
  };
}

export function button(label, onClick, cls = "") {
  return el("button", { type: "button", class: `btn ${cls}`, onclick: onClick }, label);
}

/** Two-column label/value list. rows: [{key, label}] */
export function readouts(rows) {
  const values = {};
  const dl = el("dl", { class: "readouts" });
  for (const r of rows) {
    values[r.key] = el("dd", {}, "–");
    dl.append(el("dt", {}, r.label), values[r.key]);
  }
  return {
    root: dl,
    set(key, text) { if (values[key]) values[key].textContent = text; },
    clear() { Object.values(values).forEach((v) => { v.textContent = "–"; }); },
  };
}

export function legend(items) {
  return el("div", { class: "legend" }, items.map((it) =>
    el("span", {}, el("i", { class: it.dash ? "dash" : "", style: `background:${it.color};color:${it.color}` }), it.label)));
}

export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export const SERIES = () => [cssVar("--series-1"), cssVar("--series-2"), cssVar("--series-3")];
