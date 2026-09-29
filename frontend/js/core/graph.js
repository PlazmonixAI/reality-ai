// Line / bar graph on canvas with nice ticks, a playback cursor and a hover crosshair + tooltip.
import { createStage, niceStep, label } from "./stage.js";
import { el, legend as legendEl, cssVar } from "./ui.js";
import { fmt } from "./format.js";

export class LineGraph {
  /**
   * @param parent container element
   * @param opts {title, xLabel, yLabel, height, includeZero, xFormat, yFormat, logY}
   */
  constructor(parent, opts = {}) {
    this.opts = { height: 170, includeZero: false, xFormat: (v) => fmt(v, 3), yFormat: (v) => fmt(v, 3), ...opts };
    this.series = [];
    this.cursorX = null;
    this.hover = null;
    this.legendSlot = el("div");
    const canvasBox = el("div", { class: "graph-canvas", style: `height:${this.opts.height}px` });
    this.root = el("div", { class: "graph-card" },
      el("div", { class: "graph-head" }, el("span", { class: "graph-title" }, this.opts.title || ""), this.legendSlot),
      canvasBox);
    parent.append(this.root);
    this.stage = createStage(canvasBox, { onResize: () => this.draw() });
    const c = this.stage.canvas;
    c.addEventListener("pointermove", (e) => {
      const r = c.getBoundingClientRect();
      this.hover = { x: e.clientX - r.left, y: e.clientY - r.top };
      this.draw();
    });
    c.addEventListener("pointerleave", () => { this.hover = null; this.draw(); });
  }

  /** series: [{name, color, x: [], y: [], dash, bars, width}] */
  setSeries(series) {
    this.series = series;
    this.legendSlot.replaceChildren(series.length >= 2
      ? legendEl(series.map((s) => ({ label: s.name, color: s.color, dash: !!s.dash })))
      : "");
    this.draw();
  }

  setCursor(x) { this.cursorX = x; this.draw(); }

  bounds() {
    let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
    for (const s of this.series) {
      for (let i = 0; i < s.x.length; i++) {
        const y = s.y[i];
        if (y === null || !Number.isFinite(y)) continue;
        xmin = Math.min(xmin, s.x[i]); xmax = Math.max(xmax, s.x[i]);
        ymin = Math.min(ymin, y); ymax = Math.max(ymax, y);
      }
    }
    if (this.opts.xRange) [xmin, xmax] = this.opts.xRange;
    if (this.opts.yRange) [ymin, ymax] = this.opts.yRange;
    if (!Number.isFinite(xmin)) return null;
    if (this.opts.includeZero) { ymin = Math.min(ymin, 0); ymax = Math.max(ymax, 0); }
    if (ymax - ymin < 1e-12 * Math.max(1, Math.abs(ymax))) { ymin -= 1; ymax += 1; }
    const pad = (ymax - ymin) * 0.08;
    return { xmin, xmax: xmax > xmin ? xmax : xmin + 1, ymin: this.opts.yRange ? ymin : ymin - (ymin === 0 ? 0 : pad), ymax: this.opts.yRange ? ymax : ymax + pad };
  }

  draw() {
    const { ctx, width: w, height: h } = this.stage;
    if (!w || !h) return;
    ctx.clearRect(0, 0, w, h);
    const b = this.bounds();
    const text2 = cssVar("--text-2"), text3 = cssVar("--text-3"), grid = cssVar("--grid");
    if (!b) { label(ctx, "No data", w / 2, h / 2, { color: text3, align: "center" }); return; }
    const left = 58, right = 12, top = 8, bottom = 30;
    const pw = w - left - right, ph = h - top - bottom;
    const X = (v) => left + ((v - b.xmin) / (b.xmax - b.xmin)) * pw;
    const Y = (v) => top + (1 - (v - b.ymin) / (b.ymax - b.ymin)) * ph;
    this._map = { X, Y, left, right, top, bottom, b, pw, ph };

    ctx.font = "11px system-ui";
    const ys = niceStep(b.ymax - b.ymin, Math.max(2, Math.floor(ph / 34)));
    for (let v = Math.ceil(b.ymin / ys) * ys; v <= b.ymax + 1e-9 * ys; v += ys) {
      const y = Y(v);
      ctx.strokeStyle = Math.abs(v) < ys * 1e-6 ? text3 : grid; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(w - right, y); ctx.stroke();
      label(ctx, this.opts.yFormat(Math.abs(v) < ys * 1e-6 ? 0 : v), left - 6, y, { color: text2, align: "right", font: "11px system-ui" });
    }
    const xs = niceStep(b.xmax - b.xmin, Math.max(2, Math.floor(pw / 80)));
    for (let v = Math.ceil(b.xmin / xs) * xs; v <= b.xmax + 1e-9 * xs; v += xs) {
      const x = X(v);
      ctx.strokeStyle = grid; ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + ph); ctx.stroke();
      label(ctx, this.opts.xFormat(Math.abs(v) < xs * 1e-6 ? 0 : v), x, top + ph + 12, { color: text2, align: "center", font: "11px system-ui" });
    }
    if (this.opts.xLabel) label(ctx, this.opts.xLabel, left + pw, h - 4, { color: text3, align: "right", baseline: "bottom", font: "11px system-ui" });
    if (this.opts.yLabel) {
      ctx.save(); ctx.translate(11, top + ph / 2); ctx.rotate(-Math.PI / 2);
      label(ctx, this.opts.yLabel, 0, 0, { color: text3, align: "center", font: "11px system-ui" });
      ctx.restore();
    }

