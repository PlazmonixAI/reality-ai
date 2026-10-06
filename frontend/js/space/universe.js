// Levels beyond the Solar System, all drawn from engine data: real stars (physics.star_catalog), the Galaxy
// model (physics.milky_way), real galaxies (physics.galaxy_catalog) and the ΛCDM observable universe
// (physics.cosmology). The browser only projects, sizes and labels what the engine returns.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";
import { pointsMaterial, hexToRgb, glowTexture } from "./shaders.js";

const toScene = (x, y, z) => new THREE.Vector3(x, z, -y); // catalogue frame (x, y, z) → three.js, plane horizontal
const commas = (n) => Math.round(n).toLocaleString("en-US");
const TYPE_COLOR = (t) => (t.startsWith("E") || t.startsWith("S0") ? [1.0, 0.86, 0.66] : t.startsWith("I") ? [0.66, 0.8, 1.0] : [0.82, 0.88, 1.0]);

function pointCloud(positions, colors, sizes, opts) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
  g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(colors), 3));
  g.setAttribute("size", new THREE.BufferAttribute(new Float32Array(sizes), 1));
  const p = new THREE.Points(g, pointsMaterial(opts));
  p.frustumCulled = false;
  return p;
}
function circle(r, color, opacity, segments = 256) {
  const pts = [...Array(segments)].map((_, i) => new THREE.Vector3(r * Math.cos((i / segments) * 2 * Math.PI), 0, r * Math.sin((i / segments) * 2 * Math.PI)));
  return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
}
function shell(r, color, opacity) { // a faint sphere drawn as latitude and longitude circles
  const g = new THREE.Group();
  for (let k = -2; k <= 2; k++) { const c = circle(r * Math.cos((k * Math.PI) / 6), color, opacity); c.position.y = r * Math.sin((k * Math.PI) / 6); g.add(c); }
  for (let k = 0; k < 6; k++) { const c = circle(r, color, opacity * 0.7); c.rotation.x = Math.PI / 2; c.rotation.z = (k * Math.PI) / 6; g.add(c); }
  return g;
}
function glowSprite(size, stops) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(stops), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  s.scale.set(size, size, 1);
  return s;
}

const KIND_SETTING = { star: ["labels_stars"], galaxy: ["labels_galaxies"], galaxyCat: ["labels_galaxies", "labels_all_galaxies"], structure: ["labels_structures"],
  deepsky: ["labels_deepsky"], exo: ["labels_exoplanets"], con: ["constellation_names"], ring: ["rings"] };
const DSO_COLOR = (t) => (/Planetary/.test(t) ? "#5fd6c4" : /Supernova/.test(t) ? "#ff9b5a" : /Emission|HII|Nebula/.test(t) ? "#ff6f8e" : /Reflection/.test(t) ? "#8fb4ff"
  : /Dark/.test(t) ? "#8c7f74" : /Globular/.test(t) ? "#ffd27a" : "#bcd4ff");
const STRUCT_COLOR = { group: 0xffd9a8, cluster: 0xffc27a, supercluster: 0x9fc3ff, attractor: 0xff8a5a, wall: 0xc3a6ff, void: 0x5a6b85 };
const DOME_LY = 1500; // constellation figures as seen from Earth, drawn on a far sphere behind the nearby stars
const hex6 = (n) => `#${n.toString(16).padStart(6, "0")}`;

