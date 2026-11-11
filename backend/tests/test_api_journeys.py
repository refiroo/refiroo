"""The API inventory (docs/testing/API_JOURNEYS.md) names everything the API offers (H4b).

The API is the product: every operation, query parameter, header, error code and setting serves a
journey. A new route, parameter, code or setting is added to the inventory with its journeys, or
this check names it. Every journey ID the inventory cites must exist in USER_JOURNEYS.md.
"""

import re

import layout
import pytest

from app.config import reload_settings
from app.main import create_app

INVENTORY = layout.BACKEND.parent / "docs" / "testing" / "API_JOURNEYS.md"
_OPERATION = re.compile(r"`((?:[A-Z]+/)*[A-Z]+) (/[^`\s]*)`")
_PLACEHOLDER = re.compile(r"\{[^}]*\}")
# An error code as the backend raises it: `ApiError(409, "code"`, `api_error(422, "code"`, a
# `code="…"` argument, or a refusal table entry `"code": (422, …`.
_RAISED = (
    re.compile(
        r"(?:[Ee]rror|[Rr]efusal|_refuse)\(\s*(?:status_code=)?\d{3}\s*,\s*(?:code=)?[\"']([A-Z][A-Z_]+)[\"']"
    ),
    re.compile(r"\bcode=[\"']([A-Z][A-Z_]+)[\"']"),
    re.compile(r"^\s*[\"']([A-Z][A-Z_]+)[\"']\s*:\s*\(\s*\d{3}", re.MULTILINE),
)
_SETTING = re.compile(r"""(?:env\.get|_positive)\(\s*(?:env,\s*)?["']([A-Z][A-Z_]+)["']""")


@pytest.fixture(scope="module")
def inventory() -> str:
    return INVENTORY.read_text()


@pytest.fixture(scope="module")
def openapi(monkeypatch_module) -> dict:
    monkeypatch_module.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    document = create_app().openapi()
    monkeypatch_module.undo()
    reload_settings()
    return document


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as patch:
        yield patch


def _documented_operations(text: str) -> set[tuple[str, str]]:
    found = set()
    for methods, path in _OPERATION.findall(text):
        for method in methods.split("/"):
            found.add((method, _PLACEHOLDER.sub("{}", path)))
    return found


def test_every_operation_is_listed(openapi, inventory):
    documented = _documented_operations(inventory)
    missing = sorted(
        f"{method.upper()} {path}"
        for path, operations in openapi["paths"].items()
        for method in operations
        if (method.upper(), _PLACEHOLDER.sub("{}", path.removeprefix("/api/v1"))) not in documented
    )
    assert not missing, "Add to API_JOURNEYS.md, with their journeys:\n" + "\n".join(missing)


def test_every_parameter_and_header_is_listed(openapi, inventory):
    names = {
        parameter["name"]
        for operations in openapi["paths"].values()
        for operation in operations.values()
        for parameter in operation.get("parameters", [])
        if parameter["in"] in ("query", "header")
    }
    # The per-type list's field filters are one documented family.
    missing = sorted(name for name in names if f"`{name}`" not in inventory and "<" not in name)
    assert not missing, "Add to API_JOURNEYS.md, with their journeys:\n" + "\n".join(missing)


def raised_codes() -> set[str]:
    codes = set()
    for path in layout.APP.rglob("*.py"):
        source = path.read_text()
        for pattern in _RAISED:
            codes.update(pattern.findall(source))
    return codes


def test_every_error_code_is_listed(inventory):
    codes = raised_codes()
    assert len(codes) > 100  # the extraction still finds the backend's codes
    missing = sorted(code for code in codes if f"`{code}`" not in inventory)
    assert not missing, "Add to API_JOURNEYS.md's error codes, with their journeys:\n" + "\n".join(
        missing
    )


def test_every_setting_is_listed(inventory):
    settings = set(_SETTING.findall((layout.APP / "config.py").read_text()))
    assert "DATABASE_URL" in settings
    missing = sorted(name for name in settings if name not in inventory)
    assert not missing, "Add to API_JOURNEYS.md's operator surface:\n" + "\n".join(missing)


def test_every_cited_journey_exists(inventory):
    cited = set(re.findall(r"\bJ\d\d(?:\.\d+)?\b", inventory))
    assert not layout.unknown_journeys(tuple(cited))
