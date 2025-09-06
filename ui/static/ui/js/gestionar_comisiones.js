// ui/static/ui/js/gestionar_comisiones.js
console.log("gestionar_comisiones.js cargado");

// Helpers (asumimos que fetchJSON y getCookie se cargan desde utils)
function fillSelect($sel, items, textKey = "nombre", valueKey = "id") {
    $sel.innerHTML = '<option value="">---------</option>';
    for (const it of (items || [])) {
        const opt = document.createElement("option");
        opt.value = it[valueKey];
        opt.textContent = it[textKey] ?? it.label ?? String(it[valueKey]);
        $sel.appendChild(opt);
    }
}

document.addEventListener("DOMContentLoaded", () => {

    const selCarrera = document.getElementById("sel-carrera");
    const selPlan = document.getElementById("sel-plan");
    const selMateria = document.getElementById("sel-materia");
    const selPeriodo = document.getElementById("sel-periodo");
    const comisionesContainer = document.getElementById("comisiones-container");

    const API = {
        planes: (carreraId) => `/api/planes/?carrera=${carreraId}`,
        materias: (planId, periodoId) => `/api/materias/?plan_id=${planId}&periodo_id=${periodoId}`,
        comisiones: (params) => `/api/comisiones/materia/?${params.toString()}`,
        addComision: () => `/api/comisiones/add/`,
    };

    async function updatePlanes() {
        const carreraId = selCarrera.value;
        selPlan.innerHTML = '<option value="">---------</option>';
        selMateria.innerHTML = '<option value="">---------</option>';
        selPlan.disabled = true;
        selMateria.disabled = true;
        comisionesContainer.innerHTML = '<p class="muted">Por favor, completá los campos superiores para ver las comisiones.</p>';
        if (!carreraId) return;

        try {
            const data = await fetchJSON(API.planes(carreraId));
            fillSelect(selPlan, data.results || data);
            selPlan.disabled = false;
        } catch (e) {
            console.error("Error cargando planes:", e);
        }
    }

    async function updateMaterias() {
        const planId = selPlan.value;
        const periodoId = selPeriodo.value;
        selMateria.innerHTML = '<option value="">---------</option>';
        selMateria.disabled = true;
        comisionesContainer.innerHTML = '<p class="muted">Por favor, completá los campos superiores para ver las comisiones.</p>';

        if (!planId || !periodoId) return;

        try {
            const data = await fetchJSON(API.materias(planId, periodoId));
            fillSelect(selMateria, data.results || data);
            selMateria.disabled = false;
        } catch (e) {
            console.error("Error cargando materias:", e);
        }
    }

    async function cargarComisiones() {
        const planId = selPlan.value;
        const materiaId = selMateria.value;
        const periodoId = selPeriodo.value;

        if (!planId || !materiaId || !periodoId) {
            comisionesContainer.innerHTML = '<p class="muted">Por favor, completá los campos superiores para ver las comisiones.</p>';
            return;
        }

        comisionesContainer.innerHTML = '<p class="muted">Cargando...</p>';
        try {
            const params = new URLSearchParams({ plan_id: planId, materia_id: materiaId, periodo_id: periodoId });
            const data = await fetchJSON(API.comisiones(params));
            renderComisiones(data.comisiones || []);
        } catch (e) {
            console.error("Error cargando comisiones:", e);
            comisionesContainer.innerHTML = '<p class="error">No se pudieron cargar las comisiones.</p>';
        }
    }

    function renderComisiones(comisiones) {
        if (comisiones.length === 0) {
            comisionesContainer.innerHTML = '<p>No hay comisiones para esta materia. Puedes crear la inicial.</p>';
        } else {
            let html = '<ul>';
            comisiones.forEach(c => {
                html += `<li>Comisión ${c.seccion} (${c.nombre})</li>`;
            });
            html += '</ul>';
            comisionesContainer.innerHTML = html;
        }

        const ultimaComision = comisiones.length > 0 ? comisiones[comisiones.length - 1].seccion : '@';
        const nuevaSeccion = String.fromCharCode(ultimaComision.charCodeAt(0) + 1);

        comisionesContainer.innerHTML += `<button id="btn-add-comision" class="btn btn-primary mt-3">+ Añadir Comisión ${nuevaSeccion}</button>`;
    }

    async function addComision() {
        const planId = selPlan.value;
        const materiaId = selMateria.value;
        const periodoId = selPeriodo.value;

        if (!planId || !materiaId || !periodoId) {
            alert("Asegúrate de tener seleccionada una Carrera, Plan, Materia y Período.");
            return;
        }

        if (!confirm("¿Estás seguro de que deseas crear una nueva comisión para esta materia?")) {
            return;
        }

        try {
            const payload = { plan_id: planId, materia_id: materiaId, periodo_id: periodoId };
            const data = await fetch(API.addComision(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify(payload)
            }).then(res => res.json());

            if (data.ok) {
                alert(`Comisión ${data.seccion} creada exitosamente.`);
                await cargarComisiones(); // Recargar la lista
            } else {
                alert(`Error al crear la comisión: ${data.error}`);
            }
        } catch (e) {
            console.error("Error al añadir comisión:", e);
            alert("Ocurrió un error de red.");
        }
    }

    // Asignar eventos
    selCarrera.addEventListener('change', updatePlanes);
    selPlan.addEventListener('change', updateMaterias);
    selPeriodo.addEventListener('change', updateMaterias);
    selMateria.addEventListener('change', cargarComisiones);
    comisionesContainer.addEventListener('click', (e) => {
        if (e.target.id === 'btn-add-comision') {
            addComision();
        }
    });
});
