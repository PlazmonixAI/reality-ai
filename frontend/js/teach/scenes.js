// ASM Teach classroom pictures. Every number drawn here comes from the engine's teach.experiment result (outputs,
// scene roles and the swept graph); the browser only lays them out and animates them.
import { cssVar } from "../core/ui.js";
import { fmt } from "../core/format.js";
import { arrow, label, niceStep } from "../core/stage.js";

const INK = "#0B1526", EMBER = "#FF5B2E";
const col = () => ({ s1: cssVar("--series-1") || "#2a78d6", s2: cssVar("--series-2") || "#eb6834", s3: cssVar("--series-3") || "#1baf7a",
  text: cssVar("--text") || INK, text2: cssVar("--text-2") || "#4D5769", text3: cssVar("--text-3") || "#7D8698", grid: cssVar("--grid") || "#e3e8ef" });
const num = (v, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v : d);
const T = (ctx, text, x, y, o = {}) => label(ctx, text, x, y, { color: o.color || INK, font: o.font || "600 14px Plex, system-ui", align: o.align || "center", baseline: o.baseline || "middle", halo: o.halo });

function outputsOf(res) { return Object.fromEntries((res.outputs || []).map((o) => [o.name, o])); }
function paramMax(res, name) { return num(res.params?.find((p) => p.name === name)?.max, 1); }

// ---------------------------------------------------------------- generic pieces
function plotArea(ctx, w, h, xs, ys, { pad = 46, equal = false, ground = false, c }) {
  let xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  if (ground) ymin = Math.min(ymin, 0);
  if (xmax - xmin < 1e-12) { xmin -= 1; xmax += 1; }
  if (ymax - ymin < 1e-12) { ymin -= 1; ymax += 1; }
  let sx = (w - 2 * pad) / (xmax - xmin), sy = (h - 2 * pad) / (ymax - ymin);
  if (equal) { const s = Math.min(sx, sy); sx = sy = s; }
  const ox = pad + ((w - 2 * pad) - (xmax - xmin) * sx) / 2, oy = h - pad - ((h - 2 * pad) - (ymax - ymin) * sy) / 2;
  const X = (x) => ox + (x - xmin) * sx, Y = (y) => oy - (y - ymin) * sy;
  ctx.strokeStyle = c.grid; ctx.lineWidth = 1; ctx.font = "11px system-ui";
  const xstep = niceStep(xmax - xmin, 6), ystep = niceStep(ymax - ymin, 5);
  for (let v = Math.ceil(xmin / xstep) * xstep; v <= xmax + 1e-9; v += xstep) {
    ctx.beginPath(); ctx.moveTo(X(v), Y(ymin)); ctx.lineTo(X(v), Y(ymax)); ctx.stroke();
    T(ctx, fmt(Math.abs(v) < xstep * 1e-6 ? 0 : v, 3), X(v), Y(ymin) + 14, { color: c.text3, font: "11px system-ui" });
  }
  for (let v = Math.ceil(ymin / ystep) * ystep; v <= ymax + 1e-9; v += ystep) {
    ctx.beginPath(); ctx.moveTo(X(xmin), Y(v)); ctx.lineTo(X(xmax), Y(v)); ctx.stroke();
    T(ctx, fmt(Math.abs(v) < ystep * 1e-6 ? 0 : v, 3), X(xmin) - 6, Y(v), { color: c.text3, font: "11px system-ui", align: "right" });
  }
  ctx.strokeStyle = c.text3; ctx.lineWidth = 1.2;
  if (ymin <= 0 && ymax >= 0) { ctx.beginPath(); ctx.moveTo(X(xmin), Y(0)); ctx.lineTo(X(xmax), Y(0)); ctx.stroke(); }
  if (xmin <= 0 && xmax >= 0) { ctx.beginPath(); ctx.moveTo(X(0), Y(ymin)); ctx.lineTo(X(0), Y(ymax)); ctx.stroke(); }
  return { X, Y };
}

function line(ctx, pts, color, width = 2.5, dash = []) {
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash); ctx.lineJoin = "round";
  ctx.beginPath(); let pen = false;
  for (const [x, y] of pts) { if (!Number.isFinite(x) || !Number.isFinite(y)) { pen = false; continue; } if (pen) ctx.lineTo(x, y); else { ctx.moveTo(x, y); pen = true; } }
  ctx.stroke(); ctx.setLineDash([]);
}

function ball(ctx, x, y, r, fill) { ctx.fillStyle = fill; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); }

