// Gravity & Orbits: escape/circular speeds, state_to_elements and propagate_two_body from the engine.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, button, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, enablePanZoom, sampleAt, starfield, arrow, label, scaleBar } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime, fmtDistance } from "../core/format.js";

export const BODIES = {
  earth: { label: "Earth", radius: 6.378137e6, colors: ["#5aa9ff", "#1c5cab"], land: "#3aa55a" },
  moon: { label: "Moon", radius: 1.7374e6, colors: ["#e4e6ea", "#8d939c"] },
  mars: { label: "Mars", radius: 3.3962e6, colors: ["#f08a5d", "#9c3f1b"] },
  jupiter: { label: "Jupiter", radius: 7.1492e7, colors: ["#e9c79b", "#a8805a"] },
};

export function drawPlanet(ctx, view, key, x = 0, y = 0, minPx = 6) {
  const b = BODIES[key];
  const r = Math.max(minPx, view.len(b.radius));
  const cx = view.x(x), cy = view.y(y);
  const g = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.35, r * 0.1, cx, cy, r);
  g.addColorStop(0, b.colors[0]); g.addColorStop(1, b.colors[1]);
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
  if (b.land && r > 14) {
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = b.land; ctx.globalAlpha = 0.8;
    ctx.beginPath(); ctx.ellipse(cx - r * 0.3, cy - r * 0.2, r * 0.35, r * 0.22, 0.6, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(cx + r * 0.35, cy + r * 0.3, r * 0.25, r * 0.3, -0.4, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
  if (key === "jupiter" && r > 10) {
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = "rgba(140,90,50,.35)";
    for (const f of [-0.45, -0.1, 0.3]) ctx.fillRect(cx - r, cy + f * r, 2 * r, r * 0.12);
    ctx.restore();
  }
  return r;
}

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => { if (autoFit) fitView(); draw(); } });
    const view = new View();
    let data = null;      // {traj, elements, res, r0}
    let simTime = 0;
    let autoFit = true;
    const [c1, c2] = SERIES();

    const body = select({ label: "Planet", value: "earth", options: Object.entries(BODIES).map(([value, b]) => ({ value, label: b.label })), onChange: () => { setAltRange(); recompute(); } });
    const alt = slider({ label: "Launch altitude", min: 100, max: 60000, value: 400, log: true, unit: "km", onInput: () => recompute() });
    const speed = slider({ label: "Launch speed", min: 100, max: 16000, step: 1, value: 7669, unit: "m/s", digits: 5, onInput: () => recompute() });
    const fpa = slider({ label: "Flight-path angle (above horizontal)", min: -60, max: 60, step: 1, value: 0, unit: "°", onInput: () => recompute() });
    let speeds = { circ: null, esc: null };
    let first = true;
    const circBtn = button("Circular speed", () => { if (speeds.circ) { speed.set(speeds.circ); fpa.set(0); recompute(); } });
    const escBtn = button("Escape speed", () => { if (speeds.esc) { speed.set(speeds.esc * 1.0001); recompute(); } });
    const out = readouts([
      { key: "type", label: "Orbit" }, { key: "peri", label: "Periapsis altitude" }, { key: "apo", label: "Apoapsis altitude" },
      { key: "ecc", label: "Eccentricity" }, { key: "period", label: "Period" }, { key: "circ", label: "Circular speed here" },
      { key: "esc", label: "Escape speed here" },
    ]);
    const live = readouts([{ key: "t", label: "Time" }, { key: "alt", label: "Altitude" }, { key: "v", label: "Speed" }]);
    const resetView = button("Fit view", () => { autoFit = true; fitView(); draw(); });

    function setAltRange() {
      const R = BODIES[body.value].radius / 1000;
      alt.setRange(Math.min(100, R * 0.05), R * 12);
    }

    L.side.append(
      panel("Launch", body.root, alt.root, speed.root, el("div", { class: "btn-row control" }, circBtn, escBtn), fpa.root),
      panel("Orbit (from the engine)", out.root),
      panel("Now", live.root, el("p", { class: "note" }, "Scroll to zoom, drag to pan."), resetView),
    );

    const player = new Player(L.bottom, (t) => { simTime = t; draw(); updateGraph(); }, { speeds: [0.25, 0.5, 1, 2, 4] });
    const graph = new LineGraph(L.bottom, { title: "Altitude over time", xLabel: "time (h)", yLabel: "altitude (km)", height: 150 });

    enablePanZoom(stage.canvas, view, () => { autoFit = false; draw(); });

    const recompute = liveRequest(async (signal) => {
      const b = body.value, R = BODIES[b].radius, altitude = alt.value * 1000;
      const [esc, circ] = await Promise.all([
        simulate("physics", "escape_velocity", { altitude, body: b }, signal),
        simulate("physics", "circular_velocity", { altitude, body: b }, signal),
      ]);
      const r0 = R + altitude, v = speed.value, g = (fpa.value * Math.PI) / 180;
      const position = [r0, 0, 0], velocity = [v * Math.sin(g), v * Math.cos(g), 0];
      const elements = await simulate("physics", "state_to_elements", { position, velocity, body: b }, signal);
      const duration = elements.period ? elements.period * 1.02 : Math.min(40 * r0 / v, 30 * 86400);
      const res = await simulate("physics", "propagate_two_body", { position, velocity, duration, n_points: 900, body: b }, signal);
      return { esc: esc.result, circ: circ.result, elements, res, r0 };
    }, {
      onBusy: L.busy,
      onError: (e) => L.error(e.message),
      onResult: (d) => {
        L.clearError();
        speeds = { circ: d.circ, esc: d.esc };
        speed.setRange(100, Math.max(1000, Math.ceil(d.esc * 1.5)));
        if (first) { first = false; speed.set(d.circ); recompute(); return; }
        const R = BODIES[body.value].radius;
        data = { traj: d.res.trajectory, elements: d.elements, res: d.res.result, r0: d.r0, R };
        const e = d.elements;
        const kind = d.res.result.impact ? "Crashes into the surface" : e.orbit_type[0].toUpperCase() + e.orbit_type.slice(1);
        out.set("type", kind);
        out.set("peri", fmtDistance(e.periapsis_radius - R));
        out.set("apo", e.apoapsis_radius ? fmtDistance(e.apoapsis_radius - R) : "∞ (escapes)");
        out.set("ecc", fmt(e.result.eccentricity, 4));
        out.set("period", e.period ? fmtTime(e.period) : "— (unbound)");
        out.set("circ", `${fmt(d.circ, 5)} m/s`); out.set("esc", `${fmt(d.esc, 5)} m/s`);
        const hours = data.traj.t.map((t) => t / 3600);
        graph.setSeries([{ name: "Altitude", color: c1, x: hours, y: data.traj.x.map((x, i) => (Math.hypot(x, data.traj.y[i]) - R) / 1000) }]);
        if (autoFit) fitView();
        player.load(d.res.result.final_time, 12);
      },
    });

    function fitView() {
      const { width: w, height: h } = stage;
      if (!data || !w) { view.fit(-2e7, 2e7, -2e7, 2e7, w || 1, h || 1); return; }
      const xs = data.traj.x, ys = data.traj.y, R = data.R * 1.15;
      view.fit(Math.min(-R, ...xs), Math.max(R, ...xs), Math.min(-R, ...ys), Math.max(R, ...ys), w, h, { pad: 0.07 });
    }

    function updateGraph() { graph.setCursor(simTime / 3600); }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      starfield(ctx, w, h);
      drawPlanet(ctx, view, body.value, 0, 0, 4);
      if (!data) return;
      const { traj } = data;
      const tEnd = data.res.final_time;
      // Full predicted path (faint), travelled path (bright)
      ctx.lineWidth = 1.5; ctx.strokeStyle = "rgba(134,182,239,.35)"; ctx.setLineDash([5, 5]);
      ctx.beginPath(); traj.x.forEach((x, i) => (i ? ctx.lineTo(view.x(x), view.y(traj.y[i])) : ctx.moveTo(view.x(x), view.y(traj.y[i])))); ctx.stroke();
      ctx.setLineDash([]); ctx.strokeStyle = c1; ctx.lineWidth = 2.5; ctx.beginPath();
      for (let i = 0; i < traj.t.length && traj.t[i] <= simTime; i++) {
        const X = view.x(traj.x[i]), Y = view.y(traj.y[i]);
        if (i) ctx.lineTo(X, Y); else ctx.moveTo(X, Y);
      }
      ctx.stroke();

      // Apsides
      const e = data.elements;
      const w0 = (e.result.arg_periapsis_deg * Math.PI) / 180;
      const mark = (r, txt) => {
        const X = view.x(r * Math.cos(w0) * (txt === "apoapsis" ? -1 : 1)), Y = view.y(r * Math.sin(w0) * (txt === "apoapsis" ? -1 : 1));
        ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(X, Y, 3.5, 0, Math.PI * 2); ctx.fill();
        label(ctx, txt, X + 7, Y - 8, { color: "rgba(255,255,255,.8)", font: "11px system-ui" });
      };
      if (e.result.eccentricity > 0.01) {
        mark(e.periapsis_radius, "periapsis");
        if (e.apoapsis_radius) mark(e.apoapsis_radius, "apoapsis");
      }

      // Spacecraft
      const t = Math.min(simTime, tEnd);
      const x = sampleAt(traj.t, traj.x, t), y = sampleAt(traj.t, traj.y, t);
      const vx = sampleAt(traj.t, traj.vx, t), vy = sampleAt(traj.t, traj.vy, t);
      const X = view.x(x), Y = view.y(y);
      const vmag = Math.hypot(vx, vy);
      arrow(ctx, X, Y, X + (vx / vmag) * 40, Y - (vy / vmag) * 40, c2, 2, 8);
      const crashed = data.res.impact && simTime >= tEnd;
      ctx.fillStyle = crashed ? "#e34948" : "#fff";
      ctx.beginPath(); ctx.arc(X, Y, crashed ? 7 : 5, 0, Math.PI * 2); ctx.fill();
      if (crashed) label(ctx, "Impact!", X + 10, Y, { color: "#ff9a9a", font: "bold 13px system-ui" });
      scaleBar(ctx, view, h, { unit: "km", divisor: 1000, color: "rgba(255,255,255,.8)" });

      const r = Math.hypot(x, y);
      live.set("t", fmtTime(t)); live.set("alt", fmtDistance(r - data.R)); live.set("v", `${fmt(vmag, 5)} m/s`);
    }

    setAltRange();
    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