    ctx.save();
    ctx.beginPath(); ctx.rect(left, top, pw, ph); ctx.clip();
    for (const s of this.series) {
      ctx.strokeStyle = s.color; ctx.fillStyle = s.color;
      if (s.bars) {
        const n = s.x.length;
        // Bar width from the smallest gap between x values (x need not be sorted)
        const xs = [...s.x].sort((p, q) => p - q);
        let gap = Infinity;
        for (let i = 1; i < n; i++) if (xs[i] > xs[i - 1]) gap = Math.min(gap, X(xs[i]) - X(xs[i - 1]));
        const bw = Number.isFinite(gap) ? Math.max(1, Math.min(gap - 2, 40)) : 8;
        for (let i = 0; i < n; i++) {
          if (s.y[i] === null) continue;
          const x = X(s.x[i]) - bw / 2, y0 = Y(Math.max(b.ymin, 0)), y1 = Y(s.y[i]);
          ctx.globalAlpha = s.alpha ?? 0.55;
          ctx.fillRect(x, Math.min(y0, y1), bw, Math.abs(y1 - y0));
        }
        ctx.globalAlpha = 1;
        continue;
      }
      ctx.lineWidth = s.width ?? 2; ctx.lineJoin = "round";
      ctx.setLineDash(s.dash ? [6, 4] : []);
      ctx.beginPath();
      let pen = false;
      for (let i = 0; i < s.x.length; i++) {
        const y = s.y[i];
        if (y === null || !Number.isFinite(y)) { pen = false; continue; }
        const px = X(s.x[i]), py = Y(y);
        if (pen) ctx.lineTo(px, py); else { ctx.moveTo(px, py); pen = true; }
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();

    if (this.cursorX !== null && this.cursorX >= b.xmin && this.cursorX <= b.xmax) {
      const cx = X(this.cursorX);
      ctx.strokeStyle = text2; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, top + ph); ctx.stroke(); ctx.setLineDash([]);
      for (const s of this.series) {
        if (s.bars) continue;
        const y = interp(s.x, s.y, this.cursorX);
        if (y === null) continue;
        dot(ctx, cx, Y(y), s.color);
      }
    }
    this.drawHover(ctx, w, text2);
  }

  drawHover(ctx, w, text2) {
    if (!this.hover || !this._map) return;
    const { X, Y, left, top, pw, ph, b } = this._map;
    const { x: hx, y: hy } = this.hover;
    if (hx < left || hx > left + pw || hy < top || hy > top + ph) return;
    const xv = b.xmin + ((hx - left) / pw) * (b.xmax - b.xmin);
    ctx.strokeStyle = text2; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(hx, top); ctx.lineTo(hx, top + ph); ctx.stroke();
    const lines = [`${this.opts.xLabel ? this.opts.xLabel.split(" (")[0] : "x"} = ${this.opts.xFormat(xv)}`];
    for (const s of this.series) {
      const y = s.bars ? nearest(s.x, s.y, xv) : interp(s.x, s.y, xv);
      if (y === null) continue;
      if (!s.bars) dot(ctx, hx, Y(y), s.color);
      lines.push([s.color, `${s.name}: ${this.opts.yFormat(y)}`]);
    }
    ctx.font = "12px system-ui";
    const tw = Math.max(...lines.map((l) => ctx.measureText(typeof l === "string" ? l : l[1]).width)) + 28;
    const th = lines.length * 17 + 8;
    let bx = hx + 12; if (bx + tw > w - 4) bx = hx - 12 - tw;
    const by = Math.max(top, Math.min(hy - th / 2, top + ph - th));
    ctx.fillStyle = "rgba(255,255,255,.96)"; ctx.strokeStyle = cssVar("--border");
    roundRect(ctx, bx, by, tw, th, 7); ctx.fill(); ctx.stroke();
    lines.forEach((l, i) => {
      const y = by + 13 + i * 17;
      if (typeof l === "string") { label(ctx, l, bx + 8, y, { color: cssVar("--text-2"), font: "12px system-ui" }); return; }
      ctx.fillStyle = l[0]; ctx.fillRect(bx + 8, y - 2, 10, 4);
      label(ctx, l[1], bx + 22, y, { color: cssVar("--text"), font: "12px system-ui" });
    });
  }

  destroy() { this.stage.destroy(); }
}

function dot(ctx, x, y, color) {
  ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
}

export function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

function interp(xs, ys, x) {
  const n = xs.length;
  if (!n || x < xs[0] || x > xs[n - 1]) return null;
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  const a = ys[lo], c = ys[hi];
  if (a === null || c === null) return null;
  return xs[hi] === xs[lo] ? a : a + (c - a) * (x - xs[lo]) / (xs[hi] - xs[lo]);
}

function nearest(xs, ys, x) {
  let best = null, dist = Infinity;
  for (let i = 0; i < xs.length; i++) { const d = Math.abs(xs[i] - x); if (d < dist) { dist = d; best = ys[i]; } }
  return best;
}
