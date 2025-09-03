import { resetSelect } from "./utils/form_helpers.js";
(function () {
  const form = document.getElementById("form-insc-mat");
  if (!form) return;

  const urlPlanes   = form.dataset.planesUrl;
  const urlMaterias = form.dataset.materiasUrl;

  const selProf = document.getElementById("id_profesorado");
  const selPlan = document.getElementById("id_plan");
  const selMat  = document.getElementById("id_materia");

  const prefill = (window.__INSCR_MAT_PREFILL__) || {prof:"", plan:"", mat:""};

  

  function populateSelect(sel, items, placeholder) {
    resetSelect(sel, placeholder);
    for (const it of items) {
      const opt = document.createElement("option");
      opt.value = it.id;
      opt.textContent = it.label;
      sel.appendChild(opt);
    }
    if (items.length === 1) {
      sel.value = String(items[0].id);
      sel.dispatchEvent(new Event("change"));
    }
  }

  

  

  async function loadMaterias(planId, trySelectPrefill=false) {
    selMat.disabled = true;
    resetSelect(selMat, "Cargando materias...");
    if (!planId) {
      resetSelect(selMat, "Esperando plan...");
      return;
    }

    const url = `${urlMaterias}?plan_id=${encodeURIComponent(planId)}`;
    const items = await fetchJSON(url, "materias");

    populateSelect(selMat, items, "Seleccioná una materia...");
    selMat.disabled = items.length === 0;

    if (trySelectPrefill && prefill.mat) {
      const exists = Array.from(selMat.options).some(o => String(o.value) === String(prefill.mat));
      if (exists) selMat.value = prefill.mat;
    }
  }

  // Listeners
  selProf.addEventListener("change", () => {
    const profId = selProf.value || "";
    prefill.plan = ""; prefill.mat = "";
    window.loadPlanes(form, selProf, selPlan)(profId, false);
  });

  selPlan.addEventListener("change", () => {
    const planId = selPlan.value || "";
    prefill.mat = "";
    loadMaterias(planId, false);
  });

  // Init (con prefill)
  (async function inscripcionMateria_init() {
    if (selProf.value) {
      await window.loadPlanes(form, selProf, selPlan)(selProf.value, true);
    } else if (prefill.prof) {
      selProf.value = prefill.prof;
      await window.loadPlanes(form, selProf, selPlan)(prefill.prof, true);
    }
  })();
})();