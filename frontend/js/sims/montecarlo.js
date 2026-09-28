// Monte Carlo: mathematics.monte_carlo estimates π or an integral from random samples, with its 1/√N error.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, textInput, readouts, el, button, legend, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, seed = 1;

    const method = segmented({ label: "Estimate", value: "pi", options: [{ value: "pi", label: "π with darts" }, { value: "integral", label: "An integral" }], onChange: () => { sync(); recompute(); } });
    const n = slider({ label: "Number of samples N", min: 10, max: 1e6, value: 2000, log: true, format: (v) => fmt(Math.round(v), 4), onInput: () => recompute() });
    const expr = textInput({ label: "f(x) =", value: "exp(-x**2)", mono: true, onChange: () => recompute() });
    const a = slider({ label: "from a", min: -5, max: 5, step: 0.1, value: 0, onInput: () => recompute() });
    const b = slider({ label: "to b", min: -5, max: 5, step: 0.1, value: 2, onInput: () => recompute() });
    const out = readouts([{ key: "est", label: "Estimate" }, { key: "se", label: "Standard error" }, { key: "ex", label: "Exact" }, { key: "err", label: "Actual error" }]);
    function sync() { const i = method.value === "integral"; expr.root.style.display = a.root.style.display = b.root.style.display = i ? "" : "none"; }
    L.side.append(
      panel("Experiment", method.root, n.root, expr.root, a.root, b.root, button("Throw again (new seed)", () => { seed += 1; recompute(); }),
        legend([{ label: "hit", color: c1 }, { label: "miss", color: c2 }])),
      panel("Result (from the engine)", out.root, el("p", { class: "note" }, "Random sampling converges slowly: 100× more samples buys only one more correct digit.")),
    );
    sync();
    const graph = new LineGraph(L.bottom, { title: "Error shrinks like 1/√N", xLabel: "log₁₀ N", yLabel: "log₁₀ |error|", height: 150 });

    const recompute = liveRequest((signal) => simulate("mathematics", "monte_carlo", {
      method: method.value, n_samples: Math.round(n.value), expression: expr.value, a: a.value, b: b.value, seed, n_plot: 3000,
    }, signal), {
      delay: 60, onBusy: L.busy, onError: (e) => { res = null; L.error(e.message); draw(); },
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("est", fmt(x.estimate, 6)); out.set("se", `± ${fmt(x.standard_error, 3)}`); out.set("ex", fmt(x.exact, 6));
        out.set("err", `${fmt(x.error, 3)} (${fmt(x.error_in_standard_errors, 2)} SE)`);
        const cv = r.convergence, keep = cv.abs_error.map((e, i) => (e > 0 ? i : -1)).filter((i) => i >= 0);
        graph.setSeries([
          { name: "actual error", color: c1, x: keep.map((i) => Math.log10(cv.n[i])), y: keep.map((i) => Math.log10(cv.abs_error[i])) },
          { name: "expected σ/√N", color: c2, dash: true, x: cv.n.map(Math.log10), y: cv.expected_error.map(Math.log10) },
        ]);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const s = res.samples, size = Math.min(w - 60, h - 60), ox = (w - size) / 2, oy = (h - size) / 2;
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.strokeRect(ox, oy, size, size);
      let X, Y;
      if (method.value === "pi") {
        X = (x) => ox + x * size; Y = (y) => oy + size - y * size;
        ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(ox, oy + size, size, -Math.PI / 2, 0); ctx.stroke();
      } else {
        const cy = s.curve_y, lo = Math.min(0, ...cy), hi = Math.max(0, ...cy), x0 = a.value, x1 = b.value;
        X = (x) => ox + ((x - x0) / (x1 - x0)) * size; Y = (y) => oy + size - ((y - lo) / (hi - lo || 1)) * size;
        ctx.strokeStyle = "#9aa6b5"; ctx.beginPath(); ctx.moveTo(ox, Y(0)); ctx.lineTo(ox + size, Y(0)); ctx.stroke();
      }
      const r = s.x.length > 1500 ? 1.8 : 2.8;
      s.x.forEach((x, i) => { ctx.fillStyle = s.hit[i] ? c1 : c2; ctx.globalAlpha = 0.75; ctx.beginPath(); ctx.arc(X(x), Y(s.y[i]), r, 0, Math.PI * 2); ctx.fill(); });
      ctx.globalAlpha = 1;
      if (method.value === "integral") { ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2.5; ctx.beginPath(); s.curve_x.forEach((x, i) => (i ? ctx.lineTo(X(x), Y(s.curve_y[i])) : ctx.moveTo(X(x), Y(s.curve_y[i])))); ctx.stroke(); }
      label(ctx, `showing ${s.x.length} of ${fmt(res.result.n_samples, 4)} samples`, w - 10, h - 10, { align: "right", font: "11px system-ui", color: "#7b8796" });
      label(ctx, method.value === "pi" ? `π ≈ 4 × ${fmt(res.result.inside, 6)} / ${fmt(res.result.n_samples, 6)}` : `∫ ≈ (b − a) × mean f(x)`, ox, oy - 12, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
