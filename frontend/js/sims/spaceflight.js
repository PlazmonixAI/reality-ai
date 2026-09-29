// Spaceflight Lab: build a rocket from parts, then fly it. The engine does all the physics:
// physics.rocket_design (Δv, TWR, burn times), rocket_launch_state and rocket_flight (gravity, thrust, drag,
// staging, landing, orbit prediction). The browser draws, takes the pilot's inputs and interpolates between steps.
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";

const TEMPLATES = {
  orbiter: { name: "Orbiter (2 stages)", body: "earth", parts: [{ part: "engine_booster", count: 9 }, { part: "tank_xl" }, { part: "decoupler" }, { part: "engine_vacuum" }, { part: "tank_l" }, { part: "decoupler" }, { part: "parachute" }, { part: "capsule" }, { part: "nose" }] },
  sounding: { name: "Sounding rocket", body: "earth", parts: [{ part: "engine_booster" }, { part: "tank_m" }, { part: "decoupler" }, { part: "parachute" }, { part: "probe" }, { part: "nose" }] },
  heavy: { name: "Heavy lifter", body: "earth", parts: [{ part: "engine_heavy", count: 3 }, { part: "tank_xl" }, { part: "tank_xl" }, { part: "decoupler" }, { part: "engine_vacuum", count: 2 }, { part: "tank_l" }, { part: "satellite" }, { part: "nose" }] },
  lander: { name: "Moon hopper", body: "moon", parts: [{ part: "legs" }, { part: "engine_lander" }, { part: "tank_s" }, { part: "lander" }] },
  mars: { name: "Mars ascent vehicle", body: "mars", parts: [{ part: "legs" }, { part: "engine_booster" }, { part: "tank_m" }, { part: "decoupler" }, { part: "engine_lander", count: 2 }, { part: "tank_s" }, { part: "probe" }, { part: "nose" }] },
};
const CATS = [["command", "Command"], ["tank", "Fuel tanks"], ["engine", "Engines"], ["structural", "Structure"]];
const catOf = (p) => (p.category === "payload" ? "command" : ["aero", "recovery", "structural"].includes(p.category) ? "structural" : p.category);
const WARPS = [1, 2, 5, 10, 25, 100, 1000, 10000, 100000];
const SKY = { earth: [[0, [118, 178, 255]], [12e3, [70, 120, 220]], [35e3, [20, 30, 80]], [70e3, [2, 4, 12]]], mars: [[0, [220, 170, 120]], [15e3, [150, 100, 80]], [45e3, [8, 6, 10]]], moon: [[0, [0, 0, 0]]] };
const GROUND = { earth: ["#3d7a3a", "#2c5e2a"], mars: ["#b5643b", "#8e4a2b"], moon: ["#8f8f94", "#6e6e74"] };

