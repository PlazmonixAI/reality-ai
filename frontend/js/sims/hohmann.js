// Hohmann Transfer: hohmann_transfer gives the burns; propagate_two_body flies the transfer and final orbit.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, View, enablePanZoom, sampleAt, starfield, arrow, label, scaleBar } from "../core/stage.js";
import { Player } from "../core/player.js";
import { fmt, fmtTime } from "../core/format.js";
import { drawPlanet, BODIES } from "./orbits.js";

const AU = 1.495978707e11;
const SUN = { radius: 6.957e8 };
const PRESETS = {
  leo_geo: { label: "LEO → GEO (Earth)", body: "earth", a: 300, b: 35786 },
  leo_moon: { label: "LEO → Moon's distance", body: "earth", a: 300, b: 378022 },
  earth_mars: { label: "Earth → Mars (Sun)", body: "sun", a: 1.0, b: 1.524 },
  earth_venus: { label: "Earth → Venus (Sun)", body: "sun", a: 1.0, b: 0.723 },
  mars_low_high: { label: "Low → high Mars orbit", body: "mars", a: 250, b: 17000 },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => { if (autoFit) fitView(); draw(); } });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let data = null;
    let simTime = 0;
    let autoFit = true;

    const preset = select({ label: "Scenario", value: "leo_geo", options: [...Object.entries(PRESETS).map(([value, p]) => ({ value, label: p.label })), { value: "custom", label: "Custom" }], onChange: applyPreset });
    const body = select({ label: "Central body", value: "earth", options: [
      { value: "earth", label: "Earth" }, { value: "moon", label: "Moon" }, { value: "mars", label: "Mars" }, { value: "sun", label: "Sun" },
    ], onChange: () => { preset.set("custom"); setRanges(); recompute(); } });
    const r1 = slider({ label: "Initial orbit", min: 160, max: 400000, value: 300, log: true, onInput: () => { preset.set("custom"); recompute(); } });
    const r2 = slider({ label: "Target orbit", min: 160, max: 400000, value: 35786, log: true, onInput: () => { preset.set("custom"); recompute(); } });
    const out = readouts([
      { key: "dv1", label: "Burn 1 (departure)" }, { key: "dv2", label: "Burn 2 (arrival)" }, { key: "dv", label: "Total Δv" },
      { key: "tt", label: "Transfer time" }, { key: "e", label: "Transfer eccentricity" }, { key: "dir", label: "Burns" },
    ]);
    const phase = el("p", { class: "note" });

    function isSun() { return body.value === "sun"; }
    function unitLabel() { return isSun() ? "AU (radius)" : "km (altitude)"; }
    function setRanges() {
      const fmtR = (v) => `${fmt(v, 4)} ${isSun() ? "AU" : "km"}`;
      for (const s of [r1, r2]) {
        if (isSun()) s.setRange(0.3, 10); else s.setRange(150, body.value === "earth" ? 400000 : 60000);
        s.root.querySelector("label").textContent = `${s === r1 ? "Initial" : "Target"} orbit, ${unitLabel()}`;
      }
      r1.set(r1.value); r2.set(r2.value);
      void fmtR;
    }
    function applyPreset(key) {
      if (key === "custom") return;
      const p = PRESETS[key];
      body.set(p.body); setRanges(); r1.set(p.a); r2.set(p.b); recompute();
    }
    function radius(v) { return isSun() ? v * AU : BODIES[body.value].radius + v * 1000; }

    L.side.append(
      panel("Mission", preset.root, body.root, r1.root, r2.root),
      panel("Manoeuvre (from the engine)", out.root, phase),
      panel("View", button("Fit view", () => { autoFit = true; fitView(); draw(); }), el("p", { class: "note" }, "Scroll to zoom, drag to pan. Planet sizes are to scale (min. a few pixels).")),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); }, { speeds: [0.25, 0.5, 1, 2, 4] });
    enablePanZoom(stage.canvas, view, () => { autoFit = false; draw(); });

    const recompute = liveRequest(async (signal) => {
      const a = radius(r1.value), b = radius(r2.value);
      const common = isSun() ? { body: "sun" } : { body: body.value };
      const h = await simulate("physics", "hohmann_transfer", { r1: a, r2: b, ...common }, signal);
      const v1 = h.circular_speeds.initial, vDep = v1 + (b > a ? 1 : -1) * h.result.delta_v1;
      const tt = h.result.transfer_time;
      const periodFinal = 2 * Math.PI * b / h.circular_speeds.final;
      const periodInit = 2 * Math.PI * a / v1;
      const [coast, transfer] = await Promise.all([
        // Before the burn: half an orbit on the initial circle ending at (a, 0).
        simulate("physics", "propagate_two_body", { position: [-a, 0, 0], velocity: [0, -v1, 0], duration: periodInit / 2, n_points: 200, ...common }, signal),
        simulate("physics", "propagate_two_body", { position: [a, 0, 0], velocity: [0, vDep, 0], duration: tt, n_points: 500, ...common }, signal),
      ]);
      const arr = transfer.result.final_position;
      const vf = h.circular_speeds.final;
      const after = await simulate("physics", "propagate_two_body", { position: arr, velocity: [0, Math.sign(arr[0]) * vf, 0], duration: periodFinal * 0.5, n_points: 300, ...common }, signal);
      return { h, a, b, coast, transfer, after };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (d) => {
        L.clearError();
        const t0 = d.coast.result.final_time, t1 = t0 + d.transfer.result.final_time, t2 = t1 + d.after.result.final_time;
        data = { ...d, t0, t1, t2 };
        const r = d.h.result;
        out.set("dv1", `${fmt(r.delta_v1, 5)} m/s`); out.set("dv2", `${fmt(r.delta_v2, 5)} m/s`);
        out.set("dv", `${fmt(r.delta_v_total, 5)} m/s`); out.set("tt", fmtTime(r.transfer_time));
        out.set("e", fmt(d.h.transfer_orbit.eccentricity, 4)); out.set("dir", d.h.burn_direction);
        if (autoFit) fitView();
        player.load(t2, 14);
      },
    });

    function fitView() {
      const { width: w, height: h } = stage;
      const R = data ? Math.max(data.a, data.b) * 1.1 : 5e7;
      view.fit(-R, R, -R, R, w || 1, h || 1, { pad: 0.05 });
    }

    const seg = (res, tOff, tNow, color, width = 2.5) => {
      const tr = res.trajectory;
      stage.ctx.strokeStyle = color; stage.ctx.lineWidth = width; stage.ctx.beginPath();
      for (let i = 0; i < tr.t.length && tr.t[i] + tOff <= tNow; i++) {
        const X = view.x(tr.x[i]), Y = view.y(tr.y[i]);
        if (i) stage.ctx.lineTo(X, Y); else stage.ctx.moveTo(X, Y);
      }
      stage.ctx.stroke();
    };

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      starfield(ctx, w, h, 11);
      if (isSun()) {
        const r = Math.max(8, view.len(SUN.radius));
        const g = ctx.createRadialGradient(view.x(0), view.y(0), 1, view.x(0), view.y(0), r * 2.2);
        g.addColorStop(0, "#fff6c9"); g.addColorStop(0.45, "#ffb347"); g.addColorStop(1, "rgba(255,120,0,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(view.x(0), view.y(0), r * 2.2, 0, Math.PI * 2); ctx.fill();
      } else drawPlanet(ctx, view, body.value, 0, 0, 5);
      if (!data) return;
      // Orbit circles
      ctx.setLineDash([5, 6]); ctx.lineWidth = 1.5;
      for (const [r, c] of [[data.a, "rgba(134,182,239,.6)"], [data.b, "rgba(27,175,122,.7)"]]) {
        ctx.strokeStyle = c; ctx.beginPath(); ctx.arc(view.x(0), view.y(0), view.len(r), 0, Math.PI * 2); ctx.stroke();
      }
      // Full transfer ellipse (faint)
      ctx.strokeStyle = "rgba(235,104,52,.35)"; ctx.beginPath();
      const tr = data.transfer.trajectory;
      tr.x.forEach((x, i) => (i ? ctx.lineTo(view.x(x), view.y(tr.y[i])) : ctx.moveTo(view.x(x), view.y(tr.y[i]))));
      ctx.stroke(); ctx.setLineDash([]);

      seg(data.coast, 0, simTime, c1);
      if (simTime > data.t0) seg(data.transfer, data.t0, simTime, c2, 3);
      if (simTime > data.t1) seg(data.after, data.t1, simTime, c3);

      // Burn markers
      const burn = (x, y, txt) => {
        ctx.fillStyle = "#eda100"; ctx.beginPath(); ctx.arc(view.x(x), view.y(y), 5, 0, Math.PI * 2); ctx.fill();
        label(ctx, txt, view.x(x) + 9, view.y(y) + 14, { color: "#ffd479", font: "bold 12px system-ui" });
      };
      const r = data.h.result;
      burn(data.a, 0, `Δv₁ = ${fmt(r.delta_v1, 4)} m/s`);
      const fp = data.transfer.result.final_position;
      burn(fp[0], fp[1], `Δv₂ = ${fmt(r.delta_v2, 4)} m/s`);

      // Spacecraft
      let res, tl;
      if (simTime <= data.t0) { res = data.coast; tl = simTime; phase.textContent = "Coasting in the initial orbit"; }
      else if (simTime <= data.t1) { res = data.transfer; tl = simTime - data.t0; phase.textContent = "On the transfer ellipse (engine off)"; }
      else { res = data.after; tl = simTime - data.t1; phase.textContent = "Circularised in the target orbit"; }
      const t = res.trajectory;
      const x = sampleAt(t.t, t.x, tl), y = sampleAt(t.t, t.y, tl), vx = sampleAt(t.t, t.vx, tl), vy = sampleAt(t.t, t.vy, tl);
      const X = view.x(x), Y = view.y(y), vm = Math.hypot(vx, vy);
      const nearBurn = Math.abs(simTime - data.t0) < data.t2 * 0.012 || Math.abs(simTime - data.t1) < data.t2 * 0.012;
      if (nearBurn) arrow(ctx, X, Y, X + (vx / vm) * 36 * (data.b > data.a ? 1 : -1), Y - (vy / vm) * 36 * (data.b > data.a ? 1 : -1), "#eda100", 3, 10);
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(X, Y, 5, 0, Math.PI * 2); ctx.fill();
      scaleBar(ctx, view, h, isSun() ? { unit: "AU", divisor: AU, color: "rgba(255,255,255,.8)" } : { unit: "km", divisor: 1000, color: "rgba(255,255,255,.8)" });
      label(ctx, `Mission time ${fmtTime(simTime)}`, 14, 20, { color: "#fff", font: "13px system-ui" });
    }

    setRanges();
    recompute();
    return () => { recompute.cancel(); player.destroy(); stage.destroy(); };
  },
};
