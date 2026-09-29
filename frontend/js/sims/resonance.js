// Resonance: physics.driven_oscillator gives the driven motion, steady-state amplitude, phase and response curve.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, arrow, sampleAt } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let data = null, simT = 0;

    const k = slider({ label: "Spring stiffness k", min: 10, max: 400, step: 1, value: 100, unit: "N/m", onInput: () => recompute() });
    const b = slider({ label: "Damping b", min: 0.05, max: 20, value: 1, log: true, unit: "kg/s", onInput: () => recompute() });
    const w = slider({ label: "Drive frequency ω", min: 0.5, max: 40, step: 0.05, value: 9, unit: "rad/s", onInput: () => recompute() });
    const f0 = slider({ label: "Drive force amplitude", min: 0.1, max: 5, step: 0.1, value: 1, unit: "N", onInput: () => recompute() });
    const out = readouts([
      { key: "w0", label: "Natural frequency ω₀ = √(k/m)" }, { key: "q", label: "Quality factor Q" }, { key: "a", label: "Steady amplitude" },
      { key: "ph", label: "Phase lag behind the drive" }, { key: "gain", label: "Amplitude ÷ static stretch" }, { key: "p", label: "Mean power absorbed" },
    ]);
    L.side.append(
      panel("Driven 1 kg mass", k.root, b.root, w.root, f0.root, el("p", { class: "note" }, "Push at the natural frequency and the swings grow until damping balances the drive: resonance.")),
      panel("Response (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); xg.setCursor(t); }, { speeds: [0.25, 0.5, 1, 2] });
    const xg = new LineGraph(L.bottom, { title: "Displacement: transient, then steady state", xLabel: "time (s)", yLabel: "x (m)", height: 120 });
    const rg = new LineGraph(L.bottom, { title: "Resonance curve: steady amplitude vs drive frequency", xLabel: "ω (rad/s)", yLabel: "amplitude (m)", height: 120, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "driven_oscillator", {
      mass: 1, stiffness: k.value, damping: b.value, drive_force: f0.value, drive_frequency: w.value, n_points: 2000,
    }, signal), {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const x = r.result;
        out.set("w0", `${fmt(x.natural_frequency, 4)} rad/s`); out.set("q", fmt(x.quality_factor, 4));
        out.set("a", `${fmt(x.steady_amplitude * 100, 4)} cm`); out.set("ph", `${fmt(x.phase_lag_deg, 4)}°`);
        out.set("gain", `×${fmt(x.amplification, 4)}`); out.set("p", `${fmt(x.mean_power, 4)} W`);
        xg.setSeries([{ name: "x", color: c1, x: r.trajectory.t, y: r.trajectory.x }]);
        rg.setSeries([{ name: "amplitude", color: c2, x: r.response.omega, y: r.response.amplitude }]);
        rg.setCursor(w.value);
        player.load(r.trajectory.t[r.trajectory.t.length - 1], r.trajectory.t[r.trajectory.t.length - 1]);
      },
    });

    function draw() {
      const { ctx, width: W, height: H } = stage;
      if (!W) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, W, H);
      if (!data) return;
      const tr = data.trajectory;
      const x = sampleAt(tr.t, tr.x, simT), f = sampleAt(tr.t, tr.drive, simT);
      const maxX = Math.max(...tr.x.map(Math.abs), 1e-9);
      const scale = Math.min(H * 0.3, 160) / maxX;
      const cx = W * 0.4, top = 30, rest = H * 0.5, my = rest + x * scale;
      ctx.fillStyle = "#39424e"; ctx.fillRect(cx - 70, top - 12, 140, 12);
      // Spring zig-zag from the ceiling to the mass
      const coils = 14, y0 = top, y1 = my - 28;
      ctx.strokeStyle = "#4b5868"; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(cx, y0);
      for (let i = 1; i < coils; i++) ctx.lineTo(cx + (i % 2 ? 16 : -16), y0 + ((y1 - y0) * i) / coils);
      ctx.lineTo(cx, y1); ctx.stroke();
      ctx.fillStyle = c1; ctx.fillRect(cx - 32, my - 28, 64, 56);
      label(ctx, "1 kg", cx, my, { align: "center", color: "#fff", font: "bold 13px system-ui" });
      // Drive force arrow (length ∝ F)
      const fl = (f / Math.max(f0.value, 1e-9)) * 60;
      if (Math.abs(fl) > 2) arrow(ctx, cx + 60, my, cx + 60, my + fl, c2, 3, 10);
      label(ctx, "drive force", cx + 70, my + fl / 2, { color: c2, font: "12px system-ui" });
      ctx.setLineDash([4, 4]); ctx.strokeStyle = "#9aa6b5"; ctx.beginPath(); ctx.moveTo(cx - 120, rest); ctx.lineTo(cx + 120, rest); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, "equilibrium", cx - 124, rest, { align: "right", font: "11px system-ui", color: "#7b8796" });
      label(ctx, `x = ${fmt(x * 100, 3)} cm`, W - 16, 22, { align: "right", font: "bold 13px system-ui" });
      label(ctx, `ω / ω₀ = ${fmt(w.value / data.result.natural_frequency, 3)}`, W - 16, 42, { align: "right", font: "12px system-ui", color: "#4b5868" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); xg.destroy(); rg.destroy(); stage.destroy(); };
  },
};
