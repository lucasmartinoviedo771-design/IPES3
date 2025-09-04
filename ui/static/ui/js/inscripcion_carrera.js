// C:\proyectos\academia\ui\static\ui\js\inscripcion_carrera.js (versión robusta)
(function runWhenReady(fn){
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
  else fn();
})(function(){

  

  const form = document.querySelector('#insc-carrera-form');
  if (!form) { console.warn('[insc-carrera] no existe #insc-carrera-form'); return; }

  // Dependencias/graceful fallback
  const uiShow = (window.UI && typeof window.UI.show === 'function')
    ? window.UI.show
    : (el, v) => { if (!el) return; el.style.display = v ? '' : 'none'; };

  const callLoadPlanes = (f, p, s) => {
    if (typeof window.loadPlanes === 'function') return window.loadPlanes(f, p, s);
    console.warn('[insc-carrera] window.loadPlanes no está disponible (¿cargaste ui/js/utils/loadPlanes.js antes?)');
  };

  // --- DOM
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

  // ⚠️ si el data-atribute no está, no explota
  const CERT_DOCENTE_LABEL = (form.dataset.certDocenteLabel || '').trim();

  // Helpers
  function getCbx(id) { return form.querySelector('#'+id); }
  function ch(el) { return !!(el && el.checked); }
  function disable(el, v) { if(!el) return; el.disabled = !!v; if(v) el.checked = false; }
  function textOfSelect(sel){ if(!sel) return ''; const opt = sel.options[sel.selectedIndex]; return opt ? (opt.text || '').trim() : ''; }

  function onAdeudaToggle() {
    const v = ch(adeudaBox);
    uiShow(adeudaExtra, v);
  }

  // Exclusividad: Secundario / Trámite / Adeuda
  function setupExclusivos() {
    const tSec  = getCbx('id_req_titulo_sec');
    const tTram = getCbx('id_req_titulo_tramite');
    const adeu  = getCbx('id_req_adeuda');
    const group = [tSec, tTram, adeu].filter(Boolean);

    function wire(cb) {
      if (!cb) return;
      cb.addEventListener('change', () => {
        if (!cb.checked) { if (cb === adeu) onAdeudaToggle(); updateStatus(); return; }
        group.forEach(other => {
          if (other && other !== cb && other.checked) {
            other.checked = false;
            if (other === adeu) onAdeudaToggle();
          }
        });
        if (cb === adeu) onAdeudaToggle();
        updateStatus();
      });
    }
    group.forEach(wire);
  }

  function applyProfRules() {
    const isCert = CERT_DOCENTE_LABEL && textOfSelect(selProf) === CERT_DOCENTE_LABEL;

    uiShow(bloqueSup, isCert);

    const cbTituloSec   = getCbx('id_req_titulo_sec');
    const cbTituloTram  = getCbx('id_req_titulo_tramite');
    const cbAdeuda      = getCbx('id_req_adeuda');

    uiShow(rowTSec,   !isCert);
    uiShow(rowTram,   !isCert);
    uiShow(rowAdeuda, !isCert);
    uiShow(adeudaExtra, !isCert && ch(cbAdeuda));

    disable(cbTituloSec,  isCert);
    disable(cbTituloTram, isCert);
    disable(cbAdeuda,     isCert);

    updateStatus();
  }

  function updateStatus() {
    const isCert = CERT_DOCENTE_LABEL && textOfSelect(selProf) === CERT_DOCENTE_LABEL;

    const okDNI      = ch(getCbx('id_req_dni'));
    const okMedico   = ch(getCbx('id_req_cert_med'));
    const okFotos    = ch(getCbx('id_req_fotos'));
    const okFolios   = ch(getCbx('id_req_folios'));
    const okTituloSec = ch(getCbx('id_req_titulo_sec'));
    const okTituloSup   = ch(getCbx('id_req_titulo_sup'));
    const okIncumb      = ch(getCbx('id_req_incumbencias'));

    let regular = false;
    if (isCert) {
      regular = okTituloSup && okIncumb;
    } else {
      regular = okDNI && okMedico && okFotos && okFolios && okTituloSec;
    }

    uiShow(pillRegular,  regular);
    uiShow(pillCond,    !regular);
    uiShow(ddjjWrap,    !regular);
  }

  if (adeudaBox) adeudaBox.addEventListener('change', onAdeudaToggle);
  if (selProf) {
    selProf.addEventListener('change', () => { callLoadPlanes(form, selProf, selPlan); applyProfRules(); });
  }
  form.addEventListener('change', updateStatus);

  // Init
  onAdeudaToggle();
  applyProfRules();
  callLoadPlanes(form, selProf, selPlan);
  setupExclusivos();
  updateStatus();
});