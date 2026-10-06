// Virtual Chemistry Lab: a sandbox bench. Take glassware and chemicals from the shelf and put them anywhere on the bench.
// Lift a vessel over another and it tilts and pours; bubble gas from a cylinder; heat on a burner; run a burette into a
// flask, and watch what happens. Every amount, temperature, pH, colour, precipitate, gas and
// equation comes from the engine (chemistry.lab_step); the browser draws the bench and animates bubbles and flames.
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";

const INK = "#0B1526", EMBER = "#FF5B2E";
const UNIT = 7; // the bench is about seven vessels wide (sets the drawing scale)
const POUR_RATE = { test_tube: 3, boiling_tube: 5, watch_glass: 2, default: 14 }; // mL per second while tilted
const HEATS = [["Off", 0], ["Low", 0.35], ["Medium", 0.7], ["High", 1]];
const SPEEDS = [1, 5, 20];
const DEFAULT_AMOUNT = { solid: 1, liquid: 20, solution: 10, pure: 2 };
const QUICK = { solid: [["A pinch", 0.05], ["0.5 g", 0.5], ["1 g", 1], ["5 g", 5]], liquid: [["1 drop", 0.05], ["10 drops", 0.5], ["Pipette 10 mL", 10], ["Pipette 25 mL", 25]] };
const TEST_LABEL = { litmus_red: "Red litmus", litmus_blue: "Blue litmus", ph_paper: "pH paper", lighted_splint: "Lighted splint", glowing_splint: "Glowing splint", flame: "Flame test" };
const SMALL = { sodium: 0.1, potassium: 0.05, calcium: 0.2, magnesium: 0.1 };
const GAS_QUICK = [["10 mL", 10], ["50 mL", 50], ["100 mL", 100], ["250 mL", 250]];
const SHAPE = { reagent_bottle: [54, 108], beaker: [74, 96], conical: [80, 104], test_tube: [22, 110], boiling_tube: [30, 120], crucible: [56, 36], dish: [96, 30], burette: [16, 230], cylinder: [34, 150], gas_jar: [62, 118], watch_glass: [84, 12] };

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
      el("p", { class: "muted small" }, "Put glassware anywhere on the bench. Lift one over another to pour, bubble gases from the cylinders, heat, titrate. The engine works out what happens.")),
    el("div", { class: "lab-head-tools" }, speedBtn, el("button", { class: "btn small", type: "button", onclick: () => resetBench() }, "Clear bench")));
    root.append(el("div", { class: "lab" }, head, el("div", { class: "lab-body" }, shelf, el("div", { class: "lab-stage" }, canvas, handNote), el("div", { class: "lab-side" }, insp, logBox))));

    // ---------------------------------------------------------------- shelf
    let tab = "chem";
    function renderShelf() {
      const tabs = el("div", { class: "lab-tabs" },
        el("button", { type: "button", class: tab === "chem" ? "on" : "", onclick: () => { tab = "chem"; renderShelf(); } }, "Chemicals"),
        el("button", { type: "button", class: tab === "eq" ? "on" : "", onclick: () => { tab = "eq"; renderShelf(); } }, "Equipment"),
        el("button", { type: "button", class: tab === "gas" ? "on" : "", onclick: () => { tab = "gas"; renderShelf(); } }, "Gases"));
      const body = el("div", { class: "lab-shelf-body" });
      if (tab === "gas") {
        body.append(el("p", { class: "muted small" }, "Gas cylinders. Pick one, then tap a vessel (or drag the cylinder onto it) to bubble the gas through."),
          ...cat.gases.map((g) => el("button", { class: `lab-item${hand?.gas === g.id ? " on" : ""}`, type: "button", draggable: "true", title: g.test,
            ondragstart: (ev) => ev.dataTransfer.setData("text/plain", `gs:${g.id}`), onclick: () => pick({ gas: g.id, name: g.name }) },
            el("b", {}, g.name), el("small", {}, g.id.replace("(g)", " gas")))));
      } else if (tab === "eq") {
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
      hand = (hand && (hand.id ?? hand.gas) === (c.id ?? c.gas)) ? null : c;
      handNote.hidden = !hand;
      handNote.textContent = !hand ? "" : hand.gas ? `${hand.name} cylinder: tap a vessel to bubble the gas into it`
        : `Holding ${hand.name.toLowerCase()}: tap a vessel to add it${isLiquid(hand) ? ", or tap the bench to set down a bottle of it" : ""}`;
      renderShelf();
    }

    // ---------------------------------------------------------------- bench state
    const isLiquid = (c) => c && ["liquid", "solution", "pure"].includes(c.kind);
    const halfW = (v) => Math.max(SHAPE[v.kind][0], 40) / 2 / 120 / UNIT * 1.25 + 0.012; // footprint as a fraction of the bench width
    function freeX(want, v) { // the nearest spot to `want` where v does not overlap anything
      const others = vessels.filter((o) => o !== v && o.x != null), hv = halfW(v);
      const clash = (x) => others.some((o) => Math.abs(o.x - x) < hv + halfW(o));
      for (let d = 0; d < 1; d += 0.01) for (const x of [want + d, want - d]) if (x > hv && x < 1 - hv && !clash(x)) return x;
      return null;
    }
    function place(kind, x = null, extra = {}) {
      if (vessels.length >= 20) { note("The bench is full. Remove something first."); return null; }
      const v = { id: `v${++seq}`, num: seq, kind, contents: {}, T: 25, indicators: [], heat: 0, view: null, over: null, tap: 0, ...extra };
      const at = freeX(x ?? 0.1, v);
      if (at === null) { note("There is no room on the bench. Remove something first."); return null; }
      v.x = at; vessels.push(v); selected = v.id; renderInspector(); draw();
      step([], 0);
      return v;
    }
    function bottleOf(chem, x) { // a reagent bottle filled with 250 mL of a liquid, set on the bench
      const v = place("reagent_bottle", x, { label: chem.name });
      if (v) step([{ type: "add", vessel: v.id, chemical: chem.id, amount: 250 }], 0);
    }
    function resetBench() { vessels = []; selected = null; logs = []; renderInspector(); renderLog(); draw(); }
    function note(text) { logs.unshift({ text, kind: "note" }); logs = logs.slice(0, 60); renderLog(); }

    // ---------------------------------------------------------------- engine
    async function step(actions, dt) {
      if (busy) { pending.push(...actions); resync = true; return; }
      const quiet = actions.length > 0 && actions.every((a) => a.quiet); // small pours while a vessel is held over another
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
        if (!quiet) for (const line of res.log.slice(pours.length)) logs.unshift({ text: line, kind: "action" });
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
    const nameOf = (id) => { const v = vessels.find((x) => x.id === id); return !v ? "" : v.label ? `${v.label} (bottle)` : `${cat.equipment.find((e) => e.id === v.kind).name} (${v.num})`; };
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
    function gasPrompt(gas, v) {
      const g = cat.gases.find((q) => q.id === gas);
      const input = el("input", { type: "number", min: "0", step: "any", value: 50, class: "lab-num", "aria-label": "Gas volume in mL" });
      const go = () => { const a = Number(input.value); if (a > 0) { v.gasFx = { gas: g.name, until: performance.now() / 1000 + 4 }; step([{ type: "gas", vessel: v.id, gas, volume_ml: a }], 1); } closeDialog(); };
      openDialog(`Bubble ${g.name.toLowerCase()} into ${nameOf(v.id)}`, el("div", { class: "lab-seg" }, el("span", {}, "Cylinder valve"),
        ...GAS_QUICK.map(([l, a]) => el("button", { type: "button", onclick: () => { input.value = a; } }, l))),
        el("div", { class: "lab-dialog-row" }, input, el("span", {}, "mL at 25 °C and 1 atm")), el("p", { class: "muted small" }, g.test),
        el("button", { class: "btn primary small", type: "button", onclick: go }, "Open the valve"));
      input.focus(); input.select(); input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    }
    const dialog = el("div", { class: "lab-dialog", hidden: true });
    root.querySelector(".lab-stage").append(dialog);
    function openDialog(title, ...body) { dialog.replaceChildren(el("div", { class: "lab-dialog-head" }, el("b", {}, title), el("button", { type: "button", class: "lab-x", "aria-label": "Close", onclick: closeDialog }, "×")), ...body); dialog.hidden = false; }
    function closeDialog() { dialog.hidden = true; dialog.replaceChildren(); }

    let lastInspector = "";
    function renderInspector(soft = false) {
      const v = vessels.find((x) => x.id === selected);
      if (!v) { insp.replaceChildren(el("h3", {}, "Bench"), el("p", { class: "muted small" }, "Drag glassware from the Equipment shelf to any spot on the bench. Pick a chemical and tap a vessel to add it, or tap the bench to set down a bottle. Lift a vessel and hold it over another: it tilts and pours until you let go. Gases come from the cylinders on the Gases shelf.")); lastInspector = ""; return; }
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
      const gasSel = el("select", { class: "lab-sel", "aria-label": "Bubble gas in" }, el("option", { value: "" }, "Bubble gas in…"), ...cat.gases.map((g) => el("option", { value: g.id }, g.name)));
      gasSel.addEventListener("change", () => { if (gasSel.value) gasPrompt(gasSel.value, v); gasSel.value = ""; });
      const tests = el("div", { class: "lab-seg" }, el("span", {}, "Test"), ...cat.tests.map((k) => el("button", { type: "button", onclick: () => step([{ type: "test", vessel: v.id, test: k }], 0) }, TEST_LABEL[k])));
      const rinseSel = el("select", { class: "lab-sel", "aria-label": "Rinse with", title: "Rinse with the solution it will hold, so the film left behind does not dilute it" },
        el("option", { value: "" }, "Rinse with…"), ...cat.chemicals.filter((c) => c.kind === "solution" || c.kind === "liquid" || c.kind === "pure").map((c) => el("option", { value: c.id }, c.name)));
      rinseSel.addEventListener("change", () => { if (rinseSel.value) step([{ type: "rinse", vessel: v.id, chemical: rinseSel.value }], 0); rinseSel.value = ""; });
      const extra = [];
      if (v.kind === "burette") {
        const overSel = el("select", { class: "lab-sel", "aria-label": "Burette over" }, el("option", { value: "" }, "Not over a vessel"), ...others.map((x) => el("option", { value: x.id, selected: v.over === x.id }, nameOf(x.id))));
        overSel.addEventListener("change", () => { setOver(v, overSel.value || null); renderInspector(); });
        extra.push(el("div", { class: "lab-burette" }, el("b", { class: "lab-reading" }, `Burette reading ${fmt(v.delivered || 0, 3)} mL`), overSel,
          el("div", { class: "lab-seg" }, el("span", {}, "Tap"), ...[["Shut", 0], ["Drops", 0.1], ["Slow", 0.5], ["Open", 2]].map(([l, r]) => el("button", { type: "button", class: v.tap === r ? "on" : "", disabled: !v.over, onclick: () => { v.tap = r; renderInspector(); } }, l))),
          el("button", { class: "btn small", type: "button", onclick: () => { v.delivered = 0; renderInspector(); } }, "Note the initial reading (zero)")));
      }
      insp.replaceChildren(el("h3", {}, nameOf(v.id)), facts, ...extra, heatRow, tests,
        v.kind === "burette" ? "" : el("div", { class: "lab-actions" }, el("span", { class: "muted small" }, "Delivery tube"), tubeSel, gasSel),
        el("div", { class: "lab-actions" }, pourSel, filterSel,
        el("button", { class: "btn small", type: "button", onclick: () => step([{ type: "empty", vessel: v.id }], 0) }, "Empty"),
        el("button", { class: "btn small", type: "button", title: "Wash with distilled water: a thin film of water stays on the glass", onclick: () => step([{ type: "wash", vessel: v.id }], 0) }, "Wash"),
        rinseSel,
        el("button", { class: "btn small danger", type: "button", onclick: () => { vessels = vessels.filter((x) => x !== v); vessels.forEach((x) => { if (x.over === v.id) x.over = null; if (x.gasTo === v.id) x.gasTo = null; }); selected = null; renderInspector(); draw(); } }, "Remove")),
        el("h4", {}, "Contents"), contents);
    }
    function renderLog() {
      logBox.replaceChildren(el("h4", {}, "Lab notebook"), ...(logs.length ? logs.map((l) => el("div", { class: `lab-entry ${l.kind}` },
        l.vessel ? el("small", {}, nameOf(l.vessel)) : "", el("span", {}, l.swatch ? el("i", { class: "lab-swatch", style: `background:${l.swatch}` }) : "", l.text),
        l.eq ? el("code", {}, l.eq) : "", l.kind !== "reaction" ? "" : l.dh != null ? el("small", { class: "muted" }, `ΔH = ${fmt(l.dh, 4)} kJ per mole of reaction${l.dh < 0 ? " (gives out heat)" : " (takes in heat)"}`) : el("small", { class: "muted" }, "ΔH not tabulated for this product"))) : [el("p", { class: "muted small" }, "Observations, equations and gas tests appear here.")]));
    }

    // ---------------------------------------------------------------- drawing
    let geo = { W: 0, H: 0, y: 0, unit: 0 }, lastFrame = 0;
    const posX = (v) => v.x * geo.W;
    function shapePath(ctx, kind, x, base, w, h) {
      ctx.beginPath();
      if (kind === "conical") { ctx.moveTo(x - w * 0.14, base - h); ctx.lineTo(x - w * 0.14, base - h * 0.68); ctx.lineTo(x - w / 2, base); ctx.lineTo(x + w / 2, base); ctx.lineTo(x + w * 0.14, base - h * 0.68); ctx.lineTo(x + w * 0.14, base - h); }
      else if (kind === "reagent_bottle") { ctx.moveTo(x - w * 0.18, base - h); ctx.lineTo(x - w * 0.18, base - h * 0.8); ctx.quadraticCurveTo(x - w / 2, base - h * 0.76, x - w / 2, base - h * 0.6); ctx.lineTo(x - w / 2, base); ctx.lineTo(x + w / 2, base); ctx.lineTo(x + w / 2, base - h * 0.6); ctx.quadraticCurveTo(x + w / 2, base - h * 0.76, x + w * 0.18, base - h * 0.8); ctx.lineTo(x + w * 0.18, base - h); }
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
      geo = { W, H, y: H * 0.8, unit: W / UNIT, dpr };
      const now = performance.now() / 1000, dt = Math.min(0.1, lastFrame ? now - lastFrame : 0); lastFrame = now;
      ctx.fillStyle = "#eef2f7"; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = "#d9e0ea"; for (let x = 0; x < W; x += 40) ctx.fillRect(x, 0, 1, geo.y - 30); // tiles
      ctx.fillStyle = "#3b4658"; ctx.fillRect(0, geo.y, W, H - geo.y); ctx.fillStyle = "#566176"; ctx.fillRect(0, geo.y, W, 6);
      if (!vessels.length) { ctx.fillStyle = "rgba(11,21,38,.4)"; ctx.font = "14px Plex, system-ui"; ctx.textAlign = "center"; ctx.fillText("Drag glassware here from the Equipment shelf", W / 2, geo.y - 60); }
      if (drag?.moved) liftAndPour(dt);
      for (const v of vessels) if (v !== drag?.v || !drag.moved) drawVessel(ctx, v, now);
      if (drag?.moved) drawVessel(ctx, drag.v, now); // the lifted one on top
      raf = requestAnimationFrame(draw);
    }
    // world position of a point given in a lifted vessel's own (tilted) frame
    const tiltPt = (cx, cy, ang, lx, ly) => [cx + lx * Math.cos(ang) - ly * Math.sin(ang), cy + lx * Math.sin(ang) + ly * Math.cos(ang)];
    function drawVessel(ctx, v, now) {
      const o = v.view || {}, sc = Math.min(1.25, geo.unit / 120);
      const [w0, h0] = SHAPE[v.kind], w = w0 * sc, h = h0 * sc;
      const lifted = drag?.moved && drag.v === v, ang = lifted ? drag.tilt : 0;
      let x = lifted ? drag.cx : posX(v);
      const heated = !lifted && v.heat > 0 && v.kind !== "burette" && v.kind !== "cylinder";
      let base = lifted ? drag.cy + h / 2 : geo.y - 4;
      if (heated) { // tripod, gauze or holder, Bunsen burner and flame
        const bh = 70 * sc; base = geo.y - bh - 8;
        ctx.fillStyle = "#5b6270"; ctx.fillRect(x - 6 * sc, geo.y - 46 * sc, 12 * sc, 40 * sc); ctx.fillRect(x - 16 * sc, geo.y - 8 * sc, 32 * sc, 8 * sc);
        const fl = (24 + 30 * v.heat) * sc * (0.9 + 0.1 * Math.sin(now * 20));
        const g = ctx.createLinearGradient(0, geo.y - 46 * sc - fl, 0, geo.y - 46 * sc); g.addColorStop(0, "rgba(120,150,255,0)"); g.addColorStop(0.5, "rgba(90,130,255,.75)"); g.addColorStop(1, "rgba(60,90,230,.95)");
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - 7 * sc, geo.y - 46 * sc); ctx.quadraticCurveTo(x, geo.y - 46 * sc - fl * 1.2, x + 7 * sc, geo.y - 46 * sc); ctx.fill();
        ctx.strokeStyle = "#454b56"; ctx.lineWidth = 2;
        if (["beaker", "conical", "dish", "crucible"].includes(v.kind)) { ctx.beginPath(); ctx.moveTo(x - 34 * sc, geo.y); ctx.lineTo(x - 28 * sc, base); ctx.moveTo(x + 34 * sc, geo.y); ctx.lineTo(x + 28 * sc, base); ctx.stroke(); ctx.fillStyle = "#9aa1ab"; ctx.fillRect(x - 36 * sc, base, 72 * sc, 4); }
        else { ctx.beginPath(); ctx.moveTo(x + 30 * sc, geo.y); ctx.lineTo(x + 30 * sc, base - h * 0.7); ctx.lineTo(x + w / 2, base - h * 0.7); ctx.stroke(); }
      } else if (!lifted && (v.kind === "test_tube" || v.kind === "boiling_tube")) { ctx.fillStyle = "#8a6a4a"; ctx.fillRect(x - 24 * sc, geo.y - 14 * sc, 48 * sc, 14 * sc); ctx.fillRect(x - 24 * sc, geo.y - h * 0.75, 48 * sc, 6 * sc); base = geo.y - 4; }
      if (v.kind === "burette" && !lifted) { ctx.fillStyle = "#5b6270"; ctx.fillRect(x - 26 * sc, geo.y - 8, 52 * sc, 8); ctx.fillRect(x - 24 * sc, geo.y - h - 30, 4, h + 30); ctx.fillRect(x - 24 * sc, geo.y - h * 0.6, 24 * sc, 3); base = geo.y - 70 * sc; }
      const cap = cat.equipment.find((e) => e.id === v.kind).capacity, vol = Math.max(0, (o.volume_ml || 0) - (lifted ? drag.sent + drag.acc : 0)), frac = Math.min(1, vol / cap);
      const cy = base - h / 2;
      v.geo = { x, base, w, h, top: base - h };
      // the vessel's own frame (tilted when lifted over another)
      ctx.save();
      if (ang) { ctx.translate(x, cy); ctx.rotate(ang); ctx.translate(-x, -cy); }
      // liquid: the surface stays level in the world even when the glass tilts
      ctx.save(); shapePath(ctx, v.kind, x, base, w, h); ctx.closePath(); ctx.clip();
      const liquid = (o.contents && o.contents["H2O(l)"] > 0) ? h * frac : 0;
      v.geo.liquid = liquid;
      const level = (top, fill) => { // fill everything below a level surface `top` px above the base
        if (!ang) { ctx.fillStyle = fill; ctx.fillRect(x - w, base - top, 2 * w, top + 2); return; }
        ctx.save(); ctx.setTransform(geo.dpr, 0, 0, geo.dpr, 0, 0); ctx.fillStyle = fill;
        const surf = cy + (h / 2 - top) * Math.cos(ang); ctx.fillRect(x - 2 * h, surf, 4 * h, 3 * h); ctx.restore();
      };
      if (liquid > 0) {
        level(liquid, "rgba(170,205,240,.35)"); // water itself, faintly blue
        ctx.globalAlpha = Math.max(0.3, o.liquid_alpha || 0.2); level(liquid, o.liquid_colour || "#ecf2f8"); ctx.globalAlpha = 1;
        if (!ang) { ctx.strokeStyle = "rgba(11,21,38,.45)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x - w, base - liquid); ctx.lineTo(x + w, base - liquid); ctx.stroke(); } // the water line
      }
      if (o.cloudy && liquid > 0) level(liquid, "rgba(240,224,140,.45)");
      // solids settle at the bottom (or lie in a dry vessel)
      let pile = 0;
      for (const s of o.solids || []) {
        const hh = Math.min(h * 0.4, Math.max(2, Math.sqrt(s.mass_g) * 6 * sc));
        ctx.fillStyle = s.colour; ctx.fillRect(x - w, base - pile - hh, 2 * w, hh); pile += hh;
      }
      // bubbles from gases given off (or bubbled in from a cylinder); steam when boiling
      const gasMol = (o.gases || []).filter((g) => g.gas !== "H2O").reduce((a, g) => a + g.mol, 0);
      const fx = v.gasFx && v.gasFx.until > now;
      const nb = Math.min(24, Math.round(Math.log10(1 + gasMol * 1e5) * 6)) + (o.boiling ? 14 : 0) + (fx ? 16 : 0);
      if (liquid > 4 && !ang) for (let i = 0; i < nb; i++) { const ph = (now * (0.6 + (i % 5) * 0.15) + i * 0.37) % 1; ctx.fillStyle = "rgba(255,255,255,.8)"; ctx.beginPath(); ctx.arc(x + ((i * 37) % (w * 0.8)) - w * 0.4, base - 3 - ph * (liquid - 4), 1.5 + (i % 3), 0, 6.3); ctx.fill(); }
      ctx.restore();
      if (!lifted) {
        // special effects named by the engine's reactions
        const rx = o.reacting || [];
        if (rx.includes("Sodium and water") || rx.includes("Potassium and water")) { const bx = x + Math.sin(now * 3.1) * w * 0.3; ctx.fillStyle = "#d9dde2"; ctx.beginPath(); ctx.arc(bx, base - liquid, 4 * sc, 0, 6.3); ctx.fill(); if (rx.includes("Potassium and water")) { ctx.fillStyle = "rgba(190,120,255,.7)"; ctx.beginPath(); ctx.arc(bx, base - liquid - 8 * sc, 8 * sc, 0, 6.3); ctx.fill(); } }
        if (rx.includes("Magnesium burns in air")) { const g = ctx.createRadialGradient(x, base - 10, 2, x, base - 10, 60 * sc); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, base - 10, 60 * sc, 0, 6.3); ctx.fill(); }
        if (rx.includes("Sulphur burns in air")) { ctx.fillStyle = "rgba(80,120,255,.6)"; ctx.beginPath(); ctx.ellipse(x, base - 10, 14 * sc, 9 * sc, 0, 0, 6.3); ctx.fill(); }
        const fume = (o.gases || []).find((g) => g.gas === "NO2") ? "rgba(150,70,20,.45)" : (o.gases || []).find((g) => g.gas === "SO3") ? "rgba(255,255,255,.6)" : null;
        if (o.boiling || fume) for (let i = 0; i < 6; i++) { const ph = (now * 0.4 + i / 6) % 1; ctx.fillStyle = fume || `rgba(255,255,255,${0.5 * (1 - ph)})`; ctx.beginPath(); ctx.arc(x + Math.sin(i + now) * 8, base - h - ph * 50, 5 + ph * 10, 0, 6.3); ctx.fill(); }
      }
      // a gas jar shows the gas it holds (brown for NO₂, faint for colourless gases)
      const held = Object.entries(o.contents || {}).filter(([k]) => k.endsWith("(g)")).reduce((a, [, n]) => a + n, 0);
      if (held > 1e-6) { ctx.save(); shapePath(ctx, v.kind, x, base, w, h); ctx.closePath(); ctx.clip(); ctx.fillStyle = (o.contents["NO2(g)"] || 0) > 1e-6 ? "rgba(150,70,20,.45)" : `rgba(200,225,250,${Math.min(0.5, 0.15 + held * 30)})`; ctx.fillRect(x - w, base - h, 2 * w, h); ctx.restore(); }
      if (v.kind === "gas_jar") { ctx.fillStyle = "rgba(11,21,38,.25)"; ctx.fillRect(x - w / 2 - 4, base - h - 3, w + 8, 3); } // glass lid
      // glass
      shapePath(ctx, v.kind, x, base, w, h);
      if (v.kind === "reagent_bottle") { ctx.closePath(); ctx.fillStyle = "rgba(120,80,40,.08)"; ctx.fill(); }
      ctx.strokeStyle = selected === v.id ? EMBER : INK; ctx.lineWidth = selected === v.id ? 3 : 2; ctx.stroke();
      if (v.kind === "reagent_bottle" && v.label) { // paper label
        ctx.fillStyle = "#fffdf6"; ctx.fillRect(x - w * 0.42, base - h * 0.5, w * 0.84, h * 0.24); ctx.strokeStyle = "rgba(11,21,38,.3)"; ctx.lineWidth = 1; ctx.strokeRect(x - w * 0.42, base - h * 0.5, w * 0.84, h * 0.24);
        ctx.fillStyle = INK; ctx.font = `600 ${Math.max(8, 9 * sc)}px Plex, system-ui`; ctx.textAlign = "center";
        const words = v.label.replace(/\s*\(.*\)/, "").split(" "), mid = Math.ceil(words.length / 2);
        ctx.fillText(words.slice(0, mid).join(" "), x, base - h * 0.4, w * 0.8); if (words.length > 1) ctx.fillText(words.slice(mid).join(" "), x, base - h * 0.3, w * 0.8);
      }
      ctx.restore();
      if (lifted) { drawStream(ctx, v, x, cy, w, h, ang, o, now); return; }
      // gas cylinder bubbling into this vessel
      if (fx) {
        const gx = x - w / 2 - 26 * sc, gTop = geo.y - 120 * sc;
        ctx.fillStyle = "#6f7c8f"; ctx.beginPath(); ctx.roundRect(gx - 11 * sc, gTop, 22 * sc, geo.y - gTop, 8 * sc); ctx.fill();
        ctx.fillStyle = "#2b3443"; ctx.fillRect(gx - 4 * sc, gTop - 10 * sc, 8 * sc, 10 * sc);
        ctx.fillStyle = "#fff"; ctx.font = `600 ${Math.max(8, 9 * sc)}px Plex, system-ui`; ctx.textAlign = "center"; ctx.save(); ctx.translate(gx + 3 * sc, geo.y - 40 * sc); ctx.rotate(-Math.PI / 2); ctx.fillText(v.gasFx.gas, 0, 0, 90 * sc); ctx.restore();
        ctx.strokeStyle = "rgba(11,21,38,.55)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(gx, gTop - 8 * sc); ctx.quadraticCurveTo(gx, base - h - 24 * sc, x, base - h - 8 * sc); ctx.lineTo(x, base - Math.max(6, liquid * 0.4)); ctx.stroke();
      }
      // delivery tube to the vessel that receives this one's gas
      if (v.gasTo) { const tv = vessels.find((q) => q.id === v.gasTo); if (tv?.hit) { const tx = posX(tv), top = Math.min(base - h - 18, tv.hit.y0 - 8);
        ctx.strokeStyle = "rgba(11,21,38,.55)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x, base - h * 0.85); ctx.lineTo(x, top); ctx.lineTo(tx, top); ctx.lineTo(tx, tv.hit.y1 - 52); ctx.stroke();
        if ((o.gases || []).some((g) => g.piped_to)) { const ph = (now * 0.8) % 1; ctx.fillStyle = "rgba(255,255,255,.95)"; ctx.beginPath(); ctx.arc(x + (tx - x) * ph, top, 2.5, 0, 6.3); ctx.fill(); } } }
      if (v.kind === "burette") { ctx.fillStyle = INK; ctx.fillRect(x - 6, base + 2, 12, 4); ctx.beginPath(); ctx.moveTo(x - 2, base + 6); ctx.lineTo(x - 1, base + 16); ctx.lineTo(x + 1, base + 16); ctx.lineTo(x + 2, base + 6); ctx.stroke();
        if (v.tap > 0 && v.over && vol > 0) { const ph = (now * 3) % 1; ctx.fillStyle = o.liquid_colour || "#9cc"; ctx.beginPath(); ctx.arc(x, base + 18 + ph * 20, 2, 0, 6.3); ctx.fill(); } }
      // labels
      ctx.fillStyle = "#fff"; ctx.font = `600 ${Math.max(10, 12 * sc)}px Plex, system-ui`; ctx.textAlign = "center";
      ctx.fillText(`${fmt(o.T ?? v.T, 3)} °C${o.ph != null && (o.volume_ml || 0) > 0.5 ? ` · pH ${fmt(Math.max(0, Math.min(14, o.ph)), 2)}` : ""}`, x, geo.y + 22);
      ctx.fillStyle = "#c6cfdb"; ctx.font = `${Math.max(9, 11 * sc)}px Plex, system-ui`; ctx.fillText(v.label ? v.label.replace(/\s*\(.*\)/, "") : cat.equipment.find((e) => e.id === v.kind).name.replace(/ \(.*\)/, ""), x, geo.y + 38, geo.unit * 1.1);
      v.hit = { x0: x - Math.max(w, 40) / 2 - 6, x1: x + Math.max(w, 40) / 2 + 6, y0: base - h - 10, y1: geo.y + 40 };
    }
    function drawStream(ctx, v, cx, cy, w, h, ang, o, now) { // liquid running from the tilted lip into the vessel below
      if (!drag.pourTo || Math.abs(ang) < 0.75 || drag.empty) return;
      const tv = vessels.find((q) => q.id === drag.pourTo); if (!tv?.geo) return;
      const dir = Math.sign(ang), lipW = v.kind === "reagent_bottle" ? w * 0.18 : v.kind === "conical" ? w * 0.14 : w / 2;
      const [lx, ly] = tiltPt(cx, cy, ang, dir * lipW, -h / 2);
      const endY = tv.geo.base - (tv.geo.liquid || 0) - 2;
      const dry = !((o.contents || {})["H2O(l)"] > 0);
      const colour = dry ? "rgba(120,110,100,.85)" : (o.liquid_colour && (o.liquid_alpha || 0) > 0.1 ? o.liquid_colour : "rgba(150,195,235,.95)");
      const path = () => { ctx.beginPath(); ctx.moveTo(lx, ly); ctx.quadraticCurveTo(lx + dir * 6, ly + 10, lx + dir * 4, Math.max(ly + 12, endY)); };
      ctx.setLineDash(dry ? [3, 4] : []); ctx.lineDashOffset = -now * 60;
      ctx.strokeStyle = "rgba(11,21,38,.3)"; ctx.lineWidth = dry ? 6 : 5; path(); ctx.stroke();
      ctx.strokeStyle = colour; ctx.lineWidth = dry ? 4 : 3; path(); ctx.stroke();
      if (!dry) { ctx.setLineDash([4, 9]); ctx.strokeStyle = "rgba(255,255,255,.8)"; ctx.lineWidth = 1; path(); ctx.stroke(); } // ripples running down
      ctx.setLineDash([]);
      if (!dry) { ctx.fillStyle = colour; for (let i = 0; i < 3; i++) { const ph = (now * 4 + i / 3) % 1; ctx.beginPath(); ctx.arc(lx + dir * 4 + Math.sin(i * 2 + now * 9) * 5, endY - ph * 6, 1.6, 0, 6.3); ctx.fill(); } } // splash
    }

    // ---------------------------------------------------------------- lifting and pouring
    // While a vessel is held over another it tilts towards it and liquid runs across at a steady rate, sent to the
    // engine in small pours; let go to stop. Drop it over a vessel without tilting to pour an exact amount instead.
    function setOver(b, id) { // a burette stands over a vessel: move that vessel under its tip
      b.over = id; b.tap = 0;
      const tv = vessels.find((q) => q.id === id);
      if (tv) { const x = freeX(b.x, tv); tv.x = Math.abs((x ?? tv.x) - b.x) < 0.05 ? x : b.x; }
      draw();
    }
    function targetUnder(cx, bottom) {
      return vessels.find((t) => t !== drag.v && t.geo && Math.abs(t.geo.x - cx) < t.geo.w / 2 + 30 * Math.min(1.25, geo.unit / 120) && bottom < t.geo.top + 6);
    }
    function liftAndPour(dt) {
      const v = drag.v, [w0, h0] = SHAPE[v.kind], sc = Math.min(1.25, geo.unit / 120), h = h0 * sc;
      const tv = v.kind === "burette" ? null : targetUnder(drag.cx, drag.cy + h / 2);
      drag.pourTo = tv?.id || null;
      const want = tv ? (tv.geo.x >= drag.cx ? 1 : -1) * (v.kind === "reagent_bottle" ? 1.9 : 1.6) : 0;
      drag.tilt += (want - drag.tilt) * Math.min(1, dt * 5);
      if (!tv || Math.abs(drag.tilt) < 0.75) { flushPour(); return; }
      const o = v.view || {}, left = (o.volume_ml || 0) - drag.sent - drag.acc;
      if (!((o.contents || {})["H2O(l)"] > 0)) { // a dry solid tips out all at once
        if ((o.solids || []).length && !drag.empty) { drag.empty = true; step([{ type: "pour", from: v.id, to: tv.id }], 0); }
        return;
      }
      if (left <= 0.01) { drag.empty = true; return; }
      drag.acc += Math.min(left, (POUR_RATE[v.kind] || POUR_RATE.default) * dt * Math.min(1, Math.abs(drag.tilt) - 0.5));
      drag.to = tv.id;
      if (drag.acc >= 1 || performance.now() - drag.lastSend > 300) flushPour();
    }
    function flushPour() {
      if (!drag || drag.acc <= 0.001 || !drag.to) return;
      const amt = drag.acc; drag.sent += amt; drag.acc = 0; drag.lastSend = performance.now(); drag.poured = true;
      step([{ type: "pour", from: drag.v.id, to: drag.to, volume_ml: amt, quiet: true }], 0);
    }

    // ---------------------------------------------------------------- input: tap to select or add, drag to move, lift over a vessel to pour
    const hitAt = (px, py) => [...vessels].reverse().find((v) => v.hit && px >= v.hit.x0 && px <= v.hit.x1 && py >= v.hit.y0 && py <= v.hit.y1);
    const local = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    let drag = null;
    canvas.addEventListener("pointerdown", (e) => {
      const [px, py] = local(e); const v = hitAt(px, py);
      drag = v ? { v, px, py, cx: px, cy: py, moved: false, tilt: 0, acc: 0, sent: 0, lastSend: 0, pourTo: null, to: null, empty: false, poured: false } : null;
      if (v) canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", (e) => {
      if (!drag) return; const [px, py] = local(e);
      if (!drag.moved && Math.hypot(px - drag.px, py - drag.py) > 8) { drag.moved = true; if (drag.v.heat) { drag.v.heat = 0; renderInspector(); } } // lifting it off the burner
      drag.cx = px; drag.cy = Math.min(py, geo.y - 20);
    });
    canvas.addEventListener("pointercancel", () => { flushPour(); drag = null; });
    canvas.addEventListener("pointerup", (e) => {
      const [px, py] = local(e), d = drag;
      if (!d) {
        if (hand && isLiquid(hand)) { bottleOf(hand, px / geo.W); return; }
        selected = null; renderInspector(); return;
      }
      flushPour(); drag = null;
      if (d.sent > 0) logs.unshift({ text: `Poured ${fmt(d.sent, 3)} mL from ${nameOf(d.v.id)} into ${nameOf(d.to)}`, kind: "action" }), renderLog();
      if (!d.moved) {
        if (hand?.gas) { gasPrompt(hand.gas, d.v); return; }
        if (hand) { amountPrompt(hand, d.v); return; }
        selected = d.v.id; renderInspector(); return;
      }
      selected = d.v.id;
      if (d.poured || d.empty) { renderInspector(); return; } // poured from above: it goes back to its place
      const target = hitAt(px, py);
      if (target && target !== d.v) { if (d.v.kind === "burette") { setOver(d.v, target.id); renderInspector(); } else pourPrompt(d.v, target); return; }
      const x = freeX(Math.max(0, Math.min(1, px / geo.W)), d.v);
      if (x !== null) { d.v.x = x; vessels.forEach((b) => { if (b.over === d.v.id && Math.abs(b.x - x) > 0.05) { b.over = null; b.tap = 0; } }); }
      renderInspector();
    });
    canvas.addEventListener("dragover", (e) => e.preventDefault());
    canvas.addEventListener("drop", (e) => {
      e.preventDefault();
      const [px, py] = local(e), data = e.dataTransfer.getData("text/plain"), v = hitAt(px, py);
      if (data.startsWith("eq:")) place(data.slice(3), px / geo.W);
      else if (data.startsWith("gs:")) { if (v) gasPrompt(data.slice(3), v); else note("Drop the gas cylinder onto a vessel."); }
      else if (data.startsWith("ch:")) {
        const c = cat.chemicals.find((q) => q.id === data.slice(3));
        if (v && c) amountPrompt(c, v); else if (isLiquid(c)) bottleOf(c, px / geo.W); else note("Drop the solid onto a vessel.");
      }
    });

    // ---------------------------------------------------------------- start
    simulate("chemistry", "lab_catalog", {}).then((r) => {
      cat = r.result; renderShelf(); renderInspector(); renderLog();
      place("beaker", 0.3); place("test_tube", 0.5); place("conical", 0.7);
      selected = vessels[0]?.id; renderInspector();
      draw();
    }).catch((e) => { root.append(el("p", { class: "empty" }, `Could not open the lab: ${e.message}`)); });
    return () => { cancelAnimationFrame(raf); clearInterval(timer); };
  },
};
