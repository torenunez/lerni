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
            cmd = [
                "whisper-cli",
                "-m",
                str(self.model),
                "-f",
                str(clip),
                "-l",
                "auto",
                "-nt",
                "-np",
            ]
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
            cmd = [
                "say",
                *voice,
                "-o",
                str(audio),
                "--file-format=m4af",
                "--data-format=aac",
                "--",
                text,
            ]  # "--": text starting with "-" isn't an option
            try:
                self._run(cmd, capture_output=True, timeout=TIMEOUT, check=True)
                return audio.read_bytes()
            except (OSError, subprocess.SubprocessError):
                raise SpeechUnavailable(SPOKE_NOTHING) from None


def mac_speech_from_env() -> MacSpeech | None:
    """The Mac's speech if ``say``, ``whisper-cli``, and the model are here, else ``None``."""
    model = Path(os.environ.get(MODEL_ENV, DEFAULT_MODEL)).expanduser()
    if not (shutil.which("say") and shutil.which("whisper-cli") and model.is_file()):
        return None
    return MacSpeech(model, os.environ.get(VOICE_ENV, ""))
