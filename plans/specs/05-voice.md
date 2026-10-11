# Voice: hold to talk, answers aloud (Release 2)

Approved in conversation on 2026-10-10 (approach A, refined below). Requirements: [student PRD, Release 2](../../docs/prd/student.md#release-2-talk-with-the-app). Builds on the conversation and map from [spec 04](04-interest-map.md); nothing about the agent, the map, or the tagger changes.

## What each person sees

- **Every student** (supervised and independent), when the speech helpers are running on the home server: one big **Hold to talk** button under the chat, beside the question box. Hold it and speak; let go to send. What Lerni heard appears in the chat as their message and goes to Lerni at once, as if typed. Lerni's answer appears as text, as today, and is spoken a sentence at a time as it's written. With voice on, the screen is just the chat and the button: a tap silences Lerni and a hold interrupts it (changed 2026-10-10; was Stop plus typing).
- **When the helpers aren't running:** no talk button; typing only, exactly as in Release 1. If a helper fails during a conversation: "I couldn't hear that. Try again, or type it." (or "…couldn't speak that…"), and the text answer still shows.
- No setting and no new screen. (The educator PRD's per-student Voice switch waits until someone needs voice off for one student.)

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Button | Hold to talk (press, speak, release) | Walkie-talkie; nothing to forget to stop |
| Speech services | Commands on the home server: whisper.cpp's `whisper-cli` (speech-to-text) and macOS `say` (text-to-speech), behind one adapter. Changed during the build (2026-10-10; was a Whisper server and Kokoro): see the [step 2 plan](../release-2-step-2-voice.md) | No audio leaves the house, no account, $0, nothing extra to keep running |
| Transport | Approach A, refined: Gradio events carry the audio as base64 text in hidden fields; a small browser script records and plays | Keeps every handler's sign-in check, and playback unlocked by the press is the dependable way to get sound on iPad Safari. If the iPad check shows Gradio's own audio player works, it may be used instead |
| Sending | What was heard is sent at once and shown in the chat | Smooth for talking; local speech-to-text removes the privacy reason for a confirm step |
| HTTPS | Our own certificate (mkcert) installed once on each device | Free, no account, home network only |
| Who | Everyone, whenever the helpers are running | No setting to manage |
| Keeping audio | Audio may stay on the home server for up to 7 days, like the conversation logs; Release 2 doesn't save it on purpose | The admin's call (2026-10-10): whatever is easiest for the MVP; a light audio log can come later if useful |
| Who could hear it | If audio ends up in Gradio's cache, anyone signed in could reach it by URL | Accepted for the household (at most three people signed in, each with their own account); revisit before anyone outside the family uses the app |

## How it works

**Talking** (browser → server):

1. Pressing the button starts recording with the browser's microphone (Web Audio), and unlocks audio playback for this page (iPad Safari only plays sound started from a tap).
2. Releasing stops it. The script builds a 16 kHz mono WAV in the browser (Whisper's format, so the server needs no ffmpeg), base64-encodes it, puts it in a hidden field, and triggers a Gradio event.
3. Clips shorter than half a second are dropped in the browser (Whisper invents words from silence); clips stop at 30 seconds.
4. The server handler resolves the viewer as every handler does, decodes the clip in memory, sends it to the speech-to-text helper, and gets text. Empty or failed: the friendly message above.
5. The text becomes the student's message and goes through the existing conversation path (`ask_reply`), so the voice, the safety rules, the map, the tagger, Stop, and the 7-day text logs all work unchanged.

**Answering aloud** (server → browser):

6. As Claude's answer streams, the handler cuts it into sentences. Each finished sentence is cleaned for speaking (no emoji, no markdown symbols, links read as "a link"), sent to the text-to-speech helper, and the returned mp3 goes back base64-encoded in a hidden field alongside the text.
7. The script queues each sentence's audio and plays them in order with the unlocked audio context. Stop clears the queue, silences playback, and cancels the call (Release 1's Stop).

**Audio stays in the house:** the clip and the spoken sentences never leave the home server. Lerni doesn't save them on purpose (the logs keep text only, as today); if a later change keeps audio (a Gradio audio player, or a light audio log), it's deleted within 7 days, like the logs.

## Code

- **`src/lerni/student/voice.py`** (core, standard library only):
  - `Speech` protocol: `transcribe(wav: bytes) -> str` and `speak(text: str) -> bytes` (mp3).
  - The adapter, `adapters/mac_speech.py` (`MacSpeech`, `mac_speech_from_env()`), runs the two commands; voice is off unless both and the Whisper model are there. Settings: `LERNI_WHISPER_MODEL`, `LERNI_SAY_VOICE`.
  - `sentences(stream)`: turns streamed answer pieces into finished sentences; `for_speaking(text)`: the cleanup.
  - `MIN_CLIP_SECONDS = 0.5`, `MAX_CLIP_SECONDS = 30`, `MAX_CLIP_BYTES` (30 s of 16 kHz 16-bit mono, plus the WAV header).
- **`src/lerni/student/web/talk.js`** (shipped as package data, loaded with Gradio's `head`): the hold button (pointer events, so it works with touch and mouse), recording, the WAV encoding, the hidden fields, and the playback queue. About 100 lines, commented.
- **`src/lerni/student/web/ask.py`:** the talk button and the two hidden fields on both panels (Ask and the supervised screen); a `talk` handler that transcribes and then runs the same answer flow, adding audio per sentence. Shown only when speech is available.
- **`src/lerni/student/web/serve.py` / `commands/serve.py`:** `--cert` and `--key` to serve HTTPS (uvicorn's TLS); the sign-in cookie gets `Secure` when served over HTTPS; startup prints whether voice is on.
- **Admin reference:** setting up mkcert (the certificate authority on the home server, a certificate for the server's name and address, the profile on each device and "full trust" on the iPad), installing and starting the two helpers (pinned versions, the models to download, how much disk they take), and the environment variables.

## Build order

One PR per step, each from `main`:

| Step | Ships | Done when |
|---|---|---|
| R2-1 | **HTTPS.** `lerni serve --cert --key`; `Secure` cookie over HTTPS; mkcert setup in the admin reference | The iPad opens the app over HTTPS with no warning, and signing in works |
| R2-2 | **Voice.** First, a check on the real iPad (a throwaway page): hold-to-record works and a sentence plays without an extra tap. Then `voice.py`, `talk.js`, the talk button and handler, the helpers' setup in the admin reference, and the evals | The supervised student holds a short spoken conversation on the iPad with an adult nearby, and their map grows |

If the iPad check shows Gradio's events can't carry the clip or iPad Safari won't play the queued audio, stop and revisit the transport (approach B: our own routes for the audio, with their own sign-in check) before building the rest.

## Tests and evals

Tests (fakes only, minimal):

- `sentences` and `for_speaking`: pieces become whole sentences; emoji and markdown are dropped;
- the talk handler with a fake `Speech`: the transcript reaches the conversation as the student's message, each sentence comes back with audio, a failed transcription gives the friendly message and sends nothing, and a supervised viewer still gets the supervised voice;
- a clip over the size limit is refused;
- over HTTPS the sign-in cookie is `Secure`.

Evals (real helpers, run by hand; start with 2): a round trip (speak a sentence with Kokoro, transcribe it with Whisper, compare the words), and a spoken question to the supervised voice that comes back short.

## Risks

- **iPad Safari audio rules:** the first step checks them on the real device before anything else is built.
- **Home server disk:** about 17 GB was free in September; the Whisper model (small, about 0.5 GB) and Kokoro with its Python dependencies (a few GB) fit, but check free space first.
- **Kokoro's voice may sound flat** to a young listener; try it with the students before considering a hosted voice (which needs the educator's agreement, since audio would leave the house).
- **Saved passwords:** moving from `http://` to `https://` is a new address for Safari; the saved password should follow the domain, but check it.

## Not in this design

Hands-free talking (no button), a per-student voice switch, choosing a voice in the app, reading old messages aloud on demand, an audio log.
