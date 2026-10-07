// Spin & Rabi Oscillations: physics.rabi_oscillation evolves a driven two-level system; the page draws the Bloch sphere
// and moves the state vector along the engine's path.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, arrow } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => {} });
    const [c1, c2] = SERIES();
    let res = null, raf = 0, alive = true, start = performance.now();

    const om = slider({ label: "Drive strength (Rabi frequency)", min: 0.1, max: 5, step: 0.05, value: 1, unit: "MHz", onInput: () => run() });
    const de = slider({ label: "Detuning", min: -5, max: 5, step: 0.05, value: 0, unit: "MHz", onInput: () => run() });
    const du = slider({ label: "Time shown", min: 0.5, max: 10, step: 0.1, value: 3, unit: "µs", onInput: () => run() });
    const out = readouts([{ key: "pi", label: "π pulse length" }, { key: "T", label: "Rabi period" }, { key: "max", label: "Most excitation" }, { key: "p", label: "Excited now" }]);
    L.side.append(panel("Qubit drive", om.root, de.root, du.root,
      el("p", { class: "note" }, "A spin or a qubit driven by a field. On resonance it flips completely; off resonance it only partly flips, faster. This is how quantum computers make their gates.")),
      panel("Result (from the engine)", out.root));
    const graph = new LineGraph(L.bottom, { title: "Probability of the excited state", xLabel: "time (µs)", height: 130, includeZero: true });

    const run = liveRequest((s) => simulate("physics", "rabi_oscillation", { rabi_mhz: om.value, detuning_mhz: de.value, duration_us: du.value, points: 400 }, s), {
      onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result; start = performance.now();
        out.set("pi", `${fmt(res.pi_pulse_us, 3)} µs`); out.set("T", `${fmt(res.rabi_period_us, 3)} µs`); out.set("max", fmt(res.max_excitation, 3));
        graph.setSeries([{ name: "P(excited)", color: c2, x: res.t_us, y: res.excited_probability }]);
      },
    });

    function draw(now) {
      if (!alive) return;
      raf = requestAnimationFrame(draw);
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const R = Math.min(w, h) * 0.36, cx = w / 2, cy = h / 2 + 6;
      const az = 0.6 + (now / 1000) * 0.15, elev = 0.35;
      const P = ([x, y, z]) => { const xr = x * Math.cos(az) - y * Math.sin(az), yr = x * Math.sin(az) + y * Math.cos(az); return [cx + R * xr, cy - R * (z * Math.cos(elev) - yr * Math.sin(elev)), yr]; };
      ctx.strokeStyle = "rgba(201,206,214,.35)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
      for (const ring of [(t) => [Math.cos(t), Math.sin(t), 0], (t) => [Math.cos(t), 0, Math.sin(t)]]) {
        ctx.beginPath(); for (let k = 0; k <= 64; k++) { const [px, py] = P(ring((k / 64) * Math.PI * 2)); if (k) ctx.lineTo(px, py); else ctx.moveTo(px, py); } ctx.stroke();
      }
      const axes = [[[0, 0, 1], "|g⟩ ground"], [[0, 0, -1], "|e⟩ excited"], [[1, 0, 0], "x"], [[0, 1, 0], "y"]];
      axes.forEach(([v, name]) => { const [px, py] = P(v); const [ox, oy] = P([0, 0, 0]); ctx.strokeStyle = "rgba(201,206,214,.25)"; ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(px, py); ctx.stroke(); label(ctx, name, px + 6, py, { color: "#c9ced6", font: "12px system-ui" }); });
      const n = res.bloch.length, i = Math.floor((((Math.max(0, now - start)) / 6000) % 1) * (n - 1)); // the frame clock can run a moment behind the result
      ctx.strokeStyle = "rgba(235,104,52,.75)"; ctx.lineWidth = 2; ctx.beginPath();
      for (let k = 0; k <= i; k++) { const [px, py] = P(res.bloch[k]); if (k) ctx.lineTo(px, py); else ctx.moveTo(px, py); }
      ctx.stroke();
      const [ox, oy] = P([0, 0, 0]), [tx, ty] = P(res.bloch[i]);
      arrow(ctx, ox, oy, tx, ty, c1, 3, 12);
      out.set("p", fmt(res.excited_probability[i], 3));
      graph.setCursor(res.t_us[i]);
      label(ctx, `t = ${fmt(res.t_us[i], 3)} µs`, 16, 18, { color: "#e8ecf3", font: "600 13px system-ui" });
    }

    run();
    raf = requestAnimationFrame(draw);
    return () => { alive = false; cancelAnimationFrame(raf); run.cancel(); graph.destroy(); stage.destroy(); };
  },
};
