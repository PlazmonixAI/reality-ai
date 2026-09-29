// Least-Squares Fitting: mathematics.least_squares_fit fits the points you place; residuals shown as bars.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";
import { axes, curve } from "./plotkit.js";

// Example data sets (Anscombe's first quartet set is a classic published example).
const DATA = {
  anscombe: { label: "Anscombe's quartet, set I", x: [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5], y: [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68] },
  growth: { label: "Doubling-ish growth", x: [0, 1, 2, 3, 4, 5, 6, 7], y: [1.1, 1.9, 4.2, 7.8, 16.5, 31, 66, 125] },
  arc: { label: "Projectile-like arc", x: [0, 1, 2, 3, 4, 5, 6, 7, 8], y: [0.2, 6.8, 11.4, 15.3, 15.9, 15.2, 11.8, 7.1, 0.4] },
  clear: { label: "Empty (click to add points)", x: [], y: [] },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let pts = [], res = null, m = null, drag = -1, view = [[0, 15], [0, 14]];

    const data = select({ label: "Data", value: "anscombe", options: Object.entries(DATA).map(([v, d]) => ({ value: v, label: d.label })), onChange: (v) => loadData(v) });
    const model = select({ label: "Model", value: "linear", options: [
      { value: "linear", label: "Line y = a + bx" }, { value: "polynomial", label: "Polynomial" }, { value: "exponential", label: "Exponential y = a e^(bx)" },
      { value: "power", label: "Power y = a x^b" }, { value: "logarithmic", label: "Logarithmic y = a + b ln x" }], onChange: () => { sync(); recompute(); } });
    const deg = slider({ label: "Polynomial degree", min: 1, max: 8, step: 1, value: 2, onInput: () => recompute() });
    const eq = el("p", { class: "note", style: "font-family: ui-monospace, monospace" });
    const out = readouts([{ key: "r2", label: "R²" }, { key: "rms", label: "RMS error" }, { key: "c", label: "Coefficients ± SE" }]);
    function sync() { deg.root.style.display = model.value === "polynomial" ? "" : "none"; }
    L.side.append(
      panel("Data & model", data.root, model.root, deg.root, button("Clear points", () => { pts = []; recompute(); draw(); }),
        el("p", { class: "note" }, "Click to add a point, drag to move it, right-click to delete it.")),
      panel("Fit (from the engine)", eq, out.root),
    );
    sync();
    const resid = new LineGraph(L.bottom, { title: "Residuals y − ŷ (look for patterns: a good model leaves random scatter)", xLabel: "x", yLabel: "residual", height: 140, includeZero: true });

    function loadData(v) {
      const d = DATA[v]; pts = d.x.map((x, i) => [x, d.y[i]]);
      if (pts.length) {
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
        const px = (Math.max(...xs) - Math.min(...xs)) * 0.15 + 1, py = (Math.max(...ys) - Math.min(...ys)) * 0.15 + 1;
        view = [[Math.min(0, Math.min(...xs) - px), Math.max(...xs) + px], [Math.min(0, Math.min(...ys) - py), Math.max(...ys) + py]];
      } else view = [[0, 10], [0, 10]];
      recompute(); draw();
    }

    const recompute = liveRequest((signal) => {
      if (pts.length < 2) return Promise.resolve(null);
      return simulate("mathematics", "least_squares_fit", { x: pts.map((p) => p[0]), y: pts.map((p) => p[1]), model: model.value, degree: deg.value }, signal);
    }, {
      delay: 40, onError: (e) => { res = null; L.error(e.message); eq.textContent = ""; draw(); },
      onResult: (r) => {
        res = r;
        if (!r) { L.clearError(); eq.textContent = "Add at least two points."; out.set("r2", "—"); out.set("rms", "—"); out.set("c", "—"); resid.setSeries([]); draw(); return; }
        L.clearError();
        const x = r.result;
        eq.textContent = x.equation;
        out.set("r2", fmt(x.r_squared, 5)); out.set("rms", fmt(x.rms_error, 4));
        out.set("c", Object.entries(x.coefficients).map(([k, v]) => `${k} = ${fmt(v, 4)}${x.standard_errors[k] !== null ? ` ± ${fmt(x.standard_errors[k], 2)}` : ""}`).join(", "));
        resid.setSeries([{ name: "residual", color: c2, x: pts.map((p) => p[0]), y: r.residuals, bars: true }]);
        draw();
      },
    });

    const toData = (e) => { const b = stage.canvas.getBoundingClientRect(); return m.inv(e.clientX - b.left, e.clientY - b.top); };
    const nearest = (e) => { const b = stage.canvas.getBoundingClientRect(), px = e.clientX - b.left, py = e.clientY - b.top; return pts.findIndex((p) => Math.hypot(m.X(p[0]) - px, m.Y(p[1]) - py) < 10); };
    stage.canvas.addEventListener("contextmenu", (e) => { e.preventDefault(); const i = nearest(e); if (i >= 0) { pts.splice(i, 1); data.set("clear"); recompute(); draw(); } });
    stage.canvas.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 || !m) return;
      drag = nearest(e);
      if (drag < 0) { pts.push(toData(e)); drag = pts.length - 1; }
      stage.canvas.setPointerCapture(e.pointerId); recompute(); draw();
    });
    stage.canvas.addEventListener("pointermove", (e) => { if (drag >= 0) { pts[drag] = toData(e); recompute(); draw(); } });
    stage.canvas.addEventListener("pointerup", () => { drag = -1; });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      m = axes(ctx, w, h, view[0], view[1]);
      if (res) {
        const xs = pts.map((p) => p[0]);
        // Residual segments from each point to the fitted value
        ctx.strokeStyle = "rgba(235,104,52,.6)"; ctx.lineWidth = 1.5;
        res.fitted.forEach((yh, i) => { if (i >= pts.length) return; ctx.beginPath(); ctx.moveTo(m.X(xs[i]), m.Y(pts[i][1])); ctx.lineTo(m.X(xs[i]), m.Y(yh)); ctx.stroke(); });
        curve(ctx, m, res.curve.x, res.curve.y, c1, { width: 3 });
      }
      ctx.fillStyle = "#16202c";
      pts.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(m.X(x), m.Y(y), 5.5, 0, Math.PI * 2); ctx.fill(); });
      label(ctx, `${pts.length} points`, w - 12, 16, { align: "right", font: "12px system-ui", color: "#4b5868", halo: "#fff" });
    }

    loadData("anscombe");
    return () => { recompute.cancel(); resid.destroy(); stage.destroy(); };
  },
};
