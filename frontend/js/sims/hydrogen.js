// Hydrogen Atom: physics.hydrogen_spectrum gives the energy levels and every emission line.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, readouts, el } from "../core/ui.js";
import { createStage, label, arrow } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";
import { wavelengthRGB } from "./interference.js";

const SERIES_COLORS = { Lyman: "#4a3aa7", Balmer: "#1baf7a", Paschen: "#e34948", Brackett: "#eb6834", Pfund: "#eda100", Humphreys: "#7b8796" };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    let res = null, phase = 0, flash = 0;

    const up = slider({ label: "Electron starts in level n", min: 2, max: 7, step: 1, value: 3, onInput: () => { if (low.value >= up.value) low.set(up.value - 1); recompute(); } });
    const low = slider({ label: "…and drops to level n", min: 1, max: 6, step: 1, value: 2, onInput: () => { if (low.value >= up.value) up.set(low.value + 1); recompute(); } });
    const out = readouts([
      { key: "series", label: "Series" }, { key: "wl", label: "Wavelength" }, { key: "e", label: "Photon energy" },
      { key: "f", label: "Frequency" }, { key: "ion", label: "Ionisation energy" },
    ]);
    L.side.append(
      panel("Transition", up.root, low.root, el("p", { class: "note" }, "Balmer lines (drops to n = 2) are the visible ones: red H-α, blue-green H-β, violet H-γ and H-δ.")),
      panel("Photon (from the engine)", out.root),
    );

    const recompute = liveRequest((signal) => simulate("physics", "hydrogen_spectrum", { n_upper: up.value, n_lower: low.value, n_max: 7 }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r; flash = 1;
        const x = r.result;
        out.set("series", x.series); out.set("wl", `${fmt(x.wavelength_nm, 5)} nm${x.wavelength_nm < 380 ? " (ultraviolet)" : x.wavelength_nm > 750 ? " (infrared)" : " (visible)"}`);
        out.set("e", `${fmt(x.energy_ev, 5)} eV`); out.set("f", `${fmt(x.frequency_hz, 4)} Hz`); out.set("ion", `${fmt(x.ionisation_energy_ev, 5)} eV`);
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      phase += dt; flash = Math.max(0, flash - dt * 0.6);
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      // Energy level diagram (left half)
      const lx0 = 40, lx1 = w * 0.42, top = 30, bottom = h - 120;
      const emin = res.levels[0].energy_ev;
      const Y = (e) => top + (e / emin) * (bottom - top);
      let lastY = Infinity;
      for (const lv of res.levels) {
        const on = lv.n === up.value || lv.n === low.value;
        ctx.strokeStyle = on ? "#fff" : "rgba(201,206,214,.45)"; ctx.lineWidth = on ? 2.5 : 1.5;
        ctx.beginPath(); ctx.moveTo(lx0 + 40, Y(lv.energy_ev)); ctx.lineTo(lx1, Y(lv.energy_ev)); ctx.stroke();
        // Upper levels crowd together; label only those with room (or the selected ones).
        if (on || lastY - Y(lv.energy_ev) > 13) {
          label(ctx, `n=${lv.n}`, lx0, Y(lv.energy_ev), { color: "#c9ced6", font: "12px system-ui" });
          label(ctx, `${fmt(lv.energy_ev, 3)} eV`, lx1 + 6, Y(lv.energy_ev), { color: "#7b8796", font: "11px system-ui" });
          lastY = Y(lv.energy_ev);
        }
      }
      const x = res.result;
      const col = x.wavelength_nm >= 380 && x.wavelength_nm <= 750 ? `rgb(${wavelengthRGB(x.wavelength_nm).join(",")})` : SERIES_COLORS[x.series] || "#fff";
      const lu = res.levels[up.value - 1], ll = res.levels[low.value - 1];  // a typed level the engine has not computed yet is skipped
      if (lu && ll) arrow(ctx, (lx0 + lx1) / 2 + 20, Y(lu.energy_ev), (lx0 + lx1) / 2 + 20, Y(ll.energy_ev), col, 4, 12);
      // Bohr picture (right)
      const cx = w * 0.74, cy = (top + bottom) / 2, s = Math.min(w * 0.22, (bottom - top) / 2) / Math.sqrt(res.levels[6].orbit_radius_nm);
      for (const lv of res.levels) {
        const r = Math.sqrt(lv.orbit_radius_nm) * s;
        ctx.strokeStyle = lv.n === up.value || lv.n === low.value ? "rgba(255,255,255,.7)" : "rgba(201,206,214,.2)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
      }
      label(ctx, "n → ∞ (0 eV)", lx0 + 40, top - 12, { color: "#7b8796", font: "11px system-ui" });
      ctx.fillStyle = "#e34948"; ctx.beginPath(); ctx.arc(cx, cy, 6, 0, Math.PI * 2); ctx.fill();
      const nNow = flash > 0.5 ? up.value : low.value, rNow = Math.sqrt(res.levels[nNow - 1].orbit_radius_nm) * s, a = phase * 2 / nNow;
      ctx.fillStyle = "#5598e7"; ctx.beginPath(); ctx.arc(cx + rNow * Math.cos(a), cy + rNow * Math.sin(a), 6, 0, Math.PI * 2); ctx.fill();
      if (flash > 0 && flash < 0.5) {
        ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.beginPath();
        const d = (0.5 - flash) * 400;
        for (let k = 0; k < 60; k++) { const px = cx + rNow + d + k * 3; ctx.lineTo(px, cy + 8 * Math.sin(k * 0.8)); }
        ctx.stroke();
      }
      label(ctx, "orbits not to scale (radius ∝ n²)", cx, bottom + 16, { align: "center", color: "#7b8796", font: "11px system-ui" });
      // Spectrum strip with all lines, current one highlighted
      const sy = h - 70, sx0 = 40, sx1 = w - 40, wmin = 80, wmax = 2000;
      const SX = (nm) => sx0 + (Math.log(nm / wmin) / Math.log(wmax / wmin)) * (sx1 - sx0);
      for (let nm = 380; nm <= 750; nm += 3) { ctx.fillStyle = `rgba(${wavelengthRGB(nm).join(",")},.25)`; ctx.fillRect(SX(nm), sy, SX(nm + 3) - SX(nm) + 1, 36); }
      ctx.strokeStyle = "rgba(201,206,214,.4)"; ctx.strokeRect(sx0, sy, sx1 - sx0, 36);
      for (const ln of res.lines) {
        if (ln.wavelength_nm < wmin || ln.wavelength_nm > wmax) continue;
        const cur = ln.n_upper === up.value && ln.n_lower === low.value;
        ctx.strokeStyle = cur ? "#fff" : SERIES_COLORS[ln.series]; ctx.lineWidth = cur ? 3 : 1.5;
        ctx.beginPath(); ctx.moveTo(SX(ln.wavelength_nm), sy); ctx.lineTo(SX(ln.wavelength_nm), sy + 36); ctx.stroke();
      }
      for (const nm of [100, 200, 500, 1000, 2000]) label(ctx, `${nm} nm`, SX(nm), sy + 50, { align: "center", color: "#7b8796", font: "11px system-ui" });
      Object.entries(SERIES_COLORS).slice(0, 4).forEach(([name, c], i) => label(ctx, `■ ${name}`, sx0 + i * 90, sy - 12, { color: c, font: "11px system-ui" }));
    });

    recompute();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
