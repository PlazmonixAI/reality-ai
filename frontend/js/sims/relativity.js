// Special Relativity: physics.special_relativity gives gamma, time dilation, length contraction and the twin trip.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1] = SERIES();
    let res = null, tEarth = 0;

    const beta = slider({ label: "Ship speed (fraction of c)", min: 0.05, max: 0.995, step: 0.005, value: 0.8, onInput: () => recompute() });
    const dist = slider({ label: "Distance to the star", min: 1, max: 20, step: 0.5, value: 4, unit: "light-years", onInput: () => recompute() });
    const out = readouts([
      { key: "g", label: "Lorentz factor γ" }, { key: "earth", label: "Round trip, Earth clock" }, { key: "ship", label: "Round trip, ship clock" },
      { key: "diff", label: "Traveller is younger by" }, { key: "len", label: "Distance seen from the ship" },
    ]);
    L.side.append(panel("Twin paradox", beta.root, dist.root, el("p", { class: "note" }, "One twin flies to a star and back; the other stays on Earth. Moving clocks run slow by the factor γ.")),
      panel("Relativity (from the engine)", out.root));
    const player = new Player(L.bottom, (t) => { tEarth = t; draw(); }, { speeds: [0.5, 1, 2], timeFormat: (v) => `${fmt(v, 3)} years (Earth)` });
    const graph = new LineGraph(L.bottom, { title: "γ grows without limit as v → c", xLabel: "v / c", yLabel: "γ", height: 140, yRange: [1, 10] });

    const recompute = liveRequest((signal) => simulate("physics", "special_relativity", { beta: beta.value, distance_ly: dist.value }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        const t = res.trip;
        out.set("g", fmt(res.gamma, 5)); out.set("earth", `${fmt(t.earth_years, 4)} years`); out.set("ship", `${fmt(t.traveller_years, 4)} years`);
        out.set("diff", `${fmt(t.age_difference_years, 4)} years`); out.set("len", `${fmt(t.distance_seen_by_traveller_ly, 4)} ly each way`);
        graph.setSeries([{ name: "γ", color: c1, x: r.gamma_curve.beta, y: r.gamma_curve.gamma.map((g) => Math.min(g, 10)) }]);
        graph.setCursor(beta.value);
        player.load(t.earth_years, 10);
      },
    });

    function clock(ctx, x, y, years, name, color) {
      ctx.fillStyle = "#fff"; ctx.strokeStyle = color; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(x, y, 42, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      const a = (years % 1) * Math.PI * 2 - Math.PI / 2;
      ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(a) * 32, y + Math.sin(a) * 32); ctx.stroke();
      label(ctx, `${fmt(years, 3)} yr`, x, y + 60, { align: "center", font: "bold 14px system-ui", color: "#fff" });
      label(ctx, name, x, y - 56, { align: "center", font: "12px system-ui", color });
    }

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#0b1426"; ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 80; i++) { ctx.fillStyle = "rgba(255,255,255,.5)"; ctx.fillRect((i * 97) % w, (i * 53) % h, 1.5, 1.5); }
      if (!res) return;
      const t = res.trip, half = t.earth_years / 2;
      const x0 = 80, x1 = w - 80, y = h * 0.28;
      ctx.fillStyle = "#2a78d6"; ctx.beginPath(); ctx.arc(x0, y, 22, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#ffd479"; ctx.beginPath(); ctx.arc(x1, y, 16, 0, Math.PI * 2); ctx.fill();
      label(ctx, "Earth", x0, y + 36, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      label(ctx, `star, ${fmt(dist.value, 3)} ly away`, x1, y + 36, { align: "center", color: "#c9ced6", font: "12px system-ui" });
      const frac = tEarth <= half ? tEarth / half : 2 - tEarth / half;
      const sx = x0 + 30 + frac * (x1 - x0 - 60);
      // Ship, squashed along its motion by 1/γ (length contraction as seen from Earth)
      const len = 44 / res.gamma;
      ctx.fillStyle = "#e8ecf2"; ctx.beginPath(); ctx.ellipse(sx, y, len / 2 + 4, 10, 0, 0, Math.PI * 2); ctx.fill();
      label(ctx, `ship length seen from Earth ÷ ${fmt(res.gamma, 3)}`, sx, y - 22, { align: "center", color: "#c9ced6", font: "11px system-ui" });
      clock(ctx, w * 0.3, h * 0.66, tEarth, "Earth twin", "#2a78d6");
      clock(ctx, w * 0.7, h * 0.66, tEarth / res.gamma, "Travelling twin", "#eb6834");
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
