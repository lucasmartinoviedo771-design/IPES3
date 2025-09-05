// ui/static/ui/js/utils/fetchJSON.js
export async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, {
    credentials: 'same-origin',
    headers: { "X-Requested-With": "XMLHttpRequest" },
    ...opts
  });
  const txt = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${txt.slice(0, 200)}`);

  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) throw new Error(`Non-JSON response for ${url}`);

  return JSON.parse(txt);
}
// Sin bundler: exponer global
if (typeof window !== "undefined") window.fetchJSON = fetchJSON;