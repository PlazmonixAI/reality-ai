// Number formatting helpers for readouts.

export function fmt(value, digits = 4) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const a = Math.abs(value);
  if (a !== 0 && (a >= 1e6 || a < 1e-3)) {
    const [m, e] = value.toExponential(digits - 1).split("e");
    return `${m}×10${superscript(Number(e))}`;
  }
  const rounded = Number(value.toPrecision(digits));
  return rounded.toLocaleString("en-US", { maximumFractionDigits: 8 });
}

export function fmtUnit(value, unit, digits = 4) {
  const s = fmt(value, digits);
  return s === "—" || !unit ? s : `${s} ${unit}`;
}

const SUP = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
export function superscript(n) {
  return String(n).split("").map((c) => SUP[c] ?? c).join("");
}

/** Human-friendly duration: s, min, h or days. */
export function fmtTime(seconds, digits = 3) {
  if (!Number.isFinite(seconds)) return "—";
  const a = Math.abs(seconds);
  if (a < 120) return `${fmt(seconds, digits)} s`;
  if (a < 7200) return `${fmt(seconds / 60, digits)} min`;
  if (a < 3 * 86400) return `${fmt(seconds / 3600, digits)} h`;
  return `${fmt(seconds / 86400, digits)} days`;
}

/** Distance in m or km. */
export function fmtDistance(m, digits = 4) {
  if (!Number.isFinite(m)) return "—";
  return Math.abs(m) >= 1e4 ? `${fmt(m / 1000, digits)} km` : `${fmt(m, digits)} m`;
}
