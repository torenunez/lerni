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
    """Speech to text and text to speech, behind an adapter."""

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
    text = "".join(c for c in text if unicodedata.category(c) not in ("So", "Sk", "Cs"))
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
