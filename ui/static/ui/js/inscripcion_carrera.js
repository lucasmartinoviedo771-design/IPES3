(function () {
  const form = document.querySelector('#insc-carrera-form');
  if (!form) return;

  const selEst   = form.querySelector('#id_estudiante');
  const selProf  = form.querySelector('#id_profesorado');
  const selPlan  = form.querySelector('#id_plan');

  const rowTSec   = document.getElementById('row-titulo-sec');
  const rowTram   = document.getElementById('row-titulo-tramite');
  const rowAdeuda = document.getElementById('row-adeuda');
  const adeudaBox = form.querySelector('#id_req_adeuda') || document.getElementById('id_req_adeuda');
  const adeudaExtra = document.getElementById('adeuda-extra');

  const bloqueSup = document.getElementById('req-cert-docente');

  const pillRegular = document.getElementById('pill-regular');
  const pillCond    = document.getElementById('pill-cond');
  const ddjjWrap    = document.getElementById('ddjj-wrap');

  const CERT_DOCENTE_LABEL = (window.CERT_DOCENTE_LABEL || 'Certificación Docente para la Educación Secundaria').trim();

  // Helpers
  function getCbx(id) { return form.querySelector('#'+id); }
  function ch(el) { return !!(el && el.checked); }
  
  function disable(el, v) { if(!el) return; el.disabled = !!v; if(v) el.checked = false; }
  function textOfSelect(sel){ if(!sel) return ''; const opt = sel.options[sel.selectedIndex]; return opt ? (opt.text || '').trim() : ''; }

  // 1) Toggle Adeuda detalle
  function onAdeudaToggle() {
    const v = ch(adeudaBox);
    window.UI.show(adeudaExtra, v);
  }

  // --- Exclusividad entre: Título secundario / Título en trámite / Adeuda materias
function setupExclusivos() {
  const tSec  = getCbx('id_req_titulo_sec');
  const tTram = getCbx('id_req_titulo_tramite');
  const adeu  = getCbx('id_req_adeuda');
  const group = [tSec, tTram, adeu].filter(Boolean);

  function wire(cb) {
    if (!cb) return;
    cb.addEventListener('change', () => {
      // si se destilda, solo sincronizamos visibilidad y estado
      if (!cb.checked) {
        if (cb === adeu) onAdeudaToggle();
        updateStatus();
        return;
      }
      // si se tilda, apagamos los otros dos
      group.forEach(other => {
        if (other && other !== cb && other.checked) {
          other.checked = false;
          if (other === adeu) onAdeudaToggle(); // cerrar "adeuda-extra" si estaba abierto
        }
      });
      if (cb === adeu) onAdeudaToggle(); // abrir "adeuda-extra" si corresponde
      updateStatus();
    });
  }

  group.forEach(wire);
}

  // 2) Cargar Planes por AJAX
  

  // 3) Regla de negocio según PROFESORADO
  function applyProfRules() {
    const isCert = textOfSelect(selProf) === CERT_DOCENTE_LABEL;

    // Common: mostrar/ocultar bloques
    window.UI.show(bloqueSup, isCert);

    // Activar/desactivar los de Secundario
    const cbTituloSec   = getCbx('id_req_titulo_sec');
    const cbTituloTram  = getCbx('id_req_titulo_tramite');
    const cbAdeuda      = getCbx('id_req_adeuda');

    window.UI.show(rowTSec,   !isCert);
    window.UI.show(rowTram,   !isCert);
    window.UI.show(rowAdeuda, !isCert);
    window.UI.show(adeudaExtra, !isCert && ch(cbAdeuda));

    disable(cbTituloSec,  isCert);
    disable(cbTituloTram, isCert);
    disable(cbAdeuda,     isCert);

    // Al cambiar el régimen, recalculamos estado
    updateStatus();
  }

  // 4) Cálculo del estado Administrativo
  function updateStatus() {
    const isCert = textOfSelect(selProf) === CERT_DOCENTE_LABEL;

    // Comunes (si querés que para CERT también se exijan, cambia "false" a sus checks)
    const okDNI      = ch(getCbx('id_req_dni'));
    const okMedico   = ch(getCbx('id_req_cert_med'));
    const okFotos    = ch(getCbx('id_req_fotos'));
    const okFolios   = ch(getCbx('id_req_folios'));

    // Secundario
    const okTituloSec = ch(getCbx('id_req_titulo_sec'));
    // const okTituloTram = ch(getCbx('id_req_titulo_tramite')); // opcional para reg/cond

    // Superior (para Cert Docente)
    const okTituloSup   = ch(getCbx('id_req_titulo_sup'));
    const okIncumb      = ch(getCbx('id_req_incumbencias'));

    let regular = false;
    if (isCert) {
      // Para Certificación Docente: se toman SOLO estos (según lo pedido)
      regular = okTituloSup && okIncumb;
    } else {
      // Para el resto: DNI + Cert médico + Fotos + Folios + Título Secundario
      regular = okDNI && okMedico && okFotos && okFolios && okTituloSec;
    }

    // Mostrar píldoras + DDJJ si es condicional
    window.UI.show(pillRegular,  regular);
    window.UI.show(pillCond,    !regular);
    window.UI.show(ddjjWrap,    !regular);
  }

  // Listeners
  if (adeudaBox) adeudaBox.addEventListener('change', onAdeudaToggle);
  if (selProf) {
    selProf.addEventListener('change', () => { window.loadPlanes(form, selProf, selPlan); applyProfRules(); });
  }
  form.addEventListener('change', updateStatus);

  // Init (prefill estudiante si viene por GET, cargar planes si ya hay prof, etc.)
  onAdeudaToggle();
  applyProfRules();
  window.loadPlanes(form, selProf, selPlan);
  setupExclusivos();
  updateStatus();

})();;

})();