"""The backend's tiers, read from the imports (docs/BACKEND_BOUNDARIES_PLAN.md).

``common`` knows nothing about the model or the API, ``engine`` is the domain and knows nothing about
HTTP, and ``management`` and ``consumer`` are the two API tiers, which never import each other. Every
module imports at module level, never another module's private names, and no two modules import each
other, directly or around a longer cycle.

Records, relations and attribute values, live and in a change set, are added and removed only by
the write unit (``engine/records/writes.py``): no other module constructs one of those rows or
names its table in a Core insert, update or delete.
"""

import ast
from collections import defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"

# Which app modules a tier may import, by module prefix. A module belongs to the longest prefix that
# names it.
ALLOWED: dict[str, tuple[str, ...]] = {
    "app.errors": (),
    "app.config": (),
    "app.db": ("app.config",),
    "app.common": ("app.common", "app.errors", "app.config"),
    "app.models.schema": ("app.common",),
    "app.models": ("app.common", "app.models", "app.config"),
    "app.engine": ("app.common", "app.models", "app.errors", "app.db", "app.config", "app.engine"),
    "app.management": (
        "app.common",
        "app.models",
        "app.errors",
        "app.db",
        "app.config",
        "app.engine",
        "app.management",
    ),
    "app.consumer": (
        "app.common",
        "app.models",
        "app.errors",
        "app.db",
        "app.config",
        "app.engine",
        "app.consumer",
    ),
    "app.migrations": ("app.common", "app.models", "app.engine", "app.db", "app.config"),
    "app.cli": ("app.common", "app.models", "app.engine", "app.db", "app.config", "app.errors"),
    "app.main": ("app",),
}
# Third-party packages that tie a module to HTTP; only the API tiers and the app factory use them.
WEB = ("fastapi", "starlette")
WEB_ALLOWED = ("app.management", "app.consumer", "app.main")
# Inside the engine: only the API tiers start a multi-record operation.
ENGINE_RULES: tuple[tuple[str, str], ...] = (
    ("app.engine", "app.engine.operations"),
)

# The rows of the record graph, and the one module that writes them.
ROW_CLASSES = {"RdmObject", "ObjectRelation", "AttributeValue", "ChangeSetObject", "ChangeSetRelation"}
ROW_WRITER = "app.engine.records.writes"
# ``session.delete`` elsewhere, and what it deletes instead of a record-graph row.
SESSION_DELETES = {
    "app.engine.change_sets.lifecycle": "discarding a change set deletes the change set row",
}

# Violations present when a rule was introduced, each removed by the package it names. An entry
# that no longer occurs fails the test, so the list only shrinks.
ALLOWLIST: set[str] = set()


