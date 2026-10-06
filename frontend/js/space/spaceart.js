// Pictures drawn in the browser for the Universe Map: galaxies of every Hubble type, nebulae and clusters that
// have no free photograph, close-ups of stars, and star glints. They are illustrations generated from each object's
// engine data (type, axis ratio, temperature, radius); they never stand in for a measured number.
import * as THREE from "three";

// small deterministic random numbers, so an object always looks the same
export function rng(seed) {
  let s = (Math.abs(Math.floor(seed)) % 2147483646) + 1;
  return () => (s = (s * 48271) % 2147483647) / 2147483647;
}
export const hashName = (name) => [...String(name)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 7);
const gauss = (r) => { const u = Math.max(1e-9, r()), v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };

export function galaxyKind(type = "") {
  const t = type.trim();
  if (/^SB?0|^S0/.test(t)) return "lenticular";
  if (/^SB/.test(t)) return "barred";
  if (/^S/.test(t)) return "spiral";
  if (/^E/.test(t)) return "elliptical";
  if (/^I|^dI|^Irr/i.test(t)) return "irregular";
  return "spiral";
}
const axisRatio = (type) => { const m = /^E(\d)/.exec(type || ""); return m ? 1 - Number(m[1]) / 10 : 1; };

function canvas(size) { const c = document.createElement("canvas"); c.width = c.height = size; return c; }
function blob(ctx, x, y, r, rgba) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgba); g.addColorStop(1, rgba.replace(/[\d.]+\)$/, "0)")); ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); }

/** A galaxy of the given Hubble type, face-on, on a transparent background (size × size pixels). */
export function drawGalaxy(kind, seed, size = 256, type = "") {
  const c = canvas(size), ctx = c.getContext("2d"), R = rng(seed), h = size / 2;
  ctx.globalCompositeOperation = "lighter";
  if (kind === "elliptical" || kind === "lenticular") {
    const q = kind === "elliptical" ? axisRatio(type) : 1;
    ctx.save(); ctx.translate(h, h); ctx.scale(1, q);
    for (const [r, a] of [[h * 0.95, 0.10], [h * 0.6, 0.22], [h * 0.3, 0.45], [h * 0.12, 0.85]]) blob(ctx, 0, 0, r, `rgba(255,${214 + 20 * a | 0},${170 + 40 * a | 0},${a})`);
    if (kind === "lenticular") { ctx.scale(1, 1); for (let i = 0; i < 400; i++) { const t = R() * Math.PI * 2, rr = h * (0.25 + 0.6 * R()); ctx.fillStyle = "rgba(255,236,210,0.05)"; ctx.fillRect(Math.cos(t) * rr, Math.sin(t) * rr, 3, 3); } }
    for (let i = 0; i < 260; i++) { const rr = Math.abs(gauss(R)) * h * 0.35, t = R() * 7; ctx.fillStyle = "rgba(255,230,200,0.25)"; ctx.fillRect(Math.cos(t) * rr, Math.sin(t) * rr, 1.2, 1.2); }
    ctx.restore();
    return c;
  }
  if (kind === "irregular") {
    for (let i = 0; i < 22; i++) { const x = h + gauss(R) * h * 0.3, y = h + gauss(R) * h * 0.22, r = h * (0.08 + 0.2 * R()); blob(ctx, x, y, r, `rgba(${150 + 60 * R() | 0},${180 + 50 * R() | 0},255,0.22)`); }
    for (let i = 0; i < 40; i++) blob(ctx, h + gauss(R) * h * 0.3, h + gauss(R) * h * 0.22, 2 + 4 * R(), "rgba(255,120,170,0.5)");
    for (let i = 0; i < 500; i++) { ctx.fillStyle = "rgba(220,230,255,0.35)"; ctx.fillRect(h + gauss(R) * h * 0.32, h + gauss(R) * h * 0.24, 1.3, 1.3); }
    return c;
  }
  // spirals: two (sometimes more) logarithmic arms of young blue stars and pink star-forming knots, a yellow bulge
  const arms = R() < 0.75 ? 2 : 3, pitch = 0.18 + 0.22 * R(), barLen = kind === "barred" ? h * (0.22 + 0.12 * R()) : 0, rot = R() * Math.PI * 2;
  blob(ctx, h, h, h * 0.95, "rgba(150,170,230,0.10)");
  for (let a = 0; a < arms; a++) for (let i = 0; i < 70; i++) { // the soft glow of each arm under its stars
    const t = (i / 70) * 4.2, r0 = barLen || h * 0.08, rr = r0 * Math.exp(pitch * t * 2.2), th = rot + (a * 2 * Math.PI) / arms + t;
    if (rr < h * 0.92) blob(ctx, h + rr * Math.cos(th), h + rr * Math.sin(th), h * (0.06 + 0.05 * t / 4.2), "rgba(160,185,255,0.10)");
  }
  for (let a = 0; a < arms; a++) {
    for (let i = 0; i < 1400; i++) {
      const u = R(), t = u * 4.2, r0 = barLen || h * 0.08;
      const rr = r0 * Math.exp(pitch * t * 2.2), th = rot + (a * 2 * Math.PI) / arms + t;
      if (rr > h * 0.95) continue;
      const sp = h * 0.035 * (1 + 2 * u), x = h + rr * Math.cos(th) + gauss(R) * sp, y = h + rr * Math.sin(th) + gauss(R) * sp;
      const k = R();
      ctx.fillStyle = k < 0.04 ? "rgba(255,110,160,0.8)" : k < 0.6 ? "rgba(170,195,255,0.45)" : "rgba(255,240,220,0.3)";
      const s = k < 0.04 ? 2.2 : 1.3; ctx.fillRect(x, y, s, s);
    }
  }
  if (barLen) { ctx.save(); ctx.translate(h, h); ctx.rotate(rot); ctx.scale(1, 0.22); blob(ctx, 0, 0, barLen * 1.15, "rgba(255,225,180,0.55)"); ctx.restore(); }
  blob(ctx, h, h, h * 0.22, "rgba(255,226,170,0.75)"); blob(ctx, h, h, h * 0.08, "rgba(255,248,230,0.95)");
  // dust lanes on the inner edge of the arms
  ctx.globalCompositeOperation = "destination-out";
  for (let a = 0; a < arms; a++) for (let i = 0; i < 260; i++) {
    const t = R() * 3.6, r0 = barLen || h * 0.1, rr = r0 * Math.exp(pitch * t * 2.2) * 0.93, th = rot + (a * 2 * Math.PI) / arms + t - 0.12;
    if (rr > h * 0.9 || rr < h * 0.26) continue; // no dust across the bright core
    ctx.fillStyle = "rgba(0,0,0,0.18)"; ctx.fillRect(h + rr * Math.cos(th), h + rr * Math.sin(th), 3, 3);
  }
  return c;
}

