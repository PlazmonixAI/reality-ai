// Reactants, Products & Leftovers: chemistry.stoichiometry finds the limiting reagent and what is left over.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { drawMolecule, pretty } from "./atomdraw.js";

const REACTIONS = {
  water: ["Make water", "H2 + O2 -> H2O"], ammonia: ["Make ammonia", "N2 + H2 -> NH3"], methane: ["Burn methane", "CH4 + O2 -> CO2 + H2O"],
  salt: ["Make table salt", "Na + Cl2 -> NaCl"], rust: ["Rust iron", "Fe + O2 -> Fe2O3"],
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    let res = null, comps = {}, reactants = [], amounts = {};

    const pick = select({ label: "Reaction", value: "ammonia", options: Object.entries(REACTIONS).map(([v, [l, e]]) => ({ value: v, label: `${l}: ${e.split(/\s*->\s*/).map((side) => side.split(/\s+\+\s+/).map(pretty).join(" + ")).join(" → ")}` })), onChange: () => setup() });
    const sliderBox = el("div");
    const out = readouts([{ key: "eq", label: "Balanced" }, { key: "lim", label: "Limiting reactant" }, { key: "prod", label: "Products made" }, { key: "left", label: "Left over" }]);
    L.side.append(
      panel("Before the reaction", pick.root, sliderBox, el("p", { class: "note" }, "The reactant that runs out first limits how much product you can make; the rest is left over.")),
      panel("After (from the engine)", out.root),
    );

    function setup() {
      const eq = REACTIONS[pick.value][1];
      reactants = eq.split(/\s*->\s*/)[0].split(/\s+\+\s+/);
      amounts = Object.fromEntries(reactants.map((r, i) => [r, i === 0 ? 4 : 5]));
      sliderBox.replaceChildren(...reactants.map((r) => slider({ label: `${pretty(r)} molecules`, min: 0, max: 12, step: 1, value: amounts[r], onInput: (v) => { amounts[r] = v; recompute(); } }).root));
      recompute();
    }

    const recompute = liveRequest(async (signal) => {
      const eq = REACTIONS[pick.value][1];
      const given = Object.fromEntries(Object.entries(amounts).filter(([, v]) => v > 0));
      // With any reactant at zero nothing can react (the engine would otherwise treat it as unlimited)
      const r = Object.keys(given).length === reactants.length ? await simulate("chemistry", "stoichiometry", { equation: eq, moles: given, whole_reactions: true }, signal) : null;
      const species = eq.split(/\s*->\s*/).flatMap((s) => s.split(/\s+\+\s+/)).filter((s) => !comps[s]);
      const got = await Promise.all(species.map((s) => simulate("chemistry", "molar_mass", { formula: s }, signal)));
      species.forEach((s, i) => { comps[s] = Object.fromEntries(Object.entries(got[i].composition).map(([k, v]) => [k, v.atoms])); });
      return r;
    }, {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        if (!r) { ["eq", "prod"].forEach((k) => out.set(k, "—")); out.set("lim", "a reactant is missing: no reaction"); out.set("left", "everything"); draw(); return; }
        const x = r.result;
        out.set("eq", r.balanced_equation.split(/\s*->\s*/).map((side) => side.split(/\s+\+\s+/).map(pretty).join(" + ")).join(" → ")); out.set("lim", pretty(x.limiting_reagent));
        out.set("prod", Object.entries(x.products).map(([k, v]) => `${fmt(v.moles, 3)} ${pretty(k)}`).join(", ") || "none");
        out.set("left", Object.entries(x.excess_remaining).map(([k, v]) => `${fmt(v.moles, 3)} ${pretty(k)}`).join(", ") || "nothing");
        draw();
      },
    });

    function box(ctx, x, y, w, h, title, groups) {
      ctx.fillStyle = "#fff"; ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);
      label(ctx, title, x + w / 2, y - 14, { align: "center", font: "bold 14px system-ui" });
      let row = 0;
      for (const [name, count] of groups) {
        const comp = comps[name]; if (!comp || count <= 0) continue;
        const n = Math.round(count), per = Math.max(1, Math.floor((w - 130) / 48));
        label(ctx, `${pretty(name)}: ${fmt(count, 3)}`, x + 10, y + 26 + row * 56, { font: "12px system-ui", color: "#4b5868" });
        for (let k = 0; k < n; k++) drawMolecule(ctx, comp, x + 120 + (k % per) * 48, y + 26 + row * 56 + Math.floor(k / per) * 44, 9);
        row += (Math.ceil(n / per) || 1) * 44 / 56 + 0.25;
      }
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      const bw = (w - 90) / 2, bh = h - 70;
      const eq = REACTIONS[pick.value][1];
      box(ctx, 30, 44, bw, bh, "Before", reactants.map((r) => [r, amounts[r]]));
      const after = res ? [...Object.entries(res.result.excess_remaining).map(([k, v]) => [k, v.moles]), ...Object.entries(res.result.products).map(([k, v]) => [k, v.moles])] : reactants.map((r) => [r, amounts[r]]);
      box(ctx, 60 + bw, 44, bw, bh, "After", after);
      label(ctx, "→", 45 + bw, 44 + bh / 2, { align: "center", font: "bold 22px system-ui" });
      label(ctx, eq.replace("->", "→"), w / 2, h - 10, { align: "center", font: "11px system-ui", color: "#7b8796" });
    }

    setup();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