def _modules() -> dict[str, Path]:
    found = {}
    for path in APP.rglob("*.py"):
        parts = list(path.relative_to(APP.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        found[".".join(parts)] = path
    return found


MODULES = _modules()


def _package(module: str) -> str:
    return module if MODULES[module].name == "__init__.py" else module.rsplit(".", 1)[0]


def _resolve(module: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    parts = _package(module).split(".")
    if node.level > 1:
        parts = parts[: len(parts) - (node.level - 1)]
    return ".".join(parts + ([node.module] if node.module else []))


def _tier(module: str, table) -> str | None:
    matches = [key for key in table if module == key or module.startswith(key + ".")]
    return max(matches, key=len) if matches else None


def _within(module: str, prefixes) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


def _scan():
    """Every app import as (importer, target module, imported name or None, at module level)."""
    imports = []
    for module, path in MODULES.items():
        tree = ast.parse(path.read_text())
        top = {id(node) for node in tree.body}
        # An import under ``if TYPE_CHECKING:`` or ``try:`` at module level is still module level.
        for node in tree.body:
            if isinstance(node, (ast.If, ast.Try)):
                top.update(id(child) for child in ast.walk(node))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                base = _resolve(module, node)
                for alias in node.names:
                    target = f"{base}.{alias.name}"
                    if target in MODULES:
                        imports.append((module, target, None, id(node) in top))
                    else:
                        imports.append((module, base, alias.name, id(node) in top))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((module, alias.name, None, id(node) in top))
    return imports


def _violations() -> set[str]:
    found = set()
    graph = defaultdict(set)
    for importer, target, name, top in _scan():
        is_app = target == "app" or target.startswith("app.")
        if not is_app:
            if target.split(".")[0] in WEB and not _within(importer, WEB_ALLOWED):
                found.add(f"web: {importer} -> {target}")
            continue
        if target not in MODULES:
            continue
        tier = _tier(importer, ALLOWED)
        if tier is not None and not _within(target, ALLOWED[tier]) and target != importer:
            found.add(f"tier: {importer} -> {target}")
        for scope, forbidden in ENGINE_RULES:
            if (
                _within(importer, (scope,))
                and _within(target, (forbidden,))
                and not _within(importer, (forbidden,))
            ):
                found.add(f"engine: {importer} -> {target}")
        if name is not None and name.startswith("_") and not name.startswith("__"):
            found.add(f"private: {importer} -> {target}.{name}")
        if not top:
            found.add(f"deferred: {importer} -> {target}")
        if target != importer and not _within(importer, ("app.main",)):
            graph[importer].add(target)
    for cycle in _cycles(graph):
        found.add("cycle: " + " -> ".join(cycle))
    return found | _row_writes()


def _row_writes() -> set[str]:
    found = set()
    for module, path in MODULES.items():
        if module == ROW_WRITER or module.startswith("app.migrations"):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in ROW_CLASSES:
                found.add(f"rows: {module} constructs {func.id}")
            if (
                isinstance(func, ast.Name)
                and func.id in {"insert", "update", "delete"}
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in ROW_CLASSES
            ):
                found.add(f"rows: {module} runs {func.id}({node.args[0].id})")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "delete"
                and isinstance(func.value, ast.Name)
                and func.value.id == "session"
                and module not in SESSION_DELETES
            ):
                found.add(f"rows: {module} calls session.delete")
    return found


def _cycles(graph) -> list[list[str]]:
    """Strongly connected components with more than one module, each listed from its first member."""
    index, low, stack, on_stack, result = {}, {}, [], set(), []
    counter = [0]

    def visit(node: str) -> None:
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for succ in sorted(graph.get(node, ())):
            if succ not in index:
                visit(succ)
                low[node] = min(low[node], low[succ])
            elif succ in on_stack:
                low[node] = min(low[node], index[succ])
        if low[node] == index[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.discard(item)
                component.append(item)
                if item == node:
                    break
            if len(component) > 1:
                result.append(sorted(component))

    for node in sorted(graph):
        if node not in index:
            visit(node)
    return result


def test_tiers_hold():
    found = _violations()
    new = sorted(found - ALLOWLIST)
    assert not new, "Boundary violations:\n" + "\n".join(new)


def test_allowlist_only_shrinks():
    stale = sorted(ALLOWLIST - _violations())
    assert not stale, "Remove these entries from ALLOWLIST, they no longer occur:\n" + "\n".join(stale)


# SQL that only another database understands (0.9.0-alpha.1 PG2, PG-D2).
_OTHER_DIALECT_SQL = ("BEGIN IMMEDIATE", "PRAGMA", "INDEXED BY", "json_each", "json_type", "fts5")


def _dialect_terms() -> set[str]:
    """Code in ``app/`` that names a database dialect or branches on one: an identifier, attribute,
    keyword or import naming SQLite, a ``dialect`` attribute read, or SQL of another database.
    Prose (comments, docstrings, an operator message refusing a SQLite URL) is not code."""
    found = set()
    for module, path in _modules().items():
        for node in ast.walk(ast.parse(path.read_text(), str(path))):
            names: list[str] = []
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
                if node.attr == "dialect":
                    found.add(f"{module}:{node.lineno} reads .dialect")
            elif isinstance(node, ast.keyword) and node.arg:
                names.append(node.arg)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for term in _OTHER_DIALECT_SQL:
                    if term in node.value:
                        found.add(f"{module}:{node.lineno} SQL {term!r}")
            for name in names:
                if "sqlite" in name.lower():
                    found.add(f"{module}:{node.lineno} names {name}")
    return found


def test_no_dialect_branch_or_other_database_sql_remains():
    found = sorted(_dialect_terms())
    assert not found, "PostgreSQL is the only database:\n" + "\n".join(found)
