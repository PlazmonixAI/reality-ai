// Physics worlds: motion, forces, fluids, heat, sound, electricity, magnetism, light and the atom.
// Arguments are engine numbers (already in SI) plus display text; see worlds.js for the rules.
import { fmt } from "../core/format.js";
import { INK, EMBER, T, small, big, ball, rrect, seg, arr, sky, dim, thermometer, beakerShape, flame, molecules, wavePath, waveColour,
  glowColour, car, person, block, soft, ssoft, clamp, cyc, finite } from "./worlds.js";

const BLUE = "#2a78d6", GREEN = "#1baf7a", ORANGE = "#eb6834";

export const PHYS = {
  // ---------------------------------------------------------------- motion
  /** A car on a road. v: speed (m/s) now; v0/v1: start and end speeds to sweep through; dist: distance label. */
  drive(ctx, w, h, t, a) {
    const gy = h * 0.68; sky(ctx, w, h, gy);
    ctx.fillStyle = "#c4c9d1"; ctx.fillRect(0, gy, w, 40); seg(ctx, 0, gy + 20, w, gy + 20, "#fff", 3, [22, 18]);
    const v0 = finite(a.v0 ?? a.v), v1 = finite(a.v1 ?? a.v), P = 4, ph = cyc(t, P);
    const vNow = v0 + (v1 - v0) * ph, px = 60 + (w - 120) * (ph * (v0 + (v1 - v0) * ph / 2) / Math.max(1e-9, (v0 + v1) / 2 || 1));
    const x = (v0 === 0 && v1 === 0) ? w / 2 : clamp(px, 50, w - 50);
    car(ctx, x, gy + 10, Math.min(110, w / 6), a.colour || INK);
    const vl = 140 * ssoft(vNow, 20);
    arr(ctx, x, gy - 55, x + vl, gy - 55, BLUE, 3);
    big(ctx, `v = ${fmt(vNow, 3)} m/s`, x, gy - 78, { color: BLUE });
    if (a.dist !== undefined) dim(ctx, 60, gy + 52, w - 60, gy + 52, a.distText || `${fmt(a.dist, 4)} m`, "#4D5769", 0);
    (a.lines || []).forEach((s, i) => small(ctx, s, 16, 22 + i * 18, { align: "left" }));
  },
  /** Two trains approaching: vA, vB (m/s), d (m) apart, tm (s) to meet. */
  trains(ctx, w, h, t, a) {
    const gy = h * 0.62; sky(ctx, w, h, gy); seg(ctx, 0, gy - 2, w, gy - 2, "#6b5844", 4);
    const P = 5, ph = cyc(t, P), vA = finite(a.vA), vB = finite(a.vB), tot = Math.abs(vA) + Math.abs(vB) || 1;
    const gap = (w - 140) * (1 - ph), xA = 70 + (w - 140 - gap) * (Math.abs(vA) / tot), xB = xA + gap;
    rrect(ctx, xA - 90, gy - 36, 90, 32, 6, BLUE, INK); rrect(ctx, xB, gy - 36, 90, 32, 6, ORANGE, INK);
    arr(ctx, xA - 45, gy - 50, xA - 45 + 60 * soft(vA, 15), gy - 50, BLUE); arr(ctx, xB + 45, gy - 50, xB + 45 - 60 * soft(vB, 15), gy - 50, ORANGE);
    small(ctx, `A: ${fmt(vA, 3)} m/s`, xA - 45, gy - 66); small(ctx, `B: ${fmt(vB, 3)} m/s`, xB + 45, gy - 66);
    big(ctx, a.title || "", w / 2, 26);
    if (a.d !== undefined) small(ctx, `Gap at start ${fmt(a.d, 4)} m`, w / 2, gy + 30);
  },
  /** Stopping: reaction distance then braking distance. d1, d2 (m), speed (km/h). */
  stopping(ctx, w, h, t, a) {
    const gy = h * 0.66; sky(ctx, w, h, gy); ctx.fillStyle = "#c4c9d1"; ctx.fillRect(0, gy, w, 40);
    const d1 = Math.max(0, finite(a.d1)), d2 = Math.max(0, finite(a.d2)), tot = d1 + d2 || 1, L = w - 160, x0 = 70;
    const xa = x0 + L * d1 / tot, xb = x0 + L;
    ctx.fillStyle = "rgba(42,120,214,.25)"; ctx.fillRect(x0, gy + 4, xa - x0, 32); ctx.fillStyle = "rgba(235,104,52,.3)"; ctx.fillRect(xa, gy + 4, xb - xa, 32);
    small(ctx, `thinking ${fmt(d1, 3)} m`, (x0 + xa) / 2, gy + 52, { color: BLUE }); small(ctx, `braking ${fmt(d2, 3)} m`, (xa + xb) / 2, gy + 52, { color: ORANGE });
    const ph = cyc(t, 5), s = ph < 0.85 ? ph / 0.85 : 1, f = s * tot; // travelled so far
    const x = x0 + L * (f <= d1 ? f / tot : (d1 + (f - d1)) / tot);
    car(ctx, x, gy + 10, 90); block(ctx, xb + 30, gy, 14, 40, "", "#c33");
    if (f > d1 && ph < 0.85) small(ctx, "brakes on", x, gy - 60, { color: ORANGE });
    big(ctx, `${fmt(a.kmh, 3)} km/h: stops in ${fmt(tot, 4)} m`, w / 2, 26);
  },
  /** Object on a circle: r (m), T (s), v (m/s), ac (m/s²). */
  circle(ctx, w, h, t, a) {
    const cx = w / 2, cy = h * 0.5, R = Math.min(w, h) * 0.32, P = clamp(finite(a.T, 2), 0.6, 8);
    seg(ctx, cx - 4, cy, cx + 4, cy, INK); ctx.strokeStyle = "#c5ccd8"; ctx.setLineDash([6, 6]); ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke(); ctx.setLineDash([]);
    const th = (2 * Math.PI * t) / P, x = cx + R * Math.cos(th), y = cy + R * Math.sin(th);
    seg(ctx, cx, cy, x, y, "#9aa3b2", 1.5);
    arr(ctx, x, y, x - Math.sin(th) * 70, y + Math.cos(th) * 70, BLUE); arr(ctx, x, y, x + (cx - x) * 0.35, y + (cy - y) * 0.35, ORANGE);
    ball(ctx, x, y, 12, EMBER, INK);
    small(ctx, `v = ${fmt(a.v, 3)} m/s`, x - Math.sin(th) * 80, y + Math.cos(th) * 80 - 12, { color: BLUE });
    if (a.ac !== undefined) small(ctx, `a = ${fmt(a.ac, 3)} m/s² to the centre`, w / 2, h - 50, { color: ORANGE });
    small(ctx, `r = ${fmt(a.r, 3)} m   T = ${fmt(a.T, 3)} s`, w / 2, 20);
  },
  /** Two carts collide. m1,u1,m2,u2 before; v1,v2 after (equal if they stick). */
  collide(ctx, w, h, t, a) {
    const gy = h * 0.62; ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, gy); ctx.fillStyle = WOODY; ctx.fillRect(0, gy, w, h - gy);
    const P = 5, ph = cyc(t, P), m1 = Math.max(1e-6, finite(a.m1, 1)), m2 = Math.max(1e-6, finite(a.m2, 1));
    const s1 = 36 + 40 * soft(m1, Math.max(m1, m2)), s2 = 36 + 40 * soft(m2, Math.max(m1, m2));
    const vs = Math.max(Math.abs(finite(a.u1)), Math.abs(finite(a.u2)), Math.abs(finite(a.v1)), Math.abs(finite(a.v2)), 1e-9), k = (w * 0.32) / vs / 2.2;
    let x1, x2, v1, v2, after = ph > 0.5;
    const tau = after ? (ph - 0.5) * P : (ph - 0.5) * P; // 0 at impact
    if (!after) { x1 = w / 2 - s1 / 2 + finite(a.u1) * tau * k; x2 = w / 2 + s2 / 2 + finite(a.u2) * tau * k; v1 = a.u1; v2 = a.u2; }
    else { x1 = w / 2 - s1 / 2 + finite(a.v1) * tau * k; x2 = w / 2 + s2 / 2 + finite(a.v2) * tau * k; v1 = a.v1; v2 = a.v2; }
    block(ctx, x1, gy, s1, s1 * 0.7, `${fmt(m1, 3)} kg`, BLUE); block(ctx, x2, gy, s2, s2 * 0.7, `${fmt(m2, 3)} kg`, ORANGE);
    arr(ctx, x1, gy - s1 * 0.7 - 14, x1 + 60 * ssoft(v1, vs), gy - s1 * 0.7 - 14, BLUE); arr(ctx, x2, gy - s2 * 0.7 - 14, x2 + 60 * ssoft(v2, vs), gy - s2 * 0.7 - 14, ORANGE);
    small(ctx, `${fmt(v1, 3)} m/s`, x1, gy - s1 * 0.7 - 30, { color: BLUE }); small(ctx, `${fmt(v2, 3)} m/s`, x2, gy - s2 * 0.7 - 30, { color: ORANGE });
    big(ctx, after ? "After the collision" : "Before the collision", w / 2, 26);
    (a.lines || []).forEach((s, i) => small(ctx, s, w / 2, gy + 30 + i * 18));
  },
  /** A block pushed by a force: F (N), m (kg), acc (m/s²), v (m/s). */
  push(ctx, w, h, t, a) {
    const gy = h * 0.64; ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, gy); ctx.fillStyle = WOODY; ctx.fillRect(0, gy, w, h - gy);
    const ph = cyc(t, 4), m = finite(a.m, 1), sz = 40 + 50 * soft(m, 10);
    const x = 90 + (w - 220) * ph * ph * clamp(soft(a.acc, 3) * 1.6, 0.05, 1);
    block(ctx, x, gy, sz, sz * 0.8, `${fmt(m, 3)} kg`);
    const F = finite(a.F), fl = 120 * ssoft(F, 20);
    arr(ctx, x - sz / 2 - 10 - Math.abs(fl), gy - sz * 0.4, x - sz / 2 - 6, gy - sz * 0.4, BLUE, 4);
    small(ctx, `F = ${fmt(F, 3)} N`, x - sz / 2 - Math.abs(fl) / 2 - 10, gy - sz * 0.4 - 16, { color: BLUE });
    if (a.acc !== undefined) arr(ctx, x, gy - sz * 0.8 - 18, x + 70 * ssoft(a.acc, 5), gy - sz * 0.8 - 18, ORANGE);
    if (a.acc !== undefined) small(ctx, `a = ${fmt(a.acc, 3)} m/s²`, x, gy - sz * 0.8 - 34, { color: ORANGE });
    (a.lines || []).forEach((s, i) => small(ctx, s, w / 2, gy + 30 + i * 18));
  },
  /** Something dropped from height H (m) hitting the ground at v; bars for PE and KE when given. */
  fall(ctx, w, h, t, a) {
    const gy = h * 0.86; sky(ctx, w, h, gy);
    const H = Math.max(0, finite(a.H, 10)), top = 40, x = w * 0.42, P = 3, ph = cyc(t, P), f = Math.min(1, (ph / 0.8) ** 2);
    const y = top + (gy - top - 14) * f;
    seg(ctx, x - 40, top, x + 40, top, "#9aa3b2", 2, [5, 4]); dim(ctx, x + 70, top, x + 70, gy, `${fmt(H, 4)} m`, "#4D5769", 0);
    ball(ctx, x, y, 14, EMBER, INK);
    if (f > 0.2) arr(ctx, x, y + 18, x, y + 18 + 60 * f, BLUE);
    big(ctx, a.title || `Lands at ${fmt(a.v, 4)} m/s`, w / 2, 20);
    if (a.PE !== undefined) {
      const tot = Math.max(1e-9, finite(a.PE) + finite(a.KE)), bx = w * 0.72, bh = gy - 80;
      [["PE", a.PE, BLUE], ["KE", a.KE, ORANGE]].forEach(([n, v, col], i) => { const hh = bh * clamp(finite(v) / tot, 0, 1); ctx.fillStyle = col; ctx.fillRect(bx + i * 60, gy - hh, 40, hh); small(ctx, n, bx + 20 + i * 60, gy + 12); small(ctx, `${fmt(v, 3)} J`, bx + 20 + i * 60, gy - hh - 12); });
    }
    (a.lines || []).forEach((s, i) => small(ctx, s, 16, 46 + i * 18, { align: "left" }));
  },
  /** Satellite around a planet. R (m) planet radius, hgt (m) altitude, T (s), v (m/s). */
  orbit(ctx, w, h, t, a) {
    ctx.fillStyle = "#0B1526"; ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 60; i++) ball(ctx, (i * 137.5) % w, (i * 71.3) % h, 1, "rgba(255,255,255,.6)");
    const cx = w / 2, cy = h / 2, Rp = Math.min(w, h) * 0.18, R = finite(a.R, 6.371e6), r = R + Math.max(0, finite(a.hgt));
    const ro = clamp(Rp * (r / R), Rp + 10, Math.min(w, h) * 0.46);
    const g = ctx.createRadialGradient(cx - Rp * 0.3, cy - Rp * 0.3, Rp * 0.1, cx, cy, Rp); g.addColorStop(0, "#5aa0e8"); g.addColorStop(1, "#1d4f8f");
    ball(ctx, cx, cy, Rp, g);
    ctx.strokeStyle = "rgba(255,255,255,.3)"; ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.arc(cx, cy, ro, 0, 7); ctx.stroke(); ctx.setLineDash([]);
    const th = t * 0.8 * clamp(Math.sqrt((Rp + 10) / ro) ** 3, 0.08, 1), x = cx + ro * Math.cos(th), y = cy + ro * Math.sin(th);
    rrect(ctx, x - 6, y - 4, 12, 8, 2, "#d9dde2"); seg(ctx, x - 16, y, x + 16, y, "#f5c518", 3);
    if (a.escape) { const k = cyc(t, 4); const ex = cx + (Rp + k * w * 0.45) * Math.cos(-0.6), ey = cy + (Rp + k * w * 0.45) * Math.sin(-0.6); ball(ctx, ex, ey, 5, EMBER); small(ctx, "escaping", ex, ey - 14, { color: "#fff", halo: null }); }
    T(ctx, a.title || "", w / 2, 22, { color: "#fff", halo: null, font: "700 16px Plex, system-ui" });
    (a.lines || []).forEach((s, i) => T(ctx, s, 16, h - 20 - i * 20, { align: "left", color: "#cfe0f5", halo: null, font: "600 13px Plex, system-ui" }));
  },
  /** A mass hanging from a spring balance on a planet: W (N) per g. */
  weigh(ctx, w, h, t, a) {
    const items = a.items || [];
    const n = items.length || 1;
    items.forEach((it, i) => {
      const cx = w * (i + 0.5) / n, top = 50, ext = 30 + 150 * soft(it.W, Math.max(...items.map((q) => finite(q.W))) || 1);
      ctx.fillStyle = it.colour || "#c9ced8"; ctx.fillRect(cx - 60, h * 0.86, 120, h * 0.14);
      seg(ctx, cx - 40, top, cx + 40, top, INK, 4);
      ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx, top);
      for (let k = 1; k <= 12; k++) ctx.lineTo(cx + (k % 2 ? 10 : -10), top + ext * k / 13);
      ctx.lineTo(cx, top + ext); ctx.stroke();
      block(ctx, cx, top + ext + 40, 46, 40, `${fmt(it.m, 3)} kg`, ORANGE);
      big(ctx, `${fmt(it.W, 4)} N`, cx, top + ext + 66); small(ctx, it.name, cx, h * 0.93, { color: "#fff", halo: null });
    });
  },
  /** Person on a scale in a lift; acc (m/s², up positive), R (N). */
  lift(ctx, w, h, t, a) {
    const acc = finite(a.acc), cx = w / 2, shaft = 30, bob = Math.sin(t * 1.5) * 20 * ssoft(acc, 3);
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h); seg(ctx, cx, 0, cx, shaft + bob + 20, "#555", 2);
    rrect(ctx, cx - 90, shaft + bob + 20, 180, h * 0.62, 6, "#fff", INK, 3);
    const fy = shaft + bob + 20 + h * 0.62 - 10;
    rrect(ctx, cx - 30, fy - 8, 60, 8, 2, "#444"); person(ctx, cx, fy - 8, 1.3);
    arr(ctx, cx + 120, h / 2, cx + 120, h / 2 - 70 * ssoft(acc, 4), BLUE, 4); small(ctx, `a = ${fmt(acc, 3)} m/s²`, cx + 120, h / 2 + 18, { color: BLUE });
    big(ctx, `Scale reads ${fmt(a.R, 4)} N (${fmt(a.kg, 3)} kg)`, w / 2, h - 20);
  },
  /** Car on a banked curve: th (deg), v speeds. */
  banked(ctx, w, h, t, a) {
    const th = finite(a.th) * Math.PI / 180, cx = w / 2, by = h * 0.72, L = Math.min(w * 0.36, 220);
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#c4c9d1"; ctx.beginPath(); ctx.moveTo(cx - L, by); ctx.lineTo(cx + L, by); ctx.lineTo(cx + L, by - 2 * L * Math.tan(th)); ctx.closePath(); ctx.fill();
    ctx.save(); ctx.translate(cx, by - L * Math.tan(th)); ctx.rotate(-th); car(ctx, 0, 0, 90); ctx.restore();
    small(ctx, `bank ${fmt(a.th, 3)}°`, cx + L - 40, by + 16);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 26 + i * 24));
  },
  /** Atwood machine: m1, m2 (kg), acc (m/s²), tension. */
  atwood(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2, py = 50, r = 34, acc = finite(a.acc), ph = Math.sin(t * 1.2) * 60 * ssoft(acc, 4);
    seg(ctx, cx - 80, 20, cx + 80, 20, INK, 5); seg(ctx, cx, 20, cx, py, INK, 3);
    ball(ctx, cx, py, r, METALC, INK);
    const y1 = h * 0.55 + ph, y2 = h * 0.55 - ph;
    seg(ctx, cx - r, py, cx - r, y1, INK, 2); seg(ctx, cx + r, py, cx + r, y2, INK, 2);
    block(ctx, cx - r, y1 + 40 * (0.6 + soft(a.m1, 5)), 50, 40 * (0.6 + soft(a.m1, 5)), `${fmt(a.m1, 3)} kg`, BLUE);
    block(ctx, cx + r, y2 + 40 * (0.6 + soft(a.m2, 5)), 50, 40 * (0.6 + soft(a.m2, 5)), `${fmt(a.m2, 3)} kg`, ORANGE);
    small(ctx, `a = ${fmt(acc, 3)} m/s²   T = ${fmt(a.T, 4)} N`, cx, h - 20);
  },
  /** Block-and-tackle pulley: n strands, load L (N), effort E (N). */
  tackle(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const n = clamp(Math.round(finite(a.n, 2)), 1, 8), cx = w / 2, top = 30, lift = 30 * (1 + Math.sin(t * 0.8)) / 2;
    seg(ctx, cx - 120, top, cx + 120, top, INK, 5);
    const by = h * 0.62 - lift;
    for (let i = 0; i < n; i++) seg(ctx, cx - 40 + (80 * i) / Math.max(1, n - 1 || 1), top, cx - 40 + (80 * i) / Math.max(1, n - 1 || 1), by - 30, INK, 2);
    rrect(ctx, cx - 50, top, 100, 26, 6, METALC, INK); rrect(ctx, cx - 50, by - 30, 100, 26, 6, METALC, INK);
    block(ctx, cx, by + 50, 70, 50, `${fmt(a.L, 3)} N`, ORANGE); seg(ctx, cx, by - 4, cx, by, INK, 2);
    seg(ctx, cx + 60, top + 12, cx + 120, h * 0.8 + lift, INK, 2); arr(ctx, cx + 120, h * 0.8 + lift, cx + 120, h * 0.8 + lift + 40, BLUE, 3);
    small(ctx, `effort ${fmt(a.E, 3)} N`, cx + 120, h * 0.8 + lift + 56, { color: BLUE });
    big(ctx, `${n} strands: mechanical advantage ${fmt(a.MA, 3)}`, w / 2, h - 18);
  },
  /** Seesaw with masses at positions x1, x2 (m) and the centre of mass xcm. */
  seesaw(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const span = Math.max(Math.abs(finite(a.x1)), Math.abs(finite(a.x2)), Math.abs(finite(a.xcm)), 1) * 1.2, X = (x) => w / 2 + (x / span) * (w * 0.42), by = h * 0.6;
    rrect(ctx, 20, by, w - 40, 10, 4, WOODY, INK);
    ctx.fillStyle = INK; ctx.beginPath(); ctx.moveTo(X(finite(a.xcm)), by + 10); ctx.lineTo(X(finite(a.xcm)) - 18, by + 50); ctx.lineTo(X(finite(a.xcm)) + 18, by + 50); ctx.fill();
    block(ctx, X(finite(a.x1)), by, 30 + 30 * soft(a.m1, 5), 30 + 30 * soft(a.m1, 5), `${fmt(a.m1, 3)}`, BLUE);
    block(ctx, X(finite(a.x2)), by, 30 + 30 * soft(a.m2, 5), 30 + 30 * soft(a.m2, 5), `${fmt(a.m2, 3)}`, ORANGE);
    small(ctx, `x₁ = ${fmt(a.x1, 3)} m`, X(finite(a.x1)), by + 26); small(ctx, `x₂ = ${fmt(a.x2, 3)} m`, X(finite(a.x2)), by + 26);
    big(ctx, `Balances at ${fmt(a.xcm, 4)} m`, X(finite(a.xcm)), by + 76, { color: EMBER });
  },
  /** Spanner turning a nut: F (N) at r (m) and angle th (deg); tau (N m). */
  wrench(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const cx = w * 0.3, cy = h / 2, L = Math.min(w * 0.5, 80 + 260 * soft(a.r, 0.3)), rot = t * 0.6 * ssoft(a.tau, 20);
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot);
    rrect(ctx, 0, -9, L, 18, 8, METALC, INK); ctx.fillStyle = "#666"; ctx.beginPath(); for (let k = 0; k < 6; k++) { const q = k * Math.PI / 3; ctx.lineTo(18 * Math.cos(q), 18 * Math.sin(q)); } ctx.fill();
    const th = finite(a.th, 90) * Math.PI / 180, fl = 90 * soft(a.F, 50);
    arr(ctx, L - fl * Math.cos(th), -fl * Math.sin(th) - 10, L, -10, BLUE, 4);
    ctx.restore();
    small(ctx, `F = ${fmt(a.F, 3)} N at ${fmt(a.r, 3)} m, ${fmt(a.th, 3)}°`, w / 2, 24); big(ctx, `Torque ${fmt(a.tau, 4)} N m`, w / 2, h - 20, { color: EMBER });
  },
  /** Ball rolling down a slope: th (deg), L (m), v at the bottom, t time. */
  roll(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const th = clamp(finite(a.th, 20), 1, 80) * Math.PI / 180, bx = w * 0.12, by = h * 0.82, L = Math.min(w * 0.75 / Math.cos(th), (h * 0.7) / Math.sin(th));
    ctx.fillStyle = "#c9ced8"; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx + L * Math.cos(th), by); ctx.lineTo(bx, by - L * Math.sin(th)); ctx.closePath(); ctx.fill();
    const f = Math.min(1, (cyc(t, 3.2) / 0.85) ** 2), d = L * f, r = 16;
    const x = bx + d * Math.cos(th) + r * Math.sin(th), y = by - (L - d) * Math.sin(th) - r * Math.cos(th);
    ball(ctx, x, y, r, EMBER, INK); const sp = d / r; seg(ctx, x, y, x + r * Math.cos(sp), y + r * Math.sin(sp), "#fff", 2);
    small(ctx, `${fmt(a.th, 3)}°`, bx + L * Math.cos(th) - 40, by - 12);
    big(ctx, `Bottom after ${fmt(a.time, 3)} s at ${fmt(a.v, 3)} m/s`, w / 2, 24);
  },
  /** Spinning skater: w1, w2 (rad/s) before and after pulling arms in. */
  spin(ctx, w, h, t, a) {
    ctx.fillStyle = "#eaf4fb"; ctx.fillRect(0, 0, w, h);
    [[a.w1, "Arms out", w * 0.28, 1], [a.w2, "Arms in", w * 0.72, 0.4]].forEach(([om, lab, cx, arm]) => {
      const ang = t * clamp(finite(om), -12, 12), cy = h * 0.55;
      ctx.fillStyle = "rgba(0,0,0,.08)"; ctx.beginPath(); ctx.ellipse(cx, cy + 70, 60, 12, 0, 0, 7); ctx.fill();
      person(ctx, cx, cy + 66, 1.4);
      const L = 70 * arm; seg(ctx, cx - L * Math.cos(ang), cy - 10 + L * 0.3 * Math.sin(ang), cx + L * Math.cos(ang), cy - 10 - L * 0.3 * Math.sin(ang), EMBER, 5);
      big(ctx, `${fmt(om, 3)} rad/s`, cx, 40); small(ctx, lab, cx, 62);
    });
  },
  /** A spring stretched or compressed by x (m) with force F (N) and energy U (J). */
  spring(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const wy = h * 0.55, x0 = 40, rest = w * 0.45, ext = 160 * ssoft(a.x, 0.1), osc = Math.sin(t * 2) * 6;
    seg(ctx, x0, wy - 50, x0, wy + 50, INK, 6);
    const end = x0 + rest + ext + osc; ctx.strokeStyle = INK; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x0, wy);
    for (let k = 1; k <= 16; k++) ctx.lineTo(x0 + (end - x0) * k / 17, wy + (k % 2 ? 14 : -14)); ctx.lineTo(end, wy); ctx.stroke();
    block(ctx, end + 30, wy + 30, 60, 60, "", EMBER);
    seg(ctx, x0 + rest + 30, wy + 50, x0 + rest + 30, wy + 80, "#9aa3b2", 1.5, [4, 4]); small(ctx, "natural length", x0 + rest + 30, wy + 92);
    arr(ctx, end + 70, wy, end + 70 - 80 * ssoft(a.F, 20), wy, BLUE, 3); small(ctx, `F = ${fmt(a.F, 3)} N`, end + 70, wy - 20, { color: BLUE });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 26 + i * 24));
  },
  /** A wire hanging from a support stretched by a load: dL (m), L (m), load text. */
  stretch(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2, top = 30, L0 = h * 0.5, ext = 120 * soft(a.dL, 0.002);
    seg(ctx, cx - 80, top, cx + 80, top, INK, 6); seg(ctx, cx, top, cx, top + L0 + ext, "#888", 3);
    block(ctx, cx, top + L0 + ext + 60, 70, 60, a.load || "", ORANGE);
    seg(ctx, cx + 60, top + L0, cx + 110, top + L0, "#9aa3b2", 1.5, [4, 4]); seg(ctx, cx + 60, top + L0 + ext, cx + 110, top + L0 + ext, EMBER, 1.5);
    small(ctx, `stretch ${fmt(a.dL, 3)} m (drawn larger)`, cx + 120, top + L0 + ext / 2, { align: "left", color: EMBER });
    (a.lines || []).forEach((s, i) => small(ctx, s, 16, h - 20 - i * 18, { align: "left" }));
  },
  /** Force spread over an area: F (N), A (m²), P (Pa). Two blocks: narrow and wide sinking into sand. */
  pressure(ctx, w, h, t, a) {
    const gy = h * 0.64; ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, gy); ctx.fillStyle = "#e8d6a8"; ctx.fillRect(0, gy, w, h - gy);
    const bw = clamp(30 + 260 * soft(a.A, 0.1), 20, w * 0.7), sink = 50 * soft(a.P, 2e4), cx = w / 2;
    block(ctx, cx, gy + sink, bw, 70, `${fmt(a.F, 3)} N`, ORANGE);
    for (let i = 0; i < 5; i++) arr(ctx, cx - bw / 2 + (bw * (i + 0.5)) / 5, gy + sink + 6, cx - bw / 2 + (bw * (i + 0.5)) / 5, gy + sink + 30, BLUE, 2);
    big(ctx, `Pressure ${fmt(a.P, 4)} Pa`, cx, 26); small(ctx, `area ${fmt(a.A, 3)} m²: the bigger the area, the less it sinks`, cx, h - 18);
  },
  /** Hydraulic lift: d1, d2 piston diameters (m), F1, F2 (N). */
  hydraulic(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const r1 = 14 + 50 * soft(a.d1, 0.1), r2 = 14 + 110 * soft(a.d2, 0.3), by = h * 0.82, x1 = w * 0.25, x2 = w * 0.68, ph = (Math.sin(t) + 1) / 2;
    const h1 = h * 0.35 + 40 * ph, h2 = h * 0.45 - 40 * ph * (r1 * r1) / (r2 * r2);
    ctx.fillStyle = "rgba(70,140,220,.35)"; ctx.fillRect(x1 - r1, h1, 2 * r1, by - h1); ctx.fillRect(x2 - r2, h2, 2 * r2, by - h2); ctx.fillRect(x1 - r1, by - 30, x2 - x1 + r1 + r2, 30);
    rrect(ctx, x1 - r1, h1 - 10, 2 * r1, 10, 2, "#555"); rrect(ctx, x2 - r2, h2 - 10, 2 * r2, 10, 2, "#555");
    arr(ctx, x1, h1 - 80, x1, h1 - 14, BLUE, 4); small(ctx, `F₁ = ${fmt(a.F1, 3)} N`, x1, h1 - 92, { color: BLUE });
    car(ctx, x2, h2 - 10, Math.min(2 * r2, 110)); big(ctx, `Lifts ${fmt(a.F2, 4)} N`, x2, h2 - 70, { color: EMBER });
  },
  /** Tank of liquid with a point at depth hd (m), pressure. */
  depth(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const top = 50, bot = h - 30, x0 = w * 0.2, x1 = w * 0.8, dy = top + (bot - top) * soft(a.hd, 10);
    ctx.fillStyle = "rgba(40,110,200,.35)"; ctx.fillRect(x0, top, x1 - x0, bot - top); ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, top, x1 - x0, bot - top);
    person(ctx, (x0 + x1) / 2 + Math.sin(t) * 20, dy + 26, 0.8, "#163a6a");
    for (const s of [-1, 1]) arr(ctx, (x0 + x1) / 2 + s * 80, dy, (x0 + x1) / 2 + s * 40, dy, EMBER, 3);
    dim(ctx, x1 + 10, top, x1 + 10, dy, `${fmt(a.hd, 4)} m`, "#4D5769", 14);
    big(ctx, a.title || "", w / 2, 24);
  },
  /** An object in a liquid: floats or sinks. rhoO, rhoL (kg/m³), sinks (bool), extra lines. */
  float(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const sur = h * 0.35, bot = h - 20, cx = w / 2, s = 70, ratio = finite(a.rhoO) / Math.max(1e-9, finite(a.rhoL, 1000));
    ctx.fillStyle = "rgba(40,110,200,.3)"; ctx.fillRect(40, sur, w - 80, bot - sur);
    const y = ratio >= 1 ? bot - s / 2 : sur - s / 2 + s * clamp(ratio, 0, 1) + Math.sin(t * 2) * 3;
    rrect(ctx, cx - s / 2, y - s / 2, s, s, 6, WOODY, INK);
    arr(ctx, cx, y + s / 2 + 50, cx, y + s / 2 + 4, BLUE, 3); small(ctx, "upthrust", cx + 40, y + s / 2 + 30, { color: BLUE });
    big(ctx, ratio >= 1 ? "It sinks" : `It floats with ${fmt(ratio * 100, 3)}% under`, w / 2, 24, { color: EMBER });
    (a.lines || []).forEach((s2, i) => small(ctx, s2, w / 2, 50 + i * 18));
  },
  /** Flow through a pipe that narrows: v1, v2 (m/s), dP (Pa). */
  venturi(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const cy = h / 2, R1 = 70, R2 = clamp(70 * Math.sqrt(Math.max(1e-6, finite(a.v1, 1)) / Math.max(1e-6, finite(a.v2, 2))), 10, 70);
    const xs = [30, w * 0.35, w * 0.45, w * 0.55, w * 0.65, w - 30], rs = [R1, R1, R2, R2, R1, R1];
    ctx.fillStyle = "rgba(70,140,220,.25)"; ctx.beginPath(); xs.forEach((x, i) => ctx.lineTo(x, cy - rs[i])); [...xs].reverse().forEach((x, i) => ctx.lineTo(x, cy + rs[rs.length - 1 - i])); ctx.fill();
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath(); xs.forEach((x, i) => ctx.lineTo(x, cy - rs[i])); ctx.stroke(); ctx.beginPath(); xs.forEach((x, i) => ctx.lineTo(x, cy + rs[i])); ctx.stroke();
    const rAt = (x) => { for (let i = 1; i < xs.length; i++) if (x <= xs[i]) return rs[i - 1] + (rs[i] - rs[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1]); return R1; };
    for (let k = 0; k < 40; k++) { const lane = ((k * 0.618) % 1) * 2 - 1; let x = 30 + ((t * 60 + k * 47) % (w - 60)); x = 30 + ((x - 30) ** 1) ; const r = rAt(x); ball(ctx, x, cy + lane * r * 0.8, 3, BLUE); }
    small(ctx, `v₁ = ${fmt(a.v1, 3)} m/s`, w * 0.18, cy - R1 - 16); small(ctx, `v₂ = ${fmt(a.v2, 3)} m/s`, w / 2, cy - R2 - 16, { color: EMBER });
    big(ctx, `Pressure drop ${fmt(a.dP, 4)} Pa`, w / 2, h - 20);
  },
  /** Ball sinking at terminal speed vt (m/s) in a tall jar of oil. */
  stokes(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const x0 = w * 0.4, x1 = w * 0.6, top = 30, bot = h - 20; ctx.fillStyle = "rgba(220,180,60,.35)"; ctx.fillRect(x0, top, x1 - x0, bot - top); ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, top, x1 - x0, bot - top);
    const sp = 0.05 + 0.6 * soft(a.vt, 0.05), y = top + 20 + ((t * sp * (bot - top)) % (bot - top - 40));
    ball(ctx, (x0 + x1) / 2, y, 6 + 10 * soft(a.r, 0.002), "#555"); arr(ctx, (x0 + x1) / 2 + 30, y - 20, (x0 + x1) / 2 + 30, y + 20, BLUE, 2);
    big(ctx, `Terminal speed ${fmt(a.vt, 4)} m/s`, w / 2, h / 2, { align: "left" });
  },
  /** Liquid rising in a thin tube: hc (m) rise. */
  capillary(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const sur = h * 0.7, cx = w / 2, rise = (sur - 40) * soft(a.hc, 0.05) * (0.9 + 0.1 * Math.sin(t));
    ctx.fillStyle = "rgba(40,110,200,.3)"; ctx.fillRect(40, sur, w - 80, h - sur - 10);
    ctx.fillRect(cx - 6, sur - rise, 12, rise); ctx.strokeStyle = INK; ctx.lineWidth = 2; ctx.strokeRect(cx - 8, 30, 16, h - 60);
    dim(ctx, cx + 20, sur, cx + 20, sur - rise, `${fmt(a.hc, 3)} m`, EMBER, 10);
    big(ctx, "The liquid climbs the narrow tube", w / 2, 18);
  },
  /** A motor lifting a load at speed v (m/s); P (W). */
  motor(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef1f5"; ctx.fillRect(0, 0, w, h);
    const cx = w * 0.4, top = 40, y = h * 0.85 - ((t * (20 + 200 * soft(a.v, 1))) % (h * 0.6));
    rrect(ctx, cx - 40, top - 20, 80, 40, 6, "#555"); ball(ctx, cx, top, 14, METALC, INK);
    seg(ctx, cx + 14, top, cx + 14, y - 40, INK, 2); block(ctx, cx + 14, y, 60, 40, `${fmt(a.m, 3)} kg`, ORANGE);
    (a.lines || []).forEach((s, i) => big(ctx, s, w * 0.72, h * 0.4 + i * 26));
  },

  // ---------------------------------------------------------------- heat
  /** One or more beakers with thermometers. items: [{T (°C), label, heat}] */
  heat(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const items = a.items || [], n = items.length || 1;
    items.forEach((it, i) => {
      const cx = w * (i + 0.5) / n, bw = Math.min(110, w / n - 40), by = h * 0.32, bh = h * 0.4;
      const hot = clamp((finite(it.T) - 20) / 80, 0, 1);
      beakerShape(ctx, cx - bw / 2, by, bw, bh, 0.7, `rgba(${Math.round(70 + 180 * hot)},${Math.round(140 - 60 * hot)},${Math.round(220 - 160 * hot)},.35)`);
      if (it.ice) for (let k = 0; k < 3; k++) rrect(ctx, cx - 30 + k * 20, by + bh * 0.35 + Math.sin(t + k) * 3, 16 * finite(it.ice, 1), 16 * finite(it.ice, 1), 3, "rgba(230,245,255,.95)", "#9cc");
      if (it.heat) flame(ctx, cx, by + bh + 34, 28, t);
      if (hot > 0.3) for (let k = 0; k < 3; k++) { const p = cyc(t + k * 0.3, 1.2); ctx.fillStyle = `rgba(200,200,200,${0.5 * (1 - p)})`; ball(ctx, cx - 20 + k * 20, by - p * 40, 6 + p * 8, ctx.fillStyle); }
      thermometer(ctx, cx + bw / 2 - 18, by - 30, bh * 0.8, it.T);
      small(ctx, it.label || "", cx, by + bh + (it.heat ? 76 : 20));
    });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** A rod that grows when hot: L (m), dL (m), dT. */
  rod(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const y = h * 0.45, L0 = w * 0.6, ext = 120 * soft(a.dL, 0.002), heat = clamp(finite(a.dT) / 300, 0, 1);
    rrect(ctx, 40, y - 16, L0, 32, 4, "#b0b6bf", INK); rrect(ctx, 40, y + 40, L0 + ext, 32, 4, `rgb(${180 + 70 * heat},${150 - 50 * heat},${120 - 80 * heat})`, INK);
    for (let k = 0; k < 5; k++) flame(ctx, 60 + k * (L0 / 5), y + 104, 20, t + k);
    small(ctx, "cold", 40 + L0 / 2, y - 30); small(ctx, `heated by ${fmt(a.dT, 3)} K`, 40 + L0 / 2, y + 26);
    dim(ctx, 40 + L0, y + 80, 40 + L0 + ext, y + 80, `+${fmt(a.dL, 3)} m`, EMBER, 30);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** Heat flowing through a wall: H (W), hot and cold sides. */
  conduct(ctx, w, h, t, a) {
    const cx = w / 2; ctx.fillStyle = "#fbe1d6"; ctx.fillRect(0, 0, cx - 40, h); ctx.fillStyle = "#dbe9f7"; ctx.fillRect(cx + 40, 0, w, h);
    const g = ctx.createLinearGradient(cx - 40, 0, cx + 40, 0); g.addColorStop(0, "#e0603a"); g.addColorStop(1, "#5a9be0"); ctx.fillStyle = g; ctx.fillRect(cx - 40, 30, 80, h - 60);
    const sp = 30 + 150 * soft(a.H, 100);
    for (let k = 0; k < 6; k++) { const x = cx - 120 + ((t * sp + k * 50) % 240); ball(ctx, x, 60 + k * (h - 120) / 5, 5, EMBER); }
    big(ctx, `Heat flow ${fmt(a.H, 4)} W`, w / 2, h - 14); small(ctx, "hot side", cx - 120, 20); small(ctx, "cold side", cx + 120, 20);
  },
  /** A hot body glowing: Tk (K), lam (m) peak, P (W). */
  glow(ctx, w, h, t, a) {
    ctx.fillStyle = "#101522"; ctx.fillRect(0, 0, w, h);
    const col = glowColour(a.Tk), cx = w / 2, cy = h * 0.45, r = 60;
    const g = ctx.createRadialGradient(cx, cy, 5, cx, cy, r * 2.4); g.addColorStop(0, col); g.addColorStop(1, "rgba(0,0,0,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, r * 2.4, 0, 7); ctx.fill(); ball(ctx, cx, cy, r, col);
    T(ctx, `${fmt(a.Tk, 4)} K`, cx, cy + r + 40, { color: "#fff", halo: null, font: "700 18px Plex, system-ui" });
    T(ctx, `Brightest at ${fmt(finite(a.lam) * 1e9, 4)} nm`, cx, cy + r + 66, { color: waveColour(a.lam), halo: null });
    T(ctx, `Radiates ${fmt(a.P, 4)} W`, cx, 24, { color: "#fff", halo: null });
  },
  /** Gas in a cylinder with a piston: V1→V2 fraction, molecule speed from temperature, lines. */
  piston(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const x0 = w * 0.18, x1 = w * 0.82, by = h * 0.85, maxH = h * 0.62, r = clamp(finite(a.ratio, 1), 0.05, 20);
    const f = (Math.sin(t * 0.9) + 1) / 2, V = 1 + (r - 1) * f, top = by - maxH * clamp(V / Math.max(1, r), 0.06, 1);
    ctx.fillStyle = "rgba(255,180,120,.18)"; ctx.fillRect(x0, top, x1 - x0, by - top);
    molecules(ctx, x0 + 4, top + 4, x1 - x0 - 8, by - top - 8, 34, t, clamp(finite(a.speed, 0.5), 0, 1), BLUE, 4);
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x0, by - maxH - 10); ctx.lineTo(x0, by); ctx.lineTo(x1, by); ctx.lineTo(x1, by - maxH - 10); ctx.stroke();
    rrect(ctx, x0 + 2, top - 14, x1 - x0 - 4, 14, 3, "#555"); seg(ctx, (x0 + x1) / 2, top - 14, (x0 + x1) / 2, top - 60, "#555", 6);
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** Heat engine: Qh in, W out, Qc to the cold side. */
  engine(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2; rrect(ctx, cx - 120, 20, 240, 50, 8, "#f3c6b3", INK); rrect(ctx, cx - 120, h - 70, 240, 50, 8, "#c9def3", INK);
    T(ctx, `Hot ${fmt(a.Th, 4)} K`, cx, 45); T(ctx, `Cold ${fmt(a.Tc, 4)} K`, cx, h - 45);
    ball(ctx, cx, h / 2, 40, "#e8ebf0", INK); seg(ctx, cx, h / 2, cx + 30 * Math.cos(t * 3), h / 2 + 30 * Math.sin(t * 3), INK, 4);
    const tot = Math.max(1e-9, finite(a.Qh)); const wid = (q) => 4 + 26 * clamp(finite(q) / tot, 0, 1);
    arr(ctx, cx, 72, cx, h / 2 - 44, EMBER, wid(a.Qh)); arr(ctx, cx, h / 2 + 44, cx, h - 74, BLUE, wid(a.Qc)); arr(ctx, cx + 44, h / 2, cx + 160, h / 2, GREEN, wid(a.W));
    small(ctx, `${fmt(a.Qh, 4)} J in`, cx + 60, h / 2 - 70); small(ctx, `${fmt(a.Qc, 4)} J out`, cx + 60, h / 2 + 70); small(ctx, `work ${fmt(a.W, 4)} J`, cx + 110, h / 2 - 16, { color: GREEN });
    big(ctx, `Efficiency ${fmt(finite(a.eta) * 100, 3)}%`, cx - 170, h / 2);
  },
  /** Gas molecules at a temperature; one or two gases. items [{n, speed 0..1, colour, label}] */
  gasbox(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const x0 = 30, y0 = 40, bw = w - 60, bh = h - 90; ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, y0, bw, bh);
    (a.items || []).forEach((it, i) => molecules(ctx, x0 + 4, y0 + 4, bw - 8, bh - 8, clamp(Math.round(finite(it.n, 20)), 0, 160), t, clamp(finite(it.speed, 0.5), 0, 1), it.colour || BLUE, it.r || 4, i + 1));
    (a.items || []).forEach((it, i) => small(ctx, it.label || "", x0 + 10 + i * 220, y0 + bh + 22, { align: "left", color: it.colour || BLUE }));
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 20 + i * 22));
  },

  // ---------------------------------------------------------------- sound and waves
  /** Sound pulse to a wall and back: d (m), v (m/s), time (s). */
  echo(ctx, w, h, t, a) {
    const sea = a.sea; ctx.fillStyle = sea ? "#cfe3f5" : "#eef3f8"; ctx.fillRect(0, 0, w, h);
    const x0 = 80, x1 = w - 70, cy = h * 0.55; if (sea) { ctx.fillStyle = "#2a5f9a"; ctx.fillRect(0, cy + 60, w, h); }
    if (sea) rrect(ctx, x0 - 50, cy - 30, 100, 26, 8, INK); else person(ctx, x0, cy + 40, 1.3);
    ctx.fillStyle = "#8b7a66"; ctx.fillRect(x1, 20, 50, h - 40);
    const ph = cyc(t, 3), out = ph < 0.5, f = out ? ph * 2 : (1 - ph) * 2, x = x0 + 20 + (x1 - x0 - 20) * f;
    ctx.strokeStyle = out ? BLUE : ORANGE; ctx.lineWidth = 3; for (let k = 0; k < 3; k++) { ctx.beginPath(); ctx.arc(x - (out ? k * 10 : -k * 10), cy, 18 + k * 6, -0.7, 0.7); if (!out) { ctx.beginPath(); ctx.arc(x + k * 10, cy, 18 + k * 6, Math.PI - 0.7, Math.PI + 0.7); } ctx.stroke(); }
    dim(ctx, x0, cy + 70, x1, cy + 70, `${fmt(a.d, 4)} m`, "#4D5769", 0);
    big(ctx, a.title || `Echo returns after ${fmt(a.time, 3)} s at ${fmt(a.v, 4)} m/s`, w / 2, 24);
  },
  /** Standing wave on a string or in a pipe: nh loops, f (Hz), lam (m), kind "string" | "open" | "closed". */
  standing(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const x0 = 50, x1 = w - 50, cy = h * 0.5, n = clamp(Math.round(finite(a.nh, 1)), 1, 12), amp = h * 0.18 * Math.cos(t * 8);
    const kind = a.kind || "string";
    if (kind !== "string") { ctx.fillStyle = "rgba(200,220,240,.5)"; ctx.fillRect(x0, cy - h * 0.22, x1 - x0, h * 0.44); seg(ctx, x0, cy - h * 0.22, x1, cy - h * 0.22, INK, 3); seg(ctx, x0, cy + h * 0.22, x1, cy + h * 0.22, INK, 3); if (kind === "closed") seg(ctx, x1, cy - h * 0.22, x1, cy + h * 0.22, INK, 6); }
    else { seg(ctx, x0, cy - 40, x0, cy + 40, INK, 6); seg(ctx, x1, cy - 40, x1, cy + 40, INK, 6); }
    const k = kind === "closed" ? (2 * n - 1) * Math.PI / 2 : n * Math.PI;
    ctx.strokeStyle = kind === "string" ? EMBER : BLUE; ctx.lineWidth = 3;
    for (const sgn of kind === "string" ? [1] : [1, -1]) { ctx.beginPath(); for (let x = x0; x <= x1; x += 2) { const u = (x - x0) / (x1 - x0), y = cy + sgn * amp * (kind === "string" ? Math.sin(k * u) : Math.cos(k * u)); if (x === x0) ctx.moveTo(x, y); else ctx.lineTo(x, y); } ctx.stroke(); }
    big(ctx, `${fmt(a.f, 4)} Hz`, w / 2, 24, { color: EMBER }); (a.lines || []).forEach((s, i) => small(ctx, s, w / 2, h - 40 + i * 18));
  },
  /** Two notes beating: f1, f2 (Hz), fb. */
  beats(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const f1 = finite(a.f1, 256), f2 = finite(a.f2, 260), fb = Math.abs(f1 - f2), x0 = 30, x1 = w - 30;
    const scale = 2 / Math.max(fb, 0.5), span = scale * 1.2; // show about two beats across the width
    const plot = (yc, fn, col) => { ctx.strokeStyle = col; ctx.lineWidth = 1.6; ctx.beginPath(); for (let x = x0; x <= x1; x += 1) { const tt = (x - x0) / (x1 - x0) * span + t * 0.05; const y = yc + fn(tt); if (x === x0) ctx.moveTo(x, y); else ctx.lineTo(x, y); } ctx.stroke(); };
    const vis = 30 / Math.max(f1, f2); // draw the carrier slower so it is visible
    plot(h * 0.2, (q) => 22 * Math.sin(2 * Math.PI * f1 * q * vis * 40), BLUE); plot(h * 0.42, (q) => 22 * Math.sin(2 * Math.PI * f2 * q * vis * 40), ORANGE);
    plot(h * 0.72, (q) => 22 * (Math.sin(2 * Math.PI * f1 * q * vis * 40) + Math.sin(2 * Math.PI * f2 * q * vis * 40)), INK);
    const loud = Math.abs(Math.cos(Math.PI * fb * t)); ball(ctx, w - 50, 40, 10 + 18 * loud, `rgba(255,91,46,${0.3 + 0.7 * loud})`);
    small(ctx, `${fmt(f1, 4)} Hz`, 60, h * 0.2 - 30, { color: BLUE }); small(ctx, `${fmt(f2, 4)} Hz`, 60, h * 0.42 - 30, { color: ORANGE });
    big(ctx, `Together: ${fmt(a.fb, 3)} beats every second`, w / 2, h - 18);
  },
  /** Moving sound source: vs (m/s), f (Hz) emitted, fh (Hz) heard in front. */
  doppler(ctx, w, h, t, a) {
    ctx.fillStyle = "#eef3f8"; ctx.fillRect(0, 0, w, h);
    const cy = h * 0.5, v = clamp(finite(a.vs) / 340, -0.9, 0.9), P = 6, ph = cyc(t, P), sx = w * 0.2 + w * 0.5 * ph;
    for (let k = 0; k < 10; k++) { const age = (ph * P - k * 0.5); if (age < 0) continue; const ex = w * 0.2 + w * 0.5 * ((ph * P - age) / P), r = age * 70; ctx.strokeStyle = `rgba(42,120,214,${Math.max(0, 0.8 - age / 5)})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(ex, cy, r, 0, 7); ctx.stroke(); }
    car(ctx, sx, cy + 20, 70, "#c33"); person(ctx, w - 40, cy + 40, 1);
    void v; small(ctx, `source ${fmt(a.vs, 3)} m/s, gives ${fmt(a.f, 4)} Hz`, w / 2, 22); big(ctx, `You hear ${fmt(a.fh, 4)} Hz`, w - 120, cy - 60, { color: EMBER });
  },

  // ---------------------------------------------------------------- electricity
  /** A circuit loop: battery V, resistor R (ohm), current I (A); glow from power P. extra resistors labels. */
  loop(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const x0 = w * 0.16, x1 = w * 0.84, y0 = h * 0.24, y1 = h * 0.74, I = finite(a.I);
    ctx.strokeStyle = INK; ctx.lineWidth = 3; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(x0 - 10, (y0 + y1) / 2 - 24, 20, 48); seg(ctx, x0 - 20, (y0 + y1) / 2 - 10, x0 + 20, (y0 + y1) / 2 - 10, INK, 3); seg(ctx, x0 - 10, (y0 + y1) / 2 + 8, x0 + 10, (y0 + y1) / 2 + 8, INK, 6);
    small(ctx, a.Vtext || `${fmt(a.V, 3)} V`, x0 - 30, (y0 + y1) / 2, { align: "right" });
    const parts = a.parts || [{ label: `${fmt(a.R, 3)} Ω`, P: a.P }];
    parts.forEach((p, i) => { const cx = x0 + (x1 - x0) * (i + 1) / (parts.length + 1); const glow = clamp(soft(p.P, 20), 0, 1);
      if (glow > 0.05) { const g = ctx.createRadialGradient(cx, y0, 4, cx, y0, 60); g.addColorStop(0, `rgba(255,140,40,${glow})`); g.addColorStop(1, "rgba(255,140,40,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, y0, 60, 0, 7); ctx.fill(); }
      rrect(ctx, cx - 34, y0 - 12, 68, 24, 4, "#fff", EMBER, 3); small(ctx, p.label, cx, y0 - 28); });
    const per = 2 * ((x1 - x0) + (y1 - y0)), sp = 20 + 120 * soft(I, 2);
    for (let k = 0; k < 22; k++) { let s = ((t * sp * Math.sign(I || 1) + (k * per) / 22) % per + per) % per, px, py;
      if (s < x1 - x0) { px = x0 + s; py = y0; } else if ((s -= x1 - x0) < y1 - y0) { px = x1; py = y0 + s; } else if ((s -= y1 - y0) < x1 - x0) { px = x1 - s; py = y1; } else { s -= x1 - x0; px = x0; py = y1 - s; }
      ball(ctx, px, py, 3.5, BLUE); }
    if (a.meter) { ball(ctx, (x0 + x1) / 2, y1, 22, "#fff", INK); small(ctx, a.meter, (x0 + x1) / 2, y1); }
    big(ctx, a.title || `I = ${fmt(I, 4)} A`, w / 2, y1 + 44); (a.lines || []).forEach((s, i) => small(ctx, s, w / 2, y1 + 70 + i * 18));
  },
  /** A metre wire with a sliding contact at l (cm out of 100). */
  bridge(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const x0 = 50, x1 = w - 50, y = h * 0.62, l = clamp(finite(a.l, 50), 0, 100), xj = x0 + (x1 - x0) * l / 100;
    rrect(ctx, x0 - 10, y - 6, x1 - x0 + 20, 30, 4, WOODY); seg(ctx, x0, y, x1, y, "#b87333", 3);
    for (let k = 0; k <= 10; k++) { seg(ctx, x0 + (x1 - x0) * k / 10, y + 6, x0 + (x1 - x0) * k / 10, y + 16, INK, 1); small(ctx, `${k * 10}`, x0 + (x1 - x0) * k / 10, y + 30); }
    seg(ctx, xj, y - 70, xj, y - 4, INK, 3); ball(ctx, xj, y - 4, 5, EMBER); ball(ctx, xj, y - 90, 22, "#fff", INK); small(ctx, a.meter || "G", xj, y - 90);
    small(ctx, `l = ${fmt(l, 4)} cm`, xj, y - 124, { color: EMBER });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** Capacitor plates: charge level 0..1 (fill), field arrows, labels. */
  capacitor(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2, cy = h * 0.5, gap = 30 + 120 * soft(a.d, 0.003), ph = clamp(finite(a.fill, 1), 0, 1), H = h * 0.5;
    rrect(ctx, cx - gap / 2 - 12, cy - H / 2, 12, H, 2, "#c33"); rrect(ctx, cx + gap / 2, cy - H / 2, 12, H, 2, BLUE);
    const n = Math.round(10 * ph);
    for (let k = 0; k < n; k++) { const y = cy - H / 2 + (H * (k + 0.5)) / 10; small(ctx, "+", cx - gap / 2 - 22, y, { color: "#c33" }); small(ctx, "−", cx + gap / 2 + 22, y, { color: BLUE }); arr(ctx, cx - gap / 2 + 4, y, cx + gap / 2 - 4, y, "rgba(235,104,52,.6)", 1.5); }
    if (a.K && finite(a.K) > 1) { ctx.fillStyle = "rgba(27,175,122,.18)"; ctx.fillRect(cx - gap / 2, cy - H / 2, gap, H); }
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
    if (a.bar !== undefined) { const bx = w - 60, bh = h * 0.6; rrect(ctx, bx, h * 0.2, 24, bh, 4, "#fff", INK); ctx.fillStyle = EMBER; ctx.fillRect(bx + 2, h * 0.2 + bh * (1 - clamp(a.bar, 0, 1)), 20, bh * clamp(a.bar, 0, 1)); small(ctx, a.barLabel || "", bx + 12, h * 0.2 + bh + 16); }
  },
  /** Two point charges and field lines; tilt (deg) in a field. */
  dipole(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2, sep = 80, th = finite(a.th, 0) * Math.PI / 180 * (a.field ? 1 : 0);
    if (a.field) for (let k = 0; k < 7; k++) arr(ctx, 30, 40 + k * (h - 80) / 6, w - 30, 40 + k * (h - 80) / 6, "rgba(42,120,214,.35)", 1.5);
    const wob = a.field ? Math.sin(t * 2) * 0.05 * ssoft(a.tau, 1e-24) : 0, ang = th + wob;
    const px = cx + sep * Math.cos(ang), py = cy - sep * Math.sin(ang), nx = cx - sep * Math.cos(ang), ny = cy + sep * Math.sin(ang);
    if (!a.field) for (let k = -3; k <= 3; k++) { ctx.strokeStyle = "rgba(235,104,52,.45)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(px, py); ctx.bezierCurveTo(px + 40, py - 40 * k, nx - 40, ny - 40 * k, nx, ny); ctx.stroke(); }
    seg(ctx, nx, ny, px, py, INK, 2); ball(ctx, px, py, 16, "#c33"); ball(ctx, nx, ny, 16, BLUE); T(ctx, "+", px, py, { color: "#fff", halo: null }); T(ctx, "−", nx, ny, { color: "#fff", halo: null });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** Straight wire (or solenoid / loop) with magnetic field circles and a compass. */
  bfield(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2, kind = a.kind || "wire", I = finite(a.I, 1), rot = t * 0.5 * Math.sign(I || 1);
    if (kind === "wire") {
      for (let k = 1; k <= 4; k++) { ctx.strokeStyle = `rgba(42,120,214,${0.7 - k * 0.12})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, k * 40, 0, 7); ctx.stroke(); const q = rot + k; arr(ctx, cx + k * 40 * Math.cos(q), cy + k * 40 * Math.sin(q), cx + k * 40 * Math.cos(q + 0.25), cy + k * 40 * Math.sin(q + 0.25), BLUE, 2); }
      ball(ctx, cx, cy, 12, METALC, INK); T(ctx, I >= 0 ? "•" : "×", cx, cy, { halo: null });
    } else if (kind === "solenoid") {
      for (let k = 0; k < 14; k++) { ctx.strokeStyle = "#b87333"; ctx.lineWidth = 3; ctx.beginPath(); ctx.ellipse(cx - 150 + k * 23, cy, 8, 50, 0, 0, 7); ctx.stroke(); }
      for (let k = -1; k <= 1; k++) arr(ctx, cx - 160, cy + k * 24, cx + 160, cy + k * 24, BLUE, 2);
    } else if (kind === "rails") {
      seg(ctx, 40, cy - 70, w - 40, cy - 70, INK, 4); seg(ctx, 40, cy + 70, w - 40, cy + 70, INK, 4); seg(ctx, 40, cy - 70, 40, cy + 70, INK, 3);
      for (let i = 0; i < 6; i++) for (let j = 0; j < 3; j++) small(ctx, "×", 80 + i * (w - 120) / 6, cy - 40 + j * 40, { color: "rgba(42,120,214,.6)" });
      const x = 80 + ((t * (20 + 160 * soft(a.v, 5))) % (w - 160)); seg(ctx, x, cy - 76, x, cy + 76, EMBER, 6); arr(ctx, x + 10, cy, x + 60, cy, ORANGE, 3);
    } else if (kind === "coil") {
      const ang = t * (0.5 + 2 * soft(a.f, 50)); ctx.fillStyle = "#c33"; ctx.fillRect(40, cy - 80, 50, 160); ctx.fillStyle = BLUE; ctx.fillRect(w - 90, cy - 80, 50, 160);
      ctx.strokeStyle = "#b87333"; ctx.lineWidth = 4; ctx.beginPath(); ctx.ellipse(cx, cy, 90 * Math.abs(Math.cos(ang)) + 2, 70, 0, 0, 7); ctx.stroke();
    } else if (kind === "parallel") {
      const d = 40 + 140 * soft(a.d, 0.05), pull = (finite(a.I1) * finite(a.I2) >= 0 ? -1 : 1) * Math.sin(t * 3) * 3;
      seg(ctx, cx - d / 2 - pull, 30, cx - d / 2 - pull, h - 30, "#b87333", 6); seg(ctx, cx + d / 2 + pull, 30, cx + d / 2 + pull, h - 30, "#b87333", 6);
      const sgn = finite(a.I1) * finite(a.I2) >= 0 ? 1 : -1; arr(ctx, cx - d / 2 - 40, cy, cx - d / 2 - 40 + sgn * 30, cy, EMBER, 3); arr(ctx, cx + d / 2 + 40, cy, cx + d / 2 + 40 - sgn * 30, cy, EMBER, 3);
      small(ctx, sgn > 0 ? "same direction: they attract" : "opposite: they repel", cx, h - 14);
    } else if (kind === "spiral") {
      const r = clamp(30 + 150 * soft(a.r, 0.05), 20, Math.min(w, h) * 0.42), q = t * 2; ctx.strokeStyle = "rgba(235,104,52,.35)"; ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke(); ctx.setLineDash([]);
      for (let i = 0; i < 6; i++) for (let j = 0; j < 4; j++) small(ctx, "×", 40 + i * (w - 80) / 5, 40 + j * (h - 80) / 3, { color: "rgba(42,120,214,.5)" });
      ball(ctx, cx + r * Math.cos(q), cy + r * Math.sin(q), 8, EMBER, INK);
    } else if (kind === "magnet") {
      ctx.fillStyle = "#c33"; ctx.fillRect(cx - 160, cy - 90, 80, 180); ctx.fillStyle = BLUE; ctx.fillRect(cx + 80, cy - 90, 80, 180); T(ctx, "N", cx - 120, cy, { color: "#fff", halo: null }); T(ctx, "S", cx + 120, cy, { color: "#fff", halo: null });
      for (let k = -2; k <= 2; k++) arr(ctx, cx - 76, cy + k * 30, cx + 76, cy + k * 30, "rgba(42,120,214,.45)", 1.5);
      const jig = Math.sin(t * 8) * 3 * soft(a.F, 0.5); ball(ctx, cx, cy + jig, 10, "#b87333", INK); arr(ctx, cx, cy, cx, cy - 70 * soft(a.F, 0.5) - 10, EMBER, 4);
    }
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },
  /** AC: a rotating coil's sine wave with peak and rms lines. */
  ac(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const cy = h / 2, A = h * 0.32, x0 = 30, x1 = w - 30;
    seg(ctx, x0, cy, x1, cy, "#c5ccd8", 1); seg(ctx, x0, cy - A, x1, cy - A, "#c5ccd8", 1, [4, 4]); seg(ctx, x0, cy - A * 0.7071, x1, cy - A * 0.7071, GREEN, 1.5, [6, 4]);
    wavePath(ctx, x0, x1, cy, -A, (x1 - x0) / 2.5, t * 3, BLUE);
    small(ctx, a.peak || "", x1 - 4, cy - A - 12, { align: "right" }); small(ctx, a.rms || "", x1 - 4, cy - A * 0.7071 - 12, { align: "right", color: GREEN });
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24));
  },

  // ---------------------------------------------------------------- light
  /** A ray crossing from medium 1 to 2: i, r angles (deg); tir when r is missing. slab: thickness and shift. */
  refract(ctx, w, h, t, a) {
    const cy = h * 0.5, cx = w / 2; ctx.fillStyle = "#f2f6fb"; ctx.fillRect(0, 0, w, cy); ctx.fillStyle = `rgba(80,150,220,${0.15 + 0.25 * soft(finite(a.n2, 1.5) - 1, 0.5)})`; ctx.fillRect(0, cy, w, h - cy);
    if (a.slab) { ctx.fillStyle = "#f2f6fb"; ctx.fillRect(0, cy + h * 0.28, w, h); }
    seg(ctx, cx, 20, cx, h - 20, "#9aa3b2", 1, [5, 5]);
    const i = finite(a.i) * Math.PI / 180, L = Math.min(cx, cy) * 0.9, sx = cx - L * Math.sin(i), sy = cy - L * Math.cos(i);
    const pulse = cyc(t, 2);
    ctx.strokeStyle = "#e33"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(cx, cy); ctx.stroke();
    if (a.r === null || a.r === undefined || !Number.isFinite(a.r)) {
      const ex = cx + L * Math.sin(i), ey = cy - L * Math.cos(i); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(ex, ey); ctx.stroke(); big(ctx, "Total internal reflection", w / 2, 24, { color: EMBER });
    } else {
      const r = finite(a.r) * Math.PI / 180; const L2 = a.slab ? (h * 0.28) / Math.cos(r) : L;
      const ex = cx + L2 * Math.sin(r), ey = cy + L2 * Math.cos(r); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(ex, ey); if (a.slab) ctx.lineTo(ex + L * 0.6 * Math.sin(i), ey + L * 0.6 * Math.cos(i)); ctx.stroke();
      ctx.strokeStyle = "rgba(230,50,50,.25)"; ctx.beginPath(); ctx.moveTo(cx - L * 0.15 * Math.sin(i), cy - L * 0.15 * Math.cos(i)); ctx.lineTo(sx + (cx - sx) * pulse, sy + (cy - sy) * pulse); ctx.stroke();
      small(ctx, `r = ${fmt(a.r, 3)}°`, cx + 50, cy + 40, { color: "#c33" });
    }
    small(ctx, `i = ${fmt(a.i, 3)}°`, cx - 50, cy - 40, { color: "#c33" }); small(ctx, a.top || "", 16, 20, { align: "left" }); small(ctx, a.bottom || "", 16, h - 18, { align: "left" });
    (a.lines || []).forEach((s, k) => big(ctx, s, w - 20, 24 + k * 22, { align: "right" }));
  },
  /** An optical bench: lenses [{x (cm), f (cm)}] with parallel light from the left meeting at the first focus. */
  lensbench(ctx, w, h, t, a) {
    ctx.fillStyle = "#f2f6fb"; ctx.fillRect(0, 0, w, h);
    const L = (a.lenses || []).map((q) => ({ x: finite(q.x), f: finite(q.f, 10) })), cy = h / 2;
    const span = Math.max(1, ...L.map((q) => Math.abs(q.x) + Math.abs(q.f))) * 1.25, s = (w * 0.62) / span, X = (x) => w * 0.22 + x * s;
    seg(ctx, 10, cy, w - 10, cy, "#9aa3b2", 1);
    L.forEach((q) => { const lx = X(q.x); ctx.strokeStyle = BLUE; ctx.lineWidth = 3; ctx.beginPath(); if (a.mirror) { ctx.arc(lx + 200, cy, 200, Math.PI - 0.45, Math.PI + 0.45); } else { ctx.ellipse(lx, cy, q.f >= 0 ? 10 : 4, h * 0.32, 0, 0, 7); } ctx.stroke();
      for (const sgn of [-1, 1]) { ball(ctx, X(q.x + sgn * q.f), cy, 4, INK); } small(ctx, `f = ${fmt(q.f, 3)} cm`, lx, cy + h * 0.36); });
    if (L.length) { const q = L[0], lx = X(q.x), fx = X(q.x + q.f), ph = cyc(t, 2.5);
      for (let k = -2; k <= 2; k++) { if (!k) continue; const y = cy + k * h * 0.11; ctx.strokeStyle = "#e33"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(20, y); ctx.lineTo(lx, y);
        if (q.f >= 0) ctx.lineTo(fx + (fx - lx) * 0.6, cy + (cy - y) * 0.6); else { ctx.lineTo(lx + (lx - fx) * 1.4, y + (y - cy) * 1.4); } ctx.stroke(); if (q.f < 0) seg(ctx, lx, y, fx, cy, "rgba(230,50,50,.35)", 1.5, [5, 5]); }
      ball(ctx, 20 + (lx - 20) * ph, cy - h * 0.22, 4, "#e33"); }
    (a.lines || []).forEach((s2, i) => big(ctx, s2, w / 2, 22 + i * 24));
  },
  /** Bright and dark fringes on a screen with spacing beta (m) and a slit pair. */
  fringes(ctx, w, h, t, a) {
    ctx.fillStyle = "#0e1320"; ctx.fillRect(0, 0, w, h);
    const col = waveColour(a.lam), sx = w * 0.12, scr = w * 0.78, cy = h / 2, sp = clamp(8 + 80 * soft(a.beta, 0.004), 6, 120);
    ctx.fillStyle = "#555"; ctx.fillRect(sx, 20, 8, cy - 30); ctx.fillRect(sx, cy - 4, 8, 8); ctx.fillRect(sx, cy + 10, 8, h - cy - 30);
    for (let k = 0; k < 8; k++) { const r = ((t * 60) + k * 30) % (scr - sx); ctx.strokeStyle = col; ctx.globalAlpha = 0.25; ctx.beginPath(); ctx.arc(sx + 8, cy - 7, r, -0.6, 0.6); ctx.stroke(); ctx.beginPath(); ctx.arc(sx + 8, cy + 7, r, -0.6, 0.6); ctx.stroke(); ctx.globalAlpha = 1; }
    for (let y = 20; y < h - 20; y += 2) { const ph = (y - cy) / sp, I = a.single ? (ph === 0 ? 1 : (Math.sin(Math.PI * ph) / (Math.PI * ph)) ** 2) : Math.cos(Math.PI * ph) ** 2; ctx.globalAlpha = I; ctx.fillStyle = col; ctx.fillRect(scr, y, 40, 2); }
    ctx.globalAlpha = 1; T(ctx, a.title || "", w / 2, 18, { color: "#fff", halo: null }); (a.lines || []).forEach((s, i) => T(ctx, s, w * 0.45, h - 20 - i * 20, { color: "#cfe0f5", halo: null, font: "600 13px Plex, system-ui" }));
  },
  /** Two polarisers at angle th; transmitted fraction f. */
  polar(ctx, w, h, t, a) {
    ctx.fillStyle = "#0e1320"; ctx.fillRect(0, 0, w, h);
    const cy = h / 2, f = clamp(finite(a.f, 1), 0, 1), th = finite(a.th) * Math.PI / 180;
    const disc = (x, ang) => { ball(ctx, x, cy, 60, "rgba(200,220,255,.12)", "#cfe0f5"); for (let k = -3; k <= 3; k++) { const ox = k * 14 * Math.cos(ang), oy = k * 14 * Math.sin(ang); seg(ctx, x + ox - 55 * Math.sin(ang) * 0.8, cy + oy + 55 * Math.cos(ang) * 0.8, x + ox + 55 * Math.sin(ang) * 0.8, cy + oy - 55 * Math.cos(ang) * 0.8, "rgba(207,224,245,.5)", 1.5); } };
    ctx.fillStyle = "rgba(255,240,180,.8)"; ctx.fillRect(20, cy - 20, w * 0.3 - 20, 40); ctx.fillStyle = `rgba(255,240,180,${0.8 * f})`; ctx.fillRect(w * 0.7, cy - 20, w * 0.3 - 20, 40);
    disc(w * 0.35, 0); disc(w * 0.62, th);
    T(ctx, `Angle ${fmt(a.th, 3)}°: ${fmt(f * 100, 3)}% gets through`, w / 2, h - 24, { color: "#fff", halo: null }); void t;
  },
  /** Light knocks electrons off a metal if the photon has enough energy. K (eV) max kinetic energy. */
  photo(ctx, w, h, t, a) {
    ctx.fillStyle = "#101522"; ctx.fillRect(0, 0, w, h);
    const col = waveColour(a.lam), mx = w * 0.6;
    rrect(ctx, mx, 40, 30, h - 80, 4, "#b0b6bf");
    for (let k = 0; k < 6; k++) { const p = cyc(t + k * 0.35, 2); const x = 30 + (mx - 30) * p, y = 60 + k * (h - 120) / 5; wavePath(ctx, x - 30, x, y, 5, 10, t * 10, col, 2); }
    const K = finite(a.K), on = K > 0;
    if (on) for (let k = 0; k < 6; k++) { const p = cyc(t * (0.4 + soft(K, 2)) + k * 0.17, 1); ball(ctx, mx + 34 + p * (w - mx - 50), 60 + k * (h - 120) / 5 + p * 10, 4, "#7fd3ff"); }
    T(ctx, on ? `Electrons fly off with up to ${fmt(K, 3)} eV` : "Below the threshold: no electrons", w / 2, 22, { color: on ? "#7fd3ff" : "#ffb3a0", halo: null });
    T(ctx, `λ = ${fmt(finite(a.lam) * 1e9, 4)} nm`, 80, h - 18, { color: col, halo: null });
  },
  /** Electron dropping from n2 to n1 in hydrogen, emitting a photon of wavelength lam (m). */
  levels(ctx, w, h, t, a) {
    ctx.fillStyle = "#101522"; ctx.fillRect(0, 0, w, h);
    const cx = w * 0.35, cy = h / 2, n1 = clamp(Math.round(finite(a.n1, 2)), 1, 8), n2 = clamp(Math.round(finite(a.n2, 3)), 1, 9), R = (n) => 14 + n * n * 5.5;
    ball(ctx, cx, cy, 8, "#ff8b6b");
    for (let n = 1; n <= Math.max(n2, 4); n++) { ctx.strokeStyle = n === n1 || n === n2 ? "rgba(255,255,255,.6)" : "rgba(255,255,255,.15)"; ctx.beginPath(); ctx.arc(cx, cy, Math.min(R(n), h * 0.45), 0, 7); ctx.stroke(); }
    const p = cyc(t, 2.4), r = p < 0.5 ? R(n2) : R(n2) + (R(n1) - R(n2)) * Math.min(1, (p - 0.5) * 4), q = t * 2;
    ball(ctx, cx + Math.min(r, h * 0.45) * Math.cos(q), cy + Math.min(r, h * 0.45) * Math.sin(q), 5, "#7fd3ff");
    if (p > 0.62) wavePath(ctx, cx + R(n1), cx + R(n1) + (w - cx) * (p - 0.62) * 1.4, cy, 8, 16, t * 12, waveColour(a.lam), 3);
    T(ctx, `n = ${n2} → ${n1}`, w * 0.78, 40, { color: "#fff", halo: null, font: "700 18px Plex, system-ui" });
    T(ctx, `λ = ${fmt(finite(a.lam) * 1e9, 4)} nm`, w * 0.78, 70, { color: waveColour(a.lam), halo: null });
    if (a.E !== undefined) T(ctx, `photon ${fmt(a.E, 4)} eV`, w * 0.78, 96, { color: "#cfe0f5", halo: null });
  },
  /** A nucleus of Z protons and N neutrons with binding energy per nucleon. */
  nucleus(ctx, w, h, t, a) {
    ctx.fillStyle = "#f6f4ef"; ctx.fillRect(0, 0, w, h);
    const Z = clamp(Math.round(finite(a.Z, 2)), 0, 120), A = clamp(Math.round(finite(a.A, 4)), 1, 300), cx = w / 2, cy = h / 2, R = 10 + 6 * Math.cbrt(A) * 3;
    for (let k = 0; k < Math.min(A, 160); k++) { const r = R * Math.sqrt((k + 0.5) / Math.min(A, 160)), q = k * 2.39996; ball(ctx, cx + r * Math.cos(q) + Math.sin(t * 6 + k) * 1.2, cy + r * Math.sin(q), 7, k < Z * Math.min(A, 160) / A ? "#d9534f" : "#8a94a6", "rgba(0,0,0,.2)"); }
    (a.lines || []).forEach((s, i) => big(ctx, s, w / 2, 22 + i * 24)); small(ctx, "red: protons, grey: neutrons", w / 2, h - 16);
  },
};

const WOODY = "#d8c3a5", METALC = "#c9ced8";