// ---------- part drawing (used by both the builder and the flight view) ----------
function drawPart(ctx, p, cx, yb, s, opts = {}) {
  // cx = centre x, yb = bottom y (screen), s = px per metre. Returns drawn height in px.
  const h = p.height * s, w = p.width * s, x = cx - w / 2, y = yb - h;
  const white = opts.dim ? "#9fb0c4" : "#f4f6f9", shade = "rgba(0,0,0,.18)";
  const cyl = (fill) => { const g = ctx.createLinearGradient(x, 0, x + w, 0); g.addColorStop(0, fill); g.addColorStop(0.45, "#ffffff"); g.addColorStop(1, "#9aa6b5"); return g; };
  ctx.save();
  ctx.lineWidth = Math.max(1, s * 0.05); ctx.strokeStyle = "rgba(20,30,45,.6)";
  switch (p.id) {
    case "tank_s": case "tank_m": case "tank_l": case "tank_xl": {
      ctx.fillStyle = cyl(white); ctx.fillRect(x, y, w, h); ctx.strokeRect(x, y, w, h);
      ctx.fillStyle = "#1c2430";
      for (const f of [0.08, 0.92]) ctx.fillRect(x, y + h * f - s * 0.12, w, s * 0.24);
      if (p.height >= 6) { ctx.fillStyle = shade; ctx.fillRect(x + w * 0.1, y + h * 0.25, w * 0.12, h * 0.5); }
      break;
    }
    case "engine_booster": case "engine_vacuum": case "engine_heavy": case "engine_lander": {
      const n = p.count || 1, bw = Math.min(w, (p.width * 3.4 * s) / Math.max(1, Math.sqrt(n) * 1.6)) * (p.id === "engine_vacuum" ? 1 : 0.9);
      const across = Math.min(n, 5), gap = bw * 0.9, span = (across - 1) * gap;
      ctx.fillStyle = "#30353d"; ctx.fillRect(cx - Math.max(bw, span / 2 + bw / 2) * 0.55, y, Math.max(bw, span / 2 + bw / 2) * 1.1, h * 0.25);
      for (let i = 0; i < across; i++) {
        const ex = cx - span / 2 + i * gap, top = y + h * 0.2, bot = yb;
        const g = ctx.createLinearGradient(ex - bw / 2, 0, ex + bw / 2, 0);
        g.addColorStop(0, "#1b1e23"); g.addColorStop(0.5, p.id === "engine_vacuum" ? "#b8745a" : "#6b7280"); g.addColorStop(1, "#1b1e23");
        ctx.fillStyle = g; ctx.beginPath();
        ctx.moveTo(ex - bw * 0.22, top); ctx.lineTo(ex + bw * 0.22, top); ctx.quadraticCurveTo(ex + bw * 0.3, bot - h * 0.3, ex + bw / 2, bot); ctx.lineTo(ex - bw / 2, bot); ctx.quadraticCurveTo(ex - bw * 0.3, bot - h * 0.3, ex - bw * 0.22, top); ctx.fill(); ctx.stroke();
      }
      if (n > 5) { ctx.fillStyle = "#fff"; ctx.font = `bold ${Math.max(9, s * 0.8)}px system-ui`; ctx.textAlign = "center"; ctx.fillText(`×${n}`, cx, y + h * 0.18); }
      break;
    }
    case "decoupler": ctx.fillStyle = "#2a2f36"; ctx.fillRect(x, y, w, h); ctx.fillStyle = "#f2c230"; for (let i = 0; i < 6; i++) ctx.fillRect(x + (i + 0.25) * (w / 6), y + h * 0.25, w / 12, h * 0.5); break;
    case "nose": { ctx.fillStyle = cyl(white); ctx.beginPath(); ctx.moveTo(x, yb); ctx.quadraticCurveTo(x, y + h * 0.15, cx, y); ctx.quadraticCurveTo(x + w, y + h * 0.15, x + w, yb); ctx.closePath(); ctx.fill(); ctx.stroke(); break; }
    case "capsule": case "lander": {
      ctx.fillStyle = cyl(p.id === "lander" ? "#d8c79a" : "#c8ced8"); ctx.beginPath(); ctx.moveTo(x, yb); ctx.lineTo(x + w * 0.28, y); ctx.lineTo(x + w * 0.72, y); ctx.lineTo(x + w, yb); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#1c3350"; ctx.beginPath(); ctx.arc(cx, y + h * 0.5, Math.max(1.5, w * 0.1), 0, Math.PI * 2); ctx.fill();
      break;
    }
    case "probe": ctx.fillStyle = "#c9ced6"; ctx.beginPath(); ctx.ellipse(cx, yb, w / 2, h, 0, Math.PI, 0); ctx.fill(); ctx.stroke(); ctx.fillStyle = "#2a78d6"; ctx.fillRect(cx - w * 0.08, y + h * 0.3, w * 0.16, h * 0.3); break;
    case "satellite": ctx.fillStyle = "#c9a44a"; ctx.fillRect(x + w * 0.2, y, w * 0.6, h); ctx.strokeRect(x + w * 0.2, y, w * 0.6, h); ctx.fillStyle = "#23408a"; ctx.fillRect(x - w * 0.4, y + h * 0.35, w * 0.6, h * 0.3); ctx.fillRect(x + w * 0.8, y + h * 0.35, w * 0.6, h * 0.3); break;
    case "parachute": ctx.fillStyle = "#e0662e"; ctx.beginPath(); ctx.roundRect(x + w * 0.1, y, w * 0.8, h, h * 0.4); ctx.fill(); ctx.stroke(); break;
    case "legs": ctx.strokeStyle = "#5b6270"; ctx.lineWidth = Math.max(1.5, s * 0.25); ctx.beginPath(); ctx.moveTo(cx - w * 0.25, y); ctx.lineTo(x, yb); ctx.moveTo(cx + w * 0.25, y); ctx.lineTo(x + w, yb); ctx.stroke(); break;
    default: ctx.fillStyle = white; ctx.fillRect(x, y, w, h);
  }
  if (opts.selected) { ctx.strokeStyle = "#ffd33d"; ctx.lineWidth = 2; ctx.setLineDash([5, 4]); ctx.strokeRect(x - 3, y - 3, w + 6, h + 6); ctx.setLineDash([]); }
  ctx.restore();
  return h;
}

