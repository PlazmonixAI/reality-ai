// Virtual Chemistry Lab: a sandbox bench. Take glassware and chemicals from the shelf, add, pour, heat on a burner,
// run a burette into a flask, and watch what happens. Every amount, temperature, pH, colour, precipitate, gas and
// equation comes from the engine (chemistry.lab_step); the browser draws the bench and animates bubbles and flames.
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";

const INK = "#0B1526", EMBER = "#FF5B2E";
const SLOTS = 7;
const HEATS = [["Off", 0], ["Low", 0.35], ["Medium", 0.7], ["High", 1]];
const SPEEDS = [1, 5, 20];
const DEFAULT_AMOUNT = { solid: 1, liquid: 20, solution: 10, pure: 2 };
const QUICK = { solid: [["A pinch", 0.05], ["0.5 g", 0.5], ["1 g", 1], ["5 g", 5]], liquid: [["1 drop", 0.05], ["10 drops", 0.5], ["Pipette 10 mL", 10], ["Pipette 25 mL", 25]] };
const TEST_LABEL = { litmus_red: "Red litmus", litmus_blue: "Blue litmus", ph_paper: "pH paper", lighted_splint: "Lighted splint", glowing_splint: "Glowing splint", flame: "Flame test" };
const SMALL = { sodium: 0.1, potassium: 0.05, calcium: 0.2, magnesium: 0.1 };
const SHAPE = { beaker: [74, 96], conical: [80, 104], test_tube: [22, 110], boiling_tube: [30, 120], crucible: [56, 36], dish: [96, 30], burette: [16, 230], cylinder: [34, 150], gas_jar: [62, 118], watch_glass: [84, 12] };

