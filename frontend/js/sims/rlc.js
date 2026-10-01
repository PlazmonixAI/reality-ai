// RC / RL / RLC Circuits: rlc_circuit gives the transient; rlc_frequency_response the resonance curve.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, SERIES } from "../core/ui.js";
import { createStage, sampleAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let data = null, simTime = 0, dotPhase = 0, lastT = 0;

    const kind = segmented({ label: "Circuit", value: "rlc", options: [{ value: "rc", label: "RC" }, { value: "rl", label: "RL" }, { value: "rlc", label: "RLC" }], onChange: () => { sync(); recompute(); } });
    const source = segmented({ label: "Source", value: "dc", options: [{ value: "dc", label: "DC (switch on)" }, { value: "ac", label: "AC" }], onChange: () => { sync(); recompute(); } });
    const R = slider({ label: "Resistance R", min: 1, max: 10000, value: 20, log: true, unit: "Ω", onInput: () => recompute() });
    const Lh = slider({ label: "Inductance L", min: 0.001, max: 10, value: 0.1, log: true, format: (v) => (v < 1 ? `${fmt(v * 1000, 3)} mH` : `${fmt(v, 3)} H`), onInput: () => recompute() });
    const C = slider({ label: "Capacitance C", min: 1e-7, max: 1e-2, value: 1e-4, log: true, format: (v) => (v < 1e-3 ? `${fmt(v * 1e6, 3)} µF` : `${fmt(v * 1000, 3)} mF`), onInput: () => recompute() });
    const V = slider({ label: "Source voltage (peak for AC)", min: 1, max: 24, step: 0.5, value: 9, unit: "V", onInput: () => recompute() });
    const f = slider({ label: "AC frequency", min: 1, max: 5000, value: 50, log: true, unit: "Hz", onInput: () => recompute() });
    const out = readouts([{ key: "tau", label: "Time constant" }, { key: "f0", label: "Resonant frequency" }, { key: "q", label: "Quality factor Q" }, { key: "regime", label: "Response" }]);
    function sync() {
      Lh.root.style.display = kind.value === "rc" ? "none" : "";
      C.root.style.display = kind.value === "rl" ? "none" : "";
      f.root.style.display = source.value === "ac" ? "" : "none";
    }
    L.side.append(panel("Circuit", kind.root, source.root, R.root, Lh.root, C.root, V.root, f.root), panel("Behaviour (from the engine)", out.root));
    sync();
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); vGraph.setCursor(t * 1000); iGraph.setCursor(t * 1000); }, { speeds: [0.25, 0.5, 1, 2] });
    const vGraph = new LineGraph(L.bottom, { title: "Voltages", xLabel: "time (ms)", yLabel: "voltage (V)", height: 130 });
    const iGraph = new LineGraph(L.bottom, { title: "Current", xLabel: "time (ms)", yLabel: "current (A)", height: 110 });
    const fGraph = new LineGraph(L.side, { title: "AC current vs frequency", xLabel: "log₁₀ f (Hz)", yLabel: "current (A)", height: 150, includeZero: true });
    fGraph.root.style.display = "none";

    // Plot window: several of the circuit's natural time scales (only chooses what to show).
    function plotWindow() {
      const r = R.value, l = kind.value === "rc" ? 0 : Lh.value, c = kind.value === "rl" ? null : C.value;
      const scales = [];
      if (c && !l) scales.push(5 * r * c);
      if (l && !c) scales.push(5 * l / r);
      if (l && c) scales.push(Math.min(10 * l / r, 40 * Math.PI * Math.sqrt(l * c)), 6 * Math.PI * Math.sqrt(l * c));
      if (source.value === "ac") scales.push(4 / f.value);
      return Math.min(Math.max(...scales, 1e-5), 20);
    }

    const recompute = liveRequest(async (signal) => {
      const args = {
        resistance: R.value, voltage: V.value, duration: plotWindow(), source: source.value, frequency: f.value, n_points: 2001,
        inductance: kind.value === "rc" ? 0 : Lh.value,
      };
      if (kind.value !== "rl") args.capacitance = C.value;
      const tr = simulate("physics", "rlc_circuit", args, signal);
      const fr = kind.value === "rlc" ? simulate("physics", "rlc_frequency_response", { resistance: R.value, inductance: Lh.value, capacitance: C.value, voltage: V.value }, signal) : null;
      return { tr: await tr, fr: fr && await fr };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ tr, fr }) => {
        L.clearError(); data = tr;
        const r = tr.result, T = tr.trajectory, ms = T.t.map((t) => t * 1000);
        out.set("tau", r.time_constant ? fmtTime(r.time_constant) : "–");
        out.set("f0", r.natural_frequency_hz ? `${fmt(r.natural_frequency_hz, 4)} Hz` : "–");
        out.set("q", r.quality_factor ? fmt(r.quality_factor, 3) : "–");
        out.set("regime", r.regime || (kind.value === "rc" ? "exponential charging" : "exponential rise"));
        const series = [{ name: "V across R", color: c1, x: ms, y: T.v_resistor }];
        if (kind.value !== "rc") series.push({ name: "V across L", color: c2, x: ms, y: T.v_inductor, dash: true });
        if (kind.value !== "rl") series.push({ name: "V across C", color: c3, x: ms, y: T.v_capacitor });
        vGraph.setSeries(series);
        iGraph.setSeries([{ name: "Current", color: c1, x: ms, y: T.current }]);
        fGraph.root.style.display = fr && source.value === "ac" ? "" : "none";
        if (fr) {
          fGraph.setSeries([{ name: "Current amplitude", color: c1, x: fr.curve.frequency.map(Math.log10), y: fr.curve.current }]);
          fGraph.setCursor(Math.log10(f.value));
          out.set("f0", `${fmt(fr.result.resonant_frequency_hz, 4)} Hz (bandwidth ${fmt(fr.result.bandwidth_hz, 3)} Hz)`);
        }
        player.load(T.t[T.t.length - 1], 8);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f8fafc"; ctx.fillRect(0, 0, w, h);
      const x0 = w * 0.18, x1 = w * 0.82, y0 = h * 0.22, y1 = h * 0.8;
      ctx.strokeStyle = "#8a6d3b"; ctx.lineWidth = 4; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      const T = data && data.trajectory;
      const i = T ? sampleAt(T.t, T.current, simTime) : 0;
      const imax = T ? Math.max(...T.current.map(Math.abs), 1e-12) : 1;
      // Current dots around the loop
      const per = 2 * ((x1 - x0) + (y1 - y0));
      dotPhase += (i / imax) * 90 * Math.max(0, (performance.now() - lastT) / 1000);
      lastT = performance.now();
      ctx.fillStyle = "rgba(42,120,214,.9)";
      for (let d = ((dotPhase % 22) + 22) % 22; d < per; d += 22) {
        let x, y, s = d;
        if (s < x1 - x0) { x = x0 + s; y = y0; } else if ((s -= x1 - x0) < y1 - y0) { x = x1; y = y0 + s; }
        else if ((s -= y1 - y0) < x1 - x0) { x = x1 - s; y = y1; } else { s -= x1 - x0; x = x0; y = y1 - s; }
        ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
      }
      const box = (cx, cy, wd, ht) => { ctx.fillStyle = "#f8fafc"; ctx.fillRect(cx - wd / 2, cy - ht / 2, wd, ht); };
      // Source (left)
      box(x0, (y0 + y1) / 2, 40, 70);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(x0, (y0 + y1) / 2, 24, 0, Math.PI * 2); ctx.stroke();
      label(ctx, source.value === "dc" ? "⎓" : "∿", x0, (y0 + y1) / 2 + 1, { align: "center", font: "bold 20px system-ui" });
      label(ctx, `${fmt(V.value, 3)} V`, x0 - 34, (y0 + y1) / 2, { align: "right", font: "12px system-ui" });
      const parts = [["R", c1]];
      if (kind.value !== "rc") parts.push(["L", c2]);
      if (kind.value !== "rl") parts.push(["C", c3]);
      parts.forEach(([name, color], k) => {
        const cx = x0 + ((k + 1) / (parts.length + 1)) * (x1 - x0);
        box(cx, y0, 70, 36);
        ctx.strokeStyle = color; ctx.lineWidth = 3;
        if (name === "R") { ctx.beginPath(); for (let j = 0; j <= 8; j++) ctx.lineTo(cx - 32 + j * 8, y0 + (j % 2 ? -9 : 9) * (j === 0 || j === 8 ? 0 : 1)); ctx.stroke(); }
        if (name === "L") { ctx.beginPath(); for (let j = 0; j < 4; j++) ctx.arc(cx - 24 + j * 16, y0, 8, Math.PI, 0); ctx.stroke(); }
        if (name === "C") {
          ctx.beginPath(); ctx.moveTo(cx - 6, y0 - 16); ctx.lineTo(cx - 6, y0 + 16); ctx.moveTo(cx + 6, y0 - 16); ctx.lineTo(cx + 6, y0 + 16); ctx.stroke();
          const vc = T ? sampleAt(T.t, T.v_capacitor, simTime) : 0;
          label(ctx, vc >= 0 ? "+" : "−", cx - 14, y0 - 20, { align: "center", font: "bold 13px system-ui", color: "#e34948" });
        }
        const key = { R: "v_resistor", L: "v_inductor", C: "v_capacitor" }[name];
        const v = T ? sampleAt(T.t, T[key], simTime) : 0;
        label(ctx, `${name}: ${fmt(v, 3)} V`, cx, y0 - 34, { align: "center", font: "bold 12px system-ui", color });
      });
      label(ctx, `I = ${fmt(i, 3)} A`, (x0 + x1) / 2, y1 + 26, { align: "center", font: "bold 14px system-ui" });
      label(ctx, `t = ${fmtTime(simTime)}`, 14, 18, { font: "13px system-ui" });
      label(ctx, "Dots show conventional current; speed relative to the peak", w - 14, h - 14, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    const tick = setInterval(draw, 40);
    recompute();
    return () => { clearInterval(tick); recompute.cancel(); player.destroy(); vGraph.destroy(); iGraph.destroy(); fGraph.destroy(); stage.destroy(); };
  },
};
