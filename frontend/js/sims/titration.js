// Acid-Base Titration: chemistry.titration_curve solves the pH at every titrant volume.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, sampleAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const ANALYTES = {
  hcl: { label: "HCl (strong acid)", analyte: "strong_acid" },
  acetic: { label: "Acetic acid (weak, pKa 4.76)", analyte: "weak_acid", pka: 4.76 },
  nh3: { label: "Ammonia (weak base, pKb 4.75)", analyte: "weak_base", pkb: 4.75 },
  naoh: { label: "NaOH (strong base)", analyte: "strong_base" },
};
// Indicator colours below / above the transition range (display only).
const INDICATOR_COLORS = {
  "methyl orange": ["#e34948", "#eda100"], "methyl red": ["#e34948", "#e8c21d"], "bromothymol blue": ["#e8c21d", "#2a78d6"],
  "phenol red": ["#e8c21d", "#e34948"], phenolphthalein: ["#ffffff", "#e87ba4"], thymolphthalein: ["#ffffff", "#2a78d6"],
};
const mix = (a, b, t) => {
  const h = (s) => [1, 3, 5].map((i) => parseInt(s.slice(i, i + 2), 16));
  const [x, y] = [h(a), h(b)];
  return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(",")})`;
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1] = SERIES();
    let data = null, vol = 0;

    const analyte = select({ label: "In the flask", value: "acetic", options: Object.entries(ANALYTES).map(([v, a]) => ({ value: v, label: a.label })), onChange: () => recompute() });
    const conc = slider({ label: "Flask concentration", min: 0.01, max: 1, step: 0.01, value: 0.1, unit: "M", onInput: () => recompute() });
    const vA = slider({ label: "Flask volume", min: 5, max: 50, step: 1, value: 25, unit: "mL", onInput: () => recompute() });
    const tConc = slider({ label: "Titrant concentration", min: 0.01, max: 1, step: 0.01, value: 0.1, unit: "M", onInput: () => recompute() });
    const indicator = select({ label: "Indicator", value: "phenolphthalein", options: [{ value: "", label: "None" }, ...Object.keys(INDICATOR_COLORS).map((k) => ({ value: k, label: k }))], onChange: () => draw() });
    const added = slider({ label: "Titrant added", min: 0, max: 50, step: 0.05, value: 0, unit: "mL", onInput: (v) => { vol = v; player.pause(); sync(); } });
    const out = readouts([
      { key: "ph", label: "pH now" }, { key: "veq", label: "Equivalence volume" }, { key: "pheq", label: "pH at equivalence" },
      { key: "half", label: "pH at half-equivalence" }, { key: "ind", label: "Good indicators" },
    ]);
    L.side.append(
      panel("Titration", analyte.root, conc.root, vA.root, tConc.root, indicator.root),
      panel("Burette", added.root, el("p", { class: "note" }, "Drag the slider, or press play to titrate automatically.")),
      panel("Curve (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { vol = t; added.set(t); sync(); }, { speeds: [0.5, 1, 2], timeFormat: (v) => `${fmt(v, 3)} mL` });
    const graph = new LineGraph(L.bottom, { title: "pH vs titrant added", xLabel: "titrant (mL)", yLabel: "pH", height: 170, yRange: [0, 14] });

    const titrant = () => (ANALYTES[analyte.value].analyte.endsWith("acid") ? "NaOH" : "HCl");
    const recompute = liveRequest((signal) => {
      const a = ANALYTES[analyte.value];
      return simulate("chemistry", "titration_curve", {
        analyte: a.analyte, pka: a.pka, pkb: a.pkb, analyte_concentration: conc.value, analyte_volume: vA.value,
        titrant_concentration: tConc.value, n_points: 601,
      }, signal);
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const res = r.result, vmax = r.curve.volume[r.curve.volume.length - 1];
        added.setRange(0, vmax); vol = Math.min(vol, vmax); added.set(vol);
        out.set("veq", `${fmt(res.equivalence_volume, 4)} mL`); out.set("pheq", fmt(res.equivalence_ph, 4));
        out.set("half", fmt(res.half_equivalence_ph, 4)); out.set("ind", res.indicators.join(", ") || "—");
        graph.setSeries([{ name: "pH", color: c1, x: r.curve.volume, y: r.curve.ph }]);
        player.load(vmax, 12, { autoplay: false }); player.seek(vol);
      },
    });

    function phNow() { return data ? sampleAt(data.curve.volume, data.curve.ph, vol) : 7; }
    function sync() { graph.setCursor(vol); out.set("ph", fmt(phNow(), 4)); draw(); }

    function solutionColor(ph) {
      const ind = indicator.value;
      if (!ind || !data) return "#e9f2fb";
      const [lo, hi] = data.indicator_ranges[ind];
      return mix(...INDICATOR_COLORS[ind], Math.max(0, Math.min(1, (ph - lo) / (hi - lo))));
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      const cx = w * 0.4;
      // Burette
      const bTop = 20, bBot = h * 0.45, bw = 26;
      const vmax = data ? data.curve.volume[data.curve.volume.length - 1] : 50;
      ctx.fillStyle = "#fff"; ctx.fillRect(cx - bw / 2, bTop, bw, bBot - bTop);
      const level = bTop + ((bBot - bTop) * vol) / vmax;
      ctx.fillStyle = "rgba(42,120,214,.25)"; ctx.fillRect(cx - bw / 2, level, bw, bBot - level);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.strokeRect(cx - bw / 2, bTop, bw, bBot - bTop);
      for (let k = 0; k <= 10; k++) { const y = bTop + ((bBot - bTop) * k) / 10; ctx.beginPath(); ctx.moveTo(cx + bw / 2 - 8, y); ctx.lineTo(cx + bw / 2, y); ctx.stroke(); }
      ctx.fillStyle = "#39424e"; ctx.fillRect(cx - 4, bBot, 8, 24); ctx.fillRect(cx - 14, bBot + 6, 28, 6);
      label(ctx, `${fmt(tConc.value, 3)} M ${titrant()}`, cx + bw / 2 + 10, bTop + 12, { font: "12px system-ui" });
      if (player.playing) { ctx.fillStyle = "rgba(42,120,214,.7)"; ctx.beginPath(); ctx.arc(cx, bBot + 34 + ((performance.now() / 4) % 30), 3, 0, Math.PI * 2); ctx.fill(); }
      // Flask
      const fTop = h * 0.55, fBot = h - 30, neck = 22, base = Math.min(170, w * 0.22);
      const ph = phNow();
      ctx.fillStyle = solutionColor(ph);
      ctx.beginPath(); ctx.moveTo(cx - neck, fTop + 20); ctx.lineTo(cx - base, fBot); ctx.lineTo(cx + base, fBot); ctx.lineTo(cx + neck, fTop + 20); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(cx - neck, fTop - 10); ctx.lineTo(cx - neck, fTop + 20); ctx.lineTo(cx - base, fBot); ctx.lineTo(cx + base, fBot); ctx.lineTo(cx + neck, fTop + 20); ctx.lineTo(cx + neck, fTop - 10); ctx.stroke();
      label(ctx, `${fmt(vA.value, 3)} mL of ${fmt(conc.value, 3)} M ${ANALYTES[analyte.value].label.split(" (")[0]}`, cx, fBot + 18, { align: "center", font: "12px system-ui" });
      // pH meter
      const mx = w * 0.7, my = h * 0.35;
      ctx.fillStyle = "#26303d"; ctx.beginPath(); ctx.roundRect(mx, my, 140, 76, 10); ctx.fill();
      ctx.fillStyle = "#c9f0d8"; ctx.fillRect(mx + 12, my + 12, 116, 52);
      label(ctx, fmt(ph, 3), mx + 70, my + 38, { align: "center", font: "bold 28px ui-monospace, monospace", color: "#133b25" });
      label(ctx, "pH", mx + 124, my + 56, { align: "right", font: "11px system-ui", color: "#133b25" });
      ctx.strokeStyle = "#26303d"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(mx + 20, my + 76); ctx.quadraticCurveTo(mx - 20, fTop, cx + base * 0.4, fTop + 40); ctx.lineTo(cx + base * 0.4, fBot - 30); ctx.stroke();
      label(ctx, `${fmt(vol, 3)} mL added`, 14, 18, { font: "13px system-ui" });
    }

    const tick = setInterval(() => { if (player.playing) draw(); }, 50);
    recompute();
    return () => { clearInterval(tick); recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
