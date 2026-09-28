// Colligative Properties: chemistry.colligative_properties — boiling-point elevation, freezing-point depression, osmosis.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Solute formula and ideal van 't Hoff factor (particles per formula unit).
const SOLUTES = { NaCl: ["Table salt NaCl", 2], CaCl2: ["Road salt CaCl₂", 3], C12H22O11: ["Sugar (sucrose)", 1], C6H12O6: ["Glucose", 1], C2H6O2: ["Antifreeze (ethylene glycol)", 1], CH4N2O: ["Urea", 1] };
const SOLVENTS = { water: "Water", benzene: "Benzene", cyclohexane: "Cyclohexane", acetic_acid: "Acetic acid" };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null;

    const solute = select({ label: "Solute", value: "NaCl", options: Object.entries(SOLUTES).map(([v, [l]]) => ({ value: v, label: l })), onChange: () => recompute() });
    const solvent = select({ label: "Solvent", value: "water", options: Object.entries(SOLVENTS).map(([v, l]) => ({ value: v, label: l })), onChange: () => recompute() });
    const mass = slider({ label: "Solute dissolved", min: 0, max: 300, step: 1, value: 58, unit: "g", onInput: () => recompute() });
    const solv = slider({ label: "Solvent mass", min: 0.1, max: 2, step: 0.05, value: 1, unit: "kg", onInput: () => recompute() });
    const out = readouts([
      { key: "m", label: "Molality (particles)" }, { key: "fp", label: "Freezing point" }, { key: "bp", label: "Boiling point" },
      { key: "vp", label: "Vapour pressure vs pure" }, { key: "os", label: "Osmotic pressure" },
    ]);
    L.side.append(
      panel("Solution", solute.root, solvent.root, mass.root, solv.root, el("p", { class: "note" }, "Only the number of dissolved particles matters: salt splits into 2 ions, so it counts double.")),
      panel("Properties (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "Freezing-point drop and boiling-point rise as you add solute", xLabel: "solute (g)", yLabel: "ΔT (K)", height: 150, includeZero: true });

    const args = (g) => ({ formula: solute.value, solute_mass: g, solvent_mass: solv.value, van_t_hoff: SOLUTES[solute.value][1], solvent: solvent.value });
    const recompute = liveRequest(async (signal) => {
      const now = await simulate("chemistry", "colligative_properties", args(mass.value), signal);
      const gs = Array.from({ length: 13 }, (_, i) => i * 25);
      const line = await Promise.all(gs.map((g) => simulate("chemistry", "colligative_properties", args(g), signal)));
      return { now, gs, line };
    }, {
      delay: 40, onError: (e) => L.error(e.message),
      onResult: ({ now, gs, line }) => {
        L.clearError(); res = now;
        const x = now.result;
        out.set("m", `${fmt(x.particle_molality, 4)} mol/kg`); out.set("fp", `${fmt(x.freezing_point, 4)} °C (−${fmt(x.freezing_point_depression, 3)} K)`);
        out.set("bp", `${fmt(x.boiling_point, 5)} °C (+${fmt(x.boiling_point_elevation, 3)} K)`); out.set("vp", `${fmt(x.vapour_pressure_ratio * 100, 4)} %`);
        out.set("os", `${fmt(x.osmotic_pressure_atm, 4)} atm`);
        graph.setSeries([
          { name: "freezing-point drop", color: c1, x: gs, y: line.map((l) => l.result.freezing_point_depression) },
          { name: "boiling-point rise", color: c2, x: gs, y: line.map((l) => l.result.boiling_point_elevation) },
        ]);
        graph.setCursor(mass.value);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const x = res.result, s = res.solvent;
      // Temperature scale from below the new freezing point to above the new boiling point
      const lo = Math.min(s.freezing_point, x.freezing_point) - 10, hi = Math.max(s.boiling_point, x.boiling_point) + 10;
      const X = (t) => 60 + ((t - lo) / (hi - lo)) * (w - 120), y = h * 0.45;
      ctx.fillStyle = "#dbe9f7"; ctx.fillRect(X(s.freezing_point), y - 16, X(s.boiling_point) - X(s.freezing_point), 12);
      ctx.fillStyle = "#2a78d6"; ctx.fillRect(X(x.freezing_point), y + 4, X(x.boiling_point) - X(x.freezing_point), 12);
      label(ctx, `pure ${SOLVENTS[s.name].toLowerCase()} is liquid`, X(s.freezing_point), y - 28, { font: "12px system-ui", color: "#4b5868" });
      label(ctx, "the solution is liquid", X(x.freezing_point), y + 30, { font: "bold 12px system-ui", color: "#2a78d6" });
      ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(60, y + 50); ctx.lineTo(w - 60, y + 50); ctx.stroke();
      const step = (hi - lo) > 100 ? 20 : 10;
      for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) { ctx.beginPath(); ctx.moveTo(X(t), y + 46); ctx.lineTo(X(t), y + 54); ctx.stroke(); label(ctx, `${t}`, X(t), y + 66, { align: "center", font: "11px system-ui", color: "#4b5868" }); }
      label(ctx, "°C", w - 50, y + 66, { font: "11px system-ui", color: "#4b5868" });
      label(ctx, `freezes at ${fmt(x.freezing_point, 4)} °C`, X(x.freezing_point), y + 88, { align: "center", font: "bold 12px system-ui", color: c1 });
      label(ctx, `boils at ${fmt(x.boiling_point, 5)} °C`, X(x.boiling_point), y + 108, { align: "center", font: "bold 12px system-ui", color: c2 });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
