// Shared energy bar chart drawn inside a scene (kinetic / potential / thermal / total).
import { label } from "../core/stage.js";
import { fmt } from "../core/format.js";

/** bars: [{name, value, color}] ; max: scale maximum (J). Draws in the box (x, y, w, h). */
export function drawEnergyBars(ctx, bars, max, x, y, w, h, { dark = false } = {}) {
  ctx.fillStyle = dark ? "rgba(255,255,255,.08)" : "rgba(255,255,255,.85)";
  ctx.strokeStyle = dark ? "rgba(255,255,255,.2)" : "#d8dee8";
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, 10); ctx.fill(); ctx.stroke();
  const ink = dark ? "#fff" : "#16202c", ink2 = dark ? "rgba(255,255,255,.7)" : "#4b5868";
  label(ctx, "Energy", x + w / 2, y + 14, { color: ink, font: "bold 12px system-ui", align: "center" });
  const top = y + 30, bottom = y + h - 34, span = bottom - top;
  const bw = Math.min(24, (w - 20) / bars.length - 14);
  const gap = (w - bars.length * bw) / (bars.length + 1);
  ctx.strokeStyle = ink2; ctx.beginPath(); ctx.moveTo(x + 8, bottom); ctx.lineTo(x + w - 8, bottom); ctx.stroke();
  bars.forEach((b, i) => {
    const bx = x + gap + i * (bw + gap);
    const bh = max > 0 ? Math.max(0, Math.min(1, b.value / max)) * span : 0;
    ctx.fillStyle = b.color;
    ctx.beginPath(); ctx.roundRect(bx, bottom - bh, bw, bh, [4, 4, 0, 0]); ctx.fill();
    label(ctx, b.name, bx + bw / 2, bottom + 11, { color: ink2, font: "11px system-ui", align: "center" });
    const v = Math.abs(b.value) < max * 1e-3 ? 0 : b.value;
    label(ctx, v === 0 ? "0" : fmt(v, 2), bx + bw / 2, bottom + 24, { color: ink, font: "11px system-ui", align: "center" });
  });
  label(ctx, "J", x + w - 10, y + 14, { color: ink2, font: "11px system-ui", align: "right" });
}
