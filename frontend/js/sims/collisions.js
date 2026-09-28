// Collisions Lab: physics.collisions_2d simulates the discs exactly (event-driven); we animate the frames.
import { simulate, liveRequest } from "../core/api.js";
import { simLayout, panel, slider, select, checkbox, readouts, el, SERIES } from "../core/ui.js";
import { createStage, View, indexAt, sampleAt, label, arrow } from "../core/stage.js";
import { Player } from "../core/player.js";
import { LineGraph } from "../core/graph.js";
import { fmt } from "../core/format.js";

const W = 3, H = 2, DURATION = 10;
const COLORS = ["#eb6834", "#2a78d6", "#1baf7a", "#eda100", "#4a3aa7"];
const START = [
  { mass: 1, x: 0.6, y: 1.0, vx: 1.2, vy: 0.3 }, { mass: 2, x: 1.8, y: 1.1, vx: -0.4, vy: 0 },
  { mass: 1.5, x: 2.4, y: 0.5, vx: 0, vy: 0.6 }, { mass: 0.5, x: 1.2, y: 1.6, vx: 0.5, vy: -0.5 }, { mass: 3, x: 2.5, y: 1.6, vx: -0.3, vy: -0.2 },
];
const radius = (m) => 0.08 + 0.05 * Math.cbrt(m);

