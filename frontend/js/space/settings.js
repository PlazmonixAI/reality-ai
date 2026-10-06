// Universe map settings: which names and layers are shown. Saved in this browser only.
import { el } from "../core/ui.js";

export const SETTINGS = [
  ["Names", [
    ["labels_planets", "Planets, moons and spacecraft", true],
    ["labels_stars", "Stars", true],
    ["labels_deepsky", "Nebulae and star clusters", true],
    ["labels_exoplanets", "Stars with planets", true],
    ["labels_galaxies", "Galaxies", true],
    ["labels_all_galaxies", "Catalogue galaxies too (NGC, IC, UGC…)", false],
    ["labels_structures", "Galaxy clusters, superclusters, walls and voids", true],
  ]],
  ["Constellations", [
    ["constellation_lines", "Constellation lines", true],
    ["constellation_names", "Constellation names", true],
    ["constellation_3d", "Real 3D shapes (lines join the actual stars)", false],
    ["constellation_hindi", "Hindi names too", false],
    ["constellation_borders", "Constellation boundaries", false],
  ]],
  ["Layers", [
    ["exoplanets", "Exoplanet systems", true],
    ["deep_sky", "Nebulae and clusters (glows)", true],
    ["open_clusters", "Open star clusters in the Milky Way", true],
    ["structures", "Shapes of clusters and superclusters", true],
    ["galaxy_art", "Galaxy pictures (simulated from each galaxy's type)", true],
    ["rings", "Distance rings", true],
  ]],
];
const KEY = "reality-asm.universe-settings";

export function createSettings() {
  const values = Object.fromEntries(SETTINGS.flatMap(([, items]) => items.map(([k, , d]) => [k, d])));
  values.density = 1;
  try { Object.assign(values, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch { /* storage unavailable */ }
  const listeners = [];
  return {
    get: (k) => values[k],
    set(k, v) { values[k] = v; try { localStorage.setItem(KEY, JSON.stringify(values)); } catch { /* storage unavailable */ } listeners.forEach((f) => f(k, v)); },
    onChange: (f) => listeners.push(f),
  };
}

/** A floating settings panel (gear button + sheet). */
export function settingsPanel(settings) {
  const sheet = el("div", { class: "ss-settings hidden", role: "dialog", "aria-label": "Map settings" });
  const close = () => sheet.classList.add("hidden");
  const draw = () => sheet.replaceChildren(
    el("div", { class: "ss-settings-head" }, el("b", {}, "Map settings"), el("button", { type: "button", class: "ss-close", "aria-label": "Close", onclick: close }, "×")),
    ...SETTINGS.map(([group, items]) => el("section", {}, el("h4", {}, group),
      ...items.map(([k, label]) => {
        const box = el("input", { type: "checkbox", checked: !!settings.get(k), onchange: () => settings.set(k, box.checked) });
        return el("label", { class: "ss-check" }, box, el("span", {}, label));
      }))),
    el("section", {}, el("h4", {}, "How many names"),
      (() => { const r = el("input", { type: "range", min: 0.4, max: 3, step: 0.1, value: settings.get("density"), "aria-label": "Label density", oninput: () => settings.set("density", Number(r.value)) }); return el("div", { class: "ss-density" }, el("span", {}, "Fewer"), r, el("span", {}, "More")); })()));
  draw();
  const btn = el("button", { class: "ss-gear", type: "button", title: "Map settings: names, constellations and layers", "aria-label": "Map settings", onclick: () => { sheet.classList.toggle("hidden"); } }, "⚙ Settings");
  return { btn, sheet };
}