function iconCanvas(p) {
  const c = el("canvas", { width: 56, height: 56 }), ctx = c.getContext("2d");
  const s = Math.min(44 / Math.max(p.height, 0.1), 44 / (p.width * 1.6));
  drawPart(ctx, { ...p, count: p.category === "engine" ? 1 : 1 }, 28, 28 + (p.height * s) / 2, s);
  return c;
}

export default {
  mount(root) {
    let catalogue = null, stack = TEMPLATES.orbiter.parts.map((p) => ({ ...p })), body = "earth", selected = -1, design = null;
    let mode = "build";
    const rootEl = el("div", { class: "sf-root" });
    root.append(rootEl);

    // ======================= BUILD MODE =======================
    const bCanvas = el("canvas", { class: "sf-build-canvas" });
    const palette = el("div", { class: "sf-palette" });
    const statsBox = el("div", { class: "sf-stats" });
    const partBox = el("div", { class: "sf-partbox" });
    const tplSel = el("select", { class: "sf-select", "aria-label": "Template", onchange: () => { const t = TEMPLATES[tplSel.value]; if (t) { stack = t.parts.map((p) => ({ ...p })); body = t.body; bodySel.value = body; selected = -1; refresh(); } } },
      el("option", { value: "" }, "Templates…"), ...Object.entries(TEMPLATES).map(([k, t]) => el("option", { value: k }, t.name)));
    const bodySel = el("select", { class: "sf-select", "aria-label": "Launch from", onchange: () => { body = bodySel.value; refresh(); } },
      el("option", { value: "earth" }, "Launch from Earth"), el("option", { value: "moon" }, "Launch from the Moon"), el("option", { value: "mars" }, "Launch from Mars"));
    const launchBtn = el("button", { class: "sf-launch", type: "button", onclick: () => startFlight() }, "LAUNCH ▶");
    const clearBtn = el("button", { class: "sf-small", type: "button", onclick: () => { stack = []; selected = -1; refresh(); } }, "Clear");
    const buildView = el("div", { class: "sf-build" },
      el("div", { class: "sf-build-top" }, el("span", { class: "sf-title" }, "ROCKET BUILDER"), tplSel, bodySel, clearBtn, el("span", { class: "sf-spacer" }), launchBtn),
      palette, el("div", { class: "sf-build-stage" }, bCanvas), el("div", { class: "sf-right" }, partBox, statsBox));
    rootEl.append(buildView);

    function renderPalette() {
      palette.replaceChildren(...CATS.map(([c, label]) => el("div", { class: "sf-cat" }, el("div", { class: "sf-cat-title" }, label),
        ...catalogue.parts.filter((p) => catOf(p) === c).map((p) => el("button", { class: "sf-part", type: "button", title: p.name, onclick: () => { stack.push({ part: p.id }); selected = stack.length - 1; refresh(); } },
          iconCanvas(p), el("span", {}, p.name), el("small", {}, p.thrust_vac ? `${fmt(p.thrust_vac / 1000, 3)} kN · Isp ${p.isp_vac} s` : p.prop ? `${fmt(p.prop / 1000, 3)} t fuel` : `${fmt(p.mass, 3)} kg`))))));
    }
    const partOf = (e) => ({ ...catalogue.parts.find((p) => p.id === e.part), count: e.count || 1 });

    function renderPartBox() {
      if (selected < 0 || !stack[selected]) { partBox.replaceChildren(el("p", { class: "sf-hint" }, "Tap a part on the left to stack it on top. Tap a part on the rocket to edit it. Decouplers split stages; the lowest stage fires first.")); return; }
      const p = partOf(stack[selected]);
      const row = [el("div", { class: "sf-part-name" }, p.name)];
      if (p.category === "engine") row.push(el("div", { class: "sf-row" }, el("span", {}, "Engines"),
        el("button", { class: "sf-small", type: "button", onclick: () => { stack[selected].count = Math.max(1, (stack[selected].count || 1) - 1); refresh(); } }, "−"),
        el("b", {}, String(p.count)), el("button", { class: "sf-small", type: "button", onclick: () => { stack[selected].count = Math.min(9, (stack[selected].count || 1) + 1); refresh(); } }, "+")));
      row.push(el("div", { class: "sf-row" },
        el("button", { class: "sf-small", type: "button", onclick: () => { if (selected < stack.length - 1) { [stack[selected], stack[selected + 1]] = [stack[selected + 1], stack[selected]]; selected++; refresh(); } } }, "Move up"),
        el("button", { class: "sf-small", type: "button", onclick: () => { if (selected > 0) { [stack[selected], stack[selected - 1]] = [stack[selected - 1], stack[selected]]; selected--; refresh(); } } }, "Move down"),
        el("button", { class: "sf-small danger", type: "button", onclick: () => { stack.splice(selected, 1); selected = -1; refresh(); } }, "Remove")));
      const facts = [["Mass", `${fmt(p.mass * p.count, 4)} kg`]];
      if (p.prop) facts.push(["Propellant", `${fmt(p.prop, 4)} kg`]);
      if (p.thrust_vac) facts.push(["Thrust (sea level / vacuum)", `${fmt((p.thrust_sl * p.count) / 1000, 4)} / ${fmt((p.thrust_vac * p.count) / 1000, 4)} kN`], ["Isp (sea level / vacuum)", `${p.isp_sl} / ${p.isp_vac} s`]);
      partBox.replaceChildren(...row, ...facts.map(([k, v]) => el("div", { class: "sf-fact" }, el("span", {}, k), el("b", {}, v))));
    }

    let designSeq = 0;
    async function refresh() {
      renderPartBox(); drawBuild();
      if (!stack.length) { design = null; statsBox.replaceChildren(el("p", { class: "sf-hint" }, "Empty launch pad.")); launchBtn.disabled = true; return; }
      const seq = ++designSeq;
      try {
        const r = await simulate("physics", "rocket_design", { parts: stack, body });
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
        el("div", { class: "sf-fact" }, el("span", {}, "Mass"), el("b", {}, `${fmt(d.total_mass / 1000, 4)} t`)),
        el("div", { class: "sf-fact" }, el("span", {}, "Height"), el("b", {}, `${fmt(d.height, 3)} m`)),
        ...d.stages.map((s) => el("div", { class: "sf-stage" }, el("div", { class: "sf-stage-h" }, `Stage ${s.stage + 1}`),
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
      const s = Math.min((H - 80) / total, (W * 0.5) / maxW, 22);
      let yb = H - 40;
      ctx.fillStyle = "rgba(255,255,255,.15)"; ctx.fillRect(W / 2 - 80, yb, 160, 6);
      bLayout = [];
      parts.forEach((p, i) => { const hpx = drawPart(ctx, p, W / 2, yb, s, { selected: i === selected }); bLayout.push([yb - hpx, yb]); yb -= hpx; });
      // stage brackets
      let st = 1, from = H - 40;
      parts.forEach((p, i) => { if (p.id === "decoupler" || i === parts.length - 1) { const to = bLayout[i][0]; ctx.strokeStyle = "rgba(255,255,255,.45)"; ctx.beginPath(); ctx.moveTo(W / 2 + maxW * s / 2 + 26, from); ctx.lineTo(W / 2 + maxW * s / 2 + 32, from); ctx.lineTo(W / 2 + maxW * s / 2 + 32, to); ctx.lineTo(W / 2 + maxW * s / 2 + 26, to); ctx.stroke(); ctx.fillStyle = "#cfe0f5"; ctx.font = "12px system-ui"; ctx.fillText(`Stage ${st}`, W / 2 + maxW * s / 2 + 38, (from + to) / 2 + 4); st++; from = to; } });
      if (!parts.length) { ctx.fillStyle = "#cfe0f5"; ctx.font = "15px system-ui"; ctx.textAlign = "center"; ctx.fillText("Add an engine, a fuel tank and a capsule", W / 2, H / 2); ctx.textAlign = "left"; }
    }
    bCanvas.addEventListener("click", (e) => {
      const r = bCanvas.getBoundingClientRect(), y = e.clientY - r.top;
      selected = bLayout.findIndex(([t, b]) => y >= t && y <= b); refresh();
    });

    // ======================= FLIGHT MODE =======================
    const fCanvas = el("canvas", { class: "sf-flight-canvas" });
    const hud = el("div", { class: "sf-hud" });
    const toast = el("div", { class: "sf-toast" });
    const thr = el("input", { class: "sf-throttle", type: "range", min: 0, max: 100, value: 0, "aria-label": "Throttle", oninput: () => { throttle = thr.value / 100; thrLabel.textContent = `${thr.value}%`; } });
    const thrLabel = el("div", { class: "sf-thr-label" }, "0%");
    const warpLabel = el("span", { class: "sf-warp-label" }, "1×");
    const sasBtns = ["free", "prograde", "retrograde", "up"].map((m) => el("button", { class: "sf-sas", type: "button", onclick: () => setSas(m) }, { free: "Free", prograde: "Prograde", retrograde: "Retro", up: "Up" }[m]));
    const hold = (dirn) => { const b = el("button", { class: "sf-rot", type: "button", "aria-label": dirn < 0 ? "Rotate left" : "Rotate right" }, dirn < 0 ? "⟲" : "⟳");
      b.addEventListener("pointerdown", () => { rotating = dirn; setSas("free"); }); ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => b.addEventListener(ev, () => { rotating = 0; })); return b; };
    const flightView = el("div", { class: "sf-flight hidden" }, fCanvas, hud, toast,
      el("div", { class: "sf-topright" },
        el("button", { class: "sf-btn", type: "button", onclick: () => setWarp(warpIdx - 1) }, "«"), warpLabel, el("button", { class: "sf-btn", type: "button", onclick: () => setWarp(warpIdx + 1) }, "»"),
        el("button", { class: "sf-btn wide", type: "button", onclick: () => { mapView = !mapView; } }, "MAP"),
        el("button", { class: "sf-btn wide", type: "button", onclick: () => toBuild() }, "BUILD")),
      el("div", { class: "sf-throttle-box" }, el("div", { class: "sf-thr-title" }, "THROTTLE"), thr, thrLabel,
        el("button", { class: "sf-small", type: "button", onclick: () => setThrottle(1) }, "Full"), el("button", { class: "sf-small", type: "button", onclick: () => setThrottle(0) }, "Cut")),
      el("div", { class: "sf-bottomleft" }, hold(-1), hold(1), el("div", { class: "sf-sas-row" }, ...sasBtns)),
      el("div", { class: "sf-bottomright" },
        el("button", { class: "sf-stagebtn", type: "button", onclick: () => { stageReq = true; } }, "STAGE"),
        el("button", { class: "sf-chutebtn", type: "button", onclick: () => { chuteReq = true; } }, "CHUTE")));
    rootEl.append(flightView);

    let flight = null, prev = null, throttle = 0, rel = 0, rotating = 0, sas = "free", warpIdx = 0, mapView = false, stageReq = false, chuteReq = false;
    let busy = false, stepStart = 0, stepLen = 0.1, simClock = 0, zoom = 1, raf = 0, lastT = 0, log = [], ended = false;
    const setThrottle = (v) => { throttle = v; thr.value = Math.round(v * 100); thrLabel.textContent = `${thr.value}%`; };
    function setSas(m) { sas = m; sasBtns.forEach((b, i) => b.classList.toggle("on", ["free", "prograde", "retrograde", "up"][i] === m)); }
    function setWarp(i) { warpIdx = Math.max(0, Math.min(WARPS.length - 1, i)); warpLabel.textContent = `${WARPS[warpIdx]}×`; }
    setSas("free");

    async function startFlight() {
      if (!design || design.warnings.some((w) => w.includes("cannot leave"))) { if (!confirm("This rocket probably can't lift off. Launch anyway?")) return; }
      const r = await simulate("physics", "rocket_launch_state", { parts: stack, body });
      flight = { state: r.result, tel: null, traj: [], planet: null, parts: stack.map(partOf), stages: splitStages(stack.map(partOf)) };
      prev = null; rel = 0; setThrottle(0); setWarp(0); mapView = false; log = []; ended = false; zoom = 1; simClock = 0;
      mode = "flight"; buildView.classList.add("hidden"); flightView.classList.remove("hidden");
      say(`Ready on the pad — ${bodySel.selectedOptions[0].textContent.replace("Launch from ", "")}. Throttle up (Z) to lift off.`);
      step(0.05);
    }
    function toBuild() { mode = "build"; flightView.classList.add("hidden"); buildView.classList.remove("hidden"); refresh(); }
    function splitStages(parts) { const out = []; let cur = []; parts.forEach((p) => { cur.push(p); if (p.id === "decoupler") { out.push(cur); cur = []; } }); if (cur.length) out.push(cur); return out; }
    function say(msg) { log.unshift({ msg, t: performance.now() }); log = log.slice(0, 4); }

    function localUp(s) { return Math.atan2(s.y, s.x); }
    function commandAngle() {
      const s = flight.state, up = localUp(s);
      if (sas !== "free" && flight.tel && !s.landed) {
        const om = { earth: -7.2921159e-5, moon: -2.6617e-6, mars: -7.088218e-5 }[s.body];
        const surface = flight.tel.altitude < 30000;
        const vx = surface ? s.vx - -om * s.y : s.vx, vy = surface ? s.vy - om * s.x : s.vy; // surface velocity low down
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
      const wantStage = stageReq, wantChute = chuteReq; stageReq = chuteReq = false;
      try {
        const r = await simulate("physics", "rocket_flight", { state: s, parts: stack, throttle: ended ? 0 : throttle, angle: commandAngle(), dt, stage: wantStage, deploy_chute: wantChute, predict: mapView || warpIdx > 0 || Math.random() < 0.2 });
        prev = { ...flight.state }; flight.state = r.result.state; flight.tel = r.result.telemetry; flight.planet = r.planet;
        if (r.trajectory.length) flight.traj = r.trajectory;
        for (const e of r.result.events) say(e.charAt(0).toUpperCase() + e.slice(1));
        if (flight.state.crashed && !ended) { ended = true; setThrottle(0); setWarp(0); say("Vehicle destroyed. Press BUILD to try again."); }
        if (r.result.telemetry.status === "orbit" && !flight.orbitSaid) { flight.orbitSaid = true; say("Orbit achieved! 🎉"); }
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
      if (k === " ") { stageReq = true; e.preventDefault(); } if (k === "m") mapView = !mapView;
      if (k === "." || k === ">") setWarp(warpIdx + 1); if (k === "," || k === "<") setWarp(warpIdx - 1);
    };
    const kd = (e) => onKey(e, true), ku = (e) => onKey(e, false);
    window.addEventListener("keydown", kd); window.addEventListener("keyup", ku);
    fCanvas.addEventListener("wheel", (e) => { zoom = Math.max(0.0005, Math.min(40, zoom * (e.deltaY > 0 ? 0.85 : 1.18))); e.preventDefault(); }, { passive: false });

    function lerpState() {
      const s = flight.state;
      if (!prev) return s;
      const f = Math.min(1, (performance.now() - stepStart) / 1000 / stepLen);
      const out = { ...s };
      for (const k of ["x", "y", "vx", "vy", "t"]) out[k] = prev[k] + (s[k] - prev[k]) * f;
      return out;
    }

    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.1, (now - lastT) / 1000 || 0); lastT = now;
      if (mode === "flight" && flight) {
        if (rotating) rel += rotating * dt * 1.2;
        // limit time warp while thrusting or inside the atmosphere
        const tel = flight.tel, inAir = tel && flight.planet && tel.altitude < flight.planet.atmosphere_top;
        const maxWarp = (throttle > 0 && !ended) || inAir ? 5 : Infinity;
        if (WARPS[warpIdx] > maxWarp) { setWarp(WARPS.findIndex((w) => w >= maxWarp)); }
        if (!busy && performance.now() - stepStart >= stepLen * 1000 * 0.9) step(Math.min(0.1 * WARPS[warpIdx], 86400 * 30));
        drawFlight();
      } else if (mode === "build") { /* static */ }
    }

    function skyColor(alt) {
      const tab = SKY[body];
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
      const s = lerpState(), tel = flight.tel, R = flight.planet?.radius || 6.371e6;
      const alt = Math.hypot(s.x, s.y) - R;
      if (mapView) return drawMap(ctx, W, H, s, R);
      const sky = skyColor(alt);
      ctx.fillStyle = `rgb(${sky.join(",")})`; ctx.fillRect(0, 0, W, H);
      const starA = Math.max(0, Math.min(1, 1 - (sky[0] + sky[1] + sky[2]) / 200));
      if (starA > 0) { ctx.fillStyle = `rgba(255,255,255,${starA})`; for (const [a, b, z] of starSeed) ctx.fillRect(a * W, b * H, 1 + z, 1 + z); }
      const rocketH = flight.parts.reduce((a, p) => a + p.height, 0);
      const scale = ((H * 0.32) / Math.max(10, rocketH)) * zoom; // px per metre
      const up = Math.atan2(s.y, s.x), cx = W / 2, cy = Math.min(H * 0.8, H / 2 + (rocketH * scale) / 2); // the state point is the rocket's base
      // world → screen: rotate so local up is screen up, centred on the rocket
      const toScreen = (wx, wy) => { const dx = wx - s.x, dy = wy - s.y; const a = Math.PI / 2 - up; const rx = dx * Math.cos(a) - dy * Math.sin(a), ry = dx * Math.sin(a) + dy * Math.cos(a); return [cx + rx * scale, cy - ry * scale]; };
      // Ground: polygon of the surface arc under the view
      const span = (Math.hypot(W, H) / scale) / R * 1.5;
      if (alt * scale < H * 3) {
        const pts = [];
        for (let i = 0; i <= 80; i++) { const th = up - span + (2 * span * i) / 80; pts.push(toScreen(R * Math.cos(th), R * Math.sin(th))); }
        const deep = (R - Math.min(R * 0.5, 3 * H / scale));
        for (let i = 80; i >= 0; i--) { const th = up - span + (2 * span * i) / 80; pts.push(toScreen(deep * Math.cos(th), deep * Math.sin(th))); }
        const [g1, g2] = GROUND[body];
        const grad = ctx.createLinearGradient(0, cy, 0, H);
        grad.addColorStop(0, g1); grad.addColorStop(1, g2);
        ctx.fillStyle = grad; ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); ctx.fill();
        // Launch pad (fixed to the rotating surface)
        const om = { earth: -7.2921159e-5, moon: -2.6617e-6, mars: -7.088218e-5 }[s.body];
        const padA = Math.PI / 2 + om * s.t;
        const [px, py] = toScreen(R * Math.cos(padA), R * Math.sin(padA));
        ctx.save(); ctx.translate(px, py); ctx.rotate(-(padA - up));
        ctx.fillStyle = "#4b5563"; ctx.fillRect(-9 * scale, -1.2 * scale, 18 * scale, 1.2 * scale);
        ctx.fillStyle = "#8a93a3"; ctx.fillRect(6 * scale, -rocketH * 1.05 * scale, 1.6 * scale, rocketH * 1.05 * scale);
        ctx.restore();
      }
      // Rocket (upper stages only once lower ones are dropped)
      const parts = flight.stages.slice(s.stage).flat();
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(-(s.angle - up));
      const totalH = parts.reduce((a, p) => a + p.height, 0);
      let yb = 0;
      // flame
      if (tel && tel.thrust > 0 && !s.crashed) {
        const fl = (0.75 + 0.25 * Math.random()) * (0.5 + throttle * 2.5) * Math.max(6, flight.parts[0].width * 4) * scale * (tel.air_density < 0.01 ? 1.6 : 1);
        const fw = Math.max(...flight.stages[s.stage].map((p) => p.width)) * scale * 0.55;
        const g = ctx.createLinearGradient(0, yb, 0, yb + fl);
        const vac = tel.air_density < 0.01;
        g.addColorStop(0, "rgba(255,255,230,.95)"); g.addColorStop(0.3, vac ? "rgba(140,170,255,.7)" : "rgba(255,170,60,.85)"); g.addColorStop(1, "rgba(255,90,20,0)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(-fw / 2, yb); ctx.quadraticCurveTo(-fw * (vac ? 1.3 : 0.7), yb + fl * 0.5, 0, yb + fl); ctx.quadraticCurveTo(fw * (vac ? 1.3 : 0.7), yb + fl * 0.5, fw / 2, yb); ctx.fill();
      }
      if (s.chute) { const top = -totalH * scale; ctx.fillStyle = "#e0662e"; ctx.beginPath(); ctx.ellipse(0, top - 22 * scale, 14 * scale, 8 * scale, 0, Math.PI, 0); ctx.fill(); ctx.strokeStyle = "#ddd"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(-14 * scale, top - 22 * scale); ctx.lineTo(0, top); ctx.lineTo(14 * scale, top - 22 * scale); ctx.stroke(); }
      if (s.crashed) { ctx.fillStyle = "rgba(255,120,40,.8)"; ctx.beginPath(); ctx.arc(0, yb, 8 * scale + 20, 0, Math.PI * 2); ctx.fill(); }
      else for (const p of parts) yb -= drawPart(ctx, p, 0, yb, scale);
      ctx.restore();
      drawHud(tel, s);
    }

    function drawMap(ctx, W, H, s, R) {
      ctx.fillStyle = "#050a14"; ctx.fillRect(0, 0, W, H);
      const pts = flight.traj.length ? flight.traj : [[s.x, s.y]];
      let ext = R * 1.3; for (const [x, y] of pts) ext = Math.max(ext, Math.abs(x) * 1.1, Math.abs(y) * 1.1);
      const sc = Math.min(W, H) / 2 / ext * zoom, cx = W / 2, cy = H / 2, S = (x, y) => [cx + x * sc, cy - y * sc];
      const top = flight.planet.atmosphere_top;
      if (top) { ctx.fillStyle = "rgba(110,170,255,.15)"; ctx.beginPath(); ctx.arc(cx, cy, (R + top) * sc, 0, Math.PI * 2); ctx.fill(); }
      const g = ctx.createRadialGradient(cx - R * sc * 0.3, cy - R * sc * 0.3, R * sc * 0.1, cx, cy, R * sc);
      const [c1, c2] = { earth: ["#4f8fe0", "#1d3f7a"], mars: ["#d0643b", "#6e2c16"], moon: ["#bbbbbb", "#555"] }[body];
      g.addColorStop(0, c1); g.addColorStop(1, c2); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * sc, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "#2a78d6"; ctx.lineWidth = 2; ctx.beginPath(); pts.forEach(([x, y], i) => { const [a, b] = S(x, y); i ? ctx.lineTo(a, b) : ctx.moveTo(a, b); }); ctx.stroke();
      if (flight.traj.length > 3) {
        let lo = 0, hi = 0; pts.forEach(([x, y], i) => { const r = Math.hypot(x, y); if (r > Math.hypot(...pts[hi])) hi = i; if (r < Math.hypot(...pts[lo])) lo = i; });
        const tel = flight.tel;
        const mark = (i, text, col) => { const [a, b] = S(...pts[i]); ctx.fillStyle = col; ctx.beginPath(); ctx.arc(a, b, 5, 0, Math.PI * 2); ctx.fill(); ctx.font = "12px system-ui"; ctx.fillText(text, a + 8, b - 6); };
        if (tel.apoapsis_alt !== null && tel.apoapsis_alt > 0) mark(hi, `Ap ${fmtAlt(tel.apoapsis_alt)}`, "#eb6834");
        if (tel.periapsis_alt !== null && Math.hypot(...pts[lo]) > R) mark(lo, `Pe ${fmtAlt(tel.periapsis_alt)}`, "#1baf7a");
      }
      const [rx, ry] = S(s.x, s.y);
      ctx.save(); ctx.translate(rx, ry); ctx.rotate(-s.angle + Math.PI / 2);
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(6, 7); ctx.lineTo(-6, 7); ctx.closePath(); ctx.fill(); ctx.restore();
      ctx.fillStyle = "#7b8fa8"; ctx.font = "12px system-ui"; ctx.fillText("MAP — scroll to zoom, M to return", 16, H - 16);
      drawHud(flight.tel, s);
    }

    const fmtAlt = (m) => (Math.abs(m) >= 1e6 ? `${fmt(m / 1e3, 5)} km` : Math.abs(m) >= 1e4 ? `${fmt(m / 1e3, 4)} km` : `${fmt(m, 4)} m`);
    const fmtT = (sec) => { sec = Math.round(sec); const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60), x = sec % 60; return `${d ? d + "d " : ""}${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}`; };
    function drawHud(tel, s) {
      if (!tel) return;
      const rows = [
        ["Altitude", fmtAlt(tel.altitude)], ["Speed", `${fmt(tel.altitude < 30000 ? tel.surface_speed : tel.speed, 4)} m/s`],
        ["Vertical", `${fmt(tel.vertical_speed, 3)} m/s`], ["Apoapsis", s.landed ? "—" : tel.apoapsis_alt === null ? "escape" : fmtAlt(tel.apoapsis_alt)],
        ["Periapsis", s.landed ? "—" : tel.periapsis_alt < 0 ? "below surface" : fmtAlt(tel.periapsis_alt)], ["Δv left", `${fmt(tel.delta_v_remaining, 4)} m/s`],
        ["TWR", fmt(tel.twr, 3)], ["G-force", `${fmt(tel.acceleration_g, 3)} g`], ["Mission time", fmtT(s.t)],
      ];
      if (tel.mach) rows.splice(3, 0, ["Mach", fmt(tel.mach, 3)]);
      hud.replaceChildren(el("div", { class: `sf-status ${tel.status.replace(/\W+/g, "-")}` }, tel.status.toUpperCase()),
        ...rows.map(([k, v]) => el("div", { class: "sf-hud-row" }, el("span", {}, k), el("b", {}, v))),
        el("div", { class: "sf-fuel" }, el("span", {}, `Stage ${s.stage + 1} fuel`), el("div", { class: "sf-meter" }, el("i", { style: `width:${tel.stage_fuel_fraction * 100}%;background:${tel.stage_fuel_fraction > 0.2 ? "#1baf7a" : "#eb6834"}` }))));
      const now = performance.now();
      toast.replaceChildren(...log.filter((l) => now - l.t < 6000).map((l) => el("div", {}, l.msg)));
    }

    // ---------- boot ----------
    const ro = new ResizeObserver(() => { if (mode === "build") drawBuild(); }); ro.observe(rootEl);
    simulate("physics", "rocket_parts", {}).then((r) => { catalogue = r.result; renderPalette(); refresh(); });
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); window.removeEventListener("keydown", kd); window.removeEventListener("keyup", ku); };
  },
};
