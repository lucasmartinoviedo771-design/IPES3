// ui/static/ui/js/utils/onReady.js
export function onReady(fn) {
  if (document.readyState !== 'loading') {
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

if (typeof window !== 'undefined') {
  window.onReady = onReady;
}
