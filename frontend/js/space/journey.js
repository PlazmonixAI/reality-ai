// Journey: a playable tour of the Universe Map. It starts with the Big Bang (physics.cosmic_history), then flies
// in from the edge of the observable universe through the galaxies, the Milky Way and the nearby stars to the
// Solar System, and visits its belts and planets. Every number in the captions comes from the engine; the
// browser only moves the camera and draws.
import * as THREE from "three";
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";

const CHAPTERS = [["bigbang", "Big Bang"], ["cosmos", "Universe"], ["galaxies", "Galaxies"], ["milkyway", "Milky Way"], ["stars", "Stars"], ["solar", "Solar System"]];
const SPEEDS = [1, 2, 4];
const LY_AU = 63241.077;
const smooth = (k) => k * k * (3 - 2 * k);
const commas = (n) => Math.round(n).toLocaleString("en-US");

export function fmtTime(s) {
  const y = s / 31557600;
  if (s < 1e-3) { const e = Math.floor(Math.log10(s)); return `${fmt(s / 10 ** e, 3)} × 10${sup(e)} s`; }
  if (s < 120) return `${fmt(s, 3)} s`;
  if (s < 7200) return `${fmt(s / 60, 3)} minutes`;
  if (y < 1) return `${fmt(s / 86400, 3)} days`;
  if (y < 1e6) return `${commas(y)} years`;
  if (y < 1e9) return `${fmt(y / 1e6, 3)} million years`;
  return `${fmt(y / 1e9, 4)} billion years`;
}
const SUP = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
const sup = (n) => String(n).split("").map((c) => SUP[c]).join("");
const sci = (v) => { const e = Math.floor(Math.log10(v)); return e < 5 ? commas(v) : `${fmt(v / 10 ** e, 3)} × 10${sup(e)}`; };
export function fmtSize(ly) {
  if (ly < 0.01) return `${fmt(ly * LY_AU, 3)} AU (Sun–Earth distances)`;
  if (ly < 1e6) return `${fmt(ly, 3)} light years`;
  if (ly < 1e9) return `${fmt(ly / 1e6, 3)} million light years`;
  return `${fmt(ly / 1e9, 3)} billion light years`;
}

