// Playback controls for a precomputed simulation: play/pause, restart, scrub and speed.
import { el } from "./ui.js";
import { fmtTime } from "./format.js";

/** Every Player on screen; the keyboard drives the most recent one (see playerKeys). */
const PLAYERS = new Set();

export class Player {
  /**
   * @param parent container
   * @param onFrame (simTime) => void, called every animation frame and on seek
   * @param opts {speeds: [numbers], speed, loop, autoplay, timeFormat}
   */
  constructor(parent, onFrame, opts = {}) {
    this.onFrame = onFrame;
    this.opts = { speeds: [0.25, 0.5, 1, 2, 4], speed: 1, loop: false, timeFormat: fmtTime, ...opts };
    this.duration = 0;
    this.baseRate = 1;   // sim seconds per real second at 1x
    this.speed = this.opts.speed;
    this.time = 0;
    this.playing = false;
    this.last = null;

    this.playBtn = el("button", { class: "play", type: "button", "aria-label": "Play", onclick: () => this.toggle() }, "▶");
    const restart = el("button", { class: "icon-btn", type: "button", "aria-label": "Restart", title: "Restart", onclick: () => { this.seek(0); this.play(); } }, "↺");
    this.scrub = el("input", { type: "range", min: 0, max: 1000, value: 0, "aria-label": "Time" });
    this.scrub.addEventListener("input", () => this.seek((this.scrub.value / 1000) * this.duration));
    this.timeLabel = el("span", { class: "time" }, "–");
    this.speedSel = el("select", { "aria-label": "Speed" },
      this.opts.speeds.map((s) => el("option", { value: s }, `${s}×`)));
    this.speedSel.value = String(this.speed);
    this.speedSel.addEventListener("change", () => { this.speed = Number(this.speedSel.value); });
    this.playBtn.title = "Play or pause (Space)"; restart.title = "Restart (R)";
    this.root = el("div", { class: "player" }, this.playBtn, restart, this.scrub, this.timeLabel, this.speedSel);
    PLAYERS.add(this);
    parent.append(this.root);
    this.tick = this.tick.bind(this);
    this.raf = requestAnimationFrame(this.tick);
  }

  /** New simulation: duration in sim seconds, played over `seconds` of real time at 1×. */
  load(duration, seconds = 10, { autoplay = true } = {}) {
    this.duration = duration;
    this.baseRate = duration / seconds;
    this.seek(0);
    if (autoplay) this.play();
  }

  play() {
    if (this.time >= this.duration) this.time = 0;
    this.playing = true; this.last = null;
    this.playBtn.textContent = "❚❚"; this.playBtn.setAttribute("aria-label", "Pause");
  }

  pause() {
    this.playing = false;
    this.playBtn.textContent = "▶"; this.playBtn.setAttribute("aria-label", "Play");
  }

  toggle() { if (this.playing) this.pause(); else this.play(); }

  seek(t) {
    this.time = Math.max(0, Math.min(t, this.duration));
    this.sync();
    this.onFrame(this.time);
  }

  sync() {
    this.scrub.value = this.duration ? Math.round((this.time / this.duration) * 1000) : 0;
    this.timeLabel.textContent = this.opts.timeFormat(this.time);
  }

  tick(now) {
    this.raf = requestAnimationFrame(this.tick);
    if (!this.playing || !this.duration) { this.last = now; return; }
    const dt = this.last === null ? 0 : Math.min((now - this.last) / 1000, 0.1);
    this.last = now;
    this.time += dt * this.baseRate * this.speed;
    if (this.time >= this.duration) {
      if (this.opts.loop) this.time %= this.duration;
      else { this.time = this.duration; this.pause(); }
    }
    this.sync();
    this.onFrame(this.time);
  }

  destroy() { cancelAnimationFrame(this.raf); PLAYERS.delete(this); }
}

/** Continuous animation loop (for purely visual motion like jiggling particles). */
export function animationLoop(fn) {
  let raf, last = null, alive = true;
  const step = (now) => {
    if (!alive) return;
    const dt = last === null ? 0 : Math.min((now - last) / 1000, 0.05);
    last = now;
    fn(dt, now);
    raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
  return () => { alive = false; cancelAnimationFrame(raf); };
}

/** Keyboard for playback, for any simulation page: Space play/pause, R restart, ← → step 5%, [ ] slower/faster.
 * Ignored while typing in a box or when a canvas that uses the arrow keys has focus. Returns a detach function. */
export function playerKeys(root) {
  const key = (e) => {
    if (!root.isConnected || e.ctrlKey || e.metaKey || e.altKey || e.target.closest?.("input, textarea, select, [contenteditable], button, canvas")) return;
    const p = [...PLAYERS].reverse().find((x) => x.root.isConnected && root.contains(x.root));
    if (!p) return;
    const sp = p.opts.speeds, i = sp.indexOf(p.speed);
    const act = { " ": () => p.toggle(), r: () => { p.seek(0); p.play(); }, ArrowLeft: () => p.seek(p.time - 0.05 * p.duration), ArrowRight: () => p.seek(p.time + 0.05 * p.duration),
      "[": () => { if (i > 0) { p.speed = sp[i - 1]; p.speedSel.value = String(p.speed); } }, "]": () => { if (i < sp.length - 1) { p.speed = sp[i + 1]; p.speedSel.value = String(p.speed); } } }[e.key.length === 1 ? e.key.toLowerCase() : e.key];
    if (act) { e.preventDefault(); act(); }
  };
  window.addEventListener("keydown", key);
  return () => window.removeEventListener("keydown", key);
}
