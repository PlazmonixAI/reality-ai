// Spaceflight Lab: design engines and satellites, build a rocket from parts, then fly it — to orbit, to the Moon
// and back. The engine does all the physics: physics.rocket_engine_design, satellite_design, rocket_design,
// rocket_launch_state and rocket_flight (gravity of Earth and the moving Moon, thrust, drag, staging, fairings,
// landing, orbit prediction). The browser draws, takes the pilot's inputs and interpolates between steps.
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";

const P = (part, count) => (count ? { part, count } : { part });
const TEMPLATES = {
  orbiter: { name: "Crew orbiter (2 stages)", body: "earth", parts: [P("engine_booster", 9), P("tank_xl"), P("interstage"), P("decoupler"), P("engine_vacuum"), P("tank_l"), P("decoupler"), P("parachute"), P("capsule"), P("nose")] },
  smallsat: { name: "Small launcher + CubeSat", body: "earth", parts: [P("engine_micro", 9), P("tank_xs"), P("tank_xs"), P("tank_xs"), P("interstage_s"), P("decoupler"), P("engine_micro"), P("tank_xs"), P("decoupler"), P("sat_cubesat"), P("fairing_s")] },
  geo: { name: "Geostationary comsat launcher", body: "earth", parts: [P("engine_methalox", 5), P("tank_xl"), P("tank_xl"), P("tank_xl"), P("interstage"), P("decoupler"), P("engine_vacuum"), P("tank_l"), P("tank_l"), P("decoupler"), P("sat_comms"), P("fairing")] },
  lunarOrbiter: { name: "Lunar orbiter mission", body: "earth", parts: [P("engine_methalox", 5), P("tank_xl"), P("tank_xl"), P("tank_xl"), P("interstage"), P("decoupler"), P("engine_vacuum"), P("tank_l"), P("tank_l"), P("decoupler"), P("sat_lunar"), P("fairing")] },
  telescope: { name: "Space telescope (heavy)", body: "earth", parts: [P("engine_heavy", 3), P("tank_xl"), P("tank_xl"), P("interstage"), P("decoupler"), P("engine_vacuum", 2), P("tank_l"), P("decoupler"), P("sat_telescope"), P("fairing_xl")] },
  moon: { name: "Moon landing (super-heavy)", body: "earth", parts: [P("engine_f1", 5), P("tank_xl"), P("tank_xl"), P("tank_xl"), P("interstage"), P("decoupler"), P("engine_hydrolox", 2), P("tank_xl"), P("interstage"), P("decoupler"), P("engine_cryo_vac"), P("tank_l"), P("decoupler"), P("legs"), P("engine_lander"), P("tank_s"), P("lander"), P("nose")] },
  sounding: { name: "Sounding rocket", body: "earth", parts: [P("engine_booster"), P("tank_m"), P("decoupler"), P("parachute"), P("probe"), P("nose")] },
  hopper: { name: "Moon hopper", body: "moon", parts: [P("legs"), P("engine_lander"), P("tank_s"), P("lander")] },
  mars: { name: "Mars ascent vehicle", body: "mars", parts: [P("legs"), P("engine_booster"), P("tank_m"), P("interstage"), P("decoupler"), P("engine_lander", 2), P("tank_s"), P("probe"), P("nose")] },
};
const GROUPS = [
  ["My designs", (p) => p.custom], ["Command & crew", (p) => p.category === "command"], ["Satellites", (p) => p.category === "satellite" && !p.custom],
  ["Fuel tanks", (p) => p.category === "tank"],
  ["Engines · small", (p) => p.category === "engine" && !p.custom && p.class === "small"], ["Engines · medium", (p) => p.category === "engine" && !p.custom && p.class === "medium"],
  ["Engines · large", (p) => p.category === "engine" && !p.custom && p.class === "large"], ["Engines · heavy", (p) => p.category === "engine" && !p.custom && p.class === "heavy"],
  ["Structure, fairings & recovery", (p) => ["structural", "aero", "recovery"].includes(p.category)],
];
const WARPS = [1, 2, 5, 10, 25, 100, 1000, 10000, 100000];
const SKY = { earth: [[0, [118, 178, 255]], [12e3, [70, 120, 220]], [35e3, [20, 30, 80]], [70e3, [2, 4, 12]]], mars: [[0, [220, 170, 120]], [15e3, [150, 100, 80]], [45e3, [8, 6, 10]]], moon: [[0, [0, 0, 0]]] };
const GROUND = { earth: ["#3d7a3a", "#2c5e2a"], mars: ["#b5643b", "#8e4a2b"], moon: ["#8f8f94", "#6e6e74"] };
const OMEGA = { earth: -7.2921159e-5, moon: -2.6617e-6, mars: -7.088218e-5 };
const CLASS_TONE = { small: "#8a93a3", medium: "#6b7280", large: "#5b6270", heavy: "#474d57" };
const STORE = "reality-asm.spaceflight.custom-parts";
const SITES = [[-52.77, "Kourou (Guiana)"], [80.23, "Sriharikota (India)"], [-80.6, "Cape Canaveral (USA)"], [63.3, "Baikonur (Kazakhstan)"], [110.95, "Wenchang (China)"]];
const takeStored = (key) => { try { const v = localStorage.getItem(key); localStorage.removeItem(key); return v; } catch { return null; } };
const putStored = (key, v) => { try { localStorage.setItem(key, v); } catch { /* storage unavailable */ } };
const loadCustom = () => { try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; } };
const saveCustom = (c) => { try { localStorage.setItem(STORE, JSON.stringify(c)); } catch { /* storage unavailable */ } };
const isFairing = (p) => p.id?.startsWith("fairing");
const isEngine = (p) => p.category === "engine";

