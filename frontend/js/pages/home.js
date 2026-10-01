// Home: a greeting, the latest saved work and the main places to go.
import { el } from "../core/ui.js";
import { api, currentUser, history, when } from "../core/session.js";
import { openLink, KIND_LABEL } from "./history.js";

const PLACES = [
  ["#/teach", "ASM Teach", "Coursework 1 to 4 in physics, chemistry and maths as live simulations, with a whiteboard and practice.", "book"],
  ["#/sims", "All simulations", "82 research simulations across physics, chemistry and mathematics.", "grid"],
  ["#/ask", "Ask the AI", "Ask a question in plain words; it runs the engine and explains the answer.", "chat"],
  ["#/sim/solarsystem", "Solar System", "Every planet and moon on any date, out to the stars and galaxies.", "planet"],
  ["#/sim/spaceflight", "Spaceflight Lab", "Build a rocket from parts or pick a real one, and fly it to orbit or the Moon.", "rocket"],
  ["#/company", "Mission Control", "Your space company: launch satellites, keep them flying, take pictures, send probes.", "sat"],
  ["#/challenges", "Challenges", "Set missions checked by the engine, from the Kármán line to Jupiter.", "flag"],
];
const ICON = {
  rocket: '<path d="M12 2c3 2 5 6 5 10l-2 3H9l-2-3c0-4 2-8 5-10z"/><circle cx="12" cy="9" r="1.6"/><path d="M9 15l-2 4 3-1M15 15l2 4-3-1"/>',
  sat: '<rect x="9" y="9" width="6" height="6" rx="1"/><path d="M3 7l4 4M17 13l4 4M7 11l-2 2 4 4 2-2M13 7l2-2 4 4-2 2"/>',
  planet: '<circle cx="12" cy="12" r="5"/><ellipse cx="12" cy="12" rx="10" ry="3.2" transform="rotate(-18 12 12)"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  chat: '<path d="M4 5h16v11H9l-5 4z"/>',
  book: '<path d="M4 5c3-1.5 6-1.5 8 0v14c-2-1.5-5-1.5-8 0zM12 5c2-1.5 5-1.5 8 0v14c-3-1.5-6-1.5-8 0"/>',
};
export const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[name] || ""}</svg>`;

export default {
  title: "Home",
  mount(root) {
    const recent = el("div", { class: "recent" }, el("p", { class: "muted" }, "Loading your latest work…"));
    const status = el("div", { class: "home-status" });
    const hello = el("h1", {}, "Welcome");
    root.append(el("div", { class: "home" },
      el("div", { class: "home-head" }, hello, el("p", { class: "muted" }, "Pick up where you left off, or start something new.")),
      status,
      el("div", { class: "places" }, PLACES.map(([href, title, text, ic]) => el("a", { class: "place", href },
        el("span", { class: "place-icon", html: icon(ic) }), el("b", {}, title), el("span", {}, text)))),
      el("h2", { class: "section-title" }, "Recent", el("a", { href: "#/history", class: "more" }, "See all history")),
      recent));
    let alive = true;
    currentUser().then((u) => {
      const h = new Date().getHours();
      hello.textContent = `${h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"}, ${u.name.split(" ")[0]}`;
    }).catch(() => {});
    history.list({ limit: 6 }).then(({ items }) => {
      if (!alive) return;
      recent.replaceChildren(...(items.length ? items.map((r) => el("a", { class: "recent-item", href: openLink(r) },
        el("span", { class: `kind k-${r.kind}` }, KIND_LABEL[r.kind] || r.kind), el("b", {}, r.title), el("small", {}, when(r.updated_at))))
        : [el("p", { class: "muted" }, "Nothing saved yet. Flights in the Spaceflight Lab save themselves; in any other simulation press Save on the right edge.")]));
    }).catch((e) => recent.replaceChildren(el("p", { class: "muted" }, e.message)));
    Promise.all([api("/api/company").catch(() => null), api("/api/challenges").catch(() => null)]).then(([c, ch]) => {
      if (!alive) return;
      const bits = [];
      if (c?.company) {
        const n = c.company.counts || {};
        const active = (n.orbiting || 0) + (n["in cruise"] || 0) + (n.scheduled || 0);
        bits.push(el("a", { href: "#/company", class: "stat" }, el("b", {}, String(active)), el("span", {}, `active spacecraft at ${c.company.name}`)));
      } else bits.push(el("a", { href: "#/company", class: "stat" }, el("b", {}, "New"), el("span", {}, "Found your space company")));
      if (ch) bits.push(el("a", { href: "#/challenges", class: "stat" }, el("b", {}, `${ch.completed}/${ch.total}`), el("span", {}, "challenges complete")));
      status.replaceChildren(...bits);
    });
    return () => { alive = false; };
  },
};
