// Reaction Rates: reaction_kinetics integrates the rate law; arrhenius gives k from temperature.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, checkbox, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, sampleAt, label } from "../core/stage.js";
import { Player, animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";

const N = 240;
const K_UNITS = { 0: "M/s", 1: "1/s", 2: "1/(M·s)" };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2] = SERIES();
    let data = null, simTime = 0, kValue = null;
    let seed = 9;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const molecules = Array.from({ length: N }, () => ({ x: rand(), y: rand(), vx: rand() - 0.5, vy: rand() - 0.5 }));
    const order = Array.from({ length: N }, (_, i) => i).sort(() => rand() - 0.5);   // conversion order

    const ord = segmented({ label: "Reaction order", value: "1", options: [{ value: "0", label: "Zero" }, { value: "1", label: "First" }, { value: "2", label: "Second" }], onChange: () => recompute() });
    const a0 = slider({ label: "[A]₀ initial concentration", min: 0.1, max: 2, step: 0.05, value: 1, unit: "M", onInput: () => recompute() });
    const kSlider = slider({ label: "Rate constant k", min: 1e-4, max: 1, value: 0.01, log: true, onInput: () => recompute() });
    const useArr = checkbox({ label: "Set k from temperature (Arrhenius)", onChange: (on) => { arrPanel.style.display = on ? "" : "none"; kSlider.disable(on); recompute(); } });
    const ea = slider({ label: "Activation energy Ea", min: 20, max: 150, step: 1, value: 75, unit: "kJ/mol", onInput: () => recompute() });
    const T = slider({ label: "Temperature", min: 250, max: 600, step: 1, value: 298, unit: "K", onInput: () => recompute() });
    const A = slider({ label: "Pre-exponential factor A", min: 1e6, max: 1e14, value: 1e11, log: true, onInput: () => recompute() });
    const arrPanel = el("div", { style: "display:none" }, ea.root, T.root, A.root);
    const out = readouts([{ key: "k", label: "k" }, { key: "half", label: "Half-life" }, { key: "a", label: "[A] now" }, { key: "b", label: "[B] now" }]);
    L.side.append(
      panel("Reaction A → B", ord.root, a0.root, kSlider.root, useArr.root, arrPanel),
      panel("Kinetics (from the engine)", out.root, el("p", { class: "note" }, "Rate = k[A]ⁿ. The container shows 240 molecules; the share still blue follows [A]/[A]₀.")),
    );
    const player = new Player(L.bottom, (t) => { simTime = t; graph.setCursor(t); updateReadouts(); }, { speeds: [0.5, 1, 2, 4] });
    const graph = new LineGraph(L.bottom, { title: "Concentration", xLabel: "time (s)", yLabel: "concentration (M)", height: 150, includeZero: true });

    const recompute = liveRequest(async (signal) => {
      let k = kSlider.value;
      if (useArr.value) {
        const r = await simulate("chemistry", "arrhenius", { pre_exponential: A.value, activation_energy: ea.value * 1000, temperature: T.value }, signal);
        k = r.result;
      }
      const res = await simulate("chemistry", "reaction_kinetics", { order: Number(ord.value), rate_constant: k, initial_concentration: a0.value, n_points: 400 }, signal);
      return { k, res };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ k, res }) => {
        L.clearError(); data = res; kValue = k;
        if (useArr.value) kSlider.set(Math.min(Math.max(k, 1e-4), 1));
        const c = res.curve;
        graph.setSeries([
          { name: "[A]", color: c1, x: c.t, y: c.concentration },
          { name: "[B]", color: c2, x: c.t, y: c.concentration.map((v) => a0.value - v), dash: true },
        ]);
        out.set("k", `${fmt(k, 3)} ${K_UNITS[ord.value]}`); out.set("half", fmtTime(res.result.half_life));
        player.load(c.t[c.t.length - 1], 12);
      },
    });

    function concentration() { return data ? sampleAt(data.curve.t, data.curve.concentration, simTime) : a0.value; }
    function updateReadouts() {
      const a = concentration();
      out.set("a", `${fmt(a, 3)} M`); out.set("b", `${fmt(a0.value - a, 3)} M`);
    }

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f4f7fb"; ctx.fillRect(0, 0, w, h);
      const bx = 30, by = 40, bw = Math.min(w - 60, (h - 80) * 1.8), bh = h - 90;
      ctx.fillStyle = "#fff"; ctx.fillRect(bx, by, bw, bh);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3; ctx.strokeRect(bx, by, bw, bh);
      const fracA = Math.max(0, Math.min(1, concentration() / a0.value));
      const nA = Math.round(fracA * N);
      const speed = useArr.value ? 0.12 + 0.25 * ((T.value - 250) / 350) : 0.2;
      molecules.forEach((m, i) => {
        m.x += m.vx * speed * dt; m.y += m.vy * speed * dt * 1.6;
        if (m.x < 0 || m.x > 1) { m.vx *= -1; m.x = Math.max(0, Math.min(1, m.x)); }
        if (m.y < 0 || m.y > 1) { m.vy *= -1; m.y = Math.max(0, Math.min(1, m.y)); }
        m.vx += (Math.random() - 0.5) * 0.6 * dt; m.vy += (Math.random() - 0.5) * 0.6 * dt;
        const isA = order.indexOf(i) < nA;
        ctx.fillStyle = isA ? c1 : c2;
        const x = bx + 8 + m.x * (bw - 16), y = by + 8 + m.y * (bh - 16);
        ctx.beginPath();
        if (isA) ctx.arc(x, y, 5, 0, Math.PI * 2); else ctx.rect(x - 4.5, y - 4.5, 9, 9);
        ctx.fill();
      });
      label(ctx, `A: ${nA}   B: ${N - nA}`, bx, by - 14, { font: "bold 13px system-ui" });
      label(ctx, `t = ${fmtTime(simTime)}`, bx + bw, by - 14, { font: "13px system-ui", align: "right" });
      if (kValue !== null) label(ctx, `k = ${fmt(kValue, 3)} ${K_UNITS[ord.value]}`, bx + bw / 2, by - 14, { font: "13px system-ui", align: "center", color: "#4b5868" });
    });

    L.scene.append(el("div", { style: "position:absolute;right:16px;bottom:10px" }, legend([{ label: "A (reactant, circles)", color: c1 }, { label: "B (product, squares)", color: c2 }])));
    recompute();
    return () => { stop(); recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
