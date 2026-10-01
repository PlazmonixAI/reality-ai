// Cloudflare Worker for the pre-launch site (Workers with static assets). The pages are the plain files in
// cloudflare/public; this script only handles the two dynamic parts, reusing the same code as the Pages functions:
//   POST /api/waitlist   store an email in the WAITLIST KV namespace
//   /test, /test/*       username and password (TEST_USERNAME / TEST_PASSWORD), and the waitlist CSV
// Anything else is a static file; unknown addresses get 404.html, the "Coming soon" page.
import { onRequestPost as joinWaitlist } from "./functions/api/waitlist.js";
import { onRequest as testGate } from "./functions/test/_middleware.js";
import { onRequestGet as waitlistCsv } from "./functions/test/waitlist.csv.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const assets = () => env.ASSETS.fetch(request);
    if (url.pathname === "/api/waitlist") {
      if (request.method !== "POST") return new Response("Method not allowed", { status: 405, headers: { Allow: "POST" } });
      return joinWaitlist({ request, env });
    }
    if (url.pathname === "/test" || url.pathname.startsWith("/test/")) {
      const next = () => {
        if (url.pathname !== "/test/waitlist.csv") return assets();
        return request.method === "GET" ? waitlistCsv({ env }) : new Response("Method not allowed", { status: 405 });
      };
      return testGate({ request, env, next });
    }
    return assets();
  },
};
