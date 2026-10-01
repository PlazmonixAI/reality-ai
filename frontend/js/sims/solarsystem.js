// Solar System 3D → the observable Universe. Every position, spin, orbit, star and galaxy comes from the engine
// (physics.solar_system, planet_moons, minor_bodies, asteroid_belt, star_catalog, milky_way, galaxy_catalog,
// cosmology); the browser renders them with three.js and interpolates between the engine's samples.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";
import { api, history as saved, toast } from "../core/session.js";
import { planetMaterial, atmosphereMaterial, ringMaterial, sunMaterial, glowTexture, pointsMaterial, hexToRgb, tailMaterial } from "../space/shaders.js";
import { createUniverseLevels } from "../space/universe.js";
import { buildSky } from "../space/sky.js";

const TEX = "assets/textures/";
const COLORS = { sun: "#ffcc55", mercury: "#9c8f86", venus: "#d8b27a", earth: "#4f8fe0", moon: "#b9b9b9", mars: "#d0643b",
  jupiter: "#d6a77a", saturn: "#e3cf96", uranus: "#8fd3e0", neptune: "#4a6fe0", pluto: "#bfa58a" };
const KIND_COLOR = { "natural satellite": "#b8c4d6", "dwarf planet": "#c9a27e", asteroid: "#9a9189", comet: "#7fd6ff", centaur: "#b58f6a", "Kuiper belt object": "#c98a6a" };
const SPEEDS = [ // simulated days per real second
  [0, "paused"], [1 / 86400, "real time"], [1 / 1440, "1 min / s"], [1 / 24, "1 hour / s"], [0.25, "6 hours / s"], [1, "1 day / s"],
  [7, "1 week / s"], [30, "1 month / s"], [182.6, "6 months / s"], [365.25, "1 year / s"],
];
const jdToDate = (jd) => new Date((jd - 2440587.5) * 86400000);
const dateToJd = (d) => d.getTime() / 86400000 + 2440587.5;
const AU_KM = 149597870.7;

// Surface appearance of each body (textures and shading only; sizes, spins and positions come from the engine)
const LOOK = {
  mercury: { map: "mercury.jpg", normal: "mercury_normal.jpg", airless: 1 },
  venus: { map: "venus_clouds.jpg", tint: [1.0, 0.94, 0.82], atmo: [1.0, 0.85, 0.55], atmoStrength: 0.9, shell: [1.0, 0.82, 0.5, 1.05] },
  moon: { map: "moon.jpg", normal: "moon_normal.jpg", airless: 1 },
  mars: { map: "mars.jpg", normal: "mars_normal.jpg", normalScale: 0.6, atmo: [0.95, 0.6, 0.45], atmoStrength: 0.35, shell: [0.95, 0.55, 0.4, 1.025] },
  jupiter: { map: "jupiter.jpg", atmo: [0.9, 0.8, 0.65], atmoStrength: 0.3, ring: ["jupiter_ring.png", 122500, 129360, 0.35] },
  saturn: { map: "saturn.jpg", atmo: [0.95, 0.85, 0.6], atmoStrength: 0.25, ring: ["saturn_ring.png", 74510, 140245, 1] },
  uranus: { map: "uranus.jpg", atmo: [0.6, 0.9, 1.0], atmoStrength: 0.45, ring: ["uranus_ring.png", 37812, 52392, 0.9] },
  neptune: { map: "neptune.jpg", atmo: [0.4, 0.6, 1.0], atmoStrength: 0.5, ring: ["neptune_ring.png", 40900, 62947, 0.9] },
  pluto: { map: "pluto.jpg", airless: 1 },
  titan: { map: "titan.jpg", tint: [1.0, 0.78, 0.45], atmo: [1.0, 0.65, 0.3], atmoStrength: 0.8, shell: [1.0, 0.6, 0.25, 1.08] },
  triton: { map: "triton.jpg", airless: 1, atmo: [0.6, 0.75, 1.0], atmoStrength: 0.15 },
  hyperion: { map: "icy.jpg", airless: 1, lumpy: 0.25 }, phoebe: { map: "asteroid.jpg", airless: 1, tint: [0.55, 0.55, 0.55], lumpy: 0.12 },
  proteus: { map: "asteroid.jpg", airless: 1, lumpy: 0.18 }, nereid: { map: "icy.jpg", airless: 1, lumpy: 0.1 },
  nix: { map: "icy.jpg", airless: 1, lumpy: 0.3 }, hydra: { map: "icy.jpg", airless: 1, lumpy: 0.3 },
  kerberos: { map: "icy.jpg", airless: 1, lumpy: 0.3 }, styx: { map: "icy.jpg", airless: 1, lumpy: 0.3 },
  phobos: { map: "phobos.jpg", airless: 1, lumpy: 0.18 }, deimos: { map: "deimos.jpg", airless: 1, lumpy: 0.15 },
  eris: { map: "icy.jpg", airless: 1 }, haumea: { map: "icy.jpg", airless: 1 },
  makemake: { map: "icy.jpg", airless: 1, tint: [1.0, 0.85, 0.72] }, gonggong: { map: "icy.jpg", airless: 1, tint: [1.0, 0.72, 0.6] },
  quaoar: { map: "icy.jpg", airless: 1, tint: [0.95, 0.78, 0.66] }, sedna: { map: "icy.jpg", airless: 1, tint: [1.0, 0.6, 0.45] },
};
const TEXTURED_MOONS = new Set(["io", "europa", "ganymede", "callisto", "mimas", "enceladus", "tethys", "dione", "rhea", "iapetus",
  "miranda", "ariel", "umbriel", "titania", "oberon", "charon", "ceres", "vesta"]);
function lookFor(id, kind) {
  if (LOOK[id]) return LOOK[id];
  if (TEXTURED_MOONS.has(id)) return { map: `${id}.jpg`, airless: 1 };
  if (kind === "comet") return { map: "asteroid.jpg", airless: 1, tint: [0.45, 0.43, 0.4], lumpy: 0.3 };
  return { map: kind === "centaur" || kind === "Kuiper belt object" ? "icy.jpg" : "asteroid.jpg", airless: 1, lumpy: 0.28 };
}

