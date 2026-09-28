// Doppler Effect: physics.doppler_effect gives the heard pitch of a passing source, wavefront emissions and the Mach cone.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label, sampleAt } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const HALF = 200; // m of road either side of the listener
const C = 343; // speed of sound sent to the engine (m/s)

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let data = null, simT = 0;

    const vs = slider({ label: "Source speed", min: 1, max: 700, step: 1, value: 40, unit: "m/s", onInput: () => recompute() });
    const f = slider({ label: "Siren frequency", min: 100, max: 2000, step: 10, value: 700, unit: "Hz", onInput: () => recompute() });
    const d = slider({ label: "Listener distance from the road", min: 2, max: 100, step: 1, value: 25, unit: "m", onInput: () => recompute() });
    const out = readouts([
      { key: "a", label: "Pitch while approaching" }, { key: "r", label: "Pitch while receding" }, { key: "s", label: "Drop in pitch" },
      { key: "m", label: "Mach number" }, { key: "now", label: "Heard right now" },
    ]);
    L.side.append(
      panel("Drive-by", vs.root, f.root, d.root, el("p", { class: "note" }, "Waves bunch up ahead of a moving source and spread out behind it. Past 343 m/s the source outruns its own sound: a Mach cone (sonic boom).")),
      panel("Sound (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { simT = t; draw(); graph.setCursor(t); upd(); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "Pitch heard by the listener", xLabel: "time (s)", yLabel: "frequency (Hz)", height: 140 });

    const recompute = liveRequest((signal) => simulate("physics", "doppler_effect", {
      frequency: f.value, source_speed: vs.value, sound_speed: C, pass_distance: d.value, track_half_length: HALF, n_points: 1200,
      n_wavefronts: Math.round(Math.min(300, Math.max(20, (2 * HALF / vs.value) * 12))),
    }, signal), {
      delay: 40, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); data = r;
        const x = r.result;
        out.set("a", x.approaching_frequency ? `${fmt(x.approaching_frequency, 4)} Hz` : "— (supersonic: silent until the cone passes)");
        out.set("r", `${fmt(x.receding_frequency, 4)} Hz`);
        out.set("s", x.pitch_drop_semitones ? `${fmt(x.pitch_drop_semitones, 3)} semitones` : "—");
        out.set("m", `${fmt(x.mach_number, 3)}${x.supersonic ? ` (cone half-angle ${fmt(x.mach_cone_half_angle_deg, 3)}°)` : ""}`);
        const db = r.drive_by, cap = (y) => Math.min(y, 6 * f.value);
        if (db.boom_index === null) {
          graph.setSeries([{ name: "heard", color: c1, x: db.arrival_time, y: db.heard_frequency }]);
        } else {
          // Supersonic: two sounds after the boom — the approach sound (heard backwards) and the departing one
          const k = db.boom_index, early = [...db.arrival_time.slice(0, k + 1)].reverse(), earlyF = [...db.heard_frequency.slice(0, k + 1)].reverse();
          graph.setSeries([
            { name: "approach sound (arrives time-reversed)", color: c1, x: early, y: earlyF.map(cap) },
            { name: "departing sound", color: c2, x: db.arrival_time.slice(k), y: db.heard_frequency.slice(k).map(cap) },
          ]);
        }
        const T = db.arrival_time[db.arrival_time.length - 1];
        player.load(T, Math.min(T, 14));
        upd();
      },
    });

    function upd() {
      if (!data) return;
      const db = data.drive_by;
      if (db.boom_index === null) {
        out.set("now", simT < db.arrival_time[0] ? "silence (sound not here yet)" : `${fmt(sampleAt(db.arrival_time, db.heard_frequency, simT), 4)} Hz`);
      } else if (simT < db.boom_time) {
        out.set("now", "silence — the Mach cone hasn't arrived");
      } else {
        out.set("now", Math.abs(simT - db.boom_time) < 0.05 ? "BOOM!" : `${fmt(sampleAt(db.arrival_time.slice(db.boom_index), db.heard_frequency.slice(db.boom_index), simT), 4)} Hz (plus the approach sound)`);
      }
    }

    function draw() {
      const { ctx, width: W, height: H } = stage;
      if (!W) return;
      ctx.fillStyle = "#eef3f0"; ctx.fillRect(0, 0, W, H);
      if (!data) return;
      const db = data.drive_by, c = C;
      const s = (W - 40) / (2 * HALF), X = (x) => W / 2 + x * s, roadY = H * 0.35, Y = (y) => roadY + y * s;
      ctx.fillStyle = "#5b6270"; ctx.fillRect(0, roadY - 14, W, 28);
      ctx.setLineDash([16, 12]); ctx.strokeStyle = "#e3e8ef"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, roadY); ctx.lineTo(W, roadY); ctx.stroke(); ctx.setLineDash([]);
      // Wavefronts: emitted by the engine at (x_e, 0) at time t_e; radius c (t − t_e)
      const te = db.wavefronts.time, xe = db.wavefronts.x;
      ctx.lineWidth = 1.5;
      te.forEach((t0, i) => {
        if (t0 > simT) return;
        const rad = c * (simT - t0) * s;
        ctx.strokeStyle = `rgba(42,120,214,${Math.max(0.1, 0.8 - rad / W)})`;
        ctx.beginPath(); ctx.arc(X(xe[i]), roadY, rad, 0, Math.PI * 2); ctx.stroke();
      });
      const sx = sampleAt(db.emission_time, db.source_x, Math.min(simT, db.duration));
      if (simT <= db.duration) {
        ctx.fillStyle = "#e34948"; ctx.beginPath(); ctx.roundRect(X(sx) - 20, roadY - 10, 40, 20, 5); ctx.fill();
        ctx.fillStyle = "#5598e7"; ctx.fillRect(X(sx) - 6, roadY - 14, 12, 5);
      }
      // Listener
      const lx = X(0), ly = Y(d.value);
      ctx.fillStyle = "#16202c"; ctx.beginPath(); ctx.arc(lx, ly - 10, 7, 0, Math.PI * 2); ctx.fill(); ctx.fillRect(lx - 5, ly - 3, 10, 18);
      label(ctx, "listener", lx, ly + 28, { align: "center", font: "12px system-ui" });
      label(ctx, "wavefronts drawn from the engine's emission points", W - 12, H - 12, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
