// Rocket Lab: multi_stage_delta_v for the design, optimize_staging for the optimum split.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

// Approximate public figures, for play only.
const PRESETS = {
  falcon: { label: "Falcon 9-like (expendable)", s1: [411, 25.6, 300], s2: [107.5, 4, 348], payload: 22.8 },
  saturn: { label: "Saturn V-like (first two stages)", s1: [2150, 131, 283], s2: [444, 36, 421], payload: 140 },
  electron: { label: "Small launcher (Electron-like)", s1: [9.25, 0.95, 311], s2: [2.05, 0.25, 343], payload: 0.3 },
};
// Rough delta-v budgets from Earth's surface including typical gravity and drag losses.
const TARGETS = [["Low Earth orbit", 9.4], ["Geostationary transfer", 11.8], ["Trans-lunar injection", 12.5]];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let res = null, optimum = null;

    const mk = (label, max, value, unit, onInput = () => { optimum = null; recompute(); }) =>
      slider({ label, min: 0, max, step: max / 1000, value, unit, onInput });
    const s1p = mk("Propellant", 3000, 411, "t"), s1d = mk("Dry mass", 200, 25.6, "t"), s1i = mk("Isp", 450, 300, "s");
    const s2p = mk("Propellant", 600, 107.5, "t"), s2d = mk("Dry mass", 60, 4, "t"), s2i = mk("Isp", 470, 348, "s");
    const payload = mk("Payload", 200, 22.8, "t");
    const preset = select({ label: "Start from", value: "falcon", options: [...Object.entries(PRESETS).map(([value, p]) => ({ value, label: p.label })), { value: "custom", label: "Custom" }], onChange: (k) => applyPreset(k) });
    const target = slider({ label: "Target Δv", min: 4, max: 14, step: 0.1, value: 9.4, unit: "km/s", onInput: () => draw() });
    const out = readouts([
      { key: "dv", label: "Total Δv" }, { key: "dv1", label: "Stage 1 Δv" }, { key: "dv2", label: "Stage 2 Δv" },
      { key: "m0", label: "Lift-off mass" }, { key: "pf", label: "Payload fraction" },
    ]);
    const optOut = el("p", { class: "note" });
    const optBtn = button("Size stages optimally for the target", () => optimise(), "primary");

    function applyPreset(k) {
      if (k === "custom") return;
      const p = PRESETS[k];
      [[s1p, s1d, s1i], [s2p, s2d, s2i]].forEach((st, i) => st.forEach((s, j) => {
        const v = (i ? p.s2 : p.s1)[j];
        if (j < 2) s.setRange(0, Math.max(v * 3, 1));
        s.set(v);
      }));
      payload.setRange(0, Math.max(p.payload * 4, 1)); payload.set(p.payload);
      optimum = null; recompute();
    }

    L.side.append(
      panel("Design", preset.root, payload.root),
      panel("Stage 1 (bottom)", s1p.root, s1d.root, s1i.root),
      panel("Stage 2 (top)", s2p.root, s2d.root, s2i.root),
      panel("Optimiser", target.root, optBtn, optOut),
    );
    const outPanel = panel("Performance (from the engine)", out.root);
    L.side.insertBefore(outPanel, L.side.children[1]);
    const graph = new LineGraph(L.bottom, { title: "Δv vs payload for this rocket", xLabel: "payload (t)", yLabel: "Δv (km/s)", height: 170, includeZero: true });

    const stagesKg = () => [
      { isp: s1i.value, propellant_mass: s1p.value * 1000, dry_mass: s1d.value * 1000 },
      { isp: s2i.value, propellant_mass: s2p.value * 1000, dry_mass: s2d.value * 1000 },
    ];

    const recompute = liveRequest(async (signal) => {
      const stages = stagesKg();
      const main = await simulate("physics", "multi_stage_delta_v", { stages, payload_mass: payload.value * 1000 }, signal);
      const pmax = Math.max(payload.value * 3, 1);
      const loads = Array.from({ length: 13 }, (_, i) => (pmax * i) / 12);
      const sweep = await Promise.all(loads.map((p) => simulate("physics", "multi_stage_delta_v", { stages, payload_mass: p * 1000 }, signal)));
      return { main, loads, sweep };
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: ({ main, loads, sweep }) => {
        L.clearError(); res = main;
        out.set("dv", `${fmt(main.result / 1000, 4)} km/s`);
        out.set("dv1", `${fmt(main.stages[0].delta_v / 1000, 4)} km/s`);
        out.set("dv2", `${fmt(main.stages[1].delta_v / 1000, 4)} km/s`);
        out.set("m0", `${fmt(main.liftoff_mass / 1000, 4)} t`);
        out.set("pf", `${fmt(main.payload_fraction * 100, 3)} %`);
        graph.setSeries([
          { name: "Δv", color: c1, x: loads, y: sweep.map((s) => s.result / 1000) },
          { name: "Target", color: c2, x: [loads[0], loads[loads.length - 1]], y: [target.value, target.value], dash: true },
        ]);
        draw();
      },
    });

    async function optimise() {
      const stages = stagesKg().map((s) => ({ isp: s.isp, structural_fraction: s.dry_mass / (s.dry_mass + s.propellant_mass) }));
      L.busy(true);
      try {
        const r = await simulate("physics", "optimize_staging", { delta_v: target.value * 1000, payload_mass: payload.value * 1000, stages });
        L.clearError();
        const [a, b] = r.result.stages;
        const before = res ? res.liftoff_mass : null;
        for (const [s, v] of [[s1p, a.propellant_mass], [s1d, a.dry_mass], [s2p, b.propellant_mass], [s2d, b.dry_mass]]) {
          s.setRange(0, Math.max(v / 1000 * 2, 1)); s.set(v / 1000);
        }
        preset.set("custom");
        optimum = r;
        optOut.textContent = `Optimal lift-off mass for ${fmt(target.value, 3)} km/s: ${fmt(r.result.liftoff_mass / 1000, 4)} t` +
          (before ? ` (previous design ${fmt(before / 1000, 4)} t).` : ".") +
          ` Stage split: ${fmt(a.delta_v / 1000, 3)} + ${fmt(b.delta_v / 1000, 3)} km/s.`;
        recompute();
      } catch (e) { L.error(e.message); optOut.textContent = ""; }
      finally { L.busy(false); }
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, "#07142b"); bg.addColorStop(1, "#1d3b66");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#2c3e2f"; ctx.fillRect(0, h - 26, w, 26);

      // Rocket (stage heights ~ cube root of mass)
      const m1 = s1p.value + s1d.value, m2 = s2p.value + s2d.value, mp = Math.max(payload.value, 0.01);
      const unit = (h - 110) / (Math.cbrt(m1) + Math.cbrt(m2) + Math.cbrt(mp) + 1e-9) * 0.9;
      const h1 = Math.cbrt(m1) * unit, h2 = Math.cbrt(m2) * unit, hp = Math.max(18, Math.cbrt(mp) * unit);
      const rw = Math.max(26, Math.min(60, unit * 1.2));
      const rx = w * 0.3, base = h - 26;
      const flameH = 30 + 10 * Math.sin(performance.now() / 90);
      ctx.fillStyle = "#eda100"; ctx.beginPath(); ctx.moveTo(rx - rw * 0.35, base); ctx.lineTo(rx, base + Math.min(24, flameH)); ctx.lineTo(rx + rw * 0.35, base); ctx.fill();
      const stageBox = (y, hh, color, txt) => {
        ctx.fillStyle = color; ctx.fillRect(rx - rw / 2, y - hh, rw, hh);
        ctx.strokeStyle = "rgba(0,0,0,.25)"; ctx.strokeRect(rx - rw / 2, y - hh, rw, hh);
        label(ctx, txt, rx + rw / 2 + 10, y - hh / 2, { color: "#fff", font: "12px system-ui" });
      };
      stageBox(base, h1, "#e8ecf2", `Stage 1 · ${fmt(m1, 4)} t`);
      stageBox(base - h1, h2, "#cfd6e0", `Stage 2 · ${fmt(m2, 4)} t`);
      ctx.fillStyle = "#eb6834"; ctx.beginPath();
      const py = base - h1 - h2;
      ctx.moveTo(rx - rw / 2, py); ctx.lineTo(rx + rw / 2, py); ctx.lineTo(rx, py - hp); ctx.closePath(); ctx.fill();
      label(ctx, `Payload · ${fmt(payload.value, 4)} t`, rx + rw / 2 + 10, py - hp / 2, { color: "#fff", font: "12px system-ui" });

      // Δv bar vs budgets
      const bx = w * 0.68, bw = 46, top = 40, bot = h - 60, vmax = 15;
      const Y = (v) => bot - (v / vmax) * (bot - top);
      ctx.fillStyle = "rgba(255,255,255,.08)"; ctx.fillRect(bx, top, bw, bot - top);
      if (res) {
        const d1 = res.stages[0].delta_v / 1000, d2 = res.stages[1].delta_v / 1000;
        ctx.fillStyle = c1; ctx.fillRect(bx, Y(d1), bw, bot - Y(d1));
        ctx.fillStyle = c2; ctx.fillRect(bx, Y(d1 + d2), bw, Y(d1) - Y(d1 + d2) - 2);
        label(ctx, `${fmt(d1 + d2, 3)} km/s`, bx + bw / 2, Math.min(Y(d1 + d2) - 12, bot - 12), { color: "#fff", align: "center", font: "bold 13px system-ui", halo: "rgba(7,20,43,.8)" });
      }
      for (const [name, v] of [...TARGETS, ["Your target", target.value]]) {
        const y = Y(v), mine = name === "Your target";
        ctx.strokeStyle = mine ? "#ffd479" : "rgba(255,255,255,.55)"; ctx.setLineDash(mine ? [] : [5, 4]); ctx.lineWidth = mine ? 2 : 1;
        ctx.beginPath(); ctx.moveTo(bx - 14, y); ctx.lineTo(bx + bw + 14, y); ctx.stroke(); ctx.setLineDash([]);
        if (mine) label(ctx, `Your target ${fmt(v, 3)} km/s`, bx - 20, y, { color: "#ffd479", font: "bold 12px system-ui", align: "right" });
        else label(ctx, `${name} ≈ ${v} km/s`, bx + bw + 20, y, { color: "rgba(255,255,255,.8)", font: "12px system-ui" });
      }
      label(ctx, "Δv (stage 1 + stage 2)", bx + bw / 2, h - 40, { color: "rgba(255,255,255,.8)", align: "center", font: "12px system-ui" });
      label(ctx, "Budgets are rough figures incl. gravity & drag losses", 14, 20, { color: "rgba(255,255,255,.6)", font: "11px system-ui" });
      if (optimum) label(ctx, "Optimised design", 14, 38, { color: "#1baf7a", font: "bold 12px system-ui" });
    }

    const flame = setInterval(draw, 80);
    recompute();
    return () => { clearInterval(flame); recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
