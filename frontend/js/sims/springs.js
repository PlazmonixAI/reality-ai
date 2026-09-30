// Masses & Springs: physics.harmonic_oscillator computes x(t), v(t) and energies exactly.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, sampleAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtUnit } from "../core/format.js";
import { drawEnergyBars } from "./energy_bars.js";

const G = 9.80665, L0 = 0.25, DURATION = 12;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2, c3] = SERIES();
    let data = null, simTime = 0, dragging = false, dragX = 0;

    const mass = slider({ label: "Mass", min: 0.05, max: 2, step: 0.01, value: 0.5, unit: "kg", onInput: () => recompute() });
    const k = slider({ label: "Spring constant", min: 5, max: 200, step: 1, value: 40, unit: "N/m", onInput: () => recompute() });
    const damping = slider({ label: "Damping", min: 0, max: 8, step: 0.05, value: 0.3, unit: "kg/s", onInput: () => recompute() });
    const x0 = slider({ label: "Initial displacement (down +)", min: -0.2, max: 0.2, step: 0.005, value: 0.1, unit: "m", onInput: () => recompute() });
    const out = readouts([
      { key: "w0", label: "Natural frequency" }, { key: "period", label: "Period" }, { key: "zeta", label: "Damping ratio" },
      { key: "regime", label: "Regime" }, { key: "q", label: "Quality factor Q" },
    ]);
    L.side.append(
      panel("Spring & mass", mass.root, k.root, damping.root, x0.root, el("p", { class: "note" }, "Or drag the mass in the scene and let go.")),
      panel("Oscillator (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "Displacement from equilibrium", xLabel: "time (s)", yLabel: "x (m)", height: 140 });

    const recompute = liveRequest((signal) => simulate("physics", "harmonic_oscillator", {
      mass: mass.value, stiffness: k.value, damping: damping.value, initial_displacement: x0.value,
      initial_velocity: 0, duration: DURATION, n_points: 1201,
    }, signal), {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (res) => {
        L.clearError();
        data = res;
        const r = res.result;
        out.set("w0", `${fmt(r.natural_frequency, 4)} rad/s (${fmt(r.natural_frequency_hz, 3)} Hz)`);
        out.set("period", r.period ? fmtUnit(r.period, "s") : "no oscillation");
        out.set("zeta", fmt(r.damping_ratio, 3)); out.set("regime", r.regime);
        out.set("q", r.quality_factor ? fmt(r.quality_factor, 3) : "∞");
        graph.setSeries([{ name: "x", color: c1, x: res.trajectory.t, y: res.trajectory.x }]);
        player.load(DURATION, DURATION);
      },
    });

    const yEq = () => -(L0 + (mass.value * G) / k.value);
    const blockSize = () => 0.05 + 0.05 * Math.cbrt(mass.value);

    stage.canvas.addEventListener("pointerdown", (e) => {
      if (!data) return;
      const r = stage.canvas.getBoundingClientRect();
      const [wx, wy] = view.toWorld(e.clientX - r.left, e.clientY - r.top);
      const xNow = dragging ? dragX : sampleAt(data.trajectory.t, data.trajectory.x, simTime);
      const by = yEq() - xNow;
      if (Math.abs(wx) < 0.12 && Math.abs(wy - (by - blockSize() / 2)) < blockSize()) {
        dragging = true; player.pause(); stage.canvas.setPointerCapture(e.pointerId);
      }
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const r = stage.canvas.getBoundingClientRect();
      const [, wy] = view.toWorld(e.clientX - r.left, e.clientY - r.top);
      dragX = Math.max(-0.2, Math.min(0.2, yEq() - (wy + blockSize() / 2)));
      x0.set(dragX); draw();
    });
    stage.canvas.addEventListener("pointerup", () => { if (dragging) { dragging = false; recompute(); } });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, "#f3f7fc"); bg.addColorStop(1, "#e3ebf5");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      view.fit(-0.45, 0.75, -1.05, 0.05, w, h, { pad: 0.04 });
      const x = dragging ? dragX : data ? sampleAt(data.trajectory.t, data.trajectory.x, simTime) : x0.value;
      const top = view.y(0), cx = view.x(0);

      // Ceiling
      ctx.fillStyle = "#7b8796"; ctx.fillRect(cx - 90, top - 12, 180, 12);
      for (let i = -90; i < 90; i += 12) { ctx.strokeStyle = "#5b6574"; ctx.beginPath(); ctx.moveTo(cx + i, top - 12); ctx.lineTo(cx + i + 8, top - 20); ctx.stroke(); }

      // Ruler
      ctx.strokeStyle = "#9aa6b5"; ctx.lineWidth = 1;
      const rx = view.x(-0.3);
      ctx.beginPath(); ctx.moveTo(rx, view.y(0)); ctx.lineTo(rx, view.y(-1)); ctx.stroke();
      for (let d = 0; d <= 100; d += 5) {
        const yy = view.y(-d / 100);
        ctx.beginPath(); ctx.moveTo(rx, yy); ctx.lineTo(rx + (d % 10 ? 5 : 10), yy); ctx.stroke();
        if (d % 20 === 0) label(ctx, `${d} cm`, rx - 6, yy, { color: "#4b5868", align: "right", font: "11px system-ui" });
      }

      // Equilibrium line
      const ye = yEq();
      ctx.setLineDash([6, 5]); ctx.strokeStyle = "#1baf7a"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(view.x(-0.25), view.y(ye)); ctx.lineTo(view.x(0.25), view.y(ye)); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, "equilibrium", view.x(0.26), view.y(ye), { color: "#15845d", font: "11px system-ui" });

      // Spring coil
      const bs = blockSize();
      const yTop = 0, yBot = ye - x;
      const coils = 14, amp = 0.035;
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(cx, view.y(yTop));
      const lead = 0.03;
      ctx.lineTo(cx, view.y(yTop - lead));
      for (let i = 1; i < coils * 2; i++) {
        const f = i / (coils * 2);
        ctx.lineTo(view.x(i % 2 ? amp : -amp), view.y(yTop - lead + (yBot + lead - yTop + lead) * f - lead * f));
      }
      ctx.lineTo(cx, view.y(yBot)); ctx.stroke();

      // Mass block
      const bx = view.x(-bs / 2), byTop = view.y(yBot), sz = view.len(bs);
      ctx.fillStyle = dragging ? "#1c5cab" : c1;
      ctx.beginPath(); ctx.roundRect(bx, byTop, sz, sz, 6); ctx.fill();
      label(ctx, `${fmt(mass.value, 3)} kg`, cx, byTop + sz / 2, { color: "#fff", align: "center", font: "bold 12px system-ui" });

      // Energy bars
      if (data) {
        const tr = data.trajectory;
        const ke = dragging ? 0 : sampleAt(tr.t, tr.kinetic, simTime);
        const pe = dragging ? 0.5 * k.value * dragX * dragX : sampleAt(tr.t, tr.potential, simTime);
        const e0 = tr.energy[0], total = dragging ? pe : sampleAt(tr.t, tr.energy, simTime);
        const thermal = dragging ? 0 : Math.max(0, e0 - total);
        const max = Math.max(e0, pe, 1e-9) * 1.05;
        drawEnergyBars(ctx, [
          { name: "Kinetic", value: ke, color: c1 }, { name: "Elastic", value: pe, color: c2 },
          { name: "Thermal", value: thermal, color: c3 }, { name: "Total", value: ke + pe + thermal, color: "#7b8796" },
        ], max, w - 230, 16, 214, Math.min(260, h - 32));
      }
      label(ctx, `x = ${fmt(x * 100, 3)} cm   t = ${fmt(simTime, 3)} s`, 14, h - 16, { color: "#16202c", font: "13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
