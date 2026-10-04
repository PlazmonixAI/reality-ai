// Maths worlds: the idea made visible with real objects and moving pictures, not only a curve.
import { fmt } from "../core/format.js";
import { INK, EMBER, T, small, big, ball, rrect, seg, arr, dim, soft, clamp, cyc, finite } from "./worlds.js";

const BLUE = "#2a78d6", GREEN = "#1baf7a", ORANGE = "#eb6834", PURPLE = "#8a63d2";
const bg = (ctx, w, h) => { ctx.fillStyle = "#fbfbf8"; ctx.fillRect(0, 0, w, h); };

/** World-to-screen mapping that fits the given points with equal scales. */
function fit(w, h, pts, pad = 50) {
  const xs = pts.map((p) => p[0]).concat([0]), ys = pts.map((p) => p[1]).concat([0]);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  if (x1 - x0 < 1e-9) { x0 -= 1; x1 += 1; } if (y1 - y0 < 1e-9) { y0 -= 1; y1 += 1; }
  const s = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0)), ox = (w - (x1 - x0) * s) / 2, oy = (h + (y1 - y0) * s) / 2;
  return { X: (x) => ox + (x - x0) * s, Y: (y) => oy - (y - y0) * s, s, x0, x1, y0, y1 };
}
function axes(ctx, w, h, m) {
  ctx.strokeStyle = "#e3e8ef"; ctx.lineWidth = 1;
  const step = Math.pow(10, Math.floor(Math.log10((m.x1 - m.x0) / 2))) || 1;
  for (let v = Math.ceil(m.x0 / step) * step; v <= m.x1; v += step) { ctx.beginPath(); ctx.moveTo(m.X(v), 0); ctx.lineTo(m.X(v), h); ctx.stroke(); }
  for (let v = Math.ceil(m.y0 / step) * step; v <= m.y1; v += step) { ctx.beginPath(); ctx.moveTo(0, m.Y(v)); ctx.lineTo(w, m.Y(v)); ctx.stroke(); }
  seg(ctx, 0, m.Y(0), w, m.Y(0), "#9aa3b2", 1.5); seg(ctx, m.X(0), 0, m.X(0), h, "#9aa3b2", 1.5);
}

