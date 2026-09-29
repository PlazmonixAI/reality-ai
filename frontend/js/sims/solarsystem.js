// Solar System 3D: physics.solar_system gives every body's real position (JPL elements), spin angle, pole and
// facts for any date; the browser renders them with three.js and interpolates between the engine's samples.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";

const TEX = "assets/textures/";
const J2000 = 2451545.0;
const COLORS = { mercury: "#9c8f86", venus: "#d8b27a", earth: "#4f8fe0", moon: "#b9b9b9", mars: "#d0643b", jupiter: "#d6a77a",
  saturn: "#e3cf96", uranus: "#8fd3e0", neptune: "#4a6fe0", pluto: "#bfa58a", sun: "#ffcc55" };
const SPEEDS = [ // simulated days per real second
  [0, "paused"], [1 / 86400, "real time"], [1 / 1440, "1 min / s"], [1 / 24, "1 hour / s"], [0.25, "6 hours / s"], [1, "1 day / s"],
  [7, "1 week / s"], [30, "1 month / s"], [182.6, "6 months / s"], [365.25, "1 year / s"],
];
const jdToDate = (jd) => new Date((jd - 2440587.5) * 86400000);
const dateToJd = (d) => d.getTime() / 86400000 + 2440587.5;

// Scene mapping: ecliptic (x, y, z) → three.js (x, z, −y) so the ecliptic is the horizontal plane
const toScene = (p) => new THREE.Vector3(p[0], p[2], -p[1]);

function compress(p, real) {
  const r = Math.hypot(p[0], p[1], p[2]);
  if (r === 0) return toScene([0, 0, 0]);
  const k = real ? 40 : (40 * Math.pow(r, 0.55)) / r; // AU → scene units (compressed keeps directions)
  return toScene([p[0] * k, p[1] * k, p[2] * k]);
}
function displayRadius(km, real) {
  if (real) return (km / 149597870.7) * 40; // true scale: planets become specks
  if (km > 100000) return 5.2; // the Sun
  return 0.55 * Math.pow(km / 6371, 0.45);
}

// Polar interpolation around the centre (keeps orbits round between engine samples)
function interp(a, b, f) {
  const ra = Math.hypot(a[0], a[1]), rb = Math.hypot(b[0], b[1]);
  let ta = Math.atan2(a[1], a[0]), tb = Math.atan2(b[1], b[0]);
  if (tb - ta > Math.PI) tb -= 2 * Math.PI; else if (ta - tb > Math.PI) tb += 2 * Math.PI;
  const r = ra + (rb - ra) * f, t = ta + (tb - ta) * f;
  return [r * Math.cos(t), r * Math.sin(t), a[2] + (b[2] - a[2]) * f];
}

function glowTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 256;
  const g = c.getContext("2d"), grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, "rgba(255,240,200,1)"); grad.addColorStop(0.2, "rgba(255,200,90,.65)"); grad.addColorStop(0.5, "rgba(255,140,40,.16)"); grad.addColorStop(1, "rgba(255,120,20,0)");
  g.fillStyle = grad; g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

