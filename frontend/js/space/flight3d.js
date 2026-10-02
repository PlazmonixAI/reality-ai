// Spaceflight Lab's 3D view: the flight drawn in the Solar System's Earth–Moon system on the real date. Everything
// placed here comes from the engine: physics.rocket_flight's `view3d` (craft, pointing, Moon, trajectory, Earth's
// rotation angle and the Sun's direction, equatorial J2000) plus star_catalog and milky_way for the sky.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { simulate } from "../core/api.js";
import { el } from "../core/ui.js";
import { fmt } from "../core/format.js";
import { planetMaterial, atmosphereMaterial, glowTexture } from "./shaders.js";
import { buildSky } from "./sky.js";

const TEX = "assets/textures/";
const KM = 1e-6;                 // scene unit = 1,000 km
const EARTH_R = 6371, MOON_R = 1737.4, MOON_D = 384400, MOON_SOI = 66194; // km
const toScene = (p) => new THREE.Vector3(p[0], p[2], -p[1]); // equatorial (x, y, z) → three.js (x, z, −y)
const m2s = (p) => toScene(p).multiplyScalar(KM);

export function createFlight3D(host, { onSolarSystem, rocketHeight = 50 } = {}) {
  const loader = new THREE.TextureLoader(), texs = [];
  const tex = (name, srgb = true) => { const t = loader.load(TEX + name); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; texs.push(t); return t; };
  const wrap = el("div", { class: "sf3d" });
  const labels = el("div", { class: "sf3d-labels" });
  const focusBtns = ["rocket", "earth", "moon"].map((f) => el("button", { class: "sf-btn wide", type: "button", onclick: () => setFocus(f) }, { rocket: "ROCKET", earth: "EARTH", moon: "MOON" }[f]));
  const dateBox = el("div", { class: "sf3d-date" });
  wrap.append(labels, el("div", { class: "sf3d-bar" }, ...focusBtns,
    el("button", { class: "sf-btn wide accent", type: "button", onclick: () => onSolarSystem?.(jd) }, "SOLAR SYSTEM")), dateBox,
    el("div", { class: "sf3d-note" }, "True-scale Earth and Moon on the mission date · drag to orbit, scroll to zoom"));
  host.append(wrap);

  const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  wrap.prepend(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 1e-6, 2e6);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 2e-5; controls.maxDistance = 3000;
  scene.add(new THREE.AmbientLight(0x404050, 0.25));
  const sunLight = new THREE.DirectionalLight(0xffffff, 3.0);
  scene.add(sunLight);
  const skyHolder = new THREE.Group();
  scene.add(skyHolder);

  // Earth: the same day/night, ocean glint, clouds and atmosphere as the Solar System view
  const earth = new THREE.Group(), earthSpin = new THREE.Group();
  earth.add(earthSpin);
  const earthMat = planetMaterial({ map: tex("earth_day.jpg"), nightMap: tex("earth_night.jpg"), specMap: tex("earth_water.png", false), atmo: [0.3, 0.55, 1.0], atmoStrength: 0.35, ambient: 0.02 });
  earthSpin.add(new THREE.Mesh(new THREE.SphereGeometry(EARTH_R * KM * 1000, 160, 120), earthMat));
  const clouds = new THREE.Mesh(new THREE.SphereGeometry(EARTH_R * 1.004 * KM * 1000, 160, 120), new THREE.MeshStandardMaterial({ color: 0xffffff, alphaMap: tex("earth_clouds.jpg", false), transparent: true, opacity: 0.9, depthWrite: false, roughness: 1 }));
  earthSpin.add(clouds);
  const earthAtmo = new THREE.Mesh(new THREE.SphereGeometry(EARTH_R * 1.025 * KM * 1000, 96, 64), atmosphereMaterial([0.35, 0.6, 1.0], 1.0, 3.5));
  earth.add(earthAtmo);
  scene.add(earth);
  // Moon: tidally locked, textured and normal-mapped
  const moon = new THREE.Group();
  const moonMat = planetMaterial({ map: tex("moon.jpg"), normalMap: tex("moon_normal.jpg", false), airless: 1 });
  const moonMesh = new THREE.Mesh(new THREE.SphereGeometry(MOON_R * KM * 1000, 128, 96), moonMat);
  moon.add(moonMesh);
  const soi = new THREE.Mesh(new THREE.SphereGeometry(MOON_SOI * KM * 1000, 48, 24), new THREE.MeshBasicMaterial({ color: 0xaab4c8, wireframe: true, transparent: true, opacity: 0.05, depthWrite: false }));
  moon.add(soi);
  scene.add(moon);
  const ghost = new THREE.Mesh(new THREE.SphereGeometry(MOON_R * KM * 1000, 48, 32), new THREE.MeshBasicMaterial({ color: 0xcfd6e0, transparent: true, opacity: 0.25, depthWrite: false }));
  ghost.visible = false; scene.add(ghost);
  const moonOrbit = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([...Array(360)].map((_, i) => new THREE.Vector3(Math.cos(i * Math.PI / 180) * MOON_D / 1000, 0, Math.sin(i * Math.PI / 180) * MOON_D / 1000))),
    new THREE.LineBasicMaterial({ color: 0x8894a8, transparent: true, opacity: 0.25 }));
  scene.add(moonOrbit);
  // The Sun, far away in the engine's Sun direction
  const sunGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
  scene.add(sunGlow);
  // The rocket: a true-scale body plus a marker that stays visible from afar, an engine glow, trail and prediction
  const rocket = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1, 16), new THREE.MeshStandardMaterial({ color: 0xf2f4f7, roughness: 0.5, metalness: 0.2 }));
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.18, 16), new THREE.MeshStandardMaterial({ color: 0xf2f4f7, roughness: 0.5 }));
  nose.position.y = 0.59; rocket.add(body, nose);
  rocket.scale.setScalar(rocketHeight * KM);
  const marker = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture([[0, "rgba(255,255,255,1)"], [0.25, "rgba(120,200,255,.9)"], [1, "rgba(80,160,255,0)"]]), sizeAttenuation: false, depthTest: false, transparent: true }));
  marker.scale.set(0.035, 0.035, 1); marker.renderOrder = 10;
  const flame = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture([[0, "rgba(255,250,220,1)"], [0.3, "rgba(255,170,60,.8)"], [1, "rgba(255,90,20,0)"]]), sizeAttenuation: false, depthTest: false, blending: THREE.AdditiveBlending, transparent: true }));
  flame.scale.set(0.05, 0.05, 1); flame.renderOrder = 11;
  scene.add(rocket, marker, flame);
  const TRAIL_MAX = 20000;
  const trailGeo = new THREE.BufferGeometry(); trailGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(TRAIL_MAX * 3), 3)); trailGeo.setDrawRange(0, 0);
  const trail = new THREE.Line(trailGeo, new THREE.LineBasicMaterial({ color: 0xff9a4a, transparent: true, opacity: 0.9 }));
  trail.frustumCulled = false;
  const predict = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x4f9dff, transparent: true, opacity: 0.85 }));
  predict.frustumCulled = false;
  scene.add(trail, predict);
  let trailN = 0, lastTrail = null;

  // Labels
  const label = (text, color) => { const e = el("div", { class: "ss-label sf3d-label" }, text); e.style.setProperty("--c", color); labels.append(e); return e; };
  const lEarth = label("Earth", "#4f8fe0"), lMoon = label("Moon", "#b9b9b9"), lRocket = label("Your rocket", "#ffb640"), lGhost = label("", "#cfd6e0");

  // Sky from the engine's star catalogue (equatorial frame) and Galaxy model
  Promise.all([simulate("physics", "star_catalog", { max_magnitude: 6.5, frame: "equatorial" }), simulate("physics", "milky_way", { n_points: 30000 })])
    .then(([s, m]) => skyHolder.add(buildSky(s.result, m.result, m.result.galactic_to_equatorial, toScene))).catch(() => {});

  let cur = null, prev = null, jd = null, focus = "rocket", lastFocusPos = null, placed = false, thrusting = false;
  const craftPos = new THREE.Vector3(), tmp = new THREE.Vector3(), mtx = new THREE.Matrix4();
  function setFocus(f) { focus = f; focusBtns.forEach((b, i) => b.classList.toggle("on", ["rocket", "earth", "moon"][i] === f)); lastFocusPos = null; placed = false; }
  setFocus("rocket");

  function update(r) {
    const v = r.view3d;
    if (!v) return;
    prev = cur; cur = v; jd = v.julian_date; thrusting = r.result.telemetry.thrust > 0;
    predict.geometry.setFromPoints(v.trajectory.map(m2s));
    const p = m2s(v.craft);
    if (!lastTrail || lastTrail.distanceTo(p) > 0.002) { // record the flown path
      if (trailN >= TRAIL_MAX) { trailGeo.attributes.position.array.copyWithin(0, 3); trailN--; }
      trailGeo.attributes.position.setXYZ(trailN++, p.x, p.y, p.z); trailGeo.attributes.position.needsUpdate = true; trailGeo.setDrawRange(0, trailN);
      lastTrail = p;
    }
    const e = v.encounter;
    ghost.visible = !!e && !!v.moon;
    if (ghost.visible) { ghost.position.copy(m2s(e.moon)); lGhost.textContent = e.impact ? "Moon at impact" : `Moon at closest pass · ${fmt(e.periselene_alt / 1000, 4)} km`; }
    const date = new Date((jd - 2440587.5) * 86400000);
    dateBox.textContent = `${date.toUTCString().slice(5, 22)} UTC`;
  }

  // Push a point back out to `radius + margin` (scene units) if it went inside a body centred at `centre`
  function keepOutside(pos, centre, radius, margin) {
    const d = pos.distanceTo(centre), min = radius + margin;
    if (d < min) { if (d < 1e-9) pos.set(centre.x, centre.y + min, centre.z); else pos.sub(centre).multiplyScalar(min / d).add(centre); }
  }
  function lerpVec(a, b, f) { return a && b ? [0, 1, 2].map((k) => a[k] + (b[k] - a[k]) * f) : (b || a); }
  function render(f) {
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !cur) return;
    if (renderer.domElement.width !== Math.floor(w * renderer.getPixelRatio())) { renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); }
    const v = cur, pv = prev || cur;
    craftPos.copy(m2s(lerpVec(pv.craft, v.craft, f)));
    const moonP = v.moon ? m2s(lerpVec(pv.moon, v.moon, f)) : null;
    // Earth turns at the engine's rotation angle; the Sun lights everything from the engine's direction
    earthSpin.rotation.y = THREE.MathUtils.degToRad(pv.earth_rotation_deg + (((v.earth_rotation_deg - pv.earth_rotation_deg + 540) % 360) - 180) * f);
    clouds.rotation.y += 0.00002;
    const sunDir = toScene(v.sun_direction).normalize(), sunPos = sunDir.clone().multiplyScalar(1e5);
    sunLight.position.copy(sunDir.clone().multiplyScalar(1000)); sunGlow.position.copy(sunDir.clone().multiplyScalar(2e4)); sunGlow.scale.setScalar(1400);
    for (const m of [earthMat, moonMat, earthAtmo.material]) m.uniforms.sunPos.value.copy(sunPos);
    moon.visible = !!moonP; moonOrbit.visible = !!moonP;
    if (moonP) { // near side (+X of the texture) faces the Earth
      moon.position.copy(moonP);
      const x = moonP.clone().negate().normalize(), y = new THREE.Vector3(0, 1, 0), z = new THREE.Vector3().crossVectors(x, y).normalize(); y.crossVectors(z, x);
      moonMesh.quaternion.setFromRotationMatrix(mtx.makeBasis(x, y, z));
      soi.visible = craftPos.distanceTo(moonP) < MOON_SOI / 1000 * 3;
    }
    // Rocket: pointing from the engine, stood on its tail
    rocket.position.copy(craftPos); marker.position.copy(craftPos);
    const dirV = toScene(v.pointing).normalize();
    rocket.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dirV);
    flame.visible = thrusting; flame.position.copy(craftPos).addScaledVector(dirV, -rocketHeight * KM * 0.6);
    // Camera follows the focus body
    const target = focus === "rocket" ? craftPos : focus === "moon" && moonP ? moonP : new THREE.Vector3();
    if (!placed) {
      const up = craftPos.clone().normalize();
      let side = sunDir.clone().addScaledVector(up, -sunDir.dot(up)); // step toward the sunlit side for the first view
      if (side.lengthSq() < 1e-6) side = new THREE.Vector3().crossVectors(up, new THREE.Vector3(0, 1, 0));
      side.normalize();
      const dist = focus === "rocket" ? Math.max(0.6, craftPos.length() - EARTH_R / 1000) * 4 : focus === "moon" ? 8 : 26;
      camera.position.copy(target).addScaledVector(up, focus === "rocket" ? dist * 0.35 : 0).addScaledVector(side, dist).add(new THREE.Vector3(0, dist * 0.35, 0));
      if (focus !== "rocket") camera.position.copy(target).add(new THREE.Vector3(dist * 0.6, dist * 0.45, dist * 0.8));
      controls.target.copy(target); placed = true; lastFocusPos = target.clone();
    } else if (lastFocusPos) {
      const d = target.clone().sub(lastFocusPos); camera.position.add(d); controls.target.add(d); lastFocusPos.copy(target);
    }
    controls.update();
    keepOutside(camera.position, new THREE.Vector3(), EARTH_R / 1000, 3e-6); // planets are solid: the camera stops at the surface
    if (moonP) keepOutside(camera.position, moonP, MOON_R / 1000, 3e-6);
    skyHolder.position.copy(camera.position);
    renderer.render(scene, camera);
    // Labels
    const place = (e, pos, show = true) => {
      tmp.copy(pos).project(camera);
      const ok = show && tmp.z < 1 && Math.abs(tmp.x) < 1.05 && Math.abs(tmp.y) < 1.05;
      e.style.display = ok ? "" : "none";
      if (ok) e.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h}px) translate(-50%, -150%)`;
    };
    place(lEarth, tmp.set(0, EARTH_R / 1000 * 1.1, 0).clone(), camera.position.length() > EARTH_R / 1000 * 3);
    if (moonP) place(lMoon, moonP.clone().add(new THREE.Vector3(0, MOON_R / 1000 * 1.3, 0))); else lMoon.style.display = "none";
    place(lRocket, craftPos);
    place(lGhost, ghost.position, ghost.visible);
  }

  return {
    update, render,
    show(on) { wrap.style.display = on ? "" : "none"; if (on) placed = false; },
    dispose() { controls.dispose(); scene.traverse((o) => { o.geometry?.dispose?.(); const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach((x) => { x.map?.dispose?.(); x.dispose(); }); }); texs.forEach((t) => t.dispose()); renderer.dispose(); wrap.remove(); },
  };
}
