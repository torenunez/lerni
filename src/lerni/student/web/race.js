// The race: each car glides from its last place to its new one when the track is redrawn.
(() => {
  const last = {};  // "race id:lane" -> x
  const still = window.matchMedia('(prefers-reduced-motion: reduce)');
  function glide(svg) {
    if (svg.dataset.seen) return;
    svg.dataset.seen = '1';
    svg.querySelectorAll('.lerni-racer').forEach(car => {
      const key = `${svg.dataset.race}:${car.dataset.lane}`, x = Number(car.dataset.x);
      const from = last[key];
      last[key] = x;
      if (from === undefined || from === x || still.matches) return;  // new race, or no motion
      car.style.transition = 'none';
      car.style.transform = `translateX(${from - x}px)`;  // start where it was
      car.getBoundingClientRect();
      car.style.transition = 'transform 0.6s ease-out';
      car.style.transform = '';
    });
  }
  new MutationObserver(() => document.querySelectorAll('#lerni-track svg').forEach(glide))
    .observe(document.body, {childList: true, subtree: true});
})();
