"""0.9 V1: the Scalar API reference page at /docs/api, its bundled script and the CDN setting."""

import base64
import hashlib
import json
import re
from pathlib import Path

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
    StaticSite,
    page_headers,
    render_page,
    with_meta_policy,
)
from app.management.reference.static_site import load_api_theme


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

    page = client.get("/docs/api")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert f'<script src="{BUNDLED_SCRIPT_PATH}"></script>' in page.text
    # Nothing on the page names another host: the script, the source and the options are local.
    assert "http://" not in page.text and "https://" not in page.text
    # The page links to the documentation the engine serves beside it (0.13 DOC1).
    assert 'href="/docs/"' in page.text and 'href="/docs/api/" aria-current="page"' in page.text
    # The logo leads to the application, and Scalar's own colour toggle is hidden for the header's (HD).
    assert 'class="rdm-mark" href="/"' in page.text
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
        "hideDarkModeToggle": True,
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


def _directives(policy: str) -> dict[str, list[str]]:
    parts = [part.strip().split() for part in policy.split(";") if part.strip()]
    return {part[0]: part[1:] for part in parts}


def test_the_page_runs_only_the_scripts_it_ships_and_cannot_be_framed(monkeypatch):
    """The page can mint a management token from the session cookie, so a script that got into it
    (from a description a model author wrote) must not run: scripts are the bundled file and the
    page's own, named by hash; nothing is evaluated; the page reaches only the engine (0.12
    E1, C10)."""
    client = _client(monkeypatch, None)

    response = client.get("/docs/api")
    policy = _directives(response.headers["content-security-policy"])
    scripts = re.findall(r"<script>(.*?)</script>", response.text, flags=re.DOTALL)
    assert len(scripts) == 4  # theme, the reference, the console sign-in, the theme wiring
    hashes = [
        "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"
        for text in scripts
    ]
    assert policy["script-src"] == ["'self'", *hashes]
    assert policy["connect-src"] == ["'self'"]
    assert policy["object-src"] == ["'none'"] and policy["frame-ancestors"] == ["'none'"]
    assert policy["default-src"] == ["'none'"] and policy["base-uri"] == ["'none'"]
    assert response.headers["x-frame-options"] == "DENY"
    # The script-bearing sources are never opened up, whatever styles and images ask for.
    assert not any("unsafe" in word for word in policy["script-src"] + policy["connect-src"])


def test_the_cdn_setting_names_the_pinned_host_in_its_policy(monkeypatch):
    client = _client(monkeypatch, "cdn")

    policy = _directives(client.get("/docs/api").headers["content-security-policy"])
    assert "https://cdn.jsdelivr.net" in policy["script-src"]
    assert "'self'" in policy["script-src"]


def test_the_cdn_setting_loads_the_pinned_version_under_its_integrity(monkeypatch):
    client = _client(monkeypatch, " CDN ")

    page = client.get("/docs/api").text
    assert SCALAR_CDN_URL.endswith(
        f"@scalar/api-reference@{SCALAR_VERSION}/dist/browser/standalone.js"
    )
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

    page = client.get("/docs/api").text
    assert f'<script src="/rdm{BUNDLED_SCRIPT_PATH}"></script>' in page
    assert _configuration(page)["sources"][0]["url"] == "/rdm/openapi.json"


def test_swagger_ui_and_redoc_are_gone_and_the_page_is_outside_the_openapi_document():
    client = TestClient(app)

    response = client.get("/redoc")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    # The documentation site is mounted at /docs, so an address under it that is no page answers its 404.
    assert client.get("/docs/oauth2-redirect").status_code == 404
    paths = app.openapi()["paths"]
    assert not [path for path in paths if path.startswith("/docs")]


def test_the_header_is_the_shared_one_and_the_theme_is_the_applications_choice(monkeypatch):
    """HD: the page links the shared header stylesheet the engine serves (equal to the one the guide and
    the interface use), hides Scalar's toggle and drives its colour mode from ``rdm:theme:v1``."""
    client = _client(monkeypatch, None)

    page = client.get("/docs/api").text
    assert '<link rel="stylesheet" href="/brand/refiroo-header.css" />' in page
    assert _configuration(page)["hideDarkModeToggle"] is True
    assert "rdm:theme:v1" in page and "forceDarkModeState" in page and '"storage"' in page
    # TH: the colour theme is a second, independent key; Website purple sets data-scheme, Normal sets nothing.
    assert (
        "rdm:scheme:v1" in page
        and 'dataset.scheme = "purple"' in page
        and "theme.schemeKey" in page
    )
    css = client.get("/brand/refiroo-header.css")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    shared = (
        Path(__file__).resolve().parents[2] / "frontend" / "public" / "brand" / "refiroo-header.css"
    )
    assert css.content == shared.read_bytes()


