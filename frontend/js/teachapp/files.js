// A teacher's own files: slides, PDFs, pictures and short videos, uploaded once and shown on the board.
import { el } from "../core/ui.js";
import { api, toast, confirmBox, when } from "../core/session.js";

const ACCEPT = ".pdf,.ppt,.pptx,.doc,.docx,.png,.jpg,.jpeg,.webp,.gif,.mp4,.webm";
const KIND = { pdf: "PDF", ppt: "Slides", pptx: "Slides", doc: "Document", docx: "Document", png: "Picture", jpg: "Picture",
  jpeg: "Picture", webp: "Picture", gif: "Picture", mp4: "Video", webm: "Video" };
const size = (n) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

async function upload(file) {
  const r = await fetch(`/api/teach/files?name=${encodeURIComponent(file.name)}`, {
    method: "POST", body: file, credentials: "same-origin", headers: { "Content-Type": file.type || "application/octet-stream" } });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Upload failed (${r.status})`);
  return data;
}

/** What a file looks like inside a board window: the picture, the video, or the PDF in the browser's viewer. */
export function fileWindowContent(f) {
  const src = `/api/teach/files/${f.id}`;
  if (["png", "jpg", "jpeg", "webp", "gif"].includes(f.ext)) return el("img", { class: "ta-file-img", src, alt: f.name });
  if (["mp4", "webm"].includes(f.ext)) return el("video", { class: "ta-file-video", src, controls: true, preload: "metadata" });
  if (f.viewable_pdf) return el("iframe", { class: "ta-file-pdf", src: f.ext === "pdf" ? src : `${src}?as_pdf=true`, title: f.name });
  return el("div", { class: "ta-file-none" },
    el("p", {}, `${f.name} can't be shown inside the browser on this server.`),
    el("p", { class: "muted small" }, "In PowerPoint or Word use File › Save As › PDF, then upload the PDF: it opens right on the board, page by page."),
    el("a", { class: "btn small", href: `${src}?download=true` }, "Download the original"));
}

/** Upload box, storage bar and file list. onShow(file) puts a file on the board. */
export function filesManager({ compact = false, onShow } = {}) {
  const list = el("div", { class: "ta-files" }, el("p", { class: "muted small" }, "Loading your files…"));
  const bar = el("div", { class: "ta-storage" });
  const input = el("input", { type: "file", accept: ACCEPT, multiple: true, hidden: true });
  const pick = el("button", { type: "button", class: "btn primary small" }, "Upload files");
  const drop = el("div", { class: "ta-drop" }, pick, el("span", { class: "muted small" }, compact ? "PDF, slides, pictures, videos" :
    "PDF, PowerPoint, Word, pictures (PNG, JPG) and short videos (MP4), up to 25 MB each. Or drop files here."), input);
  pick.onclick = () => input.click();
  input.onchange = () => send([...input.files]);
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); send([...e.dataTransfer.files]); });

  async function send(files) {
    for (const f of files) {
      pick.disabled = true; pick.textContent = `Uploading ${f.name}…`;
      try {
        const r = await upload(f);
        toast(["ppt", "pptx", "doc", "docx"].includes(r.file.ext) && !r.converted
          ? `${f.name} saved. Save it as PDF to show it on the board.` : `${f.name} uploaded.`);
      } catch (err) { toast(err.message, "error"); }
    }
    pick.disabled = false; pick.textContent = "Upload files"; input.value = "";
    refresh();
  }

  async function refresh() {
    try {
      const [{ files }, me] = await Promise.all([api("/api/teach/files"), api("/api/teach/me")]);
      const used = me.teacher.storage_used, limit = me.teacher.storage_limit;
      bar.replaceChildren(el("div", { class: "ta-storage-track" }, el("div", { style: `width:${Math.min(100, (100 * used) / limit).toFixed(1)}%` })),
        el("span", { class: "muted small" }, `${size(used)} of ${size(limit)} used`));
      list.replaceChildren(...(files.length ? files.map(row) : [el("p", { class: "muted small" }, "No files yet. Upload the slides and PDFs you teach with.")]));
    } catch (err) { list.replaceChildren(el("p", { class: "muted small" }, err.message)); }
  }

  function row(f) {
    return el("div", { class: "ta-file" },
      el("span", { class: `ta-file-kind k-${KIND[f.ext]?.toLowerCase()}` }, KIND[f.ext] || f.ext),
      el("div", { class: "ta-file-name" }, el("b", { title: f.name }, f.name), el("small", {}, `${size(f.size)} · ${when(f.created_at)}`)),
      el("div", { class: "ta-file-actions" },
        onShow ? el("button", { type: "button", class: "btn small primary", onclick: () => onShow(f) }, "Show") : "",
        compact ? "" : el("a", { class: "btn small", href: `/api/teach/files/${f.id}?download=true` }, "Download"),
        el("button", { type: "button", class: "btn small", "aria-label": `Delete ${f.name}`, onclick: async () => {
          if (!(await confirmBox("Delete this file?", f.name, "Delete", true))) return;
          try { await api(`/api/teach/files/${f.id}`, { method: "DELETE" }); refresh(); } catch (err) { toast(err.message, "error"); }
        } }, "Delete")));
  }

  refresh();
  return el("div", { class: "ta-filesbox" }, drop, bar, list);
}

export default {
  title: "My files",
  mount(root) {
    root.append(el("div", { class: "ta-head" }, el("h1", {}, "My files"),
      el("p", { class: "muted" }, "Your own slides, PDFs, pictures and clips. Press Show to open one on the board.")),
    filesManager({ onShow: (f) => { location.hash = `#/board?show=${f.id}`; } }));
  },
};
