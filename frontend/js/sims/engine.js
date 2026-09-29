// Heat Engines: physics.heat_engine_cycle gives the PV loop, work, heat and efficiency.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, niceStep } from "../core/stage.js";
import { Player } from "../core/player.js";
import { fmt } from "../core/format.js";

const LEG_COLORS = ["#e34948", "#eb6834", "#2a78d6", "#1baf7a"];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    let res = null, s = 0;   // s: position around the loop, 0..4 (legs)

    const cycle = segmented({ label: "Cycle", value: "otto", options: [{ value: "carnot", label: "Carnot" }, { value: "otto", label: "Otto (petrol)" }, { value: "diesel", label: "Diesel" }], onChange: () => { sync(); recompute(); } });
    const th = slider({ label: "Hot reservoir", min: 350, max: 1500, step: 10, value: 600, unit: "K", onInput: () => recompute() });
    const tc = slider({ label: "Cold reservoir", min: 200, max: 500, step: 5, value: 300, unit: "K", onInput: () => recompute() });
    const er = slider({ label: "Isothermal expansion ratio", min: 1.2, max: 5, step: 0.1, value: 2, onInput: () => recompute() });
    const r = slider({ label: "Compression ratio", min: 2, max: 25, step: 0.5, value: 9, onInput: () => recompute() });
    const tmax = slider({ label: "Peak temperature", min: 1000, max: 3000, step: 50, value: 2000, unit: "K", onInput: () => recompute() });
    const rc = slider({ label: "Cutoff ratio", min: 1.2, max: 4, step: 0.1, value: 2, onInput: () => recompute() });
    const gamma = slider({ label: "γ = Cp/Cv", min: 1.1, max: 1.67, step: 0.01, value: 1.4, onInput: () => recompute() });
    const out = readouts([
      { key: "w", label: "Net work per cycle" }, { key: "qin", label: "Heat in" }, { key: "qout", label: "Heat out" },
      { key: "eff", label: "Efficiency (numerical)" }, { key: "form", label: "Textbook formula" }, { key: "carnot", label: "Carnot limit (same T range)" },
    ]);
    const legBox = el("div");
    function sync() {
      const c = cycle.value;
      th.root.style.display = tc.root.style.display = er.root.style.display = c === "carnot" ? "" : "none";
      r.root.style.display = c === "carnot" ? "none" : "";
      tmax.root.style.display = c === "otto" ? "" : "none";
      rc.root.style.display = c === "diesel" ? "" : "none";
    }
    L.side.append(panel("Engine (1 mol ideal gas)", cycle.root, th.root, tc.root, er.root, r.root, tmax.root, rc.root, gamma.root),
      panel("Cycle (from the engine)", out.root, legBox));
    sync();
    const player = new Player(L.bottom, (t) => { s = t; draw(); }, { speeds: [0.5, 1, 2], loop: true, timeFormat: (v) => `stroke ${Math.min(4, Math.floor(v) + 1)} of 4` });

    const recompute = liveRequest((signal) => {
      const c = cycle.value;
      const args = { cycle: c, gamma: gamma.value };
      if (c === "carnot") Object.assign(args, { t_hot: Math.max(th.value, tc.value + 10), t_cold: tc.value, expansion_ratio: er.value });
      else Object.assign(args, { compression_ratio: r.value, t_max: tmax.value, cutoff_ratio: Math.min(rc.value, r.value * 0.9) });
      return simulate("physics", "heat_engine_cycle", args, signal);
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (x) => {
        L.clearError(); res = x;
        const q = x.result;
        out.set("w", `${fmt(q.net_work / 1000, 4)} kJ`); out.set("qin", `${fmt(q.heat_in / 1000, 4)} kJ`); out.set("qout", `${fmt(q.heat_out / 1000, 4)} kJ`);
        out.set("eff", `${fmt(q.efficiency * 100, 4)} %`); out.set("form", `${fmt(q.formula_efficiency * 100, 4)} %`); out.set("carnot", `${fmt(q.carnot_limit * 100, 4)} %`);
        legBox.replaceChildren(...x.legs.map((l, i) => el("div", { style: "display:flex;gap:8px;align-items:center;font-size:12px;margin-top:4px" },
          el("i", { style: `width:14px;height:4px;border-radius:2px;background:${LEG_COLORS[i]}` }), `${i + 1}. ${l.name}`)));
        player.load(4, 8);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const vs = res.legs.flatMap((l) => l.v), ps = res.legs.flatMap((l) => l.p);
      const vmax = Math.max(...vs) * 1.08, pmax = Math.max(...ps) * 1.08;
      const left = 64, right = w * 0.68, top = 24, bottom = h - 40;
      const X = (v) => left + (v / vmax) * (right - left), Y = (p) => bottom - (p / pmax) * (bottom - top);
      ctx.strokeStyle = "#e3e8ef";
      const pv = niceStep(pmax / 1000, 5) * 1000, vv = niceStep(vmax * 1000, 6) / 1000;
      for (let p = 0; p <= pmax; p += pv) { ctx.beginPath(); ctx.moveTo(left, Y(p)); ctx.lineTo(right, Y(p)); ctx.stroke(); label(ctx, fmt(p / 1000, 3), left - 6, Y(p), { align: "right", font: "11px system-ui", color: "#4b5868" }); }
      for (let v = 0; v <= vmax; v += vv) { ctx.beginPath(); ctx.moveTo(X(v), top); ctx.lineTo(X(v), bottom); ctx.stroke(); label(ctx, fmt(v * 1000, 3), X(v), bottom + 14, { align: "center", font: "11px system-ui", color: "#4b5868" }); }
      label(ctx, "P (kPa)", 14, 14, { font: "11px system-ui", color: "#7b8796" });
      label(ctx, "V (litres)", right, bottom + 30, { align: "right", font: "11px system-ui", color: "#7b8796" });
      // Enclosed area = net work
      ctx.fillStyle = "rgba(42,120,214,.12)"; ctx.beginPath();
      res.legs.forEach((l, k) => l.v.forEach((v, i) => (k === 0 && i === 0 ? ctx.moveTo(X(v), Y(l.p[i])) : ctx.lineTo(X(v), Y(l.p[i])))));
      ctx.closePath(); ctx.fill();
      res.legs.forEach((l, k) => {
        ctx.strokeStyle = LEG_COLORS[k]; ctx.lineWidth = 3; ctx.beginPath();
        l.v.forEach((v, i) => (i ? ctx.lineTo(X(v), Y(l.p[i])) : ctx.moveTo(X(v), Y(l.p[i])))); ctx.stroke();
      });
      res.states.forEach((st, i) => {
        ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(X(st.v), Y(st.p), 4, 0, Math.PI * 2); ctx.fill();
        label(ctx, `${i + 1} (${fmt(st.t, 3)} K)`, X(st.v) + 8, Y(st.p) - 10, { font: "11px system-ui", halo: "#fff" });
      });
      label(ctx, `shaded area = net work = ${fmt(res.result.net_work / 1000, 3)} kJ`, (left + right) / 2, top + 4, { align: "center", font: "bold 12px system-ui", color: "#1c5cab" });
      // Moving state point + cylinder
      const k = Math.min(3, Math.floor(s)), f = s - k, leg = res.legs[k];
      const i = Math.min(leg.v.length - 1, Math.round(f * (leg.v.length - 1)));
      const v = leg.v[i], p = leg.p[i];
      ctx.fillStyle = LEG_COLORS[k]; ctx.beginPath(); ctx.arc(X(v), Y(p), 8, 0, Math.PI * 2); ctx.fill();
      const cx = w * 0.84, cw = Math.min(110, w * 0.13), ch = h * 0.6, cy = h * 0.2;
      const gasH = (v / vmax) * ch;
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3; ctx.strokeRect(cx - cw / 2, cy, cw, ch);
      const heat = Math.min(1, (p * v / 8.314462618) / 2500);
      ctx.fillStyle = `rgba(${Math.round(80 + 170 * heat)},${Math.round(130 - 60 * heat)},${Math.round(220 - 170 * heat)},.5)`;
      ctx.fillRect(cx - cw / 2 + 2, cy + ch - gasH, cw - 4, gasH - 2);
      ctx.fillStyle = "#7b8796"; ctx.fillRect(cx - cw / 2 + 2, cy + ch - gasH - 12, cw - 4, 12); ctx.fillRect(cx - 4, cy - 30, 8, ch - gasH + 18);
      label(ctx, leg.name, cx, cy + ch + 20, { align: "center", font: "bold 11px system-ui", color: LEG_COLORS[k] });
      label(ctx, `${fmt(p * v / 8.314462618, 3)} K`, cx, cy + ch - gasH / 2, { align: "center", font: "bold 12px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); stage.destroy(); };
  },
};
