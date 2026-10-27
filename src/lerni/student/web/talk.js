// Hold to talk: record while the button is held, show a live preview, send a 16 kHz WAV,
// and play the spoken answer a sentence at a time.
(() => {
  const S = {ctx: null, stream: null, src: null, node: null, chunks: [], t0: 0, on: false,
             peek: null, queue: [], playing: null, player: new Audio()};
  const session = navigator.audioSession;  // Safari 16.4+: says whether we record or play

  // inside the tap: wake the recorder, and play a moment of silence on the player,
  // so iPad and iPhone Safari let it play the answer later without another tap
  function unlock() {
    if (!S.ctx) S.ctx = new (window.AudioContext || window.webkitAudioContext)();
    S.ctx.resume();
    if (S.playing) return;  // already playing, so already allowed; swapping it would end it
    S.player.src = URL.createObjectURL(new Blob([wav(new Float32Array(1600))], {type: 'audio/wav'}));
    S.player.play().catch(() => {});
  }

  const MAX_HOLD = 29.5;  // seconds: the clip sends itself before the server's 30-second limit
  const NO_MIC = 'No microphone: type here';

  // the microphone failed: switch to Type, and say so in the question box; remember it on
  // this device only when the microphone was refused, not when it was just busy
  function noMic(suffix, err) {
    mode('type', err?.name === 'NotAllowedError');
    const box = document.querySelector(`#lerni-question-${suffix} textarea`);
    if (box) { box.placeholder = NO_MIC; box.focus(); }
  }

  async function start(e, btn, suffix) {
    e.preventDefault();
    stop();  // a tap silences Lerni; a hold also asks something new
    document.getElementById(`lerni-hush-${suffix}`)?.click();  // and stops the answer coming
    unlock();
    // the button turns red only once the microphone hears, so no first words are lost
    const press = S.press = (S.press || 0) + 1;  // a newer press replaces this one
    S.on = true; S.live = false; S.chunks = []; S.t0 = Infinity;
    let stream = S.stream;
    try {
      if (session) session.type = 'play-and-record';
      if (!stream) stream = await navigator.mediaDevices.getUserMedia({audio: true});
    } catch (err) {  // no microphone: typing still works
      if (press === S.press) { reset(btn); noMic(suffix, err); }
      return;
    }
    if (!S.on || press !== S.press) {  // let go, or pressed again, while Safari was asking
      if (stream !== S.stream) stream.getTracks().forEach(t => t.stop());  // release it
      if (press === S.press) reset(btn);
      return;
    }
    S.stream = stream;
    clearInterval(S.peek);  // never two previews at once
    S.src = S.ctx.createMediaStreamSource(S.stream);
    S.node = S.ctx.createScriptProcessor(4096, 1, 1);
    S.node.onaudioprocess = ev => {
      if (!S.on) return;
      const buf = ev.inputBuffer.getChannelData(0);
      if (!S.live) {
        if (!buf.some(x => x !== 0)) return;  // the microphone is still waking up
        S.live = true; S.t0 = performance.now();
        btn.textContent = '🔴\nListening…';  // now it's safe to talk
        btn.classList.add('lerni-listening');
      }
      S.chunks.push(new Float32Array(buf));
      if ((performance.now() - S.t0) / 1000 >= MAX_HOLD) send(null, btn, suffix);  // still holding
    };
    S.src.connect(S.node); S.node.connect(S.ctx.destination);
    // every 1.5 s, send the clip so far for a live preview
    S.peek = setInterval(() => fill(`lerni-partial-${suffix}`, `lerni-peek-${suffix}`), 1500);
  }

  function reset(btn) {
    S.on = false; clearInterval(S.peek);
    if (S.src) { S.src.disconnect(); S.node.disconnect(); S.src = S.node = null; }
    // release the microphone, so Safari goes back to normal (loud) playback
    if (S.stream) { S.stream.getTracks().forEach(t => t.stop()); S.stream = null; }
    if (session) session.type = 'playback';  // plays even when the device is on silent
    btn.textContent = '🎤\nHold to talk';
    btn.classList.remove('lerni-listening');
  }

  // average down to 16 kHz mono, at most 30 seconds
  function downsample(buf, rate) {
    const r = rate / 16000;
    const out = new Float32Array(Math.min(Math.floor(buf.length / r), 16000 * 30));
    for (let i = 0; i < out.length; i++) {
      const a = Math.floor(i * r), b = Math.min(buf.length, Math.floor((i + 1) * r));
      let sum = 0; for (let j = a; j < b; j++) sum += buf[j];
      out[i] = sum / Math.max(1, b - a);
    }
    return out;
  }

  function wav(x) {
    const v = new DataView(new ArrayBuffer(44 + x.length * 2));
    const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0, 'RIFF'); v.setUint32(4, 36 + x.length * 2, true); w(8, 'WAVE'); w(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true);
    v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, x.length * 2, true);
    for (let i = 0; i < x.length; i++) {
      v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x[i])) * 0x7fff, true);
    }
    return new Uint8Array(v.buffer);
  }

  function b64(bytes) {
    let s = '';
    for (let i = 0; i < bytes.length; i += 0x8000) {
      s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    }
    return btoa(s);
  }

  // put the clip so far in a hidden field and press its hidden button
  function fill(boxId, buttonId) {
    let n = 0; S.chunks.forEach(c => n += c.length);
    if (!S.ctx || n < S.ctx.sampleRate * 0.5) return;  // under half a second: nothing yet
    const all = new Float32Array(n);
    let o = 0; S.chunks.forEach(c => { all.set(c, o); o += c.length; });
    const box = document.querySelector(`#${boxId} textarea`);
    box.value = b64(wav(downsample(all, S.ctx.sampleRate)));
    box.dispatchEvent(new Event('input', {bubbles: true}));
    setTimeout(() => document.getElementById(buttonId).click(), 50);
  }

  function send(e, btn, suffix) {
    if (!S.on) return;  // sent already (at 30 seconds), or never started
    e?.preventDefault();
    const held = (performance.now() - S.t0) / 1000;
    S.on = false;  // stop collecting before the last copy
    if (held >= 0.5) fill(`lerni-clip-${suffix}`, `lerni-heard-${suffix}`);  // shorter: Whisper invents words
    reset(btn);
  }

  // play the next sentence on the player the tap unlocked
  function next() {
    if (S.playing || !S.queue.length) return;
    const bin = Uint8Array.from(atob(S.queue.shift()), c => c.charCodeAt(0));
    const url = URL.createObjectURL(new Blob([bin], {type: 'audio/mp4'}));
    S.playing = url;  // one sentence at a time
    const done = () => {
      URL.revokeObjectURL(url);
      if (S.playing === url) { S.playing = null; next(); idle(); }
    };
    S.player.onended = done;
    S.player.src = url;
    S.player.play().catch(done);  // skip a sentence that won't play
  }

  // the server sends [count, audio]; play each sentence in order
  function play(v) {
    if (!v) return;
    S.queue.push(JSON.parse(v)[1]); next();
  }

  function stop() {
    S.queue = []; S.playing = null;
    S.player.pause();
    idle();
  }

  // nothing left to say (ended, failed, or stopped): race.js lets Next go
  function idle() {
    if (!S.playing && !S.queue.length) document.dispatchEvent(new Event('lerni-talk-idle'));
  }

  // a race reading: replaces the one playing; an empty clip just says there's nothing to say
  function say(v) {
    if (!v) return;
    S.queue = []; S.playing = null;
    S.player.pause();
    if (JSON.parse(v)[1]) play(v); else idle();
  }

  window.lerniTalk = {play, say, stop, unlock};  // race.js unlocks it on a tap, to read aloud

  // Talk or Type: switch every dock, and remember it on this device (just the choice)
  function mode(m, keep = true) {
    document.querySelectorAll('.lerni-voice').forEach(d => { d.dataset.mode = m; });
    document.querySelectorAll('.lerni-mode button').forEach(b => {
      b.setAttribute('aria-pressed', b.dataset.mode === m);
    });
    if (!keep) return;
    try { localStorage.setItem('lerni-mode', m); } catch (err) {}  // private mode: not kept
  }
  function saved() {
    try { return localStorage.getItem('lerni-mode') || 'talk'; } catch (err) { return 'talk'; }
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('.lerni-mode button');
    if (!b) return;
    mode(b.dataset.mode);
    if (b.dataset.mode === 'type') b.closest('.lerni-dock')?.querySelector('textarea')?.focus();
  });

  // size the visible chat so the page fits the screen exactly, keyboard up or down
  function fit() {
    const chat = [...document.querySelectorAll('#lerni-ask-chat, #lerni-home-chat')]
      .find(c => c.offsetParent);
    if (!chat) return;
    const screen = window.visualViewport?.height || window.innerHeight;
    const box = chat.getBoundingClientRect();
    // the lowest visible control under the chat (the dock, New conversation)
    const panel = chat.closest('[role="tabpanel"]') || document.body;
    const low = Math.max(box.bottom, ...[...panel.querySelectorAll('button, textarea')]
      .filter(el => el.offsetParent).map(el => el.getBoundingClientRect().bottom));
    const above = box.top + window.scrollY, below = low - box.bottom;
    const h = Math.max(160, Math.floor(screen - above - below - 8));
    if (Math.abs(chat.offsetHeight - h) > 2) chat.style.setProperty('height', `${h}px`, 'important');
  }
  window.visualViewport?.addEventListener('resize', fit);
  setInterval(fit, 500);  // also after Talk/Type switches and new messages

  // a typed question: silence the last answer, and let this one play aloud (needs the tap)
  function typed() { stop(); unlock(); }

  // wire each talk button once Gradio draws it (tabs appear after sign-in)
  setInterval(() => {
    for (const suffix of ['ask', 'home', 'bonus']) {
      const btn = document.getElementById(`lerni-talk-${suffix}`);
      if (!btn || btn.dataset.wired) continue;
      btn.dataset.wired = '1';
      mode(saved());
      document.getElementById(`lerni-send-${suffix}`)?.addEventListener('pointerdown', typed);
      document.querySelector(`#lerni-question-${suffix} textarea`)?.addEventListener(
        'keydown', e => { if (e.key === 'Enter' && !e.shiftKey) typed(); });
      btn.addEventListener('pointerdown', e => start(e, btn, suffix));
      for (const t of ['pointerup', 'pointercancel', 'pointerleave']) {
        btn.addEventListener(t, e => send(e, btn, suffix));
      }
      btn.addEventListener('contextmenu', e => e.preventDefault());
    }
  }, 500);
})();
