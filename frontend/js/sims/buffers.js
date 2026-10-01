// Buffers: chemistry.buffer_ph compares a buffer with pure water as strong acid or base is added.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const SYSTEMS = {
  acetate: { label: "Acetic acid / acetate (pKa 4.76)", pka: 4.76 },
  phosphate: { label: "H₂PO₄⁻ / HPO₄²⁻ (pKa 7.21)", pka: 7.21 },
  ammonium: { label: "NH₄⁺ / NH₃ (pKa 9.25)", pka: 9.25 },
};
const VOLUME = 0.1;   // L in each beaker
const STEP = 0.5e-3;  // mol per drop

function phColor(ph) {
  const stops = [[0, [227, 73, 72]], [4, [237, 161, 0]], [7, [27, 175, 122]], [10, [42, 120, 214]], [14, [74, 58, 167]]];
  for (let i = 1; i < stops.length; i++) if (ph <= stops[i][0]) {
    const [p0, c0] = stops[i - 1], [p1, c1] = stops[i], t = (ph - p0) / (p1 - p0);
    return `rgb(${c0.map((v, k) => Math.round(v + (c1[k] - v) * t)).join(",")})`;
  }
  return "rgb(74,58,167)";
}

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let net = 0, buf = null, water = null;   // net added strong acid (mol, negative = base)

    const system = select({ label: "Buffer pair", value: "acetate", options: Object.entries(SYSTEMS).map(([v, s]) => ({ value: v, label: s.label })), onChange: () => recompute() });
    const ca = slider({ label: "Weak acid concentration", min: 0, max: 1, step: 0.01, value: 0.1, unit: "M", onInput: () => recompute() });
    const cb = slider({ label: "Conjugate base concentration", min: 0, max: 1, step: 0.01, value: 0.1, unit: "M", onInput: () => recompute() });
    const addedLbl = el("p", { class: "note" });
    const out = readouts([
      { key: "bph", label: "Buffer pH (exact)" }, { key: "hh", label: "Henderson–Hasselbalch" }, { key: "cap", label: "Buffer capacity" },
      { key: "wph", label: "Pure water pH" },
    ]);
    L.side.append(
      panel("Buffer (100 mL)", system.root, ca.root, cb.root),
      panel("Add to both beakers", el("div", { class: "btn-row" },
        button("+ 0.5 mmol HCl", () => { net += STEP; recompute(); }, "primary"),
        button("+ 0.5 mmol NaOH", () => { net -= STEP; recompute(); }),
        button("Reset", () => { net = 0; recompute(); })), addedLbl),
      panel("Result (from the engine)", out.root),
    );
    const graph = new LineGraph(L.bottom, { title: "pH as strong acid (+) or base (−) is added", xLabel: "net strong acid added (mmol)", yLabel: "pH", height: 180, yRange: [0, 14] });

    const args = (acid) => ({ acid_concentration: ca.value, base_concentration: cb.value, pka: SYSTEMS[system.value].pka, volume: VOLUME,
      added_acid: Math.max(0, acid), added_base: Math.max(0, -acid) });
    const waterArgs = (acid) => ({ acid_concentration: 0, base_concentration: 0, pka: 7, volume: VOLUME, added_acid: Math.max(0, acid), added_base: Math.max(0, -acid) });

    const recompute = liveRequest(async (signal) => {
      const [b, w] = await Promise.all([simulate("chemistry", "buffer_ph", args(net), signal), simulate("chemistry", "buffer_ph", waterArgs(net), signal)]);
      const xs = Array.from({ length: 41 }, (_, i) => (i - 20) * 1e-3);   // -20..20 mmol
      const [sb, sw] = await Promise.all([
        Promise.all(xs.map((x) => simulate("chemistry", "buffer_ph", args(x), signal))),
        Promise.all(xs.map((x) => simulate("chemistry", "buffer_ph", waterArgs(x), signal))),
      ]);
      return { b, w, xs, sb, sw };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ b, w, xs, sb, sw }) => {
        L.clearError(); buf = b; water = w;
        out.set("bph", fmt(b.result, 4)); out.set("hh", b.henderson_hasselbalch === null ? "buffer used up" : fmt(b.henderson_hasselbalch, 4));
        out.set("cap", `${fmt(b.buffer_capacity, 3)} mol/(L·pH)`); out.set("wph", fmt(w.result, 4));
        addedLbl.textContent = net === 0 ? "Nothing added yet." : `Net added: ${fmt(Math.abs(net) * 1000, 3)} mmol ${net > 0 ? "HCl" : "NaOH"}`;
        const mm = xs.map((x) => x * 1000);
        graph.setSeries([
          { name: "Buffer", color: c1, x: mm, y: sb.map((s) => s.result) },
          { name: "Pure water", color: c2, x: mm, y: sw.map((s) => s.result), dash: true },
        ]);
        graph.setCursor(net * 1000);
        draw();
      },
    });

    function beaker(ctx, x, w, h, ph, title) {
      const top = 60, bot = h - 40, bw = Math.min(170, w * 0.28);
      ctx.fillStyle = ph === null ? "#e9f2fb" : phColor(ph); ctx.globalAlpha = 0.75;
      ctx.fillRect(x - bw / 2 + 4, top + 50, bw - 8, bot - top - 54); ctx.globalAlpha = 1;
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(x - bw / 2 - 6, top); ctx.lineTo(x - bw / 2, top + 8); ctx.lineTo(x - bw / 2, bot); ctx.lineTo(x + bw / 2, bot); ctx.lineTo(x + bw / 2, top + 8); ctx.lineTo(x + bw / 2 + 6, top); ctx.stroke();
      label(ctx, title, x, top - 22, { align: "center", font: "bold 14px system-ui" });
      label(ctx, ph === null ? "…" : `pH ${fmt(ph, 3)}`, x, (top + bot) / 2 + 20, { align: "center", font: "bold 24px system-ui", color: "#fff", halo: "rgba(0,0,0,.35)" });
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      beaker(ctx, w * 0.3, w, h, buf ? buf.result : null, "Buffer");
      beaker(ctx, w * 0.7, w, h, water ? water.result : null, "Pure water");
      label(ctx, "Both beakers hold 100 mL and get the same additions", w / 2, h - 14, { align: "center", font: "11px system-ui", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
