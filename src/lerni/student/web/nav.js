// The menu: ☰ opens the drawer of sections; a section, the backdrop, or Escape closes it.
(() => {
  const open = on => {
    // the state sits on the drawer and backdrop: the page's styles only reach inside the app
    document.querySelectorAll('#lerni-drawer, .lerni-backdrop').forEach(el => {
      el.classList.toggle('lerni-open', on);
    });
    document.querySelector('.lerni-menu-btn')?.setAttribute('aria-expanded', on);
    if (!on) return;
    // mark the open section, so the student sees where they are
    const here = document.querySelector('.lerni-title')?.textContent.trim();
    document.querySelectorAll('.lerni-nav-item').forEach(b => {
      b.classList.toggle('lerni-here', b.textContent.trim() === here);
    });
  };
  document.addEventListener('click', e => {
    if (e.target.closest('.lerni-menu-btn')) {
      open(!document.querySelector('#lerni-drawer')?.classList.contains('lerni-open'));
    } else if (e.target.closest('.lerni-backdrop')) {
      open(false);
    }
  });
  // Maps: a tap on the map strip opens or closes the whole picture
  document.addEventListener('click', e => {
    e.target.closest('.lerni-map-strip')?.classList.toggle('lerni-open');
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') open(false); });
  window.lerniMenu = open;  // a section's button closes the menu
})();
