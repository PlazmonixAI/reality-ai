// Complex Plane: mathematics.complex_numbers for products, quotients and n-th roots; drag z and w.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label, arrow } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { axes } from "./plotkit.js";

const cstr = ([a, b]) => `${fmt(a, 3)} ${b < 0 ? "−" : "+"} ${fmt(Math.abs(b), 3)}i`;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let z = [1.5, 1], w = [0.5, 1.5], res = null, drag = null, map = null;

    const show = segmented({ label: "Show", value: "product", options: [{ value: "sum", label: "z + w" }, { value: "product", label: "z · w" }, { value: "quotient", label: "z / w" }, { value: "roots", label: "roots of z" }], onChange: () => draw() });
    const n = slider({ label: "n for the n-th roots", min: 2, max: 12, step: 1, value: 5, onInput: () => recompute() });
    const out = readouts([
      { key: "z", label: "z" }, { key: "zp", label: "|z|, arg z" }, { key: "w", label: "w" }, { key: "wp", label: "|w|, arg w" },
      { key: "p", label: "z · w" }, { key: "pp", label: "|zw|, arg zw" }, { key: "q", label: "z / w" },
    ]);
    L.side.append(
      panel("Operation", show.root, n.root, legend([{ label: "z", color: c1 }, { label: "w", color: c2 }, { label: "result", color: c3 }]),
        el("p", { class: "note" }, "Drag the tips of z and w. Multiplying multiplies the lengths and adds the angles.")),
      panel("Values (from the engine)", out.root),
    );

    const recompute = liveRequest((signal) => simulate("mathematics", "complex_numbers", { z, w, n: n.value }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        const pol = (p) => `${fmt(p.modulus, 3)}, ${fmt(p.argument_deg, 4)}°`;
        out.set("z", cstr(res.z)); out.set("zp", pol(res.z_polar)); out.set("w", cstr(res.w)); out.set("wp", pol(res.w_polar));
        out.set("p", cstr(res.product)); out.set("pp", pol(res.product_polar)); out.set("q", res.quotient ? cstr(res.quotient) : "undefined (w = 0)");
        draw();
      },
    });

    const world = (e) => { const r = stage.canvas.getBoundingClientRect(); return map.inv(e.clientX - r.left, e.clientY - r.top); };
    stage.canvas.addEventListener("pointerdown", (e) => {
      if (!map) return;
      const [x, y] = world(e);
      drag = Math.hypot(x - z[0], y - z[1]) < 0.35 ? "z" : Math.hypot(x - w[0], y - w[1]) < 0.35 ? "w" : null;
      if (drag) stage.canvas.setPointerCapture(e.pointerId);
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const [x, y] = world(e), p = [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
      if (drag === "z") z = p; else w = p;
      recompute(); draw();
    });
    stage.canvas.addEventListener("pointerup", () => { drag = null; });

    function draw() {
      const { ctx, width: W, height: H } = stage;
      if (!W) return;
      map = axes(ctx, W, H, [-4, 4], [-3, 3], { equal: true });
      const O = [map.X(0), map.Y(0)], P = (p) => [map.X(p[0]), map.Y(p[1])];
      ctx.strokeStyle = "#e3e8ef"; ctx.beginPath(); ctx.arc(...O, map.X(1) - map.X(0), 0, Math.PI * 2); ctx.stroke();
      label(ctx, "Re", W - 18, map.Y(0) - 10, { font: "12px system-ui", color: "#4b5868" });
      label(ctx, "Im", map.X(0) + 8, 14, { font: "12px system-ui", color: "#4b5868" });
      if (!res) return;
      const angArc = (p, color, rr) => {
        const a = Math.atan2(p[1], p[0]);
        ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(...O, rr, 0, -a, a > 0); ctx.stroke();
      };
      if (show.value === "roots") {
        const pts = res.roots.map(P);
        ctx.strokeStyle = c3; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4]); ctx.beginPath();
        pts.forEach((p, i) => (i ? ctx.lineTo(...p) : ctx.moveTo(...p))); ctx.closePath(); ctx.stroke(); ctx.setLineDash([]);
        pts.forEach((p) => { ctx.fillStyle = c3; ctx.beginPath(); ctx.arc(...p, 6, 0, Math.PI * 2); ctx.fill(); });
        label(ctx, `the ${n.value} values of z^(1/${n.value})`, 14, 20, { font: "bold 13px system-ui" });
      } else {
        const r = res[show.value];
        if (r) {
          if (show.value === "sum") {
            ctx.setLineDash([5, 4]); ctx.strokeStyle = "#9aa6b5"; ctx.beginPath(); ctx.moveTo(...P(z)); ctx.lineTo(...P(r)); ctx.lineTo(...P(w)); ctx.stroke(); ctx.setLineDash([]);
          } else { angArc(z, c1, 26); angArc(w, c2, 34); angArc(r, c3, 44); }
          arrow(ctx, ...O, ...P(r), c3, 3.5, 12);
          label(ctx, `${show.value === "product" ? "z·w" : show.value === "sum" ? "z+w" : "z/w"} = ${cstr(r)}`, P(r)[0] + 10, P(r)[1] - 12, { font: "bold 12px system-ui", color: c3, halo: "#fff" });
        }
      }
      arrow(ctx, ...O, ...P(z), c1, 3, 11); arrow(ctx, ...O, ...P(w), c2, 3, 11);
      for (const [p, name, col] of [[z, "z", c1], [w, "w", c2]]) {
        ctx.fillStyle = "rgba(22,32,44,.12)"; ctx.beginPath(); ctx.arc(...P(p), 11, 0, Math.PI * 2); ctx.fill();
        label(ctx, name, P(p)[0] + 12, P(p)[1] - 12, { font: "bold 15px system-ui", color: col, halo: "#fff" });
      }
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
