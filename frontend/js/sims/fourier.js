// Fourier Series: mathematics.fourier_series computes the coefficients and the partial sums.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, textInput, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label, niceStep } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const FUNCS = { square: "Square wave", sawtooth: "Sawtooth", triangle: "Triangle wave", custom: "Your own f(x)" };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null;

    const func = select({ label: "Function", value: "square", options: Object.entries(FUNCS).map(([v, l]) => ({ value: v, label: l })), onChange: () => { sync(); recompute(); } });
    const expr = textInput({ label: "f(x) on [−π, π]", value: "abs(x)", mono: true, onChange: () => recompute() });
    const terms = slider({ label: "Number of harmonics", min: 0, max: 60, step: 1, value: 5, onInput: () => recompute() });
    const out = readouts([{ key: "a0", label: "a₀ / 2 (average)" }, { key: "rms", label: "RMS error" }, { key: "peak", label: "Peak of partial sum" }]);
    function sync() { expr.root.style.display = func.value === "custom" ? "" : "none"; }
    L.side.append(
      panel("Signal", func.root, expr.root, terms.root, el("p", { class: "note" }, "Add harmonics and watch the sum converge. Near a jump the overshoot never goes away (Gibbs phenomenon, about 9%).")),
      panel("Series (from the engine)", out.root),
    );
    sync();
    L.scene.append(el("div", { style: "position:absolute;right:14px;top:12px;background:rgba(255,255,255,.9);padding:4px 8px;border-radius:8px" },
      legend([{ label: "f(x)", color: c2, dash: true }, { label: "partial sum", color: c1 }])));
    const spectrum = new LineGraph(L.bottom, { title: "Harmonic amplitudes √(aₙ² + bₙ²)", xLabel: "harmonic n", yLabel: "amplitude", height: 150, includeZero: true,
      xFormat: (v) => (Number.isInteger(Math.round(v * 1000) / 1000) ? String(Math.round(v)) : "") });

    const recompute = liveRequest((signal) => simulate("mathematics", "fourier_series", {
      function: func.value === "custom" ? expr.value.trim() : func.value, half_period: Math.PI, n_terms: terms.value, n_points: 1601,
    }, signal), {
      delay: 60, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("a0", fmt(x.a0 / 2, 4)); out.set("rms", fmt(x.rms_error, 4)); out.set("peak", `${fmt(x.max_partial_sum, 4)} (function max ${fmt(x.max_function, 3)})`);
        const n = x.a.map((_, i) => i + 1);
        spectrum.opts.xRange = [0.5, Math.max(1, n.length) + 0.5];
        spectrum.setSeries([{ name: "Amplitude", color: c1, x: n, y: x.a.map((a, i) => Math.hypot(a, x.b[i])), bars: true, alpha: 0.8 }]);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const xs = res.curve.x, f = res.curve.function, s = res.curve.partial_sum;
      const lo = Math.min(...f, ...s), hi = Math.max(...f, ...s), pad = (hi - lo || 1) * 0.12;
      const X = (v) => 40 + ((v - xs[0]) / (xs[xs.length - 1] - xs[0])) * (w - 60);
      const Y = (v) => h - 30 - ((v - (lo - pad)) / (hi - lo + 2 * pad)) * (h - 60);
      ctx.strokeStyle = "#e3e8ef"; ctx.lineWidth = 1;
      for (let k = -2; k <= 2; k++) { const x = X(k * Math.PI); ctx.beginPath(); ctx.moveTo(x, 10); ctx.lineTo(x, h - 30); ctx.stroke(); label(ctx, k === 0 ? "0" : `${k === 1 ? "" : k === -1 ? "−" : k}π`, x, h - 14, { align: "center", font: "11px system-ui", color: "#4b5868" }); }
      const ys = niceStep(hi - lo + 2 * pad, 5);
      for (let v = Math.ceil((lo - pad) / ys) * ys; v <= hi + pad; v += ys) { ctx.beginPath(); ctx.moveTo(40, Y(v)); ctx.lineTo(w - 20, Y(v)); ctx.stroke(); label(ctx, fmt(v, 2), 34, Y(v), { align: "right", font: "11px system-ui", color: "#4b5868" }); }
      ctx.strokeStyle = "#7b8796"; ctx.beginPath(); ctx.moveTo(40, Y(0)); ctx.lineTo(w - 20, Y(0)); ctx.stroke();
      const line = (arr, color, width, dash) => {
        ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash ? [6, 5] : []); ctx.beginPath();
        arr.forEach((v, i) => (i ? ctx.lineTo(X(xs[i]), Y(v)) : ctx.moveTo(X(xs[i]), Y(v)))); ctx.stroke(); ctx.setLineDash([]);
      };
      line(f, c2, 2, true);
      line(s, c1, 2.5, false);
      label(ctx, `${terms.value} harmonic${terms.value === 1 ? "" : "s"}`, 48, 22, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); spectrum.destroy(); stage.destroy(); };
  },
};
