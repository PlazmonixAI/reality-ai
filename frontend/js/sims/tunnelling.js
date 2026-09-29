// Quantum Tunnelling: physics.quantum_tunnelling gives the exact transmission through a rectangular barrier.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null;

    const e = slider({ label: "Electron energy", min: 0.05, max: 10, step: 0.05, value: 1, unit: "eV", onInput: () => recompute() });
    const v = slider({ label: "Barrier height", min: 0, max: 10, step: 0.05, value: 2, unit: "eV", onInput: () => recompute() });
    const a = slider({ label: "Barrier width", min: 0.05, max: 2, step: 0.01, value: 0.4, unit: "nm", onInput: () => recompute() });
    const out = readouts([{ key: "t", label: "Transmission T" }, { key: "r", label: "Reflection R" }, { key: "d", label: "Decay length inside" }, { key: "l", label: "de Broglie wavelength" }]);
    L.side.append(
      panel("Barrier", e.root, v.root, a.root, el("p", { class: "note" }, "Classically an electron below the barrier always bounces back. Quantum waves leak through, falling off exponentially inside.")),
      panel("Result (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "Transmission vs energy (cursor = this electron)", xLabel: "energy (eV)", yLabel: "T", height: 150, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "quantum_tunnelling", { energy_ev: e.value, barrier_ev: v.value, width_nm: a.value }, signal), {
      delay: 30, onError: (err) => L.error(err.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("t", fmt(x.transmission, 4)); out.set("r", fmt(x.reflection, 4));
        out.set("d", x.decay_length_nm ? `${fmt(x.decay_length_nm, 3)} nm` : "— (above the barrier)"); out.set("l", `${fmt(x.wavelength_nm, 3)} nm`);
        graph.setSeries([{ name: "T", color: c1, x: r.curve.energy_ev, y: r.curve.transmission }]);
        graph.setCursor(e.value);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const wf = res.wavefunction, xs = wf.x_nm, x0 = xs[0], x1 = xs[xs.length - 1];
      const X = (x) => 30 + ((x - x0) / (x1 - x0)) * (w - 60), eTop = Math.max(v.value, e.value) * 1.6 || 1, Y = (en) => h - 40 - (en / eTop) * (h * 0.45);
      ctx.fillStyle = "rgba(235,104,52,.25)"; ctx.fillRect(X(0), Y(v.value), X(a.value) - X(0), Y(0) - Y(v.value));
      ctx.strokeStyle = c2; ctx.lineWidth = 2; ctx.strokeRect(X(0), Y(v.value), X(a.value) - X(0), Y(0) - Y(v.value));
      label(ctx, `barrier ${fmt(v.value, 3)} eV`, X(a.value / 2), Y(v.value) - 10, { align: "center", color: c2, font: "12px system-ui" });
      ctx.strokeStyle = "#c9ced6"; ctx.setLineDash([6, 5]); ctx.beginPath(); ctx.moveTo(30, Y(e.value)); ctx.lineTo(w - 30, Y(e.value)); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, `E = ${fmt(e.value, 3)} eV`, 34, Y(e.value) - 10, { color: "#c9ced6", font: "12px system-ui" });
      // |ψ|² on top (relative to the incoming wave's |ψ|² = 1)
      const dmax = Math.max(...wf.density, 1), top = 40, span = h * 0.34;
      ctx.strokeStyle = c1; ctx.lineWidth = 2.5; ctx.beginPath();
      wf.density.forEach((d, i) => { const y = top + span - (d / dmax) * span; if (i) ctx.lineTo(X(xs[i]), y); else ctx.moveTo(X(xs[i]), y); });
      ctx.stroke();
      ctx.strokeStyle = "rgba(201,206,214,.3)"; ctx.beginPath(); ctx.moveTo(30, top + span); ctx.lineTo(w - 30, top + span); ctx.stroke();
      label(ctx, "|ψ|²: incoming + reflected (left), decaying inside, transmitted (right)", 34, 20, { color: "#c9ced6", font: "12px system-ui" });
      label(ctx, `T = ${fmt(res.result.transmission, 3)}`, w - 34, top + span - (res.wavefunction.density[res.wavefunction.density.length - 1] / dmax) * span - 12, { align: "right", color: c1, font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
