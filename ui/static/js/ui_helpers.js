(function () {
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\s*' + name + '\s*=\s*([^;]+)');
    return m ? m.pop() : '';
  }
  if (!window.getCSRF) window.getCSRF = () => getCookie('csrftoken');

  if (!window.fetchJSON) {
    window.fetchJSON = async function (url, options = {}) {
      const res = await fetch(url, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          ...(options.method && options.method !== 'GET'
            ? { 'Content-Type': 'application/json', 'X-CSRFToken': window.getCSRF() }
            : {})
        },
        ...options
      });
      const ct = res.headers.get('content-type') || '';
      const txt = await res.text();
      if (!res.ok) throw new Error(`HTTP ${res.status} ${url}: ${txt.slice(0,200)}`);
      if (!ct.includes('application/json')) throw new Error(`No-JSON desde ${url}: ${txt.slice(0,200)}`);
      return JSON.parse(txt);
    };
  }
})();

