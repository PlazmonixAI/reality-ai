// Vapour Pressure & Boiling: chemistry.vapor_pressure (Clausius-Clapeyron) sets when a liquid boils at a given pressure.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Enthalpy of vaporisation (J/mol) and normal boiling point (K), common textbook values.
const LIQUIDS = {
  water: ["Water", 40650, 373.15], ethanol: ["Ethanol", 38560, 351.4], benzene: ["Benzene", 30720, 353.2],
  acetone: ["Acetone", 29100, 329.2], ether: ["Diethyl ether", 26520, 307.6],
};
// External pressure presets (Pa): places people cook.
const PLACES = { sea: ["Sea level", 101325], denver: ["Denver (1.6 km)", 83400], lapaz: ["La Paz (3.6 km)", 64000], everest: ["Everest summit", 33700], cooker: ["Pressure cooker", 200000] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2] = SERIES();
    let res = null, tb = null, t = 0;
    const bubbles = [];

    const liquid = select({ label: "Liquid", value: "water", options: Object.entries(LIQUIDS).map(([v, [l]]) => ({ value: v, label: l })), onChange: () => recompute() });
    const place = select({ label: "Where", value: "sea", options: [...Object.entries(PLACES).map(([v, [l]]) => ({ value: v, label: l })), { value: "custom", label: "Custom pressure" }], onChange: (v) => { if (PLACES[v]) pres.set(PLACES[v][1] / 1000); recompute(); } });
    const pres = slider({ label: "Air pressure", min: 10, max: 250, step: 0.1, value: 101.3, unit: "kPa", onInput: () => { place.set("custom"); recompute(); } });
    const temp = slider({ label: "Liquid temperature", min: 250, max: 420, step: 0.5, value: 350, unit: "K", onInput: () => recompute() });
    const out = readouts([
      { key: "vp", label: "Vapour pressure now" }, { key: "tb", label: "Boiling point here" }, { key: "state", label: "State" },
      { key: "ds", label: "ΔS_vap (Trouton ≈ 88)" },
    ]);
    L.side.append(
      panel("Pot", liquid.root, place.root, pres.root, temp.root, el("p", { class: "note" }, "A liquid boils when its vapour pressure reaches the pressure above it, so water boils cooler on a mountain.")),
      panel("Result (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "Vapour pressure vs temperature", xLabel: "temperature (K)", yLabel: "pressure (kPa)", height: 160, includeZero: true });

    const recompute = liveRequest((signal) => {
      const [, dh, tn] = LIQUIDS[liquid.value];
      return simulate("chemistry", "vapor_pressure", { enthalpy_vap: dh, boiling_point: tn, temperature: temp.value, pressure: pres.value * 1000, t_min: 250, t_max: 420 }, signal);
    }, {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result; tb = res.boiling_point_at_pressure;
        const boiling = res.vapor_pressure >= pres.value * 1000;
        out.set("vp", `${fmt(res.vapor_pressure / 1000, 4)} kPa`); out.set("tb", `${fmt(tb, 4)} K (${fmt(tb - 273.15, 4)} °C)`);
        out.set("state", boiling ? "boiling" : "below its boiling point"); out.set("ds", `${fmt(res.entropy_vap, 4)} J/(mol·K)`);
        const keep = r.curve.pressure.map((p, i) => (p <= 300e3 ? i : -1)).filter((i) => i >= 0);
        graph.setSeries([
          { name: `${LIQUIDS[liquid.value][0]} vapour pressure`, color: c1, x: keep.map((i) => r.curve.temperature[i]), y: keep.map((i) => r.curve.pressure[i] / 1000) },
          { name: "air pressure", color: c2, dash: true, x: [250, 420], y: [pres.value, pres.value] },
        ]);
        graph.setCursor(temp.value);
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      t += dt;
      const pw = Math.min(320, w * 0.45), ph = Math.min(200, h * 0.45), px = w * 0.4 - pw / 2, py = h * 0.35;
      const boiling = res.vapor_pressure >= pres.value * 1000;
      // Flame intensity follows how hot the liquid is (display only)
      const heat = Math.max(0, Math.min(1, (temp.value - 250) / 170));
      for (let i = 0; i < 7; i++) {
        const fx = px + pw * (0.15 + i * 0.12), fh = 18 + 30 * heat + 6 * Math.sin(t * 9 + i);
        ctx.fillStyle = `rgba(235,104,52,${0.3 + 0.6 * heat})`; ctx.beginPath(); ctx.moveTo(fx - 9, py + ph + 44); ctx.quadraticCurveTo(fx, py + ph + 44 - fh * 2, fx + 9, py + ph + 44); ctx.fill();
      }
      ctx.fillStyle = "#39424e"; ctx.fillRect(px - 20, py + ph + 44, pw + 40, 10);
      ctx.fillStyle = "rgba(42,120,214,.35)"; ctx.fillRect(px, py + ph * 0.3, pw, ph * 0.7);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, py + ph); ctx.lineTo(px + pw, py + ph); ctx.lineTo(px + pw, py); ctx.stroke();
      // Bubbles form throughout the liquid only when boiling; otherwise a few evaporating molecules at the surface
      const ratio = res.vapor_pressure / (pres.value * 1000);
      if (boiling && Math.random() < dt * 40) bubbles.push({ x: px + 10 + Math.random() * (pw - 20), y: py + ph - 6, r: 2 + Math.random() * 3 });
      for (const b of bubbles) { b.y -= dt * 60; b.r += dt * 3; }
      for (let i = bubbles.length - 1; i >= 0; i--) if (bubbles[i].y < py + ph * 0.3) bubbles.splice(i, 1);
      ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = 1.5;
      for (const b of bubbles) { ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2); ctx.stroke(); }
      ctx.fillStyle = "rgba(42,120,214,.5)";
      const nVap = Math.round(Math.min(1.5, ratio) * 20);
      for (let i = 0; i < nVap; i++) { const vx = px + ((i * 53 + t * 20) % pw), vy = py + ph * 0.3 - ((i * 37 + t * 30) % (ph * 0.3 + 40)); ctx.beginPath(); ctx.arc(vx, vy, 2.5, 0, Math.PI * 2); ctx.fill(); }
      label(ctx, boiling ? "BOILING" : "not boiling", px + pw / 2, py - 24, { align: "center", font: "bold 16px system-ui", color: boiling ? "#eb6834" : "#4b5868" });
      // Thermometer
      const tx = px + pw + 90, top = py - 30, bot = py + ph + 20;
      const TY = (k) => bot - ((k - 250) / 170) * (bot - top);
      ctx.fillStyle = "#fff"; ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.beginPath(); ctx.roundRect(tx - 9, top - 8, 18, bot - top + 16, 9); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#e34948"; ctx.fillRect(tx - 5, TY(temp.value), 10, bot - TY(temp.value) + 4);
      ctx.strokeStyle = "#1baf7a"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(tx - 16, TY(tb)); ctx.lineTo(tx + 16, TY(tb)); ctx.stroke();
      label(ctx, `boils at ${fmt(tb - 273.15, 3)} °C`, tx + 22, TY(tb), { font: "12px system-ui", color: "#1baf7a", halo: "#f7f9fc" });
      label(ctx, `${fmt(temp.value - 273.15, 3)} °C`, tx + 22, TY(temp.value) + (Math.abs(TY(temp.value) - TY(tb)) < 16 ? 16 : 0), { font: "bold 12px system-ui", color: "#e34948", halo: "#f7f9fc" });
      label(ctx, `air pressure ${fmt(pres.value, 4)} kPa`, px + pw / 2, py - 50, { align: "center", font: "12px system-ui", color: "#4b5868" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