export function createUniverseLevels({ renderer, labels, showPanel, hidePanel, goLevel, settings }) {
  const data = {};
  const S = settings || { get: () => true, onChange: () => {} };
  const kindOn = (kind) => !kind || !KIND_SETTING[kind] || KIND_SETTING[kind].every((k) => S.get(k));
  const listeners = [];
  const base = (name, icon, { start, min, max, near, far, prev, next }) => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, 1, near, far);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enabled = false; controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.minDistance = min; controls.maxDistance = max;
    const L = {
      name, icon, scene, camera, controls, labelItems: [], ready: false, groups: {}, atlasDone: false,
      enter(direction) {
        controls.enabled = true;
        const d = direction === "in" ? max * 0.8 : Math.max(min * 3, start.length() * 0.35);
        camera.position.copy(start).setLength(d); controls.target.set(0, 0, 0); controls.update();
        L.fly = { from: d, to: start.length(), t: 0 };
        for (const it of L.labelItems) labels.append(it.el);
        if (L.ready) L.onEnter?.();
        else showPanel(`Loading ${name.toLowerCase()}…`, "#9fb3cc", [], "Fetching engine data.");
      },
      exit() { controls.enabled = false; },
      wheel(e, go) {
        const dist = camera.position.distanceTo(controls.target);
        if (e.deltaY > 0 && dist > max * 0.97 && next !== undefined) go(next);
        if (e.deltaY < 0 && dist < min * 1.05 && prev !== undefined) go(prev);
      },
      frame(dt) {
        if (!L.ready && (!L.requires || data[L.requires])) { L.ready = true; L.load?.(); }
        if (L.fly && L.fly.t < 1) { // glide in after arriving from another scale
          L.fly.t = Math.min(1, L.fly.t + dt * 0.9);
          const k = L.fly.t * L.fly.t * (3 - 2 * L.fly.t);
          camera.position.setLength(L.fly.from + (L.fly.to - L.fly.from) * k);
        }
        controls.update();
        L.update?.(dt);
        L.beforeRender?.();
        placeLabels(L);
        renderer.render(scene, camera);
      },
      pick(ndc) { L.onPick?.(ndc); },
    };
    listeners.push(controls);
    return L;
  };
  function label(L, text, color, pos, { cls = "", onclick = null, priority = 0, minDist = 0, maxDist = Infinity, lum = null, kind = null } = {}) {
    const e = el("button", { class: `ss-label ${cls}`, type: "button", onclick }, text);
    e.style.setProperty("--c", color);
    const it = { el: e, pos, priority, minDist, maxDist, lum, kind };
    L.labelItems.push(it);
    if (L.controls.enabled) labels.append(e);
    return it;
  }
  const tmp = new THREE.Vector3();
  function placeLabels(L) {
    const w = renderer.domElement.clientWidth, h = renderer.domElement.clientHeight;
    const cam = L.camera.position, placed = [];
    for (const it of L.labelItems) if (it.lum !== null) it.priority = Math.log10(it.lum / Math.max(cam.distanceToSquared(it.pos), 1e-6)); // brightest as seen from here
    const items = L.labelItems.slice().sort((a, b) => b.priority - a.priority);
    let shown = 0;
    const cap = Math.round((L.maxLabels || 60) * (S.get("density") || 1));
    for (const it of items) {
      if (it.hidden || !kindOn(it.kind)) { it.el.style.display = "none"; continue; }
      const d = cam.distanceTo(it.pos);
      tmp.copy(it.pos).project(L.camera);
      let ok = tmp.z < 1 && Math.abs(tmp.x) < 1.02 && Math.abs(tmp.y) < 1.02 && d >= it.minDist && d <= it.maxDist;
      const x = ((tmp.x + 1) / 2) * w, y = ((1 - tmp.y) / 2) * h, lw = (it.w = it.el.offsetWidth || it.w || 120);
      if (ok && (shown >= cap || placed.some(([px, py, pw]) => Math.abs(px - x) < (pw + lw) / 2 + 6 && Math.abs(py - y) < 18))) ok = false; // avoid clutter
      if (ok) { placed.push([x, y, lw]); shown++; }
      it.el.style.display = ok ? "" : "none";
      if (ok) it.el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -130%)`;
    }
  }
  function nearestPoint(L, ndc, xs, ys, zs, maxPx = 14) { // index of the catalogue point closest to a click
    const w = renderer.domElement.clientWidth, h = renderer.domElement.clientHeight;
    let best = -1, bestD = maxPx;
    for (let i = 0; i < xs.length; i++) {
      tmp.copy(toScene(xs[i], ys[i], zs[i])).project(L.camera);
      if (tmp.z > 1) continue;
      const d = Math.hypot((tmp.x - ndc.x) * w / 2, (tmp.y - ndc.y) * h / 2);
      if (d < bestD) { bestD = d; best = i; }
    }
    return best;
  }

  // ---------- 1. Nearby stars (1 unit = 1 light year) ----------
  const stars = base("Stars", "✦", { start: new THREE.Vector3(0, 35, 80), min: 0.6, max: 5000, near: 0.01, far: 1e6, prev: 0, next: 2 });
  stars.requires = "stars";
  stars.load = () => {
    const s = data.stars, n = s.count, pos = [], col = [], size = [];
    for (let i = 0; i < n; i++) {
      const v = toScene(s.x_ly[i], s.y_ly[i], s.z_ly[i]);
      pos.push(v.x, v.y, v.z); col.push(...hexToRgb(s.color[i])); size.push(110 * Math.sqrt(Math.max(s.luminosity_solar[i], 1e-5)));
    }
    stars.scene.add(pointCloud(pos, col, size, { scale: 1, fixedSize: false, minSize: 1.4, maxSize: 26 }));
    stars.scene.add(pointCloud([0, 0, 0], [1, 0.95, 0.9], [110], { scale: 1, fixedSize: false, minSize: 4, maxSize: 26 }));
    stars.maxLabels = 28;
    const rings = (stars.groups.rings = new THREE.Group()); stars.scene.add(rings);
    for (const r of [10, 50, 100, 500, 1000]) {
      rings.add(circle(r, 0x4f78b0, 0.35));
      label(stars, `${commas(r)} light years`, "#4f78b0", new THREE.Vector3(r, 0, 0), { cls: "minor", priority: -1, maxDist: r * 12, kind: "ring" });
    }
    label(stars, "Sun · you are here", "#ffcc55", new THREE.Vector3(0, 0, 0), { priority: 100, onclick: () => goLevel(0) });
    const named = [];
    for (let i = 0; i < n; i++) if (s.proper_name[i]) named.push(i);
    for (const i of named) {
      const lum = s.luminosity_solar[i];
      label(stars, s.name[i], s.color[i], toScene(s.x_ly[i], s.y_ly[i], s.z_ly[i]), { cls: "star", lum, onclick: () => starInfo(i), kind: "star" });
    }
    if (data.atlas) atlasStars();
    applySettings();
    stars.onEnter();
  };
  stars.onEnter = () => showPanel("Our stellar neighbourhood", "#cfe0ff", [
    ["Stars shown", commas(data.stars.count)], ["Nearest star", "Proxima Centauri · 4.24 ly"],
    ["Brightest in our sky", "Sirius · 8.6 ly"], ["Scale", "1 light year = 9.46 trillion km"],
  ], "Real stars from the HYG catalogue (Hipparcos, Yale, Gliese) via physics.star_catalog. Colours are blackbody colours from each star's temperature. Click a star; scroll out for the Milky Way.");
  function starInfo(i) {
    const s = data.stars, year = new Date().getUTCFullYear();
    showPanel(s.name[i], s.color[i], [
      ["Distance", `${fmt(s.distance_ly[i], 4)} light years`], ["Light you see left it in", s.distance_ly[i] < year ? `${commas(year - s.distance_ly[i])} AD` : `${commas(s.distance_ly[i] - year)} BC`],
      ["Spectral type", s.spectral_type[i] || "–"], ["Temperature", `${commas(s.temperature_k[i])} K`],
      ["Luminosity (V band)", `${fmt(s.luminosity_solar[i], 4)} × Sun`], ["Apparent magnitude", fmt(s.apparent_magnitude[i], 3)],
      ["Absolute magnitude", fmt(s.absolute_magnitude[i], 3)], ["Constellation", s.constellation[i] || "–"],
    ], "physics.star_catalog (HYG v4.1). Temperature from the B−V colour index.");
  }
  stars.onPick = (ndc) => { const s = data.stars, i = nearestPoint(stars, ndc, s.x_ly, s.y_ly, s.z_ly); if (i >= 0) starInfo(i); };

  // ---------- 2. The Milky Way (1 unit = 1 kpc = 3,262 ly) ----------
  const galaxy = base("Milky Way", "◎", { start: new THREE.Vector3(0, 38, 24), min: 1.2, max: 400, near: 0.01, far: 1e5, prev: 1, next: 3 });
  galaxy.requires = "milkyWay";
  galaxy.load = () => {
    const m = data.milkyWay, P = m.points, pos = [], col = [], size = [];
    for (let i = 0; i < P.x_kpc.length; i++) {
      const v = toScene(P.x_kpc[i], P.y_kpc[i], P.z_kpc[i]);
      const c = P.component[i], w = c === 0 ? 0.3 : c === 2 || c === 4 ? 0.34 : 0.2;
      pos.push(v.x, v.y, v.z); col.push(...hexToRgb(P.color[i]).map((x) => x * w)); size.push(c === 0 ? 1.1 : c === 5 ? 0.4 : 0.8);
    }
    galaxy.scene.add(pointCloud(pos, col, size, { scale: 700, fixedSize: false, minSize: 2, maxSize: 90, opacity: 0.55 }));
    const disc = new THREE.Mesh(new THREE.CircleGeometry(17, 96), new THREE.MeshBasicMaterial({ map: glowTexture([[0, "rgba(255,225,180,.55)"], [0.2, "rgba(240,215,190,.22)"], [0.55, "rgba(160,180,230,.08)"], [1, "rgba(120,150,220,0)"]]), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    disc.rotation.x = -Math.PI / 2; galaxy.scene.add(disc);
    const core = glowSprite(7, [[0, "rgba(255,236,200,.9)"], [0.25, "rgba(255,200,130,.35)"], [1, "rgba(255,170,90,0)"]]);
    galaxy.scene.add(core);
    const gc = m.globular_clusters, gpos = [], gcol = [], gsize = [];
    gc.name.forEach((_, i) => { const v = toScene(gc.x_kpc[i], gc.y_kpc[i], gc.z_kpc[i]); gpos.push(v.x, v.y, v.z); gcol.push(1, 0.85, 0.55); gsize.push(0.25); });
    galaxy.scene.add(pointCloud(gpos, gcol, gsize, { scale: 700, fixedSize: false, minSize: 2, maxSize: 8 }));
    const sun = toScene(...m.sun_position_kpc);
    const ring = circle(0.35, 0xffcc55, 0.9, 64); ring.position.copy(sun); galaxy.scene.add(ring);
    galaxy.scene.add(circle(m.sun_distance_kpc, 0xffcc55, 0.18));
    label(galaxy, "Sun · you are here", "#ffcc55", sun, { priority: 100, onclick: () => goLevel(1) });
    label(galaxy, "Sagittarius A* · central black hole", "#ffd9a8", new THREE.Vector3(0, 0, 0), { priority: 90 });
    for (const a of m.arms) { const p = a.points_kpc[80]; label(galaxy, `${a.name} Arm`, "#9fc3ff", toScene(...p), { cls: "minor", priority: 50 }); }
    const famous = { "OME Cen": "ω Centauri", "47 Tuc": "47 Tucanae", "M 13": "M13 (Hercules)", "M 4": "M4", "M 22": "M22" };
    gc.name.forEach((nm, i) => { if (famous[nm]) label(galaxy, famous[nm], "#ffd98a", toScene(gc.x_kpc[i], gc.y_kpc[i], gc.z_kpc[i]), { cls: "minor", priority: 10, maxDist: 60, kind: "deepsky" }); });
    if (data.atlas) atlasGalaxy();
    applySettings();
    galaxy.onEnter();
  };
  galaxy.onEnter = () => {
    const m = data.milkyWay;
    showPanel("The Milky Way", "#cfe0ff", [
      ["Type", "Barred spiral (SBbc)"], ["Disc diameter (model)", `~${commas(m.disc_diameter_ly)} ly`],
      ["Sun to the centre", `${commas(m.sun_distance_ly)} ly (${fmt(m.sun_distance_kpc, 4)} kpc)`],
      ["Sun's orbital speed", `${fmt(m.circular_speed_at_sun_km_s, 4)} km/s`], ["One galactic year", `${fmt(m.galactic_year_myr, 4)} million years`],
      ["Mass inside the Sun's orbit", `${fmt(m.mass_within_sun_orbit_msun, 3)} Suns`], ["Mass within 163,000 ly", `${fmt(m.mass_within_50kpc_msun, 3)} Suns`],
      ["Globular clusters shown", String(m.globular_clusters.name.length)],
    ], "physics.milky_way: structural model with a bulge + disc + dark-halo rotation curve. The flat rotation curve needs far more mass than the stars: dark matter. Yellow dots are real globular clusters.");
  };

  // ---------- 3. Galaxies of the local universe (1 unit = 1 million ly) ----------
  const galaxies = base("Galaxies", "✺", { start: new THREE.Vector3(0, 60, 150), min: 0.25, max: 9000, near: 0.001, far: 1e6, prev: 2, next: 4 });
  galaxies.load = async () => {
    const r = (await simulate("physics", "galaxy_catalog", { max_distance_mly: 6000, limit: 25000, include_redshift: true })).result;
    data.galaxies = r;
    const pos = [], col = [], size = [];
    for (let i = 0; i < r.count; i++) {
      const v = toScene(r.x_mly[i], r.y_mly[i], r.z_mly[i]);
      const lum = Math.pow(10, -0.4 * (r.absolute_magnitude[i] + 20));
      pos.push(v.x, v.y, v.z); col.push(...TYPE_COLOR(r.type[i]).map((c) => c * Math.min(1, 0.55 + 0.45 * lum))); size.push(Math.max(r.radius_ly[i], 5000) / 1e6 * 2.2);
    }
    galaxies.scene.add(pointCloud(pos, col, size, { scale: 6000, fixedSize: false, minSize: 1.8, maxSize: 70 }));
    galaxies.maxLabels = 30;
    galaxies.scene.add(glowSprite(0.12, [[0, "rgba(255,240,215,1)"], [0.3, "rgba(200,210,255,.4)"], [1, "rgba(150,170,255,0)"]]));
    label(galaxies, "Milky Way · you are here", "#ffcc55", new THREE.Vector3(0, 0, 0), { priority: 100, onclick: () => goLevel(2) });
    const catalogueName = /^(NGC|IC|UGC|PGC|ESO|MCG|CGCG|KK|KDG|DDO|UGCA|HIPASS|LSBC|FGC|AGC|KUG|Mrk|BK|FM|LEDA|AM|dw|Dw|HIZSS|KKH|KKs|KKSG|MB|A \d|F \d|Cas|Cam|Ho |Sc )/;
    const catalogued = [], common = r.common_name || [];
    const gname = (i) => (common[i] && !r.name[i].includes(common[i]) ? `${common[i]} · ${r.name[i]}` : r.name[i]);
    for (let i = 0; i < r.count; i++) {
      const lum = Math.pow(10, -0.4 * (r.absolute_magnitude[i] + 20));
      if (!common[i] && catalogueName.test(r.name[i])) { catalogued.push([lum / Math.max(r.distance_mly[i], 0.5) ** 2, i]); continue; }
      label(galaxies, gname(i), "#cfe0ff", toScene(r.x_mly[i], r.y_mly[i], r.z_mly[i]), { cls: "minor", lum: lum * (common[i] ? 4e4 : 1e4), onclick: () => galaxyInfo(i), kind: "galaxy" });
    }
    catalogued.sort((a, b) => b[0] - a[0]);  // the brightest-looking catalogue galaxies get names too, when switched on
    for (const [, i] of catalogued.slice(0, 2500)) {
      const lum = Math.pow(10, -0.4 * (r.absolute_magnitude[i] + 20));
      label(galaxies, r.name[i], "#a9bedb", toScene(r.x_mly[i], r.y_mly[i], r.z_mly[i]), { cls: "minor", lum: lum * 3e3, onclick: () => galaxyInfo(i), kind: "galaxyCat" });
    }
    const m87 = r.name.indexOf("M 87");
    if (m87 >= 0) label(galaxies, "Virgo Cluster", "#ffd9a8", toScene(r.x_mly[m87], r.y_mly[m87], r.z_mly[m87] + 4), { priority: 80, minDist: 60 });
    const grings = (galaxies.groups.rings = new THREE.Group()); galaxies.scene.add(grings);
    for (const d of [10, 100, 1000]) { grings.add(circle(d, 0x4f78b0, 0.3)); label(galaxies, `${commas(d)} million ly`, "#4f78b0", new THREE.Vector3(d, 0, 0), { cls: "minor", priority: -1, maxDist: d * 10, kind: "ring" }); }
    if (data.atlas) atlasGalaxies();
    applySettings();
    galaxies.onEnter();
  };
  galaxies.onEnter = () => {
    const r = data.galaxies;
    if (!r) return;
    showPanel("The local universe", "#cfe0ff", [
      ["Galaxies shown", commas(r.count)], ["Farthest in this catalogue", `${commas(Math.max(...r.distance_mly))} million ly`],
      ["Nearest big spiral", "Andromeda · 2.5 million ly"], ["Nearest giant cluster", "Virgo · ~54 million ly"],
    ], "Real galaxies with measured distances via physics.galaxy_catalog (NED, RC3, Karachentsev+ 2004). Blue-white: spirals and irregulars; gold: ellipticals and lenticulars. Click one.");
  };
  function galaxyInfo(i) {
    const r = data.galaxies;
    const nick = r.common_name?.[i] && !r.name[i].includes(r.common_name[i]) ? r.common_name[i] : null;
    showPanel(nick || r.name[i], "#cfe0ff", [
      ...(nick ? [["Catalogue", r.name[i]]] : []), ["Type", r.type[i] || "–"], ["Distance", `${fmt(r.distance_mly[i], 4)} million ly`],
      ["Light left it", `${fmt(r.distance_mly[i], 4)} million years ago`], ["Radius", `${commas(r.radius_ly[i])} ly`],
      ["Absolute magnitude", fmt(r.absolute_magnitude[i], 3)],
      ["Moving away (Hubble law)", r.hubble_velocity_km_s[i] === null ? "bound by local gravity" : `${commas(r.hubble_velocity_km_s[i])} km/s`],
      ["Redshift z", r.redshift[i] === null ? "–" : fmt(r.redshift[i], 4)],
    ], "physics.galaxy_catalog: measured distance; recession speed from Hubble's law with H0 = 67.66 km/s/Mpc.");
  }
  galaxies.onPick = (ndc) => { const r = data.galaxies; if (!r) return; const i = nearestPoint(galaxies, ndc, r.x_mly, r.y_mly, r.z_mly); if (i >= 0) galaxyInfo(i); };

  // ---------- 4. The observable universe (1 unit = 1 billion ly, comoving) ----------
  const cosmos = base("Universe", "◯", { start: new THREE.Vector3(0, 55, 125), min: 0.4, max: 400, near: 0.001, far: 1e5, prev: 3 });
  cosmos.load = async () => {
    const [c, g] = await Promise.all([simulate("physics", "cosmology", { z: 1 }), data.galaxies ? Promise.resolve({ result: data.galaxies }) : simulate("physics", "galaxy_catalog", { max_distance_mly: 3000 })]);
    const r = c.result, gal = g.result;
    data.cosmology = r; data.galaxies = gal;
    const pos = [], col = [], size = [];
    for (let i = 0; i < gal.count; i++) { const v = toScene(gal.x_mly[i] / 1000, gal.y_mly[i] / 1000, gal.z_mly[i] / 1000); pos.push(v.x, v.y, v.z); col.push(...TYPE_COLOR(gal.type[i]).map((x) => x * 0.8)); size.push(0.02); }
    cosmos.scene.add(pointCloud(pos, col, size, { scale: 900, fixedSize: false, minSize: 1.2, maxSize: 6 }));
    // CMB: the last-scattering surface, glowing faintly; beyond it the particle horizon
    const cmb = new THREE.Mesh(new THREE.SphereGeometry(r.cmb_comoving_distance_gly, 96, 64), new THREE.ShaderMaterial({
      uniforms: { tint: { value: new THREE.Color(1.0, 0.55, 0.3) } },
      vertexShader: "varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(mat3(modelMatrix)*normal); vec4 w = modelMatrix*vec4(position,1.0); vP = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }",
      fragmentShader: "uniform vec3 tint; varying vec3 vN; varying vec3 vP; void main(){ float f = pow(1.0 - abs(dot(normalize(vN), normalize(cameraPosition - vP))), 2.0); gl_FragColor = vec4(tint * (0.08 + 0.5 * f), 0.08 + 0.5 * f); }",
      transparent: true, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    cosmos.scene.add(cmb);
    cosmos.scene.add(shell(r.observable_universe_radius_gly, 0x9fc3ff, 0.25));
    cosmos.scene.add(shell(r.hubble_radius_gly, 0x6fa0ff, 0.12));
    label(cosmos, `Edge of the observable universe · ${fmt(r.observable_universe_radius_gly, 3)} billion ly`, "#9fc3ff", new THREE.Vector3(-r.observable_universe_radius_gly * 0.72, r.observable_universe_radius_gly * 0.69, 0), { priority: 90 });
    label(cosmos, `Cosmic microwave background · z = ${commas(r.cmb_redshift)} · 380,000 years after the Big Bang`, "#ffae7a", new THREE.Vector3(r.cmb_comoving_distance_gly * 0.72, -r.cmb_comoving_distance_gly * 0.69, 0), { priority: 80 });
    label(cosmos, `Hubble sphere · ${fmt(r.hubble_radius_gly, 3)} billion ly`, "#6fa0ff", new THREE.Vector3(0, 0, r.hubble_radius_gly), { cls: "minor", priority: 40 });
    r.shells.filter((s) => s.z >= 0.5 && s.z <= 100).forEach((s, k) => {
      const ring = circle(s.comoving_distance_gly, 0x4f78b0, 0.3); cosmos.scene.add(ring);
      const a = -0.5 + k * 0.45, d = s.comoving_distance_gly;
      label(cosmos, `z = ${s.z} · light left ${fmt(s.lookback_time_gyr, 3)} billion years ago`, "#7fa6d8", new THREE.Vector3(d * Math.cos(a), 0, d * Math.sin(a)), { cls: "minor", priority: 30 - s.z });
    });
    label(cosmos, "Mapped galaxies (~2 billion ly)", "#ffcc55", new THREE.Vector3(0, 0, 0), { priority: 100, onclick: () => goLevel(3), maxDist: 150 });
    if (data.atlas) atlasCosmos();
    applySettings();
    cosmos.onEnter();
  };
  cosmos.onEnter = () => {
    const r = data.cosmology;
    if (!r) return;
    showPanel("The observable universe", "#9fc3ff", [
      ["Age", `${fmt(r.age_now_gyr, 4)} billion years`], ["Radius (comoving)", `${fmt(r.observable_universe_radius_gly, 4)} billion ly`],
      ["Diameter", `${fmt(r.observable_universe_diameter_gly, 4)} billion ly`], ["Hubble radius", `${fmt(r.hubble_radius_gly, 4)} billion ly`],
      ["Event horizon", `${fmt(r.event_horizon_gly, 4)} billion ly`], ["CMB emitted at", `z = ${r.cmb_redshift}, now ${fmt(r.cmb_comoving_distance_gly, 4)} billion ly away`],
      ["Critical density", `${fmt(r.critical_density_kg_m3, 3)} kg/m³ (≈ 5 protons per m³)`], ["Matter inside it", `${fmt(r.matter_mass_in_observable_universe_kg, 3)} kg`],
      ["Dark energy share (ΩΛ)", fmt(r.omega_lambda, 4)],
    ], "physics.cosmology: Friedmann equation, Planck 2018 ΛCDM. Distances are comoving (where those regions are now). The universe is 13.8 billion years old but 93 billion ly across because space expanded while light travelled.");
  };

  // ---------- the sky atlas on every scale (physics.sky_atlas) ----------
  const lineSegs = (pairs, color, opacity) => {
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pairs), 3));
    return new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false }));
  };
  const conName = (c) => (S.get("constellation_hindi") && c.hindi ? `${c.name} · ${c.hindi}` : c.name);
  const conLabels = [];
  function conInfo(c) {
    const stars_ = c.lines.flat().filter((p) => p.distance_ly);
    const near = Math.min(...stars_.map((p) => p.distance_ly)), far = Math.max(...stars_.map((p) => p.distance_ly));
    showPanel(c.name, "#9fc3ff", [["Hindi name", c.hindi || "–"], ["Latin genitive", c.genitive || "–"], ["Abbreviation", c.abbr],
      ["Nearest star in the figure", `${fmt(near, 4)} ly`], ["Farthest star in the figure", `${fmt(far, 4)} ly`]],
      "The stars of a constellation only line up as seen from Earth: in 3D they are at very different distances. Fly around and the figure falls apart.");
  }
  function atlasStars() {
    if (stars.atlasDone || !data.atlas) return; stars.atlasDone = true;
    const A = data.atlas, pairs = [], dome = [], R = DOME_LY;
    const onDome = (u) => toScene(u[0] * R, u[1] * R, u[2] * R);
    for (const c of A.constellations) {
      for (const line of c.lines) for (let k = 1; k < line.length; k++) {
        const a = toScene(...line[k - 1].xyz_ly), b = toScene(...line[k].xyz_ly); pairs.push(a.x, a.y, a.z, b.x, b.y, b.z);
        const p = onDome(line[k - 1].unit), q = onDome(line[k].unit); dome.push(p.x, p.y, p.z, q.x, q.y, q.z);
      }
      const it = label(stars, conName(c), "#9fc3ff", onDome(c.label_unit), { cls: "con", priority: 20 - c.rank * 4, onclick: () => conInfo(c), kind: "con" });
      it.dome = it.pos; it.real = toScene(...c.centre_ly);
      conLabels.push([it, c]);
    }
    stars.scene.add((stars.groups.constellation_real = lineSegs(pairs, 0x6f9fe0, 0.5)));
    const domeLines = (stars.groups.constellation_dome = lineSegs(dome, 0x6f9fe0, 0.4));
    stars.scene.add(domeLines);
    stars.beforeRender = () => { // the dome is the sky seen from home; fade it out as the camera leaves it
      const k = Math.min(1, Math.max(0, 1 - (stars.camera.position.length() - 600) / 700));
      domeLines.material.opacity = 0.4 * k;
      for (const [it] of conLabels) it.hidden = !S.get("constellation_3d") && k < 0.3;
    };
    // exoplanet systems
    const E = A.exoplanets, epos = [], ecol = [], esize = [];
    for (let i = 0; i < E.count; i++) { const v = toScene(E.x_ly[i], E.y_ly[i], E.z_ly[i]); epos.push(v.x, v.y, v.z); ecol.push(0.35, 0.95, 0.6); esize.push(0.6 + 0.25 * E.n[i]); }
    stars.scene.add((stars.groups.exoplanets = pointCloud(epos, ecol, esize, { scale: 1, fixedSize: false, minSize: 1.6, maxSize: 7 })));
    for (let i = 0; i < E.count; i++) {
      if (!(E.n[i] >= 3 || E.distance_ly[i] < 40)) continue;
      label(stars, `${E.host[i]} · ${E.n[i]} planet${E.n[i] > 1 ? "s" : ""}`, "#5ff29a", toScene(E.x_ly[i], E.y_ly[i], E.z_ly[i]), { cls: "minor exo", lum: E.n[i] * 2, onclick: () => exoInfo(i), kind: "exo" });
    }
    // nebulae and clusters with a known distance
    const dso = new THREE.Group();
    for (const d of A.deep_sky) {
      if (!d.xyz_ly || d.distance_ly > 9000) continue;
      const col = DSO_COLOR(d.type), sp = glowSprite(Math.max(4, Math.min(60, (d.size_arcmin || 10) / 60 * Math.PI / 180 * d.distance_ly * 6)), [[0, col + "cc"], [0.4, col + "44"], [1, col + "00"]]);
      sp.position.copy(toScene(...d.xyz_ly)); dso.add(sp);
      label(stars, d.name, col, sp.position.clone(), { cls: "minor dso", priority: 12 - (d.magnitude || 8), onclick: () => dsoInfo(d), kind: "deepsky", minDist: 5 });
    }
    stars.scene.add((stars.groups.deep_sky = dso));
    applySettings();
  }
  function exoInfo(i) {
    const E = data.atlas.exoplanets;
    showPanel(E.host[i], "#5ff29a", [["Planets", String(E.n[i])], ["Names", E.planets[i].join(", ")], ["Distance", `${fmt(E.distance_ly[i], 4)} ly`],
      ["Found by", E.methods[i].join(", ")], ["First found", E.year[i] ? String(E.year[i]) : "–"]],
      "Open Exoplanet Catalogue via physics.sky_atlas. Every green dot is a star with known planets.");
  }
  function dsoInfo(d) {
    showPanel(d.name, DSO_COLOR(d.type), [["Type", d.type], ["Catalogue", [d.messier, d.id].filter(Boolean).join(" · ")],
      ["Distance", d.distance_ly ? `${commas(d.distance_ly)} ly` : "not measured"], ["Light you see left it", d.distance_ly ? `${commas(d.distance_ly)} years ago` : "–"],
      ["Brightness (magnitude)", d.magnitude === null ? "–" : fmt(d.magnitude, 3)], ["Size on the sky", d.size_arcmin ? `${fmt(d.size_arcmin, 3)}′` : "–"]],
      `OpenNGC (NGC/IC/Messier) via physics.sky_atlas; distance from ${d.distance_source || "no measurement"}.`);
  }
  function atlasGalaxy() {
    if (galaxy.atlasDone || !data.atlas) return; galaxy.atlasDone = true;
    const A = data.atlas, O = A.open_clusters, pos = [], col = [], size = [];
    for (let i = 0; i < O.count; i++) { const v = toScene(O.x_kpc[i], O.y_kpc[i], O.z_kpc[i]); pos.push(v.x, v.y, v.z); col.push(0.55, 0.75, 1.0); size.push(0.05); }
    galaxy.scene.add((galaxy.groups.open_clusters = pointCloud(pos, col, size, { scale: 700, fixedSize: false, minSize: 1.2, maxSize: 4, opacity: 0.8 })));
    const dso = new THREE.Group();
    for (const d of A.deep_sky) {
      if (!d.galactocentric_kpc || d.distance_ly > 60000) continue;
      const colr = DSO_COLOR(d.type), sp = glowSprite(0.35, [[0, colr + "ee"], [0.4, colr + "55"], [1, colr + "00"]]);
      sp.position.copy(toScene(...d.galactocentric_kpc)); dso.add(sp);
      label(galaxy, d.name, colr, sp.position.clone(), { cls: "minor dso", priority: 8 - (d.magnitude || 8) / 2, onclick: () => dsoInfo(d), kind: "deepsky", maxDist: 40 });
    }
    galaxy.scene.add((galaxy.groups.deep_sky = dso));
    applySettings();
  }
  function structInfo(s) {
    showPanel(s.name, hex6(STRUCT_COLOR[s.kind] || 0xffffff), [["What it is", s.kind[0].toUpperCase() + s.kind.slice(1)], ["Distance", `${commas(s.distance_mly)} million ly`],
      ...(s.redshift ? [["Redshift z", String(s.redshift)]] : []), ...(s.radius_mly ? [["Typical radius", `${commas(s.radius_mly)} million ly`]] : [])], s.note);
  }
  function atlasGalaxies() {
    if (galaxies.atlasDone || !data.atlas) return; galaxies.atlasDone = true;
    const shapes = new THREE.Group();
    for (const s of data.atlas.structures) {
      if (s.distance_mly > 6000) continue;
      const c = STRUCT_COLOR[s.kind] || 0xffffff, p = toScene(s.x_mly, s.y_mly, s.z_mly);
      const sh = shell(s.radius_mly, c, s.kind === "void" ? 0.18 : 0.12); sh.position.copy(p); shapes.add(sh);
      label(galaxies, s.name, hex6(c), p.clone().add(new THREE.Vector3(0, s.radius_mly * 0.6, 0)), { priority: s.kind === "supercluster" ? 70 : 60, onclick: () => structInfo(s), kind: "structure", minDist: s.radius_mly * 0.8 });
    }
    galaxies.scene.add((galaxies.groups.structures = shapes));
    applySettings();
  }
  function atlasCosmos() {
    if (cosmos.atlasDone || !data.atlas) return; cosmos.atlasDone = true;
    const shapes = new THREE.Group(), pos = [], col = [], size = [];
    for (const s of [...data.atlas.structures, ...data.atlas.far_objects.map((f) => ({ ...f, kind: "far" }))]) {
      const p = toScene(s.x_mly / 1000, s.y_mly / 1000, s.z_mly / 1000);
      pos.push(p.x, p.y, p.z); col.push(1, 0.75, 0.45); size.push(0.25);
      if (s.distance_mly > 400) label(cosmos, `${s.name}${s.redshift ? ` · z = ${s.redshift}` : ""}`, s.kind === "far" ? "#ffb37a" : hex6(STRUCT_COLOR[s.kind] || 0xffffff), p,
        { cls: "minor", priority: 50 + Math.log10(s.distance_mly), onclick: () => structInfo({ ...s, kind: s.kind === "far" ? "distant object" : s.kind }), kind: "structure" });
    }
    shapes.add(pointCloud(pos, col, size, { scale: 900, fixedSize: false, minSize: 3, maxSize: 9 }));
    cosmos.scene.add((cosmos.groups.structures = shapes));
    applySettings();
  }
  function applySettings() {
    const real = !!S.get("constellation_3d"), lines = !!S.get("constellation_lines");
    for (const L of [stars, galaxy, galaxies, cosmos]) for (const [k, g] of Object.entries(L.groups)) {
      g.visible = k === "constellation_real" ? lines && real : k === "constellation_dome" ? lines && !real : !!S.get(k);
    }
    for (const [it, c] of conLabels) { it.el.textContent = conName(c); it.pos = real ? it.real : it.dome; it.minDist = real ? 40 : 0; }
  }
  S.onChange(() => applySettings());

  const levels = [stars, galaxy, galaxies, cosmos];
  return {
    levels,
    setData(d) {
      Object.assign(data, d);
      if (d.atlas) { if (stars.ready) atlasStars(); if (galaxy.ready) atlasGalaxy(); if (data.galaxies && galaxies.ready) atlasGalaxies(); if (data.cosmology && cosmos.ready) atlasCosmos(); }
    },
    resize(w, h) { for (const L of levels) { L.camera.aspect = w / h; L.camera.updateProjectionMatrix(); } },
    dispose() {
      for (const c of listeners) c.dispose();
      for (const L of levels) L.scene.traverse((o) => { o.geometry?.dispose?.(); const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { x.map?.dispose(); x.dispose(); }); });
    },
    hidePanel,
  };
}
