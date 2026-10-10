# Release 2, step 2: voice — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every student can hold a button, speak, see what Lerni heard as their message, and hear Lerni's answer spoken a sentence at a time, all on the home server.

**Architecture:** A `Speech` protocol in core (`voice.py`, standard library) with the pure pieces: checking a clip, cutting the streamed answer into sentences, and cleaning them for speaking. One adapter, `MacSpeech`, runs two commands on the home server: `whisper-cli` (speech to text) and macOS `say` (text to speech). The browser script `talk.js` records, sends the clip as base64 through a hidden Gradio field, and plays the returned audio in order. The answer goes through `ask_reply` as typed questions do, so roles, voices, the map, logs, and Stop are unchanged.

**Tech Stack:** Python standard library, Gradio 6.30 events and `js=`, whisper.cpp (Homebrew `whisper.cpp`, `whisper-cli`), macOS `say`.

**Spec:** [plans/specs/05-voice.md](specs/05-voice.md).

## Changes from the spec (2026-10-10)

- **The iPad check passed** (on the iPhone; same Safari rules): hold to record works, the clip reaches the server through a Gradio event, and the answer plays with no extra tap. Approach A stays.
- **Text to speech:** the Mac's own voice (`say`), not Kokoro. The admin liked it; there's nothing to install and no second program to keep running. Kokoro can replace it behind the same `Speech` protocol.
- **Speech to text:** `whisper-cli` per clip, not a running `whisper-server`. It's one less program to keep running, and loading the model costs well under a second on the M4. If that's too slow, `whisper-server` replaces it behind the same protocol.
- **The button reacts at once** (turns red and pulses, "Listening… let go to send"), and **a live preview** shows what Lerni hears while the button is held: every ~1.5 s the clip so far goes to `whisper-cli` (about 0.6 s on the M4), and the newest result replaces the last (`trigger_mode="always_last"`, so previews never pile up). The admin chose this over Safari's dictation, which sends audio to Apple (2026-10-10).
- **Only talked questions are answered aloud.** Typed questions stay text-only. The student never hears their own clip; what was heard shows in the chat so they can check it.

## Global Constraints

