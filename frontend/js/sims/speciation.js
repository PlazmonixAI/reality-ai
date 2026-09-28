// Polyprotic Acids: chemistry.acid_speciation gives the fraction of each protonation state at every pH.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Textbook pKa values at 25 °C.
const ACIDS = {
  phosphoric: ["Phosphoric acid H₃PO₄", [2.15, 7.2, 12.35]], carbonic: ["Carbonic acid H₂CO₃", [6.35, 10.33]],
  citric: ["Citric acid", [3.13, 4.76, 6.4]], oxalic: ["Oxalic acid", [1.25, 4.27]], glycine: ["Glycine (amino acid)", [2.34, 9.6]], acetic: ["Acetic acid", [4.76]],
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const cols = SERIES();
    let res = null, fr = null, shown = [];

    const acid = select({ label: "Acid", value: "phosphoric", options: Object.entries(ACIDS).map(([v, [l]]) => ({ value: v, label: l })), onChange: () => recompute() });
    const ph = slider({ label: "Solution pH", min: 0, max: 14, step: 0.05, value: 7, onInput: () => recompute() });
    const conc = slider({ label: "Acid concentration (for its own pH)", min: 0.001, max: 1, value: 0.1, log: true, unit: "M", onInput: () => recompute() });
    const out = readouts([{ key: "dom", label: "Main form at this pH" }, { key: "h", label: "Protons still bound (average)" }, { key: "own", label: "pH of the acid alone" }]);
    const shares = el("div", { class: "note" });
    L.side.append(
      panel("Acid", acid.root, ph.root, conc.root, el("p", { class: "note" }, "Each proton comes off around its pKa: at pH = pKa the two neighbouring forms are 50 : 50.")),
      panel("Speciation (from the engine)", out.root, shares),
    );
    const graph = new LineGraph(L.bottom, { title: "Fractions of the forms nearest this pH", xLabel: "pH", yLabel: "fraction", height: 160, includeZero: true });

    const recompute = liveRequest((signal) => simulate("chemistry", "acid_speciation", { pkas: ACIDS[acid.value][1], concentration: conc.value, ph: ph.value }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result, at = x.at_ph, names = x.species;
        fr = at.fractions;
        out.set("dom", names[at.dominant]); out.set("h", fmt(at.protons_bound, 3)); out.set("own", fmt(x.ph_of_acid_solution, 3));
        shares.replaceChildren(...names.map((n, j) => el("div", {}, `${n}: ${fmt(at.fractions[j] * 100, 3)} %`)));
        // At most three series: the dominant form and its neighbours
        const n = names.length, first = Math.max(0, Math.min(at.dominant - 1, n - 3)), idx = [first, first + 1, first + 2].filter((j) => j < n);
        shown = idx;
        graph.setSeries(idx.map((j, k) => ({ name: names[j], color: cols[k], x: r.curves.ph, y: r.curves.fractions[j] })));
        graph.setCursor(ph.value);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      // Same colours as the graph for the forms it shows; grey for the rest
      const tone = (j) => (shown.includes(j) ? cols[shown.indexOf(j)] : "#9aa6b5");
      const names = res.result.species, bw = Math.min(360, w * 0.5), bh = h - 90, bx = w * 0.35 - bw / 2, by = 40;
      ctx.fillStyle = "rgba(42,120,214,.1)"; ctx.fillRect(bx, by + 20, bw, bh - 20);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by); ctx.stroke();
      // 100 tokens split by the engine's fractions (largest-remainder rounding, display only)
      const raw = fr.map((f) => f * 100), counts = raw.map(Math.floor);
      let left = 100 - counts.reduce((a, b) => a + b, 0);
      raw.map((v, j) => [v - Math.floor(v), j]).sort((a, b) => b[0] - a[0]).forEach(([, j]) => { if (left > 0) { counts[j]++; left--; } });
      let k = 0;
      counts.forEach((c, j) => { for (let i = 0; i < c; i++, k++) {
        const col = k % 10, row = Math.floor(k / 10), x = bx + 20 + col * ((bw - 40) / 9), y = by + 40 + row * ((bh - 60) / 10);
        ctx.fillStyle = tone(j); ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fill();
      } });
      names.forEach((n, j) => { ctx.fillStyle = tone(j); ctx.beginPath(); ctx.arc(bx + bw + 40, by + 30 + j * 30, 8, 0, Math.PI * 2); ctx.fill(); label(ctx, `${n}  ${fmt(fr[j] * 100, 3)} %`, bx + bw + 56, by + 30 + j * 30, { font: "13px system-ui" }); });
      label(ctx, `pH ${fmt(ph.value, 3)} — each dot is 1 % of the acid`, bx, by - 14, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
