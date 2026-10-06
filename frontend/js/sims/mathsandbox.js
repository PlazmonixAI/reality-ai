// Maths Sandbox: a graphing notebook. Type any number of lines (functions, equations, inequalities, points,
// parametric and polar curves, sliders, named functions, sums) and see them on one grid. Every curve, region,
// root, turning point, intersection and value comes from the engine (mathematics.sandbox); the browser draws them.
import { simulate, liveRequest } from "../core/api.js";
import { el, SERIES } from "../core/ui.js";
import { fmt } from "../core/format.js";

const EXAMPLES = [
  ["Parabola with sliders", ["a = 1", "b = 0", "c = -2", "y = a x^2 + b x + c"]],
  ["Circle and a line", ["x^2 + y^2 = 16", "y = 0.5x + 1"]],
  ["Where do they meet?", ["y = sin(x)", "y = x/4", "y = cos(x)"]],
  ["Your own function", ["f(x) = x^3 - 4x", "y = f(x)", "y = f(x - 2) + 1", "f(3)"]],
  ["Inequalities", ["y > x^2 - 4", "y < 2 - x"]],
  ["Polar rose", ["k = 4", "r = 4 cos(k theta)"]],
  ["Lissajous curve", ["(6 sin(3t), 5 sin(2t))"]],
  ["Ellipse and hyperbola", ["x^2/16 + y^2/9 = 1", "x^2/4 - y^2 = 1"]],
  ["Points and a line", ["A = (-3, -1)", "B = (4, 3)", "y = (3 - (-1))/(4 - (-3)) (x + 3) - 1"]],
  ["Calculator", ["sqrt(2) + sqrt(8)", "sin(pi/6)", "log10(1000)", "2^64", "e^(I pi)"]],
];
const DASH = [[], [7, 5], [2, 4]];
const KIND_NAME = { root: "root", maximum: "maximum", minimum: "minimum", "y-intercept": "y-intercept", cross: "intersection" };

