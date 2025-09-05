// --- helpers: CSRF + fetchJSON (idempotente si ya existen) ---
(function(){
  if (!window.getCSRF) {
    window.getCSRF = function () {
      const m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
      return m ? m[2] : '';
    };
  }
  if (!window.fetchJSON) {
    window.fetchJSON = async function (url, options = {}) {
      const res = await fetch(url, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          ...(options.method && options.method !== 'GET' ? {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.getCSRF()
          } : {})
        },
        ...options
      });
      const ct = res.headers.get('content-type') || '';
      const txt = await res.text();
      if (!res.ok) throw new Error(`HTTP ${res.status} ${url}: ${txt.slice(0,200)}`);
      if (!ct.includes('application/json')) throw new Error(`No-JSON: ${txt.slice(0,200)}`);
      return JSON.parse(txt);
    };
  }
})();

// ------------------ armar_horarios.js v13 ------------------
(function(){
  console.log('armar_horarios.js v13 cargado');

  // ---- CONFIG / HELPERS ----
  const grid = document.getElementById('grid-horarios');
  const $ = sel => document.querySelector(sel);
  const normTurno = s => (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');

  // Mapa HH:MM -> índice SLOTS (debe coincidir con SLOTS del backend)
  const SLOTS_MAP = {
    "07:45": 0,  "08:25": 1,  "09:05": 2,  "09:15": 3,  "09:55": 4,  "10:35": 5,  "10:45": 6,  "11:25": 7,  "12:05": 8,
    "13:00": 9,  "13:40":10,  "14:20":11,  "14:30":12,  "15:10":13,  "15:50":14,  "16:00":15,  "16:40":16,  "17:20":17,
    "18:10":18,  "18:50":19,  "19:30":20,  "19:40":21,  "20:20":22,  "21:00":23,  "21:10":24,  "21:50":25,  "22:30":26,
    // sábado
    "09:00":27,  "09:40":28,  "10:20":29,  "10:30":30,  "11:10":31,  "11:50":32,  "12:00":33,  "12:40":34,  "13:20":35,
  };

  function msg(text){ if (grid) grid.innerHTML = `<p class="muted">${text}</p>`; }

  // ---- RENDER (payload con {dias, lv, sab, rows}) ----
  function renderGridV2(payload){
    const { dias=[], lv=[], sab=[], rows=[] } = payload;
    const NOMBRES = {1:'Lun',2:'Mar',3:'Mié',4:'Jue',5:'Vie',6:'Sáb'};

    // Index de ocupadas: 'dia@HH:MM' → html
    const ocupados = {};
    rows.forEach(r=>{
      const key = `${r.dia}@${r.desde}`;
      const docentes = Array.isArray(r.docentes) ? r.docentes.join(', ') : (r.docentes||'');
      ocupados[key] = `<strong>${r.comision||''}</strong><br><small>${docentes}</small><br><small>${r.aula||''}</small>`;
    });

    const len = Math.max(lv.length, sab.length);
    let html = `
      <table class="tabla-grilla">
        <thead>
          <tr>
            <th class="col-hora-lv">Hora (L-V)</th>
            ${[1,2,3,4,5].map(d=>`<th>${NOMBRES[d]}</th>`).join('')}
            <th class="col-sab">${NOMBRES[6]||'Sáb'}</th>
            <th class="col-hora-sab">Hora (Sábado)</th>
          </tr>
        </thead>
        <tbody>
    `;

    for (let i=0;i<len;i++){
      const a = lv[i]||{}, b = sab[i]||{};
      const isRecA = !!a.recreo, isRecB = !!b.recreo;

      html += `<tr>
        <th class="${isRecA?'recreo-label':''}">${a.desde&&a.hasta?`${a.desde} – ${a.hasta}`:''}</th>
        ${[1,2,3,4,5].map(d=>{
          if (isRecA) return `<td class="recreo">Recreo</td>`;
          const desde = a.desde||'';
          const key   = `${d}@${desde}`;
          const idx   = SLOTS_MAP[desde];
          const cls   = (desde && idx!=null)
                        ? (ocupados[key] ? 'celda-ocupada' : 'celda-vacia')
                        : 'disabled';
          return `<td data-dia="${d}" data-hora="${desde}" data-slot-idx="${idx??''}" class="${cls}">
                    ${ocupados[key]||''}
                  </td>`;
        }).join('')}
        ${
          isRecB
          ? `<td class="recreo">Recreo</td>`
          : (()=>{
              const desde = b.desde||'';
              const key   = `6@${desde}`;
              const idx   = SLOTS_MAP[desde];
              const cls   = (desde && idx!=null)
                            ? (ocupados[key] ? 'celda-ocupada' : 'celda-vacia')
                            : 'disabled';
              return `<td data-dia="6" data-hora="${desde}" data-slot-idx="${idx??''}" class="${cls}">
                        ${ocupados[key]||''}
                      </td>`;
            })()
        }
        <th class="${isRecB?'recreo-label':''}">${b.desde&&b.hasta?`${b.desde} – ${b.hasta}`:''}</th>
      </tr>`;
    }

    html += `</tbody></table>`;
    grid.innerHTML = html;

    // Clicks: vacías → agregar; ocupadas → marcar para borrar
    grid.querySelectorAll('td.celda-vacia').forEach(td=>{
      td.addEventListener('click', ()=>{
        td.classList.toggle('sel-add');
      });
    });
    grid.querySelectorAll('td.celda-ocupada').forEach(td=>{
      td.addEventListener('click', ()=>{
        td.classList.toggle('sel-del');
      });
    });
  }

  // ---- CARGA DE GRILLA ----
  async function loadGrid(){
    const planId = $('#id_plan')?.value || '';
    const espId  = $('#id_materia')?.value || '';
    const turno  = normTurno($('#id_turno')?.value || '');

    if (!planId || !espId || !turno) { msg('Seleccioná Plan, Materia y Turno.'); return; }

    const base = (window.API_GRID_URL || '/panel/horarios/api/grilla/').trim();
    const url  = `${base}${base.includes('?')?'&':'?'}plan=${encodeURIComponent(planId)}&materia=${encodeURIComponent(espId)}&turno=${encodeURIComponent(turno)}`;

    try {
      const data = await window.fetchJSON(url);
      console.log('[grilla] payload', data);
      if (Array.isArray(data.lv) && Array.isArray(data.sab)) {
        renderGridV2(data);
      } else {
        msg('Formato de respuesta no compatible.'); // fallback simple si cambiara el backend
      }
    } catch (e) {
      console.error('[grilla] error', e);
      msg('No se pudo cargar la grilla. Revisá consola.');
    }
  }

  // ---- GUARDAR ----
  async function guardarHorarios(){
    if (!grid) return;

    const planId = $('#id_plan')?.value;
    const espId  = $('#id_materia')?.value;
    const turno  = normTurno($('#id_turno')?.value);

    if (!planId || !espId || !turno) {
      alert('Completá Plan, Materia y Turno.'); return;
    }

    // Estado final deseado = ocupadas no marcadas para borrar + vacías marcadas para agregar
    const kept  = [...grid.querySelectorAll('td.celda-ocupada:not(.sel-del)')];
    const added = [...grid.querySelectorAll('td.sel-add')];

    const rows = [];
    for (const td of [...kept, ...added]) {
      const d = Number(td.dataset.dia);
      const i = Number(td.dataset.slotIdx);
      if (!Number.isFinite(d) || !Number.isFinite(i)) continue; // ignora celdas sin índice
      rows.push({ d, i });
    }

    if (rows.length === 0 && kept.length === 0) {
      alert('No hay cambios para guardar.');
      return;
    }

    let resp;
    try {
      resp = await fetch(window.API_HORARIO_SAVE || '/panel/horarios/api/guardar/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.getCSRF(),
        },
        body: JSON.stringify({
          plan_id: Number(planId),
          espacio_id: Number(espId),
          turno: turno,
          rows: rows,
        }),
      });
    } catch (e) {
      alert('No se pudo llamar a la API (fetch).'); console.error(e); return;
    }

    const raw = await resp.text();
    let data = null;
    try { data = JSON.parse(raw); } catch {}

    if (!resp.ok || !data?.ok) {
      const detalle = (data && data.error) || raw || '(sin detalle)';
      alert(`No se pudo guardar (HTTP ${resp.status}). ${detalle}`);
      console.warn('respuesta cruda:', raw, 'json:', data);
      return;
    }

    alert(`Guardado OK. Altas: ${data.added||0} | Bajas: ${data.removed||0}`);
    await loadGrid();
  }

  // ---- EVENTOS ----
  

  onReady(()=>{
    ['#id_plan', '#id_materia', '#id_turno'].forEach(sel=>{
      const el = $(sel);
      if (el) el.addEventListener('change', loadGrid);
    });

    const btn = $('#btn-guardar-horario');
    if (btn) btn.addEventListener('click', ()=>{ console.log('[ui] click Guardar'); guardarHorarios(); });
    else console.warn('[ui] no encontré #btn-guardar-horario');

    loadGrid();
  });

})();
