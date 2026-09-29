// Faraday's Law: magnet_field draws the magnet's field; magnet_coil_induction gives flux, EMF and current.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, checkbox, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, sampleAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const MAG_LEN = 0.08, RESISTANCE = 2;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1, c2] = SERIES();
    let field = null, data = null, simTime = 0;

    const motion = segmented({ label: "Magnet motion", value: "pass", options: [{ value: "pass", label: "Push through" }, { value: "oscillate", label: "Oscillate" }], onChange: () => { sync(); recompute(); } });
    const speed = slider({ label: "Speed", min: 0.1, max: 3, step: 0.05, value: 1, unit: "m/s", onInput: () => recompute() });
    const amp = slider({ label: "Amplitude", min: 1, max: 15, step: 0.5, value: 8, unit: "cm", onInput: () => recompute() });
    const freq = slider({ label: "Frequency", min: 0.2, max: 5, step: 0.1, value: 1, unit: "Hz", onInput: () => recompute() });
    const turns = slider({ label: "Coil turns", min: 1, max: 500, step: 1, value: 200, onInput: () => recompute() });
    const radius = slider({ label: "Coil radius", min: 1, max: 6, step: 0.1, value: 3, unit: "cm", onInput: () => recompute() });
    const strength = slider({ label: "Magnet strength (moment)", min: 0.2, max: 5, step: 0.1, value: 1.5, unit: "A·m²", onInput: () => { recompute(); fieldReq(); } });
    const flip = checkbox({ label: "Flip magnet (N ↔ S)", onChange: () => recompute() });
    const out = readouts([{ key: "emf", label: "EMF now" }, { key: "peak", label: "Peak EMF" }, { key: "i", label: "Current now" }, { key: "lam", label: "Flux linkage now" }]);
    function sync() {
      speed.root.style.display = motion.value === "pass" ? "" : "none";
      amp.root.style.display = freq.root.style.display = motion.value === "oscillate" ? "" : "none";
    }
    L.side.append(
      panel("Magnet", motion.root, speed.root, amp.root, freq.root, strength.root, flip.root),
      panel("Coil", turns.root, radius.root, el("p", { class: "note" }, `A ${RESISTANCE} Ω bulb completes the circuit.`)),
      panel("Induction (from the engine)", out.root),
    );
    sync();
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); lamGraph.setCursor(t); emfGraph.setCursor(t); }, { speeds: [0.1, 0.25, 0.5, 1], speed: 0.25 });
    const lamGraph = new LineGraph(L.bottom, { title: "Flux linkage NΦ", xLabel: "time (s)", yLabel: "mWb-turns", height: 110 });
    const emfGraph = new LineGraph(L.bottom, { title: "Induced EMF = −N dΦ/dt", xLabel: "time (s)", yLabel: "EMF (mV)", height: 110 });

    const fieldReq = liveRequest((signal) => simulate("physics", "magnet_field", {
      moment: strength.value, length: MAG_LEN, x_range: [-0.25, 0.25], y_range: [-0.15, 0.15], grid: 20, n_lines: 18,
    }, signal), { onResult: (r) => { field = r; draw(); }, onError: (e) => L.error(e.message) });

    const recompute = liveRequest((signal) => simulate("physics", "magnet_coil_induction", {
      moment: strength.value, length: MAG_LEN, turns: Math.round(turns.value), radius: radius.value / 100, resistance: RESISTANCE,
      motion: motion.value, speed: speed.value, travel: 0.3, amplitude: amp.value / 100, frequency: freq.value, centre: -0.1,
      flip: flip.value, n_points: 1601,
    }, signal), {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const T = r.trajectory;
        lamGraph.setSeries([{ name: "NΦ", color: c1, x: T.t, y: T.flux_linkage.map((v) => v * 1000) }]);
        emfGraph.setSeries([{ name: "EMF", color: c2, x: T.t, y: T.emf.map((v) => v * 1000) }]);
        out.set("peak", `${fmt(r.result.peak_emf * 1000, 4)} mV`);
        player.load(T.t[T.t.length - 1], motion.value === "pass" ? T.t[T.t.length - 1] : 3 / freq.value);
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      view.fit(-0.36, 0.36, -0.2, 0.2, w, h, { pad: 0.02 });
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      const T = data && data.trajectory;
      const z = T ? sampleAt(T.t, T.position, simTime) : -0.3;
      const o = flip.value ? -1 : 1;
      // Field lines, moved rigidly with the magnet (the engine computes them for a magnet at the origin, N at +x).
      if (field) {
        ctx.strokeStyle = "rgba(74,58,167,.35)"; ctx.lineWidth = 1.2;
        for (const line of field.field_lines) {
          ctx.beginPath();
          line.forEach(([x, y], k) => { const X = view.x(z + o * x), Y = view.y(y); if (k) ctx.lineTo(X, Y); else ctx.moveTo(X, Y); });
          ctx.stroke();
        }
      }
      // Coil (back half, then magnet, then front half)
      const a = radius.value / 100, n = Math.min(24, Math.max(3, Math.round(turns.value / 20)));
      const coilW = 0.03, X = (i) => view.x(-coilW / 2 + (i / (n - 1)) * coilW);
      ctx.strokeStyle = "#a0662b"; ctx.lineWidth = 2.5;
      for (let i = 0; i < n; i++) { ctx.beginPath(); ctx.ellipse(X(i), view.y(0), view.len(a) * 0.28, view.len(a), 0, Math.PI / 2, (3 * Math.PI) / 2); ctx.stroke(); }
      // Magnet
      const mx0 = view.x(z - MAG_LEN / 2), mx1 = view.x(z + MAG_LEN / 2), mh = view.len(0.014);
      const north = o > 0 ? [view.x(z), mx1] : [mx0, view.x(z)], south = o > 0 ? [mx0, view.x(z)] : [view.x(z), mx1];
      ctx.fillStyle = "#e34948"; ctx.fillRect(north[0], view.y(0) - mh, north[1] - north[0], 2 * mh);
      ctx.fillStyle = "#2a78d6"; ctx.fillRect(south[0], view.y(0) - mh, south[1] - south[0], 2 * mh);
      label(ctx, "N", (north[0] + north[1]) / 2, view.y(0), { align: "center", color: "#fff", font: "bold 14px system-ui" });
      label(ctx, "S", (south[0] + south[1]) / 2, view.y(0), { align: "center", color: "#fff", font: "bold 14px system-ui" });
      ctx.strokeStyle = "#c98843"; ctx.lineWidth = 2.5;
      for (let i = 0; i < n; i++) { ctx.beginPath(); ctx.ellipse(X(i), view.y(0), view.len(a) * 0.28, view.len(a), 0, -Math.PI / 2, Math.PI / 2); ctx.stroke(); }
      // Leads to bulb and voltmeter
      const emf = T ? sampleAt(T.t, T.emf, simTime) : 0, peak = data ? data.result.peak_emf || 1 : 1;
      const bx = view.x(0), by = view.y(-0.17);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(X(0), view.y(-a)); ctx.lineTo(X(0), by); ctx.lineTo(bx - 60, by); ctx.moveTo(X(n - 1), view.y(-a)); ctx.lineTo(X(n - 1), by); ctx.lineTo(bx + 60, by); ctx.stroke();
      const glow = Math.min(1, Math.abs(emf) / peak);
      const g = ctx.createRadialGradient(bx - 60, by, 2, bx - 60, by, 34);
      g.addColorStop(0, `rgba(255,220,90,${0.9 * glow * glow})`); g.addColorStop(1, "rgba(255,220,90,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(bx - 60, by, 34, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = `rgba(255,${230 - 40 * glow},${160 - 120 * glow},${0.4 + 0.6 * glow})`; ctx.strokeStyle = "#39424e";
      ctx.beginPath(); ctx.arc(bx - 60, by, 12, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      // Voltmeter
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(bx + 60, by, 26, Math.PI, 0); ctx.closePath(); ctx.fill(); ctx.stroke();
      const ang = -Math.PI / 2 + Math.max(-1, Math.min(1, emf / peak)) * 1.2;
      ctx.strokeStyle = "#e34948"; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(bx + 60, by); ctx.lineTo(bx + 60 + Math.cos(ang) * 22, by + Math.sin(ang) * 22); ctx.stroke();
      label(ctx, "V", bx + 60, by + 12, { align: "center", font: "bold 11px system-ui" });
      if (T) {
        out.set("emf", `${fmt(emf * 1000, 4)} mV`); out.set("i", `${fmt((emf / RESISTANCE) * 1000, 4)} mA`);
        out.set("lam", `${fmt(sampleAt(T.t, T.flux_linkage, simTime) * 1000, 4)} mWb-turns`);
      }
      label(ctx, `t = ${fmt(simTime, 3)} s   magnet at ${fmt(z * 100, 3)} cm`, 14, 18, { font: "13px system-ui" });
      label(ctx, "Purple lines: the magnet's field (from the engine)", w - 14, 18, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    fieldReq();
    recompute();
    return () => { recompute.cancel(); fieldReq.cancel(); player.destroy(); lamGraph.destroy(); emfGraph.destroy(); stage.destroy(); };
  },
};
