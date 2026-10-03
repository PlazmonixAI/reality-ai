// ASM Teach app shell: a separate product from ASM. Teachers get the board, experiments, files and their profile;
// the school admin gets the admin panel. The role comes from /api/teach/me.
//   teacher: #/board  #/teach  #/teach/<id>  #/lab  #/files  #/profile        school: #/admin  #/account
import { el } from "../core/ui.js";
import { api } from "../core/session.js";

const app = document.getElementById("app");
const nav = document.getElementById("ta-nav");
let cleanup = null, me = null;

const NAV = {
  teacher: [["board", "Board"], ["teach", "Experiments"], ["lab", "Lab"], ["files", "My files"], ["profile", "Profile"]],
  school: [["admin", "Teachers"], ["account", "School account"]],
};
const PAGES = {
  board: () => import("./board.js"), teach: () => import("../pages/teach.js"), lab: () => import("../sims/labbench.js"), files: () => import("./files.js"),
  profile: () => import("./profile.js"), admin: () => import("./admin.js"), account: () => import("./account.js"),
};

function parse() {
  const [path, qs = ""] = location.hash.replace(/^#/, "").split("?");
  return { path: path || "/", params: Object.fromEntries(new URLSearchParams(qs)) };
}

async function route() {
  try { cleanup?.(); } catch (e) { console.error(e); }
  cleanup = null;
  app.replaceChildren();
  const { path, params } = parse();
  const home = me.role === "school" ? "admin" : "board";
  let name = path.replace(/^\//, "").split("/")[0] || home;
  if (!NAV[me.role].some(([k]) => k === name)) name = home;
  nav.querySelectorAll("a").forEach((a) => a.classList.toggle("on", a.dataset.route === name));
  document.body.classList.toggle("ta-on-board", name === "board");
  const page = el("div", { class: `page ta-page ta-${name}` });
  app.append(page);
  try {
    const mod = await PAGES[name]();
    document.title = `${mod.default.title || "ASM Teach"} · ASM Teach`;
    cleanup = mod.default.mount(page, params, me) || null;
    const exp = path.match(/^\/teach\/([\w-]+)/);
    if (exp && me.role === "teacher") api("/api/teach/events", { method: "POST", body: { kind: "experiment", ref: exp[1] } }).catch(() => {});
  } catch (err) {
    console.error(err);
    page.append(el("p", { class: "empty" }, `Could not open this page: ${err.message}`));
  }
  window.scrollTo(0, 0);
}

async function start() {
  try { me = await api("/api/teach/me"); } catch { location.href = "/teach"; return; }
  const who = me.role === "school" ? `${me.school.name} · admin` : `${me.teacher.name} · ${me.teacher.school_name}`;
  document.getElementById("ta-who").textContent = who;
  nav.replaceChildren(...NAV[me.role].map(([k, label]) => el("a", { href: `#/${k}`, "data-route": k }, label)));
  document.getElementById("ta-signout").addEventListener("click", async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } finally { location.href = "/teach"; }
  });
  window.addEventListener("hashchange", route);
  route();
}

start();
