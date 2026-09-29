// Shared three.js materials for the space views. Rendering only: lighting, shading and glow. Every position,
// size, spin and orbit comes from the engine (physics.solar_system, planet_moons, minor_bodies, …).
import * as THREE from "three";

const VERT = `
varying vec2 vUv; varying vec3 vN; varying vec3 vT; varying vec3 vB; varying vec3 vPos;
void main() {
  vUv = uv;
  vec3 n = normalize(normal);
  vec3 t = normalize(vec3(n.z, 0.0, -n.x) + vec3(1e-6, 0.0, 0.0)); // east, along increasing longitude
  vN = normalize(mat3(modelMatrix) * n);
  vT = normalize(mat3(modelMatrix) * t);
  vB = normalize(cross(vN, vT)); // north
  vec4 w = modelMatrix * vec4(position, 1.0);
  vPos = w.xyz;
  gl_Position = projectionMatrix * viewMatrix * w;
}`;

// Planet/moon surface: texture, optional normal map, lunar-Lambert (airless) or Lambert (atmosphere)
// lighting, atmospheric rim, optional ring shadow and night-side lights.
const FRAG = `
uniform sampler2D map; uniform sampler2D normalMap; uniform sampler2D nightMap; uniform sampler2D specMap;
uniform sampler2D ringMap;
uniform vec3 sunPos; uniform vec3 tint; uniform vec3 atmo; uniform float atmoStrength; uniform float airless;
uniform float useNormal; uniform float normalScale; uniform float useNight; uniform float useSpec; uniform float ambient;
uniform float useRing; uniform vec3 center; uniform vec3 ringNormal; uniform float ringInner; uniform float ringOuter;
varying vec2 vUv; varying vec3 vN; varying vec3 vT; varying vec3 vB; varying vec3 vPos;
void main() {
  vec3 n = normalize(vN);
  if (useNormal > 0.5) {
    vec3 m = texture2D(normalMap, vUv).xyz * 2.0 - 1.0;
    m.xy *= normalScale;
    n = normalize(vT * m.x + vB * m.y + n * m.z);
  }
  vec3 l = normalize(sunPos - vPos); vec3 v = normalize(cameraPosition - vPos);
  float mu0 = max(dot(n, l), 0.0), mu = max(dot(n, v), 0.0);
  float geo = max(dot(normalize(vN), l), 0.0);
  float lambert = mu0;
  float lunar = 2.0 * mu0 / (mu0 + mu + 1e-4);                 // Lommel–Seeliger: airless regolith
  float light = mix(lambert, mix(lambert, lunar * 0.9, 0.7), airless) * smoothstep(-0.02, 0.08, geo);
  if (useRing > 0.5) {                                          // shadow of the rings on the planet
    float denom = dot(l, ringNormal);
    if (abs(denom) > 1e-4) {
      float s = dot(center - vPos, ringNormal) / denom;
      if (s > 0.0) {
        float r = length(vPos + l * s - center);
        if (r > ringInner && r < ringOuter) light *= 1.0 - 0.85 * texture2D(ringMap, vec2((r - ringInner) / (ringOuter - ringInner), 0.5)).a;
      }
    }
  }
  vec3 base = texture2D(map, vUv).rgb * tint;
  vec3 col = base * (ambient + 1.05 * light);
  if (useNight > 0.5) {
    float dayMix = smoothstep(-0.12, 0.22, dot(normalize(vN), l));
    col = mix(texture2D(nightMap, vUv).rgb * vec3(1.0, 0.85, 0.6) * 2.4, col, dayMix);
  }
  if (useSpec > 0.5) {
    vec3 h = normalize(l + v);
    col += vec3(1.0, 0.95, 0.85) * pow(max(dot(n, h), 0.0), 60.0) * texture2D(specMap, vUv).r * 0.55 * smoothstep(-0.1, 0.2, geo);
  }
  float rim = pow(1.0 - max(dot(normalize(vN), v), 0.0), 2.5);
  col += atmo * rim * atmoStrength * smoothstep(-0.25, 0.35, dot(normalize(vN), l));
  gl_FragColor = vec4(col, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

const blank = (() => { const t = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1); t.needsUpdate = true; return t; })();
const flatNormal = (() => { const t = new THREE.DataTexture(new Uint8Array([128, 128, 255, 255]), 1, 1); t.needsUpdate = true; return t; })();

export function planetMaterial({ map, normalMap = null, nightMap = null, specMap = null, tint = [1, 1, 1], atmo = [0, 0, 0],
  atmoStrength = 0, airless = 0, normalScale = 1, ambient = 0.035 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      map: { value: map }, normalMap: { value: normalMap || flatNormal }, nightMap: { value: nightMap || blank },
      specMap: { value: specMap || blank }, ringMap: { value: blank },
      sunPos: { value: new THREE.Vector3() }, tint: { value: new THREE.Color(...tint) }, atmo: { value: new THREE.Color(...atmo) },
      atmoStrength: { value: atmoStrength }, airless: { value: airless }, ambient: { value: ambient },
      useNormal: { value: normalMap ? 1 : 0 }, normalScale: { value: normalScale }, useNight: { value: nightMap ? 1 : 0 },
      useSpec: { value: specMap ? 1 : 0 }, useRing: { value: 0 }, center: { value: new THREE.Vector3() },
      ringNormal: { value: new THREE.Vector3(0, 1, 0) }, ringInner: { value: 1 }, ringOuter: { value: 2 },
    },
    vertexShader: VERT, fragmentShader: FRAG,
  });
}

// Atmosphere shell (back faces, additive): brightest at the lit limb.
const ATMO_VERT = `varying vec3 vN; varying vec3 vPos;
void main(){ vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position,1.0); vPos = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const ATMO_FRAG = `uniform vec3 sunPos; uniform vec3 tint; uniform float strength; uniform float power; varying vec3 vN; varying vec3 vPos;
void main(){ vec3 n = normalize(vN); vec3 v = normalize(cameraPosition - vPos); vec3 l = normalize(sunPos - vPos);
  float rim = pow(1.0 - abs(dot(n, v)), power); float lit = smoothstep(-0.35, 0.45, dot(n, l));
  gl_FragColor = vec4(tint * strength, rim * lit); }`;
