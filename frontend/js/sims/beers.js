// Beer's Law Lab: absorbance_spectrum and beer_lambert from the engine drive the spectrophotometer.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, sampleAt, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";
import { wavelengthRGB } from "./interference.js";

// Single-band approximations of real solutions (illustrative values, not reference data).
const SOLUTIONS = {
  permanganate: { label: "Potassium permanganate (approx.)", bands: [{ wavelength: 525, epsilon: 2400, width: 30 }], c: 1e-4 },
  chromate: { label: "Potassium chromate (approx.)", bands: [{ wavelength: 372, epsilon: 4800, width: 30 }], c: 3e-4 },
  copper: { label: "Copper(II) sulfate (approx.)", bands: [{ wavelength: 800, epsilon: 12, width: 90 }], c: 0.05 },
  custom: { label: "Custom single band", bands: null, c: 1e-3 },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let spec = null;

    const solution = select({ label: "Solution", value: "permanganate", options: Object.entries(SOLUTIONS).map(([v, s]) => ({ value: v, label: s.label })), onChange: (v) => { conc.set(SOLUTIONS[v].c); sync(); recompute(); } });
    const peak = slider({ label: "Band peak", min: 380, max: 780, step: 1, value: 500, unit: "nm", onInput: () => recompute() });
    const eps = slider({ label: "Peak molar absorptivity ε", min: 10, max: 50000, value: 5000, log: true, unit: "L/(mol·cm)", onInput: () => recompute() });
    const lam = slider({ label: "Light wavelength", min: 380, max: 780, step: 1, value: 525, unit: "nm", onInput: () => recompute() });
    const conc = slider({ label: "Concentration", min: 1e-6, max: 0.2, value: 1e-4, log: true, format: (v) => `${fmt(v * 1000, 3)} mM`, onInput: () => recompute() });
    const path = slider({ label: "Cuvette width (path length)", min: 0.5, max: 2, step: 0.1, value: 1, unit: "cm", onInput: () => recompute() });
    const out = readouts([{ key: "a", label: "Absorbance" }, { key: "t", label: "Transmittance" }, { key: "eps", label: "ε at this wavelength" }, { key: "lmax", label: "λ max" }]);
    function sync() { const custom = solution.value === "custom"; peak.root.style.display = eps.root.style.display = custom ? "" : "none"; }
    L.side.append(
      panel("Sample", solution.root, peak.root, eps.root, conc.root, path.root),
      panel("Spectrophotometer", lam.root),
      panel("Reading (from the engine)", out.root),
    );
    sync();
    const specGraph = new LineGraph(L.bottom, { title: "Absorbance spectrum", xLabel: "wavelength (nm)", yLabel: "absorbance", height: 140, includeZero: true });
    const lawGraph = new LineGraph(L.bottom, { title: "Beer's law at this wavelength", xLabel: "concentration (mM)", yLabel: "absorbance", height: 120, includeZero: true });

    const bands = () => SOLUTIONS[solution.value].bands || [{ wavelength: peak.value, epsilon: eps.value, width: 30 }];
    const recompute = liveRequest(async (signal) => {
      const s = await simulate("chemistry", "absorbance_spectrum", { bands: bands(), concentration: conc.value, path_length: path.value, probe: lam.value, wl_max: 800 }, signal);
      const e = s.result.probe_epsilon;
      const cs = Array.from({ length: 11 }, (_, i) => (conc.value * 2 * i) / 10);
      const line = e > 0 ? await Promise.all(cs.map((c) => simulate("chemistry", "beer_lambert", { absorptivity: e, path_length: path.value, concentration: c }, signal))) : [];
      return { s, cs, line };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ s, cs, line }) => {
        L.clearError(); spec = s;
        const r = s.result;
        out.set("a", fmt(r.probe_absorbance, 4)); out.set("t", `${fmt(r.probe_transmittance * 100, 4)} %`);
        out.set("eps", `${fmt(r.probe_epsilon, 4)} L/(mol·cm)`); out.set("lmax", `${fmt(r.lambda_max, 4)} nm`);
        specGraph.setSeries([{ name: "Absorbance", color: c1, x: s.spectrum.wavelength, y: s.spectrum.absorbance }]);
        specGraph.setCursor(lam.value);
        lawGraph.setSeries(line.length ? [{ name: "Absorbance", color: c2, x: cs.map((c) => c * 1000), y: line.map((l) => l.result.absorbance) }] : []);
        lawGraph.setCursor(conc.value * 1000);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#1a2230"; ctx.fillRect(0, 0, w, h);
      const y = h / 2, rgb = wavelengthRGB(lam.value);
      const T = spec ? spec.result.probe_transmittance : 1;
      // Source
      ctx.fillStyle = "#39424e"; ctx.fillRect(20, y - 40, 90, 80);
      label(ctx, `${lam.value} nm`, 65, y + 56, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      ctx.fillStyle = `rgb(${rgb.join(",")})`; ctx.beginPath(); ctx.arc(110, y, 8, 0, Math.PI * 2); ctx.fill();
      // Cuvette with the solution's colour (transmittance at blue / green / red from the engine spectrum)
      const cx = w * 0.45, cw = 40 * path.value;
      let tint = "rgba(255,255,255,.15)";
      if (spec) {
        const tr = (nm) => sampleAt(spec.spectrum.wavelength, spec.spectrum.transmittance, nm);
        tint = `rgba(${Math.round(255 * tr(620))},${Math.round(255 * tr(540))},${Math.round(255 * tr(460))},0.9)`;
      }
      ctx.fillStyle = tint; ctx.fillRect(cx - cw / 2, y - 70, cw, 140);
      ctx.strokeStyle = "#dfe6ee"; ctx.lineWidth = 2; ctx.strokeRect(cx - cw / 2, y - 80, cw, 150);
      label(ctx, `${fmt(path.value, 2)} cm`, cx, y + 92, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      // Beam in and out (brightness ~ transmitted fraction)
      ctx.strokeStyle = `rgba(${rgb.join(",")},0.95)`; ctx.lineWidth = 10;
      ctx.beginPath(); ctx.moveTo(118, y); ctx.lineTo(cx - cw / 2, y); ctx.stroke();
      ctx.strokeStyle = `rgba(${rgb.join(",")},${Math.max(0.03, T)})`;
      ctx.beginPath(); ctx.moveTo(cx + cw / 2, y); ctx.lineTo(w - 150, y); ctx.stroke();
      // Detector
      ctx.fillStyle = "#39424e"; ctx.fillRect(w - 150, y - 50, 130, 100);
      ctx.fillStyle = "#c9f0d8"; ctx.fillRect(w - 140, y - 38, 110, 76);
      label(ctx, spec ? `A = ${fmt(spec.result.probe_absorbance, 3)}` : "…", w - 85, y - 12, { align: "center", font: "bold 16px ui-monospace, monospace", color: "#133b25" });
      label(ctx, spec ? `T = ${fmt(T * 100, 3)}%` : "", w - 85, y + 16, { align: "center", font: "bold 14px ui-monospace, monospace", color: "#133b25" });
      label(ctx, "light source", 65, y - 56, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      label(ctx, "detector", w - 85, y - 64, { align: "center", color: "#c9ced6", font: "12px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); specGraph.destroy(); lawGraph.destroy(); stage.destroy(); };
  },
};
