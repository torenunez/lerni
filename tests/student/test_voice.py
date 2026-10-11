"""Voice: a clip becomes a question, and an answer becomes spoken sentences."""

import base64
import io
import wave

import pytest

from lerni.student.voice import MAX_CLIP_BYTES, ClipRefused, SpeechUnavailable, heard, spoken_reply


class FakeSpeech:
    """Hears a fixed question and speaks anything, counting what it does."""

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
    """A silent 16 kHz mono WAV, base64-encoded as the page sends it."""
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
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
