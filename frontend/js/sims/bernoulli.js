// Fluid Flow: physics.pipe_flow applies continuity and Bernoulli's equation along a pipe.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1, c2] = SERIES();
    let res = null;
    const dots = Array.from({ length: 90 }, (_, i) => ({ s: (i * 0.618) % 1 * 4, lane: ((i * 0.377) % 1) - 0.5 }));

    const d = [0, 1, 2, 3, 4].map((i) => slider({ label: `Diameter at ${"ABCDE"[i]}`, min: 2, max: 20, step: 0.5, value: [12, 12, 5, 12, 12][i], unit: "cm", onInput: () => recompute() }));
    const hEnd = slider({ label: "Outlet height (rises from C to E)", min: -5, max: 10, step: 0.5, value: 0, unit: "m", onInput: () => recompute() });
    const q = slider({ label: "Flow rate", min: 0.5, max: 30, step: 0.5, value: 10, unit: "L/s", onInput: () => recompute() });
    const p0 = slider({ label: "Inlet pressure", min: 100, max: 400, step: 5, value: 200, unit: "kPa", onInput: () => recompute() });
    const out = readouts([{ key: "v", label: "Speeds A…E" }, { key: "p", label: "Pressures A…E" }, { key: "c", label: "Cavitation?" }]);
    L.side.append(
      panel("Pipe (water)", ...d.map((s) => s.root), hEnd.root, q.root, p0.root),
      panel("Flow (from the engine)", out.root, el("p", { class: "note" }, "Where the pipe narrows the water speeds up and its pressure drops (Venturi). Lifting the water costs ρgh of pressure.")),
    );
    const pg = new LineGraph(L.bottom, { title: "Pressure along the pipe", xLabel: "section (A → E)", yLabel: "kPa", height: 120 });
    const vg = new LineGraph(L.bottom, { title: "Speed along the pipe", xLabel: "section (A → E)", yLabel: "m/s", height: 110, includeZero: true });

    const heights = () => [0, 0, 0, hEnd.value / 2, hEnd.value];
    const recompute = liveRequest((signal) => simulate("physics", "pipe_flow", {
      diameters: d.map((s) => s.value / 100), heights: heights(), flow_rate: q.value / 1000, inlet_pressure: p0.value * 1000, n_points: 400,
    }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("v", x.section_speeds.map((v) => fmt(v, 3)).join(", ") + " m/s");
        out.set("p", x.section_pressures.map((p) => fmt(p / 1000, 3)).join(", ") + " kPa");
        out.set("c", x.cavitation_risk ? "yes: pressure falls below water's vapour pressure" : "no");
        pg.setSeries([{ name: "pressure", color: c1, x: r.profile.position, y: r.profile.pressure.map((p) => p / 1000) }]);
        vg.setSeries([{ name: "speed", color: c2, x: r.profile.position, y: r.profile.speed }]);
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const pr = res.profile, x0 = 50, x1 = w - 50, X = (s) => x0 + (s / 4) * (x1 - x0);
      const hmax = Math.max(10, Math.abs(hEnd.value)), baseY = h * 0.62, hs = (h * 0.28) / hmax, ds = Math.min(3.2, (h * 0.12) / 0.2) * 100;
      const cy = (s) => baseY - sampleAt(pr.position, pr.height, s) * hs, rad = (s) => (sampleAt(pr.position, pr.diameter, s) * ds) / 2;
      // Pipe walls
      ctx.fillStyle = "rgba(42,120,214,.18)"; ctx.beginPath();
      pr.position.forEach((s, i) => (i ? ctx.lineTo(X(s), cy(s) - rad(s)) : ctx.moveTo(X(s), cy(s) - rad(s))));
      [...pr.position].reverse().forEach((s) => ctx.lineTo(X(s), cy(s) + rad(s))); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3;
      for (const sg of [-1, 1]) { ctx.beginPath(); pr.position.forEach((s, i) => (i ? ctx.lineTo(X(s), cy(s) + sg * rad(s)) : ctx.moveTo(X(s), cy(s) + sg * rad(s)))); ctx.stroke(); }
      // Water parcels move at the engine's local speed (scaled for display)
      const vmax = Math.max(...pr.speed), k = 1.2 / Math.max(vmax, 1e-9);
      ctx.fillStyle = "#2a78d6";
      for (const p of dots) {
        p.s += sampleAt(pr.position, pr.speed, p.s) * k * dt;
        if (p.s > 4) p.s -= 4;
        ctx.beginPath(); ctx.arc(X(p.s), cy(p.s) + p.lane * 1.6 * rad(p.s), 3, 0, Math.PI * 2); ctx.fill();
      }
      // Manometer columns: height ∝ pressure (display scale)
      const pmax = Math.max(...res.result.section_pressures, 1);
      res.result.section_pressures.forEach((p, i) => {
        const x = X(i), top = cy(i) - rad(i), colH = Math.max(0, (p / pmax) * (h * 0.33));
        ctx.fillStyle = "rgba(42,120,214,.5)"; ctx.fillRect(x - 5, top - colH, 10, colH);
        ctx.strokeStyle = "#7b8796"; ctx.lineWidth = 1; ctx.strokeRect(x - 6, top - h * 0.34, 12, h * 0.34);
        label(ctx, "ABCDE"[i], x, cy(i) + rad(i) + 16, { align: "center", font: "bold 13px system-ui" });
        label(ctx, `${fmt(p / 1000, 3)} kPa`, x, top - h * 0.34 - 10, { align: "center", font: "11px system-ui", color: "#4b5868" });
      });
    });

    recompute();
    return () => { stop(); recompute.cancel(); pg.destroy(); vg.destroy(); stage.destroy(); };
  },
};
