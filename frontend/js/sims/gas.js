// Gas Properties: ideal_gas_law gives the pressure; maxwell_boltzmann gives the molecular speed distribution.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const GASES = {
  he: { label: "Helium (He)", M: 4.0026, color: "#eda100" },
  n2: { label: "Nitrogen (N₂)", M: 28.014, color: "#2a78d6" },
  o2: { label: "Oxygen (O₂)", M: 31.998, color: "#e34948" },
  ar: { label: "Argon (Ar)", M: 39.95, color: "#4a3aa7" },
  co2: { label: "Carbon dioxide (CO₂)", M: 44.009, color: "#39424e" },
};
const V_MAX_PLOT = 3500;   // m/s, fixed axis so gases/temperatures compare
const PX_PER_MPS = 0.16;   // visual speed scale

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2] = SERIES();
    let dist = null, pressure = null;
    let particles = [];
    let rngSeed = 3;
    const rand = () => ((rngSeed = (rngSeed * 16807) % 2147483647) / 2147483647);

    const gas = select({ label: "Gas", value: "n2", options: Object.entries(GASES).map(([value, g]) => ({ value, label: g.label })), onChange: () => recompute() });
    const moles = slider({ label: "Amount", min: 0.1, max: 5, step: 0.05, value: 1, unit: "mol", onInput: () => recompute() });
    const temp = slider({ label: "Temperature", min: 50, max: 1500, step: 5, value: 300, unit: "K", onInput: () => recompute() });
    const vol = slider({ label: "Volume", min: 5, max: 50, step: 0.5, value: 24.6, unit: "L", onInput: () => recompute() });
    const out = readouts([
      { key: "p", label: "Pressure" }, { key: "patm", label: "" },
      { key: "vp", label: "Most probable speed" }, { key: "vm", label: "Mean speed" }, { key: "vrms", label: "RMS speed" },
    ]);
    L.side.append(
      panel("Gas", gas.root, moles.root, temp.root, vol.root, el("p", { class: "note" }, "Each dot stands for many molecules; dot speeds are drawn from the real Maxwell–Boltzmann distribution.")),
      panel("State (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "Molecular speeds", xLabel: "speed (m/s)", yLabel: "density (×10⁻³ s/m)", height: 170, includeZero: true, xRange: [0, V_MAX_PLOT], yFormat: (v) => fmt(v * 1000, 2) });

    const recompute = liveRequest(async (signal) => {
      const [p, mb] = await Promise.all([
        simulate("chemistry", "ideal_gas_law", { volume: vol.value / 1000, moles: moles.value, temperature: temp.value }, signal),
        simulate("chemistry", "maxwell_boltzmann", { molar_mass: GASES[gas.value].M, temperature: temp.value, n_points: 140, max_speed: V_MAX_PLOT * 2 }, signal),
      ]);
      return { p, mb };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ p, mb }) => {
        L.clearError();
        pressure = p.result;
        const v = mb.curve.speed, f = mb.curve.probability_density;
        const cdf = [0];
        for (let i = 1; i < v.length; i++) cdf.push(cdf[i - 1] + 0.5 * (f[i] + f[i - 1]) * (v[i] - v[i - 1]));
        dist = { v, f, cdf: cdf.map((c) => c / cdf[cdf.length - 1]), res: mb.result };
        out.set("p", `${fmt(pressure / 1000, 4)} kPa`); out.set("patm", `${fmt(p.conversions.pressure_atm, 4)} atm`);
        out.set("vp", `${fmt(mb.result.most_probable_speed, 4)} m/s`); out.set("vm", `${fmt(mb.result.mean_speed, 4)} m/s`);
        out.set("vrms", `${fmt(mb.result.rms_speed, 4)} m/s`);
        syncParticles();
      },
    });

    // Speed for quantile u from the engine's distribution (inverse CDF).
    function speedAt(u) {
      const { v, cdf } = dist;
      let lo = 0, hi = cdf.length - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (cdf[m] < u) lo = m; else hi = m; }
      const f = (u - cdf[lo]) / Math.max(cdf[hi] - cdf[lo], 1e-12);
      return v[lo] + f * (v[hi] - v[lo]);
    }

    function box() {
      const { width: w, height: h } = stage;
      const bh = Math.min(h - 90, 360), maxW = Math.min(w - 170, bh * 1.9);
      const bw = maxW * (vol.value / 50);
      return { x: 60, y: (h - bh) / 2 + 20, w: bw, h: bh, maxW };
    }

    function syncParticles() {
      const n = Math.min(400, Math.round(moles.value * 90));
      const b = box();
      while (particles.length < n) {
        const a = rand() * Math.PI * 2;
        particles.push({ x: b.x + rand() * b.w, y: b.y + rand() * b.h, dx: Math.cos(a), dy: Math.sin(a), u: 0.02 + rand() * 0.96 });
      }
      particles.length = n;
      for (const p of particles) p.speed = speedAt(p.u);
    }

    let histTimer = 0;
    function updateHistogram() {
      if (!dist) return;
      const bins = 35, width = V_MAX_PLOT / bins, counts = new Array(bins).fill(0);
      for (const p of particles) { const k = Math.floor(p.speed / width); if (k < bins) counts[k]++; }
      const n = Math.max(1, particles.length);
      graph.setSeries([
        { name: "Molecules in the box", color: c1, x: counts.map((_, i) => (i + 0.5) * width), y: counts.map((c) => c / n / width), bars: true, alpha: 0.45 },
        { name: "Maxwell–Boltzmann (engine)", color: c2, x: dist.v, y: dist.f },
      ]);
    }

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#eef3f9"; ctx.fillRect(0, 0, w, h);
      const b = box();
      // Container, piston, handle
      ctx.fillStyle = "#fff"; ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 4; ctx.strokeRect(b.x, b.y, b.w, b.h);
      ctx.fillStyle = "#7b8796"; ctx.fillRect(b.x + b.w, b.y - 4, 12, b.h + 8);
      ctx.fillRect(b.x + b.w + 12, b.y + b.h / 2 - 4, b.maxW - b.w + 40, 8);
      // Heater
      const hot = Math.min(1, (temp.value - 50) / 1450);
      ctx.fillStyle = `rgb(${Math.round(80 + 175 * hot)},${Math.round(90 - 40 * hot)},${Math.round(110 - 80 * hot)})`;
      ctx.fillRect(b.x + 10, b.y + b.h + 8, b.w - 20, 10);
      label(ctx, `${fmt(temp.value, 4)} K`, b.x + b.w / 2, b.y + b.h + 32, { align: "center", font: "12px system-ui", color: "#4b5868" });

      // Particles
      const color = GASES[gas.value].color;
      ctx.fillStyle = color;
      for (const p of particles) {
        const s = (p.speed || 0) * PX_PER_MPS * dt;
        p.x += p.dx * s; p.y += p.dy * s;
        if (p.x < b.x + 4) { p.x = b.x + 4; p.dx = Math.abs(p.dx); }
        if (p.x > b.x + b.w - 4) { p.x = b.x + b.w - 4; p.dx = -Math.abs(p.dx); }
        if (p.y < b.y + 4) { p.y = b.y + 4; p.dy = Math.abs(p.dy); }
        if (p.y > b.y + b.h - 4) { p.y = b.y + b.h - 4; p.dy = -Math.abs(p.dy); }
        ctx.beginPath(); ctx.arc(p.x, p.y, 3, 0, Math.PI * 2); ctx.fill();
      }

      // Pressure gauge
      const gx = b.x + 70, gy = b.y - 40, r = 30;
      ctx.fillStyle = "#fff"; ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(gx, gy, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      if (pressure !== null) {
        const frac = Math.min(1, pressure / 2.5e6);
        const a = Math.PI * 0.75 + frac * Math.PI * 1.5;
        ctx.strokeStyle = "#e34948"; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(gx + Math.cos(a) * (r - 6), gy + Math.sin(a) * (r - 6)); ctx.stroke();
        label(ctx, `${fmt(pressure / 1000, 4)} kPa`, gx + r + 10, gy, { font: "bold 14px system-ui" });
      }
      label(ctx, `${fmt(vol.value, 3)} L`, b.x + b.w / 2, b.y - 12, { align: "center", font: "12px system-ui", color: "#4b5868" });

      histTimer += dt;
      if (histTimer > 0.4) { histTimer = 0; updateHistogram(); }
    });

    recompute();
    return () => { stop(); recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