export const MATH = {
  /** Points, segments and shaded polygons on a grid. pts [{x,y,label}], segs [[i,j]], poly [i...], note lines. */
  plane(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const P = (a.pts || []).map((p) => [finite(p.x), finite(p.y)]);
    const m = fit(w, h, P.length ? P : [[0, 0], [1, 1]]); axes(ctx, w, h, m);
    if (a.poly) { ctx.fillStyle = "rgba(255,91,46,.15)"; ctx.beginPath(); a.poly.forEach((i) => ctx.lineTo(m.X(P[i][0]), m.Y(P[i][1]))); ctx.closePath(); ctx.fill(); }
    (a.segs || []).forEach(([i, j], k) => { const draw = Math.min(1, cyc(t, 4) * 2.5 - k * 0.3); if (draw <= 0) return; seg(ctx, m.X(P[i][0]), m.Y(P[i][1]), m.X(P[i][0] + (P[j][0] - P[i][0]) * draw), m.Y(P[i][1] + (P[j][1] - P[i][1]) * draw), k ? BLUE : EMBER, 3); });
    if (a.line) { const [A, B, C] = a.line.map(finite); const xs = [m.x0 - 10, m.x1 + 10]; if (Math.abs(B) > 1e-9) seg(ctx, m.X(xs[0]), m.Y(-(A * xs[0] + C) / B), m.X(xs[1]), m.Y(-(A * xs[1] + C) / B), BLUE, 2.5); else seg(ctx, m.X(-C / A), 0, m.X(-C / A), h, BLUE, 2.5); }
    (a.pts || []).forEach((p, i) => { ball(ctx, m.X(P[i][0]), m.Y(P[i][1]), 6, p.colour || INK); small(ctx, `${p.label || ""}(${fmt(p.x, 3)}, ${fmt(p.y, 3)})`, m.X(P[i][0]) + 8, m.Y(P[i][1]) - 14, { align: "left" }); });
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** Points in space on rotating 3D axes. pts [{x,y,z,label}], segs. */
  space(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const pts = (a.pts || []).map((p) => [finite(p.x), finite(p.y), finite(p.z)]), R = Math.max(1, ...pts.flat().map(Math.abs));
    const ang = t * 0.35, el = 0.45, s = Math.min(w, h) * 0.32 / R, cx = w / 2, cy = h / 2;
    const P = ([x, y, z]) => { const X = x * Math.cos(ang) - y * Math.sin(ang), Y = x * Math.sin(ang) + y * Math.cos(ang); return [cx + X * s, cy - (z * Math.cos(el) - Y * Math.sin(el)) * s]; };
    [[R, 0, 0, "x"], [0, R, 0, "y"], [0, 0, R, "z"]].forEach(([x, y, z, n]) => { const [px, py] = P([x * 1.2, y * 1.2, z * 1.2]); const [ox, oy] = P([0, 0, 0]); arr(ctx, ox, oy, px, py, "#9aa3b2", 1.5); small(ctx, n, px + 8, py); });
    (a.lineDirs || []).forEach((d, k) => { const p0 = d.p || [0, 0, 0], v = d.v.map(finite), L = R * 1.2 / Math.max(1e-9, Math.hypot(...v)); const [x1, y1] = P(p0.map((q, i) => q - v[i] * L)), [x2, y2] = P(p0.map((q, i) => q + v[i] * L)); seg(ctx, x1, y1, x2, y2, k ? BLUE : EMBER, 3); });
    (a.segs || []).forEach(([i, j]) => { const [x1, y1] = P(pts[i]), [x2, y2] = P(pts[j]); seg(ctx, x1, y1, x2, y2, EMBER, 3); });
    (a.pts || []).forEach((p, i) => { const [x, y] = P(pts[i]); ball(ctx, x, y, 6, INK); small(ctx, p.label || `(${fmt(p.x, 3)}, ${fmt(p.y, 3)}, ${fmt(p.z, 3)})`, x + 8, y - 12, { align: "left" }); });
    (a.lines || []).forEach((s2, i) => big(ctx, s2, 16, 24 + i * 24, { align: "left" }));
  },
  /** A wireframe solid turning slowly: kind frustum | conehemi | box | prism, with dimensions. */
  solid(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const ang = t * 0.5, cx = w / 2, cy = h * 0.55, s = Math.min(w, h) * 0.28;
    const proj = (x, y, z) => [cx + (x * Math.cos(ang) - z * Math.sin(ang)) * s, cy - y * s + (x * Math.sin(ang) + z * Math.cos(ang)) * s * 0.25];
    const ring = (r, y, n = 40) => { ctx.beginPath(); for (let k = 0; k <= n; k++) { const q = (k / n) * Math.PI * 2, [px, py] = proj(r * Math.cos(q), y, r * Math.sin(q)); if (k) ctx.lineTo(px, py); else ctx.moveTo(px, py); } ctx.stroke(); };
    ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.fillStyle = "rgba(255,91,46,.12)";
    if (a.kind === "frustum" || a.kind === "conehemi") {
      const R = 1, r = a.kind === "frustum" ? clamp(finite(a.r) / Math.max(1e-9, finite(a.R)), 0, 1) : 0, H = clamp(finite(a.h) / Math.max(1e-9, finite(a.R)), 0.1, 3) * 0.9;
      const yb = -0.6, yt = yb + H; ring(R, yb); if (r > 0) ring(r, yt);
      for (let k = 0; k < 8; k++) { const q = k * Math.PI / 4; const [x1, y1] = proj(R * Math.cos(q), yb, R * Math.sin(q)), [x2, y2] = proj(r * Math.cos(q), yt, r * Math.sin(q)); seg(ctx, x1, y1, x2, y2, INK, 1.5); }
      if (a.kind === "conehemi") for (let k = 1; k < 6; k++) { const th = (k / 6) * Math.PI / 2; ring(Math.cos(th), yb - Math.sin(th)); }
    } else if (a.kind === "box") {
      const S = 1, x = clamp(finite(a.x) / Math.max(1e-9, finite(a.s)), 0, 0.5), L = S - 2 * x, Hh = x * 2;
      const c = (px, py, pz) => proj((px - 0.5) * 1.6, py * 1.6 - 0.4, (pz - 0.5) * 1.6);
      const fold = Math.min(1, cyc(t, 6) * 2);
      const base = [[x, 0, x], [x + L, 0, x], [x + L, 0, x + L], [x, 0, x + L]];
      ctx.beginPath(); base.forEach((p, i) => { const [px, py] = c(...p); if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py); }); ctx.closePath(); ctx.fill(); ctx.stroke();
      base.forEach((p, i) => { const q = base[(i + 1) % 4], up = Hh * fold; const a1 = c(p[0], up, p[2]), a2 = c(q[0], up, q[2]), b1 = c(...p), b2 = c(...q); ctx.beginPath(); ctx.moveTo(...b1); ctx.lineTo(...a1); ctx.lineTo(...a2); ctx.lineTo(...b2); ctx.stroke(); });
      small(ctx, `cut ${fmt(a.x, 3)} from each corner`, w / 2, h - 20);
    }
    (a.lines || []).forEach((s2, i) => big(ctx, s2, 16, 24 + i * 24, { align: "left" }));
  },
  /** Two dice: highlight the ways of getting the sum S. */
  dice(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const S = Math.round(finite(a.S, 7)), cell = Math.min(40, (Math.min(w * 0.55, h - 80)) / 6), gx = 40, gy = 50;
    for (let i = 1; i <= 6; i++) for (let j = 1; j <= 6; j++) { const hit = i + j === S; rrect(ctx, gx + (j - 1) * cell, gy + (i - 1) * cell, cell - 3, cell - 3, 5, hit ? EMBER : "#e3e8ef"); small(ctx, `${i},${j}`, gx + (j - 0.5) * cell, gy + (i - 0.5) * cell, { color: hit ? "#fff" : "#7D8698", halo: null }); }
    const r1 = 1 + (Math.floor(t * 3) % 6), r2 = 1 + (Math.floor(t * 3 + 2) % 6), dx = gx + 6 * cell + 60;
    [r1, r2].forEach((v, k) => { rrect(ctx, dx + k * 80, gy + 40, 64, 64, 10, "#fff", INK); big(ctx, String(v), dx + 32 + k * 80, gy + 72); });
    big(ctx, `${fmt(a.ways, 3)} ways out of 36`, dx + 70, gy + 150, { color: EMBER }); big(ctx, `P = ${fmt(a.P, 4)}`, dx + 70, gy + 180);
  },
  /** A bag of balls: fav of total coloured; draw animation. */
  bag(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const total = clamp(Math.round(finite(a.total, 10)), 1, 400), fav = clamp(Math.round(finite(a.fav, 3)), 0, total), cols = Math.ceil(Math.sqrt(total * 1.6)), r = Math.min(14, (w * 0.55) / cols / 2.4);
    for (let k = 0; k < total; k++) { const cx = 40 + (k % cols) * r * 2.4 + r, cy = 60 + Math.floor(k / cols) * r * 2.4 + r; ball(ctx, cx, cy, r, k < fav ? EMBER : "#c5ccd8", INK); }
    const pick = Math.floor(t / 1.2) % total, pcol = (pick * 7) % total < fav;
    ball(ctx, w * 0.78, h * 0.4, 26, pcol ? EMBER : "#c5ccd8", INK); small(ctx, "picked at random", w * 0.78, h * 0.4 + 44);
    big(ctx, `P = ${fmt(a.P, 4)}`, w * 0.78, h * 0.62, { color: EMBER }); (a.lines || []).forEach((s, i) => small(ctx, s, w * 0.78, h * 0.7 + i * 18));
  },
  /** Bars (data, sequence terms, distribution). vals [], highlight index, labels, line value. */
  bars(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const vals = (a.vals || []).map((v) => finite(v)), n = vals.length || 1, max = Math.max(...vals.map(Math.abs), 1e-9), x0 = 50, x1 = w - 30, base = h - 50, top = 60;
    const bwid = (x1 - x0) / n, grow = Math.min(1, cyc(t, 6) * 2);
    vals.forEach((v, i) => { const hh = (base - top) * Math.abs(v) / max * Math.min(1, grow * n / Math.max(1, i + 1) / 1.2); ctx.fillStyle = i === a.hi ? EMBER : (a.colour || BLUE); ctx.fillRect(x0 + i * bwid + 2, base - hh, bwid - 4, hh); if (n <= 16) small(ctx, a.labels ? a.labels[i] : String(i + 1), x0 + (i + 0.5) * bwid, base + 14); });
    seg(ctx, x0, base, x1, base, INK, 2);
    if (a.mark !== undefined) { const y = base - (base - top) * finite(a.mark) / max; seg(ctx, x0, y, x1, y, GREEN, 2, [6, 4]); small(ctx, a.markLabel || "", x1, y - 12, { align: "right", color: GREEN }); }
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** Money growing in a jar each period: amounts per period, total. */
  money(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const vals = (a.vals || []).map(finite), n = vals.length, max = Math.max(...vals, 1e-9), shown = Math.min(n, 1 + Math.floor(cyc(t, 8) * n * 1.2)), bw = Math.min(50, (w - 80) / Math.max(1, n)), base = h - 50;
    for (let i = 0; i < shown; i++) { const hh = (h - 130) * vals[i] / max, coins = Math.max(1, Math.round(hh / 8)); for (let k = 0; k < coins; k++) { ctx.fillStyle = k % 2 ? "#e0b13a" : "#f2c94c"; ctx.beginPath(); ctx.ellipse(40 + i * bw + bw / 2, base - k * (hh / coins) - 4, bw * 0.4, 4, 0, 0, 7); ctx.fill(); } }
    seg(ctx, 30, base + 2, w - 30, base + 2, INK, 2);
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** Staircase of blocks: terms of an AP or GP. */
  stairs(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const vals = (a.vals || []).map(finite), n = vals.length, max = Math.max(...vals.map(Math.abs), 1e-9), bw = Math.min(46, (w - 80) / Math.max(1, n)), base = h - 40, unit = (h - 120) / max;
    const shown = Math.min(n, 1 + Math.floor(cyc(t, 7) * n * 1.2));
    for (let i = 0; i < shown; i++) { const hh = Math.abs(vals[i]) * unit; rrect(ctx, 40 + i * bw, base - hh, bw - 4, hh, 3, i === n - 1 ? EMBER : BLUE); if (n <= 14) small(ctx, fmt(vals[i], 3), 40 + i * bw + bw / 2 - 2, base - hh - 10); }
    seg(ctx, 30, base, w - 30, base, INK, 2); (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** Unit circle with an angle (deg) and arc; optional second angle B. */
  angle(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const cx = w * 0.38, cy = h / 2, R = Math.min(w, h) * 0.34, A = finite(a.A) * Math.PI / 180, B = a.B !== undefined ? finite(a.B) * Math.PI / 180 : null;
    seg(ctx, cx - R - 20, cy, cx + R + 20, cy, "#9aa3b2", 1); seg(ctx, cx, cy - R - 20, cx, cy + R + 20, "#9aa3b2", 1);
    ctx.strokeStyle = "#c5ccd8"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke();
    const tot = B === null ? A : A + B, sweep = tot * Math.min(1, cyc(t, 5) * 1.6);
    ctx.strokeStyle = EMBER; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(cx, cy, R, 0, -Math.min(sweep, A), sweep < 0); ctx.stroke();
    if (B !== null && sweep > A) { ctx.strokeStyle = BLUE; ctx.beginPath(); ctx.arc(cx, cy, R, -A, -sweep, true); ctx.stroke(); }
    const px = cx + R * Math.cos(sweep), py = cy - R * Math.sin(sweep);
    seg(ctx, cx, cy, px, py, INK, 2); ball(ctx, px, py, 6, INK); seg(ctx, px, py, px, cy, GREEN, 2, [4, 4]); seg(ctx, cx, cy, px, cy, PURPLE, 2, [4, 4]);
    small(ctx, "sin", px + 12, (py + cy) / 2, { color: GREEN, align: "left" }); small(ctx, "cos", (cx + px) / 2, cy + 14, { color: PURPLE });
    (a.lines || []).forEach((s, i) => big(ctx, s, w - 20, 30 + i * 26, { align: "right" }));
  },
  /** Complex number z = r∠θ raised to n: arrows for z, z², ... zⁿ spiralling. */
  complex(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const r = Math.max(1e-9, finite(a.r, 1)), th = finite(a.th) * Math.PI / 180, n = clamp(Math.round(finite(a.n, 3)), 1, 24), cx = w / 2, cy = h / 2;
    const maxR = Math.max(...Array.from({ length: n }, (_, k) => r ** (k + 1))), s = Math.min(w, h) * 0.42 / maxR;
    seg(ctx, 20, cy, w - 20, cy, "#9aa3b2", 1); seg(ctx, cx, 20, cx, h - 20, "#9aa3b2", 1);
    const shown = 1 + Math.floor(cyc(t, 6) * n * 1.1);
    for (let k = 1; k <= Math.min(shown, n); k++) { const rr = r ** k * s, q = th * k; arr(ctx, cx, cy, cx + rr * Math.cos(q), cy - rr * Math.sin(q), k === n ? EMBER : "rgba(42,120,214,.6)", k === n ? 3.5 : 2); }
    small(ctx, "Re", w - 30, cy - 12); small(ctx, "Im", cx + 14, 24);
    (a.lines || []).forEach((s2, i) => big(ctx, s2, 16, 24 + i * 24, { align: "left" }));
  },
  /** Venn diagram: two sets with counts or probabilities. */
  venn(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const cx = w / 2, cy = h / 2 + 10, R = Math.min(w, h) * 0.28, off = R * 0.6 * (1 - clamp(finite(a.overlap, 0.3), 0, 0.95)) + R * 0.2;
    ctx.globalAlpha = 0.35; ball(ctx, cx - off, cy, R, BLUE); ball(ctx, cx + off, cy, R, ORANGE); ctx.globalAlpha = 1;
    ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx - off, cy, R, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(cx + off, cy, R, 0, 7); ctx.stroke();
    big(ctx, a.onlyA ?? "", cx - off - R * 0.45, cy); big(ctx, a.both ?? "", cx, cy, { color: EMBER }); big(ctx, a.onlyB ?? "", cx + off + R * 0.45, cy);
    small(ctx, a.nameA || "A", cx - off, cy - R - 12, { color: BLUE }); small(ctx, a.nameB || "B", cx + off, cy - R - 12, { color: ORANGE });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, h - 30 + i * 22 - ((a.lines || []).length - 1) * 22)); void t;
  },
  /** A population of dots: test results (Bayes). prior, sens, fpr → coloured dots. */
  population(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const N = 400, cols = 25, r = Math.min(7, (w * 0.62) / cols / 2.4), prior = clamp(finite(a.prior), 0, 1), sens = clamp(finite(a.sens), 0, 1), fpr = clamp(finite(a.fpr), 0, 1);
    const ill = Math.round(N * prior), tp = Math.round(ill * sens), fp = Math.round((N - ill) * fpr);
    for (let k = 0; k < N; k++) { const x = 30 + (k % cols) * r * 2.4 + r, y = 50 + Math.floor(k / cols) * r * 2.4 + r; const isIll = k < ill, pos = isIll ? k < tp : k - ill < fp; ball(ctx, x, y, r, isIll ? (pos ? EMBER : "#f4b29b") : (pos ? BLUE : "#d6dde7")); }
    const lx = 30 + cols * r * 2.4 + 30; [["ill, test positive", EMBER], ["ill, missed", "#f4b29b"], ["well, false alarm", BLUE], ["well, negative", "#d6dde7"]].forEach(([s, c], i) => { ball(ctx, lx, 60 + i * 24, 7, c); small(ctx, s, lx + 14, 60 + i * 24, { align: "left" }); });
    big(ctx, `If the test is positive: ${fmt(finite(a.post) * 100, 3)}% chance of being ill`, w / 2, h - 22); void t;
  },
  /** Matrix as a transformation of the unit square: area becomes |det|. */
  matrix(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const [p, q, r2, s2] = [finite(a.a, 1), finite(a.b), finite(a.c), finite(a.d, 1)], f = (Math.sin(t * 0.8) + 1) / 2;
    const M = [1 + (p - 1) * f, q * f, r2 * f, 1 + (s2 - 1) * f], pts = [[0, 0], [M[0], M[2]], [M[0] + M[1], M[2] + M[3]], [M[1], M[3]]];
    const m = fit(w, h, [[0, 0], [p, r2], [p + q, r2 + s2], [q, s2], [1, 1]]); axes(ctx, w, h, m);
    ctx.fillStyle = "rgba(255,91,46,.2)"; ctx.beginPath(); pts.forEach(([x, y]) => ctx.lineTo(m.X(x), m.Y(y))); ctx.closePath(); ctx.fill(); ctx.strokeStyle = EMBER; ctx.lineWidth = 2.5; ctx.stroke();
    arr(ctx, m.X(0), m.Y(0), m.X(M[0]), m.Y(M[2]), BLUE, 3); arr(ctx, m.X(0), m.Y(0), m.X(M[1]), m.Y(M[3]), GREEN, 3);
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** Area under a curve sampled by the engine (xs, fy), optional second curve gy, optional rectangles rx/rh of width rw. */
  area(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const xs = (a.xs || []).map(finite), fy = (a.fy || []).map(finite), gy = a.gy ? a.gy.map(finite) : null;
    if (xs.length < 2) return;
    const m = fit(w, h, xs.flatMap((x, i) => [[x, fy[i]], [x, gy ? gy[i] : 0]]), 50); axes(ctx, w, h, m);
    if (a.rx && a.rh) { const rw = finite(a.rw), many = a.rx.length > 40; a.rx.forEach((x, k) => { const y = finite(a.rh[k]); ctx.fillStyle = "rgba(255,91,46,.25)"; ctx.fillRect(m.X(x), Math.min(m.Y(y), m.Y(0)), Math.max(1, m.X(x + rw) - m.X(x)), Math.abs(m.Y(y) - m.Y(0))); if (!many) { ctx.strokeStyle = EMBER; ctx.lineWidth = 1; ctx.strokeRect(m.X(x), Math.min(m.Y(y), m.Y(0)), m.X(x + rw) - m.X(x), Math.abs(m.Y(y) - m.Y(0))); } }); }
    else { const grow = Math.min(1, cyc(t, 5) * 1.5), n = Math.max(2, Math.round(xs.length * grow)); ctx.fillStyle = "rgba(255,91,46,.22)"; ctx.beginPath(); for (let i = 0; i < n; i++) ctx.lineTo(m.X(xs[i]), m.Y(fy[i])); for (let i = n - 1; i >= 0; i--) ctx.lineTo(m.X(xs[i]), m.Y(gy ? gy[i] : 0)); ctx.closePath(); ctx.fill(); }
    ctx.strokeStyle = BLUE; ctx.lineWidth = 3; ctx.beginPath(); xs.forEach((x, i) => (i ? ctx.lineTo(m.X(x), m.Y(fy[i])) : ctx.moveTo(m.X(x), m.Y(fy[i])))); ctx.stroke();
    if (gy) { ctx.strokeStyle = GREEN; ctx.beginPath(); xs.forEach((x, i) => (i ? ctx.lineTo(m.X(x), m.Y(gy[i])) : ctx.moveTo(m.X(x), m.Y(gy[i])))); ctx.stroke(); }
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** A chord from x0 to x1 on a curve sampled by the engine (xs, fy) closing in on the tangent of slope `slope` at x0. */
  secant(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const xs = (a.xs || []).map(finite), fy = (a.fy || []).map(finite); if (xs.length < 2) return;
    const at = (x) => { for (let i = 1; i < xs.length; i++) if (x <= xs[i]) { const f = (x - xs[i - 1]) / (xs[i] - xs[i - 1] || 1); return fy[i - 1] + (fy[i] - fy[i - 1]) * f; } return fy[fy.length - 1]; };
    const m = fit(w, h, xs.map((x, i) => [x, fy[i]]), 50); axes(ctx, w, h, m);
    ctx.strokeStyle = BLUE; ctx.lineWidth = 3; ctx.beginPath(); xs.forEach((x, i) => (i ? ctx.lineTo(m.X(x), m.Y(fy[i])) : ctx.moveTo(m.X(x), m.Y(fy[i])))); ctx.stroke();
    const x0 = finite(a.x0), x1full = finite(a.x1), k = 0.08 + 0.92 * (Math.cos(t * 0.8) + 1) / 2, x1 = x0 + (x1full - x0) * k;
    const y0 = at(x0), y1 = at(x1), sl = (y1 - y0) / ((x1 - x0) || 1e-9), lo = xs[0], hi = xs[xs.length - 1];
    seg(ctx, m.X(lo), m.Y(y0 + sl * (lo - x0)), m.X(hi), m.Y(y0 + sl * (hi - x0)), EMBER, 2.5);
    if (a.slope !== undefined) { const s0 = finite(a.slope); seg(ctx, m.X(lo), m.Y(y0 + s0 * (lo - x0)), m.X(hi), m.Y(y0 + s0 * (hi - x0)), GREEN, 1.5, [6, 4]); }
    ball(ctx, m.X(x0), m.Y(y0), 6, INK); ball(ctx, m.X(x1), m.Y(y1), 6, EMBER);
    small(ctx, "orange: the chord, green dashed: the tangent", w / 2, h - 16);
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** A circle growing at rate drdt: ripple in water. */
  ripple(ctx, w, h, t, a) {
    ctx.fillStyle = "#cfe3f5"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2, rr = clamp(finite(a.r, 1), 0, 1e9), s = Math.min(w, h) * 0.38 / Math.max(rr * 1.4, 1e-9), grow = (t * finite(a.drdt, 1) * s * 0.3) % (Math.min(w, h) * 0.2);
    for (let k = 0; k < 4; k++) { ctx.strokeStyle = `rgba(42,120,214,${0.7 - k * 0.15})`; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(cx, cy, Math.max(1, rr * s - k * 20 + grow), 0, 7); ctx.stroke(); }
    (a.lines || []).forEach((s2, i) => big(ctx, s2, 16, 24 + i * 24, { align: "left" }));
  },
  /** Feasible region and corner points of a linear programme. corners [[x,y]], best index. */
  lpp(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const C = (a.corners || []).map((p) => p.map(finite)), m = fit(w, h, C.length ? C : [[0, 0], [1, 1]]); axes(ctx, w, h, m);
    ctx.fillStyle = "rgba(27,175,122,.2)"; ctx.beginPath(); C.forEach(([x, y]) => ctx.lineTo(m.X(x), m.Y(y))); ctx.closePath(); ctx.fill(); ctx.strokeStyle = GREEN; ctx.lineWidth = 2; ctx.stroke();
    C.forEach(([x, y], i) => { ball(ctx, m.X(x), m.Y(y), i === a.best ? 9 : 6, i === a.best ? EMBER : INK); small(ctx, `(${fmt(x, 3)}, ${fmt(y, 3)})`, m.X(x) + 10, m.Y(y) - 12, { align: "left" }); });
    const k = cyc(t, 4); if (a.p !== undefined) { const p = finite(a.p), q = finite(a.q, 1), Z = finite(a.Zmax) * k; if (Math.abs(q) > 1e-9) seg(ctx, m.X(m.x0 - 5), m.Y((Z - p * (m.x0 - 5)) / q), m.X(m.x1 + 5), m.Y((Z - p * (m.x1 + 5)) / q), EMBER, 2, [6, 4]); }
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, 24 + i * 24, { align: "left" }));
  },
  /** A tower or tree seen from two points at angles al and be (deg) d apart; height h. */
  tower(ctx, w, h, t, a) {
    ctx.fillStyle = "#eaf2fb"; ctx.fillRect(0, 0, w, h); const gy = h * 0.82; ctx.fillStyle = "#d9dfd0"; ctx.fillRect(0, gy, w, h - gy);
    const H = Math.max(1e-9, finite(a.H, 10)), X = Math.max(0, finite(a.x, 10)), D = Math.max(0, finite(a.d, 10)), span = X + D, s = Math.min((w - 140) / Math.max(span, 1e-9), (gy - 50) / H);
    const tx = w - 70, top = gy - H * s;
    ctx.fillStyle = "#8b7a66"; ctx.fillRect(tx - 12, top, 24, gy - top);
    const p1 = tx - X * s, p2 = tx - (X + D) * s;
    person(ctx, p1, gy, 0.6); person(ctx, p2, gy, 0.6);
    const k = Math.min(1, cyc(t, 4) * 1.6); seg(ctx, p1, gy - 30 * 0.6, p1 + (tx - p1) * k, gy - 18 + (top + 18 - gy) * k, EMBER, 2, [6, 4]); seg(ctx, p2, gy - 30 * 0.6, p2 + (tx - p2) * k, gy - 18 + (top + 18 - gy) * k, BLUE, 2, [6, 4]);
    small(ctx, `${fmt(a.al, 3)}°`, p1 + 26, gy - 26, { color: EMBER }); small(ctx, `${fmt(a.be, 3)}°`, p2 + 26, gy - 26, { color: BLUE });
    dim(ctx, p2, gy + 10, p1, gy + 10, `${fmt(D, 4)} m`); dim(ctx, tx + 24, gy, tx + 24, top, `${fmt(H, 4)} m`, EMBER, 10);
    function person(c, x, y, sc) { c.strokeStyle = INK; c.lineWidth = 2; ball(c, x, y - 50 * sc, 7 * sc, INK); c.beginPath(); c.moveTo(x, y - 44 * sc); c.lineTo(x, y - 16 * sc); c.lineTo(x - 8 * sc, y); c.moveTo(x, y - 16 * sc); c.lineTo(x + 8 * sc, y); c.stroke(); }
  },
  /** Circle with an outside point and the tangent of length L. */
  tangent(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const r = Math.max(1e-9, finite(a.r, 3)), d = Math.max(r, finite(a.d, 5)), s = Math.min(w, h) * 0.38 / d, cx = w * 0.35, cy = h / 2, px = cx + d * s;
    ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(cx, cy, r * s, 0, 7); ctx.stroke();
    const ang = Math.acos(r / d), qx = cx + r * s * Math.cos(ang), qy = cy - r * s * Math.sin(ang);
    seg(ctx, cx, cy, qx, qy, BLUE, 2); seg(ctx, cx, cy, px, cy, "#9aa3b2", 1.5, [5, 4]); const k = Math.min(1, cyc(t, 4) * 1.6); seg(ctx, px, cy, px + (qx - px) * k, cy + (qy - cy) * k, EMBER, 3);
    ball(ctx, px, cy, 6, INK); ball(ctx, qx, qy, 5, EMBER);
    small(ctx, `r = ${fmt(r, 3)}`, (cx + qx) / 2 - 16, (cy + qy) / 2); small(ctx, `d = ${fmt(d, 3)}`, (cx + px) / 2, cy + 16); big(ctx, `tangent = ${fmt(a.L, 4)}`, (px + qx) / 2 + 40, (cy + qy) / 2 - 20, { color: EMBER });
  },
  /** Arranging r of n objects in a row (permutations) or choosing a group (combinations). */
  arrange(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const n = clamp(Math.round(finite(a.n, 5)), 1, 20), r = clamp(Math.round(finite(a.r, 2)), 0, n), cols = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22", "#1abc9c", "#34495e"];
    const k = Math.floor(t / 1.2), slots = []; let seed = k * 7 + 3; const avail = [...Array(n).keys()];
    for (let i = 0; i < r; i++) { seed = (seed * 31 + 11) % 997; slots.push(avail.splice(seed % avail.length, 1)[0]); }
    const rad = Math.min(18, (w - 60) / n / 2.6);
    for (let i = 0; i < n; i++) ball(ctx, 40 + i * rad * 2.6 + rad, 60, rad, slots.includes(i) ? "#e3e8ef" : cols[i % cols.length], INK);
    for (let i = 0; i < r; i++) { rrect(ctx, 40 + i * 70, h * 0.5 - 30, 60, 60, 8, "#fff", INK); ball(ctx, 70 + i * 70, h * 0.5, 22, cols[slots[i] % cols.length], INK); }
    (a.lines || []).forEach((s, i) => big(ctx, s, 16, h - 50 + i * 24, { align: "left" }));
  },
  /** Parallelogram and trapezium side by side with base, top and height. */
  quad(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const b1 = Math.max(1e-9, finite(a.b1, 6)), b2 = Math.max(0, finite(a.b2, 4)), H = Math.max(1e-9, finite(a.h, 3)), s = Math.min((w / 2 - 60) / Math.max(b1, b2) / 1.3, (h - 120) / H), sk = Math.sin(t * 0.6) * 0.3 * H * s;
    const draw = (ox, top) => { const by = h * 0.75; ctx.fillStyle = "rgba(255,91,46,.15)"; ctx.beginPath(); ctx.moveTo(ox, by); ctx.lineTo(ox + b1 * s, by); ctx.lineTo(ox + sk + (b1 * s + top * s) / 2, by - H * s); ctx.lineTo(ox + sk + (b1 * s - top * s) / 2, by - H * s); ctx.closePath(); ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.stroke(); seg(ctx, ox + sk + b1 * s / 2, by, ox + sk + b1 * s / 2, by - H * s, BLUE, 1.5, [4, 4]); };
    draw(40, b1); draw(w / 2 + 20, b2);
    small(ctx, `parallelogram: ${fmt(a.Ap, 4)}`, 40 + b1 * s / 2, h * 0.75 + 22); small(ctx, `trapezium: ${fmt(a.At, 4)}`, w / 2 + 20 + b1 * s / 2, h * 0.75 + 22);
    big(ctx, "Sliding the top does not change the area", w / 2, 24);
  },
};
