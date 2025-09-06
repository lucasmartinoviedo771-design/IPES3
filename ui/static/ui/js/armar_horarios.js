// static/ui/js/armar_horarios.js
// v18 - Carga de horarios existentes y confirmación de guardado.
console.log("armar_horarios.js v18 cargado");

// ----------------- helpers -----------------
async function fetchJSON(url) {
  const r = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`HTTP ${r.status} en ${url}\n${txt}`);
  }
  return r.json();
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

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
  const ini = (s.inicio || s.ini || s.start || s.hora_inicio || s.desde).slice(0, 5); // HH:MM
  const fin = (s.fin || s.hora_fin || s.hasta || s.end).slice(0, 5); // HH:MM
  const recreo = s.es_recreo ?? s.recreo ?? s.is_break ?? false;
  return { ini, fin, recreo };
}

// ----------------- elementos y estado -----------------
const selCarrera = document.getElementById("sel-carrera");
const selPlan    = document.getElementById("sel-plan");
const selMateria = document.getElementById("sel-materia");
const selTurno   = document.getElementById("sel-turno");
const tblGrilla  = document.getElementById("grilla");
const btnGuardar = document.getElementById("btn-guardar");

let currentSlots = { lv: [], sab: [] };

// ----------------- rutas API -----------------
const API = {
  planes:      (carreraId) => `/panel/horarios/api/planes/?carrera=${encodeURIComponent(carreraId)}`,
  materias:    (planId)    => `/panel/horarios/api/materias/?plan=${encodeURIComponent(planId)}`,
  timeslots:   (turno)     => `/panel/horarios/api/timeslots/?turno=${encodeURIComponent(turno)}`,
  getHorarios: (params)    => `/api/horarios/materia/?${params.toString()}`,
  guardar:     ()          => `/api/horario/save`,
};

// ----------------- combos -----------------
async function cargarPlanes() {
  const carreraId = selCarrera.value;
  selPlan.innerHTML = '<option value="">---------</option>';
  selMateria.innerHTML = '<option value="">---------</option>';
  if (!carreraId) return;
  try {
    const data = await fetchJSON(API.planes(carreraId));
    fillSelect(selPlan, data.results || data);
  } catch (e) {
    console.error(e);
    alert("No se pudieron cargar los planes.");
  }
}

async function cargarMaterias() {
  const planId = selPlan.value;
  selMateria.innerHTML = '<option value="">---------</option>';
  if (!planId) return;
  try {
    const data = await fetchJSON(API.materias(planId));
    fillSelect(selMateria, data.results || data, "nombre", "id");
    await cargarTimeSlots();
  } catch (e) {
    console.error(e);
    alert("No se pudieron cargar las materias.");
  }
}

// ----------------- grilla -----------------
function dibujarHeader() {
  const thead = document.createElement("thead");
  thead.innerHTML = `
      <tr>
        <th>Hora (L-V)</th>
        <th>Lun</th><th>Mar</th><th>Mié</th><th>Jue</th><th>Vie</th>
        <th>Sáb</th>
        <th>Hora (Sábado)</th>
      </tr>
    `;
  return thead;
}

window.buildBody = function(lvSlots, sabSlots) {
  const tbody = document.createElement("tbody");
  const maxRows = Math.max(lvSlots.length, sabSlots.length);

  for (let i = 0; i < maxRows; i++) {
    const tr = document.createElement("tr");
    const lv = lvSlots[i] ? normSlot(lvSlots[i]) : null;
    const thHoraLV = document.createElement("th");
    thHoraLV.className = "col-hora";
    thHoraLV.textContent = lv ? `${lv.ini} – ${lv.fin}` : "";
    tr.appendChild(thHoraLV);

    for (let d = 0; d < 5; d++) {
      const td = document.createElement("td");
      td.dataset.row = String(i);
      td.dataset.day = String(d + 1);
      if (lv) { td.dataset.slot = `${lv.ini}-${lv.fin}`; }
      if (lv?.recreo) { td.classList.add("recreo"); td.textContent = "Recreo"; }
      tr.appendChild(td);
    }

    const sab = sabSlots[i] ? normSlot(sabSlots[i]) : null;
    const tdSab = document.createElement("td");
    tdSab.dataset.row = String(i);
    tdSab.dataset.day = "6";
    if (sab) { tdSab.dataset.slot = `${sab.ini}-${sab.fin}`; }
    if (sab?.recreo) { tdSab.classList.add("recreo"); tdSab.textContent = "Recreo"; }
    tr.appendChild(tdSab);

    const thHoraSab = document.createElement("th");
    thHoraSab.className = "col-hora";
    thHoraSab.textContent = sab ? `${sab.ini} – ${sab.fin}` : "";
    tr.appendChild(thHoraSab);
    tbody.appendChild(tr);
  }
  return tbody;
};

