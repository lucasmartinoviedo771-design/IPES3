// ======= Utilidades comunes (idénticas a Cátedra/Docente) =======

const GRILLAS = {
  manana: {
    label: "Mañana",
    blocks: [["07:45","08:25"],["08:25","09:05"],["09:05","09:15"],["09:15","09:55"],["09:55","10:35"],["10:35","10:45"],["10:45","11:25"],["11:25","12:05"],["12:05","12:45"]],
    breaks: [["09:05","09:15"],["10:35","10:45"]]
  },
  tarde: {
    label: "Tarde",
    blocks: [["13:00","13:40"],["13:40","14:20"],["14:20","14:30"],["14:30","15:10"],["15:10","15:50"],["15:50","16:00"],["16:00","16:40"],["16:40","17:20"],["17:20","17:40"]],
    breaks: [["14:20","14:30"],["15:50","16:00"]]
  },
  vespertino: {
    label: "Vespertino",
    blocks: [["18:10","18:50"],["18:50","19:30"],["19:30","19:40"],["19:40","20:10"],["20:10","20:50"],["20:50","21:00"],["21:00","21:30"],["21:30","22:10"],["22:10","22:50"]],
    breaks: [["19:30","19:40"],["20:50","21:00"]]
  },
  sabado: {
    label: "Sábado",
    blocks: [["09:00","09:40"],["09:40","10:20"],["10:20","10:30"],["10:30","11:10"],["11:10","11:50"],["11:50","12:00"],["12:00","12:40"],["12:40","13:20"],["13:20","14:00"]],
    breaks: [["10:20","10:30"],["11:50","12:00"]]
  }
};

const YEARS = [1,2,3,4];
const DAY_INDEX = { lu:1, ma:2, mi:3, ju:4, vi:5, sa:6 };

