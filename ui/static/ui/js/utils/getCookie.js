// ui/static/ui/js/utils/getCookie.js
export function getCookie(name) {
  const m = document.cookie.match('(^|;)\s*' + name + '\s*=\s*([^;]+)');
  return m ? m.pop() : '';
}

if (typeof window !== 'undefined') {
  window.getCookie = getCookie;
}

