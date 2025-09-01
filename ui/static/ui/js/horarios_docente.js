/* static/ui/js/horarios_docente.js */
import { buildGrid, paintItem } from "./horarios_common.js";

const $doc = document.getElementById("hd_docente");
const $gridM = document.getElementById("hd_grid_m");
const $gridT = document.getElementById("hd_grid_t");
const $gridV = document.getElementById("hd_grid_v");
const $gridS = document.getElementById("hd_grid_s");

const grids = {
  m: $gridM,
  t: $gridT,
  v: $gridV,
  s: $gridS,
};

document.getElementById("hd_btn_imprimir").addEventListener("click", () => window.print());

// Docentes
(async function loadDocentes(){
  const url = new URL(API_DOCENTES, location.origin);
  const data = await fetch(url).then(r => r.json()).catch(()=>({items:[]}));
  (data.results || data.items || []).forEach(d => $doc.add(new Option(d.nombre, d.id)));
})();

$doc.addEventListener("change", render);

async function render(){
  const docenteId = $doc.value;
  if (!docenteId) {
    Object.values(grids).forEach(grid => grid.innerHTML = "");
    return;
  }

  for (const turno in grids) {
    const grid = grids[turno];
    buildGrid(grid, turno);

    const url = new URL(API_HDOC, location.origin);
    url.searchParams.set("docente_id", docenteId);
    url.searchParams.set("turno", turno);

    const data = await fetch(url).then(r=>r.json()).catch(()=>({items:[]}));
    (data.items || []).forEach(ev => paintItem(grid, ev));
  }
}