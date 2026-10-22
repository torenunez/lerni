// The race: each car glides from its last place to its new one when the track is redrawn.
// Gradio patches the same picture in place, so watch each car's data-x, and animate with
// the Web Animations API, which leaves the style attribute Gradio rewrites alone.
// Sounds: a roar for a right answer, a sputter for a wrong one, and a finish sound,
// unlocked by the Race! tap (iPad Safari plays nothing before a tap), with a 🔇 button.
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

  const SECONDS = {roar: 1.5, sputter: 1.5, finish: 2.5}, FADE = 0.3, VOLUME = 0.6;
  const clips = {};  // name -> decoded audio
  let audio = null;
  const heard = {};  // race id -> the step whose sound was played
  function soundOn() {
    try { return localStorage.getItem('lerni-sound') !== 'off'; } catch { return true; }
  }
  function unlock() {
    if (audio) { audio.resume?.(); return; }
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    audio = new Ctx();
    audio.resume?.();
    for (const name of Object.keys(SECONDS)) {  // a missing clip just stays silent
      fetch(`/sounds/${name}`, {credentials: 'same-origin'})
        .then(r => (r.ok ? r.arrayBuffer() : Promise.reject()))
        .then(data => new Promise((ok, no) => audio.decodeAudioData(data, ok, no)?.catch?.(no)))
        .then(buffer => { clips[name] = buffer; })
        .catch(() => {});
    }
  }
  function play(name) {
    if (!audio || !clips[name] || !soundOn()) return;
    const source = audio.createBufferSource(), gain = audio.createGain();
    const now = audio.currentTime, end = now + Math.min(SECONDS[name], clips[name].duration);
    source.buffer = clips[name];
    gain.gain.setValueAtTime(VOLUME, now);  // full until the fade, then down to silence
    gain.gain.setValueAtTime(VOLUME, Math.max(now, end - FADE));
    gain.gain.linearRampToValueAtTime(0, end);
    source.connect(gain).connect(audio.destination);
    source.start(now);
    source.stop(end);
  }
  function listen(svg) {
    // a new answer on the same race plays once; a refresh or a repeat tap plays nothing
    const id = svg.dataset.race, step = Number(svg.dataset.step), right = Number(svg.dataset.right);
    const before = heard[id];
    heard[id] = {step, right};
    if (!id || !before || step !== before.step + 1) return;
    play(step >= Number(svg.dataset.total) ? 'finish' : right > before.right ? 'roar' : 'sputter');
  }
  function label() {
    const button = document.getElementById('lerni-mute');
    if (!button) return;
    const on = soundOn(), text = on ? '🔊' : '🔇';
    if (button.textContent === text) return;  // writing it anyway would wake the observer again
    button.textContent = text;
    button.setAttribute('aria-label', on ? 'Sound on' : 'Sound off');
  }
  document.addEventListener('click', event => {
    // Race! unlocks sound; an answer tap wakes it again after the iPad paused it
    if (event.target.closest?.('.lerni-go, .lerni-choice')) unlock();
    if (event.target.closest?.('#lerni-mute')) {
      try { localStorage.setItem('lerni-sound', soundOn() ? 'off' : 'on'); } catch {}
      unlock();
      label();
    }
  }, true);

  new MutationObserver(records => {
    // results, purchases, and the right answer after a wrong one are announced
    for (const live of [document.getElementById('lerni-note'),
                        document.querySelector('.lerni-question')]) {
      if (live && !live.hasAttribute('role')) {
        live.setAttribute('role', 'status');
        live.setAttribute('aria-live', 'polite');
      }
    }
    const cars = new Set();
    for (const r of records) {
      if (r.type === 'attributes' && r.target.matches?.('#lerni-track .lerni-racer')) cars.add(r.target);
      if (r.type === 'childList') {
        document.querySelectorAll('#lerni-track .lerni-racer').forEach(c => cars.add(c));
      }
    }
    cars.forEach(glide);
    const svg = document.querySelector('#lerni-track svg[data-race]');
    if (svg) listen(svg);
    label();
  }).observe(document.body, {childList: true, subtree: true, attributes: true,
                              attributeFilter: ['data-x', 'data-step']});
})();
