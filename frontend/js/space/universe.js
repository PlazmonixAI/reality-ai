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

export function createUniverseLevels({ renderer, labels, showPanel, hidePanel, goLevel }) {
  const data = {};
  const listeners = [];
  const base = (name, icon, { start, min, max, near, far, prev, next }) => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, 1, near, far);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enabled = false; controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.minDistance = min; controls.maxDistance = max;
    const L = {
      name, icon, scene, camera, controls, labelItems: [], ready: false,
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
        placeLabels(L);
        renderer.render(scene, camera);
      },
      pick(ndc) { L.onPick?.(ndc); },
    };
    listeners.push(controls);
    return L;
  };
  function label(L, text, color, pos, { cls = "", onclick = null, priority = 0, minDist = 0, maxDist = Infinity, lum = null } = {}) {
    const e = el("button", { class: `ss-label ${cls}`, type: "button", onclick }, text);
    e.style.setProperty("--c", color);
    const it = { el: e, pos, priority, minDist, maxDist, lum };
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
    for (const it of items) {
      const d = cam.distanceTo(it.pos);
      tmp.copy(it.pos).project(L.camera);
      let ok = tmp.z < 1 && Math.abs(tmp.x) < 1.02 && Math.abs(tmp.y) < 1.02 && d >= it.minDist && d <= it.maxDist;
      const x = ((tmp.x + 1) / 2) * w, y = ((1 - tmp.y) / 2) * h, lw = (it.w = it.el.offsetWidth || it.w || 120);
      if (ok && (shown >= (L.maxLabels || 60) || placed.some(([px, py, pw]) => Math.abs(px - x) < (pw + lw) / 2 + 6 && Math.abs(py - y) < 18))) ok = false; // avoid clutter
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
    for (const r of [10, 50, 100, 500, 1000]) {
      stars.scene.add(circle(r, 0x4f78b0, 0.35));
      label(stars, `${commas(r)} light years`, "#4f78b0", new THREE.Vector3(r, 0, 0), { cls: "minor", priority: -1, maxDist: r * 12 });
    }
    label(stars, "Sun · you are here", "#ffcc55", new THREE.Vector3(0, 0, 0), { priority: 100, onclick: () => goLevel(0) });
    const named = [];
    for (let i = 0; i < n; i++) if (s.proper_name[i]) named.push(i);
    for (const i of named) {
      const lum = s.luminosity_solar[i];
      label(stars, s.name[i], s.color[i], toScene(s.x_ly[i], s.y_ly[i], s.z_ly[i]), { cls: "star", lum, onclick: () => starInfo(i) });
    }
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
    gc.name.forEach((nm, i) => { if (famous[nm]) label(galaxy, famous[nm], "#ffd98a", toScene(gc.x_kpc[i], gc.y_kpc[i], gc.z_kpc[i]), { cls: "minor", priority: 10, maxDist: 60 }); });
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
    const r = (await simulate("physics", "galaxy_catalog", { max_distance_mly: 3000 })).result;
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
    for (let i = 0; i < r.count; i++) {
      if (catalogueName.test(r.name[i]) && !/^NGC (5128|4594|4486|3031|5194|224|598)$/.test(r.name[i])) continue;
      const lum = Math.pow(10, -0.4 * (r.absolute_magnitude[i] + 20));
      label(galaxies, r.name[i], "#cfe0ff", toScene(r.x_mly[i], r.y_mly[i], r.z_mly[i]), { cls: "minor", lum: lum * 1e4, onclick: () => galaxyInfo(i) });
    }
    const m87 = r.name.indexOf("M 87");
    if (m87 >= 0) label(galaxies, "Virgo Cluster", "#ffd9a8", toScene(r.x_mly[m87], r.y_mly[m87], r.z_mly[m87] + 4), { priority: 80, minDist: 60 });
    label(galaxies, "Local Group", "#ffd9a8", new THREE.Vector3(0, 2.2, 0), { priority: 85, minDist: 8, maxDist: 400 });
    for (const d of [10, 100, 1000]) { galaxies.scene.add(circle(d, 0x4f78b0, 0.3)); label(galaxies, `${commas(d)} million ly`, "#4f78b0", new THREE.Vector3(d, 0, 0), { cls: "minor", priority: -1, maxDist: d * 10 }); }
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
    showPanel(r.name[i], "#cfe0ff", [
      ["Type", r.type[i] || "–"], ["Distance", `${fmt(r.distance_mly[i], 4)} million ly`],
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

  const levels = [stars, galaxy, galaxies, cosmos];
  return {
    levels,
    setData(d) { Object.assign(data, d); },
    resize(w, h) { for (const L of levels) { L.camera.aspect = w / h; L.camera.updateProjectionMatrix(); } },
    dispose() {
      for (const c of listeners) c.dispose();
      for (const L of levels) L.scene.traverse((o) => { o.geometry?.dispose?.(); const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { x.map?.dispose(); x.dispose(); }); });
    },
    hidePanel,
  };
}
