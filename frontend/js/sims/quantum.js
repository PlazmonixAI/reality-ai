// Quantum Wells: physics.quantum_well gives energy levels and wavefunctions of a particle in a 1D well.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";

const HBAR_EV = 6.582119569e-16; // ħ in eV·s, to convert the ħω slider to ω (rad/s)

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2] = SERIES();
    let res = null, phase = 0;

    const well = segmented({ label: "Well", value: "infinite", options: [{ value: "infinite", label: "Infinite box" }, { value: "finite", label: "Finite well" }, { value: "harmonic", label: "Harmonic" }], onChange: () => { sync(); recompute(); } });
    const width = slider({ label: "Well width", min: 0.2, max: 3, step: 0.05, value: 1, unit: "nm", onInput: () => recompute() });
    const depth = slider({ label: "Well depth", min: 0.2, max: 20, step: 0.1, value: 5, unit: "eV", onInput: () => recompute() });
    const hw = slider({ label: "Level spacing ħω", min: 0.1, max: 3, step: 0.05, value: 1, unit: "eV", onInput: () => recompute() });
    const show = segmented({ label: "Draw", value: "psi", options: [{ value: "psi", label: "ψ (animated phase)" }, { value: "prob", label: "|ψ|² (probability)" }], onChange: () => {} });
    const pick = slider({ label: "Highlight level n", min: 1, max: 6, step: 1, value: 1, onInput: () => {} });
    const out = readouts([{ key: "e", label: "Energy levels" }, { key: "n", label: "Bound states" }, { key: "l", label: "Photon for n=2 → 1" }]);
    function sync() { width.root.style.display = well.value === "harmonic" ? "none" : ""; depth.root.style.display = well.value === "finite" ? "" : "none"; hw.root.style.display = well.value === "harmonic" ? "" : "none"; }
    L.side.append(
      panel("Electron in a well", well.root, width.root, depth.root, hw.root, show.root, pick.root, el("p", { class: "note" }, "Confinement quantises energy: only standing waves fit. Narrower wells mean higher, wider-spaced levels.")),
      panel("States (from the engine)", out.root),
    );
    sync();

    const recompute = liveRequest((signal) => simulate("physics", "quantum_well", {
      well: well.value, width_nm: width.value, depth_ev: depth.value, omega: hw.value / HBAR_EV, particle: "electron", n_levels: 6, n_grid: 1500,
    }, signal), {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("e", x.energies_ev.map((e) => fmt(e, 3)).join(", ") + " eV");
        out.set("n", well.value === "finite" ? `${x.bound_states} (of the first 6 asked)` : `${x.bound_states} shown`);
        out.set("l", x.transition_wavelengths_nm.length ? `${fmt(x.transition_wavelengths_nm[0], 4)} nm` : "–");
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      phase += dt;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const xs = res.x_nm, es = res.result.energies_ev, n = es.length;
      const top = well.value === "finite" ? depth.value * 1.15 : es[n - 1] * 1.15, x0 = xs[0], x1 = xs[xs.length - 1];
      const pad = 50, padR = 110, X = (x) => pad + ((x - x0) / (x1 - x0)) * (w - pad - padR), Y = (e) => h - 30 - (e / top) * (h - 60);
      // Potential
      ctx.strokeStyle = "#c9ced6"; ctx.lineWidth = 3; ctx.beginPath();
      if (well.value === "infinite") { ctx.moveTo(X(0), 20); ctx.lineTo(X(0), Y(0)); ctx.lineTo(X(x1), Y(0)); ctx.lineTo(X(x1), 20); }
      else res.potential_ev.forEach((v, i) => { const y = Y(Math.min(v, top * 1.2)); if (i) ctx.lineTo(X(xs[i]), y); else ctx.moveTo(X(xs[i]), y); });
      ctx.stroke();
      // Levels and wavefunctions drawn on their energy baselines
      es.forEach((e, j) => {
        // Scale each state by its own spacing to the neighbouring levels so none overlap
        const gap = Math.min(j > 0 ? e - es[j - 1] : Infinity, j < n - 1 ? es[j + 1] - e : Infinity, n > 1 ? Infinity : top / 3);
        const on = j + 1 === pick.value;
        ctx.strokeStyle = on ? "#fff" : "rgba(201,206,214,.35)"; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(pad, Y(e)); ctx.lineTo(w - padR, Y(e)); ctx.stroke(); ctx.setLineDash([]);
        label(ctx, `n=${j + 1}: ${fmt(e, 3)} eV`, w - padR + 6, Y(e), { color: on ? "#fff" : "#7b8796", font: "11px system-ui" });
        const arr = show.value === "psi" ? res.wavefunctions[j] : res.densities[j], amp = Math.max(...arr.map(Math.abs)) || 1;
        const scaleE = 0.42 * gap / amp, osc = show.value === "psi" ? Math.cos(phase * 2 * (j + 1)) : 1;
        ctx.strokeStyle = on ? c2 : c1; ctx.lineWidth = on ? 2.5 : 1.5; ctx.globalAlpha = on ? 1 : 0.7; ctx.beginPath();
        arr.forEach((v, i) => { const y = Y(e + v * scaleE * osc); if (i) ctx.lineTo(X(xs[i]), y); else ctx.moveTo(X(xs[i]), y); });
        ctx.stroke(); ctx.globalAlpha = 1;
      });
      label(ctx, `x (nm): ${fmt(x0, 3)} … ${fmt(x1, 3)}`, pad, h - 10, { color: "#7b8796", font: "11px system-ui" });
      if (show.value === "psi") label(ctx, "ψ oscillates in time as e^(−iEt/ħ) (phase animated, not to scale)", w - padR, 14, { align: "right", color: "#7b8796", font: "11px system-ui" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
