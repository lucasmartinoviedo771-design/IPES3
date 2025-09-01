/* static/ui/js/horarios_profesorado.js */
import { buildGrid, paintItem } from "./horarios_common.js";

const $carrera = document.getElementById("hp_carrera");
const $plan    = document.getElementById("hp_plan");
const $turno   = document.getElementById("hp_turno");
const $grid    = document.getElementById("hp_grid");

document.getElementById("hp_btn_imprimir").addEventListener("click", () => window.print());

// Carga inicial de carreras
(async function loadCarreras() {
  const url = new URL(API_CARRERAS, location.origin);
  const data = await fetch(url).then(r => r.json()).catch(() => ({ results: [] }));
  (data.results || []).forEach(c => {
    $carrera.add(new Option(c.nombre, c.id));
  });
})();

// Carga planes por carrera (tus endpoints ya existentes)
$carrera.addEventListener("change", async () => {
  $plan.innerHTML = `<option value="">---------</option>`;
  $plan.disabled = true;
  if (!$carrera.value) return;
  const url = new URL(API_PLANES, location.origin);
  url.searchParams.set("carrera", $carrera.value);
  const data = await fetch(url).then(r => r.json());
  (data.results || data.items || []).forEach(p => {
    $plan.add(new Option(p.nombre, p.id));
  });
  $plan.disabled = false;
  render();
});

$plan.addEventListener("change", render);
$turno.addEventListener("change", render);

async function render() {
  const turno = $turno.value;
  if (!turno) { $grid.innerHTML=""; return; }
  buildGrid($grid, turno);

  if (!$carrera.value || !$plan.value) return;

  const url = new URL(API_HPROF, location.origin);
  url.searchParams.set("carrera", $carrera.value);
  url.searchParams.set("plan_id", $plan.value);
  url.searchParams.set("turno", turno);

  const data = await fetch(url).then(r=>r.json()).catch(()=>({items:[]}));
  (data.items || []).forEach(ev => paintItem($grid, ev));
}
