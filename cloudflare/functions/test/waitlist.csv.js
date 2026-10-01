// Download the waitlist as CSV. Lives under /test, so the same username and password protect it.
export async function onRequestGet({ env }) {
  if (!env.WAITLIST) return new Response("The waitlist isn't set up yet.", { status: 503 });
  const rows = [["email", "joined_at", "page", "country"]];
  let cursor;
  do {
    const page = await env.WAITLIST.list({ prefix: "email:", cursor });
    for (const k of page.keys) {
      const v = JSON.parse((await env.WAITLIST.get(k.name)) || "{}");
      rows.push([v.email || k.name.slice(6), v.at || "", v.source || "", v.country || ""]);
    }
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n") + "\n";
  return new Response(csv, { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'attachment; filename="waitlist.csv"', "Cache-Control": "no-store" } });
}
