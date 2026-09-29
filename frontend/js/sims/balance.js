// Balancing Equations: chemistry.check_balance tallies every atom for the coefficients you choose.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, select, readouts, el, button, legend, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { drawMolecule, atomColor, pretty } from "./atomdraw.js";

const EQUATIONS = [
  "H2 + O2 -> H2O", "N2 + H2 -> NH3", "CH4 + O2 -> CO2 + H2O", "C3H8 + O2 -> CO2 + H2O", "Fe + O2 -> Fe2O3",
  "Al + O2 -> Al2O3", "Na + Cl2 -> NaCl", "KClO3 -> KCl + O2", "C6H12O6 + O2 -> CO2 + H2O", "Fe2O3 + CO -> Fe + CO2",
  "NH3 + O2 -> NO + H2O", "Cu + Ag+ -> Cu^2+ + Ag",
];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, coeffs = [], comps = {}, reveal = false;

    const pick = select({ label: "Reaction", value: EQUATIONS[0], options: EQUATIONS.map((e) => ({ value: e, label: e.split(/\s*->\s*/).map((side) => side.split(/\s+\+\s+/).map(pretty).join(" + ")).join(" → ") })), onChange: () => start() });
    const steppers = el("div", { class: "control" });
    const out = readouts([{ key: "s", label: "Status" }]);
    L.side.append(
      panel("Choose coefficients", pick.root, steppers, button("Show the answer", () => { reveal = true; draw(); }), button("Reset to 1s", () => start()),
        el("p", { class: "note" }, "Atoms are never created or destroyed: every element must count the same on both sides.")),
      panel("Check (from the engine)", out.root, legend([{ label: "atoms on reactant side", color: c1 }, { label: "atoms on product side", color: c2 }])),
    );

    function renderSteppers(species) {
      steppers.replaceChildren(...species.map((sp, i) => el("div", { style: "display:flex;align-items:center;gap:8px;margin:4px 0" },
        button("−", () => { coeffs[i] = Math.max(1, coeffs[i] - 1); recompute(); }),
        el("b", { style: "min-width:2ch;text-align:center" }, String(coeffs[i])),
        button("+", () => { coeffs[i] = Math.min(20, coeffs[i] + 1); recompute(); }),
        el("span", {}, pretty(sp)))));
    }

    async function start() {
      reveal = false;
      const n = pick.value.split(/\s*->\s*/).flatMap((s) => s.split(/\s+\+\s+/)).length;
      coeffs = Array(n).fill(1);
      recompute();
    }

    const recompute = liveRequest(async (signal) => {
      const r = await simulate("chemistry", "check_balance", { equation: pick.value, coefficients: coeffs }, signal);
      // Composition of each species (for drawing molecules)
      const need = r.result.species.filter((s) => !comps[s]);
      const got = await Promise.all(need.map((s) => simulate("chemistry", "molar_mass", { formula: s.replace(/\^?\d*[+-]$/, "") }, signal)));
      need.forEach((s, i) => { comps[s] = Object.fromEntries(Object.entries(got[i].composition).map(([k, v]) => [k, v.atoms])); });
      return r;
    }, {
      delay: 10, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        renderSteppers(res.species);
        out.set("s", res.balanced ? (res.smallest ? "Balanced! ✔" : `Balanced, but every coefficient can be divided by ${res.multiple_of_smallest}`) : "Not balanced yet");
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = res && res.balanced ? "#eef8f2" : "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const sp = res.species, sides = res.sides, nL = sides.filter((s) => s < 0).length;
      // Equation line
      const text = sp.map((s, i) => `${coeffs[i] > 1 ? coeffs[i] + " " : ""}${pretty(s)}`), left = text.slice(0, nL).join(" + "), right = text.slice(nL).join(" + ");
      label(ctx, `${left}  →  ${right}`, w / 2, 30, { align: "center", font: "bold 20px system-ui" });
      if (reveal) label(ctx, `Answer: ${res.correct_equation}`, w / 2, 58, { align: "center", font: "14px system-ui", color: "#4b5868" });
      // Molecules: left half and right half
      const drawSide = (idx, x0, x1) => {
        let x = x0 + 20;
        idx.forEach((i) => {
          const comp = comps[sp[i]]; if (!comp) return;
          const nAtoms = Object.values(comp).reduce((a, b) => a + b, 0), cell = 34 + Math.sqrt(nAtoms) * 16;
          for (let k = 0; k < Math.min(coeffs[i], 12); k++) {
            const col = k % 3, row = Math.floor(k / 3);
            drawMolecule(ctx, comp, x + col * cell + cell / 2, 110 + row * cell + cell / 2, 10);
          }
          label(ctx, pretty(sp[i]), x + (Math.min(coeffs[i], 3) * cell) / 2, 96, { align: "center", font: "12px system-ui", color: "#4b5868" });
          x += Math.min(coeffs[i], 3) * cell + 24;
        });
        return x;
      };
      drawSide(sp.map((_, i) => i).filter((i) => sides[i] < 0), 0, w / 2);
      drawSide(sp.map((_, i) => i).filter((i) => sides[i] > 0), w / 2, w);
      ctx.strokeStyle = "#c9ced6"; ctx.beginPath(); ctx.moveTo(w / 2, 80); ctx.lineTo(w / 2, h - 170); ctx.stroke();
      // Atom tally bars (left vs right) from the engine
      const rows = res.tally, top = h - 150, bw = Math.min(70, (w - 80) / rows.length - 16), maxN = Math.max(...rows.map((r) => Math.max(Math.abs(r.left), Math.abs(r.right))), 1);
      rows.forEach((r, j) => {
        const x = 40 + j * (bw + 16) * 1.0 + j * 10, sc = 90 / maxN;
        ctx.fillStyle = c1; ctx.fillRect(x, top + 100 - Math.abs(r.left) * sc, bw / 2 - 2, Math.abs(r.left) * sc);
        ctx.fillStyle = c2; ctx.fillRect(x + bw / 2, top + 100 - Math.abs(r.right) * sc, bw / 2 - 2, Math.abs(r.right) * sc);
        label(ctx, r.element === "charge" ? "charge" : r.element, x + bw / 2, top + 116, { align: "center", font: "bold 12px system-ui", color: r.element === "charge" ? "#16202c" : atomColor(r.element) === "#ffffff" ? "#16202c" : atomColor(r.element) });
        label(ctx, `${fmt(r.left, 3)} | ${fmt(r.right, 3)}`, x + bw / 2, top + 132, { align: "center", font: "11px system-ui", color: r.balanced ? "#1baf7a" : "#e34948" });
      });
    }

    start();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
