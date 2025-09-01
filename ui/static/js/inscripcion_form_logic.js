
document.addEventListener('DOMContentLoaded', function () {
    // --- Elementos del Formulario ---
    const form = document.querySelector('form');
    const carreraSelect = form.querySelector('[name="profesorado"]');

    // Grupos de campos a mostrar/ocultar
    const tituloSecundarioGroup = document.getElementById('id_grupo_titulo_secundario');
    const tituloSuperiorGroup = document.getElementById('id_grupo_titulo_superior');
    const adeudaMateriasGroup = document.getElementById('id_grupo_adeuda_materias');

    // Checkboxes mutuamente excluyentes
    const tituloSecundarioCheck = form.querySelector('[name="req_titulo_sec"]');
    const tituloEnTramiteCheck = form.querySelector('[name="req_titulo_tramite"]');
    const adeudaMateriasCheck = form.querySelector('[name="req_adeuda"]');
    const mutualExclusionGroup = [tituloSecundarioCheck, tituloEnTramiteCheck, adeudaMateriasCheck];

    // --- Lógica de la Aplicación ---

    // Función para manejar la visibilidad basada en la carrera seleccionada
    function handleCarreraChange() {
        if (!carreraSelect) return;

        const selectedOption = carreraSelect.options[carreraSelect.selectedIndex];
        // El valor real puede ser el ID, pero el texto es lo que vemos.
        // Usamos el texto de la etiqueta del form de Django para ser más robustos.
        const isCertificacionDocente = selectedOption.text.includes('Certificación Docente');

        if (isCertificacionDocente) {
            // Ocultar Título Secundario y sus relacionados
            if (tituloSecundarioGroup) tituloSecundarioGroup.style.display = 'none';
            if (tituloSecundarioCheck) tituloSecundarioCheck.checked = false;
            if (tituloEnTramiteCheck) tituloEnTramiteCheck.checked = false;
            if (adeudaMateriasCheck) adeudaMateriasCheck.checked = false;
            
            // Mostrar Título Superior
            if (tituloSuperiorGroup) tituloSuperiorGroup.style.display = 'block';
        } else {
            // Mostrar Título Secundario
            if (tituloSecundarioGroup) tituloSecundarioGroup.style.display = 'block';
            
            // Ocultar Título Superior
            if (tituloSuperiorGroup) tituloSuperiorGroup.style.display = 'none';
            if (form.querySelector('[name="req_titulo_sup"]')) form.querySelector('[name="req_titulo_sup"]').checked = false;
            if (form.querySelector('[name="req_incumbencias"]')) form.querySelector('[name="req_incumbencias"]').checked = false;
        }
        // Siempre re-evaluar la visibilidad de los detalles de materias adeudadas
        toggleAdeudaMateriasDetails();
    }

    // Función para manejar la exclusión mutua de los checkboxes de titulación
    function handleMutualExclusion(event) {
        const currentCheckbox = event.target;
        if (currentCheckbox.checked) {
            mutualExclusionGroup.forEach(checkbox => {
                if (checkbox !== currentCheckbox) {
                    checkbox.checked = false;
                }
            });
        }
        // Re-evaluar si mostramos los detalles de materias adeudadas
        toggleAdeudaMateriasDetails();
    }

    // Función para mostrar/ocultar los detalles de materias adeudadas
    function toggleAdeudaMateriasDetails() {
        if (adeudaMateriasGroup) {
            adeudaMateriasGroup.style.display = adeudaMateriasCheck && adeudaMateriasCheck.checked ? 'block' : 'none';
        }
    }

    // --- Inicialización y Event Listeners ---

    // Añadir listeners a los checkboxes de exclusión mutua
    mutualExclusionGroup.forEach(checkbox => {
        if (checkbox) {
            checkbox.addEventListener('change', handleMutualExclusion);
        }
    });

    // Añadir listener al selector de carrera
    if (carreraSelect) {
        carreraSelect.addEventListener('change', handleCarreraChange);
    }

    // Ejecutar las funciones al inicio para establecer el estado inicial correcto
    handleCarreraChange();
    toggleAdeudaMateriasDetails();
});
