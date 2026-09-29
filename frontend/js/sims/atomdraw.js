// Shared helper: draw a molecule as a small cluster of CPK-coloured atoms (composition comes from the engine).
const CPK = { H: "#ffffff", C: "#39424e", N: "#3b6fd6", O: "#e34948", Cl: "#1baf7a", F: "#8fd16a", S: "#eda100", P: "#eb6834",
  Na: "#7b5cd6", K: "#8f5cc0", Ca: "#9aa6b5", Fe: "#b5543a", Cu: "#c46a2c", Ag: "#c9ced6", Zn: "#8c96a8", Mg: "#5fb04a", Al: "#b8c4d3" };
export const atomColor = (el) => CPK[el] || "#c9a0dc";

/** composition: {El: count}; draws atoms spiralling out from (x, y) with radius r. */
export function drawMolecule(ctx, composition, x, y, r = 7) {
  const atoms = [];
  for (const [el, n] of Object.entries(composition)) for (let i = 0; i < n; i++) atoms.push(el);
  atoms.sort((a, b) => (a === "H") - (b === "H")); // heavy atoms in the middle, H around
  atoms.forEach((el, i) => {
    const ring = i === 0 ? 0 : Math.ceil(Math.sqrt(i));
    const ang = i * 2.39996; // golden angle
    const px = x + Math.cos(ang) * ring * r * 1.05, py = y + Math.sin(ang) * ring * r * 1.05;
    ctx.fillStyle = atomColor(el); ctx.strokeStyle = "rgba(22,32,44,.55)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(px, py, el === "H" ? r * 0.72 : r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  });
}

/** Display a formula with subscripts and superscript charges: 'Fe2O3' → 'Fe₂O₃', 'Cu^2+' → 'Cu²⁺'. */
export function pretty(formula) {
  const sub = "₀₁₂₃₄₅₆₇₈₉", sup = "⁰¹²³⁴⁵⁶⁷⁸⁹";
  const m = formula.match(/^(.*?)(?:\^(\d*)([+-])|([+-]+))$/);
  let body = formula, charge = "";
  if (m && m[1]) { body = m[1]; const n = m[2] ?? ""; const sign = m[3] || m[4][0]; charge = [...(m[4] ? (m[4].length > 1 ? String(m[4].length) : "") : n)].map((d) => sup[+d]).join("") + (sign === "+" ? "⁺" : "⁻"); }
  return body.replace(/([A-Za-z)\]])(\d+)/g, (_, a, d) => a + [...d].map((x) => sub[+x]).join("")) + charge;
}
