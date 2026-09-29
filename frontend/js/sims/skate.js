// Energy Skate Park: physics.skate_track integrates the skater along the spline track.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, sampleAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";
import { drawEnergyBars } from "./energy_bars.js";

const TRACKS = {
  halfpipe: { label: "Half-pipe", pts: [[-4, 4], [-2.5, 1.2], [0, 0.3], [2.5, 1.2], [4, 4]] },
  double: { label: "Double well", pts: [[-4.5, 4.5], [-3, 0.9], [-1.5, 0.5], [0, 2.2], [1.5, 0.5], [3, 0.9], [4.5, 4.5]] },
  steps: { label: "Hill and valley", pts: [[-4.5, 5], [-3, 1.5], [-1.5, 0.4], [0, 1.8], [1.5, 2.6], [3, 1.2], [4.5, 3.5]] },
};
const GRAV = { earth: ["Earth", 9.80665], moon: ["Moon", 1.62], jupiter: ["Jupiter", 24.79] };
const DURATION = 15;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let pts = TRACKS.halfpipe.pts.map((p) => [...p]);
    let start = 0.03, data = null, simTime = 0, drag = null;

    const track = select({ label: "Track", value: "halfpipe", options: Object.entries(TRACKS).map(([v, t]) => ({ value: v, label: t.label })), onChange: (v) => { pts = TRACKS[v].pts.map((p) => [...p]); start = 0.03; recompute(); } });
    const mass = slider({ label: "Skater mass", min: 20, max: 120, step: 1, value: 60, unit: "kg", onInput: () => recompute() });
    const friction = slider({ label: "Friction", min: 0, max: 0.3, step: 0.005, value: 0, onInput: () => recompute() });
    const grav = select({ label: "Gravity", value: "earth", options: Object.entries(GRAV).map(([v, [l, g]]) => ({ value: v, label: `${l} (${g} m/s²)` })), onChange: () => recompute() });
    const out = readouts([{ key: "v", label: "Speed" }, { key: "h", label: "Height" }, { key: "vmax", label: "Top speed" }, { key: "lost", label: "Energy to heat (end)" }]);
    L.side.append(
      panel("Park", track.root, mass.root, friction.root, grav.root, el("p", { class: "note" }, "Drag the white track points to reshape the track. Drag the skater to choose where to start.")),
      panel("Skater (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "Energy", xLabel: "time (s)", yLabel: "energy (J)", height: 140, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "skate_track", {
      track_points: pts, mass: mass.value, start, friction: friction.value, gravity: GRAV[grav.value][1], duration: DURATION, n_points: 901,
    }, signal), {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const tr = r.trajectory;
        out.set("vmax", `${fmt(r.result.max_speed, 3)} m/s`);
        out.set("lost", `${fmt(r.result.energy_dissipated, 4)} J`);
        graph.setSeries([
          { name: "Kinetic", color: c1, x: tr.t, y: tr.kinetic },
          { name: "Potential", color: c2, x: tr.t, y: tr.potential },
          { name: "Thermal", color: c3, x: tr.t, y: tr.thermal },
        ]);
        if (!drag) player.load(DURATION, DURATION);
      },
    });

    const world = (e) => { const r = stage.canvas.getBoundingClientRect(); return view.toWorld(e.clientX - r.left, e.clientY - r.top); };
    function skaterPos() {
      if (!data) return null;
      const tr = data.trajectory;
      return [sampleAt(tr.t, tr.x, simTime), sampleAt(tr.t, tr.y, simTime)];
    }
    stage.canvas.addEventListener("pointerdown", (e) => {
      const [wx, wy] = world(e);
      const i = pts.findIndex(([px, py]) => Math.hypot(px - wx, py - wy) < 0.25);
      const sp = skaterPos();
      if (i >= 0) drag = { point: i };
      else if (sp && Math.hypot(sp[0] - wx, sp[1] + 0.35 - wy) < 0.5) drag = { skater: true };
      if (drag) { player.pause(); stage.canvas.setPointerCapture(e.pointerId); }
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const [wx, wy] = world(e);
      if (drag.point !== undefined) {
        const i = drag.point, lo = i > 0 ? pts[i - 1][0] + 0.3 : -5.5, hi = i < pts.length - 1 ? pts[i + 1][0] - 0.3 : 5.5;
        pts[i] = [Math.min(hi, Math.max(lo, wx)), Math.min(7, Math.max(0, wy))];
        track.set(track.value); recompute();
      } else if (data) {
        // Nearest point of the engine's track polyline -> fraction of the way along it.
        const tx = data.track.x, ty = data.track.y;
        let best = 0, bd = Infinity;
        for (let k = 0; k < tx.length; k++) { const d = Math.hypot(tx[k] - wx, ty[k] - wy); if (d < bd) { bd = d; best = k; } }
        let total = 0, upto = 0;
        for (let k = 1; k < tx.length; k++) { const d = Math.hypot(tx[k] - tx[k - 1], ty[k] - ty[k - 1]); total += d; if (k <= best) upto += d; }
        start = Math.min(1, Math.max(0, upto / total));
        player.seek(0);
        data.trajectory.x[0] = tx[best]; data.trajectory.y[0] = ty[best];
      }
      draw();
    });
    stage.canvas.addEventListener("pointerup", () => { if (drag) { drag = null; recompute(); } });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      view.fit(-5.5, 5.5, -0.3, 7, w, h, { pad: 0.02 });
      const sky = ctx.createLinearGradient(0, 0, 0, h); sky.addColorStop(0, "#bfe3ff"); sky.addColorStop(1, "#eef7ff");
      ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#6cbf5b"; ctx.fillRect(0, view.y(0), w, h - view.y(0));
      // Height grid
      for (let y = 1; y <= 7; y++) {
        ctx.strokeStyle = "rgba(255,255,255,.7)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(0, view.y(y)); ctx.lineTo(w, view.y(y)); ctx.stroke();
        label(ctx, `${y} m`, 8, view.y(y) - 8, { font: "11px system-ui", color: "#4b5868" });
      }
      if (data) {
        const tx = data.track.x, ty = data.track.y;
        ctx.strokeStyle = "#7b5a3a"; ctx.lineWidth = 7; ctx.lineJoin = "round";
        ctx.beginPath(); tx.forEach((x, k) => (k ? ctx.lineTo(view.x(x), view.y(ty[k])) : ctx.moveTo(view.x(x), view.y(ty[k])))); ctx.stroke();
        ctx.strokeStyle = "#b58b5f"; ctx.lineWidth = 3; ctx.stroke();
        ctx.fillStyle = "rgba(123,90,58,.5)";
        for (let k = 0; k < tx.length; k += 25) ctx.fillRect(view.x(tx[k]) - 2, view.y(ty[k]), 4, view.y(0) - view.y(ty[k]));
      }
      for (const [px, py] of pts) {
        ctx.fillStyle = "#fff"; ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(view.x(px), view.y(py), 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      }
      const sp = skaterPos();
      if (sp) {
        const [x, y] = sp, X = view.x(x), Y = view.y(y);
        ctx.fillStyle = "#eb6834"; ctx.beginPath(); ctx.arc(X, Y - 26, 9, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#2a78d6"; ctx.beginPath(); ctx.roundRect(X - 8, Y - 18, 16, 16, 4); ctx.fill();
        ctx.fillStyle = "#39424e"; ctx.fillRect(X - 14, Y - 3, 28, 4);
        const tr = data.trajectory;
        const ke = sampleAt(tr.t, tr.kinetic, simTime), pe = sampleAt(tr.t, tr.potential, simTime), th = sampleAt(tr.t, tr.thermal, simTime);
        out.set("v", `${fmt(sampleAt(tr.t, tr.speed, simTime), 3)} m/s`); out.set("h", `${fmt(y, 3)} m`);
        drawEnergyBars(ctx, [
          { name: "Kinetic", value: ke, color: c1 }, { name: "Potential", value: pe, color: c2 },
          { name: "Thermal", value: th, color: c3 }, { name: "Total", value: ke + pe + th, color: "#7b8796" },
        ], (tr.kinetic[0] + tr.potential[0]) * 1.05, w - 230, 14, 214, Math.min(240, h - 28));
      }
      label(ctx, `t = ${fmt(simTime, 3)} s`, 14, 18, { font: "13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
