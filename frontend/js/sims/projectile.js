// Projectile Motion: physics.projectile_motion computes every trajectory; this file draws and animates it.
import { simulate } from "../core/api.js";
import { simLayout, panel, slider, select, checkbox, button, readouts, el } from "../core/ui.js";
import { createStage, View, sampleAt, label, niceStep, arrow } from "../core/stage.js";
import { Player } from "../core/player.js";
import { fmtUnit, fmt } from "../core/format.js";

const OBJECTS = {
  cannonball: { label: "Cannonball", mass: 17.6, diameter: 0.18, cd: 0.47, color: "#39424e" },
  baseball: { label: "Baseball", mass: 0.145, diameter: 0.074, cd: 0.35, color: "#f4f1ea" },
  golf: { label: "Golf ball", mass: 0.0459, diameter: 0.0427, cd: 0.25, color: "#ffffff" },
  pumpkin: { label: "Pumpkin", mass: 5, diameter: 0.37, cd: 0.6, color: "#eb6834" },
  football: { label: "Football (soccer)", mass: 0.43, diameter: 0.22, cd: 0.25, color: "#ffffff" },
};
const WORLDS = {
  earth: { label: "Earth", g: 9.80665, rho: 1.225, sky: ["#9fd3ff", "#e3f3ff"], ground: "#6cbf5b" },
  moon: { label: "Moon", g: 1.62, rho: 0, sky: ["#0b1024", "#26304a"], ground: "#9aa0a8" },
  mars: { label: "Mars", g: 3.71, rho: 0.020, sky: ["#d9a17a", "#f3d3b8"], ground: "#b5643c" },
  jupiter: { label: "Jupiter (no surface!)", g: 24.79, rho: 0.16, sky: ["#d8b58a", "#f1dfc6"], ground: "#a8805a" },
};
const MAX_SHOTS = 5;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    let shots = [];       // [{traj, result, obj, color}]
    let current = null;   // shot being animated
    let simTime = 0;

    const angle = slider({ label: "Launch angle", min: 0, max: 90, step: 1, value: 45, unit: "°", digits: 3, onInput: draw });
    const speed = slider({ label: "Initial speed", min: 1, max: 100, step: 0.5, value: 20, unit: "m/s", onInput: draw });
    const height = slider({ label: "Launch height", min: 0, max: 30, step: 0.5, value: 0, unit: "m", onInput: draw });
    const object = select({ label: "Projectile", value: "cannonball", options: Object.entries(OBJECTS).map(([value, o]) => ({ value, label: o.label })) });
    const world = select({ label: "World", value: "earth", options: Object.entries(WORLDS).map(([value, w]) => ({ value, label: w.label })), onChange: () => { refreshDragAvail(); draw(); } });
    const drag = checkbox({ label: "Air resistance" });
    const out = readouts([
      { key: "range", label: "Range" }, { key: "hmax", label: "Max height" },
      { key: "time", label: "Flight time" }, { key: "vimp", label: "Impact speed" },
      { key: "vt", label: "Terminal velocity" },
    ]);
    const fire = button("Fire!", () => launch(), "primary big");
    const erase = button("Erase", () => { shots = []; current = null; out.clear(); draw(); });
    const dragNote = el("p", { class: "note" });

    function refreshDragAvail() {
      const rho = WORLDS[world.value].rho;
      drag.root.style.opacity = rho ? 1 : 0.5;
      drag.root.querySelector("input").disabled = !rho;
      if (!rho) drag.set(false);
      dragNote.textContent = rho ? `Air density ${rho} kg/m³` : "No atmosphere here — air resistance unavailable.";
    }

    L.side.append(
      panel("Cannon", angle.root, speed.root, height.root, el("div", { class: "btn-row" }, fire, erase)),
      panel("Setup", object.root, world.root, drag.root, dragNote),
      panel("Last shot", out.root, el("p", { class: "note" }, "Up to five shots stay on screen for comparison. Drag in the scene to aim.")),
    );
    refreshDragAvail();

    const player = new Player(L.bottom, (t) => { simTime = t; draw(); }, { speeds: [0.25, 0.5, 1, 2] });

    async function launch() {
      const o = OBJECTS[object.value], w = WORLDS[world.value];
      const args = { speed: speed.value, angle_deg: angle.value, height: height.value, gravity: w.g, n_points: 400 };
      if (drag.value && w.rho) Object.assign(args, { mass: o.mass, drag_coefficient: o.cd, area: Math.PI * o.diameter ** 2 / 4, air_density: w.rho });
      L.busy(true);
      try {
        const res = await simulate("physics", "projectile_motion", args);
        L.clearError();
        current = { traj: res.trajectory, result: res.result, obj: o, drag: !!args.mass };
        shots.push(current);
        if (shots.length > MAX_SHOTS) shots.shift();
        const r = res.result;
        out.set("range", fmtUnit(r.range, "m")); out.set("hmax", fmtUnit(r.max_height, "m"));
        out.set("time", fmtUnit(r.flight_time, "s")); out.set("vimp", fmtUnit(r.impact_speed, "m/s"));
        out.set("vt", r.terminal_velocity ? fmtUnit(r.terminal_velocity, "m/s") : "— (no drag)");
        player.load(r.flight_time, r.flight_time, { autoplay: true });
      } catch (e) {
        L.error(e.message);
      } finally { L.busy(false); }
    }

    // Aim by dragging in the scene: angle toward the pointer, speed from distance.
    let aiming = false;
    const aim = (e) => {
      const r = stage.canvas.getBoundingClientRect();
      const [wx, wy] = view.toWorld(e.clientX - r.left, e.clientY - r.top);
      const dx = wx, dy = wy - height.value;
      angle.set(Math.round(Math.max(0, Math.min(90, (Math.atan2(dy, dx) * 180) / Math.PI))), { silent: true });
      draw();
    };
    stage.canvas.addEventListener("pointerdown", (e) => { aiming = true; stage.canvas.setPointerCapture(e.pointerId); aim(e); });
    stage.canvas.addEventListener("pointermove", (e) => { if (aiming) aim(e); });
    stage.canvas.addEventListener("pointerup", () => { aiming = false; });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const wd = WORLDS[world.value];
      // World extent: fit all shots, with a minimum field of view.
      let xmax = 20, ymax = Math.max(8, height.value + 4);
      for (const s of shots) {
        xmax = Math.max(xmax, Math.max(...s.traj.x) * 1.1);
        ymax = Math.max(ymax, Math.max(...s.traj.y) * 1.15);
      }
      view.fit(-xmax * 0.06, xmax, -ymax * 0.08, ymax, w, h, { pad: 0.04, anchor: "bottom-left" });

      const g = ctx.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, wd.sky[0]); g.addColorStop(1, wd.sky[1]);
      ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
      const gy = view.y(0);
      ctx.fillStyle = wd.ground; ctx.fillRect(0, gy, w, h - gy);

      // Distance ticks along the ground
      const dark = world.value === "moon";
      const tickColor = dark ? "rgba(255,255,255,.8)" : "rgba(20,30,40,.7)";
      const step = niceStep(xmax, 8);
      for (let x = 0; x <= xmax; x += step) {
        ctx.strokeStyle = tickColor; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(view.x(x), gy); ctx.lineTo(view.x(x), gy + 6); ctx.stroke();
        label(ctx, `${fmt(x, 3)} m`, view.x(x), gy + 16, { color: tickColor, align: "center", font: "11px system-ui" });
      }

      // Launch platform + cannon
      const px = view.x(0), py = view.y(height.value);
      if (height.value > 0) { ctx.fillStyle = "#8a7560"; ctx.fillRect(px - 26, py, 40, gy - py); }
      const a = (angle.value * Math.PI) / 180;
      ctx.save(); ctx.translate(px, py - 10); ctx.rotate(-a);
      ctx.fillStyle = "#39424e"; ctx.fillRect(-6, -9, 50, 18); ctx.fillStyle = "#1e252d"; ctx.fillRect(40, -10, 8, 20);
      ctx.restore();
      ctx.fillStyle = "#5a4634"; ctx.beginPath(); ctx.arc(px, py - 6, 12, 0, Math.PI * 2); ctx.fill();
      arrow(ctx, px, py - 10, px + Math.cos(a) * (40 + speed.value * 1.2), py - 10 - Math.sin(a) * (40 + speed.value * 1.2), "rgba(42,120,214,.85)", 2, 9);

      // Trails
      shots.forEach((s, i) => {
        const isCur = s === current;
        const tEnd = isCur ? simTime : Infinity;
        ctx.strokeStyle = isCur ? "#2a78d6" : "rgba(42,120,214,.35)";
        ctx.lineWidth = 2.5; ctx.setLineDash(s.drag ? [] : [7, 5]);
        ctx.beginPath();
        let started = false;
        for (let k = 0; k < s.traj.t.length && s.traj.t[k] <= tEnd; k++) {
          const X = view.x(s.traj.x[k]), Y = view.y(s.traj.y[k]);
          if (started) ctx.lineTo(X, Y); else { ctx.moveTo(X, Y); started = true; }
        }
        ctx.stroke(); ctx.setLineDash([]);
        if (!isCur || simTime >= s.result.flight_time) {
          const lx = view.x(s.result.range);
          ctx.fillStyle = "#e34948"; ctx.beginPath(); ctx.moveTo(lx, gy); ctx.lineTo(lx - 6, gy - 10); ctx.lineTo(lx + 6, gy - 10); ctx.fill();
          if (isCur) label(ctx, `${fmt(s.result.range, 4)} m`, lx, gy - 18, { align: "center", font: "bold 12px system-ui", halo: "rgba(255,255,255,.85)" });
        }
        void i;
      });

      // Projectile
      if (current) {
        const t = Math.min(simTime, current.result.flight_time);
        const x = sampleAt(current.traj.t, current.traj.x, t), y = sampleAt(current.traj.t, current.traj.y, t);
        const r = Math.max(5, view.len(current.obj.diameter / 2));
        ctx.fillStyle = current.obj.color; ctx.strokeStyle = "#1e252d"; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(view.x(x), view.y(y) - r, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        label(ctx, `t = ${fmt(t, 3)} s   x = ${fmt(x, 3)} m   y = ${fmt(y, 3)} m`, 14, 20,
          { font: "13px system-ui", color: dark ? "#fff" : "#16202c", halo: dark ? null : "rgba(255,255,255,.7)" });
      }
      label(ctx, `Angle ${angle.value}°  ·  ${fmt(speed.value, 3)} m/s  ·  g = ${wd.g} m/s²`, w - 14, 20,
        { align: "right", font: "12px system-ui", color: dark ? "#fff" : "#16202c", halo: dark ? null : "rgba(255,255,255,.7)" });
    }

    draw();
    return () => { player.destroy(); stage.destroy(); };
  },
};