// Scene mapping: ecliptic (x, y, z) → three.js (x, z, −y) so the ecliptic is the horizontal plane
const toScene = (p) => new THREE.Vector3(p[0], p[2], -p[1]);
function compress(p, real) {
  const r = Math.hypot(p[0], p[1], p[2]);
  if (r === 0) return toScene([0, 0, 0]);
  const k = real ? 40 : (40 * Math.pow(r, 0.55)) / r; // AU → scene units (compressed keeps directions)
  return toScene([p[0] * k, p[1] * k, p[2] * k]);
}
function displayRadius(km, real) {
  if (real) return (km / AU_KM) * 40; // true scale: planets become specks
  if (km > 100000) return 5.2; // the Sun
  return Math.max(0.012, 0.55 * Math.pow(km / 6371, 0.45));
}
// Moon distance from its planet in compressed mode: logarithmic in planet radii, so every system fits between planets
const moonDistance = (aKm, planetKm, planetShown) => planetShown * (1.4 + 1.1 * Math.log(Math.max(1.05, aKm / planetKm)));

function interp(a, b, f) { // polar interpolation around the ecliptic pole (keeps orbits round between samples)
  const ra = Math.hypot(a[0], a[1]), rb = Math.hypot(b[0], b[1]);
  let ta = Math.atan2(a[1], a[0]), tb = Math.atan2(b[1], b[0]);
  if (tb - ta > Math.PI) tb -= 2 * Math.PI; else if (ta - tb > Math.PI) tb += 2 * Math.PI;
  const r = ra + (rb - ra) * f, t = ta + (tb - ta) * f;
  return [r * Math.cos(t), r * Math.sin(t), a[2] + (b[2] - a[2]) * f];
}
function lerp3(a, b, f) { return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]; }
function phaseSample(orbit, start, period, jd, polar = false) { // follow an orbit sampled at equal time steps
  const n = orbit.length;
  let f = ((jd - start) / period) % 1; if (f < 0) f += 1;
  const x = f * n, i = Math.floor(x) % n, j = (i + 1) % n;
  return (polar ? interp : lerp3)(orbit[i], orbit[j], x - Math.floor(x));
}

