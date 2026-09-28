// Molecule Shapes: chemistry.molecule_shape gives VSEPR domains; we draw them in 3D and let you rotate.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, select, textInput, checkbox, readouts, el } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { fmt } from "../core/format.js";

const EXAMPLES = ["CO2", "BF3", "CH4", "NH3", "H2O", "SO2", "PCl5", "SF4", "ClF3", "XeF2", "SF6", "IF5", "XeF4", "NO3^-", "NH4^+", "SO4^2-"];
const COLORS = { H: "#f4f4f4", C: "#39424e", N: "#2a78d6", O: "#e34948", F: "#7cc76b", Cl: "#1baf7a", Br: "#a0522d", I: "#7e3fa3",
  S: "#e8c21d", P: "#eb6834", B: "#f0a8a8", Xe: "#3aa6b9", Se: "#c98500", Si: "#b8a47e", Be: "#9bd08f", Kr: "#5cb8d1", Al: "#a8b5c2", As: "#9b6ab5" };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    let res = null, yaw = 0.6, pitch = 0.35, drag = null, spin = true;

    const formula = textInput({ label: "Molecule or ion", value: "SF4", mono: true, onChange: () => recompute() });
    const example = select({ label: "Examples", value: "SF4", options: EXAMPLES.map((e) => ({ value: e, label: e })), onChange: (v) => { formula.set(v); recompute(); } });
    const real = checkbox({ label: "Lone pairs push harder (real angles)", value: false, onChange: () => draw() });
    const showLP = checkbox({ label: "Show lone pairs", value: true, onChange: () => draw() });
    const out = readouts([
      { key: "axe", label: "AXE notation" }, { key: "eg", label: "Electron geometry" }, { key: "mg", label: "Molecular geometry" },
      { key: "ideal", label: "Ideal bond angles" }, { key: "real", label: "With lone-pair repulsion" },
    ]);
    L.side.append(
      panel("Molecule", formula.root, example.root, el("p", { class: "note" }, "Charges as ^+, ^-, ^2-. One central atom; terminal H, halogens, O, S, N.")),
      panel("View", real.root, showLP.root, el("p", { class: "note" }, "Drag to rotate.")),
      panel("Shape (from the engine)", out.root),
    );

    const recompute = liveRequest((signal) => simulate("chemistry", "molecule_shape", { formula: formula.value.trim() }, signal), {
      delay: 250, onBusy: L.busy, onError: (e) => { L.error(e.message); },
      onResult: (r) => {
        L.clearError(); res = r;
        const x = r.result;
        out.set("axe", x.axe); out.set("eg", x.electron_geometry); out.set("mg", x.molecular_geometry);
        out.set("ideal", x.ideal_bond_angles.map((a) => `${fmt(a, 4)}°`).join(", "));
        out.set("real", x.compressed_bond_angles.map((a) => `${fmt(a, 4)}°`).join(", "));
        draw();
      },
    });

    stage.canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY }; spin = false; stage.canvas.setPointerCapture(e.pointerId); });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      yaw += (e.clientX - drag.x) * 0.01; pitch = Math.max(-1.5, Math.min(1.5, pitch + (e.clientY - drag.y) * 0.01));
      drag = { x: e.clientX, y: e.clientY }; draw();
    });
    stage.canvas.addEventListener("pointerup", () => { drag = null; });

    function project([x, y, z], s, cx, cy) {
      const x1 = x * Math.cos(yaw) + z * Math.sin(yaw), z1 = -x * Math.sin(yaw) + z * Math.cos(yaw);
      const y2 = y * Math.cos(pitch) - z1 * Math.sin(pitch), z2 = y * Math.sin(pitch) + z1 * Math.cos(pitch);
      const f = 1 / (1 - z2 * 0.18);
      return { x: cx + x1 * s * f, y: cy - y2 * s * f, z: z2, f };
    }
    function sphere(ctx, p, r, color) {
      const g = ctx.createRadialGradient(p.x - r * 0.35, p.y - r * 0.35, r * 0.1, p.x, p.y, r);
      g.addColorStop(0, "#fff"); g.addColorStop(0.25, color); g.addColorStop(1, shade(color));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill();
    }
    const shade = (hex) => { const n = parseInt(hex.slice(1), 16); return `rgb(${(n >> 16) * 0.45 | 0},${((n >> 8) & 255) * 0.45 | 0},${(n & 255) * 0.45 | 0})`; };

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      const bg = ctx.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, Math.max(w, h) * 0.7);
      bg.addColorStop(0, "#1f2a3c"); bg.addColorStop(1, "#0b1220");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      if (!res) return;
      const cx = w / 2, cy = h / 2, s = Math.min(w, h) * 0.3;
      const dirs = real.value ? res.domains.with_lone_pair_repulsion : res.domains.ideal;
      const kinds = res.domains.kinds;
      const terminals = Object.entries(res.terminals).flatMap(([el2, n]) => Array(n).fill(el2));
      const items = [];
      let t = 0;
      dirs.forEach((d, i) => {
        if (kinds[i] === "B") {
          const sym = terminals[t++] || "?";
          items.push({ kind: "bond", p: project(d, s, cx, cy), sym });
        } else if (showLP.value) items.push({ kind: "lp", p: project(d.map((v) => v * 0.62), s, cx, cy), d });
      });
      const centre = project([0, 0, 0], s, cx, cy);
      items.push({ kind: "centre", p: centre });
      items.sort((a, b) => a.p.z - b.p.z);
      for (const it of items) {
        if (it.kind === "bond") {
          ctx.strokeStyle = "#c9ced6"; ctx.lineWidth = 9 * it.p.f; ctx.lineCap = "round";
          ctx.beginPath(); ctx.moveTo(centre.x, centre.y); ctx.lineTo(it.p.x, it.p.y); ctx.stroke();
          sphere(ctx, it.p, 22 * it.p.f, COLORS[it.sym] || "#9aa6b5");
          label(ctx, it.sym, it.p.x, it.p.y, { align: "center", font: `bold ${Math.round(13 * it.p.f)}px system-ui`, color: it.sym === "H" ? "#16202c" : "#fff" });
        } else if (it.kind === "lp") {
          const g = ctx.createRadialGradient(it.p.x, it.p.y, 2, it.p.x, it.p.y, 34 * it.p.f);
          g.addColorStop(0, "rgba(235,104,52,.75)"); g.addColorStop(1, "rgba(235,104,52,0)");
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(it.p.x, it.p.y, 34 * it.p.f, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = "#fff"; for (const o of [-5, 5]) { ctx.beginPath(); ctx.arc(it.p.x + o, it.p.y, 2.5, 0, Math.PI * 2); ctx.fill(); }
        } else {
          const sym = res.result.central_atom || "A";
          sphere(ctx, it.p, 30 * it.p.f, COLORS[sym] || "#9aa6b5");
          label(ctx, sym, it.p.x, it.p.y, { align: "center", font: "bold 15px system-ui", color: "#fff" });
        }
      }
      label(ctx, `${formula.value}  ·  ${res.result.molecular_geometry}`, 14, 20, { font: "bold 15px system-ui", color: "#fff" });
      label(ctx, showLP.value && kinds.includes("L") ? "orange clouds = lone pairs" : "", w - 14, 20, { align: "right", font: "12px system-ui", color: "#c9ced6" });
    }

    const tick = setInterval(() => { if (spin) { yaw += 0.01; draw(); } }, 30);
    recompute();
    return () => { clearInterval(tick); recompute.cancel(); stage.destroy(); };
  },
};
