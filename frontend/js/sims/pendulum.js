// Pendulum Lab: physics.pendulum integrates the full nonlinear equation and gives the exact period.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, sampleAt, indexAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtUnit } from "../core/format.js";
import { drawEnergyBars } from "./energy_bars.js";

const GRAVITY = { earth: ["Earth", 9.80665], moon: ["Moon", 1.62], mars: ["Mars", 3.71], jupiter: ["Jupiter", 24.79] };
const DURATION = 20;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let data = null, simTime = 0, dragging = false, dragAngle = 0;

    const length = slider({ label: "Length", min: 0.1, max: 2, step: 0.01, value: 1, unit: "m", onInput: () => recompute() });
    const mass = slider({ label: "Mass", min: 0.1, max: 1.5, step: 0.01, value: 0.5, unit: "kg", onInput: () => recompute() });
    const angle = slider({ label: "Release angle", min: -170, max: 170, step: 1, value: 30, unit: "°", onInput: () => recompute() });
    const damping = slider({ label: "Friction (damping)", min: 0, max: 0.5, step: 0.005, value: 0, unit: "kg/s", onInput: () => recompute() });
    const gravity = select({ label: "Gravity", value: "earth", options: Object.entries(GRAVITY).map(([value, [lbl, g]]) => ({ value, label: `${lbl} (${g} m/s²)` })), onChange: () => recompute() });
    const out = readouts([
      { key: "period", label: "Period (exact)" }, { key: "small", label: "Small-angle 2π√(L/g)" }, { key: "ratio", label: "Ratio" },
      { key: "motion", label: "Motion" }, { key: "vmax", label: "Max speed" },
    ]);
    L.side.append(
      panel("Pendulum", length.root, mass.root, angle.root, damping.root, gravity.root, el("p", { class: "note" }, "Drag the bob to set the release angle.")),
      panel("Period (from the engine)", out.root, el("p", { class: "note" }, "The exact period uses an elliptic integral; it grows beyond the small-angle value as the amplitude increases.")),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "Angle", xLabel: "time (s)", yLabel: "θ (°)", height: 140 });

    const recompute = liveRequest((signal) => simulate("physics", "pendulum", {
      length: length.value, mass: mass.value, initial_angle_deg: angle.value, damping: damping.value,
      gravity: GRAVITY[gravity.value][1], duration: DURATION, n_points: 2001,
    }, signal), {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (res) => {
        L.clearError(); data = res;
        const r = res.result;
        out.set("period", r.period ? fmtUnit(r.period, "s") : "—");
        out.set("small", fmtUnit(r.small_angle_period, "s"));
        out.set("ratio", r.period_ratio ? `${fmt(r.period_ratio, 5)}×` : "—");
        out.set("motion", r.motion); out.set("vmax", fmtUnit(r.max_speed, "m/s"));
        graph.setSeries([{ name: "θ", color: c1, x: res.trajectory.t, y: res.trajectory.theta_deg }]);
        player.load(DURATION, DURATION);
      },
    });

    const bobPos = () => {
      if (dragging || !data) { const a = ((dragging ? dragAngle : angle.value) * Math.PI) / 180; return [length.value * Math.sin(a), -length.value * Math.cos(a)]; }
      const tr = data.trajectory;
      return [sampleAt(tr.t, tr.x, simTime), sampleAt(tr.t, tr.y, simTime)];
    };
    stage.canvas.addEventListener("pointerdown", (e) => {
      const r = stage.canvas.getBoundingClientRect();
      const [wx, wy] = view.toWorld(e.clientX - r.left, e.clientY - r.top);
      const [bx, by] = bobPos();
      if (Math.hypot(wx - bx, wy - by) < Math.max(0.08, 25 / view.scale)) { dragging = true; player.pause(); stage.canvas.setPointerCapture(e.pointerId); }
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const r = stage.canvas.getBoundingClientRect();
      const [wx, wy] = view.toWorld(e.clientX - r.left, e.clientY - r.top);
      dragAngle = Math.max(-170, Math.min(170, Math.round((Math.atan2(wx, -wy) * 180) / Math.PI)));
      angle.set(dragAngle); draw();
    });
    stage.canvas.addEventListener("pointerup", () => { if (dragging) { dragging = false; recompute(); } });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, "#faf6ee"); bg.addColorStop(1, "#efe6d6");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      // Fixed scale (so length changes are visible); leave room above the pivot only for big swings.
      const amp = Math.abs(dragging ? dragAngle : angle.value) * Math.PI / 180;
      const above = 0.25 + Math.max(0, -Math.cos(amp)) * length.value;
      view.fit(-2.7, 2.2, -2.15, above, w, h, { pad: 0.03 });
      const px = view.x(0), py = view.y(0);

      // Protractor
      ctx.strokeStyle = "rgba(75,88,104,.35)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(px, py, view.len(0.35), 0, Math.PI); ctx.stroke();
      for (let d = -90; d <= 90; d += 10) {
        const a = (d * Math.PI) / 180, r1 = view.len(0.35), r2 = view.len(d % 30 ? 0.32 : 0.29);
        ctx.beginPath(); ctx.moveTo(px + Math.sin(a) * r1, py + Math.cos(a) * r1); ctx.lineTo(px + Math.sin(a) * r2, py + Math.cos(a) * r2); ctx.stroke();
      }
      ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, view.y(-length.value - 0.15)); ctx.stroke(); ctx.setLineDash([]);

      // Trail (last 1.5 s)
      if (data && !dragging) {
        const tr = data.trajectory, i1 = indexAt(tr.t, simTime), i0 = indexAt(tr.t, Math.max(0, simTime - 1.5));
        for (let i = i0 + 1; i <= i1; i++) {
          ctx.strokeStyle = `rgba(42,120,214,${(0.6 * (i - i0)) / Math.max(1, i1 - i0)})`; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.moveTo(view.x(tr.x[i - 1]), view.y(tr.y[i - 1])); ctx.lineTo(view.x(tr.x[i]), view.y(tr.y[i])); ctx.stroke();
        }
      }

      // Rod, pivot, bob
      const [bx, by] = bobPos();
      ctx.fillStyle = "#7b8796"; ctx.fillRect(px - 60, py - 10, 120, 10);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(view.x(bx), view.y(by)); ctx.stroke();
      ctx.fillStyle = "#39424e"; ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.fill();
      const br = 10 + 10 * Math.cbrt(mass.value);
      ctx.fillStyle = dragging ? "#c14f22" : c2; ctx.beginPath(); ctx.arc(view.x(bx), view.y(by), br, 0, Math.PI * 2); ctx.fill();
      const th = (Math.atan2(bx, -by) * 180) / Math.PI;
      label(ctx, `θ = ${fmt(th, 3)}°`, 14, 20, { font: "13px system-ui" });

      if (data) {
        const tr = data.trajectory;
        const g = GRAVITY[gravity.value][1];
        const pe = dragging ? mass.value * g * length.value * (1 - Math.cos((dragAngle * Math.PI) / 180)) : sampleAt(tr.t, tr.potential, simTime);
        const ke = dragging ? 0 : sampleAt(tr.t, tr.kinetic, simTime);
        const e0 = tr.kinetic[0] + tr.potential[0];
        const thermal = dragging ? 0 : Math.max(0, e0 - ke - pe);
        drawEnergyBars(ctx, [
          { name: "Kinetic", value: ke, color: c1 }, { name: "Potential", value: pe, color: c2 },
          { name: "Thermal", value: thermal, color: c3 }, { name: "Total", value: ke + pe + thermal, color: "#7b8796" },
        ], Math.max(e0, pe, 1e-9) * 1.05, w - 230, 16, 214, Math.min(260, h - 32));
      }
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