function lumpyGeometry(amount, seed) { // irregular small bodies: a sphere with smooth random bumps
  const g = new THREE.SphereGeometry(1, 48, 32), p = g.attributes.position;
  const k = [...Array(6)].map((_, i) => [Math.sin(seed * (i + 1) * 12.9898) * 43758.5453 % 1, Math.sin(seed * (i + 3) * 78.233) * 12345.678 % 1]);
  for (let i = 0; i < p.count; i++) {
    const v = new THREE.Vector3().fromBufferAttribute(p, i);
    let s = 1;
    k.forEach(([a, b], j) => { s += amount / (j + 1) * Math.sin((j + 1) * 2.1 * v.x + a * 6) * Math.cos((j + 1) * 1.7 * v.y + b * 6) * Math.sin((j + 2) * 1.3 * v.z + a * b * 9); });
    v.multiplyScalar(s * (1 - amount * 0.3 * Math.abs(v.y)));
    p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}

export function mountAt(root, startLevel = 0, params = {}) {
  const loader = new THREE.TextureLoader();
  const texCache = {};
  const tex = (name, srgb = true) => {
    if (texCache[name]) return texCache[name];
    const t = loader.load(TEX + name); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    return (texCache[name] = t);
  };

  // ---------- layout (full-bleed canvas with floating controls) ----------
  const view = el("div", { class: "ss-view" });
  const labels = el("div", { class: "ss-labels" });
  const dateBig = el("div", { class: "ss-date" }), timeSmall = el("div", { class: "ss-time" });
  const brand = el("div", { class: "ss-brand" }, "SOLAR SYSTEM ", el("b", {}, "3D"));
  const speedText = el("span", { class: "ss-speed-text" });
  const info = el("aside", { class: "ss-info hidden" });
  const list = el("div", { class: "ss-list hidden" });
  const status = el("div", { class: "ss-status" }, "Loading the Solar System…");
  const fade = el("div", { class: "ss-fade" });
  let simJd = dateToJd(new Date()), window_ = null, loading = false, firstLoad = true;
  try { // arriving from a Spaceflight Lab mission: open on its date
    const d = localStorage.getItem("reality-asm.solar-date");
    if (d) { localStorage.removeItem("reality-asm.solar-date"); simJd = dateToJd(new Date(d)); }
  } catch { /* storage unavailable */ }
  let speedIdx = 5, playing = true, showOrbits = true, showLabels = true, realScale = false, showMinor = true, showBelts = true;
  const tool = (icon, title, onclick) => el("button", { class: "ss-tool", type: "button", title, "aria-label": title, onclick }, icon);
  const bOrbits = tool("◯", "Orbits", () => { showOrbits = !showOrbits; bOrbits.classList.toggle("off", !showOrbits); orbitsGroup.visible = showOrbits; });
  const bLabels = tool("Aa", "Labels", () => { showLabels = !showLabels; bLabels.classList.toggle("off", !showLabels); labels.style.display = showLabels ? "" : "none"; });
  const bScale = tool("⤢", "Real scale (distances and sizes)", () => { realScale = !realScale; bScale.classList.toggle("on", realScale); rebuildScale(); });
  const bMinor = tool("☄", "Dwarf planets, asteroids and comets", () => { showMinor = !showMinor; bMinor.classList.toggle("off", !showMinor); minorGroup.visible = showMinor; minorOrbits.visible = showMinor; });
  const bBelts = tool("⁘", "Asteroid belt, trojans and Kuiper belt", () => { showBelts = !showBelts; bBelts.classList.toggle("off", !showBelts); beltPoints.visible = showBelts; });
  const bList = tool("☰", "All bodies", () => list.classList.toggle("hidden"));
  const bLaunch = tool("⇧", "Launch a rocket on this date (Spaceflight Lab)", () => {
    try { localStorage.setItem("reality-asm.mission-date", jdToDate(simJd).toISOString()); } catch { /* storage unavailable */ }
    location.hash = "#/sim/spaceflight";
  });
  const bHome = tool("⌂", "Whole Solar System", () => select(null));
  const bSave = tool("⇩", "Save this view to your history", async () => {
    const date = jdToDate(simJd);
    try {
      await saved.create({ kind: "space_view", sim_id: "solarsystem",
        title: `${selected && bodies[selected] ? bodies[selected].data.name : "Solar System"}, ${date.toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" })}`,
        payload: { jd: simJd, selected, level, real_scale: realScale, speed: speedIdx }, summary: { date: date.toISOString() } });
      toast("View saved to your history.");
    } catch (e) { toast(e.message, "error"); }
  });
  // the clock panel: date, rate and time controls in one place (top left)
  const bPlay = el("button", { class: "ss-btn", type: "button", "aria-label": "Play or pause", onclick: () => { playing = !playing; bPlay.textContent = playing ? "Hold" : "Run"; bPlay.classList.toggle("on", !playing); } }, "Hold");
  const rate = el("input", { class: "ss-rate", type: "range", min: 1, max: SPEEDS.length - 1, step: 1, value: speedIdx, "aria-label": "Rate of time", oninput: () => setSpeed(+rate.value) });
  const reverse = el("button", { class: "ss-btn", type: "button", title: "Run time backwards", onclick: () => { dir = -dir; reverse.classList.toggle("on", dir < 0); reverse.textContent = dir < 0 ? "Backward" : "Forward"; window_ = null; } }, "Forward");
  const today = el("button", { class: "ss-btn", type: "button", onclick: () => { simJd = dateToJd(new Date()); window_ = null; } }, "Now");
  const dateInput = el("input", { class: "ss-dateinput", type: "date", min: "1800-01-01", max: "2050-12-31", "aria-label": "Jump to date", onchange: () => { if (dateInput.value) { simJd = dateToJd(new Date(dateInput.value + "T12:00:00Z")); window_ = null; } } });
  const toolbar = el("div", { class: "ss-toolbar" }, bList, bHome, bOrbits, bLabels, bMinor, bBelts, bScale, bLaunch, bSave);
  const timebar = el("div", { class: "ss-clock" },
    el("div", { class: "ss-clock-head" }, el("span", {}, "Mission clock"), speedText), dateBig, timeSmall,
    el("div", { class: "ss-clock-rate" }, el("span", {}, "Rate"), rate),
    el("div", { class: "ss-clock-row" }, reverse, bPlay, today, dateInput));
  const ladder = el("nav", { class: "ss-ladder", "aria-label": "Scale" });
  const credit = el("div", { class: "ss-credit" }, "Engine: JPL elements, HYG stars, Celestia catalogues, ΛCDM · textures: NASA/JPL, USGS, Celestia (see CREDITS)");
  const rootEl = el("div", { class: "ss-root" }, view, labels, el("div", { class: "ss-top" }, brand),
    toolbar, ladder, list, info, status, timebar, credit, fade);
  root.append(rootEl);
  function setSpeed(i) { speedIdx = Math.max(1, Math.min(SPEEDS.length - 1, i)); speedText.textContent = SPEEDS[speedIdx][1]; rate.value = speedIdx; window_ = null; }
  let dir = 1;
  setSpeed(speedIdx);

  // ---------- three.js ----------
  const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  view.append(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.0005, 200000);
  camera.position.set(0, 120, 260);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 0.003; controls.maxDistance = 9000;
  scene.add(new THREE.AmbientLight(0x404050, 0.3));
  const sunLight = new THREE.PointLight(0xffffff, 3.2, 0, 0);
  scene.add(sunLight);
  const sky = new THREE.Group(); // real stars and the Milky Way band, centred on the camera
  scene.add(sky);
  const orbitsGroup = new THREE.Group(), minorGroup = new THREE.Group(), minorOrbits = new THREE.Group();
  orbitsGroup.add(minorOrbits);
  scene.add(orbitsGroup, minorGroup);
  const SUN_POS = new THREE.Vector3();

  const bodies = {}; // id → {group, tilt, spin, mesh, radiusKm, data, label, kind, parent, mats[]}
  const fx = { sun: null, clouds: null, rings: {} };
  function addLabel(id, name, color, cls = "") {
    const label = el("button", { class: `ss-label ${cls}`, type: "button", onclick: () => select(id) }, name);
    label.style.setProperty("--c", color);
    if (level === 0) labels.append(label); // other scales keep their own labels; this one is re-added on return
    return label;
  }
  function makeBody(d, kind = d.type) {
    const id = d.id, group = new THREE.Group(), tilt = new THREE.Group(), spin = new THREE.Group();
    group.add(tilt); tilt.add(spin);
    if (d.pole_ecliptic) tilt.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), toScene(d.pole_ecliptic).normalize());
    const look = lookFor(id, kind), mats = [];
    let mesh;
    if (id === "sun") {
      mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), sunMaterial(tex("sun.jpg")));
      const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
      glow.scale.set(7, 7, 1); group.add(glow);
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture([[0, "rgba(255,230,190,.35)"], [0.3, "rgba(255,170,80,.08)"], [1, "rgba(255,140,40,0)"]]), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
      halo.scale.set(18, 18, 1); group.add(halo);
      fx.sun = { glow, halo, mat: mesh.material };
    } else if (id === "earth") {
      const m = planetMaterial({ map: tex("earth_day.jpg"), nightMap: tex("earth_night.jpg"), specMap: tex("earth_water.png", false), atmo: [0.3, 0.55, 1.0], atmoStrength: 0.35, ambient: 0.02 });
      mats.push(m);
      mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 96), m);
      const clouds = new THREE.Mesh(new THREE.SphereGeometry(1.012, 128, 96), new THREE.MeshStandardMaterial({ color: 0xffffff, alphaMap: tex("earth_clouds.jpg", false), transparent: true, opacity: 0.95, depthWrite: false, roughness: 1 }));
      spin.add(clouds); fx.clouds = clouds;
      const shell = new THREE.Mesh(new THREE.SphereGeometry(1.06, 64, 48), atmosphereMaterial([0.35, 0.6, 1.0], 1.0));
      tilt.add(shell); mats.push(shell.material);
    } else {
      const m = planetMaterial({ map: tex(look.map), normalMap: look.normal ? tex(look.normal, false) : null, tint: look.tint, atmo: look.atmo, atmoStrength: look.atmoStrength || 0, airless: look.airless || 0, normalScale: look.normalScale || 1 });
      mats.push(m);
      mesh = new THREE.Mesh(look.lumpy ? lumpyGeometry(look.lumpy, id.length + id.charCodeAt(0)) : new THREE.SphereGeometry(1, 96, 64), m);
      if (look.shell) {
        const [r, g, b, size] = look.shell;
        const shell = new THREE.Mesh(new THREE.SphereGeometry(size, 64, 48), atmosphereMaterial([r, g, b], 1.0));
        tilt.add(shell); mats.push(shell.material);
      }
      if (look.ring) {
        const [file, innerKm, outerKm, opacity] = look.ring;
        const inner = innerKm / d.radius_km, outer = outerKm / d.radius_km;
        const rm = ringMaterial(tex(file), inner, outer, opacity);
        const ring = new THREE.Mesh(new THREE.RingGeometry(inner, outer, 256, 1), rm);
        ring.rotation.x = -Math.PI / 2;
        tilt.add(ring);
        m.uniforms.ringMap.value = rm.uniforms.ringMap.value; m.uniforms.useRing.value = 1;
        fx.rings[id] = { ring, rm, inner, outer };
      }
    }
    spin.add(mesh);
    group.userData.id = id; mesh.userData.id = id;
    (!COLORS[id] && kind !== "natural satellite" ? minorGroup : scene).add(group);
    const color = COLORS[id] || KIND_COLOR[kind] || "#b8c4d6";
    const label = addLabel(id, d.name, color, d.parent ? "moon" : COLORS[id] ? "" : "minor");
    return { group, tilt, spin, mesh, radiusKm: d.radius_km, data: d, label, kind, parent: d.parent || (id === "moon" ? "earth" : null), mats, color };
  }
  function orbitLine(points, color, opacity) {
    return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
  }
  function buildOrbit(d, group = orbitsGroup) {
    const line = orbitLine(d.orbit.map((p) => compress(p, realScale)), COLORS[d.id] || KIND_COLOR[d.type] || "#8899aa", COLORS[d.id] ? 0.45 : 0.07);
    line.userData = { id: d.id, raw: d.orbit };
    group.add(line);
    return line;
  }
  function placeMoon(moonId, rel) { // rel: planetocentric ecliptic AU → scene offset from the planet
    const b = bodies[moonId], p = bodies[b.parent];
    const r = Math.hypot(rel[0], rel[1], rel[2]);
    if (realScale) return toScene(rel).multiplyScalar(40);
    return toScene(rel).multiplyScalar(moonDistance(r * AU_KM, p.radiusKm, p.group.scale.x) / r);
  }
  function buildMoonOrbit(moonId) {
    const b = bodies[moonId], orbit = b.data.orbit;
    const line = orbitLine(orbit.map((q) => placeMoon(moonId, q)), b.color, 0.28);
    line.userData = { id: moonId, moon: true };
    orbitsGroup.add(line);
    b.orbitLine = line;
  }
  function rebuildScale() {
    for (const b of Object.values(bodies)) if (b?.group) b.group.scale.setScalar(displayRadius(b.radiusKm, realScale));
    for (const line of [...orbitsGroup.children, ...minorOrbits.children]) if (line.userData.raw) line.geometry.setFromPoints(line.userData.raw.map((p) => compress(p, realScale)));
    for (const b of Object.values(bodies)) if (b?.orbitLine) b.orbitLine.geometry.setFromPoints(b.data.orbit.map((q) => placeMoon(b.data.id, q)));
  }

  // ---------- engine data ----------
  let moonsData = null, belts = null, beltPoints = new THREE.Points();
  async function loadStatic() {
    const [moons, belt, stars, mw] = await Promise.all([
      simulate("physics", "planet_moons", { date: jdToDate(simJd).toISOString(), planet: "all", orbit_points: 256 }),
      simulate("physics", "asteroid_belt", { date: jdToDate(simJd).toISOString(), n_main: 2600, n_trojans: 700, n_kuiper: 1500, samples_per_orbit: 16 }),
      simulate("physics", "star_catalog", { max_magnitude: 6.5, nearby_ly: 100, frame: "ecliptic" }),
      simulate("physics", "milky_way", { n_points: 40000 }),
    ]);
    moonsData = moons.result.moons;
    for (const m of moonsData) { bodies[m.id] = makeBody(m, "natural satellite"); }
    belts = belt.result;
    buildBelts();
    sky.add(buildSky(stars.result, mw.result, mw.result.galactic_to_ecliptic, toScene));
    universe.setData({ stars: stars.result, milkyWay: mw.result });
    rebuildScale();
    for (const m of moonsData) buildMoonOrbit(m.id);
    buildList();
  }
  function buildBelts() {
    const n = belts.groups.reduce((s, g) => s + g.count, 0);
    const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), size = new Float32Array(n);
    const tints = [[0.62, 0.56, 0.5], [0.7, 0.6, 0.45], [0.55, 0.65, 0.8]];
    let k = 0;
    belts.groups.forEach((g, gi) => { for (let i = 0; i < g.count; i++, k++) { col.set(tints[gi].map((c) => c * (0.7 + 0.3 * Math.random())), k * 3); size[k] = gi === 2 ? 1.8 : 1.5; } });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("color", new THREE.BufferAttribute(col, 3)); geo.setAttribute("size", new THREE.BufferAttribute(size, 1));
    beltPoints = new THREE.Points(geo, pointsMaterial({ scale: 1, minSize: 1.2, maxSize: 3, opacity: 0.85 }));
    beltPoints.frustumCulled = false;
    scene.add(beltPoints);
  }
  function updateBelts() {
    if (!belts || !beltPoints.visible) return;
    const pos = beltPoints.geometry.attributes.position.array;
    let k = 0;
    for (const g of belts.groups) for (let i = 0; i < g.count; i++, k++) {
      const v = compress(phaseSample(g.orbits[i], belts.orbit_start_jd, g.period_days[i], simJd, true), realScale);
      pos[k * 3] = v.x; pos[k * 3 + 1] = v.y; pos[k * 3 + 2] = v.z;
    }
    beltPoints.geometry.attributes.position.needsUpdate = true;
  }
  // A window of positions around the current time (planets + small bodies, with tracks for interpolation)
  async function loadWindow(startJd) {
    if (loading) return;
    loading = true;
    const speed = SPEEDS[speedIdx][0] * dir;
    const span = Math.max(1, Math.abs(speed) * 20);
    const from = speed < 0 ? startJd - span : startJd;
    const iso = jdToDate(Math.min(Math.max(from, 2378497), 2469800 - span)).toISOString();
    const nTrack = Math.min(2000, Math.max(40, Math.ceil(span / 2)));
    try {
      const [r, mb] = await Promise.all([
        simulate("physics", "solar_system", { date: iso, span_days: span, n_track: nTrack, orbit_points: firstLoad ? 360 : 16 }),
        simulate("physics", "minor_bodies", { date: iso, kind: "all", span_days: span, n_track: nTrack, orbit_points: firstLoad ? 360 : 16 }),
      ]);
      const all = [...r.result.bodies, ...mb.result.bodies];
      if (firstLoad) {
        for (const d of r.result.bodies) { bodies[d.id] = makeBody(d, d.id === "moon" ? "natural satellite" : "planet"); if (d.orbit && d.id !== "moon") buildOrbit(d); }
        bodies.moon.data.orbit = r.result.bodies.find((d) => d.id === "moon").orbit;
        for (const d of mb.result.bodies) { bodies[d.id] = makeBody(d, d.type); buildOrbit(d, minorOrbits); if (d.type === "comet") addTail(d.id); }
        rebuildScale();
        buildMoonOrbit("moon");
        firstLoad = false; status.remove();
        loadStatic().then(() => { rebuildScale(); }).catch((e) => { status.textContent = `Engine error: ${e.message}`; rootEl.append(status); });
        buildList();
      }
      for (const d of all) Object.assign(bodies[d.id].data, d, { orbit: bodies[d.id].data.orbit || d.orbit });
      window_ = { t: r.track_times_jd, bodies: Object.fromEntries(all.map((d) => [d.id, d])) };
      if (selected) showInfo(selected);
    } catch (e) {
      status.textContent = `Engine error: ${e.message}`;
    } finally { loading = false; }
  }
  function sample(id) {
    const w = window_, t = w.t, tr = w.bodies[id].track, n = t.length;
    let f = (simJd - t[0]) / (t[n - 1] - t[0]) * (n - 1);
    f = Math.max(0, Math.min(n - 1.0001, f));
    const i = Math.floor(f);
    if (id === "moon") { // interpolate the Moon relative to Earth
      const e0 = w.bodies.earth.track[i], e1 = w.bodies.earth.track[i + 1];
      return lerp3(tr[i].map((v, k) => v - e0[k]), tr[i + 1].map((v, k) => v - e1[k]), f - i);
    }
    return interp(tr[i], tr[i + 1], f - i);
  }

  // Comet tails: anti-sunward, brighter closer to the Sun (inverse-square sunlight)
  const tails = {};
  function addTail(id) {
    const make = (color, len, width) => {
      const g = new THREE.ConeGeometry(width, len, 32, 1, true);
      g.translate(0, -len / 2, 0); g.rotateX(Math.PI); // apex at the nucleus, opening away from it
      const m = new THREE.Mesh(g, tailMaterial(color, 0.9));
      m.frustumCulled = false; scene.add(m); return m;
    };
    tails[id] = { ion: make([0.45, 0.7, 1.0], 1, 0.05), dust: make([1.0, 0.9, 0.7], 0.8, 0.12) };
  }
  function updateTails() {
    for (const [id, t] of Object.entries(tails)) {
      const b = bodies[id], r = b.data.distance_sun_au || 10;
      const strength = Math.min(1, 1 / (r * r)), vis = showMinor && r < 5;
      for (const [k, m] of Object.entries(t)) {
        m.visible = vis;
        if (!vis) continue;
        const dirV = b.group.position.clone().sub(SUN_POS).normalize();
        const len = (k === "ion" ? 3.5 : 2.2) * Math.min(1.5, 1 / r) * (realScale ? 0.3 : 1);
        m.position.copy(b.group.position);
        m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), k === "dust" ? dirV.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), 0.25).normalize() : dirV);
        m.scale.set(len * 0.5, len, len * 0.5);
        m.material.uniforms.strength.value = strength * (k === "ion" ? 0.9 : 0.6);
      }
    }
  }

  // ---------- selection, info panel and list ----------
  let selected = null;
  const LIST_GROUPS = [["Sun & planets", (b) => b.kind === "planet" || b.data.id === "sun"], ["Moons", (b) => b.kind === "natural satellite"],
    ["Dwarf planets", (b) => b.kind === "dwarf planet"], ["Asteroids & centaurs", (b) => ["asteroid", "centaur", "Kuiper belt object"].includes(b.kind)], ["Comets", (b) => b.kind === "comet"]];
  function buildList() {
    const all = Object.values(bodies).filter((b) => b?.data?.id);
    list.replaceChildren(...LIST_GROUPS.flatMap(([title, test]) => {
      const items = all.filter(test);
      if (!items.length) return [];
      return [el("div", { class: "ss-list-title" }, title), ...items.map((b) => el("button", { class: "ss-list-item", type: "button", onclick: () => { select(b.data.id); list.classList.add("hidden"); } },
        el("span", { class: "dot", style: `background:${b.color}` }), b.data.name, el("small", {}, b.parent ? `${b.parent}` : b.data.type || b.kind)))];
    }), el("button", { class: "ss-list-item", type: "button", onclick: () => { list.classList.add("hidden"); goLevel(1); } }, el("span", { class: "dot", style: "background:#fff" }), "Nearby stars →"));
  }
  const fact = (k, v) => el("div", { class: "ss-fact" }, el("span", {}, k), el("b", {}, v));
  const days = (d) => (d > 700 ? `${fmt(d / 365.25, 4)} years` : d > 2 ? `${fmt(d, 4)} days` : `${fmt(d * 24, 4)} h`);
  function showPanel(name, color, rows, note) {
    info.classList.remove("hidden");
    info.replaceChildren(el("button", { class: "ss-close", type: "button", "aria-label": "Close", onclick: () => { info.classList.add("hidden"); if (level === 0) select(null); } }, "×"),
      el("div", { class: "ss-info-name", style: `--c:${color}` }, name), ...rows.filter(Boolean).map(([k, v]) => fact(k, v)), el("p", { class: "ss-note" }, note));
  }
  function showInfo(id) {
    const b = bodies[id], d = { ...b.data, ...(window_?.bodies[id] || {}) };
    const rows = [["Type", d.type || b.kind], d.parent && ["Orbits", d.parent[0].toUpperCase() + d.parent.slice(1)],
      d.radius_km && ["Radius", `${fmt(d.radius_km, 5)} km`], d.mass_kg && ["Mass", `${fmt(d.mass_kg, 4)} kg`],
      d.surface_gravity && ["Surface gravity", `${fmt(d.surface_gravity, 3)} m/s²`], d.escape_velocity_km_s && ["Escape velocity", `${fmt(d.escape_velocity_km_s, 3)} km/s`],
      d.rotation_period_hours && ["Day (sidereal)", d.rotation_period_hours > 48 ? `${fmt(d.rotation_period_hours / 24, 4)} days` : `${fmt(d.rotation_period_hours, 4)} h`],
      d.axial_tilt_deg !== undefined && ["Axial tilt", `${fmt(d.axial_tilt_deg, 3)}°${d.retrograde_rotation ? " (spins backwards)" : ""}`],
      d.mean_temperature_c !== undefined && ["Mean temperature", `${fmt(d.mean_temperature_c, 3)} °C`], d.moons !== undefined && ["Known moons", String(d.moons)],
      d.orbital_period_days && [b.kind === "natural satellite" ? "Orbital period" : "Year", days(d.orbital_period_days)],
      d.semi_major_axis_km && ["Distance from planet", `${fmt(d.semi_major_axis_km, 5)} km`],
      d.inclination_to_equator_deg !== undefined && ["Orbit tilt to equator", `${fmt(d.inclination_to_equator_deg, 3)}°${d.retrograde_orbit ? " (retrograde)" : ""}`],
      d.tidally_locked !== undefined && ["Same face to planet", d.tidally_locked ? "yes (tidally locked)" : "no"],
      d.eccentricity !== undefined && !d.parent && ["Eccentricity", fmt(d.eccentricity, 4)],
      d.perihelion_au && ["Perihelion – aphelion", `${fmt(d.perihelion_au, 4)} – ${fmt(d.aphelion_au, 4)} AU`],
      d.distance_sun_au !== undefined && d.id !== "sun" && ["Distance from Sun", `${fmt(d.distance_sun_au, 4)} AU`],
      d.distance_earth_au !== undefined && ["Distance from Earth", `${fmt(d.distance_earth_au, 4)} AU`], d.light_time_min !== undefined && ["Light takes", `${fmt(d.light_time_min, 3)} min`]];
    showPanel(d.name, b.color, rows, d.parent ? "Moon data: planet_moons (JPL mean elements via Celestia)." : "Computed by the Reality ASM engine for the displayed date.");
  }
  let fly = null, follow = null, lastFollow = null;
  function select(id) {
    for (const l of minorOrbits.children) l.material.opacity = l.userData.id === id ? 0.7 : 0.07; // highlight the chosen orbit
    selected = id; follow = null;
    const start = { target: controls.target.clone(), cam: camera.position.clone(), t: 0 };
    if (!id) {
      info.classList.add("hidden");
      fly = { ...start, id: null, homeTarget: new THREE.Vector3(), homeCam: new THREE.Vector3(0, 120, 260).multiplyScalar(realScale ? 5 : 1) };
      return;
    }
    showInfo(id);
    const r = bodies[id].group.scale.x * (id === "saturn" ? 2.5 : 1), comet = bodies[id].kind === "comet";
    let off = camera.position.clone().sub(controls.target).normalize().multiplyScalar(Math.max(r * 4.5, 0.004));
    if (comet) { // look at a comet side-on so both tails show
      const anti = bodies[id].group.position.clone().normalize();
      off = new THREE.Vector3().crossVectors(anti, new THREE.Vector3(0, 1, 0)).normalize().multiplyScalar(2.2).addScaledVector(anti, -0.6).add(new THREE.Vector3(0, 0.5, 0));
    }
    fly = { ...start, id, off };
  }

  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  let downAt = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { downAt = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    if (level > 0) { universe.levels[level - 1].pick(mouse); return; }
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObjects(Object.values(bodies).filter((b) => b?.mesh && b.group.visible).map((b) => b.mesh))[0];
    if (hit) select(hit.object.userData.id);
  });

  // ---------- scale ladder: Solar System → stars → Milky Way → galaxies → observable Universe ----------
  const universe = createUniverseLevels({ renderer, labels, showPanel, hidePanel: () => info.classList.add("hidden"), goLevel: (i) => goLevel(i) });
  const LEVELS = [{ name: "Solar System", icon: "☉" }, ...universe.levels];
  let level = 0;
  const ladderBtns = LEVELS.map((L, i) => el("button", { class: "ss-rung", type: "button", title: L.name, onclick: () => goLevel(i) }, el("span", {}, L.icon), el("small", {}, L.name)));
  ladder.append(...ladderBtns);
  function goLevel(i) {
    if (i === level || i < 0 || i >= LEVELS.length) return;
    fade.classList.add("on");
    switchedAt = performance.now();
    setTimeout(() => {
      if (level > 0) universe.levels[level - 1].exit();
      level = i;
      info.classList.add("hidden"); list.classList.add("hidden");
      labels.replaceChildren();
      if (level === 0) {
        for (const b of Object.values(bodies)) if (b?.label) labels.append(b.label);
        for (const p of probes) labels.append(p.label);
        controls.enabled = true;
        camera.position.set(0, 1800, 4200); controls.target.set(0, 0, 0); select(null); // glide in from the stars
      } else { controls.enabled = false; universe.levels[level - 1].enter(i < prevLevel ? "in" : "out"); }
      prevLevel = level;
      for (const x of [toolbar, timebar]) x.style.display = level === 0 ? "" : "none";
      brand.replaceChildren(level === 0 ? "SOLAR SYSTEM " : "", el("b", {}, level === 0 ? "3D" : LEVELS[level].name.toUpperCase()));
      ladderBtns.forEach((b, k) => b.classList.toggle("on", k === level));
      resize();
      fade.classList.remove("on");
    }, 350);
  }
  let prevLevel = 0;
  ladderBtns[0].classList.add("on");
  // Labels sit above the canvas: pass their wheel events through so zooming works anywhere
  labels.addEventListener("wheel", (e) => { e.preventDefault(); renderer.domElement.dispatchEvent(new WheelEvent("wheel", e)); }, { passive: false });
  // Zooming past the edge of a level moves to the next scale
  let switchedAt = 0;
  renderer.domElement.addEventListener("wheel", (e) => {
    if (performance.now() - switchedAt < 1200) return; // let one scroll gesture finish before changing scale again
    if (level === 0) {
      if (e.deltaY > 0 && camera.position.distanceTo(controls.target) > controls.maxDistance * 0.97) goLevel(1);
    } else universe.levels[level - 1].wheel(e, (to) => goLevel(to));
  }, { passive: true });

  // ---------- animation ----------
  function resize() {
    const w = view.clientWidth, h = view.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    universe.resize(w, h);
  }
  const ro = new ResizeObserver(resize); ro.observe(view); resize();
  let last = performance.now(), raf = 0;
  const tmp = new THREE.Vector3(), q = new THREE.Quaternion(), mtx = new THREE.Matrix4();
  // ---------- your company's probes, drawn along their engine-computed transfer arcs ----------
  const probes = [];
  const probeGeo = new THREE.OctahedronGeometry(1, 0), probeMat = new THREE.MeshBasicMaterial({ color: 0xff5b2e });
  async function loadProbes() {
    let fleet;
    try { fleet = (await api("/api/company/fleet")).fleet; } catch { return; } // no company yet
    for (const s of fleet.filter((x) => x.kind === "probe")) {
      try {
        const d = await api(`/api/company/spacecraft/${s.id}`);
        const m = d.mission;
        if (!m?.path_au?.length) continue;
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(m.path_au.map((p) => compress(p, realScale))),
          new THREE.LineBasicMaterial({ color: 0xff5b2e, transparent: true, opacity: 0.75 }));
        line.userData.raw = m.path_au;
        orbitsGroup.add(line);
        const marker = new THREE.Mesh(probeGeo, probeMat);
        scene.add(marker);
        const label = el("button", { class: "ss-label probe", type: "button", title: `${d.name}: open in Mission Control`, onclick: () => { location.hash = `#/company?craft=${d.id}`; } }, d.name);
        label.style.setProperty("--c", "#FF5B2E");
        if (level === 0) labels.append(label);
        probes.push({ id: d.id, name: d.name, path: m.path_au, dep: dateToJd(new Date(m.depart)), arr: dateToJd(new Date(m.arrive)), target: m.target, capture: m.capture, line, marker, label });
      } catch { /* skip a probe that can't be loaded */ }
    }
  }
  function updateProbes() {
    const w = view.clientWidth, h = view.clientHeight;
    for (const p of probes) {
      let pos = null;
      if (simJd >= p.dep && simJd <= p.arr) { // between engine samples (evenly spaced in time), interpolate
        const f = ((simJd - p.dep) / (p.arr - p.dep)) * (p.path.length - 1), i = Math.min(p.path.length - 2, Math.floor(f)), u = f - i;
        const a = p.path[i], b = p.path[i + 1];
        pos = compress([a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u], realScale);
      } else if (simJd > p.arr && p.capture && bodies[p.target]?.group) pos = bodies[p.target].group.position.clone();
      p.marker.visible = !!pos && level === 0;
      if (pos) { p.marker.position.copy(pos); p.marker.scale.setScalar(Math.max(0.05, camera.position.distanceTo(pos) * 0.008)); }
      const v = pos ? pos.clone().project(camera) : null;
      const show = v && showLabels && level === 0 && v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05;
      p.label.style.display = show ? "" : "none";
      if (show) p.label.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -140%)`;
    }
  }
  loadProbes();
  // A saved view (from the history): date, scale, speed, then the selected body once it exists
  let pendingSelect = null;
  if (params.view) {
    saved.get(params.view).then((run) => {
      const v = run.payload;
      simJd = v.jd; window_ = null;
      if (v.real_scale && !realScale) bScale.click();
      if (v.speed) setSpeed(v.speed);
      if (v.level) goLevel(v.level); else pendingSelect = v.selected || null;
      toast(`Opened your saved view of ${jdToDate(v.jd).toLocaleDateString(undefined, { dateStyle: "medium", timeZone: "UTC" })}.`);
    }).catch((e) => toast(e.message, "error"));
  }

  function updateSolar(dt, now) {
    if (pendingSelect && bodies[pendingSelect]?.group && window_) { select(pendingSelect); pendingSelect = null; }
    if (playing) simJd = Math.min(2469807, Math.max(2378497, simJd + SPEEDS[speedIdx][0] * dir * dt));
    if (!window_ && !loading) loadWindow(simJd);
    if (window_) {
      const t = window_.t, span = t[t.length - 1] - t[0];
      const frac = (simJd - t[0]) / (span || 1);
      if (((frac > 0.75 || frac < 0) && dir > 0) || ((frac < 0.25 || frac > 1) && dir < 0)) loadWindow(simJd);
      for (const [id, b] of Object.entries(bodies)) {
        if (!b?.group || b.kind === "natural satellite" || !window_.bodies[id]?.track) continue;
        b.group.position.copy(compress(sample(id), realScale));
      }
      // Moons: Earth's Moon from the lunar series, the rest by phase along their engine-sampled orbits
      for (const b of Object.values(bodies)) {
        if (b?.kind !== "natural satellite" || !bodies[b.parent]) continue;
        const rel = b.data.id === "moon" ? sample("moon") : phaseSample(b.data.orbit, b.data.orbit_start_jd, b.data.orbital_period_days, simJd);
        const planet = bodies[b.parent].group.position;
        b.group.position.copy(planet).add(placeMoon(b.data.id, rel));
        if (b.orbitLine) b.orbitLine.position.copy(planet);
        if (b.data.tidally_locked !== false && b.data.id !== "moon") { // keep the prime meridian (+X) facing the planet
          const x = planet.clone().sub(b.group.position).normalize(), y = new THREE.Vector3(0, 1, 0);
          const z = new THREE.Vector3().crossVectors(x, y).normalize(); y.crossVectors(z, x);
          b.tilt.quaternion.setFromRotationMatrix(mtx.makeBasis(x, y, z));
        }
      }
      // Spin: prime-meridian angle from the engine, advanced at the engine's rotation rate
      for (const [id, b] of Object.entries(bodies)) {
        const d = window_.bodies[id];
        if (!b?.spin || d?.rotation_rate_deg_per_day === undefined) continue;
        b.spin.rotation.y = THREE.MathUtils.degToRad(d.prime_meridian_deg + d.rotation_rate_deg_per_day * (simJd - window_.t[0]));
      }
      if (fx.clouds) fx.clouds.rotation.y += dt * 0.004 * Math.sign(SPEEDS[speedIdx][0]);
      const date = jdToDate(simJd);
      dateBig.textContent = date.toISOString().slice(0, 10);
      timeSmall.textContent = `${date.toISOString().slice(11, 19)} UTC   JD ${simJd.toFixed(3)}`;
    }
    // Lighting uniforms, rings and the Sun
    for (const b of Object.values(bodies)) for (const m of b?.mats || []) m.uniforms.sunPos.value.copy(SUN_POS);
    for (const [id, r] of Object.entries(fx.rings)) {
      const p = bodies[id], s = p.group.scale.x;
      p.group.updateMatrixWorld();
      const normal = new THREE.Vector3(0, 1, 0).applyQuaternion(p.tilt.getWorldQuaternion(q));
      r.rm.uniforms.sunPos.value.copy(SUN_POS); r.rm.uniforms.center.value.copy(p.group.position);
      r.rm.uniforms.planetRadius.value = s; r.rm.uniforms.ringNormal.value.copy(normal);
      const pu = p.mats[0].uniforms;
      pu.center.value.copy(p.group.position); pu.ringNormal.value.copy(normal); pu.ringInner.value = r.inner * s; pu.ringOuter.value = r.outer * s;
    }
    if (fx.sun) {
      fx.sun.mat.uniforms.time.value = now / 1000;
      const dSun = camera.position.distanceTo(SUN_POS);
      fx.sun.halo.scale.setScalar(Math.max(18, dSun * 0.1)); // the corona glare stays visible from afar
    }
    updateBelts();
    updateTails();
    updateProbes();
    // Camera: fly to the selected body, then ride along with it
    if (fly) {
      fly.t = Math.min(1, fly.t + dt * 1.1);
      const k = fly.t * fly.t * (3 - 2 * fly.t);
      const goal = fly.id ? bodies[fly.id].group.position : fly.homeTarget;
      const camGoal = fly.id ? tmp.copy(goal).add(fly.off) : fly.homeCam;
      controls.target.lerpVectors(fly.target, goal, k);
      camera.position.lerpVectors(fly.cam, camGoal, k);
      if (fly.t >= 1) { follow = fly.id; lastFollow = fly.id ? goal.clone() : null; fly = null; }
    } else if (follow && bodies[follow]) {
      const p = bodies[follow].group.position;
      const delta = p.clone().sub(lastFollow);
      controls.target.add(delta); camera.position.add(delta); lastFollow.copy(p);
    }
    const focus = bodies[follow || (fly && fly.id) || "sun"];
    if (focus?.group) controls.minDistance = focus.group.scale.x * (focus.data.id === "sun" ? 1.6 : 1.25); // never fly inside a body
    controls.update();
    sky.position.copy(camera.position);
    if (showLabels) {
      const w = view.clientWidth, h = view.clientHeight, camD = (b) => camera.position.distanceTo(b.group.position);
      for (const b of Object.values(bodies)) {
        if (!b?.label) continue;
        const parent = b.parent && bodies[b.parent];
        let show = b.group.visible && (b.kind !== "natural satellite" || (parent && camD(parent) < parent.group.scale.x * (b.data.id === "moon" ? 60 : 30)));
        if (!COLORS[b.data.id] && b.kind !== "natural satellite") show = show && showMinor && (camD(b) < 80 || b.kind === "dwarf planet" || b.kind === "comet");
        tmp.copy(b.group.position); tmp.y += b.group.scale.x * 1.2;
        const v = tmp.project(camera), visible = show && v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05;
        b.label.style.display = visible ? "" : "none";
        if (visible) b.label.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -120%)`;
      }
    }
    renderer.render(scene, camera);
  }
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (level === 0) updateSolar(dt, now);
    else {
      if (!window_ && !loading) loadWindow(simJd); // the sky and stars data arrive with the first Solar System load
      universe.levels[level - 1].frame(dt, now);
    }
  }
  raf = requestAnimationFrame(frame);
  if (startLevel) setTimeout(() => goLevel(startLevel), 50);

  return () => {
    cancelAnimationFrame(raf); ro.disconnect(); controls.dispose(); universe.dispose();
    scene.traverse((o) => { o.geometry?.dispose?.(); const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => x.dispose()); });
    Object.values(texCache).forEach((t) => t.dispose());
    renderer.dispose();
  };
}

export default { mount: (root, params) => mountAt(root, 0, params) };
