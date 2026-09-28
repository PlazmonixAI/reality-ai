// Wave Interference: physics.slit_interference gives the screen pattern and the near-slit wave field.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

/** Approximate visible colour for a wavelength in nm (display only). */
export function wavelengthRGB(nm) {
  let r = 0, g = 0, b = 0;
  if (nm < 440) { r = -(nm - 440) / 60; b = 1; }
  else if (nm < 490) { g = (nm - 440) / 50; b = 1; }
  else if (nm < 510) { g = 1; b = -(nm - 510) / 20; }
  else if (nm < 580) { r = (nm - 510) / 70; g = 1; }
  else if (nm < 645) { r = 1; g = -(nm - 645) / 65; }
  else r = 1;
  const f = nm < 420 ? 0.3 + 0.7 * (nm - 380) / 40 : nm > 700 ? 0.3 + 0.7 * (750 - nm) / 50 : 1;
  return [r, g, b].map((c) => Math.round(255 * Math.max(0, c * f) ** 0.8));
}

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const [c1] = SERIES();
    let data = null, phase = 0;
    let fieldImg = null;

    const lam = slider({ label: "Wavelength", min: 380, max: 750, step: 1, value: 532, unit: "nm", onInput: () => recompute() });
    const slits = select({ label: "Number of slits", value: "2", options: [1, 2, 3, 4, 5, 10, 20].map((n) => ({ value: String(n), label: n === 1 ? "1 (single slit)" : n === 2 ? "2 (double slit)" : `${n} (grating)` })), onChange: () => recompute() });
    const spacing = slider({ label: "Slit spacing d", min: 5, max: 500, step: 1, value: 60, unit: "µm", onInput: () => recompute() });
    const widthS = slider({ label: "Slit width a", min: 0, max: 100, step: 1, value: 12, unit: "µm", onInput: () => recompute() });
    const dist = slider({ label: "Screen distance", min: 0.2, max: 3, step: 0.05, value: 1, unit: "m", onInput: () => recompute() });
    const out = readouts([{ key: "fs", label: "Fringe spacing" }, { key: "cw", label: "Central max width" }, { key: "m1", label: "1st-order max at" }]);
    L.side.append(
      panel("Light", lam.root),
      panel("Barrier", slits.root, spacing.root, widthS.root, dist.root),
      panel("Pattern (from the engine)", out.root, el("p", { class: "note" }, "Left: the wave just past the slits (animated, not to scale). Right: what you'd see on the screen.")),
    );
    const graph = new LineGraph(L.bottom, { title: "Intensity on the screen", xLabel: "position on screen (mm)", yLabel: "relative intensity", height: 160, yRange: [0, 1.05] });

    const recompute = liveRequest((signal) => {
      const N = Number(slits.value);
      const a = widthS.value * 1e-6, d = Math.max(spacing.value * 1e-6, a + 1e-6);
      return simulate("physics", "slit_interference", {
        wavelength: lam.value * 1e-9, n_slits: N, slit_spacing: d, slit_width: N === 1 ? Math.max(a, 1e-6) : a,
        screen_distance: dist.value, n_points: 1201,
      }, signal);
    }, {
      onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (res) => {
        L.clearError(); data = res; fieldImg = null;
        const r = res.result;
        out.set("fs", r.fringe_spacing ? `${fmt(r.fringe_spacing * 1000, 4)} mm` : "—");
        out.set("cw", r.central_width ? `${fmt(r.central_width * 1000, 4)} mm` : "—");
        const m1 = r.maxima.filter((y) => y > 1e-12)[0];
        out.set("m1", m1 ? `${fmt(m1 * 1000, 4)} mm` : "—");
        graph.setSeries([{ name: "Intensity", color: c1, x: res.pattern.y.map((y) => y * 1000), y: res.pattern.intensity }]);
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      phase += dt * 2 * Math.PI * 0.8;
      ctx.fillStyle = "#0a0f1c"; ctx.fillRect(0, 0, w, h);
      if (!data) return;
      const rgb = wavelengthRGB(lam.value);
      const nf = data.near_field;
      const gx = nf.x.length, gy = nf.y.length;
      if (!fieldImg) fieldImg = { img: new ImageData(gx, gy), off: new OffscreenCanvas(gx, gy) };
      const cph = Math.cos(phase), sph = Math.sin(phase);
      const px = fieldImg.img.data;
      for (let j = 0; j < gy; j++) for (let i = 0; i < gx; i++) {
        const v = nf.re[j][i] * cph + nf.im[j][i] * sph;          // Re(A e^{-iωt})
        const s = Math.max(0, Math.min(1, 0.5 + 0.9 * v));
        const k = (j * gx + i) * 4;
        px[k] = rgb[0] * s; px[k + 1] = rgb[1] * s; px[k + 2] = rgb[2] * s; px[k + 3] = 255;
      }
      fieldImg.off.getContext("2d").putImageData(fieldImg.img, 0, 0);
      const fw = Math.round(w * 0.58), fx = 40;
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(fieldImg.off, fx, 0, fw, h);
      // Barrier with slits
      ctx.fillStyle = "#c9ced6"; ctx.fillRect(fx - 12, 0, 12, h);
      const ySpan = nf.y[gy - 1] - nf.y[0];
      ctx.fillStyle = "#0a0f1c";
      // In a compressed view the slits are drawn as narrow openings (the view treats them as point sources).
      const slitPx = Math.max(3, Math.min((Math.max(widthS.value * 1e-6, 1e-6) / ySpan) * h, nf.spacing_compressed ? 8 : h));
      for (const yc of nf.slits_y) {
        const y = h / 2 - (yc / ySpan) * h;
        ctx.fillRect(fx - 12, y - slitPx / 2, 12, slitPx);
      }
      // Incoming plane wave on the left of the barrier
      for (let x = 0; x < fx - 12; x += 2) {
        const s = 0.5 + 0.5 * Math.cos(phase - x * 0.25);
        ctx.fillStyle = `rgba(${rgb.join(",")},${0.2 + 0.6 * s})`; ctx.fillRect(x, 0, 2, h);
      }
      // Screen with the engine's intensity pattern
      const sx = fx + fw + 30, sw = w - sx - 20;
      const ys = data.pattern.y, I = data.pattern.intensity, n = ys.length;
      for (let j = 0; j < h; j++) {
        const k = Math.round((j / (h - 1)) * (n - 1));
        const b = I[n - 1 - k];
        ctx.fillStyle = `rgb(${rgb.map((c) => Math.round(c * Math.min(1, b) ** 0.7)).join(",")})`;
        ctx.fillRect(sx, j, sw, 1);
      }
      ctx.strokeStyle = "#39424e"; ctx.strokeRect(sx, 0, sw, h);
      label(ctx, "screen", sx + sw / 2, h - 12, { align: "center", color: "#c9ced6", font: "11px system-ui" });
      label(ctx, `${fmt(ys[n - 1] * 1000, 3)} mm`, sx - 6, 12, { align: "right", color: "#c9ced6", font: "11px system-ui" });
      label(ctx, `${fmt(ys[0] * 1000, 3)} mm`, sx - 6, h - 12, { align: "right", color: "#c9ced6", font: "11px system-ui" });
      label(ctx, `λ = ${lam.value} nm`, fx + 10, 18, { color: "#fff", font: "13px system-ui" });
      label(ctx, nf.spacing_compressed ? "Near-slit view: slit spacing drawn compressed (too many wavelengths to draw); screen pattern is exact"
        : `${fmt(ySpan * 1e6, 3)} µm tall, to scale`, fx + 10, h - 14, { color: "rgba(255,255,255,.7)", font: "11px system-ui", halo: "rgba(10,15,28,.7)" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); graph.destroy(); stage.destroy(); };
  },
};
