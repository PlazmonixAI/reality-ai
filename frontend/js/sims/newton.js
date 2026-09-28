// Newton's Method: mathematics.newton_method gives every iterate and its tangent line.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, textInput, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { axes, curve, robustRange } from "./plotkit.js";

const EXAMPLES = ["x^2 - 2", "cos(x) - x", "x^3 - 2*x + 2", "(x - 1)^2", "atan(x)", "x^3 - x"];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null, fcurve = null, shown = 1, drag = false, map = null;

    const f = textInput({ label: "f(x) =", value: "x^2 - 2", mono: true, onChange: () => recompute() });
    const ex = select({ label: "Examples", value: "x^2 - 2", options: EXAMPLES.map((e) => ({ value: e, label: e })), onChange: (v) => { f.set(v); recompute(); } });
    const x0 = slider({ label: "Starting guess x₀", min: -4, max: 4, step: 0.05, value: 1, onInput: () => recompute() });
    const stepBtn = button("Next step", () => { if (res) { shown = Math.min(res.steps.length, shown + 1); list(); draw(); } }, "primary");
    const allBtn = button("Show all", () => { if (res) { shown = res.steps.length; list(); draw(); } });
    const out = readouts([{ key: "status", label: "Status" }, { key: "root", label: "Root" }, { key: "it", label: "Iterations" }, { key: "ord", label: "Observed order" }]);
    const table = el("div", { style: "font:12px ui-monospace,monospace;max-height:220px;overflow:auto" });
    L.side.append(
      panel("Function", f.root, ex.root, x0.root, el("div", { class: "btn-row" }, stepBtn, allBtn),
        el("p", { class: "note" }, "Drag the starting point on the x-axis. Try x³ − 2x + 2 from 0 (it cycles) and atan(x) from 1.5 (it diverges).")),
      panel("Iteration (from the engine)", out.root, table),
    );

    const recompute = liveRequest(async (signal) => {
      const e = f.value.trim();
      const [r, c] = await Promise.all([
        simulate("mathematics", "newton_method", { expression: e, x0: x0.value }, signal),
        simulate("mathematics", "evaluate_function", { expression: e, start: -5, stop: 5, n_points: 500 }, signal),
      ]);
      return { r, c };
    }, {
      delay: 60, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ r, c }) => {
        L.clearError(); res = r; fcurve = c.result; shown = 1;
        const x = r.result;
        out.set("status", x.status); out.set("root", x.root === null ? "—" : fmt(x.root, 12));
        out.set("it", String(x.iterations)); out.set("ord", x.convergence_order === null ? "—" : fmt(x.convergence_order, 3));
        list(); draw();
      },
    });
    function list() {
      table.replaceChildren(...res.steps.slice(0, shown).map((s, i) => el("div", {}, `x${i} = ${s.x.toPrecision(12)}`)));
    }

    stage.canvas.addEventListener("pointerdown", (e) => { drag = true; stage.canvas.setPointerCapture(e.pointerId); move(e); });
    stage.canvas.addEventListener("pointermove", (e) => { if (drag) move(e); });
    stage.canvas.addEventListener("pointerup", () => { drag = false; });
    function move(e) { if (!map) return; const r = stage.canvas.getBoundingClientRect(); x0.set(Math.max(-4, Math.min(4, Math.round(map.inv(e.clientX - r.left, 0)[0] * 20) / 20))); recompute(); }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const yr = fcurve ? robustRange(fcurve.y) : [-3, 3];
      map = axes(ctx, w, h, [-5, 5], yr);
      if (!fcurve) return;
      curve(ctx, map, fcurve.x, fcurve.y, c1, { jump: (yr[1] - yr[0]) * 3 });
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, h); ctx.clip();
      res.steps.slice(0, shown).forEach((s, i) => {
        const fade = 0.35 + 0.65 * ((i + 1) / shown);
        ctx.strokeStyle = `rgba(235,104,52,${fade})`; ctx.lineWidth = 1.8;
        const xa = s.x - 3, xb = s.x + 3;
        ctx.beginPath(); ctx.moveTo(map.X(xa), map.Y(s.f + s.slope * (xa - s.x))); ctx.lineTo(map.X(xb), map.Y(s.f + s.slope * (xb - s.x))); ctx.stroke();
        ctx.setLineDash([3, 3]); ctx.strokeStyle = "#9aa6b5"; ctx.beginPath(); ctx.moveTo(map.X(s.x), map.Y(0)); ctx.lineTo(map.X(s.x), map.Y(s.f)); ctx.stroke(); ctx.setLineDash([]);
        ctx.fillStyle = c2; ctx.beginPath(); ctx.arc(map.X(s.x), map.Y(s.f), 4.5, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(map.X(s.x), map.Y(0), 4, 0, Math.PI * 2); ctx.fill();
        if (i < 6) label(ctx, `x${i}`, map.X(s.x), map.Y(0) + (i % 2 ? 26 : 16), { align: "center", font: "11px system-ui", halo: "#fff" });
      });
      ctx.restore();
      if (res.result.root !== null) { ctx.fillStyle = c3; ctx.beginPath(); ctx.arc(map.X(res.result.root), map.Y(0), 7, 0, Math.PI * 2); ctx.fill(); }
      label(ctx, `step ${shown} of ${res.steps.length}`, 14, 20, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