export default {
  title: "Virtual Chemistry Lab",
  mount(root) {
    let cat = null, vessels = [], seq = 0, selected = null, hand = null, busy = false, pending = [], resync = false, speed = 0, t = 0, logs = [], raf = 0, timer = 0;
    const shelf = el("div", { class: "lab-shelf" });
    const canvas = el("canvas", { class: "lab-canvas", "aria-label": "Lab bench" });
    const insp = el("div", { class: "lab-inspector" });
    const logBox = el("div", { class: "lab-log" });
    const handNote = el("div", { class: "lab-hand", hidden: true });
    const speedBtn = el("button", { class: "btn small", type: "button", title: "Time speed (useful while heating)", onclick: () => { speed = (speed + 1) % SPEEDS.length; speedBtn.textContent = `Time ×${SPEEDS[speed]}`; } }, "Time ×1");
    const head = el("div", { class: "lab-head" }, el("div", {}, el("h1", {}, "Virtual Chemistry Lab"),
      el("p", { class: "muted small" }, "Pick glassware and chemicals from the shelf. Add, pour, heat, titrate. The engine works out what happens.")),
    el("div", { class: "lab-head-tools" }, speedBtn, el("button", { class: "btn small", type: "button", onclick: () => resetBench() }, "Clear bench")));
    root.append(el("div", { class: "lab" }, head, el("div", { class: "lab-body" }, shelf, el("div", { class: "lab-stage" }, canvas, handNote), el("div", { class: "lab-side" }, insp, logBox))));

    // ---------------------------------------------------------------- shelf
    let tab = "chem";
    function renderShelf() {
      const tabs = el("div", { class: "lab-tabs" },
        el("button", { type: "button", class: tab === "chem" ? "on" : "", onclick: () => { tab = "chem"; renderShelf(); } }, "Chemicals"),
        el("button", { type: "button", class: tab === "eq" ? "on" : "", onclick: () => { tab = "eq"; renderShelf(); } }, "Equipment"));
      const body = el("div", { class: "lab-shelf-body" });
      if (tab === "eq") {
        body.append(...cat.equipment.map((e) => el("button", { class: "lab-item", type: "button", draggable: "true",
          ondragstart: (ev) => ev.dataTransfer.setData("text/plain", `eq:${e.id}`), onclick: () => place(e.id) },
          el("b", {}, e.name), el("small", {}, e.flame ? "Can go on the burner" : "Not for heating"))),
        el("div", { class: "lab-group" }, "Tools on the bench"),
          ...Object.values(cat.tools).map((t) => el("p", { class: "lab-tool" }, t)),
          el("p", { class: "muted small" }, "Select a vessel to use the tools: burner, delivery tube, filter funnel, litmus, pH paper, splints and the flame-test wire."));
      } else {
        const groups = [...new Set(cat.chemicals.map((c) => c.group))];
        for (const g of groups) {
          body.append(el("div", { class: "lab-group" }, g));
          body.append(...cat.chemicals.filter((c) => c.group === g).map((c) => el("button", { class: `lab-item${hand?.id === c.id ? " on" : ""}`, type: "button", draggable: "true", title: c.note || c.name,
            ondragstart: (ev) => ev.dataTransfer.setData("text/plain", `ch:${c.id}`), onclick: () => pick(c) },
            el("b", {}, c.name), el("small", {}, c.kind === "solution" ? `${c.conc} mol/L` : c.kind === "indicator" ? "a few drops" : c.kind === "pure" ? "concentrated" : c.kind))));
        }
      }
      shelf.replaceChildren(tabs, body);
    }
    function pick(c) {
      hand = hand?.id === c.id ? null : c;
      handNote.hidden = !hand;
      handNote.textContent = hand ? `Holding ${hand.name.toLowerCase()}: tap a vessel to add it` : "";
      renderShelf();
    }

    // ---------------------------------------------------------------- bench state
    const vesselAt = (slot) => vessels.find((v) => v.slot === slot);
    function place(kind, slot = null) {
      const free = slot ?? [...Array(SLOTS).keys()].find((s) => !vesselAt(s));
      if (free === undefined) { note("The bench is full. Remove something first."); return; }
      if (vesselAt(free)) { note("That spot is taken."); return; }
      const v = { id: `v${++seq}`, kind, slot: free, contents: {}, T: 25, indicators: [], heat: 0, view: null, over: null, tap: 0 };
      vessels.push(v); selected = v.id; renderInspector(); draw();
      step([], 0);
    }
    function resetBench() { vessels = []; selected = null; logs = []; renderInspector(); renderLog(); draw(); }
    function note(text) { logs.unshift({ text, kind: "note" }); logs = logs.slice(0, 60); renderLog(); }

    // ---------------------------------------------------------------- engine
    async function step(actions, dt) {
      if (busy) { pending.push(...actions); resync = true; return; }
      busy = true;
      const send = vessels.map((v) => ({ id: v.id, kind: v.kind, contents: v.contents, T: v.T, indicators: v.indicators, heat: v.heat, ...(v.gasTo ? { gas_to: v.gasTo } : {}) }));
      // burettes run into the vessel under them
      const pours = [];
      if (dt > 0) for (const b of vessels) if (b.kind === "burette" && b.over && b.tap > 0 && (b.view?.volume_ml || 0) > 0.001) pours.push({ type: "pour", from: b.id, to: b.over, volume_ml: Math.min(b.view.volume_ml, b.tap * Math.min(dt, 0.5)) });
      try {
        const r = await simulate("chemistry", "lab_step", { vessels: send, actions: [...pours, ...actions], dt, t });
        const res = r.result; t = res.t;
        for (const out of res.vessels) {
          const v = vessels.find((x) => x.id === out.id);
          if (!v) continue;
          Object.assign(v, { contents: out.contents, T: out.T, indicators: out.indicators, view: out });
          if (v.kind === "burette" && v.over) v.delivered = (v.delivered || 0) + (pours.find((p) => p.from === v.id)?.volume_ml || 0);
        }
        for (const line of res.log.slice(pours.length)) logs.unshift({ text: line, kind: "action" });
        for (const e of res.events) {
          const key = `${e.vessel}|${e.reaction}`;
          if (!seen.has(key)) { seen.add(key); logs.unshift({ text: e.observation, eq: e.equation, dh: e.delta_h_kj_per_mol, vessel: e.vessel, kind: "reaction" }); }
        }
        for (const v of res.vessels) for (const g of v.gases) {
          const key = `${v.id}|gas|${g.gas}`;
          if (g.gas !== "H2O" && !seen.has(key)) { seen.add(key); logs.unshift({ text: g.piped_to ? `${g.test} (going through the delivery tube into ${nameOf(g.piped_to)})` : g.test, kind: "gas", vessel: v.id }); }
        }
        for (const r of res.tests || []) logs.unshift({ text: `${TEST_LABEL[r.test]}: ${r.result}`, kind: "test", vessel: r.vessel, swatch: r.colour });
        logs = logs.slice(0, 60);
        renderLog(); renderInspector(true);
      } catch (e) { note(e.message); } finally { busy = false; }
      if (pending.length || resync) { resync = false; const a = pending.splice(0); step(a, 0); }
    }
    const seen = new Set();
    const active = () => vessels.some((v) => v.heat > 0 || (v.view?.reacting?.length) || (v.view?.gases?.length) || Math.abs(v.T - 25) > 0.3 || (v.kind === "burette" && v.over && v.tap > 0));
    timer = setInterval(() => { if (!busy && active()) step([], 0.5 * SPEEDS[speed]); }, 500);

    // ---------------------------------------------------------------- inspector
    const nameOf = (id) => { const v = vessels.find((x) => x.id === id); return v ? `${cat.equipment.find((e) => e.id === v.kind).name} (${v.slot + 1})` : ""; };
    function amountPrompt(chem, v) {
      if (chem.kind === "indicator") { step([{ type: "add", vessel: v.id, chemical: chem.id, amount: 1 }], 0.5); return; }
      const unit = chem.kind === "solid" ? "g" : "mL", start = SMALL[chem.id] ?? DEFAULT_AMOUNT[chem.kind];
      const input = el("input", { type: "number", min: "0", step: "any", value: start, class: "lab-num", "aria-label": `Amount in ${unit}` });
      const go = () => { const a = Number(input.value); if (a > 0) step([{ type: "add", vessel: v.id, chemical: chem.id, amount: a }], 0.5); closeDialog(); };
      const chips = el("div", { class: "lab-seg" }, el("span", {}, chem.kind === "solid" ? "Spatula" : "Dropper or pipette"),
        ...QUICK[chem.kind === "solid" ? "solid" : "liquid"].map(([l, a]) => el("button", { type: "button", onclick: () => { input.value = a; } }, l)));
      openDialog(`Add ${chem.name.toLowerCase()}`, chips, el("div", { class: "lab-dialog-row" }, input, el("span", {}, unit)),
        chem.note ? el("p", { class: "muted small" }, chem.note) : "", el("button", { class: "btn primary small", type: "button", onclick: go }, "Add"));
      input.focus(); input.select(); input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    }
    function pourPrompt(from, to) {
      const vol = from.view?.volume_ml || 0;
      if (vol <= 0) { note("That vessel is empty."); return; }
      const input = el("input", { type: "number", min: "0", step: "any", value: Math.min(vol, from.kind === "burette" ? 10 : vol).toFixed(1), class: "lab-num" });
      const go = () => { const a = Number(input.value); if (a > 0) step([{ type: "pour", from: from.id, to: to.id, volume_ml: a }], 0.5); closeDialog(); };
      const chips = el("div", { class: "lab-seg" }, el("span", {}, "Dropper or pipette"),
        ...QUICK.liquid.filter(([, a]) => a <= vol + 1e-9).map(([l, a]) => el("button", { type: "button", onclick: () => { input.value = a; } }, l)),
        el("button", { type: "button", onclick: () => { input.value = vol.toFixed(2); } }, "All"));
      openDialog(`Pour from ${nameOf(from.id)} into ${nameOf(to.id)}`, chips, el("div", { class: "lab-dialog-row" }, input, el("span", {}, `mL of ${fmt(vol, 3)} mL`)),
        el("button", { class: "btn primary small", type: "button", onclick: go }, "Pour"));
      input.focus(); input.select(); input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    }
    const dialog = el("div", { class: "lab-dialog", hidden: true });
    root.querySelector(".lab-stage").append(dialog);
    function openDialog(title, ...body) { dialog.replaceChildren(el("div", { class: "lab-dialog-head" }, el("b", {}, title), el("button", { type: "button", class: "lab-x", "aria-label": "Close", onclick: closeDialog }, "×")), ...body); dialog.hidden = false; }
    function closeDialog() { dialog.hidden = true; dialog.replaceChildren(); }

    let lastInspector = "";
    function renderInspector(soft = false) {
      const v = vessels.find((x) => x.id === selected);
      if (!v) { insp.replaceChildren(el("h3", {}, "Bench"), el("p", { class: "muted small" }, "Tap glassware on the Equipment shelf to put it on the bench, then pick a chemical and tap the glassware to add it. Drag one vessel onto another to pour. Select a vessel to heat it, pour it or read its contents.")); lastInspector = ""; return; }
      const o = v.view || {};
      const key = JSON.stringify([v.id, v.heat, v.over, v.tap, v.gasTo, vessels.length]);
      const facts = el("div", { class: "lab-facts" },
        el("div", {}, el("span", {}, "Temperature"), el("b", {}, `${fmt(o.T ?? v.T, 4)} °C`)),
        el("div", {}, el("span", {}, "Volume"), el("b", {}, `${fmt(o.volume_ml || 0, 3)} mL`)),
        el("div", {}, el("span", {}, "pH"), el("b", {}, o.ph == null ? "–" : fmt(Math.max(0, Math.min(14, o.ph)), 3))),
        el("div", {}, el("span", {}, "Mass of contents"), el("b", {}, `${fmt(o.mass_g || 0, 3)} g`)));
      const rows = Object.entries(v.contents).filter(([, n]) => n > 1e-7).map(([k, n]) => el("li", {}, el("span", {}, k), el("b", {}, n >= 0.01 ? `${fmt(n, 3)} mol` : `${fmt(n * 1000, 3)} mmol`)));
      const contents = el("ul", { class: "lab-contents" }, ...(rows.length ? rows : [el("li", { class: "muted" }, "Empty")]), ...(v.indicators.length ? [el("li", {}, el("span", {}, "Indicator"), el("b", {}, v.indicators.join(", ")))] : []));
      if (soft && key === lastInspector) {
        insp.querySelector(".lab-facts")?.replaceWith(facts); insp.querySelector(".lab-contents")?.replaceWith(contents);
        const rd = insp.querySelector(".lab-reading"); if (rd) rd.textContent = `Burette reading ${fmt(v.delivered || 0, 3)} mL`;
        return;
      }
      lastInspector = key;
      const others = vessels.filter((x) => x.id !== v.id);
      const heatRow = !cat.equipment.find((e) => e.id === v.kind).flame ? el("p", { class: "muted small" }, "Not for heating.") :
        el("div", { class: "lab-seg" }, el("span", {}, "Burner"), ...HEATS.map(([label, h]) => el("button", { type: "button", class: v.heat === h ? "on" : "", onclick: () => { v.heat = h; renderInspector(); draw(); } }, label)));
      const pourSel = el("select", { class: "lab-sel", "aria-label": "Pour into" }, el("option", { value: "" }, "Pour into…"), ...others.map((x) => el("option", { value: x.id }, nameOf(x.id))));
      pourSel.addEventListener("change", () => { const to = vessels.find((x) => x.id === pourSel.value); if (to) pourPrompt(v, to); pourSel.value = ""; });
      const filterSel = el("select", { class: "lab-sel", "aria-label": "Filter into" }, el("option", { value: "" }, "Filter into…"), ...others.map((x) => el("option", { value: x.id }, nameOf(x.id))));
      filterSel.addEventListener("change", () => { if (filterSel.value) step([{ type: "filter", from: v.id, to: filterSel.value }], 0.5); filterSel.value = ""; });
      const tubeSel = el("select", { class: "lab-sel", "aria-label": "Delivery tube" }, el("option", { value: "" }, "No delivery tube"),
        ...others.filter((x) => x.kind !== "burette").map((x) => el("option", { value: x.id, selected: v.gasTo === x.id }, `Gas into ${nameOf(x.id)}`)));
      tubeSel.addEventListener("change", () => { v.gasTo = tubeSel.value || null; renderInspector(); draw(); });
      const tests = el("div", { class: "lab-seg" }, el("span", {}, "Test"), ...cat.tests.map((k) => el("button", { type: "button", onclick: () => step([{ type: "test", vessel: v.id, test: k }], 0) }, TEST_LABEL[k])));
      const extra = [];
      if (v.kind === "burette") {
        const overSel = el("select", { class: "lab-sel", "aria-label": "Burette over" }, el("option", { value: "" }, "Not over a vessel"), ...others.map((x) => el("option", { value: x.id, selected: v.over === x.id }, nameOf(x.id))));
        overSel.addEventListener("change", () => { v.over = overSel.value || null; v.tap = 0; renderInspector(); draw(); });
        extra.push(el("div", { class: "lab-burette" }, el("b", { class: "lab-reading" }, `Burette reading ${fmt(v.delivered || 0, 3)} mL`), overSel,
          el("div", { class: "lab-seg" }, el("span", {}, "Tap"), ...[["Shut", 0], ["Drops", 0.1], ["Slow", 0.5], ["Open", 2]].map(([l, r]) => el("button", { type: "button", class: v.tap === r ? "on" : "", disabled: !v.over, onclick: () => { v.tap = r; renderInspector(); } }, l))),
          el("button", { class: "btn small", type: "button", onclick: () => { v.delivered = 0; renderInspector(); } }, "Note the initial reading (zero)")));
      }
      insp.replaceChildren(el("h3", {}, nameOf(v.id)), facts, ...extra, heatRow, tests,
        v.kind === "burette" ? "" : el("div", { class: "lab-actions" }, el("span", { class: "muted small" }, "Delivery tube"), tubeSel),
        el("div", { class: "lab-actions" }, pourSel, filterSel,
        el("button", { class: "btn small", type: "button", onclick: () => step([{ type: "empty", vessel: v.id }], 0) }, "Empty"),
        el("button", { class: "btn small danger", type: "button", onclick: () => { vessels = vessels.filter((x) => x !== v); vessels.forEach((x) => { if (x.over === v.id) x.over = null; if (x.gasTo === v.id) x.gasTo = null; }); selected = null; renderInspector(); draw(); } }, "Remove")),
        el("h4", {}, "Contents"), contents);
    }
    function renderLog() {
      logBox.replaceChildren(el("h4", {}, "Lab notebook"), ...(logs.length ? logs.map((l) => el("div", { class: `lab-entry ${l.kind}` },
        l.vessel ? el("small", {}, nameOf(l.vessel)) : "", el("span", {}, l.swatch ? el("i", { class: "lab-swatch", style: `background:${l.swatch}` }) : "", l.text),
        l.eq ? el("code", {}, l.eq) : "", l.kind !== "reaction" ? "" : l.dh != null ? el("small", { class: "muted" }, `ΔH = ${fmt(l.dh, 4)} kJ per mole of reaction${l.dh < 0 ? " (gives out heat)" : " (takes in heat)"}`) : el("small", { class: "muted" }, "ΔH not tabulated for this product"))) : [el("p", { class: "muted small" }, "Observations, equations and gas tests appear here.")]));
    }

    // ---------------------------------------------------------------- drawing
    let geo = { W: 0, H: 0, y: 0, slotW: 0 };
    const slotX = (s) => geo.slotW * (s + 0.5);
    function shapePath(ctx, kind, x, base, w, h) {
      ctx.beginPath();
      if (kind === "conical") { ctx.moveTo(x - w * 0.14, base - h); ctx.lineTo(x - w * 0.14, base - h * 0.68); ctx.lineTo(x - w / 2, base); ctx.lineTo(x + w / 2, base); ctx.lineTo(x + w * 0.14, base - h * 0.68); ctx.lineTo(x + w * 0.14, base - h); }
      else if (kind === "test_tube" || kind === "boiling_tube") { ctx.moveTo(x - w / 2, base - h); ctx.lineTo(x - w / 2, base - w / 2); ctx.arc(x, base - w / 2, w / 2, Math.PI, 0, true); ctx.lineTo(x + w / 2, base - h); }
      else if (kind === "crucible") { ctx.moveTo(x - w / 2, base - h); ctx.lineTo(x - w * 0.32, base); ctx.lineTo(x + w * 0.32, base); ctx.lineTo(x + w / 2, base - h); }
      else if (kind === "dish" || kind === "watch_glass") { ctx.moveTo(x - w / 2, base - h); ctx.quadraticCurveTo(x, base + h * 0.6, x + w / 2, base - h); }
      else { ctx.moveTo(x - w / 2, base - h); ctx.lineTo(x - w / 2, base); ctx.lineTo(x + w / 2, base); ctx.lineTo(x + w / 2, base - h); }
    }
    function draw() {
      const W = canvas.clientWidth, H = canvas.clientHeight;
      if (!W || !cat) return;
      const dpr = Math.min(2, devicePixelRatio);
      if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
      const ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      geo = { W, H, y: H * 0.8, slotW: W / SLOTS };
      const now = performance.now() / 1000;
      ctx.fillStyle = "#eef2f7"; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "#d9e0ea"; for (let x = 0; x < W; x += 40) ctx.fillRect(x, 0, 1, geo.y - 30); // tiles
      ctx.fillStyle = "#3b4658"; ctx.fillRect(0, geo.y, W, H - geo.y); ctx.fillStyle = "#566176"; ctx.fillRect(0, geo.y, W, 6);
      for (let s = 0; s < SLOTS; s++) if (!vesselAt(s)) { ctx.strokeStyle = "rgba(11,21,38,.15)"; ctx.setLineDash([5, 5]); ctx.strokeRect(slotX(s) - geo.slotW * 0.38, geo.y - 150, geo.slotW * 0.76, 146); ctx.setLineDash([]); }
      for (const v of vessels) drawVessel(ctx, v, now);
      raf = requestAnimationFrame(draw);
    }
    function drawVessel(ctx, v, now) {
      const o = v.view || {}, x = slotX(v.slot), sc = Math.min(1.25, geo.slotW / 120);
      const [w0, h0] = SHAPE[v.kind], w = w0 * sc, h = h0 * sc;
      const heated = v.heat > 0 && v.kind !== "burette" && v.kind !== "cylinder";
      let base = geo.y - 4;
      if (heated) { // tripod, gauze or holder, Bunsen burner and flame
        const bh = 70 * sc; base = geo.y - bh - 8;
        ctx.fillStyle = "#5b6270"; ctx.fillRect(x - 6 * sc, geo.y - 46 * sc, 12 * sc, 40 * sc); ctx.fillRect(x - 16 * sc, geo.y - 8 * sc, 32 * sc, 8 * sc);
        const fl = (24 + 30 * v.heat) * sc * (0.9 + 0.1 * Math.sin(now * 20));
        const g = ctx.createLinearGradient(0, geo.y - 46 * sc - fl, 0, geo.y - 46 * sc); g.addColorStop(0, "rgba(120,150,255,0)"); g.addColorStop(0.5, "rgba(90,130,255,.75)"); g.addColorStop(1, "rgba(60,90,230,.95)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - 7 * sc, geo.y - 46 * sc); ctx.quadraticCurveTo(x, geo.y - 46 * sc - fl * 1.2, x + 7 * sc, geo.y - 46 * sc); ctx.fill();
        ctx.strokeStyle = "#454b56"; ctx.lineWidth = 2;
        if (["beaker", "conical", "dish", "crucible"].includes(v.kind)) { ctx.beginPath(); ctx.moveTo(x - 34 * sc, geo.y); ctx.lineTo(x - 28 * sc, base); ctx.moveTo(x + 34 * sc, geo.y); ctx.lineTo(x + 28 * sc, base); ctx.stroke(); ctx.fillStyle = "#9aa1ab"; ctx.fillRect(x - 36 * sc, base, 72 * sc, 4); }
        else { ctx.beginPath(); ctx.moveTo(x + 30 * sc, geo.y); ctx.lineTo(x + 30 * sc, base - h * 0.7); ctx.lineTo(x + w / 2, base - h * 0.7); ctx.stroke(); }
      } else if (v.kind === "test_tube" || v.kind === "boiling_tube") { ctx.fillStyle = "#8a6a4a"; ctx.fillRect(x - 24 * sc, geo.y - 14 * sc, 48 * sc, 14 * sc); ctx.fillRect(x - 24 * sc, geo.y - h * 0.75, 48 * sc, 6 * sc); base = geo.y - 4; }
      if (v.kind === "burette") { ctx.fillStyle = "#5b6270"; ctx.fillRect(x - 26 * sc, geo.y - 8, 52 * sc, 8); ctx.fillRect(x - 24 * sc, geo.y - h - 30, 4, h + 30); ctx.fillRect(x - 24 * sc, geo.y - h * 0.6, 24 * sc, 3); base = geo.y - 70 * sc; }
      const cap = cat.equipment.find((e) => e.id === v.kind).capacity, vol = o.volume_ml || 0, frac = Math.min(1, vol / cap);
      // liquid
      ctx.save(); shapePath(ctx, v.kind, x, base, w, h); ctx.closePath(); ctx.clip();
      const liquid = (o.contents && o.contents["H2O(l)"] > 0) ? h * frac : 0;
      if (liquid > 0) {
        ctx.fillStyle = "rgba(170,205,240,.35)"; ctx.fillRect(x - w, base - liquid, 2 * w, liquid + 2); // water itself, faintly blue
        ctx.globalAlpha = Math.max(0.3, o.liquid_alpha || 0.2); ctx.fillStyle = o.liquid_colour || "#ecf2f8"; ctx.fillRect(x - w, base - liquid, 2 * w, liquid + 2); ctx.globalAlpha = 1;
        ctx.strokeStyle = "rgba(11,21,38,.45)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x - w, base - liquid); ctx.lineTo(x + w, base - liquid); ctx.stroke(); // the water line
      }
      if (o.cloudy && liquid > 0) { ctx.fillStyle = "rgba(240,224,140,.45)"; ctx.fillRect(x - w, base - liquid, 2 * w, liquid); }
      // solids settle at the bottom (or lie in a dry vessel)
      let pile = 0;
      for (const s of o.solids || []) {
        const hh = Math.min(h * 0.4, Math.max(2, Math.sqrt(s.mass_g) * 6 * sc));
        ctx.fillStyle = s.colour; ctx.fillRect(x - w, base - pile - hh, 2 * w, hh); pile += hh;
      }
      // bubbles from gases given off; steam when boiling
      const gasMol = (o.gases || []).filter((g) => g.gas !== "H2O").reduce((a, g) => a + g.mol, 0);
      const nb = Math.min(24, Math.round(Math.log10(1 + gasMol * 1e5) * 6)) + (o.boiling ? 14 : 0);
      if (liquid > 4) for (let i = 0; i < nb; i++) { const ph = (now * (0.6 + (i % 5) * 0.15) + i * 0.37) % 1; ctx.fillStyle = "rgba(255,255,255,.8)"; ctx.beginPath(); ctx.arc(x + ((i * 37) % (w * 0.8)) - w * 0.4, base - 3 - ph * (liquid - 4), 1.5 + (i % 3), 0, 6.3); ctx.fill(); }
      ctx.restore();
      // special effects named by the engine's reactions
      const rx = o.reacting || [];
      if (rx.includes("Sodium and water") || rx.includes("Potassium and water")) { const bx = x + Math.sin(now * 3.1) * w * 0.3; ctx.fillStyle = "#d9dde2"; ctx.beginPath(); ctx.arc(bx, base - liquid, 4 * sc, 0, 6.3); ctx.fill(); if (rx.includes("Potassium and water")) { ctx.fillStyle = "rgba(190,120,255,.7)"; ctx.beginPath(); ctx.arc(bx, base - liquid - 8 * sc, 8 * sc, 0, 6.3); ctx.fill(); } }
      if (rx.includes("Magnesium burns in air")) { const g = ctx.createRadialGradient(x, base - 10, 2, x, base - 10, 60 * sc); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, base - 10, 60 * sc, 0, 6.3); ctx.fill(); }
      if (rx.includes("Sulphur burns in air")) { ctx.fillStyle = "rgba(80,120,255,.6)"; ctx.beginPath(); ctx.ellipse(x, base - 10, 14 * sc, 9 * sc, 0, 0, 6.3); ctx.fill(); }
      const fume = (o.gases || []).find((g) => g.gas === "NO2") ? "rgba(150,70,20,.45)" : (o.gases || []).find((g) => g.gas === "SO3") ? "rgba(255,255,255,.6)" : null;
      if (o.boiling || fume) for (let i = 0; i < 6; i++) { const ph = (now * 0.4 + i / 6) % 1; ctx.fillStyle = fume || `rgba(255,255,255,${0.5 * (1 - ph)})`; ctx.beginPath(); ctx.arc(x + Math.sin(i + now) * 8, base - h - ph * 50, 5 + ph * 10, 0, 6.3); ctx.fill(); }
      // a gas jar shows the gas it holds (brown for NO₂, faint for colourless gases)
      const held = Object.entries(o.contents || {}).filter(([k]) => k.endsWith("(g)")).reduce((a, [, n]) => a + n, 0);
      if (held > 1e-6) { ctx.save(); shapePath(ctx, v.kind, x, base, w, h); ctx.closePath(); ctx.clip(); ctx.fillStyle = (o.contents["NO2(g)"] || 0) > 1e-6 ? "rgba(150,70,20,.45)" : `rgba(200,225,250,${Math.min(0.5, 0.15 + held * 30)})`; ctx.fillRect(x - w, base - h, 2 * w, h); ctx.restore(); }
      if (v.kind === "gas_jar") { ctx.fillStyle = "rgba(11,21,38,.25)"; ctx.fillRect(x - w / 2 - 4, base - h - 3, w + 8, 3); } // glass lid
      // delivery tube to the vessel that receives this one's gas
      if (v.gasTo) { const tv = vessels.find((q) => q.id === v.gasTo); if (tv?.hit) { const tx = slotX(tv.slot), top = Math.min(base - h - 18, tv.hit.y0 - 8);
        ctx.strokeStyle = "rgba(11,21,38,.55)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x, base - h * 0.85); ctx.lineTo(x, top); ctx.lineTo(tx, top); ctx.lineTo(tx, tv.hit.y1 - 52); ctx.stroke();
        if ((o.gases || []).some((g) => g.piped_to)) { const ph = (now * 0.8) % 1; ctx.fillStyle = "rgba(255,255,255,.95)"; ctx.beginPath(); ctx.arc(x + (tx - x) * ph, top, 2.5, 0, 6.3); ctx.fill(); } } }
      // glass
      shapePath(ctx, v.kind, x, base, w, h);
      ctx.strokeStyle = selected === v.id ? EMBER : INK; ctx.lineWidth = selected === v.id ? 3 : 2; ctx.stroke();
      if (v.kind === "burette") { ctx.fillStyle = INK; ctx.fillRect(x - 6, base + 2, 12, 4); ctx.beginPath(); ctx.moveTo(x - 2, base + 6); ctx.lineTo(x - 1, base + 16); ctx.lineTo(x + 1, base + 16); ctx.lineTo(x + 2, base + 6); ctx.stroke();
        if (v.tap > 0 && v.over && vol > 0) { const ph = (now * 3) % 1; ctx.fillStyle = o.liquid_colour || "#9cc"; ctx.beginPath(); ctx.arc(x, base + 18 + ph * 20, 2, 0, 6.3); ctx.fill(); }
        if (v.over) { const tv = vessels.find((q) => q.id === v.over); if (tv) { ctx.strokeStyle = "rgba(255,91,46,.6)"; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(x, base + 16); ctx.lineTo(slotX(tv.slot), geo.y - 110); ctx.stroke(); ctx.setLineDash([]); } } }
      // labels
      ctx.fillStyle = "#fff"; ctx.font = `600 ${Math.max(10, 12 * sc)}px Plex, system-ui`; ctx.textAlign = "center";
      ctx.fillText(`${fmt(o.T ?? v.T, 3)} °C${o.ph != null && (o.volume_ml || 0) > 0.5 ? ` · pH ${fmt(Math.max(0, Math.min(14, o.ph)), 2)}` : ""}`, x, geo.y + 22);
      ctx.fillStyle = "#c6cfdb"; ctx.font = `${Math.max(9, 11 * sc)}px Plex, system-ui`; ctx.fillText(cat.equipment.find((e) => e.id === v.kind).name.replace(/ \(.*\)/, ""), x, geo.y + 38);
      v.hit = { x0: x - Math.max(w, 40) / 2 - 6, x1: x + Math.max(w, 40) / 2 + 6, y0: base - h - 10, y1: geo.y + 40 };
    }

    // ---------------------------------------------------------------- input: tap to select or add, drag to move or pour
    const hitAt = (px, py) => vessels.find((v) => v.hit && px >= v.hit.x0 && px <= v.hit.x1 && py >= v.hit.y0 && py <= v.hit.y1);
    const local = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    let drag = null;
    canvas.addEventListener("pointerdown", (e) => { const [px, py] = local(e); const v = hitAt(px, py); drag = v ? { v, px, py, moved: false } : null; if (v) canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => { if (!drag) return; const [px, py] = local(e); if (Math.hypot(px - drag.px, py - drag.py) > 8) drag.moved = true; });
    canvas.addEventListener("pointerup", (e) => {
      const [px, py] = local(e), d = drag; drag = null;
      if (!d) { selected = null; renderInspector(); return; }
      if (!d.moved) {
        if (hand) { amountPrompt(hand, d.v); return; }
        selected = d.v.id; renderInspector(); return;
      }
      const target = hitAt(px, py);
      if (target && target !== d.v) { if (d.v.kind === "burette") { d.v.over = target.id; selected = d.v.id; renderInspector(); } else pourPrompt(d.v, target); return; }
      const slot = Math.max(0, Math.min(SLOTS - 1, Math.floor(px / geo.slotW)));
      if (!vesselAt(slot)) { d.v.slot = slot; }
    });
    canvas.addEventListener("dragover", (e) => e.preventDefault());
    canvas.addEventListener("drop", (e) => {
      e.preventDefault();
      const [px, py] = local(e), data = e.dataTransfer.getData("text/plain");
      if (data.startsWith("eq:")) place(data.slice(3), Math.max(0, Math.min(SLOTS - 1, Math.floor(px / geo.slotW))));
      else if (data.startsWith("ch:")) { const v = hitAt(px, py), c = cat.chemicals.find((q) => q.id === data.slice(3)); if (v && c) amountPrompt(c, v); else note("Drop the chemical onto a vessel."); }
    });

    // ---------------------------------------------------------------- start
    simulate("chemistry", "lab_catalog", {}).then((r) => {
      cat = r.result; renderShelf(); renderInspector(); renderLog();
      place("beaker"); place("test_tube"); place("conical");
      selected = vessels[0]?.id; renderInspector();
      draw();
    }).catch((e) => { root.append(el("p", { class: "empty" }, `Could not open the lab: ${e.message}`)); });
    return () => { cancelAnimationFrame(raf); clearInterval(timer); };
  },
};
