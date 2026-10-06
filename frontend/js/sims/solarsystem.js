// Solar System 3D → the observable Universe. Every position, spin, orbit, star and galaxy comes from the engine
// (physics.solar_system, planet_moons, minor_bodies, asteroid_belt, star_catalog, milky_way, galaxy_catalog,
// cosmology); the browser renders them with three.js and interpolates between the engine's samples.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";
const commas = (n) => Math.round(n).toLocaleString("en-US");
import { api, history as saved, toast } from "../core/session.js";
import { planetMaterial, atmosphereMaterial, ringMaterial, sunMaterial, glowTexture, pointsMaterial, hexToRgb, tailMaterial } from "../space/shaders.js";
import { createUniverseLevels } from "../space/universe.js";
import { buildSky } from "../space/sky.js";
import { createSettings, settingsPanel } from "../space/settings.js";
import { createJourney } from "../space/journey.js";

const TEX = "/app/assets/textures/"; // absolute, so the same view works inside ASM Teach
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
  const brand = el("div", { class: "ss-brand" }, "UNIVERSE MAP ", el("b", {}, "SOLAR SYSTEM"));
  const speedText = el("span", { class: "ss-speed-text" });
  const info = el("aside", { class: "ss-info hidden" });
  const list = el("div", { class: "ss-list hidden" });
  const status = el("div", { class: "ss-status" }, "Loading the Solar System…");
  const fade = el("div", { class: "ss-fade" });
  let simJd = dateToJd(new Date()), window_ = null, loading = false, firstLoad = true;
  try { // arriving from a Space Program mission: open on its date
    const d = localStorage.getItem("reality-asm.solar-date");
    if (d) { localStorage.removeItem("reality-asm.solar-date"); simJd = dateToJd(new Date(d)); }
  } catch { /* storage unavailable */ }
  const settings = createSettings();
  let speedIdx = 5, playing = true, showOrbits = true, showLabels = settings.get("labels_planets"), realScale = false, showMinor = true, showBelts = true;
  const tool = (icon, title, onclick) => el("button", { class: "ss-tool", type: "button", title, "aria-label": title, onclick }, icon);
  const bOrbits = tool("◯", "Orbits", () => { showOrbits = !showOrbits; bOrbits.classList.toggle("off", !showOrbits); orbitsGroup.visible = showOrbits; });
  const bLabels = tool("Aa", "Names", () => settings.set("labels_planets", !showLabels));
  const bScale = tool("⤢", "Real scale (distances and sizes)", () => { realScale = !realScale; bScale.classList.toggle("on", realScale); rebuildScale(); });
  const bMinor = tool("☄", "Dwarf planets, asteroids and comets", () => { showMinor = !showMinor; bMinor.classList.toggle("off", !showMinor); minorGroup.visible = showMinor; minorOrbits.visible = showMinor; });
  const bBelts = tool("⁘", "Asteroid belts, Kuiper belt, Oort cloud and heliosphere", () => { showBelts = !showBelts; bBelts.classList.toggle("off", !showBelts); beltPoints.visible = showBelts; });
  const bList = tool("☰", "All bodies", () => list.classList.toggle("hidden"));
  const bLaunch = tool("⇧", "Launch a rocket on this date (Space Program)", () => {
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
  const gear = settingsPanel(settings);
  const rootEl = el("div", { class: "ss-root" }, view, labels, el("div", { class: "ss-top" }, brand),
    toolbar, ladder, list, info, status, timebar, credit, gear.btn, gear.sheet, fade);
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
  controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 0.003; controls.maxDistance = 24000; // out past the Oort cloud
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
      simulate("physics", "asteroid_belt", { date: jdToDate(simJd).toISOString(), n_main: 4500, n_trojans: 1100, n_kuiper: 2600, n_hilda: 500, n_nea: 260, n_scattered: 700, n_oort: 2500, samples_per_orbit: 16 }),
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
    simulate("physics", "sky_atlas", { frame: "ecliptic" }).then((r) => { universe.setData({ atlas: r.result }); buildSkyAtlas(r.result); }).catch((e) => console.warn("sky atlas", e));
  }
  // ---------- constellations on the night sky (directions only, as seen from the Sun) ----------
  const skyCon = new THREE.Group(), skyBorders = new THREE.Group(), skyNames = [];
  sky.add(skyCon, skyBorders);
  function buildSkyAtlas(A) {
    const R = 59000, pairs = [], bpairs = [];
    for (const c of A.constellations) {
      for (const line of c.lines) for (let k = 1; k < line.length; k++) { const a = toScene(line[k - 1].unit).multiplyScalar(R), b = toScene(line[k].unit).multiplyScalar(R); pairs.push(a.x, a.y, a.z, b.x, b.y, b.z); }
      const e = el("button", { class: "ss-label con", type: "button", onclick: () => showPanel(c.name, "#9fc3ff", [["Hindi name", c.hindi || "–"], ["Latin genitive", c.genitive || "–"], ["Abbreviation", c.abbr]], "IAU constellation (d3-celestial stick figure). Its stars are at very different distances: zoom out to the stars scale to see them in 3D.") }, c.name);
      e.style.setProperty("--c", "#9fc3ff");
      skyNames.push({ el: e, dir: toScene(c.label_unit), c });
      if (level === 0) labels.append(e);
    }
    for (const line of A.constellation_borders) for (let k = 1; k < line.length; k++) { const a = toScene(line[k - 1]).multiplyScalar(R * 1.001), b = toScene(line[k]).multiplyScalar(R * 1.001); bpairs.push(a.x, a.y, a.z, b.x, b.y, b.z); }
    const seg = (arr, color, opacity) => { const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(arr), 3)); const m = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false })); m.frustumCulled = false; m.renderOrder = -1; return m; };
    skyCon.add(seg(pairs, 0x6f9fe0, 0.5)); skyBorders.add(seg(bpairs, 0x8a6fd0, 0.25));
    applySkySettings();
  }
  function applySkySettings() {
    skyCon.visible = settings.get("constellation_lines"); skyBorders.visible = settings.get("constellation_borders");
    for (const n of skyNames) n.el.textContent = settings.get("constellation_hindi") && n.c.hindi ? `${n.c.name} · ${n.c.hindi}` : n.c.name;
    showLabels = settings.get("labels_planets"); bLabels.classList.toggle("off", !showLabels);
  }
  settings.onChange(() => applySkySettings());
  function placeSkyNames() {
    const w = view.clientWidth, h = view.clientHeight, on = settings.get("constellation_names");
    for (const n of skyNames) {
      tmp.copy(n.dir).multiplyScalar(1e4).add(camera.position).project(camera);
      const ok = on && level === 0 && tmp.z < 1 && Math.abs(tmp.x) < 1.02 && Math.abs(tmp.y) < 1.02;
      n.el.style.display = ok ? "" : "none";
      if (ok) n.el.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h}px) translate(-50%, -50%)`;
    }
  }
  // The debris belts, the Oort cloud and the edge of the Sun's wind (physics.asteroid_belt), each with a name tag
  const BELT_LOOK = { "main belt": ["#b3a493", "Main asteroid belt", 2.4], "Jupiter trojans": ["#d0b07a", "Jupiter trojans", 2.4], "Kuiper belt": ["#9fb8d6", "Kuiper belt", 2.6],
    Hildas: ["#c9a46a", "Hilda asteroids", 2.2], "near-Earth asteroids": ["#ff8a5c", "Near-Earth asteroids", 2.4], "scattered disc": ["#8aa0c8", "Scattered disc", 2.4], "Oort cloud": ["#7f93b8", "Oort cloud (model)", 2.2] };
  const beltLabels = [], helio = new THREE.Group(), beltList = []; // beltList: what the Journey says about each belt
  scene.add(helio);
  function buildBelts() {
    const n = belts.groups.reduce((s, g) => s + g.count, 0);
    const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), size = new Float32Array(n);
    let k = 0;
    belts.groups.forEach((g) => {
      const [hex, , px] = BELT_LOOK[g.name] || ["#a0a0a0", g.name, 2], c = new THREE.Color(hex);
      for (let i = 0; i < g.count; i++, k++) { const f = 0.75 + 0.25 * ((i * 7919) % 100) / 100; col.set([c.r * f, c.g * f, c.b * f], k * 3); size[k] = px; }
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("color", new THREE.BufferAttribute(col, 3)); geo.setAttribute("size", new THREE.BufferAttribute(size, 1));
    beltPoints = new THREE.Points(geo, pointsMaterial({ scale: 1, minSize: 1.6, maxSize: 4.5, opacity: 0.95 }));
    beltPoints.frustumCulled = false;
    scene.add(beltPoints);
    // name tags: placed at a typical member's distance, in a direction away from the planets' crowd
    belts.groups.forEach((g, gi) => {
      const [hex, name] = BELT_LOOK[g.name] || ["#a0a0a0", g.name];
      const sa = [...g.semi_major_axis_au].sort((x, y) => x - y), lo = sa[Math.floor(sa.length * 0.05)], hi = sa[Math.floor(sa.length * 0.95)], mid = sa[Math.floor(sa.length / 2)];
      const span = hi > 1000 ? `${commas(Math.round(lo / 100) * 100)}–${commas(Math.round(hi / 1000) * 1000)} AU` : `${fmt(lo, 2)}–${fmt(hi, 2)} AU`;
      const ang = [3.9, 1.2, 2.5, 4.6, 5.4, 0.4, 3.3][gi % 7];
      const e = el("button", { class: "ss-label belt", type: "button", title: `${name}: ${commas(g.count)} sample bodies`, onclick: () => beltInfo(g, name, span) }, `${name} · ${span}`);
      beltList.push({ key: g.name, name, span, au: mid, note: BELT_NOTES[g.name] || "" });
      e.style.setProperty("--c", hex);
      beltLabels.push({ el: e, raw: [mid * Math.cos(ang), mid * Math.sin(ang), 0] });
      if (level === 0) labels.append(e);
    });
    // the heliosphere: where the Voyagers crossed the termination shock and the heliopause
    for (const bd of belts.boundaries.filter((x) => x.distance_au < 1000)) {
      const r = compress([bd.distance_au, 0, 0], realScale).length(), helioPause = /Heliopause/.test(bd.name);
      const ring = new THREE.Mesh(new THREE.RingGeometry(r * 0.998, r * 1.002, 256), new THREE.MeshBasicMaterial({ color: helioPause ? 0x7fb2ff : 0x5f86c0, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }));
      ring.rotation.x = -Math.PI / 2; ring.userData.au = bd.distance_au; helio.add(ring);
      if (/Voyager 1/.test(bd.name)) {
        const shellM = new THREE.Mesh(new THREE.SphereGeometry(r, 64, 48), new THREE.MeshBasicMaterial({ color: helioPause ? 0x6f9fff : 0x4f6fa0, transparent: true, opacity: helioPause ? 0.05 : 0.03, side: THREE.BackSide, depthWrite: false }));
        shellM.userData.au = bd.distance_au; helio.add(shellM);
        const e = el("button", { class: "ss-label belt", type: "button", onclick: () => showPanel(bd.name, "#7fb2ff", [["Distance from the Sun", `${fmt(bd.distance_au, 4)} AU`], ["Light takes", `${fmt(bd.distance_au * 499.005 / 3600, 3)} hours`]], helioPause ? "The heliopause: where the solar wind meets the gas between the stars. Voyager 1 crossed it in August 2012, Voyager 2 in November 2018." : "The termination shock: where the solar wind slows below the speed of sound.") }, `${helioPause ? "Heliopause" : "Termination shock"} · ${fmt(bd.distance_au, 4)} AU`);
        e.style.setProperty("--c", "#7fb2ff");
        beltLabels.push({ el: e, raw: [0, -bd.distance_au * 0.7071, bd.distance_au * 0.7071] });
        beltList.push({ key: helioPause ? "heliopause" : "shock", name: helioPause ? "The heliopause" : "The termination shock", span: `${fmt(bd.distance_au, 4)} AU`, au: bd.distance_au,
          note: helioPause ? "Where the Sun's wind ends and interstellar space begins. Voyager 1 crossed it in 2012." : "Where the solar wind slows below the speed of sound." });
        if (level === 0) labels.append(e);
      }
    }
  }
  function beltInfo(g, name, span) {
    const notes = BELT_NOTES;
    showPanel(name, (BELT_LOOK[g.name] || ["#a0a0a0"])[0], [["Where", span], ["Sample bodies drawn", commas(g.count)],
      ...(g.name === "main belt" ? [["Kirkwood gaps (AU)", belts.kirkwood_gaps.map((k) => `${k.resonance} ${fmt(k.semi_major_axis_au, 3)}`).join(", ")]] : []),
      ...(g.name === "Hildas" ? [["3:2 resonance with Jupiter", `${fmt(belts.hilda_resonance_au, 4)} AU`]] : [])],
      `${notes[g.name] || ""} physics.asteroid_belt: a statistical sample; the dots are not individual real asteroids.`);
  }
  const BELT_NOTES = { "main belt": "Between Mars and Jupiter. The gaps are Kirkwood gaps, cleared by resonances with Jupiter.", "Jupiter trojans": "They share Jupiter's orbit, 60° ahead and behind it (the L4 and L5 points).",
      "Kuiper belt": "Icy bodies beyond Neptune, home of Pluto. Plutinos orbit twice for every three of Neptune's.", Hildas: "Three orbits for every two of Jupiter's (the 3:2 resonance), so they trace a rounded triangle.",
      "near-Earth asteroids": "Asteroids whose closest point to the Sun is within 1.3 AU: the ones watched for impacts.", "scattered disc": "Icy bodies flung onto long, tilted orbits by Neptune; Eris lives here.",
      "Oort cloud": "A vast sphere of comets, never seen directly; long-period comets come from it. The points show the model, not real objects." };
  function updateBelts() {
    helio.visible = showBelts;
    for (const m of helio.children) m.scale.setScalar(compress([m.userData.au, 0, 0], realScale).length() / (m.geometry.parameters.radius || m.geometry.parameters.outerRadius / 1.002));
    if (!belts || !beltPoints.visible) return;
    const pos = beltPoints.geometry.attributes.position.array;
    let k = 0;
    for (const g of belts.groups) for (let i = 0; i < g.count; i++, k++) {
      const v = compress(phaseSample(g.orbits[i], belts.orbit_start_jd, g.period_days[i], simJd, true), realScale);
      pos[k * 3] = v.x; pos[k * 3 + 1] = v.y; pos[k * 3 + 2] = v.z;
    }
    beltPoints.geometry.attributes.position.needsUpdate = true;
  }
  // hide a name that would sit on top of the Sun's crowd when zoomed far out
  const sunPx = () => { const v = SUN_POS.clone().project(camera); return [((v.x + 1) / 2) * view.clientWidth, ((1 - v.y) / 2) * view.clientHeight]; };
  function placeBeltLabels() {
    const w = view.clientWidth, h = view.clientHeight, [sx, sy] = sunPx();
    for (const b of beltLabels) {
      tmp.copy(compress(b.raw, realScale)).project(camera);
      const x = ((tmp.x + 1) / 2) * w, y = ((1 - tmp.y) / 2) * h;
      const ok = showBelts && showLabels && level === 0 && tmp.z < 1 && Math.abs(tmp.x) < 1.02 && Math.abs(tmp.y) < 1.02 && Math.hypot(x - sx, y - sy) > 90;
      b.el.style.display = ok ? "" : "none";
      if (ok) b.el.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h}px) translate(-50%, -50%)`;
    }
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
  function showPanel(name, color, rows, note, media = null) {
    info.classList.remove("hidden");
    info.replaceChildren(el("button", { class: "ss-close", type: "button", "aria-label": "Close", onclick: () => { info.classList.add("hidden"); if (level === 0) select(null); } }, "×"),
      el("div", { class: "ss-info-name", style: `--c:${color}` }, name), media || "", ...rows.filter(Boolean).map(([k, v]) => fact(k, v)), el("p", { class: "ss-note" }, note));
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
  const universe = createUniverseLevels({ renderer, labels, showPanel, hidePanel: () => info.classList.add("hidden"), goLevel: (i) => goLevel(i), settings });
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
        for (const n of skyNames) labels.append(n.el);
        for (const b of beltLabels) labels.append(b.el);
        controls.enabled = true;
        camera.position.set(0, 1800, 4200); controls.target.set(0, 0, 0); select(null); // glide in from the stars
        if (!interactive) fly = null;
      } else { controls.enabled = false; universe.levels[level - 1].enter(i < prevLevel ? "in" : "out"); }
      if (!interactive) setInteractive(false);
      prevLevel = level;
      for (const x of [toolbar, timebar]) x.style.display = level === 0 ? "" : "none";
      rootEl.classList.toggle("ss-solar", level === 0); // time travel (the clock) belongs to the Solar System scale only
      brand.replaceChildren("UNIVERSE MAP ", el("b", {}, LEVELS[level].name.toUpperCase()));
      ladderBtns.forEach((b, k) => b.classList.toggle("on", k === level));
      resize();
      fade.classList.remove("on");
    }, 350);
  }
  let prevLevel = 0;
  ladderBtns[0].classList.add("on");

  // ---------- one set of controls for mouse, keyboard and touch ----------
  let interactive = true; // off while the Journey drives the camera
  const camOf = () => (level === 0 ? { camera, controls } : universe.levels[level - 1]);
  function setInteractive(on) {
    interactive = on;
    controls.enabled = on && level === 0;
    universe.levels.forEach((L, i) => { L.controls.enabled = on && level === i + 1; });
  }
  function zoomBy(f) { // f < 1 moves closer; past the end of a scale, go to the next one
    const { camera: c, controls: k } = camOf(), off = c.position.clone().sub(k.target), d = off.length(), nd = d * f;
    if (f > 1 && d >= k.maxDistance * 0.97) return goLevel(level + 1);
    if (f < 1 && d <= k.minDistance * 1.05 && level > 0) return goLevel(level - 1);
    c.position.copy(k.target).add(off.setLength(Math.min(k.maxDistance, Math.max(k.minDistance, nd))));
    if (level === 0) { follow = null; fly = null; }
  }
  function orbitBy(yaw, pitch) {
    const { camera: c, controls: k } = camOf(), off = c.position.clone().sub(k.target);
    const sph = new THREE.Spherical().setFromVector3(off);
    sph.theta += yaw; sph.phi = Math.min(Math.PI - 0.05, Math.max(0.05, sph.phi + pitch));
    c.position.copy(k.target).add(new THREE.Vector3().setFromSpherical(sph));
  }
  const zoomBtns = el("div", { class: "ss-zoom" },
    el("button", { type: "button", class: "ss-tool", title: "Zoom in (+). Past the closest view: the smaller scale", "aria-label": "Zoom in", onclick: () => zoomBy(0.7) }, "+"),
    el("button", { type: "button", class: "ss-tool", title: "Zoom out (−). Past the widest view: the next scale out", "aria-label": "Zoom out", onclick: () => zoomBy(1.45) }, "−"),
    el("button", { type: "button", class: "ss-tool", title: "Keyboard and touch help (?)", "aria-label": "Controls help", onclick: () => help.classList.toggle("hidden") }, "?"));
  const help = el("div", { class: "ss-help hidden", role: "dialog", "aria-label": "Controls" },
    el("div", { class: "ss-settings-head" }, el("b", {}, "Controls"), el("button", { type: "button", class: "ss-close", "aria-label": "Close", onclick: () => help.classList.add("hidden") }, "×")),
    el("table", {}, ...[["Look around", "drag · arrow keys or W A S D", "drag with one finger"], ["Zoom", "scroll · + and −", "pinch · + − buttons"],
      ["Change scale", "zoom past the end · Page Up / Page Down · keys 1 to 5", "pinch past the end · scale buttons on top"],
      ["Pick a body or star", "click it", "tap it"], ["Time (Solar System)", "Space: hold or run · , and . slower or faster", "clock panel"],
      ["Names on or off", "N", "Aa button"], ["Back to the whole view", "H", "⌂ button"], ["Journey from the Big Bang", "J (Space pause, ← → chapters, Esc leave)", "Journey button"]]
      .map(([a, b, c]) => el("tr", {}, el("th", {}, a), el("td", {}, b), el("td", {}, c)))));
  rootEl.append(zoomBtns, help);
  // touch and trackpad: pinching past the end of a scale changes scale, like the mouse wheel does
  for (const [i, k] of [[0, controls], ...universe.levels.map((L, j) => [j + 1, L.controls])]) {
    let startD = 0;
    k.addEventListener("start", () => { startD = k.object.position.distanceTo(k.target); });
    k.addEventListener("end", () => {
      if (!interactive || level !== i || performance.now() - switchedAt < 1200) return;
      const d = k.object.position.distanceTo(k.target);
      if (d >= k.maxDistance * 0.97 && d > startD * 1.02) goLevel(i + 1);
      else if (i > 0 && d <= k.minDistance * 1.05 && d < startD * 0.98) goLevel(i - 1);
    });
  }
  function onKey(e) {
    if (!rootEl.isConnected) return;
    if (journey.key(e)) return;
    if (e.target.closest?.("input, textarea, select") || e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key;
    const act = {
      ArrowLeft: () => orbitBy(-0.08, 0), a: () => orbitBy(-0.08, 0), ArrowRight: () => orbitBy(0.08, 0), d: () => orbitBy(0.08, 0),
      ArrowUp: () => orbitBy(0, -0.06), w: () => orbitBy(0, -0.06), ArrowDown: () => orbitBy(0, 0.06), s: () => orbitBy(0, 0.06),
      "+": () => zoomBy(0.8), "=": () => zoomBy(0.8), "-": () => zoomBy(1.25), _: () => zoomBy(1.25),
      PageUp: () => goLevel(level + 1), PageDown: () => goLevel(level - 1),
      1: () => goLevel(0), 2: () => goLevel(1), 3: () => goLevel(2), 4: () => goLevel(3), 5: () => goLevel(4),
      h: () => (level === 0 ? select(null) : universe.levels[level - 1].enter("out")), n: () => bLabels.click(), j: () => journey.start(), "?": () => help.classList.toggle("hidden"),
      " ": () => level === 0 && bPlay.click(), ",": () => level === 0 && setSpeed(speedIdx - 1), ".": () => level === 0 && setSpeed(speedIdx + 1),
      Escape: () => { help.classList.add("hidden"); gear.sheet.classList.add("hidden"); info.classList.add("hidden"); },
    }[k.length === 1 ? k.toLowerCase() : k];
    if (!act || !interactive) return;
    e.preventDefault(); act();
  }
  window.addEventListener("keydown", onKey);

  // ---------- Journey: from the Big Bang to the Earth ----------
  const journey = createJourney({ rootEl, universe, goLevel: (i) => goLevel(i), getLevel: () => level,
    solar: { camera, controls, select: (id) => select(id), bodies, stopFly: () => { fly = null; follow = null; }, setInteractive,
      sceneOfAU: (au) => compress([au, 0, 0], realScale).length(), beltNames: () => beltList } });
  const bJourney = el("button", { class: "ss-journey", type: "button", title: "Watch the universe begin, then fly from its edge to the Earth (J)", onclick: () => journey.start() }, "▶ Journey", el("span", { class: "long" }, " from the Big Bang"));
  rootEl.append(bJourney);
  if (params.journey) setTimeout(() => journey.start(), 600);
  // Labels sit above the canvas: pass their wheel events through so zooming works anywhere
  labels.addEventListener("wheel", (e) => { e.preventDefault(); renderer.domElement.dispatchEvent(new WheelEvent("wheel", e)); }, { passive: false });
  // Zooming past the edge of a level moves to the next scale
  let switchedAt = 0;
  renderer.domElement.addEventListener("wheel", (e) => {
    if (!interactive || performance.now() - switchedAt < 1200) return; // let one scroll gesture finish before changing scale again
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
    for (const b of Object.values(bodies)) { // every planet and moon is solid, not only the one in focus
      if (!b?.group?.visible) continue;
      const c = b.group.position, min = b.group.scale.x * (b.data.id === "sun" ? 1.15 : 1.03), d = camera.position.distanceTo(c);
      if (d < min && d > 0) camera.position.sub(c).multiplyScalar(min / d).add(c);
    }
    sky.position.copy(camera.position);
    placeSkyNames();
    placeBeltLabels();
    if (showLabels) {
      const w = view.clientWidth, h = view.clientHeight, camD = (b) => camera.position.distanceTo(b.group.position), [sx, sy] = sunPx();
      for (const b of Object.values(bodies)) {
        if (!b?.label) continue;
        const parent = b.parent && bodies[b.parent];
        let show = b.group.visible && (b.kind !== "natural satellite" || (parent && camD(parent) < parent.group.scale.x * (b.data.id === "moon" ? 60 : 30)));
        if (!COLORS[b.data.id] && b.kind !== "natural satellite") show = show && showMinor && (camD(b) < 80 || b.kind === "dwarf planet" || b.kind === "comet");
        tmp.copy(b.group.position); tmp.y += b.group.scale.x * 1.2;
        const v = tmp.project(camera), px = ((v.x + 1) / 2) * w, py = ((1 - v.y) / 2) * h;
        const visible = show && v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05 && (b.data.id === "sun" || b.parent || Math.hypot(px - sx, py - sy) > 16);
        b.label.style.display = visible ? "" : "none";
        if (visible) b.label.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -120%)`;
      }
    } else for (const b of Object.values(bodies)) if (b?.label) b.label.style.display = "none";
    renderer.render(scene, camera);
  }
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (journey.covering) return; // the Big Bang fills the screen: no need to draw the 3D map under it
    if (level === 0) updateSolar(dt, now);
    else {
      if (!window_ && !loading) loadWindow(simJd); // the sky and stars data arrive with the first Solar System load
      universe.levels[level - 1].frame(dt, now);
    }
  }
  raf = requestAnimationFrame(frame);
  rootEl.classList.toggle("ss-solar", !startLevel);
  if (startLevel) { timebar.style.display = "none"; toolbar.style.display = "none"; setTimeout(() => goLevel(startLevel), 50); }

  return () => {
    cancelAnimationFrame(raf); ro.disconnect(); controls.dispose(); universe.dispose(); journey.stop(); window.removeEventListener("keydown", onKey);
    scene.traverse((o) => { o.geometry?.dispose?.(); const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => x.dispose()); });
    Object.values(texCache).forEach((t) => t.dispose());
    renderer.dispose();
  };
}

export default { mount: (root, params) => mountAt(root, 0, params) };
