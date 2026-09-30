// Charges & Fields: physics.electric_field gives the field, potential, field lines and probe readings.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, checkbox, segmented, readouts, el, button } from "../core/ui.js";
import { createStage, View, label, arrow } from "../core/stage.js";
import { fmt } from "../core/format.js";

const NEG = [42, 120, 214], POS = [227, 73, 72], MID = [240, 239, 236];   // diverging blue <-> red, grey midpoint

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => { recompute(); draw(); } });
    const view = new View();
    let charges = [{ q: 1, x: -0.6, y: 0 }, { q: -1, x: 0.6, y: 0 }];   // nC, m
    let probe = { x: 0, y: 0.8 };
    let res = null, drag = null, img = null;

    const size = segmented({ label: "New charge size", value: "1", options: [{ value: "1", label: "1 nC" }, { value: "2", label: "2 nC" }, { value: "5", label: "5 nC" }] });
    const add = (s) => () => { charges.push({ q: s * Number(size.value), x: (Math.random() - 0.5) * 1.5, y: (Math.random() - 0.5) * 1 }); recompute(); };
    const showLines = checkbox({ label: "Field lines", value: true, onChange: () => draw() });
    const showVec = checkbox({ label: "Field vectors", value: false, onChange: () => draw() });
    const showV = checkbox({ label: "Voltage map", value: true, onChange: () => draw() });
    const out = readouts([{ key: "e", label: "|E| at sensor" }, { key: "dir", label: "Direction" }, { key: "v", label: "Voltage at sensor" }, { key: "f", label: "Force between the two charges" }]);
    L.side.append(
      panel("Charges", el("div", { class: "btn-row control" }, button("+ Add positive", add(1), "primary"), button("− Add negative", add(-1))), size.root,
        el("div", { class: "btn-row" }, button("Dipole", () => { charges = [{ q: 1, x: -0.6, y: 0 }, { q: -1, x: 0.6, y: 0 }]; recompute(); }),
          button("Like charges", () => { charges = [{ q: 1, x: -0.6, y: 0 }, { q: 1, x: 0.6, y: 0 }]; recompute(); }),
          button("Capacitor", () => { charges = []; for (let i = -4; i <= 4; i++) { charges.push({ q: 1, x: i * 0.2, y: 0.5 }, { q: -1, x: i * 0.2, y: -0.5 }); } recompute(); }),
          button("Clear", () => { charges = []; res = null; draw(); })),
        el("p", { class: "note" }, "Drag charges and the yellow sensor. Double-click a charge to remove it.")),
      panel("Show", showLines.root, showVec.root, showV.root),
      panel("Measurements (from the engine)", out.root),
    );

    function bounds() {
      const { width: w, height: h } = stage;
      const hw = 2, hh = (hw * h) / Math.max(w, 1);
      return [-hw, hw, -hh, hh];
    }

    const recompute = liveRequest(async (signal) => {
      if (!charges.length || !stage.width) return null;
      const [x0, x1, y0, y1] = bounds();
      const main = simulate("physics", "electric_field", {
        charges: charges.map((c) => ({ q: c.q * 1e-9, x: c.x, y: c.y })),
        x_range: [x0, x1], y_range: [y0, y1], grid: 64, lines_per_charge: 14, points: [[probe.x, probe.y]],
      }, signal);
      const force = charges.length === 2 ? simulate("physics", "coulomb_force", {
        q1: charges[0].q * 1e-9, q2: charges[1].q * 1e-9, distance: Math.max(1e-3, Math.hypot(charges[0].x - charges[1].x, charges[0].y - charges[1].y)),
      }, signal) : null;
      return { main: await main, force: force && await force };
    }, {
      delay: 30, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (d) => {
        L.clearError();
        if (!d) { res = null; draw(); return; }
        res = d.main; img = null;
        const p = res.result.probes[0];
        out.set("e", `${fmt(p.magnitude, 4)} N/C`);
        out.set("dir", `${fmt((Math.atan2(p.ey, p.ex) * 180) / Math.PI, 3)}°`);
        out.set("v", `${fmt(p.potential, 4)} V`);
        out.set("f", d.force ? `${fmt(d.force.magnitude, 4)} N (${d.force.nature})` : "needs exactly two");
        draw();
      },
    });

    const world = (e) => { const r = stage.canvas.getBoundingClientRect(); return view.toWorld(e.clientX - r.left, e.clientY - r.top); };
    const hitCharge = (wx, wy) => charges.findIndex((c) => Math.hypot(c.x - wx, c.y - wy) < 14 / view.scale);
    stage.canvas.addEventListener("pointerdown", (e) => {
      const [wx, wy] = world(e);
      if (Math.hypot(probe.x - wx, probe.y - wy) < 14 / view.scale) drag = { probe: true };
      else { const i = hitCharge(wx, wy); if (i >= 0) drag = { i }; }
      if (drag) stage.canvas.setPointerCapture(e.pointerId);
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const [wx, wy] = world(e);
      if (drag.probe) probe = { x: wx, y: wy }; else Object.assign(charges[drag.i], { x: wx, y: wy });
      draw(); recompute();
    });
    stage.canvas.addEventListener("pointerup", () => { drag = null; });
    stage.canvas.addEventListener("dblclick", (e) => {
      const [wx, wy] = world(e); const i = hitCharge(wx, wy);
      if (i >= 0) { charges.splice(i, 1); if (!charges.length) res = null; recompute(); draw(); }
    });

    function colour(v, vmax) {
      const t = Math.sign(v) * Math.log10(1 + Math.abs(v) / 2) / Math.log10(1 + vmax / 2);
      const c = t >= 0 ? POS : NEG, a = Math.min(1, Math.abs(t));
      return MID.map((m, k) => Math.round(m + (c[k] - m) * a));
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const [x0, x1, y0, y1] = bounds();
      view.fit(x0, x1, y0, y1, w, h, { pad: 0 });
      ctx.fillStyle = "#f0efec"; ctx.fillRect(0, 0, w, h);
      if (res && showV.value) {
        const g = res.grid, ny = g.y.length, nx = g.x.length;
        if (!img) {
          const vmax = 8.99 * Math.max(...charges.map((c) => Math.abs(c.q))) * 2;
          const data = new ImageData(nx, ny);
          for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
            const c = colour(g.potential[ny - 1 - j][i], vmax), k = (j * nx + i) * 4;
            data.data[k] = c[0]; data.data[k + 1] = c[1]; data.data[k + 2] = c[2]; data.data[k + 3] = 255;
          }
          img = new OffscreenCanvas(nx, ny); img.getContext("2d").putImageData(data, 0, 0);
        }
        ctx.imageSmoothingEnabled = true; ctx.drawImage(img, 0, 0, w, h);
      }
      if (res && showVec.value) {
        const g = res.grid;
        for (let j = 1; j < g.y.length; j += 3) for (let i = 1; i < g.x.length; i += 3) {
          const ex = g.ex[j][i], ey = g.ey[j][i], m = Math.hypot(ex, ey);
          if (!m) continue;
          const len = Math.min(22, 4 + 5 * Math.log10(1 + m));
          const X = view.x(g.x[i]), Y = view.y(g.y[j]);
          arrow(ctx, X, Y, X + (ex / m) * len, Y - (ey / m) * len, `rgba(22,32,44,${Math.min(0.9, 0.2 + m / 60)})`, 1.2, 5);
        }
      }
      if (res && showLines.value) {
        ctx.strokeStyle = "rgba(22,32,44,.7)"; ctx.lineWidth = 1.3;
        for (const line of res.field_lines) {
          ctx.beginPath(); line.forEach(([x, y], i) => (i ? ctx.lineTo(view.x(x), view.y(y)) : ctx.moveTo(view.x(x), view.y(y)))); ctx.stroke();
          const k = Math.floor(line.length / 2);
          if (line.length > 4) {
            const sign = res.result.net_charge >= 0 ? 1 : -1;
            const [ax, ay] = line[k], [bx, by] = line[k + sign];
            arrow(ctx, view.x(ax), view.y(ay), view.x(bx), view.y(by), "rgba(22,32,44,.8)", 1.3, 7);
          }
        }
      }
      for (const c of charges) {
        const X = view.x(c.x), Y = view.y(c.y), r = 10 + 2 * Math.abs(c.q);
        ctx.fillStyle = c.q > 0 ? "#e34948" : "#2a78d6"; ctx.strokeStyle = "#fff"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(X, Y, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        label(ctx, c.q > 0 ? "+" : "−", X, Y + 1, { align: "center", color: "#fff", font: "bold 16px system-ui" });
      }
      // Sensor
      const PX = view.x(probe.x), PY = view.y(probe.y);
      if (res) {
        const p = res.result.probes[0], m = Math.hypot(p.ex, p.ey);
        if (m) arrow(ctx, PX, PY, PX + (p.ex / m) * 50, PY - (p.ey / m) * 50, "#eda100", 3, 10);
        label(ctx, `${fmt(p.magnitude, 3)} N/C · ${fmt(p.potential, 3)} V`, PX + 14, PY + 18, { font: "bold 12px system-ui", halo: "rgba(255,255,255,.85)" });
      }
      ctx.fillStyle = "#eda100"; ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(PX, PY, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      label(ctx, "1 m", view.x(x0 + 0.1) + view.len(0.5), h - 22, { align: "center", font: "11px system-ui", color: "#4b5868" });
      ctx.strokeStyle = "#4b5868"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(view.x(x0 + 0.1), h - 12); ctx.lineTo(view.x(x0 + 1.1), h - 12); ctx.stroke();
      if (showV.value) label(ctx, "red = positive voltage · blue = negative", w - 12, h - 14, { align: "right", font: "11px system-ui", color: "#4b5868" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
