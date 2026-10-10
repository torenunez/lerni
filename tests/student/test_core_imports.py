"""The student core imports only the standard library and itself (ARCHITECTURE boundary 7)."""

import ast
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "src" / "lerni" / "student"
CORE_MODULES = [
    "__init__.py", "canonical.py", "catalog.py", "domain.py", "engine.py",
    "plans.py", "plan_import.py", "jsonfiles.py", "students.py", "signin.py", "conversation.py",
    "interests.py", "tagging.py", "logs.py", "upload.py",
    "feedback.py",
]


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module)
    return roots


def test_core_modules_import_only_stdlib_and_lerni_student():
    for name in CORE_MODULES:
        for module in imported_roots(CORE / name):
            top = module.split(".")[0]
            allowed = top in sys.stdlib_module_names or module.startswith("lerni.student")
            assert allowed, f"{name} imports {module}"
            assert not module.startswith("lerni.student.web"), f"{name} imports the screens"
