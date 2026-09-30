// Conic Sections: mathematics.conic_section classifies Ax² + Bxy + Cy² + Dx + Ey + F = 0 and gives foci, axes, branches.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { axes, curve } from "./plotkit.js";

const PRESETS = {
  ellipse: ["Ellipse x²/9 + y²/4 = 1", [4, 0, 9, 0, 0, -36]],
  circle: ["Circle x² + y² = 9", [1, 0, 1, 0, 0, -9]],
  parabola: ["Parabola y = x²/4", [1, 0, 0, 0, -4, 0]],
  hyperbola: ["Hyperbola x²/4 − y² = 1", [1, 0, -4, 0, 0, -4]],
  rotated: ["Rotated ellipse", [5, 4, 5, -14, -14, 5]],
  xy: ["Rectangular hyperbola xy = 2", [0, 1, 0, 0, 0, -2]],
};
const NAMES = ["A", "B", "C", "D", "E", "F"];
const SUFFIX = ["x²", "xy", "y²", "x", "y", ""];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null;

    const preset = select({ label: "Start from", value: "ellipse", options: [...Object.entries(PRESETS).map(([v, [l]]) => ({ value: v, label: l })), { value: "custom", label: "Custom" }], onChange: (v) => { if (PRESETS[v]) PRESETS[v][1].forEach((c, i) => sl[i].set(c)); recompute(); } });
    const sl = NAMES.map((n, i) => slider({ label: `${n}${SUFFIX[i] ? " (" + SUFFIX[i] + ")" : ""}`, min: n === "F" ? -50 : -10, max: n === "F" ? 50 : 10, step: 0.5, value: PRESETS.ellipse[1][i], onInput: () => { preset.set("custom"); recompute(); } }));
    const eq = el("p", { class: "note", style: "font-family: ui-monospace, monospace" });
    const out = readouts([
      { key: "type", label: "Type" }, { key: "e", label: "Eccentricity" }, { key: "c", label: "Centre / vertex" },
      { key: "ax", label: "Axes" }, { key: "ang", label: "Rotation" }, { key: "disc", label: "B² − 4AC" },
    ]);
    L.side.append(
      panel("Ax² + Bxy + Cy² + Dx + Ey + F = 0", preset.root, ...sl.map((s) => s.root), eq),
      panel("Conic (from the engine)", out.root, el("p", { class: "note" }, "B² − 4AC < 0: ellipse · = 0: parabola · > 0: hyperbola. Orange dots are foci.")),
    );

    const recompute = liveRequest((signal) => {
      const [a, b, c, d, e, f] = sl.map((s) => s.value);
      return simulate("mathematics", "conic_section", { a, b, c, d, e, f, extent: 30 }, signal);
    }, {
      delay: 30, onError: (e) => { res = null; L.error(e.message); draw(); },
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result, pt = (p) => `(${fmt(p[0], 3)}, ${fmt(p[1], 3)})`;
        eq.textContent = sl.map((s, i) => (s.value ? `${s.value >= 0 && i ? "+ " : ""}${s.value < 0 ? "− " : ""}${fmt(Math.abs(s.value), 3)}${SUFFIX[i]}` : "")).filter(Boolean).join(" ") + " = 0";
        out.set("type", x.type); out.set("e", x.eccentricity !== undefined ? fmt(x.eccentricity, 4) : "–");
        out.set("c", x.center ? pt(x.center) : x.vertex ? `vertex ${pt(x.vertex)}` : "–");
        out.set("ax", x.semi_major ? `a = ${fmt(x.semi_major, 4)}, b = ${fmt(x.semi_minor, 4)}` : x.semi_transverse ? `a = ${fmt(x.semi_transverse, 4)}, b = ${fmt(x.semi_conjugate, 4)}` : x.focal_length ? `focal length ${fmt(x.focal_length, 4)}` : "–");
        out.set("ang", x.angle_deg !== undefined ? `${fmt(x.angle_deg, 4)}°` : "–"); out.set("disc", fmt(x.discriminant, 4));
        draw();
      },
    });

    function line(ctx, m, p, d, color) {
      ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.setLineDash([6, 5]); ctx.beginPath();
      ctx.moveTo(m.X(p[0] - 60 * d[0]), m.Y(p[1] - 60 * d[1])); ctx.lineTo(m.X(p[0] + 60 * d[0]), m.Y(p[1] + 60 * d[1])); ctx.stroke(); ctx.setLineDash([]);
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const m = axes(ctx, w, h, [-10, 10], [-8, 8], { equal: true });
      if (!res) return;
      const x = res.result;
      (x.asymptotes || []).forEach((a) => line(ctx, m, a.point, a.direction, "#9aa6b5"));
      if (x.directrix) line(ctx, m, x.directrix.point, x.directrix.direction, c3);
      res.branches.forEach((b) => curve(ctx, m, b.x, b.y, c1, { width: 3 }));
      const dot = (p, col, r = 5) => { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(m.X(p[0]), m.Y(p[1]), r, 0, Math.PI * 2); ctx.fill(); };
      (x.foci || (x.focus ? [x.focus] : [])).forEach((p) => dot(p, c2, 6));
      (x.vertices || (x.vertex ? [x.vertex] : [])).forEach((p) => dot(p, "#16202c", 3.5));
      if (x.center) dot(x.center, "#16202c", 3);
      if (x.directrix) label(ctx, "directrix", m.X(x.directrix.point[0]) + 6, m.Y(x.directrix.point[1]) - 8, { color: c3, font: "11px system-ui", halo: "#fff" });
      label(ctx, x.type, 12, 16, { font: "bold 13px system-ui", halo: "#fff" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
