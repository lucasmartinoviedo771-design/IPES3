(function () {
  const items = document.querySelectorAll('.nav-item.has-children');

  // Cierra todos y abre el clickeado (acordeón)
  function openOnly(item) {
    items.forEach(i => i.classList.toggle('open', i === item));
  }

  // Toggle al hacer click en el padre
  items.forEach(item => {
    const parent = item.querySelector('.nav-parent');
    parent.addEventListener('click', (e) => {
      e.preventDefault();
      const isOpen = item.classList.contains('open');
      items.forEach(i => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  // Si hay un hijo activo en esta página, que arranque abierto
  items.forEach(item => {
    if (item.querySelector('.subnav a.active')) {
      item.classList.add('open');
    }
  });
})();