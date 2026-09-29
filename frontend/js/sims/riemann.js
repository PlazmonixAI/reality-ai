// Riemann Sums: mathematics.riemann_sum computes the approximation and the shapes to draw.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, segmented, textInput, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";
import { axes, curve, robustRange } from "./plotkit.js";

const EXAMPLES = ["x^2", "sin(x) + 1.5", "exp(-x^2)", "sqrt(x)", "1/x", "x^3 - 3x + 3"];
const METHODS = ["left", "right", "midpoint", "trapezoid", "simpson"];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null;

    const f = textInput({ label: "f(x) =", value: "x^2", mono: true, onChange: () => recompute() });
    const ex = select({ label: "Examples", value: "x^2", options: EXAMPLES.map((e) => ({ value: e, label: e })), onChange: (v) => { f.set(v); recompute(); } });
    const a = slider({ label: "a", min: -5, max: 5, step: 0.1, value: 0, onInput: () => recompute() });
    const b = slider({ label: "b", min: -5, max: 5, step: 0.1, value: 2, onInput: () => recompute() });
    const n = slider({ label: "Subintervals n", min: 2, max: 100, step: 2, value: 8, onInput: () => recompute() });
    const method = segmented({ label: "Rule", value: "midpoint", options: METHODS.map((m) => ({ value: m, label: m[0].toUpperCase() + m.slice(1) })), onChange: () => recompute() });
    const out = readouts([{ key: "s", label: "Approximation" }, { key: "i", label: "Integral" }, { key: "e", label: "Error" }]);
    L.side.append(panel("Integral", f.root, ex.root, a.root, b.root, n.root, method.root), panel("Result (from the engine)", out.root));
    const graph = new LineGraph(L.bottom, { title: "How fast each rule converges", xLabel: "log₁₀ n", yLabel: "log₁₀ |error|", height: 150 });

    const recompute = liveRequest(async (signal) => {
      const lo = Math.min(a.value, b.value), hi = Math.max(a.value, b.value) + (a.value === b.value ? 0.1 : 0);
      const e = f.value.trim();
      const main = await simulate("mathematics", "riemann_sum", { expression: e, a: lo, b: hi, n: n.value, method: method.value }, signal);
      const ns = [2, 4, 8, 16, 32, 64, 128, 256];
      const conv = await Promise.all(["left", "midpoint", "simpson"].map((m) =>
        Promise.all(ns.map((k) => simulate("mathematics", "riemann_sum", { expression: e, a: lo, b: hi, n: k, method: m }, signal)))));
      return { main, ns, conv };
    }, {
      delay: 100, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ main, ns, conv }) => {
        L.clearError(); res = main;
        out.set("s", fmt(main.result.approximation, 6)); out.set("i", fmt(main.result.integral, 6)); out.set("e", fmt(main.result.error, 3));
        const lx = ns.map(Math.log10);
        const ly = (rs) => rs.map((r) => (Math.abs(r.result.error) > 1e-15 ? Math.log10(Math.abs(r.result.error)) : null));
        graph.setSeries([
          { name: "Left", color: c1, x: lx, y: ly(conv[0]) },
          { name: "Midpoint", color: c2, x: lx, y: ly(conv[1]), dash: true },
          { name: "Simpson", color: c3, x: lx, y: ly(conv[2]) },
        ]);
        graph.setCursor(Math.log10(n.value));
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const x0 = res ? res.curve.x[0] : -1, x1 = res ? res.curve.x[res.curve.x.length - 1] : 3;
      const m = axes(ctx, w, h, [x0, x1], res ? robustRange(res.curve.y) : [-1, 5]);
      if (!res) return;
      for (const s of res.shapes) {
        const pos = (s.y0 + s.y1) / 2 >= 0;
        ctx.fillStyle = pos ? "rgba(42,120,214,.22)" : "rgba(227,73,72,.22)"; ctx.strokeStyle = pos ? "rgba(42,120,214,.8)" : "rgba(227,73,72,.8)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(m.X(s.x0), m.Y(0)); ctx.lineTo(m.X(s.x0), m.Y(s.y0)); ctx.lineTo(m.X(s.x1), m.Y(s.y1)); ctx.lineTo(m.X(s.x1), m.Y(0)); ctx.closePath(); ctx.fill(); ctx.stroke();
        if (s.sample_x !== undefined) { ctx.fillStyle = "#eb6834"; ctx.beginPath(); ctx.arc(m.X(s.sample_x), m.Y(s.y0), 3, 0, Math.PI * 2); ctx.fill(); }
      }
      curve(ctx, m, res.curve.x, res.curve.y, "#16202c", { width: 2.5 });
      label(ctx, `${method.value} rule, n = ${n.value}: ${fmt(res.result.approximation, 6)}`, 14, 20, { font: "bold 13px system-ui" });
      if (method.value === "simpson") label(ctx, "Simpson fits a parabola through each pair of strips (outline shows the strips)", 14, 38, { font: "11px system-ui", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
