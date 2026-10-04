// Chemistry worlds: particles in solutions, gases, reactions over time, cells and electrolysis, the lab bench.
import { fmt } from "../core/format.js";
import { INK, EMBER, T, small, big, ball, rrect, seg, arr, dim, thermometer, beakerShape, flame, molecules, waveColour, soft, clamp, cyc, finite } from "./worlds.js";

const BLUE = "#2a78d6", GREEN = "#1baf7a", ORANGE = "#eb6834", PURPLE = "#8a63d2";
const bg = (ctx, w, h) => { ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h); };

export const CHEM = {
  /** Beakers of solution: items [{n particles shown, colour, label, fill (0..1), solid (excess at the bottom 0..1), tint}] */
  solution(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const items = a.items || [], n = items.length || 1;
    items.forEach((it, i) => {
      const cx = w * (i + 0.5) / n, bw = Math.min(150, w / n - 40), by = h * 0.26, bh = h * 0.5;
      const tint = it.tint || `rgba(70,140,220,${0.12 + 0.35 * clamp(finite(it.strength, 0.3), 0, 1)})`;
      const box = beakerShape(ctx, cx - bw / 2, by, bw, bh, clamp(finite(it.fill, 0.7), 0.05, 1), tint);
      molecules(ctx, box.x0, box.lvl + 2, box.x1 - box.x0, box.bottom - box.lvl - 2, clamp(Math.round(finite(it.n, 20)), 0, 140), t, 0.25, it.colour || PURPLE, 3.5, i + 2);
      const sol = clamp(finite(it.solid, 0), 0, 1); if (sol > 0) { ctx.fillStyle = it.solidColour || "#e9e2cf"; ctx.beginPath(); ctx.ellipse(cx, box.bottom - 4, bw * 0.38 * Math.sqrt(sol) + 6, 6 + 14 * sol, 0, Math.PI, 0); ctx.fill(); }
      if (it.gas) molecules(ctx, cx - bw / 2 + 4, by - 70, bw - 8, 60, clamp(Math.round(finite(it.gas, 10)), 0, 80), t, 0.6, it.gasColour || "#9aa3b2", 3, i + 9);
      if (it.T !== undefined) thermometer(ctx, cx + bw / 2 - 16, by - 20, bh * 0.7, it.T, it.Tlo ?? -20, it.Thi ?? 120);
      if (it.heat) flame(ctx, cx, by + bh + 30, 26, t);
      small(ctx, it.label || "", cx, by + bh + (it.heat ? 70 : 22));
      if (it.sub) small(ctx, it.sub, cx, by + bh + (it.heat ? 88 : 40), { color: EMBER });
    });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** A balance with a heap of substance; mass (g), particle count text. */
  balance(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const cx = w / 2, by = h * 0.7, heap = 20 + 80 * soft(a.m, 20);
    rrect(ctx, cx - 140, by, 280, 50, 8, "#dfe3ea", INK); rrect(ctx, cx - 70, by + 12, 140, 26, 4, "#1b2a40"); T(ctx, `${fmt(a.m, 4)} g`, cx, by + 25, { color: "#7fffb0", halo: null, font: "600 15px Plex Mono, monospace" });
    seg(ctx, cx - 110, by - 4, cx + 110, by - 4, INK, 4);
    ctx.fillStyle = a.colour || "#e9e2cf"; ctx.beginPath(); ctx.ellipse(cx, by - 6, heap, heap * 0.55, 0, Math.PI, 0); ctx.fill();
    const zoom = { x: w - 150, y: 50, r: 70 }; ball(ctx, zoom.x, zoom.y + zoom.r, zoom.r, "#fff", INK);
    molecules(ctx, zoom.x - zoom.r * 0.6, zoom.y + zoom.r * 0.4, zoom.r * 1.2, zoom.r * 1.2, 26, t, 0.15, a.dot || PURPLE, 4);
    seg(ctx, cx + heap * 0.5, by - heap * 0.4, zoom.x - zoom.r * 0.7, zoom.y + zoom.r * 1.5, "#9aa3b2", 1, [4, 4]); small(ctx, "zoomed in", zoom.x, zoom.y + zoom.r * 2 + 14);
    (a.lines || []).forEach((s, i) => big(ctx, s, 20, 30 + i * 26, { align: "left" }));
  },
  /** A molecule drawn from atom counts: atoms [{el, n, colour}] in a chain or ball. */
  molecule(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const list = []; (a.atoms || []).forEach((at) => { for (let k = 0; k < Math.min(60, Math.max(0, Math.round(finite(at.n)))); k++) list.push(at); });
    const cx = w / 2, cy = h * 0.48, n = list.length || 1;
    const carbons = list.filter((x) => x.el === "C"), others = list.filter((x) => x.el !== "C");
    const step = Math.min(56, (w - 120) / Math.max(1, carbons.length)), y = cy + Math.sin(t) * 2;
    carbons.forEach((at, i) => { const x = cx - ((carbons.length - 1) * step) / 2 + i * step; if (i) seg(ctx, x - step, y, x, y, INK, 3); });
    others.forEach((at, i) => { const host = carbons.length ? carbons[i % carbons.length] : null; const hi = carbons.length ? i % carbons.length : 0; const x0 = cx - ((carbons.length - 1) * step) / 2 + hi * step, q = (Math.floor(i / Math.max(1, carbons.length)) * 1.7 + 0.8) % (Math.PI * 2), r = 34; const x = host ? x0 + r * Math.cos(q) : cx + 90 * Math.cos(i * 6.28 / Math.max(1, others.length)), yy = host ? y + r * Math.sin(q) : cy + 90 * Math.sin(i * 6.28 / Math.max(1, others.length)); seg(ctx, host ? x0 : cx, host ? y : cy, x, yy, "#9aa3b2", 2); ball(ctx, x, yy, at.el === "H" ? 9 : 13, at.colour || "#ddd", INK); T(ctx, at.el, x, yy, { font: "700 11px Plex, system-ui", halo: null }); });
    carbons.forEach((at, i) => { const x = cx - ((carbons.length - 1) * step) / 2 + i * step; ball(ctx, x, y, 15, "#333", INK); T(ctx, "C", x, y, { color: "#fff", halo: null, font: "700 12px Plex, system-ui" }); });
    void n; (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, h - 50 + i * 24));
  },
  /** Gas made in a heated tube and collected: m (g) solid, gas volume text. */
  heatTube(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const tx = w * 0.3, ty = h * 0.4;
    ctx.save(); ctx.translate(tx, ty); ctx.rotate(-0.25); rrect(ctx, -90, -18, 180, 36, 18, "rgba(255,255,255,.7)", INK); ctx.fillStyle = a.colour || "#eee"; ctx.fillRect(-80, 0, 70, 14); ctx.restore();
    flame(ctx, tx - 30, ty + 90, 30, t);
    seg(ctx, tx + 85, ty - 22, w * 0.68, ty - 22, INK, 3); seg(ctx, w * 0.68, ty - 22, w * 0.68, h * 0.62, INK, 3);
    const gx = w * 0.62, gy = h * 0.55; ctx.fillStyle = "rgba(70,140,220,.3)"; ctx.fillRect(gx - 60, gy, 180, h - gy - 10);
    for (let k = 0; k < 6; k++) { const p = cyc(t + k * 0.2, 1.4); ball(ctx, w * 0.68 + Math.sin(k) * 4, h * 0.62 - p * 30, 4, "rgba(255,255,255,.9)", "#9cc"); }
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** Electrolysis cell: current I (A), metal deposited mass m (g); bubbles of gas. */
  electrolysis(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const by = h * 0.3, bw = Math.min(320, w * 0.6), cx = w / 2, bh = h * 0.5;
    const box = beakerShape(ctx, cx - bw / 2, by, bw, bh, 0.8, a.tint || "rgba(60,130,220,.3)");
    const thick = 2 + 14 * soft(a.m, 1);
    rrect(ctx, cx - bw * 0.3 - 8, by - 30, 16, bh * 0.85, 2, "#888"); rrect(ctx, cx + bw * 0.3 - 8, by - 30, 16, bh * 0.85, 2, "#b87333");
    ctx.fillStyle = a.metal || "#b87333"; ctx.fillRect(cx + bw * 0.3 - 8 - thick, box.lvl, 16 + 2 * thick, by + bh * 0.85 - 30 - box.lvl);
    for (let k = 0; k < 8; k++) { const p = cyc(t * (0.5 + soft(a.I, 2)) + k * 0.13, 1); ball(ctx, cx - bw * 0.3 + Math.sin(k * 3) * 6, box.bottom - 20 - p * (box.bottom - box.lvl - 20), 3, "rgba(255,255,255,.9)", "#9cc"); }
    for (let k = 0; k < 10; k++) { const p = cyc(t * (0.2 + soft(a.I, 2)) + k * 0.1, 1); ball(ctx, cx - bw * 0.3 + p * bw * 0.6, box.lvl + 20 + (k % 5) * 18, 3.5, k % 2 ? ORANGE : BLUE); }
    seg(ctx, cx - bw * 0.3, by - 30, cx - bw * 0.3, by - 60, INK, 2); seg(ctx, cx - bw * 0.3, by - 60, cx + bw * 0.3, by - 60, INK, 2); seg(ctx, cx + bw * 0.3, by - 60, cx + bw * 0.3, by - 30, INK, 2);
    rrect(ctx, cx - 30, by - 76, 60, 30, 4, "#fff", INK); small(ctx, `${fmt(a.I, 3)} A`, cx, by - 61);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, h - 46 + i * 24));
  },
  /** A two-beaker cell with a salt bridge and a voltmeter showing E (V). */
  cell(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const by = h * 0.42, bw = Math.min(160, w * 0.3), bh = h * 0.4, lx = w * 0.27, rx = w * 0.73;
    beakerShape(ctx, lx - bw / 2, by, bw, bh, 0.75, a.leftTint || "rgba(180,180,200,.3)"); beakerShape(ctx, rx - bw / 2, by, bw, bh, 0.75, a.rightTint || "rgba(60,130,220,.35)");
    rrect(ctx, lx - 8, by - 30, 16, bh * 0.8, 2, "#9aa3b2"); rrect(ctx, rx - 8, by - 30, 16, bh * 0.8, 2, "#b87333");
    ctx.strokeStyle = "#ccc"; ctx.lineWidth = 16; ctx.beginPath(); ctx.moveTo(lx + 30, by + 40); ctx.lineTo(lx + 30, by - 10); ctx.lineTo(rx - 30, by - 10); ctx.lineTo(rx - 30, by + 40); ctx.stroke();
    seg(ctx, lx, by - 30, lx, 50, INK, 2); seg(ctx, rx, by - 30, rx, 50, INK, 2); seg(ctx, lx, 50, w / 2 - 40, 50, INK, 2); seg(ctx, rx, 50, w / 2 + 40, 50, INK, 2);
    ball(ctx, w / 2, 50, 40, "#fff", INK); const E = finite(a.E), q = -Math.PI / 2 + clamp(E / 2.5, -1, 1) * 1.2; seg(ctx, w / 2, 50, w / 2 + 30 * Math.cos(q), 50 + 30 * Math.sin(q), EMBER, 3);
    small(ctx, `${fmt(E, 4)} V`, w / 2, 76);
    for (let k = 0; k < 6; k++) { const p = cyc(t * 0.5 + k / 6, 1); ball(ctx, lx + (rx - lx) * p, 50, 3, BLUE); }
    small(ctx, a.left || "anode", lx, by + bh + 20); small(ctx, a.right || "cathode", rx, by + bh + 20);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, h - 18 - i * 22));
  },
  /** Reactant molecules disappearing: frac (0..1) left, speed of molecules from temperature. */
  kinetics(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const x0 = 30, y0 = 50, bw = w * 0.55, bh = h - 100, N = 80, left = Math.round(N * clamp(finite(a.frac, 1), 0, 1));
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, y0, bw, bh);
    molecules(ctx, x0 + 4, y0 + 4, bw - 8, bh - 8, N, t, clamp(finite(a.speed, 0.4), 0, 1), (i) => (i < left ? (a.reactant || BLUE) : (a.product || ORANGE)), 5, 3);
    const bx = x0 + bw + 40, bwid = w - bx - 30; rrect(ctx, bx, y0, bwid, 22, 4, "#e3e8ef"); ctx.fillStyle = BLUE; ctx.fillRect(bx, y0, bwid * clamp(finite(a.frac, 1), 0, 1), 22);
    small(ctx, `${fmt(finite(a.frac) * 100, 3)}% of the reactant left`, bx, y0 + 40, { align: "left" });
    (a.lines || []).forEach((s, i) => small(ctx, s, bx, y0 + 80 + i * 22, { align: "left", font: "600 14px Plex, system-ui", color: INK }));
    small(ctx, "blue: reactant, orange: product", x0 + bw / 2, h - 22);
  },
  /** Energy hill: reactants over Ea to products; molecules that make it at the given T (fraction). */
  hill(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const x0 = 40, x1 = w - 40, base = h * 0.75, peak = h * 0.25, endY = base + clamp(finite(a.dH, 0) / 400, -0.4, 0.4) * h * 0.4;
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x0, base); ctx.bezierCurveTo(w * 0.4, base, w * 0.42, peak, w / 2, peak); ctx.bezierCurveTo(w * 0.58, peak, w * 0.6, endY, x1, endY); ctx.stroke();
    const f = clamp(finite(a.frac), 0, 1);
    for (let k = 0; k < 12; k++) { const over = (k / 12) < Math.max(f, 0.02) * 4, p = cyc(t * 0.4 + k / 12, 1); const x = over ? x0 + (x1 - x0) * p : x0 + 40 + 60 * Math.abs(Math.sin(t + k)); const y = over ? (p < 0.5 ? base - (base - peak) * Math.sin(p * Math.PI) : peak + (endY - peak) * Math.sin((p - 0.5) * Math.PI)) : base - 10 - 30 * Math.abs(Math.sin(t * 2 + k)); ball(ctx, x, y - 8, 6, over ? ORANGE : BLUE); }
    small(ctx, `Ea = ${fmt(a.Ea, 4)}`, w / 2, peak - 18);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** Light through a coloured cuvette: absorbance A, transmitted fraction Tr. */
  colorimeter(ctx, w, h, t, a) {
    ctx.fillStyle = "#101522"; ctx.fillRect(0, 0, w, h);
    const cy = h / 2, cx = w / 2, tr = clamp(finite(a.Tr, 1), 0, 1);
    ctx.fillStyle = "rgba(255,250,220,.85)"; ctx.fillRect(20, cy - 14, cx - 60, 28); ctx.fillStyle = `rgba(255,250,220,${0.85 * tr})`; ctx.fillRect(cx + 40, cy - 14, w - cx - 80, 28);
    rrect(ctx, cx - 40, cy - 60, 80, 120, 4, `rgba(138,99,210,${0.15 + 0.8 * (1 - tr)})`, "#cfe0f5");
    rrect(ctx, w - 50, cy - 30, 30, 60, 4, "#333", "#cfe0f5");
    T(ctx, `${fmt(tr * 100, 3)}% of the light gets through   A = ${fmt(a.A, 3)}`, w / 2, h - 24, { color: "#fff", halo: null }); void t;
  },
  /** Paper chromatography: solvent front df, spot distance ds (cm). */
  chroma(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const px = w / 2 - 60, py = 30, ph = h - 80, base = py + ph - 30, df = clamp(finite(a.df, 10), 0.1, 50), ds = clamp(finite(a.ds, 5), 0, df), scale = (ph - 60) / df;
    const grow = Math.min(1, cyc(t, 6) * 1.4);
    ctx.fillStyle = "#fff"; ctx.fillRect(px, py, 120, ph); ctx.strokeStyle = INK; ctx.strokeRect(px, py, 120, ph);
    ctx.fillStyle = "rgba(70,140,220,.15)"; ctx.fillRect(px, base - df * scale * grow, 120, df * scale * grow + 30);
    seg(ctx, px - 10, base, px + 130, base, "#9aa3b2", 1, [4, 4]); ball(ctx, w / 2, base - ds * scale * grow, 9, PURPLE);
    seg(ctx, px - 10, base - df * scale * grow, px + 130, base - df * scale * grow, BLUE, 1.5);
    small(ctx, `spot ${fmt(ds, 3)} cm`, px + 140, base - ds * scale, { align: "left", color: PURPLE }); small(ctx, `solvent ${fmt(df, 3)} cm`, px + 140, base - df * scale, { align: "left", color: BLUE });
    big(ctx, `Rf = ${fmt(a.Rf, 3)}`, px - 60, h / 2);
  },
  /** A unit cell: kind sc/bcc/fcc from Z (atoms per cell). */
  crystal(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const Z = Math.round(finite(a.Z, 1)), cx = w / 2, cy = h / 2, s = Math.min(w, h) * 0.22, ang = t * 0.4;
    const P = (x, y, z) => { const X = x * Math.cos(ang) - z * Math.sin(ang), Zr = x * Math.sin(ang) + z * Math.cos(ang); return [cx + X * s, cy - y * s + Zr * s * 0.3]; };
    const pts = []; for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) pts.push([x, y, z]);
    const edges = [[0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3], [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7]];
    edges.forEach(([i, j]) => { const p = P(...pts[i]), q = P(...pts[j]); seg(ctx, p[0], p[1], q[0], q[1], "#9aa3b2", 1.5); });
    pts.forEach((p) => { const [x, y] = P(...p); ball(ctx, x, y, 14, BLUE, INK); });
    if (Z === 2) { const [x, y] = P(0, 0, 0); ball(ctx, x, y, 14, ORANGE, INK); }
    if (Z === 4) for (const f of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) { const [x, y] = P(...f); ball(ctx, x, y, 12, ORANGE, INK); }
    big(ctx, `${Z === 1 ? "Simple cubic" : Z === 2 ? "Body-centred cubic" : Z === 4 ? "Face-centred cubic" : `${Z} atoms per cell`}: density ${fmt(a.rho, 4)} kg/m³`, w / 2, 24);
  },
  /** d-orbital splitting with electrons: t2g, eg counts. Or unpaired electron arrows (spin). */
  orbitals(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const box = (x, y, n) => { rrect(ctx, x, y, 40, 40, 4, "#fff", INK); if (n >= 1) arr(ctx, x + 14, y + 32, x + 14, y + 8, BLUE, 2.5); if (n >= 2) arr(ctx, x + 26, y + 8, x + 26, y + 32, ORANGE, 2.5); };
    if (a.split) {
      const t2g = clamp(Math.round(finite(a.t2g)), 0, 6), eg = clamp(Math.round(finite(a.eg)), 0, 4), gap = 60 + 60 * soft(a.D, 1);
      const fill = (n, k) => (n > k ? 1 : 0) + (n > k + (k < 3 ? 3 : 2) ? 1 : 0);
      for (let k = 0; k < 3; k++) box(w / 2 - 80 + k * 54, h * 0.6, fill(t2g, k)); for (let k = 0; k < 2; k++) box(w / 2 - 53 + k * 54, h * 0.6 - gap - 40, fill(eg, k));
      small(ctx, "t₂g", w / 2 - 120, h * 0.6 + 20); small(ctx, "eg", w / 2 - 92, h * 0.6 - gap - 20); dim(ctx, w / 2 + 110, h * 0.6 + 20, w / 2 + 110, h * 0.6 - gap - 20, "Δo", "#4D5769", 0);
    } else {
      const n = clamp(Math.round(finite(a.n)), 0, 5); for (let k = 0; k < 5; k++) box(w / 2 - 125 + k * 50, h / 2 - 20, k < n ? 1 : 0); small(ctx, `${n} unpaired electrons spinning`, w / 2, h / 2 + 50);
      for (let k = 0; k < n; k++) { const q = t * 3 + k; ctx.strokeStyle = "rgba(42,120,214,.4)"; ctx.beginPath(); ctx.ellipse(w / 2 - 105 + k * 50, h / 2 - 50, 10, 4, q, 0, 7); ctx.stroke(); }
    }
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 24 + i * 24));
  },
  /** Light as a photon wave packet with wavelength lam (m), energy line. Or a particle's matter wave. */
  wave(ctx, w, h, t, a) {
    ctx.fillStyle = "#101522"; ctx.fillRect(0, 0, w, h);
    const col = a.colour || waveColour(a.lam), lp = clamp(20 + 140 * soft(a.lamRel ?? finite(a.lam) * 1e7, 3), 12, 200);
    ctx.strokeStyle = col; ctx.lineWidth = 3; ctx.beginPath();
    for (let x = 20; x < w - 20; x += 2) { const env = Math.exp(-(((x - w / 2) / (w * 0.28)) ** 2)), y = h / 2 + 50 * env * Math.sin((2 * Math.PI * x) / lp - t * 6); if (x === 20) ctx.moveTo(x, y); else ctx.lineTo(x, y); }
    ctx.stroke();
    (a.lines || []).forEach((s, i) => T(ctx, s, w / 2, 26 + i * 24, { color: "#fff", halo: null, font: "700 16px Plex, system-ui" }));
  },
  /** Two liquids in a closed flask with vapour above; fractions for colour. */
  vapour(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const cx = w / 2, by = h * 0.35, bw = 240, bh = h * 0.5;
    const box = beakerShape(ctx, cx - bw / 2, by, bw, bh, 0.55, "rgba(70,140,220,.25)");
    rrect(ctx, cx - bw / 2 - 6, by - 6, bw + 12, 8, 2, INK);
    const xA = clamp(finite(a.xA, 0.5), 0, 1), yA = clamp(finite(a.yA, xA), 0, 1);
    molecules(ctx, box.x0, box.lvl + 2, box.x1 - box.x0, box.bottom - box.lvl, 40, t, 0.2, (i) => ((i % 40) / 40 < xA ? BLUE : ORANGE), 4, 3);
    molecules(ctx, box.x0, by + 4, box.x1 - box.x0, box.lvl - by - 8, Math.round(10 + 30 * soft(a.p, 50)), t, 0.7, (i) => ((i * 0.37) % 1 < yA ? BLUE : ORANGE), 3, 4);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** U-tube with a membrane: solvent moving into the solution side, rise height. */
  osmosis(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const lx = w * 0.32, rx = w * 0.68, by = h * 0.82, top = h * 0.2, rise = 20 + 120 * soft(a.Pi, 500000);
    ctx.fillStyle = "rgba(70,140,220,.2)"; ctx.fillRect(lx - 30, h * 0.5 + rise / 2, 60, by - h * 0.5 - rise / 2); ctx.fillRect(rx - 30, h * 0.5 - rise / 2, 60, by - h * 0.5 + rise / 2); ctx.fillRect(lx - 30, by - 30, rx - lx + 60, 30);
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(lx - 30, top, 60, by - top); ctx.strokeRect(rx - 30, top, 60, by - top); seg(ctx, w / 2, by - 30, w / 2, by, "#c33", 3, [3, 3]);
    molecules(ctx, rx - 26, h * 0.5 - rise / 2 + 4, 52, by - h * 0.5 + rise / 2 - 8, 16, t, 0.2, PURPLE, 4, 5);
    for (let k = 0; k < 4; k++) { const p = cyc(t + k * 0.25, 1.4); ball(ctx, w / 2 - 20 + 40 * p, by - 16, 3, BLUE); }
    small(ctx, "solvent", lx, top - 12); small(ctx, "solution", rx, top - 12); big(ctx, `Osmotic pressure ${fmt(a.Pi, 4)} Pa`, w / 2, 22);
  },
  /** Fuel burning under a can of water: Q (J), water heated. */
  burner(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const cx = w / 2, by = h * 0.3; beakerShape(ctx, cx - 70, by, 140, h * 0.32, 0.7, "rgba(70,140,220,.3)");
    rrect(ctx, cx - 30, h * 0.78, 60, 30, 6, "#d7c39b", INK); flame(ctx, cx, h * 0.78, 30 + 30 * soft(a.Q, 1e5), t);
    thermometer(ctx, cx + 50, by - 30, h * 0.25, a.T ?? 60);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** A ball rolling downhill if the change is spontaneous (dG < 0), uphill otherwise. */
  downhill(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const dG = finite(a.dG), sp = dG < 0, x0 = 60, x1 = w - 60, y0 = h * 0.35, y1 = h * 0.35 + clamp(-dG / 50, -0.35, 0.35) * h;
    seg(ctx, x0, y0, x1, y1, INK, 4); const p = sp ? cyc(t, 3) : 0.05 + 0.04 * Math.sin(t * 3);
    ball(ctx, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p - 14, 12, sp ? GREEN : EMBER, INK);
    big(ctx, sp ? `ΔG = ${fmt(dG, 4)}: it goes by itself` : `ΔG = ${fmt(dG, 4)}: it does not go by itself`, w / 2, h - 30, { color: sp ? GREEN : EMBER });
    (a.lines || []).forEach((s, i) => small(ctx, s, w / 2, 22 + i * 20));
  },
  /** Yield: product crystals against the theoretical amount. got, theo (g). */
  yieldDish(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const cx = w / 2, cy = h * 0.6, f = clamp(finite(a.got) / Math.max(1e-9, finite(a.theo)), 0, 1.2);
    ctx.fillStyle = "#e3e8ef"; ctx.beginPath(); ctx.ellipse(cx, cy, 160, 40, 0, 0, 7); ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.stroke();
    for (let k = 0; k < Math.round(40 * f); k++) { const x = cx - 120 + ((k * 61) % 240), y = cy - 10 + ((k * 37) % 20); ctx.fillStyle = a.colour || "#bfe3d0"; ctx.beginPath(); ctx.moveTo(x, y - 8); ctx.lineTo(x + 6, y); ctx.lineTo(x, y + 8); ctx.lineTo(x - 6, y); ctx.fill(); }
    big(ctx, `${fmt(a.got, 4)} g of ${fmt(a.theo, 4)} g possible: ${fmt(a.pct, 3)}%`, w / 2, 30); void t;
  },
  /** Equilibrium: forward and back arrows with A and B particles. ratio Q/K. */
  equilibrium(ctx, w, h, t, a) {
    bg(ctx, w, h);
    const dir = a.dir || "at equilibrium", x0 = 40, y0 = 50, bw = w - 80, bh = h - 120;
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, y0, bw, bh);
    const fA = clamp(finite(a.fA, 0.5), 0, 1);
    molecules(ctx, x0 + 4, y0 + 4, bw - 8, bh - 8, 60, t, 0.35, (i) => ((i % 60) / 60 < fA ? BLUE : ORANGE), 5, 4);
    big(ctx, dir, w / 2, h - 40, { color: EMBER }); (a.lines || []).forEach((s, i) => small(ctx, s, w / 2, 24 + i * 18));
  },
};
