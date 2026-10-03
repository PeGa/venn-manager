"""The core never imports a framework (AGENTS.md § Hexagonal architecture)."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
CORE = [
    *sorted((APP / "domain").glob("*.py")),
    *sorted((APP / "application").glob("*.py")),
    APP / "ports.py",
]
FORBIDDEN = (
    "fastapi",
    "starlette",
    "pydantic",
    "sqlalchemy",
    "alembic",
    "argon2",
    "app.adapters",
)


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", CORE, ids=lambda p: str(p.relative_to(APP)))
def test_core_module_imports_no_framework_or_adapter(path: Path) -> None:
    offending = {
        name
        for name in _imports(path)
        if name.split(".")[0] in FORBIDDEN or name.startswith("app.adapters")
    }
    assert offending == set()