// ---------- part drawing (used by the builder, the flight view and the designers) ----------
function bell(ctx, ex, top, bot, bw, tone, vacuum) {
  const g = ctx.createLinearGradient(ex - bw / 2, 0, ex + bw / 2, 0);
  g.addColorStop(0, "#1b1e23"); g.addColorStop(0.5, vacuum ? "#b8745a" : tone); g.addColorStop(1, "#1b1e23");
  ctx.fillStyle = g; ctx.beginPath();
  const neck = vacuum ? 0.16 : 0.22, h = bot - top;
  ctx.moveTo(ex - bw * neck, top); ctx.lineTo(ex + bw * neck, top); ctx.quadraticCurveTo(ex + bw * 0.3, bot - h * 0.3, ex + bw / 2, bot);
  ctx.lineTo(ex - bw / 2, bot); ctx.quadraticCurveTo(ex - bw * 0.3, bot - h * 0.3, ex - bw * neck, top); ctx.fill(); ctx.stroke();
}
function drawProfile(ctx, prof, cx, top, sy, sx, tone) { // engine drawn from the designer's computed nozzle contour
  const zmax = prof[prof.length - 1][0];
  const g = ctx.createLinearGradient(cx - prof[prof.length - 1][1] * sx, 0, cx + prof[prof.length - 1][1] * sx, 0);
  g.addColorStop(0, "#1b1e23"); g.addColorStop(0.5, tone); g.addColorStop(1, "#1b1e23");
  ctx.fillStyle = g; ctx.beginPath();
  prof.forEach(([z, r], i) => { const y = top + (z / zmax) * sy; i ? ctx.lineTo(cx + r * sx, y) : ctx.moveTo(cx + r * sx, y); });
  for (let i = prof.length - 1; i >= 0; i--) { const [z, r] = prof[i]; ctx.lineTo(cx - r * sx, top + (z / zmax) * sy); }
  ctx.closePath(); ctx.fill(); ctx.stroke();
}
function panels(ctx, x, y, w, h, span, rows = 1) {
  ctx.fillStyle = "#23408a"; ctx.strokeStyle = "rgba(160,190,255,.5)";
  for (const side of [-1, 1]) {
    const px = side < 0 ? x - span : x + w, pw = span;
    ctx.fillRect(px, y, pw, h); ctx.strokeRect(px, y, pw, h);
    for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(px + (pw * i) / 4, y); ctx.lineTo(px + (pw * i) / 4, y + h); ctx.stroke(); }
    if (rows > 1) { ctx.beginPath(); ctx.moveTo(px, y + h / 2); ctx.lineTo(px + pw, y + h / 2); ctx.stroke(); }
  }
}
function drawSatellite(ctx, p, cx, yb, s, x, y, w, h) {
  const gold = ctx.createLinearGradient(x, 0, x + w, 0); gold.addColorStop(0, "#9c7a2c"); gold.addColorStop(0.5, "#f0cf6b"); gold.addColorStop(1, "#8a6a22");
  ctx.strokeStyle = "rgba(20,30,45,.7)";
  const box = (bx, by, bw, bh, fill = gold) => { ctx.fillStyle = fill; ctx.fillRect(bx, by, bw, bh); ctx.strokeRect(bx, by, bw, bh); };
  switch (p.id) {
    case "sat_cubesat": box(x, y, w, h, "#c9ced6"); ctx.fillStyle = "#23408a"; ctx.fillRect(x + w * 0.1, y + h * 0.1, w * 0.8, h * 0.8); panels(ctx, x, y + h * 0.2, w, h * 0.5, w * 0.9); break;
    case "sat_comms": box(x + w * 0.15, y + h * 0.1, w * 0.7, h * 0.8); panels(ctx, x + w * 0.15, y + h * 0.3, w * 0.7, h * 0.35, w * 1.1, 2);
      ctx.fillStyle = "#e6e9ee"; ctx.beginPath(); ctx.ellipse(cx, y + h * 0.1, w * 0.32, h * 0.08, 0, Math.PI, 0); ctx.fill(); ctx.stroke(); break;
    case "sat_telescope": { const g = ctx.createLinearGradient(x, 0, x + w, 0); g.addColorStop(0, "#8b939e"); g.addColorStop(0.5, "#eef1f5"); g.addColorStop(1, "#7a828c");
      box(x + w * 0.1, y, w * 0.8, h, g); ctx.fillStyle = "#1c2430"; ctx.fillRect(x + w * 0.1, y, w * 0.8, h * 0.05); panels(ctx, x + w * 0.1, y + h * 0.45, w * 0.8, h * 0.3, w * 0.35); break; }
    case "sat_nav": box(x + w * 0.2, y + h * 0.15, w * 0.6, h * 0.7); panels(ctx, x + w * 0.2, y + h * 0.3, w * 0.6, h * 0.4, w * 0.8, 2); ctx.fillStyle = "#e6e9ee"; ctx.fillRect(x + w * 0.3, y, w * 0.4, h * 0.15); break;
    case "sat_earthobs": box(x + w * 0.2, y + h * 0.1, w * 0.6, h * 0.8); panels(ctx, x + w * 0.2, y + h * 0.2, w * 0.6, h * 0.35, w * 0.7);
      ctx.fillStyle = "#1c2430"; ctx.beginPath(); ctx.arc(cx, y + h * 0.8, w * 0.12, 0, Math.PI * 2); ctx.fill(); break;
    default: { // generic, lunar orbiter and user-designed satellites
      const hasEngine = !!p.thrust_vac;
      box(x + w * 0.15, y, w * 0.7, h * (hasEngine ? 0.78 : 1)); panels(ctx, x + w * 0.15, y + h * 0.2, w * 0.7, h * 0.35, Math.max(w * 0.6, s * Math.sqrt(p.solar_area || 6) * 0.5));
      if (hasEngine) { ctx.strokeStyle = "rgba(20,30,45,.6)"; bell(ctx, cx, y + h * 0.78, yb, w * 0.35, "#6b7280", true); }
    }
  }
}
function drawPart(ctx, p, cx, yb, s, opts = {}) {
  // cx = centre x, yb = bottom y (screen), s = px per metre. Returns drawn height in px.
  const h = p.height * s, w = p.width * s, x = cx - w / 2, y = yb - h;
  const white = opts.dim ? "#9fb0c4" : "#f4f6f9", shade = "rgba(0,0,0,.18)";
  const cyl = (fill) => { const g = ctx.createLinearGradient(x, 0, x + w, 0); g.addColorStop(0, fill); g.addColorStop(0.45, "#ffffff"); g.addColorStop(1, "#9aa6b5"); return g; };
  ctx.save();
  ctx.lineWidth = Math.max(1, s * 0.05); ctx.strokeStyle = "rgba(20,30,45,.6)";
  if (p.category === "tank") {
    ctx.fillStyle = cyl(white); ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = "#1c2430";
    for (const f of [0.08, 0.92]) ctx.fillRect(x, y + h * f - s * 0.12, w, s * 0.24);
    if (p.height >= 6) { ctx.fillStyle = shade; ctx.fillRect(x + w * 0.1, y + h * 0.25, w * 0.12, h * 0.5); }
  } else if (isEngine(p)) {
    const n = p.count || 1, vacuum = p.isp_sl < 0.6 * p.isp_vac, tone = CLASS_TONE[p.class] || "#6b7280";
    if (opts.profile && n === 1) {
      ctx.fillStyle = "#30353d"; ctx.fillRect(cx - w * 0.3, y, w * 0.6, h * 0.08);
      drawProfile(ctx, opts.profile, cx, y + h * 0.06, h * 0.94, (w / 2) / Math.max(...opts.profile.map((q) => q[1])) * 0.9, vacuum ? "#b8745a" : tone);
    } else {
      const bw = Math.min(w, (p.width * 3.4 * s) / Math.max(1, Math.sqrt(n) * 1.6)) * (vacuum ? 1 : 0.9);
      const across = Math.min(n, 5), gap = bw * 0.9, span = (across - 1) * gap;
      ctx.fillStyle = "#30353d"; ctx.fillRect(cx - Math.max(bw, span / 2 + bw / 2) * 0.55, y, Math.max(bw, span / 2 + bw / 2) * 1.1, h * 0.25);
      for (let i = 0; i < across; i++) bell(ctx, cx - span / 2 + i * gap, y + h * 0.2, yb, bw, tone, vacuum);
      if (n > 5) { ctx.fillStyle = "#fff"; ctx.font = `bold ${Math.max(9, s * 0.8)}px system-ui`; ctx.textAlign = "center"; ctx.fillText(`×${n}`, cx, y + h * 0.18); }
    }
  } else if (p.category === "satellite") drawSatellite(ctx, p, cx, yb, s, x, y, w, h);
  else if (p.id.startsWith("interstage")) {
    const g = ctx.createLinearGradient(x, 0, x + w, 0); g.addColorStop(0, "#2a2f36"); g.addColorStop(0.5, "#5b6270"); g.addColorStop(1, "#23272e");
    ctx.fillStyle = g; ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);
  } else if (isFairing(p)) { // the nose of the fairing (its cylinder around the payload is drawn by drawShells)
    ctx.fillStyle = cyl(white); ctx.globalAlpha = opts.ghost ? 0.55 : 1; ctx.beginPath(); ctx.moveTo(x, yb); ctx.bezierCurveTo(x, y + h * 0.35, cx - w * 0.3, y, cx, y); ctx.bezierCurveTo(cx + w * 0.3, y, x + w, y + h * 0.35, x + w, yb); ctx.closePath(); ctx.fill(); ctx.stroke();
  } else switch (p.id) {
    case "decoupler": ctx.fillStyle = "#2a2f36"; ctx.fillRect(x, y, w, h); ctx.fillStyle = "#f2c230"; for (let i = 0; i < 6; i++) ctx.fillRect(x + (i + 0.25) * (w / 6), y + h * 0.25, w / 12, h * 0.5); break;
    case "nose": { ctx.fillStyle = cyl(white); ctx.beginPath(); ctx.moveTo(x, yb); ctx.quadraticCurveTo(x, y + h * 0.15, cx, y); ctx.quadraticCurveTo(x + w, y + h * 0.15, x + w, yb); ctx.closePath(); ctx.fill(); ctx.stroke(); break; }
    case "capsule": case "lander": {
      ctx.fillStyle = cyl(p.id === "lander" ? "#d8c79a" : "#c8ced8"); ctx.beginPath(); ctx.moveTo(x, yb); ctx.lineTo(x + w * 0.28, y); ctx.lineTo(x + w * 0.72, y); ctx.lineTo(x + w, yb); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#1c3350"; ctx.beginPath(); ctx.arc(cx, y + h * 0.5, Math.max(1.5, w * 0.1), 0, Math.PI * 2); ctx.fill();
      break;
    }
    case "probe": ctx.fillStyle = "#c9ced6"; ctx.beginPath(); ctx.ellipse(cx, yb, w / 2, h, 0, Math.PI, 0); ctx.fill(); ctx.stroke(); ctx.fillStyle = "#2a78d6"; ctx.fillRect(cx - w * 0.08, y + h * 0.3, w * 0.16, h * 0.3); break;
    case "parachute": ctx.fillStyle = "#e0662e"; ctx.beginPath(); ctx.roundRect(x + w * 0.1, y, w * 0.8, h, h * 0.4); ctx.fill(); ctx.stroke(); break;
    case "legs": ctx.strokeStyle = "#5b6270"; ctx.lineWidth = Math.max(1.5, s * 0.25); ctx.beginPath(); ctx.moveTo(cx - w * 0.25, y); ctx.lineTo(x, yb); ctx.moveTo(cx + w * 0.25, y); ctx.lineTo(x + w, yb); ctx.stroke(); break;
    default: ctx.fillStyle = white; ctx.fillRect(x, y, w, h);
  }
  if (opts.selected) { ctx.strokeStyle = "#ffd33d"; ctx.lineWidth = 2; ctx.setLineDash([5, 4]); ctx.strokeRect(x - 3, y - 3, w + 6, h + 6); ctx.setLineDash([]); }
  ctx.restore();
  return h;
}
// Fairing cylinders around their payloads and interstage shrouds around the next stage's engine
function drawShells(ctx, parts, layout, cx, s, ghost) {
  ctx.save();
  ctx.lineWidth = Math.max(1, s * 0.05); ctx.strokeStyle = "rgba(20,30,45,.6)";
  parts.forEach((p, i) => {
    let from = -1;
    if (isFairing(p)) { from = i; while (from > 0 && parts[from - 1].id !== "decoupler") from--; if (from === i) return; }
    else if (p.id.startsWith("interstage") && parts[i + 1]?.id === "decoupler" && parts[i + 2] && isEngine(parts[i + 2])) from = i + 3;
    else return;
    const w = p.width * s, x = cx - w / 2;
    const top = isFairing(p) ? layout[i][1] : layout[i + 2][0], bottom = isFairing(p) ? layout[from][1] : layout[i][0];
    const g = ctx.createLinearGradient(x, 0, x + w, 0);
    if (isFairing(p)) { g.addColorStop(0, "#c9d1dc"); g.addColorStop(0.45, "#ffffff"); g.addColorStop(1, "#9aa6b5"); } else { g.addColorStop(0, "#2a2f36"); g.addColorStop(0.5, "#5b6270"); g.addColorStop(1, "#23272e"); }
    ctx.globalAlpha = ghost ? 0.5 : 1; ctx.fillStyle = g; ctx.fillRect(x, top, w, bottom - top);
    ctx.globalAlpha = 1; ctx.strokeRect(x, top, w, bottom - top);
    if (ghost) { ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, bottom); ctx.stroke(); ctx.setLineDash([]); }
  });
  ctx.restore();
}
function drawStack(ctx, parts, cx, yb, s, opts = {}) { // → [[top, bottom], …] per part
  const layout = [], covered = new Set(); // parts inside a closed (non-cutaway) fairing are hidden
  if (!opts.ghost && !opts.hideFairing) parts.forEach((p, i) => { if (isFairing(p)) for (let j = i - 1; j >= 0 && parts[j].id !== "decoupler"; j--) covered.add(j); });
  parts.forEach((p, i) => {
    const h = p.height * s;
    layout.push([yb - h, yb]);
    if (!(isFairing(p) && opts.hideFairing) && !covered.has(i)) drawPart(ctx, p, cx, yb, s, { selected: i === opts.selected, profile: p.profile, ghost: opts.ghost });
    yb -= h;
  });
  drawShells(ctx, opts.hideFairing ? parts.map((p) => (isFairing(p) ? { ...p, id: "gone" } : p)) : parts, layout, cx, s, opts.ghost);
  return layout;
}
function iconCanvas(p) {
  const c = el("canvas", { width: 56, height: 56 }), ctx = c.getContext("2d");
  const wide = p.category === "satellite" ? 2.6 : 1.1;
  const s = Math.min(44 / Math.max(p.height, 0.1), 44 / (p.width * wide));
  drawPart(ctx, { ...p, count: 1 }, 28, 28 + (p.height * s) / 2, s, { profile: p.profile });
  return c;
}

