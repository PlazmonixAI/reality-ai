// Vector Addition & Products: mathematics.vector_operations computes sum, dot, cross, angle and projection.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, checkbox, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, View, label, arrow } from "../core/stage.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let a = [4, 1], b = [1, 3], res = null, drag = null;

    const showSum = checkbox({ label: "Show a + b (parallelogram)", value: true, onChange: () => draw() });
    const showDiff = checkbox({ label: "Show a − b", value: false, onChange: () => draw() });
    const showProj = checkbox({ label: "Show projection of a onto b", value: false, onChange: () => draw() });
    const out = readouts([
      { key: "a", label: "a" }, { key: "b", label: "b" }, { key: "sum", label: "a + b" }, { key: "ma", label: "|a|, |b|" },
      { key: "dot", label: "a · b" }, { key: "cross", label: "a × b (z)" }, { key: "ang", label: "Angle between" },
    ]);
    L.side.append(
      panel("Show", showSum.root, showDiff.root, showProj.root, legend([{ label: "a", color: c1 }, { label: "b", color: c2 }, { label: "a + b", color: c3 }]),
        el("p", { class: "note" }, "Drag the arrow tips. Tips snap to the grid.")),
      panel("Results (from the engine)", out.root, el("p", { class: "note" }, "|a × b| is the area of the parallelogram; a · b = |a||b| cos θ.")),
    );

    const recompute = liveRequest((signal) => simulate("mathematics", "vector_operations", { a, b }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        const v = (p) => `(${fmt(p[0], 3)}, ${fmt(p[1], 3)})`;
        out.set("a", v(a)); out.set("b", v(b)); out.set("sum", v(res.sum));
        out.set("ma", `${fmt(res.magnitude_a, 4)}, ${fmt(res.magnitude_b, 4)}`);
        out.set("dot", fmt(res.dot, 4)); out.set("cross", fmt(res.cross[2], 4));
        out.set("ang", res.angle_deg === null ? "–" : `${fmt(res.angle_deg, 4)}°`);
        draw();
      },
    });

    const world = (e) => { const r = stage.canvas.getBoundingClientRect(); return view.toWorld(e.clientX - r.left, e.clientY - r.top); };
    stage.canvas.addEventListener("pointerdown", (e) => {
      const [x, y] = world(e);
      drag = Math.hypot(x - a[0], y - a[1]) < 0.6 ? "a" : Math.hypot(x - b[0], y - b[1]) < 0.6 ? "b" : null;
      if (drag) stage.canvas.setPointerCapture(e.pointerId);
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const [x, y] = world(e), p = [Math.round(x * 2) / 2, Math.round(y * 2) / 2];
      if (drag === "a") a = p; else b = p;
      recompute(); draw();
    });
    stage.canvas.addEventListener("pointerup", () => { drag = null; });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      view.fit(-8, 8, -6, 6, w, h, { pad: 0.02 });
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      for (let x = -12; x <= 12; x++) { ctx.strokeStyle = x === 0 ? "#7b8796" : "#eef1f5"; ctx.lineWidth = x === 0 ? 1.5 : 1; ctx.beginPath(); ctx.moveTo(view.x(x), 0); ctx.lineTo(view.x(x), h); ctx.stroke(); }
      for (let y = -9; y <= 9; y++) { ctx.strokeStyle = y === 0 ? "#7b8796" : "#eef1f5"; ctx.lineWidth = y === 0 ? 1.5 : 1; ctx.beginPath(); ctx.moveTo(0, view.y(y)); ctx.lineTo(w, view.y(y)); ctx.stroke(); }
      const O = [view.x(0), view.y(0)], P = (p) => [view.x(p[0]), view.y(p[1])];
      if (res && showSum.value) {
        ctx.fillStyle = "rgba(27,175,122,.1)"; ctx.beginPath(); ctx.moveTo(...O); ctx.lineTo(...P(a)); ctx.lineTo(...P(res.sum)); ctx.lineTo(...P(b)); ctx.closePath(); ctx.fill();
        ctx.setLineDash([5, 4]); ctx.strokeStyle = "rgba(75,88,104,.6)"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(...P(a)); ctx.lineTo(...P(res.sum)); ctx.lineTo(...P(b)); ctx.stroke(); ctx.setLineDash([]);
        arrow(ctx, ...O, ...P(res.sum), c3, 3, 12);
        label(ctx, "a + b", ...P(res.sum).map((v, i) => v + (i ? -12 : 8)), { font: "bold 13px system-ui", color: c3, halo: "#fff" });
      }
      if (res && showDiff.value) {
        ctx.setLineDash([7, 5]); arrow(ctx, ...P(b), ...P(a), "#4a3aa7", 2.5, 11); ctx.setLineDash([]);
        label(ctx, "a − b", (P(a)[0] + P(b)[0]) / 2 + 8, (P(a)[1] + P(b)[1]) / 2, { font: "bold 12px system-ui", color: "#4a3aa7", halo: "#fff" });
      }
      if (res && showProj.value) {
        const pr = res.projection_a_on_b;
        ctx.setLineDash([3, 3]); ctx.strokeStyle = "#7b8796"; ctx.beginPath(); ctx.moveTo(...P(a)); ctx.lineTo(...P(pr)); ctx.stroke(); ctx.setLineDash([]);
        arrow(ctx, ...O, ...P(pr), "#eda100", 4, 10);
        label(ctx, `proj = ${fmt(res.scalar_projection, 3)}`, P(pr)[0] + 8, P(pr)[1] + 14, { font: "bold 12px system-ui", color: "#b77c00", halo: "#fff" });
      }
      arrow(ctx, ...O, ...P(a), c1, 3.5, 12); arrow(ctx, ...O, ...P(b), c2, 3.5, 12);
      for (const [v, name, col] of [[a, "a", c1], [b, "b", c2]]) {
        const [X, Y] = P(v);
        ctx.fillStyle = "rgba(22,32,44,.12)"; ctx.beginPath(); ctx.arc(X, Y, 11, 0, Math.PI * 2); ctx.fill();
        label(ctx, name, X + 12, Y - 12, { font: "bold 15px system-ui", color: col, halo: "#fff" });
      }
      if (res && res.angle_deg !== null) label(ctx, `θ = ${fmt(res.angle_deg, 3)}°`, 14, 20, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
