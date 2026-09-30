// Circuit Builder: place parts on a grid; physics.dc_circuit solves it with Kirchhoff's laws.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, button } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";

const COLS = 10, ROWS = 6;
const TOOLS = [
  { value: "select", label: "Select" }, { value: "wire", label: "Wire" }, { value: "resistor", label: "Resistor" },
  { value: "bulb", label: "Bulb" }, { value: "battery", label: "Battery" }, { value: "switch", label: "Switch" }, { value: "erase", label: "Erase" },
];
const DEFAULTS = { resistor: 20, bulb: 10, battery: 9 };
const key = (a, b) => (a[0] < b[0] || (a[0] === b[0] && a[1] < b[1]) ? `${a}|${b}` : `${b}|${a}`);
const ends = (k) => k.split("|").map((s) => s.split(",").map(Number));

function defaultCircuit() {
  const m = new Map();
  const put = (a, b, part) => m.set(key(a, b), part);
  const wire = { type: "wire" };
  put([1, 2], [1, 3], { type: "battery", value: 9, flip: false });  // + at the first node in key order (top)
  put([1, 1], [1, 2], wire); put([1, 3], [1, 4], wire);
  put([1, 1], [2, 1], wire); put([2, 1], [3, 1], { type: "switch", closed: true });
  put([3, 1], [4, 1], { type: "resistor", value: 20 }); put([4, 1], [5, 1], wire); put([5, 1], [6, 1], wire);
  put([6, 1], [6, 2], wire); put([6, 2], [6, 3], { type: "bulb", value: 10 }); put([6, 3], [6, 4], wire);
  put([4, 1], [4, 2], wire); put([4, 2], [4, 3], { type: "bulb", value: 10 }); put([4, 3], [4, 4], wire);
  for (let c = 1; c < 6; c++) put([c, 4], [c + 1, 4], wire);
  return m;
}

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    let parts = defaultCircuit();
    let results = null, selected = null, hoverNode = null, short = false;
    const phases = new Map();

    const tool = segmented({ label: "Tool (then click between two dots)", value: "select", options: TOOLS });
    const editBox = el("div");
    const out = readouts([{ key: "p", label: "Total power" }, { key: "i", label: "Battery current" }]);
    L.side.append(
      panel("Build", tool.root, el("div", { class: "btn-row" },
        button("Reset", () => { parts = defaultCircuit(); selected = null; renderEdit(); recompute(); }),
        button("Clear all", () => { parts = new Map(); selected = null; renderEdit(); recompute(); })),
        el("p", { class: "note" }, "Select a part to change its value. Click a switch (Select tool) to open or close it. Hover a junction to read its voltage.")),
      panel("Selected part", editBox),
      panel("Circuit (from the engine)", out.root, el("p", { class: "note" }, "Moving dots show conventional current (+ to −); speed ∝ current. Bulbs glow with power.")),
    );

    function renderEdit() {
      const p = selected && parts.get(selected);
      if (!p) { editBox.replaceChildren(el("p", { class: "note" }, "Nothing selected.")); return; }
      const rows = [el("p", { style: "margin:0 0 8px;font-weight:600" }, p.type[0].toUpperCase() + p.type.slice(1))];
      if (p.type === "resistor" || p.type === "bulb") rows.push(slider({ label: "Resistance", min: 1, max: 1000, value: p.value, log: true, unit: "Ω", onInput: (v) => { p.value = v; recompute(); } }).root);
      if (p.type === "battery") {
        rows.push(slider({ label: "Voltage", min: 0.5, max: 24, step: 0.5, value: p.value, unit: "V", onInput: (v) => { p.value = v; recompute(); } }).root);
        rows.push(button("Flip direction", () => { p.flip = !p.flip; recompute(); }));
      }
      if (p.type === "switch") rows.push(button(p.closed ? "Open switch" : "Close switch", () => { p.closed = !p.closed; renderEdit(); recompute(); }));
      const info = el("dl", { class: "readouts", style: "margin-top:10px" });
      const r = results && results.byKey.get(selected);
      if (r) for (const [k, v] of [["Current", `${fmt(Math.abs(r.current), 4)} A`], ["Voltage", `${fmt(Math.abs(r.voltage), 4)} V`], ["Power", `${fmt(Math.abs(r.power), 4)} W`]])
        info.append(el("dt", {}, k), el("dd", {}, v));
      rows.push(info, button("Delete", () => { parts.delete(selected); selected = null; renderEdit(); recompute(); }));
      editBox.replaceChildren(...rows);
    }

    function engineComponents() {
      const list = [], keys = [];
      for (const [k, p] of parts) {
        const [a, b] = ends(k).map((e) => e.join(","));
        if (p.type === "switch" && !p.closed) continue;
        if (p.type === "wire" || p.type === "switch") list.push({ type: "wire", a, b });
        else if (p.type === "battery") list.push({ type: "voltage_source", a: p.flip ? b : a, b: p.flip ? a : b, value: p.value });
        else list.push({ type: "resistor", a, b, value: p.value });
        keys.push(k);
      }
      return { list, keys };
    }

    const recompute = liveRequest(async (signal) => {
      const { list, keys } = engineComponents();
      if (!list.some((c) => c.type === "voltage_source")) return { none: true };
      const res = await simulate("physics", "dc_circuit", { components: list }, signal);
      return { res, keys, list };
    }, {
      delay: 60, onBusy: L.busy,
      onError: (e) => { L.error(e.message); results = null; },
      onResult: (d) => {
        L.clearError();
        if (d.none) { results = null; out.set("p", "–"); out.set("i", "add a battery"); renderEdit(); return; }
        const byKey = new Map();
        d.res.result.components.forEach((c, i) => {
          const k = d.keys[i], [a] = ends(k).map((e) => e.join(","));
          // Normalise so current is positive from the first node of the key to the second.
          const sign = c.a === a ? 1 : -1;
          byKey.set(k, { current: sign * c.current, voltage: sign * c.voltage, power: c.power });
        });
        results = { byKey, volts: d.res.result.node_voltages, total: d.res.result.power_supplied };
        const bat = d.res.result.components.filter((c) => c.type === "voltage_source");
        const imax = Math.max(0, ...bat.map((c) => Math.abs(c.current)));
        short = imax > 20;
        out.set("p", `${fmt(results.total, 4)} W`); out.set("i", `${fmt(imax, 4)} A`);
        renderEdit();
      },
    });

    function geom() {
      const { width: w, height: h } = stage;
      const s = Math.min((w - 80) / (COLS - 1), (h - 80) / (ROWS - 1));
      return { s, ox: (w - s * (COLS - 1)) / 2, oy: (h - s * (ROWS - 1)) / 2 };
    }
    const P = ([c, r], g) => [g.ox + c * g.s, g.oy + r * g.s];

    function edgeAt(mx, my) {
      const g = geom();
      let best = null, bd = g.s * 0.3;
      for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) {
        for (const [dc, dr] of [[1, 0], [0, 1]]) {
          if (c + dc >= COLS || r + dr >= ROWS) continue;
          const [x1, y1] = P([c, r], g), [x2, y2] = P([c + dc, r + dr], g);
          const d = Math.hypot(mx - (x1 + x2) / 2, my - (y1 + y2) / 2);
          if (d < bd) { bd = d; best = key([c, r], [c + dc, r + dr]); }
        }
      }
      return best;
    }

    stage.canvas.addEventListener("pointerdown", (e) => {
      const r = stage.canvas.getBoundingClientRect();
      const k = edgeAt(e.clientX - r.left, e.clientY - r.top);
      if (!k) return;
      const t = tool.value;
      if (t === "select") {
        const p = parts.get(k);
        if (p && p.type === "switch" && selected === k) { p.closed = !p.closed; recompute(); }
        selected = p ? k : null;
      } else if (t === "erase") { parts.delete(k); if (selected === k) selected = null; }
      else {
        parts.set(k, t === "battery" ? { type: t, value: DEFAULTS.battery, flip: false } : t === "switch" ? { type: t, closed: true } : t === "wire" ? { type: t } : { type: t, value: DEFAULTS[t] });
        selected = k;
      }
      renderEdit(); recompute();
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      const r = stage.canvas.getBoundingClientRect(), g = geom();
      const c = Math.round((e.clientX - r.left - g.ox) / g.s), rr = Math.round((e.clientY - r.top - g.oy) / g.s);
      const [x, y] = P([c, rr], g);
      hoverNode = c >= 0 && c < COLS && rr >= 0 && rr < ROWS && Math.hypot(e.clientX - r.left - x, e.clientY - r.top - y) < 12 ? `${c},${rr}` : null;
    });

    function drawPart(ctx, k, p, g, dt) {
      const [a, b] = ends(k), [x1, y1] = P(a, g), [x2, y2] = P(b, g);
      const len = Math.hypot(x2 - x1, y2 - y1), ang = Math.atan2(y2 - y1, x2 - x1);
      const res = results && results.byKey.get(k);
      ctx.save(); ctx.translate(x1, y1); ctx.rotate(ang);
      const mid = len / 2, body = Math.min(46, len * 0.55);
      const isSel = k === selected;
      ctx.lineWidth = 5; ctx.strokeStyle = "#8a6d3b"; ctx.lineCap = "round";
      const lead = (from, to) => { ctx.beginPath(); ctx.moveTo(from, 0); ctx.lineTo(to, 0); ctx.stroke(); };
      if (p.type === "wire" || (p.type === "switch")) {
        if (p.type === "wire") lead(0, len);
        else {
          lead(0, mid - body / 2); lead(mid + body / 2, len);
          ctx.strokeStyle = "#39424e"; ctx.lineWidth = 4;
          ctx.beginPath(); ctx.moveTo(mid - body / 2, 0);
          ctx.lineTo(mid + body / 2, p.closed ? 0 : -body * 0.5); ctx.stroke();
          ctx.fillStyle = "#39424e"; ctx.beginPath(); ctx.arc(mid - body / 2, 0, 4, 0, Math.PI * 2); ctx.arc(mid + body / 2, 0, 4, 0, Math.PI * 2); ctx.fill();
        }
      } else if (p.type === "resistor") {
        lead(0, mid - body / 2); lead(mid + body / 2, len);
        ctx.fillStyle = "#d9b98a"; ctx.fillRect(mid - body / 2, -9, body, 18);
        for (const [f, c] of [[0.25, "#7a3e1d"], [0.45, "#16202c"], [0.65, "#e34948"]]) { ctx.fillStyle = c; ctx.fillRect(mid - body / 2 + body * f, -9, 4, 18); }
      } else if (p.type === "bulb") {
        lead(0, mid - 10); lead(mid + 10, len);
        const pw = res ? Math.abs(res.power) : 0;
        const glow = Math.min(1, Math.sqrt(pw / 10));
        if (glow > 0.01) {
          const gr = ctx.createRadialGradient(mid, -12, 2, mid, -12, 40 * (0.4 + glow));
          gr.addColorStop(0, `rgba(255,220,90,${0.9 * glow})`); gr.addColorStop(1, "rgba(255,220,90,0)");
          ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(mid, -12, 40 * (0.4 + glow), 0, Math.PI * 2); ctx.fill();
        }
        ctx.fillStyle = `rgba(255,${230 - 40 * glow},${150 - 120 * glow},${0.35 + 0.65 * glow})`; ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(mid, -12, 13, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#7b8796"; ctx.fillRect(mid - 7, -1, 14, 8);
      } else if (p.type === "battery") {
        lead(0, mid - body / 2); lead(mid + body / 2, len);
        ctx.fillStyle = "#39424e"; ctx.fillRect(mid - body / 2, -12, body, 24);
        const plusLeft = !p.flip;
        ctx.fillStyle = "#eda100"; ctx.fillRect(plusLeft ? mid - body / 2 : mid + body / 2 - 12, -12, 12, 24);
        ctx.restore(); ctx.save();
        const pl = plusLeft ? [x1 + (x2 - x1) * 0.3, y1 + (y2 - y1) * 0.3] : [x1 + (x2 - x1) * 0.7, y1 + (y2 - y1) * 0.7];
        label(ctx, "+", pl[0] + (y1 === y2 ? 0 : 20), pl[1] + (y1 === y2 ? -20 : 0), { align: "center", font: "bold 15px system-ui", color: "#c98500" });
        label(ctx, `${fmt(p.value, 3)} V`, (x1 + x2) / 2 + (y1 === y2 ? 0 : 34), (y1 + y2) / 2 + (y1 === y2 ? 26 : 0), { align: "center", font: "12px system-ui" });
        ctx.restore(); ctx.save(); ctx.translate(x1, y1); ctx.rotate(ang);
      }
      // Current dots
      if (res && Math.abs(res.current) > 1e-9) {
        const ph = (phases.get(k) || 0) + res.current * dt * 40;
        phases.set(k, ph);
        ctx.fillStyle = "rgba(42,120,214,.9)";
        const sp = 16;
        for (let d = ((ph % sp) + sp) % sp; d < len; d += sp) { ctx.beginPath(); ctx.arc(d, 0, 2.6, 0, Math.PI * 2); ctx.fill(); }
      }
      if (isSel) { ctx.strokeStyle = "rgba(42,120,214,.6)"; ctx.lineWidth = 2; ctx.setLineDash([4, 3]); ctx.strokeRect(-4, -22, len + 8, 44); ctx.setLineDash([]); }
      ctx.restore();
      if (res && (p.type === "resistor" || p.type === "bulb")) {
        const off = y1 === y2 ? [0, 26] : [38, 0];
        label(ctx, `${fmt(p.value, 3)} Ω`, (x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], { align: "center", font: "11px system-ui", color: "#4b5868" });
      }
    }

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f3f6f0"; ctx.fillRect(0, 0, w, h);
      const g = geom();
      ctx.fillStyle = "#b8c4d3";
      for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++) { const [x, y] = P([c, r], g); ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill(); }
      for (const [k, p] of parts) drawPart(ctx, k, p, g, dt);
      if (hoverNode && results) {
        const [c, r] = hoverNode.split(",").map(Number), [x, y] = P([c, r], g);
        const v = results.volts[hoverNode];
        ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
        if (v !== undefined) label(ctx, `${fmt(v, 4)} V`, x + 10, y - 14, { font: "bold 12px system-ui", halo: "#fff" });
      }
      if (short) label(ctx, "⚠ Short circuit! Huge current through the wires.", w / 2, 22, { align: "center", font: "bold 14px system-ui", color: "#c93a3a", halo: "#fff" });
      label(ctx, "Voltages are relative to the battery's − terminal", 14, h - 14, { font: "11px system-ui", color: "#7b8796" });
    });

    renderEdit();
    recompute();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
