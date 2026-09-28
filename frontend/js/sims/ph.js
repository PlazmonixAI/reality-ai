// pH Scale: chemistry.ph solves the exact acid/base equilibrium including water autoionisation.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, segmented, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt, superscript } from "../core/format.js";

const PRESETS = {
  hcl: { label: "Hydrochloric acid (HCl)", kind: "strong_acid" },
  hno3: { label: "Nitric acid (HNO₃)", kind: "strong_acid" },
  acetic: { label: "Acetic acid (vinegar)", kind: "weak_acid", pk: 4.76 },
  formic: { label: "Formic acid", kind: "weak_acid", pk: 3.75 },
  hf: { label: "Hydrofluoric acid (HF)", kind: "weak_acid", pk: 3.17 },
  naoh: { label: "Sodium hydroxide (NaOH)", kind: "strong_base" },
  baoh2: { label: "Barium hydroxide (Ba(OH)₂)", kind: "strong_base", eq: 2 },
  nh3: { label: "Ammonia (NH₃)", kind: "weak_base", pk: 4.75 },
  methylamine: { label: "Methylamine", kind: "weak_base", pk: 3.36 },
  custom: { label: "Custom", kind: null },
};
// Universal-indicator-like colours for pH 0..14
const PH_COLORS = ["#d7263d", "#e34948", "#eb6834", "#f08a24", "#eda100", "#e8c21d", "#b9cf2a", "#58b947", "#1baf7a", "#1f9f9a", "#2a78d6", "#3551b8", "#4a3aa7", "#5b2c8f", "#4a1f70"];

