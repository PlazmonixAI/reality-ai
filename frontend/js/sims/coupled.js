// Coupled Oscillators: physics.coupled_oscillators gives normal modes and the exact motion of a mass-spring chain.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const cols = SERIES();
    let data = null, simT = 0;

    const count = segmented({ label: "Masses", value: 2, options: [{ value: 2, label: "2" }, { value: 3, label: "3" }], onChange: () => { syncStart(); recompute(); } });
    const kw = slider({ label: "Wall springs", min: 1, max: 40, step: 0.5, value: 10, unit: "N/m", onInput: () => recompute() });
    const kc = slider({ label: "Coupling springs", min: 0.1, max: 40, step: 0.1, value: 1, unit: "N/m", onInput: () => recompute() });
    const mass = slider({ label: "Each mass", min: 0.2, max: 5, step: 0.1, value: 1, unit: "kg", onInput: () => recompute() });
    const start = segmented({ label: "Start by", value: "pull", options: [{ value: "pull", label: "Pulling mass 1" }, { value: "m1", label: "Mode 1" }, { value: "m2", label: "Mode 2" }, { value: "m3", label: "Mode 3" }], onChange: () => recompute() });
    function syncStart() { start.root.querySelectorAll("button")[3].style.display = count.value === 3 ? "" : "none"; if (count.value === 2 && start.value === "m3") start.set("m1"); }
    const out = readouts([{ key: "f", label: "Normal-mode frequencies" }, { key: "t", label: "Beat period (modes 1–2)" }, { key: "e", label: "Total energy" }]);
    L.side.append(
      panel("Chain", count.root, mass.root, kw.root, kc.root, start.root, el("p", { class: "note" }, "Weak coupling + one mass pulled = beats: the motion flows back and forth. Start in a normal mode and it never changes shape.")),
      panel("Modes (from the engine)", out.root),
    );
    syncStart();
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); }, { speeds: [0.5, 1, 2, 4] });
    const graph = new LineGraph(L.bottom, { title: "Displacement of each mass", xLabel: "time (s)", yLabel: "x (cm)", height: 150 });

    const recompute = liveRequest(async (signal) => {
      const n = count.value, ms = Array(n).fill(mass.value), ks = [kw.value, ...Array(n - 1).fill(kc.value), kw.value];
      let disp = [0.1, ...Array(n - 1).fill(0)];
      if (start.value !== "pull") {
        const modes = await simulate("physics", "coupled_oscillators", { masses: ms, springs: ks, n_points: 2 }, signal);
        disp = modes.result.mode_shapes[Number(start.value[1]) - 1].map((s) => 0.1 * s);
      }
      return simulate("physics", "coupled_oscillators", { masses: ms, springs: ks, displacements: disp, n_points: 3000 }, signal);
    }, {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const f = r.result.frequencies;
        out.set("f", f.map((x) => fmt(x, 4)).join(", ") + " rad/s");
        out.set("t", `${fmt((2 * Math.PI) / (f[1] - f[0]), 4)} s`); out.set("e", `${fmt(r.result.total_energy * 1000, 4)} mJ`);
        graph.setSeries(r.trajectory.x.map((xs, i) => ({ name: `mass ${i + 1}`, color: cols[i], x: r.trajectory.t, y: xs.map((v) => v * 100) })));
        const T = r.trajectory.t[r.trajectory.t.length - 1];
        player.load(T, T);
      },
    });

    function spring(ctx, x0, x1, y, k) {
      const coils = 10, amp = 7 + Math.min(6, k / 6);
      ctx.strokeStyle = "#4b5868"; ctx.lineWidth = 1.5 + Math.min(2, k / 15); ctx.beginPath(); ctx.moveTo(x0, y);
      for (let i = 1; i < coils; i++) ctx.lineTo(x0 + ((x1 - x0) * i) / coils, y + (i % 2 ? amp : -amp));
      ctx.lineTo(x1, y); ctx.stroke();
    }

    function draw() {
      const { ctx, width: W, height: H } = stage;
      if (!W) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, W, H);
      if (!data) return;
      const n = data.trajectory.x.length, tr = data.trajectory;
      const wl = 40, wr = W - 40, y = H * 0.45, gap = (wr - wl) / (n + 1), box = 56, scale = gap * 2.2; // 10 cm → 0.22 gap
      ctx.fillStyle = "#9aa6b5"; ctx.fillRect(wl - 14, y - 60, 14, 120); ctx.fillRect(wr, y - 60, 14, 120);
      ctx.strokeStyle = "#39424e"; ctx.beginPath(); ctx.moveTo(wl - 14, y + 40); ctx.lineTo(wr + 14, y + 40); ctx.stroke();
      const xs = tr.x.map((row, i) => wl + gap * (i + 1) + sampleAt(tr.t, row, simT) * scale);
      const ks = [kw.value, ...Array(n - 1).fill(kc.value), kw.value];
      let prev = wl;
      xs.forEach((x, i) => { spring(ctx, prev, x - box / 2, y, ks[i]); prev = x + box / 2; });
      spring(ctx, prev, wr, y, ks[n]);
      xs.forEach((x, i) => {
        ctx.fillStyle = cols[i]; ctx.fillRect(x - box / 2, y - box / 2 + 12, box, box - 24 + 16);
        label(ctx, `${i + 1}`, x, y + 8, { align: "center", color: "#fff", font: "bold 16px system-ui" });
        ctx.setLineDash([3, 4]); ctx.strokeStyle = "#9aa6b5"; ctx.beginPath(); ctx.moveTo(wl + gap * (i + 1), y + 44); ctx.lineTo(wl + gap * (i + 1), y + 70); ctx.stroke(); ctx.setLineDash([]);
      });
      // Mode shape diagrams from the engine
      const shapes = data.result.mode_shapes, f = data.result.frequencies;
      shapes.forEach((s, j) => {
        const bx = 40 + j * ((W - 80) / shapes.length), by = H - 70, bw = (W - 80) / shapes.length - 20;
        label(ctx, `mode ${j + 1}: ω = ${fmt(f[j], 3)} rad/s`, bx, by - 30, { font: "12px system-ui", color: "#4b5868" });
        s.forEach((v, i) => {
          const px = bx + (bw * (i + 1)) / (s.length + 1);
          ctx.strokeStyle = "#c9ced6"; ctx.beginPath(); ctx.moveTo(px, by); ctx.lineTo(px + v * 26, by); ctx.stroke();
          ctx.fillStyle = cols[i]; ctx.beginPath(); ctx.arc(px + v * 26, by, 6, 0, Math.PI * 2); ctx.fill();
        });
      });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
