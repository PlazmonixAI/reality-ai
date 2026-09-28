// Slope Fields & Phase Portraits: slope_field and phase_portrait from the engine; click to add solution curves.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, segmented, select, textInput, button, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, label, arrow } from "../core/stage.js";
import { fmt } from "../core/format.js";

const SLOPE = {
  linear: { label: "y′ = x − y", f: "x - y", range: [-4, 4, -4, 4] },
  logistic: { label: "y′ = y(1 − y)  (logistic)", f: "y*(1 - y)", range: [-3, 5, -1, 2] },
  growth: { label: "y′ = x·y", f: "x*y", range: [-3, 3, -3, 3] },
  forced: { label: "y′ = sin(x) − y", f: "sin(x) - y", range: [-6, 6, -3, 3] },
};
const PHASE = {
  predator: { label: "Predator–prey (Lotka–Volterra)", f: "x - x*y", g: "x*y - y", range: [-0.2, 3.5, -0.2, 3.5] },
  damped: { label: "Damped oscillator", f: "y", g: "-x - 0.4*y", range: [-3, 3, -3, 3] },
  pendulum: { label: "Pendulum (x = angle)", f: "y", g: "-sin(x)", range: [-7, 7, -3, 3] },
  vanderpol: { label: "Van der Pol oscillator", f: "y", g: "(1 - x^2)*y - x", range: [-4, 4, -4, 4] },
  saddle: { label: "Saddle", f: "x + y", g: "4*x + y", range: [-3, 3, -3, 3] },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2] = SERIES();
    let res = null, points = [];

    const mode = segmented({ label: "Mode", value: "phase", options: [{ value: "slope", label: "Slope field y′ = f(x, y)" }, { value: "phase", label: "Phase portrait" }], onChange: () => { sync(); applyPreset(); } });
    const presetS = select({ label: "Equation", value: "linear", options: [...Object.entries(SLOPE).map(([v, p]) => ({ value: v, label: p.label })), { value: "custom", label: "Custom" }], onChange: () => applyPreset() });
    const presetP = select({ label: "System", value: "predator", options: [...Object.entries(PHASE).map(([v, p]) => ({ value: v, label: p.label })), { value: "custom", label: "Custom" }], onChange: () => applyPreset() });
    const fIn = textInput({ label: "f(x, y) =", value: "x - y", mono: true, onChange: () => { markCustom(); recompute(); } });
    const gIn = textInput({ label: "dy/dt = g(x, y) =", value: "", mono: true, onChange: () => { markCustom(); recompute(); } });
    const eqBox = el("div");
    let range = [-4, 4, -4, 4];
    function markCustom() { (mode.value === "slope" ? presetS : presetP).set("custom"); }
    function sync() {
      const ph = mode.value === "phase";
      presetS.root.style.display = ph ? "none" : ""; presetP.root.style.display = ph ? "" : "none";
      gIn.root.style.display = ph ? "" : "none";
      fIn.root.querySelector("label").textContent = ph ? "dx/dt = f(x, y) =" : "dy/dx = f(x, y) =";
    }
    function applyPreset() {
      const ph = mode.value === "phase";
      const p = ph ? PHASE[presetP.value] : SLOPE[presetS.value];
      if (p) { fIn.set(p.f); if (ph) gIn.set(p.g); range = p.range; }
      points = ph ? [[1.5, 0.6], [0.5, 1.8], [2.5, 1.2]].map(([x, y]) => [range[0] + (x / 3) * (range[1] - range[0]), range[2] + (y / 3) * (range[3] - range[2])]) : [[0, 1], [0, -2]];
      recompute();
    }
    L.side.append(
      panel("Equation", mode.root, presetS.root, presetP.root, fIn.root, gIn.root, el("div", { class: "btn-row" }, button("Clear curves", () => { points = []; recompute(); }))),
      panel("Equilibria (from the engine)", eqBox, el("p", { class: "note" }, "Click anywhere to start a new solution curve.")),
    );
    sync();

    const recompute = liveRequest((signal) => {
      const [x0, x1, y0, y1] = range;
      if (mode.value === "slope") return simulate("mathematics", "slope_field", { expression: fIn.value, x_range: [x0, x1], y_range: [y0, y1], grid: 25, points }, signal);
      return simulate("mathematics", "phase_portrait", { dx: fIn.value, dy: gIn.value, x_range: [x0, x1], y_range: [y0, y1], grid: 25, points, duration: 25 }, signal);
    }, {
      delay: 150, onBusy: L.busy, onError: (e) => { L.error(e.message); },
      onResult: (r) => {
        L.clearError(); res = r;
        const eq = r.result.equilibria;
        if (!eq) eqBox.replaceChildren(el("p", { class: "note" }, "Slope fields show the direction of solutions at every point."));
        else if (!eq.length) eqBox.replaceChildren(el("p", { class: "note" }, "No equilibrium in this window."));
        else {
          const ro = readouts(eq.map((e, i) => ({ key: String(i), label: `(${fmt(e.x, 3)}, ${fmt(e.y, 3)})` })));
          eq.forEach((e, i) => ro.set(String(i), e.type));
          eqBox.replaceChildren(ro.root);
        }
        draw();
      },
    });

    stage.canvas.addEventListener("pointerdown", (e) => {
      const r = stage.canvas.getBoundingClientRect();
      const [x, y] = view.toWorld(e.clientX - r.left, e.clientY - r.top);
      points = [...points.slice(-19), [x, y]];
      recompute();
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const [x0, x1, y0, y1] = range;
      view.fit(x0, x1, y0, y1, w, h, { pad: 0.03 });
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "#9aa6b5"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(view.x(x0), view.y(0)); ctx.lineTo(view.x(x1), view.y(0)); ctx.moveTo(view.x(0), view.y(y0)); ctx.lineTo(view.x(0), view.y(y1)); ctx.stroke();
      if (!res) return;
      const F = res.field, cell = view.len((x1 - x0) / (F.x.length - 1)) * 0.38;
      ctx.strokeStyle = "rgba(75,88,104,.55)"; ctx.lineWidth = 1.3;
      F.y.forEach((yy, j) => F.x.forEach((xx, i) => {
        let dx, dy;
        if (F.slope) { const s = F.slope[j][i]; if (s === null) return; const n = Math.hypot(1, s); dx = 1 / n; dy = s / n; }
        else { const u = F.u[j][i], v = F.v[j][i], n = Math.hypot(u, v); if (!n) return; dx = u / n; dy = v / n; }
        const X = view.x(xx), Y = view.y(yy);
        if (F.slope) { ctx.beginPath(); ctx.moveTo(X - dx * cell, Y + dy * cell); ctx.lineTo(X + dx * cell, Y - dy * cell); ctx.stroke(); }
        else arrow(ctx, X - dx * cell, Y + dy * cell, X + dx * cell, Y - dy * cell, "rgba(75,88,104,.55)", 1.2, 5);
      }));
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, h); ctx.clip();
      for (const c of res.curves || res.trajectories || []) {
        ctx.strokeStyle = c1; ctx.lineWidth = 2.5; ctx.beginPath();
        c.x.forEach((xx, k) => (k ? ctx.lineTo(view.x(xx), view.y(c.y[k])) : ctx.moveTo(view.x(xx), view.y(c.y[k])))); ctx.stroke();
        ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(view.x(c.start[0]), view.y(c.start[1]), 5, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();
      for (const e of res.result.equilibria || []) {
        const X = view.x(e.x), Y = view.y(e.y);
        ctx.fillStyle = "#fff"; ctx.strokeStyle = c2; ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(X, Y, 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        label(ctx, e.type, X + 10, Y - 12, { font: "bold 12px system-ui", color: "#c14f22", halo: "#fff" });
      }
      label(ctx, `x ∈ [${x0}, ${x1}],  y ∈ [${y0}, ${y1}]`, w - 12, h - 12, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    applyPreset();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
