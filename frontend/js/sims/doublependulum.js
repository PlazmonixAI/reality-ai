// Double Pendulum: physics.double_pendulum integrates the motion and a nearly identical twin to reveal chaos.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, checkbox, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, indexAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let data = null, simT = 0;

    const t1 = slider({ label: "Upper arm start angle", min: -179, max: 179, step: 1, value: 120, unit: "°", onInput: () => recompute() });
    const t2 = slider({ label: "Lower arm start angle", min: -179, max: 179, step: 1, value: -10, unit: "°", onInput: () => recompute() });
    const mr = slider({ label: "Lower mass ÷ upper mass", min: 0.1, max: 5, value: 1, log: true, onInput: () => recompute() });
    const lr = slider({ label: "Lower arm ÷ upper arm", min: 0.3, max: 2, step: 0.05, value: 1, onInput: () => recompute() });
    const eps = slider({ label: "Twin starts off by", min: 1e-9, max: 1, value: 1e-4, log: true, unit: "°", onInput: () => recompute() });
    const trail = checkbox({ label: "Show trails", value: true, onChange: () => draw() });
    const out = readouts([{ key: "lyap", label: "Lyapunov exponent (≈)" }, { key: "dt", label: "Error ×10 every" }, { key: "flip", label: "Lower-arm flips" }, { key: "e", label: "Energy drift (numerical)" }]);
    L.side.append(
      panel("Double pendulum (1 m arm)", t1.root, t2.root, mr.root, lr.root, eps.root, trail.root, legend([{ label: "pendulum", color: c1 }, { label: "twin", color: c2 }])),
      panel("Chaos (from the engine)", out.root, el("p", { class: "note" }, "Two pendulums that start a hair apart soon do completely different things: sensitive dependence on initial conditions.")),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "How far apart the twins are (log scale)", xLabel: "time (s)", yLabel: "log₁₀ separation", height: 140 });

    const recompute = liveRequest((signal) => simulate("physics", "double_pendulum", {
      theta1: t1.value, theta2: t2.value, mass1: 1, mass2: mr.value, length1: 1, length2: lr.value,
      duration: 30, n_points: 3001, perturbation_deg: eps.value,
    }, signal), {
      delay: 80, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const x = r.result;
        out.set("lyap", x.lyapunov_exponent !== null ? `${fmt(x.lyapunov_exponent, 3)} s⁻¹` : "no exponential growth");
        out.set("dt", x.lyapunov_exponent > 0.01 ? `${fmt(Math.log(10) / x.lyapunov_exponent, 3)} s` : "—");
        out.set("flip", String(x.flips)); out.set("e", fmt(x.max_energy_drift, 2));
        graph.setSeries([{ name: "separation", color: c1, x: r.trajectory.t, y: r.twin.separation.map((s) => Math.log10(s)) }]);
        player.load(30, 30);
      },
    });

    function drawOne(ctx, cx, cy, s, k, x1, y1, x2, y2, col, alpha) {
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = "#c9ced6"; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(cx, cy); if (x1) ctx.lineTo(cx + x1[k] * s, cy - y1[k] * s); ctx.lineTo(cx + x2[k] * s, cy - y2[k] * s); ctx.stroke();
      if (x1) { ctx.fillStyle = "#9aa6b5"; ctx.beginPath(); ctx.arc(cx + x1[k] * s, cy - y1[k] * s, 9, 0, Math.PI * 2); ctx.fill(); }
      ctx.fillStyle = col; ctx.beginPath(); ctx.arc(cx + x2[k] * s, cy - y2[k] * s, 7 + 4 * Math.cbrt(mr.value), 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
    }

    function draw() {
      const { ctx, width: W, height: H } = stage;
      if (!W) return;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, W, H);
      if (!data) return;
      const tr = data.trajectory, tw = data.twin;
      const k = indexAt(tr.t, simT), reach = 1 + lr.value, s = Math.min(W, H) * 0.45 / reach, cx = W / 2, cy = H / 2;
      if (trail.value) {
        for (const [xs, ys, col] of [[tw.x2, tw.y2, c2], [tr.x2, tr.y2, c1]]) {
          ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.beginPath();
          for (let i = Math.max(0, k - 400); i <= k; i++) { const px = cx + xs[i] * s, py = cy - ys[i] * s; if (i === Math.max(0, k - 400)) ctx.moveTo(px, py); else ctx.lineTo(px, py); }
          ctx.globalAlpha = 0.55; ctx.stroke(); ctx.globalAlpha = 1;
        }
      }
      drawOne(ctx, cx, cy, s, k, tw.x1, tw.y1, tw.x2, tw.y2, c2, 0.6);
      drawOne(ctx, cx, cy, s, k, tr.x1, tr.y1, tr.x2, tr.y2, c1, 1);
      ctx.fillStyle = "#c9ced6"; ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2); ctx.fill();
      label(ctx, `separation ${fmt(data.twin.separation[k], 2)}`, 16, 20, { color: "#c9ced6", font: "12px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
