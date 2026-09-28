// Catalogue of simulations. Each entry lazy-loads its module, whose default export is
// { mount(root) -> cleanup }. Add new simulations here.

const sky = (inner) => `<svg viewBox="0 0 240 128" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;

export const DOMAINS = [
  { id: "physics", label: "Physics" },
  { id: "chemistry", label: "Chemistry" },
  { id: "mathematics", label: "Mathematics" },
];

export const SIMS = [
  {
    id: "projectile", domain: "physics", title: "Projectile Motion",
    blurb: "Fire cannonballs, baseballs and more — with or without air resistance, on Earth or the Moon.",
    load: () => import("./projectile.js"),
    art: sky(`<rect width="240" height="128" fill="#bfe3ff"/><rect y="104" width="240" height="24" fill="#6cbf5b"/>
      <path d="M30 100 Q120 -10 210 104" fill="none" stroke="#2a78d6" stroke-width="3" stroke-dasharray="7 5"/>
      <rect x="18" y="92" width="26" height="14" rx="3" fill="#39424e"/><rect x="28" y="84" width="30" height="9" rx="3" fill="#4b5563" transform="rotate(-40 30 90)"/>
      <circle cx="150" cy="38" r="7" fill="#39424e"/>`),
  },
  {
    id: "orbits", domain: "physics", title: "Gravity & Orbits",
    blurb: "Launch a satellite at any speed and angle. Watch circles, ellipses, escapes and crashes.",
    load: () => import("./orbits.js"),
    art: sky(`<rect width="240" height="128" fill="#081228"/><ellipse cx="120" cy="64" rx="92" ry="44" fill="none" stroke="#86b6ef" stroke-width="2.5"/>
      <circle cx="96" cy="64" r="20" fill="#2a78d6"/><path d="M84 56 q8 -8 18 -2 q-4 10 -14 8z" fill="#1baf7a"/><circle cx="212" cy="64" r="5" fill="#eb6834"/>
      <circle cx="30" cy="20" r="1" fill="#fff"/><circle cx="200" cy="18" r="1" fill="#fff"/><circle cx="60" cy="110" r="1" fill="#fff"/>`),
  },
  {
    id: "hohmann", domain: "physics", title: "Hohmann Transfer",
    blurb: "Plan the classic two-burn transfer between circular orbits — from LEO to GEO or Earth to Mars.",
    load: () => import("./hohmann.js"),
    art: sky(`<rect width="240" height="128" fill="#081228"/><circle cx="110" cy="64" r="26" fill="none" stroke="#86b6ef" stroke-dasharray="4 4"/>
      <circle cx="110" cy="64" r="56" fill="none" stroke="#86b6ef" stroke-dasharray="4 4"/><path d="M136 64 A41 32 0 0 0 54 64" fill="none" stroke="#eb6834" stroke-width="3"/>
      <circle cx="110" cy="64" r="10" fill="#2a78d6"/><circle cx="136" cy="64" r="4" fill="#fff"/><circle cx="54" cy="64" r="4" fill="#fff"/>`),
  },
  {
    id: "earth-moon", domain: "physics", title: "Earth–Moon Voyage",
    blurb: "Three-body gravity: send a spacecraft toward the Moon and try for a free-return loop.",
    load: () => import("./earth_moon.js"),
    art: sky(`<rect width="240" height="128" fill="#081228"/><circle cx="50" cy="64" r="14" fill="#2a78d6"/><circle cx="196" cy="64" r="7" fill="#c9ced6"/>
      <path d="M58 56 C110 10 200 30 204 60 C206 90 120 110 58 72" fill="none" stroke="#eb6834" stroke-width="2.5"/>`),
  },
  {
    id: "springs", domain: "physics", title: "Masses & Springs",
    blurb: "Hang a mass on a spring, pull it and let go. Explore damping, period and energy.",
    load: () => import("./springs.js"),
    art: sky(`<rect width="240" height="128" fill="#eef4fb"/><rect x="60" y="6" width="120" height="8" fill="#7b8796"/>
      <polyline points="120,14 108,22 132,30 108,38 132,46 108,54 132,62 120,70" fill="none" stroke="#39424e" stroke-width="3"/>
      <rect x="100" y="70" width="40" height="34" rx="5" fill="#2a78d6"/><text x="120" y="92" fill="#fff" font-size="13" text-anchor="middle" font-family="sans-serif">1 kg</text>`),
  },
  {
    id: "pendulum", domain: "physics", title: "Pendulum Lab",
    blurb: "Swing a pendulum to large angles and see why the small-angle period breaks down.",
    load: () => import("./pendulum.js"),
    art: sky(`<rect width="240" height="128" fill="#f5f0e6"/><rect x="80" y="8" width="80" height="6" fill="#7b8796"/>
      <line x1="120" y1="14" x2="160" y2="96" stroke="#39424e" stroke-width="2.5"/><circle cx="160" cy="96" r="13" fill="#eb6834"/>
      <path d="M120 60 A46 46 0 0 1 140 56" fill="none" stroke="#2a78d6" stroke-width="2"/><line x1="120" y1="14" x2="120" y2="110" stroke="#7b8796" stroke-dasharray="4 4"/>`),
  },
  {
    id: "rocket", domain: "physics", title: "Rocket Lab",
    blurb: "Design a two-stage rocket, see its delta-v budget, and let the optimiser size the stages.",
    load: () => import("./rocket.js"),
    art: sky(`<rect width="240" height="128" fill="#0e1f3a"/><rect x="104" y="30" width="22" height="70" rx="3" fill="#e8ecf2"/>
      <rect x="107" y="14" width="16" height="18" rx="2" fill="#c9ced6"/><path d="M107 14 L115 2 L123 14z" fill="#eb6834"/>
      <path d="M106 100 L115 124 L124 100z" fill="#eda100"/><rect x="150" y="30" width="16" height="70" fill="#2a78d6"/><rect x="150" y="14" width="16" height="16" fill="#1baf7a"/>`),
  },
  {
    id: "waves", domain: "physics", title: "Waves on a String",
    blurb: "Wiggle, pulse and tune a string. Find standing waves, reflections and damping.",
    load: () => import("./waves.js"),
    art: sky(`<rect width="240" height="128" fill="#eef4fb"/><rect x="10" y="44" width="22" height="40" fill="#39424e"/>
      ${[...Array(24)].map((_, i) => `<circle cx="${40 + i * 8}" cy="${64 - 26 * Math.sin(i / 23 * Math.PI * 2)}" r="3.2" fill="${i % 10 ? "#e34948" : "#1baf7a"}"/>`).join("")}
      <rect x="228" y="40" width="6" height="48" fill="#39424e"/>`),
  },
  {
    id: "interference", domain: "physics", title: "Wave Interference",
    blurb: "Shine light through one, two or many slits and see the fringes form on the screen.",
    load: () => import("./interference.js"),
    art: sky(`<rect width="240" height="128" fill="#0a0f1c"/>${[...Array(9)].map((_, i) => `<circle cx="40" cy="64" r="${14 + i * 14}" fill="none" stroke="#1baf7a" stroke-opacity="${0.7 - i * 0.06}" stroke-width="3"/>`).join("")}
      <rect x="34" y="0" width="8" height="128" fill="#c9ced6"/><rect x="34" y="52" width="8" height="6" fill="#0a0f1c"/><rect x="34" y="70" width="8" height="6" fill="#0a0f1c"/>
      ${[...Array(13)].map((_, i) => `<rect x="214" y="${i * 10}" width="16" height="6" fill="#1baf7a" opacity="${Math.cos((i - 6) * 0.5) ** 2}"/>`).join("")}`),
  },
  {
    id: "lenses", domain: "physics", title: "Lenses & Mirrors",
    blurb: "Trace principal rays through lenses and off mirrors; find real and virtual images.",
    load: () => import("./lenses.js"),
    art: sky(`<rect width="240" height="128" fill="#fdfdfb"/><line x1="0" y1="80" x2="240" y2="80" stroke="#9aa6b5"/>
      <path d="M120 20 Q134 64 120 110 Q106 64 120 20" fill="#5598e7" fill-opacity=".25" stroke="#5598e7" stroke-width="2"/>
      <line x1="50" y1="80" x2="50" y2="44" stroke="#eb6834" stroke-width="4"/><polyline points="50,44 120,44 200,100" fill="none" stroke="#2a78d6" stroke-width="2"/>
      <polyline points="50,44 200,110" fill="none" stroke="#eb6834" stroke-width="2"/><line x1="190" y1="80" x2="190" y2="104" stroke="#1c5cab" stroke-width="4"/>`),
  },
  {
    id: "refraction", domain: "physics", title: "Bending Light",
    blurb: "Aim a laser across air, water, glass and diamond. Snell's law, reflection and total internal reflection.",
    load: () => import("./refraction.js"),
    art: sky(`<rect width="240" height="64" fill="#f4f7fb"/><rect y="64" width="240" height="64" fill="#b9d3f2"/>
      <line x1="120" y1="0" x2="120" y2="128" stroke="#7b8796" stroke-dasharray="5 5"/>
      <line x1="50" y1="0" x2="120" y2="64" stroke="#e34948" stroke-width="5"/><line x1="120" y1="64" x2="160" y2="128" stroke="#e34948" stroke-width="5" stroke-opacity=".8"/>
      <line x1="120" y1="64" x2="190" y2="0" stroke="#e34948" stroke-width="4" stroke-opacity=".25"/>`),
  },
  {
    id: "circuit", domain: "physics", title: "Circuit Builder",
    blurb: "Build DC circuits with batteries, resistors, bulbs and switches. Kirchhoff's laws solve them live.",
    load: () => import("./circuit.js"),
    art: sky(`<rect width="240" height="128" fill="#f3f6f0"/><rect x="40" y="24" width="160" height="80" fill="none" stroke="#8a6d3b" stroke-width="5"/>
      <rect x="28" y="48" width="24" height="32" fill="#39424e"/><rect x="28" y="48" width="24" height="10" fill="#eda100"/>
      <circle cx="120" cy="24" r="16" fill="#ffe27a" stroke="#39424e" stroke-width="2"/><rect x="176" y="54" width="48" height="20" fill="#d9b98a" transform="rotate(90 200 64)"/>
      ${[...Array(8)].map((_, i) => `<circle cx="${60 + i * 18}" cy="104" r="3" fill="#2a78d6"/>`).join("")}`),
  },
  {
    id: "charges", domain: "physics", title: "Charges & Fields",
    blurb: "Drag charges around to see field lines, field vectors and the voltage map; measure with a sensor.",
    load: () => import("./charges.js"),
    art: sky(`<defs><radialGradient id="cp" cx="30%" cy="50%" r="45%"><stop offset="0" stop-color="#e34948" stop-opacity=".55"/><stop offset="1" stop-color="#f0efec" stop-opacity="0"/></radialGradient>
      <radialGradient id="cn" cx="70%" cy="50%" r="45%"><stop offset="0" stop-color="#2a78d6" stop-opacity=".55"/><stop offset="1" stop-color="#f0efec" stop-opacity="0"/></radialGradient></defs>
      <rect width="240" height="128" fill="#f0efec"/><rect width="240" height="128" fill="url(#cp)"/><rect width="240" height="128" fill="url(#cn)"/>
      ${[-40, -20, 0, 20, 40].map((d) => `<path d="M72 64 Q120 ${64 + d * 2.2} 168 64" fill="none" stroke="#16202c" stroke-opacity=".6" stroke-width="1.5"/>`).join("")}
      <circle cx="72" cy="64" r="13" fill="#e34948"/><circle cx="168" cy="64" r="13" fill="#2a78d6"/>`),
  },
  {
    id: "collisions", domain: "physics", title: "Collisions Lab",
    blurb: "Set up billiard-ball collisions, elastic or sticky, and watch momentum stay constant.",
    load: () => import("./collisions.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><rect x="8" y="8" width="224" height="112" fill="none" stroke="#39424e" stroke-width="3"/>
      <circle cx="80" cy="70" r="18" fill="#eb6834"/><circle cx="150" cy="56" r="24" fill="#2a78d6"/>
      <line x1="80" y1="70" x2="118" y2="66" stroke="#16202c" stroke-width="2.5"/><path d="M118 66 l-9 -5 l1 10z" fill="#16202c"/>`),
  },
  {
    id: "ramp", domain: "physics", title: "Forces on a Ramp",
    blurb: "Slide a block on an incline: gravity, normal force, static and kinetic friction, pushes.",
    load: () => import("./ramp.js"),
    art: sky(`<rect width="240" height="128" fill="#dff0ff"/><rect y="108" width="240" height="20" fill="#6cbf5b"/>
      <path d="M20 108 L200 108 L200 28 Z" fill="#c8a878" stroke="#8a6d3b" stroke-width="2"/>
      <rect x="118" y="40" width="30" height="30" fill="#2a78d6" transform="rotate(-24 133 70)"/>
      <line x1="140" y1="58" x2="110" y2="72" stroke="#e34948" stroke-width="3"/>`),
  },
  {
    id: "skate", domain: "physics", title: "Energy Skate Park",
    blurb: "Build a track, drop a skater, and watch kinetic, potential and thermal energy trade places.",
    load: () => import("./skate.js"),
    art: sky(`<rect width="240" height="128" fill="#bfe3ff"/><rect y="112" width="240" height="16" fill="#6cbf5b"/>
      <path d="M16 20 C60 120 180 120 224 20" fill="none" stroke="#7b5a3a" stroke-width="7"/>
      <circle cx="52" cy="54" r="7" fill="#eb6834"/><rect x="45" y="61" width="14" height="12" rx="3" fill="#2a78d6"/>
      <rect x="170" y="30" width="12" height="40" fill="#2a78d6"/><rect x="186" y="50" width="12" height="20" fill="#eb6834"/><rect x="202" y="64" width="12" height="6" fill="#1baf7a"/>`),
  },
  {
    id: "rlc", domain: "physics", title: "RC, RL & RLC Circuits",
    blurb: "Charge a capacitor, build up an inductor's current, ring an RLC circuit and find resonance.",
    load: () => import("./rlc.js"),
    art: sky(`<rect width="240" height="128" fill="#f8fafc"/><rect x="30" y="24" width="180" height="84" fill="none" stroke="#8a6d3b" stroke-width="4"/>
      <circle cx="30" cy="66" r="14" fill="#f8fafc" stroke="#39424e" stroke-width="3"/>
      <polyline points="70,24 76,16 84,32 92,16 100,32 106,24" fill="#f8fafc" stroke="#2a78d6" stroke-width="3"/>
      <path d="M126 24 a6 6 0 0 1 12 0 a6 6 0 0 1 12 0 a6 6 0 0 1 12 0" fill="none" stroke="#eb6834" stroke-width="3"/>
      <line x1="184" y1="12" x2="184" y2="36" stroke="#1baf7a" stroke-width="3"/><line x1="194" y1="12" x2="194" y2="36" stroke="#1baf7a" stroke-width="3"/>`),
  },
  {
    id: "faraday", domain: "physics", title: "Faraday's Law",
    blurb: "Push a magnet through a coil and light a bulb. Flux, induced EMF and Lenz's law.",
    load: () => import("./faraday.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/>${[0, 1, 2, 3, 4, 5].map((i) => `<ellipse cx="${140 + i * 6}" cy="60" rx="9" ry="30" fill="none" stroke="#c98843" stroke-width="2.5"/>`).join("")}
      <rect x="40" y="52" width="36" height="16" fill="#2a78d6"/><rect x="76" y="52" width="36" height="16" fill="#e34948"/>
      <path d="M112 60 C140 10 60 10 40 60" fill="none" stroke="#4a3aa7" stroke-opacity=".4" stroke-width="1.5"/>
      <circle cx="150" cy="110" r="9" fill="#ffe27a" stroke="#39424e" stroke-width="2"/>`),
  },
  {
    id: "gas", domain: "chemistry", title: "Gas Properties",
    blurb: "Pump gas into a box, heat it, squeeze it. Pressure from PV = nRT and real molecular speeds.",
    load: () => import("./gas.js"),
    art: sky(`<rect width="240" height="128" fill="#eef4fb"/><rect x="30" y="18" width="150" height="92" fill="#fff" stroke="#39424e" stroke-width="3"/>
      <rect x="180" y="18" width="10" height="92" fill="#7b8796"/>${[...Array(18)].map((_, i) =>
      `<circle cx="${45 + (i * 37) % 125}" cy="${30 + (i * 23) % 70}" r="4" fill="${i % 3 ? "#2a78d6" : "#eb6834"}"/>`).join("")}`),
  },
  {
    id: "kinetics", domain: "chemistry", title: "Reaction Rates",
    blurb: "Watch A turn into B for zero, first and second-order reactions; heat it up with Arrhenius.",
    load: () => import("./kinetics.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M20 20 C60 80 100 100 220 108" fill="none" stroke="#2a78d6" stroke-width="3"/>
      <path d="M20 108 C60 48 100 28 220 20" fill="none" stroke="#eb6834" stroke-width="3" stroke-dasharray="7 4"/>
      <line x1="20" y1="112" x2="224" y2="112" stroke="#7b8796"/><line x1="20" y1="10" x2="20" y2="112" stroke="#7b8796"/>`),
  },
  {
    id: "ph", domain: "chemistry", title: "pH Scale",
    blurb: "Dilute acids and bases, strong or weak, and read the pH, [H₃O⁺] and [OH⁻].",
    load: () => import("./ph.js"),
    art: sky(`<defs><linearGradient id="phg" x1="0" x2="1"><stop offset="0" stop-color="#e34948"/><stop offset=".3" stop-color="#eda100"/>
      <stop offset=".5" stop-color="#1baf7a"/><stop offset=".75" stop-color="#2a78d6"/><stop offset="1" stop-color="#4a3aa7"/></linearGradient></defs>
      <rect width="240" height="128" fill="#fff"/><rect x="20" y="96" width="200" height="14" rx="7" fill="url(#phg)"/>
      <path d="M86 20 v56 q0 12 12 12 h44 q12 0 12 -12 v-56" fill="#fff" stroke="#39424e" stroke-width="3"/><rect x="89" y="46" width="62" height="39" fill="#eda100" opacity=".8"/>`),
  },
  {
    id: "equilibrium", domain: "chemistry", title: "Chemical Equilibrium",
    blurb: "Mix reactants and products, set K, and solve the ICE table for any reaction.",
    load: () => import("./equilibrium.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><rect x="36" y="40" width="22" height="70" fill="#2a78d6" opacity=".35"/><rect x="62" y="80" width="22" height="30" fill="#2a78d6"/>
      <rect x="110" y="60" width="22" height="50" fill="#eb6834" opacity=".35"/><rect x="136" y="84" width="22" height="26" fill="#eb6834"/>
      <rect x="180" y="110" width="22" height="0" fill="#1baf7a"/><rect x="180" y="30" width="22" height="80" fill="#1baf7a"/><text x="120" y="24" font-size="18" text-anchor="middle" fill="#39424e" font-family="sans-serif">⇌</text>`),
  },
  {
    id: "titration", domain: "chemistry", title: "Acid–Base Titration",
    blurb: "Drip base into acid (or acid into base), watch the indicator flip and find the equivalence point.",
    load: () => import("./titration.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/><rect x="112" y="4" width="14" height="60" fill="#fff" stroke="#39424e" stroke-width="2"/>
      <rect x="114" y="30" width="10" height="32" fill="#86b6ef"/><path d="M104 80 L78 122 L160 122 L134 80 Z" fill="#e87ba4" stroke="#39424e" stroke-width="3"/>
      <path d="M150 110 C170 110 176 30 200 26 L230 24" fill="none" stroke="#2a78d6" stroke-width="3"/>`),
  },
  {
    id: "buffers", domain: "chemistry", title: "Buffers",
    blurb: "Add acid or base to a buffer and to pure water side by side. Why does the buffer barely budge?",
    load: () => import("./buffers.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/><rect x="36" y="40" width="64" height="72" fill="#eda100" opacity=".8"/>
      <rect x="140" y="40" width="64" height="72" fill="#e34948" opacity=".8"/>
      <path d="M30 30 v84 h76 v-84 M134 30 v84 h76 v-84" fill="none" stroke="#39424e" stroke-width="3"/>`),
  },
  {
    id: "beers", domain: "chemistry", title: "Beer's Law Lab",
    blurb: "Shine light of any colour through a coloured solution and measure absorbance and transmittance.",
    load: () => import("./beers.js"),
    art: sky(`<rect width="240" height="128" fill="#1a2230"/><rect x="10" y="44" width="40" height="40" fill="#39424e"/>
      <rect x="50" y="60" width="60" height="8" fill="#1baf7a"/><rect x="110" y="30" width="26" height="70" fill="#a3319e" opacity=".85"/>
      <rect x="136" y="60" width="50" height="8" fill="#1baf7a" opacity=".35"/><rect x="186" y="40" width="46" height="48" fill="#39424e"/>`),
  },
  {
    id: "molecules", domain: "chemistry", title: "Molecule Shapes",
    blurb: "VSEPR in 3D: see how bonds and lone pairs arrange themselves, and measure the bond angles.",
    load: () => import("./molecules.js"),
    art: sky(`<rect width="240" height="128" fill="#131c2c"/><line x1="120" y1="64" x2="120" y2="16" stroke="#c9ced6" stroke-width="6"/>
      <line x1="120" y1="64" x2="74" y2="96" stroke="#c9ced6" stroke-width="6"/><line x1="120" y1="64" x2="168" y2="96" stroke="#c9ced6" stroke-width="6"/>
      <circle cx="120" cy="16" r="12" fill="#7cc76b"/><circle cx="74" cy="96" r="12" fill="#7cc76b"/><circle cx="168" cy="96" r="12" fill="#7cc76b"/>
      <circle cx="120" cy="64" r="16" fill="#eb6834"/><circle cx="160" cy="44" r="16" fill="#eb6834" opacity=".35"/>`),
  },
  {
    id: "atom", domain: "chemistry", title: "Build an Atom",
    blurb: "Add protons, neutrons and electrons. Make elements, ions and isotopes; check which are stable.",
    load: () => import("./atom.js"),
    art: sky(`<rect width="240" height="128" fill="#0f1a2b"/><circle cx="120" cy="64" r="30" fill="none" stroke="#c9ced6" stroke-opacity=".4"/>
      <circle cx="120" cy="64" r="52" fill="none" stroke="#c9ced6" stroke-opacity=".4"/>
      <circle cx="115" cy="60" r="7" fill="#e34948"/><circle cx="125" cy="62" r="7" fill="#9aa6b5"/><circle cx="118" cy="70" r="7" fill="#9aa6b5"/><circle cx="126" cy="70" r="7" fill="#e34948"/>
      <circle cx="150" cy="64" r="5" fill="#5598e7"/><circle cx="90" cy="64" r="5" fill="#5598e7"/><circle cx="120" cy="12" r="5" fill="#5598e7"/>`),
  },
  {
    id: "grapher", domain: "mathematics", title: "Calculus Grapher",
    blurb: "Plot any function with its derivative, tangent line and the area under the curve.",
    load: () => import("./grapher.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><line x1="10" y1="64" x2="230" y2="64" stroke="#7b8796"/><line x1="120" y1="6" x2="120" y2="122" stroke="#7b8796"/>
      <path d="M10 90 C50 10 80 10 120 64 S190 118 230 38 L230 64 L10 64z" fill="#2a78d6" opacity=".12"/>
      <path d="M10 90 C50 10 80 10 120 64 S190 118 230 38" fill="none" stroke="#2a78d6" stroke-width="3"/>
      <line x1="40" y1="100" x2="140" y2="20" stroke="#1baf7a" stroke-width="2.5"/>`),
  },
  {
    id: "unitcircle", domain: "mathematics", title: "Unit Circle & Trig",
    blurb: "Drag around the unit circle and see exact sin, cos and tan values trace out their graphs.",
    load: () => import("./unitcircle.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><circle cx="70" cy="64" r="48" fill="none" stroke="#39424e" stroke-width="2"/>
      <line x1="70" y1="64" x2="112" y2="40" stroke="#16202c" stroke-width="2.5"/><line x1="70" y1="64" x2="112" y2="64" stroke="#eb6834" stroke-width="4"/>
      <line x1="112" y1="64" x2="112" y2="40" stroke="#2a78d6" stroke-width="4"/>
      <path d="M130 64 C145 20 160 20 175 64 S205 108 220 64" fill="none" stroke="#2a78d6" stroke-width="2.5"/>`),
  },
  {
    id: "fourier", domain: "mathematics", title: "Fourier Series",
    blurb: "Build square, sawtooth and triangle waves from sines and cosines, one harmonic at a time.",
    load: () => import("./fourier.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M10 90 H60 V38 H120 V90 H180 V38 H230" fill="none" stroke="#eb6834" stroke-width="2" stroke-dasharray="6 4"/>
      <path d="M10 88 C30 94 40 90 58 60 C66 34 80 30 100 40 C112 44 116 30 122 60 C130 90 150 94 178 60 C186 34 200 30 230 40" fill="none" stroke="#2a78d6" stroke-width="3"/>`),
  },
  {
    id: "phase", domain: "mathematics", title: "Slope Fields & Phase Portraits",
    blurb: "See differential equations as flows: click to draw solutions, find and classify equilibria.",
    load: () => import("./phase.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/>${[...Array(40)].map((_, i) => { const x = 18 + (i % 8) * 29, y = 14 + Math.floor(i / 8) * 25, a = Math.atan2(-(x - 120) * 0.5, y - 64); return `<line x1="${x - 8 * Math.cos(a)}" y1="${y - 8 * Math.sin(a)}" x2="${x + 8 * Math.cos(a)}" y2="${y + 8 * Math.sin(a)}" stroke="#7b8796" stroke-width="1.5"/>`; }).join("")}
      <ellipse cx="120" cy="64" rx="70" ry="40" fill="none" stroke="#2a78d6" stroke-width="3"/><circle cx="120" cy="64" r="5" fill="#eb6834"/>`),
  },
  {
    id: "vectors", domain: "mathematics", title: "Vector Addition",
    blurb: "Drag two vectors: see their sum, difference, projection, dot and cross products.",
    load: () => import("./vectors.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M40 110 L150 90 L200 30 L90 50 Z" fill="#1baf7a" opacity=".1"/>
      <line x1="40" y1="110" x2="150" y2="90" stroke="#2a78d6" stroke-width="4"/><line x1="40" y1="110" x2="90" y2="50" stroke="#eb6834" stroke-width="4"/>
      <line x1="40" y1="110" x2="200" y2="30" stroke="#1baf7a" stroke-width="4"/>`),
  },
  {
    id: "probability", domain: "mathematics", title: "Probability & the CLT",
    blurb: "Explore normal, binomial, Poisson and more — then watch sample means become a bell curve.",
    load: () => import("./probability.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/>${[4, 12, 26, 44, 60, 66, 60, 44, 26, 12, 4].map((hh, i) => `<rect x="${32 + i * 16}" y="${110 - hh * 1.4}" width="12" height="${hh * 1.4}" fill="#2a78d6" opacity=".45"/>`).join("")}
      <path d="M26 110 C80 110 90 14 122 14 C154 14 164 110 218 110" fill="none" stroke="#eb6834" stroke-width="3"/>`),
  },
  {
    id: "taylor", domain: "mathematics", title: "Taylor Series",
    blurb: "Approximate functions with polynomials, move the centre, and find where the series stops working.",
    load: () => import("./taylor.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M10 64 C40 10 70 10 100 64 S160 118 190 64 S220 30 230 40" fill="none" stroke="#2a78d6" stroke-width="3"/>
      <path d="M40 120 C70 30 100 30 120 64 S150 100 170 20" fill="none" stroke="#eb6834" stroke-width="2.5" stroke-dasharray="7 5"/><circle cx="120" cy="64" r="5" fill="#1baf7a"/>`),
  },
  {
    id: "riemann", domain: "mathematics", title: "Riemann Sums",
    blurb: "Left, right, midpoint, trapezoid and Simpson: approximate integrals and compare how fast they converge.",
    load: () => import("./riemann.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/>${[0, 1, 2, 3, 4, 5, 6].map((i) => { const x = 30 + i * 26, hh = 8 + i * i * 2.2; return `<rect x="${x}" y="${112 - hh}" width="26" height="${hh}" fill="#2a78d6" fill-opacity=".22" stroke="#2a78d6"/>`; }).join("")}
      <path d="M30 110 C90 106 150 80 212 8" fill="none" stroke="#16202c" stroke-width="3"/>`),
  },
  {
    id: "complex", domain: "mathematics", title: "Complex Plane",
    blurb: "Drag complex numbers: see sums, products (angles add!), quotients and the n-th roots.",
    load: () => import("./complex.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><line x1="0" y1="80" x2="240" y2="80" stroke="#7b8796"/><line x1="100" y1="0" x2="100" y2="128" stroke="#7b8796"/>
      <line x1="100" y1="80" x2="150" y2="50" stroke="#2a78d6" stroke-width="3.5"/><line x1="100" y1="80" x2="115" y2="30" stroke="#eb6834" stroke-width="3.5"/>
      <line x1="100" y1="80" x2="60" y2="10" stroke="#1baf7a" stroke-width="3.5"/>`),
  },
  {
    id: "transform", domain: "mathematics", title: "Linear Transformations",
    blurb: "Bend the plane with a 2×2 matrix: determinant as area, eigenvectors that keep their direction.",
    load: () => import("./transform.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/>${[-3, -2, -1, 0, 1, 2, 3].map((k) => `<line x1="${120 + k * 22 - 60}" y1="128" x2="${120 + k * 22 + 60}" y2="0" stroke="#2a78d6" stroke-opacity=".35"/><line x1="0" y1="${64 + k * 18}" x2="240" y2="${64 + k * 18 - 30}" stroke="#2a78d6" stroke-opacity=".35"/>`).join("")}
      <path d="M120 64 L162 57 L184 18 L142 25 Z" fill="#eb6834" fill-opacity=".25" stroke="#eb6834" stroke-width="2"/>`),
  },
  {
    id: "newton", domain: "mathematics", title: "Newton's Method",
    blurb: "Slide down tangent lines to a root — and see when Newton's method cycles or runs away.",
    load: () => import("./newton.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><line x1="0" y1="90" x2="240" y2="90" stroke="#7b8796"/>
      <path d="M20 120 C80 110 140 70 220 8" fill="none" stroke="#2a78d6" stroke-width="3"/><line x1="100" y1="128" x2="230" y2="20" stroke="#eb6834" stroke-width="2"/>
      <circle cx="196" cy="30" r="4" fill="#eb6834"/><circle cx="137" cy="90" r="5" fill="#16202c"/>`),
  },
  {
    id: "engine", domain: "physics", title: "Heat Engines",
    blurb: "Run Carnot, Otto and Diesel cycles on a PV diagram: net work is the enclosed area, and nothing beats Carnot.",
    load: () => import("./engine.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M40 20 C70 40 110 60 200 70 L190 110 C120 104 80 90 50 60 Z" fill="#2a78d6" fill-opacity=".2" stroke="#2a78d6" stroke-width="3"/>
      <line x1="30" y1="118" x2="230" y2="118" stroke="#7b8796"/><line x1="30" y1="10" x2="30" y2="118" stroke="#7b8796"/>`),
  },
  {
    id: "blackbody", domain: "physics", title: "Blackbody Spectrum",
    blurb: "Heat a body from lava to blue stars: Planck's curve, Wien's peak shift and the T⁴ power law.",
    load: () => import("./blackbody.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><rect x="40" y="10" width="40" height="108" fill="url(#bbv)" opacity=".4"/>
      <defs><linearGradient id="bbv"><stop offset="0" stop-color="#7b3fe4"/><stop offset=".5" stop-color="#1baf7a"/><stop offset="1" stop-color="#e34948"/></linearGradient></defs>
      <path d="M10 118 C40 20 70 18 110 60 S190 112 230 116" fill="none" stroke="#2a78d6" stroke-width="3"/><path d="M10 118 C60 80 90 70 140 90 S200 114 230 117" fill="none" stroke="#eb6834" stroke-width="2" stroke-dasharray="6 5"/>`),
  },
  {
    id: "photoelectric", domain: "physics", title: "Photoelectric Effect",
    blurb: "Shine light on metals: only photons above the threshold frequency free electrons, however bright the lamp.",
    load: () => import("./photoelectric.js"),
    art: sky(`<rect width="240" height="128" fill="#101826"/><rect x="50" y="24" width="10" height="80" fill="#b8c4d3"/><rect x="180" y="24" width="10" height="80" fill="#7b8796"/>
      <path d="M10 6 L30 6 L60 90 L60 38 Z" fill="#7b3fe4" fill-opacity=".5"/>${[0, 1, 2, 3, 4].map((i) => `<circle cx="${80 + i * 22}" cy="${40 + (i * 13) % 50}" r="4" fill="#5598e7"/>`).join("")}`),
  },
  {
    id: "hydrogen", domain: "physics", title: "Hydrogen Atom",
    blurb: "Drop the electron between Bohr levels and see the emitted photon: Lyman, Balmer and Paschen lines.",
    load: () => import("./hydrogen.js"),
    art: sky(`<rect width="240" height="128" fill="#0f1a2b"/>${[20, 70, 90, 98, 102].map((y) => `<line x1="20" y1="${y}" x2="110" y2="${y}" stroke="#c9ced6" stroke-opacity=".6" stroke-width="2"/>`).join("")}
      <line x1="65" y1="90" x2="65" y2="74" stroke="#e34948" stroke-width="4"/>${[18, 34, 52].map((r) => `<circle cx="180" cy="64" r="${r}" fill="none" stroke="#c9ced6" stroke-opacity=".4"/>`).join("")}<circle cx="180" cy="64" r="5" fill="#e34948"/><circle cx="214" cy="64" r="5" fill="#5598e7"/>`),
  },
  {
    id: "decay", domain: "physics", title: "Radioactive Decay",
    blurb: "Watch 400 atoms decay at random while the totals follow exact half-life curves, including decay chains.",
    load: () => import("./decay.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/>${Array.from({ length: 60 }, (_, i) => `<rect x="${14 + (i % 12) * 18}" y="${12 + Math.floor(i / 12) * 22}" width="14" height="14" fill="${(i * 37) % 5 < 2 ? "#2a78d6" : "#eb6834"}"/>`).join("")}`),
  },
  {
    id: "relativity", domain: "physics", title: "Special Relativity",
    blurb: "Fly to a star near light speed: time dilation, length contraction and the twin paradox, computed exactly.",
    load: () => import("./relativity.js"),
    art: sky(`<rect width="240" height="128" fill="#0b1426"/><circle cx="30" cy="40" r="14" fill="#2a78d6"/><circle cx="212" cy="40" r="10" fill="#ffd479"/><ellipse cx="120" cy="40" rx="12" ry="7" fill="#e8ecf2"/>
      <circle cx="70" cy="92" r="24" fill="#fff" stroke="#2a78d6" stroke-width="3"/><circle cx="170" cy="92" r="24" fill="#fff" stroke="#eb6834" stroke-width="3"/>
      <line x1="70" y1="92" x2="84" y2="80" stroke="#16202c" stroke-width="2.5"/><line x1="170" y1="92" x2="170" y2="74" stroke="#16202c" stroke-width="2.5"/>`),
  },
  {
    id: "molarity", domain: "chemistry", title: "Molarity & Dilution",
    blurb: "Dissolve a solute, then add water: moles stay the same while the concentration drops (C₁V₁ = C₂V₂).",
    load: () => import("./molarity.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/><rect x="36" y="50" width="60" height="64" fill="#286edc" fill-opacity=".8"/><rect x="144" y="30" width="60" height="84" fill="#286edc" fill-opacity=".3"/>
      <path d="M32 20 V116 H100 V20 M140 20 V116 H208 V20" fill="none" stroke="#39424e" stroke-width="4"/>`),
  },
  {
    id: "galvanic", domain: "chemistry", title: "Galvanic Cells",
    blurb: "Build a battery from two metals: standard potentials, the Nernst equation, ΔG and the equilibrium constant.",
    load: () => import("./galvanic.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/><rect x="24" y="70" width="70" height="50" fill="#dce6f0"/><rect x="146" y="70" width="70" height="50" fill="#3c82e6" fill-opacity=".45"/>
      <rect x="52" y="44" width="14" height="66" fill="#9aa6b5"/><rect x="174" y="44" width="14" height="66" fill="#c46a2c"/><path d="M80 96 V62 H160 V96" fill="none" stroke="#d9c9a3" stroke-width="12"/>
      <path d="M59 44 V14 H181 V44" fill="none" stroke="#16202c" stroke-width="2.5"/><rect x="96" y="4" width="48" height="22" fill="#16202c"/><text x="120" y="20" fill="#1baf7a" font-size="12" text-anchor="middle" font-family="monospace">1.10 V</text>`),
  },
  {
    id: "realgas", domain: "chemistry", title: "Real Gases",
    blurb: "Van der Waals isotherms, the critical point and condensation: where real gases stop behaving ideally.",
    load: () => import("./realgas.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M40 118 C60 30 110 20 130 30 C150 45 190 110 225 118 Z" fill="#7b8796" fill-opacity=".15" stroke="#7b8796"/>
      <path d="M30 6 C40 60 48 76 60 76 L170 76 C190 90 210 104 230 108" fill="none" stroke="#2a78d6" stroke-width="3"/><path d="M30 20 C60 90 100 100 230 112" fill="none" stroke="#1baf7a" stroke-width="2"/>`),
  },
  {
    id: "vapor", domain: "chemistry", title: "Vapour Pressure & Boiling",
    blurb: "Why water boils at 71 °C on Everest: Clausius–Clapeyron vapour pressure against the air above.",
    load: () => import("./vapor.js"),
    art: sky(`<rect width="240" height="128" fill="#f7f9fc"/><rect x="50" y="56" width="110" height="44" fill="#2a78d6" fill-opacity=".35"/><path d="M50 30 V100 H160 V30" fill="none" stroke="#39424e" stroke-width="4"/>
      ${[0, 1, 2, 3, 4].map((i) => `<circle cx="${66 + i * 20}" cy="${70 + (i % 2) * 14}" r="${4 + (i % 3)}" fill="none" stroke="#fff" stroke-width="2"/>`).join("")}${[0, 1, 2, 3, 4].map((i) => `<path d="M${70 + i * 18} 118 q6 -18 12 0" fill="#eb6834"/>`).join("")}
      <rect x="196" y="16" width="12" height="96" rx="6" fill="#fff" stroke="#39424e" stroke-width="2"/><rect x="199" y="50" width="6" height="60" fill="#e34948"/>`),
  },
  {
    id: "profile", domain: "chemistry", title: "Reaction Energy Profile",
    blurb: "Activation energy, exothermic vs endothermic, and how a catalyst lowers the barrier without moving equilibrium.",
    load: () => import("./profile.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><path d="M10 70 H50 C80 70 90 10 120 10 C150 10 160 100 190 100 H230" fill="none" stroke="#2a78d6" stroke-width="3.5"/>
      <path d="M50 70 C80 70 95 42 120 42 C145 42 160 100 190 100" fill="none" stroke="#eb6834" stroke-width="3" stroke-dasharray="7 5"/>`),
  },
];
