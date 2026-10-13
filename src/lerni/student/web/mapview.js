// MentalMap pictures: tap an item to light up its links and open it in the list;
// pinch (or scroll) to zoom, drag to move once zoomed, Reset view to go back.
(() => {
  const views = {};  // per map (data-key): the zoomed viewBox and the tapped item
  const box = svg => svg.getAttribute('viewBox').split(' ').map(Number);

  // the list's hidden field for this picture: lerni-map-mine → lerni-pick-mine
  function pick(wrap, id) {
    const field = wrap.closest('[id^="lerni-map-"]')?.id.replace('lerni-map-', 'lerni-pick-');
    const input = field && document.querySelector(`#${field} textarea, #${field} input`);
    if (!input) return;
    input.value = id;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    setTimeout(() => document.getElementById(`${field}-go`)?.click(), 50);  // as talk.js does
  }

  // dim everything but the tapped item and what it links to
  function focus(wrap, id) {
    const svg = wrap.querySelector('svg');
    const near = new Set(id ? [id] : []);
    // a group lights up its whole family: follow kind-of lines down
    const down = id ? [id] : [];
    while (down.length) {
      const top = down.pop();
      svg.querySelectorAll(`line[data-k="kind_of"][data-b="${top}"]`).forEach(l => {
        if (!near.has(l.dataset.a)) { near.add(l.dataset.a); down.push(l.dataset.a); }
      });
    }
    svg.querySelectorAll('line').forEach(l => {
      const on = id && (l.dataset.a === id || l.dataset.b === id
        || (l.dataset.k === 'kind_of' && near.has(l.dataset.a) && near.has(l.dataset.b)));
      l.classList.toggle('lerni-near', !!on);
      if (on) { near.add(l.dataset.a); near.add(l.dataset.b); }
    });
    svg.querySelectorAll('.lerni-node').forEach(n => {
      n.classList.toggle('lerni-near', near.has(n.dataset.id));
      n.classList.toggle('lerni-picked', n.dataset.id === id);
    });
    svg.classList.toggle('lerni-focus', !!id);
  }

  function zoom(wrap, next) {
    const svg = wrap.querySelector('svg'), view = views[wrap.dataset.key] ||= {};
    view.box = next;
    if (next) svg.setAttribute('viewBox', next.join(' '));
    // zoomed in, one finger moves the map; otherwise it scrolls the page
    svg.style.touchAction = next ? 'none' : 'pan-x pan-y';
  }

  // a redraw (an edit, or MentalMaps every 30 s) keeps the zoom and the tapped item
  function restore(wrap) {
    const svg = wrap.querySelector('svg'), view = views[wrap.dataset.key];
    if (!svg || svg.dataset.home) return;
    svg.dataset.home = svg.getAttribute('viewBox');
    if (!view) return;
    if (view.box) zoom(wrap, view.box);
    if (view.picked) focus(wrap, view.picked);
  }
  new MutationObserver(() => document.querySelectorAll('.lerni-map-wrap').forEach(restore))
    .observe(document.body, {childList: true, subtree: true});

  document.addEventListener('click', e => {
    const wrap = e.target.closest('.lerni-map-wrap');
    if (!wrap || wrap.dataset.dragged) { if (wrap) delete wrap.dataset.dragged; return; }
    const view = views[wrap.dataset.key] ||= {};
    if (e.target.closest('.lerni-map-reset')) {
      const svg = wrap.querySelector('svg');
      zoom(wrap, null); svg.setAttribute('viewBox', svg.dataset.home);
      view.picked = null; focus(wrap, null); pick(wrap, '');
      return;
    }
    const node = e.target.closest('.lerni-node');
    const id = node && node.dataset.id !== view.picked ? node.dataset.id : null;
    view.picked = id; focus(wrap, id); pick(wrap, id || '');
  });

  // pointers: two pinch, one drags (only once zoomed in)
  const down = new Map();
  let start = null;
  document.addEventListener('pointerdown', e => {
    const svg = e.target.closest('.lerni-map-wrap svg');
    if (!svg) return;
    down.set(e.pointerId, [e.clientX, e.clientY]);
    start = {svg, box: box(svg), pts: [...down.values()].map(p => [...p])};
  });
  document.addEventListener('pointermove', e => {
    if (!start || !down.has(e.pointerId)) return;
    down.set(e.pointerId, [e.clientX, e.clientY]);
    const {svg, box: [x, y, w, h], pts} = start, wrap = svg.closest('.lerni-map-wrap');
    const scale = w / svg.getBoundingClientRect().width;  // map units per screen pixel
    const now = [...down.values()];
    if (now.length >= 2 && pts.length >= 2) {
      const gap = p => Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]) || 1;
      const k = Math.min(Math.max(gap(pts) / gap(now), 0.15), 1.5);  // fingers apart: zoom in
      const r = svg.getBoundingClientRect();
      const cx = x + ((pts[0][0] + pts[1][0]) / 2 - r.left) * scale;
      const cy = y + ((pts[0][1] + pts[1][1]) / 2 - r.top) * scale;
      zoom(wrap, [cx - (cx - x) * k, cy - (cy - y) * k, w * k, h * k]);
      wrap.dataset.dragged = '1';
    } else if (views[wrap.dataset.key]?.box) {
      const dx = (now[0][0] - pts[0][0]) * scale, dy = (now[0][1] - pts[0][1]) * scale;
      if (Math.hypot(dx, dy) > 3 * scale) wrap.dataset.dragged = '1';
      zoom(wrap, [x - dx, y - dy, w, h]);
    }
  });
  const up = e => {
    down.delete(e.pointerId);
    if (start && down.size) start = {...start, box: box(start.svg), pts: [...down.values()]};
    else start = null;
  };
  document.addEventListener('pointerup', up);
  document.addEventListener('pointercancel', up);
  document.addEventListener('wheel', e => {  // a trackpad pinch (or Ctrl and scroll) zooms
    const svg = e.target.closest('.lerni-map-wrap svg');
    if (!svg || !e.ctrlKey) return;
    e.preventDefault();
    const [x, y, w, h] = box(svg), r = svg.getBoundingClientRect(), k = e.deltaY > 0 ? 1.15 : 0.87;
    const cx = x + (e.clientX - r.left) * w / r.width, cy = y + (e.clientY - r.top) * h / r.height;
    zoom(svg.closest('.lerni-map-wrap'), [cx - (cx - x) * k, cy - (cy - y) * k, w * k, h * k]);
  }, {passive: false});
})();