// ---------------------------------------------------------------- scenes
const SCENES = {
  gauges(ctx, w, h, res, t, c) {
    // The main equation large, and the computed outputs as big numbers: what a teacher writes up first.
    const outs = res.outputs || [];
    T(ctx, res.equations?.[0]?.pretty || res.title, w / 2, h * 0.2, { font: `600 ${Math.min(40, w / 16)}px Plex, system-ui` });
    const n = Math.min(outs.length, 4), cw = Math.min(260, (w - 40) / Math.max(n, 1));
    outs.slice(0, 4).forEach((o, i) => {
      const x = w / 2 + (i - (n - 1) / 2) * cw, y = h * 0.58;
      T(ctx, o.label, x, y - 34, { color: c.text2, font: "13px Plex, system-ui" });
      T(ctx, `${fmt(o.value, 4)}${o.unit ? " " + o.unit : ""}`, x, y, { color: i === 0 ? EMBER : INK, font: `600 ${Math.min(30, cw / 7)}px Plex, system-ui` });
    });
  },

  graph(ctx, w, h, res, t, c) {
    const g = res.graph;
    if (!g) return SCENES.gauges(ctx, w, h, res, t, c);
    const xs = g.x.values, all = g.series.flatMap((s) => s.values.filter((v) => v !== null));
    if (!all.length) return SCENES.gauges(ctx, w, h, res, t, c);
    const lo = Math.min(...all), hi = Math.max(...all), span = hi - lo || 1;
    const clip = (v) => (v === null ? NaN : Math.max(lo - span, Math.min(hi + span, v)));
    const { X, Y } = plotArea(ctx, w, h, g.path ? g.series[0].values.filter((v) => v !== null) : xs, g.path ? g.series[1].values.filter((v) => v !== null) : all, { c, equal: g.path });
    const colors = [c.s1, c.s2, c.s3];
    if (g.path) line(ctx, g.series[0].values.map((x, i) => [X(clip(x)), Y(clip(g.series[1].values[i]))]), c.s1, 3);
    else g.series.slice(0, 3).forEach((s, k) => line(ctx, xs.map((x, i) => [X(x), Y(clip(s.values[i]))]), colors[k], 3));
    if (!g.path && g.series.length > 1) g.series.slice(0, 3).forEach((s, k) => T(ctx, `${s.label}`, w - 60, 18 + 18 * k, { color: colors[k], align: "right", font: "600 12px Plex, system-ui" }));
    // a tracer moving along the first curve
    const i = Math.floor(((t * 0.25) % 1) * (xs.length - 1));
    const px = g.path ? g.series[0].values[i] : xs[i], py = g.path ? g.series[1].values[i] : g.series[0].values[i];
    if (px !== null && py !== null) ball(ctx, X(px), Y(clip(py)), 6, EMBER);
  },

  path(ctx, w, h, res, t, c) {
    const g = res.graph;
    if (g?.path) {
      const xs = g.series[0].values, ys = g.series[1].values;
      const { X, Y } = plotArea(ctx, w, h, xs.filter((v) => v !== null), ys.filter((v) => v !== null), { c, equal: true, ground: true });
      ctx.fillStyle = "#e9efe4"; ctx.fillRect(0, Y(0), w, h - Y(0));
      line(ctx, xs.map((x, i) => [X(x), Y(ys[i])]), c.s1, 2, [6, 5]);
      const i = Math.min(xs.length - 1, Math.floor(((t * 0.3) % 1.15) * (xs.length - 1)));
      ball(ctx, X(xs[i]), Y(ys[i]), 9, EMBER);
      const o = outputsOf(res);
      if (o.R) T(ctx, `Range ${fmt(o.R.value, 4)} ${o.R.unit}`, X(xs[xs.length - 1]), Y(0) + 26, { color: c.text2, font: "600 13px Plex, system-ui" });
      if (o.H) T(ctx, `Max height ${fmt(o.H.value, 4)} ${o.H.unit}`, w / 2, 22, { color: c.text2, font: "600 13px Plex, system-ui" });
      return;
    }
    // Straight-line motion: a car drives along a road; speed on screen follows the engine's velocity output.
    const o = outputsOf(res);
    const v = num(o.v?.value ?? o.u?.value ?? o.v_avg?.value, 5);
    const road = h * 0.62;
    ctx.fillStyle = "#dfe3ea"; ctx.fillRect(0, road, w, 36);
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 3; ctx.setLineDash([22, 18]);
    ctx.beginPath(); ctx.moveTo(0, road + 18); ctx.lineTo(w, road + 18); ctx.stroke(); ctx.setLineDash([]);
    const x = ((t * (40 + Math.min(Math.abs(v), 60) * 6)) % (w + 120)) - 60;
    ctx.fillStyle = INK; ctx.beginPath(); ctx.roundRect(x - 40, road - 30, 80, 26, 7); ctx.fill();
    ctx.fillStyle = EMBER; ctx.fillRect(x + 22, road - 26, 12, 8);
    ball(ctx, x - 22, road - 3, 8, "#333"); ball(ctx, x + 22, road - 3, 8, "#333");
    if (o.v) T(ctx, `v = ${fmt(o.v.value, 4)} ${o.v.unit}`, w / 2, road - 70, { font: "600 20px Plex, system-ui" });
    SCENES.caption(ctx, w, h, res, c);
  },

  caption(ctx, w, h, res, c) {
    const eq = res.equations?.[0]?.pretty;
    if (eq) T(ctx, eq, w / 2, h - 26, { color: c.text2, font: "600 16px Plex, system-ui" });
  },

  pendulum(ctx, w, h, res, t, c) {
    const r = res.scene.roles, L = num(r.L, 1), amp = num(r.amp, 10) * Math.PI / 180, P = num(r.T, 2);
    const px = w / 2, py = 30, len = Math.min(h - 90, (h - 90) * Math.min(1, L / paramMax(res, "L") * 1.6));
    const th = amp * Math.cos((2 * Math.PI * t) / P);
    const bx = px + len * Math.sin(th), by = py + len * Math.cos(th);
    ctx.fillStyle = "#c9ced8"; ctx.fillRect(px - 60, py - 8, 120, 8);
    ctx.strokeStyle = c.text3; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, py + len + 20); ctx.stroke(); ctx.setLineDash([]);
    ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(bx, by); ctx.stroke();
    ball(ctx, bx, by, 16, EMBER);
    T(ctx, `L = ${fmt(L, 3)} m`, px + 70, py + len / 2, { align: "left" });
    T(ctx, `T = ${fmt(P, 4)} s`, 20, 24, { align: "left", font: "600 18px Plex, system-ui" });
    SCENES.caption(ctx, w, h, res, c);
  },

  spring(ctx, w, h, res, t, c) {
    const r = res.scene.roles, amp = num(r.amp, 0.1), P = num(r.T, 1);
    const top = 24, rest = h * 0.5, A = Math.min(h * 0.18, 60) * Math.min(1, amp / paramMax(res, "A"));
    const y = rest + A * Math.cos((2 * Math.PI * t) / P), cx = w / 2;
    ctx.fillStyle = "#c9ced8"; ctx.fillRect(cx - 70, top - 10, 140, 10);
    ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx, top);
    const coils = 14;
    for (let i = 1; i <= coils; i++) ctx.lineTo(cx + (i % 2 ? 16 : -16), top + ((y - 26 - top) * i) / (coils + 1));
    ctx.lineTo(cx, y - 26); ctx.stroke();
    ctx.fillStyle = EMBER; ctx.fillRect(cx - 26, y - 26, 52, 52);
    ctx.strokeStyle = c.text3; ctx.setLineDash([5, 5]);
    for (const yy of [rest - A, rest, rest + A]) { ctx.beginPath(); ctx.moveTo(cx + 60, yy); ctx.lineTo(cx + 140, yy); ctx.stroke(); }
    ctx.setLineDash([]);
    T(ctx, "+A", cx + 150, rest - A, { align: "left", color: c.text2 }); T(ctx, "0", cx + 150, rest, { align: "left", color: c.text2 }); T(ctx, "−A", cx + 150, rest + A, { align: "left", color: c.text2 });
    T(ctx, `T = ${fmt(P, 4)} s`, 20, 24, { align: "left", font: "600 18px Plex, system-ui" });
    SCENES.caption(ctx, w, h, res, c);
  },

  wave(ctx, w, h, res, t, c) {
    const g = res.graph, r = res.scene.roles, lam = num(r.lam, 1), f = num(r.f, 1);
    if (!g) return SCENES.gauges(ctx, w, h, res, t, c);
    const xs = g.x.values, ys = g.series[0].values;
    const span = xs[xs.length - 1] - xs[0], amp = Math.max(...ys.map((v) => Math.abs(v ?? 0))) || 1;
    const X = (x) => 30 + ((x - xs[0]) / span) * (w - 60), Y = (y) => h / 2 - (y / amp) * h * 0.3;
    // Travel: sample the engine's snapshot at x − vt, using its periodicity in λ (animation only, slowed down for the eye)
    const shift = ((t * 0.5) % 1) * lam;
    const sample = (x) => { let q = x - shift; while (q < xs[0]) q += lam; const i = (q - xs[0]) / span * (xs.length - 1); const i0 = Math.floor(i), fr = i - i0; return (ys[i0] ?? 0) * (1 - fr) + (ys[i0 + 1] ?? ys[i0] ?? 0) * fr; };
    ctx.strokeStyle = c.grid; ctx.beginPath(); ctx.moveTo(20, h / 2); ctx.lineTo(w - 20, h / 2); ctx.stroke();
    line(ctx, xs.map((x) => [X(x), Y(sample(x))]), c.s1, 3);
    arrow(ctx, X(xs[0]), h / 2 + h * 0.36, X(xs[0] + lam), h / 2 + h * 0.36, c.text2, 1.5, 7);
    T(ctx, `λ = ${fmt(lam, 4)} m`, X(xs[0] + lam / 2), h / 2 + h * 0.36 - 14, { color: c.text2 });
    T(ctx, `f = ${fmt(f, 4)} Hz`, 20, 24, { align: "left", font: "600 18px Plex, system-ui" });
    SCENES.caption(ctx, w, h, res, c);
  },

  circuit(ctx, w, h, res, t, c) {
    const r = res.scene.roles, layout = r.layout || "single", I = num(r.I, 0);
    const x0 = w * 0.18, x1 = w * 0.82, y0 = h * 0.22, y1 = h * 0.72;
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    // battery on the left
    ctx.fillStyle = cssVar("--surface") || "#fff"; ctx.fillRect(x0 - 8, (y0 + y1) / 2 - 22, 16, 44);
    ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x0 - 18, (y0 + y1) / 2 - 10); ctx.lineTo(x0 + 18, (y0 + y1) / 2 - 10); ctx.stroke();
    ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x0 - 9, (y0 + y1) / 2 + 8); ctx.lineTo(x0 + 9, (y0 + y1) / 2 + 8); ctx.stroke();
    T(ctx, `${fmt(num(r.V), 3)} V`, x0 - 30, (y0 + y1) / 2, { align: "right" });
    const resistor = (cx, cy, lab) => { ctx.fillStyle = cssVar("--surface") || "#fff"; ctx.fillRect(cx - 34, cy - 12, 68, 24); ctx.strokeStyle = EMBER; ctx.lineWidth = 3; ctx.strokeRect(cx - 34, cy - 12, 68, 24); T(ctx, lab, cx, cy - 26, { color: c.text2, font: "600 12px Plex, system-ui" }); };
    if (layout === "series") [0.35, 0.55, 0.75].forEach((f, i) => resistor(x0 + (x1 - x0) * f, y0, `R${i + 1}`));
    else if (layout === "parallel") {
      const xs = [0.45, 0.62, 0.79].map((f) => x0 + (x1 - x0) * f);
      xs.forEach((x) => { ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y1); ctx.stroke(); });
      xs.forEach((x, i) => resistor(x, (y0 + y1) / 2, `R${i + 1}`));
    } else resistor((x0 + x1) / 2, y0, `R = ${fmt(num(r.R), 3)} Ω`);
    // moving charges, speed follows the computed current
    const per = 2 * ((x1 - x0) + (y1 - y0)), speed = 30 + 60 * Math.log10(1 + Math.abs(I) * 10);
    for (let k = 0; k < 18; k++) {
      let s = ((t * speed + (k * per) / 18) % per + per) % per, px, py;
      if (s < x1 - x0) { px = x0 + s; py = y0; } else if ((s -= x1 - x0) < y1 - y0) { px = x1; py = y0 + s; }
      else if ((s -= y1 - y0) < x1 - x0) { px = x1 - s; py = y1; } else { s -= x1 - x0; px = x0; py = y1 - s; }
      ball(ctx, px, py, 4, c.s1);
    }
    T(ctx, `I = ${fmt(I, 4)} A`, (x0 + x1) / 2, y1 + 30, { font: "600 18px Plex, system-ui" });
  },

  lens(ctx, w, h, res, t, c, mirror = false) {
    const r = res.scene.roles, u = num(r.u, 30), f = num(r.f, 10), v = num(r.v, 15), m = num(r.m, -0.5);
    const convex = r.kind === "convex";
    const reach = Math.max(u, Math.abs(v), Math.abs(f) * 2, 10) * 1.15;
    const cx = mirror ? w * 0.72 : w * 0.5, cy = h * 0.52, sc = Math.min((mirror ? cx - 30 : w / 2 - 30) / reach, 6);
    const X = (x) => cx + x * sc, ho = Math.min(h * 0.2, 60), Y = (y) => cy - y;
    ctx.strokeStyle = c.text3; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(10, cy); ctx.lineTo(w - 10, cy); ctx.stroke();
    // optic
    ctx.strokeStyle = c.s1; ctx.lineWidth = 3; ctx.beginPath();
    if (mirror) { const bulge = convex ? -14 : 14; ctx.moveTo(cx, cy - h * 0.34); ctx.quadraticCurveTo(cx + bulge, cy, cx, cy + h * 0.34); }
    else { ctx.ellipse(cx, cy, convex ? 12 : 5, h * 0.34, 0, 0, Math.PI * 2); }
    ctx.stroke();
    const fx = mirror ? (convex ? f : -Math.abs(f)) : f;
    for (const x of mirror ? [fx, 2 * fx] : [fx, -fx]) { ball(ctx, X(x), cy, 3.5, c.text2); T(ctx, Math.abs(x) === Math.abs(2 * fx) && mirror ? "C" : "F", X(x), cy + 16, { color: c.text2, font: "12px Plex, system-ui" }); }
    // object at x = -u, image at x = v (Cartesian signs)
    arrow(ctx, X(-u), cy, X(-u), Y(ho), INK, 3, 10);
    const hi = ho * m, ix = X(v);
    if (Number.isFinite(v) && Math.abs(v) < 1e6) {
      const virtual = mirror ? v > 0 : v < 0;
      ctx.setLineDash(virtual ? [6, 5] : []); arrow(ctx, ix, cy, ix, Y(hi), EMBER, 3, 10); ctx.setLineDash([]);
      // two principal rays from the object's tip to the image's tip (both points from the engine)
      ctx.strokeStyle = "rgba(255,91,46,.55)"; ctx.lineWidth = 1.5;
      const tip = [X(-u), Y(ho)], it = [ix, Y(hi)];
      // ray 1: parallel to the axis, then through the focus; ray 2: through the optical centre (or to the pole)
      for (const via of [[cx, Y(ho)], [cx, cy]]) {
        ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(...tip); ctx.lineTo(...via); ctx.stroke();
        ctx.setLineDash(virtual ? [4, 4] : []); ctx.beginPath(); ctx.moveTo(...via); ctx.lineTo(...it); ctx.stroke();
      }
      ctx.setLineDash([]);
      T(ctx, virtual ? "virtual image" : "real image", ix, Y(hi) + (hi > 0 ? -16 : 18), { color: EMBER, font: "600 12px Plex, system-ui" });
    }
    T(ctx, `u = ${fmt(-u, 4)} cm   v = ${fmt(v, 4)} cm   m = ${fmt(m, 3)}`, w / 2, 22, { font: "600 15px Plex, system-ui" });
  },

  mirror(ctx, w, h, res, t, c) { SCENES.lens(ctx, w, h, res, t, c, true); },

  gas(ctx, w, h, res, t, c) {
    const r = res.scene.roles, V = num(r.V, 1), Tk = num(r.T, 300), P = num(r.P, 1);
    const vmax = paramMax(res, "V2") || paramMax(res, "V"), frac = Math.max(0.12, Math.min(1, V / (vmax || V * 1.5)));
    const bx = w * 0.3, bw = w * 0.4, bottom = h * 0.85, full = h * 0.7, top = bottom - full * frac;
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(bx, bottom - full - 10); ctx.lineTo(bx, bottom); ctx.lineTo(bx + bw, bottom); ctx.lineTo(bx + bw, bottom - full - 10); ctx.stroke();
    ctx.fillStyle = "#8a93a3"; ctx.fillRect(bx + 3, top - 14, bw - 6, 14); ctx.fillRect(bx + bw / 2 - 5, top - 60, 10, 46);
    const speed = 40 * Math.sqrt(Tk / 300);
    for (let k = 0; k < 40; k++) {
      const sx = (Math.sin(k * 12.9898) * 43758.5453) % 1, sy = (Math.sin(k * 78.233) * 12345.678) % 1;
      const px = bx + 8 + Math.abs(((Math.abs(sx) * 500 + t * speed * (0.6 + (k % 5) / 5)) % (2 * (bw - 16))) - (bw - 16));
      const py = top + 8 + Math.abs(((Math.abs(sy) * 500 + t * speed * (0.7 + (k % 3) / 4)) % (2 * (bottom - top - 16))) - (bottom - top - 16));
      ball(ctx, px, py, 4, k % 7 ? c.s1 : EMBER);
    }
    const ou = outputsOf(res);
    T(ctx, `P = ${fmt(P, 4)} ${ou.P?.unit || ou.P2?.unit || ""}`, bx + bw + 20, top, { align: "left" });
    T(ctx, `V = ${fmt(V, 4)} L`, bx + bw + 20, top + 24, { align: "left" });
    T(ctx, `T = ${fmt(Tk, 4)} K`, bx + bw + 20, top + 48, { align: "left" });
  },

  beaker(ctx, w, h, res, t, c) {
    const pH = num(res.scene.roles.pH, 7);
    // universal indicator colours from red (0) through green (7) to violet (14)
    const stops = [[0, [210, 30, 40]], [3, [240, 120, 40]], [5, [245, 200, 50]], [7, [80, 170, 70]], [9, [40, 120, 190]], [11, [70, 60, 170]], [14, [110, 40, 140]]];
    let rgb = stops[stops.length - 1][1];
    for (let i = 1; i < stops.length; i++) if (pH <= stops[i][0]) { const [a, ca] = stops[i - 1], [b, cb] = stops[i], f = (pH - a) / (b - a); rgb = ca.map((v, k) => Math.round(v + (cb[k] - v) * f)); break; }
    const bw = Math.min(w * 0.3, 200), bx = w / 2 - bw / 2, bottom = h * 0.82, bh = Math.min(h * 0.6, 260);
    ctx.fillStyle = `rgb(${rgb.join(",")})`; ctx.globalAlpha = 0.8; ctx.fillRect(bx + 4, bottom - bh * 0.65, bw - 8, bh * 0.65 - 4); ctx.globalAlpha = 1;
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(bx - 8, bottom - bh); ctx.lineTo(bx, bottom - bh + 8); ctx.lineTo(bx, bottom); ctx.lineTo(bx + bw, bottom); ctx.lineTo(bx + bw, bottom - bh); ctx.stroke();
    for (let k = 0; k < 6; k++) { const yy = bottom - 20 - ((t * 30 + k * 37) % (bh * 0.6)); ball(ctx, bx + 20 + ((k * 53) % (bw - 40)), yy, 3, "rgba(255,255,255,.7)"); }
    T(ctx, `pH ${fmt(pH, 3)}`, w / 2, bottom - bh - 26, { font: "600 22px Plex, system-ui" });
    T(ctx, pH < 6.5 ? "acidic" : pH > 7.5 ? "basic" : "neutral", w / 2, bottom + 24, { color: c.text2 });
    // scale bar
    const sx = w * 0.12, sw = w * 0.76, sy = h - 22;
    for (let i = 0; i < 14; i++) { let cc = stops[0][1]; for (let j = 1; j < stops.length; j++) if (i + 0.5 <= stops[j][0]) { const [a, ca] = stops[j - 1], [b, cb] = stops[j], f = (i + 0.5 - a) / (b - a); cc = ca.map((v, k) => Math.round(v + (cb[k] - v) * f)); break; } ctx.fillStyle = `rgb(${cc.join(",")})`; ctx.fillRect(sx + (sw / 14) * i, sy - 8, sw / 14, 8); }
    ball(ctx, sx + (sw * Math.max(0, Math.min(14, pH))) / 14, sy - 14, 5, INK);
  },

  titration(ctx, w, h, res, t, c) {
    // A burette over a conical flask. The titrant runs in until the engine's end-point reading V, then the flask turns.
    const r = res.scene.roles, V = Math.max(0.1, num(r.V, 10)), Vf = num(r.Vf, 10), ind = r.ind || "phph";
    const look = { kmno4: { titrant: [106, 27, 106], start: [244, 246, 250], end: [244, 170, 205], name: "KMnO₄ is its own indicator: colourless to pale pink" },
      phph: { titrant: [232, 240, 248], start: [244, 246, 250], end: [246, 150, 196], name: "Phenolphthalein: colourless to pink" },
      mo: { titrant: [232, 240, 248], start: [242, 200, 75], end: [232, 102, 58], name: "Methyl orange: yellow to orange-red" } }[ind] || {};
    const cyc = 9, ph = t % cyc, f = Math.min(1, ph / 6), added = f * V, done = ph >= 6; // 6 s to the end point, then hold
    const full = 50, bx = w * 0.42, top = h * 0.08, bh = h * 0.5, bw = Math.max(16, w * 0.03), y0 = top + 10, yScale = (bh - 20) / full;
    // stand
    ctx.fillStyle = c.text3; ctx.fillRect(w * 0.2, h * 0.93, w * 0.32, 6); ctx.fillRect(w * 0.22, top - 10, 5, h * 0.93 - top + 10);
    ctx.fillRect(w * 0.22, top + bh * 0.3, bx - w * 0.22, 4);
    // burette: liquid from the current reading down to the tap, graduations 0 at the top
    const rgb = (a) => `rgb(${a.join(",")})`;
    ctx.fillStyle = rgb(look.titrant); ctx.globalAlpha = 0.85; ctx.fillRect(bx - bw / 2 + 2, y0 + added * yScale, bw - 4, (full - added) * yScale); ctx.globalAlpha = 1;
    ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.strokeRect(bx - bw / 2, top, bw, bh);
    ctx.lineWidth = 1; ctx.font = "10px system-ui";
    for (let m = 0; m <= full; m += 5) { const y = y0 + m * yScale; ctx.beginPath(); ctx.moveTo(bx - bw / 2, y); ctx.lineTo(bx - bw / 2 + (m % 10 ? 5 : 9), y); ctx.stroke(); if (m % 10 === 0) T(ctx, String(m), bx - bw / 2 - 6, y, { align: "right", color: c.text3, font: "10px system-ui" }); }
    ctx.beginPath(); ctx.moveTo(bx - 3, top + bh); ctx.lineTo(bx - 1.5, top + bh + 26); ctx.lineTo(bx + 1.5, top + bh + 26); ctx.lineTo(bx + 3, top + bh); ctx.stroke();
    ctx.fillStyle = INK; ctx.fillRect(bx - 8, top + bh + 6, 16, 5); // tap
    // conical flask
    const fx = bx, fy = h * 0.92, fw = Math.min(w * 0.22, 150), fh = h * 0.28, neck = fw * 0.22;
    if (!done) for (let k = 0; k < 3; k++) { const dy = ((t * 3 + k / 3) % 1) * (fy - fh - (top + bh + 28)); ball(ctx, bx, top + bh + 30 + dy, 3, rgb(look.titrant)); }
    const col2 = done ? look.end : look.start, liq = fh * (0.35 + 0.15 * f * V / Math.max(V, Vf));
    ctx.save(); ctx.beginPath(); ctx.moveTo(fx - neck / 2, fy - fh); ctx.lineTo(fx - neck / 2, fy - fh * 0.62); ctx.lineTo(fx - fw / 2, fy); ctx.lineTo(fx + fw / 2, fy); ctx.lineTo(fx + neck / 2, fy - fh * 0.62); ctx.lineTo(fx + neck / 2, fy - fh); ctx.closePath();
    ctx.clip(); ctx.fillStyle = rgb(col2); ctx.globalAlpha = 0.9; ctx.fillRect(fx - fw / 2, fy - liq, fw, liq); ctx.restore();
    ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(fx - neck / 2, fy - fh); ctx.lineTo(fx - neck / 2, fy - fh * 0.62); ctx.lineTo(fx - fw / 2, fy); ctx.lineTo(fx + fw / 2, fy); ctx.lineTo(fx + neck / 2, fy - fh * 0.62); ctx.lineTo(fx + neck / 2, fy - fh); ctx.stroke();
    // readings
    // readings, sized to the room beside the burette
    const o = outputsOf(res), tx = Math.max(bx + bw + 40, w * 0.6), room = w - tx - 12, fs = Math.max(10, Math.min(16, room / 15)), gap = fs * 1.6;
    const [indName, indChange] = (look.name || "").split(": ");
    const rows = [[`Burette reading ${fmt(added, 3)} mL`, `600 ${fs}px Plex, system-ui`, c.text],
      [done ? `End point at ${fmt(V, 3)} mL` : "Adding drop by drop", `${fs - 1}px Plex, system-ui`, done ? EMBER : c.text2],
      [`${fmt(Vf, 3)} mL pipetted`, `${fs - 1}px Plex, system-ui`, c.text2],
      [indName || "", `${fs - 3}px Plex, system-ui`, c.text3], [indChange || "", `${fs - 3}px Plex, system-ui`, c.text3], ["", "", ""],
      o.M2 ? [`${o.M2.label.replace(/^Molarity of /, "")}: ${fmt(o.M2.value, 4)} ${o.M2.unit}`, `600 ${fs}px Plex, system-ui`, c.text] : null,
      o.S ? [`${fmt(o.S.value, 4)} ${o.S.unit}`, `${fs - 1}px Plex, system-ui`, c.text2] : null].filter(Boolean);
    rows.forEach(([text, font, color], i) => { if (text) T(ctx, text, tx, h * 0.14 + i * gap, { align: "left", font, color }); });
  },

  atom(ctx, w, h, res, t, c) {
    const r = res.scene.roles, n = Math.round(num(r.n, 1)), Z = Math.round(num(r.Z, 1));
    const cx = w / 2, cy = h / 2, maxN = Math.max(n, 3), R = Math.min(w, h) * 0.42;
    for (let k = 1; k <= maxN; k++) {
      const rr = R * (k * k) / (maxN * maxN) + 18;
      ctx.strokeStyle = k === n ? EMBER : c.grid; ctx.lineWidth = k === n ? 2 : 1;
      ctx.beginPath(); ctx.arc(cx, cy, rr, 0, Math.PI * 2); ctx.stroke();
      T(ctx, `n=${k}`, cx + rr + 4, cy, { align: "left", color: c.text3, font: "11px Plex, system-ui" });
    }
    ball(ctx, cx, cy, 12, INK); T(ctx, `+${Z}`, cx, cy, { color: "#fff", font: "600 11px Plex, system-ui" });
    const rr = R * (n * n) / (maxN * maxN) + 18, a = t * 2 / Math.max(1, n);
    ball(ctx, cx + rr * Math.cos(a), cy + rr * Math.sin(a), 7, c.s1);
    const o = outputsOf(res);
    if (o.E) T(ctx, `E = ${fmt(o.E.value, 4)} ${o.E.unit}`, 20, 24, { align: "left", font: "600 18px Plex, system-ui" });
    if (o.r) T(ctx, `r = ${fmt(o.r.value, 4)} ${o.r.unit}`, 20, 48, { align: "left", color: c.text2 });
  },

  vector(ctx, w, h, res, t, c) {
    const r = res.scene.roles, A = num(r.A, 1), B = num(r.B, 1), th = num(r.th, 60) * Math.PI / 180;
    const bx = B * Math.cos(th), by = B * Math.sin(th);
    const xs = [0, A, bx, A + bx], ys = [0, 0, by, by];
    const { X, Y } = plotArea(ctx, w, h, xs, ys, { c, equal: true, pad: 60 });
    arrow(ctx, X(0), Y(0), X(A), Y(0), c.s1, 3, 12);
    arrow(ctx, X(0), Y(0), X(bx), Y(by), c.s3, 3, 12);
    ctx.setLineDash([5, 5]); ctx.strokeStyle = c.text3; ctx.beginPath(); ctx.moveTo(X(A), Y(0)); ctx.lineTo(X(A + bx), Y(by)); ctx.lineTo(X(bx), Y(by)); ctx.stroke(); ctx.setLineDash([]);
    if (r.R !== undefined) arrow(ctx, X(0), Y(0), X(A + bx), Y(by), EMBER, 3, 12);
    T(ctx, `${fmt(A, 3)}`, X(A / 2), Y(0) + 16, { color: c.s1 });
    T(ctx, `${fmt(B, 3)}`, X(bx / 2) - 12, Y(by / 2), { color: c.s3, align: "right" });
    T(ctx, `θ = ${fmt(th * 180 / Math.PI, 3)}°`, X(0) + 34, Y(0) - 14, { align: "left", color: c.text2 });
  },

  incline(ctx, w, h, res, t, c) {
    const r = res.scene.roles, th = num(r.th, 30) * Math.PI / 180, a = num(r.a, 0);
    const x0 = w * 0.1, y0 = h * 0.85, L = Math.min(w * 0.8, (h * 0.7) / Math.max(Math.sin(th), 0.15));
    const x1 = x0 + L * Math.cos(th), y1 = y0 - L * Math.sin(th);
    ctx.fillStyle = "#e4e8ef"; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y0); ctx.lineTo(x1, y1); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.stroke();
    const period = 3, s = a > 0 ? Math.min(1, 0.5 * a * ((t % period) ** 2) / 9.8 / 1.2) : 0;
    const d = L * (1 - s) - 40, bxp = x0 + d * Math.cos(th), byp = y0 - d * Math.sin(th);
    ctx.save(); ctx.translate(bxp, byp); ctx.rotate(-th); ctx.fillStyle = EMBER; ctx.fillRect(-22, -36, 44, 36); ctx.restore();
    ctx.beginPath(); ctx.arc(x0, y0, 46, -th, 0); ctx.strokeStyle = c.text2; ctx.stroke();
    T(ctx, `${fmt(th * 180 / Math.PI, 3)}°`, x0 + 60, y0 - 14, { align: "left", color: c.text2 });
    T(ctx, a > 0 ? `a = ${fmt(a, 4)} m/s² down the slope` : "The block stays put: friction holds it", w / 2, 26, { font: "600 16px Plex, system-ui" });
  },

  decay(ctx, w, h, res, t, c) {
    const r = res.scene.roles, frac = Math.max(0, Math.min(1, num(r.N, 0) / num(r.N0, 1)));
    const n = 400, cols = 25, rows = 16, size = Math.min((w - 40) / cols, (h - 70) / rows);
    const ox = (w - cols * size) / 2, oy = 40;
    for (let k = 0; k < n; k++) {
      const rank = ((Math.sin(k * 91.17) * 43758.5453) % 1 + 1) % 1; // fixed order in which nuclei decay
      const alive = rank < frac;
      ball(ctx, ox + (k % cols + 0.5) * size, oy + (Math.floor(k / cols) + 0.5) * size, size * 0.36, alive ? EMBER : c.grid);
    }
    T(ctx, `${fmt(frac * 100, 3)}% of nuclei left`, w / 2, 20, { font: "600 16px Plex, system-ui" });
  },

  field(ctx, w, h, res, t, c) {
    const r = res.scene.roles, q = num(r.q, 1), cx = w * 0.4, cy = h / 2;
    const sign = q >= 0 ? 1 : -1;
    ctx.strokeStyle = c.s1; ctx.lineWidth = 1.5;
    for (let k = 0; k < 16; k++) {
      const a = (k / 16) * Math.PI * 2, r0 = 22, r1 = Math.min(w, h) * 0.45;
      arrow(ctx, cx + r0 * Math.cos(a), cy + r0 * Math.sin(a), cx + r1 * Math.cos(a), cy + r1 * Math.sin(a), c.s1, 1.5, sign > 0 ? 8 : 0);
      if (sign < 0) arrow(ctx, cx + r1 * Math.cos(a), cy + r1 * Math.sin(a), cx + (r1 - 30) * Math.cos(a), cy + (r1 - 30) * Math.sin(a), c.s1, 1.5, 8);
    }
    ball(ctx, cx, cy, 18, sign > 0 ? EMBER : c.s1); T(ctx, sign > 0 ? "+" : "−", cx, cy, { color: "#fff", font: "700 20px Plex, system-ui" });
    const rr = Math.min(w * 0.45, 60 + 40 * Math.log10(1 + num(r.r, 1)));
    ball(ctx, cx + rr, cy, 6, INK); T(ctx, `r = ${fmt(num(r.r), 3)}`, cx + rr, cy - 16, { color: c.text2 });
    SCENES.caption(ctx, w, h, res, c);
  },

  prism(ctx, w, h, res, t, c) {
    const r = res.scene.roles, deg = Math.PI / 180;
    const A = num(r.A, 60) * deg, i = num(r.i, 45) * deg, r1 = num(r.r1, 28) * deg, e = num(r.e, 45) * deg, a = A / 2;
    const cx = w / 2, base = h * 0.82, slant = Math.min(h * 0.68 / Math.cos(a), w * 0.3 / Math.sin(a));
    const apex = [cx, base - slant * Math.cos(a)], L = [cx - slant * Math.sin(a), base], R = [cx + slant * Math.sin(a), base];
    ctx.fillStyle = "rgba(42,120,214,.1)"; ctx.strokeStyle = c.s1; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(...apex); ctx.lineTo(...L); ctx.lineTo(...R); ctx.closePath(); ctx.fill(); ctx.stroke();
    // Screen angles (y down). Inward normal of the left face points at +a; the outward normal of the right face at −a.
    const dir = (ang) => [Math.cos(ang), Math.sin(ang)];
    const P = [(apex[0] * 0.55 + L[0] * 0.45), (apex[1] * 0.55 + L[1] * 0.45)];
    const din = dir(a - i), dr = dir(a - r1), nR = dir(-a), Rf = [(apex[0] + R[0]) / 2, (apex[1] + R[1]) / 2];
    const tHit = ((Rf[0] - P[0]) * nR[0] + (Rf[1] - P[1]) * nR[1]) / (dr[0] * nR[0] + dr[1] * nR[1]);
    const Q = [P[0] + dr[0] * tHit, P[1] + dr[1] * tHit], dout = dir(-a + e);
    line(ctx, [[P[0] - din[0] * 170, P[1] - din[1] * 170], P], EMBER, 2.5);
    if (Number.isFinite(tHit) && tHit > 0) {
      line(ctx, [P, Q], EMBER, 2.5);
      line(ctx, [Q, [Q[0] + dout[0] * 170, Q[1] + dout[1] * 170]], EMBER, 2.5);
      line(ctx, [P, [P[0] + din[0] * 150, P[1] + din[1] * 150]], c.text3, 1, [5, 5]); // undeviated path, to show δ
    }
    T(ctx, `A = ${fmt(num(r.A), 3)}°   i = ${fmt(num(r.i), 3)}°   e = ${fmt(num(r.e), 3)}°   δ = ${fmt(num(r.delta), 4)}°`, w / 2, 22, { font: "600 15px Plex, system-ui" });
  },

  lever(ctx, w, h, res, t, c) {
    const r = res.scene.roles, la = num(r.la, 0.2), ea = num(r.ea, 1);
    const cx = w * (0.15 + 0.7 * la / (la + ea)), y = h * 0.55, sc = (w * 0.7) / (la + ea);
    ctx.fillStyle = INK; ctx.beginPath(); ctx.moveTo(cx, y); ctx.lineTo(cx - 18, y + 34); ctx.lineTo(cx + 18, y + 34); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#8a93a3"; ctx.fillRect(cx - la * sc, y - 8, (la + ea) * sc, 8);
    ctx.fillStyle = EMBER; ctx.fillRect(cx - la * sc - 20, y - 48, 40, 40);
    arrow(ctx, cx + ea * sc, y - 80, cx + ea * sc, y - 12, c.s1, 3, 10);
    T(ctx, `load ${fmt(num(r.L), 4)} N`, cx - la * sc, y - 60);
    T(ctx, `effort ${fmt(num(r.E), 4)} N`, cx + ea * sc, y - 92, { color: c.s1 });
    T(ctx, `${fmt(la, 3)} m`, cx - (la * sc) / 2, y + 22, { color: c.text2 }); T(ctx, `${fmt(ea, 3)} m`, cx + (ea * sc) / 2, y + 22, { color: c.text2 });
  },

  shape(ctx, w, h, res, t, c) {
    const r = res.scene.roles, kind = r.kind, a = num(r.a, 1), b = num(r.b, 1), cc = num(r.c, 1);
    const cx = w / 2, cy = h / 2, S = Math.min(w, h) * 0.34;
    ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.fillStyle = "rgba(255,91,46,.12)";
    const lab = (s, x, y, o) => T(ctx, s, x, y, { color: c.text2, font: "600 13px Plex, system-ui", ...o });
    if (kind === "triangle") {
      const cosC = (a * a + b * b - cc * cc) / (2 * a * b), C = Math.acos(Math.max(-1, Math.min(1, cosC))), k = (2 * S) / Math.max(a, b, cc);
      const P = [cx - (a * k) / 2, cy + S * 0.5], Q = [P[0] + a * k, P[1]], R = [P[0] + b * k * Math.cos(C), P[1] - b * k * Math.sin(C)];
      ctx.beginPath(); ctx.moveTo(...P); ctx.lineTo(...Q); ctx.lineTo(...R); ctx.closePath(); ctx.fill(); ctx.stroke();
      lab(`a = ${fmt(a, 3)}`, (P[0] + Q[0]) / 2, P[1] + 16); lab(`b = ${fmt(b, 3)}`, (P[0] + R[0]) / 2 - 30, (P[1] + R[1]) / 2); lab(`c = ${fmt(cc, 3)}`, (Q[0] + R[0]) / 2 + 30, (Q[1] + R[1]) / 2);
    } else if (kind === "triangle_angles") {
      const A = a * Math.PI / 180, B = b * Math.PI / 180, base = 2 * S, hgt = base / (1 / Math.tan(A) + 1 / Math.tan(B));
      const P = [cx - S, cy + S * 0.5], Q = [cx + S, cy + S * 0.5], R = [P[0] + hgt / Math.tan(A), P[1] - hgt];
      ctx.beginPath(); ctx.moveTo(...P); ctx.lineTo(...Q); ctx.lineTo(...R); ctx.closePath(); ctx.fill(); ctx.stroke();
      lab(`${fmt(a, 3)}°`, P[0] + 34, P[1] - 12); lab(`${fmt(b, 3)}°`, Q[0] - 34, Q[1] - 12); lab(`${fmt(180 - a - b, 3)}°`, R[0], R[1] + 26, { color: EMBER });
    } else if (kind === "circle_chord" || kind === "sector") {
      ctx.beginPath(); ctx.arc(cx, cy, S, 0, Math.PI * 2); ctx.stroke();
      if (kind === "sector") { const th = b * Math.PI / 180; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, S, -Math.PI / 2, -Math.PI / 2 + th); ctx.closePath(); ctx.fill(); ctx.stroke(); lab(`${fmt(b, 3)}°`, cx + 18, cy - 20); }
      else { const d = Math.min(0.999, b / a) * S, half = Math.sqrt(Math.max(0, S * S - d * d)); ctx.beginPath(); ctx.moveTo(cx - half, cy - d); ctx.lineTo(cx + half, cy - d); ctx.strokeStyle = EMBER; ctx.stroke(); ctx.setLineDash([5, 5]); ctx.strokeStyle = c.text2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx, cy - d); ctx.stroke(); ctx.setLineDash([]); lab(`d = ${fmt(b, 3)}`, cx + 30, cy - d / 2); }
      lab(`r = ${fmt(a, 3)}`, cx, cy + S + 18);
    } else if (kind === "tower") {
      const th = b * Math.PI / 180, base = w * 0.55, hh = Math.min(h * 0.75, base * Math.tan(th)), bx = w * 0.2, by = h * 0.85;
      ctx.fillStyle = "#c9ced8"; ctx.fillRect(bx + base - 14, by - hh, 28, hh);
      ctx.strokeStyle = EMBER; ctx.setLineDash([6, 5]); ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx + base, by - hh); ctx.stroke(); ctx.setLineDash([]);
      ctx.strokeStyle = INK; ctx.beginPath(); ctx.moveTo(bx - 20, by); ctx.lineTo(bx + base + 40, by); ctx.stroke();
      lab(`${fmt(a, 3)} m`, bx + base / 2, by + 16); lab(`${fmt(b, 3)}°`, bx + 44, by - 12);
      const o = outputsOf(res); if (o.h) lab(`h = ${fmt(o.h.value, 4)} m`, bx + base + 30, by - hh / 2, { align: "left", color: INK });
    } else {
      // solids: a clean 2D sketch with the dimensions
      if (kind === "sphere") { ctx.beginPath(); ctx.arc(cx, cy, S, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.ellipse(cx, cy, S, S * 0.28, 0, 0, Math.PI * 2); ctx.setLineDash([5, 5]); ctx.stroke(); ctx.setLineDash([]); lab(`r = ${fmt(a, 3)}`, cx + S / 2, cy - 12); }
      else if (kind === "cylinder" || kind === "cone") {
        const rw = S * 0.7, hh = S * 1.5 * Math.min(1.4, b / Math.max(a, 1e-9) / 2 + 0.3), top = cy - hh / 2, bot = cy + hh / 2;
        ctx.beginPath(); ctx.ellipse(cx, bot, rw, rw * 0.28, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        if (kind === "cylinder") { ctx.beginPath(); ctx.ellipse(cx, top, rw, rw * 0.28, 0, 0, Math.PI * 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(cx - rw, top); ctx.lineTo(cx - rw, bot); ctx.moveTo(cx + rw, top); ctx.lineTo(cx + rw, bot); ctx.stroke(); }
        else { ctx.beginPath(); ctx.moveTo(cx - rw, bot); ctx.lineTo(cx, top); ctx.lineTo(cx + rw, bot); ctx.stroke(); }
        lab(`r = ${fmt(a, 3)}`, cx + rw / 2, bot + 26); lab(`h = ${fmt(b, 3)}`, cx + rw + 30, cy, { align: "left" });
      } else if (kind === "cuboid") {
        const k = (1.6 * S) / Math.max(a, b, cc), L = a * k, B = b * k * 0.5, H = cc * k, x0 = cx - L / 2 - B / 2, y0 = cy + H / 2;
        ctx.beginPath(); ctx.rect(x0, y0 - H, L, H); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x0, y0 - H); ctx.lineTo(x0 + B, y0 - H - B); ctx.lineTo(x0 + L + B, y0 - H - B); ctx.lineTo(x0 + L, y0 - H); ctx.moveTo(x0 + L + B, y0 - H - B); ctx.lineTo(x0 + L + B, y0 - B); ctx.lineTo(x0 + L, y0); ctx.stroke();
        lab(`${fmt(a, 3)}`, x0 + L / 2, y0 + 16); lab(`${fmt(b, 3)}`, x0 + L + B / 2 + 20, y0 - B / 2); lab(`${fmt(cc, 3)}`, x0 - 24, y0 - H / 2);
      }
    }
    SCENES.caption(ctx, w, h, res, c);
  },
};

/** Draw the experiment's picture for animation time t (seconds). */
export function drawScene(ctx, w, h, res, t) {
  ctx.clearRect(0, 0, w, h);
  if (!res) return;
  const draw = SCENES[res.scene?.type] || SCENES.gauges;
  const c = col();
  ctx.save();
  try { draw(ctx, w, h, res, t, c); } catch (err) { console.error(err); SCENES.gauges(ctx, w, h, res, t, c); }
  ctx.restore();
}
