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
