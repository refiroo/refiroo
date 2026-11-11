"""``management/docs_site.py``: the documentation served at ``/docs`` (0.13 DOC1).

A built guide is served from its folder with headers that keep a page inside the engine. Where no
build exists the engine's application still builds and ``/docs`` says how to build the guide.
"""

import base64
import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.management import guide_site


def _built(directory):
    (directory / "how").mkdir(parents=True)
    (directory / "index.html").write_text("<title>start</title>")
    (directory / "how" / "index.html").write_text("<title>how</title>")
    (directory / "404.html").write_text("<title>missing</title>")
    return directory


def _served(monkeypatch, candidates):
    monkeypatch.setattr(guide_site, "BUILT_GUIDE_CANDIDATES", tuple(candidates))
    application = FastAPI(docs_url=None, redoc_url=None)
    guide_site.mount_guide(application)
    return TestClient(application)


def test_a_built_guide_is_served_with_headers_that_keep_it_inside_the_engine(monkeypatch, tmp_path):
    client = _served(monkeypatch, [tmp_path / "absent", _built(tmp_path / "built")])
    page = client.get("/docs/how/")
    assert page.status_code == 200 and "<title>how</title>" in page.text
    policy = page.headers["content-security-policy"]
    assert "default-src 'none'" in policy and "connect-src 'self'" in policy
    assert "font-src 'self'" in policy and "frame-ancestors 'none'" in policy
    assert page.headers["x-content-type-options"] == "nosniff"
    # The folder's address without its slash goes to the address with it, as does /docs itself.
    moved = client.get("/docs/how", follow_redirects=False)
    assert moved.status_code in (301, 307) and moved.headers["location"].endswith("/docs/how/")
    assert client.get("/docs", follow_redirects=False).headers["location"].endswith("/docs/")
    assert client.get("/docs/").status_code == 200
    # A path that is not in the build answers the build's own 404 page, and nothing outside the
    # folder is reachable.
    missing = client.get("/docs/nothing/")
    assert missing.status_code == 404 and "<title>missing</title>" in missing.text
    assert client.get("/docs/../../etc/passwd").status_code == 404


def test_the_api_reference_is_not_shadowed_by_the_documentation(monkeypatch, tmp_path):
    monkeypatch.setattr(guide_site, "BUILT_GUIDE_CANDIDATES", (_built(tmp_path / "built"),))
    client = TestClient(create_app())
    for path in ("/docs/api", "/docs/api/"):
        page = client.get(path)
        assert page.status_code == 200 and "refiroo API reference" in page.text, path
    assert client.get("/docs/api/scalar/standalone.js").status_code == 200
    assert client.get("/docs/how/").status_code == 200


def test_without_a_build_the_guide_says_how_to_build_it(monkeypatch, tmp_path):
    client = _served(monkeypatch, [tmp_path / "absent"])
    for path in ("/docs", "/docs/", "/docs/how/refiroo-works/"):
        page = client.get(path)
        assert page.status_code == 404
        assert "npm run build" in page.text
        assert "default-src 'none'" in page.headers["content-security-policy"]


def test_the_engine_starts_whether_or_not_the_guide_is_built(monkeypatch, tmp_path):
    names = {}
    for label, candidates in (
        ("absent", [tmp_path / "absent"]),
        ("built", [_built(tmp_path / "b")]),
    ):
        monkeypatch.setattr(guide_site, "BUILT_GUIDE_CANDIDATES", tuple(candidates))
        names[label] = {getattr(route, "name", None) for route in create_app().routes}
    assert "guide" in names["built"] and "guide" not in names["absent"]


def test_a_built_page_names_its_own_inline_scripts_by_hash_and_allows_no_other(
    monkeypatch, tmp_path
):
    built = _built(tmp_path / "built")
    (built / "index.html").write_text(
        '<script>window.a = 1;</script><script type="module">window.b = 2;</script>'
        '<script src="/docs/_astro/x.js"></script>'
    )
    client = _served(monkeypatch, [built])

    policy = client.get("/docs/").headers["content-security-policy"]

    for text in (b"window.a = 1;", b"window.b = 2;"):
        digest = base64.b64encode(hashlib.sha256(text).digest()).decode()
        assert f"'sha256-{digest}'" in policy
    assert policy.count("sha256-") == 2 and "unsafe-inline" not in policy.split("style-src")[0]
    # A page without inline scripts allows none.
    assert "sha256-" not in client.get("/docs/how/").headers["content-security-policy"]
