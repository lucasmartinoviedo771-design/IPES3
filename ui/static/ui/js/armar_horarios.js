// ARMAR-HORARIOS v8 (interactivo)
(function(){
  console.log('ARMAR-HORARIOS v8 cargado');
  const $ = s => document.querySelector(s);
  const selTurno   = $('#id_turno');
  const selPlan    = $('#id_plan');
  const selCarrera = $('#id_carrera');
  const selMateria = $('#id_materia') || $('#id_materia_id');
  const grid = $('#grid');
  const btnSave = document.querySelector('button, input[type="submit"]');

  // util

const HH = s => { const m=String(s||'').match(/^(\d{1,2}):(\d{2})/); return m? (+m[1] + (+m[2]/60)) : 0; };



// REEMPLAZA tu loadSlots por esta versión
async function loadSlots(){
  const turno = (document.querySelector('#id_turno')?.value || 'manana')
                 .toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'');
  const candidates = [];
  if (window.API_GRILLA_CONFIG) candidates.push(window.API_GRILLA_CONFIG);
  candidates.push('/ui/api/grilla_config/', '/api/grilla_config/');

  let lastError = null, data = null;
  for (const base of candidates){
    try{
      const url = new URL(base, location.origin);
      url.searchParams.set('turno', turno);
      const {ok,status,json} = await fetchJSON(url);
      console.log('[grilla] intento', url.href, status, json);
      if (!ok) { lastError = `HTTP ${status}`; continue; }
      data = json; break;
    }catch(e){ lastError = e.message; }
  }
  if (!data){
    throw new Error('No se pudo obtener grilla: ' + (lastError || 'sin detalles'));
  }

  // aceptar varias formas del payload
  const rows = data.rows || data.bloques || data.config || data;
  const seen = new Set();
  const slots = (rows||[])
    .map(r => ({
      ini: window.toHM(r.ini || r.inicio || r.hora_inicio || r[0]),
      fin: window.toHM(r.fin || r.hora_fin || r[1]),
      recreo: !!r.recreo
    }))
    .filter(s => s.ini && s.fin)
    .filter(s => { const k=`${s.ini}|${s.fin}|${s.recreo?1:0}`; if (seen.has(k)) return false; seen.add(k); return true; })
    .sort((a,b) => (HH(a.ini)-HH(b.ini)) || (HH(a.fin)-HH(b.fin)));

  if (!slots.length) throw new Error('La API devolvió 0 filas de grilla');
  return slots;
}

  // --- Lógica de Renderizado e Interacción ---
  function render(slots){
    if(!grid) return;
    const mkRow = (s) => `
      <tr class="${s.recreo?'is-break':''}">
        <th>${s.ini} – ${s.fin}</th>
        <td data-dia="lu" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>
        <td data-dia="ma" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>
        <td data-dia="mi" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>
        <td data-dia="ju" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>
        <td data-dia="vi" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>
        <th>${s.ini} – ${s.fin}</th>
        <td data-dia="sa" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>
      </tr>`;
    grid.innerHTML = `
      <table class="sheet__table" id="tabla-horarios">
        <thead><tr>
          <th>Hora (L–V)</th><th>Lunes</th><th>Martes</th><th>Miércoles</th>
          <th>Jueves</th><th>Viernes</th><th>Hora (Sábado)</th><th>Sábado</th>
        </tr></thead>
        <tbody>${slots.map(mkRow).join('')}</tbody>
      </table>`;
    grid.querySelectorAll('tr.is-break td[data-dia]').forEach(td=>td.classList.add('is-break'));
    bindClicks();
  }

  function keyFrom(td){ return `${td.dataset.dia}|${td.dataset.ini}|${td.dataset.fin}`; }

  function bindClicks(){
    grid.addEventListener('click', (ev)=>{
      const td = ev.target.closest('td[data-dia]');
      if(!td || td.classList.contains('is-break') || td.classList.contains('is-busy')) return;
      td.classList.toggle('is-sel');
      updateCounter();
    });
    updateCounter();
  }

  function updateCounter(){
    const n = grid.querySelectorAll('td.is-sel').length;
    console.log('Bloques seleccionados:', n);
    const counterEl = document.getElementById('block-counter');
    if(counterEl) counterEl.textContent = `${n} bloques seleccionados`;
  }

  async function loadBusy(){
    if(!window.API_HORARIOS_OCUPADOS) return;
    const params = new URLSearchParams({profesorado_id:selCarrera?.value||'', plan_id:selPlan?.value|| '', materia_id:selMateria?.value||'', turno:normTurno(selTurno?.value)});
    const u = `${window.API_HORARIOS_OCUPADOS}?${params.toString()}`;
    const data = await window.fetchJSON(u);
    const index = {};
    grid.querySelectorAll('td[data-dia]').forEach(td => index[keyFrom(td)] = td);
    (data || []).forEach(it=>{
      const dia = String(it.dia).toLowerCase().slice(0,2);
      const ini = window.toHM(it.inicio), fin = window.toHM(it.fin);
      const td = index[`${dia}|${ini}|${fin}`];
      if(!td) return;
      td.classList.remove('is-sel');
      td.classList.add('is-busy');
      const mat = it.materia || it.materia_nombre || it['materia__nombre'] || '';
      const doc = it.docente || [it['docente__apellido'], it['docente__nombre']].filter(Boolean).join(', ') || 'Sin Docente';
      td.innerHTML = `<div><strong>${mat}</strong><br><small>${doc}</small></div>`;
    });
    updateCounter();
  }

  // --- Lógica de Guardado ---
  btnSave?.addEventListener('click', async (ev)=>{
    ev.preventDefault();
    const items = [...grid.querySelectorAll('td.is-sel')].map(td => ({dia:td.dataset.dia, inicio:td.dataset.ini, fin:td.dataset.fin}));
    if(!items.length) return alert('No hay bloques seleccionados.');
    const payload = {profesorado_id:selCarrera?.value, plan_id:selPlan?.value, materia_id:selMateria?.value, turno:normTurno(selTurno?.value), items};
    try{
      const r = await fetch(window.API_HORARIO_SAVE, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
      if(!r.ok){
        const j = await r.json().catch(()=>({}));
        const msg = j?.error || j?.detail || `Error ${r.status}`;
        return alert(msg);
      }
      alert('Malla guardada.');
      await loadBusy();
    }catch(e){
      console.error(e);
      alert('No se pudo guardar.');
    }
  });

  // --- Ejecución Principal ---
  async function run(){
    try{
      const slots = await loadSlots();
      render(slots);
      await loadBusy();
      console.log('Grilla lista', {turno: normTurno(selTurno?.value), filas: slots.length});
    }catch(e){
      console.error('No se pudo construir la grilla', e);
      if(grid) grid.innerHTML = `<p class="empty">No se pudo cargar la grilla.</p>`;
    }
  }

  [selTurno, selPlan, selCarrera, selMateria].forEach(el => el && el.addEventListener('change', run));
  document.addEventListener('DOMContentLoaded', run);
})();