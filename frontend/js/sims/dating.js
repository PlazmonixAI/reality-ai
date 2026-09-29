// Radiometric Dating: chemistry.radiometric_dating turns a measured isotope ratio into an age.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const SYSTEMS = { "C-14": "Carbon-14 (wood, bone, cloth)", "K-40/Ar-40": "Potassium-40 → Argon-40 (volcanic rock)", "U-238/Pb-206": "Uranium-238 → Lead-206 (zircon)", "U-235/Pb-207": "Uranium-235 → Lead-207", "Rb-87/Sr-87": "Rubidium-87 → Strontium-87" };
const years = (y) => (y >= 1e9 ? `${fmt(y / 1e9, 4)} billion years` : y >= 1e6 ? `${fmt(y / 1e6, 4)} million years` : `${fmt(y, 4)} years`);

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null;

    const sys = select({ label: "Dating method", value: "C-14", options: Object.entries(SYSTEMS).map(([v, l]) => ({ value: v, label: l })), onChange: () => { sync(); recompute(); } });
    const frac = slider({ label: "C-14 left (compared with living things)", min: 0.005, max: 1, value: 0.35, log: true, format: (v) => `${fmt(v * 100, 3)} %`, onInput: () => recompute() });
    const ratio = slider({ label: "Daughter atoms per parent atom", min: 0.001, max: 5, value: 0.5, log: true, format: (v) => fmt(v, 3), onInput: () => recompute() });
    const err = slider({ label: "Measurement uncertainty", min: 0, max: 0.2, step: 0.005, value: 0.02, format: (v) => `± ${fmt(v * 100, 3)} %`, onInput: () => recompute() });
    function sync() { const c = sys.value === "C-14"; frac.root.style.display = c ? "" : "none"; ratio.root.style.display = c ? "none" : ""; }
    const out = readouts([{ key: "age", label: "Age" }, { key: "range", label: "Age range" }, { key: "hl", label: "Half-lives elapsed" }, { key: "use", label: "Method works for" }]);
    L.side.append(
      panel("Sample", sys.root, frac.root, ratio.root, err.root, el("p", { class: "note" }, "Every half-life, half of the remaining parent atoms decay. Count what's left and you know how long it has been.")),
      panel("Age (from the engine)", out.root),
    );
    sync();
    const graph = new LineGraph(L.bottom, { title: "Parent atoms left and daughter atoms made (as fractions of the original parent)", xLabel: "time", yLabel: "fraction", height: 150, includeZero: true });

    const recompute = liveRequest((signal) => simulate("chemistry", "radiometric_dating", {
      system: sys.value, relative_error: err.value, ...(sys.value === "C-14" ? { fraction_remaining: frac.value } : { daughter_parent_ratio: ratio.value }),
    }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result, big = x.half_life_years > 1e6, sc = big ? 1e9 : 1;
        out.set("age", years(x.age_years)); out.set("range", `${years(x.age_range_years[0])} – ${years(x.age_range_years[1])}`);
        out.set("hl", fmt(x.half_lives_elapsed, 3)); out.set("use", `${years(x.useful_range_years[0])} – ${years(x.useful_range_years[1])}`);
        graph.opts.xLabel = big ? "time (billion years)" : "time (years)";
        graph.setSeries([
          { name: "parent left", color: c1, x: r.curve.t_years.map((t) => t / sc), y: r.curve.parent_fraction },
          { name: `${x.daughter} made`, color: c2, x: r.curve.t_years.map((t) => t / sc), y: r.curve.daughter_per_initial_parent },
        ]);
        graph.setCursor(x.age_years / sc);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const x = res.result, parent = Math.round(x.fraction_remaining * 400), size = Math.min((w - 80) / 20, (h - 90) / 20) - 3;
      const ox = (w - 20 * (size + 3)) / 2, oy = 50;
      for (let i = 0; i < 400; i++) {
        const col = i % 20, row = Math.floor(i / 20);
        ctx.fillStyle = i < parent ? c1 : "rgba(235,104,52,.45)";
        ctx.fillRect(ox + col * (size + 3), oy + row * (size + 3), size, size);
      }
      label(ctx, `■ parent ${sys.value.split("/")[0]}: ${fmt(x.fraction_remaining * 100, 3)} %`, ox, 24, { color: c1, font: "bold 13px system-ui" });
      label(ctx, `■ decayed (${x.daughter} and other products)`, ox + 260, 24, { color: c2, font: "bold 13px system-ui" });
      label(ctx, `Age ≈ ${years(x.age_years)}`, w / 2, h - 16, { align: "center", font: "bold 15px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
