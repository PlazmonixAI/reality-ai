// Lenses & Mirrors: physics.lens_mirror computes the image and the three principal rays.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, View, label, arrow } from "../core/stage.js";
import { fmt } from "../core/format.js";

const KINDS = {
  converging_lens: "Converging lens", diverging_lens: "Diverging lens",
  concave_mirror: "Concave mirror", convex_mirror: "Convex mirror",
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let res = null, dragging = false;

    const kind = select({ label: "Optic", value: "converging_lens", options: Object.entries(KINDS).map(([value, label]) => ({ value, label })), onChange: () => recompute() });
    const f = slider({ label: "Focal length", min: 5, max: 30, step: 0.5, value: 12, unit: "cm", onInput: () => recompute() });
    const dObj = slider({ label: "Object distance", min: 2, max: 70, step: 0.5, value: 30, unit: "cm", onInput: () => recompute() });
    const hObj = slider({ label: "Object height", min: 1, max: 8, step: 0.1, value: 4, unit: "cm", onInput: () => recompute() });
    const out = readouts([{ key: "di", label: "Image distance" }, { key: "m", label: "Magnification" }, { key: "hi", label: "Image height" }, { key: "type", label: "Image" }]);
    L.side.append(
      panel("Setup", kind.root, f.root, dObj.root, hObj.root, el("p", { class: "note" }, "Drag the orange object left and right.")),
      panel("Image (from the engine)", out.root),
      panel("Principal rays", legend([{ label: "∥ axis → F", color: c1 }, { label: "through centre", color: c2 }, { label: "through F → ∥", color: c3 }]),
        el("p", { class: "note" }, "Dashed lines are backward extensions: where rays only appear to come from (virtual image).")),
    );

    const recompute = liveRequest((signal) => simulate("physics", "lens_mirror", {
      kind: kind.value, focal_length: f.value / 100, object_distance: dObj.value / 100, object_height: hObj.value / 100,
    }, signal), {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("di", x.image_distance === null ? "∞" : `${fmt(x.image_distance * 100, 4)} cm`);
        out.set("m", x.magnification === null ? "—" : `${fmt(x.magnification, 4)}×`);
        out.set("hi", x.image_height === null ? "—" : `${fmt(x.image_height * 100, 4)} cm`);
        out.set("type", x.orientation ? `${x.image_type}, ${x.orientation}` : x.image_type);
        draw();
      },
    });

    const toWorldX = (e) => { const r = stage.canvas.getBoundingClientRect(); return view.toWorld(e.clientX - r.left, e.clientY - r.top); };
    stage.canvas.addEventListener("pointerdown", (e) => {
      const [wx, wy] = toWorldX(e);
      if (Math.abs(wx + dObj.value / 100) < 0.03 && wy > -0.01 && wy < hObj.value / 100 + 0.02) { dragging = true; stage.canvas.setPointerCapture(e.pointerId); }
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const [wx] = toWorldX(e);
      dObj.set(Math.max(2, Math.min(70, Math.round(-wx * 200) / 2))); recompute();
    });
    stage.canvas.addEventListener("pointerup", () => { dragging = false; });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fdfdfb"; ctx.fillRect(0, 0, w, h);
      const mirror = kind.value.endsWith("mirror");
      // Frame the setup: object, focal points and (if not far off) the image.
      const di = res && res.result.image_distance !== null ? Math.abs(res.result.image_distance) : 0;
      const span = Math.min(0.8, Math.max(0.3, 2.4 * f.value / 100, (dObj.value / 100) * 1.15, Math.min(di, 0.8) * 1.15));
      const vert = Math.max(0.1, (hObj.value / 100) * 2.2, res && res.result.image_height !== null ? Math.min(Math.abs(res.result.image_height), 0.3) * 1.2 : 0);
      view.fit(-span, mirror ? span * 0.35 : span, -vert, vert, w, h, { pad: 0.03 });
      // Axis and distance ticks
      ctx.strokeStyle = "#9aa6b5"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, view.y(0)); ctx.lineTo(w, view.y(0)); ctx.stroke();
      const tick = span > 0.5 ? 10 : 5;
      for (let cm = -80; cm <= 80; cm += tick) {
        const x = view.x(cm / 100);
        ctx.beginPath(); ctx.moveTo(x, view.y(0) - 3); ctx.lineTo(x, view.y(0) + 3); ctx.stroke();
        if (cm % (tick * 2) === 0) label(ctx, `${cm} cm`, x, view.y(0) + 26, { align: "center", font: "10px system-ui", color: "#7b8796" });
      }
      // Optic
      const top = view.y(vert * 0.85), bot = view.y(-vert * 0.85), ox = view.x(0);
      ctx.strokeStyle = "#5598e7"; ctx.fillStyle = "rgba(85,152,231,.18)"; ctx.lineWidth = 2;
      if (!mirror) {
        const bulge = kind.value === "converging_lens" ? 14 : -10;
        ctx.beginPath(); ctx.moveTo(ox, top);
        ctx.quadraticCurveTo(ox + bulge * 1.6, (top + bot) / 2, ox, bot);
        ctx.quadraticCurveTo(ox - bulge * 1.6, (top + bot) / 2, ox, top);
        if (bulge < 0) { ctx.moveTo(ox - 10, top); ctx.lineTo(ox + 10, top); ctx.moveTo(ox - 10, bot); ctx.lineTo(ox + 10, bot); }
        ctx.fill(); ctx.stroke();
      } else {
        const bend = kind.value === "concave_mirror" ? 12 : -12;
        ctx.lineWidth = 4; ctx.strokeStyle = "#7b8796";
        ctx.beginPath(); ctx.moveTo(ox + bend, top); ctx.quadraticCurveTo(ox - bend, (top + bot) / 2, ox + bend, bot); ctx.stroke();
        ctx.strokeStyle = "#b8c4d3"; ctx.lineWidth = 1;
        for (let y = top; y < bot; y += 10) { ctx.beginPath(); ctx.moveTo(ox + Math.abs(bend) + 2, y); ctx.lineTo(ox + Math.abs(bend) + 10, y + 8); ctx.stroke(); }
      }
      if (!res) return;
      const g = res.geometry;
      // Focal points
      for (const fx of g.focal_points) {
        for (const mult of mirror ? [1] : [1, 2]) {
          const x = view.x(fx * mult);
          ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(x, view.y(0), 3.5, 0, Math.PI * 2); ctx.fill();
          label(ctx, mult === 2 ? "2F" : "F", x, view.y(0) - 12, { align: "center", font: "bold 12px system-ui" });
        }
      }
      // Rays
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, w, h); ctx.clip();
      [c1, c2, c3].forEach((c, i) => {
        const r = g.rays[i]; if (!r) return;
        ctx.strokeStyle = c; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(view.x(r[0][0]), view.y(r[0][1])); ctx.lineTo(view.x(r[1][0]), view.y(r[1][1])); ctx.lineTo(view.x(r[2][0]), view.y(r[2][1])); ctx.stroke();
        const m = [(r[0][0] + r[1][0]) / 2, (r[0][1] + r[1][1]) / 2];
        const d = [r[1][0] - r[0][0], r[1][1] - r[0][1]], n = Math.hypot(...d);
        arrow(ctx, view.x(m[0]), view.y(m[1]), view.x(m[0] + d[0] / n * 0.01), view.y(m[1] + d[1] / n * 0.01), c, 2, 8);
        const e = g.virtual_extensions[i];
        if (e) { ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.moveTo(view.x(e[0][0]), view.y(e[0][1])); ctx.lineTo(view.x(e[1][0]), view.y(e[1][1])); ctx.stroke(); ctx.setLineDash([]); }
      });
      ctx.restore();
      // Object and image arrows
      const drawArrowObj = (x, hgt, color, dashed, txt) => {
        ctx.setLineDash(dashed ? [5, 4] : []);
        arrow(ctx, view.x(x), view.y(0), view.x(x), view.y(hgt), color, 4, 12);
        ctx.setLineDash([]);
        label(ctx, txt, view.x(x), view.y(hgt) + (hgt > 0 ? -14 : 14), { align: "center", font: "bold 12px system-ui", color });
      };
      drawArrowObj(g.object.x, g.object.height, "#eb6834", false, "object");
      if (g.image && Math.abs(g.image.x) < 5) drawArrowObj(g.image.x, g.image.height, "#1c5cab", res.result.image_type === "virtual", `${res.result.image_type} image`);
      label(ctx, KINDS[kind.value], 14, 20, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
