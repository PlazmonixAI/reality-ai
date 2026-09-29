// Radioactive Decay: physics.radioactive_decay solves the decay chain exactly (Bateman).
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, indexAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";

const YEAR = 365.25 * 86400;
// Well-known half-lives (rounded); chains are illustrative two-step models.
const PRESETS = {
  c14: { label: "Carbon-14 → Nitrogen-14", names: ["C-14", "N-14"], halves: [5730 * YEAR, null] },
  i131: { label: "Iodine-131 → Xenon-131", names: ["I-131", "Xe-131"], halves: [8.02 * 86400, null] },
  co60: { label: "Cobalt-60 → Nickel-60", names: ["Co-60", "Ni-60"], halves: [5.27 * YEAR, null] },
  chain: { label: "Custom chain A → B → C", names: ["A", "B", "C"], halves: null },
};
const N_ATOMS = 400;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const cols = SERIES();
    let data = null, simTime = 0, names = [];
    let seed = 5; const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const order = Array.from({ length: N_ATOMS }, (_, i) => i).sort(() => rand() - 0.5);

    const preset = select({ label: "Isotope", value: "chain", options: Object.entries(PRESETS).map(([v, p]) => ({ value: v, label: p.label })), onChange: () => { sync(); recompute(); } });
    const ha = slider({ label: "Half-life of A", min: 1, max: 100, step: 1, value: 10, unit: "s", onInput: () => recompute() });
    const hb = slider({ label: "Half-life of B", min: 1, max: 100, step: 1, value: 30, unit: "s", onInput: () => recompute() });
    const out = readouts([{ key: "t", label: "Time" }, { key: "a", label: "Remaining parent" }, { key: "hl", label: "Half-lives elapsed" }]);
    function sync() { const c = preset.value === "chain"; ha.root.style.display = hb.root.style.display = c ? "" : "none"; }
    L.side.append(panel("Sample", preset.root, ha.root, hb.root, el("p", { class: "note" }, "Each square is one atom of 400. Decay is random for each atom, but the totals follow the engine's exact curves.")),
      panel("Amounts (from the engine)", out.root));
    sync();
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t / scale()); upd(); }, { speeds: [0.5, 1, 2, 4] });
    const graph = new LineGraph(L.bottom, { title: "Atoms of each kind", xLabel: "time", yLabel: "atoms", height: 150, includeZero: true });

    const halves = () => preset.value === "chain" ? [ha.value, hb.value, null] : PRESETS[preset.value].halves;
    const scale = () => { const h = halves()[0]; return h > 3 * YEAR ? YEAR : h > 3 * 86400 ? 86400 : 1; };
    const unit = () => ({ [YEAR]: "years", 86400: "days", 1: "s" }[scale()]);

    const recompute = liveRequest((signal) => {
      const hs = halves();
      const dur = 6 * Math.max(...hs.filter((x) => x));
      return simulate("physics", "radioactive_decay", { half_lives: hs, initial: [N_ATOMS, ...hs.slice(1).map(() => 0)], duration: dur, n_points: 401 }, signal);
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r; names = PRESETS[preset.value].names;
        graph.opts.xLabel = `time (${unit()})`;
        graph.setSeries(r.curves.amounts.map((a, i) => ({ name: names[i], color: cols[i], x: r.curves.t.map((t) => t / scale()), y: a, dash: i === 1 })));
        player.load(r.curves.t[r.curves.t.length - 1], 12);
      },
    });

    function upd() {
      if (!data) return;
      const k = indexAt(data.curves.t, simTime);
      out.set("t", scale() === 1 ? fmtTime(simTime) : `${fmt(simTime / scale(), 4)} ${unit()}`);
      out.set("a", `${fmt(data.curves.amounts[0][k], 4)} of ${N_ATOMS}`);
      out.set("hl", fmt(simTime / halves()[0], 3));
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!data) return;
      const k = indexAt(data.curves.t, simTime);
      const counts = data.curves.amounts.map((a) => Math.round(a[k]));
      const cols20 = 25, size = Math.min((w - 40) / cols20, (h - 60) / (N_ATOMS / cols20)) - 3;
      const ox = (w - cols20 * (size + 3)) / 2, oy = 30;
      order.forEach((atom, rank) => {
        let kind = 0, acc = counts[0];
        while (rank >= acc && kind < counts.length - 1) { kind++; acc += counts[kind]; }
        const x = ox + (atom % cols20) * (size + 3), y = oy + Math.floor(atom / cols20) * (size + 3);
        ctx.fillStyle = cols[kind] || "#9aa6b5";
        ctx.globalAlpha = kind === counts.length - 1 && counts.length > 1 ? 0.45 : 1;
        ctx.fillRect(x, y, size, size); ctx.globalAlpha = 1;
      });
      names.forEach((n, i) => label(ctx, `■ ${n}: ${counts[i]}`, 20 + i * 140, 14, { color: cols[i], font: "bold 13px system-ui" }));
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
