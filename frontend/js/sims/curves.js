// Parametric & Polar Curves: mathematics.plane_curve samples the curve and computes arc length and enclosed area.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, segmented, textInput, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { fmt } from "../core/format.js";
import { axes } from "./plotkit.js";

const PI = Math.PI;
const PRESETS = {
  cardioid: { label: "Cardioid", kind: "polar", r: "a*(1 + cos(theta))", end: 2, a: 2 },
  rose: { label: "Rose r = a cos(bθ)", kind: "polar", r: "a*cos(b*theta)", end: 1, a: 4, b: 3 },
  spiral: { label: "Archimedean spiral", kind: "polar", r: "a*theta/(2*pi)", end: 8, a: 1 },
  lissajous: { label: "Lissajous figure", kind: "parametric", x: "4*sin(a*t + pi/2)", y: "4*sin(b*t)", end: 2, a: 3, b: 2 },
  cycloid: { label: "Cycloid", kind: "parametric", x: "a*(t - sin(t))", y: "a*(1 - cos(t))", end: 4, a: 1 },
  astroid: { label: "Astroid", kind: "parametric", x: "a*cos(t)**3", y: "a*sin(t)**3", end: 2, a: 5 },
  butterfly: { label: "Butterfly curve", kind: "polar", r: "exp(cos(theta)) - 2*cos(4*theta) + sin(theta/12)**5", end: 24, a: 1 },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, frac = 1;

    const preset = select({ label: "Curve", value: "rose", options: Object.entries(PRESETS).map(([v, p]) => ({ value: v, label: p.label })), onChange: (v) => load(v) });
    const kind = segmented({ label: "Type", value: "polar", options: [{ value: "polar", label: "Polar r(θ)" }, { value: "parametric", label: "Parametric (x(t), y(t))" }], onChange: () => { sync(); recompute(); } });
    const rIn = textInput({ label: "r(θ) =", mono: true, onChange: () => recompute() });
    const xIn = textInput({ label: "x(t) =", mono: true, onChange: () => recompute() });
    const yIn = textInput({ label: "y(t) =", mono: true, onChange: () => recompute() });
    const end = slider({ label: "Parameter runs from 0 to", min: 0.25, max: 24, step: 0.25, value: 2, format: (v) => `${fmt(v, 3)}π`, onInput: () => recompute() });
    const a = slider({ label: "a", min: 0.5, max: 8, step: 0.5, value: 4, onInput: () => recompute() });
    const b = slider({ label: "b", min: 1, max: 9, step: 1, value: 3, onInput: () => recompute() });
    const out = readouts([{ key: "len", label: "Arc length" }, { key: "area", label: "Enclosed area" }, { key: "closed", label: "Closed curve?" }]);
    function sync() { const p = kind.value === "polar"; rIn.root.style.display = p ? "" : "none"; xIn.root.style.display = yIn.root.style.display = p ? "none" : ""; }
    function load(v) {
      const p = PRESETS[v]; kind.set(p.kind); sync();
      if (p.r) rIn.set(p.r); if (p.x) { xIn.set(p.x); yIn.set(p.y); }
      end.set(p.end); a.set(p.a ?? 1); if (p.b) b.set(p.b);
      recompute();
    }
    L.side.append(
      panel("Curve", preset.root, kind.root, rIn.root, xIn.root, yIn.root, end.root, a.root, b.root, el("p", { class: "note" }, "Use a and b in the formulas; they follow the sliders.")),
      panel("Measurements (from the engine)", out.root, el("p", { class: "note" }, "Area is ½∮(x dy − y dx) (polar: ½∫r² dθ), overlapping loops count more than once.")),
    );
    const player = new Player(L.bottom, (t) => { frac = t; draw(); }, { speeds: [0.5, 1, 2], loop: false, timeFormat: (v) => `${fmt(v * end.value, 3)}π` });

    const recompute = liveRequest((signal) => simulate("mathematics", "plane_curve", {
      kind: kind.value, r_expression: rIn.value, x_expression: xIn.value, y_expression: yIn.value,
      start: 0, stop: end.value * PI, n_points: 3000, parameters: { a: a.value, b: b.value },
    }, signal), {
      delay: 60, onBusy: L.busy, onError: (e) => { res = null; L.error(e.message); draw(); },
      onResult: (r) => {
        L.clearError(); res = r;
        out.set("len", fmt(r.result.arc_length, 5)); out.set("area", fmt(r.result.area, 5)); out.set("closed", r.result.closed ? "yes" : "no");
        player.load(1, 5);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      if (!res) { axes(ctx, w, h, [-5, 5], [-5, 5], { equal: true }); return; }
      const bx = res.result.bounds, span = Math.max(bx.x[1] - bx.x[0], bx.y[1] - bx.y[0], 1) * 0.6;
      const cx = (bx.x[0] + bx.x[1]) / 2, cy = (bx.y[0] + bx.y[1]) / 2;
      const m = axes(ctx, w, h, [cx - span, cx + span], [cy - span, cy + span], { equal: true });
      const xs = res.curve.x, ys = res.curve.y, n = Math.max(2, Math.round(frac * xs.length));
      ctx.strokeStyle = "rgba(42,120,214,.18)"; ctx.lineWidth = 2; ctx.beginPath(); xs.forEach((x, i) => (i ? ctx.lineTo(m.X(x), m.Y(ys[i])) : ctx.moveTo(m.X(x), m.Y(ys[i])))); ctx.stroke();
      ctx.strokeStyle = c1; ctx.lineWidth = 3; ctx.beginPath(); for (let i = 0; i < n; i++) (i ? ctx.lineTo(m.X(xs[i]), m.Y(ys[i])) : ctx.moveTo(m.X(xs[i]), m.Y(ys[i]))); ctx.stroke();
      const k = n - 1;
      if (kind.value === "polar") { ctx.strokeStyle = c2; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(m.X(0), m.Y(0)); ctx.lineTo(m.X(xs[k]), m.Y(ys[k])); ctx.stroke(); }
      ctx.fillStyle = c2; ctx.beginPath(); ctx.arc(m.X(xs[k]), m.Y(ys[k]), 6, 0, Math.PI * 2); ctx.fill();
      label(ctx, `${kind.value === "polar" ? "θ" : "t"} = ${fmt((res.curve.s[k] / PI), 3)}π`, 12, 16, { font: "bold 13px system-ui", halo: "#fff" });
    }

    load("rose");
    return () => { recompute.cancel(); player.destroy(); stage.destroy(); };
  },
};
