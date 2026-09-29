// Taylor Series Explorer: mathematics.taylor_approximation builds the polynomial and samples it.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, textInput, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { axes, curve, robustRange } from "./plotkit.js";

const EXAMPLES = ["sin(x)", "cos(x)", "exp(x)", "ln(1 + x)", "1/(1 - x)", "atan(x)", "sqrt(1 + x)"];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, drag = false, map = null;

    const f = textInput({ label: "f(x) =", value: "sin(x)", mono: true, onChange: () => recompute() });
    const ex = select({ label: "Examples", value: "sin(x)", options: EXAMPLES.map((e) => ({ value: e, label: e })), onChange: (v) => { f.set(v); recompute(); } });
    const order = slider({ label: "Order n", min: 0, max: 25, step: 1, value: 3, onInput: () => recompute() });
    const centre = slider({ label: "Centre c", min: -4, max: 4, step: 0.25, value: 0, onInput: () => recompute() });
    const out = readouts([{ key: "max", label: "Max error on view" }]);
    const polyBox = el("code", { style: "display:block;white-space:pre-wrap;word-break:break-word;font-size:12px" });
    L.side.append(
      panel("Function", f.root, ex.root, order.root, centre.root, el("p", { class: "note" }, "Drag the green centre point along the axis. Try ln(1 + x) and 1/(1 − x): beyond |x − c| = 1 no order helps (radius of convergence).")),
      panel("Taylor polynomial (from the engine)", polyBox, out.root),
    );
    L.scene.append(el("div", { style: "position:absolute;right:14px;top:12px;background:rgba(255,255,255,.9);padding:4px 8px;border-radius:8px" },
      legend([{ label: "f(x)", color: c1 }, { label: "Pₙ(x)", color: c2, dash: true }])));

    const recompute = liveRequest((signal) => simulate("mathematics", "taylor_approximation", {
      expression: f.value.trim(), order: order.value, centre: centre.value, start: -6, stop: 6, n_points: 600,
    }, signal), {
      delay: 80, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => { L.clearError(); res = r; polyBox.textContent = `P${order.value}(x) = ${r.result.polynomial}`; out.set("max", fmt(r.result.max_error, 4)); draw(); },
    });

    stage.canvas.addEventListener("pointerdown", (e) => { drag = true; stage.canvas.setPointerCapture(e.pointerId); move(e); });
    stage.canvas.addEventListener("pointermove", (e) => { if (drag) move(e); });
    stage.canvas.addEventListener("pointerup", () => { drag = false; });
    function move(e) {
      if (!map) return;
      const r = stage.canvas.getBoundingClientRect();
      centre.set(Math.max(-4, Math.min(4, Math.round(map.inv(e.clientX - r.left, 0)[0] * 4) / 4))); recompute();
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const yr = res ? robustRange(res.curve.function) : [-2, 2];
      map = axes(ctx, w, h, [-6, 6], yr);
      if (!res) return;
      const span = yr[1] - yr[0];
      curve(ctx, map, res.curve.x, res.curve.function, c1, { jump: span * 3 });
      curve(ctx, map, res.curve.x, res.curve.polynomial.map((y) => (y !== null && Math.abs(y) < span * 20 ? y : null)), c2, { dash: true, jump: span * 3 });
      ctx.fillStyle = "#1baf7a"; ctx.beginPath(); ctx.arc(map.X(centre.value), map.Y(0), 7, 0, Math.PI * 2); ctx.fill();
      label(ctx, `c = ${centre.value}`, map.X(centre.value) + 10, map.Y(0) + 16, { font: "bold 12px system-ui", color: "#15845d", halo: "#fff" });
      label(ctx, `order ${order.value}`, 14, 20, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
