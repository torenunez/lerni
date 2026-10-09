"""Every code and test file is described in docs/code-manifest.md."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_code_file_is_in_the_manifest():
    manifest = (ROOT / "docs" / "code-manifest.md").read_text(encoding="utf-8")
    patterns = ("src/**/*.py", "scripts/*.py", "tests/**/*.py")
    files = [f for p in patterns for f in sorted(ROOT.glob(p)) if "__pycache__" not in f.parts]
    names = [str(f.relative_to(ROOT)) for f in files]
    missing = [n for n in names if f"`{n}`" not in manifest]
    assert not missing, f"add these to docs/code-manifest.md: {missing}"
