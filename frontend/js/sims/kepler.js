// Kepler's Laws: physics.kepler_orbit solves Kepler's equation; equal-time sectors show equal areas.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, checkbox, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, indexAt, starfield } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Orbital elements (semi-major axis in AU, eccentricity), rounded textbook values.
const BODIES = { earth: ["Earth", 1.0, 0.0167], mercury: ["Mercury", 0.387, 0.2056], mars: ["Mars", 1.524, 0.0934], jupiter: ["Jupiter", 5.203, 0.0489], halley: ["Halley's Comet", 17.8, 0.967], custom: ["Custom", null, null] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, simT = 0;

    const body = select({ label: "Orbit", value: "mercury", options: Object.entries(BODIES).map(([v, [l]]) => ({ value: v, label: l })), onChange: (v) => { if (BODIES[v][1]) { a.set(BODIES[v][1]); e.set(BODIES[v][2]); } recompute(); } });
    const a = slider({ label: "Semi-major axis a", min: 0.2, max: 40, value: 0.387, log: true, unit: "AU", onInput: () => { body.set("custom"); recompute(); } });
    const e = slider({ label: "Eccentricity e", min: 0, max: 0.97, step: 0.001, value: 0.2056, onInput: () => { body.set("custom"); recompute(); } });
    const sectors = checkbox({ label: "Shade equal-time sectors", value: true, onChange: () => draw() });
    const out = readouts([
      { key: "T", label: "Period (T² = a³)" }, { key: "peri", label: "Perihelion / aphelion" }, { key: "v", label: "Speed at perihelion / aphelion" },
      { key: "area", label: "Each sector's area" }, { key: "k3", label: "T² / a³" },
    ]);
    L.side.append(
      panel("Orbit around the Sun", body.root, a.root, e.root, sectors.root, el("p", { class: "note" }, "1st law: ellipse with the Sun at a focus. 2nd: equal areas in equal times, fast when close. 3rd: T² ∝ a³.")),
      panel("Kepler's laws (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); }, { speeds: [0.5, 1, 2, 4], loop: true, timeFormat: (v) => `${fmt(v, 3)} years` });
    const graph = new LineGraph(L.bottom, { title: "Orbital speed over one period", xLabel: "time (years)", yLabel: "km/s", height: 130, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "kepler_orbit", { semi_major_axis_au: a.value, eccentricity: e.value, n_points: 1441, n_sectors: 12 }, signal), {
      delay: 30, onError: (err) => L.error(err.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("T", `${fmt(x.period_years, 4)} years`); out.set("peri", `${fmt(x.perihelion_au, 4)} / ${fmt(x.aphelion_au, 4)} AU`);
        out.set("v", `${fmt(x.perihelion_speed / 1000, 4)} / ${fmt(x.aphelion_speed / 1000, 4)} km/s`);
        out.set("area", `${fmt(x.sector_areas_au2[0], 4)} AU² (all 12 equal)`); out.set("k3", `${fmt(x.t2_over_a3, 5)} yr²/AU³`);
        graph.setSeries([{ name: "speed", color: c2, x: r.orbit.t_years, y: r.orbit.speed_km_s }]);
        player.load(x.period_years, 10);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0b1426"; ctx.fillRect(0, 0, w, h); starfield(ctx, w, h);
      if (!res) return;
      const o = res.orbit, xs = o.x_au, ys = o.y_au;
      const minX = Math.min(...xs), maxX = Math.max(...xs), maxY = Math.max(...ys.map(Math.abs));
      const s = Math.min((w - 80) / (maxX - minX), (h - 80) / (2 * maxY)), ox = w / 2 - ((minX + maxX) / 2) * s, oy = h / 2;
      const P = (i) => [ox + xs[i] * s, oy - ys[i] * s];
      if (sectors.value) {
        const tk = res.sector_times_years;
        for (let j = 0; j < tk.length - 1; j++) {
          const i0 = indexAt(o.t_years, tk[j]), i1 = indexAt(o.t_years, tk[j + 1]);
          ctx.fillStyle = j % 2 ? "rgba(42,120,214,.28)" : "rgba(235,104,52,.28)"; ctx.beginPath(); ctx.moveTo(ox, oy);
          for (let i = i0; i <= i1; i++) ctx.lineTo(...P(i));
          ctx.closePath(); ctx.fill();
        }
      }
      ctx.strokeStyle = "rgba(201,206,214,.6)"; ctx.lineWidth = 1.5; ctx.beginPath(); xs.forEach((_, i) => (i ? ctx.lineTo(...P(i)) : ctx.moveTo(...P(i)))); ctx.stroke();
      ctx.fillStyle = "#ffd479"; ctx.beginPath(); ctx.arc(ox, oy, 9, 0, Math.PI * 2); ctx.fill();
      const k = indexAt(o.t_years, simT % res.result.period_years), [px, py] = P(k);
      ctx.strokeStyle = "rgba(255,212,121,.5)"; ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(px, py); ctx.stroke();
      ctx.fillStyle = c1; ctx.beginPath(); ctx.arc(px, py, 7, 0, Math.PI * 2); ctx.fill();
      label(ctx, `r = ${fmt(o.r_au[k], 3)} AU, v = ${fmt(o.speed_km_s[k], 3)} km/s`, 14, 20, { color: "#c9ced6", font: "bold 12px system-ui" });
      label(ctx, "Sun at a focus", ox, oy + 22, { align: "center", color: "#ffd479", font: "11px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
