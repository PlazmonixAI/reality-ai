// The teacher's board: a full-width whiteboard with everything else folded into a slim rail on the right, closed until
// tapped, so the board keeps the room. The rail opens: suggested experiments (from what is written and said), the
// Equation Lab, YouTube, a web window, the teacher's own files, listen mode and the AI co-teacher (only when tapped).
import { el } from "../core/ui.js";
import { simulate } from "../core/api.js";
import { api, history, toast } from "../core/session.js";
import { mountAiPanel } from "../core/aichat.js";
import { createBoard } from "../teach/board.js";
import { equationLab } from "../teach/eqlab.js";
import { listenButton, setListenHandler } from "../teach/listen.js";
import { filesManager, fileWindowContent } from "./files.js";

const SUBJECT = { physics: "Physics", chemistry: "Chemistry", mathematics: "Maths" };
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* full or private */ } },
};
const event = (kind, ref = "") => api("/api/teach/events", { method: "POST", body: { kind, ref } }).catch(() => {});

/** "https://youtu.be/ID", "youtube.com/watch?v=ID", "/shorts/ID", "/embed/ID" or a bare 11-character id -> id */
export function youtubeId(text) {
  const t = text.trim();
  if (/^[\w-]{11}$/.test(t)) return t;
  const m = t.match(/(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/|live\/))([\w-]{11})/);
  return m ? m[1] : null;
}

