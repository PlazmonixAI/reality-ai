// Chemical Equilibrium: equilibrium_ice solves the ICE table for any stoichiometry.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";

// K values are textbook teaching values at the stated temperature.
const REACTIONS = {
  hi: { label: "H₂ + I₂ ⇌ 2 HI (≈ 700 K)", eq: "H2(g) + I2(g) <=> 2 HI(g)", k: 50.5, species: ["H2", "I2", "HI"], init: { H2: 1, I2: 1, HI: 0 } },
  n2o4: { label: "N₂O₄ ⇌ 2 NO₂ (298 K)", eq: "N2O4(g) <=> 2 NO2(g)", k: 4.64e-3, species: ["N2O4", "NO2"], init: { N2O4: 0.1, NO2: 0 } },
  haber: { label: "N₂ + 3 H₂ ⇌ 2 NH₃ (≈ 670 K)", eq: "N2(g) + 3 H2(g) <=> 2 NH3(g)", k: 0.5, species: ["N2", "H2", "NH3"], init: { N2: 1, H2: 1, NH3: 0 } },
  shift: { label: "CO + H₂O ⇌ CO₂ + H₂ (≈ 1100 K)", eq: "CO(g) + H2O(g) <=> CO2(g) + H2(g)", k: 1.0, species: ["CO", "H2O", "CO2", "H2"], init: { CO: 1, H2O: 1, CO2: 0, H2: 0 } },
  acetic: { label: "CH₃COOH ⇌ H⁺ + CH₃COO⁻ (aq)", eq: "CH3COOH <=> H+ + CH3COO-", k: 1.8e-5, species: ["CH3COOH", "H+", "CH3COO-"], init: { CH3COOH: 0.1, "H+": 0, "CH3COO-": 0 } },
};
const titleOf = (eq) => eq.replace(/\(g\)/g, "").split(" ").map((t) => (t === "+" ? "+" : t === "<=>" ? "⇌" : /^\d+$/.test(t) ? t : pretty(t))).join(" ");
const pretty = (s) => s.replace(/(\d+)/g, (d) => d.split("").map((c) => "₀₁₂₃₄₅₆₇₈₉"[c]).join("")).replace("+", "⁺").replace(/-$/, "⁻");

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2] = SERIES();
    let res = null, shown = null, target = null;

    const rxn = select({ label: "Reaction", value: "hi", options: Object.entries(REACTIONS).map(([value, r]) => ({ value, label: r.label })), onChange: () => build() });
    const k = slider({ label: "Equilibrium constant Kc", min: 1e-6, max: 1e6, value: 50.5, log: true, format: (v) => fmt(v, 3), onInput: () => recompute() });
    const initBox = el("div");
    let inits = {};
    const out = readouts([{ key: "dir", label: "Reaction shifts" }, { key: "q", label: "Q at equilibrium" }, { key: "conv", label: "Conversion" }]);
    const table = el("div");
    L.side.append(
      panel("Reaction", rxn.root, k.root),
      panel("Initial concentrations (M)", initBox),
      panel("Result (from the engine)", out.root),
    );
    L.bottom.append(el("div", { class: "graph-card" }, el("div", { class: "graph-head" }, el("span", { class: "graph-title" }, "ICE table (M)")), table));

    function build() {
      const r = REACTIONS[rxn.value];
      k.set(r.k);
      inits = {};
      initBox.replaceChildren(...r.species.map((s) => {
        inits[s] = slider({ label: `[${pretty(s)}]₀`, min: 0, max: 2, step: 0.01, value: r.init[s], unit: "M", onInput: () => recompute() });
        return inits[s].root;
      }));
      res = null; shown = null;
      recompute();
    }

    const recompute = liveRequest((signal) => {
      const r = REACTIONS[rxn.value];
      const initial = Object.fromEntries(r.species.map((s) => [s, inits[s].value]));
      return simulate("chemistry", "equilibrium_ice", { equation: r.eq, k: k.value, initial }, signal).then((x) => ({ x, initial }));
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ x, initial }) => {
        L.clearError(); res = { ...x, initial };
        target = x.result;
        if (!shown) shown = { ...initial };
        out.set("dir", { forward: "→ toward products", reverse: "← toward reactants", "at equilibrium": "already at equilibrium" }[x.direction]);
        out.set("q", fmt(x.reaction_quotient_check, 4));
        const conv = Object.entries(x.fraction_converted);
        out.set("conv", conv.length ? conv.map(([s, f]) => `${pretty(s)} ${fmt(f * 100, 3)}%`).join(", ") : "—");
        const sp = REACTIONS[rxn.value].species;
        table.replaceChildren(el("table", { class: "ice" },
          el("thead", {}, el("tr", {}, el("th", {}, ""), sp.map((s) => el("th", {}, pretty(s))))),
          el("tbody", {},
            el("tr", {}, el("td", {}, "Initial"), sp.map((s) => el("td", {}, fmt(initial[s], 4)))),
            el("tr", {}, el("td", {}, "Change"), sp.map((s) => { const d = x.result[s] - initial[s]; return el("td", {}, `${d >= 0 ? "+" : ""}${fmt(d, 4)}`); })),
            el("tr", {}, el("td", {}, "Equilibrium"), sp.map((s) => el("td", {}, fmt(x.result[s], 4)))))));
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fbfcfe"; ctx.fillRect(0, 0, w, h);
      const r = REACTIONS[rxn.value];
      label(ctx, titleOf(r.eq), w / 2, 30, { align: "center", font: "bold 18px system-ui" });
      if (!res || !shown) return;
      // Tween displayed equilibrium bars toward the engine's answer.
      for (const s of r.species) shown[s] += (target[s] - shown[s]) * Math.min(1, dt * 3);
      const sp = r.species, nReact = r.eq.split("<=>")[0].split(" + ").length;
      const top = 70, bot = h - 60, left = 70, right = w - 30;
      const vmax = Math.max(0.05, ...sp.map((s) => Math.max(res.initial[s], target[s]))) * 1.15;
      const Y = (v) => bot - (v / vmax) * (bot - top);
      ctx.strokeStyle = "#e3e8ef"; ctx.lineWidth = 1;
      const step = vmax > 1 ? 0.5 : vmax > 0.2 ? 0.1 : vmax > 0.05 ? 0.02 : 0.01;
      for (let v = 0; v <= vmax; v += step) {
        ctx.beginPath(); ctx.moveTo(left, Y(v)); ctx.lineTo(right, Y(v)); ctx.stroke();
        label(ctx, fmt(v, 3), left - 8, Y(v), { align: "right", font: "11px system-ui", color: "#4b5868" });
      }
      const gw = (right - left) / sp.length, bw = Math.min(46, gw / 3);
      sp.forEach((s, i) => {
        const color = i < nReact ? c1 : c2, cx = left + gw * (i + 0.5);
        ctx.fillStyle = color; ctx.globalAlpha = 0.3;
        ctx.fillRect(cx - bw - 2, Y(res.initial[s]), bw, bot - Y(res.initial[s]));
        ctx.globalAlpha = 1;
        ctx.fillRect(cx + 2, Y(shown[s]), bw, bot - Y(shown[s]));
        label(ctx, pretty(s), cx, bot + 18, { align: "center", font: "bold 13px system-ui" });
        label(ctx, fmt(target[s], 3), cx + 2 + bw / 2, Y(shown[s]) - 10, { align: "center", font: "11px system-ui" });
      });
      ctx.strokeStyle = "#39424e"; ctx.beginPath(); ctx.moveTo(left, bot); ctx.lineTo(right, bot); ctx.stroke();
    });

    L.scene.append(el("div", { style: "position:absolute;right:16px;top:52px" }, legend([
      { label: "Reactants", color: c1 }, { label: "Products", color: c2 },
    ]), el("div", { class: "note", style: "text-align:right" }, "faded = initial · solid = equilibrium")));
    build();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
