// ui/js/oferta_ajax.js  v10 (Profesorado + Plan)
(function () {
  const $ = (q) => document.querySelector(q);
  const selCarrera = $('#id_carrera') || $('#id_profesorado') || document.querySelector("select[name*='profesorado' i],select[name*='carrera' i]");
  const selPlan    = $('#id_plan');
  const $sheets    = $('#sheets');

  const DIAS = ['lu','ma','mi','ju','vi','sa'];
  const DIA_LABEL = { lu:'Lunes', ma:'Martes', mi:'Miércoles', ju:'Jueves', vi:'Viernes', sa:'Sábado' };
  const TURNOS = ['manana','tarde','vespertino'];
  const norm = (s) => String(s||'').trim();
  const normTurno = (t) => norm(t).toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'');

  async function fetchJSON(u) {
    const r = await fetch(u, { headers: { "X-Requested-With": "XMLHttpRequest" }});
    if (!r.ok) throw new Error(`HTTP ${r.status} for ${u}`);
    return r.json();
  }

  async function cargarPlanes() {
    if (!selCarrera || !selPlan) return;
    selPlan.innerHTML = '<option value="">---------</option>';
    selPlan.disabled = true;
    if (!selCarrera.value) return;

    const u = new URL(window.API_PLANES, location.origin);
    u.searchParams.set('carrera', selCarrera.value);
    const data = await fetchJSON(u);
    const list = data?.results || [];
    for (const p of list) selPlan.add(new Option(p.nombre, p.id));
    selPlan.disabled = list.length === 0;
  }

  function pickTurno(itemsByYear){
    const cnt = {manana:0,tarde:0,vespertino:0};
    Object.values(itemsByYear||{}).forEach(arr=>{
      (arr||[]).forEach(it=>{
        const k = normTurno(it.turno);
        if (k in cnt) cnt[k]++;
      });
    });
    return Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0][0] || 'manana';
  }

  async function loadGridConfig(turno) {
    const u = new URL(window.API_GRILLA_CONFIG, location.origin);
    u.searchParams.set('turno', TURNOS.includes(turno) ? turno : 'manana');
    const cfg = await fetchJSON(u);
    const rows = cfg?.rows || cfg?.bloques || [];
    return rows.map(r => ({
      ini: r.ini || r.inicio || r.hora_inicio || r[0],
      fin: r.fin || r.hora_fin || r[1],
      recreo: !!r.recreo
    })).filter(s => s.ini && s.fin);
  }

  function buildSheetsHTML(slots, metaText){
    const sheet = (anio) => `
      <div class="sheet">
        <div class="only-print" style="margin-bottom:8px">
          <div style="font-weight:800;font-size:18pt;margin-bottom:2mm;">Horarios por Profesorado</div>
          <div style="font-size:11pt;opacity:.9;">${metaText} — ${anio}° Año</div>
        </div>
        <div class="sheet__title">${anio}° Año</div>
        <div class="sheet__meta">${metaText}</div>
        <table class="sheet__table">
          <thead><tr>
            <th>Hora</th>
            ${DIAS.map(d => `<th>${DIA_LABEL[d]}</th>`).join('')}
          </tr></thead>
          <tbody>
            ${slots.map(s=>`
              <tr class="${s.recreo ? 'is-break':''}">
                <th>${s.ini} – ${s.fin}</th>
                ${DIAS.map(d=>`<td data-dia="${d}" data-ini="${s.ini}" data-fin="${s.fin}">${s.recreo?'Recreo':''}</td>`).join('')}
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
    return `<div class="sheets__grid">${[1,2,3,4].map(n=>sheet(n)).join('')}</div>`;
  }

  function paint(itemsByYear, slots, turno){
    const tdIndex = {};
    document.querySelectorAll('.sheet td[data-dia]').forEach(td=>{
      const key = `${td.dataset.dia}|${td.dataset.ini}|${td.dataset.fin}`;
      (tdIndex[key] ||= []).push(td);
    });
    const sheets = {};
    [1,2,3,4].forEach(n => sheets[n] = document.querySelector(`.sheet:nth-child(${n})`));

    const put = (anio, it) => {
      if (TURNOS.includes(turno) && normTurno(it.turno) !== turno) return;
      const dia = norm(it.dia).toLowerCase().slice(0,2);
      const key = `${dia}|${it.inicio}|${it.fin}`;
      const tds = tdIndex[key] || [];
      const sheet = sheets[anio];
      const td = tds.find(x => sheet && sheet.contains(x));
      if (!td || td.closest('tr').classList.contains('is-break')) return;
      td.innerHTML = `
        <div class="cell">
          <div class="cell__materia">${it.materia || ''}</div>
          <div class="cell__docente">${it.docente || ''}</div>
          <div class="cell__extra">${it.comision || ''} ${it.aula ? '• ' + it.aula : ''}</div>
        </div>`;
      td.classList.add('is-filled');
    };

    [1,2,3,4].forEach(anio=>{
      (itemsByYear[anio]||[]).forEach(it=>put(anio,it));
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

    // 1) datos por año, filtrando por plan si viene
    const u = new URL(window.API_OFERTA_PROFESORADO, location.origin);
    u.searchParams.set('profesorado_id', profId);
    if (planId) u.searchParams.set('plan_id', planId);
    const data = await fetchJSON(u);
    const total = Object.values(data||{}).reduce((a,v)=>a+(v?.length||0),0);
    if (!total){ setEmpty(); return; }

    // 2) turno predominante y malla
    const chosenTurno = pickTurno(data) || 'manana';
    const slots = await loadGridConfig(chosenTurno);
    if (!slots.length){ setEmpty(); return; }

    // 3) dibujar y pintar
    const carreraTxt = selCarrera?.selectedOptions?.[0]?.text || '';
    const planTxt    = selPlan?.selectedOptions?.[0]?.text || '';
    const meta = [carreraTxt, planTxt ? `Plan: ${planTxt}` : null, `Turno: ${chosenTurno[0].toUpperCase()+chosenTurno.slice(1)}`].filter(Boolean).join(' • ');
    $sheets.innerHTML = buildSheetsHTML(slots, meta);
    paint(data, slots, chosenTurno);
  }

  // eventos
  selCarrera?.addEventListener('change', async () => { await cargarPlanes(); await cargar(); });
  selPlan?.addEventListener('change', () => cargar().catch(console.error));

  // imprimir
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