function fetchJSON(url, params={}) {
  const qs = new URLSearchParams(params).toString();
  const full = qs ? `${url}?${qs}` : url;
  return fetch(full, {headers:{"Accept":"application/json"}}).then(r=>{
    if(!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });
}

function makeTable(containerId, headers, tableId) {
  const host = document.getElementById(containerId);
  host.innerHTML = "";
  const tbl = document.createElement("table");
  tbl.className = "grid-table";
  if (tableId) tbl.id = tableId;
  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  headers.forEach((h,i)=> {
    const th = document.createElement("th");
    th.textContent = h;
    if (i===0) th.className = "col-time";
    trh.appendChild(th);
  });
  thead.appendChild(trh);
  const tbody = document.createElement("tbody");
  tbl.appendChild(thead); tbl.appendChild(tbody);
  host.appendChild(tbl);
  return { table: tbl, tbody };
}

function drawLVInto(turnoKey, leftContainerId, tableIdPrefix) {
  const week = GRILLAS[turnoKey] || GRILLAS.manana;
  const breaks = new Set((week.breaks || []).map(([a,b])=>`${a}-${b}`));
  const { tbody } = makeTable(leftContainerId, ["Hora","Lunes","Martes","Miércoles","Jueves","Viernes"], `${tableIdPrefix}_lv`);
  (week.blocks || []).forEach(([from,to])=>{
    const tr = document.createElement("tr");
    const key = `${from}-${to}`;
    const tdTime = document.createElement("td");
    tdTime.className="col-time"; tdTime.textContent=`${from} – ${to}`;
    tr.appendChild(tdTime);
    for (let d=1; d<=5; d++){
      const td = document.createElement("td");
      if (breaks.has(key)){ td.textContent="Recreo"; td.className="ah-break"; }
      else { td.className="ah-cell"; td.dataset.day=String(d); td.dataset.hhmm=from; td.dataset.hasta=to; }
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
}

function drawSabadoInto(rightContainerId, tableIdPrefix) {
  const sat = GRILLAS.sabado || {};
  const breaks = new Set((sat.breaks || []).map(([a,b])=>`${a}-${b}`));
  const { tbody } = makeTable(rightContainerId, ["Hora (Sábado)","Sábado"], `${tableIdPrefix}_sab`);
  (sat.blocks || []).forEach(([from,to])=>{
    const tr = document.createElement("tr");
    const key = `${from}-${to}`;
    const tdTime = document.createElement("td");
    tdTime.className="col-time"; tdTime.textContent=`${from} – ${to}`;
    tr.appendChild(tdTime);
    const td = document.createElement("td");
    if (breaks.has(key)){ td.textContent="Recreo"; td.className="ah-break"; }
    else { td.className="ah-cell"; td.dataset.day="6"; td.dataset.hhmm=from; td.dataset.hasta=to; }
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
}

function renderDualInto(prefix, turnoKey){
  drawLVInto(turnoKey, `${prefix}_left`,  prefix);
  drawSabadoInto(       `${prefix}_right`, prefix);
}

// ======= Lógica específica PROFESORADO =======

const API_CARRERAS  = "/ui/api/carreras";
const API_PLANES    = "/ui/api/planes";               // ?carrera=ID
const API_HORARIO_P = "/ui/api/horarios/profesorado"; // ?carrera=&plan_id=

// Construye 4 secciones vacías, pero cada una con el TURNO que le toque
function buildProfesoradoSections(turnoPorAnio) {
  const root = document.getElementById("hp_sections");
  root.innerHTML = "";
  YEARS.forEach(y=>{
    const turnoKey = turnoPorAnio[y] || "manana";
    const sec = document.createElement("section");
    sec.className = "grid-section";
    sec.innerHTML = `
      <h3>${y}º Año — ${GRILLAS[turnoKey]?.label || ""}</h3>
      <div class="grid-dual" id="hp_y${y}">
        <div id="hp_y${y}_left"></div>
        <div id="hp_y${y}_right"></div>
      </div>`;
    root.appendChild(sec);
    renderDualInto(`hp_y${y}`, turnoKey);
  });
}

// Detecta el turno de un año mirando los 'inicio' de L–V
function detectarTurno(itemsYear) {
  // Si alguno trae 'turno', lo usamos
  const it = itemsYear.find(x => x.turno && x.dia !== 'sa');
  if (it) return normalizarTurno(it.turno);

  // Si no, detectamos por el inicio
  const setMan = new Set((GRILLAS.manana.blocks||[]).map(b=>b[0]));
  const setTar = new Set((GRILLAS.tarde.blocks||[]).map(b=>b[0]));
  const setVes = new Set((GRILLAS.vespertino.blocks||[]).map(b=>b[0]));
  for (const x of itemsYear) {
    if (x.dia === 'sa') continue; // sábado no define turno L-V
    if (setMan.has(x.inicio)) return "manana";
    if (setTar.has(x.inicio)) return "tarde";
    if (setVes.has(x.inicio)) return "vespertino";
  }
  return "manana"; // fallback
}

function normalizarTurno(t) {
  const s = String(t || "").toLowerCase();
  if (s.startsWith("ma")) return "manana";
  if (s.startsWith("ta")) return "tarde";
  if (s.startsWith("ve")) return "vespertino";
  return "manana";
}

function prepararTurnosPorAnio(payload) {
  // 1) si el backend trae mapping explícito, usamos ese:
  if (payload && payload.turnos_por_anio) {
    const map = {};
    YEARS.forEach(y => map[y] = normalizarTurno(payload.turnos_por_anio[y]));
    return map;
  }
  // 2) si no, detectamos por items
  const porAnio = {};
  YEARS.forEach(y=>{
    const itemsY = (payload.items||[]).filter(it => Number(it.anio) === y);
    porAnio[y] = detectarTurno(itemsY);
  });
  return porAnio;
}

function paintItemProf(item) {
  const y = Number(item.anio);
  if (!YEARS.includes(y)) return;
  const d = DAY_INDEX[item.dia];
  if (!d) return;

  const prefix  = `hp_y${y}`;
  const tableId = d===6 ? `${prefix}_sab` : `${prefix}_lv`;
  const root    = document.getElementById(tableId);
  if (!root) return;

  const sel  = `td.ah-cell[data-day="${d}"][data-hhmm="${item.inicio}"][data-hasta="${item.fin}"]`;
  const cell = root.querySelector(sel);
  if (!cell) return;

  const chip = document.createElement("div");
  chip.className = "chip";
  chip.innerHTML = `
    <div class="chip-line ${item.cuatrimestral?"chip-diag": ""}">
      <strong>${item.materia || ""}</strong>
      <span class="chip-sub">${item.docente || ""}</span>
      <span class="chip-sub">
        ${item.comision?("Comisión "+item.comision+" · "):""}${item.aula?("Aula "+item.aula):""}
      </span>
    </div>`;
  cell.appendChild(chip);
}

// --- UI: combos Carrera/Plan, una sola carga ---
async function seedCarreras(){
  const $c = document.getElementById("hp_carrera");
  const data = await fetchJSON(API_CARRERAS);
  $c.innerHTML = '<option value="">---------</option>';
  (data.results||[]).forEach(x => $c.add(new Option(x.nombre, x.id)));
}

async function seedPlanes(carreraId){
  const $p = document.getElementById("hp_plan");
  $p.innerHTML = '<option value="">---------</option>';
  if (!carreraId) return;
  const data = await fetchJSON(API_PLANES, { carrera:carreraId });
  (data.results||[]).forEach(x => $p.add(new Option(x.nombre, x.id)));
}

async function loadProfesorado(){
  const carrera = document.getElementById("hp_carrera")?.value;
  const plan_id = document.getElementById("hp_plan")?.value;
  if (!carrera || !plan_id) return;

  const payload = await fetchJSON(API_HORARIO_P, { carrera, plan_id });
  const turnosPorAnio = prepararTurnosPorAnio(payload);

  // Dibuja 4 grillas con el turno que le toque a cada año
  buildProfesoradoSections(turnosPorAnio);

  // Pinta todos los items
  (payload.items||[]).forEach(paintItemProf);
}

document.addEventListener("DOMContentLoaded", ()=>{
  seedCarreras();
  // render inicial vacío: por defecto asume mañana en todos
  buildProfesoradoSections({1:"manana",2:"manana",3:"manana",4:"manana"});

  document.getElementById("hp_carrera")?.addEventListener("change", (e)=> seedPlanes(e.target.value));
  document.getElementById("hp_plan")?.addEventListener("change", loadProfesorado);
});
