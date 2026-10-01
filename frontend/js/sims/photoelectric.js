// Photoelectric Effect: physics.photoelectric computes photon energy, K_max, stopping voltage and the I-V curve.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";
import { wavelengthRGB } from "./interference.js";

// Typical textbook work functions (they vary with surface preparation).
const METALS = { sodium: ["Sodium", 2.28], potassium: ["Potassium", 2.3], calcium: ["Calcium", 2.9], zinc: ["Zinc", 4.3], copper: ["Copper", 4.7], platinum: ["Platinum", 5.65] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1] = SERIES();
    let res = null;
    const electrons = [];

    const metal = select({ label: "Metal", value: "sodium", options: Object.entries(METALS).map(([v, [l, p]]) => ({ value: v, label: `${l} (φ ≈ ${p} eV)` })), onChange: () => recompute() });
    const lam = slider({ label: "Wavelength", min: 100, max: 850, step: 1, value: 400, unit: "nm", onInput: () => recompute() });
    const power = slider({ label: "Light intensity", min: 0, max: 100, step: 1, value: 50, unit: "%", onInput: () => recompute() });
    const volt = slider({ label: "Battery voltage", min: -5, max: 5, step: 0.05, value: 0, unit: "V", onInput: () => { recompute(); iv.setCursor(volt.value); } });
    const out = readouts([
      { key: "e", label: "Photon energy" }, { key: "k", label: "Max electron energy" }, { key: "vs", label: "Stopping voltage" },
      { key: "th", label: "Threshold wavelength" }, { key: "i", label: "Current now" },
    ]);
    L.side.append(
      panel("Experiment", metal.root, lam.root, power.root, volt.root, el("p", { class: "note" }, "Below the threshold frequency no electrons come out, however bright the light. Negative voltage pushes electrons back.")),
      panel("Result (from the engine)", out.root),
    );
    const iv = new LineGraph(L.bottom, { title: "Current vs battery voltage", xLabel: "voltage (V)", yLabel: "current (µA)", height: 160, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "photoelectric", {
      wavelength_nm: lam.value, work_function_ev: METALS[metal.value][1], power: 1e-3 * power.value / 100, quantum_efficiency: 0.1,
    }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("e", `${fmt(x.photon_energy_ev, 4)} eV`); out.set("k", x.electrons_emitted ? `${fmt(x.max_kinetic_energy_ev, 4)} eV` : "no emission");
        out.set("vs", x.electrons_emitted ? `${fmt(x.stopping_voltage, 4)} V` : "–"); out.set("th", `${fmt(x.threshold_wavelength_nm, 4)} nm`);
        out.set("i", `${fmt(sampleAt(r.iv_curve.voltage, r.iv_curve.current, volt.value) * 1e6, 4)} µA`);
        iv.setSeries([{ name: "Current", color: c1, x: r.iv_curve.voltage, y: r.iv_curve.current.map((c) => c * 1e6) }]);
        iv.setCursor(volt.value);
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#101826"; ctx.fillRect(0, 0, w, h);
      const tubeL = w * 0.18, tubeR = w * 0.82, cy = h * 0.45;
      ctx.strokeStyle = "rgba(201,206,214,.5)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.roundRect(tubeL - 30, cy - 90, tubeR - tubeL + 60, 180, 80); ctx.stroke();
      ctx.fillStyle = "#b8c4d3"; ctx.fillRect(tubeL, cy - 70, 16, 140);
      ctx.fillStyle = "#7b8796"; ctx.fillRect(tubeR - 16, cy - 70, 16, 140);
      label(ctx, METALS[metal.value][0], tubeL + 8, cy + 88, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      // Light beam
      const rgb = lam.value >= 380 && lam.value <= 750 ? wavelengthRGB(lam.value) : [180, 140, 255];
      ctx.fillStyle = `rgba(${rgb.join(",")},${0.08 + 0.4 * power.value / 100})`;
      ctx.beginPath(); ctx.moveTo(w * 0.05, 20); ctx.lineTo(w * 0.12, 20); ctx.lineTo(tubeL + 16, cy - 60); ctx.lineTo(tubeL + 16, cy + 60); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#39424e"; ctx.fillRect(w * 0.03, 6, w * 0.1, 18);
      label(ctx, lam.value < 380 ? "UV" : lam.value > 750 ? "IR" : "", w * 0.08, 36, { align: "center", color: "#c9ced6", font: "11px system-ui" });
      // Electrons: spawn rate ∝ saturation current; speed from K_max; retarding field from the battery.
      if (res && res.result.electrons_emitted) {
        const rate = res.result.saturation_current / 3.2e-5 * 60;
        if (Math.random() < rate * dt) electrons.push({ x: tubeL + 18, y: cy + (Math.random() - 0.5) * 120, v: Math.sqrt(Math.random()) * Math.sqrt(res.result.max_kinetic_energy_ev) });
      }
      const span = tubeR - tubeL - 34;
      for (const e of electrons) {
        // energy along the gap: K(x) = K0 + e V (x / span); visual speed ∝ sqrt(K)
        const frac = (e.x - tubeL - 18) / span;
        const k = e.v * e.v + volt.value * frac;
        if (k <= 0) e.back = true;
        const sp = 140 * Math.sqrt(Math.max(k, 0.02));
        e.x += (e.back ? -1 : 1) * sp * dt;
      }
      for (let i = electrons.length - 1; i >= 0; i--) { const e = electrons[i]; if (e.x > tubeR - 16 || e.x < tubeL + 16) electrons.splice(i, 1); }
      ctx.fillStyle = "#5598e7";
      for (const e of electrons) { ctx.beginPath(); ctx.arc(e.x, e.y, 3.5, 0, Math.PI * 2); ctx.fill(); }
      // Circuit + battery
      ctx.strokeStyle = "#c9ced6"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(tubeL + 8, cy + 70); ctx.lineTo(tubeL + 8, h - 30); ctx.lineTo(tubeR - 8, h - 30); ctx.lineTo(tubeR - 8, cy + 70); ctx.stroke();
      ctx.fillStyle = "#26303d"; ctx.fillRect(w / 2 - 50, h - 48, 100, 36);
      label(ctx, `${volt.value >= 0 ? "+" : ""}${fmt(volt.value, 3)} V`, w / 2, h - 30, { align: "center", color: "#fff", font: "bold 13px system-ui" });
      label(ctx, "blue dots = photoelectrons (illustrative)", w - 12, 16, { align: "right", color: "#7b8796", font: "11px system-ui" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); iv.destroy(); stage.destroy(); };
  },
};