function phColor(ph) {
  const x = Math.max(0, Math.min(14, ph));
  const i = Math.min(13, Math.floor(x)), f = x - i;
  const a = hex(PH_COLORS[i]), b = hex(PH_COLORS[i + 1]);
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(",")})`;
}
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const pow10 = (e) => `10${superscript(Math.round(e))}`;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null;

    const preset = select({ label: "Solute", value: "acetic", options: Object.entries(PRESETS).map(([value, p]) => ({ value, label: p.label })), onChange: (k) => applyPreset(k) });
    const kind = segmented({ label: "Type", value: "weak_acid", options: [
      { value: "strong_acid", label: "Strong acid" }, { value: "weak_acid", label: "Weak acid" },
      { value: "strong_base", label: "Strong base" }, { value: "weak_base", label: "Weak base" },
    ], onChange: () => { preset.set("custom"); syncControls(); recompute(); } });
    const conc = slider({ label: "Concentration", min: 1e-7, max: 1, value: 0.1, log: true, format: (v) => `${fmt(v, 3)} M`, onInput: () => recompute() });
    const pk = slider({ label: "pKa", min: 1, max: 12, step: 0.01, value: 4.76, digits: 3, onInput: () => { preset.set("custom"); recompute(); } });
    const out = readouts([
      { key: "ph", label: "pH" }, { key: "poh", label: "pOH" }, { key: "h", label: "[H₃O⁺]" }, { key: "oh", label: "[OH⁻]" }, { key: "ion", label: "Ionised" },
    ]);
    let equivalents = 1;

    function syncControls() {
      const weak = kind.value.startsWith("weak");
      pk.root.style.display = weak ? "" : "none";
      pk.root.querySelector("label").textContent = kind.value === "weak_base" ? "pKb" : "pKa";
    }
    function applyPreset(k) {
      const p = PRESETS[k];
      if (!p.kind) return;
      kind.set(p.kind); equivalents = p.eq || 1;
      if (p.pk) pk.set(p.pk);
      syncControls(); recompute();
    }

    L.side.append(
      panel("Solution", preset.root, kind.root, conc.root, pk.root, el("p", { class: "note" }, "25 °C, ideal solution. Try diluting a strong acid below 10⁻⁷ M: the pH stops at 7 instead of turning basic.")),
      panel("Equilibrium (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "pH vs concentration", xLabel: "log₁₀ concentration (M)", yLabel: "pH", height: 170, yRange: [0, 14], xFormat: (v) => fmt(v, 2) });

    const args = (c) => {
      const a = { kind: kind.value, concentration: c };
      if (kind.value.startsWith("weak")) a[kind.value === "weak_acid" ? "pka" : "pkb"] = pk.value;
      else a.equivalents = kind.value === "strong_base" || kind.value === "strong_acid" ? equivalents : 1;
      return a;
    };
    const recompute = liveRequest(async (signal) => {
      const main = await simulate("chemistry", "ph", args(conc.value), signal);
      const xs = Array.from({ length: 29 }, (_, i) => -7 + i * 0.25);
      const sweep = await Promise.all(xs.map((x) => simulate("chemistry", "ph", args(10 ** x), signal)));
      return { main, xs, sweep };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ main, xs, sweep }) => {
        L.clearError(); res = main;
        out.set("ph", fmt(main.result, 4)); out.set("poh", fmt(main.pOH, 4));
        out.set("h", `${fmt(main.h_concentration, 3)} M`); out.set("oh", `${fmt(main.oh_concentration, 3)} M`);
        out.set("ion", `${fmt(main.percent_ionised, 3)} %`);
        graph.setSeries([{ name: "pH", color: c1, x: xs, y: sweep.map((s) => s.result) }]);
        graph.setCursor(Math.log10(conc.value));
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      const ph = res ? res.result : 7;
      // Beaker
      const bw = Math.min(220, w * 0.28), bh = Math.min(260, h - 150), bx = w * 0.2, by = h - bh - 70;
      const level = by + bh * 0.3;
      ctx.fillStyle = phColor(ph); ctx.globalAlpha = 0.85;
      ctx.fillRect(bx + 4, level, bw - 8, by + bh - level - 4); ctx.globalAlpha = 1;
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(bx - 8, by); ctx.lineTo(bx, by + 8); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by + 8); ctx.lineTo(bx + bw + 8, by); ctx.stroke();
      for (let i = 1; i <= 4; i++) { const y = by + bh - (bh * i) / 5; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(bx, y); ctx.lineTo(bx + 18, y); ctx.stroke(); }
      label(ctx, PRESETS[preset.value].label === "Custom" ? kind.value.replace("_", " ") : PRESETS[preset.value].label, bx + bw / 2, by + bh + 22, { align: "center", font: "bold 13px system-ui" });
      label(ctx, `${fmt(conc.value, 3)} M`, bx + bw / 2, by + bh + 40, { align: "center", font: "12px system-ui", color: "#4b5868" });

      // pH meter with probe
      const mx = bx + bw + 60, my = by - 60;
      ctx.fillStyle = "#26303d"; ctx.beginPath(); ctx.roundRect(mx, my, 130, 70, 10); ctx.fill();
      ctx.fillStyle = "#c9f0d8"; ctx.fillRect(mx + 12, my + 12, 106, 46);
      label(ctx, res ? fmt(ph, 3) : "…", mx + 65, my + 36, { align: "center", font: "bold 26px ui-monospace, monospace", color: "#133b25" });
      label(ctx, "pH", mx + 118, my + 52, { align: "right", font: "11px system-ui", color: "#133b25" });
      ctx.strokeStyle = "#26303d"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(mx + 20, my + 70); ctx.quadraticCurveTo(mx - 20, my + 110, bx + bw * 0.7, by + 40); ctx.lineTo(bx + bw * 0.7, level + 60); ctx.stroke();
      ctx.fillStyle = "#26303d"; ctx.fillRect(bx + bw * 0.7 - 5, level + 40, 10, 34);

      // pH scale bar
      const sx = 30, sy = 26, sw = w - 60, sh = 14;
      for (let i = 0; i < sw; i++) { ctx.fillStyle = phColor((i / sw) * 14); ctx.fillRect(sx + i, sy, 1.5, sh); }
      for (let p = 0; p <= 14; p++) label(ctx, String(p), sx + (p / 14) * sw, sy + sh + 22, { align: "center", font: "11px system-ui", color: "#4b5868" });
      label(ctx, "acidic", sx, sy - 9, { font: "11px system-ui", color: "#c93a3a" });
      label(ctx, "basic", sx + sw, sy - 9, { font: "11px system-ui", color: "#4a3aa7", align: "right" });
      label(ctx, "neutral", sx + sw / 2, sy - 9, { font: "11px system-ui", color: "#15845d", align: "center" });
      const px = sx + (Math.max(0, Math.min(14, ph)) / 14) * sw;
      ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.moveTo(px, sy + sh + 1); ctx.lineTo(px - 7, sy + sh + 12); ctx.lineTo(px + 7, sy + sh + 12); ctx.fill();

      // Log bars for [H3O+] and [OH-]
      if (res) {
        const gx = Math.max(mx + 170, w * 0.62), gy = by, gh = bh, gw = 40;
        const Y = (c) => gy + gh - ((Math.log10(c) + 15) / 16) * gh;   // 1e-15 .. 1e1
        ctx.strokeStyle = "#9aa6b5"; ctx.lineWidth = 1;
        for (let e = -14; e <= 0; e += 2) {
          const y = Y(10 ** e);
          ctx.beginPath(); ctx.moveTo(gx - 6, y); ctx.lineTo(gx + gw * 2 + 30, y); ctx.stroke();
          label(ctx, pow10(e), gx - 10, y, { align: "right", font: "11px system-ui", color: "#4b5868" });
        }
        const bar = (x, c, color, name) => {
          ctx.fillStyle = color; ctx.fillRect(x, Y(c), gw, gy + gh - Y(c));
          label(ctx, name, x + gw / 2, gy + gh + 16, { align: "center", font: "bold 12px system-ui" });
          label(ctx, `${fmt(c, 2)} M`, x + gw / 2, Y(c) - 10, { align: "center", font: "11px system-ui" });
        };
        bar(gx, res.h_concentration, c1, "H₃O⁺");
        bar(gx + gw + 24, res.oh_concentration, c2, "OH⁻");
        label(ctx, "concentration (log scale, M)", gx + gw + 12, gy - 14, { align: "center", font: "11px system-ui", color: "#4b5868" });
      }
    }

    syncControls();
    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
