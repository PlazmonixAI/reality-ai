// Molarity & Dilution: chemistry.molarity_dilution computes molar mass (from the formula), moles and concentration.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Colours are for display only (typical appearance of the aqueous ions).
const SOLUTES = {
  CuSO4: { label: "Copper(II) sulfate, CuSO₄", rgb: [40, 110, 220] },
  KMnO4: { label: "Potassium permanganate, KMnO₄", rgb: [130, 20, 140] },
  K2Cr2O7: { label: "Potassium dichromate, K₂Cr₂O₇", rgb: [235, 110, 20] },
  CoCl2: { label: "Cobalt(II) chloride, CoCl₂", rgb: [220, 60, 120] },
  NiCl2: { label: "Nickel(II) chloride, NiCl₂", rgb: [40, 170, 80] },
  NaCl: { label: "Sodium chloride, NaCl", rgb: [200, 210, 220] },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1] = SERIES();
    let res = null;

    const solute = select({ label: "Solute", value: "CuSO4", options: Object.entries(SOLUTES).map(([v, s]) => ({ value: v, label: s.label })), onChange: () => recompute() });
    const mass = slider({ label: "Mass dissolved", min: 0, max: 50, step: 0.1, value: 8, unit: "g", onInput: () => recompute() });
    const vol = slider({ label: "Solution volume", min: 50, max: 1000, step: 10, value: 250, unit: "mL", onInput: () => { if (dil.value < vol.value) dil.set(vol.value); recompute(); } });
    const dil = slider({ label: "Dilute with water to", min: 50, max: 2000, step: 10, value: 250, unit: "mL", onInput: () => { if (dil.value < vol.value) dil.set(vol.value); recompute(); } });
    const out = readouts([
      { key: "mm", label: "Molar mass" }, { key: "n", label: "Amount of solute" }, { key: "c1", label: "Concentration (before)" },
      { key: "c2", label: "Concentration (after dilution)" }, { key: "g", label: "Mass concentration" },
    ]);
    L.side.append(
      panel("Make a solution", solute.root, mass.root, vol.root, dil.root, el("p", { class: "note" }, "Adding water spreads the same moles through more volume: C₁V₁ = C₂V₂.")),
      panel("Solution (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "Concentration as water is added", xLabel: "final volume (mL)", yLabel: "mol/L", height: 150, includeZero: true });

    const args = (v2) => ({ formula: solute.value, solute_mass: mass.value, volume: vol.value * 1e-6, final_volume: v2 * 1e-6 });
    const recompute = liveRequest(async (signal) => {
      const now = await simulate("chemistry", "molarity_dilution", args(dil.value), signal);
      const vs = Array.from({ length: 13 }, (_, i) => vol.value * (1 + i * 0.25));
      const line = await Promise.all(vs.map((v) => simulate("chemistry", "molarity_dilution", args(v), signal)));
      return { now, vs, line };
    }, {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ now, vs, line }) => {
        L.clearError(); res = now.result;
        out.set("mm", `${fmt(res.molar_mass, 5)} g/mol`); out.set("n", `${fmt(res.moles * 1000, 4)} mmol`);
        out.set("c1", `${fmt(res.concentration_before_dilution, 4)} mol/L`); out.set("c2", `${fmt(res.concentration, 4)} mol/L`);
        out.set("g", `${fmt(res.mass_concentration, 4)} g/L`);
        graph.setSeries([{ name: "Concentration", color: c1, x: vs, y: line.map((l) => l.result.concentration) }]);
        graph.setCursor(dil.value);
        draw();
      },
    });

    function beaker(ctx, x, y, bw, bh, fill, conc, title) {
      const cap = 2000, lh = (bh - 10) * Math.min(1, fill / cap);
      const rgb = SOLUTES[solute.value].rgb;
      // Colour intensity from absorbance-like saturation of concentration (display only)
      const alpha = Math.min(0.92, 0.08 + 1 - Math.exp(-conc * 6));
      ctx.fillStyle = `rgba(${rgb.join(",")},${alpha})`;
      ctx.fillRect(x + 3, y + bh - lh, bw - 6, lh - 3);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(x - 6, y); ctx.lineTo(x, y + 6); ctx.lineTo(x, y + bh); ctx.lineTo(x + bw, y + bh); ctx.lineTo(x + bw, y); ctx.stroke();
      ctx.lineWidth = 1; ctx.strokeStyle = "#9aa6b5";
      for (let m = 250; m <= cap; m += 250) { const yy = y + bh - (bh - 10) * m / cap; ctx.beginPath(); ctx.moveTo(x + bw - 18, yy); ctx.lineTo(x + bw, yy); ctx.stroke(); label(ctx, `${m}`, x + bw + 4, yy, { font: "10px system-ui", color: "#7b8796" }); }
      label(ctx, title, x + bw / 2, y + bh + 22, { align: "center", font: "bold 13px system-ui" });
      label(ctx, `${fmt(fill, 4)} mL · ${fmt(conc, 3)} M`, x + bw / 2, y + bh + 40, { align: "center", font: "12px system-ui", color: "#4b5868" });
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const bw = Math.min(200, w * 0.28), bh = Math.min(h - 110, 360), y = 40;
      beaker(ctx, w * 0.25 - bw / 2, y, bw, bh, vol.value, res.concentration_before_dilution, "Stock solution");
      beaker(ctx, w * 0.72 - bw / 2, y, bw, bh, dil.value, res.concentration, `Diluted ×${fmt(res.dilution_factor, 3)}`);
      ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 2; ctx.setLineDash([6, 5]);
      ctx.beginPath(); ctx.moveTo(w * 0.25 + bw / 2 + 30, y + bh / 2); ctx.lineTo(w * 0.72 - bw / 2 - 30, y + bh / 2); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, "+ water", w * 0.485, y + bh / 2 - 14, { align: "center", color: "#4b5868" });
      label(ctx, "colour depth is illustrative", w - 12, h - 10, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
