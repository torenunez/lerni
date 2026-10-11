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
