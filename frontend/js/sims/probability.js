// Probability & the CLT: probability_distribution for the chosen law; sample_means for the central limit theorem.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, niceStep } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const DISTS = {
  normal: { label: "Normal", params: { mean: [-10, 10, 0.1, 0], sd: [0.2, 5, 0.1, 1] } },
  binomial: { label: "Binomial", params: { n: [1, 60, 1, 20], p: [0.01, 0.99, 0.01, 0.3] } },
  poisson: { label: "Poisson", params: { rate: [0.2, 30, 0.1, 4] } },
  exponential: { label: "Exponential", params: { rate: [0.1, 5, 0.05, 1] } },
  uniform: { label: "Uniform", params: { low: [-10, 9, 0.5, 0], high: [-9, 10, 0.5, 1] } },
};

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null;

    const kind = select({ label: "Distribution", value: "binomial", options: Object.entries(DISTS).map(([v, d]) => ({ value: v, label: d.label })), onChange: () => build() });
    const paramBox = el("div");
    let params = {};
    const lo = slider({ label: "Interval from a", min: -20, max: 60, step: 0.5, value: 4, onInput: () => recompute() });
    const hi = slider({ label: "to b", min: -20, max: 60, step: 0.5, value: 8, onInput: () => recompute() });
    const n = slider({ label: "Sample size n", min: 1, max: 200, step: 1, value: 5, onInput: () => recompute() });
    const out = readouts([{ key: "mean", label: "Mean" }, { key: "sd", label: "Standard deviation" }, { key: "p", label: "P(a ≤ X ≤ b)" }]);
    const clt = readouts([{ key: "m", label: "Mean of sample means" }, { key: "s", label: "SD of sample means" }, { key: "pred", label: "CLT prediction σ/√n" }, { key: "skew", label: "Skewness of means" }]);
    L.side.append(
      panel("Distribution", kind.root, paramBox, lo.root, hi.root),
      panel("Exact values (from the engine)", out.root),
      panel("Central limit theorem", n.root, clt.root, el("p", { class: "note" }, "2,000 random samples of size n: their means pile up into a bell curve, whatever the starting shape.")),
    );
    const graph = new LineGraph(L.bottom, { title: "Distribution of sample means", xLabel: "sample mean", yLabel: "density", height: 170, includeZero: true });

    function build() {
      params = {};
      paramBox.replaceChildren(...Object.entries(DISTS[kind.value].params).map(([name, [mn, mx, st, v]]) => {
        const s = slider({ label: name, min: mn, max: mx, step: st, value: v, onInput: (val) => { params[name] = val; recompute(); } });
        params[name] = v; return s.root;
      }));
      recompute();
    }

    const recompute = liveRequest(async (signal) => {
      const p = { ...params };
      if (kind.value === "binomial") p.n = Math.round(p.n);
      if (kind.value === "uniform" && p.high <= p.low) p.high = p.low + 0.5;
      const [d, s] = await Promise.all([
        simulate("mathematics", "probability_distribution", { kind: kind.value, params: p, interval: [Math.min(lo.value, hi.value), Math.max(lo.value, hi.value)] }, signal),
        simulate("mathematics", "sample_means", { kind: kind.value, params: p, sample_size: n.value, n_samples: 2000, seed: 7 }, signal),
      ]);
      return { d, s };
    }, {
      delay: 80, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ d, s }) => {
        L.clearError(); res = d;
        out.set("mean", fmt(d.result.mean, 4)); out.set("sd", fmt(d.result.sd, 4)); out.set("p", fmt(d.result.probability, 4));
        clt.set("m", fmt(s.result.mean_of_means, 4)); clt.set("s", fmt(s.result.sd_of_means, 4));
        clt.set("pred", fmt(s.result.clt_sd, 4)); clt.set("skew", fmt(s.result.skewness, 3));
        graph.setSeries([
          { name: "Sample means", color: c1, x: s.histogram.x, y: s.histogram.density, bars: true, alpha: 0.45 },
          { name: "CLT normal curve", color: c2, x: s.clt_curve.x, y: s.clt_curve.density },
        ]);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const xs = res.curve.x, ys = res.curve.density, disc = res.discrete;
      const x0 = xs[0] - (disc ? 1 : 0), x1 = xs[xs.length - 1] + (disc ? 1 : 0), ymax = Math.max(...ys) * 1.15;
      const left = 50, bottom = h - 34, top = 30, right = w - 20;
      const X = (v) => left + ((v - x0) / (x1 - x0)) * (right - left), Y = (v) => bottom - (v / ymax) * (bottom - top);
      const a = Math.min(lo.value, hi.value), b = Math.max(lo.value, hi.value);
      ctx.strokeStyle = "#e3e8ef";
      const ystep = niceStep(ymax, 5);
      for (let v = 0; v <= ymax; v += ystep) { ctx.beginPath(); ctx.moveTo(left, Y(v)); ctx.lineTo(right, Y(v)); ctx.stroke(); label(ctx, fmt(v, 2), left - 6, Y(v), { align: "right", font: "11px system-ui", color: "#4b5868" }); }
      const xstep = niceStep(x1 - x0, 10);
      for (let v = Math.ceil(x0 / xstep) * xstep; v <= x1; v += xstep) label(ctx, fmt(v, 3), X(v), bottom + 14, { align: "center", font: "11px system-ui", color: "#4b5868" });
      if (disc) {
        const bw = Math.max(2, (X(1) - X(0)) * 0.8);
        xs.forEach((x, i) => {
          ctx.fillStyle = x >= a && x <= b ? c1 : "rgba(42,120,214,.25)";
          ctx.fillRect(X(x) - bw / 2, Y(ys[i]), bw, bottom - Y(ys[i]));
        });
      } else {
        ctx.fillStyle = "rgba(42,120,214,.25)"; ctx.beginPath(); ctx.moveTo(X(Math.max(a, x0)), bottom);
        xs.forEach((x, i) => { if (x >= a && x <= b) ctx.lineTo(X(x), Y(ys[i])); });
        ctx.lineTo(X(Math.min(b, x1)), bottom); ctx.closePath(); ctx.fill();
        ctx.strokeStyle = c1; ctx.lineWidth = 2.5; ctx.beginPath(); xs.forEach((x, i) => (i ? ctx.lineTo(X(x), Y(ys[i])) : ctx.moveTo(X(x), Y(ys[i])))); ctx.stroke();
      }
      ctx.strokeStyle = "#39424e"; ctx.beginPath(); ctx.moveTo(left, bottom); ctx.lineTo(right, bottom); ctx.stroke();
      label(ctx, `P(${fmt(a, 3)} ≤ X ≤ ${fmt(b, 3)}) = ${fmt(res.result.probability, 4)}`, left, 16, { font: "bold 13px system-ui" });
      label(ctx, disc ? "probability mass function" : "probability density function", right, 16, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    build();
    return () => { recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
