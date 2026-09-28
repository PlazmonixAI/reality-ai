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
    id: "grapher", domain: "mathematics", title: "Calculus Grapher",
    blurb: "Plot any function with its derivative, tangent line and the area under the curve.",
    load: () => import("./grapher.js"),
    art: sky(`<rect width="240" height="128" fill="#fff"/><line x1="10" y1="64" x2="230" y2="64" stroke="#7b8796"/><line x1="120" y1="6" x2="120" y2="122" stroke="#7b8796"/>
      <path d="M10 90 C50 10 80 10 120 64 S190 118 230 38 L230 64 L10 64z" fill="#2a78d6" opacity=".12"/>
      <path d="M10 90 C50 10 80 10 120 64 S190 118 230 38" fill="none" stroke="#2a78d6" stroke-width="3"/>
      <line x1="40" y1="100" x2="140" y2="20" stroke="#1baf7a" stroke-width="2.5"/>`),
  },
];
