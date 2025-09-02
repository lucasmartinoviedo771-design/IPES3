// --- Config horarios por turno (mismo que usaste en Cátedra) ---
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

// --- util común ---
const DAY_INDEX = { lu:1, ma:2, mi:3, ju:4, vi:5, sa:6 };

function makeTable(containerId, headers, tableId) {
  const host = document.getElementById(containerId);
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
  const breaks = new Set((week.breaks || []).map(([a,b]) => `${a}-${b}`));
  const { tbody } = makeTable("hd_grid_left", ["Hora","Lunes","Martes","Miércoles","Jueves","Viernes"], "hd_grid_lv");
  (week.blocks || []).forEach(([from,to])=>{
    const key = `${from}-${to}`;
    const tr = document.createElement("tr");
    const tdTime = document.createElement("td");
    tdTime.className="col-time"; tdTime.textContent=`${from} – ${to}`;
    tr.appendChild(tdTime);
    for(let d=1; d<=5; d++){
      const td = document.createElement("td");
      if (breaks.has(key)){
        td.textContent="Recreo"; td.className="ah-break";
      } else {
        td.className="ah-cell ah-clickable";
        td.dataset.day=String(d);
        td.dataset.hhmm=from;
        td.dataset.hasta=to;
      }
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
}

function drawSabado() {
  const sat = GRILLAS.sabado || {};
  const blocks = sat.blocks || [];
  const breaks = new Set((sat.breaks || []).map(([a,b]) => `${a}-${b}`));
  const { tbody } = makeTable("hd_grid_right", ["Hora (Sábado)","Sábado"], "hd_grid_sab");
  blocks.forEach(([from,to])=>{
    const key = `${from}-${to}`;
    const tr = document.createElement("tr");
    const tdTime = document.createElement("td");
    tdTime.className="col-time"; tdTime.textContent=`${from} – ${to}`;
    tr.appendChild(tdTime);
    const td = document.createElement("td");
    if (breaks.has(key)){
      td.textContent="Recreo"; td.className="ah-break";
    } else {
      td.className="ah-cell ah-clickable";
      td.dataset.day="6";
      td.dataset.hhmm=from;
      td.dataset.hasta=to;
    }
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
}

function renderGridDual(turnoKey){
  drawLV(turnoKey);
  drawSabado();
}

// pinta chip en la celda correcta (L–V o Sábado)
function paintItemDocente(item){
  const d = DAY_INDEX[item.dia];        // 'lu','ma','mi','ju','vi','sa'
  if (!d) return;
  const hh = item.inicio, ff=item.fin;
  const tableId = d===6 ? "hd_grid_sab" : "hd_grid_lv";
  const root = document.getElementById(tableId);
  if (!root) return;
  const sel = `td.ah-cell[data-day="${d}"][data-hhmm="${hh}"][data-hasta="${ff}"]`;
  const cell = root.querySelector(sel);
  if (!cell) return;

  const chip = document.createElement("div");
  chip.className = "chip";
  chip.innerHTML = `
    <div class="chip-line ${item.cuatrimestral ? "chip-diag": ""}">
      <strong>${item.materia || ""}</strong>
      <span class="chip-sub">${item.anio || ""}${item.comision?(" · "+item.comision):""}${item.aula?(" · Aula "+item.aula):""}</span>
    </div>
  `;
  cell.appendChild(chip);
}

// --- API & wiring ---


async function fetchJSON(url, params={}) {
  const qs = new URLSearchParams(params).toString();
  const full = qs ? `${url}?${qs}` : url;
  const r = await fetch(full, { headers: { "Accept": "application/json" } });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${full}`);
  return r.json();
}

async function seedDocentes() {
  const $doc = document.getElementById("hd_docente");
  try {
    console.log("Cargando docentes desde", API_DOCENTES_LIST);
    const data = await fetchJSON(API_DOCENTES_LIST);
    console.log("Respuesta docentes:", data);

    $doc.innerHTML = '<option value="">---------</option>';
    (data.results || []).forEach(d => {
      $doc.add(new Option(d.nombre, d.id));
    });
  } catch (e) {
    console.warn("Error cargando docentes:", e);
    // Para ver el detalle en la UI, si querés:
    $doc.innerHTML = '<option value="">(error al cargar)</option>';
  }
}

async function syncDocente(){
  const id  = document.getElementById("hd_docente")?.value;
  const tun = document.getElementById("hd_turno")?.value || "manana";
  if (!id) return;

  renderGridDual(tun);                       // siempre dibujamos vacío primero
  try{
    const data = await fetchJSON(API_HORARIO_DOC, { docente_id:id, turno:tun });
    (data.items || []).forEach(paintItemDocente);
  }catch(e){
    console.warn("Horario docente:", e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  seedDocentes();                         // opcional
  renderGridDual("manana");

  document.getElementById("hd_turno")?.addEventListener("change", syncDocente);
  document.getElementById("hd_docente")?.addEventListener("change", syncDocente);

  document.getElementById("hd_btn_imprimir")?.addEventListener("click", ()=> window.print());
});
