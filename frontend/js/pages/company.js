// Mission Control: your space company. Satellites and probes are stored on the server and move in real time;
// every position, decay rate, burn and photo footprint comes from the engine (satellite_track, satellite_manoeuvre,
// satellite_imaging, interplanetary_mission). This page draws them and sends your commands.
import { el, cssVar } from "../core/ui.js";
import { fmt } from "../core/format.js";
import { LineGraph } from "../core/graph.js";
import { simulate } from "../core/api.js";
import { api, history, toast, confirmBox, promptBox, when } from "../core/session.js";

const DAY = 86400;
const PLANET_NAMES = { mercury: "Mercury", venus: "Venus", mars: "Mars", jupiter: "Jupiter", saturn: "Saturn", uranus: "Uranus", neptune: "Neptune" };
const ORBIT_PRESETS = [
  ["usual", "The satellite's usual orbit"],
  ["leo", "Low Earth orbit, 420 km, 51.6°"],
  ["sso", "Sun-synchronous, 600 km, 97.8°"],
  ["geo", "Geostationary slot"],
  ["meo", "Navigation orbit, 20,180 km, 55°"],
  ["custom", "Custom orbit"],
];
const km = (m) => (m == null ? "–" : `${fmt(m / 1000, Math.abs(m) >= 1e6 ? 6 : 4)} km`);
const deg = (d, digits = 2) => (d == null ? "–" : `${d.toFixed(digits)}°`);
const latlon = (lat, lon) => `${Math.abs(lat).toFixed(2)}° ${lat >= 0 ? "N" : "S"}, ${Math.abs(lon).toFixed(2)}° ${lon >= 0 ? "E" : "W"}`;
const dateOf = (ts) => new Date(ts * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
const loadImg = (src) => new Promise((ok, fail) => { const i = new Image(); i.crossOrigin = "anonymous"; i.onload = () => ok(i); i.onerror = fail; i.src = src; });
let earthLoading = null, dayImg = null, nightImg = null;
const earthImages = () => (earthLoading ||= Promise.all([loadImg("assets/textures/earth_day.jpg"), loadImg("assets/textures/earth_night.jpg")])
  .then(([d, n]) => { dayImg = d; nightImg = n; return [d, n]; }));

function fact(label, value, cls = "") { return el("div", { class: `mc-fact ${cls}` }, el("span", {}, label), el("b", {}, value)); }
function modal(title, ...body) {
  const back = el("div", { class: "modal-back" });
  const close = () => back.remove();
  back.addEventListener("click", (e) => { if (e.target === back) close(); });
  const box = el("div", { class: "modal wide-modal", role: "dialog", "aria-modal": "true", "aria-label": title },
    el("div", { class: "modal-title" }, el("h3", {}, title), el("button", { class: "ai-x", type: "button", "aria-label": "Close", onclick: close }, "×")), ...body);
  back.append(box);
  document.body.append(back);
  return { back, box, close };
}

// ---------------------------------------------------------------- photo rendering
async function renderPhoto(canvas, photo, size = 512) {
  const im = photo.imaging, fp = im.footprint;
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#0b1526"; ctx.fillRect(0, 0, size, size);
  let source = "nasa";
  try {
    const img = await loadImg(photo.source.url);
    ctx.drawImage(img, 0, 0, size, size);
  } catch {
    source = "local";
    const [day] = await earthImages();
    const W = day.naturalWidth, H = day.naturalHeight;
    const x0 = ((fp.west + 180) / 360) * W, x1 = ((fp.east + 180) / 360) * W;
    const y0 = ((90 - fp.north) / 180) * H, y1 = ((90 - fp.south) / 180) * H;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(day, x0, y0, Math.max(1, x1 - x0), Math.max(1, y1 - y0), 0, 0, size, size);
  }
  // Coarser than the picture's pixels? Show the camera's real resolution by resampling to it.
  const spanM = im.swath;
  const cells = Math.max(2, Math.min(size, Math.round(spanM / im.resolution)));
  if (cells < size) {
    const small = document.createElement("canvas"); small.width = small.height = cells;
    small.getContext("2d").drawImage(canvas, 0, 0, cells, cells);
    ctx.imageSmoothingEnabled = false; ctx.drawImage(small, 0, 0, size, size); ctx.imageSmoothingEnabled = true;
  }
  if (im.camera_type === "sar") { // radar images are greyscale backscatter
    const d = ctx.getImageData(0, 0, size, size);
    for (let i = 0; i < d.data.length; i += 4) { const v = 0.35 * d.data[i] + 0.5 * d.data[i + 1] + 0.15 * d.data[i + 2]; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; }
    try { ctx.putImageData(d, 0, 0); } catch { /* tainted canvas: leave colour */ }
  }
  return source;
}

function openPhoto(photo) {
  const canvas = el("canvas", { class: "photo-canvas" });
  const im = photo.imaging;
  const note = el("p", { class: "muted small" }, "Loading imagery…");
  modal(`${photo.satellite}: ${latlon(im.target.lat, im.target.lon)}`, el("div", { class: "photo-view" }, canvas,
    el("div", { class: "photo-facts" },
      fact("Taken", new Date(photo.taken_at * 1000).toLocaleString()),
      fact("Resolution", `${fmt(im.resolution, 3)} m`), fact("Swath", km(im.swath)),
      fact("Off nadir", deg(im.off_nadir_deg, 1)), fact("Sun elevation", deg(im.sun_elevation_deg, 0)),
      fact("Satellite altitude", km(im.satellite.altitude)),
      im.diffraction_limit ? fact("Diffraction limit", `${fmt(im.diffraction_limit, 3)} m`) : "",
      note)));
  renderPhoto(canvas, photo).then((src) => {
    note.textContent = src === "nasa"
      ? `Imagery: ${photo.source.credit}. Shown at the camera's resolution or the imagery's (~250 m), whichever is coarser.`
      : "Live NASA imagery couldn't be loaded, so this uses the app's Blue Marble base map (~10 km per pixel). Framing and resolution still come from the engine.";
  });
}

// ---------------------------------------------------------------- page
export default {
  title: "Mission Control",
  mount(root, params) {
    let company = null, fleet = [], subsolar = null, selected = null, detail = null, detailAt = 0, target = null, catalog = null;
    let alive = true, pollT = 0, detailT = 0, raf = 0;
    const wrap = el("div", { class: "mc" });
    root.append(wrap);

    const cleanup = () => { alive = false; clearTimeout(pollT); clearTimeout(detailT); cancelAnimationFrame(raf); ro?.disconnect(); };
    let ro = null;

    // ----- founding
    function founding() {
      const name = el("input", { class: "text-input", placeholder: "e.g. Chandra Orbital", maxlength: 48 });
      const form = el("form", { class: "found" },
        el("h1", {}, "Found your space company"),
        el("p", { class: "muted" }, "Buy launches on real rockets, run a fleet that keeps flying in real time, take pictures of Earth and send probes to other planets."),
        el("label", { class: "field-label" }, "Company name"), name,
        el("button", { class: "btn primary big", type: "submit" }, "Found company"));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { const r = await api("/api/company", { method: "POST", body: { name: name.value.trim() } }); company = r.company; build(); }
        catch (err) { toast(err.message, "error"); }
      });
      wrap.replaceChildren(form);
      name.focus();
    }

    // ----- main layout
    const mapCanvas = el("canvas", { class: "mc-map", "aria-label": "World map with your satellites" });
    const mapBox = el("div", { class: "mc-mapbox" }, mapCanvas, el("div", { class: "mc-map-hint" }, "Click the map to choose a photo target for the selected satellite"));
    const list = el("div", { class: "mc-list" });
    const side = el("div", { class: "mc-detail" });
    const header = el("div", { class: "mc-head" });
    const banner = el("div", { class: "mc-banner", hidden: true });

    function build() {
      header.replaceChildren(
        el("div", {}, el("h1", {}, company.name), el("small", { class: "muted" }, `Founded ${dateOf(company.founded_at)}`)),
        el("span", { class: "grow" }),
        el("button", { class: "btn", type: "button", onclick: renameCompany }, "Rename"),
        el("button", { class: "btn", type: "button", onclick: openProbe }, "Send a probe"),
        el("button", { class: "btn primary", type: "button", onclick: () => openLaunch() }, "Launch a satellite"));
      wrap.replaceChildren(header, banner, el("div", { class: "mc-body" }, el("div", { class: "mc-left" }, mapBox, list), side));
      ro = new ResizeObserver(() => drawMap()); ro.observe(mapBox);
      if (params.challenge) showChallenge(params.challenge);
      poll();
      loop();
      if (params.probe) openProbe();
      if (params.craft) select(params.craft);
      if (params.run) openFromHistory(params.run);
      else side.replaceChildren(el("div", { class: "mc-empty" }, el("b", {}, "Select a spacecraft"), el("p", { class: "muted small" }, "Pick one from the list to see its orbit, fire thrusters or take pictures.")));
    }

    async function renameCompany() {
      const n = await promptBox("Rename company", "Company name", company.name);
      if (!n) return;
      try { company = (await api("/api/company", { method: "POST", body: { name: n } })).company; build(); } catch (e) { toast(e.message, "error"); }
    }

    async function showChallenge(id) {
      try {
        const { challenges } = await api("/api/challenges");
        const c = challenges.find((x) => x.id === id);
        if (!c) return;
        const res = el("span", { class: "muted small" });
        banner.hidden = false;
        banner.replaceChildren(el("b", {}, `Challenge: ${c.title}`), el("span", {}, c.goal), res,
          el("button", { class: "btn small primary", type: "button", onclick: async () => {
            try { const r = await api(`/api/challenges/${id}/submit`, { method: "POST", body: {} }); res.textContent = r.message; if (r.passed) toast(`Challenge complete: ${c.title}`); }
            catch (e) { toast(e.message, "error"); }
          } }, "Check"));
      } catch { /* ignore */ }
    }

    async function openFromHistory(runId) {
      try {
        const run = await history.get(runId);
        const sid = run.payload.spacecraft_id;
        if (sid) await select(sid);
        if (run.kind === "photo" && detail?.photos) { const p = detail.photos.find((x) => x.id === run.payload.photo_id); if (p) openPhoto(p); }
      } catch (e) { toast(e.message, "error"); }
    }

    // ----- polling
    async function poll() {
      clearTimeout(pollT);
      try {
        const r = await api("/api/company/fleet");
        fleet = r.fleet; subsolar = r.subsolar;
        drawList();
      } catch (e) { if (e.status !== 401) list.replaceChildren(el("p", { class: "muted" }, e.message)); }
      if (alive) pollT = setTimeout(poll, 8000);
    }

    function statusChip(s) {
      const cls = { orbiting: "ok", "in cruise": "ok", "in orbit": "ok", scheduled: "info", decaying: "warn", "re-entered": "bad", "flew by": "info" }[s] || "info";
      return el("span", { class: `chip-s ${cls}` }, s);
    }

    function drawList() {
      if (!fleet.length) {
        list.replaceChildren(el("div", { class: "mc-empty" }, el("b", {}, "No spacecraft yet"),
          el("p", { class: "muted small" }, "Launch a satellite on a real rocket, or fly your own in the Spaceflight Lab and deploy it from orbit."),
          el("button", { class: "btn primary", type: "button", onclick: () => openLaunch() }, "Launch your first satellite")));
        return;
      }
      list.replaceChildren(...fleet.map((s) => el("button", { class: `mc-item${s.id === selected ? " on" : ""}`, type: "button", onclick: () => select(s.id) },
        el("div", { class: "mc-item-top" }, el("b", {}, s.name), statusChip(s.status)),
        el("small", { class: "muted" }, s.kind === "probe"
          ? `${PLANET_NAMES[s.mission?.target] || ""} · ${s.mission?.now?.phase === "cruise" ? `${Math.round(s.mission.now.progress * 100)} % of the way` : s.mission?.now?.phase || ""}`
          : s.status === "re-entered" ? "Re-entered" : `${km(s.altitude)} · ${latlon(s.lat, s.lon)}${s.sunlit === false ? " · in shadow" : ""}`))));
    }

    async function select(id) {
      selected = id; target = null; drawList();
      side.replaceChildren(el("p", { class: "muted" }, "Loading…"));
      await refreshDetail();
    }

    async function refreshDetail() {
      clearTimeout(detailT);
      if (!selected) return;
      try {
        detail = await api(`/api/company/spacecraft/${selected}`);
        detailAt = performance.now();
        drawDetail();
      } catch (e) { side.replaceChildren(el("p", { class: "muted" }, e.message)); }
      if (alive) detailT = setTimeout(refreshDetail, 30000);
    }

    // ----- detail panel
    function drawDetail() {
      const d = detail;
      const head = el("div", { class: "mc-dhead" },
        el("div", {}, el("h2", {}, d.name), el("small", { class: "muted" }, d.spec?.purpose || (d.kind === "probe" ? "Deep-space probe" : "Satellite"))),
        statusChip(d.status));
      const actions = el("div", { class: "btn-row" },
        el("button", { class: "btn small", type: "button", onclick: async () => {
          const n = await promptBox("Rename spacecraft", "Name", d.name);
          if (n) { try { await api(`/api/company/spacecraft/${d.id}`, { method: "PATCH", body: { name: n } }); await refreshDetail(); poll(); } catch (e) { toast(e.message, "error"); } }
        } }, "Rename"),
        el("button", { class: "btn small danger-text", type: "button", onclick: async () => {
          if (!(await confirmBox(`Retire ${d.name}?`, "It will be removed from your fleet with its photos.", "Retire", true))) return;
          try { await api(`/api/company/spacecraft/${d.id}`, { method: "DELETE" }); selected = null; detail = null; side.replaceChildren(); poll(); } catch (e) { toast(e.message, "error"); }
        } }, "Retire"));
      const parts = [head];
      if (d.kind === "probe") parts.push(...probeDetail(d));
      else parts.push(...satDetail(d));
      parts.push(el("details", { class: "mc-log" }, el("summary", {}, "Mission log"),
        el("ul", {}, (d.log || []).slice().reverse().map((l) => el("li", {}, el("small", { class: "muted" }, new Date(l.t * 1000).toLocaleString()), " ", l.event)))), actions);
      side.replaceChildren(...parts);
    }

    function satDetail(d) {
      if (d.status === "re-entered") return [el("p", {}, "This satellite has re-entered the atmosphere. Its log is kept below.")];
      const el_ = d.elements;
      const out = [
        el("div", { class: "mc-facts" },
          fact("Altitude", km(d.altitude)), fact("Speed", `${fmt(d.speed / 1000, 4)} km/s`), fact("Over", latlon(d.lat, d.lon)),
          fact("Sunlight", d.sunlit ? "In sunlight" : "In Earth's shadow"),
          fact("Perigee × apogee", `${fmt(el_.perigee_alt / 1000, 4)} × ${fmt(el_.apogee_alt / 1000, 4)} km`),
          fact("Inclination", deg(el_.i_deg)), fact("Period", `${fmt(el_.period / 60, 4)} min`),
          fact("Launched on", d.spec?.launch?.vehicle || "–")),
      ];
      // decay
      const decay = el("div", { class: "mc-section" }, el("h4", {}, "Orbit health"));
      if (d.lifetime_days != null) {
        const reentry = Date.now() / 1000 + d.lifetime_days * DAY;
        decay.append(el("p", { class: d.lifetime_days < 60 ? "warn-text" : "" },
          `Sinking about ${fmt(d.decay_m_per_day || 0, 3)} m a day. Without a boost it re-enters around ${dateOf(reentry)} (${fmt(d.lifetime_days, 3)} days).`));
        if (d.decay_history?.length > 2) {
          const g = new LineGraph(decay, { title: "Perigee and apogee without a boost", height: 140, xFormat: (v) => `${fmt(v, 3)} d`, yFormat: (v) => `${fmt(v, 3)} km` });
          const t = d.decay_history.map((h) => h.t_days);
          g.setSeries([{ name: "Apogee", color: cssVar("--series-1"), x: t, y: d.decay_history.map((h) => h.apogee_alt / 1000) },
            { name: "Perigee", color: cssVar("--series-2"), x: t, y: d.decay_history.map((h) => h.perigee_alt / 1000) }]);
        }
      } else decay.append(el("p", {}, d.lifetime_beyond_years ? `High enough that drag won't bring it down for over ${d.lifetime_beyond_years} years.` : "No atmospheric drag at this altitude."));
      out.push(decay);
      // propulsion
      const prop = el("div", { class: "mc-section" }, el("h4", {}, "Thrusters"),
        el("div", { class: "mc-facts" }, fact("Propellant", `${fmt(d.propellant, 4)} kg`), fact("Δv available", `${fmt(d.delta_v_available || 0, 4)} m/s`),
          fact("Isp", d.spec?.isp ? `${fmt(d.spec.isp, 4)} s` : "none")));
      if (d.spec?.isp > 0 && d.propellant > 0) {
        const alt = el("input", { class: "text-input small", type: "number", min: 150, max: 400000, step: 1, value: Math.round(el_.apogee_alt / 1000 + 20), "aria-label": "Target altitude in km" });
        const dv = el("input", { class: "text-input small", type: "number", min: 0.1, max: 5000, step: 0.1, value: 5, "aria-label": "Delta-v in m/s" });
        const dir = el("select", { class: "text-input small", "aria-label": "Burn direction" }, ...[["prograde", "Prograde"], ["retrograde", "Retrograde"], ["normal", "Normal"], ["antinormal", "Anti-normal"], ["radial_out", "Radial out"], ["radial_in", "Radial in"]].map(([v, t]) => el("option", { value: v }, t)));
        const fire = async (body, label) => {
          try {
            const r = await api(`/api/company/spacecraft/${d.id}/burn`, { method: "POST", body });
            toast(`${label}: ${fmt(r.burn.delta_v_total, 3)} m/s, ${fmt(r.burn.propellant_used, 3)} kg used.`);
            detail = r.spacecraft; detailAt = performance.now(); drawDetail(); poll();
          } catch (e) { toast(e.message, "error"); }
        };
        prop.append(
          el("div", { class: "mc-row" }, el("span", {}, "Move to a circular orbit at"), alt, el("span", {}, "km"),
            el("button", { class: "btn small primary", type: "button", onclick: () => fire({ burn: "change_altitude", target_altitude: +alt.value * 1000 }, "Orbit change") }, "Go")),
          el("div", { class: "mc-row" }, el("span", {}, "Burn"), dv, el("span", {}, "m/s"), dir,
            el("button", { class: "btn small primary", type: "button", onclick: () => fire({ burn: dir.value, delta_v: +dv.value }, "Burn") }, "Fire")),
          el("div", { class: "btn-row" },
            el("button", { class: "btn small", type: "button", onclick: () => fire({ burn: "circularize" }, "Circularized") }, "Circularize at apoapsis"),
            el("button", { class: "btn small danger-text", type: "button", onclick: async () => {
              if (await confirmBox("De-orbit?", "Lowers the perigee to 50 km so the satellite burns up safely.", "De-orbit", true)) fire({ burn: "deorbit" }, "De-orbit burn");
            } }, "De-orbit")));
      } else prop.append(el("p", { class: "muted small" }, d.spec?.isp > 0 ? "Tanks are empty." : "This satellite has no thrusters."));
      out.push(prop);
      // camera
      const cam = d.spec?.camera;
      const camBox = el("div", { class: "mc-section" }, el("h4", {}, "Camera"));
      if (cam) {
        camBox.append(el("p", { class: "small" }, cam.type === "sar"
          ? `Radar (${cam.band}), ${cam.resolution_m} m resolution, ${cam.swath_km} km swath. Works day and night, looks sideways.`
          : `Optical, ${fmt(cam.aperture_m * 100, 3)} cm aperture, ${fmt(cam.ifov_urad * d.altitude / 1e6, 3)} m per pixel straight down from here. ${cam.bands?.join(", ") || ""}`));
        const tgt = el("span", { class: "small muted" }, target ? `Target ${latlon(target.lat, target.lon)}` : "No target chosen: the photo is taken straight down.");
        const shoot = async (tg) => {
          try {
            const p = await api(`/api/company/spacecraft/${d.id}/photo`, { method: "POST", body: tg ? { target_lat: tg.lat, target_lon: tg.lon } : {} });
            openPhoto({ ...p, satellite: d.name });
            await refreshDetail();
          } catch (e) { toast(e.message, "error"); }
        };
        camBox.append(tgt, el("div", { class: "btn-row" },
          el("button", { class: "btn small primary", type: "button", onclick: () => shoot(null) }, "Photo straight down"),
          el("button", { class: "btn small", type: "button", disabled: !target, onclick: () => shoot(target) }, "Photo of the map target")));
        if (d.photos?.length) {
          const g = el("div", { class: "thumbs" });
          d.photos.slice(0, 12).forEach((p) => {
            const c = el("canvas", { class: "thumb", title: `${latlon(p.imaging.target.lat, p.imaging.target.lon)}, ${when(p.taken_at)}` });
            c.addEventListener("click", () => openPhoto({ ...p, satellite: d.name }));
            renderPhoto(c, p, 96);
            g.append(c);
          });
          camBox.append(g);
        }
      } else camBox.append(el("p", { class: "muted small" }, "No camera on this satellite."));
      out.push(camBox);
      return out;
    }

    function probeDetail(d) {
      const m = d.mission, now = m.now || {};
      const canvas = el("canvas", { class: "mc-helio" });
      const facts = el("div", { class: "mc-facts" },
        fact("Target", PLANET_NAMES[m.target]), fact("Departs", m.depart.slice(0, 10)), fact("Arrives", m.arrive.slice(0, 10)),
        fact("Flight time", `${fmt(m.tof_days, 4)} days`), fact("Launch energy C3", `${fmt(m.c3_km2s2, 3)} km²/s²`),
        fact("Departure burn", `${fmt(m.departure_burn, 4)} m/s`), fact(m.capture ? "Capture burn" : "Arrival speed", m.capture ? `${fmt(m.capture_burn, 4)} m/s` : `${fmt(m.vinf_arrival / 1000, 3)} km/s`),
        now.distance_from_earth ? fact("Distance from Earth", `${fmt(now.distance_from_earth / 1.495978707e11, 4)} AU`) : "",
        now.light_time_s ? fact("Signal delay", `${fmt(now.light_time_s / 60, 3)} min`) : "",
        now.days_to_arrival ? fact("Arrival in", `${fmt(now.days_to_arrival, 4)} days`) : "",
        now.days_to_launch ? fact("Launch in", `${fmt(now.days_to_launch, 4)} days`) : "");
      const progress = now.phase === "cruise" ? el("div", { class: "meter" }, el("i", { style: `width:${now.progress * 100}%` })) : "";
      requestAnimationFrame(() => drawHelio(canvas, m));
      return [el("p", { class: "small" }, { "waiting for launch": "Waiting on the pad for its launch date.", cruise: "Coasting on its transfer orbit around the Sun.",
        arrived: m.capture ? `In orbit around ${PLANET_NAMES[m.target]}.` : `Flew past ${PLANET_NAMES[m.target]}.` }[now.phase] || ""), progress, canvas, facts];
    }

    function drawHelio(canvas, m) {
      const W = canvas.clientWidth || 320, H = canvas.clientHeight || 260, dpr = Math.min(2, devicePixelRatio);
      canvas.width = W * dpr; canvas.height = H * dpr;
      const ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "#0b1526"; ctx.fillRect(0, 0, W, H);
      const all = [...m.origin_orbit_au, ...m.target_orbit_au];
      const ext = Math.max(...all.map((p) => Math.hypot(p[0], p[1]))) * 1.08;
      const s = Math.min(W, H) / 2 / ext, S = (p) => [W / 2 + p[0] * s, H / 2 - p[1] * s];
      const line = (pts, color, w = 1, dash = []) => { ctx.strokeStyle = color; ctx.lineWidth = w; ctx.setLineDash(dash); ctx.beginPath(); pts.forEach((p, i) => { const [x, y] = S(p); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke(); ctx.setLineDash([]); };
      line(m.origin_orbit_au, "rgba(120,170,255,.45)"); line(m.target_orbit_au, "rgba(255,160,120,.45)");
      line(m.path_au, "#FF5B2E", 2, [5, 4]);
      const dot = (p, r, c, label) => { const [x, y] = S(p); ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); if (label) { ctx.font = "11px Plex, system-ui"; ctx.fillStyle = "#cfd8e6"; ctx.fillText(label, x + r + 4, y - 4); } };
      dot([0, 0], 6, "#ffd36b", "Sun");
      dot(m.origin_at_departure_au, 3.5, "#6fa8ff", "Earth at launch");
      dot(m.target_at_arrival_au, 3.5, "#ff9b6b", `${PLANET_NAMES[m.target]} at arrival`);
      if (m.now?.position_au) dot(m.now.position_au, 5, "#ffffff", m.now.phase === "cruise" ? "Probe now" : "");
    }

    // ----- world map
    function mapGeom() {
      const W = mapBox.clientWidth, H = Math.round(W / 2);
      return { W, H, X: (lon) => ((((lon + 180) % 360) + 360) % 360) / 360 * W, Y: (lat) => (90 - lat) / 180 * H };
    }
    function liveTrackPosition() {
      if (!detail?.ground_track?.length) return null;
      const dt = (performance.now() - detailAt) / 1000;
      const tr = detail.ground_track;
      for (let i = 1; i < tr.length; i++) {
        if (tr[i][2] >= dt) {
          const a = tr[i - 1], b = tr[i], f = (dt - a[2]) / (b[2] - a[2]);
          let dl = b[1] - a[1]; if (dl > 180) dl -= 360; if (dl < -180) dl += 360;
          return [a[0] + (b[0] - a[0]) * f, ((a[1] + dl * f + 540) % 360) - 180];
        }
      }
      return null;
    }
    function drawMap() {
      if (!alive || !dayImg) return;
      const { W, H, X, Y } = mapGeom();
      if (!W) return;
      const dpr = Math.min(2, devicePixelRatio);
      if (mapCanvas.width !== Math.round(W * dpr)) { mapCanvas.width = Math.round(W * dpr); mapCanvas.height = Math.round(H * dpr); mapCanvas.style.height = `${H}px`; }
      const ctx = mapCanvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.drawImage(dayImg, 0, 0, W, H);
      if (subsolar) { // night side: the half of the globe facing away from the sub-solar point
        const la = subsolar.lat * Math.PI / 180, lo = subsolar.lon;
        const pts = [];
        for (let x = 0; x <= W; x += 3) {
          const lon = (x / W) * 360 - 180, dl = (lon - lo) * Math.PI / 180;
          const lat = Math.abs(la) < 1e-4 ? (Math.cos(dl) > 0 ? -90 : 90) : Math.atan(-Math.cos(dl) / Math.tan(la)) * 180 / Math.PI;
          pts.push([x, Y(lat)]);
        }
        ctx.save(); ctx.beginPath(); ctx.moveTo(0, la > 0 ? H : 0);
        pts.forEach(([x, y]) => ctx.lineTo(x, y)); ctx.lineTo(W, la > 0 ? H : 0); ctx.closePath(); ctx.clip();
        ctx.fillStyle = "rgba(4,10,24,.62)"; ctx.fillRect(0, 0, W, H);
        if (nightImg) { ctx.globalAlpha = 0.9; ctx.globalCompositeOperation = "lighter"; ctx.drawImage(nightImg, 0, 0, W, H); }
        ctx.restore();
        ctx.fillStyle = "#ffd36b"; ctx.beginPath(); ctx.arc(X(subsolar.lon), Y(subsolar.lat), 5, 0, Math.PI * 2); ctx.fill();
      }
      // selected ground track
      if (detail?.ground_track?.length && detail.id === selected) {
        ctx.strokeStyle = "rgba(255,91,46,.85)"; ctx.lineWidth = 1.6; ctx.beginPath();
        let prev = null;
        for (const [lat, lon] of detail.ground_track) { const x = X(lon), y = Y(lat); if (prev && Math.abs(x - prev) < W / 2) ctx.lineTo(x, y); else ctx.moveTo(x, y); prev = x; }
        ctx.stroke();
      }
      if (target) { const x = X(target.lon), y = Y(target.lat); ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x - 7, y); ctx.lineTo(x + 7, y); ctx.moveTo(x, y - 7); ctx.lineTo(x, y + 7); ctx.stroke(); }
      ctx.font = "12px Plex, system-ui";
      for (const s of fleet) {
        if (s.kind !== "satellite" || s.status === "re-entered" || s.lat == null) continue;
        let p = [s.lat, s.lon];
        if (s.id === selected) p = liveTrackPosition() || p;
        const x = X(p[1]), y = Y(p[0]), on = s.id === selected;
        ctx.fillStyle = on ? "#FF5B2E" : "#fff"; ctx.strokeStyle = "#0b1526"; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(x, y, on ? 6 : 4, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = "#fff"; ctx.shadowColor = "#000"; ctx.shadowBlur = 3; ctx.fillText(s.name, x + 8, y - 6); ctx.shadowBlur = 0;
      }
    }
    earthImages().then(() => drawMap()).catch(() => {});
    function loop() { if (!alive) return; drawMap(); raf = requestAnimationFrame(() => setTimeout(loop, 250)); }
    mapCanvas.addEventListener("click", (e) => {
      const r = mapCanvas.getBoundingClientRect();
      const lon = ((e.clientX - r.left) / r.width) * 360 - 180, lat = 90 - ((e.clientY - r.top) / r.height) * 180;
      target = { lat: +lat.toFixed(3), lon: +lon.toFixed(3) };
      if (detail?.kind === "satellite") drawDetail();
      drawMap();
    });

    // ----- launch dialog
    async function getCatalog() { return (catalog ||= await api("/api/company/catalog")); }
    async function openLaunch() {
      let cat;
      try { cat = await getCatalog(); } catch (e) { toast(e.message, "error"); return; }
      const satSel = el("select", { class: "text-input" },
        el("optgroup", { label: "Real satellites" }, ...cat.satellites.map((s) => el("option", { value: s.id }, `${s.name} (${s.agency}, ${fmt(s.mass, 4)} kg)${s.fleet.camera ? "" : ", no camera"}`))),
        el("optgroup", { label: "Your own" }, el("option", { value: "custom" }, "Design my own satellite")));
      const vehSel = el("select", { class: "text-input" }, ...cat.vehicles.map((v) => el("option", { value: v.id }, `${v.name} (${v.agency}), LEO ${v.payload_leo_kg ? fmt(v.payload_leo_kg / 1000, 3) + " t" : "n/a"}`)));
      const siteSel = el("select", { class: "text-input" }, ...Object.entries(cat.sites).map(([k, s]) => el("option", { value: k }, `${s.name} (${s.latitude.toFixed(1)}°)`)));
      const orbSel = el("select", { class: "text-input" }, ...ORBIT_PRESETS.map(([v, t]) => el("option", { value: v }, t)));
      const num = (v, attrs = {}) => el("input", { class: "text-input", type: "number", value: v, ...attrs });
      const peri = num(500, { min: 150, step: 1 }), apo = num(500, { min: 150, step: 1 }), inc = num(51.6, { min: 0, max: 180, step: "any" }), lon = num(85, { min: -180, max: 180, step: "any" });
      const customBox = el("div", { class: "grid2", hidden: true });
      const cName = el("input", { class: "text-input", value: "My satellite", maxlength: 48 }), cDry = num(250, { min: 1 }), cProp = num(30, { min: 0 }), cIsp = num(220, { min: 0 }), cArea = num(3, { min: 0.01, step: "any" });
      const cCam = el("select", { class: "text-input" }, el("option", { value: "" }, "No camera"),
        ...cat.satellites.filter((s) => s.fleet.camera).map((s) => el("option", { value: s.id }, `Camera like ${s.name}`)));
      customBox.append(lab("Name", cName), lab("Dry mass (kg)", cDry), lab("Propellant (kg)", cProp), lab("Thruster Isp (s)", cIsp), lab("Cross-section (m²)", cArea), lab("Camera", cCam));
      const orbitBox = el("div", { class: "grid2" }, lab("Perigee altitude (km)", peri), lab("Apogee altitude (km)", apo), lab("Inclination (°)", inc), lab("Longitude (geostationary)", lon));
      const msg = el("p", { class: "form-msg" });
      const nameIn = el("input", { class: "text-input", placeholder: "Leave blank to use the satellite's name", maxlength: 48 });
      function lab(t, input) { return el("label", { class: "stack" }, el("span", { class: "field-label" }, t), input); }
      const syncOrbit = () => {
        const s = cat.satellites.find((x) => x.id === satSel.value), o = s?.orbit;
        const preset = orbSel.value;
        const set = (p, a, i, l) => { peri.value = p; apo.value = a; inc.value = i; if (l !== undefined) lon.value = l; };
        if (preset === "usual" && o) set(o.altitude_km, o.altitude_km, o.inclination_deg, o.longitude_deg ?? lon.value);
        if (preset === "leo") set(420, 420, 51.6);
        if (preset === "sso") set(600, 600, 97.8);
        if (preset === "geo") set(35786, 35786, 0);
        if (preset === "meo") set(20180, 20180, 55);
        lon.closest("label").hidden = !(+peri.value > 35000 && +peri.value < 36500 && +inc.value < 5);
        [peri, apo, inc].forEach((x) => { x.disabled = preset !== "custom"; });
      };
      satSel.addEventListener("change", () => {
        customBox.hidden = satSel.value !== "custom";
        const s = cat.satellites.find((x) => x.id === satSel.value);
        if (s && s.agency === "ISRO") siteSel.value = "sriharikota";
        syncOrbit();
      });
      vehSel.addEventListener("change", () => { const v = cat.vehicles.find((x) => x.id === vehSel.value); if (v) siteSel.value = v.site; });
      orbSel.addEventListener("change", syncOrbit);
      [peri, inc].forEach((x) => x.addEventListener("input", syncOrbit));
      satSel.value = "cartosat3"; vehSel.value = "pslv_xl"; siteSel.value = "sriharikota"; syncOrbit();
      const go = el("button", { class: "btn primary big", type: "submit" }, "Launch");
      const form = el("form", { class: "launch-form", novalidate: true },
        el("div", { class: "grid2" }, lab("Satellite", satSel), lab("Name in your fleet", nameIn), lab("Rocket", vehSel), lab("Launch site", siteSel)),
        customBox, lab("Orbit", orbSel), orbitBox,
        el("p", { class: "muted small" }, "The launch only goes ahead if the rocket's staged Δv, from this site, can reach the orbit with your satellite on top."),
        msg, el("div", { class: "modal-actions" }, go));
      const dlg = modal("Launch a satellite", form);
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        msg.textContent = ""; go.disabled = true; go.textContent = "Checking the rocket…";
        const body = { vehicle: vehSel.value, site: siteSel.value, name: nameIn.value.trim() || null,
          orbit: { perigee_alt: +peri.value * 1000, apogee_alt: +apo.value * 1000, inclination_deg: +inc.value,
            longitude_deg: lon.closest("label").hidden ? null : +lon.value } };
        if (satSel.value === "custom") {
          const camSat = cat.satellites.find((s) => s.id === cCam.value);
          body.custom_satellite = { name: cName.value, dry_mass: +cDry.value, propellant: +cProp.value, isp: +cIsp.value, area_m2: +cArea.value, camera: camSat ? camSat.fleet.camera : null };
        } else body.satellite = satSel.value;
        try {
          const s = await api("/api/company/launch", { method: "POST", body });
          dlg.close(); toast(`${s.name} is in orbit.`);
          await poll(); select(s.id);
        } catch (err) { msg.textContent = err.message; }
        finally { go.disabled = false; go.textContent = "Launch"; }
      });
    }

    // ----- probe dialog
    async function openProbe() {
      let cat;
      try { cat = await getCatalog(); } catch (e) { toast(e.message, "error"); return; }
      const num = (v, attrs = {}) => el("input", { class: "text-input", type: "number", value: v, ...attrs });
      const name = el("input", { class: "text-input", value: "Pathfinder", maxlength: 48 });
      const tgt = el("select", { class: "text-input" }, ...Object.entries(PLANET_NAMES).filter(([k]) => !["uranus", "neptune"].includes(k)).map(([k, v]) => el("option", { value: k }, v)));
      tgt.value = "mars";
      const veh = el("select", { class: "text-input" }, ...cat.vehicles.map((v) => el("option", { value: v.id }, `${v.name} (${v.agency})`)));
      veh.value = "falcon_heavy";
      const dry = num(1500, { min: 10 }), prop = num(1600, { min: 0 }), isp = num(320, { min: 0 });
      const capture = el("input", { type: "checkbox", checked: true });
      const depart = el("input", { class: "text-input", type: "date" }), tof = num(300, { min: 20, max: 6000 });
      const pork = el("canvas", { class: "porkchop" });
      const best = el("p", { class: "small" }, "Find a launch window to fill in the dates.");
      const msg = el("p", { class: "form-msg" });
      const lab = (t, i) => el("label", { class: "stack" }, el("span", { class: "field-label" }, t), i);
      let grid = null;
      const find = el("button", { class: "btn", type: "button" }, "Find launch windows");
      find.addEventListener("click", async () => {
        find.disabled = true; best.textContent = "Solving Lambert's problem on a grid of dates…";
        try {
          const today = new Date().toISOString().slice(0, 10);
          const span = { mercury: 400, venus: 700, mars: 900, jupiter: 500, saturn: 450 }[tgt.value];
          const r = await simulate("physics", "interplanetary_porkchop", { origin: "earth", target: tgt.value, depart_start: today, depart_days: span, n_depart: 45, n_tof: 32 });
          grid = r.result;
          const b = grid.best;
          depart.value = b.depart.slice(0, 10); tof.value = Math.round(b.tof_days);
          best.textContent = `Best: leave ${b.depart.slice(0, 10)}, arrive ${b.arrive.slice(0, 10)} (${Math.round(b.tof_days)} days), C3 ${fmt(b.c3_km2s2, 3)} km²/s², total Δv from low orbit into orbit there ${fmt(b.total_delta_v / 1000, 3)} km/s. Click the chart to pick another.`;
          drawPork();
        } catch (e) { best.textContent = e.message; } finally { find.disabled = false; }
      });
      function drawPork() {
        if (!grid) return;
        const W = pork.clientWidth || 520, H = 200, dpr = Math.min(2, devicePixelRatio);
        pork.width = W * dpr; pork.height = H * dpr; pork.style.height = `${H}px`;
        const ctx = pork.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        const Z = grid.total_delta_v, nx = grid.depart.length, ny = grid.tof_days.length;
        const vals = Z.flat().filter((v) => v != null), lo = Math.min(...vals), hi = Math.min(Math.max(...vals), lo * 2.2);
        const cw = W / nx, ch = H / ny;
        for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
          const v = Z[j][i];
          if (v == null) { ctx.fillStyle = "#1b2436"; } else {
            const f = Math.min(1, (v - lo) / (hi - lo)); // low Δv = ember, high = navy
            ctx.fillStyle = `rgb(${Math.round(255 - f * 230)},${Math.round(91 - f * 60)},${Math.round(46 + f * 20)})`;
          }
          ctx.fillRect(i * cw, H - (j + 1) * ch, cw + 0.5, ch + 0.5);
        }
        const bi = grid.depart_jd.findIndex((x) => Math.abs(x - grid.best.depart_jd) < 1e-6), bj = grid.tof_days.findIndex((x) => Math.abs(x - grid.best.tof_days) < 1e-6);
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.strokeRect(bi * cw, H - (bj + 1) * ch, cw, ch);
        ctx.fillStyle = "rgba(255,255,255,.85)"; ctx.font = "11px Plex, system-ui";
        ctx.fillText(`departure ${grid.depart[0]} → ${grid.depart[nx - 1]}`, 6, H - 6);
        ctx.fillText(`flight time ${Math.round(grid.tof_days[0])} to ${Math.round(grid.tof_days[ny - 1])} days ↑`, 6, 14);
      }
      pork.addEventListener("click", (e) => {
        if (!grid) return;
        const r = pork.getBoundingClientRect(), nx = grid.depart.length, ny = grid.tof_days.length;
        const i = Math.min(nx - 1, Math.floor(((e.clientX - r.left) / r.width) * nx)), j = Math.min(ny - 1, Math.floor(((r.bottom - e.clientY) / r.height) * ny));
        const v = grid.total_delta_v[j][i];
        depart.value = grid.depart[i]; tof.value = Math.round(grid.tof_days[j]);
        best.textContent = v == null ? "No transfer there." : `Leave ${grid.depart[i]}, ${Math.round(grid.tof_days[j])} days, C3 ${fmt(grid.c3[j][i], 3)} km²/s², total ${fmt(v, 3)} km/s.`;
      });
      tgt.addEventListener("change", () => { grid = null; pork.getContext("2d").clearRect(0, 0, pork.width, pork.height); best.textContent = "Find a launch window to fill in the dates."; });
      const go = el("button", { class: "btn primary big", type: "submit" }, "Launch probe");
      const form = el("form", { class: "launch-form", novalidate: true },
        el("div", { class: "grid2" }, lab("Probe name", name), lab("Destination", tgt), lab("Rocket", veh), lab("Probe dry mass (kg)", dry),
          lab("Propellant for arrival (kg)", prop), lab("Engine Isp (s)", isp)),
        el("label", { class: "check" }, capture, " Enter orbit on arrival (needs the propellant for the capture burn); untick for a flyby"),
        el("div", { class: "row-gap" }, find), pork, best,
        el("div", { class: "grid2" }, lab("Departure date", depart), lab("Flight time (days)", tof)),
        msg, el("div", { class: "modal-actions" }, go));
      const dlg = modal("Send a probe", form);
      requestAnimationFrame(drawPork);
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!depart.value) { msg.textContent = "Pick a departure date (use Find launch windows)."; return; }
        go.disabled = true; msg.textContent = "";
        try {
          const p = await api("/api/company/probes", { method: "POST", body: { name: name.value.trim() || "Probe", vehicle: veh.value, target: tgt.value,
            depart: depart.value, tof_days: +tof.value, probe_dry_mass: +dry.value, probe_propellant: +prop.value, probe_isp: +isp.value, capture: capture.checked } });
          dlg.close(); toast(`${p.name} is booked for ${PLANET_NAMES[tgt.value]}.`);
          await poll(); select(p.id);
        } catch (err) { msg.textContent = err.message; } finally { go.disabled = false; }
      });
    }

    // ----- boot
    api("/api/company").then((r) => {
      if (!alive) return;
      company = r.company;
      if (company) build(); else founding();
    }).catch((e) => wrap.replaceChildren(el("p", { class: "muted" }, e.message)));
    return cleanup;
  },
};
