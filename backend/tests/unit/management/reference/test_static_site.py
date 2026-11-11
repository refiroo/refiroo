"""HD: the API reference as a static page for the public site, written by ``static_site``."""

import base64
import hashlib
import json
import re
from html import unescape

from app.management.reference import StaticSite, render_page, static_site, with_meta_policy


def test_the_static_page_has_no_sign_in_and_covers_every_script_by_its_meta_policy():
    sources = [
        {"title": "Management API", "slug": "management", "url": "/docs/api/management.json"}
    ]
    page = with_meta_policy("bundled", render_page("bundled", "", sources, static=StaticSite()))

    assert "console-token" not in page and "rdm-api-reference" in page
    configuration = json.loads(
        re.search(r'createApiReference\("#rdm-api-reference", (\{.*\})\);', page).group(1)
    )
    assert configuration["hideTestRequestButton"] is True
    # The logo leads to the site's home (W4-D5); the API page is the current one.
    assert 'class="rdm-mark" href="/"' in page and 'href="/docs/api/" aria-current="page"' in page
    assert (
        'href="/docs/brand/refiroo-header.css"' in page and 'src="/docs/refiroo-mascot.png"' in page
    )
    policy = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', page).group(
        1
    )
    policy = unescape(policy)
    assert "frame-ancestors" not in policy
    for text in re.findall(r"<script>(.*?)</script>", page, flags=re.DOTALL):
        digest = base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
        assert f"'sha256-{digest}'" in policy


def test_a_link_to_a_catalogue_entry_is_kept_and_scrolled_to_whatever_the_root_path():
    """Scalar rewrites the address and does not scroll to the introduction's headings, so the page's own
    script reads the address before Scalar starts and scrolls to the heading once it exists. It has to run
    first, on the instance page (under a root path) and on the static build alike."""
    sources = [
        {"title": "Management API", "slug": "management", "url": "/docs/api/management.json"}
    ]
    for page in (
        render_page("bundled", "/rdm", sources),
        render_page("bundled", "", sources, static=StaticSite()),
    ):
        scripts = re.findall(r"<script>(.*?)</script>", page, flags=re.DOTALL)
        anchor = next(text for text in scripts if "scrollIntoView" in text)
        assert page.index(anchor) < page.index("createApiReference")
        # It reads the address as opened and acts only on an entry of the catalogue.
        assert "location.hash" in anchor and r"/description/" in anchor.replace("\\", "")
        assert "getElementById(wanted)" in anchor and "history.replaceState" in anchor
        # It gives up when the reader takes over, and after a bounded time.
        assert "wheel" in anchor and "keydown" in anchor and "> 80" in anchor


def test_the_build_writes_the_page_its_two_documents_and_the_script(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")

    static_site.build(tmp_path)

    page = (tmp_path / "api" / "index.html").read_text()
    configuration = json.loads(
        re.search(r'createApiReference\("#rdm-api-reference", (\{.*\})\);', page).group(1)
    )
    assert [(item["slug"], item["url"]) for item in configuration["sources"]] == [
        ("management", "/docs/api/management.json"),
        ("consumer-stops-v1", "/docs/api/stops.json"),
    ]
    assert configuration["sources"][1]["title"] == "Example: Stops API · v1"
    assert (
        json.loads((tmp_path / "api" / "management.json").read_text())["info"]["title"]
        == "refiroo API"
    )
    assert json.loads((tmp_path / "api" / "stops.json").read_text())["openapi"].startswith("3.1")
    assert (tmp_path / "api" / "scalar" / "standalone.js").is_file()
    assert (tmp_path / "brand" / "refiroo-header.css").is_file()


def test_the_management_document_lists_the_gated_operations_too():
    paths = static_site._management_document()["paths"]

    assert any("/model-drafts" in path for path in paths)
    assert any("/consumer-subscriptions" in path for path in paths)
    assert any("/jobs" in path for path in paths)


def test_an_attributed_inline_script_of_a_host_theme_is_hashed_and_a_script_file_is_not():
    page = (
        '<html><head><meta charset="utf-8" />'
        '<script type="module" data-host="x">window.host = 1;</script>'
        '<script src="/theme/host.js" defer></script></head><body></body></html>'
    )

    policy = unescape(re.search(r'content="([^"]*)"', with_meta_policy("bundled", page)).group(1))

    digest = base64.b64encode(hashlib.sha256(b"window.host = 1;").digest()).decode()
    assert f"'sha256-{digest}'" in policy
    assert policy.count("sha256-") == 1


def test_the_build_serves_the_examples_the_document_references_under_its_base(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")

    static_site.build(tmp_path, base="/guide")

    document = json.loads((tmp_path / "api" / "management.json").read_text())
    reference = document["paths"]["/api/v1/workspaces/{workspace_key}"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["examples"]["graubuenden"]["externalValue"]
    assert reference == "/guide/api/examples/get-api-v1-workspaces-workspace_key/response.json"
    served = tmp_path / "api" / "examples" / "get-api-v1-workspaces-workspace_key" / "response.json"
    assert json.loads(served.read_text())["key"] == "graubuenden"
