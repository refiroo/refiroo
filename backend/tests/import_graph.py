"""How the harness reads imports: the app's modules and the tests' own (H4b, TS4).

One reading for ``test_boundaries.py`` (the tiers) and ``affected.py`` (the tests a change needs).
A module is named by its dotted path: ``app.engine.records.rules`` for the app; for the tests the
file's stem (``seeds``, ``scenario``: ``tests/`` and ``tests/journeys/`` are on the import path) and
``unit.engine.records.test_rules`` for a file under ``tests/unit/``. ``conftest.py`` files are not
modules of the graph (``affected.RULES`` decides what one selects).
"""

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent
BACKEND = TESTS.parent
APP = BACKEND / "app"


def modules() -> dict[str, Path]:
    """Every module of the app, by dotted name (a package by its ``__init__.py``)."""
    found = {}
    for path in APP.rglob("*.py"):
        parts = list(path.relative_to(APP.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        found[".".join(parts)] = path
    return found


def test_side_modules() -> dict[str, Path]:
    """Every harness module and test module, by the name the tests import it under."""
    found = {}
    for path in [*TESTS.glob("*.py"), *(TESTS / "journeys").glob("*.py")]:
        if path.name not in {"conftest.py", "__init__.py"}:
            found[path.stem] = path
    for path in (TESTS / "unit").rglob("*.py"):
        if path.name != "conftest.py":
            parts = list(path.relative_to(TESTS).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            found[".".join(parts)] = path
    return found


def package(known: dict[str, Path], module: str) -> str:
    return module if known[module].name == "__init__.py" else module.rsplit(".", 1)[0]


def resolve(known: dict[str, Path], module: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    parts = package(known, module).split(".")
    if node.level > 1:
        parts = parts[: len(parts) - (node.level - 1)]
    return ".".join(parts + ([node.module] if node.module else []))


def scan(known: dict[str, Path]) -> list[tuple[str, str, str | None, bool]]:
    """Every import of the modules in ``known`` as (importer, target module, imported name or
    None, at module level)."""
    imports = []
    for module, path in known.items():
        tree = ast.parse(path.read_text())
        top = {id(node) for node in tree.body}
        # An import under ``if TYPE_CHECKING:`` or ``try:`` at module level is still module level.
        for node in tree.body:
            if isinstance(node, (ast.If, ast.Try)):
                top.update(id(child) for child in ast.walk(node))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                base = resolve(known, module, node)
                for alias in node.names:
                    target = f"{base}.{alias.name}"
                    if target in known:
                        imports.append((module, target, None, id(node) in top))
                    else:
                        imports.append((module, base, alias.name, id(node) in top))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((module, alias.name, None, id(node) in top))
    return imports
