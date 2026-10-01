// Forces on a Ramp: physics.ramp_motion gives the force breakdown and the piecewise-exact motion.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, sampleAt, label, arrow } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const LENGTH = 5, DURATION = 5;
const SURFACES = { ice: ["Ice", 0.1, 0.05], wood: ["Wood", 0.5, 0.3], rubber: ["Rubber", 1.0, 0.8], custom: ["Custom", null, null] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null, simTime = 0;

    const mass = slider({ label: "Mass", min: 1, max: 100, step: 1, value: 20, unit: "kg", onInput: () => recompute() });
    const angle = slider({ label: "Ramp angle", min: 0, max: 60, step: 0.5, value: 30, unit: "°", onInput: () => recompute() });
    const surface = select({ label: "Surface", value: "wood", options: Object.entries(SURFACES).map(([v, [l]]) => ({ value: v, label: l })), onChange: (v) => {
      const [, s, k] = SURFACES[v]; if (s !== null) { muS.set(s); muK.set(k); } recompute();
    } });
    const muS = slider({ label: "Static friction μs", min: 0, max: 1.2, step: 0.01, value: 0.5, onInput: () => { surface.set("custom"); if (muK.value > muS.value) muK.set(muS.value); recompute(); } });
    const muK = slider({ label: "Kinetic friction μk", min: 0, max: 1.2, step: 0.01, value: 0.3, onInput: () => { surface.set("custom"); if (muK.value > muS.value) muS.set(muK.value); recompute(); } });
    const force = slider({ label: "Applied force (up the ramp +)", min: -500, max: 500, step: 5, value: 0, unit: "N", onInput: () => recompute() });
    const pos0 = slider({ label: "Start position (from bottom)", min: 0, max: LENGTH, step: 0.1, value: 4, unit: "m", onInput: () => recompute() });
    const v0 = slider({ label: "Start velocity (up +)", min: -6, max: 6, step: 0.1, value: 0, unit: "m/s", onInput: () => recompute() });
    const out = readouts([
      { key: "moves", label: "Does it move?" }, { key: "a", label: "Acceleration" }, { key: "fr", label: "Friction force" },
      { key: "n", label: "Normal force" }, { key: "rep", label: "Slides by itself above" },
    ]);
    L.side.append(
      panel("Block & ramp", mass.root, angle.root, surface.root, muS.root, muK.root),
      panel("Push & start", force.root, pos0.root, v0.root),
      panel("Forces (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "Energy", xLabel: "time (s)", yLabel: "energy (J)", height: 140, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "ramp_motion", {
      mass: mass.value, angle_deg: angle.value, mu_static: muS.value, mu_kinetic: Math.min(muK.value, muS.value),
      applied_force: force.value, position: pos0.value, velocity: v0.value, length: LENGTH, duration: DURATION, n_points: 501,
    }, signal), {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const f = r.forces;
        out.set("moves", r.result.moves ? (r.result.stopped_at_end ? `yes, until the ${r.result.stopped_at_end}` : "yes") : "no, static friction holds");
        out.set("a", `${fmt(r.result.initial_acceleration, 4)} m/s²`);
        out.set("fr", `${fmt(f.friction, 4)} N (max static ${fmt(f.max_static_friction, 3)} N)`);
        out.set("n", `${fmt(f.normal, 4)} N`);
        out.set("rep", `${fmt(r.result.angle_of_repose_deg, 3)}° (tan θ = μs)`);
        const tr = r.trajectory;
        graph.setSeries([
          { name: "Kinetic", color: c1, x: tr.t, y: tr.kinetic },
          { name: "Potential", color: c2, x: tr.t, y: tr.potential },
          { name: "Thermal", color: c3, x: tr.t, y: tr.thermal },
        ]);
        player.load(DURATION, DURATION);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const sky = ctx.createLinearGradient(0, 0, 0, h); sky.addColorStop(0, "#dff0ff"); sky.addColorStop(1, "#f6fbff");
      ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
      const th = (angle.value * Math.PI) / 180;
      const ground = h - 40, x0 = 60;
      const scale = Math.min((w * 0.62 - x0) / (LENGTH * Math.cos(th) + 0.01), (ground - 60) / (LENGTH * Math.sin(th) + 0.01), 140);
      ctx.fillStyle = "#6cbf5b"; ctx.fillRect(0, ground, w, h - ground);
      const top = [x0 + LENGTH * Math.cos(th) * scale, ground - LENGTH * Math.sin(th) * scale];
      ctx.fillStyle = "#c8a878"; ctx.beginPath(); ctx.moveTo(x0, ground); ctx.lineTo(top[0], top[1]); ctx.lineTo(top[0], ground); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#8a6d3b"; ctx.lineWidth = 2; ctx.stroke();
      label(ctx, `${fmt(angle.value, 3)}°`, x0 + 46, ground - 12, { font: "bold 12px system-ui" });
      // Block
      const s = res ? sampleAt(res.trajectory.t, res.trajectory.position, simTime) : pos0.value;
      const vNow = res ? sampleAt(res.trajectory.t, res.trajectory.velocity, simTime) : v0.value;
      const bs = Math.max(26, Math.min(60, 22 + Math.cbrt(mass.value) * 8));
      const cx = x0 + s * Math.cos(th) * scale, cy = ground - s * Math.sin(th) * scale;
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(-th);
      ctx.fillStyle = "#2a78d6"; ctx.fillRect(-bs / 2, -bs, bs, bs);
      label(ctx, `${fmt(mass.value, 3)} kg`, 0, -bs / 2, { align: "center", color: "#fff", font: "bold 11px system-ui" });
      ctx.restore();
      label(ctx, `v = ${fmt(vNow, 3)} m/s   s = ${fmt(s, 3)} m`, 14, 20, { font: "13px system-ui" });

      // Free-body diagram (forces at the current velocity state, from the engine)
      if (!res) return;
      const f = res.forces;
      const fx = w - 150, fy = 150, maxF = Math.max(Math.abs(f.gravity_along_ramp), f.normal, Math.abs(f.applied), 1);
      const k = 100 / maxF;
      ctx.fillStyle = "rgba(255,255,255,.9)"; ctx.strokeStyle = "#d8dee8";
      ctx.beginPath(); ctx.roundRect(fx - 130, fy - 130, 260, 270, 10); ctx.fill(); ctx.stroke();
      label(ctx, "Forces on the block at the start", fx, fy - 114, { align: "center", font: "bold 12px system-ui" });
      const ux = Math.cos(th), uy = -Math.sin(th);       // up-ramp direction on screen
      const nx = Math.sin(th), ny = Math.cos(th) * -1;   // normal (away from surface) on screen
      ctx.fillStyle = "#2a78d6"; ctx.fillRect(fx - 7, fy - 7, 14, 14);
      // Forces along the ramp share a line, so each is drawn slightly offset sideways.
      const vec = (mag, dx, dy, color, name, off = 0) => {
        if (Math.abs(mag) < 1e-9) return;
        const L2 = mag * k, ox = fx + nx * off, oy = fy + ny * off;
        arrow(ctx, ox, oy, ox + dx * L2, oy + dy * L2, color, 3, 10);
        label(ctx, `${name} ${fmt(Math.abs(mag), 3)} N`, ox + dx * L2 + (dx * mag >= 0 ? 6 : -6), oy + dy * L2 + 4, { font: "11px system-ui", align: dx * mag >= 0 ? "left" : "right", halo: "#fff" });
      };
      vec(f.gravity_along_ramp, ux, uy, "#7b8796", "gravity ∥", -16);
      vec(f.normal, nx, ny, "#1baf7a", "normal");
      vec(f.friction, ux, uy, "#e34948", "friction", 16);
      vec(f.applied, ux, uy, "#eda100", "applied", 32);
      label(ctx, `net ${fmt(f.net, 3)} N along the ramp`, fx, fy + 124, { align: "center", font: "bold 11px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
