// Bending Light: physics.refraction gives Snell's-law angles and Fresnel reflectance.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";
import { wavelengthRGB } from "./interference.js";

const MATERIALS = { air: ["Air", 1.0003], water: ["Water", 1.333], glass: ["Glass", 1.5], diamond: ["Diamond", 2.417], custom: ["Custom", null] };
const tint = (n) => `rgba(42,120,214,${Math.min(0.45, (n - 1) * 0.3)})`;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null, dragging = false;

    const top = select({ label: "Top material", value: "air", options: Object.entries(MATERIALS).map(([v, [l]]) => ({ value: v, label: l })), onChange: () => syncN() });
    const nTop = slider({ label: "n (top)", min: 1, max: 2.5, step: 0.001, value: 1.0003, digits: 4, onInput: () => { top.set("custom"); recompute(); } });
    const bot = select({ label: "Bottom material", value: "water", options: Object.entries(MATERIALS).map(([v, [l]]) => ({ value: v, label: l })), onChange: () => syncN() });
    const nBot = slider({ label: "n (bottom)", min: 1, max: 2.5, step: 0.001, value: 1.333, digits: 4, onInput: () => { bot.set("custom"); recompute(); } });
    const angle = slider({ label: "Angle of incidence", min: 0, max: 89, step: 0.5, value: 45, unit: "°", onInput: () => { recompute(); graph.setCursor(angle.value); } });
    const lam = slider({ label: "Laser colour", min: 400, max: 700, step: 1, value: 632, unit: "nm", onInput: () => draw() });
    const out = readouts([
      { key: "t2", label: "Refraction angle" }, { key: "R", label: "Reflected" }, { key: "T", label: "Transmitted" },
      { key: "crit", label: "Critical angle" }, { key: "brew", label: "Brewster angle" },
    ]);
    function syncN() {
      for (const [sel, sl] of [[top, nTop], [bot, nBot]]) { const n = MATERIALS[sel.value][1]; if (n) sl.set(n); }
      recompute();
    }
    L.side.append(
      panel("Materials", top.root, nTop.root, bot.root, nBot.root),
      panel("Laser", angle.root, lam.root, el("p", { class: "note" }, "Drag the laser around the top half. Put the denser material on top to find total internal reflection.")),
      panel("Result (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "Reflectance vs angle of incidence", xLabel: "incidence (°)", yLabel: "fraction reflected", height: 160, yRange: [0, 1] });

    const recompute = liveRequest(async (signal) => {
      const n1 = nTop.value, n2 = nBot.value;
      const main = await simulate("physics", "refraction", { n1, n2, incidence_deg: angle.value }, signal);
      const angles = Array.from({ length: 45 }, (_, i) => i * 2);
      const sweep = await Promise.all(angles.map((a) => simulate("physics", "refraction", { n1, n2, incidence_deg: a }, signal)));
      return { main, angles, sweep };
    }, {
      delay: 60, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ main, angles, sweep }) => {
        L.clearError(); res = main.result;
        out.set("t2", res.total_internal_reflection ? "— (total internal reflection)" : `${fmt(res.refraction_deg, 4)}°`);
        out.set("R", `${fmt(res.reflectance * 100, 3)} %`); out.set("T", `${fmt(res.transmittance * 100, 3)} %`);
        out.set("crit", res.critical_angle_deg ? `${fmt(res.critical_angle_deg, 4)}°` : "none (n₁ ≤ n₂)");
        out.set("brew", `${fmt(res.brewster_angle_deg, 4)}°`);
        graph.setSeries([
          { name: "s-polarised", color: c1, x: angles, y: sweep.map((s) => s.result.reflectance_s) },
          { name: "p-polarised", color: c2, x: angles, y: sweep.map((s) => s.result.reflectance_p), dash: true },
          { name: "unpolarised", color: c3, x: angles, y: sweep.map((s) => s.result.reflectance) },
        ]);
        graph.setCursor(angle.value);
        draw();
      },
    });

    const centre = () => [stage.width / 2, stage.height / 2];
    stage.canvas.addEventListener("pointerdown", (e) => { dragging = true; stage.canvas.setPointerCapture(e.pointerId); move(e); });
    stage.canvas.addEventListener("pointermove", (e) => { if (dragging) move(e); });
    stage.canvas.addEventListener("pointerup", () => { dragging = false; });
    function move(e) {
      const r = stage.canvas.getBoundingClientRect(), [cx, cy] = centre();
      const dx = e.clientX - r.left - cx, dy = cy - (e.clientY - r.top);
      if (dy <= 0) return;
      angle.set(Math.min(89, Math.round((Math.atan2(Math.abs(dx), dy) * 180) / Math.PI * 2) / 2)); recompute(); draw();
    }

    function ray(ctx, x0, y0, ang, len, rgb, alpha, width = 5) {
      ctx.strokeStyle = `rgba(${rgb.join(",")},${alpha})`; ctx.lineWidth = width; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + Math.cos(ang) * len, y0 + Math.sin(ang) * len); ctx.stroke();
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const [cx, cy] = centre();
      ctx.fillStyle = "#fbfcfe"; ctx.fillRect(0, 0, w, cy);
      ctx.fillStyle = tint(nTop.value); ctx.fillRect(0, 0, w, cy);
      ctx.fillStyle = "#fbfcfe"; ctx.fillRect(0, cy, w, h - cy);
      ctx.fillStyle = tint(nBot.value); ctx.fillRect(0, cy, w, h - cy);
      label(ctx, `${MATERIALS[top.value][0]}  n = ${fmt(nTop.value, 4)}`, 14, 20, { font: "13px system-ui" });
      label(ctx, `${MATERIALS[bot.value][0]}  n = ${fmt(nBot.value, 4)}`, 14, h - 18, { font: "13px system-ui" });
      ctx.setLineDash([6, 6]); ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(cx, 20); ctx.lineTo(cx, h - 20); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, "normal", cx + 6, 34, { font: "11px system-ui", color: "#7b8796" });
      const len = Math.hypot(w, h), rgb = wavelengthRGB(lam.value);
      const t1 = (angle.value * Math.PI) / 180;
      // Laser housing
      const lx = cx - Math.sin(t1) * Math.min(cx, cy) * 0.85, ly = cy - Math.cos(t1) * Math.min(cx, cy) * 0.85;
      ctx.save(); ctx.translate(lx, ly); ctx.rotate(Math.PI / 2 - t1);
      ctx.fillStyle = "#39424e"; ctx.fillRect(-46, -11, 50, 22); ctx.fillStyle = "#e34948"; ctx.fillRect(0, -5, 6, 10);
      ctx.restore();
      ray(ctx, lx, ly, Math.atan2(cy - ly, cx - lx), Math.hypot(cx - lx, cy - ly), rgb, 1);
      if (res) {
        ray(ctx, cx, cy, -Math.PI / 2 + t1, len, rgb, Math.max(0.08, res.reflectance));
        if (!res.total_internal_reflection) {
          const t2 = (res.refraction_deg * Math.PI) / 180;
          ray(ctx, cx, cy, Math.PI / 2 - t2, len, rgb, Math.max(0.08, res.transmittance));
          ctx.strokeStyle = "#16202c"; ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.arc(cx, cy, 70, Math.PI / 2 - t2, Math.PI / 2); ctx.stroke();
          label(ctx, `θ₂ = ${fmt(res.refraction_deg, 3)}°`, cx + 16, cy + 92, { font: "bold 13px system-ui" });
        } else label(ctx, "Total internal reflection", cx + 16, cy + 40, { font: "bold 14px system-ui", color: "#c93a3a" });
        ctx.strokeStyle = "#16202c"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(cx, cy, 70, -Math.PI / 2 - t1, -Math.PI / 2); ctx.stroke();
        label(ctx, `θ₁ = ${fmt(angle.value, 3)}°`, cx - 16, cy - 90, { font: "bold 13px system-ui", align: "right" });
        label(ctx, `reflected ${fmt(res.reflectance * 100, 3)}%`, cx + Math.sin(t1) * 150 + 10, cy - Math.cos(t1) * 150, { font: "12px system-ui" });
      }
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
