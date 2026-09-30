// Calculus Grapher: evaluate_function, differentiate and integrate from the engine.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, checkbox, textInput, readouts, el, legend, SERIES, cssVar } from "../core/ui.js";
import { createStage, niceStep, label } from "../core/stage.js";
import { roundRect } from "../core/graph.js";
import { fmt } from "../core/format.js";

const EXAMPLES = [
  "sin(x) + x/3", "x^3 - 3x", "exp(-x^2/2)", "sin(x)/x", "ln(x)", "1/(1 + x^2)", "abs(x) - 2", "x^2 * cos(3x)", "sqrt(4 - x^2)", "tan(x)",
];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let F = null, D = null, area = null, tangent = null, derivText = "";
    let hover = null, draggingX0 = false;

    const expr = textInput({ label: "f(x) =", value: EXAMPLES[0], mono: true, onChange: () => recompute() });
    const example = select({ label: "Examples", value: EXAMPLES[0], options: EXAMPLES.map((e) => ({ value: e, label: e })), onChange: (v) => { expr.set(v); recompute(); } });
    const xmin = slider({ label: "x from", min: -20, max: 0, step: 0.5, value: -8, onInput: () => recompute() });
    const xmax = slider({ label: "x to", min: 0.5, max: 20, step: 0.5, value: 8, onInput: () => recompute() });
    const showD = checkbox({ label: "Show derivative f′(x)", value: true, onChange: () => draw() });
    const showA = checkbox({ label: "Show area ∫ f(x) dx", value: true, onChange: () => recompute() });
    const a = slider({ label: "from a", min: -20, max: 20, step: 0.1, value: -2, onInput: () => recompute() });
    const b = slider({ label: "to b", min: -20, max: 20, step: 0.1, value: 3, onInput: () => recompute() });
    const showT = checkbox({ label: "Show tangent line", value: true, onChange: () => recompute() });
    const x0 = slider({ label: "at x₀", min: -20, max: 20, step: 0.05, value: 1, onInput: () => recompute() });
    const out = readouts([{ key: "fx0", label: "f(x₀)" }, { key: "slope", label: "slope f′(x₀)" }, { key: "area", label: "∫ₐᵇ f(x) dx" }]);
    const derivBox = el("code", { style: "display:block;white-space:pre-wrap;word-break:break-word;font-size:12px;margin-top:6px" }, "");

    L.side.append(
      panel("Function", expr.root, example.root, xmin.root, xmax.root, el("p", { class: "note" }, "Use x, ^ or ** for powers, sin, cos, exp, ln, sqrt, abs, pi, E…")),
      panel("Calculus", showD.root, showT.root, x0.root, showA.root, a.root, b.root),
      panel("Results (from the engine)", out.root, el("div", { class: "note" }, "f′(x) ="), derivBox),
    );
    L.scene.append(el("div", { style: "position:absolute;right:14px;top:12px;background:rgba(255,255,255,.9);padding:4px 8px;border-radius:8px" },
      legend([{ label: "f(x)", color: c1 }, { label: "f′(x)", color: c2, dash: true }, { label: "tangent", color: c3 }])));

    const recompute = liveRequest(async (signal) => {
      const e = expr.value.trim();
      const lo = xmin.value, hi = xmax.value;
      const [f, d] = await Promise.all([
        simulate("mathematics", "evaluate_function", { expression: e, start: lo, stop: hi, n_points: 800 }, signal),
        simulate("mathematics", "differentiate", { expression: e }, signal),
      ]);
      const df = await simulate("mathematics", "evaluate_function", { expression: d.result, start: lo, stop: hi, n_points: 800 }, signal);
      let integral = null, tan = null;
      if (showA.value && a.value !== b.value) {
        integral = await simulate("mathematics", "integrate", { expression: e, lower: Math.min(a.value, b.value), upper: Math.max(a.value, b.value) }, signal)
          .catch((err) => ({ error: err.message }));
      }
      if (showT.value) {
        const eps = 1e-9 * Math.max(1, Math.abs(x0.value));
        const [fv, dv] = await Promise.all([
          simulate("mathematics", "evaluate_function", { expression: e, start: x0.value, stop: x0.value + eps, n_points: 2 }, signal),
          simulate("mathematics", "evaluate_function", { expression: d.result, start: x0.value, stop: x0.value + eps, n_points: 2 }, signal),
        ]);
        tan = { x: x0.value, y: fv.result.y[0], m: dv.result.y[0] };
      }
      return { f, d, df, integral, tan };
    }, {
      delay: 180, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ f, d, df, integral, tan }) => {
        L.clearError();
        F = f.result; D = df.result; derivText = d.result; tangent = tan;
        area = integral && !integral.error ? { lo: Math.min(a.value, b.value), hi: Math.max(a.value, b.value), value: integral.numeric, exact: integral.result } : null;
        derivBox.textContent = derivText;
        out.set("fx0", tan ? fmt(tan.y, 5) : "–"); out.set("slope", tan ? fmt(tan.m, 5) : "–");
        out.set("area", integral ? (integral.error ? "diverges / undefined" : `${fmt(integral.numeric, 6)}${integral.result !== String(integral.numeric) && integral.result.length < 24 ? `  (= ${integral.result})` : ""}`) : "–");
        draw();
      },
    });

    // y-range from robust percentiles so asymptotes don't flatten everything
    function yRange() {
      const ys = F.y.filter((v) => v !== null).sort((p, q) => p - q);
      if (!ys.length) return [-1, 1];
      let lo = ys[Math.floor(ys.length * 0.02)], hi = ys[Math.ceil(ys.length * 0.98) - 1];
      if (showD.value && D) {
        const ds = D.y.filter((v) => v !== null).sort((p, q) => p - q);
        if (ds.length) { lo = Math.min(lo, ds[Math.floor(ds.length * 0.05)]); hi = Math.max(hi, ds[Math.ceil(ds.length * 0.95) - 1]); }
      }
      lo = Math.min(lo, 0); hi = Math.max(hi, 0);
      const pad = (hi - lo || 2) * 0.12;
      return [lo - pad, hi + pad];
    }

    let map = null;
    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!F) return;
      const [ylo, yhi] = yRange();
      const xlo = F.x[0], xhi = F.x[F.x.length - 1];
      const X = (v) => ((v - xlo) / (xhi - xlo)) * w, Y = (v) => h - ((v - ylo) / (yhi - ylo)) * h;
      map = { X, Y, xlo, xhi, ylo, yhi };
      const grid = cssVar("--grid"), ink2 = cssVar("--text-2");
      ctx.lineWidth = 1;
      const xs = niceStep(xhi - xlo, Math.floor(w / 90)), ys = niceStep(yhi - ylo, Math.floor(h / 60));
      for (let v = Math.ceil(xlo / xs) * xs; v <= xhi; v += xs) { ctx.strokeStyle = grid; ctx.beginPath(); ctx.moveTo(X(v), 0); ctx.lineTo(X(v), h); ctx.stroke(); }
      for (let v = Math.ceil(ylo / ys) * ys; v <= yhi; v += ys) { ctx.strokeStyle = grid; ctx.beginPath(); ctx.moveTo(0, Y(v)); ctx.lineTo(w, Y(v)); ctx.stroke(); }
      ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.moveTo(X(0), 0); ctx.lineTo(X(0), h); ctx.stroke();
      for (let v = Math.ceil(xlo / xs) * xs; v <= xhi; v += xs) if (Math.abs(v) > xs / 2) label(ctx, fmt(v, 3), X(v), Math.min(h - 10, Math.max(10, Y(0) + 12)), { align: "center", font: "11px system-ui", color: ink2 });
      for (let v = Math.ceil(ylo / ys) * ys; v <= yhi; v += ys) if (Math.abs(v) > ys / 2) label(ctx, fmt(v, 3), Math.min(w - 30, Math.max(4, X(0) + 6)), Y(v), { font: "11px system-ui", color: ink2 });

      // Area
      if (area) {
        ctx.fillStyle = c1; ctx.globalAlpha = 0.16; ctx.beginPath();
        ctx.moveTo(X(area.lo), Y(0));
        F.x.forEach((x, i) => { if (x >= area.lo && x <= area.hi && F.y[i] !== null) ctx.lineTo(X(x), Y(F.y[i])); });
        ctx.lineTo(X(area.hi), Y(0)); ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1;
        ctx.strokeStyle = c1; ctx.setLineDash([3, 3]);
        for (const x of [area.lo, area.hi]) { ctx.beginPath(); ctx.moveTo(X(x), 0); ctx.lineTo(X(x), h); ctx.stroke(); }
        ctx.setLineDash([]);
      }
      const curve = (S, color, dash) => {
        ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.setLineDash(dash ? [7, 5] : []); ctx.beginPath();
        let pen = false, prev = null;
        S.x.forEach((x, i) => {
          const y = S.y[i];
          if (y === null || (prev !== null && Math.abs(y - prev) > (yhi - ylo) * 3)) { pen = false; prev = y; if (y === null) return; }
          if (pen) ctx.lineTo(X(x), Y(y)); else { ctx.moveTo(X(x), Y(y)); pen = true; }
          prev = y;
        });
        ctx.stroke(); ctx.setLineDash([]);
      };
      if (showD.value && D) curve(D, c2, true);
      curve(F, c1, false);
      if (tangent && tangent.y !== null && tangent.m !== null) {
        ctx.strokeStyle = c3; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(X(xlo), Y(tangent.y + tangent.m * (xlo - tangent.x))); ctx.lineTo(X(xhi), Y(tangent.y + tangent.m * (xhi - tangent.x))); ctx.stroke();
        ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(X(tangent.x), Y(tangent.y), 7, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = c3; ctx.beginPath(); ctx.arc(X(tangent.x), Y(tangent.y), 5, 0, Math.PI * 2); ctx.fill();
      }
      if (area) label(ctx, `area = ${fmt(area.value, 5)}`, X((area.lo + area.hi) / 2), 18, { align: "center", font: "bold 13px system-ui", color: "#1c5cab", halo: "#fff" });
      drawHover(ctx, w, h);
    }

    function nearestY(S, x) {
      const i = Math.round(((x - S.x[0]) / (S.x[S.x.length - 1] - S.x[0])) * (S.x.length - 1));
      return i >= 0 && i < S.y.length ? S.y[i] : null;
    }
    function drawHover(ctx, w, h) {
      if (!hover || !map || draggingX0) return;
      const x = map.xlo + (hover.x / w) * (map.xhi - map.xlo);
      const fy = nearestY(F, x), dy = D ? nearestY(D, x) : null;
      ctx.strokeStyle = cssVar("--text-3"); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(hover.x, 0); ctx.lineTo(hover.x, h); ctx.stroke();
      const lines = [`x = ${fmt(x, 4)}`, `f(x) = ${fy === null ? "undefined" : fmt(fy, 4)}`];
      if (showD.value) lines.push(`f′(x) = ${dy === null ? "undefined" : fmt(dy, 4)}`);
      if (fy !== null) { ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(hover.x, map.Y(fy), 4, 0, Math.PI * 2); ctx.fill(); }
      ctx.font = "12px system-ui";
      const tw = Math.max(...lines.map((l) => ctx.measureText(l).width)) + 16, th = lines.length * 17 + 8;
      let bx = hover.x + 12; if (bx + tw > w) bx = hover.x - 12 - tw;
      const by = Math.min(Math.max(8, hover.y - th / 2), h - th - 8);
      ctx.fillStyle = "rgba(255,255,255,.96)"; ctx.strokeStyle = cssVar("--border");
      roundRect(ctx, bx, by, tw, th, 7); ctx.fill(); ctx.stroke();
      lines.forEach((l, i) => label(ctx, l, bx + 8, by + 13 + i * 17, { font: "12px system-ui" }));
    }

    const c = stage.canvas;
    const worldX = (e) => { const r = c.getBoundingClientRect(); return map.xlo + ((e.clientX - r.left) / r.width) * (map.xhi - map.xlo); };
    c.addEventListener("pointerdown", (e) => {
      if (!map || !tangent) return;
      const r = c.getBoundingClientRect();
      if (Math.hypot(e.clientX - r.left - map.X(tangent.x), e.clientY - r.top - map.Y(tangent.y ?? 0)) < 14) { draggingX0 = true; c.setPointerCapture(e.pointerId); }
    });
    c.addEventListener("pointermove", (e) => {
      const r = c.getBoundingClientRect();
      hover = { x: e.clientX - r.left, y: e.clientY - r.top };
      if (draggingX0 && map) { x0.set(Math.round(worldX(e) * 20) / 20); recompute(); }
      draw();
    });
    c.addEventListener("pointerup", () => { draggingX0 = false; });
    c.addEventListener("pointerleave", () => { hover = null; draw(); });
    L.scene.append(el("div", { class: "scene-hint dark" }, "Drag the green point to move the tangent"));

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
