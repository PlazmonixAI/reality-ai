// Fractal Explorer: mathematics.fractal computes escape-time images of the Mandelbrot and Julia sets.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, segmented, readouts, el, button } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";

// Colour map for display only: smooth escape count → palette; inside = near-black.
const STOPS = [[15, 26, 43], [42, 120, 214], [235, 242, 250], [235, 104, 52], [120, 30, 20]];
function palette(t) {
  const u = (t % 1) * (STOPS.length - 1), i = Math.floor(u), f = u - i, a = STOPS[i], b = STOPS[(i + 1) % STOPS.length];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: () => recompute() });
    let img = null, res = null, view = { re: -0.75, im: 0, width: 3.5 };
    const off = document.createElement("canvas");

    const kind = segmented({ label: "Set", value: "mandelbrot", options: [{ value: "mandelbrot", label: "Mandelbrot" }, { value: "julia", label: "Julia" }], onChange: () => { reset(); } });
    const click = segmented({ label: "Clicking the picture", value: "zoom", options: [{ value: "zoom", label: "Zooms in ×3" }, { value: "pick", label: "Picks Julia c" }], onChange: () => {} });
    const cre = slider({ label: "Julia c (real part)", min: -2, max: 1, step: 0.001, value: -0.8, onInput: () => { if (kind.value === "julia") recompute(); } });
    const cim = slider({ label: "Julia c (imaginary part)", min: -1.5, max: 1.5, step: 0.001, value: 0.156, onInput: () => { if (kind.value === "julia") recompute(); } });
    const iters = slider({ label: "Max iterations", min: 50, max: 2000, step: 50, value: 250, onInput: () => recompute() });
    const out = readouts([{ key: "c", label: "View centre" }, { key: "w", label: "View width" }, { key: "in", label: "Pixels inside the set" }, { key: "j", label: "Julia set connected?" }]);
    function reset() { view = kind.value === "mandelbrot" ? { re: -0.75, im: 0, width: 3.5 } : { re: 0, im: 0, width: 3.4 }; recompute(); }
    L.side.append(
      panel("Explore", kind.root, click.root, cre.root, cim.root, iters.root, button("Reset view", reset), button("Zoom out ×3", () => { view.width = Math.min(20, view.width * 3); recompute(); }),
        el("p", { class: "note" }, "Pick c inside the Mandelbrot set and its Julia set is one connected piece; outside it shatters into dust. Right-click zooms out.")),
      panel("Image (from the engine)", out.root),
    );

    const recompute = liveRequest((signal) => {
      const { width: w, height: h } = stage;
      const scale = Math.min(1, Math.sqrt(300000 / Math.max(1, w * h)));
      const px = Math.max(16, Math.round(w * scale)), py = Math.max(16, Math.round(h * scale));
      return simulate("mathematics", "fractal", { kind: kind.value, center_re: view.re, center_im: view.im, width: view.width, pixels_x: px, pixels_y: py, max_iter: iters.value, c_re: cre.value, c_im: cim.value }, signal);
    }, {
      delay: 80, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r;
        const im = r.image, bytes = Uint8Array.from(atob(im.data), (ch) => ch.charCodeAt(0));
        const vals = new Uint16Array(bytes.buffer), data = new ImageData(im.width, im.height);
        for (let i = 0; i < vals.length; i++) {
          const v = vals[i], o = 4 * i;
          const [cr, cg, cb] = v === 65535 ? [8, 12, 20] : palette(Math.sqrt(v / 16) / 6);
          data.data[o] = cr; data.data[o + 1] = cg; data.data[o + 2] = cb; data.data[o + 3] = 255;
        }
        off.width = im.width; off.height = im.height; off.getContext("2d").putImageData(data, 0, 0); img = true;
        const x = r.result;
        out.set("c", `${fmt(view.re, 8)} ${view.im >= 0 ? "+" : "−"} ${fmt(Math.abs(view.im), 8)}i`); out.set("w", fmt(view.width, 4));
        out.set("in", `${fmt(x.fraction_inside * 100, 3)} %`);
        out.set("j", x.julia ? (x.julia.connected ? "yes (c is in the Mandelbrot set)" : "no, Cantor dust") : "–");
        draw();
      },
    });

    const toC = (e) => {
      const b = stage.canvas.getBoundingClientRect(), fx = (e.clientX - b.left) / b.width - 0.5, fy = (e.clientY - b.top) / b.height - 0.5;
      return [view.re + fx * view.width, view.im - fy * view.width * (b.height / b.width)];
    };
    stage.canvas.addEventListener("click", (e) => {
      const [re, im] = toC(e);
      if (click.value === "pick" && kind.value === "mandelbrot") { cre.set(re); cim.set(im); kind.set("julia"); click.set("zoom"); reset(); return; }
      view = { re, im, width: view.width / 3 }; recompute();
    });
    stage.canvas.addEventListener("contextmenu", (e) => { e.preventDefault(); view.width = Math.min(20, view.width * 3); recompute(); });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#08101c"; ctx.fillRect(0, 0, w, h);
      if (!img) return;
      ctx.imageSmoothingEnabled = true; ctx.drawImage(off, 0, 0, w, h);
      label(ctx, kind.value === "julia" ? `Julia set, c = ${fmt(cre.value, 4)} ${cim.value >= 0 ? "+" : "−"} ${fmt(Math.abs(cim.value), 4)}i` : "Mandelbrot set", 12, 16, { color: "#fff", font: "bold 13px system-ui" });
      label(ctx, "colours are a display palette for the engine's escape counts", w - 10, h - 10, { align: "right", color: "#c9ced6", font: "11px system-ui" });
    }

    recompute();
    return () => { recompute.cancel(); stage.destroy(); };
  },
};
