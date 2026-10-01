// Quantum Harmonic Oscillator: physics.quantum_oscillator gives the levels, the eigenfunctions and the frames of a
// two-level superposition; the page draws the textbook ladder and plays the superposition.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => {} });
    const [c1, c2, c3] = SERIES();
    let res = null, raf = 0, alive = true, start = performance.now();

    const hw = slider({ label: "Level spacing ħω", min: 0.02, max: 1, step: 0.01, value: 0.2, unit: "eV", onInput: () => run() });
    const nmax = slider({ label: "Levels shown", min: 1, max: 8, step: 1, value: 5, digits: 2, onInput: () => run() });
    const opts = Array.from({ length: 9 }, (_, n) => ({ value: String(n), label: `n = ${n}` }));
    const a = select({ label: "Superpose level", options: opts, value: "0", onChange: () => run() });
    const b = select({ label: "with level", options: opts, value: "1", onChange: () => run() });
    const out = readouts([{ key: "zp", label: "Zero-point energy" }, { key: "len", label: "Oscillator length" }, { key: "T", label: "Slosh period" }, { key: "x", label: "Mean position now" }]);
    L.side.append(panel("Oscillator", hw.root, nmax.root, a.root, b.root,
      el("p", { class: "note" }, "Energy comes in equal steps of ħω and never reaches zero. A single level does not move; a mix of two levels sloshes back and forth.")),
      panel("Result (from the engine)", out.root));
    const graph = new LineGraph(L.bottom, { title: "Mean position of the superposition over one period", xLabel: "time (fs)", height: 130 });

    const run = liveRequest((s) => simulate("physics", "quantum_oscillator", { hbar_omega_ev: hw.value, n_max: Math.round(nmax.value),
      superpose_a: Number(a.value), superpose_b: Number(b.value) === Number(a.value) ? (Number(a.value) + 1) % 9 : Number(b.value), frames: 60 }, s), {
      onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result; start = performance.now();
        out.set("zp", `${fmt(res.zero_point_energy_ev, 3)} eV`); out.set("len", `${fmt(res.oscillator_length_nm, 3)} nm`); out.set("T", `${fmt(res.period_fs, 4)} fs`);
        graph.setSeries([{ name: "⟨x⟩", color: c3, x: res.times_fs, y: res.mean_x_nm }]);
      },
    });

    function draw(now) {
      if (!alive) return;
      raf = requestAnimationFrame(draw);
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const xs = res.x_nm, xmax = xs[xs.length - 1];
      const lw = w * 0.62, X = (x) => 30 + ((x + xmax) / (2 * xmax)) * (lw - 40);
      const emax = res.levels[res.levels.length - 1].energy_ev + hw.value, Y = (e) => h - 30 - (e / emax) * (h - 60);
      // potential
      ctx.strokeStyle = c2; ctx.lineWidth = 2; ctx.beginPath();
      xs.forEach((x, i) => { const v = res.potential_ev[i]; if (v > emax) return; ctx.lineTo(X(x), Y(v)); });
      ctx.stroke();
      // ladder with ψ_n drawn on each level
      const pmax = Math.max(...res.levels.flatMap((l) => l.psi.map(Math.abs)));
      res.levels.forEach((l) => {
        const y = Y(l.energy_ev);
        ctx.strokeStyle = "rgba(201,206,214,.35)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(X(-xmax), y); ctx.lineTo(X(xmax), y); ctx.stroke();
        ctx.strokeStyle = c1; ctx.lineWidth = 1.8; ctx.beginPath();
        l.psi.forEach((p, i) => { const py = y - (p / pmax) * hw.value / emax * (h - 60) * 0.42; if (i) ctx.lineTo(X(xs[i]), py); else ctx.moveTo(X(xs[i]), py); });
        ctx.stroke();
        label(ctx, `n=${l.n}  ${fmt(l.energy_ev, 3)} eV`, lw - 6, y - 8, { align: "right", color: "#c9ced6", font: "11px system-ui" });
      });
      // the superposition, animated from the engine's frames
      const nf = res.times_fs.length, f = Math.floor((((now - start) / 2600) % 1) * (nf - 1));
      const d = res.superposition_density[f], dm = Math.max(...res.superposition_density.flat());
      const x2 = lw + 20, ww = w - x2 - 20, bx = (x) => x2 + ((x + xmax) / (2 * xmax)) * ww, base = h * 0.7;
      ctx.beginPath(); ctx.moveTo(bx(-xmax), base);
      d.forEach((v, i) => ctx.lineTo(bx(xs[i]), base - (v / dm) * h * 0.45));
      ctx.lineTo(bx(xmax), base); ctx.closePath(); ctx.fillStyle = "rgba(27,175,122,.35)"; ctx.fill(); ctx.strokeStyle = c3; ctx.lineWidth = 2; ctx.stroke();
      ctx.strokeStyle = "rgba(201,206,214,.4)"; ctx.beginPath(); ctx.moveTo(bx(-xmax), base); ctx.lineTo(bx(xmax), base); ctx.stroke();
      label(ctx, `|ψ|² of (n=${a.value} + n=${b.value})/√2`, x2 + ww / 2, base + 22, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      out.set("x", `${fmt(res.mean_x_nm[f], 3)} nm`);
      graph.setCursor(res.times_fs[f]);
    }

    run();
    raf = requestAnimationFrame(draw);
    return () => { alive = false; cancelAnimationFrame(raf); run.cancel(); graph.destroy(); stage.destroy(); };
  },
};
