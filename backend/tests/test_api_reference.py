"""0.9 V1: the Scalar API reference page at /docs, its bundled script and the CDN setting."""

import base64
import hashlib
import json
import re

import pytest
from harness_identity import TestClient

from app.config import reload_settings
from app.main import app, create_app
from app.management.reference import (
    BUNDLED_SCRIPT_PATH,
    OFFLINE_OPTIONS,
    SCALAR_CDN_URL,
    SCALAR_INTEGRITY,
    SCALAR_SCRIPT,
    SCALAR_VERSION,
)


def _configuration(page: str) -> dict:
    match = re.search(r'Scalar\.createApiReference\("#rdm-api-reference", (\{.*\})\);', page)
    assert match, page
    return json.loads(match.group(1))


def _client(monkeypatch: pytest.MonkeyPatch, script: str | None) -> TestClient:
    if script is None:
        monkeypatch.delenv("RDM_API_REFERENCE_SCRIPT", raising=False)
    else:
        monkeypatch.setenv("RDM_API_REFERENCE_SCRIPT", script)
    try:
        return TestClient(create_app())
    finally:
        monkeypatch.undo()
        reload_settings()


def test_docs_serves_the_bundled_script_with_the_management_source(monkeypatch):
    client = _client(monkeypatch, None)

    page = client.get("/docs")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert f'<script src="{BUNDLED_SCRIPT_PATH}"></script>' in page.text
    # Nothing on the page names another host: the script, the source and the options are local.
    assert "http://" not in page.text and "https://" not in page.text
    configuration = _configuration(page.text)
    # The management API comes first and is the default; any other source is a consumer API of the
    # active release, which depends on what ran before on this database (none on a fresh one).
    assert configuration["sources"][0] == {
        "title": "Management API",
        "slug": "management",
        "url": "/openapi.json",
        "default": True,
    }
    assert all(item["slug"].startswith("consumer-") for item in configuration["sources"][1:])
    assert OFFLINE_OPTIONS == {
        "withDefaultFonts": False,
        "telemetry": False,
        "agent": {"disabled": True},
        "mcp": {"disabled": True},
        "showDeveloperTools": "never",
        "hideClientButton": True,
    }
    assert OFFLINE_OPTIONS.items() <= configuration.items()
    # Scalar mounts an unconfigured instance on an element with this id by itself.
    assert 'id="api-reference"' not in page.text

    script = client.get(BUNDLED_SCRIPT_PATH)
    assert script.status_code == 200
    assert script.headers["content-type"].startswith("text/javascript")
    assert "createApiReference" in script.text
    # The integrity the CDN setting relies on is the bundled file's own, so both load one version.
    digest = base64.b64encode(hashlib.sha384(script.content).digest()).decode()
    assert f"sha384-{digest}" == SCALAR_INTEGRITY
    assert script.content == SCALAR_SCRIPT.read_bytes()
    assert (SCALAR_SCRIPT.parent / "LICENSE").read_text().startswith("MIT License")


def test_the_cdn_setting_loads_the_pinned_version_under_its_integrity(monkeypatch):
    client = _client(monkeypatch, " CDN ")

    page = client.get("/docs").text
    assert SCALAR_CDN_URL.endswith(f"@scalar/api-reference@{SCALAR_VERSION}/dist/browser/standalone.js")
    assert (
        f'<script src="{SCALAR_CDN_URL}" integrity="{SCALAR_INTEGRITY}" crossorigin="anonymous">'
        in page
    )
    assert BUNDLED_SCRIPT_PATH not in page
    assert _configuration(page)["sources"][0]["url"] == "/openapi.json"


def test_an_unknown_script_setting_refuses_to_start(monkeypatch):
    monkeypatch.setenv("RDM_API_REFERENCE_SCRIPT", "unpkg")
    with pytest.raises(RuntimeError, match="RDM_API_REFERENCE_SCRIPT must be one of bundled, cdn"):
        create_app()
    monkeypatch.undo()
    reload_settings()


def test_the_page_follows_a_root_path(monkeypatch):
    monkeypatch.delenv("RDM_API_REFERENCE_SCRIPT", raising=False)
    client = TestClient(create_app(), root_path="/rdm")
    reload_settings()

    page = client.get("/docs").text
    assert f'<script src="/rdm{BUNDLED_SCRIPT_PATH}"></script>' in page
    assert _configuration(page)["sources"][0]["url"] == "/rdm/openapi.json"


def test_swagger_ui_and_redoc_are_gone_and_the_page_is_outside_the_openapi_document():
    client = TestClient(app)

    for path in ("/redoc", "/docs/oauth2-redirect"):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json()["error"]["code"] == "HTTP_ERROR"
    paths = app.openapi()["paths"]
    assert not [path for path in paths if path.startswith("/docs")]
