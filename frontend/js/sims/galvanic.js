// Galvanic Cell: chemistry.galvanic_cell gives E°, the Nernst potential, ΔG and K for two metal electrodes.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, arrow } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Display colours for each electrode material and its ion solution (illustrative).
const METALS = {
  Zn: ["Zinc", "#9aa6b5", "rgba(220,230,240,.5)"], Cu: ["Copper", "#c46a2c", "rgba(60,130,230,.45)"],
  Ag: ["Silver", "#d9dee5", "rgba(220,230,240,.5)"], Fe: ["Iron", "#6b6f76", "rgba(150,200,140,.45)"],
  Ni: ["Nickel", "#a5a28e", "rgba(90,190,110,.45)"], Pb: ["Lead", "#5b6270", "rgba(220,230,240,.5)"],
  Mg: ["Magnesium", "#c9ced6", "rgba(220,230,240,.5)"], Al: ["Aluminium", "#b8c4d3", "rgba(220,230,240,.5)"],
  Au: ["Gold", "#e3b53a", "rgba(240,220,120,.45)"], H2: ["Hydrogen (Pt, 1 bar H₂)", "#e8ecf2", "rgba(220,230,240,.5)"],
};
const opts = Object.entries(METALS).map(([v, [l]]) => ({ value: v, label: l }));

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1] = SERIES();
    let res = null, t = 0;

    const anode = select({ label: "Left electrode (anode if E > 0)", value: "Zn", options: opts, onChange: () => recompute() });
    const cathode = select({ label: "Right electrode (cathode if E > 0)", value: "Cu", options: opts, onChange: () => recompute() });
    const ca = slider({ label: "Left ion concentration", min: 1e-4, max: 2, value: 1, log: true, unit: "M", onInput: () => recompute() });
    const cc = slider({ label: "Right ion concentration", min: 1e-4, max: 2, value: 1, log: true, unit: "M", onInput: () => recompute() });
    const temp = slider({ label: "Temperature", min: 273, max: 373, step: 1, value: 298, unit: "K", onInput: () => recompute() });
    const out = readouts([
      { key: "e0", label: "Standard potential E°" }, { key: "e", label: "Cell potential E (Nernst)" }, { key: "n", label: "Electrons transferred n" },
      { key: "dg", label: "ΔG = −nFE" }, { key: "k", label: "Equilibrium constant K" }
    ]);
    const rx = el("p", { class: "note" });
    L.side.append(
      panel("Cell", anode.root, cathode.root, ca.root, cc.root, temp.root, el("p", { class: "note" }, "Electrons flow through the wire from the more easily oxidised metal; the salt bridge closes the circuit.")),
      panel("Cell (from the engine)", out.root, rx),
    );
    const graph = new LineGraph(L.bottom, { title: "Nernst equation: E falls as products build up", xLabel: "log₁₀ Q", yLabel: "E (V)", height: 150 });

    const recompute = liveRequest((signal) => simulate("chemistry", "galvanic_cell", {
      anode: anode.value, cathode: cathode.value, anode_concentration: ca.value, cathode_concentration: cc.value, temperature: temp.value,
    }, signal), {
      delay: 30, onError: (e) => { res = null; rx.textContent = ""; L.error(e.message); },
      onResult: (r) => {
        L.clearError(); res = r.result;
        out.set("e0", `${fmt(res.standard_potential, 4)} V`); out.set("e", `${fmt(res.cell_potential, 4)} V`);
        out.set("n", String(res.electrons_transferred)); out.set("dg", `${fmt(res.delta_g / 1000, 4)} kJ/mol`);
        out.set("k", `10^${fmt(res.log10_k, 4)}`); rx.textContent = res.spontaneous ? `Reaction: ${res.overall}` : `E < 0: the reaction runs the other way (${res.overall} is not spontaneous).`;
        graph.setSeries([{ name: "E", color: c1, x: r.nernst_curve.log10_q, y: r.nernst_curve.potential }]);
        graph.setCursor(res.log10_q);
      },
    });

    function cup(ctx, x, y, cw, ch, metal) {
      ctx.fillStyle = METALS[metal][2]; ctx.fillRect(x, y + ch * 0.25, cw, ch * 0.75);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y + ch); ctx.lineTo(x + cw, y + ch); ctx.lineTo(x + cw, y); ctx.stroke();
      ctx.fillStyle = METALS[metal][1]; ctx.fillRect(x + cw / 2 - 12, y - 30, 24, ch * 0.85);
      ctx.strokeStyle = "rgba(0,0,0,.25)"; ctx.lineWidth = 1; ctx.strokeRect(x + cw / 2 - 12, y - 30, 24, ch * 0.85);
    }

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      const cw = Math.min(220, w * 0.28), ch = Math.min(220, h * 0.45), y = h * 0.4;
      const xl = w * 0.27 - cw / 2, xr = w * 0.73 - cw / 2;
      cup(ctx, xl, y, cw, ch, anode.value); cup(ctx, xr, y, cw, ch, cathode.value);
      // Salt bridge
      ctx.strokeStyle = "#d9c9a3"; ctx.lineWidth = 22; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(xl + cw * 0.8, y + ch * 0.55); ctx.lineTo(xl + cw * 0.8, y - 10); ctx.lineTo(xr + cw * 0.2, y - 10); ctx.lineTo(xr + cw * 0.2, y + ch * 0.55); ctx.stroke();
      ctx.lineCap = "butt";
      label(ctx, "salt bridge (KNO₃)", w / 2, y - 10, { align: "center", font: "11px system-ui", color: "#4b5868" });
      // Wire and voltmeter
      const ax = xl + cw / 2, bx = xr + cw / 2, wy = y - 110;
      ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.moveTo(ax, y - 30); ctx.lineTo(ax, wy); ctx.lineTo(bx, wy); ctx.lineTo(bx, y - 30); ctx.stroke();
      ctx.fillStyle = "#16202c"; ctx.fillRect(w / 2 - 60, wy - 28, 120, 56);
      ctx.fillStyle = "#1baf7a"; ctx.font = "bold 22px ui-monospace, monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(res ? `${res.cell_potential >= 0 ? "" : "−"}${Math.abs(res.cell_potential).toFixed(3)} V` : "–", w / 2, wy);
      ctx.textAlign = "left";
      label(ctx, `${METALS[anode.value][0]}, ${fmt(ca.value, 3)} M`, xl + cw / 2, y + ch + 20, { align: "center", font: "bold 12px system-ui" });
      label(ctx, `${METALS[cathode.value][0]}, ${fmt(cc.value, 3)} M`, xr + cw / 2, y + ch + 20, { align: "center", font: "bold 12px system-ui" });
      if (!res) return;
      const fwd = res.cell_potential > 0;
      label(ctx, fwd ? "anode (−) oxidation" : "cathode (+) reduction", ax, y + ch + 38, { align: "center", font: "11px system-ui", color: "#4b5868" });
      label(ctx, fwd ? "cathode (+) reduction" : "anode (−) oxidation", bx, y + ch + 38, { align: "center", font: "11px system-ui", color: "#4b5868" });
      // Electrons: speed grows with |E| (illustrative)
      t += dt * (0.3 + Math.min(2, Math.abs(res.cell_potential)));
      const path = [[ax, y - 30], [ax, wy], [bx, wy], [bx, y - 30]];
      const segs = [wy - (y - 30), bx - ax, (y - 30) - wy].map(Math.abs), total = segs.reduce((s, v) => s + v, 0);
      ctx.fillStyle = "#2a78d6";
      for (let i = 0; i < 14; i++) {
        let d = ((i / 14 + t * 0.25) % 1) * total;
        if (!fwd) d = total - d;
        let k = 0; while (k < 2 && d > segs[k]) { d -= segs[k]; k++; }
        const [x0, y0] = path[k], [x1, y1] = path[k + 1], f = d / segs[k];
        const px = x0 + (x1 - x0) * f, py = y0 + (y1 - y0) * f;
        if (Math.abs(px - w / 2) < 62 && Math.abs(py - wy) < 30) continue;
        ctx.beginPath(); ctx.arc(px, py, 4, 0, Math.PI * 2); ctx.fill();
      }
      arrow(ctx, fwd ? w / 2 - 110 : w / 2 + 110, wy - 22, fwd ? w / 2 - 75 : w / 2 + 75, wy - 22, "#2a78d6", 2, 7);
      label(ctx, "e⁻", fwd ? w / 2 - 92 : w / 2 + 92, wy - 36, { align: "center", color: "#2a78d6", font: "bold 12px system-ui" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
