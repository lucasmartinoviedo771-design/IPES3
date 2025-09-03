// ui/static/ui/js/utils/loadPlanes.js
window.loadPlanes = async function(form, selProf, selPlan) {
  const url = form.getAttribute('data-planes-url');
  if (!url || !selProf) return;

  const profId = selProf.value;
  selPlan.innerHTML = '<option value="">---------</option>';
  if (!profId) return;

  try {
    const r = await window.fetchJSON(url + '?profesorado=' + encodeURIComponent(profId));
    if (!r.ok) return;
    const data = await r.json();
    (data.planes || []).forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id; opt.textContent = p.nombre;
      selPlan.appendChild(opt);
    });
  } catch (e) { /* silencio */ }
};