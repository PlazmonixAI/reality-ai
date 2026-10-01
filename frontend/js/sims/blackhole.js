// Black Hole & Singularity: physics.black_hole (radii, clocks, curvature, fall to r = 0), physics.black_hole_light
// (null geodesics) and physics.black_hole_orbit (timelike geodesics). The browser only draws and animates the paths.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, starfield } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt, fmtTime } from "../core/format.js";

const EMBER = "#FF5B2E";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => {} });
    const [c1, c2, c3] = SERIES();
    let bh = null, light = null, orbit = null, raf = 0, alive = true;

    const mass = slider({ label: "Mass", min: 1, max: 1e10, log: true, value: 10, unit: "M☉", digits: 3, onInput: () => { runBH(); runLight(); } });
    const fall = slider({ label: "Start of the fall (r / r_s)", min: 1, max: 20, step: 0.1, value: 3, onInput: () => runBH() });
    const bmax = slider({ label: "Widest light ray (impact parameter, r_s)", min: 3, max: 12, step: 0.1, value: 7, onInput: () => runLight() });
    const nrays = slider({ label: "Number of rays", min: 4, max: 30, step: 1, value: 17, digits: 2, onInput: () => runLight() });
    const r0 = slider({ label: "Probe start (r / r_s)", min: 2, max: 30, step: 0.1, value: 9, onInput: () => runOrbit() });
    const sp = slider({ label: "Probe speed (× circular)", min: 0, max: 1.3, step: 0.01, value: 0.9, onInput: () => runOrbit() });
    const out = readouts([
      { key: "rs", label: "Event horizon radius" }, { key: "ps", label: "Photon sphere" }, { key: "isco", label: "Last stable orbit" },
      { key: "tau", label: "Proper time to the singularity" }, { key: "curv", label: "Curvature at the horizon" },
      { key: "tidal", label: "Tidal stretch at horizon (2 m)" }, { key: "temp", label: "Hawking temperature" }, { key: "life", label: "Evaporation time" },
      { key: "orbit", label: "Probe" },
    ]);
    L.side.append(
      panel("Black hole", mass.root, fall.root, el("p", { class: "note" }, "A non-rotating black hole. Inside the horizon every path ends at r = 0, the singularity, where the curvature of spacetime becomes infinite.")),
      panel("Light", bmax.root, nrays.root),
      panel("Orbiting probe", r0.root, sp.root),
      panel("Result (from the engine)", out.root));
    const g1 = new LineGraph(L.bottom, { title: "Outside the horizon", xLabel: "r / r_s", height: 130, includeZero: true });
    const g2 = new LineGraph(L.bottom, { title: "Curvature, log₁₀ of the Kretschmann scalar (1/m⁴): infinite at r = 0", xLabel: "r / r_s", height: 130 });

    const runBH = liveRequest((s) => simulate("physics", "black_hole", { mass_solar: mass.value, fall_from_rs: fall.value }, s), {
      onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); bh = r.result;
        const km = (m) => (m >= 1e4 ? `${fmt(m / 1000, 4)} km` : `${fmt(m, 4)} m`);
        out.set("rs", km(bh.schwarzschild_radius_m)); out.set("ps", km(bh.photon_sphere_m)); out.set("isco", km(bh.isco_m));
        out.set("tau", fmtTime(bh.proper_time_to_singularity_s)); out.set("curv", `${fmt(bh.curvature_at_horizon_m_minus4, 3)} m⁻⁴`);
        out.set("tidal", `${fmt(bh.tidal_at_horizon_m_s2, 3)} m/s²`); out.set("temp", `${fmt(bh.hawking_temperature_K, 3)} K`);
        out.set("life", `${fmt(bh.evaporation_time_years, 3)} years`);
        const p = bh.profiles;
        g1.setSeries([{ name: "clock rate dτ/dt", color: c1, x: p.r_over_rs, y: p.clock_rate }, { name: "escape speed / c", color: c2, x: p.r_over_rs, y: p.escape_speed_over_c }]);
        g2.setSeries([{ name: "log₁₀ K", color: c3, x: bh.curvature_profile.r_over_rs, y: bh.curvature_profile.log10_kretschmann }]);
        g2.setCursor(1);
      },
    });
    const runLight = liveRequest((s) => simulate("physics", "black_hole_light", { b_min: 0.4, b_max: bmax.value, rays: Math.round(nrays.value), mass_solar: mass.value }, s), {
      onError: (e) => L.error(e.message), onResult: (r) => { light = r.result; },
    });
    const runOrbit = liveRequest((s) => simulate("physics", "black_hole_orbit", { r0: r0.value, speed_factor: sp.value, orbits: 3 }, s), {
      onError: (e) => L.error(e.message),
      onResult: (r) => {
        orbit = r.result;
        out.set("orbit", orbit.plunges ? `plunges (closest ${fmt(orbit.periapsis, 3)} r_s)` : orbit.precession_deg_per_orbit != null ? `orbits, periapsis turns ${fmt(orbit.precession_deg_per_orbit, 3)}° each lap` : "orbits");
      },
    });

    function draw(now) {
      if (!alive) return;
      raf = requestAnimationFrame(draw);
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const t = now / 1000;
      ctx.fillStyle = "#04060b"; ctx.fillRect(0, 0, w, h);
      starfield(ctx, w, h, 5);
      const reach = Math.max(6, bmax.value, r0.value) * 1.05;
      const s = Math.min(w, h) / 2 / reach, cx = w / 2, cy = h / 2;
      const X = (x) => cx + x * s, Y = (y) => cy - y * s;
      // light rays (engine paths); a photon pulse runs along each
      if (light) light.rays.forEach((ray, k) => {
        const n = ray.x.length;
        ctx.strokeStyle = ray.captured ? "rgba(255,91,46,.55)" : "rgba(120,170,255,.55)"; ctx.lineWidth = 1.4; ctx.beginPath();
        for (let i = 0; i < n; i++) { const px = X(ray.x[i]), py = Y(ray.y[i]); if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py); }
        ctx.stroke();
        const i = Math.floor(((t * 0.35 + k * 0.03) % 1) * (n - 1));
        ctx.fillStyle = ray.captured ? EMBER : "#cfe0ff"; ctx.beginPath(); ctx.arc(X(ray.x[i]), Y(ray.y[i]), 2.6, 0, Math.PI * 2); ctx.fill();
      });
      // ISCO and photon sphere
      ctx.setLineDash([5, 6]); ctx.lineWidth = 1;
      ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.beginPath(); ctx.arc(cx, cy, 3 * s, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = "rgba(255,200,120,.6)"; ctx.beginPath(); ctx.arc(cx, cy, 1.5 * s, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      // the horizon with a faint glow, and the singularity at the centre
      const glow = ctx.createRadialGradient(cx, cy, s * 0.9, cx, cy, s * 1.9);
      glow.addColorStop(0, "rgba(255,120,60,.35)"); glow.addColorStop(1, "rgba(255,120,60,0)");
      ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(cx, cy, s * 1.9, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#000"; ctx.beginPath(); ctx.arc(cx, cy, s, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "rgba(255,91,46,.9)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, s, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(cx, cy, 1.6, 0, Math.PI * 2); ctx.fill();
      label(ctx, "event horizon", cx, cy + s + 12, { align: "center", color: EMBER, font: "11px system-ui" });
      label(ctx, "photon sphere", cx + 1.06 * s * 1.5, cy - 1.06 * s * 1.5, { color: "rgba(255,200,120,.9)", font: "11px system-ui" });
      label(ctx, "last stable orbit", cx + 2.2 * s, cy - 2.2 * s, { color: "rgba(255,255,255,.6)", font: "11px system-ui" });
      label(ctx, "r = 0", cx + 6, cy - 6, { color: "#fff", font: "10px system-ui" });
      // the probe's orbit (engine path) and the probe moving along it
      if (orbit) {
        const n = orbit.x.length;
        ctx.strokeStyle = "rgba(27,175,122,.7)"; ctx.lineWidth = 1.6; ctx.beginPath();
        for (let i = 0; i < n; i++) { const px = X(orbit.x[i]), py = Y(orbit.y[i]); if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py); }
        ctx.stroke();
        const i = Math.min(n - 1, Math.floor(((t * 0.08) % 1.1) * n));
        ctx.fillStyle = "#1baf7a"; ctx.beginPath(); ctx.arc(X(orbit.x[i]), Y(orbit.y[i]), 5, 0, Math.PI * 2); ctx.fill();
      }
      if (bh) label(ctx, `M = ${fmt(mass.value, 3)} M☉   r_s = ${bh.schwarzschild_radius_m >= 1e4 ? fmt(bh.schwarzschild_radius_m / 1000, 4) + " km" : fmt(bh.schwarzschild_radius_m, 4) + " m"}`, 14, 18, { color: "#e8ecf3", font: "600 13px system-ui" });
      label(ctx, "blue: light that escapes   ember: light that falls in   green: probe", 14, h - 14, { color: "rgba(232,236,243,.75)", font: "12px system-ui" });
    }

    runBH(); runLight(); runOrbit();
    raf = requestAnimationFrame(draw);
    return () => { alive = false; cancelAnimationFrame(raf); runBH.cancel(); runLight.cancel(); runOrbit.cancel(); g1.destroy(); g2.destroy(); stage.destroy(); };
  },
};
