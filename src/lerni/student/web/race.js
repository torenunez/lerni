// The race: each car glides from its last place to its new one when the track is redrawn.
// Gradio patches the same picture in place, so watch each car's data-x, and animate with
// the Web Animations API, which leaves the style attribute Gradio rewrites alone.
// Sounds: the server names each answer's sound on the track (a roar, a sputter, the bonus's
// by its grade, the finish), unlocked by the Race! tap (iPad Safari plays nothing before a
// tap). One Sound switch in the top bar covers every sound in the app, Chat's voice too.
// With sound on, each question and a wrong answer's right answer are said by themselves (Next
// waits for the right answer), and a tap on the card reads it again.
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

  // each sound: its clip, seconds, and volume; zoom plays the roar until its clip is there
  const SOUNDS = {roar: ['roar', 1.5, 0.6], rev: ['roar', 0.8, 0.35], sputter: ['sputter', 1.5, 0.6],
                  finish: ['finish', 2.5, 0.6], zoom: ['zoom', 2.5, 0.6]};
  const FADE = 0.3;
  let lastPlay = 0;  // when a sound last started, so a reading waits for it
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
    for (const name of ['roar', 'sputter', 'finish', 'zoom']) {  // a missing clip stays silent
      fetch(`/sounds/${name}`, {credentials: 'same-origin'})
        .then(r => (r.ok ? r.arrayBuffer() : Promise.reject()))
        .then(data => new Promise((ok, no) => audio.decodeAudioData(data, ok, no)?.catch?.(no)))
        .then(buffer => { clips[name] = buffer; })
        .catch(() => {});
    }
  }
  function play(name) {
    if (!SOUNDS[name]) return;
    let [clip, seconds, volume] = SOUNDS[name];
    if (!clips[clip] && clip === 'zoom') clip = 'roar';
    if (!audio || !clips[clip] || !soundOn()) return;
    const source = audio.createBufferSource(), gain = audio.createGain();
    const now = audio.currentTime, end = now + Math.min(seconds, clips[clip].duration);
    source.buffer = clips[clip];
    lastPlay = Date.now();
    gain.gain.setValueAtTime(volume, now);  // full until the fade, then down to silence
    gain.gain.setValueAtTime(volume, Math.max(now, end - FADE));
    gain.gain.linearRampToValueAtTime(0, end);
    source.connect(gain).connect(audio.destination);
    source.start(now);
    source.stop(end);
  }
  function listen(svg) {
    // a new answer on the same race plays once; a refresh or a repeat tap plays nothing
    const id = svg.dataset.race, step = Number(svg.dataset.step);
    const before = heard[id];
    heard[id] = step;
    if (!id || before === undefined || step !== before + 1) return;
    play(svg.dataset.sound);
  }
  // the right answer after a wrong one, said once per race and step; Next waits until it's done
  const HOLD_MS = 20000;  // never stuck: Next comes back after this, said or not
  let whyKey = '', holdTimer = 0;
  // a reading asked for before Sound off or a tap that moved on is dropped when it arrives
  let asked = 0, current = 0;
  window.lerniRace = {wants: () => soundOn() && asked === current};
  window.lerniSound = soundOn;  // talk.js: Chat's voice follows the same switch
  function hold(on) {
    clearTimeout(holdTimer);
    holdTimer = on ? setTimeout(() => hold(false), HOLD_MS) : 0;
    if (on) document.body.dataset.lerniHold = '1'; else delete document.body.dataset.lerniHold;
  }
  document.addEventListener('lerni-talk-idle', () => { if (holdTimer) hold(false); });
  function autoWhy() {
    const reader = document.getElementById('lerni-read-go');
    const svg = document.querySelector('#lerni-track svg[data-race]');
    if (!reader || !svg || !svg.dataset.why) return;
    const key = `${svg.dataset.race}:${svg.dataset.step}`;
    if (key === whyKey) return;  // a redraw doesn't say it again
    whyKey = key;  // kept with sound off too, so turning it on later never says it
    if (!soundOn()) return;
    hold(true);
    asked = current;
    reader.click();
  }
  // a new question is read by itself once, after the sound for the last answer
  let askKey = '', askTimer = 0;
  function autoAsk() {
    const reader = document.getElementById('lerni-read-go');
    const svg = document.querySelector('#lerni-track svg[data-race]');
    if (!reader || !svg || !svg.dataset.ask) return;
    const key = `${svg.dataset.race}:${svg.dataset.step}`;
    if (key === askKey) return;  // a redraw doesn't read it again
    askKey = key;  // kept with sound off too, so turning it on later never reads it
    if (!soundOn()) return;
    const mine = current;
    askTimer = setTimeout(() => {
      if (mine !== current) return;  // answered or moved on meanwhile
      asked = current;
      reader.click();
    }, Math.max(0, lastPlay + 1200 - Date.now()));
  }
  function label() {
    const button = document.getElementById('lerni-mute');
    if (!button) return;
    const on = soundOn(), text = on ? '🔊' : '🔇';
    if (button.textContent === text) return;  // writing it anyway would wake the observer again
    button.textContent = text;
    button.setAttribute('aria-pressed', String(on));
    button.setAttribute('aria-label', on ? 'Sound on' : 'Sound off');
  }
  function moveOn() {  // an answer or Race!: moving on stops a reading
    unlock();
    current++;
    window.lerniTalk?.stop();
    hold(false);
    // inside the tap, so the iPad lets the right answer play later; with sound off the
    // player stays untouched (an iPad's music keeps playing)
    if (soundOn()) window.lerniTalk?.unlock();
  }
  // Return in a typed answer sends it, like a tap on Check
  document.addEventListener('keydown', event => {
    if (event.key === 'Enter' && event.target.closest?.('#lerni-typed')) moveOn();
  });
  // sentences in order (v4.13): each tap numbers a card; a tap on a numbered one undoes it
  // and every card after it; the taps go in the hidden answer field as "2,0,1" for Check
  function orderTap(card) {
    const box = card.closest('.lerni-order');
    let picks = box.dataset.picks ? box.dataset.picks.split(',') : [];
    const i = card.dataset.i, at = picks.indexOf(i);
    picks = at >= 0 ? picks.slice(0, at) : picks.concat(i);  // undo from here, or add it
    box.dataset.picks = picks.join(',');
    box.querySelectorAll('.lerni-order-item').forEach(c => {
      const n = picks.indexOf(c.dataset.i);
      c.classList.toggle('lerni-on', n >= 0);
      c.querySelector('b').textContent = n >= 0 ? String(n + 1) : '';
    });
    const hint = box.querySelector('.lerni-order-hint');
    if (hint) hint.textContent = 'Tap again to undo.';
    const field = document.querySelector('#lerni-typed input, #lerni-typed textarea');
    if (field) {  // Gradio reads the field on its input event
      field.value = box.dataset.picks;
      field.dispatchEvent(new Event('input', {bubbles: true}));
    }
  }
  document.addEventListener('click', event => {
    const at = selector => event.target.closest?.(selector);
    const orderCard = at('.lerni-order-item');
    if (orderCard) { orderTap(orderCard); return; }
    const box = document.querySelector('#lerni-dock-typed .lerni-order');
    if (at('.lerni-check') && box) {  // Check waits until every sentence is numbered
      const picked = box.dataset.picks ? box.dataset.picks.split(',').length : 0;
      if (picked < Number(box.dataset.n)) {
        event.preventDefault();
        event.stopPropagation();
        const hint = box.querySelector('.lerni-order-hint');
        if (hint) hint.textContent = `Tap all ${box.dataset.n} first.`;
        return;
      }
    }
    if (at('#lerni-next') && holdTimer) {  // still saying the right answer
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    // Race! and Next unlock sound; an answer tap wakes it again after the iPad paused it
    if (at('.lerni-go, .lerni-choice, .lerni-check')) moveOn();
    // a tap on the card (or on the note when it holds the right answer) reads it aloud
    const svg = document.querySelector('#lerni-track svg[data-race]');
    const card = at('.lerni-question') || (at('#lerni-note') && svg?.dataset.why);
    const reader = document.getElementById('lerni-read-go');
    if (card && reader && soundOn() && !at('a, button, details')) {
      clearTimeout(askTimer);  // this tap reads it: the reading by itself isn't needed
      window.lerniTalk?.unlock();
      asked = current;
      reader.click();
    }
    if (at('#lerni-mute')) {
      const on = !soundOn();
      try { localStorage.setItem('lerni-sound', on ? 'on' : 'off'); } catch {}
      if (!on) { current++; window.lerniTalk?.stop(); hold(false); }  // off silences a reading too
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
    autoWhy();
    autoAsk();
  }).observe(document.body, {childList: true, subtree: true, attributes: true,
                              attributeFilter: ['data-x', 'data-step', 'data-why', 'data-ask']});

  // typed questions (v4.10, in races v4.11) and a paragraph (v4.14): the iPad's keyboard must
  // not fix the answer, so the field gets no autocorrect, capitals, suggestions, or spell
  // check; a picture's number gets the number keyboard
  new MutationObserver(() => {
    const picture = !!document.querySelector('#lerni-dock-typed .lerni-pic');
    const money = !!document.querySelector('#lerni-dock-typed .lerni-money, #lerni-dock-typed .lerni-ruler');
    document.querySelectorAll('#lerni-typed input, #lerni-typed textarea, #lerni-paragraph textarea').forEach(e => {
      if (!e.dataset.noHelp) {  // once per field
        e.dataset.noHelp = '1';
        e.setAttribute('autocorrect', 'off');
        e.setAttribute('autocapitalize', 'none');
        e.setAttribute('autocomplete', 'off');
        e.spellcheck = false;
      }
      // follows the question on screen: a decimal point for money and rulers
      const mode = money ? 'decimal' : picture ? 'numeric' : 'text';
      if (e.inputMode !== mode) e.inputMode = mode;
    });
  }).observe(document.body, {childList: true, subtree: true});
})();