export default {
  mount(root) {
    let catalogue = null, stack = TEMPLATES.orbiter.parts.map((p) => ({ ...p })), body = "earth", selected = -1, design = null;
    let mode = "build", customs = loadCustom();
    const rootEl = el("div", { class: "sf-root" });
    root.append(rootEl);
    const usedCustom = (parts = stack) => { const ids = new Set(parts.map((p) => p.part)); const out = {}; for (const [id, c] of Object.entries(customs)) if (ids.has(id)) out[id] = c.spec; return out; };
    const allParts = () => [...catalogue.parts, ...Object.entries(customs).map(([id, c]) => ({ id, ...c.spec, class: c.class, profile: c.profile, custom: true }))];

    // ======================= BUILD MODE =======================
    const bCanvas = el("canvas", { class: "sf-build-canvas" });
    const palette = el("div", { class: "sf-palette" });
    const statsBox = el("div", { class: "sf-stats" });
    const partBox = el("div", { class: "sf-partbox" });
    const tplSel = el("select", { class: "sf-select", "aria-label": "Template", onchange: () => { const t = TEMPLATES[tplSel.value]; if (t) { stack = t.parts.map((p) => ({ ...p })); body = t.body; bodySel.value = body; selected = -1; refresh(); } } },
      el("option", { value: "" }, "Templates…"), ...Object.entries(TEMPLATES).map(([k, t]) => el("option", { value: k }, t.name)));
    const bodySel = el("select", { class: "sf-select", "aria-label": "Launch from", onchange: () => { body = bodySel.value; refresh(); } },
      el("option", { value: "earth" }, "Launch from Earth"), el("option", { value: "moon" }, "Launch from the Moon"), el("option", { value: "mars" }, "Launch from Mars"));
    const handoff = takeStored("reality-asm.mission-date"); // set by the Solar System's "launch on this date" button
    const dateIn = el("input", { class: "sf-select sf-date", type: "datetime-local", "aria-label": "Launch date (UTC)", title: "Launch date and time (UTC): sets the real Moon, Sun and Earth rotation",
      value: (handoff ? new Date(handoff) : new Date()).toISOString().slice(0, 16) });
    const siteSel = el("select", { class: "sf-select", "aria-label": "Launch site", title: "Launch site (flights are planar, so the site is projected onto the equator)" },
      ...SITES.map(([lon, name]) => el("option", { value: lon }, name)));
    const startSel = el("select", { class: "sf-select", "aria-label": "Start" }, el("option", { value: "pad" }, "Start on the launch pad"), el("option", { value: "orbit" }, "Start in low orbit (skip ascent)"));
    const launchBtn = el("button", { class: "sf-launch", type: "button", onclick: () => startFlight() }, "LAUNCH ▶");
    const clearBtn = el("button", { class: "sf-small", type: "button", onclick: () => { stack = []; selected = -1; refresh(); } }, "Clear");
    const buildView = el("div", { class: "sf-build" },
      el("div", { class: "sf-build-top" }, el("span", { class: "sf-title" }, "ROCKET BUILDER"), tplSel, bodySel, siteSel, dateIn, startSel, clearBtn,
        el("button", { class: "sf-small accent", type: "button", onclick: () => openEngineDesigner() }, "⚙ Engine designer"),
        el("button", { class: "sf-small accent", type: "button", onclick: () => openSatDesigner() }, "🛰 Satellite designer"),
        el("span", { class: "sf-spacer" }), launchBtn),
      palette, el("div", { class: "sf-build-stage" }, bCanvas), el("div", { class: "sf-right" }, partBox, statsBox));
    rootEl.append(buildView);

    function renderPalette() {
      const parts = allParts();
      palette.replaceChildren(...GROUPS.flatMap(([label, test]) => {
        const items = parts.filter(test);
        if (!items.length) return label === "My designs" ? [el("div", { class: "sf-cat" }, el("div", { class: "sf-cat-title" }, label), el("p", { class: "sf-hint small" }, "Design an engine or a satellite (buttons above) and it appears here."))] : [];
        return [el("div", { class: "sf-cat" }, el("div", { class: "sf-cat-title" }, label), ...items.map((p) => el("div", { class: "sf-part-wrap" },
          el("button", { class: "sf-part", type: "button", title: p.name, onclick: () => { stack.push({ part: p.id }); selected = stack.length - 1; refresh(); } },
            iconCanvas(p), el("span", {}, p.name), el("small", {}, p.thrust_vac && p.category === "engine" ? `${fmt(p.thrust_vac / 1000, 3)} kN · Isp ${fmt(p.isp_vac, 3)} s` : p.prop ? `${fmt(p.prop / 1000, 3)} t fuel` : `${fmt(p.mass, 3)} kg`)),
          p.custom ? el("button", { class: "sf-del", type: "button", title: "Delete design", "aria-label": `Delete ${p.name}`, onclick: () => { delete customs[p.id]; saveCustom(customs); stack = stack.filter((q) => q.part !== p.id); renderPalette(); refresh(); } }, "✕") : "")))];
      }));
    }
    const partOf = (e) => { const p = allParts().find((q) => q.id === e.part) || { id: e.part, name: e.part, category: "structural", mass: 0, height: 1, width: 1 }; return { ...p, count: e.count || 1 }; };

    function renderPartBox() {
      if (selected < 0 || !stack[selected]) { partBox.replaceChildren(el("p", { class: "sf-hint" }, "Tap a part on the left to stack it on top. Tap a part on the rocket to edit it. Decouplers split stages; the lowest stage fires first. Put an interstage under a decoupler to cover the next engine, and a fairing on top to protect satellites.")); return; }
      const p = partOf(stack[selected]);
      const row = [el("div", { class: "sf-part-name" }, p.name)];
      if (isEngine(p)) row.push(el("div", { class: "sf-row" }, el("span", {}, "Engines"),
        el("button", { class: "sf-small", type: "button", onclick: () => { stack[selected].count = Math.max(1, (stack[selected].count || 1) - 1); refresh(); } }, "−"),
        el("b", {}, String(p.count)), el("button", { class: "sf-small", type: "button", onclick: () => { stack[selected].count = Math.min(9, (stack[selected].count || 1) + 1); refresh(); } }, "+")));
      row.push(el("div", { class: "sf-row" },
        el("button", { class: "sf-small", type: "button", onclick: () => { if (selected < stack.length - 1) { [stack[selected], stack[selected + 1]] = [stack[selected + 1], stack[selected]]; selected++; refresh(); } } }, "Move up"),
        el("button", { class: "sf-small", type: "button", onclick: () => { if (selected > 0) { [stack[selected], stack[selected - 1]] = [stack[selected - 1], stack[selected]]; selected--; refresh(); } } }, "Move down"),
        el("button", { class: "sf-small danger", type: "button", onclick: () => { stack.splice(selected, 1); selected = -1; refresh(); } }, "Remove")));
      const facts = [["Mass", `${fmt(p.mass * p.count, 4)} kg`]];
      if (p.class) facts.push(["Size class", p.class]);
      if (p.prop) facts.push(["Propellant", `${fmt(p.prop, 4)} kg`]);
      if (p.thrust_vac) facts.push(["Thrust (sea level / vacuum)", `${fmt((p.thrust_sl * p.count) / 1000, 4)} / ${fmt((p.thrust_vac * p.count) / 1000, 4)} kN`], ["Isp (sea level / vacuum)", `${fmt(p.isp_sl, 3)} / ${fmt(p.isp_vac, 3)} s`]);
      partBox.replaceChildren(...row, ...facts.map(([k, v]) => el("div", { class: "sf-fact" }, el("span", {}, k), el("b", {}, v))));
    }

    let designSeq = 0;
    async function refresh() {
      renderPartBox(); drawBuild();
      if (!stack.length) { design = null; statsBox.replaceChildren(el("p", { class: "sf-hint" }, "Empty launch pad.")); launchBtn.disabled = true; return; }
      const seq = ++designSeq;
      try {
        const r = await simulate("physics", "rocket_design", { parts: stack, body, custom_parts: usedCustom() });
        if (seq !== designSeq) return;
        design = r.result; renderStats(); launchBtn.disabled = false;
      } catch (e) { statsBox.replaceChildren(el("p", { class: "sf-warn" }, e.message)); launchBtn.disabled = true; }
    }
    function renderStats() {
      const d = design, need = d.delta_v_to_orbit_estimate, frac = Math.min(1, d.total_delta_v_vac / need);
      statsBox.replaceChildren(
        el("div", { class: "sf-stat-big" }, el("span", {}, "Δv (vacuum)"), el("b", {}, `${fmt(d.total_delta_v_vac, 4)} m/s`)),
        el("div", { class: "sf-meter" }, el("i", { style: `width:${frac * 100}%;background:${frac >= 1 ? "#1baf7a" : "#eb6834"}` })),
        el("div", { class: "sf-meter-label" }, `${frac >= 1 ? "Enough" : "Not enough"} for orbit (≈ ${fmt(need, 3)} m/s incl. losses)`),
        el("div", { class: "sf-missions" }, ...Object.entries(d.mission_delta_v).map(([m, dv]) => el("span", { class: d.total_delta_v_vac >= dv ? "ok" : "" }, `${d.total_delta_v_vac >= dv ? "✓" : "✗"} ${m} · ${fmt(dv / 1000, 3)} km/s`))),
        el("div", { class: "sf-fact" }, el("span", {}, "Mass"), el("b", {}, `${fmt(d.total_mass / 1000, 4)} t`)),
        el("div", { class: "sf-fact" }, el("span", {}, "Height"), el("b", {}, `${fmt(d.height, 3)} m`)),
        ...d.stages.map((s) => el("div", { class: "sf-stage" }, el("div", { class: "sf-stage-h" }, `Stage ${s.stage + 1}${s.has_fairing ? " · fairing" : ""}${s.interstage ? " · interstage" : ""}`),
          el("div", { class: "sf-fact" }, el("span", {}, "Δv"), el("b", {}, `${fmt(s.delta_v_vac, 4)} m/s`)),
          el("div", { class: "sf-fact" }, el("span", {}, "TWR"), el("b", { class: s.twr_surface < 1 && s.stage === 0 ? "bad" : "" }, fmt(s.twr_surface, 3))),
          el("div", { class: "sf-fact" }, el("span", {}, "Burn time"), el("b", {}, s.burn_time ? `${fmt(s.burn_time, 3)} s` : "—")))),
        ...d.warnings.map((w) => el("p", { class: "sf-warn" }, "⚠ " + w)));
    }

    let bLayout = [];
    function drawBuild() {
      const c = bCanvas, W = c.clientWidth, H = c.clientHeight;
      if (!W || !catalogue) return;
      const dpr = Math.min(2, devicePixelRatio); c.width = W * dpr; c.height = H * dpr;
      const ctx = c.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "#1f4f86"; ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = "rgba(255,255,255,.08)"; ctx.lineWidth = 1;
      for (let gx = 0; gx < W; gx += 24) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke(); }
      for (let gy = 0; gy < H; gy += 24) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke(); }
      const parts = stack.map(partOf), total = parts.reduce((a, p) => a + p.height, 0) || 1, maxW = Math.max(3.2, ...parts.map((p) => p.width));
      const s = Math.min((H - 80) / total, (W * 0.45) / maxW, 22);
      const yb = H - 40;
      ctx.fillStyle = "rgba(255,255,255,.15)"; ctx.fillRect(W / 2 - 80, yb, 160, 6);
      bLayout = drawStack(ctx, parts, W / 2, yb, s, { selected, ghost: true });
      let st = 1, from = yb; // stage brackets
      parts.forEach((p, i) => { if (p.id === "decoupler" || i === parts.length - 1) { const to = bLayout[i][0], bx = W / 2 + maxW * s / 2 + 26; ctx.strokeStyle = "rgba(255,255,255,.45)"; ctx.beginPath(); ctx.moveTo(bx, from); ctx.lineTo(bx + 6, from); ctx.lineTo(bx + 6, to); ctx.lineTo(bx, to); ctx.stroke(); ctx.fillStyle = "#cfe0f5"; ctx.font = "12px system-ui"; ctx.fillText(`Stage ${st}`, bx + 12, (from + to) / 2 + 4); st++; from = to; } });
      if (!parts.length) { ctx.fillStyle = "#cfe0f5"; ctx.font = "15px system-ui"; ctx.textAlign = "center"; ctx.fillText("Add an engine, a fuel tank and a capsule or satellite", W / 2, H / 2); ctx.textAlign = "left"; }
    }
    bCanvas.addEventListener("click", (e) => {
      const r = bCanvas.getBoundingClientRect(), y = e.clientY - r.top;
      selected = bLayout.findIndex(([t, b]) => y >= t && y <= b); refresh();
    });

    // ======================= DESIGNERS (engine and satellite) =======================
    const modal = el("div", { class: "sf-modal hidden" });
    rootEl.append(modal);
    const closeModal = () => { modal.classList.add("hidden"); modal.replaceChildren(); };
    function control(label, input, out) { return el("label", { class: "sf-ctl" }, el("span", {}, label), input, out || ""); }
    function slider(min, max, value, step, onInput, log = false) {
      const toV = (u) => (log ? Math.exp(Math.log(min) + (Math.log(max) - Math.log(min)) * u) : min + (max - min) * u);
      const toU = (v) => (log ? (Math.log(v) - Math.log(min)) / (Math.log(max) - Math.log(min)) : (v - min) / (max - min));
      const out = el("b", { class: "sf-ctl-val" });
      const inp = el("input", { type: "range", min: 0, max: 1000, value: Math.round(toU(value) * 1000), oninput: () => { const v = +(toV(inp.value / 1000)).toPrecision(3); out.textContent = fmt(v, 3); onInput(v); } });
      out.textContent = fmt(value, 3);
      return [inp, out];
    }
    function addCustom(kind, name, spec, extra) {
      const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 24) || kind;
      const id = `custom_${slug}_${Date.now().toString(36)}`;
      customs[id] = { spec, ...extra };
      saveCustom(customs); renderPalette();
      stack.push({ part: id }); selected = stack.length - 1; refresh();
      closeModal();
    }

    function openEngineDesigner() {
      const args = { name: "My engine", propellant: "lox_ch4", cycle: "full_flow", chamber_pressure_bar: 250, expansion_ratio: 35, thrust_vac_kn: 1800, nozzle: "bell" };
      let res = null, seq = 0;
      const canvas = el("canvas", { class: "sf-design-canvas" }), stats = el("div", { class: "sf-design-stats" }), addBtn = el("button", { class: "sf-launch", type: "button", disabled: true, onclick: () => res && addCustom("engine", args.name, res.part, { class: res.size_class, profile: res.profile }) }, "ADD TO MY PARTS");
      const sel = (key, opts) => el("select", { class: "sf-select", onchange: (e) => { args[key] = e.target.value; run(); } }, ...opts.map(([v, t]) => el("option", { value: v, selected: v === args[key] }, t)));
      const [pcIn, pcOut] = slider(5, 350, args.chamber_pressure_bar, 1, (v) => { args.chamber_pressure_bar = v; run(); });
      const [epsIn, epsOut] = slider(3, 300, args.expansion_ratio, 1, (v) => { args.expansion_ratio = v; run(); }, true);
      const [fIn, fOut] = slider(1, 10000, args.thrust_vac_kn, 1, (v) => { args.thrust_vac_kn = v; run(); }, true);
      const nameIn = el("input", { class: "sf-text", value: args.name, maxlength: 32, oninput: () => { args.name = nameIn.value || "My engine"; } });
      const controls = el("div", { class: "sf-design-controls" },
        control("Name", nameIn),
        control("Propellant", sel("propellant", [["lox_rp1", "LOX / kerosene (RP-1)"], ["lox_ch4", "LOX / methane"], ["lox_lh2", "LOX / hydrogen"], ["nto_mmh", "N₂O₄ / MMH (hypergolic)"]])),
        control("Engine cycle", sel("cycle", [["pressure_fed", "Pressure-fed"], ["electric_pump", "Electric pump"], ["gas_generator", "Gas generator"], ["expander", "Expander"], ["staged_combustion", "Staged combustion"], ["full_flow", "Full-flow staged combustion"]])),
        control("Chamber pressure (bar)", pcIn, pcOut), control("Nozzle expansion ratio", epsIn, epsOut), control("Vacuum thrust (kN)", fIn, fOut),
        control("Nozzle shape", sel("nozzle", [["bell", "Bell (80 %)"], ["cone", "15° cone"]])),
        el("p", { class: "sf-hint small" }, "Sea-level engines use expansion ratios of ~10–40; vacuum engines 80–300. Higher chamber pressure means a smaller, more efficient engine."));
      modal.replaceChildren(el("div", { class: "sf-design" },
        el("div", { class: "sf-design-head" }, el("b", {}, "ENGINE DESIGNER"), el("small", {}, "physics.rocket_engine_design — ideal-rocket nozzle theory calibrated on real engines"),
          el("button", { class: "sf-close", type: "button", "aria-label": "Close", onclick: closeModal }, "×")),
        el("div", { class: "sf-design-body" }, controls, el("div", { class: "sf-design-view" }, canvas, stats)),
        el("div", { class: "sf-design-foot" }, addBtn)));
      modal.classList.remove("hidden");
      let timer = 0;
      function run() { clearTimeout(timer); timer = setTimeout(go, 120); }
      async function go() {
        const my = ++seq;
        try { const r = await simulate("physics", "rocket_engine_design", args); if (my !== seq) return; res = r.result; addBtn.disabled = false; show(); }
        catch (e) { stats.replaceChildren(el("p", { class: "sf-warn" }, e.message)); addBtn.disabled = true; }
      }
      function show() {
        const r = res, W = canvas.clientWidth || 300, H = canvas.clientHeight || 300, dpr = Math.min(2, devicePixelRatio);
        canvas.width = W * dpr; canvas.height = H * dpr;
        const ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.fillStyle = "#0e2240"; ctx.fillRect(0, 0, W, H);
        const sc = Math.min((H - 60) / r.length, (W - 80) / r.exit_diameter);
        ctx.strokeStyle = "rgba(20,30,45,.8)"; ctx.lineWidth = 1;
        drawProfile(ctx, r.profile, W / 2, 30, r.length * sc, sc, r.sea_level_flow_separation ? "#b8745a" : CLASS_TONE[r.size_class]);
        ctx.fillStyle = "#9cc0ea"; ctx.font = "11px system-ui"; ctx.textAlign = "center";
        ctx.fillText(`exit Ø ${fmt(r.exit_diameter, 3)} m`, W / 2, 30 + r.length * sc + 16);
        const tz = r.profile[2][0] / r.profile[r.profile.length - 1][0] * r.length * sc + 30;
        ctx.textAlign = "left"; ctx.fillText(`throat Ø ${fmt(r.throat_diameter, 3)} m`, W / 2 + r.throat_diameter * sc / 2 + 8, tz + 4);
        ctx.fillText(`length ${fmt(r.length, 3)} m`, 8, 18);
        const rows = [["Size class", r.size_class], ["Thrust sea level / vacuum", `${fmt(r.thrust_sl / 1000, 4)} / ${fmt(r.thrust_vac / 1000, 4)} kN`],
          ["Isp sea level / vacuum", `${fmt(r.isp_sl, 4)} / ${fmt(r.isp_vac, 4)} s`], ["Mass · thrust/weight", `${fmt(r.mass, 4)} kg · ${fmt(r.thrust_to_weight, 3)}`],
          ["Mass flow (fuel + oxidizer)", `${fmt(r.mass_flow, 4)} kg/s`], ["c* · exit Mach", `${fmt(r.characteristic_velocity, 4)} m/s · ${fmt(r.exit_mach, 3)}`],
          ["Exit pressure", `${fmt(r.exit_pressure / 1000, 3)} kPa`], ["Chamber temperature", `${fmt(r.chamber_temperature, 4)} K`]];
        stats.replaceChildren(...rows.map(([k, v]) => el("div", { class: "sf-fact" }, el("span", {}, k), el("b", {}, v))),
          el("div", { class: "sf-alt" }, el("span", {}, "Thrust vs altitude (% of vacuum)"), ...r.thrust_vs_altitude.map((a) => el("i", { title: `${a.altitude_km} km: ${fmt(a.thrust_kn, 4)} kN, Isp ${fmt(a.isp, 3)} s`, style: `height:${Math.max(2, (a.thrust_kn / (r.thrust_vac / 1000)) * 100)}%` }, el("em", {}, `${a.altitude_km} km`)))),
          ...r.warnings.map((w) => el("p", { class: "sf-warn" }, "⚠ " + w)));
      }
      go();
    }

    function openSatDesigner() {
      const args = { name: "My satellite", bus: "medium", payload_kg: 300, solar_area_m2: 12, cell_efficiency: 0.3, battery_wh: 4500, power_draw_w: 1500, propellant_kg: 200, thruster: "hydrazine", altitude_km: 700 };
      let res = null, seq = 0;
      const canvas = el("canvas", { class: "sf-design-canvas" }), stats = el("div", { class: "sf-design-stats" }), addBtn = el("button", { class: "sf-launch", type: "button", disabled: true, onclick: () => res && addCustom("satellite", args.name, { ...res.part }, {}) }, "ADD TO MY PARTS");
      const sel = (key, opts) => el("select", { class: "sf-select", onchange: (e) => { args[key] = e.target.value; run(); } }, ...opts.map(([v, t]) => el("option", { value: v, selected: v === args[key] }, t)));
      const sl = (key, min, max, log) => slider(min, max, args[key], 1, (v) => { args[key] = v; run(); }, log);
      const nameIn = el("input", { class: "sf-text", value: args.name, maxlength: 32, oninput: () => { args.name = nameIn.value || "My satellite"; } });
      const controls = el("div", { class: "sf-design-controls" }, control("Name", nameIn),
        control("Bus size", sel("bus", [["cubesat", "CubeSat"], ["small", "Small (≤ 500 kg)"], ["medium", "Medium"], ["large", "Large"]])),
        control("Instruments / payload (kg)", ...sl("payload_kg", 1, 8000, true)), control("Solar array area (m²)", ...sl("solar_area_m2", 0.1, 150, true)),
        control("Solar cell efficiency", ...sl("cell_efficiency", 0.15, 0.4)), control("Battery (Wh)", ...sl("battery_wh", 20, 50000, true)),
        control("Electrical load (W)", ...sl("power_draw_w", 5, 20000, true)), control("Propellant (kg)", ...sl("propellant_kg", 1, 5000, true)),
        control("Thruster", sel("thruster", [["cold_gas", "Cold gas"], ["hydrazine", "Hydrazine"], ["bipropellant", "Bipropellant"], ["ion", "Ion (electric)"]])),
        control("Orbit altitude (km)", ...sl("altitude_km", 200, 36000, true)),
        el("p", { class: "sf-hint small" }, "LEO ≈ 400–800 km · navigation ≈ 20,200 km · geostationary = 35,786 km."));
      modal.replaceChildren(el("div", { class: "sf-design" },
        el("div", { class: "sf-design-head" }, el("b", {}, "SATELLITE DESIGNER"), el("small", {}, "physics.satellite_design — mass, Δv, power and eclipse budget"),
          el("button", { class: "sf-close", type: "button", "aria-label": "Close", onclick: closeModal }, "×")),
        el("div", { class: "sf-design-body" }, controls, el("div", { class: "sf-design-view" }, canvas, stats)),
        el("div", { class: "sf-design-foot" }, addBtn)));
      modal.classList.remove("hidden");
      let timer = 0;
      function run() { clearTimeout(timer); timer = setTimeout(go, 120); }
      async function go() {
        const my = ++seq;
        try { const r = await simulate("physics", "satellite_design", args); if (my !== seq) return; res = r.result; addBtn.disabled = false; show(); }
        catch (e) { stats.replaceChildren(el("p", { class: "sf-warn" }, e.message)); addBtn.disabled = true; }
      }
      function show() {
        const r = res, W = canvas.clientWidth || 300, H = canvas.clientHeight || 300, dpr = Math.min(2, devicePixelRatio);
        canvas.width = W * dpr; canvas.height = H * dpr;
        const ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.fillStyle = "#050a14"; ctx.fillRect(0, 0, W, H);
        const p = { ...r.part, id: "custom", solar_area: args.solar_area_m2 };
        const span = Math.sqrt(args.solar_area_m2 / 2), sc = Math.min((H - 60) / p.height, (W - 40) / (p.width + 2 * Math.max(span, p.width * 0.6)));
        drawPart(ctx, p, W / 2, H / 2 + (p.height * sc) / 2, sc);
        ctx.fillStyle = "#9cc0ea"; ctx.font = "11px system-ui"; ctx.fillText(`bus ≈ ${fmt(p.width, 2)} m`, 8, 18);
        const rows = [["Dry / wet mass", `${fmt(r.dry_mass, 4)} / ${fmt(r.wet_mass, 4)} kg`], ["Δv (own thruster)", `${fmt(r.delta_v, 4)} m/s`], ["Thrust", `${fmt(r.thrust, 3)} N`],
          ["Orbital period", `${fmt(r.orbital_period / 60, 4)} min`], ["Longest eclipse", `${fmt(r.eclipse_duration / 60, 3)} min`],
          ["Power in sunlight / orbit average", `${fmt(r.power_in_sunlight, 4)} / ${fmt(r.orbit_average_power, 4)} W`], ["Battery depth of discharge", `${fmt(r.battery_depth_of_discharge * 100, 3)} %`]];
        stats.replaceChildren(el("div", { class: `sf-badge ${r.power_ok ? "ok" : "bad"}` }, r.power_ok ? "Power budget closes" : "Power budget fails"),
          ...rows.map(([k, v]) => el("div", { class: "sf-fact" }, el("span", {}, k), el("b", {}, v))), ...r.warnings.map((w) => el("p", { class: "sf-warn" }, "⚠ " + w)));
      }
      go();
    }

    // ======================= FLIGHT MODE =======================
    const fCanvas = el("canvas", { class: "sf-flight-canvas" });
    const hud = el("div", { class: "sf-hud" });
    const toast = el("div", { class: "sf-toast" });
    const thr = el("input", { class: "sf-throttle", type: "range", min: 0, max: 100, value: 0, "aria-label": "Throttle", oninput: () => { throttle = thr.value / 100; thrLabel.textContent = `${thr.value}%`; } });
    const thrLabel = el("div", { class: "sf-thr-label" }, "0%");
    const warpLabel = el("span", { class: "sf-warp-label" }, "1×");
    const focusBtn = el("button", { class: "sf-btn wide", type: "button", onclick: () => { mapFocus = mapFocus === "earth" ? "moon" : mapFocus === "moon" ? "auto" : "earth"; focusBtn.textContent = `FOCUS: ${mapFocus.toUpperCase()}`; } }, "FOCUS: AUTO");
    const sasBtns = ["free", "prograde", "retrograde", "up"].map((m) => el("button", { class: "sf-sas", type: "button", onclick: () => setSas(m) }, { free: "Free", prograde: "Prograde", retrograde: "Retro", up: "Up" }[m]));
    const hold = (dirn) => { const b = el("button", { class: "sf-rot", type: "button", "aria-label": dirn < 0 ? "Rotate left" : "Rotate right" }, dirn < 0 ? "⟲" : "⟳");
      b.addEventListener("pointerdown", () => { rotating = dirn; setSas("free"); }); ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => b.addEventListener(ev, () => { rotating = 0; })); return b; };
    const fairingBtn = el("button", { class: "sf-fairbtn", type: "button", onclick: () => { fairingReq = true; } }, "FAIRING");
    const btn3d = el("button", { class: "sf-btn wide accent", type: "button", title: "See the flight in 3D over the real Earth and Moon", onclick: () => show3d(!view3dOn) }, "3D");
    let f3d = null, view3dOn = false;
    async function show3d(on) {
      view3dOn = on; btn3d.classList.toggle("on", on);
      if (on && !f3d) {
        const { createFlight3D } = await import("../space/flight3d.js");
        f3d = createFlight3D(flightView, { rocketHeight: flight.parts.reduce((a, q) => a + q.height, 0),
          onSolarSystem: (jd) => { putStored("reality-asm.solar-date", new Date((jd - 2440587.5) * 86400000).toISOString()); location.hash = "#/sim/solarsystem"; } });
        if (flight.last) f3d.update(flight.last);
      }
      if (f3d) f3d.show(view3dOn);
      if (on) mapView = false;
    }
    const flightView = el("div", { class: "sf-flight hidden" }, fCanvas, hud, toast,
      el("div", { class: "sf-topright" },
        el("button", { class: "sf-btn", type: "button", onclick: () => setWarp(warpIdx - 1) }, "«"), warpLabel, el("button", { class: "sf-btn", type: "button", onclick: () => setWarp(warpIdx + 1) }, "»"),
        el("button", { class: "sf-btn wide", type: "button", onclick: () => { mapView = !mapView; show3d(false); } }, "MAP"), focusBtn, btn3d,
        el("button", { class: "sf-btn wide", type: "button", onclick: () => toBuild() }, "BUILD")),
      el("div", { class: "sf-throttle-box" }, el("div", { class: "sf-thr-title" }, "THROTTLE"), thr, thrLabel,
        el("button", { class: "sf-small", type: "button", onclick: () => setThrottle(1) }, "Full"), el("button", { class: "sf-small", type: "button", onclick: () => setThrottle(0) }, "Cut")),
      el("div", { class: "sf-bottomleft" }, hold(-1), hold(1), el("div", { class: "sf-sas-row" }, ...sasBtns)),
      el("div", { class: "sf-bottomright" }, fairingBtn,
        el("button", { class: "sf-stagebtn", type: "button", onclick: () => { stageReq = true; } }, "STAGE"),
        el("button", { class: "sf-chutebtn", type: "button", onclick: () => { chuteReq = true; } }, "CHUTE")));
    rootEl.append(flightView);

    let flight = null, prev = null, throttle = 0, rel = 0, rotating = 0, sas = "free", warpIdx = 0, mapView = false, mapFocus = "auto";
    let stageReq = false, chuteReq = false, fairingReq = false, busy = false, stepStart = 0, stepLen = 0.1, zoom = 1, raf = 0, lastT = 0, log = [], ended = false;
    const setThrottle = (v) => { throttle = v; thr.value = Math.round(v * 100); thrLabel.textContent = `${thr.value}%`; };
    function setSas(m) { sas = m; sasBtns.forEach((b, i) => b.classList.toggle("on", ["free", "prograde", "retrograde", "up"][i] === m)); }
    function setWarp(i) { warpIdx = Math.max(0, Math.min(WARPS.length - 1, i)); warpLabel.textContent = `${WARPS[warpIdx]}×`; }
    setSas("free");

    async function startFlight() {
      const start = startSel.value;
      if (start === "pad" && (!design || design.warnings.some((w) => w.includes("cannot leave")))) { if (!confirm("This rocket probably can't lift off. Launch anyway?")) return; }
      const custom = usedCustom();
      let r;
      const when = body === "earth" ? { date: new Date((dateIn.value || new Date().toISOString().slice(0, 16)) + ":00Z").toISOString(), site_longitude_deg: +siteSel.value } : {};
      try { r = await simulate("physics", "rocket_launch_state", { parts: stack, body, custom_parts: custom, start, ...when }); }
      catch (e) { statsBox.prepend(el("p", { class: "sf-warn" }, "⚠ " + e.message)); return; }
      const parts = stack.map(partOf);
      flight = { state: r.result, tel: null, traj: [], trajMoon: [], trajDt: 0, planet: null, local: null, moon: null, parts, stages: splitStages(parts), custom, ref: body, jettisonAt: 0 };
      prev = null; rel = 0; setThrottle(0); setWarp(0); mapView = false; log = []; ended = false; zoom = 1;
      fairingBtn.style.display = parts.some(isFairing) ? "" : "none";
      btn3d.style.display = body === "earth" ? "" : "none"; show3d(false);
      if (f3d) { f3d.dispose(); f3d = null; }
      mode = "flight"; buildView.classList.add("hidden"); flightView.classList.remove("hidden");
      say(start === "orbit" ? "In a circular parking orbit. Open the MAP (M); the HUD shows the next trans-lunar injection window." : `Ready on the pad — ${bodySel.selectedOptions[0].textContent.replace("Launch from ", "")}. Throttle up (Z) to lift off.`);
      step(0.05);
    }
    function toBuild() { show3d(false); mode = "build"; flightView.classList.add("hidden"); buildView.classList.remove("hidden"); refresh(); }
    function splitStages(parts) { const out = []; let cur = []; parts.forEach((p) => { cur.push(p); if (p.id === "decoupler") { out.push(cur); cur = []; } }); if (cur.length) out.push(cur); return out; }
    function say(msg) { log.unshift({ msg, t: performance.now() }); log = log.slice(0, 4); }

    function commandAngle() {
      const s = flight.state, L = flight.local || { x: s.x, y: s.y, vx: s.vx, vy: s.vy, body: s.body }, up = Math.atan2(L.y, L.x);
      if (sas !== "free" && flight.tel && !s.landed) {
        const om = OMEGA[L.body] || 0, surface = flight.tel.altitude < 30000 && L.body !== "moon";
        const vx = surface ? L.vx - -om * L.y : L.vx, vy = surface ? L.vy - om * L.x : L.vy; // surface velocity low down
        let target = up;
        if (sas === "prograde" && Math.hypot(vx, vy) > 1) target = Math.atan2(vy, vx);
        if (sas === "retrograde" && Math.hypot(vx, vy) > 1) target = Math.atan2(-vy, -vx);
        rel = Math.atan2(Math.sin(target - up), Math.cos(target - up));
      }
      return up + rel;
    }

    async function step(dt) {
      if (busy || !flight) return;
      busy = true;
      const s = flight.state;
      const wantStage = stageReq, wantChute = chuteReq, wantFairing = fairingReq; stageReq = chuteReq = fairingReq = false;
      try {
        const r = await simulate("physics", "rocket_flight", { state: s, parts: stack, throttle: ended ? 0 : throttle, angle: commandAngle(), dt, stage: wantStage, deploy_chute: wantChute,
          jettison_fairing: wantFairing, custom_parts: flight.custom, predict: mapView || view3dOn || warpIdx > 0 || Math.random() < 0.2 });
        flight.last = r; if (f3d) f3d.update(r);
        prev = { ...flight.state, local: flight.local }; flight.state = r.result.state; flight.tel = r.result.telemetry; flight.planet = r.planet; flight.local = r.local; flight.moon = r.moon || null;
        if (r.trajectory.length) { flight.traj = r.trajectory; flight.trajMoon = r.trajectory_moon || []; flight.trajDt = r.trajectory_dt || 0; }
        for (const e of r.result.events) { say(e.charAt(0).toUpperCase() + e.slice(1)); if (e.startsWith("fairing jettisoned")) flight.jettisonAt = performance.now(); }
        const tel = r.result.telemetry;
        if (tel.reference !== flight.ref) { say(tel.reference === "moon" ? "Entered the Moon's sphere of influence" : "Left the Moon's sphere of influence"); flight.ref = tel.reference; }
        if (flight.state.crashed && !ended) { ended = true; setThrottle(0); setWarp(0); say("Vehicle destroyed. Press BUILD to try again."); }
        if (tel.status === "orbit" && !flight.orbitSaid) { flight.orbitSaid = true; say("Orbit achieved! 🎉"); }
        if (tel.status === "lunar orbit" && !flight.lunarSaid) { flight.lunarSaid = true; say("Lunar orbit achieved! 🌕"); }
        stepStart = performance.now(); stepLen = Math.max(0.05, dt / WARPS[warpIdx]);
      } catch (e) { say(`Engine error: ${e.message}`); } finally { busy = false; }
    }

    // Keyboard
    const onKey = (e, down) => {
      if (mode !== "flight" || e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      const k = e.key.toLowerCase();
      if (["arrowleft", "a"].includes(k)) { rotating = down ? -1 : 0; if (down) setSas("free"); e.preventDefault(); }
      if (["arrowright", "d"].includes(k)) { rotating = down ? 1 : 0; if (down) setSas("free"); e.preventDefault(); }
      if (!down) return;
      if (k === "z") setThrottle(1); if (k === "x") setThrottle(0);
      if (k === "shift") setThrottle(Math.min(1, throttle + 0.1)); if (k === "control") setThrottle(Math.max(0, throttle - 0.1));
      if (k === " ") { stageReq = true; e.preventDefault(); } if (k === "m") { mapView = !mapView; show3d(false); } if (k === "f") fairingReq = true;
      if (k === "v" && body === "earth") show3d(!view3dOn);
      if (k === "." || k === ">") setWarp(warpIdx + 1); if (k === "," || k === "<") setWarp(warpIdx - 1);
    };
    const kd = (e) => onKey(e, true), ku = (e) => onKey(e, false);
    window.addEventListener("keydown", kd); window.addEventListener("keyup", ku);
    let panY = 0, drag = null; // drag the flight view along the rocket to inspect it; double-click recentres
    fCanvas.addEventListener("pointerdown", (e) => { if (!mapView) drag = [e.clientY, panY]; });
    fCanvas.addEventListener("pointermove", (e) => { if (drag && flight) { const rocketH = flight.parts.reduce((a, q) => a + q.height, 0); const scale = ((fCanvas.clientHeight * 0.32) / Math.max(10, rocketH)) * zoom; panY = Math.max(-rocketH * 1.2, Math.min(rocketH * 0.2, drag[1] - (e.clientY - drag[0]) / scale)); } });
    ["pointerup", "pointerleave"].forEach((ev) => fCanvas.addEventListener(ev, () => { drag = null; }));
    fCanvas.addEventListener("dblclick", () => { panY = 0; zoom = 1; });
    fCanvas.addEventListener("wheel", (e) => { zoom = Math.max(0.0005, Math.min(60, zoom * (e.deltaY > 0 ? 0.85 : 1.18))); e.preventDefault(); }, { passive: false });

    function lerp(a, b, f) { return a + (b - a) * f; }
    function lerpState() {
      const s = flight.state, L = flight.local;
      if (!prev || !L) return { s, L: L || { x: s.x, y: s.y, vx: s.vx, vy: s.vy, radius: flight.planet?.radius || 6.371e6, atmosphere_top: 0, body } };
      const f = Math.min(1, (performance.now() - stepStart) / 1000 / stepLen);
      const out = { ...s };
      for (const k of ["x", "y", "vx", "vy", "t"]) out[k] = lerp(prev[k], s[k], f);
      const pl = prev.local && prev.local.body === L.body ? prev.local : L;
      return { s: out, L: { ...L, x: lerp(pl.x, L.x, f), y: lerp(pl.y, L.y, f) } };
    }

    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.1, (now - lastT) / 1000 || 0); lastT = now;
      if (mode === "flight" && flight) {
        if (rotating) rel += rotating * dt * 1.2;
        const tel = flight.tel, inAir = tel && flight.local && tel.altitude < flight.local.atmosphere_top; // limit time warp while thrusting or in air
        const maxWarp = (throttle > 0 && !ended) || inAir ? 5 : Infinity;
        if (WARPS[warpIdx] > maxWarp) setWarp(WARPS.findIndex((w) => w >= maxWarp));
        if (!busy && performance.now() - stepStart >= stepLen * 1000 * 0.9) step(Math.min(0.1 * WARPS[warpIdx], 86400 * 30));
        if (view3dOn && f3d) { f3d.render(Math.min(1, (performance.now() - stepStart) / 1000 / stepLen)); drawHud(flight.tel, flight.state); }
        else drawFlight();
      }
    }

    function skyColor(ref, alt) {
      const tab = SKY[ref] || SKY.moon;
      let a = tab[0], b = tab[tab.length - 1];
      for (let i = 0; i < tab.length - 1; i++) if (alt >= tab[i][0] && alt < tab[i + 1][0]) { a = tab[i]; b = tab[i + 1]; }
      const f = b[0] === a[0] ? 1 : Math.min(1, Math.max(0, (alt - a[0]) / (b[0] - a[0])));
      return a[1].map((v, i) => Math.round(v + (b[1][i] - v) * f));
    }

    const starSeed = Array.from({ length: 220 }, (_, i) => [((i * 7919) % 1000) / 1000, ((i * 104729) % 997) / 997, ((i * 31) % 7) / 7]);
    function drawFlight() {
      const c = fCanvas, W = c.clientWidth, H = c.clientHeight;
      if (!W) return;
      const dpr = Math.min(2, devicePixelRatio);
      if (c.width !== W * dpr) { c.width = W * dpr; c.height = H * dpr; }
      const ctx = c.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const { s, L } = lerpState(), tel = flight.tel, R = L.radius, ref = L.body || body;
      const alt = Math.hypot(L.x, L.y) - R;
      if (mapView) return drawMap(ctx, W, H, s, L);
      const sky = skyColor(ref, alt);
      ctx.fillStyle = `rgb(${sky.join(",")})`; ctx.fillRect(0, 0, W, H);
      const starA = Math.max(0, Math.min(1, 1 - (sky[0] + sky[1] + sky[2]) / 200));
      if (starA > 0) { ctx.fillStyle = `rgba(255,255,255,${starA})`; for (const [a, b, z] of starSeed) ctx.fillRect(a * W, b * H, 1 + z, 1 + z); }
      const rocketH = flight.parts.reduce((a, p) => a + p.height, 0);
      const scale = ((H * 0.32) / Math.max(10, rocketH)) * zoom; // px per metre
      const up = Math.atan2(L.y, L.x), cx = W / 2, cy = Math.min(H * 0.8, H / 2 + (rocketH * scale) / 2) - panY * scale; // the state point is the rocket's base
      const toScreen = (wx, wy) => { const dx = wx - L.x, dy = wy - L.y; const a = Math.PI / 2 - up; const rx = dx * Math.cos(a) - dy * Math.sin(a), ry = dx * Math.sin(a) + dy * Math.cos(a); return [cx + rx * scale, cy - ry * scale]; };
      const span = (Math.hypot(W, H) / scale) / R * 1.5;
      if (alt * scale < H * 3) { // ground: polygon of the surface arc under the view
        const pts = [];
        for (let i = 0; i <= 80; i++) { const th = up - span + (2 * span * i) / 80; pts.push(toScreen(R * Math.cos(th), R * Math.sin(th))); }
        const deep = (R - Math.min(R * 0.5, 3 * H / scale));
        for (let i = 80; i >= 0; i--) { const th = up - span + (2 * span * i) / 80; pts.push(toScreen(deep * Math.cos(th), deep * Math.sin(th))); }
        const [g1, g2] = GROUND[ref] || GROUND.moon;
        const grad = ctx.createLinearGradient(0, cy, 0, H); grad.addColorStop(0, g1); grad.addColorStop(1, g2);
        ctx.fillStyle = grad; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.fill();
        if (ref === body && ref !== "moon" || body === "moon" && ref === "moon" && !flight.moon) { // launch pad fixed to the rotating surface
          const padA = Math.PI / 2 + OMEGA[body] * s.t;
          const [px, py] = toScreen(R * Math.cos(padA), R * Math.sin(padA));
          ctx.save(); ctx.translate(px, py); ctx.rotate(-(padA - up));
          ctx.fillStyle = "#4b5563"; ctx.fillRect(-9 * scale, -1.2 * scale, 18 * scale, 1.2 * scale);
          ctx.fillStyle = "#8a93a3"; ctx.fillRect(6 * scale, -rocketH * 1.05 * scale, 1.6 * scale, rocketH * 1.05 * scale);
          ctx.restore();
        }
      }
      // Rocket (upper stages only once lower ones are dropped)
      const parts = flight.stages.slice(s.stage).flat();
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(-(s.angle - up));
      const totalH = parts.reduce((a, p) => a + p.height, 0);
      if (tel && tel.thrust > 0 && !s.crashed) { // flame
        const fl = (0.75 + 0.25 * Math.random()) * (0.5 + throttle * 2) * Math.max(6, flight.stages[s.stage][0].width * 4, rocketH * 0.12) * scale * (tel.air_density < 0.01 ? 1.6 : 1);
        const fw = Math.max(...flight.stages[s.stage].map((p) => (isEngine(p) || p.thrust_vac ? p.width : 0.5))) * scale * 0.55;
        const g = ctx.createLinearGradient(0, 0, 0, fl), vac = tel.air_density < 0.01;
        g.addColorStop(0, "rgba(255,255,230,.95)"); g.addColorStop(0.3, vac ? "rgba(140,170,255,.7)" : "rgba(255,170,60,.85)"); g.addColorStop(1, "rgba(255,90,20,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(-fw / 2, 0); ctx.quadraticCurveTo(-fw * (vac ? 1.3 : 0.7), fl * 0.5, 0, fl); ctx.quadraticCurveTo(fw * (vac ? 1.3 : 0.7), fl * 0.5, fw / 2, 0); ctx.fill();
      }
      if (s.chute) { const top = -totalH * scale; ctx.fillStyle = "#e0662e"; ctx.beginPath(); ctx.ellipse(0, top - 22 * scale, 14 * scale, 8 * scale, 0, Math.PI, 0); ctx.fill(); ctx.strokeStyle = "#ddd"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-14 * scale, top - 22 * scale); ctx.lineTo(0, top); ctx.lineTo(14 * scale, top - 22 * scale); ctx.stroke(); }
      if (s.crashed) { ctx.fillStyle = "rgba(255,120,40,.8)"; ctx.beginPath(); ctx.arc(0, 0, 8 * scale + 20, 0, Math.PI * 2); ctx.fill(); }
      else {
        const layout = drawStack(ctx, parts, 0, 0, scale, { hideFairing: !s.fairing });
        const since = (performance.now() - flight.jettisonAt) / 1000; // fairing halves drifting away after jettison
        if (!s.fairing && flight.jettisonAt && since < 4) {
          const fi = parts.findIndex(isFairing);
          if (fi >= 0) {
            let from = fi; while (from > 0 && parts[from - 1].id !== "decoupler") from--;
            const top = layout[fi][0], bottom = layout[from][1], w = parts[fi].width * scale;
            for (const side of [-1, 1]) {
              const midY = (top + bottom) / 2; // each half tumbles about its own middle as it drifts away
              ctx.save(); ctx.translate(side * since * 6 * scale, since * 3 * scale + midY); ctx.rotate(side * since * 0.25); ctx.translate(0, -midY); ctx.globalAlpha = Math.max(0, 1 - since / 4);
              ctx.fillStyle = "#e9edf2"; ctx.strokeStyle = "rgba(20,30,45,.6)"; ctx.beginPath();
              ctx.moveTo(0, top); ctx.bezierCurveTo(side * w * 0.3, top, side * w / 2, top + (layout[fi][1] - top) * 0.65, side * w / 2, layout[fi][1]); ctx.lineTo(side * w / 2, bottom); ctx.lineTo(0, bottom); ctx.closePath(); ctx.fill(); ctx.stroke();
              ctx.restore();
            }
          }
        }
      }
      ctx.restore();
      drawHud(tel, s);
    }

    function drawMap(ctx, W, H, s, L) {
      ctx.fillStyle = "#050a14"; ctx.fillRect(0, 0, W, H);
      const moon = flight.moon, tel = flight.tel;
      const focus = mapFocus === "auto" ? (L.body === "moon" && moon ? "moon" : "primary") : mapFocus === "moon" && moon ? "moon" : "primary";
      const pts = focus === "moon" ? (flight.trajMoon.length ? flight.trajMoon : [[s.x - moon.x, s.y - moon.y]]) : (flight.traj.length ? flight.traj : [[s.x, s.y]]);
      const craft = focus === "moon" ? [s.x - moon.x, s.y - moon.y] : [s.x, s.y];
      const Rc = focus === "moon" ? moon.radius : flight.planet.radius;
      let ext = Rc * 1.3; for (const [x, y] of [...pts, craft]) ext = Math.max(ext, Math.abs(x) * 1.1, Math.abs(y) * 1.1);
      if (focus !== "moon" && moon && ext > 6e7) ext = Math.max(ext, moon.orbit_radius * 1.1);
      const sc = Math.min(W, H) / 2 / ext * zoom, cx = W / 2, cy = H / 2, S = (x, y) => [cx + x * sc, cy - y * sc];
      const disc = (x, y, r, c1, c2) => { const [a, b] = S(x, y), rr = Math.max(2, r * sc); const g = ctx.createRadialGradient(a - rr * 0.3, b - rr * 0.3, rr * 0.1, a, b, rr); g.addColorStop(0, c1); g.addColorStop(1, c2); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(a, b, rr, 0, Math.PI * 2); ctx.fill(); };
      if (focus === "moon") {
        disc(0, 0, moon.radius, "#cfcfcf", "#555");
        ctx.setLineDash([6, 6]); ctx.strokeStyle = "rgba(200,200,200,.3)"; ctx.beginPath(); ctx.arc(cx, cy, moon.soi * sc, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
        const ex = -moon.x, ey = -moon.y, d = Math.hypot(ex, ey); ctx.fillStyle = "#4f8fe0"; ctx.font = "12px system-ui"; const [ax, ay] = S((ex / d) * ext * 0.85, (ey / d) * ext * 0.85); ctx.fillText("→ Earth", ax, ay);
      } else {
        const top = flight.planet.atmosphere_top, R = flight.planet.radius;
        if (top) { ctx.fillStyle = "rgba(110,170,255,.15)"; ctx.beginPath(); ctx.arc(cx, cy, (R + top) * sc, 0, Math.PI * 2); ctx.fill(); }
        const [c1, c2] = { earth: ["#4f8fe0", "#1d3f7a"], mars: ["#d0643b", "#6e2c16"], moon: ["#bbbbbb", "#555"] }[body];
        disc(0, 0, R, c1, c2);
        if (moon) {
          ctx.strokeStyle = "rgba(200,200,200,.18)"; ctx.beginPath(); ctx.arc(cx, cy, moon.orbit_radius * sc, 0, Math.PI * 2); ctx.stroke();
          disc(moon.x, moon.y, moon.radius, "#cfcfcf", "#555");
          ctx.setLineDash([6, 6]); ctx.strokeStyle = "rgba(200,200,200,.35)"; const [mx, my] = S(moon.x, moon.y); ctx.beginPath(); ctx.arc(mx, my, moon.soi * sc, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
          ctx.fillStyle = "#cfd8e6"; ctx.font = "12px system-ui"; ctx.fillText("Moon", mx + Math.max(6, moon.radius * sc) + 4, my - 6);
        }
      }
      ctx.strokeStyle = "#2a78d6"; ctx.lineWidth = 2; ctx.beginPath(); pts.forEach(([x, y], i) => { const [a, b] = S(x, y); i ? ctx.lineTo(a, b) : ctx.moveTo(a, b); }); ctx.stroke();
      const mark = (p, text, col) => { const [a, b] = S(...p); ctx.fillStyle = col; ctx.beginPath(); ctx.arc(a, b, 5, 0, Math.PI * 2); ctx.fill(); ctx.font = "12px system-ui"; ctx.fillText(text, a + 8, b - 6); };
      const sameFrame = (focus === "moon") === (L.body === "moon");
      if (pts.length > 3 && sameFrame) {
        let lo = 0, hi = 0; pts.forEach(([x, y], i) => { const r = Math.hypot(x, y); if (r > Math.hypot(...pts[hi])) hi = i; if (r < Math.hypot(...pts[lo])) lo = i; });
        if (tel.apoapsis_alt !== null && tel.apoapsis_alt > 0 && tel.apoapsis_alt < 3e8) mark(pts[hi], `Ap ${fmtAlt(tel.apoapsis_alt)}`, "#eb6834");
        if (tel.periapsis_alt !== null && Math.hypot(...pts[lo]) > Rc) mark(pts[lo], `Pe ${fmtAlt(tel.periapsis_alt)}`, "#1baf7a");
      }
      if (tel.encounter && focus !== "moon") { // where the Moon will be when the craft passes it
        const e = tel.encounter, [gx, gy] = S(...e.moon_position);
        ctx.globalAlpha = 0.45; disc(...e.moon_position, moon.radius, "#cfcfcf", "#555");
        ctx.setLineDash([3, 5]); ctx.strokeStyle = "rgba(220,220,220,.5)"; ctx.beginPath(); ctx.arc(gx, gy, moon.soi * sc, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
        mark(e.craft_position, e.impact ? "Moon impact!" : `Closest to Moon: ${fmtAlt(e.periselene_alt)} (Moon then)`, "#d7d7d7");
      } else if (tel.encounter && flight.trajDt) {
        const i = Math.min(pts.length - 1, Math.round(tel.encounter.time_from_now / flight.trajDt));
        if (pts[i]) mark(pts[i], tel.encounter.impact ? "Moon impact!" : `Closest to Moon: ${fmtAlt(tel.encounter.periselene_alt)}`, "#d7d7d7");
      }
      const [rx, ry] = S(...craft);
      ctx.save(); ctx.translate(rx, ry); ctx.rotate(-s.angle + Math.PI / 2);
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(6, 7); ctx.lineTo(-6, 7); ctx.closePath(); ctx.fill(); ctx.restore();
      ctx.fillStyle = "#7b8fa8"; ctx.font = "12px system-ui"; ctx.fillText(`MAP (${focus === "moon" ? "Moon-centred" : "Earth-centred"}) — scroll to zoom, M to return`, 16, H - 16);
      drawHud(tel, s);
    }

    const fmtAlt = (m) => (Math.abs(m) < 0.5 ? "0 m" : Math.abs(m) >= 1e6 ? `${fmt(m / 1e3, 5)} km` : Math.abs(m) >= 1e4 ? `${fmt(m / 1e3, 4)} km` : `${fmt(m, 4)} m`);
    const fmtT = (sec) => { sec = Math.max(0, Math.round(sec)); const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60), x = sec % 60; return `${d ? d + "d " : ""}${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}`; };
    function drawHud(tel, s) {
      if (!tel) return;
      fairingBtn.style.display = s.fairing ? "" : "none";
      const refName = { earth: "Earth", moon: "Moon", mars: "Mars" }[tel.reference] || tel.reference;
      const rows = [
        ["Near", refName], ["Altitude", fmtAlt(tel.altitude)], ["Speed", `${fmt(tel.altitude < 30000 && tel.reference !== "moon" ? tel.surface_speed : tel.speed, 4)} m/s`],
        ["Vertical", `${fmt(Math.abs(tel.vertical_speed) < 0.05 ? 0 : tel.vertical_speed, 3)} m/s`], ["Apoapsis", s.landed ? "—" : tel.apoapsis_alt === null ? "escape" : fmtAlt(tel.apoapsis_alt)],
        ["Periapsis", s.landed ? "—" : tel.periapsis_alt < 0 ? "below surface" : fmtAlt(tel.periapsis_alt)], ["Δv left", `${fmt(tel.delta_v_remaining, 4)} m/s`],
        ["TWR", fmt(tel.twr, 3)], ["G-force", `${fmt(tel.acceleration_g, 3)} g`], ["Mission time", fmtT(s.t)],
      ];
      if (tel.mach) rows.splice(4, 0, ["Mach", fmt(tel.mach, 3)]);
      if (tel.moon_altitude !== undefined && tel.reference !== "moon") rows.push(["Moon distance", fmtAlt(tel.moon_altitude)]);
      if (tel.tli) rows.push(["TLI burn Δv", `${fmt(tel.tli.delta_v, 4)} m/s prograde`], ["TLI window in", fmtT(tel.tli.time_to_window)]);
      if (tel.encounter) rows.push([tel.encounter.impact ? "Moon impact in" : "Moon closest in", fmtT(tel.encounter.time_from_now)], ["… at altitude", fmtAlt(tel.encounter.periselene_alt)]);
      hud.replaceChildren(el("div", { class: `sf-status ${tel.status.replace(/\W+/g, "-")}` }, tel.status.toUpperCase()),
        ...rows.map(([k, v]) => el("div", { class: "sf-hud-row" }, el("span", {}, k), el("b", {}, v))),
        el("div", { class: "sf-fuel" }, el("span", {}, `Stage ${s.stage + 1} fuel`), el("div", { class: "sf-meter" }, el("i", { style: `width:${tel.stage_fuel_fraction * 100}%;background:${tel.stage_fuel_fraction > 0.2 ? "#1baf7a" : "#eb6834"}` }))));
      const now = performance.now();
      toast.replaceChildren(...log.filter((l) => now - l.t < 6000).map((l) => el("div", {}, l.msg)));
    }

    // ---------- boot ----------
    const ro = new ResizeObserver(() => { if (mode === "build") drawBuild(); }); ro.observe(rootEl);
    simulate("physics", "rocket_parts", {}).then((r) => {
      catalogue = r.result;
      for (const id of Object.keys(customs)) if (!customs[id]?.spec) delete customs[id];
      renderPalette(); refresh();
    });
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); f3d?.dispose(); window.removeEventListener("keydown", kd); window.removeEventListener("keyup", ku); };
  },
};
