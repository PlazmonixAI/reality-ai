// ASM Teach "worlds": what an experiment looks like in real life, drawn beside its numbers.
// Each world is a picture that moves with the engine's results (teach.experiment outputs and the values it used).
// The browser never computes physics here: sizes, speeds and colours are scaled from engine numbers only, so when a
// teacher types a new value the picture changes the way the real thing would.
import { fmt } from "../core/format.js";
import { arrow, label } from "../core/stage.js";

export const INK = "#0B1526", EMBER = "#FF5B2E";
const SKY = "#eaf2fb", GROUND = "#d9dfd0", WATER = "rgba(70,140,220,.28)", METAL = "#9aa3b2", WOOD = "#b98a5a";

// ---------------------------------------------------------------- helpers
export const finite = (v, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v : d);
/** Soft size in 0..1 for any positive value against a typical value: never off the screen, always changes. */
export const soft = (x, ref) => { const a = Math.abs(finite(x)), r = Math.abs(ref) || 1; return a / (a + r); };
/** Signed soft value in -1..1. */
export const ssoft = (x, ref) => Math.sign(finite(x)) * soft(x, ref);
export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
export const cyc = (t, period) => ((t % period) + period) % period / period; // 0..1 phase

export function T(ctx, text, x, y, o = {}) {
  label(ctx, String(text), x, y, { color: o.color || INK, font: o.font || "600 14px Plex, system-ui", align: o.align || "center", baseline: o.baseline || "middle", halo: o.halo === undefined ? "rgba(255,255,255,.85)" : o.halo });
}
export const small = (ctx, text, x, y, o = {}) => T(ctx, text, x, y, { font: "600 12px Plex, system-ui", color: "#4D5769", ...o });
export const big = (ctx, text, x, y, o = {}) => T(ctx, text, x, y, { font: "700 18px Plex, system-ui", ...o });
export function ball(ctx, x, y, r, fill, stroke) { ctx.fillStyle = fill; ctx.beginPath(); ctx.arc(x, y, Math.max(0.5, r), 0, Math.PI * 2); ctx.fill(); if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1.5; ctx.stroke(); } }
export function rrect(ctx, x, y, w, h, r, fill, stroke, lw = 2) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); } }
export function seg(ctx, x1, y1, x2, y2, color = INK, w = 2, dash) { ctx.strokeStyle = color; ctx.lineWidth = w; if (dash) ctx.setLineDash(dash); ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.setLineDash([]); }
export function arr(ctx, x1, y1, x2, y2, color = EMBER, w = 2.5) { if (Math.hypot(x2 - x1, y2 - y1) > 3) arrow(ctx, x1, y1, x2, y2, color, w, 9); }
export function sky(ctx, w, h, groundY) { ctx.fillStyle = SKY; ctx.fillRect(0, 0, w, groundY); ctx.fillStyle = GROUND; ctx.fillRect(0, groundY, w, h - groundY); seg(ctx, 0, groundY, w, groundY, "#9aa58c", 2); }
/** Dimension line with a label between two points. */
export function dim(ctx, x1, y1, x2, y2, text, color = "#4D5769", off = 14) {
  const a = Math.atan2(y2 - y1, x2 - x1), nx = -Math.sin(a) * off, ny = Math.cos(a) * off;
  seg(ctx, x1 + nx, y1 + ny, x2 + nx, y2 + ny, color, 1.2);
  seg(ctx, x1 + nx * 0.6, y1 + ny * 0.6, x1 + nx * 1.4, y1 + ny * 1.4, color, 1.2); seg(ctx, x2 + nx * 0.6, y2 + ny * 0.6, x2 + nx * 1.4, y2 + ny * 1.4, color, 1.2);
  small(ctx, text, (x1 + x2) / 2 + nx * 2, (y1 + y2) / 2 + ny * 2, { color });
}
/** Thermometer with a red column from lo..hi °C range. */
export function thermometer(ctx, x, y, hgt, T_c, lo = -20, hi = 120) {
  const f = clamp((finite(T_c) - lo) / (hi - lo), 0, 1);
  rrect(ctx, x - 7, y, 14, hgt, 7, "#fff", INK, 1.5); ball(ctx, x, y + hgt + 6, 11, "#d33", INK);
  ctx.fillStyle = "#d33"; ctx.fillRect(x - 3, y + hgt * (1 - f), 6, hgt * f + 6);
  small(ctx, `${fmt(T_c, 4)} °C`, x, y - 12);
}
/** Beaker outline (returns the inner box). */
export function beakerShape(ctx, x, y, bw, bh, fillFrac = 0.6, liquid = WATER) {
  const lvl = y + bh * (1 - clamp(fillFrac, 0, 1));
  ctx.fillStyle = liquid; ctx.fillRect(x + 3, lvl, bw - 6, y + bh - lvl - 3);
  ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x, y + 4); ctx.lineTo(x, y + bh); ctx.lineTo(x + bw, y + bh); ctx.lineTo(x + bw, y + 4); ctx.lineTo(x + bw + 6, y); ctx.stroke();
  return { lvl, x0: x + 3, x1: x + bw - 3, bottom: y + bh - 3 };
}
export function flame(ctx, x, y, size, t) {
  const s = size * (0.9 + 0.1 * Math.sin(t * 18));
  const g = ctx.createLinearGradient(0, y - s, 0, y); g.addColorStop(0, "rgba(120,150,255,0)"); g.addColorStop(0.5, "rgba(90,130,255,.8)"); g.addColorStop(1, "rgba(60,90,230,1)");
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - size * 0.25, y); ctx.quadraticCurveTo(x, y - s * 1.3, x + size * 0.25, y); ctx.fill();
  ctx.fillStyle = "#5b6270"; ctx.fillRect(x - 6, y, 12, 26);
}
/** Molecules bouncing in a box, deterministic in time; speed scales with `speed` (0..1). */
export function molecules(ctx, x, y, bw, bh, n, t, speed = 0.5, color = "#2a78d6", r = 4, seed = 1) {
  for (let i = 0; i < n; i++) {
    const a = (i * 97.13 + seed * 13.7) % 1, b = (i * 57.31 + seed * 7.9) % 1, va = 0.3 + ((i * 31.7) % 1), vb = 0.3 + ((i * 17.3) % 1);
    const sp = 0.05 + speed * 0.6;
    const px = Math.abs(((a + t * sp * va) % 2 + 2) % 2 - 1), py = Math.abs(((b + t * sp * vb * 0.8) % 2 + 2) % 2 - 1);
    ball(ctx, x + r + px * (bw - 2 * r), y + r + py * (bh - 2 * r), r, typeof color === "function" ? color(i) : color);
  }
}
export function wavePath(ctx, x0, x1, yMid, amp, lambdaPx, phase, color = "#2a78d6", w = 2.5) {
  ctx.strokeStyle = color; ctx.lineWidth = w; ctx.beginPath();
  for (let x = x0; x <= x1; x += 2) { const y = yMid + amp * Math.sin((2 * Math.PI * (x - x0)) / lambdaPx - phase); if (x === x0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }
  ctx.stroke();
}
/** Visible-spectrum colour for a wavelength in metres (grey outside 380..750 nm). */
export function waveColour(lamM) {
  const nm = finite(lamM) * 1e9;
  if (nm < 380 || nm > 750) return nm < 380 ? "#8a63d2" : "#9b3b3b";
  const stops = [[380, [120, 0, 200]], [440, [40, 60, 255]], [490, [0, 200, 220]], [530, [40, 200, 40]], [580, [240, 220, 0]], [620, [255, 120, 0]], [750, [200, 0, 0]]];
  for (let i = 1; i < stops.length; i++) if (nm <= stops[i][0]) { const [a, ca] = stops[i - 1], [b, cb] = stops[i], f = (nm - a) / (b - a); return `rgb(${ca.map((v, k) => Math.round(v + (cb[k] - v) * f)).join(",")})`; }
  return "#c00";
}
/** Hot-body colour for a temperature in kelvin (dull red to white-blue). */
export function glowColour(Tk) {
  const f = clamp((finite(Tk) - 700) / 6000, 0, 1);
  const r = 255, g = Math.round(60 + 195 * Math.min(1, f * 1.6)), b = Math.round(20 + 235 * Math.max(0, f * 1.4 - 0.4));
  return finite(Tk) < 700 ? "#5a5f6b" : `rgb(${r},${Math.min(255, g)},${Math.min(255, b)})`;
}
export function car(ctx, x, y, len = 80, colour = INK) {
  rrect(ctx, x - len / 2, y - len * 0.33, len, len * 0.28, 7, colour);
  rrect(ctx, x - len * 0.25, y - len * 0.5, len * 0.45, len * 0.2, 6, colour);
  ctx.fillStyle = "#cfe3f7"; ctx.fillRect(x - len * 0.2, y - len * 0.46, len * 0.16, len * 0.13); ctx.fillRect(x + 0.02 * len, y - len * 0.46, len * 0.15, len * 0.13);
  ball(ctx, x - len * 0.28, y - len * 0.05, len * 0.1, "#333"); ball(ctx, x + len * 0.28, y - len * 0.05, len * 0.1, "#333");
}
export function person(ctx, x, y, s = 1, colour = INK) {
  ctx.strokeStyle = colour; ctx.lineWidth = 3 * s; ball(ctx, x, y - 52 * s, 8 * s, colour);
  ctx.beginPath(); ctx.moveTo(x, y - 44 * s); ctx.lineTo(x, y - 18 * s); ctx.moveTo(x, y - 18 * s); ctx.lineTo(x - 9 * s, y); ctx.moveTo(x, y - 18 * s); ctx.lineTo(x + 9 * s, y); ctx.moveTo(x - 12 * s, y - 36 * s); ctx.lineTo(x + 12 * s, y - 36 * s); ctx.stroke();
}
export function block(ctx, x, y, bw, bh, text, fill = EMBER) { rrect(ctx, x - bw / 2, y - bh, bw, bh, 5, fill, INK, 2); if (text) T(ctx, text, x, y - bh / 2, { color: "#fff", halo: null, font: "700 12px Plex, system-ui" }); }
