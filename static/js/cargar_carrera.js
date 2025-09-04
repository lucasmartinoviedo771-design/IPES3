(() => {
  const sel = document.getElementById("selCarrera");
  const txtNombre = document.getElementById("txtNombre");
  const txtAbrev  = document.getElementById("txtAbrev");
  const chkVig    = document.getElementById("chkVigente");
  const btnNueva  = document.getElementById("btnNueva");
  const btnGuardar= document.getElementById("btnGuardar");
  const btnEliminar= document.getElementById("btnEliminar");
  const msg       = document.getElementById("msg");

  const showMsg = (text, ok=true) => {
    msg.style.display = "block";
    msg.style.borderColor = ok ? "#d7e6d7" : "#f3c2c2";
    msg.style.background = ok ? "#f2faf2" : "#fff0f0";
    msg.textContent = text;
  };

  const clearForm = () => {
    sel.value = "";
    txtNombre.value = "";
    txtAbrev.value = "";
    chkVig.checked = true;
    msg.style.display = "none";
  };

  // Cargar datos de una carrera
  sel.addEventListener("change", async () => {
    const id = sel.value;
    if (!id) { clearForm(); return; }
    const r = await fetch(`/panel/administracion/carreras/api/get/${id}/`);
    const js = await r.json();
    if (!js.ok) { showMsg("No se pudo cargar la carrera", false); return; }
    const d = js.data;
    txtNombre.value = d.nombre || "";
    txtAbrev.value  = d.nombre_corto || "";
    chkVig.checked  = !!d.vigente;
  });

  btnNueva.addEventListener("click", clearForm);

  btnGuardar.addEventListener("click", async () => {
    const payload = {
      id: sel.value || null,
      nombre: txtNombre.value.trim(),
      nombre_corto: txtAbrev.value.trim(),
      vigente: chkVig.checked
    };
    if (!payload.nombre) { showMsg("El nombre es obligatorio", false); return; }

    const r = await fetch(`/panel/administracion/carreras/api/save/`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const js = await r.json();
    if (!js.ok) {
      if (js.errors) {
        // Mostrar primeros errores del form
        const first = Object.values(js.errors)[0];
        showMsg(Array.isArray(first) ? first.join(" • ") : String(first), false);
      } else {
        showMsg(js.error || "No se pudo guardar", false);
      }
      return;
    }
    // Si fue nuevo, actualizamos el select
    if (!payload.id) {
      const opt = document.createElement("option");
      opt.value = js.id;
      opt.textContent = payload.nombre;
      sel.appendChild(opt);
      sel.value = js.id;
    } else {
      // Si se editó, refrescamos el texto de la opción seleccionada
      const opt = sel.querySelector(`option[value="${payload.id}"]`);
      if (opt) opt.textContent = payload.nombre;
    }
    showMsg("Guardado con éxito");
  });

  btnEliminar.addEventListener("click", async () => {
    const id = sel.value;
    if (!id) { showMsg("Seleccioná una carrera primero", false); return; }
    if (!confirm("¿Eliminar esta carrera?")) return;

    const r = await fetch(`/panel/administracion/carreras/api/delete/${id}/`, { method: "POST" });
    const js = await r.json();
    if (!js.ok) { showMsg(js.error || "No se pudo eliminar", false); return; }

    // Quitar del select y limpiar
    const opt = sel.querySelector(`option[value="${id}"]`);
    if (opt) opt.remove();
    clearForm();
    showMsg("Eliminada con éxito");
  });
})();