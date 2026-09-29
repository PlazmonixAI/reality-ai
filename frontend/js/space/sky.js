// The night sky drawn from engine data: real stars (physics.star_catalog) and the Milky Way band from the engine's
// Galaxy model (physics.milky_way) seen from the Sun. `M` rotates galactic vectors into the stars' frame.
import * as THREE from "three";
import { pointsMaterial, hexToRgb } from "./shaders.js";

export function buildSky(stars, mw, M, toScene, R = 60000) {
  const sky = new THREE.Group();
  const bright = stars.apparent_magnitude.map((m, i) => [m, i]).filter(([m]) => m <= 6.5);
  const pos = new Float32Array(bright.length * 3), col = new Float32Array(bright.length * 3), size = new Float32Array(bright.length);
  bright.forEach(([m, i], k) => {
    const d = stars.distance_ly[i], v = toScene([stars.x_ly[i] / d, stars.y_ly[i] / d, stars.z_ly[i] / d]).multiplyScalar(R);
    pos.set([v.x, v.y, v.z], k * 3);
    const glow = Math.min(1, 0.22 + 0.78 * Math.pow(10, -0.4 * (m - 1.5)));
    col.set(hexToRgb(stars.color[i]).map((c) => c * glow), k * 3);
    size[k] = 1.1 + 6.5 * Math.pow(10, -0.2 * (m + 1.46));
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("color", new THREE.BufferAttribute(col, 3)); g.setAttribute("size", new THREE.BufferAttribute(size, 1));
  const starPts = new THREE.Points(g, pointsMaterial({ minSize: 1.0, maxSize: 10 }));
  const sun = mw.sun_position_kpc, P = mw.points, n = P.x_kpc.length;
  const mpos = new Float32Array(n * 3), mcol = new Float32Array(n * 3), msize = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const gx = P.x_kpc[i] - sun[0], gy = P.y_kpc[i] - sun[1], gz = P.z_kpc[i] - sun[2], d = Math.hypot(gx, gy, gz) || 1;
    const e = [0, 1, 2].map((r) => (M[r][0] * gx + M[r][1] * gy + M[r][2] * gz) / d);
    const v = toScene(e).multiplyScalar(R * 1.02);
    mpos.set([v.x, v.y, v.z], i * 3);
    const w = 0.05 + 0.1 * Math.min(1, 3 / d);
    mcol.set(hexToRgb(P.color[i]).map((c) => c * w), i * 3);
    msize[i] = 6 + 10 * Math.min(1, 2 / d);
  }
  const mg = new THREE.BufferGeometry();
  mg.setAttribute("position", new THREE.BufferAttribute(mpos, 3)); mg.setAttribute("color", new THREE.BufferAttribute(mcol, 3)); mg.setAttribute("size", new THREE.BufferAttribute(msize, 1));
  const band = new THREE.Points(mg, pointsMaterial({ minSize: 4, maxSize: 26, opacity: 0.55 }));
  for (const o of [band, starPts]) { o.frustumCulled = false; o.renderOrder = -1; sky.add(o); }
  return sky;
}
