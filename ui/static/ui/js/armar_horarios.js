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

  function renderSabadosLegend(targetId = "ah_sabados_info") {
    const box = document.getElementById(targetId);
    if (!box) return;
    const g = GRILLAS.sabado; // Sábado (mañana)
    if (!g) { console.error("GRILLAS.sabado not found"); return; }
    const table = document.createElement("table");
    table.className = "grid-table sat-times-legend";
    table.innerHTML = "<thead><tr><th>Sábados</th></tr></thead><tbody></tbody>";
    const tb = table.querySelector("tbody");
    const slots = buildSlots(g);
    slots.forEach(slot => {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.textContent = `${fmt(slot.from)} – ${fmt(slot.to)}`;
        if (slot.isBreak) {
            td.style.fontStyle = "italic";
            td.style.opacity = "0.7";
        }
        tr.appendChild(td);
        tb.appendChild(tr);
    });
    box.replaceChildren(table);
  }

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
    const start = toMinutes(turnoCfg.start), end = toMinutes(turnoCfg.end);
    const breaks = turnoCfg.breaks.map(([a,b]) => [toMinutes(a), toMinutes(b)]).sort((x,y)=>x[0]-y[0]);
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

  function ensureInfoAndTable() {
    let host = document.getElementById("ah-grid");
    if (!host) { host = document.body; }

    let table = document.getElementById("ah-grid-table");
    if (!table) {
      table = document.createElement("table");
      table.id = "ah-grid-table";
      table.style.width = "100%";
      table.style.tableLayout = "fixed";
      table.style.borderCollapse = "separate";
      table.style.borderSpacing = "10px 8px";

      const thead = document.createElement("thead");
      const hr = document.createElement("tr");
      const th0 = document.createElement("th");
      th0.textContent = "Hora";
      th0.style.width = "150px";
      th0.style.textAlign = "left";
      hr.appendChild(th0);
      for (const d of DAYS) { const th = document.createElement("th"); th.textContent = d; th.style.textAlign = "center"; hr.appendChild(th); }
      thead.appendChild(hr);

      const tbody = document.createElement("tbody");
      tbody.id = "ah-grid-body";
      
      table.appendChild(thead);
      table.appendChild(tbody);
      host.appendChild(table);
    }
    return {tbody: document.getElementById("ah-grid-body")};
  }

  function clearNode(n){ while(n && n.firstChild) n.removeChild(n.firstChild); }

  async function renderGrid(turnoKey) {
    const cfg = GRILLAS[turnoKey];
    if (!cfg) return;

    const {tbody} = ensureInfoAndTable();
    clearNode(tbody);

    const currentSlots = buildSlots(cfg);
    const maxSelectable = currentSlots.filter(s => !s.isBreak).length * DAYS.length;
    updateCount(0, maxSelectable);

    for (const slot of currentSlots) {
      const tr = document.createElement("tr");
      const tdTime = document.createElement("td");
      tdTime.textContent = `${fmt(slot.from)} – ${fmt(slot.to)}`;
      tdTime.style.cssText = `font-weight: 600; color: #5B5141; border: 0; background: transparent;`;
      tr.appendChild(tdTime);

      for (let dayIdx=0; dayIdx<DAYS.length; dayIdx++) {
        const td = document.createElement("td");
        td.className = "ah-cell";
        if (slot.isBreak) {
          td.textContent = "Recreo";
          td.classList.add("ah-break");
          td.style.cssText = styleBase + styleBreak;
        } else {
          td.dataset.day  = String(dayIdx + 1);
          td.dataset.hhmm = fmt(slot.from);
          td.classList.add("ah-clickable");
          td.style.cssText = styleBase + styleClickable;
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    
    tbody.removeEventListener("click", onCellClick);
    tbody.addEventListener("click", onCellClick);

    await syncFromServer();
  }

  function findCell(day, hhmm) {
    return document.querySelector(`#ah-grid-body td[data-day='${day}'][data-hhmm='${hhmm}']`);
  }

  function selectCell(cell, selected, {skipSave = false} = {}) {
      if (!cell) return;
      cell.classList.toggle("on", selected);
      cell.style.cssText = styleBase + (selected ? styleSelected : styleClickable);
  }

  function clearAllSelected() {
    document.querySelectorAll("#ah-grid-body td.on").forEach(td => {
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
        td && selectCell(td, true, {skipSave:true});
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
      td && selectCell(td, !selected, {skipSave:true}); // Revert
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

    selectCell(cell, willBeSelected, {skipSave:true}); // Optimistic update
    const currentSelected = document.querySelectorAll("#ah-grid-body td.on").length;
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
          renderGrid(key0);
          renderSabadosLegend();
        }
    }

    selTurno.addEventListener("change", (e) => {
      const key = turnoKeyFromSelectValue(e.target.value);
      const {tbody} = ensureInfoAndTable();
      clearNode(tbody);
      if (!key) {
        updateCount(0, 0);
        return;
      }
      renderGrid(key);
      renderSabadosLegend();
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