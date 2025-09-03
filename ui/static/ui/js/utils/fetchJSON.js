// ui/static/ui/js/utils/fetchJSON.js
export async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, ...opts });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
// Sin bundler: exponer global
if (typeof window !== "undefined") window.fetchJSON = fetchJSON;