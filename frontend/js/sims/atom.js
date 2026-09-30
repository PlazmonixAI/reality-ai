// Build an Atom: chemistry.atom_builder identifies the element, ion, stability and electron shells.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, readouts, el, button } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { animationLoop } from "../core/player.js";
import { fmt } from "../core/format.js";

// Layout of the first 20 elements in the periodic table (symbol, period, group) for the mini table.
const TABLE = "H 1 1,He 1 18,Li 2 1,Be 2 2,B 2 13,C 2 14,N 2 15,O 2 16,F 2 17,Ne 2 18,Na 3 1,Mg 3 2,Al 3 13,Si 3 14,P 3 15,S 3 16,Cl 3 17,Ar 3 18,K 4 1,Ca 4 2"
  .split(",").map((s) => { const [sym, p, g] = s.split(" "); return { sym, p: +p, g: +g }; });

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene);
    const counts = { p: 1, n: 0, e: 1 };
    let res = null, phase = 0;

    const counter = (key, name) => {
      const val = el("strong", { style: "min-width:28px;text-align:center" }, "0");
      const row = el("div", { class: "btn-row control", style: "align-items:center" },
        el("span", { style: "flex:1;font-weight:600" }, name),
        button("−", () => { counts[key] = Math.max(0, counts[key] - 1); refresh(); }),
        val,
        button("+", () => { counts[key] = Math.min(key === "p" ? 20 : 30, counts[key] + 1); refresh(); }, "primary"));
      return { row, val };
    };
    const P = counter("p", "Protons"), N = counter("n", "Neutrons"), E = counter("e", "Electrons");
    const out = readouts([
      { key: "el", label: "Element" }, { key: "mass", label: "Mass number" }, { key: "charge", label: "Net charge" },
      { key: "stable", label: "Nucleus" }, { key: "cfg", label: "Electron configuration" }, { key: "be", label: "Binding energy" },
    ]);
    const tableBox = el("div", { style: "display:grid;grid-template-columns:repeat(18,1fr);gap:2px;font-size:10px" });
    L.side.append(
      panel("Particles", P.row, N.row, E.row, el("p", { class: "note" }, "Up to 20 protons (hydrogen to calcium).")),
      panel("Your atom (from the engine)", out.root),
      panel("Periodic table", tableBox),
    );

    function refresh() {
      P.val.textContent = counts.p; N.val.textContent = counts.n; E.val.textContent = counts.e;
      recompute();
    }

    const recompute = liveRequest((signal) => simulate("chemistry", "atom_builder", { protons: counts.p, neutrons: counts.n, electrons: counts.e }, signal), {
      delay: 40, onBusy: L.busy, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = r.result;
        out.set("el", res.element ? `${res.element.name} (${res.element.symbol})` : "no protons");
        out.set("mass", String(res.mass_number));
        out.set("charge", res.charge === 0 ? "0 (neutral atom)" : `${res.charge > 0 ? "+" : ""}${res.charge} (ion)`);
        out.set("stable", res.stable_nucleus === null ? "–" : res.stable_nucleus ? "stable" : "unstable (radioactive)");
        out.set("cfg", res.electron_configuration || "–");
        out.set("be", r.binding_energy.total ? `${fmt(r.binding_energy.total, 4)} MeV (${fmt(r.binding_energy.per_nucleon, 3)} per nucleon)` : "–");
        tableBox.replaceChildren(...TABLE.map((t) => el("div", {
          style: `grid-column:${t.g};grid-row:${t.p};padding:3px 0;text-align:center;border-radius:4px;` +
            (res.element && res.element.symbol === t.sym ? "background:#2a78d6;color:#fff;font-weight:700" : "background:#eef2f7"),
        }, t.sym)));
      },
    });

    // Nucleon positions: a compact golden-angle spiral so the nucleus stays round as it grows.
    function nucleons() {
      const list = [];
      const total = counts.p + counts.n;
      for (let i = 0; i < total; i++) {
        const r = 7 * Math.sqrt(i), a = i * 2.39996;
        // interleave protons and neutrons
        const isP = Math.round(((i + 1) * counts.p) / Math.max(1, total)) > Math.round((i * counts.p) / Math.max(1, total));
        list.push({ x: r * Math.cos(a), y: r * Math.sin(a), p: isP });
      }
      return list;
    }

    const stop = animationLoop((dt) => {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      phase += dt;
      ctx.fillStyle = "#0f1a2b"; ctx.fillRect(0, 0, w, h);
      const cx = w * 0.45, cy = h / 2;
      const shells = res ? res.shells : [];
      const base = Math.min(w, h) * 0.13, gap = Math.min(w, h) * 0.1;
      shells.forEach((n, k) => {
        const r = base + gap * k;
        ctx.strokeStyle = "rgba(201,206,214,.35)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
        for (let j = 0; j < n; j++) {
          const a = (j / n) * Math.PI * 2 + phase * (0.6 / (k + 1));
          ctx.fillStyle = "#5598e7"; ctx.beginPath(); ctx.arc(cx + r * Math.cos(a), cy + r * Math.sin(a), 6, 0, Math.PI * 2); ctx.fill();
        }
      });
      for (const nuc of nucleons()) {
        ctx.fillStyle = nuc.p ? "#e34948" : "#9aa6b5";
        ctx.strokeStyle = "rgba(0,0,0,.35)"; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(cx + nuc.x, cy + nuc.y, 6.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      }
      if (res && res.element) {
        const x = w - 130, y = 40;
        ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.roundRect(x, y, 110, 120, 10); ctx.fill();
        label(ctx, String(res.mass_number), x + 14, y + 22, { font: "bold 14px system-ui" });
        label(ctx, String(counts.p), x + 14, y + 100, { font: "bold 14px system-ui" });
        label(ctx, res.element.symbol, x + 60, y + 62, { align: "center", font: "bold 44px system-ui" });
        if (res.charge) label(ctx, `${Math.abs(res.charge) > 1 ? Math.abs(res.charge) : ""}${res.charge > 0 ? "+" : "−"}`, x + 100, y + 22, { align: "right", font: "bold 14px system-ui", color: "#c93a3a" });
        label(ctx, res.stable_nucleus ? "stable" : "unstable", x + 55, y + 138, { align: "center", font: "12px system-ui", color: res.stable_nucleus ? "#7fe0b5" : "#ff9a9a" });
      }
      label(ctx, "red = proton · grey = neutron · blue = electron", 14, h - 14, { font: "11px system-ui", color: "#c9ced6" });
    });

    refresh();
    return () => { stop(); recompute.cancel(); stage.destroy(); };
  },
};
