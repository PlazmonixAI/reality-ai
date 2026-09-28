// Unit Circle & Trig Graphs: trig_exact gives exact values; evaluate_function draws the sine and cosine waves.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, checkbox, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, arrow } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null, drag = false;

    const angle = slider({ label: "Angle θ", min: 0, max: 360, step: 1, value: 30, unit: "°", onInput: () => { recompute(); draw(); } });
    const snap = checkbox({ label: "Snap to special angles (multiples of 15°)", value: true });
    const out = readouts([
      { key: "rad", label: "Radians" }, { key: "sin", label: "sin θ" }, { key: "cos", label: "cos θ" }, { key: "tan", label: "tan θ" },
      { key: "q", label: "Quadrant" }, { key: "ref", label: "Reference angle" },
    ]);
    L.side.append(
      panel("Angle", angle.root, snap.root, el("p", { class: "note" }, "Drag the point around the circle.")),
      panel("Values (exact, from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "sin θ and cos θ", xLabel: "θ (degrees)", yLabel: "value", height: 170, yRange: [-1.2, 1.2] });
    Promise.all([
      simulate("mathematics", "evaluate_function", { expression: "sin(x*pi/180)", start: 0, stop: 360, n_points: 361 }),
      simulate("mathematics", "evaluate_function", { expression: "cos(x*pi/180)", start: 0, stop: 360, n_points: 361 }),
    ]).then(([s, c]) => {
      graph.setSeries([{ name: "sin θ", color: c1, x: s.result.x, y: s.result.y }, { name: "cos θ", color: c2, x: c.result.x, y: c.result.y, dash: true }]);
      graph.setCursor(angle.value);
    }).catch((e) => L.error(e.message));

    const recompute = liveRequest((signal) => simulate("mathematics", "trig_exact", { angle_deg: angle.value }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("rad", `${r.radians} ≈ ${fmt(r.radians_value, 4)}`);
        out.set("sin", `${x.sin} ≈ ${fmt(x.sin_value, 4)}`);
        out.set("cos", `${x.cos} ≈ ${fmt(x.cos_value, 4)}`);
        out.set("tan", x.tan === "undefined" ? "undefined" : `${x.tan} ≈ ${fmt(x.tan_value, 4)}`);
        out.set("q", r.quadrant ? ["I", "II", "III", "IV"][r.quadrant - 1] : "on an axis");
        out.set("ref", `${fmt(r.reference_angle_deg, 3)}°`);
        graph.setCursor(angle.value);
        draw();
      },
    });

    const geom = () => { const { width: w, height: h } = stage; const R = Math.min(w * 0.3, h * 0.38); return { cx: w * 0.42, cy: h / 2, R }; };
    const setFromPointer = (e) => {
      const r = stage.canvas.getBoundingClientRect(), { cx, cy } = geom();
      let a = (Math.atan2(cy - (e.clientY - r.top), e.clientX - r.left - cx) * 180) / Math.PI;
      if (a < 0) a += 360;
      a = snap.value ? Math.round(a / 15) * 15 % 360 : Math.round(a);
      angle.set(a); recompute(); draw();
    };
    stage.canvas.addEventListener("pointerdown", (e) => { drag = true; stage.canvas.setPointerCapture(e.pointerId); setFromPointer(e); });
    stage.canvas.addEventListener("pointermove", (e) => { if (drag) setFromPointer(e); });
    stage.canvas.addEventListener("pointerup", () => { drag = false; });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      const { cx, cy, R } = geom();
      ctx.strokeStyle = "#e3e8ef"; ctx.lineWidth = 1;
      for (let a = 0; a < 360; a += 15) {
        const t = (a * Math.PI) / 180;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(t) * R * 1.08, cy - Math.sin(t) * R * 1.08); ctx.stroke();
      }
      ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(cx - R * 1.25, cy); ctx.lineTo(cx + R * 1.25, cy); ctx.moveTo(cx, cy - R * 1.25); ctx.lineTo(cx, cy + R * 1.25); ctx.stroke();
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
      for (const [t, s] of [[0, "(1, 0)"], [90, "(0, 1)"], [180, "(−1, 0)"], [270, "(0, −1)"]]) {
        const a = (t * Math.PI) / 180;
        label(ctx, s, cx + Math.cos(a) * R * 1.14, cy - Math.sin(a) * R * 1.14, { align: "center", font: "11px system-ui", color: "#4b5868" });
      }
      if (!res) return;
      const cs = res.result.cos_value, sn = res.result.sin_value;
      const px = cx + cs * R, py = cy - sn * R;
      // Angle arc
      ctx.strokeStyle = c3; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, R * 0.18, 0, -(angle.value * Math.PI) / 180, true); ctx.stroke();
      label(ctx, `${angle.value}°`, cx + R * 0.26 * Math.cos((angle.value * Math.PI) / 360), cy - R * 0.26 * Math.sin((angle.value * Math.PI) / 360), { font: "bold 12px system-ui", color: c3 });
      // Triangle: cos along x, sin along y
      ctx.lineWidth = 4;
      ctx.strokeStyle = c2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(px, cy); ctx.stroke();
      ctx.strokeStyle = c1; ctx.beginPath(); ctx.moveTo(px, cy); ctx.lineTo(px, py); ctx.stroke();
      arrow(ctx, cx, cy, px, py, "#16202c", 2, 10);
      ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(px, py, 7, 0, Math.PI * 2); ctx.fill();
      label(ctx, `cos θ = ${res.result.cos}`, (cx + px) / 2, cy + (sn >= 0 ? 16 : -16), { align: "center", font: "bold 12px system-ui", color: c2, halo: "#fff" });
      label(ctx, `sin θ = ${res.result.sin}`, px + (cs >= 0 ? 10 : -10), (cy + py) / 2, { align: cs >= 0 ? "left" : "right", font: "bold 12px system-ui", color: c1, halo: "#fff" });
      label(ctx, `(${fmt(cs, 3)}, ${fmt(sn, 3)})`, px + (cs >= 0 ? 12 : -12), py - 14, { align: cs >= 0 ? "left" : "right", font: "12px system-ui", halo: "#fff" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
