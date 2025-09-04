(function(){
    document.querySelectorAll('.panel input, .panel select, .panel textarea').forEach(el=>{
      if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'file') return;
      const hasClass = ['input','select','textarea'].some(c=>el.classList.contains(c));
      if (hasClass) return;
      el.classList.add(el.tagName === 'SELECT' ? 'select' : (el.tagName === 'TEXTAREA' ? 'textarea' : 'input'));
    });
  })();