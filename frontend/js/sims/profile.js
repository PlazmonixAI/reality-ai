// Reaction Energy Profile: chemistry.reaction_profile gives barriers, Arrhenius rates, catalytic speed-up
// and the Maxwell-Boltzmann fraction of molecules that can climb the barrier.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, checkbox, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label, arrow, sampleAt } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";
import { axes, curve } from "./plotkit.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, hover = null;

    const ea = slider({ label: "Activation energy Ea", min: 10, max: 150, step: 1, value: 75, unit: "kJ/mol", onInput: () => { if (cat.value >= ea.value) cat.set(ea.value - 1); recompute(); } });
    const dh = slider({ label: "Reaction enthalpy ΔH", min: -120, max: 80, step: 1, value: -40, unit: "kJ/mol", onInput: () => { if (dh.value > ea.value) ea.set(dh.value); recompute(); } });
    const useCat = checkbox({ label: "Add a catalyst", value: true, onChange: () => { cat.disable(!useCat.value); recompute(); } });
    const cat = slider({ label: "Catalysed Ea", min: 5, max: 149, step: 1, value: 50, unit: "kJ/mol", onInput: () => { if (cat.value >= ea.value) ea.set(cat.value + 1); recompute(); } });
    const temp = slider({ label: "Temperature", min: 200, max: 800, step: 1, value: 298, unit: "K", onInput: () => recompute() });
    const out = readouts([
      { key: "er", label: "Reverse barrier" }, { key: "k", label: "Rate constant k (A = 10¹³ s⁻¹)" }, { key: "t", label: "Half-life" },
      { key: "f", label: "Molecules with E ≥ Ea" }, { key: "x", label: "Catalyst speed-up" }, { key: "tc", label: "Half-life with catalyst" },
    ]);
    L.side.append(
      panel("Reaction", ea.root, dh.root, useCat.root, cat.root, temp.root, legend([{ label: "uncatalysed", color: c1 }, { label: "catalysed", color: c2, dash: true }])),
      panel("Kinetics (from the engine)", out.root, el("p", { class: "note" }, "A catalyst opens a lower path: both directions speed up by the same factor, so the equilibrium doesn't move.")),
    );
    const dist = new LineGraph(L.bottom, { title: "Energy distribution of molecules (log scale): the cursor marks Ea", xLabel: "kinetic energy (kJ/mol)", yLabel: "log₁₀ (fraction per kJ/mol)", height: 150 });

    const recompute = liveRequest((signal) => simulate("chemistry", "reaction_profile", {
      activation_energy: ea.value * 1000, reaction_enthalpy: dh.value * 1000, temperature: temp.value,
      ...(useCat.value ? { catalyst_activation_energy: cat.value * 1000 } : {}),
    }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result, c = x.catalysed;
        out.set("er", `${fmt(x.reverse_activation_energy / 1000, 4)} kJ/mol`); out.set("k", `${fmt(x.k_forward, 3)} s⁻¹`);
        out.set("t", fmtTime(x.half_life_forward)); out.set("f", fmt(x.fraction_above_barrier, 3));
        out.set("x", c ? `×${fmt(c.rate_enhancement, 3)}` : "—"); out.set("tc", c ? fmtTime(c.half_life_forward) : "—");
        // Log scale so the tiny high-energy tail that actually reacts is visible
        const keep = r.distribution.density.map((d, i) => (d > 0 ? i : -1)).filter((i) => i >= 0);
        dist.setSeries([{ name: "molecules", color: c1, x: keep.map((i) => r.distribution.energy[i] / 1000), y: keep.map((i) => Math.log10(r.distribution.density[i] * 1000)) }]);
        dist.setCursor(ea.value);
        draw();
      },
    });

    stage.canvas.addEventListener("pointermove", (e) => { const b = stage.canvas.getBoundingClientRect(); hover = e.clientX - b.left; draw(); });
    stage.canvas.addEventListener("pointerleave", () => { hover = null; draw(); });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      if (!res) { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h); return; }
      const p = res.profile, x = res.result;
      const E = p.energy.map((v) => v / 1000), Ec = p.energy_catalysed?.map((v) => v / 1000);
      const lo = Math.min(0, dh.value) - 25, hi = Math.max(ea.value, 0) + 30;
      const m = axes(ctx, w, h, [-0.05, 1.05], [lo, hi], { pad: 44 });
      curve(ctx, m, p.coordinate, E, c1, { width: 3.5 });
      if (Ec) curve(ctx, m, p.coordinate, Ec, c2, { width: 3, dash: true });
      // Annotations: Ea from reactants to the top, ΔH from reactants to products
      const xr = 0.08, xp = 0.92, top = ea.value;
      ctx.setLineDash([4, 4]); ctx.strokeStyle = "#9aa6b5"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(m.X(0), m.Y(top)); ctx.lineTo(m.X(0.5), m.Y(top)); ctx.moveTo(m.X(0.5), m.Y(dh.value)); ctx.lineTo(m.X(1), m.Y(dh.value)); ctx.stroke(); ctx.setLineDash([]);
      arrow(ctx, m.X(xr), m.Y(0), m.X(xr), m.Y(top), "#16202c", 2, 8);
      label(ctx, `Ea = ${fmt(ea.value, 3)}`, m.X(xr) + 8, m.Y(top / 2), { font: "bold 12px system-ui", halo: "#fff" });
      arrow(ctx, m.X(xp), m.Y(0), m.X(xp), m.Y(dh.value), dh.value < 0 ? "#1baf7a" : "#e34948", 2, 8);
      label(ctx, `ΔH = ${fmt(dh.value, 3)}`, m.X(xp) - 8, m.Y(dh.value / 2), { align: "right", font: "bold 12px system-ui", halo: "#fff" });
      if (Ec) { arrow(ctx, m.X(0.3), m.Y(0), m.X(0.3), m.Y(cat.value), c2, 2, 8); label(ctx, `Ea(cat) = ${fmt(cat.value, 3)}`, m.X(0.3) + 8, m.Y(cat.value * 0.6), { font: "12px system-ui", color: c2, halo: "#fff" }); }
      label(ctx, "reactants", m.X(0.05), m.Y(0) + 16, { align: "center", font: "12px system-ui", color: "#4b5868" });
      label(ctx, "products", m.X(0.95), m.Y(dh.value) + 16, { align: "center", font: "12px system-ui", color: "#4b5868" });
      label(ctx, "transition state", m.X(0.5), m.Y(top) - 14, { align: "center", font: "12px system-ui", color: "#4b5868" });
      label(ctx, "energy (kJ/mol)", 48, 14, { font: "11px system-ui", color: "#7b8796" });
      label(ctx, `reaction progress → · ${x.exothermic ? "exothermic" : "endothermic"}`, w - 12, h - 12, { align: "right", font: "11px system-ui", color: "#7b8796" });
      if (hover !== null) {
        const [cx] = m.inv(hover, 0);
        if (cx >= 0 && cx <= 1) {
          const e1 = sampleAt(p.coordinate, E, cx), e2 = Ec ? sampleAt(p.coordinate, Ec, cx) : null;
          ctx.strokeStyle = "rgba(22,32,44,.3)"; ctx.beginPath(); ctx.moveTo(hover, 0); ctx.lineTo(hover, h); ctx.stroke();
          label(ctx, `E = ${fmt(e1, 3)}${e2 !== null ? ` / ${fmt(e2, 3)} (cat)` : ""} kJ/mol`, Math.min(hover + 8, w - 220), 34, { font: "bold 12px system-ui", halo: "#fff" });
        }
      }
    }

    recompute();
    return () => { recompute.cancel(); dist.destroy(); stage.destroy(); };
  },
};
