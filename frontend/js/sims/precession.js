// J2 Precession: physics.j2_precession — Earth's equatorial bulge swings orbit planes; sun-synchronous orbits.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt, starfield } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const RE = 6378.137; // km, display scale

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, simT = 0;

    const alt = slider({ label: "Altitude", min: 200, max: 2000, step: 10, value: 700, unit: "km", onInput: () => recompute() });
    const inc = slider({ label: "Inclination", min: 0, max: 180, step: 0.1, value: 51.6, unit: "°", onInput: () => recompute() });
    const days = slider({ label: "Watch for", min: 1, max: 60, step: 1, value: 30, unit: "days", onInput: () => recompute() });
    const out = readouts([
      { key: "raan", label: "Node drift (J2 theory)" }, { key: "num", label: "Node drift (simulated)" }, { key: "argp", label: "Perigee drift" },
      { key: "ss", label: "Sun-synchronous inclination here" }, { key: "T", label: "Orbital period" },
    ]);
    L.side.append(
      panel("Circular orbit around Earth", alt.root, inc.root, days.root, button("Make it sun-synchronous", () => { if (res?.result.sun_synchronous_inclination_deg) { inc.set(res.result.sun_synchronous_inclination_deg); recompute(); } }),
        el("p", { class: "note" }, "Earth's bulge tugs on tilted orbits, so the orbit plane slowly turns. Tuned just right (≈98°), it turns once a year and keeps the same angle to the Sun.")),
      panel("Precession (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); }, { speeds: [0.5, 1, 2], timeFormat: (v) => `day ${fmt(v, 3)}` });
    const graph = new LineGraph(L.bottom, { title: "Right ascension of the ascending node", xLabel: "days", yLabel: "RAAN (°)", height: 140 });

    const recompute = liveRequest((signal) => simulate("physics", "j2_precession", { perigee_alt: alt.value * 1000, inclination_deg: inc.value, duration_days: days.value, n_points: 400 }, signal), {
      delay: 120, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("raan", `${fmt(x.raan_rate_deg_per_day, 4)} °/day`); out.set("num", `${fmt(x.raan_rate_numerical_deg_per_day, 4)} °/day`);
        out.set("argp", `${fmt(x.perigee_rate_deg_per_day, 4)} °/day (matters for elliptical orbits)`);
        out.set("ss", x.sun_synchronous_inclination_deg ? `${fmt(x.sun_synchronous_inclination_deg, 4)}°` : "none (too high)"); out.set("T", `${fmt(x.period_minutes, 4)} min`);
        graph.setSeries([
          { name: "simulated (osculating)", color: c1, x: r.trace.t_days, y: r.trace.raan_deg },
          { name: "J2 theory", color: c2, dash: true, x: r.trace.t_days, y: r.trace.raan_analytic_deg },
        ]);
        player.load(days.value, 10);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0b1426"; ctx.fillRect(0, 0, w, h); starfield(ctx, w, h);
      if (!res) return;
      const cx = w * 0.5, cy = h * 0.5, R = Math.min(w, h) * 0.2, r = R * (1 + alt.value / RE) * 1.35;
      const az = -0.6, el_ = 0.42;
      const proj = ([x, y, z]) => { const X = x * Math.cos(az) - y * Math.sin(az), Y = x * Math.sin(az) + y * Math.cos(az); return [cx + X, cy - (z * Math.cos(el_) - Y * Math.sin(el_)), Y * Math.cos(el_) + z * Math.sin(el_)]; };
      const raan = (sampleAt(res.trace.t_days, res.trace.raan_deg, simT) * Math.PI) / 180, i = (inc.value * Math.PI) / 180;
      const pt = (u) => [r * (Math.cos(raan) * Math.cos(u) - Math.sin(raan) * Math.sin(u) * Math.cos(i)), r * (Math.sin(raan) * Math.cos(u) + Math.cos(raan) * Math.sin(u) * Math.cos(i)), r * Math.sin(u) * Math.sin(i)];
      // Sun direction turns 360° per year (0.9856°/day) — the reference a sun-synchronous orbit follows
      const sunAng = (simT * 360 / 365.2422) * Math.PI / 180, sun = proj([Math.cos(sunAng) * R * 3, Math.sin(sunAng) * R * 3, 0]);
      const drawOrbit = (front) => {
        ctx.strokeStyle = c1; ctx.lineWidth = front ? 3 : 1.5; ctx.globalAlpha = front ? 1 : 0.4; ctx.beginPath();
        let pen = false;
        for (let k = 0; k <= 200; k++) { const [x, y, d] = proj(pt((k / 200) * 2 * Math.PI)); if ((d >= 0) === front) { if (pen) ctx.lineTo(x, y); else { ctx.moveTo(x, y); pen = true; } } else pen = false; }
        ctx.stroke(); ctx.globalAlpha = 1;
      };
      drawOrbit(false);
      const g = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.3, R * 0.2, cx, cy, R);
      g.addColorStop(0, "#5598e7"); g.addColorStop(1, "#1d4f8f");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.fill();
      // Equator
      ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 1; ctx.beginPath();
      for (let k = 0; k <= 100; k++) { const [x, y] = proj([Math.cos((k / 100) * 2 * Math.PI) * R, Math.sin((k / 100) * 2 * Math.PI) * R, 0]); if (k) ctx.lineTo(x, y); else ctx.moveTo(x, y); }
      ctx.stroke();
      drawOrbit(true);
      // Ascending node marker
      const [nx, ny] = proj(pt(0));
      ctx.fillStyle = c2; ctx.beginPath(); ctx.arc(nx, ny, 6, 0, Math.PI * 2); ctx.fill();
      label(ctx, "ascending node", nx + 10, ny, { color: c2, font: "12px system-ui" });
      ctx.fillStyle = "#ffd479"; ctx.beginPath(); ctx.arc(sun[0], sun[1], 10, 0, Math.PI * 2); ctx.fill();
      label(ctx, "to the Sun", sun[0], sun[1] - 18, { align: "center", color: "#ffd479", font: "12px system-ui" });
      label(ctx, `day ${fmt(simT, 3)}: node at ${fmt(((raan * 180) / Math.PI) % 360, 4)}°`, 14, 20, { color: "#c9ced6", font: "bold 12px system-ui" });
      label(ctx, "orbit size exaggerated", w - 12, h - 12, { align: "right", color: "#7b8796", font: "11px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
