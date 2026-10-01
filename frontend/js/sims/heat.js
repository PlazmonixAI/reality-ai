// Heat Conduction: physics.heat_conduction solves the 1D heat equation (Crank-Nicolson) along a rod.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, checkbox, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, indexAt } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";

const MATERIALS = { copper: "Copper", aluminium: "Aluminium", iron: "Iron", stainless_steel: "Stainless steel", glass: "Glass", water: "Water (still)", wood: "Wood" };
// Display colour scale: cold blue → white → hot red
function heatColor(t, lo, hi) {
  const u = Math.max(0, Math.min(1, (t - lo) / (hi - lo || 1)));
  const a = u < 0.5 ? [42, 120, 214] : [255, 255, 255], b = u < 0.5 ? [255, 255, 255] : [227, 73, 72], f = u < 0.5 ? u * 2 : u * 2 - 1;
  return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * f)).join(",")})`;
}

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, simT = 0;

    const mat = select({ label: "Rod material", value: "copper", options: Object.entries(MATERIALS).map(([v, l]) => ({ value: v, label: l })), onChange: () => recompute() });
    const len = slider({ label: "Rod length", min: 0.05, max: 1, step: 0.01, value: 0.3, unit: "m", onInput: () => recompute() });
    const init = select({ label: "Starting temperatures", value: "uniform", options: [{ value: "uniform", label: "Rod at 20 °C" }, { value: "hot_middle", label: "Hot middle third (100 °C)" }, { value: "sine", label: "Smooth hump" }], onChange: () => recompute() });
    const insL = checkbox({ label: "Insulate left end", value: false, onChange: () => { tl.disable(insL.value); recompute(); } });
    const tl = slider({ label: "Left end held at", min: -20, max: 200, step: 1, value: 100, unit: "°C", onInput: () => recompute() });
    const insR = checkbox({ label: "Insulate right end", value: false, onChange: () => { tr.disable(insR.value); recompute(); } });
    const tr = slider({ label: "Right end held at", min: -20, max: 200, step: 1, value: 0, unit: "°C", onInput: () => recompute() });
    const dur = slider({ label: "Simulated time", min: 10, max: 1e6, value: 300, log: true, format: (v) => fmtTime(v), onInput: () => recompute() });
    const out = readouts([{ key: "a", label: "Thermal diffusivity α" }, { key: "tau", label: "Time constant L²/(π²α)" }, { key: "mean", label: "Mean temperature now" }]);
    L.side.append(
      panel("Rod", mat.root, len.root, init.root, insL.root, tl.root, insR.root, tr.root, dur.root),
      panel("Heat flow (from the engine)", out.root, el("p", { class: "note" }, "Heat spreads from hot to cold; metals with high diffusivity settle fastest. Fixed ends give a straight-line steady state.")),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); upd(); }, { speeds: [0.5, 1, 2], timeFormat: (v) => fmtTime(v) });
    const graph = new LineGraph(L.bottom, { title: "Temperature along the rod", xLabel: "position (cm)", yLabel: "°C", height: 150 });

    const recompute = liveRequest((signal) => simulate("physics", "heat_conduction", {
      material: mat.value, length: len.value, duration: dur.value, initial: init.value, initial_temperature: 20, hot_temperature: 100,
      left_temperature: insL.value ? null : tl.value, right_temperature: insR.value ? null : tr.value, n_nodes: 101, n_frames: 121,
    }, signal), {
      delay: 60, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        out.set("a", `${fmt(r.result.diffusivity, 3)} m²/s`); out.set("tau", fmtTime(r.result.time_constant));
        player.load(dur.value, 8);
      },
    });

    function upd() {
      if (!res) return;
      const k = indexAt(res.frames.t, simT), T = res.frames.temperature[k];
      out.set("mean", `${fmt(T.reduce((a, b) => a + b, 0) / T.length, 4)} °C`);
      graph.setSeries([
        { name: `t = ${fmtTime(res.frames.t[k])}`, color: c1, x: res.x.map((x) => x * 100), y: T },
        { name: "steady state", color: c2, dash: true, x: res.x.map((x) => x * 100), y: res.steady_state },
      ]);
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const k = indexAt(res.frames.t, simT), T = res.frames.temperature[k];
      const all = res.frames.temperature.flat(), lo = Math.min(...all), hi = Math.max(...all);
      const x0 = 70, x1 = w - 70, y = h / 2 - 30, rh = 60, n = T.length, cw = (x1 - x0) / n;
      T.forEach((t, i) => { ctx.fillStyle = heatColor(t, lo, hi); ctx.fillRect(x0 + i * cw, y, cw + 1, rh); });
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2; ctx.strokeRect(x0, y, x1 - x0, rh);
      const end = (x, ins, temp, side) => {
        ctx.fillStyle = ins ? "#d9c9a3" : heatColor(temp, lo, hi); ctx.fillRect(side < 0 ? x - 44 : x, y - 20, 44, rh + 40);
        ctx.strokeStyle = "#39424e"; ctx.strokeRect(side < 0 ? x - 44 : x, y - 20, 44, rh + 40);
        label(ctx, ins ? "insulated" : `${fmt(temp, 3)} °C`, side < 0 ? x - 22 : x + 22, y + rh + 36, { align: "center", font: "12px system-ui" });
      };
      end(x0, insL.value, tl.value, -1); end(x1, insR.value, tr.value, 1);
      // Colour scale
      for (let i = 0; i <= 100; i++) { ctx.fillStyle = heatColor(lo + ((hi - lo) * i) / 100, lo, hi); ctx.fillRect(x0 + ((x1 - x0) * i) / 100, h - 40, (x1 - x0) / 100 + 1, 12); }
      label(ctx, `${fmt(lo, 3)} °C`, x0, h - 16, { font: "11px system-ui", color: "#4b5868" });
      label(ctx, `${fmt(hi, 3)} °C`, x1, h - 16, { align: "right", font: "11px system-ui", color: "#4b5868" });
      label(ctx, `${MATERIALS[mat.value]} rod, ${fmt(len.value * 100, 3)} cm, t = ${fmtTime(res.frames.t[k])}`, 16, 20, { font: "bold 13px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
