// Rolling Race: physics.rolling_race — moment of inertia decides who reaches the bottom first.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, checkbox, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const SHAPES = { solid_sphere: "Solid ball", hollow_sphere: "Hollow ball", solid_cylinder: "Solid cylinder", hoop: "Hoop (ring)", frictionless_block: "Ice block (no friction)" };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const cols = SERIES();
    let res = null, simT = 0;

    const picks = Object.entries(SHAPES).map(([v, l], i) => checkbox({ label: l, value: i < 3, onChange: () => { limit(); recompute(); } }));
    function limit() { const on = picks.filter((p) => p.value); if (on.length > 3) on[on.length - 1].set(false); if (!picks.some((p) => p.value)) picks[0].set(true); }
    const ang = slider({ label: "Ramp angle", min: 5, max: 60, step: 1, value: 20, unit: "°", onInput: () => recompute() });
    const len = slider({ label: "Ramp length", min: 1, max: 10, step: 0.5, value: 4, unit: "m", onInput: () => recompute() });
    const mu = slider({ label: "Friction coefficient μ", min: 0, max: 1, step: 0.01, value: 0.6, onInput: () => recompute() });
    const out = readouts([{ key: "w", label: "Winner" }, { key: "o", label: "Finish order" }]);
    const table = el("div", { class: "note" });
    L.side.append(
      panel("Racers (up to 3)", ...picks.map((p) => p.root)),
      panel("Ramp", ang.root, len.root, mu.root, el("p", { class: "note" }, "Same drop, same energy — but spinning takes a share. The more mass far from the axis, the slower it rolls.")),
      panel("Race (from the engine)", out.root, table),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); }, { speeds: [0.25, 0.5, 1] });
    const graph = new LineGraph(L.bottom, { title: "Distance down the ramp", xLabel: "time (s)", yLabel: "distance (m)", height: 140, includeZero: true });

    const chosen = () => Object.keys(SHAPES).filter((_, i) => picks[i].value).slice(0, 3);
    const recompute = liveRequest((signal) => simulate("physics", "rolling_race", { shapes: chosen(), angle_deg: ang.value, length: len.value, mu: mu.value, radius: 0.15 }, signal), {
      delay: 30, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        out.set("w", SHAPES[res.winner]); out.set("o", res.finish_order.map((s) => SHAPES[s].split(" (")[0]).join(" → "));
        table.replaceChildren(...res.racers.map((x, i) => el("div", { style: `color:${cols[i]}` },
          `${SHAPES[x.shape]}: ${fmt(x.time, 3)} s, ${fmt(x.final_speed, 3)} m/s, ${fmt(x.energy_fraction_rotational * 100, 3)} % spin${x.rolling || x.shape === "frictionless_block" ? "" : " (slipping!)"}`)));
        graph.setSeries(res.racers.map((x, i) => ({ name: SHAPES[x.shape], color: cols[i], x: x.trajectory.t, y: x.trajectory.distance })));
        const T = Math.max(...res.racers.map((x) => x.time));
        player.load(T * 1.05, Math.max(3, T * 1.05));
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const th = (ang.value * Math.PI) / 180, lane = 46, n = res.racers.length;
      const avail = Math.min((w - 200) / Math.cos(th), (h - 60 - n * lane) / Math.sin(th));
      const s = avail / len.value, x0 = 60, y0 = h - 40 - avail * Math.sin(th) - (n - 1) * lane;
      res.racers.forEach((x, i) => {
        const oy = y0 + i * lane, ex = x0 + avail * Math.cos(th), ey = oy + avail * Math.sin(th);
        ctx.fillStyle = "#c9ced6"; ctx.beginPath(); ctx.moveTo(x0, oy); ctx.lineTo(ex, ey); ctx.lineTo(ex, ey + 8); ctx.lineTo(x0, oy + 8); ctx.fill();
        ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(ex, ey - 30); ctx.lineTo(ex, ey + 8); ctx.stroke();
        const d = Math.min(len.value, sampleAt(x.trajectory.t, x.trajectory.distance, Math.min(simT, x.time))), rot = sampleAt(x.trajectory.t, x.trajectory.angle_rad, Math.min(simT, x.time));
        const R = 16, cx = x0 + d * s * Math.cos(th) + R * Math.sin(th), cy = oy + d * s * Math.sin(th) - R * Math.cos(th);
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot);
        ctx.fillStyle = cols[i]; ctx.strokeStyle = cols[i]; ctx.lineWidth = 5;
        if (x.shape === "frictionless_block") { ctx.restore(); ctx.save(); ctx.translate(cx, cy); ctx.rotate(th); ctx.fillStyle = "#bfe3f5"; ctx.fillRect(-R, -R + 2, 2 * R, 2 * R - 2); ctx.strokeStyle = cols[i]; ctx.lineWidth = 2; ctx.strokeRect(-R, -R + 2, 2 * R, 2 * R - 2); }
        else if (x.shape === "hoop") { ctx.beginPath(); ctx.arc(0, 0, R - 2.5, 0, Math.PI * 2); ctx.stroke(); }
        else if (x.shape === "hollow_sphere") { ctx.globalAlpha = 0.35; ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1; ctx.lineWidth = 3; ctx.stroke(); }
        else { ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.fill(); }
        if (x.shape !== "frictionless_block") { ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(R - 3, 0); ctx.stroke(); }
        ctx.restore();
        label(ctx, SHAPES[x.shape], x0, oy - 26, { color: cols[i], font: "bold 12px system-ui" });
        if (simT >= x.time) label(ctx, `${fmt(x.time, 3)} s`, ex + 26, ey - 14, { color: cols[i], font: "bold 13px system-ui" });
      });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
