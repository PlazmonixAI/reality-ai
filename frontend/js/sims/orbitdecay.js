// Orbital Decay: physics.orbital_decay — thin upper-atmosphere drag slowly pulls low satellites down.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt, starfield } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Rough ballistic coefficients m/(Cd·A) in kg/m² for familiar spacecraft (illustrative).
const CRAFT = { cubesat: ["CubeSat (1U)", 20], starlink: ["Small satellite", 60], iss: ["Space station", 140], dense: ["Dense probe", 400] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1] = SERIES();
    let res = null, simT = 0, spin = 0;

    const craft = select({ label: "Spacecraft", value: "iss", options: Object.entries(CRAFT).map(([v, [l, b]]) => ({ value: v, label: `${l} — B ≈ ${b} kg/m²` })), onChange: (v) => { bc.set(CRAFT[v][1]); recompute(); } });
    const bc = slider({ label: "Ballistic coefficient B = m/(C_d·A)", min: 5, max: 1000, value: 140, log: true, unit: "kg/m²", onInput: () => recompute() });
    const alt = slider({ label: "Starting altitude", min: 150, max: 900, step: 5, value: 400, unit: "km", onInput: () => recompute() });
    const years = slider({ label: "Simulate up to", min: 0.1, max: 30, value: 5, log: true, unit: "years", onInput: () => recompute() });
    const out = readouts([{ key: "life", label: "Time to re-entry" }, { key: "rate", label: "Decay rate at the start" }, { key: "rho", label: "Air density at start" }, { key: "orb", label: "Orbits per day" }]);
    L.side.append(
      panel("Low Earth orbit", craft.root, bc.root, alt.root, years.root, el("p", { class: "note" }, "Up here the air is a trillion times thinner than at sea level, but at 7.7 km/s it still drags. Light, wide spacecraft fall fastest.")),
      panel("Decay (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); }, { speeds: [0.5, 1, 2], timeFormat: (v) => `day ${fmt(v, 4)}` });
    const graph = new LineGraph(L.bottom, { title: "Altitude over time", xLabel: "days", yLabel: "altitude (km)", height: 140, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "orbital_decay", { altitude: alt.value * 1000, ballistic_coefficient: bc.value, max_days: years.value * 365.25, n_points: 400 }, signal), {
      delay: 60, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("life", x.reentered ? (x.lifetime_days > 730 ? `${fmt(x.lifetime_days / 365.25, 3)} years` : `${fmt(x.lifetime_days, 3)} days`) : `longer than ${fmt(years.value, 3)} years`);
        out.set("rate", `${fmt(x.initial_decay_rate_m_per_day, 3)} m/day`); out.set("rho", `${fmt(x.density_at_start, 3)} kg/m³`); out.set("orb", fmt(x.orbits_per_day, 3));
        graph.setSeries([{ name: "altitude", color: c1, x: r.curve.t_days, y: r.curve.altitude_km }]);
        const T = r.curve.t_days[r.curve.t_days.length - 1];
        player.load(T, 10);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0b1426"; ctx.fillRect(0, 0, w, h); starfield(ctx, w, h);
      if (!res) return;
      // Side view of a slice of Earth; altitude exaggerated ×40 so the decay is visible
      const cx = w / 2, R = w * 1.6, cy = h * 0.95 + R, ex = 40, kmPx = (R / 6371) * ex / 40 * 0.9;
      const a = sampleAt(res.curve.t_days, res.curve.altitude_km, simT);
      ctx.fillStyle = "rgba(85,152,231,.12)"; ctx.beginPath(); ctx.arc(cx, cy, R + 120 * kmPx * 1.3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#1d4f8f"; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.fill();
      for (const km of [100, 200, 400, 600, 800]) {
        ctx.strokeStyle = km === 100 ? "rgba(227,73,72,.6)" : "rgba(201,206,214,.18)"; ctx.setLineDash([4, 6]);
        ctx.beginPath(); ctx.arc(cx, cy, R + km * kmPx * 1.3, -Math.PI / 2 - 0.35, -Math.PI / 2 + 0.35); ctx.stroke(); ctx.setLineDash([]);
        label(ctx, `${km} km`, cx + 0.33 * (R + km * kmPx * 1.3), cy - (R + km * kmPx * 1.3) * Math.cos(0.34) + 4, { color: km === 100 ? "#e34948" : "#7b8796", font: "11px system-ui" });
      }
      spin += 0.01;
      const ang = -Math.PI / 2 + Math.sin(spin) * 0.25, rr = R + a * kmPx * 1.3;
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(cx + rr * Math.cos(ang), cy + rr * Math.sin(ang), 6, 0, Math.PI * 2); ctx.fill();
      label(ctx, `${fmt(a, 4)} km`, cx + rr * Math.cos(ang) + 10, cy + rr * Math.sin(ang) - 10, { color: "#fff", font: "bold 13px system-ui" });
      label(ctx, "altitudes exaggerated; re-entry at 100 km (red)", w - 12, 18, { align: "right", color: "#7b8796", font: "11px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
