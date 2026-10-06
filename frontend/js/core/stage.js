// HiDPI canvas that tracks its container size, plus a world<->screen viewport with pan & zoom.
import { el } from "./ui.js";

export function createStage(parent, { onResize } = {}) {
  const canvas = el("canvas", { class: "stage" });
  parent.append(canvas);
  const ctx = canvas.getContext("2d");
  const size = { width: 0, height: 0 };
  const ro = new ResizeObserver(() => {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    size.width = r.width; size.height = r.height;
    canvas.width = Math.max(1, Math.round(r.width * dpr));
    canvas.height = Math.max(1, Math.round(r.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    onResize?.(size.width, size.height);
  });
  ro.observe(canvas);
  return {
    canvas, ctx,
    get width() { return size.width; },
    get height() { return size.height; },
    destroy() { ro.disconnect(); },
  };
}

/** Uniform-scale mapping from world coordinates (y up) to screen pixels. */
export class View {
  constructor() { this.scale = 1; this.cx = 0; this.cy = 0; this.w = 1; this.h = 1; }

  fit(xmin, xmax, ymin, ymax, w, h, { pad = 0.08, anchor = "center" } = {}) {
    this.w = w; this.h = h;
    const dx = Math.max(xmax - xmin, 1e-12), dy = Math.max(ymax - ymin, 1e-12);
    this.scale = Math.min((w * (1 - 2 * pad)) / dx, (h * (1 - 2 * pad)) / dy);
    this.cx = (xmin + xmax) / 2;
    this.cy = (ymin + ymax) / 2;
    if (anchor === "bottom-left") {
      // Keep the world's lower-left corner at the padded lower-left of the screen.
      this.cx = xmin + (w / 2 - w * pad) / this.scale;
      this.cy = ymin + (h / 2 - h * pad) / this.scale;
    }
  }

  x(wx) { return this.w / 2 + (wx - this.cx) * this.scale; }
  y(wy) { return this.h / 2 - (wy - this.cy) * this.scale; }
  len(d) { return d * this.scale; }
  toWorld(sx, sy) { return [this.cx + (sx - this.w / 2) / this.scale, this.cy - (sy - this.h / 2) / this.scale]; }
}

/** Pan and zoom for mouse, touch and keyboard: wheel or pinch to zoom, drag to pan, and with the canvas focused
 * (tap or Tab to it) the arrow keys pan, + and − zoom, 0 resets. onChange runs after every change; returns a detach. */
export function enablePanZoom(canvas, view, onChange, { enabled = () => true, onReset = null } = {}) {
  const pts = new Map();
  let drag = null, pinch = null;
  const local = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  const zoomAt = (sx, sy, f) => {
    const [wx, wy] = view.toWorld(sx, sy);
    view.scale *= f;
    view.cx = wx - (wx - view.cx) / f;
    view.cy = wy - (wy - view.cy) / f;
    onChange();
  };
  const wheel = (e) => {
    if (!enabled()) return;
    e.preventDefault();
    const [x, y] = local(e);
    zoomAt(x, y, Math.exp(-e.deltaY * 0.0015));
  };
  const down = (e) => {
    if (!enabled() || (e.pointerType === "mouse" && e.button !== 0)) return;
    pts.set(e.pointerId, local(e)); canvas.setPointerCapture(e.pointerId);
    if (pts.size === 1) drag = { x: e.clientX, y: e.clientY };
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]) }; drag = null; }
  };
  const move = (e) => {
    if (pts.has(e.pointerId)) pts.set(e.pointerId, local(e));
    if (pinch && pts.size === 2) {
      const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (d > 0 && pinch.d > 0) zoomAt((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, d / pinch.d);
      pinch.d = d; return;
    }
    if (!drag) return;
    view.cx -= (e.clientX - drag.x) / view.scale;
    view.cy += (e.clientY - drag.y) / view.scale;
    drag = { x: e.clientX, y: e.clientY };
    onChange();
  };
  const up = (e) => { pts.delete(e.pointerId); if (pts.size < 2) pinch = null; if (!pts.size) drag = null; };
  const key = (e) => {
    if (!enabled()) return;
    const step = 60 / view.scale, w = view.w / 2, h = view.h / 2;
    const act = { ArrowLeft: () => { view.cx -= step; onChange(); }, ArrowRight: () => { view.cx += step; onChange(); },
      ArrowUp: () => { view.cy += step; onChange(); }, ArrowDown: () => { view.cy -= step; onChange(); },
      "+": () => zoomAt(w, h, 1.25), "=": () => zoomAt(w, h, 1.25), "-": () => zoomAt(w, h, 0.8), 0: () => onReset?.() }[e.key];
    if (act) { e.preventDefault(); act(); }
  };
  if (!canvas.hasAttribute("tabindex")) canvas.tabIndex = 0;
  canvas.style.touchAction = "none";
  canvas.addEventListener("wheel", wheel, { passive: false });
  canvas.addEventListener("pointerdown", down);
  canvas.addEventListener("pointermove", move);
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", up);
  canvas.addEventListener("keydown", key);
  return () => {
    canvas.removeEventListener("wheel", wheel);
    canvas.removeEventListener("pointerdown", down);
    canvas.removeEventListener("pointermove", move);
    canvas.removeEventListener("pointerup", up);
    canvas.removeEventListener("pointercancel", up);
    canvas.removeEventListener("keydown", key);
  };
}