export default {
  mount(root) {
    const L = simLayout(root);
    const stage = createStage(L.scene, { onResize: draw });
    const view = new View();
    const [c1] = SERIES();
    let balls = START.slice(0, 2).map((b) => ({ ...b }));
    let data = null, simTime = 0, drag = null;

    const count = select({ label: "Number of balls", value: "2", options: [1, 2, 3, 4, 5].map((n) => ({ value: String(n), label: String(n) })), onChange: (v) => {
      const n = Number(v);
      balls = balls.slice(0, n); while (balls.length < n) balls.push({ ...START[balls.length] });
      buildMass(); recompute();
    } });
    const elastic = slider({ label: "Elasticity", min: 0, max: 100, step: 1, value: 100, unit: "%", onInput: () => recompute() });
    const walls = checkbox({ label: "Reflecting border", value: true, onChange: () => recompute() });
    const massBox = el("div");
    const table = el("div");
    function buildMass() {
      massBox.replaceChildren(...balls.map((b, i) => slider({ label: `Ball ${i + 1} mass`, min: 0.1, max: 5, step: 0.1, value: b.mass, unit: "kg", onInput: (v) => { b.mass = v; recompute(); } }).root));
    }
    L.side.append(
      panel("Setup", count.root, elastic.root, walls.root, el("p", { class: "note" }, "Drag balls to move them and drag the arrow tips to set velocities, then press play.")),
      panel("Masses", massBox),
      panel("Momentum (from the engine)", table),
    );
    buildMass();
    const player = new Player(L.bottom, (t) => { simTime = t; draw(); graph.setCursor(t); updateTable(); }, { speeds: [0.25, 0.5, 1, 2] });
    const graph = new LineGraph(L.bottom, { title: "Total kinetic energy", xLabel: "time (s)", yLabel: "energy (J)", height: 130, includeZero: true });

    const recompute = liveRequest((signal) => simulate("physics", "collisions_2d", {
      balls: balls.map((b) => ({ mass: b.mass, radius: radius(b.mass), x: b.x, y: b.y, vx: b.vx, vy: b.vy })),
      duration: DURATION, width: W, height: H, restitution: elastic.value / 100, reflecting_walls: walls.value, n_frames: 1001,
    }, signal), {
      delay: 80, onBusy: L.busy, onError: (e) => { L.error(e.message); data = null; draw(); },
      onResult: (res) => {
        L.clearError(); data = res;
        graph.setSeries([{ name: "Kinetic energy", color: c1, x: res.frames.t, y: res.kinetic_energy }]);
        player.load(DURATION, DURATION, { autoplay: false });
        updateTable();
      },
    });

    function updateTable() {
      if (!data) { table.replaceChildren(); return; }
      const k = indexAt(data.frames.t, simTime);
      const px = data.momentum.px[k], py = data.momentum.py[k];
      const dl = el("dl", { class: "readouts" },
        el("dt", {}, "Total momentum x"), el("dd", {}, `${fmt(px, 4)} kg·m/s`),
        el("dt", {}, "Total momentum y"), el("dd", {}, `${fmt(py, 4)} kg·m/s`),
        el("dt", {}, "Kinetic energy"), el("dd", {}, `${fmt(data.kinetic_energy[k], 4)} J`),
        el("dt", {}, "Ball–ball collisions"), el("dd", {}, String(data.events.filter((e) => e.type === "ball" && e.t <= simTime).length)));
      table.replaceChildren(dl);
    }

    const pos = (i) => {
      if (!data || simTime === 0 || drag) return [balls[i].x, balls[i].y];
      const f = data.frames;
      return [sampleAt(f.t, f.x[i], simTime), sampleAt(f.t, f.y[i], simTime)];
    };
    const world = (e) => { const r = stage.canvas.getBoundingClientRect(); return view.toWorld(e.clientX - r.left, e.clientY - r.top); };
    const VSCALE = 0.35;   // metres of arrow per m/s
    stage.canvas.addEventListener("pointerdown", (e) => {
      if (simTime > 0) { player.seek(0); player.pause(); }
      const [wx, wy] = world(e);
      balls.forEach((b, i) => {
        if (Math.hypot(wx - (b.x + b.vx * VSCALE), wy - (b.y + b.vy * VSCALE)) < 0.07) drag = { i, what: "v" };
      });
      if (!drag) balls.forEach((b, i) => { if (Math.hypot(wx - b.x, wy - b.y) < radius(b.mass)) drag = { i, what: "p" }; });
      if (drag) stage.canvas.setPointerCapture(e.pointerId);
    });
    stage.canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const [wx, wy] = world(e), b = balls[drag.i], r = radius(b.mass);
      if (drag.what === "p") { b.x = Math.min(W - r, Math.max(r, wx)); b.y = Math.min(H - r, Math.max(r, wy)); }
      else { b.vx = Math.round(((wx - b.x) / VSCALE) * 10) / 10; b.vy = Math.round(((wy - b.y) / VSCALE) * 10) / 10; }
      draw();
    });
    stage.canvas.addEventListener("pointerup", () => { if (drag) { drag = null; recompute(); } });

    function draw() {
      const { ctx, width: w, height: h } = stage;
      if (!w) return;
      view.fit(0, W, 0, H, w, h, { pad: 0.05 });
      ctx.fillStyle = "#eef3f9"; ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#fff"; ctx.fillRect(view.x(0), view.y(H), view.len(W), view.len(H));
      ctx.strokeStyle = walls.value ? "#39424e" : "#b8c4d3"; ctx.lineWidth = walls.value ? 3 : 1; ctx.setLineDash(walls.value ? [] : [6, 5]);
      ctx.strokeRect(view.x(0), view.y(H), view.len(W), view.len(H)); ctx.setLineDash([]);
      ctx.strokeStyle = "#eef1f5"; ctx.lineWidth = 1;
      for (let x = 0.5; x < W; x += 0.5) { ctx.beginPath(); ctx.moveTo(view.x(x), view.y(0)); ctx.lineTo(view.x(x), view.y(H)); ctx.stroke(); }
      for (let y = 0.5; y < H; y += 0.5) { ctx.beginPath(); ctx.moveTo(view.x(0), view.y(y)); ctx.lineTo(view.x(W), view.y(y)); ctx.stroke(); }
      // Trails
      if (data && simTime > 0) {
        const k = indexAt(data.frames.t, simTime);
        balls.forEach((_, i) => {
          ctx.strokeStyle = COLORS[i]; ctx.globalAlpha = 0.35; ctx.lineWidth = 2; ctx.beginPath();
          for (let j = Math.max(0, k - 150); j <= k; j++) {
            const X = view.x(data.frames.x[i][j]), Y = view.y(data.frames.y[i][j]);
            if (j === Math.max(0, k - 150)) ctx.moveTo(X, Y); else ctx.lineTo(X, Y);
          }
          ctx.stroke(); ctx.globalAlpha = 1;
        });
      }
      balls.forEach((b, i) => {
        const [x, y] = pos(i), r = radius(b.mass);
        ctx.fillStyle = COLORS[i]; ctx.beginPath(); ctx.arc(view.x(x), view.y(y), view.len(r), 0, Math.PI * 2); ctx.fill();
        label(ctx, String(i + 1), view.x(x), view.y(y), { align: "center", color: "#fff", font: "bold 13px system-ui" });
        if (simTime === 0 || !data) {
          arrow(ctx, view.x(b.x), view.y(b.y), view.x(b.x + b.vx * VSCALE), view.y(b.y + b.vy * VSCALE), "#16202c", 2, 9);
          ctx.fillStyle = "rgba(22,32,44,.15)"; ctx.beginPath(); ctx.arc(view.x(b.x + b.vx * VSCALE), view.y(b.y + b.vy * VSCALE), 9, 0, Math.PI * 2); ctx.fill();
          label(ctx, `${fmt(Math.hypot(b.vx, b.vy), 2)} m/s`, view.x(b.x) + 12, view.y(b.y) - view.len(r) - 10, { font: "11px system-ui", color: "#4b5868" });
        }
      });
      label(ctx, `t = ${fmt(simTime, 3)} s`, 14, 18, { font: "13px system-ui" });
      label(ctx, "Box 3 m × 2 m", w - 14, 18, { align: "right", font: "11px system-ui", color: "#7b8796" });
    }

    recompute();
    return () => { recompute.cancel(); player.destroy(); graph.destroy(); stage.destroy(); };
  },
};
