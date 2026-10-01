// AI analyst panel shown beside every simulation. It sends the question together with a snapshot of the
// simulation (its title and the latest engine calls it made) to POST /ask; the model can quote those engine
// numbers and call further engine tools. Works with whichever LLM provider the server is configured for.
import { el } from "./ui.js";
import { recentCalls } from "./api.js";
import { toolCard } from "../ask.js";

const QUICK = [
  ["Analyse this", "Analyse what this simulation is showing right now. Explain the key numbers on screen, the physics or maths behind them, and anything notable or surprising."],
  ["Explain the science", "Explain the underlying science of this simulation in simple terms, with the governing equations, and relate it to the current numbers."],
  ["What should I try?", "Suggest three interesting experiments I can try in this simulation and what I should expect to see, based on its current state."],
];

let statusPromise = null;
const llmStatus = () => (statusPromise ||= fetch("/llm/status").then((r) => r.json()).catch(() => ({ configured: false })));

export function mountAiPanel(page, sim, { label = "AI analyst", quick = QUICK } = {}) {
  const history = [];
  const log = el("div", { class: "ai-log", role: "log", "aria-live": "polite" });
  const input = el("textarea", { class: "ai-input", rows: 2, placeholder: `Ask about ${sim.title}…`, "aria-label": `Ask the ${label}` });
  const send = el("button", { class: "ai-send", type: "submit" }, "Send");
  const note = el("div", { class: "ai-note" });
  const panel = el("aside", { class: "ai-panel", "aria-label": label },
    el("div", { class: "ai-head" }, el("div", {}, el("b", {}, label), el("small", {}, sim.title)),
      el("button", { class: "ai-x", type: "button", "aria-label": `Close ${label}`, onclick: () => toggle(false) }, "×")),
    note,
    el("div", { class: "ai-quick" }, quick.map(([label, q]) => el("button", { class: "ai-chip", type: "button", onclick: () => askIt(q, label) }, label))),
    log,
    el("form", { class: "ai-form", onsubmit: (e) => { e.preventDefault(); askIt(input.value.trim()); } }, input, send));
  const tab = el("button", { class: "ai-tab", type: "button", onclick: () => toggle(), title: `Open the ${label}` }, label.toUpperCase());
  page.append(panel, tab);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askIt(input.value.trim()); } });

  llmStatus().then((s) => {
    note.textContent = s.configured ? `${s.provider?.toUpperCase()} · ${s.model}` : `The AI analyst isn't switched on for this server yet.`;
    note.classList.toggle("warn", !s.configured);
  });

  function toggle(open = !panel.classList.contains("open")) { panel.classList.toggle("open", open); tab.classList.toggle("hidden", open); if (open) input.focus(); }
  const bubble = (who, ...kids) => { const b = el("div", { class: `ai-msg ${who}` }, ...kids); log.append(b); log.scrollTop = log.scrollHeight; return b; };

  async function askIt(q, label) {
    if (!q || send.disabled) return;
    input.value = ""; send.disabled = true;
    bubble("user", label || q);
    const wait = bubble("bot pending", "Reading the simulation and thinking…");
    const context = { sim_id: sim.id, title: sim.title, blurb: sim.blurb, recent: recentCalls() };
    try {
      const r = await fetch("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, history: history.slice(-8), context }) });
      const body = await r.json().catch(() => ({}));
      wait.remove();
      if (!r.ok) { bubble("bot error", r.status === 503 ? "The AI isn't connected yet. Once the LLM keys are added on the server, I'll analyse this simulation for you." : (body.detail || `Request failed (${r.status})`)); return; }
      history.push({ role: "user", content: q }, { role: "assistant", content: body.answer });
      bubble("bot", el("div", { class: "ai-answer" }, body.answer || "(no answer)"), body.tool_calls?.length ? el("div", { class: "tools" }, body.tool_calls.map(toolCard)) : "");
    } catch (e) {
      wait.remove(); bubble("bot error", `Could not reach the server: ${e.message}`);
    } finally { send.disabled = false; }
  }
  return () => { panel.remove(); tab.remove(); };
}