/** Linear interpolation of arr at time t over sorted times ts. */
export function sampleAt(ts, arr, t) {
  const n = ts.length;
  if (!n) return NaN;
  if (t <= ts[0]) return arr[0];
  if (t >= ts[n - 1]) return arr[n - 1];
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (ts[mid] <= t) lo = mid; else hi = mid;
  }
  const f = (t - ts[lo]) / (ts[hi] - ts[lo]);
  return arr[lo] + (arr[hi] - arr[lo]) * f;
}

/** Index of the last sample with time <= t. */
export function indexAt(ts, t) {
  let lo = 0, hi = ts.length - 1;
  if (t >= ts[hi]) return hi;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (ts[mid] <= t) lo = mid; else hi = mid;
  }
  return lo;
}

export function starfield(ctx, w, h, seed = 7) {
  let s = seed;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#050a18"); g.addColorStop(1, "#0b1830");
  ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  const n = Math.round((w * h) / 2600);
  for (let i = 0; i < n; i++) {
    const a = 0.25 + rand() * 0.6;
    ctx.fillStyle = `rgba(255,255,255,${a})`;
    ctx.fillRect(rand() * w, rand() * h, rand() < 0.1 ? 1.6 : 1, rand() < 0.1 ? 1.6 : 1);
  }
}

export function arrow(ctx, x1, y1, x2, y2, color, width = 2, head = 8) {
  const ang = Math.atan2(y2 - y1, x2 - x1);
  ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width;
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2 - Math.cos(ang) * head * 0.6, y2 - Math.sin(ang) * head * 0.6); ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - head * Math.cos(ang - 0.45), y2 - head * Math.sin(ang - 0.45));
  ctx.lineTo(x2 - head * Math.cos(ang + 0.45), y2 - head * Math.sin(ang + 0.45));
  ctx.closePath(); ctx.fill();
}

export function label(ctx, text, x, y, { color = "#16202c", font = "12px system-ui", align = "left", baseline = "middle", halo = null } = {}) {
  ctx.font = font; ctx.textAlign = align; ctx.textBaseline = baseline;
  if (halo) { ctx.lineWidth = 4; ctx.strokeStyle = halo; ctx.lineJoin = "round"; ctx.strokeText(text, x, y); }
  ctx.fillStyle = color; ctx.fillText(text, x, y);
}

/** "Nice" tick step (1, 2, 5 × 10^n) for about `target` ticks across span. */
export function niceStep(span, target = 6) {
  const raw = span / Math.max(target, 1);
  const p = 10 ** Math.floor(Math.log10(raw));
  const m = raw / p;
  return (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * p;
}

/** Draws a scale bar (bottom-left) of a round length for the given view. */
export function scaleBar(ctx, view, h, { unit = "m", divisor = 1, color = "#fff" } = {}) {
  const worldPx = 120 / view.scale;
  const step = niceStep(worldPx / divisor, 1) * divisor;
  const px = view.len(step);
  const x = 16, y = h - 18;
  ctx.strokeStyle = color; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(x, y - 5); ctx.lineTo(x, y); ctx.lineTo(x + px, y); ctx.lineTo(x + px, y - 5); ctx.stroke();
  label(ctx, `${Number((step / divisor).toPrecision(3)).toLocaleString("en-US")} ${unit}`, x + px / 2, y - 10,
    { color, align: "center", font: "12px system-ui" });
}
