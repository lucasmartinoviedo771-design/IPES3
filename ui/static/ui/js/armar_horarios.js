// --- parche: fetchJSON y getCSRF si faltan ---
(function(){
  if (!window.getCSRF) {
    window.getCSRF = function () {
      const m = document.cookie.match('(^|;)\s*csrftoken\s*=\s*([^;]+)');
      return m ? m.pop() : '';
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

// Lógica de la página de carga de horarios v12 (backend-driven)
(function(){
  console.log('armar_horarios.js v12 cargado');

  // --- HELPERS & CONFIG ---
  function normTurno(s){ return (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,''); }
  const gridBox = document.getElementById('grid-horarios');
  function showMsg(msg){ if (gridBox) gridBox.innerHTML = `<p class="muted">${msg}</p>`; }
  function getCfg(){ return document.getElementById('cargar-horarios')?.dataset || {}; }

  // --- RENDERIZADO (V1 - compatible con 'horas') ---
  function renderGrid(dias, horas, rows) {
    let html = '<table class="tabla-grilla"><thead><tr><th>Hora</th>';
    const NOMBRES = {1:'Lun',2:'Mar',3:'Mié',4:'Jue',5:'Vie',6:'Sáb'};
    dias.forEach(d => html += `<th>${NOMBRES[d]||d}</th>`);
    html += '</tr></thead><tbody>';

    const ocupados = {}; // 'dia@hora' -> {html content}
    rows.forEach(r => {
        const key = `${r.dia}@${r.desde}`;
        const docentes = Array.isArray(r.docentes) ? r.docentes.join(', ') : (r.docentes||'');
        ocupados[key] = `<strong>${r.comision}</strong><br><small>${docentes}</small><br><small>${r.aula}</small>`;
    });

    horas.forEach(h=>{
      html += `<tr><th>${h}</th>`;
      dias.forEach(d=>{
        const key = `${d}@${h}`;
        if (ocupados[key]) {
            html += `<td data-dia="${d}" data-hora="${h}" class="celda-ocupada">${ocupados[key]}</td>`;
        } else {
            html += `<td data-dia="${d}" data-hora="${h}" class="celda-vacia" tabindex="0"></td>`;
        }
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    gridBox.innerHTML = html;

    gridBox.querySelectorAll('td.celda-vacia').forEach(td=>{
      td.addEventListener('click', ()=> { td.classList.toggle('seleccionada'); });
    });
  }

  // --- RENDERIZADO (V2 - compatible con 'lv' y 'sab') ---
  function renderGridV2(payload){
    const { dias=[], lv=[], sab=[], rows=[] } = payload;
    const grid = document.getElementById('grid-horarios');
    const NOMBRES = {1:'Lun',2:'Mar',3:'Mié',4:'Jue',5:'Vie',6:'Sáb'};
    const len = Math.max(lv.length, sab.length);

    // indexamos bloques existentes por 'dia@desde'
    const ocupados = {};
    rows.forEach(r=>{
      const key = `${r.dia}@${r.desde}`;
      const docentes = Array.isArray(r.docentes) ? r.docentes.join(', ') : (r.docentes||'');
      ocupados[key] = `<strong>${r.comision||''}</strong><br><small>${docentes}</small><br><small>${r.aula||''}</small>`;
    });

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

    for(let i=0;i<len;i++){
      const a = lv[i]  || {};
      const b = sab[i] || {};
      const isRecA = !!a.recreo, isRecB = !!b.recreo;

      html += `<tr>
        <th class="${isRecA ? 'recreo-label' : ''}">${a.desde && a.hasta ? `${a.desde} – ${a.hasta}` : ''}</th>
        ${[1,2,3,4,5].map(d=>{
            if (isRecA) return `<td class="recreo">Recreo</td>`;
            const key = `${d}@${a.desde||''}`;
            return `<td data-dia="${d}" data-hora="${a.desde||''}" class="${ocupados[key]?'celda-ocupada':'celda-vacia'}">
                      ${ocupados[key]||''}
                    </td>`;
        }).join('')}
        ${isRecB
          ? `<td class="recreo">Recreo</td>` 
          : (()=>{ 
              const key = `6@${b.desde||''}`; 
              return `<td data-dia="6" data-hora="${b.desde||''}" class="${ocupados[key]?'celda-ocupada':'celda-vacia'}">${ocupados[key]||''}</td>`;
            })()
        }
        <th class="${isRecB ? 'recreo-label' : ''}">${b.desde && b.hasta ? `${b.desde} – ${b.hasta}` : ''}</th>
      </tr>`;
    }

    html += `</tbody></table>`;
    grid.innerHTML = html;

    // Agregar: clic en vacías → toggle sel-add
    grid.querySelectorAll('td.celda-vacia').forEach(td=>{
      td.addEventListener('click', ()=>{
        td.classList.toggle('sel-add');
      });
    });

    // Quitar: clic en ocupadas → toggle sel-del
    grid.querySelectorAll('td.celda-ocupada').forEach(td=>{
      td.addEventListener('click', ()=>{
        td.classList.toggle('sel-del');
      });
    });
  }

  // --- LÓGICA DE CARGA ---
  async function loadGrid(){
    const prof = document.querySelector('#sel_profesorado, #id_profesorado, [name="carrera"], [name="profesorado"]')?.value || '';
    const plan = document.querySelector('#sel_plan, #id_plan, [name="plan"], [name="plan_id"]')?.value || '';
    const materia = document.querySelector('#sel_materia, #id_materia, [name="materia"], [name="espacio_id"]')?.value || '';
    const turno = normTurno(document.querySelector('#sel_turno, #id_turno, [name="turno"]')?.value || '');

    if (!plan || !materia) { showMsg('Seleccioná Plan y Materia para ver/armar la grilla.'); return; }

    const { gridUrl } = getCfg();
    const base = (gridUrl || '/panel/horarios/api/grilla/').trim();
    const q = new URLSearchParams({ carrera: prof, plan, materia, turno });
    const url = base + (base.includes('?') ? '&' : '?') + q.toString();

    try {
      const data = await window.fetchJSON(url);
      console.log('[grilla] payload', data);
      if (Array.isArray(data.lv) && Array.isArray(data.sab)) {
        renderGridV2(data);
      } else {
        // compat con payload viejo
        renderGrid(data.dias || [], data.horas || [], data.rows || []);
      }
    } catch (e) {
      console.error('[grilla] error', e);
      showMsg('No se pudo cargar la grilla. Revisá consola.');
    }
  }

  // --- LÓGICA DE GUARDADO ---
  function getCSRF() {
    const m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
    return m ? m[2] : "";
  }

  async function guardarHorarios() {
    const grid = document.getElementById('grid-horarios');
    if (!grid) return;

    const planId  = document.querySelector('#id_plan').value;
    const materia = document.querySelector('#id_materia').value;
    const turno   = document.querySelector('#id_turno').value;

    // Celdas ocupadas que no fueron marcadas para borrar
    const kept = [...grid.querySelectorAll('td.celda-ocupada:not(.sel-del)')];
    // Celdas vacías que fueron marcadas para agregar
    const added = [...grid.querySelectorAll('td.sel-add')];

    const finalCells = [...kept, ...added];
    const keys = finalCells.map(td => `${td.dataset.dia} @${td.dataset.hora}`);

    let resp;
    try {
      resp = await fetch(window.API_HORARIO_SAVE, {
        method: 'POST',
        headers: {
          'Content-Type':'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          plan_id: Number(planId),
          espacio_id: Number(materia),
          turno: turno,
          keys: keys
        })
      });
    } catch (e) {
      alert('No se pudo llamar a la API (fetch).'); 
      console.error(e);
      return;
    }

    let data;
    try {
      data = await resp.json();
    } catch (e) {
      const text = await resp.text();
      alert(`Error ${resp.status}. Respuesta no JSON.\n${text.slice(0,400)}`);
      console.error(text);
      return;
    }

    if (!resp.ok || !data.ok) {
      alert(`No se pudo guardar. ${data.error || '(sin detalle)'} (HTTP ${resp.status})`);
      console.warn('detalle:', data);
      return;
    }

    alert(`Guardado OK. Altas: ${data.added} | Bajas: ${data.removed}`);
    // Recargamos la grilla para ver el estado final
    await loadGrid();
  }


  // --- EVENTOS ---
  ['#id_plan', '#id_materia', '#id_turno', '#id_carrera'].forEach(sel => {
      document.querySelector(sel)?.addEventListener('change', loadGrid);
  });
  document.addEventListener('DOMContentLoaded', loadGrid);
  document.getElementById('btn-guardar-horario')?.addEventListener('click', guardarHorarios);

})();
