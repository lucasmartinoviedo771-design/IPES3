console.log('OFERTA-AJAX v15 cargado');
// ui/js/oferta_ajax.js  v15 (robustez en datos de API)
(function () {
  const $ = (q) => document.querySelector(q);
  const selCarrera = $('#id_carrera') || $('#id_profesorado') || document.querySelector("select[name*='profesorado' i],select[name*='carrera' i]");
  const selPlan    = $('#id_plan');
  const $sheets    = $('#sheets');

  // --- constantes y normalizadores ---
  const TURNOS = ['manana','tarde','vespertino', 'sabado'];
  const DIAS = ['lu','ma','mi','ju','vi','sa'];
  const DIA_LABEL = { lu:'Lunes', ma:'Martes', mi:'Miércoles', ju:'Jueves', vi:'Viernes', sa:'Sábado' };

  const norm = (s) => String(s||'').trim();
  const normTurno = (t) => norm(t).toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'');

  function normDia(raw){
    const t = String(raw||'').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'');
    if (t.startsWith('lu')) return 'lu';
    if (t.startsWith('ma') && !t.startsWith('mie')) return 'ma';
    if (t.startsWith('mi')) return 'mi';
    if (t.startsWith('ju')) return 'ju';
    if (t.startsWith('vi')) return 'vi';
    if (t.startsWith('sa')) return 'sa';
    return '';
  }

  // --- helpers de datos ---
  const HH = (hhmm) => {
    const m = String(hhmm||'').match(/^(\d{1,2}):(\d{2})/);
    if (!m) return NaN;
    return parseInt(m[1],10) + parseInt(m[2],10)/60;
  };

  

  function getMateria(it){
    return it.materia || it.materia_nombre || it['materia__nombre'] || '';
  }
  function getDocente(it){
    const d1 = it.docente || '';
    const d2 = [it['docente__apellido'], it['docente__nombre']].filter(Boolean).join(', ');
    return d1 || d2 || 'Sin Docente';
  }

  // --- Lógica de carga ---
  

  async function cargarPlanes() {
    if (!selCarrera || !selPlan) return;
    selPlan.innerHTML = '<option value="">---------</option>';
    selPlan.disabled = true;
    if (!selCarrera.value) return;

    const u = new URL(window.API_PLANES, location.origin);
    u.searchParams.set('carrera', selCarrera.value);
    const data = await window.fetchJSON(u);
    (data?.results || []).forEach(p => selPlan.add(new Option(p.nombre, p.id)));
    selPlan.disabled = false;
  }

  function pickTurnoByYear(itemsByYear){
    const byYear = {};
    [1,2,3,4].forEach(anio => {
      const cnt = {manana:0,tarde:0,vespertino:0, sabado:0};
      (itemsByYear[anio] || []).forEach(it=>{
        const k = normTurno(it.turno);
        if (k in cnt) cnt[k]++; 
      });
      let chosen = Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0][0];
      if (cnt[chosen] === 0) {
        const arr = itemsByYear[anio] || [];
        const hs = arr.map(x => HH(x.inicio)).filter(x => !isNaN(x)).sort((a,b)=>a-b);
        const median = hs.length ? hs[Math.floor(hs.length/2)] : NaN;
        if (!isNaN(median)) {
          if (median < 13) chosen = 'manana';
          else if (median < 18) chosen = 'tarde';
          else chosen = 'vespertino';
        } else {
          chosen = 'manana';
        }
      }
      byYear[anio] = chosen || 'manana';
    });
    return byYear;
  }

  function uniqSlots(arr){
    const seen = new Set(); const out = [];
    for (const s of arr){
      const k = `${s.ini}|${s.fin}|${s.recreo?1:0}`;
      if (seen.has(k)) continue;
      seen.add(k); out.push(s);
    }
    out.sort((a,b) => (HH(a.ini)-HH(b.ini)) || (HH(a.fin)-HH(b.fin)));
    return out;
  }

  const gridCache = {};
  async function loadGridForTurno(turno){
    const key = TURNOS.includes(turno) ? turno : 'manana';
    if (gridCache[key]) return gridCache[key];

    const u = new URL(window.API_GRILLA_CONFIG, location.origin);
    u.searchParams.set('turno', key);

    const cfg = await window.fetchJSON(u);
    const rows = cfg?.rows || cfg?.bloques || [];
    let slots = rows.map(r => ({
      ini: window.toHM(r.ini || r.inicio || r.hora_inicio || r[0]),
      fin: window.toHM(r.fin || r.hora_fin || r[1]),
      recreo: !!r.recreo
    })).filter(s => s.ini && s.fin);

    slots = uniqSlots(slots);
    gridCache[key] = slots;
    return slots;
  }

  // --- Lógica de renderizado ---
  function buildSheetHTML(anio, slots, metaText){
    return `
      <div class="sheet" data-anio="${anio}">
        <div class="only-print" style="margin-bottom:8px">
          <div style="font-weight:800;font-size:18pt;margin-bottom:2mm;">Horarios por Profesorado</div>
          <div style="font-size:11pt;opacity:.9;">${metaText} — ${anio}° Año</div>
        </div>
        <div class="sheet__title">${anio}° Año</div>
        <div class="sheet__meta">${metaText}</div>
        <table class="sheet__table">
          <thead>
            <tr><th>Hora</th>${DIAS.map(d=>`<th>${DIA_LABEL[d]}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${slots.map(s=>`
              <tr class="${s.recreo ? 'is-break':''}">
                <th>${s.ini} – ${s.fin}</th>
                ${DIAS.map(d=>`<td data-dia="${d}" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>`).join('')}
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  }

  function paintYear(sheetEl, items, turno){
    const tdIndex = {};
    sheetEl.querySelectorAll('td[data-dia]').forEach(td=>{
      const key = `${td.dataset.dia}|${td.dataset.ini}|${td.dataset.fin}`;
      tdIndex[key] = td;
    });

    (items || []).forEach(it=>{
      const kturno = normTurno(it.turno);
      if (TURNOS.includes(turno) && kturno && kturno !== turno) return;

      const dia = normDia(it.dia);
      const ini = window.toHM(it.inicio);
      const fin = window.toHM(it.fin);
      const key = `${dia}|${ini}|${fin}`;
      const td = tdIndex[key];
      if (!td || td.closest('tr').classList.contains('is-break')) return;

      const materiaTxt = getMateria(it);
      const docenteTxt = getDocente(it);

      td.innerHTML = `
        <div class="cell">
          <div class="cell__materia">${materiaTxt}</div>
          <div class="cell__docente">${docenteTxt}</div>
          <div class="cell__extra">${it.comision || ''} ${it.aula ? '• '+it.aula : ''}</div>
        </div>`;
      td.classList.add('is-filled');
    });
  }

  function setEmpty(){
    $sheets.innerHTML = `<div class="empty">Sin resultados para los filtros seleccionados.</div>`;
  }

  async function cargar(){
    if (!$sheets) return;
    const profId = selCarrera?.value;
    const planId = selPlan?.value || '';
    if (!profId){ setEmpty(); return; }

    const u = new URL(window.API_OFERTA_PROFESORADO, location.origin);
    u.searchParams.set('profesorado_id', profId);
    if (planId) u.searchParams.set('plan_id', planId);
    const data = await window.fetchJSON(u);
    const total = Object.values(data||{}).reduce((a,v)=>a+(v?.length||0),0);
    if (!total){ setEmpty(); return; }

    const turnoByYear = pickTurnoByYear(data);
    const uniqueTurnos = [...new Set(Object.values(turnoByYear))];
    const slotsByTurno = {};
    for (const t of uniqueTurnos) slotsByTurno[t] = await loadGridForTurno(t);

    const carreraTxt = selCarrera?.selectedOptions?.[0]?.text || '';
    const planTxt    = selPlan?.selectedOptions?.[0]?.text || '';
    const metaByYear = (anio)=>[carreraTxt, planTxt?`Plan: ${planTxt}`:null, `Turno: ${turnoByYear[anio][0].toUpperCase()+turnoByYear[anio].slice(1)}`].filter(Boolean).join(' • ');
    $sheets.innerHTML = `
      <div class="sheets__grid">
        ${[1,2,3,4].map(anio => buildSheetHTML(anio, slotsByTurno[turnoByYear[anio]] || [], metaByYear(anio))).join('')}
      </div>`;

    [1,2,3,4].forEach(anio=>{
      const sheet = $sheets.querySelector(`.sheet[data-anio="${anio}"]`);
      if (!sheet) return;
      paintYear(sheet, data[anio] || [], turnoByYear[anio]);
    });
  }

  // --- Eventos ---
  selCarrera?.addEventListener('change', async () => { await cargarPlanes(); await cargar(); });
  selPlan?.addEventListener('change', () => cargar().catch(console.error));

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('btn-print');
    if (btn) btn.addEventListener('click', () => {
      const carreraTxt = selCarrera?.selectedOptions?.[0]?.text || '';
      const planTxt    = selPlan?.selectedOptions?.[0]?.text || '';
      document.title = `Horarios - ${carreraTxt}${planTxt?` - ${planTxt}`:''}`;
      window.print();
    });
    (async ()=>{ if (selCarrera?.value) await cargarPlanes(); await cargar(); })().catch(console.error);
  });
})();