export function createJourney({ rootEl, universe, goLevel, getLevel, solar }) {
  let token = 0, paused = false, speed = 0, running = false, chapter = 0, hist = null;
  const cancelled = (t) => t !== token;
  class Stop extends Error {}

  // ---------- overlay ----------
  const canvas = el("canvas", { class: "jr-canvas", hidden: true });
  const title = el("h3", {}), lines = el("div", { class: "jr-lines" }), note = el("p", { class: "jr-note" });
  const caption = el("div", { class: "jr-caption", "aria-live": "polite" }, title, lines, note);
  const chips = CHAPTERS.map(([, name], i) => el("button", { type: "button", class: "jr-chip", onclick: () => play(i) }, name));
  const bPause = el("button", { type: "button", class: "jr-btn", title: "Pause or play (Space)", "aria-label": "Pause", onclick: () => togglePause() }, "❚❚");
  const bSpeed = el("button", { type: "button", class: "jr-btn", title: "Speed (S)", onclick: () => { speed = (speed + 1) % SPEEDS.length; bSpeed.textContent = `${SPEEDS[speed]}×`; } }, "1×");
  const bar = el("div", { class: "jr-bar" },
    el("button", { type: "button", class: "jr-btn", title: "Previous chapter (←)", "aria-label": "Previous chapter", onclick: () => play(Math.max(0, chapter - 1)) }, "⏮"),
    bPause, el("button", { type: "button", class: "jr-btn", title: "Next chapter (→)", "aria-label": "Next chapter", onclick: () => play(Math.min(CHAPTERS.length - 1, chapter + 1)) }, "⏭"),
    bSpeed, el("div", { class: "jr-chips" }, ...chips),
    el("button", { type: "button", class: "jr-btn jr-exit", title: "Leave the journey (Esc)", onclick: () => stop() }, "Explore freely ✕"));
  const box = el("div", { class: "jr hidden" }, canvas, caption, bar);
  rootEl.append(box);

  function say(t, rows = [], n = "") {
    title.textContent = t;
    lines.replaceChildren(...rows.filter(Boolean).map(([k, v]) => el("div", { class: "jr-row" }, el("span", {}, k), el("b", {}, v))));
    note.textContent = n;
    caption.classList.remove("show"); void caption.offsetWidth; caption.classList.add("show");
  }
  function togglePause() { paused = !paused; bPause.textContent = paused ? "▶" : "❚❚"; bPause.setAttribute("aria-label", paused ? "Play" : "Pause"); }

  // ---------- time that respects pause, speed and cancellation ----------
  const frameP = () => new Promise((r) => requestAnimationFrame(r));
  async function tween(seconds, fn, t) {
    let k = 0, last = performance.now();
    while (k < 1) {
      await frameP();
      if (cancelled(t)) throw new Stop();
      const now = performance.now(), dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (!paused) k = Math.min(1, k + (dt * SPEEDS[speed]) / seconds);
      fn(k);
    }
  }
  const wait = (seconds, t) => tween(seconds, () => {}, t);
  async function until(test, t, seconds = 25) {
    const end = performance.now() + seconds * 1000;
    while (!test()) { await frameP(); if (cancelled(t)) throw new Stop(); if (performance.now() > end) return false; }
    return true;
  }
  async function toLevel(i, t) {
    if (getLevel() !== i) goLevel(i);
    await until(() => getLevel() === i, t, 5);
    await wait(0.5 / SPEEDS[speed], t);
    if (i > 0) universe.levels[i - 1].fly = null;
  }
  // fly a universe-scale camera along a path; onDist(distance) fires every frame for captions
  async function flight(L, from, to, seconds, t, { target = new THREE.Vector3(), targetTo = null, onDist = null, spin = 0 } = {}) {
    const tgt0 = target.clone(), tgt1 = (targetTo || target).clone();
    await tween(seconds, (k) => {
      const e = smooth(k), p = from.clone().lerp(to, e);
      if (spin) p.applyAxisAngle(new THREE.Vector3(0, 1, 0), spin * e);
      L.camera.position.copy(p); L.controls.target.copy(tgt0.clone().lerp(tgt1, e));
      onDist?.(p.distanceTo(L.controls.target), k);
    }, t);
  }
  // fire each caption once, when the camera comes closer than its distance
  function crossings(items, show) {
    const done = new Set();
    return (d) => { for (const it of items) if (!done.has(it) && d <= it.d) { done.add(it); show(it); } };
  }

  // ---------- chapter 1: the Big Bang ----------
  async function bigBang(t) {
    canvas.hidden = false;
    universe.prefetch?.(); // the next chapters' data load while the universe is young
    hist ||= (await simulate("physics", "cosmic_history", { n_frames: 240 })).result;
    const H = hist, ctx = canvas.getContext("2d"), N = 1400;
    const parts = Array.from({ length: N }, (_, i) => ({ a: (i * 2.399963) % (Math.PI * 2), r: Math.sqrt(((i * 7919) % N) / N), tw: (i * 13) % 17 }));
    const cmbIdx = H.frames.findIndex((f) => f.time_s >= H.epochs.find((e) => e.key === "cmb").time_s);
    const endIdx = H.frames.findIndex((f) => f.time_s >= H.epochs.find((e) => e.key === "firstgalaxy").time_s);
    const logS0 = Math.log10(H.frames[0].observable_patch_size_ly), logS1 = Math.log10(H.frames[endIdx].observable_patch_size_ly);
    const planck = H.epochs[0];
    say(planck.name, [["Time", fmtTime(planck.time_s)], ["Temperature", `${sci(planck.temperature_k)} K`]], planck.what);
    const shown = new Set([planck.key]);
    const draw = (fi, flash) => {
      const dpr = Math.min(1.5, devicePixelRatio), cw = Math.round(canvas.clientWidth * dpr), ch = Math.round(canvas.clientHeight * dpr);
      if (canvas.width !== cw || canvas.height !== ch) { canvas.width = cw; canvas.height = ch; }
      const W = cw, Hh = ch;
      const f = H.frames[Math.min(H.frames.length - 1, Math.floor(fi))], cx = W / 2, cy = Hh / 2, R0 = Math.min(W, Hh) * 0.46;
      const R = R0 * Math.max(0.01, (Math.log10(f.observable_patch_size_ly) - logS0) / (logS1 - logS0));
      ctx.fillStyle = "#000"; ctx.fillRect(0, 0, W, Hh);
      const hot = Math.max(0, Math.min(1, (Math.log10(f.temperature_k) - 3) / 12)); // 1,000 K → 10¹⁵ K: how much the plasma glows
      const col = f.colour || "#000000";
      if (f.colour) { // the glowing fireball
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 1.15);
        g.addColorStop(0, `rgba(255,255,255,${0.35 + 0.65 * hot})`); g.addColorStop(0.35, col); g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.globalAlpha = 0.25 + 0.75 * hot; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * 1.15, 0, 7); ctx.fill(); ctx.globalAlpha = 1;
      }
      // matter: a grainy fog that clumps, then lights up as stars and galaxies after the first stars
      const lit = f.time_s >= H.epochs.find((e) => e.key === "firststars").time_s;
      const clump = Math.max(0, Math.min(1, (fi - cmbIdx) / Math.max(1, endIdx - cmbIdx)));
      for (const p of parts) {
        const rr = R * p.r * (1 - 0.25 * clump * Math.sin(p.a * 6 + p.r * 9) ** 2);
        const x = cx + rr * Math.cos(p.a), y = cy + rr * Math.sin(p.a);
        ctx.fillStyle = lit ? (p.tw % 5 === 0 ? "#ffe9c2" : "#9fc3ff") : f.colour ? "rgba(255,255,255,0.55)" : "rgba(120,130,160,0.35)";
        const s = (lit ? 1.6 + (p.tw % 3) : 1.1) * dpr;
        ctx.globalAlpha = lit ? 0.6 + 0.4 * Math.sin(performance.now() / 300 + p.tw) : 0.8; ctx.fillRect(x, y, s, s);
      }
      ctx.globalAlpha = 1;
      if (flash > 0) { ctx.fillStyle = `rgba(255,255,255,${flash})`; ctx.fillRect(0, 0, W, Hh); }
      return f;
    };
    await tween(2.5, (k) => draw(0, 1 - k), t);
    const tick = async (from, to, seconds) => tween(seconds, (k) => {
      const fi = from + (to - from) * k, f = draw(fi, 0);
      for (const e of H.epochs) {
        if (shown.has(e.key) || e.time_s > f.time_s || e.key === "today") continue;
        shown.add(e.key);
        say(e.name, [["Time after the Big Bang", fmtTime(e.time_s)], ["Temperature", `${sci(e.temperature_k)} K`],
          e.observable_patch_size_ly && ["Today's observable universe was", fmtSize(e.observable_patch_size_ly)]], e.what);
      }
    }, t);
    await tick(0, cmbIdx, 34);
    await tick(cmbIdx, endIdx, 18);
    await tween(2, (k) => { draw(endIdx, 0); canvas.style.opacity = String(1 - k); }, t);
    canvas.hidden = true; canvas.style.opacity = "1";
  }

  // ---------- chapter 2: the observable universe (units: billion ly) ----------
  async function cosmos(t) {
    await toLevel(4, t);
    const L = universe.levels[3], D = universe.data;
    await until(() => D.cosmology && L.ready, t);
    const c = D.cosmology, A = D.atlas || {};
    say("The observable universe, today", [["Radius", `${fmt(c.observable_universe_radius_gly, 4)} billion light years`], ["Age", `${fmt(c.age_now_gyr, 4)} billion years`]],
      "Everything whose light has had time to reach us. Space has stretched while the light travelled, so it is far bigger than 13.8 billion light years.");
    const items = [
      { d: c.cmb_comoving_distance_gly * 1.02, f: () => say("The cosmic microwave background", [["Now", `${fmt(c.cmb_comoving_distance_gly, 4)} billion light years away`], ["Redshift", `z = ${c.cmb_redshift}`]], "The glow from when the universe turned transparent. Every direction we look ends here.") },
      ...(A.far_objects || []).map((o) => ({ d: o.distance_mly / 1000, f: () => say(o.name, [["Redshift", `z = ${o.redshift}`], ["Now", `${fmt(o.distance_mly / 1000, 4)} billion light years away`]], o.note) })),
      ...(A.structures || []).filter((s) => s.distance_mly > 2500).map((s) => ({ d: s.distance_mly / 1000, f: () => say(s.name, [["Distance", `${fmt(s.distance_mly / 1000, 4)} billion light years`], ["Size", `${commas(s.radius_mly * 2)} million light years across`]], s.note) })),
    ].sort((a, b) => b.d - a.d);
    const cross = crossings(items, (it) => it.f());
    await flight(L, new THREE.Vector3(30, 70, 150), new THREE.Vector3(1.2, 1.1, 3.4), 30, t, { onDist: cross, spin: 0.8 });
  }

  // ---------- chapter 3: galaxies (units: million ly) ----------
  async function galaxies(t) {
    await toLevel(3, t);
    const L = universe.levels[2], D = universe.data;
    await until(() => D.galaxies && L.ready, t);
    const G = D.galaxies, A = D.atlas || {};
    say("Galaxies, at their measured distances", [["Galaxies on the map", commas(G.count)], ["Farthest", `${commas(Math.max(...G.distance_mly))} million light years`]],
      "Each dot is a real galaxy placed where it is measured to be, so the clusters, walls and empty voids are real.");
    const famous = G.name.map((n, i) => [n, i]).filter(([, i]) => G.common_name?.[i] && G.distance_mly[i] > 2).map(([n, i]) => ({
      d: G.distance_mly[i] * 1.6, f: () => say(G.common_name[i], [["Catalogue", n], ["Distance", `${fmt(G.distance_mly[i], 4)} million light years`], ["Type", G.type[i] || "–"]], "Light from it set out that many million years ago."),
    }));
    const pick = famous.sort((a, b) => b.d - a.d).filter((_, k, arr) => k % Math.max(1, Math.floor(arr.length / 7)) === 0);
    const structs = (A.structures || []).filter((s) => s.distance_mly <= 2500 && s.distance_mly > 3).map((s) => ({ d: s.distance_mly * 1.4, f: () => say(s.name, [["Distance", `${fmt(s.distance_mly, 4)} million light years`], ["Size", `${commas(s.radius_mly * 2)} million light years across`]], s.note) }));
    const cross = crossings([...pick, ...structs].sort((a, b) => b.d - a.d), (it) => it.f());
    await flight(L, new THREE.Vector3(-900, 900, 2400), new THREE.Vector3(12, 8, 30), 30, t, { onDist: cross, spin: -0.6 });
    const and = G.name.findIndex((n, i) => (G.common_name?.[i] || n).startsWith("Andromeda"));
    if (and >= 0) {
      const p = universe.toScene(G.x_mly[and], G.y_mly[and], G.z_mly[and]);
      say("The Local Group", [["Andromeda", `${fmt(G.distance_mly[and], 4)} million light years`], ["Members", "the Milky Way, Andromeda, Triangulum and about 80 dwarfs"]], "Our own small group of galaxies. Andromeda is falling towards us.");
      await flight(L, L.camera.position.clone(), p.clone().multiplyScalar(0.5).add(new THREE.Vector3(0.6, 1.4, 2.6)), 8, t, { target: new THREE.Vector3(), targetTo: p.clone().multiplyScalar(0.5) });
      await wait(3, t);
    }
  }

  // ---------- chapter 4: the Milky Way (units: kpc) ----------
  async function milkyWay(t) {
    await toLevel(2, t);
    const L = universe.levels[1], D = universe.data;
    await until(() => D.milkyWay && L.ready, t);
    const m = D.milkyWay, sun = universe.toScene(...m.sun_position_kpc);
    say("The Milky Way", [["Across (model disc)", `about ${commas(m.disc_diameter_ly)} light years`], ["Globular clusters shown", String(m.globular_clusters.name.length)]],
      "A barred spiral of a few hundred billion stars, seen from outside, where no telescope has ever been.");
    await flight(L, new THREE.Vector3(60, 160, 260), new THREE.Vector3(0, 32, 30), 14, t, { spin: 0.9 });
    say("Sagittarius A*", [["Distance from the Sun", `${commas(m.sun_distance_ly)} light years`]], "A black hole of about four million Suns sits at the very centre.");
    await wait(4, t);
    say("The Sun's orbit", [["Speed", `${fmt(m.circular_speed_at_sun_km_s, 4)} km/s`], ["One lap (a galactic year)", `${fmt(m.galactic_year_myr, 4)} million years`]],
      "The Sun circles the centre in the disc, between two spiral arms.");
    await flight(L, L.camera.position.clone(), sun.clone().add(new THREE.Vector3(0.8, 1.6, 2.4)), 10, t, { target: new THREE.Vector3(), targetTo: sun });
    await wait(2, t);
  }

  // ---------- chapter 5: the nearby stars (units: light years) ----------
  async function stars(t) {
    await toLevel(1, t);
    const L = universe.levels[0], D = universe.data;
    await until(() => D.stars && L.ready, t);
    const S = D.stars, A = D.atlas || {};
    say("Our stellar neighbourhood", [["Stars on the map", commas(S.count)]], "Real stars at their measured distances. The constellations are only patterns seen from Earth: their stars are far apart in depth.");
    const want = ["Deneb", "Rigel", "Betelgeuse", "Polaris", "Aldebaran", "Arcturus", "Vega", "Sirius", "Proxima Centauri"];
    const items = want.map((nm) => S.name.findIndex((n) => n === nm || n.startsWith(nm))).filter((i) => i >= 0).map((i) => ({
      d: S.distance_ly[i] * 1.5 + 2, f: () => say(S.name[i], [["Distance", `${fmt(S.distance_ly[i], 4)} light years`], ["Temperature", `${commas(S.temperature_k[i])} K`], ["Luminosity", `${fmt(S.luminosity_solar[i], 3)} × Sun`]], `The light you see left it ${fmt(S.distance_ly[i], 3)} years ago.`),
    }));
    for (const dname of ["Orion Nebula", "Pleiades"]) {
      const d = (A.deep_sky || []).find((x) => x.name === dname && x.distance_ly);
      if (d) items.push({ d: d.distance_ly * 1.3, f: () => say(d.name, [["Distance", `${commas(d.distance_ly)} light years`], ["Type", d.type]], "") });
    }
    const exo = A.exoplanets;
    if (exo) items.push({ d: 60, f: () => say("Stars with planets", [["Planetary systems on the map", commas(exo.count)], ["Planets in them", commas(exo.planet_count)]], "The green dots: every star known to have planets.") });
    const cross = crossings(items.sort((a, b) => b.d - a.d), (it) => it.f());
    await flight(L, new THREE.Vector3(400, 500, 1500), new THREE.Vector3(0.6, 0.8, 2.2), 30, t, { onDist: cross, spin: 0.7 });
  }

  // ---------- chapter 6: the Solar System ----------
  async function solarSystem(t) {
    await toLevel(0, t);
    const { camera, controls, select, bodies, stopFly, sceneOfAU, beltNames } = solar;
    stopFly();
    const auOf = (d) => (d / 40) ** (1 / 0.55); // inverse of the map's distance compression
    say("The edge of the Sun's family", [], "We arrive from the stars, through a cloud of comets so faint it has never been seen.");
    const items = [
      ...beltNames().filter((b) => b.au > 30).map((b) => ({ d: sceneOfAU(b.au) * 1.15, f: () => say(b.name, [["Distance from the Sun", b.span]], b.note) })),
    ].sort((a, b) => b.d - a.d);
    const cross = crossings(items, (it) => it.f());
    const from = new THREE.Vector3(9000, 7000, 21000), to = new THREE.Vector3(0, 150, 330);
    await tween(26, (k) => {
      const e = smooth(k); camera.position.copy(from.clone().lerp(to, e)); controls.target.set(0, 0, 0);
      cross(camera.position.length());
    }, t);
    const tourStops = ["neptune", "uranus", "saturn", "jupiter", "BELT", "mars", "earth", "moon", "venus", "mercury", "sun"];
    for (const id of tourStops) {
      if (id === "BELT") {
        const b = beltNames().find((x) => x.key === "main belt");
        stopFly(); select(null); await wait(1.5, t);
        if (b) say(b.name, [["Distance from the Sun", b.span]], b.note);
        await wait(5, t); continue;
      }
      const B = bodies[id];
      if (!B?.group) continue;
      select(id);
      const d = B.data;
      say(d.name, [
        ["Radius", `${commas(d.radius_km)} km`], d.distance_sun_au !== undefined && id !== "sun" && ["From the Sun", `${fmt(d.distance_sun_au, 4)} AU`],
        d.orbital_period_days && [id === "moon" ? "Orbits Earth in" : "Year", d.orbital_period_days > 700 ? `${fmt(d.orbital_period_days / 365.25, 4)} Earth years` : `${fmt(d.orbital_period_days, 4)} days`],
        d.mean_temperature_c !== undefined && ["Mean temperature", `${fmt(d.mean_temperature_c, 3)} °C`], d.moons !== undefined && ["Known moons", String(d.moons)],
      ], id === "earth" ? "Home: the only place we know of with life." : id === "sun" ? "Our star: 99.86% of the Solar System's mass." : "");
      await wait(id === "earth" ? 9 : 6.5, t);
    }
    select("earth");
    say("Your turn", [], "The journey is over. Drag to look around, scroll or pinch to zoom, click anything to read about it.");
    await wait(4, t);
  }

  const RUN = [bigBang, cosmos, galaxies, milkyWay, stars, solarSystem];
  async function play(i) {
    const t = ++token; chapter = i; paused = false; bPause.textContent = "❚❚";
    chips.forEach((c, k) => c.classList.toggle("on", k === i));
    canvas.hidden = i !== 0;
    try {
      for (let k = i; k < RUN.length; k++) {
        chapter = k; chips.forEach((c, j) => c.classList.toggle("on", j === k));
        await RUN[k](t);
      }
      stop();
    } catch (e) {
      if (!(e instanceof Stop)) { console.error(e); say("The journey stopped", [], e.message); }
    }
  }
  function start(i = 0) {
    running = true; box.classList.remove("hidden"); rootEl.classList.add("journey-on");
    solar.setInteractive(false);
    play(i);
  }
  function stop() {
    token++; running = false; canvas.hidden = true; box.classList.add("hidden"); rootEl.classList.remove("journey-on");
    solar.setInteractive(true);
  }
  function key(e) {
    if (!running || e.target.closest?.("input, textarea, select")) return false;
    if (e.key === " ") togglePause();
    else if (e.key === "ArrowRight") play(Math.min(CHAPTERS.length - 1, chapter + 1));
    else if (e.key === "ArrowLeft") play(Math.max(0, chapter - 1));
    else if (e.key === "Escape") stop();
    else if (e.key === "s" || e.key === "S") bSpeed.click();
    else return false;
    e.preventDefault();
    return true;
  }
  return { start, stop, key, get running() { return running; }, get covering() { return running && !canvas.hidden; } };
}