export function atmosphereMaterial(tint, strength = 1, power = 2.5) {
  return new THREE.ShaderMaterial({
    uniforms: { sunPos: { value: new THREE.Vector3() }, tint: { value: new THREE.Color(...tint) }, strength: { value: strength }, power: { value: power } },
    vertexShader: ATMO_VERT, fragmentShader: ATMO_FRAG, transparent: true, blending: THREE.AdditiveBlending, side: THREE.BackSide, depthWrite: false,
  });
}

// Rings: a radial strip texture (u = inner → outer edge), lit by the Sun and darkened in the planet's shadow.
const RING_VERT = `varying float vR; varying vec3 vPos;
void main(){ vR = length(position.xy); vec4 w = modelMatrix * vec4(position,1.0); vPos = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
const RING_FRAG = `uniform sampler2D ringMap; uniform float inner; uniform float outer; uniform vec3 sunPos; uniform vec3 center;
uniform float planetRadius; uniform vec3 ringNormal; uniform float opacity; varying float vR; varying vec3 vPos;
void main(){
  float u = (vR - inner) / (outer - inner);
  if (u < 0.0 || u > 1.0) discard;
  vec4 c = texture2D(ringMap, vec2(u, 0.5));
  vec3 l = normalize(sunPos - vPos);
  vec3 toC = center - vPos; float t = dot(toC, l);
  float shadow = (t > 0.0 && length(toC - l * t) < planetRadius) ? 0.12 : 1.0;
  vec3 v = normalize(cameraPosition - vPos);
  float sameSide = sign(dot(ringNormal, l)) * sign(dot(ringNormal, v));
  float lit = sameSide > 0.0 ? 1.0 : 0.45;                     // unlit face: only forward-scattered light
  gl_FragColor = vec4(c.rgb * lit * shadow * 1.1, c.a * opacity);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;
export function ringMaterial(map, inner, outer, opacity = 1) {
  return new THREE.ShaderMaterial({
    uniforms: { ringMap: { value: map }, inner: { value: inner }, outer: { value: outer }, sunPos: { value: new THREE.Vector3() },
      center: { value: new THREE.Vector3() }, planetRadius: { value: 1 }, ringNormal: { value: new THREE.Vector3(0, 1, 0) }, opacity: { value: opacity } },
    vertexShader: RING_VERT, fragmentShader: RING_FRAG, transparent: true, side: THREE.DoubleSide, depthWrite: false,
  });
}

// The Sun: granulated photosphere with limb darkening, slowly boiling.
const SUN_FRAG = `uniform sampler2D map; uniform float time; varying vec2 vUv; varying vec3 vN; varying vec3 vT; varying vec3 vB; varying vec3 vPos;
void main(){
  vec3 v = normalize(cameraPosition - vPos); float mu = max(dot(normalize(vN), v), 0.0);
  vec3 a = texture2D(map, vUv + vec2(time * 0.0021, 0.0)).rgb, b = texture2D(map, vUv * 1.7 - vec2(time * 0.0013, time * 0.0007)).rgb;
  vec3 tex = mix(a, b, 0.35);
  float limb = 0.4 + 0.6 * pow(mu, 0.5);                       // limb darkening
  vec3 col = tex * vec3(1.55, 1.25, 0.85) * limb + vec3(1.0, 0.55, 0.15) * pow(1.0 - mu, 3.0) * 0.6;
  gl_FragColor = vec4(col, 1.0);
}`;
export function sunMaterial(map) {
  return new THREE.ShaderMaterial({ uniforms: { map: { value: map }, time: { value: 0 } }, vertexShader: VERT, fragmentShader: SUN_FRAG });
}

export function glowTexture(stops = [[0, "rgba(255,244,214,1)"], [0.12, "rgba(255,214,120,.8)"], [0.35, "rgba(255,150,50,.22)"], [1, "rgba(255,120,20,0)"]]) {
  const c = document.createElement("canvas"); c.width = c.height = 256;
  const g = c.getContext("2d"), grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  for (const [k, col] of stops) grad.addColorStop(k, col);
  g.fillStyle = grad; g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// Point sprites for stars and galaxies: size from brightness, colour per point, soft round core.
const POINTS_VERT = `attribute float size; attribute vec3 color; varying vec3 vColor; varying float vA;
uniform float scale; uniform float minSize; uniform float maxSize; uniform float fixedSize;
void main(){ vColor = color; vec4 mv = modelViewMatrix * vec4(position, 1.0);
  float s = fixedSize > 0.5 ? size * scale : size * scale / max(-mv.z, 1e-6);
  gl_PointSize = clamp(s, minSize, maxSize); vA = clamp(s / minSize, 0.15, 1.0);
  gl_Position = projectionMatrix * mv; }`;
const POINTS_FRAG = `uniform float opacity; varying vec3 vColor; varying float vA;
void main(){ vec2 d = gl_PointCoord - 0.5; float r = length(d) * 2.0; if (r > 1.0) discard;
  float core = exp(-r * r * 9.0) + 0.25 * exp(-r * r * 2.5);
  gl_FragColor = vec4(vColor * core, core * vA * opacity); }`;
export function pointsMaterial({ scale = 1, minSize = 1.2, maxSize = 24, fixedSize = true, opacity = 1, additive = true } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: { scale: { value: scale }, minSize: { value: minSize }, maxSize: { value: maxSize }, fixedSize: { value: fixedSize ? 1 : 0 }, opacity: { value: opacity } },
    vertexShader: POINTS_VERT, fragmentShader: POINTS_FRAG, transparent: true, depthWrite: false,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
}

export function hexToRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; }

// Comet tails: an additive cone pointing away from the Sun (dust = warm, ion = blue).
const TAIL_VERT = `varying float vT; varying vec3 vN; void main(){ vT = uv.y; vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const TAIL_FRAG = `uniform vec3 color; uniform float strength; varying float vT; varying vec3 vN;
void main(){ float edge = pow(abs(normalize(vN).z), 2.0);  // soft, gas-like edges
  float a = pow(vT, 2.2) * edge * strength; gl_FragColor = vec4(color * a, a); }`;
export function tailMaterial(color, strength = 1) {
  return new THREE.ShaderMaterial({ uniforms: { color: { value: new THREE.Color(...color) }, strength: { value: strength } },
    vertexShader: TAIL_VERT, fragmentShader: TAIL_FRAG, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
}
