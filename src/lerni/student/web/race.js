// The race: each car glides from its last place to its new one when the track is redrawn.
// Gradio patches the same picture in place, so watch each car's data-x, and animate with
// the Web Animations API, which leaves the style attribute Gradio rewrites alone.
(() => {
  const last = {};  // "race id:lane" -> x
  const still = window.matchMedia('(prefers-reduced-motion: reduce)');
  function glide(car) {
    const svg = car.closest('svg');
    if (!svg) return;
    const key = `${svg.dataset.race}:${car.dataset.lane}`, x = Number(car.dataset.x);
    const from = last[key];
    last[key] = x;
    if (from === undefined || from === x || still.matches || !car.animate) return;
    car.animate([{transform: `translateX(${from - x}px)`}, {transform: 'none'}],
                {duration: 600, easing: 'ease-out'});
  }
  new MutationObserver(records => {
    const note = document.getElementById('lerni-note');  // results and purchases are announced
    if (note && !note.hasAttribute('role')) {
      note.setAttribute('role', 'status');
      note.setAttribute('aria-live', 'polite');
    }
    const cars = new Set();
    for (const r of records) {
      if (r.type === 'attributes' && r.target.matches?.('#lerni-track .lerni-racer')) cars.add(r.target);
      if (r.type === 'childList') {
        document.querySelectorAll('#lerni-track .lerni-racer').forEach(c => cars.add(c));
      }
    }
    cars.forEach(glide);
  }).observe(document.body, {childList: true, subtree: true, attributes: true,
                              attributeFilter: ['data-x']});
})();
