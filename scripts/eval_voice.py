"""Voice evals: the real speech tools (and Claude for case 2), run by hand when they change.

    .venv/bin/python scripts/eval_voice.py

Needs whisper.cpp and its model (admin reference: Voice). Add one case for each problem seen.
"""

import subprocess
import tempfile
from pathlib import Path

from lerni.student.adapters.claude_code import ClaudeCodeChat
from lerni.student.adapters.mac_speech import mac_speech_from_env
from lerni.student.conversation import Turn, system_prompt


def clip(text: str) -> bytes:
    """``text`` spoken by the Mac, as the 16 kHz mono WAV the page sends."""
    with tempfile.TemporaryDirectory() as tmp:
        aiff, wav = Path(tmp) / "q.aiff", Path(tmp) / "q.wav"
        subprocess.run(["say", "-o", str(aiff), text], check=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
                        str(aiff), str(wav)], check=True)
        return wav.read_bytes()


def words(text: str) -> set[str]:
    return {w.strip(".,!?").lower() for w in text.split()}


def main() -> None:
    speech = mac_speech_from_env()
    if speech is None:
        print("Voice is off: install whisper.cpp and its model (admin reference: Voice).")
        return
    said = "Why do volcanoes erupt? I saw one in a book and it had red lava."
    got = speech.transcribe(clip(said))
    print(said, "→", got)
    heard_share = len(words(said) & words(got)) / len(words(said))
    question = speech.transcribe(clip("What do sharks eat?"))
    answer = "".join(ClaudeCodeChat().stream(system_prompt("", "supervised"),
                                             [Turn("user", question)]))
    print(question, "→", answer)
    results = [
        (f"a spoken sentence comes back ({heard_share:.0%} of words)", heard_share >= 0.8),
        ("a spoken question gets a short supervised answer", len(answer.split()) <= 60),
    ]
    for name, ok in results:
        print("PASS" if ok else "FAIL", name)


if __name__ == "__main__":
    main()
