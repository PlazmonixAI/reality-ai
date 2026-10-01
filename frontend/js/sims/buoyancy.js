// Buoyancy: physics.buoyancy applies Archimedes' principle to a block in a liquid.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, readouts, el } from "../core/ui.js";
import { createStage, label, arrow } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";

// Typical densities (kg/m³) and display colours.
const BLOCKS = { cork: ["Cork", 240, "#c89b6a"], pine: ["Pine wood", 500, "#d9b27c"], ice: ["Ice", 917, "#d7eef8"], brick: ["Brick", 1900, "#b5543a"],
  aluminium: ["Aluminium", 2700, "#b8c4d3"], iron: ["Iron", 7870, "#6b6f76"], gold: ["Gold", 19300, "#e3b53a"] };
const LIQUIDS = { water: ["Fresh water", 998, "rgba(42,120,214,.35)"], sea: ["Sea water", 1025, "rgba(27,120,160,.4)"], oil: ["Olive oil", 911, "rgba(200,180,40,.4)"],
  honey: ["Honey", 1420, "rgba(230,150,20,.5)"], mercury: ["Mercury", 13534, "rgba(160,170,180,.75)"] };

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    let res = null, depthShown = null;

    const block = select({ label: "Block", value: "pine", options: Object.entries(BLOCKS).map(([v, [l, d]]) => ({ value: v, label: `${l} (${d} kg/m³)` })), onChange: () => recompute() });
    const liquid = select({ label: "Liquid", value: "water", options: Object.entries(LIQUIDS).map(([v, [l, d]]) => ({ value: v, label: `${l} (${d} kg/m³)` })), onChange: () => recompute() });
    const size = slider({ label: "Block edge", min: 5, max: 40, step: 1, value: 20, unit: "cm", onInput: () => recompute() });
    const load = slider({ label: "Weight placed on top", min: 0, max: 20, step: 0.1, value: 0, unit: "kg", onInput: () => recompute() });
    const out = readouts([
      { key: "s", label: "Floats?" }, { key: "f", label: "Fraction under the surface" }, { key: "b", label: "Buoyant force" },
      { key: "w", label: "Weight" }, { key: "a", label: "Apparent weight" }, { key: "c", label: "Extra load before sinking" },
    ]);
    L.side.append(
      panel("Tank", block.root, liquid.root, size.root, load.root, el("p", { class: "note" }, "The liquid pushes up with the weight of the liquid pushed aside. A floating block sinks just deep enough to displace its own weight.")),
      panel("Forces (from the engine)", out.root),
    );

    const recompute = liveRequest((signal) => simulate("physics", "buoyancy", {
      object_density: BLOCKS[block.value][1], volume: (size.value / 100) ** 3, fluid_density: LIQUIDS[liquid.value][1], added_mass: load.value,
    }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        out.set("s", res.floats ? "yes" : "no, it sinks"); out.set("f", `${fmt(res.fraction_submerged * 100, 4)} %`);
        out.set("b", `${fmt(res.buoyant_force, 4)} N`); out.set("w", `${fmt(res.weight, 4)} N`);
        out.set("a", `${fmt(res.apparent_weight, 4)} N`); out.set("c", `${fmt(res.extra_load_capacity, 4)} kg`);
      },
    });

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f7f9fc"; ctx.fillRect(0, 0, w, h);
      const tx = w * 0.18, tw = w * 0.5, top = 60, bottom = h - 30, surf = top + (bottom - top) * 0.3;
      ctx.fillStyle = LIQUIDS[liquid.value][2]; ctx.fillRect(tx, surf, tw, bottom - surf);
      ctx.strokeStyle = "#39424e"; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(tx, top); ctx.lineTo(tx, bottom); ctx.lineTo(tx + tw, bottom); ctx.lineTo(tx + tw, top); ctx.stroke();
      if (!res) return;
      const px = Math.min(tw * 0.5, (bottom - surf) * 0.8) * (size.value / 40), bx = tx + tw / 2 - px / 2;
      // Target: floating → top at surf − (1 − f)·px; sinking → resting on the floor. Ease toward it (display only).
      const target = res.floats ? surf - (1 - res.fraction_submerged) * px : bottom - px - 2;
      depthShown = depthShown === null ? target : depthShown + (target - depthShown) * Math.min(1, dt * 3);
      const by = depthShown;
      ctx.fillStyle = BLOCKS[block.value][2]; ctx.fillRect(bx, by, px, px);
      ctx.strokeStyle = "rgba(0,0,0,.35)"; ctx.lineWidth = 1.5; ctx.strokeRect(bx, by, px, px);
      if (load.value > 0) { ctx.fillStyle = "#39424e"; const lw = Math.min(px, 20 + load.value * 3); ctx.fillRect(bx + px / 2 - lw / 2, by - 16, lw, 16); label(ctx, `${fmt(load.value, 3)} kg`, bx + px / 2, by - 26, { align: "center", font: "11px system-ui" }); }
      // Force arrows (length ∝ force, shared scale)
      const scale = 90 / Math.max(res.weight, res.buoyant_force, 1e-9);
      arrow(ctx, bx + px + 30, by + px / 2, bx + px + 30, by + px / 2 + res.weight * scale, "#e34948", 4, 10);
      label(ctx, `weight ${fmt(res.weight, 3)} N`, bx + px + 40, by + px / 2 + res.weight * scale - 6, { color: "#e34948", font: "12px system-ui" });
      arrow(ctx, bx - 30, by + px / 2, bx - 30, by + px / 2 - res.buoyant_force * scale, "#1baf7a", 4, 10);
      label(ctx, `buoyancy ${fmt(res.buoyant_force, 3)} N`, bx - 40, by + px / 2 - res.buoyant_force * scale + 6, { align: "right", color: "#1baf7a", font: "12px system-ui" });
      label(ctx, LIQUIDS[liquid.value][0], tx + 10, bottom - 14, { font: "12px system-ui", color: "#16202c" });
    });

    recompute();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
