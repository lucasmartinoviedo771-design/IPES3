/* ui/static/ui/js/armar_horarios.js
   Arma la grilla de horarios y aplica todos los estilos visuales directamente
   para evitar conflictos con hojas de estilo externas.
   Features: Autosave y refresco automático.
*/
(() => {
  // --- Estilos ---
  const styleBase = `height: 46px; border-radius: 12px; text-align: center; vertical-align: middle; padding: 0; transition: background .12s ease, border-color .12s ease;`;
  const styleClickable = `background: #F7F4EE; border: 1px solid #E6E2D8; cursor: pointer;`;
  const styleBreak = `background: #F4F1E9; border: 1px solid #E6E2D8; color: #6E6A60; font-style: italic; pointer-events: none;`;
  const styleSelected = `background: #E6F6EE; border: 1px solid #6DC597; cursor: pointer; box-shadow: inset 0 0 0 2px rgba(109,197,151,.25);`;

  // --- Configuración de turnos y recreos (formato HH:MM) ---
  const GRILLAS = {
    manana: {
      label: "Mañana",
      blocks: [
        ["07:45","08:25"], ["08:25","09:05"], ["09:05","09:15"], ["09:15","09:55"],
        ["09:55","10:35"], ["10:35","10:45"], ["10:45","11:25"], ["11:25","12:05"], ["12:05","12:45"]
      ],
      breaks: [["09:05","09:15"], ["10:35","10:45"]]
    },
    tarde: {
      label: "Tarde",
      blocks: [
        ["13:00","13:40"], ["13:40","14:20"], ["14:20","14:30"], ["14:30","15:10"],
        ["15:10","15:50"], ["15:50","16:00"], ["16:00","16:40"], ["16:40","17:20"], ["16:40","18:00"]
      ],
      breaks: [["14:20","14:30"], ["15:50","16:00"]]
    },
    vespertino: {
      label: "Vespertino",
      blocks: [
        ["18:10","18:50"], ["18:50","19:30"], ["19:30","19:40"], ["19:40","20:10"],
        ["20:10","20:50"], ["20:50","21:00"], ["21:00","21:30"], ["21:30","22:10"], ["22:10","22:50"]
      ],
      breaks: [["19:30","19:40"], ["20:50","21:00"]]
    },
    sabado: {
      label: "Sábado",
      blocks: [
        ["09:00","09:40"], ["09:40","10:20"], ["10:20","10:30"], ["10:30","11:10"],
        ["11:10","11:50"], ["11:50","12:00"], ["12:00","12:40"], ["12:40","13:20"], ["13:20","14:00"]
      ],
      breaks: [["10:20","10:30"], ["11:50","12:00"]]
    }
  };

  // ====== Helpers de tiempo (base 5 minutos) ====== 
  const STEP_MIN = 5;
  function parseHM(hm){ const [h,m]=hm.split(':').map(Number); return h*60+m; }
  function fmtHM(min){ const h=Math.floor(min/60), m=min%60; return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`; }
  function toStep(min){ return Math.round(min/STEP_MIN); } // redondeo por seguridad

  // Une límites (inicios/fines) de dos grillas (ej: mañana + sábados)
  function collectBoundaries(patternA, patternB){
    const set = new Set();
    const push = (blocks)=>blocks.forEach(([a,b])=>{ set.add(parseHM(a)); set.add(parseHM(b)); });
    push(patternA.blocks);
    push(patternB.blocks);
    // Asegura incluir todo el rango visible
    const min = Math.min(...[...set]);
    const max = Math.max(...[...set]);
    return {bounds: [...set].sort((a,b)=>a-b), min, max};
  }

  // Dibuja una grilla unificada (L..V usan turnoKey, Sábado usa "sabado")
  function buildUnifiedGrid(container, turnoKey){
    const DAYS = ['lu','ma','mi','ju','vi','sa'];
    const LABELS = ['Hora','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];

    const pWeek = GRILLAS[turnoKey];     // bloques L..V
    const pSat  = GRILLAS.sabado;        // bloques Sábado
    if(!pWeek || !pSat){ console.warn('Faltan patrones de grilla'); return; }

    // 1) Límites
    const {bounds, min, max} = collectBoundaries(pWeek, pSat);
    const startStep = toStep(min);
    const endStep   = toStep(max);
    const totalSteps = endStep - startStep;

    // 2) DOM base
    container.innerHTML = '';
    container.style.setProperty('--rows', totalSteps); // para grid-template-rows

    // Encabezados
    for (let c=0; c<LABELS.length; c++){
      const h = document.createElement('div');
      h.className='hcell';
      h.textContent = LABELS[c];
      h.style.gridColumn = (c+1)+' / '+(c+2);
      h.style.gridRow = '1 / 2';
      container.appendChild(h);
    }

    // Mapeo de bloques a set de segmentos [from,to] (en minutos) por día
    const mapBlocks = (blocks)=>blocks.map(([a,b])=>[parseHM(a), parseHM(b)]);
    const weekMap = mapBlocks(pWeek.blocks);
    const weekBreaks = new Set(pWeek.breaks?.map(([a,b])=>`${a}-${b}`) || []);
    const satMap  = mapBlocks(pSat.blocks);
    const satBreaks = new Set(pSat.breaks?.map(([a,b])=>`${a}-${b}`) || []);

    // Utilidades para consulta rápida
    function slotInfoFor(range, day){
      // range: [from, to] en minutos
      const [from, to] = range;
      const blocks = (day==='sa') ? satMap : weekMap;
      const isBreakList = (day==='sa') ? satBreaks : weekBreaks;
      // es un bloque válido si está exactamente definido así
      const key = `${fmtHM(from)}-${fmtHM(to)}`;
      const isBreak = isBreakList.has(key);
      const isBlock = blocks.some(([a,b]) => a===from && b===to) && !isBreak;
      return {isBlock, isBreak};
    }

    // 3) Pintar filas (un segmento por par de límites consecutivos)
    for (let i=0; i<bounds.length-1; i++){
      const fromM = bounds[i], toM = bounds[i+1];
      const rStart = (toStep(fromM)-startStep)+2; // +2 por la fila de encabezado
      const rEnd   = (toStep(toM)-startStep)+2;

      // Columna 1: Hora (solo si es un bloque real del patrón de la semana)
      const isMajor = pWeek.blocks.some(([a,b])=>parseHM(a)===fromM && parseHM(b)===toM) ||
                      pSat.blocks.some(([a,b])=>parseHM(a)===fromM && parseHM(b)===toM);
      if (isMajor){
        const tcell = document.createElement('div');
        tcell.className = 'time-slot';
        tcell.style.gridColumn = '1 / 2';
        tcell.style.gridRow = `${rStart} / ${rEnd}`;
        tcell.textContent = `${fmtHM(fromM)} – ${fmtHM(toM)}`;
        container.appendChild(tcell);
      }

      // Columnas 2..7: L..V y Sábado
      for (let d=0; d<DAYS.length; d++){
        const dayKey = DAYS[d];
        const info = slotInfoFor([fromM,toM], dayKey);
        const cell = document.createElement('div');
        cell.className = 'cell' + (info.isBreak ? ' is-break' : (info.isBlock ? ' is-selectable' : ''));
        cell.style.gridColumn = (d+2)+' / '+(d+3);
        cell.style.gridRow = `${rStart} / ${rEnd}`;
        if (info.isBreak) cell.textContent = 'Recreo';

        if (info.isBlock){
          cell.dataset.day = dayKey;
          cell.dataset.from = fmtHM(fromM);
          cell.dataset.to = fmtHM(toM);
          cell.addEventListener('click', () => {
            cell.classList.toggle('is-selected');
            updateBlockCounter();
          });
        }

        container.appendChild(cell);
      }
    }
  }

  // contador de bloques seleccionados
  function updateBlockCounter(){
    const n = document.querySelectorAll('#ah-grid-unificado .cell.is-selected').length;
    const el = document.querySelector('[data-role="blocks-counter"]');
    if (el) el.textContent = String(n);
  }

  // --- Endpoints y Helpers ---
  const API_GRID   = window.API_GRID;
  const API_TOGGLE = window.API_TOGGLE;

  function getCSRFToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function currentCombo() {
    return {
      carrera: document.getElementById("id_carrera")?.value || "",
      plan:    document.getElementById("id_plan")?.value    || "",
      materia: document.getElementById("id_materia")?.value || "",
      turno:   document.getElementById("id_turno")?.value   || "",
    };
  }

  async function syncFromServer({silent=false}={}) {
    const combo = currentCombo();
    if (!combo.carrera || !combo.plan || !combo.materia || !combo.turno) return;

    const u = new URL(API_GRID, window.location.origin);
    u.searchParams.set("carrera", combo.carrera);
    u.searchParams.set("plan",    combo.plan);
    u.searchParams.set("materia", combo.materia);
    u.searchParams.set("turno",   combo.turno);

    try {
      const res = await fetch(u, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();

      // clearAllSelected(); // No longer needed with unified grid
      // json.slots.forEach(({d, hhmm}) => {
      //   const td = findCell(d, hhmm);
      //   td && selectCell(td, true, {skipSave:true});
      // });

      // updateCount(json.count); // No longer needed with unified grid
      if (!silent) showSavedBadge("Sincronizado");
    } catch (e) {
      console.error("Sync failed", e);
      if (!silent) showSavedBadge("Sin conexión", true);
    }
  }

  async function persistToggle(day, hhmm, selected) {
    const combo = currentCombo();
    if (!combo.carrera || !combo.plan || !combo.materia || !combo.turno) return;

    showSavingBadge();

    try {
      const res = await fetch(API_TOGGLE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({...combo, day, hhmm, selected}),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) throw new Error(json.error || "Error de guardado");

      // updateCount(json.count); // No longer needed with unified grid
      showSavedBadge("Guardado");
    } catch (e) {
      console.error("Persist failed", e);
      // const td = findCell(day, hhmm); // No longer needed with unified grid
      // td && selectCell(td, !selected, {skipSave:true}); // Revert
      const errorMessage = e instanceof Error ? e.message : "Error al guardar";
      showSavedBadge(errorMessage, true);
    }
  }
  
  // function onCellClick(ev) { ... } // Replaced by event listener in buildUnifiedGrid

  let saveTimer;
  function showSavingBadge() {
    const el = document.getElementById("save-indicator");
    if (!el) return;
    el.textContent = "Guardando…";
    el.style.color = "#6b7280";
  }

  function showSavedBadge(msg="Guardado", error=false) {
    const el = document.getElementById("save-indicator");
    if (!el) return;
    el.textContent = msg;
    el.style.color = error ? "#b91c1c" : "#0f766e";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { el.textContent = ""; }, 2500);
  }

  function seedTurnoOptions() {
    const sel = document.getElementById("id_turno");
    if (!sel) return null;
    const hasRealOptions = Array.from(sel.options).some(o => o.value && o.textContent && o.textContent.trim() !== "");
    if (!hasRealOptions) {
      sel.innerHTML = "";
      sel.add(new Option("---------", ""));
      for (const [key, cfg] of Object.entries(GRILLAS)) {
        if (key !== 'sabado') {
            sel.add(new Option(cfg.label, key));
        }
      }
    }
    return sel;
  }

  function turnoKeyFromSelectValue(val) {
    if (!val) return null;
    if (GRILLAS[val]) return val;
    const entry = Object.entries(GRILLAS).find(([,cfg]) => cfg.label === val);
    return entry ? entry[0] : null;
  }

  document.addEventListener("DOMContentLoaded", () => {
    const selCarrera = document.getElementById('id_carrera');
    const selPlan = document.getElementById('id_plan');
    const selMateria = document.getElementById('id_materia');
    const selTurno = document.getElementById('id_turno');

    if (selCarrera && typeof initialSelectedCarreraId !== 'undefined' && initialSelectedCarreraId) { selCarrera.value = initialSelectedCarreraId; }
    if (selPlan && typeof initialSelectedPlanId !== 'undefined' && initialSelectedPlanId) { selPlan.value = initialSelectedPlanId; }
    if (selMateria && typeof initialSelectedMateriaId !== 'undefined' && initialSelectedMateriaId) { selMateria.value = initialSelectedMateriaId; }
    if (selTurno && typeof initialSelectedTurnoValue !== 'undefined' && initialSelectedTurnoValue) { selTurno.value = initialSelectedTurnoValue; }

    if (selCarrera && selCarrera.value) {
        selCarrera.dispatchEvent(new Event('change'));
    }

    seedTurnoOptions();

    if (selTurno && selTurno.value) {
        const key0 = turnoKeyFromSelectValue(selTurno.value);
        if (key0) {
          const host = document.getElementById("ah-grid-unificado");
          buildUnifiedGrid(host, key0);
          updateBlockCounter();
        }
    }

    selTurno.addEventListener("change", (e) => {
      const key = turnoKeyFromSelectValue(e.target.value);
      const host = document.getElementById("ah-grid-unificado");
      if (!key) {
        host.innerHTML = ''; // Clear grid
        updateBlockCounter();
        return;
      }
      buildUnifiedGrid(host, key);
      updateBlockCounter();
    });

    // Polling for auto-refresh
    setInterval(() => { 
        // Solo sincroniza si hay una selección válida
        const combo = currentCombo();
        if (combo.carrera && combo.plan && combo.materia && combo.turno) {
            syncFromServer({silent:true}); 
        }
    }, 10000);
  });
})();