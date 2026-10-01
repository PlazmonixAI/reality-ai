// Listen mode: the teacher talks, ASM Teach follows. The browser's own speech recognition turns speech into text;
// each finished sentence goes to the engine's teach.listen, which picks the experiment, the values or the equation.
// One listener for the whole Teach section, so it keeps listening while the page changes.
import { el } from "../core/ui.js";
import { simulate } from "../core/api.js";

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null, on = false, handler = null, current = null;
const pill = el("div", { class: "listen-pill", hidden: true, role: "status", "aria-live": "polite" });
const heardEl = el("span", { class: "listen-heard" }, "Listening…");
const stopBtn = el("button", { type: "button", class: "btn small", onclick: () => stop() }, "Stop");
pill.append(el("span", { class: "listen-dot" }), heardEl, stopBtn);

export const listenSupported = !!Recognition;

/** The page that is open registers what to do with what was understood. */
export function setListenHandler(fn, currentId = null) {
  handler = fn; current = currentId;
  if (!document.body.contains(pill)) document.body.append(pill);
  return () => { if (handler === fn) { handler = null; current = null; } };
}

export function listening() { return on; }

export function listenButton() {
  const btn = el("button", { type: "button", class: "btn small listen-btn", title: listenSupported ? "ASM Teach follows what you say" : "Speech recognition needs Chrome or Edge" }, "Listen");
  const sync = () => { btn.classList.toggle("on", on); btn.textContent = on ? "Listening" : "Listen"; };
  btn.addEventListener("click", () => { on ? stop() : start(); sync(); });
  document.addEventListener("teach-listen", sync);
  sync();
  return btn;
}

function start() {
  if (!Recognition) { show("This browser has no speech recognition. Use Chrome or Edge, or type the equation."); pill.hidden = false; return; }
  rec = new Recognition();
  rec.lang = "en-IN";
  rec.continuous = true;
  rec.interimResults = true;
  rec.onresult = (e) => {
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i], text = r[0].transcript.trim();
      if (!text) continue;
      if (r.isFinal) understand(text); else show(`“${text}”`);
    }
  };
  rec.onerror = (e) => { if (e.error === "not-allowed" || e.error === "service-not-allowed") { show("Microphone access was refused."); stop(); } };
  rec.onend = () => { if (on) { try { rec.start(); } catch { /* already restarting */ } } };
  on = true; pill.hidden = false; show("Listening… say an equation, a topic or a value.");
  try { rec.start(); } catch { /* started */ }
  document.dispatchEvent(new Event("teach-listen"));
}

function stop() {
  on = false;
  try { rec?.stop(); } catch { /* not running */ }
  rec = null; pill.hidden = true;
  document.dispatchEvent(new Event("teach-listen"));
}

function show(text) { heardEl.textContent = text; }

async function understand(text) {
  show(`“${text}”`);
  try {
    const r = (await simulate("teach", "listen", { transcript: text, current })).result;
    show(r.action === "none" ? `“${text}”` : `“${text}” → ${r.say}`);
    if (r.action !== "none") handler?.(r);
  } catch (err) { show(err.message); }
}
