// Hold to talk: record while the button is held, show a live preview, send a 16 kHz WAV,
// and play the spoken answer a sentence at a time.
(() => {
  const S = {ctx: null, stream: null, src: null, node: null, chunks: [], t0: 0, on: false,
             peek: null, queue: [], playing: null};

  // resume audio inside the tap, so answers can play later without another tap
  function unlock() {
    if (!S.ctx) S.ctx = new (window.AudioContext || window.webkitAudioContext)();
    S.ctx.resume();
    const s = S.ctx.createBufferSource();
    s.buffer = S.ctx.createBuffer(1, 1, 22050); s.connect(S.ctx.destination); s.start(0);
  }

  async function start(e, btn, suffix) {
    e.preventDefault();
    stop();  // a new question silences the old answer
    unlock();
    // react at once, even while Safari asks for the microphone
    btn.textContent = '🔴 Listening… let go to send';
    btn.classList.add('lerni-listening');
    S.on = true; S.chunks = []; S.t0 = performance.now();
    try {
      if (!S.stream) S.stream = await navigator.mediaDevices.getUserMedia({audio: true});
    } catch (err) { reset(btn); return; }  // no microphone: typing still works
    if (!S.on) return;  // let go while Safari was asking
    S.src = S.ctx.createMediaStreamSource(S.stream);
    S.node = S.ctx.createScriptProcessor(4096, 1, 1);
    S.node.onaudioprocess = ev => {
      if (S.on) S.chunks.push(new Float32Array(ev.inputBuffer.getChannelData(0)));
    };
    S.src.connect(S.node); S.node.connect(S.ctx.destination);
    // every 1.5 s, send the clip so far for a live preview
    S.peek = setInterval(() => fill(`lerni-partial-${suffix}`, `lerni-peek-${suffix}`), 1500);
  }

  function reset(btn) {
    S.on = false; clearInterval(S.peek);
    if (S.src) { S.src.disconnect(); S.node.disconnect(); S.src = S.node = null; }
    btn.textContent = '🎤 Hold to talk';
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
    if (!S.on) return;
    e.preventDefault();
    const held = (performance.now() - S.t0) / 1000;
    S.on = false;  // stop collecting before the last copy
    if (held >= 0.5) fill(`lerni-clip-${suffix}`, `lerni-heard-${suffix}`);  // shorter: Whisper invents words
    reset(btn);
  }

  async function next() {
    if (S.playing || !S.queue.length) return;
    const bin = Uint8Array.from(atob(S.queue.shift()), c => c.charCodeAt(0));
    const src = S.ctx.createBufferSource();
    S.playing = src;  // claimed before decoding, so sentences never overlap
    try {
      src.buffer = await S.ctx.decodeAudioData(bin.buffer);
    } catch (err) { S.playing = null; next(); return; }  // skip a sentence that won't play
    if (S.playing !== src) return;  // stopped while decoding
    src.connect(S.ctx.destination);
    src.onended = () => { if (S.playing === src) { S.playing = null; next(); } };
    src.start(0);
  }

  // the server sends [count, audio]; play each sentence in order
  function play(v) {
    if (!v || !S.ctx) return;
    S.queue.push(JSON.parse(v)[1]); next();
  }

  function stop() {
    S.queue = [];
    const src = S.playing; S.playing = null;
    if (src) { try { src.stop(); } catch (err) {} }  // not started yet: nothing to stop
  }

  window.lerniTalk = {play, stop};

  // wire each talk button once Gradio draws it (tabs appear after sign-in)
  setInterval(() => {
    for (const suffix of ['ask', 'home']) {
      const btn = document.getElementById(`lerni-talk-${suffix}`);
      if (!btn || btn.dataset.wired) continue;
      btn.dataset.wired = '1';
      btn.addEventListener('pointerdown', e => start(e, btn, suffix));
      for (const t of ['pointerup', 'pointercancel', 'pointerleave']) {
        btn.addEventListener(t, e => send(e, btn, suffix));
      }
      btn.addEventListener('contextmenu', e => e.preventDefault());
    }
  }, 500);
})();