function dibujarGrilla(slots) {
  currentSlots.lv = (slots.lv || []).map(normSlot);
  currentSlots.sab = (slots.sab || []).map(normSlot);

  tblGrilla.innerHTML = "";
  tblGrilla.appendChild(dibujarHeader());
  tblGrilla.appendChild(window.buildBody(currentSlots.lv, currentSlots.sab));
}

function pintarHorariosExistentes(horarios) {
    const diaMap = { 'lu': '1', 'ma': '2', 'mi': '3', 'ju': '4', 'vi': '5', 'sa': '6' };
    horarios.forEach(h => {
        const dia = diaMap[h.dia];
        const slot = `${h.inicio.slice(0,5)}-${h.fin.slice(0,5)}`;
        const celda = tblGrilla.querySelector(`td[data-day='${dia}'][data-slot='${slot}']`);
        if (celda) {
            celda.classList.add('seleccionada');
        }
    });
}

async function cargarTimeSlots() {
  const profesorado_id = selCarrera.value;
  const plan_id = selPlan.value;
  const materia_id = selMateria.value;
  const turno = turnoSlugFromSelect(selTurno);

  if (!profesorado_id || !plan_id || !materia_id) {
    tblGrilla.innerHTML = "";
    const cp = document.createElement("caption");
    cp.style.captionSide = "bottom";
    cp.textContent = "Seleccioná Carrera, Plan, Materia y Turno.";
    tblGrilla.appendChild(cp);
    return;
  }

  try {
    const params = new URLSearchParams({ profesorado_id, plan_id, materia_id, turno });
    const [layoutData, existentesData] = await Promise.all([
        fetchJSON(API.timeslots(turno)),
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

// ----------------- Selección y Guardado -----------------
tblGrilla.addEventListener('click', (e) => {
    if (e.target.tagName === 'TD' && !e.target.classList.contains('recreo')) {
        e.target.classList.toggle('seleccionada');
    }
});

async function guardarMallaHoraria() {
  if (!confirm("¿Estás seguro de que deseas guardar estos cambios?\nLos horarios anteriores para esta materia y turno serán reemplazados.")) {
      return;
  }

  btnGuardar.disabled = true;
  btnGuardar.textContent = "Guardando...";

  const payload = {
    profesorado_id: selCarrera.value,
    plan_id: selPlan.value,
    materia_id: selMateria.value,
    turno: turnoSlugFromSelect(selTurno),
    items: [],
  };

  if (!payload.profesorado_id || !payload.plan_id || !payload.materia_id) {
    alert("Por favor, seleccione Carrera, Plan y Materia antes de guardar.");
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Guardar Malla Horaria";
    return;
  }

  const diaMap = { '1': 'lu', '2': 'ma', '3': 'mi', '4': 'ju', '5': 'vi', '6': 'sa' };
  const celdasSeleccionadas = tblGrilla.querySelectorAll('td.seleccionada');

  celdasSeleccionadas.forEach(td => {
    const dayCode = td.dataset.day;
    const rowIndex = parseInt(td.dataset.row, 10);
    const dia = diaMap[dayCode];
    const slot = (dayCode === '6') ? currentSlots.sab[rowIndex] : currentSlots.lv[rowIndex];

    if (dia && slot) {
      payload.items.push({ dia: dia, inicio: slot.ini, fin: slot.fin });
    }
  });

  try {
    const csrftoken = getCookie('csrftoken');
    const response = await fetch(API.guardar(), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload)
    });

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
        const result = await response.json();
        if (result.ok) {
            alert(`Guardado exitoso. Se guardaron ${result.count} bloques.`);
        } else {
            alert(`Error al guardar: ${result.error || 'Error desconocido.'}`);
        }
    } else {
        const errorText = await response.text();
        console.error("La respuesta del servidor no fue JSON. Contenido:", errorText);
        alert("Error: El servidor devolvió una respuesta inesperada. Revisa la consola del navegador (F12) para más detalles.");
    }
  } catch (error) {
    console.error('Error en la petición de guardado (red/inesperado):', error);
    alert('Ocurrió un error de red o un error inesperado al intentar guardar.');
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = "Guardar Malla Horaria";
  }
}

btnGuardar?.addEventListener("click", guardarMallaHoraria);

// ----------------- eventos iniciales -----------------
selCarrera?.addEventListener("change", cargarPlanes);
selPlan?.addEventListener("change", cargarMaterias);
selTurno?.addEventListener("change", cargarTimeSlots);
selMateria?.addEventListener("change", cargarTimeSlots);

document.addEventListener("DOMContentLoaded", () => {
  if (selCarrera?.value) {
    cargarPlanes().then(() => {
      if (selPlan?.value) cargarMaterias();
    });
  }
});
