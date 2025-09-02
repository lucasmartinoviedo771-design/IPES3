/* ui/static/ui/js/armar_horarios.js
   Dibuja la grilla de horarios de forma dinámica 
   obteniendo la configuración desde la API.
*/
(() => {
  console.log("[Horarios] Script armar_horarios.js cargado.");

  // --- Endpoints y Helpers ---
  const API_MATERIA_PLAN = window.API_MATERIA_PLAN;
  const API_HORARIO_SAVE = window.API_HORARIO_SAVE;
  const API_TURNOS = window.API_TURNOS;
  const API_GRILLA_CONFIG = window.API_GRILLA_CONFIG;

  function getCSRFToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function currentCombo() {
    return {
      profesorado_id: document.getElementById("id_carrera")?.value || "",
      plan_id:    document.getElementById("id_plan")?.value    || "",
      materia_id: document.getElementById("id_materia")?.value || "",
      turno:   document.getElementById("id_turno")?.value   || "",
    };
  }

  // --- UNIFIED-GRID RENDERING ---
  function th(t){ const e=document.createElement("th"); e.textContent=t; return e; }
  function td(t,c){ const e=document.createElement("td"); if(c) e.className=c; if(t) e.textContent=t; return e; }

  async function renderGridUnified(turno) {
    console.log(`[Horarios] renderGridUnified llamado para turno: ${turno}`);
    const $grid = document.getElementById("ah-grid");
    if (!$grid) return;
    $grid.innerHTML = "<p class='loading'>Cargando grilla...</p>";

    if (!turno) {
        $grid.innerHTML = "";
        return;
    }

    try {
        const fetchJSON = async (url) => {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        };

        const cfgLV = await fetchJSON(`${API_GRILLA_CONFIG}?turno=${encodeURIComponent(turno)}`);
        const cfgSa = await fetchJSON(`${API_GRILLA_CONFIG}?turno=sabado`);

        const lvBlocks = cfgLV.bloques || [];
        const saBlocks = cfgSa.bloques || [];

        const lvTimes = Array.from(new Map(lvBlocks.filter(b => b.dia_semana >= 0 && b.dia_semana <= 4).map(b => [`${b.inicio}-${b.fin}`, {inicio: b.inicio, fin: b.fin}])).values()).sort((a,b) => a.inicio.localeCompare(b.inicio));
        const saTimes = Array.from(new Map(saBlocks.filter(b => b.dia_semana === 5).map(b => [`${b.inicio}-${b.fin}`, {inicio: b.inicio, fin: b.fin}])).values()).sort((a,b) => a.inicio.localeCompare(b.inicio));

        const byKeyLV = new Map();
        lvBlocks.forEach(b => {
            if (b.dia_semana >= 0 && b.dia_semana <= 4) {
                byKeyLV.set(`${b.dia_semana}-${b.inicio}-${b.fin}`, b);
            }
        });

        const byKeySa = new Map();
        saBlocks.forEach(b => {
            if (b.dia_semana === 5) {
                byKeySa.set(`${b.inicio}-${b.fin}`, b);
            }
        });

        const table = document.createElement("table");
        table.className = "grid-table";

        const thead = document.createElement("thead");
        const trh = document.createElement("tr");
        trh.appendChild(th("Hora (L–V)"));
        ["Lunes","Martes","Miércoles","Jueves","Viernes"].forEach(d => trh.appendChild(th(d)));
        trh.appendChild(th("Sábado"));
        trh.appendChild(th("Hora (Sábado)"));
        thead.appendChild(trh);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        const rows = Math.max(lvTimes.length, saTimes.length);

        for (let i = 0; i < rows; i++) {
            const tr = document.createElement("tr");
            const lvTime = lvTimes[i] || null;
            tr.appendChild(td(lvTime ? `${lvTime.inicio} – ${lvTime.fin}` : "", "col-time"));

            for (let day = 0; day < 5; day++) {
                const cell = td("", "col-slot");
                if (lvTime) {
                    const key = `${day}-${lvTime.inicio}-${lvTime.fin}`;
                    const block = byKeyLV.get(key);
                    if (block) {
                        cell.dataset.day   = (day + 1);
                        cell.dataset.hhmm  = lvTime.inicio;
                        cell.dataset.hasta = lvTime.fin;
                        if (block.es_recreo) {
                            cell.classList.add("is-break");
                            cell.textContent = "Recreo";
                        } else {
                            cell.classList.add("ah-cell", "ah-clickable");
                        }
                    }
                }
                tr.appendChild(cell);
            }

            const saTime = saTimes[i] || null;
            const tdSa = td("", "col-slot");
            if (saTime) {
                const keySa = `${saTime.inicio}-${saTime.fin}`;
                const block = byKeySa.get(keySa);
                if (block) {
                    tdSa.dataset.day   = 6;
                    tdSa.dataset.hhmm  = saTime.inicio;
                    tdSa.dataset.hasta = saTime.fin;
                    if (block.es_recreo) {
                        tdSa.classList.add("is-break");
                        tdSa.textContent = "Recreo";
                    } else {
                        tdSa.classList.add("ah-cell", "ah-clickable");
                    }
                }
            }
            tr.appendChild(tdSa);
            tr.appendChild(td(saTime ? `${saTime.inicio} – ${saTime.fin}` : "", "col-time col-time-right"));
            tbody.appendChild(tr);
        }

        table.appendChild(tbody);
        $grid.innerHTML = "";
        $grid.appendChild(table);

        await syncFromServer({silent: true});
    } catch (e) {
        console.error("[Horarios] Error al renderizar la grilla:", e);
        $grid.innerHTML = "<p class='error'>Error al cargar la grilla. Verifique la consola.</p>";
    }
  }

  // --- CELL & STATE HELPERS ---

  function findCell(day, hhmm) {
    return document.querySelector(`#ah-grid td[data-day='${day}'][data-hhmm='${hhmm}']`);
  }

  function selectCell(cell, selected) {
      if (!cell) return;
      cell.classList.toggle("on", selected);
  }

  function clearAllSelected() {
    document.querySelectorAll("#ah-grid .ah-cell.on").forEach(td => {
      selectCell(td, false);
    });
  }

  function updateCount(count, max) {
    const countEl = document.getElementById("block-counter");
    if (!countEl) return;
    
    let total = max;
    if (total === undefined) {
        const currentText = countEl.textContent || "";
        const maxMatch = currentText.match(/\/ (\d+)/);
        total = maxMatch ? maxMatch[1] : document.querySelectorAll('#ah-grid .ah-clickable').length;
    }
    countEl.textContent = `Bloques: ${count} / ${total}`;
  }

  async function syncFromServer({silent=false}={}) {
    const combo = currentCombo();
    if (!combo.materia_id || !combo.plan_id || !combo.profesorado_id) return;

    const u = new URL(API_MATERIA_PLAN, window.location.origin);
    u.searchParams.set("materia_id", combo.materia_id);
    u.searchParams.set("plan_id",    combo.plan_id);
    u.searchParams.set("profesorado_id", combo.profesorado_id);

    try {
      const res = await fetch(u, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();

      clearAllSelected();
      if (json.items.length > 0 && !combo.turno) {
        document.getElementById("id_turno").value = json.items[0].turno;
      }
      const mapDiaToNum = {'lu':1, 'ma':2, 'mi':3, 'ju':4, 'vi':5, 'sa':6};
      json.items.forEach(({dia, inicio}) => {
        const dayNum = mapDiaToNum[dia];
        const td = findCell(dayNum, inicio);
        if (td) selectCell(td, true);
      });

      updateCount(json.items.length);
      if (!silent) showSavedBadge("Sincronizado");
    } catch (e) {
      console.error("[Horarios] Falló la sincronización con el servidor:", e);
      if (!silent) showSavedBadge("Sin conexión", true);
    }
  }
  
  function onCellClick(ev) {
    const cell = ev.target.closest("td.ah-clickable");
    if (!cell) return;
    cell.classList.toggle("on");
    const currentSelected = document.querySelectorAll("#ah-grid .ah-cell.on").length;
    updateCount(currentSelected);
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

  async function seedTurnoOptions() {
    console.log("[Horarios] Iniciando seedTurnoOptions...");
    const sel = document.getElementById("id_turno");
    if (!sel) {
        console.error("[Horarios] Error: No se encontró el elemento <select id='id_turno'>.");
        return null;
    }

    const hasReal = Array.from(sel.options).some(o => o.value && o.textContent.trim());
    if (hasReal && sel.options.length > 1) {
        console.log("[Horarios] El selector de turnos ya tiene opciones. Omitiendo carga.");
        return sel;
    }

    try {
        console.log(`[Horarios] Cargando turnos desde: ${API_TURNOS}`)
        const res = await fetch(API_TURNOS);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status} - ${res.statusText}`);
        }
        const data = await res.json();
        console.log("[Horarios] Turnos recibidos de la API:", data);
        
        sel.innerHTML = "";
        sel.add(new Option("---------", ""));
        (data.turnos || []).forEach(turno => {
            sel.add(new Option(turno.label, turno.value));
        });
        console.log("[Horarios] Selector de turnos poblado exitosamente.");

    } catch (e) {
        console.error("[Horarios] Falló la carga de turnos desde la API.", e);
        sel.innerHTML = "";
        sel.add(new Option("Error al cargar turnos", ""));
        sel.disabled = true;
    }

    return sel;
  }

  function collectSelected() {
    const mapNumToDia = {1:'lu',2:'ma',3:'mi',4:'ju',5:'vi',6:'sa'};
    const out = [];
    document.querySelectorAll('#ah-grid .ah-clickable.on').forEach(td => {
      const dayNum = parseInt(td.dataset.day, 10);
      out.push({
        dia:   mapNumToDia[dayNum],
        inicio: td.dataset.hhmm,
        fin:    td.dataset.hasta,
      });
    });
    return out;
  }

  async function saveCurrentSelection() {
    const { profesorado_id, plan_id, materia_id, turno } = currentCombo();
    if (!profesorado_id || !plan_id || !materia_id || !turno) {
      showSavedBadge("Completá Carrera/Plan/Materia/Turno", true);
      return;
    }
    const payload = {
      profesorado_id, plan_id, materia_id, turno,
      items: collectSelected(),
    };

    showSavingBadge();

    try {
        const res = await fetch(window.API_HORARIO_SAVE, {
            method: "POST",
            headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.error || `HTTP ${res.status}`);
        }

        const data = await res.json();
        showSavedBadge(`Guardado (${data.count} bloques)`);
        return data;
    } catch (e) {
        console.error(e);
        showSavedBadge(e.message || "Error al guardar", true);
        throw e;
    }
  }

  // --- INITIALIZATION ---
  document.addEventListener("DOMContentLoaded", async () => {
    console.log("[Horarios] DOMContentLoaded disparado.");
    const selTurno = await seedTurnoOptions();
    
    const initialTurno = document.getElementById("id_turno").value;
    if (initialTurno) {
        await renderGridUnified(initialTurno);
    }

    selTurno?.addEventListener("change", async (e) => {
      await renderGridUnified(e.target.value);
    });

    document.getElementById('ah-grid')?.addEventListener('click', onCellClick);

    document.getElementById("frm-horario")?.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        try {
          await saveCurrentSelection();
        } catch (e) {
          // El error ya se muestra en el badge
        }
    });
  });

})();