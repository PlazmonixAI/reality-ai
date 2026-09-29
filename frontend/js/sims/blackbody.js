// Blackbody Spectrum: physics.blackbody gives Planck curves, Wien peak, Stefan-Boltzmann power.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, legend, SERIES } from "../core/ui.js";
import { createStage, label, niceStep } from "../core/stage.js";
import { fmt } from "../core/format.js";
import { wavelengthRGB } from "./interference.js";

const OBJECTS = { custom: ["Custom", null], sun: ["The Sun", 5778], bulb: ["Incandescent bulb", 2800], lava: ["Lava", 1400], earth: ["Earth", 288], sirius: ["Sirius", 9940], rigel: ["Rigel", 12100], betelgeuse: ["Betelgeuse", 3600] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2] = SERIES();
    let cur = null, ref = null;

    const obj = select({ label: "Object", value: "sun", options: Object.entries(OBJECTS).map(([v, [l, t]]) => ({ value: v, label: t ? `${l} (${t} K)` : l })), onChange: (v) => { if (OBJECTS[v][1]) temp.set(OBJECTS[v][1]); recompute(); } });
    const temp = slider({ label: "Temperature", min: 250, max: 15000, value: 5778, log: true, unit: "K", digits: 4, onInput: () => { obj.set("custom"); recompute(); } });
    const out = readouts([{ key: "peak", label: "Peak wavelength (Wien)" }, { key: "p", label: "Power per m² (σT⁴)" }, { key: "vis", label: "Emitted as visible light" }]);
    L.side.append(
      panel("Blackbody", obj.root, temp.root, legend([{ label: "this temperature", color: c1 }, { label: "the Sun (5778 K)", color: c2, dash: true }])),
      panel("Radiation (from the engine)", out.root, el("p", { class: "note" }, "Hotter bodies glow brighter (∝ T⁴) and bluer (peak ∝ 1/T).")),
    );
    simulate("physics", "blackbody", { temperature: 5778, wl_min_nm: 100, wl_max_nm: 3000 }).then((r) => { ref = r; draw(); });

    const recompute = liveRequest((signal) => {
      const t = temp.value, top = Math.min(30000, Math.max(3000, 4 * 2.898e6 / t));
      return simulate("physics", "blackbody", { temperature: t, wl_min_nm: 100, wl_max_nm: top, n_points: 800 }, signal);
    }, {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); cur = r;
        out.set("peak", `${fmt(r.result.peak_wavelength_nm, 4)} nm`);
        out.set("p", `${fmt(r.result.total_power_per_area, 3)} W/m²`);
        out.set("vis", `${fmt(r.result.visible_fraction * 100, 3)} %`);
        draw();
      },
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      if (!cur) return;
      const wl = cur.spectrum.wavelength_nm, b = cur.spectrum.radiance;
      const x1 = wl[wl.length - 1], ymax = Math.max(...b) * 1.12;
      const left = 60, right = w - 150, top = 24, bottom = h - 40;
      const X = (v) => left + (v / x1) * (right - left), Y = (v) => bottom - (v / ymax) * (bottom - top);
      // Visible band
      for (let nm = 380; nm <= 750; nm += 2) { if (X(nm) > right) break; ctx.fillStyle = `rgba(${wavelengthRGB(nm).join(",")},.25)`; ctx.fillRect(X(nm), top, X(nm + 2) - X(nm) + 1, bottom - top); }
      ctx.strokeStyle = "#e3e8ef";
      const xs = niceStep(x1, 8);
      for (let v = 0; v <= x1; v += xs) { ctx.beginPath(); ctx.moveTo(X(v), top); ctx.lineTo(X(v), bottom); ctx.stroke(); label(ctx, fmt(v, 4), X(v), bottom + 14, { align: "center", font: "11px system-ui", color: "#4b5868" }); }
      label(ctx, "wavelength (nm)", right, bottom + 30, { align: "right", font: "11px system-ui", color: "#7b8796" });
      label(ctx, "spectral radiance (relative)", left, 12, { font: "11px system-ui", color: "#7b8796" });
      if (ref) {
        const rb = ref.spectrum.radiance, rw = ref.spectrum.wavelength_nm;
        ctx.strokeStyle = c2; ctx.lineWidth = 2; ctx.setLineDash([6, 5]); ctx.beginPath();
        let started = false;
        rw.forEach((v, i) => { if (v > x1) return; const yy = Math.max(top, Y(rb[i])); if (started) ctx.lineTo(X(v), yy); else { ctx.moveTo(X(v), yy); started = true; } });
        ctx.stroke(); ctx.setLineDash([]);
      }
      ctx.strokeStyle = c1; ctx.lineWidth = 3; ctx.beginPath(); wl.forEach((v, i) => (i ? ctx.lineTo(X(v), Y(b[i])) : ctx.moveTo(X(v), Y(b[i])))); ctx.stroke();
      const pk = cur.result.peak_wavelength_nm;
      ctx.setLineDash([3, 3]); ctx.strokeStyle = "#16202c"; ctx.beginPath(); ctx.moveTo(X(pk), top); ctx.lineTo(X(pk), bottom); ctx.stroke(); ctx.setLineDash([]);
      label(ctx, `peak ${fmt(pk, 4)} nm`, X(pk) + 6, top + 12, { font: "bold 12px system-ui", halo: "#fff" });
      // Colour swatch: weight R, G, B by the radiance at 620 / 540 / 460 nm (display only).
      const at = (nm) => { let k = 0; while (k < wl.length - 1 && wl[k] < nm) k++; return b[k]; };
      const rgb = [at(620), at(540), at(460)], m = Math.max(...rgb);
      const col = rgb.map((v) => Math.round(255 * Math.pow(v / m, 0.45)));
      const sx = w - 75, sy = h / 2 - 20, rr = 46;
      const g = ctx.createRadialGradient(sx, sy, 4, sx, sy, rr * 1.6);
      g.addColorStop(0, `rgb(${col.join(",")})`); g.addColorStop(0.6, `rgba(${col.join(",")},.9)`); g.addColorStop(1, `rgba(${col.join(",")},0)`);
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(w - 140, top, 130, bottom - top);
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(sx, sy, rr * 1.6, 0, Math.PI * 2); ctx.fill();
      label(ctx, "apparent colour", sx, bottom - 12, { align: "center", font: "11px system-ui", color: "#c9ced6" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