export default {
  title: "Board",
  mount(root, params, me) {
    const key = `asmteach.board.${me.teacher.id}`;
    const suggestions = new Map();
    const surface = el("div", { class: "ta-surface" });
    const windows = el("div", { class: "ta-windows" });
    const drawer = el("aside", { class: "ta-drawer", "aria-label": "Board tools", hidden: true });
    const rail = el("nav", { class: "ta-rail", "aria-label": "Board tools" });
    root.append(el("div", { class: "ta-boardwrap" }, surface, windows, drawer, rail));

    // ---------------------------------------------------------------- the board itself
    const board = createBoard({ onEquation: (text) => readBoard(text) });
    surface.append(board.root);
    board.load(store.get(key, null));
    const autosave = setInterval(() => store.set(key, board.data), 4000);
    event("board", "open");

    // ---------------------------------------------------------------- rail and drawer
    const badge = el("span", { class: "ta-badge", hidden: true });
    let open = null;
    const tool = (id, label, title, onClick) => {
      const b = el("button", { type: "button", class: "ta-railbtn", "data-tool": id, title, "aria-label": title, onclick: onClick || (() => toggle(id)) }, label);
      rail.append(b);
      return b;
    };
    const DRAWERS = { suggest: ["Suggested for this lesson", suggestBody], lab: ["Equation Lab", labBody], video: ["YouTube", videoBody],
      web: ["Web", webBody], files: ["My files", filesBody] };
    tool("suggest", "Ideas", "Experiments suggested from your lesson").append(badge);
    tool("lab", "f(x)", "Equation Lab: build any equation");
    tool("video", "Video", "Play a YouTube video");
    tool("web", "Web", "Open a website");
    tool("files", "Files", "Your slides, PDFs and pictures");
    const listen = listenButton(); listen.classList.add("ta-railbtn"); rail.append(listen);
    tool("ai", "AI", "Open the AI co-teacher", () => { root.querySelector(".ai-tab")?.click(); });
    tool("save", "Save", "Save this board as a lesson", () => saveLesson());

    function toggle(id) {
      if (open === id) { closeDrawer(); return; }
      open = id;
      rail.querySelectorAll(".ta-railbtn").forEach((b) => b.classList.toggle("on", b.dataset.tool === id));
      const [title, body] = DRAWERS[id];
      drawer.hidden = false;
      drawer.replaceChildren(el("div", { class: "ta-drawer-head" }, el("b", {}, title),
        el("button", { type: "button", class: "ai-x", "aria-label": "Close", onclick: () => closeDrawer() }, "×")), body());
      if (id === "suggest") badge.hidden = true;
    }
    function closeDrawer() {
      open = null; drawer.hidden = true; drawer.replaceChildren();
      rail.querySelectorAll(".ta-railbtn").forEach((b) => b.classList.remove("on"));
    }

    // ---------------------------------------------------------------- floating windows over the board
    function floatWindow(title, content, { wide = false } = {}) {
      const close = el("button", { type: "button", class: "ai-x", "aria-label": `Close ${title}` }, "×");
      const max = el("button", { type: "button", class: "btn small", title: "Fill the board" }, "Full");
      const head = el("div", { class: "ta-win-head" }, el("b", {}, title), el("span", { class: "spacer" }), max, close);
      const win = el("section", { class: `ta-win${wide ? " wide" : ""}`, role: "dialog", "aria-label": title }, head, el("div", { class: "ta-win-body" }, content));
      const n = windows.children.length;
      win.style.left = `${40 + 30 * n}px`; win.style.top = `${30 + 30 * n}px`;
      windows.append(win);
      close.onclick = () => win.remove();
      max.onclick = () => { win.classList.toggle("max"); max.textContent = win.classList.contains("max") ? "Window" : "Full"; };
      let drag = null;  // move by the title bar
      head.addEventListener("pointerdown", (e) => {
        if (e.target.closest("button")) return;
        drag = { x: e.clientX - win.offsetLeft, y: e.clientY - win.offsetTop }; head.setPointerCapture(e.pointerId);
      });
      head.addEventListener("pointermove", (e) => { if (drag) { win.style.left = `${Math.max(0, e.clientX - drag.x)}px`; win.style.top = `${Math.max(0, e.clientY - drag.y)}px`; } });
      head.addEventListener("pointerup", () => { drag = null; });
      win.addEventListener("pointerdown", () => windows.append(win));  // bring to front
      return win;
    }

    // ---------------------------------------------------------------- suggestions from what is written and said
    function addSuggestions(matches, why) {
      let added = 0;
      for (const m of matches) {
        if (!m || suggestions.has(m.id)) continue;
        suggestions.set(m.id, { ...m, why });
        added++;
      }
      if (added && open !== "suggest") { badge.hidden = false; badge.textContent = String(suggestions.size); }
      if (open === "suggest") toggle("suggest"), toggle("suggest");
    }
    async function readBoard(text) {
      try {
        const r = (await simulate("teach", "recognize", { equation: text })).result;
        addSuggestions(r.matches.filter((m) => m.score >= 0.34), `From “${text}” on the board`);
      } catch { /* not an equation the library knows; the Equation Lab still can */ }
      if (/[=→]|->/.test(text)) { toggle("lab"); labRun?.(text); event("equation", text.slice(0, 100)); }
    }
    function suggestBody() {
      const q = el("input", { type: "search", class: "search", placeholder: "Search the library: lenses, titration, quadratic…", "aria-label": "Search experiments" });
      const results = el("div", { class: "ta-cards" });
      const list = el("div", { class: "ta-cards" });
      const card = (m) => el("a", { class: `ta-card s-${m.subject}`, href: `#/teach/${m.id}` },
        el("b", {}, m.title), el("span", {}, `Coursework ${m.class - 8} ${SUBJECT[m.subject] || ""} · ${m.chapter}`), m.why ? el("small", {}, m.why) : "");
      const draw = () => list.replaceChildren(...(suggestions.size ? [...suggestions.values()].reverse().map(card)
        : [el("p", { class: "muted small" }, "Write an equation on the board or turn on Listen, and matching experiments appear here.")]));
      let timer = 0;
      q.addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(async () => {
          if (q.value.trim().length < 2) { results.replaceChildren(); return; }
          try {
            const r = (await simulate("teach", "catalog", { query: q.value.trim() })).result;
            results.replaceChildren(...r.items.slice(0, 8).map(card));
          } catch (err) { results.replaceChildren(el("p", { class: "muted small" }, err.message)); }
        }, 250);
      });
      draw();
      return el("div", { class: "ta-drawer-body" }, q, results, el("h4", {}, "From this lesson"), list);
    }

    // ---------------------------------------------------------------- Equation Lab
    let labRun = null;
    function labBody() {
      const lab = equationLab({ onWrite: (t) => board.writeText(t, { color: "#2a78d6", size: 0.03 }) });
      const input = el("input", { type: "text", class: "teach-eq", placeholder: "sin²x + cos²x = 1, F = m a, H2 + O2 -> H2O", spellcheck: "false", "aria-label": "Equation" });
      labRun = (t) => { input.value = t; lab.run(t); };
      const form = el("form", { class: "ta-row", onsubmit: (e) => { e.preventDefault(); if (input.value.trim()) { lab.run(input.value.trim()); event("equation", input.value.trim().slice(0, 100)); } } },
        input, el("button", { type: "submit", class: "btn primary small" }, "Build"));
      return el("div", { class: "ta-drawer-body" }, form, lab.root);
    }

    // ---------------------------------------------------------------- YouTube
    function videoBody() {
      const input = el("input", { type: "url", class: "search", placeholder: "Paste a YouTube link", "aria-label": "YouTube link" });
      const err = el("p", { class: "muted small" });
      const play = () => {
        const id = youtubeId(input.value);
        if (!id) { err.textContent = "That doesn't look like a YouTube link. Copy it from the Share button on YouTube."; return; }
        err.textContent = "";
        const frame = el("iframe", { src: `https://www.youtube-nocookie.com/embed/${id}?rel=0&modestbranding=1`, title: "YouTube video",
          allow: "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen", allowfullscreen: "", referrerpolicy: "strict-origin-when-cross-origin" });
        floatWindow("YouTube", frame, { wide: true });
        event("video", id);
        closeDrawer();
      };
      const search = el("input", { type: "search", class: "search", placeholder: "Search YouTube (opens a new tab)", "aria-label": "Search YouTube" });
      return el("div", { class: "ta-drawer-body" },
        el("form", { class: "ta-row", onsubmit: (e) => { e.preventDefault(); play(); } }, input, el("button", { type: "submit", class: "btn primary small" }, "Play")), err,
        el("p", { class: "muted small" }, "The video plays in a window over the board. Drag it by its title bar, or press Full for the whole board."),
        el("form", { class: "ta-row", onsubmit: (e) => { e.preventDefault(); if (search.value.trim()) window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(search.value.trim())}`, "_blank", "noopener"); } },
          search, el("button", { type: "submit", class: "btn small" }, "Search")),
        el("p", { class: "muted small" }, "Find a video, copy its link, and paste it above to play it here."));
    }

    // ---------------------------------------------------------------- a web window
    function webBody() {
      const input = el("input", { type: "url", class: "search", placeholder: "https://…", "aria-label": "Web address" });
      const go = (url) => {
        let u = url.trim();
        if (!u) return;
        if (!/^https?:\/\//i.test(u)) u = `https://${u}`;
        if (!/^https:\/\//i.test(u)) { toast("Only secure (https) sites can open here.", "error"); return; }
        const frame = el("iframe", { src: u, title: u, sandbox: "allow-scripts allow-same-origin allow-forms allow-popups allow-presentation", referrerpolicy: "no-referrer" });
        const note = el("div", { class: "ta-webnote" }, el("span", {}, "Blank? Some sites refuse to open inside another page."),
          el("a", { class: "btn small", href: u, target: "_blank", rel: "noopener" }, "Open in a new tab"));
        floatWindow(new URL(u).hostname, el("div", { class: "ta-webwrap" }, frame, note), { wide: true });
        closeDrawer();
      };
      const quick = [["Wikipedia", "https://en.m.wikipedia.org/"], ["PhET", "https://phet.colorado.edu/"], ["OLabs", "https://www.olabs.edu.in/"], ["Desmos", "https://www.desmos.com/calculator"]];
      return el("div", { class: "ta-drawer-body" },
        el("form", { class: "ta-row", onsubmit: (e) => { e.preventDefault(); go(input.value); } }, input, el("button", { type: "submit", class: "btn primary small" }, "Open")),
        el("div", { class: "ta-chips" }, quick.map(([n, u]) => el("button", { type: "button", class: "chip", onclick: () => go(u) }, n))),
        el("p", { class: "muted small" }, "Websites open in a window over the board. Sites that block being shown inside other pages open in a new tab instead."));
    }

    // ---------------------------------------------------------------- the teacher's files
    function filesBody() {
      return el("div", { class: "ta-drawer-body" }, filesManager({ compact: true, onShow: (f) => showFile(f) }));
    }
    function showFile(f) {
      floatWindow(f.name, fileWindowContent(f), { wide: true });
      event("file_shown", f.ext);
      closeDrawer();
    }
    if (params.show) api("/api/teach/files").then(({ files }) => { const f = files.find((x) => x.id === params.show); if (f) showFile(f); }).catch(() => {});

    // ---------------------------------------------------------------- listen mode: speech feeds suggestions and the lab
    const unlisten = setListenHandler((r) => {
      if (r.experiment) addSuggestions([{ ...r.experiment }], `You said: “${r.heard}”`);
      if (r.action === "explore" && r.equation) { board.writeText(r.equation); toggle("lab"); labRun?.(r.equation); }
      for (const m of r.matches || []) if (m.score >= 0.5) addSuggestions([m], `You said: “${r.heard}”`);
      event("listen", r.action);
    });

    // ---------------------------------------------------------------- save as a lesson
    async function saveLesson() {
      if (board.isEmpty()) { toast("The board is empty; write something first."); return; }
      try {
        const title = `Board, ${new Date().toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}`;
        await history.create({ kind: "lesson", sim_id: "board", title, payload: { board: board.data }, summary: { pages: board.data?.pages?.length || 1 } });
        event("lesson_saved", "board");
        toast("Board saved to your lessons.");
      } catch (err) { toast(err.message, "error"); }
    }
    if (params.lesson) history.get(params.lesson).then((s) => { if (s.payload?.board) { board.load(s.payload.board); toast("Lesson opened."); } }).catch((e) => toast(e.message, "error"));

    // ---------------------------------------------------------------- the AI co-teacher (hidden until the rail button is tapped)
    const aiCleanup = mountAiPanel(root, { id: "teach-board", title: "Classroom board", blurb: `${me.teacher.subject || "Science"} lesson by ${me.teacher.name}` }, {
      label: "AI co-teacher",
      quick: [
        ["Explain simply", "Explain the topic on my board for a senior school class in simple words, in what I could say in two minutes."],
        ["Board questions", "Give me three questions of rising difficulty on this topic, with worked answers using the engine."],
        ["Real-life examples", "Give three real-life examples of this topic that students in India would recognise, with numbers you can compute."],
        ["Common mistakes", "What mistakes do students usually make on this topic, and how can I show each one with an ASM Teach experiment?"],
      ],
    });

    return () => {
      clearInterval(autosave); store.set(key, board.data);
      unlisten(); aiCleanup(); board.destroy();
    };
  },
};
