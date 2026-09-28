// Shared 2D plotting helpers for the mathematics sims: axes with ticks, curves with gaps, robust y-range.
import { niceStep, label } from "../core/stage.js";
import { fmt } from "../core/format.js";

/** Draw grid + axes for x in [x0, x1], y in [y0, y1]; returns {X, Y, inv} mapping helpers. */
export function axes(ctx, w, h, [x0, x1], [y0, y1], { pad = 36, equal = false } = {}) {
  let sx = (w - 2 * pad) / (x1 - x0), sy = (h - 2 * pad) / (y1 - y0);
  if (equal) { const s = Math.min(sx, sy); sx = sy = s; }
  const cx = w / 2 - ((x0 + x1) / 2) * sx, cy = h / 2 + ((y0 + y1) / 2) * sy;
  const X = (v) => cx + v * sx, Y = (v) => cy - v * sy;
  const inv = (px, py) => [(px - cx) / sx, (cy - py) / sy];
  const [vx0, vy1] = inv(0, 0), [vx1, vy0] = inv(w, h);
  ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
  const xs = niceStep(vx1 - vx0, Math.max(3, Math.floor(w / 90))), ys = niceStep(vy1 - vy0, Math.max(3, Math.floor(h / 70)));
  ctx.lineWidth = 1;
  for (let v = Math.ceil(vx0 / xs) * xs; v <= vx1; v += xs) {
    ctx.strokeStyle = "#eef1f5"; ctx.beginPath(); ctx.moveTo(X(v), 0); ctx.lineTo(X(v), h); ctx.stroke();
    if (Math.abs(v) > xs / 2) label(ctx, fmt(v, 3), X(v), Math.min(h - 8, Math.max(8, Y(0) + 12)), { align: "center", font: "11px system-ui", color: "#4b5868" });
  }
  for (let v = Math.ceil(vy0 / ys) * ys; v <= vy1; v += ys) {
    ctx.strokeStyle = "#eef1f5"; ctx.beginPath(); ctx.moveTo(0, Y(v)); ctx.lineTo(w, Y(v)); ctx.stroke();
    if (Math.abs(v) > ys / 2) label(ctx, fmt(v, 3), Math.min(w - 30, Math.max(4, X(0) + 6)), Y(v), { font: "11px system-ui", color: "#4b5868" });
  }
  ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.moveTo(X(0), 0); ctx.lineTo(X(0), h); ctx.stroke();
  return { X, Y, inv };
}

/** Polyline with breaks at null values and at huge jumps (asymptotes). */
export function curve(ctx, m, xs, ys, color, { width = 2.5, dash = false, jump = Infinity } = {}) {
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash ? [7, 5] : []); ctx.beginPath();
  let pen = false, prev = null;
  xs.forEach((x, i) => {
    const y = ys[i];
    if (y === null || !Number.isFinite(y) || (prev !== null && Math.abs(y - prev) > jump)) { pen = false; prev = y; if (y === null) return; }
    if (pen) ctx.lineTo(m.X(x), m.Y(y)); else { ctx.moveTo(m.X(x), m.Y(y)); pen = true; }
    prev = y;
  });
  ctx.stroke(); ctx.setLineDash([]);
}

/** y-range from the 3rd..97th percentile of the values, padded, always including 0. */
export function robustRange(values, { includeZero = true } = {}) {
  const v = values.filter((y) => y !== null && Number.isFinite(y)).sort((a, b) => a - b);
  if (!v.length) return [-1, 1];
  let lo = v[Math.floor(v.length * 0.03)], hi = v[Math.ceil(v.length * 0.97) - 1];
  if (includeZero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  const pad = (hi - lo || 2) * 0.12;
  return [lo - pad, hi + pad];
}
