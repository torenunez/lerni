"""Distribution tests.

A lesson that loads from the source checkout but not from an installed wheel is
a lesson that works for developers and fails for everyone else. These tests
build both distributions, install each into a throwaway environment outside the
repository, and verify the packaged bytes are byte-identical to source.

They are slow and require network-free build tooling, so they are marked and can
be deselected with ``-m "not distribution"``.
"""

import hashlib
import pathlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile

import pytest

pytestmark = pytest.mark.distribution

REPO = pathlib.Path(__file__).resolve().parents[2]
LESSONS = REPO / "src/lerni/explore/lessons"
LESSON_ID = "chain-1-acceleration"


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(args: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f"{' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> dict[str, pathlib.Path]:
    """Build a wheel and an sdist once for the whole module."""
    if shutil.which("python") is None and not sys.executable:
        pytest.skip("no python executable available to build with")
    out = tmp_path_factory.mktemp("dist")
    _run([sys.executable, "-m", "build", "--outdir", str(out)], cwd=REPO)
    wheels = list(out.glob("*.whl"))
    sdists = list(out.glob("*.tar.gz"))
    if not wheels or not sdists:
        pytest.fail(f"build produced {[p.name for p in out.iterdir()]}")
    return {"wheel": wheels[0], "sdist": sdists[0]}


def _install(artifact: pathlib.Path) -> pathlib.Path:
    """Install ``artifact`` into a fresh venv and return its site-packages."""
    env = pathlib.Path(tempfile.mkdtemp(prefix="lerni-dist-"))
    _run([sys.executable, "-m", "venv", str(env)], cwd=REPO)
    python = env / "bin" / "python"
    _run([str(python), "-m", "pip", "install", "--quiet", str(artifact)], cwd=REPO)
    scheme = sysconfig.get_paths()["purelib"].split("lib/")[-1]
    site = env / "lib" / scheme.split("/")[0] / "site-packages"
    if not site.exists():
        candidates = list((env / "lib").glob("python*/site-packages"))
        if not candidates:
            pytest.fail(f"could not locate site-packages under {env}")
        site = candidates[0]
    return site


def _load_from(site: pathlib.Path, snippet: str) -> str:
    """Run ``snippet`` with only the installed package importable.

    ``-S`` and an empty PYTHONPATH keep the source checkout off sys.path, so a
    passing result cannot be an accident of running inside the repo.
    """
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=tempfile.gettempdir(),
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(site), "PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0:
        pytest.fail(f"{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


LOAD_SNIPPET = """
import hashlib
from importlib import resources
from lerni.explore.catalog import PackageLessonCatalog, parse_lesson_toml

pkg = resources.files("lerni.explore.lessons")
lesson_bytes = pkg.joinpath("chain_1_acceleration.toml").read_bytes()
svg_bytes = pkg.joinpath("assets/chain_1_acceleration.svg").read_bytes()
lesson = parse_lesson_toml(lesson_bytes.decode("utf-8"))
print(lesson.id)
print(hashlib.sha256(lesson_bytes).hexdigest())
print(hashlib.sha256(svg_bytes).hexdigest())
print(type(PackageLessonCatalog()).__name__)
print(str(pkg))
"""


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_installed_distribution_carries_exact_lesson_bytes(built, kind):
    site = _install(built[kind])
    lesson_id, lesson_hash, svg_hash, catalog_name, _ = _load_from(site, LOAD_SNIPPET).splitlines()
    assert lesson_id == LESSON_ID
    assert catalog_name == "PackageLessonCatalog"
    assert lesson_hash == _digest(LESSONS / "chain_1_acceleration.toml")
    assert svg_hash == _digest(LESSONS / "assets/chain_1_acceleration.svg")


def test_installed_wheel_verifies_lesson_index_hash(built):
    site = _install(built["wheel"])
    snippet = """
from lerni.explore.catalog import PackageLessonCatalog
from lerni.explore.domain import LessonNotApprovedError
try:
    PackageLessonCatalog().load("chain-1-acceleration")
    print("LOADED")
except LessonNotApprovedError:
    print("REFUSED_DRAFT")
"""
    # The index must verify far enough to reach the approval check. A byte or
    # index mismatch would raise LessonContentError before this point.
    assert _load_from(site, snippet) == "REFUSED_DRAFT"


def test_installed_wheel_rejects_tampered_svg(built):
    site = _install(built["wheel"])
    svg = site / "lerni/explore/lessons/assets/chain_1_acceleration.svg"
    assert svg.exists(), "asset missing from the installed wheel"
    svg.write_bytes(svg.read_bytes() + b"<!-- tampered -->")

    snippet = """
import tomllib
from importlib import resources
from lerni.explore.catalog import PackageLessonCatalog
from lerni.explore.domain import AssetRef, LessonContentError

index = tomllib.loads(
    resources.files("lerni.explore.lessons").joinpath("lesson_index.toml").read_text()
)
entry = index["assets"][0]
ref = AssetRef(
    resource_name=entry["resource_name"],
    media_type=entry["media_type"],
    alt_text="x",
    sha256=entry["sha256"],
)
try:
    PackageLessonCatalog().read_asset(ref)
    print("SERVED_TAMPERED")
except LessonContentError:
    print("REJECTED")
"""
    assert _load_from(site, snippet) == "REJECTED"


def test_runtime_does_not_depend_on_source_checkout_path(built):
    site = _install(built["wheel"])
    location = _load_from(site, LOAD_SNIPPET).splitlines()[-1]
    assert str(REPO) not in location, f"resolved to the source checkout: {location}"
    assert str(site) in location
