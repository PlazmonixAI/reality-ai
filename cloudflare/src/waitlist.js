// Pre-launch waitlist. The endpoint comes from waitlist_endpoint in cloudflare/site.config.json: "/api/waitlist"
// stores emails in Cloudflare KV (functions/api/waitlist.js); empty makes the form a placeholder that stores nothing.
const ENDPOINT = "__WAITLIST_ENDPOINT__";
const EMAIL = /^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,24}$/;

document.querySelectorAll("form[data-waitlist]").forEach((form) => {
  const input = form.querySelector("input[type=email]");
  const msg = form.querySelector(".wl-msg");
  const btn = form.querySelector("button");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = input.value.trim();
    if (!EMAIL.test(email)) { msg.textContent = "Kindly enter a valid email address."; msg.className = "wl-msg error"; input.focus(); return; }
    btn.disabled = true;
    try {
      if (ENDPOINT) {
        const body = new URLSearchParams({ email, source: location.pathname });
        const r = await fetch(ENDPOINT, { method: "POST", body });
        if (!r.ok) throw new Error();
      }
      form.classList.add("done");
      msg.textContent = "Thank you. We'll email you when the public beta opens.";
      msg.className = "wl-msg ok";
      input.value = "";
    } catch {
      msg.textContent = "That didn't go through. Please try again in a moment.";
      msg.className = "wl-msg error";
    } finally { btn.disabled = false; }
  });
});