export default {
  title: "Maths Sandbox",
  mount(root) {
    const colours = SERIES();
    let rows = EXAMPLES[0][1].map((text) => ({ text, hidden: false }));
    let view = { cx: 0, cy: 0, ppu: 40 }; // centre and pixels per unit
    let data = null, hover = null, raf = 0;

    const list = el("div", { class: "msb-list" });
    const status = el("div", { class: "msb-status muted small" }, "");
    const exampleSel = el("select", { class: "msb-select", "aria-label": "Examples", onchange: () => { const ex = EXAMPLES[exampleSel.value]; if (ex) { rows = ex[1].map((text) => ({ text, hidden: false })); renderList(); home(); } exampleSel.value = ""; } },
      el("option", { value: "" }, "Load an example…"), ...EXAMPLES.map(([name], i) => el("option", { value: i }, name)));
    const canvas = el("canvas", { class: "msb-canvas", "aria-label": "Graph" });
    const tip = el("div", { class: "msb-tip", hidden: true });
    const zoomBtns = el("div", { class: "msb-zoom" },
      el("button", { type: "button", title: "Zoom in", "aria-label": "Zoom in", onclick: () => zoom(1.5) }, "+"),
      el("button", { type: "button", title: "Zoom out", "aria-label": "Zoom out", onclick: () => zoom(1 / 1.5) }, "−"),
      el("button", { type: "button", title: "Back to the start view", "aria-label": "Reset view", onclick: () => home() }, "⌂"));
    root.append(el("div", { class: "msb" },
      el("aside", { class: "msb-side" },
        el("div", { class: "msb-head" }, el("h1", {}, "Maths Sandbox"), el("p", { class: "muted small" }, "One line per idea: y = x^2, x^2 + y^2 = 9, y < 2x, A = (1, 2), a = 3, f(x) = …, r = 2cos(3theta), (cos t, sin t), or a sum to work out.")),
        exampleSel, list,
        el("button", { class: "btn small", type: "button", onclick: () => { rows.push({ text: "", hidden: false }); renderList(rows.length - 1); } }, "+ Add a line"),
        status),
      el("div", { class: "msb-stage" }, canvas, tip, zoomBtns)));

    // ---------------------------------------------------------------- the list of lines
    const colourOf = (i) => colours[i % 3];
    const dashOf = (i) => DASH[Math.floor(i / 3) % 3];
    function renderList(focus = -1) {
      list.replaceChildren(...rows.map((r, i) => {
        const input = el("input", { class: "msb-input", value: r.text, spellcheck: "false", autocomplete: "off", "aria-label": `Line ${i + 1}`, placeholder: "type maths here" });
        input.addEventListener("input", () => { r.text = input.value; recompute(); });
        input.addEventListener("keydown", (e) => {
          if (e.key === "Enter") { e.preventDefault(); rows.splice(i + 1, 0, { text: "", hidden: false }); renderList(i + 1); }
          if (e.key === "Backspace" && !input.value && rows.length > 1) { e.preventDefault(); rows.splice(i, 1); renderList(Math.max(0, i - 1)); recompute(); }
        });
        const swatch = el("button", { type: "button", class: `msb-swatch${r.hidden ? " off" : ""}`, title: r.hidden ? "Show" : "Hide", "aria-label": r.hidden ? "Show line" : "Hide line", style: `--c:${colourOf(i)}`,
          onclick: () => { r.hidden = !r.hidden; renderList(); } });
        if (dashOf(i).length) swatch.classList.add(dashOf(i)[0] > 3 ? "dashed" : "dotted");
        const row = el("div", { class: "msb-row", "data-i": i }, swatch, input,
          el("button", { type: "button", class: "msb-del", title: "Remove", "aria-label": "Remove line", onclick: () => { rows.splice(i, 1); if (!rows.length) rows.push({ text: "", hidden: false }); renderList(); recompute(); } }, "×"),
          el("div", { class: "msb-out" }));
        if (i === focus) requestAnimationFrame(() => input.focus());
        return row;
      }));
      fillOutputs();
    }
    function fillOutputs() {
      if (!data) return;
      for (const it of data.items) {
        const row = list.querySelector(`.msb-row[data-i="${it.index}"]`);
        if (!row || rows[it.index]?.text.trim() !== it.text) continue;
        const out = row.querySelector(".msb-out"); out.replaceChildren(); row.classList.toggle("bad", it.kind === "error");
        if (it.kind === "error") out.append(el("span", { class: "msb-err" }, it.error));
        else if (it.kind === "value") out.append(el("b", {}, "= ", it.value === null ? `${fmt(it.imag, 6)} i` : fmt(it.value, 10)), it.exact && it.exact !== String(it.value) && !/\./.test(it.exact) ? el("span", { class: "muted" }, `  (exactly ${it.exact})`) : "");
        else if (it.kind === "slider") out.append(sliderFor(it));
        else if (it.kind === "region") out.append(el("span", { class: "muted" }, `shaded: ${fmt(it.area_fraction * 100, 3)}% of the view`));
        else if (it.kind === "point") out.append(el("span", { class: "muted" }, `(${fmt(it.x, 6)}, ${fmt(it.y, 6)})`));
        else if (it.points?.length) {
          const g = (k) => it.points.filter((p) => p.kind === k);
          const say = [["root", "crosses the x-axis at x ="], ["minimum", "lowest point"], ["maximum", "highest point"]].map(([k, w]) => {
            const ps = g(k); if (!ps.length) return null;
            return k === "root" ? `${w} ${ps.slice(0, 4).map((p) => fmt(p.x, 5)).join(", ")}${ps.length > 4 ? "…" : ""}` : `${w}${ps.length > 1 ? "s" : ""} ${ps.slice(0, 2).map((p) => `(${fmt(p.x, 4)}, ${fmt(p.y, 4)})`).join(", ")}${ps.length > 2 ? "…" : ""}`;
          }).filter(Boolean);
          out.append(el("span", { class: "muted" }, say.join(" · ") || "no roots or turning points in view"));
        }
      }
    }
    function sliderFor(it) {
      const v = it.value, span = Math.max(10, Math.abs(v) * 2);
      const lo = v >= 0 && v <= 10 ? -10 : Math.floor(v - span), hi = v >= -10 && v <= 0 ? 10 : Math.ceil(v + span);
      const r = el("input", { type: "range", min: Math.min(lo, -10), max: Math.max(hi, 10), step: "any", value: v, class: "msb-range", "aria-label": `${it.name} slider` });
      const val = el("output", {}, fmt(v, 4));
      r.addEventListener("input", () => {
        const nv = Math.round(Number(r.value) * 100) / 100; val.textContent = fmt(nv, 4);
        rows[it.index].text = `${it.name} = ${nv}`;
        const inp = list.querySelector(`.msb-row[data-i="${it.index}"] .msb-input`); if (inp) inp.value = rows[it.index].text;
        recompute();
      });
      return el("div", { class: "msb-slider" }, el("span", {}, it.name), r, val);
    }

    // ---------------------------------------------------------------- the engine
    const windowOf = () => {
      const W = canvas.clientWidth || 800, H = canvas.clientHeight || 600;
      return { x_min: view.cx - W / 2 / view.ppu, x_max: view.cx + W / 2 / view.ppu, y_min: view.cy - H / 2 / view.ppu, y_max: view.cy + H / 2 / view.ppu };
    };
    const recompute = liveRequest(async (signal) => {
      const w = windowOf(), pad = (w.x_max - w.x_min) * 0.25, padY = (w.y_max - w.y_min) * 0.25; // a margin so small pans redraw at once
      const r = await simulate("mathematics", "sandbox", { entries: rows.map((r) => r.text), x_min: w.x_min - pad, x_max: w.x_max + pad, y_min: w.y_min - padY, y_max: w.y_max + padY, t_min: 0, t_max: 2 * Math.PI }, signal);
      return r.result;
    }, { delay: 90, onResult: (res) => { data = res; status.textContent = ""; fillOutputs(); }, onError: (e) => { status.textContent = e.message; } });

    // ---------------------------------------------------------------- drawing
    const toPx = (x, y) => [canvas.clientWidth / 2 + (x - view.cx) * view.ppu, canvas.clientHeight / 2 - (y - view.cy) * view.ppu];
    const niceStep = (raw) => { const p = 10 ** Math.floor(Math.log10(raw)), m = raw / p; return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p; };
    function draw() {
      raf = requestAnimationFrame(draw);
      const W = canvas.clientWidth, H = canvas.clientHeight; if (!W || !H) return;
      const dpr = Math.min(2, devicePixelRatio);
      if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
      const ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, W, H);
      const w = windowOf(), step = niceStep(80 / view.ppu), minor = step / 5;
      ctx.lineWidth = 1;
      for (const [s, c] of [[minor, "#f1f4f8"], [step, "#dfe5ee"]]) {
        ctx.strokeStyle = c; ctx.beginPath();
        for (let x = Math.ceil(w.x_min / s) * s; x <= w.x_max; x += s) { const [px] = toPx(x, 0); ctx.moveTo(Math.round(px) + 0.5, 0); ctx.lineTo(Math.round(px) + 0.5, H); }
        for (let y = Math.ceil(w.y_min / s) * s; y <= w.y_max; y += s) { const [, py] = toPx(0, y); ctx.moveTo(0, Math.round(py) + 0.5); ctx.lineTo(W, Math.round(py) + 0.5); }
        ctx.stroke();
      }
      const [ox, oy] = toPx(0, 0);
      ctx.strokeStyle = "#0B1526"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(0, oy); ctx.lineTo(W, oy); ctx.moveTo(ox, 0); ctx.lineTo(ox, H); ctx.stroke();
      ctx.fillStyle = "#5b6678"; ctx.font = "11px Plex, system-ui";
      const lx = Math.min(Math.max(ox, 4), W - 40), ly = Math.min(Math.max(oy, 4), H - 16);
      ctx.textAlign = "center"; ctx.textBaseline = "top";
      for (let x = Math.ceil(w.x_min / step) * step; x <= w.x_max; x += step) if (Math.abs(x) > step / 2) { const [px] = toPx(x, 0); ctx.fillText(fmt(x, 4), px, ly + 3); }
      ctx.textAlign = "left"; ctx.textBaseline = "middle";
      for (let y = Math.ceil(w.y_min / step) * step; y <= w.y_max; y += step) if (Math.abs(y) > step / 2) { const [, py] = toPx(0, y); ctx.fillText(fmt(y, 4), lx + 4, py); }
      if (!data) return;
      const marks = [];
      for (const it of data.items) {
        if (rows[it.index]?.hidden) continue;
        const col = colourOf(it.index); ctx.strokeStyle = col; ctx.fillStyle = col; ctx.setLineDash(dashOf(it.index)); ctx.lineWidth = 2.5;
        if (it.kind === "curve" || it.kind === "curve_y" || it.kind === "parametric") {
          ctx.beginPath(); let pen = false;
          for (let k = 0; k < it.x.length; k++) {
            const x = it.x[k], y = it.y[k];
            if (x === null || y === null) { pen = false; continue; }
            const [px, py] = toPx(x, y);
            if (Math.abs(py) > 1e5 || Math.abs(px) > 1e5) { pen = false; continue; }
            if (pen) ctx.lineTo(px, py); else ctx.moveTo(px, py); pen = true;
          }
          ctx.stroke();
          for (const p of it.points || []) marks.push({ ...p, col });
        } else if (it.kind === "implicit" || it.kind === "region") {
          if (it.kind === "region") {
            const W0 = data.window, cw = (W0[1] - W0[0]) / it.nx, ch = (W0[3] - W0[2]) / it.ny;
            ctx.globalAlpha = 0.16;
            it.cells.forEach((row, j) => { let run = -1; for (let i = 0; i <= row.length; i++) { const on = row[i] === "1";
              if (on && run < 0) run = i; if (!on && run >= 0) { const [x0, y0] = toPx(W0[0] + run * cw, W0[2] + (j + 1) * ch), [x1, y1] = toPx(W0[0] + i * cw, W0[2] + j * ch); ctx.fillRect(x0, y0, x1 - x0 + 0.5, y1 - y0 + 0.5); run = -1; } } });
            ctx.globalAlpha = 1; if (it.strict) ctx.setLineDash([6, 5]);
          }
          ctx.beginPath();
          for (const [x1, y1, x2, y2] of it.segments) { const [a, b] = toPx(x1, y1), [c, d] = toPx(x2, y2); ctx.moveTo(a, b); ctx.lineTo(c, d); }
          ctx.stroke();
        } else if (it.kind === "point") {
          const [px, py] = toPx(it.x, it.y); ctx.setLineDash([]); ctx.beginPath(); ctx.arc(px, py, 5, 0, 6.3); ctx.fill();
          ctx.fillStyle = "#0B1526"; ctx.font = "600 12px Plex, system-ui"; ctx.textAlign = "left"; ctx.textBaseline = "bottom";
          ctx.fillText(`${it.label ? it.label + " " : ""}(${fmt(it.x, 4)}, ${fmt(it.y, 4)})`, px + 7, py - 4);
          marks.push({ x: it.x, y: it.y, kind: "point", col, label: it.label });
        }
        ctx.setLineDash([]);
      }
      for (const c of data.intersections) marks.push({ ...c, kind: "cross", col: "#5b6678" });
      // points of interest: small grey rings; the hovered one gets a label
      ctx.lineWidth = 1.5;
      for (const m of marks) {
        if (m.kind === "point") continue;
        const [px, py] = toPx(m.x, m.y); if (px < -10 || py < -10 || px > W + 10 || py > H + 10) continue;
        ctx.strokeStyle = "#8a94a6"; ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(px, py, 3.5, 0, 6.3); ctx.fill(); ctx.stroke();
      }
      data._marks = marks;
      if (hover) { ctx.strokeStyle = hover.col || "#0B1526"; ctx.lineWidth = 2; const [px, py] = toPx(hover.x, hover.y); ctx.beginPath(); ctx.arc(px, py, 6, 0, 6.3); ctx.stroke(); }
    }

    // ---------------------------------------------------------------- pan, zoom and hover
    function zoom(f, px = canvas.clientWidth / 2, py = canvas.clientHeight / 2) {
      const before = [view.cx + (px - canvas.clientWidth / 2) / view.ppu, view.cy - (py - canvas.clientHeight / 2) / view.ppu];
      view.ppu = Math.min(1e7, Math.max(1e-6, view.ppu * f));
      view.cx = before[0] - (px - canvas.clientWidth / 2) / view.ppu; view.cy = before[1] + (py - canvas.clientHeight / 2) / view.ppu;
      recompute();
    }
    function home() { view = { cx: 0, cy: 0, ppu: Math.max(20, Math.min(canvas.clientWidth, canvas.clientHeight) / 20) || 40 }; recompute(); }
    const pointers = new Map(); let pan = null, pinch = null;
    const loc = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    canvas.addEventListener("pointerdown", (e) => { canvas.setPointerCapture(e.pointerId); pointers.set(e.pointerId, loc(e));
      if (pointers.size === 1) pan = { p: loc(e), c: [view.cx, view.cy] };
      if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), ppu: view.ppu }; pan = null; } });
    canvas.addEventListener("pointermove", (e) => {
      const p = loc(e);
      if (pointers.has(e.pointerId)) pointers.set(e.pointerId, p);
      if (pinch && pointers.size === 2) { const [a, b] = [...pointers.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); view.ppu = Math.max(1e-6, pinch.ppu * d / pinch.d); recompute(); return; }
      if (pan) { view.cx = pan.c[0] - (p[0] - pan.p[0]) / view.ppu; view.cy = pan.c[1] + (p[1] - pan.p[1]) / view.ppu; recompute(); tip.hidden = true; return; }
      hoverAt(p);
    });
    const up = (e) => { pointers.delete(e.pointerId); if (pointers.size < 2) pinch = null; if (!pointers.size) pan = null; };
    canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up);
    canvas.addEventListener("pointerleave", () => { hover = null; tip.hidden = true; });
    canvas.tabIndex = 0; canvas.title = "Drag or arrow keys to move, scroll, pinch or + − to zoom, 0 to reset";
    canvas.addEventListener("keydown", (e) => {
      const st = 60 / view.ppu, act = { ArrowLeft: () => { view.cx -= st; }, ArrowRight: () => { view.cx += st; }, ArrowUp: () => { view.cy += st; }, ArrowDown: () => { view.cy -= st; },
        "+": () => zoom(1.25), "=": () => zoom(1.25), "-": () => zoom(0.8), 0: () => home() }[e.key];
      if (act) { e.preventDefault(); act(); recompute(); }
    });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); const [px, py] = loc(e); zoom(Math.exp(-e.deltaY * 0.0015), px, py); }, { passive: false });
    function hoverAt([px, py]) {
      hover = null;
      let best = 10;
      for (const m of data?._marks || []) { const [x, y] = toPx(m.x, m.y), d = Math.hypot(x - px, y - py); if (d < best) { best = d; hover = m; } }
      if (!hover && data) for (const it of data.items) { // otherwise the nearest point on a curve
        if (rows[it.index]?.hidden || !it.x?.length || !["curve", "curve_y", "parametric"].includes(it.kind)) continue;
        for (let k = 0; k < it.x.length; k += 1) { if (it.x[k] === null || it.y[k] === null) continue; const [x, y] = toPx(it.x[k], it.y[k]), d = Math.hypot(x - px, y - py); if (d < best) { best = d; hover = { x: it.x[k], y: it.y[k], kind: "on", col: colourOf(it.index), line: it.index }; } }
      }
      if (!hover) { tip.hidden = true; return; }
      const [x, y] = toPx(hover.x, hover.y);
      tip.hidden = false; tip.style.left = `${x + 12}px`; tip.style.top = `${y - 12}px`; tip.style.borderColor = hover.col;
      tip.textContent = `${hover.kind === "on" ? `line ${hover.line + 1}` : hover.kind === "point" ? hover.label || "point" : KIND_NAME[hover.kind] || hover.kind}  (${fmt(hover.x, 6)}, ${fmt(hover.y, 6)})`;
    }

    const ro = new ResizeObserver(() => recompute()); ro.observe(canvas);
    renderList(); requestAnimationFrame(() => home()); draw();
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  },
};
