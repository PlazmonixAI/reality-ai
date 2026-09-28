// Shortest Paths & Spanning Trees: mathematics.shortest_path (Dijkstra) and minimum_spanning_tree (Kruskal).
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, segmented, readouts, el, button, SERIES } from "../core/ui.js";
import { createStage, label } from "../core/stage.js";
import { Player } from "../core/player.js";
import { fmt } from "../core/format.js";

// A fixed map of towns (positions in km) — input data for the algorithms.
const NODES = {
  A: [1, 2], B: [3, 1], C: [5.5, 1.5], D: [8, 1], E: [2, 4.5], F: [4.5, 4], G: [6.5, 4.5], H: [9, 3.5],
  I: [1, 7], J: [3.5, 6.5], K: [6, 7], L: [8.5, 6.5], M: [4.5, 9], N: [7.5, 9],
};
const LINKS = ["AB", "AE", "BC", "BF", "CD", "CF", "CG", "DH", "DG", "EF", "EI", "EJ", "FG", "FJ", "GH", "GK", "HL", "IJ", "IM", "JK", "JM", "KL", "KN", "LN", "MN", "FK"];

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const [c1, c2, c3] = SERIES();
    let src = "A", dst = "N", res = null, step = 1e9, seed = 0;
    let edges = [];

    function makeEdges() {
      let s = seed * 9973 + 7; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
      edges = LINKS.map(([u, v]) => {
        const [x1, y1] = NODES[u], [x2, y2] = NODES[v], d = Math.hypot(x2 - x1, y2 - y1);
        return [u, v, Math.round((seed ? d * (0.5 + 1.5 * rnd()) : d) * 10) / 10];
      });
    }
    const mode = segmented({ label: "Algorithm", value: "path", options: [{ value: "path", label: "Shortest path (Dijkstra)" }, { value: "mst", label: "Spanning tree (Kruskal)" }], onChange: () => recompute() });
    const out = readouts([{ key: "d", label: "Result" }, { key: "p", label: "Route / edges" }, { key: "n", label: "Steps" }]);
    L.side.append(
      panel("Road network", mode.root, button("Random road lengths (traffic!)", () => { seed += 1; makeEdges(); recompute(); }), button("True distances", () => { seed = 0; makeEdges(); recompute(); }),
        el("p", { class: "note" }, "Click a town to start from it, then another to go to it. Numbers on roads are lengths in km.")),
      panel("Answer (from the engine)", out.root),
    );
    const player = new Player(L.bottom, (t) => { step = t; draw(); }, { speeds: [0.5, 1, 2], timeFormat: (v) => `step ${Math.floor(v)}` });

    const recompute = liveRequest((signal) => mode.value === "path"
      ? simulate("mathematics", "shortest_path", { edges, source: src, target: dst }, signal)
      : simulate("mathematics", "minimum_spanning_tree", { edges }, signal), {
      delay: 20, onError: (e) => L.error(e.message),
      onResult: (r) => {
        L.clearError(); res = { ...r, mode: mode.value };
        const x = r.result;
        if (mode.value === "path") {
          out.set("d", x.distance !== null ? `${fmt(x.distance, 4)} km from ${src} to ${dst}` : "unreachable");
          out.set("p", x.path ? x.path.join(" → ") : "—"); out.set("n", `${r.order.length} towns settled`);
          player.load(r.order.length + 0.999, Math.min(8, r.order.length * 0.6));
        } else {
          out.set("d", `total ${fmt(x.total_weight, 4)} km of road`); out.set("p", `${x.edges.length} roads join ${x.n_nodes} towns`);
          out.set("n", `${r.rejected.length} roads skipped (would form a loop)`);
          player.load(x.edges.length + 0.999, Math.min(8, x.edges.length * 0.6));
        }
      },
    });

    let box = null;
    const P = (n) => [box.ox + NODES[n][0] * box.s, box.oy + (10 - NODES[n][1]) * box.s];
    stage.canvas.addEventListener("click", (e) => {
      if (!box) return;
      const b = stage.canvas.getBoundingClientRect(), px = e.clientX - b.left, py = e.clientY - b.top;
      const hit = Object.keys(NODES).find((n) => { const [x, y] = P(n); return Math.hypot(x - px, y - py) < 18; });
      if (!hit) return;
      if (mode.value !== "path") mode.set("path");
      if (src && dst) { src = hit; dst = null; draw(); return; }
      if (hit !== src) { dst = hit; recompute(); }
    });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      ctx.fillStyle = "#f4f7f2"; ctx.fillRect(0, 0, w, h);
      const s = Math.min((w - 60) / 10, (h - 60) / 10);
      box = { s, ox: (w - 10 * s) / 2, oy: (h - 10 * s) / 2 };
      const k = Math.floor(step);
      const on = new Set(), settled = new Map();
      if (res && res.mode === "path") {
        res.order.slice(0, k).forEach((o) => { settled.set(o.node, o.distance); if (o.via) on.add([o.via, o.node].sort().join("")); });
      } else if (res) res.result.edges.slice(0, k).forEach(([u, v]) => on.add([u, v].sort().join("")));
      const path = res && res.mode === "path" && res.result.path && k >= res.order.length ? new Set(res.result.path.slice(1).map((n, i) => [res.result.path[i], n].sort().join(""))) : new Set();
      for (const [u, v, wgt] of edges) {
        const [x1, y1] = P(u), [x2, y2] = P(v), key = [u, v].sort().join("");
        ctx.strokeStyle = path.has(key) ? c2 : on.has(key) ? c1 : "#c9ced6"; ctx.lineWidth = path.has(key) ? 7 : on.has(key) ? 4 : 3;
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
        label(ctx, fmt(wgt, 3), (x1 + x2) / 2, (y1 + y2) / 2, { align: "center", font: "11px system-ui", color: "#4b5868", halo: "#f4f7f2" });
      }
      for (const n of Object.keys(NODES)) {
        const [x, y] = P(n), isEnd = n === src || n === dst;
        ctx.fillStyle = isEnd ? c2 : settled.has(n) ? c1 : "#fff"; ctx.strokeStyle = "#16202c"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(x, y, 15, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        label(ctx, n, x, y + 1, { align: "center", font: "bold 13px system-ui", color: isEnd || settled.has(n) ? "#fff" : "#16202c" });
        if (settled.has(n)) label(ctx, fmt(settled.get(n), 3), x, y - 24, { align: "center", font: "bold 11px system-ui", color: c3, halo: "#f4f7f2" });
      }
      label(ctx, dst ? `${src} → ${dst}` : `from ${src}: now click a destination`, 12, 16, { font: "bold 13px system-ui" });
    }

    makeEdges(); recompute();
    return () => { recompute.cancel(); player.destroy(); stage.destroy(); };
  },
};
