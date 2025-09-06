// static/ui/js/armar_horarios.js
// v21 - Filtro de materias por periodo.
console.log("armar_horarios.js v21 cargado");

// ----------------- helpers -----------------
function fillSelect($sel, items, textKey = "nombre", valueKey = "id") {
  $sel.innerHTML = '<option value="">---------</option>';
  for (const it of (items || [])) {
    const opt = document.createElement("option");
    opt.value = it[valueKey];
    opt.textContent = it[textKey] ?? it.label ?? String(it[valueKey]);
    $sel.appendChild(opt);
  }
}

function turnoSlugFromSelect($selTurno) {
  const txt = $selTurno.options[$selTurno.selectedIndex]?.text?.toLowerCase() ?? "";
  if (txt.startsWith("mañ")) return "manana";
  if (txt.startsWith("tar")) return "tarde";
  if (txt.startsWith("noc")) return "noche";
  return txt || "manana";
}

function normSlot(s) {
  const ini = (s.inicio || s.ini || s.start || s.hora_inicio || s.desde).slice(0, 5);
  const fin = (s.fin || s.hora_fin || s.hasta || s.end).slice(0, 5);
  const recreo = s.es_recreo ?? s.recreo ?? s.is_break ?? false;
  return { ini, fin, recreo };
}

// ----------------- elementos y estado -----------------
const selCarrera = document.getElementById("sel-carrera");
const selPlan    = document.getElementById("sel-plan");
const selMateria = document.getElementById("sel-materia");
const selPeriodo = document.getElementById("sel-periodo");
const selTurno   = document.getElementById("sel-turno");
const selComision = document.getElementById("sel-comision");
const tblGrilla  = document.getElementById("grilla");
const btnGuardar = document.getElementById("btn-guardar");

let currentSlots = { lv: [], sab: [] };

// ----------------- rutas API -----------------
const API = {
  planes:       (carreraId) => `/panel/horarios/api/planes/?carrera=${encodeURIComponent(carreraId)}`,
  materias:     (planId, periodoId) => `/api/materias/?plan_id=${planId}&periodo_id=${periodoId}`,
  comisiones:   (params)    => `/api/comisiones/materia/?${params.toString()}`,
  timeslots:    (turno)     => `/panel/horarios/api/timeslots/?turno=${encodeURIComponent(turno)}`,
  getHorarios:  (params)    => `/api/horarios/materia/?${params.toString()}`,
  guardar:      ()          => `/api/horario/save`,
};

// ----------------- Lógica de Carga en Cascada -----------------

async function cargarPlanes() {
  selPlan.disabled = true;
  selMateria.disabled = true;
  selComision.disabled = true;
  selPlan.innerHTML = '<option value="">---------</option>';
  selMateria.innerHTML = '<option value="">---------</option>';
  selComision.innerHTML = '<option value="">---------</option>';
  if (!selCarrera.value) return;

  try {
    const data = await fetchJSON(API.planes(selCarrera.value));
    fillSelect(selPlan, data.results || data);
    selPlan.disabled = false;
  } catch (e) {
    console.error(e);
    alert("No se pudieron cargar los planes.");
  }
}

async function cargarMaterias() {
  selMateria.disabled = true;
  selComision.disabled = true;
  selMateria.innerHTML = '<option value="">---------</option>';
  selComision.innerHTML = '<option value="">---------</option>';
  if (!selPlan.value || !selPeriodo.value) return;

  try {
    const data = await fetchJSON(API.materias(selPlan.value, selPeriodo.value));
    fillSelect(selMateria, data.results || data, "nombre", "id");
    selMateria.disabled = false;
  } catch (e) {
    console.error(e);
    alert("No se pudieron cargar las materias.");
  }
}

async function cargarComisiones() {
    selComision.disabled = true;
    selComision.innerHTML = '<option value="">---------</option>';
    if (!selPlan.value || !selMateria.value || !selPeriodo.value) return;

    const params = new URLSearchParams({
        plan_id: selPlan.value,
        materia_id: selMateria.value,
        periodo_id: selPeriodo.value
    });

    try {
        const data = await fetchJSON(API.comisiones(params));
        const comisiones = data.comisiones || [];
        
        fillSelect(selComision, comisiones, 'seccion', 'id');

        if (comisiones.length > 1) {
            selComision.disabled = false;
        } else if (comisiones.length === 0) {
            selComision.innerHTML = '<option value="default">A</option>';
        }

        cargarGrillaYHorarios();
    } catch (e) {
        console.error("Error cargando comisiones:", e);
    }
}

async function cargarGrillaYHorarios() {
  const params = new URLSearchParams({
    profesorado_id: selCarrera.value,
    plan_id: selPlan.value,
    materia_id: selMateria.value,
    periodo_id: selPeriodo.value,
    turno: turnoSlugFromSelect(selTurno),
    comision_id: selComision.value
  });

  if (!params.get('profesorado_id') || !params.get('plan_id') || !params.get('materia_id') || !params.get('turno') || !params.get('periodo_id')) {
    tblGrilla.innerHTML = '<p class="muted">Seleccioná todos los campos para ver la grilla.</p>';
    return;
  }

  try {
    const [layoutData, existentesData] = await Promise.all([
        fetchJSON(API.timeslots(params.get('turno'))),
        fetchJSON(API.getHorarios(params))
    ]);
    dibujarGrilla(layoutData);
    if (existentesData.horarios) {
        pintarHorariosExistentes(existentesData.horarios);
    }
  } catch (e) {
    console.error(e);
    alert("No se pudieron cargar los datos de la grilla.\n\n" + (e?.message || e));
    tblGrilla.innerHTML = "";
  }
}

