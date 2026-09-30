// Earth–Moon Voyage: propagate_n_body with the earth_moon preset computes all three bodies.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, segmented, button, SERIES } from "../core/ui.js";
import { createStage, View, enablePanZoom, indexAt, starfield, label, scaleBar } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";
import { drawPlanet } from "./orbits.js";

const R_EARTH = 6.378137e6, R_MOON = 1.7374e6;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => { if (autoFit) fitView(); draw(); } });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let data = null, simTime = 0, autoFit = true;

    const alt = slider({ label: "Parking orbit altitude", min: 150, max: 2000, step: 10, value: 300, unit: "km", onInput: () => recompute() });
    const speed = slider({ label: "Speed after injection burn", min: 9000, max: 11400, step: 1, value: 10842, unit: "m/s", digits: 5, onInput: () => recompute() });
    const phaseAng = slider({ label: "Burn position (angle from Earth–Moon line)", min: 0, max: 360, step: 0.5, value: 235, unit: "°", onInput: () => recompute() });
    const days = slider({ label: "Mission length", min: 1, max: 30, step: 0.5, value: 8, unit: "days", onInput: () => recompute() });
    const frame = segmented({ label: "Frame", value: "rotating", options: [{ value: "inertial", label: "Inertial" }, { value: "rotating", label: "Rotating with Moon" }], onChange: () => { autoFit = true; fitView(); draw(); } });
    const out = readouts([
      { key: "close", label: "Closest to Moon (surface)" }, { key: "when", label: "…at time" },
      { key: "end", label: "Final distance from Earth" }, { key: "hit", label: "Collision" }, { key: "drift", label: "Energy drift" },
    ]);

    L.side.append(
      panel("Trans-lunar injection", alt.root, speed.root, phaseAng.root, days.root,
        el("p", { class: "note" }, "The default (10,842 m/s at 235°) passes ~5,700 km above the Moon on day 3.7 and swings back toward Earth. A few m/s or degrees either way changes everything. Try it.")),
      panel("Display", frame.root, button("Fit view", () => { autoFit = true; fitView(); draw(); })),
      panel("Result (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t / 86400); }, { speeds: [0.25, 0.5, 1, 2, 4] });
    const graph = new LineGraph(L.bottom, { title: "Distances", xLabel: "time (days)", yLabel: "distance (1000 km)", height: 150, includeZero: true });
    enablePanZoom(stage.canvas, view, () => { autoFit = false; draw(); });

    const recompute = liveRequest(async (signal) => {
      const r = R_EARTH + alt.value * 1000, a = (phaseAng.value * Math.PI) / 180, v = speed.value;
      return simulate("physics", "propagate_n_body", {
        preset: "earth_moon", duration: days.value * 86400, n_points: 2000,
        bodies: [{ name: "Spacecraft", mass: 0, position: [r * Math.cos(a), r * Math.sin(a), 0], velocity: [-v * Math.sin(a), v * Math.cos(a), 0] }],
      }, signal);
    }, {
      delay: 200, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (res) => {
        L.clearError();
        const b = res.trajectory.bodies, t = res.trajectory.t;
        const dE = t.map((_, i) => Math.hypot(b.Spacecraft.x[i] - b.Earth.x[i], b.Spacecraft.y[i] - b.Earth.y[i]));
        const dM = t.map((_, i) => Math.hypot(b.Spacecraft.x[i] - b.Moon.x[i], b.Spacecraft.y[i] - b.Moon.y[i]));
        let k = 0; dM.forEach((d, i) => { if (d < dM[k]) k = i; });
        data = { t, b, dE, dM, res: res.result };
        out.set("close", `${fmt((dM[k] - R_MOON) / 1000, 4)} km`); out.set("when", fmtTime(t[k]));
        out.set("end", `${fmt(dE[dE.length - 1] / 1000, 4)} km`);
        out.set("hit", res.result.collision ? `Yes, at ${fmtTime(res.result.final_time)}` : "None");
        out.set("drift", res.relative_energy_drift != null ? fmt(res.relative_energy_drift, 2) : "–");
        const days = t.map((x) => x / 86400);
        graph.setSeries([
          { name: "to Earth", color: c1, x: days, y: dE.map((d) => d / 1e6) },
          { name: "to Moon", color: c2, x: days, y: dM.map((d) => d / 1e6), dash: true },
        ]);
        if (autoFit) fitView();
        player.load(res.result.final_time, 14);
      },
    });

    // Transform to the chosen frame: rotating frame keeps the Earth–Moon line on the x-axis.
    function framed(i) {
      const b = data.b;
      const pts = { E: [b.Earth.x[i], b.Earth.y[i]], M: [b.Moon.x[i], b.Moon.y[i]], S: [b.Spacecraft.x[i], b.Spacecraft.y[i]] };
      if (frame.value === "inertial") return pts;
      const th = Math.atan2(pts.M[1] - pts.E[1], pts.M[0] - pts.E[0]);
      const c = Math.cos(-th), s = Math.sin(-th);
      const rot = ([x, y]) => [x * c - y * s, x * s + y * c];
      return { E: rot(pts.E), M: rot(pts.M), S: rot(pts.S) };
    }

    function fitView() {
      const { width: w, height: h } = stage;
      const R = 4.6e8;
      view.fit(-R * 0.35, R * 1.15, -R * 0.55, R * 0.55, w || 1, h || 1, { pad: 0.04 });
      if (data && frame.value === "inertial") view.fit(-R, R, -R, R, w || 1, h || 1, { pad: 0.04 });
    }

    function path(key, upto, color, width) {
      const { ctx } = stage;
      ctx.strokeStyle = color; ctx.lineWidth = width; ctx.beginPath();
      for (let i = 0; i <= upto; i++) {
        const p = framed(i)[key];
        if (i) ctx.lineTo(view.x(p[0]), view.y(p[1])); else ctx.moveTo(view.x(p[0]), view.y(p[1]));
      }
      ctx.stroke();
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      starfield(ctx, w, h, 23);
      if (!data) return;
      const i = indexAt(data.t, simTime), last = data.t.length - 1;
      ctx.setLineDash([4, 5]); path("S", last, "rgba(235,104,52,.3)", 1.5); ctx.setLineDash([]);
      if (frame.value === "inertial") path("M", i, "rgba(220,224,230,.5)", 1.5);
      path("S", i, c2, 2.5);
      const p = framed(i);
      drawPlanet(ctx, view, "earth", p.E[0], p.E[1], 7);
      drawPlanet(ctx, view, "moon", p.M[0], p.M[1], 4);
      label(ctx, "Earth", view.x(p.E[0]), view.y(p.E[1]) + 20, { color: "#cfe3ff", align: "center", font: "12px system-ui" });
      label(ctx, "Moon", view.x(p.M[0]), view.y(p.M[1]) + 16, { color: "#e4e6ea", align: "center", font: "12px system-ui" });
      const crashed = data.res.collision && i === last;
      ctx.fillStyle = crashed ? "#e34948" : "#fff";
      ctx.beginPath(); ctx.arc(view.x(p.S[0]), view.y(p.S[1]), crashed ? 6 : 4, 0, Math.PI * 2); ctx.fill();
      scaleBar(ctx, view, h, { unit: "km", divisor: 1000, color: "rgba(255,255,255,.8)" });
      label(ctx, `Day ${fmt(simTime / 86400, 3)}`, 14, 20, { color: "#fff", font: "13px system-ui" });
      label(ctx, "Bodies drawn at true size (min. a few px)", w - 14, 20, { color: "rgba(255,255,255,.6)", align: "right", font: "11px system-ui" });
      void c3;
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
