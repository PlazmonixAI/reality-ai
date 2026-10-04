// The Space Program header: one place for building and flying rockets and for running the space company.
import { el } from "../core/ui.js";

export const SPACE_NAME = "Space Program";

/** Tabs shown at the top of the rocket builder and of Mission Control. active: "fly" | "mission". */
export function spaceTabs(active) {
  const tab = (href, id, label, hint) => el("a", { class: `space-tab${active === id ? " on" : ""}`, href, title: hint, "aria-current": active === id ? "page" : null }, label);
  return el("nav", { class: "space-tabs", "aria-label": SPACE_NAME },
    el("span", { class: "space-brand" }, "ASM ", el("b", {}, SPACE_NAME)),
    tab("#/sim/spaceflight", "fly", "Build and fly", "Design engines and satellites, stack a rocket and fly it to orbit or the Moon"),
    tab("#/company", "mission", "Mission Control", "Your space company: fleet, launches, pictures and planet probes"));
}
