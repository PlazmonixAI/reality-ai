// The /test team desk: live status cards, waitlist numbers and a launch checklist kept in this browser.
const $ = (s) => document.querySelector(s);
const TODO_KEY = "rasm.team.todo";

function card(name, state, text) {
  const c = document.querySelector(`[data-check="${name}"]`);
  c.dataset.state = state; // ok | warn | bad
  c.querySelector("p").textContent = text;
}

async function get(path) {
  const res = await fetch(path, { cache: "no-store" });
  return { ok: res.ok, status: res.status, text: res.ok ? await res.text() : "" };
}

async function checkSite() {
  try {
    const [home, robots, map] = await Promise.all([get("/"), get("/robots.txt"), get("/sitemap.xml")]);
    card("site", home.ok ? "ok" : "bad", home.ok ? `Main page is up on ${location.host}.` : `Main page answered ${home.status}.`);
    const pages = (map.text.match(/<loc>/g) || []).length;
    const good = robots.ok && map.ok && robots.text.includes("Sitemap:") && pages > 0;
    card("search", good ? "ok" : "warn", good ? `robots.txt and sitemap.xml are served (${pages} page). Submit the sitemap in Search Console.`
      : "robots.txt or sitemap.xml is missing. Rebuild the site and push.");
  } catch {
    card("site", "bad", "Couldn't reach the site.");
    card("search", "bad", "Couldn't reach the site.");
  }
}

const when = (iso) => (iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "–");

function showWaitlist(w) {
  if (!w.bound) {
    card("waitlist", "bad", "No KV namespace bound as WAITLIST, so emails are not saved.");
    $("#wl-latest").innerHTML = '<p class="muted small">Nothing to show until the WAITLIST binding exists.</p>';
    return;
  }
  card("waitlist", "ok", `Saving emails. ${w.count} so far.`);
  $("#wl-total").textContent = w.count;
  $("#wl-day").textContent = w.last_24h;
  $("#wl-week").textContent = w.last_7d;
  const box = $("#wl-latest");
  box.replaceChildren();
  if (!w.latest.length) { box.innerHTML = '<p class="muted small">No one yet. Share the link.</p>'; return; }
  const table = document.createElement("table");
  table.innerHTML = "<thead><tr><th>Email</th><th>Joined</th><th>Country</th></tr></thead>";
  const body = document.createElement("tbody");
  for (const p of w.latest) {
    const tr = document.createElement("tr");
    for (const v of [p.email, when(p.at), p.country || "–"]) { const td = document.createElement("td"); td.textContent = v; tr.append(td); }
    body.append(tr);
  }
  table.append(body);
  box.append(table);
  if (w.count > w.latest.length) { const n = document.createElement("p"); n.className = "muted small"; n.textContent = `Showing the latest ${w.latest.length}. The CSV has everyone.`; box.append(n); }
}

function showBackend(b) {
  if (!b.configured) { card("backend", "warn", "Not live yet. Simulations, AI, accounts and ASM Teach need it. The waitlist site works without it."); return; }
  if (b.ok) card("backend", "ok", `Answering in ${b.ms} ms with ${b.tools} engine tools.`);
  else card("backend", "bad", b.error ? `${b.error}.` : `Health check answered ${b.status}.`);
}

async function checkStatus() {
  try {
    const res = await fetch("/test/status.json", { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    const s = await res.json();
    showWaitlist(s.waitlist);
    showBackend(s.backend);
    $("#hub-when").textContent = `Checked ${when(s.checked_at)}.`;
  } catch (err) {
    card("waitlist", "bad", `Status check failed (${err.message}).`);
    card("backend", "bad", "Status check failed.");
  }
}

function todo() {
  let done = {};
  try { done = JSON.parse(localStorage.getItem(TODO_KEY) || "{}"); } catch { /* storage blocked */ }
  const items = [...document.querySelectorAll("#todo li")];
  const count = () => { $("#todo-count").textContent = `${items.filter((li) => li.querySelector("input").checked).length} of ${items.length} done`; };
  for (const li of items) {
    const box = li.querySelector("input");
    box.checked = !!done[li.dataset.id];
    box.addEventListener("change", () => {
      done[li.dataset.id] = box.checked;
      try { localStorage.setItem(TODO_KEY, JSON.stringify(done)); } catch { /* storage blocked */ }
      count();
    });
  }
  count();
}

function refresh() {
  for (const c of document.querySelectorAll(".hub-card")) { c.dataset.state = ""; c.querySelector("p").textContent = "Checking…"; }
  checkSite();
  checkStatus();
}

todo();
refresh();
$("#hub-refresh").addEventListener("click", refresh);
