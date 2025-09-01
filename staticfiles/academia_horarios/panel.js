async function loadBloques() {
  const selTurno = document.getElementById("id_turno");
  const selDia   = document.getElementById("id_dia");
  const selBloq  = document.getElementById("id_bloque");

  if (!selTurno || !selDia || !selBloq) return;

  const turno = selTurno.value;
  const dia   = selDia.value;

  selBloq.innerHTML = ""; // limpiar
  selBloq.add(new Option("— seleccioná turno y/o día —", ""));

  // No cargar nada si no hay al menos un filtro
  if (!turno && !dia) return;

  const params = new URLSearchParams();
  if (turno) params.append("turno", turno);
  if (dia) params.append("dia", dia);

  const url = `/panel/horarios/api/timeslots/?${params.toString()}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
        selBloq.firstElementChild.textContent = "(error al cargar)";
        return;
    }
    const data = await res.json();

    if (!data.items || !data.items.length) {
        selBloq.firstElementChild.textContent = "(no hay bloques con ese filtro)";
        return;
    }

    // Quitar el placeholder y poblar
    selBloq.innerHTML = "";
    for (const it of (data.items || [])) {
        selBloq.add(new Option(it.label, it.id));
    }
  } catch (err) {
    selBloq.firstElementChild.textContent = "(error de red)";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  ["id_turno","id_dia"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", loadBloques);
  });
  // No hacemos precarga para no traer todos los bloques de una vez.
  // El usuario debe elegir un filtro primero.
});

function updateDocentesSummary() {
  const sel = document.getElementById("id_docentes");
  const summary = document.getElementById("docentesSummary");
  const countEl = document.getElementById("docCount");
  if (!sel || !summary) return;

  const selected = Array.from(sel.selectedOptions).map(o => o.text.trim());

  // contador en el label
  if (countEl) countEl.textContent = selected.length ? `(${selected.length})` : "";

  // chips/resumen
  if (!selected.length) {
    summary.innerHTML = '<em>No hay docentes seleccionados</em>';
    return;
  }
  summary.innerHTML = selected
    .map(n => `<span class="chip">${n}</span>`)
    .join(" ");
}

document.addEventListener("DOMContentLoaded", () => {
  const sel = document.getElementById("id_docentes");
  if (sel) {
    sel.addEventListener("change", updateDocentesSummary);
    sel.addEventListener("keyup", updateDocentesSummary); // soporta teclado
    updateDocentesSummary(); // inicial
  }
});