// ui/js/utils/loadPlanes.js
(function(){
  
  function setOptions(sel, items){
    if (!sel) return;
    sel.innerHTML = '<option value="">--------</option>' +
      items.map(o => `<option value="${o.id}">${o.nombre}</option>`).join('');
  }
  function normalize(list){
    return list.map(p => ({
      id: p.id ?? p.pk ?? p.value,
      nombre: p.nombre ?? p.label ?? p.resolucion ?? p.text
    })).filter(x => x.id != null && x.nombre);
  }
  function fromMap(profId, selPlan){
    const raw = (window.PLANES_MAP && window.PLANES_MAP[profId]) || [];
    setOptions(selPlan, normalize(raw));
  }

  window.loadPlanes = async function(form, selProf, selPlan){
    if (!form || !selProf || !selPlan) return;
    const profId = selProf.value;
    setOptions(selPlan, []); // reset
    if (!profId) return;

    const base = (form.dataset.planesUrl || '').trim();
    // 1) si hay endpoint, probá AJAX
    if (base) {
      const url = base + (base.includes('?') ? '&' : '?') + 'profesorado=' + encodeURIComponent(profId);
      try {
        const data = await fetchJSON(url);
        const arr = Array.isArray(data) ? data : (data.results || data.planes || []);
        const items = normalize(arr);
        if (items.length) { setOptions(selPlan, items); return; }
      } catch(e) {
        console.warn('[loadPlanes] fallo AJAX, uso PLANES_MAP', e);
      }
    }
    // 2) fallback al mapa renderizado por servidor
    fromMap(profId, selPlan);
  };
})();