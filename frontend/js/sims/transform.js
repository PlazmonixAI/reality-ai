// Linear Transformations: mathematics.linear_transform_2d maps the grid, unit square and eigenvectors.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, arrow, label } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { axes } from "./plotkit.js";

const PRESETS = {
  shear: { label: "Shear", m: [[1, 1], [0, 1]] }, rotate: { label: "Rotation 30°", m: [[0.866, -0.5], [0.5, 0.866]] },
  stretch: { label: "Stretch", m: [[2, 0], [0, 0.5]] }, symmetric: { label: "Symmetric (real eigenvectors)", m: [[2, 1], [1, 2]] },
  reflect: { label: "Reflection in y = x", m: [[0, 1], [1, 0]] }, singular: { label: "Singular (squash to a line)", m: [[1, 2], [0.5, 1]] },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null;
    const preset = select({ label: "Preset", value: "symmetric", options: [...Object.entries(PRESETS).map(([v, p]) => ({ value: v, label: p.label })), { value: "custom", label: "Custom" }], onChange: (v) => {
      if (PRESETS[v]) { const m = PRESETS[v].m; [a, b, c, d].forEach((s, i) => s.set(m[i >> 1][i & 1])); recompute(); }
    } });
    const mk = (lbl, v) => slider({ label: lbl, min: -3, max: 3, step: 0.05, value: v, onInput: () => { preset.set("custom"); recompute(); } });
    const a = mk("a (top left)", 2), b = mk("b (top right)", 1), c = mk("c (bottom left)", 1), d = mk("d (bottom right)", 2);
    const out = readouts([{ key: "det", label: "Determinant (area scale)" }, { key: "tr", label: "Trace" }, { key: "type", label: "Type" }, { key: "eig", label: "Eigenvalues" }]);
    L.side.append(
      panel("Matrix [[a, b], [c, d]]", preset.root, a.root, b.root, c.root, d.root),
      panel("Properties (from the engine)", out.root, legend([{ label: "A·e₁", color: c1 }, { label: "A·e₂", color: c2 }, { label: "eigenvectors", color: c3 }]),
        el("p", { class: "note" }, "Faint grid = before, blue grid = after. Eigenvectors keep their direction; they only stretch.")),
    );

    const recompute = liveRequest((signal) => simulate("mathematics", "linear_transform_2d", { matrix: [[a.value, b.value], [c.value, d.value]], grid: 6 }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("det", fmt(x.determinant, 4)); out.set("tr", fmt(x.trace, 4)); out.set("type", x.type);
        out.set("eig", x.real_eigenvalues ? x.eigen.map((e) => fmt(e.value, 4)).join(", ") : x.eigen.map((e) => `${fmt(e.value[0], 3)} ± ${fmt(Math.abs(e.value[1]), 3)}i`)[0]);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const m = axes(ctx, w, h, [-5, 5], [-4, 4], { equal: true });
      if (!res) return;
      ctx.strokeStyle = "rgba(42,120,214,.35)"; ctx.lineWidth = 1;
      for (const [p, q] of res.grid_lines) { ctx.beginPath(); ctx.moveTo(m.X(p[0]), m.Y(p[1])); ctx.lineTo(m.X(q[0]), m.Y(q[1])); ctx.stroke(); }
      ctx.fillStyle = "rgba(235,104,52,.2)"; ctx.strokeStyle = "#eb6834"; ctx.lineWidth = 2; ctx.beginPath();
      res.unit_square.forEach((p, i) => (i ? ctx.lineTo(m.X(p[0]), m.Y(p[1])) : ctx.moveTo(m.X(p[0]), m.Y(p[1])))); ctx.closePath(); ctx.fill(); ctx.stroke();
      const O = [m.X(0), m.Y(0)];
      if (res.result.real_eigenvalues) for (const e of res.result.eigen) {
        const [vx, vy] = e.vector;
        ctx.strokeStyle = c3; ctx.lineWidth = 1.5; ctx.setLineDash([6, 5]);
        ctx.beginPath(); ctx.moveTo(m.X(-8 * vx), m.Y(-8 * vy)); ctx.lineTo(m.X(8 * vx), m.Y(8 * vy)); ctx.stroke(); ctx.setLineDash([]);
        arrow(ctx, ...O, m.X(e.value * vx), m.Y(e.value * vy), c3, 3, 10);
        label(ctx, `λ = ${fmt(e.value, 3)}`, m.X(e.value * vx) + 8, m.Y(e.value * vy) - 10, { font: "bold 12px system-ui", color: "#15845d", halo: "#fff" });
      }
      arrow(ctx, ...O, m.X(res.result.e1_image[0]), m.Y(res.result.e1_image[1]), c1, 3.5, 12);
      arrow(ctx, ...O, m.X(res.result.e2_image[0]), m.Y(res.result.e2_image[1]), c2, 3.5, 12);
      label(ctx, `area × ${fmt(res.result.determinant, 3)}`, 14, 20, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