const EARTH_VERT = `varying vec2 vUv; varying vec3 vN; varying vec3 vPos;
void main(){ vUv = uv; vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position,1.0); vPos = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const EARTH_FRAG = `uniform sampler2D dayMap; uniform sampler2D nightMap; uniform sampler2D specMap; uniform vec3 sunPos;
varying vec2 vUv; varying vec3 vN; varying vec3 vPos;
void main(){
  vec3 n = normalize(vN); vec3 l = normalize(sunPos - vPos); vec3 v = normalize(cameraPosition - vPos);
  float ndl = dot(n, l);
  vec3 day = texture2D(dayMap, vUv).rgb * (0.06 + 1.15 * max(ndl, 0.0));
  vec3 night = texture2D(nightMap, vUv).rgb * vec3(1.0, 0.85, 0.6) * 2.6;
  float dayMix = smoothstep(-0.12, 0.22, ndl);
  vec3 col = mix(night, day, dayMix);
  float water = texture2D(specMap, vUv).r;
  vec3 h = normalize(l + v);
  col += vec3(1.0, 0.95, 0.85) * pow(max(dot(n, h), 0.0), 60.0) * water * 0.55 * dayMix;
  float rim = pow(1.0 - max(dot(n, v), 0.0), 3.0);
  col += vec3(0.3, 0.55, 1.0) * rim * 0.35 * dayMix;
  gl_FragColor = vec4(col, 1.0);
}`;
const ATMO_FRAG = `uniform vec3 sunPos; uniform vec3 tint; varying vec3 vN; varying vec3 vPos;
void main(){ vec3 n = normalize(vN); vec3 v = normalize(cameraPosition - vPos); vec3 l = normalize(sunPos - vPos);
  float rim = pow(1.0 - abs(dot(n, v)), 2.5); float lit = smoothstep(-0.3, 0.4, dot(n, l));
  gl_FragColor = vec4(tint, rim * lit * 0.9); }`;
const ATMO_VERT = `varying vec3 vN; varying vec3 vPos; void main(){ vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position,1.0); vPos = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;

