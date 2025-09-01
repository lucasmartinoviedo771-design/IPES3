/* static/ui/js/horarios_common.js */

/* Bloques y recreos por turno – mismos que venimos usando */
const GRILLAS = {
  m: {
    label: "Mañana",
    blocks: [
      ["07:45","08:25"], ["08:25","09:05"], ["09:05","09:15"], // <- recreo
      ["09:15","09:55"], ["09:55","10:35"], ["10:35","10:45"], // <- recreo
      ["10:45","11:25"], ["11:25","12:05"], ["12:05","12:45"]
    ],
    breaks: [["09:05","09:15"],["10:35","10:45"]]
  },
  t: {
    label: "Tarde",
    blocks: [
      ["13:00","13:40"], ["13:40","14:20"], ["14:20","14:30"], // recreo
      ["14:30","15:10"], ["15:10","15:50"], ["15:50","16:00"], // recreo
      ["16:00","16:40"], ["16:40","17:20"], ["17:20","17:40"]
    ],
    breaks: [["14:20","14:30"],["15:50","16:00"]]
  },
  v: {
    label: "Vespertino",
    blocks: [
      ["18:10","18:50"], ["18:50","19:30"], ["19:30","19:40"], // recreo
      ["19:40","20:10"], ["20:10","20:50"], ["20:50","21:00"], // recreo
      ["21:00","21:30"], ["21:30","22:10"], ["22:10","22:50"]
    ],
    breaks: [["19:30","19:40"],["20:50","21:00"]]
  },
  s: {
    label: "Sábado (Mañana)",
    blocks: [
      ["09:00","09:40"], ["09:40","10:20"], ["10:20","10:30"], // recreo
      ["10:30","11:10"], ["11:10","11:50"], ["11:50","12:00"], // recreo
      ["12:00","12:40"], ["12:40","13:40"]
    ],
    breaks: [["10:20","10:30"],["11:50","12:00"]]
  }
};

// Días de la semana
const DAYS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];
const DAY_KEYS = ["lu","ma","mi","ju","vi","sa"];

/** Construye la tabla base (vacía) */
export function buildGrid(container, turnoKey) {
  container.innerHTML = "";
  const g = GRILLAS[turnoKey];
  if (!g) return;

  const table = document.createElement("table");
  table.className = "grid-table";

  // Header
  const thead = document.createElement("thead");
  const trh = document.createElement("tr");
  trh.appendChild(th("Hora"));
  DAYS.forEach(d => trh.appendChild(th(d)));
  thead.appendChild(trh);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");
  g.blocks.forEach(([ini, fin]) => {
    const tr = document.createElement("tr");
    tr.appendChild(td(`${ini} – ${fin}`, "col-time"));

    DAYS.forEach((_d, idx) => {
      const cell = td("", "col-slot");
      if (isBreak(g, ini, fin)) {
        cell.classList.add("is-break");
        cell.textContent = "Recreo";
      } else {
        // queda vacía, se completa con items
        cell.dataset.time = `${ini}-${fin}`;
        cell.dataset.day = DAY_KEYS[idx];
      }
      tr.appendChild(cell);
    });

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
}

function th(t){ const e=document.createElement("th"); e.textContent=t; return e; }
function td(t,c){ const e=document.createElement("td"); if(c) e.className=c; e.textContent=t; return e; }
function isBreak(g, ini, fin){
  return g.breaks.some(([b1,b2]) => b1===ini && b2===fin);
}

/** Pinta un evento (materia/docente) en su celda correspondiente */
export function paintItem(container, item) {
  // item: {dia, inicio, fin, materia, docente, anio, comision, aula?, cuatrimestral?}
  const selector = `td.col-slot[data-day="${item.dia}"][data-time="${item.inicio}-${item.fin}"]`;
  const cell = container.querySelector(selector);
  if (!cell) return;

  const chip = document.createElement("div");
  chip.className = "chip";
  chip.innerHTML = `
    <div class="chip-line ${item.cuatrimestral ? "chip-diag": ""}">
      <strong>${item.materia}</strong>
      <span class="chip-sub">${item.docente || ""}</span>
      <span class="chip-sub">${item.anio || ""}${item.comision?(" · "+item.comision):""}${item.aula?(" · Aula "+item.aula):""}</span>
    </div>
  `;
  cell.appendChild(chip);
}