/** A nebula or star cluster of the given OpenNGC type (for objects with no free photograph). */
export function drawNebula(type, seed, size = 256) {
  const c = canvas(size), ctx = c.getContext("2d"), R = rng(seed), h = size / 2;
  ctx.globalCompositeOperation = "lighter";
  if (/Planetary/.test(type)) { // a shell: oxygen blue-green inside, hydrogen red at the edge, a hot white dwarf at the centre
    const q = 0.7 + 0.3 * R();
    ctx.save(); ctx.translate(h, h); ctx.rotate(R() * 3); ctx.scale(1, q);
    blob(ctx, 0, 0, h * 0.55, "rgba(90,220,210,0.35)");
    for (let i = 0; i < 900; i++) { const t = R() * 7, rr = h * (0.42 + 0.12 * gauss(R) * 0.5); ctx.fillStyle = R() < 0.5 ? "rgba(255,90,90,0.25)" : "rgba(120,240,220,0.18)"; ctx.fillRect(Math.cos(t) * rr, Math.sin(t) * rr, 2, 2); }
    ctx.restore(); blob(ctx, h, h, 4, "rgba(255,255,255,1)");
  } else if (/Globular/.test(type)) {
    for (let i = 0; i < 2600; i++) { const rr = Math.abs(gauss(R)) * h * 0.28, t = R() * 7; ctx.fillStyle = R() < 0.2 ? "rgba(255,200,140,0.6)" : "rgba(255,245,225,0.45)"; ctx.fillRect(h + Math.cos(t) * rr, h + Math.sin(t) * rr, 1.4, 1.4); }
    blob(ctx, h, h, h * 0.3, "rgba(255,236,200,0.35)");
  } else if (/Open cluster|association|Double/.test(type)) {
    for (let i = 0; i < 120; i++) { const x = h + gauss(R) * h * 0.35, y = h + gauss(R) * h * 0.35, k = R(); blob(ctx, x, y, 2 + 5 * R(), k < 0.7 ? "rgba(190,210,255,0.9)" : k < 0.9 ? "rgba(255,255,240,0.9)" : "rgba(255,190,120,0.9)"); }
  } else if (/Dark/.test(type)) {
    ctx.globalCompositeOperation = "source-over";
    for (let i = 0; i < 30; i++) blob(ctx, h + gauss(R) * h * 0.25, h + gauss(R) * h * 0.18, h * (0.1 + 0.2 * R()), "rgba(20,14,10,0.35)");
  } else { // emission, reflection, supernova remnants: wisps and filaments
    const col = /Reflection/.test(type) ? [110, 150, 255] : /Supernova/.test(type) ? [255, 150, 90] : [255, 80, 110];
    for (let i = 0; i < 26; i++) blob(ctx, h + gauss(R) * h * 0.3, h + gauss(R) * h * 0.3, h * (0.1 + 0.3 * R()), `rgba(${col[0]},${col[1]},${col[2]},0.12)`);
    ctx.strokeStyle = `rgba(${col[0]},${col[1] + 40},${col[2] + 40},0.35)`; ctx.lineWidth = 1.2;
    for (let i = 0; i < 40; i++) { ctx.beginPath(); let x = h + gauss(R) * h * 0.35, y = h + gauss(R) * h * 0.35; ctx.moveTo(x, y); for (let k = 0; k < 8; k++) { x += gauss(R) * 9; y += gauss(R) * 9; ctx.lineTo(x, y); } ctx.stroke(); }
    for (let i = 0; i < 40; i++) blob(ctx, h + gauss(R) * h * 0.35, h + gauss(R) * h * 0.35, 1.5 + 2 * R(), "rgba(220,235,255,0.9)");
  }
  return c;
}

