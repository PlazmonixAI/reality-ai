// Real Gases: chemistry.van_der_waals gives isotherms, the critical point and Maxwell's equal-area tie line.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { axes, curve } from "./plotkit.js";

// Textbook van der Waals constants: a in Pa·m⁶/mol², b in m³/mol.
const GASES = {
  CO2: ["Carbon dioxide", 0.3640, 4.267e-5], H2O: ["Water", 0.5536, 3.049e-5], NH3: ["Ammonia", 0.4225, 3.707e-5],
  N2: ["Nitrogen", 0.1370, 3.87e-5], He: ["Helium", 0.00346, 2.38e-5],
};
const R = 8.314462618;
const tcOf = (g) => (8 * GASES[g][1]) / (27 * R * GASES[g][2]);

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let res = null, dome = [], hover = null, m = null;

    const gas = select({ label: "Gas", value: "CO2", options: Object.entries(GASES).map(([v, [l]]) => ({ value: v, label: l })), onChange: () => { rescale(); recompute(); } });
    const tr = slider({ label: "Temperature", min: 0.6, max: 1.6, step: 0.005, value: 0.9, format: (v) => `${fmt(v * tcOf(gas.value), 4)} K (${fmt(v, 3)} Tc)`, onInput: () => recompute() });
    const vr = slider({ label: "Molar volume", min: 1.3, max: 40, value: 8, log: true, format: (v) => `${fmt(v * GASES[gas.value][2] * 1000, 3)} L/mol`, onInput: () => recompute() });
    function rescale() { tr.set(tr.value); vr.set(vr.value); }
    const out = readouts([
      { key: "tc", label: "Critical point" }, { key: "p", label: "Pressure (real)" }, { key: "pi", label: "Pressure if ideal" },
      { key: "z", label: "Compressibility Z = PV/RT" }, { key: "ph", label: "Phase" }, { key: "ps", label: "Vapour pressure" },
    ]);
    L.side.append(
      panel("Gas", gas.root, tr.root, vr.root, legend([{ label: "real (with tie line)", color: c1 }, { label: "van der Waals loop", color: c2, dash: true }, { label: "ideal gas", color: c3 }])),
      panel("State (from the engine)", out.root, el("p", { class: "note" }, "Below the critical temperature, squeezing the gas condenses it: pressure stays flat while liquid forms.")),
    );

    const loadDome = liveRequest(async (signal) => {
      const [, a, b] = GASES[gas.value], tc = tcOf(gas.value);
      const trs = [0.75, 0.78, 0.81, 0.84, 0.87, 0.9, 0.92, 0.94, 0.96, 0.975, 0.985, 0.992, 0.997];
      const rs = await Promise.all(trs.map((x) => simulate("chemistry", "van_der_waals", { a, b, temperature: x * tc, n_points: 20 }, signal)));
      return rs.map((r) => r.result.saturation).filter(Boolean);
    }, { delay: 0, onResult: (d) => { dome = d; draw(); } });

    let lastGas = null;
    const recompute = liveRequest((signal) => {
      const [, a, b] = GASES[gas.value];
      return simulate("chemistry", "van_der_waals", { a, b, temperature: tr.value * tcOf(gas.value), molar_volume: vr.value * b, v_max_factor: 45, n_points: 500 }, signal);
    }, {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        if (lastGas !== gas.value) { lastGas = gas.value; loadDome(); }
        const x = r.result, s = x.state;
        out.set("tc", `${fmt(x.critical_temperature, 4)} K, ${fmt(x.critical_pressure / 1e5, 4)} bar`);
        out.set("p", `${fmt(s.pressure / 1e5, 4)} bar`); out.set("pi", `${fmt(s.ideal_pressure / 1e5, 4)} bar`);
        out.set("z", fmt(s.compressibility, 4));
        out.set("ph", s.vapour_fraction !== null ? `${s.phase} (${fmt(s.vapour_fraction * 100, 3)} % vapour)` : s.phase);
        out.set("ps", x.saturation ? `${fmt(x.saturation.pressure / 1e5, 4)} bar` : "— (above Tc)");
        draw();
      },
    });

    stage.canvas.addEventListener("pointermove", (e) => { const r = stage.canvas.getBoundingClientRect(); hover = [e.clientX - r.left, e.clientY - r.top]; draw(); });
    stage.canvas.addEventListener("pointerleave", () => { hover = null; draw(); });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const x = res.result, iso = res.isotherm, pc = x.critical_pressure / 1e5;
      const V = iso.molar_volume.map((v) => v * 1000);
      const plotW = w - 150;
      ctx.save(); ctx.beginPath(); ctx.rect(0, 0, plotW, h); ctx.clip();
      m = axes(ctx, plotW, h, [0, V[V.length - 1]], [-0.25 * pc, 2.2 * pc], { pad: 40 });
      // Coexistence dome from the tie lines at several temperatures
      if (dome.length) {
        const left = dome.map((d) => [d.v_liquid * 1000, d.pressure / 1e5]), right = dome.map((d) => [d.v_gas * 1000, d.pressure / 1e5]).reverse();
        const pts = [...left, [x.critical_molar_volume * 1000, pc], ...right];
        ctx.fillStyle = "rgba(123,135,150,.12)"; ctx.strokeStyle = "rgba(123,135,150,.6)"; ctx.lineWidth = 1.5;
        ctx.beginPath(); pts.forEach(([a, b], i) => (i ? ctx.lineTo(m.X(a), m.Y(b)) : ctx.moveTo(m.X(a), m.Y(b)))); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#fff"; ctx.fillRect(m.X(pts[0][0]) - 2, m.Y(pts[0][1]) - 0.5, m.X(pts[pts.length - 1][0]) - m.X(pts[0][0]) + 4, 2);
        label(ctx, "liquid + vapour", m.X(x.critical_molar_volume * 1000 * 2.2), m.Y(pc * 0.25), { align: "center", color: "#7b8796", font: "11px system-ui" });
      }
      curve(ctx, m, V, iso.pressure_ideal.map((p) => p / 1e5), c3, { width: 2 });
      curve(ctx, m, V, iso.pressure_vdw.map((p) => p / 1e5), c2, { width: 2, dash: true });
      curve(ctx, m, V, iso.pressure_physical.map((p) => p / 1e5), c1, { width: 3 });
      ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(m.X(x.critical_molar_volume * 1000), m.Y(pc), 4, 0, Math.PI * 2); ctx.fill();
      label(ctx, "critical point", m.X(x.critical_molar_volume * 1000) + 8, m.Y(pc) - 10, { font: "11px system-ui", halo: "#fff" });
      const s = x.state, sx = m.X(s.molar_volume * 1000), sy = m.Y(s.pressure / 1e5);
      ctx.fillStyle = c1; ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(sx, sy, 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      label(ctx, "V (L/mol)", plotW - 10, h - 12, { align: "right", font: "11px system-ui", color: "#7b8796" });
      label(ctx, "P (bar)", 44, 14, { font: "11px system-ui", color: "#7b8796" });
      if (hover && hover[0] < plotW) {
        const [vx] = m.inv(hover[0], hover[1]);
        if (vx >= V[0] && vx <= V[V.length - 1]) {
          const p = sampleAt(V, iso.pressure_physical, vx) / 1e5;
          ctx.strokeStyle = "rgba(22,32,44,.3)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(m.X(vx), 0); ctx.lineTo(m.X(vx), h); ctx.stroke();
          label(ctx, `V = ${fmt(vx, 3)} L/mol, P = ${fmt(p, 4)} bar`, Math.min(m.X(vx) + 8, plotW - 190), 30, { font: "bold 12px system-ui", halo: "#fff" });
        }
      }
      ctx.restore();
      // Cylinder inset: liquid volume = (1 − vapour mole fraction) × V_liquid, from the engine's lever rule
      const cx = w - 120, cw = 90, top = 60, ch = h - 140;
      const vf = s.vapour_fraction !== null ? s.vapour_fraction : s.phase === "liquid" ? 0 : 1;
      const liqH = s.phase === "liquid" ? ch : s.vapour_fraction !== null ? ch * ((1 - vf) * x.saturation.v_liquid) / s.molar_volume : 0;
      ctx.fillStyle = "rgba(42,120,214,.12)"; ctx.fillRect(cx, top, cw, ch);
      ctx.fillStyle = "rgba(42,120,214,.7)"; ctx.fillRect(cx, top + ch - liqH, cw, liqH);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.strokeRect(cx, top, cw, ch);
      label(ctx, s.phase, cx + cw / 2, top + ch + 18, { align: "center", font: "bold 12px system-ui" });
      label(ctx, "liquid shown by volume", cx + cw / 2, top + ch + 34, { align: "center", font: "10px system-ui", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); loadDome.cancel(); stage.destroy(); };
  },
};
