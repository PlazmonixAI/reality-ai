// Equation Lab: shows what teach.explore built from an equation (proof, solutions, graph, curve, live formula,
// balanced reaction, or the reason it cannot hold). Every number and every point comes from the engine.
import { el, slider, SERIES } from "../core/ui.js";
import { simulate, liveRequest } from "../core/api.js";
import { LineGraph } from "../core/graph.js";
import { createStage, niceStep, label } from "../core/stage.js";
import { fmt } from "../core/format.js";

/** Does this text look like mathematics or a reaction rather than a topic name? */
export function looksLikeEquation(text) {
  return /[=→]|->|\b(sin|cos|tan|log|ln|sqrt|exp)\b|\^|[²³√π]/.test(text) || /^[\d\s+\-*/().xyz^]+$/i.test(text.trim());
}

/** Mount an Equation Lab card. onWrite(text) puts a line on the whiteboard (optional). Returns {root, run(text), destroy()}. */
export function equationLab({ onWrite } = {}) {
  const root = el("div", { class: "eqlab", hidden: true });
  let text = "", values = {}, graph = null, plane = null;
  const call = liveRequest((signal) => simulate("teach", "explore", { equation: text, values }, signal), {
    onResult: (r) => render(r.result),
    onError: (err) => { root.hidden = false; root.replaceChildren(el("p", { class: "eqlab-verdict bad" }, err.message)); },
    delay: 80,
  });

  function run(t, vals = {}) { text = t; values = { ...vals }; root.hidden = false; call(); }

  function cleanup() { graph?.destroy(); graph = null; plane?.destroy(); plane = null; }

  function render(r) {
    cleanup();
    const head = el("div", { class: "eqlab-head" },
      el("span", { class: "eqlab-tag" }, "Equation Lab"),
      r.read_as ? el("span", { class: "eqlab-read" }, r.read_as) : "");
    const verdict = el("p", { class: `eqlab-verdict ${r.valid ? "ok" : "bad"}` }, r.verdict);
    const parts = [head, verdict];
    if (r.kind === "chemical" && r.balanced) parts.push(el("p", { class: "eqlab-balanced" }, r.balanced));
    if (r.solutions?.length) parts.push(el("div", { class: "eqlab-sols" }, r.solutions.map((s) => el("span", { class: "chip" }, s))));
    if (r.params?.length) {
      const box = el("div", { class: "eqlab-params" });
      for (const p of r.params) {
        box.append(slider({ label: p.label, min: p.min, max: p.max, step: "any", value: p.value, digits: 4,
          onInput: (v) => { values[p.name] = v; call(); } }).root);
      }
      parts.push(box);
    }
    const plotBox = el("div", { class: "eqlab-plot" });
    parts.push(plotBox);
    if (r.steps?.length) {
      parts.push(el("ol", { class: "eqlab-steps" }, r.steps.map((s) => el("li", {}, s))));
      if (onWrite) parts.push(el("button", { type: "button", class: "btn small", onclick: () => { if (r.read_as) onWrite(r.read_as); r.steps.forEach((s) => onWrite(s)); } }, "Write the working on the board"));
    }
    if (r.species?.length) parts.push(el("p", { class: "muted small" }, "Molar masses: " + r.species.map((s) => `${s.species} ${fmt(s.molar_mass_g_mol, 5)} g/mol`).join(", ")));
    root.replaceChildren(...parts);

    const colors = SERIES();
    if (r.plot) {
      graph = new LineGraph(plotBox, { height: 200, xLabel: r.plot.x_label, title: r.kind === "formula" ? `${r.subject} against ${r.plot.x_label}` : "" });
      graph.setSeries(r.plot.series.slice(0, 3).map((s, k) => ({ name: s.name, color: colors[k], x: r.plot.x, y: s.y, dash: k === 1 && r.kind === "function" })));
      if (r.kind === "formula" && r.plot.marks?.length) graph.setCursor(r.plot.marks[0].x);
    } else if (r.segments || r.contours) {
      plane = curvePlane(plotBox, r, colors);
    }
  }

  return { root, run, destroy: () => { call.cancel(); cleanup(); } };
}

