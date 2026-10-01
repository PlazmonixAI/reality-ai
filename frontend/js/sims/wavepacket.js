// Quantum Wave Packets: physics.wave_packet solves the time-dependent Schrödinger equation; the page plays its frames.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const POT = [["barrier", "Barrier"], ["double_barrier", "Two barriers"], ["step", "Step"], ["well", "Well"], ["harmonic", "Trap"], ["free", "Free"]];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => {} });
    const [c1, c2] = SERIES();
    let res = null, frame = 0, playing = true, last = 0, raf = 0, alive = true;

    const pot = segmented({ label: "Potential", options: POT.map(([value, label]) => ({ value, label })), value: "barrier", onChange: () => run() });
    const en = slider({ label: "Electron energy", min: 0.05, max: 3, step: 0.01, value: 0.5, unit: "eV", onInput: () => run() });
    const hv = slider({ label: "Height (trap: ħω)", min: 0, max: 3, step: 0.01, value: 0.6, unit: "eV", onInput: () => run() });
    const wd = slider({ label: "Width", min: 0.1, max: 4, step: 0.05, value: 0.6, unit: "nm", onInput: () => run() });
    const pw = slider({ label: "Packet width", min: 0.5, max: 6, step: 0.1, value: 3, unit: "nm", onInput: () => run() });
    const play = button("Pause", () => { playing = !playing; play.textContent = playing ? "Pause" : "Play"; });
    const replay = button("Replay", () => { frame = 0; playing = true; play.textContent = "Pause"; });
    const out = readouts([{ key: "t", label: "Time" }, { key: "right", label: "Probability past the barrier" }, { key: "plane", label: "Single-energy formula" },
      { key: "v", label: "Group velocity" }, { key: "lam", label: "de Broglie wavelength" }]);
    L.side.append(panel("Wave packet", pot.root, en.root, hv.root, wd.root, pw.root,
      el("div", { class: "btn-row" }, play, replay),
      el("p", { class: "note" }, "One electron, solved from the Schrödinger equation. The packet splits: part tunnels through, part bounces back. Both happen to the same electron until it is measured.")),
      panel("Result (from the engine)", out.root));
    const graph = new LineGraph(L.bottom, { title: "Probability found to the right of the barrier", xLabel: "time (fs)", height: 140, includeZero: true });

    const run = liveRequest((s) => simulate("physics", "wave_packet", { potential: pot.value, energy_ev: en.value, height_ev: hv.value, width_nm: wd.value,
      packet_width_nm: pw.value, duration_fs: pot.value === "harmonic" ? 50 : 70, frames: 90 }, s), {
      delay: 150, onError: (e) => L.error(e.message), onBusy: (b) => L.busy(b),
      onResult: (r) => {
        L.clearError(); res = r.result; frame = 0;
        graph.setSeries([{ name: "P(right)", color: c2, x: res.times_fs, y: res.probability_right }]);
        out.set("plane", res.plane_wave_transmission == null ? "–" : fmt(res.plane_wave_transmission, 3));
        out.set("v", `${fmt(res.group_velocity_nm_per_fs, 3)} nm/fs`); out.set("lam", res.wavelength_nm ? `${fmt(res.wavelength_nm, 3)} nm` : "–");
      },
    });

    function draw(now) {
      if (!alive) return;
      raf = requestAnimationFrame(draw);
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      if (playing && now - last > 50) { frame = (frame + 1) % res.times_fs.length; last = now; if (frame === 0) frame = 0; }
      const xs = res.x_nm, x0 = -40, x1 = 40;
      const X = (x) => 30 + ((x - x0) / (x1 - x0)) * (w - 60);
      const base = h - 46, vmax = Math.max(1e-9, ...res.potential_ev.filter((v, i) => xs[i] > x0 && xs[i] < x1).map(Math.abs), en.value) * 1.3;
      const VY = (v) => base - (v / vmax) * (h * 0.32);
      // potential
      ctx.fillStyle = "rgba(235,104,52,.22)"; ctx.strokeStyle = c2; ctx.lineWidth = 2; ctx.beginPath();
      xs.forEach((x, i) => { if (x < x0 || x > x1) return; const y = VY(res.potential_ev[i]); ctx.lineTo(X(x), y); });
      ctx.stroke();
      // energy line
      ctx.strokeStyle = "rgba(201,206,214,.6)"; ctx.setLineDash([6, 5]); ctx.beginPath(); ctx.moveTo(30, VY(en.value)); ctx.lineTo(w - 30, VY(en.value)); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, `E = ${fmt(en.value, 3)} eV`, 34, VY(en.value) - 10, { color: "#c9ced6", font: "12px system-ui" });
      // |ψ|² filled, Re ψ as a thin line
      const d = res.density_per_nm[frame], re = res.real_part[frame];
      const dmax = Math.max(...res.density_per_nm[0]) * 1.15, top = 30, span = h * 0.48;
      const DY = (v) => top + span - (v / dmax) * span;
      ctx.beginPath(); ctx.moveTo(X(x0), DY(0));
      xs.forEach((x, i) => { if (x >= x0 && x <= x1) ctx.lineTo(X(x), DY(d[i])); });
      ctx.lineTo(X(x1), DY(0)); ctx.closePath();
      ctx.fillStyle = "rgba(42,120,214,.35)"; ctx.fill(); ctx.strokeStyle = c1; ctx.lineWidth = 2; ctx.stroke();
      const rmax = Math.sqrt(dmax);
      ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 1; ctx.beginPath();
      let pen = false;
      xs.forEach((x, i) => { if (x < x0 || x > x1) return; const y = top + span / 2 - (re[i] / rmax) * span * 0.25; if (pen) ctx.lineTo(X(x), y); else { ctx.moveTo(X(x), y); pen = true; } });
      ctx.stroke();
      label(ctx, "|ψ|² (blue, filled) and the real part of ψ (white)", 34, 16, { color: "#c9ced6", font: "12px system-ui" });
      const t = res.times_fs[frame];
      out.set("t", `${fmt(t, 3)} fs`); out.set("right", fmt(res.probability_right[frame], 3));
      graph.setCursor(t);
      label(ctx, `t = ${fmt(t, 3)} fs`, w - 34, 16, { align: "right", color: "#e8ecf3", font: "600 13px system-ui" });
      label(ctx, "nm", w - 30, base + 22, { align: "right", color: "#8d99ae", font: "11px system-ui" });
      for (let x = -40; x <= 40; x += 10) label(ctx, String(x), X(x), base + 22, { align: "center", color: "#8d99ae", font: "11px system-ui" });
    }

    run();
    raf = requestAnimationFrame(draw);
    return () => { alive = false; cancelAnimationFrame(raf); run.cancel(); graph.destroy(); stage.destroy(); };
  },
};
