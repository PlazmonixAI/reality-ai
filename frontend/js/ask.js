// "Ask Reality ASM": chat with the AI representative (POST /ask). The LLM picks engine tools; every number
// in the answer comes from those tool runs, which are shown under each reply.
import { el } from "./core/ui.js";
import { fmt } from "./core/format.js";
import { history as saved, toast } from "./core/session.js";

const EXAMPLES = [
  "How much delta-v does it take to go from LEO (300 km) to GEO?",
  "What is the pH of 0.1 M acetic acid?",
  "A bone has 30% of its carbon-14 left. How old is it?",
  "At what temperature does water boil on top of Mount Everest (33.7 kPa)?",
  "Integrate x^2 sin(x) from 0 to pi.",
];

export function show(v) {
  if (typeof v === "number") return fmt(v, 5);
  if (Array.isArray(v)) return `[${v.slice(0, 6).map(show).join(", ")}${v.length > 6 ? ", …" : ""}]`;
  if (v && typeof v === "object") {
    if ("n" in v && "first" in v && "last" in v) return `${v.n} values from ${show(v.first)} to ${show(v.last)}`;
    return `{ ${Object.entries(v).slice(0, 8).map(([k, x]) => `${k}: ${show(x)}`).join(", ")}${Object.keys(v).length > 8 ? ", …" : ""} }`;
  }
  return String(v);
}

export function toolCard(step) {
  const r = step.result || {};
  const main = "error" in r ? el("p", { class: "tool-error" }, r.error)
    : el("p", {}, el("b", {}, "result: "), show(r.result), r.units ? el("span", { class: "tool-units" }, `  (${r.units})`) : "");
  return el("details", { class: `tool-card ${step.ok ? "" : "failed"}` },
    el("summary", {}, `${step.ok ? "" : "Failed: "}${step.tool.replace(/^\w+\./, "").replace(/_/g, " ")}`, el("span", { class: "tool-args" }, show(step.args))),
    main,
    r.assumptions ? el("ul", {}, r.assumptions.map((a) => el("li", {}, a))) : "");
}

// Keep a saved conversation small: tool results are trimmed to what the cards show.
const trimCall = (c) => ({ tool: c.tool, ok: c.ok, args: c.args, result: c.result && ("error" in c.result
  ? { error: String(c.result.error).slice(0, 400) }
  : { result: JSON.parse(JSON.stringify(c.result.result ?? null, (k, v) => (Array.isArray(v) && v.length > 24 ? v.slice(0, 24) : v)) ?? "null"),
      units: c.result.units, assumptions: c.result.assumptions }) });

export function mountAsk(root, params = {}) {
  const history = [];
  const turns = [];
  let runId = null;
  const log = el("div", { class: "chat-log", role: "log", "aria-live": "polite" });
  const input = el("textarea", { class: "chat-input", rows: 2, placeholder: "Ask a physics, chemistry or maths question…", "aria-label": "Your question" });
  const send = el("button", { class: "btn primary", type: "submit" }, "Ask");
  const form = el("form", { class: "chat-form" }, input, send);
  const examples = el("div", { class: "chat-examples" }, EXAMPLES.map((q) => el("button", { class: "chip", type: "button", onclick: () => { input.value = q; input.focus(); } }, q)));
  root.append(el("div", { class: "ask-page" },
    el("div", { class: "hero" }, el("h1", {}, "Ask Reality ASM"),
      el("p", {}, "Ask in plain language. The AI representative chooses the engine's simulation tools, runs them, and explains the result. Every number comes from a real computation, shown below each answer.")),
    examples, log, form));

  const bubble = (who, ...kids) => { const b = el("div", { class: `bubble ${who}` }, ...kids); log.append(b); b.scrollIntoView({ block: "end", behavior: "smooth" }); return b; };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || send.disabled) return;
    await askOne(q);
  });

  function answerBubble(answer, calls, model) {
    bubble("bot", el("div", { class: "answer" }, answer || "(no answer)"),
      calls?.length ? el("div", { class: "tools" }, calls.map(toolCard)) : el("p", { class: "note" }, "No engine tools were used for this answer."),
      model ? el("p", { class: "model" }, `model: ${model}`) : "");
  }

  async function save() {
    const payload = { turns };
    const title = turns[0].q.length > 110 ? `${turns[0].q.slice(0, 107)}...` : turns[0].q;
    try {
      if (runId) await saved.update(runId, { payload, summary: { turns: turns.length } });
      else runId = (await saved.create({ kind: "ask", sim_id: "ask", title, payload, summary: { turns: turns.length } })).id;
    } catch { /* saving is best effort; the answer is already on screen */ }
  }

  async function askOne(q) {
    input.value = ""; send.disabled = true;
    bubble("user", q);
    const wait = bubble("bot pending", "Thinking and running simulations…");
    try {
      const res = await fetch("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, history: history.slice(-10) }) });
      if (res.status === 401) { location.href = `/login?next=${encodeURIComponent("/app/" + location.hash)}`; return; }
      const body = await res.json().catch(() => ({}));
      wait.remove();
      if (!res.ok) {
        const msg = res.status === 503 ? "The AI analyst isn't switched on yet. The simulations still work, and every number in them comes from the engine." : (body.detail || `Request failed (${res.status})`);
        bubble("bot error", typeof msg === "string" ? msg : JSON.stringify(msg));
        return;
      }
      history.push({ role: "user", content: q }, { role: "assistant", content: body.answer });
      answerBubble(body.answer, body.tool_calls, body.model);
      turns.push({ q, answer: body.answer, model: body.model, tool_calls: (body.tool_calls || []).map(trimCall) });
      save();
    } catch (err) {
      wait.remove();
      bubble("bot error", `Could not reach the server: ${err.message}`);
    } finally {
      send.disabled = false; input.focus();
    }
  }
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  input.focus();
  if (params.saved) { // reopen a saved conversation and carry on from it
    saved.get(params.saved).then((run) => {
      runId = run.id;
      for (const t of run.payload.turns || []) {
        bubble("user", t.q); answerBubble(t.answer, t.tool_calls, t.model);
        turns.push(t); history.push({ role: "user", content: t.q }, { role: "assistant", content: t.answer });
      }
    }).catch((e) => toast(e.message, "error"));
  }
  return null;
}
