// Charged Particles in Fields: physics.charged_particle integrates the Lorentz force q(E + v × B).
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, indexAt, label, arrow } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const PARTICLES = { proton: "Proton", electron: "Electron", positron: "Positron", alpha: "Alpha particle" };
const timeUnit = (T) => (T < 1e-9 ? [1e12, "ps"] : T < 1e-6 ? [1e9, "ns"] : T < 1e-3 ? [1e6, "µs"] : [1e3, "ms"]);
const lenUnit = (L) => (L < 1e-3 ? [1e6, "µm"] : L < 1 ? [1e3, "mm"] : [1, "m"]);

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let data = null, simT = 0, box = null;

    const part = select({ label: "Particle", value: "proton", options: Object.entries(PARTICLES).map(([v, l]) => ({ value: v, label: l })), onChange: () => recompute() });
    const bz = slider({ label: "Magnetic field B (out of screen)", min: -1, max: 1, step: 0.01, value: 0.5, unit: "T", onInput: () => recompute() });
    const ey = slider({ label: "Electric field E (up the screen)", min: -50000, max: 50000, step: 500, value: 0, unit: "V/m", onInput: () => recompute() });
    const sp = slider({ label: "Launch speed", min: 1e3, max: 1e7, value: 1e5, log: true, unit: "m/s", onInput: () => recompute() });
    const ang = slider({ label: "Launch direction", min: -180, max: 180, step: 1, value: 0, unit: "°", onInput: () => recompute() });
    const out = readouts([
      { key: "w", label: "Cyclotron frequency" }, { key: "r", label: "Radius of the circle" }, { key: "T", label: "Period" },
      { key: "d", label: "E × B drift speed" }, { key: "ke", label: "Kinetic energy (start)" },
    ]);
    L.side.append(
      panel("Fields & particle", part.root, bz.root, ey.root, sp.root, ang.root, el("p", { class: "note" }, "B bends the path into circles without changing the speed. Add E across B and the circles drift sideways at E/B.")),
      panel("Motion (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t * (data ? data.tu[0] : 1)); }, { speeds: [0.5, 1, 2], timeFormat: (v) => (data ? `${fmt(v * data.tu[0], 3)} ${data.tu[1]}` : "") });
    const graph = new LineGraph(L.bottom, { title: "Speed of the particle", xLabel: "time", yLabel: "speed (km/s)", height: 130, includeZero: true });

    const recompute = liveRequest((signal) => {
      const a = (ang.value * Math.PI) / 180;
      return simulate("physics", "charged_particle", {
        particle: part.value, magnetic_field: [0, 0, bz.value], electric_field: [0, ey.value, 0],
        velocity: [sp.value * Math.cos(a), sp.value * Math.sin(a), 0], n_points: 2000,
      }, signal);
    }, {
      delay: 40, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError();
        const tr = r.trajectory, T = tr.t[tr.t.length - 1], tu = timeUnit(T);
        const xs = tr.x, ys = tr.y;
        const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
        const span = Math.max(x1 - x0, y1 - y0, 1e-12);
        box = { x0, x1, y0, y1, span, lu: lenUnit(span) };
        data = { ...r, tu };
        const x = r.result;
        out.set("w", x.cyclotron_frequency ? `${fmt(x.cyclotron_frequency, 4)} rad/s (${fmt(x.cyclotron_frequency_hz / 1e6, 4)} MHz)` : "— (no B)");
        const lu = lenUnit(x.larmor_radius || span);
        out.set("r", x.larmor_radius !== null ? `${fmt(x.larmor_radius * lu[0], 4)} ${lu[1]}` : "—");
        const pu = x.period ? timeUnit(x.period) : null;
        out.set("T", x.period ? `${fmt(x.period * pu[0], 4)} ${pu[1]}` : "—");
        out.set("d", `${fmt(x.drift_speed / 1000, 4)} km/s`); out.set("ke", `${fmt(x.initial_kinetic_energy_ev, 4)} eV`);
        graph.opts.xLabel = `time (${tu[1]})`;
        graph.setSeries([{ name: "speed", color: c2, x: tr.t.map((t) => t * tu[0]), y: tr.speed.map((v) => v / 1000) }]);
        player.load(T, 8);
      },
    });

    function draw() {
      const { ctx, width: W, height: H } = stage;
      if (!W) return;
      ctx.fillStyle = "#101826"; ctx.fillRect(0, 0, W, H);
      // Field symbols: dots = B out of the screen, crosses = into it
      const bOut = bz.value > 0;
      ctx.strokeStyle = ctx.fillStyle = `rgba(201,206,214,${0.15 + 0.4 * Math.abs(bz.value)})`; ctx.lineWidth = 1.5;
      for (let gx = 30; gx < W; gx += 50) for (let gy = 30; gy < H; gy += 50) {
        if (bz.value === 0) continue;
        if (bOut) { ctx.beginPath(); ctx.arc(gx, gy, 2.5, 0, Math.PI * 2); ctx.fill(); }
        else { ctx.beginPath(); ctx.moveTo(gx - 4, gy - 4); ctx.lineTo(gx + 4, gy + 4); ctx.moveTo(gx + 4, gy - 4); ctx.lineTo(gx - 4, gy + 4); ctx.stroke(); }
      }
      if (ey.value !== 0) for (let gx = 55; gx < W; gx += 100) arrow(ctx, gx, H / 2 + (ey.value > 0 ? 30 : -30), gx, H / 2 + (ey.value > 0 ? -30 : 30), "rgba(235,104,52,.45)", 2, 8);
      if (!data) return;
      const tr = data.trajectory, s = Math.min(W - 80, H - 80) / box.span;
      const ox = W / 2 - ((box.x0 + box.x1) / 2) * s, oy = H / 2 + ((box.y0 + box.y1) / 2) * s;
      const k = indexAt(tr.t, simT);
      ctx.strokeStyle = c1; ctx.lineWidth = 2.5; ctx.beginPath();
      for (let i = 0; i <= k; i++) { const px = ox + tr.x[i] * s, py = oy - tr.y[i] * s; if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py); }
      ctx.stroke();
      const q = data.result.charge;
      ctx.fillStyle = q > 0 ? "#e34948" : "#5598e7"; ctx.beginPath(); ctx.arc(ox + tr.x[k] * s, oy - tr.y[k] * s, 8, 0, Math.PI * 2); ctx.fill();
      label(ctx, q > 0 ? "+" : "−", ox + tr.x[k] * s, oy - tr.y[k] * s + 1, { align: "center", color: "#fff", font: "bold 13px system-ui" });
      // Scale bar
      const [f, u] = box.lu, raw = box.span * f / 4, p10 = 10 ** Math.floor(Math.log10(raw)), nice = [1, 2, 5, 10].find((m) => m * p10 >= raw) * p10;
      const px = (nice / f) * s;
      ctx.strokeStyle = "#c9ced6"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(20, H - 20); ctx.lineTo(20 + px, H - 20); ctx.stroke();
      label(ctx, `${fmt(nice, 3)} ${u}`, 20 + px / 2, H - 32, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      label(ctx, bz.value === 0 ? "no magnetic field" : `B ${bOut ? "out of" : "into"} the screen`, W - 16, 20, { align: "right", color: "#c9ced6", font: "12px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
