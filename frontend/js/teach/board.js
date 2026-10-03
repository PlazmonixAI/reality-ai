// ASM Teach whiteboard: pen, highlighter, eraser, a plain, grid, lined or dotted board, typed equations, several pages and undo. Coordinates are stored as
// fractions of the board so a lesson looks the same on a laptop and on the classroom projector.
import { el } from "../core/ui.js";

const COLORS = [["Ink", "#0B1526"], ["Ember", "#FF5B2E"], ["Blue", "#2a78d6"], ["Green", "#1baf7a"]];
const SIZES = [["Fine", 2], ["Medium", 4], ["Bold", 8]];
const PAPERS = [["plain", "Plain"], ["grid", "Grid"], ["lines", "Lines"], ["dots", "Dots"]];
const PAPER_KEY = "asmteach.board.paper";
const savedPaper = () => { try { return localStorage.getItem(PAPER_KEY) || "grid"; } catch { return "grid"; } };

export function createBoard({ onEquation, transparent: overlay = false } = {}) {
  let transparent = overlay;
  let pages = [{ strokes: [], texts: [] }], page = 0, tool = "pen", color = COLORS[0][1], size = 4, paper = savedPaper();
  const undo = [];
  let drawing = null;

  const canvas = el("canvas", { class: "board-canvas", "aria-label": "Whiteboard" });
  const ctx = canvas.getContext("2d");
  const pageLabel = el("span", { class: "board-page" });
  const eqInput = el("input", { class: "board-eq", type: "text", placeholder: "Write an equation, e.g. v = u + at", spellcheck: "false", "aria-label": "Write an equation on the board" });
  const toolBtn = (id, label, title) => el("button", { type: "button", class: "board-tool", "data-tool": id, title, onclick: () => setTool(id) }, label);
  const tools = [toolBtn("pen", "Pen", "Pen (P)"), toolBtn("marker", "Highlight", "Highlighter (H)"), toolBtn("eraser", "Eraser", "Eraser (E)")];
  const swatches = COLORS.map(([name, c]) => el("button", { type: "button", class: "board-swatch", title: name, "aria-label": `${name} colour`, style: `background:${c}`, onclick: () => { color = c; if (tool === "eraser") setTool("pen"); sync(); } }));
  const sizeSel = el("select", { class: "board-size", "aria-label": "Pen size", onchange: (e) => { size = Number(e.target.value); } }, SIZES.map(([n, v]) => el("option", { value: v, selected: v === size }, n)));
  const paperBtns = PAPERS.map(([id, name]) => el("button", { type: "button", class: "board-tool board-paper", "data-paper": id, title: `${name} board`, onclick: () => setPaper(id) }, name));
  const bar = el("div", { class: "board-bar" },
    el("div", { class: "board-group" }, el("span", { class: "board-label" }, "Draw"), tools),
    el("div", { class: "board-group" }, el("span", { class: "board-label" }, "Colour"), el("div", { class: "board-swatches" }, swatches), sizeSel),
    el("div", { class: "board-group" }, el("span", { class: "board-label" }, "Board"), paperBtns),
    el("div", { class: "board-group" },
      el("button", { type: "button", class: "board-tool", title: "Undo (Ctrl+Z)", onclick: () => doUndo() }, "Undo"),
      el("button", { type: "button", class: "board-tool", title: "Clear this page", onclick: () => { pushUndo(); pages[page] = { strokes: [], texts: [] }; redraw(); } }, "Clear")),
    el("div", { class: "board-group" }, el("span", { class: "board-label" }, "Pages"),
      el("div", { class: "board-pages" },
        el("button", { type: "button", class: "board-tool", "aria-label": "Previous page", onclick: () => go(page - 1) }, "‹"), pageLabel,
        el("button", { type: "button", class: "board-tool", "aria-label": "Next page", onclick: () => go(page + 1) }, "›")),
      el("button", { type: "button", class: "board-tool", title: "Add a page", onclick: () => { pages.splice(page + 1, 0, { strokes: [], texts: [] }); go(page + 1); } }, "+ Page")));
  const eqForm = el("form", { class: "board-eqform", onsubmit: (e) => { e.preventDefault(); const v = eqInput.value.trim(); if (!v) return; writeText(v); eqInput.value = ""; onEquation?.(v); } },
    eqInput, el("button", { type: "submit", class: "btn small primary" }, "Write"));
  const root = el("div", { class: `board${transparent ? " overlay" : ""}` }, el("div", { class: "board-body" }, bar, el("div", { class: "board-surface" }, canvas)), eqForm);

  const ro = new ResizeObserver(() => {
    const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(r.width * dpr)); canvas.height = Math.max(1, Math.round(r.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); redraw();
  });
  ro.observe(canvas);

  function setTool(t) { tool = t; sync(); }
  function setPaper(id) { paper = id; try { localStorage.setItem(PAPER_KEY, id); } catch { /* storage unavailable */ } sync(); redraw(); }
  function sync() {
    tools.forEach((b) => b.classList.toggle("on", b.dataset.tool === tool));
    swatches.forEach((b, i) => b.classList.toggle("on", COLORS[i][1] === color && tool !== "eraser"));
    pageLabel.textContent = `${page + 1} / ${pages.length}`;
    paperBtns.forEach((b) => b.classList.toggle("on", b.dataset.paper === paper));
  }
  function go(p) { page = Math.max(0, Math.min(pages.length - 1, p)); sync(); redraw(); }
  function pushUndo() { undo.push(JSON.stringify(pages)); if (undo.length > 60) undo.shift(); }
  function doUndo() { if (!undo.length) return; pages = JSON.parse(undo.pop()); page = Math.min(page, pages.length - 1); sync(); redraw(); }

  const size2 = () => { const r = canvas.getBoundingClientRect(); return [r.width || 1, r.height || 1]; };
  function pos(e) { const r = canvas.getBoundingClientRect(); return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]; }

  function drawStroke(s, W, H) {
    ctx.strokeStyle = s.color; ctx.lineWidth = s.tool === "marker" ? s.size * 4 : s.size; ctx.globalAlpha = s.tool === "marker" ? 0.3 : 1;
    ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.beginPath();
    s.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x * W, y * H) : ctx.moveTo(x * W, y * H)));
    if (s.pts.length === 1) ctx.lineTo(s.pts[0][0] * W + 0.1, s.pts[0][1] * H);
    ctx.stroke(); ctx.globalAlpha = 1;
  }
  function redraw() {
    const [W, H] = size2();
    ctx.clearRect(0, 0, W, H);
    if (!transparent) {
      ctx.fillStyle = "#fdfdfb"; ctx.fillRect(0, 0, W, H);
      drawPaper(W, H);
    }
    const pg = pages[page];
    for (const s of pg.strokes) drawStroke(s, W, H);
    for (const t of pg.texts) {
      const fs = textSize(t, W, H);
      ctx.fillStyle = t.color; ctx.font = `600 ${fs}px Plex, system-ui`; ctx.textBaseline = "top";
      wrap(t.text, W * (0.96 - t.x)).forEach((ln, k) => ctx.fillText(ln, t.x * W, t.y * H + k * fs * 1.25));
    }
  }

  function drawPaper(W, H) { // the teacher's choice of board: plain, graph-paper grid, ruled lines or dots
    ctx.lineWidth = 1;
    if (paper === "grid") {
      for (let k = 1, x = 24; x < W; x += 24, k++) { ctx.strokeStyle = k % 5 ? "#eef0f3" : "#dfe3e9"; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (let k = 1, y = 24; y < H; y += 24, k++) { ctx.strokeStyle = k % 5 ? "#eef0f3" : "#dfe3e9"; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    } else if (paper === "lines") {
      ctx.strokeStyle = "#dbe4f0";
      for (let y = 40; y < H; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
      ctx.strokeStyle = "rgba(255,91,46,.35)"; ctx.beginPath(); ctx.moveTo(56, 0); ctx.lineTo(56, H); ctx.stroke();
    } else if (paper === "dots") {
      ctx.fillStyle = "#cfd6df";
      for (let x = 24; x < W; x += 24) for (let y = 24; y < H; y += 24) ctx.fillRect(x - 1, y - 1, 2, 2);
    }
  }

  const textSize = (t, W, H) => Math.round(Math.max(14, Math.min(H * (t.size || 0.05), W / 26, 30)));
  function wrap(text, maxW) {
    const lines = []; let cur = "";
    for (const word of text.split(" ")) {
      const next = cur ? `${cur} ${word}` : word;
      if (cur && ctx.measureText(next).width > maxW) { lines.push(cur); cur = word; } else cur = next;
    }
    if (cur) lines.push(cur);
    return lines;
  }
  function lineCount(t) {
    const [W, H] = size2(); ctx.font = `600 ${textSize(t, W, H)}px Plex, system-ui`;
    return wrap(t.text, W * (0.96 - t.x)).length;
  }

  function eraseAt([x, y]) {
    const [W, H] = size2(), rad = 14;
    const pg = pages[page], before = pg.strokes.length + pg.texts.length;
    pg.strokes = pg.strokes.filter((s) => !s.pts.some(([px, py]) => Math.hypot((px - x) * W, (py - y) * H) < rad));
    pg.texts = pg.texts.filter((t) => { const tw = t.text.length * (H * (t.size || 0.055)) * 0.55; return !(x * W > t.x * W - 4 && x * W < t.x * W + tw && y * H > t.y * H - 4 && y * H < t.y * H + H * (t.size || 0.055) + 6); });
    if (pg.strokes.length + pg.texts.length !== before) redraw();
  }

  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId); pushUndo();
    const p = pos(e);
    if (tool === "eraser") { drawing = { erase: true }; eraseAt(p); return; }
    drawing = { tool, color, size, pts: [p] }; pages[page].strokes.push(drawing); redraw();
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!drawing) return;
    const p = pos(e);
    if (drawing.erase) { eraseAt(p); return; }
    const last = drawing.pts[drawing.pts.length - 1];
    if (Math.hypot(p[0] - last[0], p[1] - last[1]) > 0.002) { drawing.pts.push([+p[0].toFixed(4), +p[1].toFixed(4)]); redraw(); }
  });
  const end = () => { drawing = null; };
  canvas.addEventListener("pointerup", end); canvas.addEventListener("pointercancel", end);

  function nextLine() {
    const texts = pages[page].texts, [W, H] = size2();
    const y = texts.length ? Math.max(...texts.map((t) => t.y + (lineCount(t) * textSize(t, W, H) * 1.25 + 8) / H)) : 0.05;
    if (y > 0.9) { pages.splice(page + 1, 0, { strokes: [], texts: [] }); go(page + 1); return 0.05; }
    return y;
  }
  /** Put a line of text on the board (an equation, a result, a derivation step). */
  function writeText(text, { color: c = color, size: sz = 0.05 } = {}) {
    pushUndo();
    pages[page].texts.push({ text, x: 0.04, y: nextLine(), color: c === "#FF5B2E" || c === "#0B1526" || c === "#2a78d6" || c === "#1baf7a" ? c : COLORS[0][1], size: sz });
    redraw();
  }

  function onKey(e) {
    if (e.target.closest?.("input, textarea, select")) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); doUndo(); }
    else if (!e.ctrlKey && !e.metaKey && !e.altKey) {
      if (e.key === "p") setTool("pen"); else if (e.key === "h") setTool("marker"); else if (e.key === "e") setTool("eraser");
    }
  }
  root.addEventListener("keydown", onKey);
  root.tabIndex = -1;
  sync();

  return {
    root,
    writeText,
    get data() { return { paper, pages: pages.map((p) => ({ strokes: p.strokes, texts: p.texts })) }; },
    load(data) {
      if (data?.paper && PAPERS.some(([id]) => id === data.paper)) paper = data.paper; // a saved lesson keeps its board
      if (data?.pages?.length) { pages = data.pages.map((p) => ({ strokes: p.strokes || [], texts: p.texts || [] })); page = 0; undo.length = 0; }
      sync(); redraw();
    },
    isEmpty() { return pages.every((p) => !p.strokes.length && !p.texts.length); },
    redraw,
    /** Over the simulation the board is see-through; beside it, it is a plain whiteboard. */
    setOverlay(v) { transparent = v; root.classList.toggle("overlay", v); redraw(); },
    destroy() { ro.disconnect(); },
  };
}