/** x-y plane with the engine's curve segments (or contour lines), axes, ticks and a hover read-out. */
function curvePlane(parent, r, colors) {
  const box = el("div", { class: "graph-card" }, el("div", { class: "graph-head" }, el("span", { class: "graph-title" },
    r.kind === "surface" ? "Contour lines of z (darker: higher)" : "Points where the equation holds")));
  const canvasBox = el("div", { class: "graph-canvas", style: "height:280px" });
  box.append(canvasBox);
  parent.append(box);
  let hover = null;
  const stage = createStage(canvasBox, { onResize: () => draw() });
  stage.canvas.addEventListener("pointermove", (e) => { const b = stage.canvas.getBoundingClientRect(); hover = { x: e.clientX - b.left, y: e.clientY - b.top }; draw(); });
  stage.canvas.addEventListener("pointerleave", () => { hover = null; draw(); });
  function draw() {
    const { ctx, width: w, height: h } = stage;
    if (!w) return;
    let [lo, hi] = r.range;
    if (r.segments?.length) {  // zoom to the curve, with a margin, never past the computed range
      const m = Math.max(...r.segments.flat().map(Math.abs));
      const fit = m * 1.25;
      if (fit < hi) { lo = -fit; hi = fit; }
    }
    const s = Math.min(w, h) / (hi - lo) * 0.92, cx = w / 2, cy = h / 2;
    const X = (x) => cx + x * s, Y = (y) => cy - y * s;
    ctx.clearRect(0, 0, w, h);
    const ink = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim() || "#8a94a6";
    ctx.strokeStyle = "rgba(128,140,160,.18)"; ctx.lineWidth = 1;
    const step = niceStep(hi - lo, 8);
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) {
      ctx.beginPath(); ctx.moveTo(X(v), Y(lo)); ctx.lineTo(X(v), Y(hi)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(X(lo), Y(v)); ctx.lineTo(X(hi), Y(v)); ctx.stroke();
      if (Math.abs(v) > 1e-9) { label(ctx, fmt(v, 3), X(v), cy + 12, { align: "center", color: ink, font: "10px system-ui" }); label(ctx, fmt(v, 3), cx + 4, Y(v), { color: ink, font: "10px system-ui" }); }
    }
    ctx.strokeStyle = "rgba(128,140,160,.6)"; ctx.beginPath(); ctx.moveTo(X(lo), cy); ctx.lineTo(X(hi), cy); ctx.moveTo(cx, Y(lo)); ctx.lineTo(cx, Y(hi)); ctx.stroke();
    label(ctx, "x", X(hi) - 10, cy - 8, { color: ink, font: "11px system-ui" }); label(ctx, "y", cx + 8, Y(hi) + 10, { color: ink, font: "11px system-ui" });
    const sets = r.contours ? r.contours.map((c, k, all) => ({ segs: c.segments, alpha: 0.25 + 0.75 * k / Math.max(1, all.length - 1) })) : [{ segs: r.segments, alpha: 1 }];
    ctx.lineWidth = 2.2; ctx.lineCap = "round";
    for (const set of sets) {
      ctx.strokeStyle = colors[0]; ctx.globalAlpha = set.alpha; ctx.beginPath();
      for (const [x0, y0, x1, y1] of set.segs) { ctx.moveTo(X(x0), Y(y0)); ctx.lineTo(X(x1), Y(y1)); }
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    if (hover) {
      const x = (hover.x - cx) / s, y = (cy - hover.y) / s;
      label(ctx, `x = ${fmt(x, 3)}, y = ${fmt(y, 3)}`, 10, 16, { color: ink, font: "12px system-ui" });
    }
  }
  draw();
  return { destroy: () => stage.destroy() };
}
