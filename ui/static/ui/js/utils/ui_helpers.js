window.UI ??= {};
window.UI.show = function(el, v) { if(!el) return; el.classList.toggle('hidden', !v); };