export default {
  mount(root) {
    const loader = new THREE.TextureLoader();
    const tex = (name, srgb = true) => { const t = loader.load(TEX + name); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };

    // ---------- layout (full-bleed canvas with floating controls) ----------
    const view = el("div", { class: "ss-view" });
    const labels = el("div", { class: "ss-labels" });
    const dateBig = el("div", { class: "ss-date" }), timeSmall = el("div", { class: "ss-time" });
    const speedText = el("span", { class: "ss-speed-text" });
    const info = el("aside", { class: "ss-info hidden" });
    const list = el("div", { class: "ss-list hidden" });
    const status = el("div", { class: "ss-status" }, "Loading the Solar System…");
    let simJd = dateToJd(new Date()), window_ = null, loading = false, firstLoad = true;
    let speedIdx = 5, playing = true, showOrbits = true, showLabels = true, realScale = false;
    const tool = (icon, title, onclick) => el("button", { class: "ss-tool", type: "button", title, "aria-label": title, onclick }, icon);
    const bOrbits = tool("◯", "Orbits", () => { showOrbits = !showOrbits; bOrbits.classList.toggle("off", !showOrbits); orbitsGroup.visible = showOrbits; });
    const bLabels = tool("Aa", "Labels", () => { showLabels = !showLabels; bLabels.classList.toggle("off", !showLabels); labels.style.display = showLabels ? "" : "none"; });
    const bScale = tool("⤢", "Real scale (distances and sizes)", () => { realScale = !realScale; bScale.classList.toggle("on", realScale); rebuildScale(); });
    const bList = tool("☰", "Planets", () => list.classList.toggle("hidden"));
    const bHome = tool("⌂", "Whole Solar System", () => select(null));
    const bPlay = el("button", { class: "ss-btn", type: "button", "aria-label": "Play or pause", onclick: () => { playing = !playing; bPlay.textContent = playing ? "❚❚" : "▶"; } }, "❚❚");
    const slower = el("button", { class: "ss-btn", type: "button", "aria-label": "Slower", onclick: () => setSpeed(speedIdx - 1) }, "◀◀");
    const faster = el("button", { class: "ss-btn", type: "button", "aria-label": "Faster", onclick: () => setSpeed(speedIdx + 1) }, "▶▶");
    const reverse = el("button", { class: "ss-btn", type: "button", title: "Run time backwards", onclick: () => { dir = -dir; reverse.classList.toggle("on", dir < 0); } }, "⇆");
    const today = el("button", { class: "ss-btn text", type: "button", onclick: () => { simJd = dateToJd(new Date()); window_ = null; } }, "Today");
    const dateInput = el("input", { class: "ss-dateinput", type: "date", "aria-label": "Jump to date", onchange: () => { if (dateInput.value) { simJd = dateToJd(new Date(dateInput.value + "T12:00:00Z")); window_ = null; } } });
    root.append(el("div", { class: "ss-root" }, view, labels,
      el("div", { class: "ss-top" }, el("div", { class: "ss-brand" }, "SOLAR SYSTEM ", el("b", {}, "3D")), dateBig, timeSmall),
      el("div", { class: "ss-toolbar" }, bList, bHome, bOrbits, bLabels, bScale),
      list, info, status,
      el("div", { class: "ss-timebar" }, reverse, slower, bPlay, faster, speedText, today, dateInput),
      el("div", { class: "ss-credit" }, "Positions: JPL Keplerian elements via the Reality ASM engine · textures: see CREDITS")));
    function setSpeed(i) { speedIdx = Math.max(1, Math.min(SPEEDS.length - 1, i)); speedText.textContent = SPEEDS[speedIdx][1]; window_ = null; }
    let dir = 1;
    setSpeed(speedIdx);

    // ---------- three.js scene ----------
    const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    view.append(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.001, 100000);
    camera.position.set(0, 120, 260);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 0.01; controls.maxDistance = 8000;
    scene.add(new THREE.AmbientLight(0x404050, 0.35));
    const sunLight = new THREE.PointLight(0xffffff, 3.2, 0, 0);
    scene.add(sunLight);
    const stars = new THREE.Mesh(new THREE.SphereGeometry(20000, 64, 32), new THREE.MeshBasicMaterial({ map: tex("stars.png"), side: THREE.BackSide, color: new THREE.Color(2.2, 2.2, 2.4), depthWrite: false }));
    scene.add(stars);
    const orbitsGroup = new THREE.Group();
    scene.add(orbitsGroup);

    const bodies = {}; // id → {group, spin, mesh, radiusKm, data, label, orbitLine}
    function makeBody(d) {
      const id = d.id, group = new THREE.Group(), tilt = new THREE.Group(), spin = new THREE.Group();
      group.add(tilt); tilt.add(spin);
      // Tilt: align local +Y with the engine's pole direction (ecliptic → scene)
      const pole = toScene(d.pole_ecliptic).normalize();
      tilt.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), pole);
      const geo = new THREE.SphereGeometry(1, 96, 64);
      let mesh;
      if (id === "sun") {
        mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: tex("sun.jpg"), color: new THREE.Color(1.4, 1.3, 1.15) }));
        const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
        glow.scale.set(7, 7, 1); group.add(glow); bodies.glow = glow;
      } else if (id === "earth") {
        mesh = new THREE.Mesh(geo, new THREE.ShaderMaterial({ uniforms: { dayMap: { value: tex("earth_day.jpg") }, nightMap: { value: tex("earth_night.jpg") }, specMap: { value: tex("earth_water.png", false) }, sunPos: { value: new THREE.Vector3() } }, vertexShader: EARTH_VERT, fragmentShader: EARTH_FRAG }));
        const clouds = new THREE.Mesh(new THREE.SphereGeometry(1.012, 96, 64), new THREE.MeshStandardMaterial({ map: tex("earth_clouds.png"), transparent: true, opacity: 0.9, depthWrite: false, roughness: 1 }));
        spin.add(clouds); bodies.clouds = clouds;
        const atmo = new THREE.Mesh(new THREE.SphereGeometry(1.06, 64, 48), new THREE.ShaderMaterial({ uniforms: { sunPos: { value: new THREE.Vector3() }, tint: { value: new THREE.Color(0.35, 0.6, 1.0) } }, vertexShader: ATMO_VERT, fragmentShader: ATMO_FRAG, transparent: true, blending: THREE.AdditiveBlending, side: THREE.BackSide, depthWrite: false }));
        tilt.add(atmo); bodies.earthAtmo = atmo;
      } else {
        const mat = new THREE.MeshStandardMaterial({ map: tex(`${id}.jpg`), roughness: 1, metalness: 0 });
        if (id === "venus") mat.color = new THREE.Color(1.0, 0.93, 0.8);
        mesh = new THREE.Mesh(geo, mat);
        if (id === "venus" || id === "mars") {
          const tint = id === "venus" ? new THREE.Color(1.0, 0.85, 0.55) : new THREE.Color(0.9, 0.55, 0.4);
          const atmo = new THREE.Mesh(new THREE.SphereGeometry(1.04, 48, 32), new THREE.ShaderMaterial({ uniforms: { sunPos: { value: new THREE.Vector3() }, tint: { value: tint } }, vertexShader: ATMO_VERT, fragmentShader: ATMO_FRAG, transparent: true, blending: THREE.AdditiveBlending, side: THREE.BackSide, depthWrite: false }));
          tilt.add(atmo); (bodies.atmos ||= []).push(atmo);
        }
      }
      spin.add(mesh);
      if (id === "saturn" || id === "uranus") {
        const [inner, outer] = id === "saturn" ? [1.24, 2.27] : [1.64, 2.0];
        const ringTex = tex(`${id}_ring.png`);
        const ring = new THREE.Mesh(new THREE.RingGeometry(inner, outer, 180, 1), new THREE.MeshStandardMaterial({ map: ringTex, transparent: true, side: THREE.DoubleSide, roughness: 1, opacity: id === "saturn" ? 1 : 0.55, depthWrite: false }));
        // RingGeometry UVs are planar across the outer diameter, matching a top-down ring image
        const pos = ring.geometry.attributes.position, uv = ring.geometry.attributes.uv;
        for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getX(i) / (2 * outer) + 0.5, pos.getY(i) / (2 * outer) + 0.5);
        ring.rotation.x = -Math.PI / 2;
        tilt.add(ring);
      }
      group.userData.id = id; mesh.userData.id = id;
      scene.add(group);
      const label = el("button", { class: "ss-label", type: "button", onclick: () => select(id) }, d.name);
      label.style.setProperty("--c", COLORS[id]);
      labels.append(label);
      return { group, tilt, spin, mesh, radiusKm: d.radius_km, data: d, label };
    }

    function buildOrbit(d) {
      const pts = d.orbit.map((p) => (d.orbit_relative_to ? toScene(p) : compress(p, realScale)));
      const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: COLORS[d.id], transparent: true, opacity: d.id === "moon" ? 0.35 : 0.45 }));
      line.userData = { id: d.id, raw: d.orbit, relative: !!d.orbit_relative_to };
      return line;
    }
    function rebuildScale() {
      for (const b of Object.values(bodies)) if (b?.group) { const r = displayRadius(b.radiusKm, realScale); b.group.scale.setScalar(r); }
      for (const line of orbitsGroup.children) if (!line.userData.relative) line.geometry.setFromPoints(line.userData.raw.map((p) => compress(p, realScale)));
      if (bodies.glow) bodies.glow.visible = true;
    }

    // ---------- engine data: a window of positions around the current time ----------
    async function loadWindow(startJd) {
      if (loading) return;
      loading = true;
      const speed = SPEEDS[speedIdx][0] * dir;
      const span = Math.max(1, Math.abs(speed) * 20);
      const from = speed < 0 ? startJd - span : startJd;
      const iso = jdToDate(from).toISOString();
      try {
        const r = await simulate("physics", "solar_system", { date: iso, span_days: span, n_track: Math.min(2000, Math.max(40, Math.ceil(span / 2))), orbit_points: firstLoad ? 360 : 16 });
        const res = r.result;
        if (firstLoad) {
          for (const d of res.bodies) { bodies[d.id] = makeBody(d); if (d.orbit) orbitsGroup.add(buildOrbit(d)); }
          rebuildScale(); buildList(res.bodies); firstLoad = false; status.remove();
        }
        for (const d of res.bodies) Object.assign(bodies[d.id].data, d, { orbit: bodies[d.id].data.orbit || d.orbit });
        window_ = { t: r.track_times_jd, bodies: Object.fromEntries(res.bodies.map((d) => [d.id, d])) };
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
        const rel0 = tr[i].map((v, k) => v - e0[k]), rel1 = tr[i + 1].map((v, k) => v - e1[k]);
        return { rel: interp(rel0, rel1, f - i) };
      }
      return { p: interp(tr[i], tr[i + 1], f - i) };
    }

    // ---------- selection, info panel and list ----------
    let selected = null;
    function buildList(ds) {
      list.replaceChildren(el("div", { class: "ss-list-title" }, "Solar System"), ...ds.map((d) => el("button", { class: "ss-list-item", type: "button", onclick: () => { select(d.id); list.classList.add("hidden"); } },
        el("span", { class: "dot", style: `background:${COLORS[d.id]}` }), d.name, el("small", {}, d.type))));
    }
    function fact(k, v) { return el("div", { class: "ss-fact" }, el("span", {}, k), el("b", {}, v)); }
    function showInfo(id) {
      const d = window_?.bodies[id] || bodies[id].data;
      info.classList.remove("hidden");
      const rows = [
        fact("Type", d.type), fact("Radius", `${fmt(d.radius_km, 5)} km`), fact("Mass", `${fmt(d.mass_kg, 4)} kg`),
        fact("Surface gravity", `${fmt(d.surface_gravity, 3)} m/s²`), fact("Escape velocity", `${fmt(d.escape_velocity_km_s, 3)} km/s`),
        fact("Day (sidereal)", d.rotation_period_hours > 48 ? `${fmt(d.rotation_period_hours / 24, 4)} days` : `${fmt(d.rotation_period_hours, 4)} h`),
        fact("Axial tilt", `${fmt(d.axial_tilt_deg, 3)}°${d.retrograde_rotation ? " (spins backwards)" : ""}`),
        fact("Mean temperature", `${fmt(d.mean_temperature_c, 3)} °C`), fact("Known moons", String(d.moons)),
      ];
      if (d.orbital_period_days) rows.push(fact("Year", d.orbital_period_days > 700 ? `${fmt(d.orbital_period_days / 365.25, 4)} Earth years` : `${fmt(d.orbital_period_days, 4)} days`));
      if (d.id !== "sun") rows.push(fact("Distance from Sun", `${fmt(d.distance_sun_au, 4)} AU`));
      if (d.distance_earth_au !== undefined) rows.push(fact("Distance from Earth", `${fmt(d.distance_earth_au, 4)} AU`), fact("Light takes", `${fmt(d.light_time_min, 3)} min`));
      info.replaceChildren(el("button", { class: "ss-close", type: "button", "aria-label": "Close", onclick: () => select(null) }, "×"),
        el("div", { class: "ss-info-name", style: `--c:${COLORS[id]}` }, d.name), ...rows,
        el("p", { class: "ss-note" }, "Computed by the Reality ASM engine for the displayed date."));
    }
    let fly = null, follow = null, lastFollow = null;
    function select(id) {
      selected = id; follow = null;
      const start = { target: controls.target.clone(), cam: camera.position.clone(), t: 0 };
      if (!id) {
        info.classList.add("hidden");
        fly = { ...start, id: null, homeTarget: new THREE.Vector3(), homeCam: new THREE.Vector3(0, 120, 260).multiplyScalar(realScale ? 5 : 1) };
        return;
      }
      showInfo(id);
      const r = bodies[id].group.scale.x;
      const off = camera.position.clone().sub(controls.target).normalize().multiplyScalar(Math.max(r * 4.5, 0.02));
      fly = { ...start, id, off };
    }

    // Click on a planet
    const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
    let downAt = null;
    renderer.domElement.addEventListener("pointerdown", (e) => { downAt = [e.clientX, e.clientY]; });
    renderer.domElement.addEventListener("pointerup", (e) => {
      if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
      const r = renderer.domElement.getBoundingClientRect();
      mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(mouse, camera);
      const hit = ray.intersectObjects(Object.values(bodies).filter((b) => b?.mesh).map((b) => b.mesh))[0];
      if (hit) select(hit.object.userData.id);
    });

    // ---------- animation ----------
    function resize() {
      const w = view.clientWidth, h = view.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    }
    const ro = new ResizeObserver(resize); ro.observe(view); resize();
    let last = performance.now(), raf = 0;
    const tmp = new THREE.Vector3();
    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (playing) simJd += SPEEDS[speedIdx][0] * dir * dt;
      if (!window_ && !loading) loadWindow(simJd);
      if (window_) {
        const t = window_.t, span = t[t.length - 1] - t[0];
        const frac = (simJd - t[0]) / (span || 1);
        if ((frac > 0.75 || frac < 0) && dir > 0 || (frac < 0.25 || frac > 1) && dir < 0) loadWindow(simJd);
        const sunScene = new THREE.Vector3();
        for (const [id, b] of Object.entries(bodies)) {
          if (!b?.group) continue;
          if (id === "moon") continue;
          const s = sample(id);
          b.group.position.copy(compress(s.p, realScale));
        }
        if (bodies.moon) { // keep the Moon visibly outside Earth in compressed mode
          const s = sample("moon"), e = bodies.earth.group;
          const rel = toScene(s.rel), dist = rel.length();
          const shown = realScale ? dist * 40 : e.scale.x * 5.5 + 0.6;
          bodies.moon.group.position.copy(e.position).add(rel.normalize().multiplyScalar(shown));
          const mo = orbitsGroup.children.find((l) => l.userData.id === "moon");
          if (mo) { mo.position.copy(e.position); mo.scale.setScalar(shown / dist); }
        }
        // Spin: prime-meridian angle from the engine, advanced at the engine's rotation rate
        for (const [id, b] of Object.entries(bodies)) {
          if (!b?.spin) continue;
          const d = window_.bodies[id], w = d.prime_meridian_deg + d.rotation_rate_deg_per_day * (simJd - window_.t[0]);
          b.spin.rotation.y = THREE.MathUtils.degToRad(w);
        }
        if (bodies.clouds) bodies.clouds.rotation.y += dt * 0.004 * Math.sign(SPEEDS[speedIdx][0]);
        const earthMat = bodies.earth?.mesh.material;
        if (earthMat?.uniforms) earthMat.uniforms.sunPos.value.copy(sunScene);
        for (const a of [bodies.earthAtmo, ...(bodies.atmos || [])]) if (a) a.material.uniforms.sunPos.value.copy(sunScene);
        const date = jdToDate(simJd);
        dateBig.textContent = date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });
        timeSmall.textContent = `${date.toISOString().slice(11, 19)} UTC · JD ${simJd.toFixed(3)}`;
      }
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
      controls.update();
      stars.position.copy(camera.position);
      // Labels
      if (showLabels) {
        const w = view.clientWidth, h = view.clientHeight;
        for (const b of Object.values(bodies)) {
          if (!b?.label) continue;
          tmp.copy(b.group.position); tmp.y += b.group.scale.x * 1.2;
          const v = tmp.project(camera), visible = v.z < 1 && Math.abs(v.x) < 1.05 && Math.abs(v.y) < 1.05;
          const tooClose = b.data.id === "moon" && !realScale && camera.position.distanceTo(bodies.earth.group.position) > 60;
          b.label.style.display = visible && !tooClose ? "" : "none";
          if (visible) b.label.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -120%)`;
        }
      }
      renderer.render(scene, camera);
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf); ro.disconnect(); controls.dispose();
      scene.traverse((o) => { o.geometry?.dispose?.(); const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { Object.values(x).forEach((v) => v?.isTexture && v.dispose()); x.dispose(); }); });
      renderer.dispose();
    };
  },
};
