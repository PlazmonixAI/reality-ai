// Phase Diagrams: chemistry.phase_diagram gives the P–T curves and the phase at any temperature and pressure.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";

const SUBS = { water: "Water", co2: "Carbon dioxide" };
const fmtP = (p) => (p >= 1e6 ? `${fmt(p / 1e6, 4)} MPa` : p >= 1e3 ? `${fmt(p / 1e3, 4)} kPa` : `${fmt(p, 4)} Pa`);

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2, c3] = SERIES();
    let res = null, t = 0;
    const parts = Array.from({ length: 36 }, (_, i) => ({ gx: i % 6, gy: Math.floor(i / 6), x: Math.random(), y: Math.random(), vx: Math.random() - 0.5, vy: Math.random() - 0.5 }));

    const sub = select({ label: "Substance", value: "water", options: Object.entries(SUBS).map(([v, l]) => ({ value: v, label: l })), onChange: (v) => { if (v === "co2") { temp.set(195); pres.set(101325); } else { temp.set(298); pres.set(101325); } recompute(); } });
    const temp = slider({ label: "Temperature", min: 150, max: 750, step: 0.5, value: 298, unit: "K", onInput: () => recompute() });
    const pres = slider({ label: "Pressure", min: 10, max: 1e8, value: 101325, log: true, format: fmtP, onInput: () => recompute() });
    const out = readouts([{ key: "ph", label: "Phase" }, { key: "bp", label: "Boils at this pressure" }, { key: "mp", label: "Melts at this pressure" }, { key: "tp", label: "Triple point" }, { key: "cp", label: "Critical point" }]);
    L.side.append(
      panel("State", sub.root, temp.root, pres.root, legend([{ label: "sublimation (solid ↔ gas)", color: c3 }, { label: "boiling (liquid ↔ gas)", color: c1 }, { label: "melting (solid ↔ liquid)", color: c2 }]), el("p", { class: "note" }, "Click the diagram to jump there. Water's melting line leans left: squeezing ice melts it. Dry ice (CO₂) never melts at 1 atm — it sublimes.")),
      panel("Phase (from the engine)", out.root),
    );

    const recompute = liveRequest((signal) => simulate("chemistry", "phase_diagram", { substance: sub.value, temperature: temp.value, pressure: pres.value, p_max: 1e9 }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result, s = x.state;
        out.set("ph", s.phase); out.set("bp", s.boiling_point ? `${fmt(s.boiling_point, 5)} K (${fmt(s.boiling_point - 273.15, 4)} °C)` : s.sublimation_point ? `sublimes at ${fmt(s.sublimation_point, 5)} K` : "— (no liquid–gas boundary here)");
        out.set("mp", s.melting_point ? `${fmt(s.melting_point, 5)} K` : "—");
        out.set("tp", `${fmt(x.triple_point.temperature, 5)} K, ${fmtP(x.triple_point.pressure)}`); out.set("cp", `${fmt(x.critical_point.temperature, 5)} K, ${fmtP(x.critical_point.pressure)}`);
      },
    });

    let M = null;
    stage.canvas.addEventListener("click", (e) => {
      if (!M) return;
      const b = stage.canvas.getBoundingClientRect(), [T, P] = M.inv(e.clientX - b.left, e.clientY - b.top);
      if (T > 150 && T < 750 && P > 10 && P < 1e8) { temp.set(T); pres.set(P); recompute(); }
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      t += dt;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const cv = res.curves, pw = w - 250, left = 60, top = 20, bottom = h - 40;
      const T0 = 150, T1 = 750, lp0 = 1, lp1 = 8;
      const X = (T) => left + ((T - T0) / (T1 - T0)) * (pw - left), Y = (P) => bottom - ((Math.log10(P) - lp0) / (lp1 - lp0)) * (bottom - top);
      M = { inv: (px, py) => [T0 + ((px - left) / (pw - left)) * (T1 - T0), 10 ** (lp0 + ((bottom - py) / (bottom - top)) * (lp1 - lp0))] };
      ctx.save(); ctx.beginPath(); ctx.rect(left, top, pw - left, bottom - top); ctx.clip();
      // Grid
      ctx.strokeStyle = "#eef1f5"; ctx.lineWidth = 1;
      for (let lp = lp0; lp <= lp1; lp++) { ctx.beginPath(); ctx.moveTo(left, Y(10 ** lp)); ctx.lineTo(pw, Y(10 ** lp)); ctx.stroke(); }
      for (let T = 200; T <= 700; T += 100) { ctx.beginPath(); ctx.moveTo(X(T), top); ctx.lineTo(X(T), bottom); ctx.stroke(); }
      const line = (c, color) => { ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.beginPath(); c.temperature.forEach((T, i) => (i ? ctx.lineTo(X(T), Y(c.pressure[i])) : ctx.moveTo(X(T), Y(c.pressure[i])))); ctx.stroke(); };
      line(cv.sublimation, c3); line(cv.vaporisation, c1); line(cv.melting, c2);
      ctx.setLineDash([5, 5]); ctx.strokeStyle = "#9aa6b5"; ctx.lineWidth = 1.5;
      const cp = res.result.critical_point, tp = res.result.triple_point;
      ctx.beginPath(); ctx.moveTo(X(cp.temperature), Y(cp.pressure)); ctx.lineTo(X(cp.temperature), top); ctx.moveTo(X(cp.temperature), Y(cp.pressure)); ctx.lineTo(pw, Y(cp.pressure)); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = "#16202c";
      for (const p of [tp, cp]) { ctx.beginPath(); ctx.arc(X(p.temperature), Y(p.pressure), 5, 0, Math.PI * 2); ctx.fill(); }
      label(ctx, "triple point", X(tp.temperature) + 8, Y(tp.pressure) + 12, { font: "11px system-ui", halo: "#fff" });
      label(ctx, "critical point", X(cp.temperature) + 8, Y(cp.pressure) + 12, { font: "11px system-ui", halo: "#fff" });
      label(ctx, "SOLID", X(tp.temperature) - 60, Y(tp.pressure * 100), { font: "bold 14px system-ui", color: "#7b8796" });
      label(ctx, "LIQUID", X(tp.temperature + 0.25 * (cp.temperature - tp.temperature)), Y(Math.min(5e7, cp.pressure * 3)), { font: "bold 14px system-ui", color: "#7b8796" });
      label(ctx, "GAS", X(cp.temperature) + 20, Y(1e3), { font: "bold 14px system-ui", color: "#7b8796" });
      label(ctx, "SUPERCRITICAL", X(cp.temperature) + 14, Y(cp.pressure * 4), { font: "bold 12px system-ui", color: "#7b8796" });
      // State point
      ctx.fillStyle = "#e34948"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(X(temp.value), Y(pres.value), 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.restore();
      ctx.strokeStyle = "#7b8796"; ctx.strokeRect(left, top, pw - left, bottom - top);
      for (let lp = lp0; lp <= lp1; lp++) label(ctx, fmtP(10 ** lp), left - 6, Y(10 ** lp), { align: "right", font: "10px system-ui", color: "#4b5868" });
      for (let T = 200; T <= 700; T += 100) label(ctx, `${T} K`, X(T), bottom + 14, { align: "center", font: "11px system-ui", color: "#4b5868" });
      // Particle box (illustrative motion for the engine's phase)
      const phase = res.result.state.phase, bx = pw + 30, by = top + 40, bs = Math.min(190, h - 120);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.strokeRect(bx, by, bs, bs);
      const heat = Math.min(1, temp.value / 700);
      parts.forEach((p, k) => {
        let px, py;
        if (phase === "solid") { px = bx + 18 + p.gx * (bs - 36) / 5 + Math.sin(t * 20 + k) * 1.5 * heat; py = by + bs - 18 - p.gy * (bs - 36) / 5 + Math.cos(t * 17 + k) * 1.5 * heat; }
        else {
          const sp = phase === "liquid" ? 0.08 : 0.35 * (0.5 + heat);
          p.x += p.vx * sp * dt * 3; p.y += p.vy * sp * dt * 3;
          if (p.x < 0 || p.x > 1) p.vx *= -1; if (p.y < 0 || p.y > 1) p.vy *= -1;
          p.x = Math.min(1, Math.max(0, p.x)); p.y = Math.min(1, Math.max(0, p.y));
          const yy = phase === "liquid" ? 0.45 + p.y * 0.55 : p.y;
          px = bx + 8 + p.x * (bs - 16); py = by + 8 + yy * (bs - 16);
        }
        ctx.fillStyle = sub.value === "water" ? "#2a78d6" : "#7b8796"; ctx.beginPath(); ctx.arc(px, py, 6, 0, Math.PI * 2); ctx.fill();
      });
      label(ctx, phase.toUpperCase(), bx + bs / 2, by - 16, { align: "center", font: "bold 14px system-ui" });
      label(ctx, `${fmt(temp.value, 4)} K, ${fmtP(pres.value)}`, bx + bs / 2, by + bs + 18, { align: "center", font: "12px system-ui", color: "#4b5868" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