/** A star seen up close: the disc in its blackbody colour with limb darkening and granulation, and the Sun to scale. */
export function drawStar(cnv, { colour = "#ffffff", radius_solar = 1, temperature_k = 5772, seed = 1 }) {
  const ctx = cnv.getContext("2d"), W = cnv.width, H = cnv.height, R = rng(seed);
  ctx.fillStyle = "#03060c"; ctx.fillRect(0, 0, W, H);
  const big = Math.max(radius_solar, 1), maxR = Math.min(W, H) * 0.42, scale = maxR / big;
  const rs = Math.max(2, radius_solar * scale), cx = radius_solar >= 1 ? W * 0.42 : W * 0.3, cy = H / 2;
  const halo = ctx.createRadialGradient(cx, cy, rs * 0.9, cx, cy, rs * 1.6); halo.addColorStop(0, colour + "88"); halo.addColorStop(1, colour + "00");
  ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(cx, cy, rs * 1.6, 0, 7); ctx.fill();
  const disc = ctx.createRadialGradient(cx - rs * 0.15, cy - rs * 0.15, 0, cx, cy, rs); // limb darkening: the edge looks dimmer and redder
  disc.addColorStop(0, "#ffffff"); disc.addColorStop(0.35, colour); disc.addColorStop(1, temperature_k < 4500 ? "#5a1c08" : "#7a4a20");
  ctx.fillStyle = disc; ctx.beginPath(); ctx.arc(cx, cy, rs, 0, 7); ctx.fill();
  ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, rs, 0, 7); ctx.clip(); // convection cells: few and huge on red giants, fine on hot stars
  const cells = Math.round(temperature_k < 4500 && radius_solar > 10 ? 18 : 260), cr = rs / Math.sqrt(cells) * 1.4;
  for (let i = 0; i < cells; i++) { const a = R() * 7, d = Math.sqrt(R()) * rs; ctx.fillStyle = R() < 0.5 ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.10)"; ctx.beginPath(); ctx.arc(cx + Math.cos(a) * d, cy + Math.sin(a) * d, cr * (0.6 + 0.6 * R()), 0, 7); ctx.fill(); }
  ctx.restore();
  // the Sun at the same scale
  const sr = Math.max(1.5, scale), sx = radius_solar >= 1 ? W * 0.88 : W * 0.72, sy = cy;
  ctx.fillStyle = "#ffe9b0"; ctx.beginPath(); ctx.arc(sx, sy, sr, 0, 7); ctx.fill();
  ctx.fillStyle = "#c9d4e4"; ctx.font = "12px Plex, system-ui"; ctx.textAlign = "center";
  ctx.fillText("the Sun, same scale", sx, Math.min(H - 6, sy + sr + 16));
}

/** A star glint with diffraction spikes, like a space-telescope image. */
export function spikeTexture() {
  const c = canvas(128), ctx = c.getContext("2d"), h = 64;
  ctx.globalCompositeOperation = "lighter";
  blob(ctx, h, h, 22, "rgba(255,255,255,0.9)");
  for (const [dx, dy] of [[1, 0], [0, 1]]) {
    const g = ctx.createLinearGradient(h - dx * h, h - dy * h, h + dx * h, h + dy * h);
    g.addColorStop(0, "rgba(255,255,255,0)"); g.addColorStop(0.5, "rgba(255,255,255,0.9)"); g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g; dx ? ctx.fillRect(0, h - 1, 128, 2) : ctx.fillRect(h - 1, 0, 2, 128);
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export const toTexture = (cnv) => { const t = new THREE.CanvasTexture(cnv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
