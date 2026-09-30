// ASM Teach: the curriculum library (#/teach) and the classroom view for one experiment (#/teach/<id>).
// Every number comes from the engine's teach.* tools; the page draws, animates and keeps the lesson.
import { el, slider, segmented, select, SERIES } from "../core/ui.js";
import { simulate, liveRequest, clearRecentCalls } from "../core/api.js";
import { LineGraph } from "../core/graph.js";
import { createStage } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { mountAiPanel } from "../core/aichat.js";
import { history, toast } from "../core/session.js";
import { drawScene } from "../teach/scenes.js";
import { createBoard } from "../teach/board.js";

const SUBJECT = { physics: "Physics", chemistry: "Chemistry", mathematics: "Maths" };
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};

export default {
  title: "ASM Teach",
  mount(root, params) {
    const id = location.hash.match(/^#\/teach\/([\w-]+)/)?.[1];
    return id ? classroom(root, id, params) : library(root);
  },
};

// ================================================================ library
function library(root) {
  root.classList.add("teach-lib");
  const f = store.get("teach.filters", { board: "", cls: "", subject: "", kind: "", q: "" });
  let items = [], counts = {};
  const list = el("div", { class: "teach-list" }, el("p", { class: "muted" }, "Loading the library…"));
  const stats = el("div", { class: "teach-stats" });
  const search = el("input", { class: "search", type: "search", placeholder: "Search chapters, laws and practicals", value: f.q, "aria-label": "Search the library" });
  search.addEventListener("input", () => { f.q = search.value; draw(); });
  const boardSel = select({ label: "", options: [{ value: "", label: "All boards" }, ...["NCERT", "CBSE", "ICSE", "State"].map((b) => ({ value: b, label: b === "State" ? "State boards" : b }))], value: f.board, onChange: (v) => { f.board = v; draw(); } });
  const clsSeg = segmented({ options: [{ value: "", label: "All classes" }, ...[9, 10, 11, 12].map((c) => ({ value: String(c), label: `Class ${c}` }))], value: f.cls, onChange: (v) => { f.cls = v; draw(); } });
  const subjSeg = segmented({ options: [{ value: "", label: "All" }, ...Object.entries(SUBJECT).map(([value, label]) => ({ value, label }))], value: f.subject, onChange: (v) => { f.subject = v; draw(); } });
  const kindSeg = segmented({ options: [{ value: "", label: "Everything" }, { value: "derivation", label: "Derivations" }, { value: "practical", label: "Practicals" }, { value: "law", label: "Laws" }, { value: "graph", label: "Graphs" }], value: f.kind, onChange: (v) => { f.kind = v; draw(); } });

  // The board reader, right on the library page: write an equation, get the experiment
  const eq = el("input", { type: "text", class: "teach-eq", placeholder: "Write an equation or a topic: T = 2π√(L/g), PV = nRT, Snell's law", spellcheck: "false", "aria-label": "Equation or topic" });
  const found = el("div", { class: "teach-found" });
  const reader = el("form", { class: "teach-reader", onsubmit: async (e) => {
    e.preventDefault();
    const text = eq.value.trim(); if (!text) return;
    found.replaceChildren(el("p", { class: "muted" }, "Reading it…"));
    try {
      const r = (await simulate("teach", "recognize", { equation: text })).result;
      found.replaceChildren(...readerResult(r));
    } catch (err) { found.replaceChildren(el("p", { class: "muted" }, err.message)); }
  } }, el("label", { class: "teach-reader-label" }, "Find a simulation from an equation"), el("div", { class: "teach-reader-row" }, eq, el("button", { type: "submit", class: "btn primary" }, "Find")), found);

  root.append(el("div", { class: "teach-home" },
    el("div", { class: "teach-hero" },
      el("div", {}, el("p", { class: "teach-eyebrow" }, "ASM Teach"),
        el("h1", {}, "Class 9 to 12, as live simulations"),
        el("p", { class: "muted" }, "Every derivation, law and practical from the physics, chemistry and maths syllabus, ready to run in class with a whiteboard, practice questions and an AI co-teacher beside it. Chapters follow NCERT; CBSE, ICSE and state board topics are mapped.")),
      stats),
    reader,
    el("div", { class: "teach-filters" }, boardSel.root, clsSeg.root, subjSeg.root, kindSeg.root, search),
    list));

  simulate("teach", "catalog", {}).then(({ result }) => {
    items = result.items; counts = result.counts;
    const bySubject = Object.keys(SUBJECT).map((s) => [s, Object.values(counts).reduce((a, c) => a + (c[s] || 0), 0)]);
    stats.replaceChildren(el("div", { class: "teach-stat" }, el("b", {}, String(result.total)), el("span", {}, "simulations")),
      ...bySubject.map(([s, n]) => el("div", { class: "teach-stat" }, el("b", {}, String(n)), el("span", {}, SUBJECT[s]))));
    draw();
  }).catch((err) => list.replaceChildren(el("p", { class: "empty" }, err.message)));

  function draw() {
    store.set("teach.filters", f);
    if (!items.length) return;
    const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
    const shown = items.filter((i) => (!f.board || i.boards.includes(f.board)) && (!f.cls || String(i.class) === f.cls) &&
      (!f.subject || i.subject === f.subject) && (!f.kind || i.kind === f.kind) &&
      (!words.length || words.every((w) => `${i.title} ${i.chapter} ${i.blurb} ${i.equation}`.toLowerCase().includes(w))));
    if (!shown.length) { list.replaceChildren(el("p", { class: "empty" }, "Nothing matches. Try another class, board or word.")); return; }
    const groups = new Map();
    for (const i of shown) {
      const key = `${i.class}|${i.subject}`;
      if (!groups.has(key)) groups.set(key, new Map());
      const ch = groups.get(key);
      if (!ch.has(i.chapter)) ch.set(i.chapter, []);
      ch.get(i.chapter).push(i);
    }
    list.replaceChildren(...[...groups.entries()].map(([key, chapters]) => {
      const [cls, subj] = key.split("|");
      const n = [...chapters.values()].reduce((a, c) => a + c.length, 0);
      return el("section", { class: "teach-group" },
        el("h2", { class: "domain-title" }, `Class ${cls} ${SUBJECT[subj]}`, el("span", { class: "count" }, String(n))),
        ...[...chapters.entries()].map(([chapter, exps]) => el("div", { class: "teach-chapter" },
          el("h3", {}, chapter),
          el("div", { class: "teach-cards" }, exps.map(card)))));
    }));
  }
  return () => {};
}

/** Near a pole (a lens at u = f) one spike can flatten the whole curve; keep the view on the bulk of the data. */
function robustRange(seriesList) {
  const v = seriesList.flat().filter((x) => x !== null && Number.isFinite(x)).sort((a, b) => a - b);
  if (v.length < 10) return undefined;
  const q = (p) => v[Math.floor(p * (v.length - 1))];
  const lo = q(0.05), hi = q(0.95), span = hi - lo || Math.abs(hi) || 1;
  if (v[v.length - 1] - v[0] < 6 * span) return undefined;
  return [lo - 0.6 * span, hi + 0.6 * span];
}

function card(i) {
  return el("a", { class: `teach-card s-${i.subject}`, href: `#/teach/${i.id}` },
    el("div", { class: "teach-card-top" }, el("span", { class: `kind k-${i.kind}` }, i.kind_label),
      i.boards.length < 4 ? el("span", { class: "teach-boards" }, i.boards.join(", ")) : ""),
    el("b", {}, i.title), el("span", { class: "teach-card-eq" }, i.equation), el("small", {}, i.blurb));
}

function readerResult(r, { onWrite } = {}) {
  const out = [];
  if (r.read_as) out.push(el("p", { class: "teach-readas" }, "Read as ", el("b", {}, r.read_as)));
  if (r.matches.length) out.push(el("div", { class: "teach-cards compact" }, r.matches.map((m) => {
    const c = card(m); c.append(el("span", { class: "teach-why" }, m.reason === "same equation" ? "Same equation" : m.reason === "topic match" ? "Topic match" : `Shares quantities (${Math.round(m.score * 100)}%)`)); return c;
  })));
  else out.push(el("p", { class: "muted" }, "Nothing in the library uses that yet. Check the symbols match the textbook's (v, u, a, t)."));
  if (r.rearranged.length) out.push(el("div", { class: "teach-rearr" }, el("span", { class: "muted small" }, "Rearranged: "),
    r.rearranged.map((x) => onWrite ? el("button", { type: "button", class: "chip", title: "Write on the board", onclick: () => onWrite(x.pretty) }, x.pretty) : el("span", { class: "chip" }, x.pretty))));
  return out;
}

// ================================================================ classroom
function classroom(root, id, params) {
  root.classList.add("teach-room");
  clearRecentCalls();
  let res = null, values = {}, readings = [], alive = true, raf = 0, aiCleanup = () => {};
  let boardMode = store.get("teach.boardMode", "beside");
  const sliders = {};

  const title = el("h1", {}, "Loading…");
  const meta = el("div", { class: "teach-meta" });
  const labLink = el("a", { class: "btn small", hidden: true }, "Full simulation");
  const modeSeg = segmented({ label: "", options: [{ value: "off", label: "No board" }, { value: "beside", label: "Board beside" }, { value: "over", label: "Draw over" }], value: boardMode, onChange: (v) => setBoardMode(v) });
  const saveBtn = el("button", { type: "button", class: "btn small primary", onclick: () => saveLesson() }, "Save lesson");
  const projBtn = el("button", { type: "button", class: "btn small", onclick: () => projector() }, "Projector");
  const head = el("header", { class: "teach-head" },
    el("a", { class: "teach-back", href: "#/teach" }, "‹ Library"),
    el("div", { class: "teach-title" }, title, meta),
    el("div", { class: "teach-actions" }, modeSeg.root, labLink, projBtn, saveBtn));

  const sceneBox = el("div", { class: "teach-scene" });
  const stage = createStage(sceneBox);
  const status = el("div", { class: "scene-status" });
  sceneBox.append(status);
  const graphBox = el("div", { class: "teach-graph" });
  const graph = new LineGraph(graphBox, { height: 170 });
  const boardSlot = el("div", { class: "teach-board" });
  const readerCard = el("div", { class: "board-reader", hidden: true });
  const board = createBoard({ onEquation: (text) => readBoard(text) });
  board.root.append(readerCard);

  const inputs = el("div", { class: "teach-inputs" });
  const results = el("dl", { class: "teach-results" });
  const tabBody = el("div", { class: "teach-tabbody" });
  const TABS = [["eq", "Equations"], ["steps", "Derivation"], ["readings", "Readings"], ["practice", "Practice"]];
  let tab = params.tab || "eq";
  const tabBar = el("div", { class: "tabs teach-tabs", role: "tablist" });
  const side = el("aside", { class: "teach-side" },
    el("section", { class: "panel" }, el("h4", {}, "Inputs"), inputs),
    el("section", { class: "panel" }, el("h4", {}, "Results from the engine"), results),
    el("section", { class: "panel teach-tabpanel" }, tabBar, tabBody));
  const main = el("div", { class: "teach-main" }, sceneBox, graphBox);
  const body = el("div", { class: "teach-body" }, main, boardSlot, side);
  root.append(head, body);
  setBoardMode(boardMode, { quiet: true });

  const run = liveRequest((signal) => simulate("teach", "experiment", { experiment_id: id, values }, signal), {
    onResult: (r) => { status.classList.remove("show", "error"); apply(r.result, r.assumptions); },
    onError: (err) => { status.textContent = err.message; status.classList.add("show", "error"); },
    delay: 60,
  });

  simulate("teach", "experiment", { experiment_id: id }).then(async (r) => {
    if (!alive) return;
    build(r.result);
    apply(r.result, r.assumptions);
    aiCleanup = mountAiPanel(root, { id: `teach-${id}`, title: r.result.title, blurb: r.result.blurb }, {
      label: "AI co-teacher",
      quick: [
        ["Explain it to my class", `Explain this experiment to a Class ${r.result.class} student in simple words, using the numbers on screen. Keep it to what a teacher could say in two minutes.`],
        ["Common mistakes", "What mistakes and misconceptions do students usually have about this topic, and how can I show each one with this simulation?"],
        ["Questions for the board", "Give me three board questions of rising difficulty on this topic, with answers worked out using the engine."],
        ["Real-life examples", "Give three real-life examples of this idea that students in India would recognise, with numbers where you can compute them."],
      ],
    });
    if (params.lesson) await openLesson(params.lesson);
    loop();
  }).catch((err) => { title.textContent = "Could not open this experiment"; body.replaceChildren(el("p", { class: "empty" }, err.message)); });

  function build(r) {
    document.title = `${r.title} · ASM Teach`;
    title.textContent = r.title;
    meta.replaceChildren(el("span", { class: `kind k-${r.kind}` }, r.kind_label), el("span", {}, `Class ${r.class} ${SUBJECT[r.subject]} · ${r.chapter}`),
      el("span", { class: "muted small" }, r.boards.length === 4 ? "NCERT, CBSE, ICSE, State" : r.boards.join(", ")));
    if (r.lab) { labLink.hidden = false; labLink.href = `#/sim/${r.lab}`; }
    for (const p of r.params) {
      values[p.name] = p.default;
      const s = slider({ label: `${p.label}${p.symbol && p.symbol !== p.label ? ` (${p.symbol})` : ""}`, min: p.min, max: p.max, step: p.step || "any", value: p.default, unit: p.unit, digits: 4,
        onInput: (v) => { values[p.name] = p.step ? Math.round(v / p.step) * p.step : v; run(); } });
      sliders[p.name] = s;
      inputs.append(s.root);
    }
    inputs.append(el("div", { class: "btn-row" }, el("button", { type: "button", class: "btn small", onclick: () => { for (const p of r.params) { values[p.name] = p.default; sliders[p.name].set(p.default); } run(); } }, "Reset")));
  }

  function apply(r, assumptions = []) {
    res = r;
    results.replaceChildren(...r.outputs.flatMap((o, k) => [
      el("dt", { title: o.formula }, o.label),
      el("dd", { class: k === 0 ? "lead" : "" }, o.value === null ? "no real value" : `${fmt(o.value, 5)}${o.unit ? " " + o.unit : ""}`)]));
    res.assumptions = assumptions;
    const g = r.graph, colors = SERIES();
    if (g) {
      graphBox.hidden = false;
      if (g.path) {
        graph.opts.xLabel = `${g.series[0].label}${g.series[0].unit ? ` (${g.series[0].unit})` : ""}`;
        graph.opts.title = `${g.series[1].label} against ${g.series[0].label.toLowerCase()}`;
        graph.setSeries([{ name: g.series[1].label, color: colors[0], x: g.series[0].values, y: g.series[1].values }]);
      } else {
        graph.opts.xLabel = `${g.x.label}${g.x.unit ? ` (${g.x.unit})` : ""}`;
        graph.opts.title = g.series.length === 1 ? `${g.series[0].label}${g.series[0].unit ? ` (${g.series[0].unit})` : ""} against ${g.x.label.toLowerCase()}` : `Against ${g.x.label.toLowerCase()}`;
        graph.setSeries(g.series.slice(0, 3).map((s, k) => ({ name: `${s.label}${s.unit ? ` (${s.unit})` : ""}`, color: colors[k], x: g.x.values, y: s.values })));
      }
      graph.opts.yRange = robustRange(g.path ? [g.series[1].values] : g.series.slice(0, 3).map((s) => s.values));
      graph.draw();
      graph.root.querySelector(".graph-title").textContent = graph.opts.title;
      graph.setCursor(g.cursor ?? null);
    } else graphBox.hidden = true;
    drawTab();
  }

  function loop() {
    const tick = (now) => {
      if (!alive) return;
      if (!document.hidden && res) drawScene(stage.ctx, stage.width, stage.height, res, now / 1000);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }

  // ---------------------------------------------------------------- tabs
  function drawTabs() {
    tabBar.replaceChildren(...TABS.map(([k, label]) => el("button", { type: "button", role: "tab", class: `tab${k === tab ? " on" : ""}`, "aria-selected": String(k === tab), onclick: () => { tab = k; drawTabs(); drawTab(); } },
      label, k === "readings" && readings.length ? el("span", { class: "count" }, String(readings.length)) : "")));
  }
  function drawTab() {
    drawTabs();
    if (!res) return;
    const write = (text) => { if (boardMode === "off") setBoardMode("beside"); board.writeText(text); };
    if (tab === "eq") {
      tabBody.replaceChildren(
        ...res.equations.map((e) => el("div", { class: "teach-eqline" }, el("span", {}, e.pretty), el("button", { type: "button", class: "btn small", onclick: () => write(e.pretty) }, "To board"))),
        el("p", { class: "muted small" }, "Each result on screen comes from:"),
        ...res.outputs.map((o) => el("div", { class: "teach-eqline small" }, el("span", {}, o.formula),
          el("button", { type: "button", class: "btn small", onclick: () => write(`${o.formula} = ${fmt(o.value, 5)}${o.unit ? " " + o.unit : ""}`) }, "To board"))),
        res.assumptions?.length ? el("p", { class: "muted small" }, `Assumes: ${res.assumptions.join(" ")}`) : "");
    } else if (tab === "steps") {
      tabBody.replaceChildren(el("ol", { class: "teach-steps" }, res.steps.map((s) => el("li", {}, s))),
        el("button", { type: "button", class: "btn small primary", onclick: () => { res.steps.forEach((s, k) => write(`${k + 1}. ${s}`)); toast("Derivation written on the board."); } }, "Write the derivation on the board"));
    } else if (tab === "readings") drawReadings();
    else drawPractice();
  }

  function drawReadings() {
    const cols = [...res.params.map((p) => ({ key: p.name, label: p.symbol, unit: p.unit, src: "in" })), ...res.outputs.slice(0, 3).map((o) => ({ key: o.name, label: o.label, unit: o.unit, src: "out" }))];
    const table = el("table", { class: "ice teach-table" },
      el("thead", {}, el("tr", {}, el("th", {}, "#"), cols.map((c) => el("th", { title: c.unit }, `${c.label}${c.unit ? ` (${c.unit})` : ""}`)))),
      el("tbody", {}, readings.map((r, k) => el("tr", {}, el("td", {}, String(k + 1)), cols.map((c) => el("td", {}, fmt(r[c.key], 4)))))));
    tabBody.replaceChildren(
      el("p", { class: "muted small" }, "Set the inputs, then record a reading, the way you would fill an observation table in the lab."),
      el("div", { class: "btn-row" },
        el("button", { type: "button", class: "btn small primary", onclick: () => { const row = { ...values }; res.outputs.forEach((o) => { row[o.name] = o.value; }); readings.push(row); drawTab(); } }, "Record reading"),
        el("button", { type: "button", class: "btn small", disabled: !readings.length, onclick: () => copyCsv(cols) }, "Copy as CSV"),
        el("button", { type: "button", class: "btn small", disabled: !readings.length, onclick: () => { readings = []; drawTab(); } }, "Clear")),
      readings.length ? el("div", { class: "teach-tablewrap" }, table) : el("p", { class: "muted small" }, "No readings yet."));
  }
  function copyCsv(cols) {
    const lines = [cols.map((c) => `${c.label}${c.unit ? ` (${c.unit})` : ""}`).join(","), ...readings.map((r) => cols.map((c) => r[c.key]).join(","))];
    navigator.clipboard?.writeText(lines.join("\n")).then(() => toast("Readings copied."), () => toast("Could not copy; your browser blocked it.", "error"));
  }

  let practice = null;
  function drawPractice() {
    const newSet = async () => {
      tabBody.replaceChildren(el("p", { class: "muted" }, "Making questions…"));
      try { practice = { ...(await simulate("teach", "practice", { experiment_id: id, count: 5, seed: Math.floor(Math.random() * 1e9) })).result, marks: {} }; }
      catch (err) { tabBody.replaceChildren(el("p", { class: "muted" }, err.message)); return; }
      drawPractice();
    };
    if (!practice) { tabBody.replaceChildren(el("p", { class: "muted small" }, "Fresh numbers every time. The engine works out each answer, so you can check the class's work at once."), el("button", { type: "button", class: "btn primary", onclick: newSet }, "Make five questions")); return; }
    const right = Object.values(practice.marks).filter(Boolean).length, tried = Object.keys(practice.marks).length;
    tabBody.replaceChildren(
      el("div", { class: "teach-score" }, el("span", {}, tried ? `${right} of ${tried} right` : "Pick an answer or type your own"), el("button", { type: "button", class: "btn small", onclick: newSet }, "New set")),
      ...practice.questions.map((q, k) => {
        const mark = practice.marks[k];
        const sol = el("ol", { class: "teach-sol", hidden: true }, q.solution.map((s) => el("li", {}, s)));
        const typed = el("input", { type: "text", inputmode: "decimal", class: "teach-answer", placeholder: `Answer in ${q.unit || "no unit"}`, "aria-label": "Your answer" });
        const check = (value) => { const ok = Number.isFinite(value) && Math.abs(value - q.answer) <= q.tolerance * Math.max(Math.abs(q.answer), 1e-12); practice.marks[k] = ok; drawPractice(); };
        return el("div", { class: `teach-q${mark === true ? " ok" : mark === false ? " no" : ""}` },
          el("p", {}, el("b", {}, `${k + 1}. `), q.text),
          el("div", { class: "teach-choices" }, q.choices.map((c, j) => el("button", { type: "button", class: `chip${mark !== undefined && j === q.correct_index ? " right" : ""}`, onclick: () => check(c) }, `${fmt(c, 4)} ${q.unit}`))),
          el("form", { class: "teach-typed", onsubmit: (e) => { e.preventDefault(); check(Number(typed.value.replace(/[^\d.eE+-]/g, ""))); } }, typed, el("button", { type: "submit", class: "btn small" }, "Check")),
          mark !== undefined ? el("p", { class: "teach-verdict" }, mark ? "Right." : `Not quite. The answer is ${fmt(q.answer, 4)} ${q.unit}.`) : "",
          el("div", { class: "btn-row" },
            el("button", { type: "button", class: "btn small", onclick: () => { sol.hidden = !sol.hidden; } }, "Show working"),
            el("button", { type: "button", class: "btn small", onclick: () => { if (boardMode === "off") setBoardMode("beside"); board.writeText(`Q${k + 1}. ${q.text}`, { size: 0.04 }); } }, "Question to board")),
          sol);
      }));
  }

  // ---------------------------------------------------------------- board
  function setBoardMode(mode, { quiet = false } = {}) {
    boardMode = mode; modeSeg.set(mode); store.set("teach.boardMode", mode);
    root.classList.toggle("board-off", mode === "off"); root.classList.toggle("board-over", mode === "over");
    if (mode === "over") { sceneBox.append(board.root); board.setOverlay(true); }
    else { boardSlot.append(board.root); board.setOverlay(false); }
    if (!quiet) requestAnimationFrame(() => board.redraw());
  }

  async function readBoard(text) {
    readerCard.hidden = false;
    readerCard.replaceChildren(el("p", { class: "muted small" }, "Reading the board…"));
    try {
      const r = (await simulate("teach", "recognize", { equation: text })).result;
      const here = r.matches.find((m) => m.id === id);
      readerCard.replaceChildren(
        el("div", { class: "board-reader-head" }, el("b", {}, here && here.score === 1 ? "That is this experiment's equation." : "The board read your equation"),
          el("button", { type: "button", class: "ai-x", "aria-label": "Close", onclick: () => { readerCard.hidden = true; } }, "×")),
        ...readerResult({ ...r, matches: r.matches.filter((m) => m.id !== id).slice(0, 3) }, { onWrite: (t) => board.writeText(t, { color: "#2a78d6" }) }));
    } catch (err) { readerCard.replaceChildren(el("p", { class: "muted small" }, err.message)); }
  }

  // ---------------------------------------------------------------- lessons
  async function saveLesson() {
    if (!res) return;
    saveBtn.disabled = true;
    try {
      const payload = { experiment_id: id, values, board: board.data, readings };
      if (JSON.stringify(payload).length > 550000) { toast("The board is too full to save. Clear a page or two and try again.", "error"); return; }
      const title = `${res.title}, ${new Date().toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}`;
      const summary = { class: res.class, subject: res.subject, chapter: res.chapter, inputs: values, readings: readings.length };
      const saved = await history.create({ kind: "lesson", sim_id: id, title, payload, summary });
      window.history.replaceState(null, "", `#/teach/${id}?lesson=${saved.id}`);
      toast("Lesson saved to your history.");
    } catch (err) { toast(err.message, "error"); } finally { saveBtn.disabled = false; }
  }
  async function openLesson(runId) {
    try {
      const saved = await history.get(runId);
      const p = saved.payload || {};
      if (p.experiment_id !== id) return;
      for (const [k, v] of Object.entries(p.values || {})) if (sliders[k]) { values[k] = v; sliders[k].set(v); }
      readings = p.readings || [];
      board.load(p.board);
      if (p.board && !board.isEmpty() && boardMode === "off") setBoardMode("beside");
      toast("Lesson opened.");
      run();
    } catch (err) { toast(err.message, "error"); }
  }

  function projector() {
    const on = !root.classList.contains("projector");
    root.classList.toggle("projector", on);
    if (on && root.requestFullscreen) root.requestFullscreen().catch(() => {});
    else if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
    requestAnimationFrame(() => board.redraw());
  }
  const onFs = () => { if (!document.fullscreenElement) root.classList.remove("projector"); };
  document.addEventListener("fullscreenchange", onFs);

  return () => {
    alive = false; cancelAnimationFrame(raf); run.cancel(); aiCleanup(); board.destroy(); stage.destroy();
    document.removeEventListener("fullscreenchange", onFs);
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  };
}
