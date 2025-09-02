/*
  horarios_profesorado.js
  Lógica para la vista de solo lectura de horarios por profesorado.
*/

// Helpers (asumimos que las APIs se inyectan desde la plantilla)
const API_CARRERAS = window.API_CARRERAS || '/ui/api/carreras';
const API_PLANES = window.API_PLANES || '/ui/api/planes';
const API_HORARIO_P = window.API_HORARIO_P || '/ui/api/horarios/profesorado';
const API_GRILLA_CONFIG = window.API_GRILLA_CONFIG || '/ui/api/grilla-config/';

async function fetchJSON(url, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const fullUrl = qs ? `${url}?${qs}` : url;
    const res = await fetch(fullUrl, { headers: { "Accept": "application/json" } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// --- Lógica de renderizado de la grilla (adaptada de armar_horarios.js) ---

function th(t) { const e = document.createElement("th"); e.textContent = t; return e; }
function td(t, c) { const e = document.createElement("td"); if (c) e.className = c; if (t) e.textContent = t; return e; }

async function renderReadOnlyGrid(containerId, turno, items) {
    const $grid = document.getElementById(containerId);
    if (!$grid) return;
    $grid.innerHTML = "<p class='loading'>Cargando grilla...</p>";

    try {
        const cfgLV = await fetchJSON(API_GRILLA_CONFIG, { turno });
        const cfgSa = await fetchJSON(API_GRILLA_CONFIG, { turno: 'sabado' });

        const lvBlocks = cfgLV.bloques || [];
        const saBlocks = cfgSa.bloques || [];

        const lvTimes = Array.from(new Map(lvBlocks.map(b => [`${b.inicio}-${b.fin}`, { inicio: b.inicio, fin: b.fin }])).values()).sort((a, b) => a.inicio.localeCompare(b.inicio));
        const saTimes = Array.from(new Map(saBlocks.map(b => [`${b.inicio}-${b.fin}`, { inicio: b.inicio, fin: b.fin }])).values()).sort((a, b) => a.inicio.localeCompare(b.inicio));

        const byKeyLV = new Map(lvBlocks.map(b => [`${b.dia_semana}-${b.inicio}-${b.fin}`, b]));
        const byKeySa = new Map(saBlocks.map(b => [`${b.inicio}-${b.fin}`, b]));

        const table = document.createElement("table");
        table.className = "grid-table";

        const thead = document.createElement("thead");
        const trh = document.createElement("tr");
        trh.appendChild(th("Hora (L–V)"));
        ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"].forEach(d => trh.appendChild(th(d)));
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
                    if (byKeyLV.has(key)) {
                        cell.dataset.day = (day + 1);
                        cell.dataset.hhmm = lvTime.inicio;
                    }
                }
                tr.appendChild(cell);
            }

            const saTime = saTimes[i] || null;
            const tdSa = td("", "col-slot");
            if (saTime && byKeySa.has(`${saTime.inicio}-${saTime.fin}`)) {
                tdSa.dataset.day = 6;
                tdSa.dataset.hhmm = saTime.inicio;
            }
            tr.appendChild(tdSa);
            tr.appendChild(td(saTime ? `${saTime.inicio} – ${saTime.fin}` : "", "col-time col-time-right"));
            tbody.appendChild(tr);
        }

        table.appendChild(tbody);
        $grid.innerHTML = "";
        $grid.appendChild(table);

        // Pintar los items sobre la grilla generada
        const mapDiaToNum = {'lu':1, 'ma':2, 'mi':3, 'ju':4, 'vi':5, 'sa':6};
        items.forEach(item => {
            const dayNum = mapDiaToNum[item.dia];
            const cell = table.querySelector(`td[data-day='${dayNum}'][data-hhmm='${item.inicio}']`);
            if (cell) {
                const chip = document.createElement("div");
                chip.className = "chip";
                chip.innerHTML = `<strong>${item.materia}</strong><span class='chip-sub'>${item.comision || ''}</span>`;
                cell.appendChild(chip);
            }
        });

    } catch (e) {
        console.error("Error rendering grid:", e);
        $grid.innerHTML = "<p class='error'>Error al cargar la grilla.</p>";
    }
}

// --- Lógica principal ---

function detectarTurnoPrincipal(items) {
    if (!items || items.length === 0) return 'manana'; // Default
    const turnos = items.map(i => i.turno).filter(t => t && t !== 'sabado');
    if (turnos.length === 0) return 'manana';
    // Devuelve el turno más frecuente
    const counts = turnos.reduce((acc, t) => (acc[t] = (acc[t] || 0) + 1, acc), {});
    return Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
}

async function loadProfesorado() {
    const profesorado_id = document.getElementById("hp_carrera")?.value;
    const plan_id = document.getElementById("hp_plan")?.value;
    
    // Ocultar todas las secciones antes de cargar
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`year-section-${i}`).style.display = 'none';
    }

    if (!profesorado_id || !plan_id) return;

    const data = await fetchJSON(API_HORARIO_P, { profesorado_id, plan_id });

    for (let anio = 1; anio <= 4; anio++) {
        const itemsDelAnio = data[anio] || [];
        const section = document.getElementById(`year-section-${anio}`);
        if (itemsDelAnio.length > 0) {
            section.style.display = 'block';
            const turnoPrincipal = detectarTurnoPrincipal(itemsDelAnio);
            await renderReadOnlyGrid(`grid-container-${anio}`, turnoPrincipal, itemsDelAnio);
        } else {
            section.style.display = 'none';
        }
    }
}

async function init() {
    const selCarrera = document.getElementById("hp_carrera");
    const selPlan = document.getElementById("hp_plan");

    const carreras = await fetchJSON(API_CARRERAS);
    selCarrera.innerHTML = '<option value="">---------</option>';
    (carreras.results || []).forEach(c => selCarrera.add(new Option(c.nombre, c.id)));

    selCarrera.addEventListener('change', async (e) => {
        selPlan.innerHTML = '<option value="">---------</option>';
        if (!e.target.value) return;
        const planes = await fetchJSON(API_PLANES, { carrera: e.target.value });
        (planes.results || []).forEach(p => selPlan.add(new Option(p.nombre, p.id)));
    });

    selPlan.addEventListener('change', loadProfesorado);
}

document.addEventListener("DOMContentLoaded", init);