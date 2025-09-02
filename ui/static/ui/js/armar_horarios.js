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
    manana: { label: "Mañana", start: "07:45", end: "12:45", breaks: [["09:05","09:15"], ["10:35","10:45"]], },
    tarde: { label: "Tarde", start: "13:00", end: "18:00", breaks: [["14:20","14:30"], ["15:50","16:00"]], },
    vespertino: { label: "Vespertino", start: "18:10", end: "23:10", breaks: [["19:30","19:40"], ["21:00","21:10"]], },
    sabado: { label: "Sábado (Mañana)", start: "09:00", end: "14:00", breaks: [["10:20","10:30"], ["11:50","12:00"]], },
  };

  const BLOCK_MIN = 40;
  const DAYS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];

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

  const toMinutes = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h*60 + m; };
  const fmt = (min) => { const h = Math.floor(min/60); const m = min % 60; return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`; };

  function buildSlots(turnoCfg) {
    if (!turnoCfg || !turnoCfg.start || !turnoCfg.end) return [];
    const start = toMinutes(turnoCfg.start), end = toMinutes(turnoCfg.end);
    const breaks = (turnoCfg.breaks || []).map(([a,b]) => [toMinutes(a), toMinutes(b)]).sort((x,y)=>x[0]-y[0]);
    const slots = [];
    let cur = start;
    for (const [bStart, bEnd] of breaks) {
      while (cur + BLOCK_MIN <= bStart) { slots.push({from: cur, to: cur + BLOCK_MIN, isBreak: false}); cur += BLOCK_MIN; }
      if (cur < bStart) cur = bStart;
      slots.push({from: bStart, to: bEnd, isBreak: true});
      cur = bEnd;
    }
    while (cur + BLOCK_MIN <= end) { slots.push({from: cur, to: cur + BLOCK_MIN, isBreak: false}); cur += BLOCK_MIN; }
    return slots;
  }

  // --- DUAL-GRID RENDERING ---

  function makeTable(containerId, headers, tableId) {
    const host = document.getElementById(containerId);
    if (!host) return { table: null, tbody: null };
    host.innerHTML = "";

    const tbl = document.createElement("table");
    tbl.className = "grid-table";
    if (tableId) tbl.id = tableId;

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    headers.forEach((h, i) => {
      const th = document.createElement("th");
      th.textContent = h;
      if (i === 0) th.className = "col-time";
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    const tbody = document.createElement("tbody");
    tbl.appendChild(thead);
    tbl.appendChild(tbody);

    host.appendChild(tbl);
    return { table: tbl, tbody };
  }

  function drawLV(turnoKey) {
    const week = GRILLAS[turnoKey] || GRILLAS.manana;
    week.blocks = buildSlots(week).map(s => [fmt(s.from), fmt(s.to)]);
    const breaks = new Set((week.breaks || []).map(([a,b]) => `${a}-${b}`));
    const { tbody } = makeTable("ah-grid-left",
      ["Hora","Lunes","Martes","Miércoles","Jueves","Viernes"],
      "ah-grid-lv");

    if (!tbody) return;

    (week.blocks || []).forEach(([from, to]) => {
      const key = `${from}-${to}`;
      const tr  = document.createElement("tr");

      const tdTime = document.createElement("td");
      tdTime.className = "col-time";
      tdTime.textContent = `${from} – ${to}`;
      tr.appendChild(tdTime);

      for (let d = 1; d <= 5; d++) {
        const td = document.createElement("td");
        if (breaks.has(key)) {
          td.textContent = "Recreo";
          td.className = "ah-break";
        } else {
          td.className = "ah-cell ah-clickable";
          td.dataset.day = String(d);
          td.dataset.hhmm = from;
          td.dataset.hasta = to;
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    });
  }

  function drawSabado() {
    const sat = GRILLAS.sabado || {};
    sat.blocks = buildSlots(sat).map(s => [fmt(s.from), fmt(s.to)]);
    const blocks = sat.blocks || [];
    const breaks = new Set((sat.breaks || []).map(([a,b]) => `${a}-${b}`));

    const { tbody } = makeTable("ah-grid-right", ["Hora (Sábado)","Sábado"], "ah-grid-sab");
    if (!tbody) return;

    blocks.forEach(([from, to]) => {
      const key = `${from}-${to}`;
      const tr  = document.createElement("tr");

      const tdTime = document.createElement("td");
      tdTime.className = "col-time";
      tdTime.textContent = `${from} – ${to}`;
      tr.appendChild(tdTime);

      const td = document.createElement("td");
      if (breaks.has(key)) {
        td.textContent = "Recreo";
        td.className = "ah-break";
      } else {
        td.className = "ah-cell ah-clickable";
        td.dataset.day  = "6";
        td.dataset.hhmm = from;
        td.dataset.hasta = to;
      }
      tr.appendChild(td);
      tbody.appendChild(tr);
    });
  }

  function renderGridDual(turnoKey) {
    drawLV(turnoKey);
    drawSabado();

    const total = document.querySelectorAll('#ah-grid .ah-clickable').length;
    const on = document.querySelectorAll('#ah-grid .ah-cell.on').length;
    if (typeof updateCount === "function") updateCount(on, total);
    
    syncFromServer({silent:true});
  }

  // --- CELL & STATE HELPERS ---

  function findCell(day, hhmm) {
    return document.querySelector(`#ah-grid td[data-day='${day}'][data-hhmm='${hhmm}']`);
  }

  function selectCell(cell, selected, {skipSave = false} = {}) {
      if (!cell) return;
      cell.classList.toggle("on", selected);
      // Use general classes instead of direct styling for easier maintenance
  }

  function clearAllSelected() {
    document.querySelectorAll("#ah-grid .ah-cell.on").forEach(td => {
      selectCell(td, false, {skipSave: true});
    });
  }

  function updateCount(count, max) {
    const countEl = document.getElementById("block-counter");
    if (!countEl) return;
    
    let total = max;
    if (total === undefined) {
        const currentText = countEl.textContent || "";
        const maxMatch = currentText.match(/\/ (\d+)/);
        total = maxMatch ? maxMatch[1] : '?';
    }
    countEl.textContent = `Bloques: ${count} / ${total}`;
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

      clearAllSelected();
      json.slots.forEach(({d, hhmm}) => {
        const td = findCell(d, hhmm);
        if (td) selectCell(td, true, {skipSave:true});
      });

      updateCount(json.count);
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

      updateCount(json.count);
      showSavedBadge("Guardado");
    } catch (e) {
      console.error("Persist failed", e);
      const td = findCell(day, hhmm);
      if (td) selectCell(td, !selected, {skipSave:true}); // Revert
      const errorMessage = e instanceof Error ? e.message : "Error al guardar";
      showSavedBadge(errorMessage, true);
    }
  }
  
  function onCellClick(ev) {
    const cell = ev.target.closest("td.ah-clickable");
    if (!cell) return;
    
    const day  = cell.dataset.day;
    const hhmm = cell.dataset.hhmm;
    const willBeSelected = !cell.classList.contains("on");

    selectCell(cell, willBeSelected, {skipSave:true});
    const currentSelected = document.querySelectorAll("#ah-grid .ah-cell.on").length;
    updateCount(currentSelected);
    persistToggle(parseInt(day,10), hhmm, willBeSelected);
  }

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

    const hasReal = Array.from(sel.options).some(o => o.value && o.textContent.trim());
    if (!hasReal) {
      sel.innerHTML = "";
      sel.add(new Option("---------", ""));
      for (const [key, cfg] of Object.entries(GRILLAS)) {
        sel.add(new Option(cfg.label, key));
      }
    }

    if (!sel.value) sel.value = "manana";
    return sel;
  }

  function turnoKeyFromSelectValue(val) {
    if (!val) return null;
    if (GRILLAS[val]) return val;
    const entry = Object.entries(GRILLAS).find(([,cfg]) => cfg.label === val);
    return entry ? entry[0] : null;
  }

  // --- INITIALIZATION ---
  document.addEventListener("DOMContentLoaded", () => {
    const selTurno = seedTurnoOptions();
    const key0 = turnoKeyFromSelectValue(selTurno?.value);
    if (key0) renderGridDual(key0);

    selTurno?.addEventListener("change", (e) => {
      const k = turnoKeyFromSelectValue(e.target.value);
      renderGridDual(k);
    });

    document.getElementById('ah-grid')?.addEventListener('click', onCellClick);

    setInterval(() => {
      const combo = currentCombo();
      if (combo.carrera && combo.plan && combo.materia && combo.turno) {
        syncFromServer({silent:true});
      }
    }, 10000);
  });

})();