- Clips: at least 0.5 s (checked in the browser), at most 30 s; the server refuses anything over `MAX_CLIP_BYTES` (30 s of 16 kHz 16-bit mono plus a 44-byte header) or not a WAV, before any command runs.
- No audio is kept on purpose: the clip's temp file is deleted as soon as `whisper-cli` returns, and spoken audio lives only in memory. Logs keep text only, as today (CLAUDE.md rule 6).
- No audio or message text in server output; errors are general ("I couldn't hear that. Try again, or type it.").
- Voice is on only when `say`, `whisper-cli`, and the model file all exist at startup; otherwise no talk button and everything works as in Release 1.
- Settings are environment variables, not code: `LERNI_WHISPER_MODEL` (default `~/.lerni/models/ggml-small.bin`), `LERNI_SAY_VOICE` (default: the Mac's system voice).
- Tests use fakes, no real commands or network, minimal. Comment code concisely. Line length 100. Manifest rows for new and changed files.

## Review Focus

- **A clip from someone signed out** is refused before any command runs. (Task 3 test.)
- **An oversized or non-WAV clip** is refused before `whisper-cli` runs. (Task 1 test.)
- **A failed `say`** keeps the text answer, with one short note. (Task 1 test.)
- **The clip's temp file** is gone after transcribing, even when the command fails. (Task 2 test.)
- **Stop** silences the voice as well as the text (manual check, Task 4).

---

### Task 1: `voice.py`, the core

**Files:** Create `src/lerni/student/voice.py`; Test `tests/student/test_voice.py`.

**Interfaces:**
- Produces: `Speech` (protocol: `transcribe(wav: bytes) -> str`, `speak(text: str) -> bytes`), `SpeechUnavailable(RuntimeError)`, `ClipRefused(ValueError)`, `MAX_CLIP_BYTES`, `heard(speech, clip_b64: str) -> str`, `spoken_reply(speech, pieces: Iterable[str]) -> Iterator[tuple[str, bytes | None]]`, `for_speaking(text) -> str`, `HEARD_NOTHING`, `SPOKE_NOTHING`.

- [ ] **Step 1: Write the failing tests**

```python
"""Voice: a clip becomes a question, and an answer becomes spoken sentences."""

import base64
import io
import wave

import pytest

from lerni.student.voice import MAX_CLIP_BYTES, ClipRefused, SpeechUnavailable, heard, spoken_reply


class FakeSpeech:
    def __init__(self, text="what do sharks eat", fail_speak=False):
        self.text, self.fail_speak, self.spoken, self.clips = text, fail_speak, [], 0

    def transcribe(self, wav):
        self.clips += 1
        return self.text

    def speak(self, text):
        if self.fail_speak:
            raise SpeechUnavailable("no voice")
        self.spoken.append(text)
        return b"audio"


def clip(seconds=1.0):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        w.writeframes(b"\0\0" * int(16000 * seconds))
    return base64.b64encode(out.getvalue()).decode()


def test_answers_are_spoken_a_clean_sentence_at_a_time():
    speech = FakeSpeech()
    out = list(spoken_reply(speech, ["**Sharks** eat fish. 🦈 See [this](http://x.y)", " too!"]))
    assert "".join(text for text, _ in out) == "**Sharks** eat fish. 🦈 See [this](http://x.y) too!"
    assert speech.spoken == ["Sharks eat fish.", "See this too!"]
    assert [audio for _, audio in out if audio] == [b"audio", b"audio"]


def test_bad_clips_are_refused_before_transcribing():
    speech = FakeSpeech()
    assert heard(speech, clip()) == "what do sharks eat"
    for bad in ("not base64!", base64.b64encode(b"x" * 100).decode(),
                base64.b64encode(b"\0" * (MAX_CLIP_BYTES + 1)).decode()):
        with pytest.raises(ClipRefused):
            heard(speech, bad)
    assert speech.clips == 1


def test_a_failed_voice_keeps_the_text():
    out = list(spoken_reply(FakeSpeech(fail_speak=True), ["Hi. ", "Bye."]))
    assert "".join(text for text, _ in out) == "Hi. Bye."
    assert all(audio is None for _, audio in out)
```

- [ ] **Step 2: Run them**

Run: `.venv/bin/python -m pytest -q tests/student/test_voice.py`
Expected: FAIL (`lerni.student.voice` doesn't exist).

- [ ] **Step 3: Implement**

```python
"""Voice: what a student said becomes their question, and Lerni's answer is spoken.

Standard library only. The speech services sit behind :class:`Speech`
(adapters in ``lerni.student.adapters``); nothing here keeps audio.
"""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
from collections.abc import Iterable, Iterator
from typing import Protocol

MAX_CLIP_SECONDS = 30
MAX_CLIP_BYTES = 44 + MAX_CLIP_SECONDS * 16000 * 2  # 16 kHz 16-bit mono WAV
HEARD_NOTHING = "I couldn't hear that. Try again, or type it."
SPOKE_NOTHING = "I couldn't say that out loud."

# a sentence ends at . ! ? (then a space) or a line break
_END = re.compile(r"(?<=[.!?])\s+|\n+")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL = re.compile(r"https?://\S+")
_MARKS = re.compile(r"[*_#`>|~]+")


class SpeechUnavailable(RuntimeError):
    """A speech service failed; the message is general, never the audio or text."""


class ClipRefused(ValueError):
    """The clip is too big, or not a WAV."""


class Speech(Protocol):
    def transcribe(self, wav: bytes) -> str: ...  # 16 kHz mono WAV in, text out
    def speak(self, text: str) -> bytes: ...  # text in, audio Safari can play


def heard(speech: Speech, clip_b64: str) -> str:
    """Return what the student said, checking the clip first.

    Raises:
        ClipRefused: Not base64, not a WAV, or longer than 30 seconds.
        SpeechUnavailable: Nothing was heard, or the service failed.
    """
    if len(clip_b64) > MAX_CLIP_BYTES * 4 // 3 + 4:  # don't decode anything huge
        raise ClipRefused(HEARD_NOTHING)
    try:
        wav = base64.b64decode(clip_b64, validate=True)
    except (binascii.Error, ValueError):
        raise ClipRefused(HEARD_NOTHING) from None
    if len(wav) > MAX_CLIP_BYTES or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        raise ClipRefused(HEARD_NOTHING)
    text = speech.transcribe(wav).strip()
    if not text:
        raise SpeechUnavailable(HEARD_NOTHING)
    return text


def for_speaking(text: str) -> str:
    """Clean a sentence for the voice: no markdown, emoji, or web addresses."""
    text = _LINK.sub(r"\1", text)
    text = _URL.sub("a link", text)
    text = _MARKS.sub("", text)
    # drop emoji and other symbols
    text = "".join(c for c in text if unicodedata.category(c) not in ("So", "Cs"))
    return " ".join(text.split())


def spoken_reply(speech: Speech, pieces: Iterable[str]) -> Iterator[tuple[str, bytes | None]]:
    """Pass the answer through a piece at a time, with audio for each finished sentence.

    Yields ``(piece, None)`` as text arrives and ``("", audio)`` when a sentence
    is done. If the voice fails, the text keeps coming without audio.
    """
    pending, voice_ok = "", True

    def say(sentence: str) -> Iterator[tuple[str, bytes | None]]:
        nonlocal voice_ok
        clean = for_speaking(sentence)
        if voice_ok and clean:
            try:
                yield "", speech.speak(clean)
            except SpeechUnavailable:
                voice_ok = False  # one failure: text only from here on

    for piece in pieces:
        yield piece, None
        pending += piece
        *done, pending = _END.split(pending)
        for sentence in done:
            yield from say(sentence)
    yield from say(pending)
```

Note: the test expects audio only from the `("", audio)` items and text only from the pieces, so `"".join(text …)` rebuilds the answer exactly.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest -q tests/student/test_voice.py && .venv/bin/python -m ruff check src/lerni/student/voice.py tests/student/test_voice.py`
Expected: 3 pass; ruff clean.

Manifest: rows for `voice.py` ("Voice: checks a clip and gets what was said; cuts Lerni's answer into clean sentences to speak; keeps no audio") and `test_voice.py`.

```bash
git add src/lerni/student/voice.py tests/student/test_voice.py docs/code-manifest.md
git commit -m "Voice core: check a clip, speak an answer a sentence at a time"
```

---

### Task 2: `MacSpeech`, the adapter

**Files:** Create `src/lerni/student/adapters/mac_speech.py`; Test `tests/student/test_mac_speech.py`.

**Interfaces:**
- Consumes: `SpeechUnavailable`, `HEARD_NOTHING`, `SPOKE_NOTHING` (Task 1).
- Produces: `MacSpeech(model: Path, voice: str = "", runner=subprocess.run)` with `transcribe` and `speak`; `mac_speech_from_env() -> MacSpeech | None`.

- [ ] **Step 1: Write the failing test**

```python
"""MacSpeech: whisper-cli and say, run as commands; the clip's temp file never stays."""

import subprocess
from pathlib import Path

from lerni.student.adapters.mac_speech import MacSpeech


def test_runs_the_commands_and_leaves_no_clip_behind(tmp_path):
    seen = []

    def run(cmd, **kwargs):
        seen.append(cmd)
        if cmd[0] == "say":
            Path(cmd[cmd.index("-o") + 1]).write_bytes(b"m4a")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        assert Path(cmd[cmd.index("-f") + 1]).read_bytes() == b"RIFFwav"
        return subprocess.CompletedProcess(cmd, 0, " What do sharks eat?\n[BLANK_AUDIO]\n", "")

    speech = MacSpeech(tmp_path / "model.bin", voice="Samantha", runner=run)
    assert speech.transcribe(b"RIFFwav") == "What do sharks eat?"
    assert speech.speak("Fish.") == b"m4a"
    clip_file = Path(seen[0][seen[0].index("-f") + 1])
    assert not clip_file.exists()  # deleted once transcribed
    assert seen[1][:3] == ["say", "-v", "Samantha"]
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python -m pytest -q tests/student/test_mac_speech.py`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
"""Speech on the home server (a Mac): whisper.cpp's ``whisper-cli`` hears, ``say`` speaks.

Both run as commands, so there's no second program to keep running. Audio
stays on the home server, in temp files deleted at once.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lerni.student.voice import HEARD_NOTHING, SPOKE_NOTHING, SpeechUnavailable

MODEL_ENV, VOICE_ENV = "LERNI_WHISPER_MODEL", "LERNI_SAY_VOICE"
DEFAULT_MODEL = Path.home() / ".lerni" / "models" / "ggml-small.bin"
TIMEOUT = 30  # seconds per command
_NOISE = re.compile(r"\[[^\]]*\]|\([^)]*\)")  # [BLANK_AUDIO], (music) and the like


class MacSpeech:
    """``whisper-cli`` for speech to text and ``say`` for text to speech."""

    def __init__(
        self, model: Path, voice: str = "", runner: Callable[..., Any] = subprocess.run
    ) -> None:
        self.model, self.voice, self._run = model, voice, runner

    def transcribe(self, wav: bytes) -> str:
        """Return what was said in a 16 kHz mono WAV ("" for silence)."""
        with tempfile.TemporaryDirectory() as tmp:  # deleted on the way out, even on errors
            clip = Path(tmp) / "clip.wav"
            clip.write_bytes(wav)
            cmd = ["whisper-cli", "-m", str(self.model), "-f", str(clip), "-l", "auto", "-nt", "-np"]
            try:
                out = self._run(cmd, capture_output=True, text=True, timeout=TIMEOUT, check=True)
            except (OSError, subprocess.SubprocessError):
                raise SpeechUnavailable(HEARD_NOTHING) from None
        return " ".join(_NOISE.sub(" ", out.stdout).split())

    def speak(self, text: str) -> bytes:
        """Return ``text`` spoken, as AAC audio Safari can play."""
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "say.m4a"
            voice = ["-v", self.voice] if self.voice else []
            cmd = ["say", *voice, "-o", str(audio), "--file-format=m4af", "--data-format=aac", text]
            try:
                self._run(cmd, capture_output=True, timeout=TIMEOUT, check=True)
                return audio.read_bytes()
            except (OSError, subprocess.SubprocessError):
                raise SpeechUnavailable(SPOKE_NOTHING) from None


def mac_speech_from_env() -> MacSpeech | None:
    """Return the Mac's speech if ``say``, ``whisper-cli``, and the model are all here, else ``None``."""
    model = Path(os.environ.get(MODEL_ENV, DEFAULT_MODEL)).expanduser()
    if not (shutil.which("say") and shutil.which("whisper-cli") and model.is_file()):
        return None
    return MacSpeech(model, os.environ.get(VOICE_ENV, ""))
```

Ruling to check at build time: `say`'s first word must be `say` for the test's `seen[1][:3]`; when no voice is set, the command is `["say", "-o", …]`.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest -q tests/student/test_mac_speech.py && .venv/bin/python -m ruff check src/lerni/student/adapters/mac_speech.py tests/student/test_mac_speech.py`
Expected: pass; ruff clean.

Manifest rows for both files.

```bash
git add src/lerni/student/adapters/mac_speech.py tests/student/test_mac_speech.py docs/code-manifest.md
git commit -m "MacSpeech: whisper-cli hears, say speaks"
```

---

### Task 3: Talk in the conversation (server side)

**Files:** Modify `src/lerni/student/web/ask.py`, `src/lerni/student/web/main.py` (pass `speech` through), `src/lerni/student/web/app.py` (`build_app(speech=…)`, `.lerni-hide` CSS, `head` with `talk.js`), `src/lerni/student/web/serve.py` (pick `mac_speech_from_env()`, print `Voice: on/off`); Test `tests/student/test_web_roles.py` (append).

**Interfaces:**
- Consumes: `heard`, `spoken_reply`, `Speech`, errors (Task 1); `mac_speech_from_env` (Task 2).
- Produces: `talk_reply(conversations, speech, viewer, clip_b64, supervised_voice=False) -> tuple[str, Iterator[tuple[str, bytes | None]]]` in `ask.py`; `build_app(..., speech: Speech | None = None)`; `ask_tab(signin, conversations, supervised=False, speech=None)`; element ids `lerni-talk-{ask|home}`, `lerni-clip-{ask|home}`, `lerni-heard-{ask|home}`, `lerni-spoken-{ask|home}` for Task 4.

- [ ] **Step 1: Write the failing test** (append)

```python
def test_a_talked_question_is_heard_then_answered_in_the_right_voice():
    from lerni.student.conversation import Conversations
    from lerni.student.web.ask import talk_reply
    from tests.student.test_voice import FakeSpeech, clip

    class Model:
        def __init__(self):
            self.systems = []

        def stream(self, system, turns):
            self.systems.append(system)
            yield "Fish. Seals too."

    model, speech = Model(), FakeSpeech()
    convos = Conversations(model)
    lee = Viewer("lee", "Lee", Role.SUPERVISED)
    text, reply = talk_reply(convos, speech, lee, clip())
    assert text == "what do sharks eat"
    out = list(reply)
    assert "".join(t for t, _ in out) == "Fish. Seals too."
    assert speech.spoken == ["Fish.", "Seals too."]
    assert "short, simple, playful" in model.systems[0]  # the supervised voice
    assert convos.history("lee")[0].text == "what do sharks eat"
    with pytest.raises(NotAllowed):
        talk_reply(convos, speech, None, clip())
    assert speech.clips == 1  # nobody signed in: nothing transcribed
    assert talk_preview(speech, lee, clip()) == "what do sharks eat"
    assert talk_preview(speech, lee, "not a clip") == ""  # a bad preview shows nothing
    with pytest.raises(NotAllowed):
        talk_preview(speech, None, clip())
```

(Import `talk_preview` alongside `talk_reply`.)

(If `tests.student` isn't importable as a package, move `FakeSpeech` and `clip` into `tests/student/conftest.py` as plain helpers and import from there; ledger the ruling.)

- [ ] **Step 2: Run it**

Run: `.venv/bin/python -m pytest -q tests/student/test_web_roles.py -k talked`
Expected: FAIL (`talk_reply` doesn't exist).

- [ ] **Step 3: Implement**

In `ask.py`:

```python
def talk_reply(
    conversations: Conversations,
    speech: Speech,
    viewer: Viewer | None,
    clip_b64: str,
    supervised_voice: bool = False,
) -> tuple[str, Iterator[tuple[str, bytes | None]]]:
    """Hear a spoken question, then answer it a piece at a time with audio per sentence.

    Raises:
        NotAllowed: Nobody is signed in (checked before anything is heard).
        ClipRefused, SpeechUnavailable: Nothing usable was heard.
    """
    require(viewer, Role.INDEPENDENT, Role.SUPERVISED)
    text = heard(speech, clip_b64)
    return text, spoken_reply(speech, ask_reply(conversations, viewer, text, supervised_voice))


def talk_preview(speech: Speech, viewer: Viewer | None, clip_b64: str) -> str:
    """What has been heard so far while the button is held; "" if nothing usable.

    Raises:
        NotAllowed: Nobody is signed in.
    """
    require(viewer, Role.INDEPENDENT, Role.SUPERVISED)
    try:
        return heard(speech, clip_b64)
    except (ClipRefused, SpeechUnavailable):
        return ""
```

The talk block also gets the preview: a `gr.Markdown(elem_id=f"lerni-preview-{suffix}")` under the button, a hidden `partial` textbox and hidden `peek` button, and

```python
            def on_peek(b64: str, request: gr.Request) -> str:
                viewer = signin.viewer(request.username)
                return f"🎤 {talk_preview(speech, viewer, b64)}" if viewer else ""

            # only the newest preview runs; older ones are dropped
            peek.click(on_peek, partial, preview, trigger_mode="always_last", **PRIVATE)
```

and `on_talk` clears the preview (`preview` joins its outputs; every yield adds `""` for it).

In `ask_tab(..., speech: Speech | None = None)`, when `speech` and `ready`, under the question row:

```python
        talking = None
        if speech is not None and ready:
            suffix = "home" if supervised else "ask"
            gr.Button("🎤 Hold to talk", elem_id=f"lerni-talk-{suffix}", size="lg")
            # hidden fields the browser script fills and reads
            clip = gr.Textbox(elem_id=f"lerni-clip-{suffix}", elem_classes="lerni-hide")
            spoken = gr.Textbox(elem_id=f"lerni-spoken-{suffix}", elem_classes="lerni-hide")
            heard_btn = gr.Button(elem_id=f"lerni-heard-{suffix}", elem_classes="lerni-hide")

            def on_talk(b64: str, supervised_voice: bool, request: gr.Request) -> Iterator[list[Any]]:
                viewer = signin.viewer(request.username)  # re-read on every clip
                if viewer is None:  # the role check lives in talk_reply
                    yield [gr.update(), gr.update()]
                    return
                shown = messages(conversations, viewer.username)
                try:
                    text, reply = talk_reply(conversations, speech, viewer, b64, supervised_voice)
                except (ClipRefused, SpeechUnavailable) as exc:
                    yield [shown + [{"role": "assistant", "content": f"⚠️ {exc}"}], gr.update()]
                    return
                shown += [{"role": "user", "content": text}, {"role": "assistant", "content": "…"}]
                yield [shown, gr.update()]
                answer, sent, quiet = "", 0, False
                try:
                    for piece, audio in reply:
                        answer += piece
                        shown[-1]["content"] = answer or "…"
                        if audio:
                            sent += 1  # a new value each time, so the page always plays it
                            yield [shown, json.dumps([sent, base64.b64encode(audio).decode()])]
                        else:
                            yield [shown, gr.update()]
                    quiet = bool(answer) and not sent  # text came, but no voice at all
                except (ConversationError, ConversationUnavailable) as exc:
                    shown[-1]["content"] = f"{answer}\n\n⚠️ {exc}" if answer else f"⚠️ {exc}"
                if quiet:
                    shown[-1]["content"] += f"\n\n🔇 {SPOKE_NOTHING}"
                yield [shown, gr.update()]

            talking = heard_btn.click(
                lambda: [gr.update(interactive=False), gr.update(visible=False),
                         gr.update(visible=True)],
                None, controls, **PRIVATE,
            ).then(on_talk, [clip, voice], [chat, spoken],
                   concurrency_limit=MAX_AT_ONCE, **PRIVATE)
            talking.then(unlock, None, controls, **PRIVATE)
            spoken.change(None, spoken, None, js="(v) => window.lerniTalk?.play(v)")
```

Then: `stop.click(..., cancels=[answering, talking] if talking else [answering])`, plus `stop.click(None, None, None, js="() => window.lerniTalk?.stop()")`, and the same `cancels` and stop script on `new.click`. (Move the stop and new wiring below this block.) Imports: `base64`, `json`, and from `lerni.student.voice` `ClipRefused`, `SPOKE_NOTHING`, `Speech`, `SpeechUnavailable`, `heard`, `spoken_reply`.

`main.py`: accept `speech` and pass it to both `ask_tab` calls. `app.py`: `build_app(..., speech=None)` passes it to `build_main_view`; `_CSS` gains `.lerni-hide { display: none !important; }` and the held button's look (`.lerni-listening { background: #dc2626 !important; color: white !important; animation: lerni-pulse 1s ease-in-out infinite; }` with a `@keyframes lerni-pulse` that scales to 1.05 and back); `mount_gradio_app(..., head=_talk_head() if speech else "")`, where `_talk_head()` reads `talk.js` with `importlib.resources` and wraps it in `<script>`. `serve.py`: `speech = _speech()` (lazy import of `mac_speech_from_env`), pass it, and print `Voice (hold to talk): on` or `off (install whisper.cpp and the model: admin reference, Voice)`.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m ruff check src/lerni/student/web/ask.py src/lerni/student/web/app.py src/lerni/student/web/main.py src/lerni/student/web/serve.py tests/student/test_web_roles.py`
Expected: all pass; ruff clean. (The page builds even though `talk.js` comes in Task 4: `_talk_head()` runs only with speech on, and tests pass `speech=None` except where faked.)

Manifest: `ask.py`, `app.py`, `main.py`, `serve.py`, `test_web_roles.py` rows mention hold to talk.

```bash
git add src/lerni/student/web tests/student/test_web_roles.py docs/code-manifest.md
git commit -m "Hold to talk: hear the question, answer aloud a sentence at a time"
```

---

### Task 4: `talk.js`, the browser side

**Files:** Create `src/lerni/student/web/talk.js`; Modify `pyproject.toml` (package data `"lerni.student.web" = ["*.js"]`); Test: the distribution test already checks package data if it lists files; otherwise a manual check.

- [ ] **Step 1: Write `talk.js`** (from the iPad check page, without the echo)

```javascript
// Hold to talk: record while the button is held, send a 16 kHz WAV, play the spoken answer.
(() => {
  const S = {ctx: null, stream: null, src: null, node: null, chunks: [], t0: 0, on: false,
             queue: [], playing: null};

  // resume audio inside the tap, so answers can play later without another tap
  function unlock() {
    if (!S.ctx) S.ctx = new (window.AudioContext || window.webkitAudioContext)();
    S.ctx.resume();
    const s = S.ctx.createBufferSource();
    s.buffer = S.ctx.createBuffer(1, 1, 22050); s.connect(S.ctx.destination); s.start(0);
  }

  async function start(e, btn) {
    e.preventDefault();
    stop();  // a new question silences the old answer
    unlock();
    try {
      if (!S.stream) S.stream = await navigator.mediaDevices.getUserMedia({audio: true});
    } catch (err) { return; }  // no microphone: typing still works
    S.chunks = []; S.t0 = performance.now(); S.on = true;
    S.src = S.ctx.createMediaStreamSource(S.stream);
    S.node = S.ctx.createScriptProcessor(4096, 1, 1);
    S.node.onaudioprocess = ev => { if (S.on) S.chunks.push(new Float32Array(ev.inputBuffer.getChannelData(0))); };
    S.src.connect(S.node); S.node.connect(S.ctx.destination);
    btn.textContent = '🔴 Listening… let go to send';
    btn.classList.add('lerni-listening');  // red and pulsing while held
    // every 1.5 s, send the clip so far for a live preview
    S.peek = setInterval(() => fill(`lerni-partial-${suffixOf(btn)}`, `lerni-peek-${suffixOf(btn)}`), 1500);
  }

  const suffixOf = btn => btn.id.replace('lerni-talk-', '');

  // put the clip so far in a hidden field and press its hidden button
  function fill(boxId, buttonId) {
    let n = 0; S.chunks.forEach(c => n += c.length);
    if (n < S.ctx.sampleRate * 0.5) return;  // under half a second: nothing to show yet
    const all = new Float32Array(n); let o = 0; S.chunks.forEach(c => { all.set(c, o); o += c.length; });
    const box = document.querySelector(`#${boxId} textarea`);
    box.value = b64(wav(downsample(all, S.ctx.sampleRate)));
    box.dispatchEvent(new Event('input', {bubbles: true}));
    setTimeout(() => document.getElementById(buttonId).click(), 50);
  }

  // average down to 16 kHz mono, at most 30 seconds
  function downsample(buf, rate) {
    const r = rate / 16000, out = new Float32Array(Math.min(Math.floor(buf.length / r), 16000 * 30));
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
    for (let i = 0; i < x.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x[i])) * 0x7fff, true);
    return new Uint8Array(v.buffer);
  }

  function b64(bytes) {
    let s = '';
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }

  function send(e, btn, suffix) {
    if (!S.on) return;
    e.preventDefault();
    S.on = false; clearInterval(S.peek); S.src.disconnect(); S.node.disconnect();
    btn.textContent = '🎤 Hold to talk';
    btn.classList.remove('lerni-listening');
    if ((performance.now() - S.t0) / 1000 < 0.5) return;  // too short: Whisper invents words
    fill(`lerni-clip-${suffix}`, `lerni-heard-${suffix}`);
  }

  async function next() {
    if (S.playing || !S.queue.length) return;
    const bin = Uint8Array.from(atob(S.queue.shift()), c => c.charCodeAt(0));
    try {
      const src = S.ctx.createBufferSource();
      src.buffer = await S.ctx.decodeAudioData(bin.buffer);
      src.connect(S.ctx.destination);
      src.onended = () => { S.playing = null; next(); };
      S.playing = src; src.start(0);
    } catch (err) { S.playing = null; next(); }  // skip a sentence that won't play
  }

  // the server sends [count, audio]; play each sentence in order
  function play(v) {
    if (!v || !S.ctx) return;
    S.queue.push(JSON.parse(v)[1]); next();
  }

  function stop() {
    S.queue = [];
    if (S.playing) { S.playing.onended = null; try { S.playing.stop(); } catch (e) {} S.playing = null; }
  }

  window.lerniTalk = {play, stop};

  // wire each talk button once Gradio draws it (tabs appear after sign-in)
  setInterval(() => {
    for (const suffix of ['ask', 'home']) {
      const btn = document.getElementById(`lerni-talk-${suffix}`);
      if (!btn || btn.dataset.wired) continue;
      btn.dataset.wired = '1';
      btn.style.touchAction = 'none'; btn.style.userSelect = 'none'; btn.style.webkitUserSelect = 'none';
      btn.style.webkitTouchCallout = 'none';
      btn.addEventListener('pointerdown', e => start(e, btn));
      ['pointerup', 'pointercancel', 'pointerleave'].forEach(t => btn.addEventListener(t, e => send(e, btn, suffix)));
      btn.addEventListener('contextmenu', e => e.preventDefault());
    }
  }, 500);
})();
```

- [ ] **Step 2: Package data and the whole suite**

Add `"lerni.student.web" = ["*.js"]` under `[tool.setuptools.package-data]`.

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 3: Install the speech tools on the home server and try it in development** (needs the admin's OK for the installs)

```bash
brew install whisper.cpp
mkdir -p ~/.lerni/models && curl -L -o ~/.lerni/models/ggml-small.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
```

Start development over HTTPS on port 7861 (`--cert`/`--key` as production, `--label Development`, `LERNI_STUDENT_DATA=~/.lerni/student-dev`). The admin tries it on the iPhone, then the iPad: hold, speak, see what was heard, hear the answer; Stop silences it; a typed question stays silent. Pick a voice: `say -v '?'` lists them; try a few with `say -v NAME "Sharks are amazing swimmers!"`, set `LERNI_SAY_VOICE`.

- [ ] **Step 4: Commit**

Manifest row for `talk.js`.

```bash
git add src/lerni/student/web/talk.js pyproject.toml docs/code-manifest.md
git commit -m "talk.js: hold to record, play the answer sentence by sentence"
```

---

### Task 5: Eval and docs

**Files:** Create `scripts/eval_voice.py`; Modify `docs/reference/admin.md` (a "Voice" section), `plans/specs/05-voice.md` (the changes above, dated), `docs/ARCHITECTURE.md`, `docs/roadmap.md`, `docs/todo.md`, `docs/progress.md`, `docs/code-manifest.md`.

- [ ] **Step 1: `scripts/eval_voice.py`** (real commands, run by hand; 2 cases): (1) round trip: `say` three sentences to AIFF, `afconvert -f WAVE -d LEI16@16000 -c 1` to a 16 kHz WAV, `MacSpeech.transcribe`, and report the share of words that came back (pass at 80% or more); (2) speak "What do sharks eat?", transcribe, ask the supervised voice through `ClaudeCodeChat`, and check the answer is under 60 words.

- [ ] **Step 2: Admin reference, "Voice"** (under "Running the student app"): install whisper.cpp and the model (the two commands above; about 0.5 GB), optional `LERNI_SAY_VOICE` (and System Settings → Accessibility → Spoken Content → System Voice → Manage Voices to download nicer ones), restart, and check the startup line says `Voice (hold to talk): on`. Voice needs HTTPS.

- [ ] **Step 3: Other docs.** Spec 05: the decisions table's "Speech services" row and the code list, dated 2026-10-10, with the reasons above. ARCHITECTURE: the speech boundary (audio stays on the home server; commands, not services). Roadmap: Release 2 step 2 in review. Todo: the stale "Next:" line becomes "Release 2 step 2, voice ([plan](../plans/release-2-step-2-voice.md))"; an Admin task to install the speech tools; an Educator task to try voice with the supervised student. Progress: a dated entry.

- [ ] **Step 4: Gate, docs drift, commit**

Run: `.venv/bin/python -m pytest -q`, then the docs-drift skill on the branch.

```bash
git add scripts/eval_voice.py docs plans
git commit -m "Voice: eval and docs"
```

---

## Done when (from the spec)

The supervised student holds a short spoken conversation on the iPad with an adult nearby, and their map grows.

## Deploying (for the PR)

Safe to put on the home server while in use. Without the speech tools, nothing changes (no talk button). With them: `brew install whisper.cpp`, download the model, pull, reinstall, restart; a restart clears open conversations. Voice needs the HTTPS address.
