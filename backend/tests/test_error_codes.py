"""Every error code the engine writes is upper case (Base 0.9 T1b, D45).

Codes are written where a refusal or a finding is raised: the code argument of ``api_error`` and
``ApiError``, of ``ModelReferenceError``, a validator's ``_fail`` and the compatibility check's
``_append_counted``, a ``code=`` keyword, the ``code`` and ``reason`` of an error, diagnostic or
outcome dict, and the ``reason`` values an item outcome declares. The check reads the source, as
``test_boundaries`` does, so a new lower-case code fails here instead of reaching a client. A
``reason`` in camel case is not a code: it names why a candidate or an input applies (D42).
"""

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
CODE = re.compile(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*")
SNAKE = re.compile(r"[a-z][a-z0-9]*(_[a-z0-9]+)+")
# The position of the code among a call's arguments.
CODE_ARGUMENT = {"api_error": 1, "ApiError": 1, "ModelReferenceError": 0, "_fail": 0, "_append_counted": 2}


def _name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    return function.attr if isinstance(function, ast.Attribute) else ""


def _text(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _codes(tree: ast.AST) -> list[tuple[ast.AST, str]]:
    """``(node, value)`` for every string literal at a code position."""
    found: list[tuple[ast.AST, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            index = CODE_ARGUMENT.get(_name(node))
            if index is not None and len(node.args) > index:
                found.append((node.args[index], _text(node.args[index])))
            found += [(item.value, _text(item.value)) for item in node.keywords if item.arg == "code"]
        elif isinstance(node, ast.Dict):
            found += [
                (value, _text(value))
                for key, value in zip(node.keys, node.values)
                if key is not None and _text(key) in ("code", "reason")
            ]
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "reason":
            found += [(item, _text(item)) for item in ast.walk(node.annotation)]
    return [(node, value) for node, value in found if value is not None]


def test_every_error_code_in_the_backend_is_upper_case():
    offending = []
    for path in sorted(APP.rglob("*.py")):
        if "migrations" in path.parts:
            continue
        for node, value in _codes(ast.parse(path.read_text())):
            if not CODE.fullmatch(value) and (SNAKE.fullmatch(value) or "_" in value):
                offending.append(f"{path.relative_to(APP.parent)}:{node.lineno}: {value!r}")
    assert offending == [], "error codes not in upper case:\n" + "\n".join(offending)


def test_the_check_finds_a_lower_case_code():
    tree = ast.parse(
        'api_error(404, "thing_not_found", "m")\n'
        'errors.append({"code": "THING_GONE"})\n'
        'outcome = {"reason": "batch_rolled_back"}\n'
    )
    assert {value for _node, value in _codes(tree)} == {
        "thing_not_found",
        "THING_GONE",
        "batch_rolled_back",
    }
