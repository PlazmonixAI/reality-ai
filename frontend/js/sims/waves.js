// Waves on a String: physics.string_wave solves the damped wave equation; we draw the beads.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, button } from "../core/ui.js";
import { createStage, indexAt, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { fmt } from "../core/format.js";

const LENGTH = 2, DURATION = 4;

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    let data = null, simTime = 0;

    const driver = segmented({ label: "Driver", value: "oscillate", options: [{ value: "oscillate", label: "Oscillate" }, { value: "pulse", label: "Pulse" }], onChange: () => { sync(); recompute(); } });
    const freq = slider({ label: "Frequency", min: 0.5, max: 12, step: 0.05, value: 3, unit: "Hz", onInput: () => recompute() });
    const width = slider({ label: "Pulse width", min: 0.02, max: 0.3, step: 0.01, value: 0.08, unit: "s", onInput: () => recompute() });
    const amp = slider({ label: "Amplitude", min: 0.5, max: 10, step: 0.1, value: 3, unit: "cm", onInput: () => recompute() });
    const tension = slider({ label: "Tension", min: 0.5, max: 20, step: 0.1, value: 4, unit: "N", onInput: () => recompute() });
    const density = slider({ label: "String density", min: 0.01, max: 0.3, step: 0.005, value: 0.1, unit: "kg/m", onInput: () => recompute() });
    const damping = slider({ label: "Damping", min: 0, max: 5, step: 0.05, value: 0.2, unit: "1/s", onInput: () => recompute() });
    const end = segmented({ label: "Right end", value: "fixed", options: [{ value: "fixed", label: "Fixed" }, { value: "loose", label: "Loose" }, { value: "none", label: "No end" }], onChange: () => recompute() });
    const out = readouts([{ key: "c", label: "Wave speed" }, { key: "lam", label: "Wavelength" }, { key: "T", label: "Period" }, { key: "trip", label: "Time to cross" }]);
    const harmBox = el("div", { class: "btn-row" });

    function sync() {
      const osc = driver.value === "oscillate";
      freq.root.style.display = osc ? "" : "none";
      width.root.style.display = osc ? "none" : "";
    }
    L.side.append(
      panel("Driver", driver.root, freq.root, width.root, amp.root),
      panel("String", tension.root, density.root, damping.root, end.root),
      panel("Waves (from the engine)", out.root, el("p", { class: "note" }, "Standing-wave harmonics — click to drive at one:"), harmBox),
    );
    sync();
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); }, { speeds: [0.1, 0.25, 0.5, 1], speed: 0.25, loop: true });

    const recompute = liveRequest((signal) => simulate("physics", "string_wave", {
      length: LENGTH, tension: tension.value, linear_density: density.value, duration: DURATION,
      driver: driver.value, frequency: freq.value, amplitude: amp.value / 100, pulse_width: width.value,
      damping: damping.value, end: end.value, n_cells: 120, n_frames: 480,
    }, signal), {
      delay: 150, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (res) => {
        L.clearError(); data = res;
        const r = res.result;
        out.set("c", `${fmt(r.wave_speed, 4)} m/s`);
        out.set("lam", r.wavelength ? `${fmt(r.wavelength, 4)} m` : "—");
        out.set("T", r.period ? `${fmt(r.period, 4)} s` : "—");
        out.set("trip", `${fmt(r.travel_time, 4)} s`);
        harmBox.replaceChildren(...(r.harmonics.length ? r.harmonics.slice(0, 4).map((f, i) =>
          button(`f${i + 1} = ${fmt(f, 3)} Hz`, () => { driver.set("oscillate"); sync(); freq.set(Math.min(12, f)); recompute(); })) : [el("span", { class: "note" }, "None with an open end.")]));
        const keep = simTime;
        player.load(DURATION, DURATION, { autoplay: true });
        player.seek(Math.min(keep, DURATION));
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, "#f6f9fd"); bg.addColorStop(1, "#e6eef8");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      const x0 = 90, x1 = w - 70, mid = h / 2, scale = Math.min(h * 0.35 / 0.1, (x1 - x0) / LENGTH);   // px per metre (vertical ≤ ±10 cm)
      // Reference line and ruler
      ctx.setLineDash([4, 6]); ctx.strokeStyle = "#b8c4d3"; ctx.beginPath(); ctx.moveTo(x0, mid); ctx.lineTo(x1, mid); ctx.stroke(); ctx.setLineDash([]);
      for (let cm = -10; cm <= 10; cm += 5) {
        const y = mid - (cm / 100) * scale;
        label(ctx, `${cm} cm`, x1 + 14, y, { font: "10px system-ui", color: "#7b8796" });
      }
      for (let m = 0; m <= LENGTH; m += 0.5) label(ctx, `${m} m`, x0 + (m / LENGTH) * (x1 - x0), h - 16, { align: "center", font: "11px system-ui", color: "#4b5868" });

      let u = null;
      if (data) u = data.frames.u[indexAt(data.frames.t, simTime)];
      const n = u ? u.length : 121;
      const X = (i) => x0 + (i / (n - 1)) * (x1 - x0), Y = (i) => mid - (u ? u[i] : 0) * scale;
      // Driver
      ctx.fillStyle = "#39424e"; ctx.fillRect(18, mid - 40, 44, 80);
      ctx.fillStyle = "#7b8796"; ctx.fillRect(62, Y(0) - 6, x0 - 62, 12);
      label(ctx, driver.value === "oscillate" ? "∿" : "⌇", 40, mid, { align: "center", font: "bold 22px system-ui", color: "#fff" });
      // String beads
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 1.5; ctx.beginPath();
      for (let i = 0; i < n; i++) (i ? ctx.lineTo(X(i), Y(i)) : ctx.moveTo(X(i), Y(i)));
      ctx.stroke();
      for (let i = 0; i < n; i++) {
        ctx.fillStyle = i % 10 === 0 ? "#1baf7a" : "#e34948";
        ctx.beginPath(); ctx.arc(X(i), Y(i), 4, 0, Math.PI * 2); ctx.fill();
      }
      // Right end
      if (end.value === "fixed") { ctx.fillStyle = "#39424e"; ctx.fillRect(x1 + 2, mid - 30, 10, 60); }
      else if (end.value === "loose") {
        ctx.fillStyle = "#7b8796"; ctx.fillRect(x1 + 12, mid - 60, 6, 120);
        ctx.strokeStyle = "#39424e"; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(x1 + 15, Y(n - 1), 9, 0, Math.PI * 2); ctx.stroke();
      } else {
        const g = ctx.createLinearGradient(x1 - 20, 0, x1 + 40, 0);
        g.addColorStop(0, "rgba(230,238,248,0)"); g.addColorStop(1, "rgba(230,238,248,1)");
        ctx.fillStyle = g; ctx.fillRect(x1 - 20, 0, 60, h);
        label(ctx, "→ continues", x1 + 4, mid + 40, { font: "11px system-ui", color: "#7b8796" });
      }
      label(ctx, `t = ${fmt(simTime, 3)} s`, 14, 20, { font: "13px system-ui" });
      label(ctx, "Green beads mark every 10th bead", w - 14, 20, { font: "11px system-ui", align: "right", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); stage.destroy(); };
  },
};
