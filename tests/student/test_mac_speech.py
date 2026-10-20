"""MacSpeech: whisper-cli and say, run as commands; the clip's temp file never stays."""

import subprocess
from pathlib import Path

import pytest

from lerni.student.adapters import mac_speech
from lerni.student.adapters.mac_speech import MacSpeech
from lerni.student.voice import SpeechUnavailable


def test_runs_the_commands_and_leaves_no_clip_behind(tmp_path):
    seen = []

    def run(cmd, **kwargs):
        seen.append(cmd)
        if cmd[0] == "say":
            Path(cmd[cmd.index("-o") + 1]).write_bytes(b"m4a" * 400)  # real audio, not silence
            return subprocess.CompletedProcess(cmd, 0, "", "")
        assert Path(cmd[cmd.index("-f") + 1]).read_bytes() == b"RIFFwav"
        return subprocess.CompletedProcess(cmd, 0, b" What do sharks eat?\n[BLANK_AUDIO]\n", b"")

    speech = MacSpeech(tmp_path / "model.bin", voice="Samantha", runner=run)
    assert speech.transcribe(b"RIFFwav") == "What do sharks eat?"
    assert speech.speak("Fish.") == b"m4a" * 400
    clip_file = Path(seen[0][seen[0].index("-f") + 1])
    assert not clip_file.exists()  # deleted once transcribed
    assert seen[1][:3] == ["say", "-v", "Samantha"]


def test_a_transcript_cut_mid_letter_still_reads(tmp_path):
    # regression: an accented letter cut short crashed the clip (seen in production 2026-10-13)
    def whisper(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=b"un caf\xc3")

    assert MacSpeech(tmp_path / "model.bin", runner=whisper).transcribe(b"RIFF") == "un caf�"


def test_silent_audio_turns_voice_off(tmp_path, monkeypatch):
    # regression: started over SSH, say wrote empty audio and Safari played silence
    def silent_say(cmd, **kwargs):
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"\0" * 28)  # what say writes with no sound
        return subprocess.CompletedProcess(cmd, 0)

    with pytest.raises(SpeechUnavailable):
        mac_speech.MacSpeech(tmp_path / "model.bin", runner=silent_say).speak("Hi")
    model = tmp_path / "model.bin"
    model.write_bytes(b"")
    monkeypatch.setenv(mac_speech.MODEL_ENV, str(model))
    monkeypatch.setattr(mac_speech.shutil, "which", lambda tool: "/usr/bin/" + tool)
    speech, why = mac_speech.mac_speech_from_env(runner=silent_say)
    assert speech is None and "SSH" in why and "tmux" in why

    def bad_voice(cmd, **kwargs):  # regression (review): every failure blamed SSH
        raise subprocess.CalledProcessError(1, cmd)

    speech, why = mac_speech.mac_speech_from_env(runner=bad_voice)
    assert speech is None and "LERNI_SAY_VOICE" in why and "SSH" not in why