def test_docs_page_carries_the_refiroo_mark_from_the_engine(monkeypatch):
    client = _client(monkeypatch, None)

    page = client.get("/docs/api")
    assert "<title>refiroo API reference</title>" in page.text
    assert "/brand/refiroo-mascot.png" in page.text and "/brand/favicon.png" in page.text
    for name in ("favicon.png", "refiroo-mascot.png", "refiroo-wordmark.png"):
        image = client.get(f"/brand/{name}")
        assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    assert client.get("/brand/secret.png").status_code == 404


def test_the_public_build_page_leads_home_flies_and_names_its_version():
    """DOC12 (E1 to E4): the static page's logo leads to the site's home, its script is under the build's
    base, it carries the version, the canonical address and the flight styles; an instance's page has none."""
    sources = [
        {"title": "Management API", "slug": "management", "url": "/docs/0.13/api/management.json"}
    ]
    site = StaticSite(base="/docs/0.13", site_url="https://refiroo.org", version="0.13", older=True)
    page = with_meta_policy("bundled", render_page("bundled", "", sources, static=site))

    assert 'href="/" aria-label="refiroo home"' in page
    assert '<script src="/docs/0.13/api/scalar/standalone.js">' in page
    assert '<link rel="canonical" href="https://refiroo.org/docs/0.13/api/" />' in page
    assert '<span class="rdm-version">v0.13</span>' in page
    assert 'Guide for 0.13 · <a href="/docs/">Latest version</a>' in page
    assert "view-transition-name: mascot" in page and "view-transition-name: terminal" in page
    assert "prefers-reduced-motion: no-preference" in page
    assert "--scalar-custom-header-height: 92px" in page
    # The policy still names every inline script by its hash.
    policy = page_headers("bundled", page)["Content-Security-Policy"]
    for text in re.findall(r"<script>(.*?)</script>", page, flags=re.DOTALL):
        digest = base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
        assert f"'sha256-{digest}'" in policy

    latest = render_page(
        "bundled", "", sources, static=StaticSite(site_url="https://refiroo.org", version="0.13")
    )
    assert "rdm-older" not in latest.replace(".rdm-older", "") and 'class="rdm-version"' in latest
    instance = render_page("bundled", "", sources)
    for text in ("view-transition", "rdm-version", "canonical"):
        assert text not in instance


def test_the_api_page_takes_a_hosts_theme_header(tmp_path):
    """DOC12 (PUBLIC_GUIDE_THEME): a host's ``api/`` folder replaces the refiroo header of the static page, its head
    elements are added, its files are written to ``theme/`` with the base path and version filled in, its inline script
    is named by hash in the policy, and Scalar leaves room for the header's own height. An instance's page is unchanged."""
    api = tmp_path / "api"
    (api / "theme").mkdir(parents=True)
    (api / "head.html").write_text('    <link rel="stylesheet" href="/__BASE__/theme/x.css">\n')
    (api / "header.html").write_text(
        '    <header class="host-nav">v__VERSION__</header><script>window.hostNav = 1;</script>\n'
    )
    (api / "theme" / "x.css").write_text('a { background: url("/__BASE__/theme/f.woff2"); }')
    (api / "theme" / "f.woff2").write_bytes(b"\x00__BASE__")
    out = tmp_path / "out"

    theme = load_api_theme(tmp_path, out, base="/docs/0.13", version="0.13")
    assert theme is not None and 'href="/docs/0.13/theme/x.css"' in theme.head
    assert (
        out / "theme" / "x.css"
    ).read_text() == 'a { background: url("/docs/0.13/theme/f.woff2"); }'
    assert (
        out / "theme" / "f.woff2"
    ).read_bytes() == b"\x00__BASE__"  # binary files are copied as they are
    assert load_api_theme(tmp_path / "none", out, base="/docs", version="") is None

    sources = [
        {"title": "Management API", "slug": "management", "url": "/docs/api/management.json"}
    ]
    page = with_meta_policy(
        "bundled",
        render_page("bundled", "", sources, static=StaticSite(version="0.13", theme=theme)),
    )
    assert '<header class="host-nav">v0.13</header>' in page
    assert 'href="/docs/0.13/theme/x.css"' in page
    assert 'class="rdm-header"' not in page.split("</style>", 1)[1]
    assert "--scalar-custom-header-height: calc(var(--rdm-header-h, 56px))" in page
    policy = page_headers("bundled", page)["Content-Security-Policy"]
    digest = base64.b64encode(hashlib.sha256(b"window.hostNav = 1;").digest()).decode()
    assert f"'sha256-{digest}'" in policy
    # Without a header picker the wiring still runs (the host's header toggles data-theme itself).
    assert "if (picker)" in page and 'attributeFilter: ["data-theme"]' in page
    # TH: a host's own look ignores the colour theme.
    assert "rdm:scheme:v1" not in page and "dataset.scheme" not in page

    plain = render_page("bundled", "", sources, static=StaticSite(version="0.13"))
    assert 'class="rdm-header"' in plain and "--scalar-custom-header-height: 56px" in plain