// ----------------- Lógica de Dibujo de Grilla -----------------

function dibujarGrilla(slots) {
  currentSlots.lv = (slots.lv || []).map(normSlot);
  currentSlots.sab = (slots.sab || []).map(normSlot);
  tblGrilla.innerHTML = '';
  const thead = document.createElement('thead');
  thead.innerHTML = `<tr><th>Hora (L-V)</th><th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th><th>Sáb</th><th>Hora (Sábado)</th></tr>`;
  tblGrilla.appendChild(thead);

  const tbody = document.createElement("tbody");
  const maxRows = Math.max(currentSlots.lv.length, currentSlots.sab.length);
  for (let i = 0; i < maxRows; i++) {
    const tr = document.createElement("tr");
    const lv = currentSlots.lv[i];
    const sab = currentSlots.sab[i];
    tr.innerHTML = `
        <th class="col-hora">${lv ? `${lv.ini} – ${lv.fin}` : ""}</th>
        ${[1,2,3,4,5].map(d => `<td data-row="${i}" data-day="${d}" data-slot="${lv ? `${lv.ini}-${lv.fin}` : ''}" class="${lv?.recreo ? 'recreo' : ''}">${lv?.recreo ? 'Recreo' : ''}</td>`).join('')}
        <td data-row="${i}" data-day="6" data-slot="${sab ? `${sab.ini}-${sab.fin}` : ''}" class="${sab?.recreo ? 'recreo' : ''}">${sab?.recreo ? 'Recreo' : ''}</td>
        <th class="col-hora">${sab ? `${sab.ini} – ${sab.fin}` : ""}</th>
    `;
    tbody.appendChild(tr);
  }
  tblGrilla.appendChild(tbody);
}

function pintarHorariosExistentes(horarios) {
    const diaMap = { 'lu': '1', 'ma': '2', 'mi': '3', 'ju': '4', 'vi': '5', 'sa': '6' };
    horarios.forEach(h => {
        const dia = diaMap[h.dia];
        const slot = `${h.inicio.slice(0,5)}-${h.fin.slice(0,5)}`;
        const celda = tblGrilla.querySelector(`td[data-day='${dia}'][data-slot='${slot}']`);
        if (celda) celda.classList.add('seleccionada');
    });
}

// ----------------- Selección y Guardado -----------------
tblGrilla.addEventListener('click', (e) => {
    if (e.target.tagName === 'TD' && !e.target.classList.contains('recreo')) {
        e.target.classList.toggle('seleccionada');
    }
});

async function guardarMallaHoraria() {
  if (!confirm("¿Estás seguro de que deseas guardar estos cambios?\nLos horarios anteriores para esta materia y turno serán reemplazados.")) return;

  btnGuardar.disabled = true;
  btnGuardar.textContent = "Guardando...";

  const payload = {
    profesorado_id: selCarrera.value,
    plan_id: selPlan.value,
    materia_id: selMateria.value,
    periodo_id: selPeriodo.value,
    turno: turnoSlugFromSelect(selTurno),
    comision_id: selComision.value,
    items: [],
  };

  if (!payload.profesorado_id || !payload.plan_id || !payload.materia_id || !payload.comision_id || !payload.periodo_id) {
    alert("Por favor, seleccione todos los campos, incluyendo la comisión, antes de guardar.");
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Guardar Malla Horaria";
    return;
  }

  const diaMap = { '1': 'lu', '2': 'ma', '3': 'mi', '4': 'ju', '5': 'vi', '6': 'sa' };
  tblGrilla.querySelectorAll('td.seleccionada').forEach(td => {
    const dayCode = td.dataset.day;
    const rowIndex = parseInt(td.dataset.row, 10);
    const dia = diaMap[dayCode];
    const slot = (dayCode === '6') ? currentSlots.sab[rowIndex] : currentSlots.lv[rowIndex];
    if (dia && slot) payload.items.push({ dia: dia, inicio: slot.ini, fin: slot.fin });
  });

  try {
    const response = await fetch(API.guardar(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (response.ok && result.ok) {
        alert(`Guardado exitoso. Se guardaron ${result.count} bloques.`);
    } else {
        alert(`Error al guardar: ${result.error || 'Respuesta no válida.'}`);
    }
  } catch (error) {
    console.error('Error en la petición de guardado:', error);
    alert('Ocurrió un error de red al intentar guardar.');
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Guardar Malla Horaria";
  }
}

// ----------------- Eventos Iniciales -----------------
selCarrera.addEventListener('change', cargarPlanes);
selPlan.addEventListener('change', cargarMaterias);
selPeriodo.addEventListener('change', cargarMaterias);
selMateria.addEventListener('change', cargarComisiones);
selTurno.addEventListener('change', cargarGrillaYHorarios);
selComision.addEventListener('change', cargarGrillaYHorarios);
btnGuardar?.addEventListener("click", guardarMallaHoraria);

document.addEventListener("DOMContentLoaded", () => {
  if (selCarrera.value) {
    cargarPlanes().then(() => {
      if (selPlan.value) cargarMaterias();
    });
  }
});
