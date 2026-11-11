"""``management/reference/content.py``: the reference text merged into the OpenAPI document.

The merge is tested on a small document and content directory; the shipped content is tested against the
application's own document: every operation of an area that has text has its section, its error list
and its example, every code an operation lists has a catalogue entry, and no text names a package or a
decision. That every operation, field and entry is covered is ``tests/test_reference_complete.py``.
"""

import copy
import json
import re

import pytest

from app.main import app
from app.management.reference.content import (
    CONTENT_DIR,
    ContentError,
    code_anchor,
    example_bodies,
    example_file_name,
    merge_content,
    parse_area,
)

DOCUMENT = {
    "openapi": "3.1.0",
    "info": {"title": "t", "version": "1", "description": "In code."},
    "paths": {
        "/things": {
            "get": {
                "tags": ["things"],
                "x-action": "things.read",
                "summary": "Get Things",
                "description": "In code (0.1 X1).",
                "parameters": [
                    {
                        "name": "size",
                        "in": "query",
                        "description": "In code.",
                        "schema": {"type": "integer"},
                    },
                    {
                        "name": "X-Hint",
                        "in": "header",
                        "description": "In code.",
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            },
            "post": {
                "tags": ["things"],
                "x-action": "things.write",
                "description": "Makes a thing.",
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {
                    "201": {
                        "description": "made",
                        "content": {"application/json": {"schema": {"type": "object"}}},
                    }
                },
            },
        },
        "/others": {"get": {"tags": ["others"], "responses": {"200": {"description": "ok"}}}},
    },
    "components": {
        "schemas": {
            "ApiErrorResponse": {"type": "object"},
            "Thing": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "In code."}},
            },
        }
    },
}

INDEX = """## Signing in

Send a token.

### Errors every operation can return

- 401 NO_TOKEN

### Headers every operation takes

- X-Hint: A hint.
"""
ERRORS = """## Error codes

### NO_TOKEN

Status 401. No token.

### GONE

Status 404. Not there.
"""
THINGS = """# things

About things.

## Concepts

A thing is a thing.

## GET /things

Title: List things

Lists things.

### Parameters

- size: How many.

### Errors

- 404 GONE: the thing is not there.

## Schemas

### Thing

- name: What it is called.
"""


def content(tmp_path, **files):
    for name, text in {
        "index.md": INDEX,
        "errors.md": ERRORS,
        "things.md": THINGS,
        **files,
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if isinstance(text, str) else json.dumps(text))
    return tmp_path


def merged(tmp_path, **files):
    return merge_content(copy.deepcopy(DOCUMENT), content(tmp_path, **files))


def test_the_content_is_merged_into_the_document(tmp_path):
    document = merged(tmp_path)
    assert document["info"]["description"].startswith("In code.\n\n## Signing in")
    assert "### GONE" in document["info"]["description"]
    # Every tag the operations use is listed in the order they appear; the one with text carries it.
    assert [tag["name"] for tag in document["tags"]] == ["things", "others"]
    overview = document["tags"][0]["description"]
    assert overview.startswith("About things.") and "## Concepts" in overview
    assert "description" not in document["tags"][1]
    listing = document["paths"]["/things"]["get"]
    # The written section replaces what the code says; its title is the operation's name.
    assert listing["description"] == "Lists things." and listing["summary"] == "List things"
    sizes = {p["name"]: p["description"] for p in listing["parameters"]}
    assert sizes == {"size": "How many.", "X-Hint": "A hint."}
    assert document["components"]["schemas"]["Thing"]["properties"]["name"]["description"] == (
        "What it is called."
    )
    # Operations that need a token carry the shared errors; the codes are grouped by status and
    # linked to the catalogue, whose anchor Scalar gives the heading.
    assert (
        "[`NO_TOKEN`](#management/description/no-token)"
        in listing["responses"]["401"]["description"]
    )
    assert "[`GONE`](#management/description/gone)" in listing["responses"]["404"]["description"]
    assert "401" not in document["paths"]["/others"]["get"]["responses"]
    assert listing["responses"]["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }
    assert code_anchor("WORKSPACE_NOT_FOUND") == "#management/description/workspace-not-found"


def test_a_line_under_a_schema_heading_is_the_schemas_own_description(tmp_path):
    """The plain text under ``### Schema`` replaces the description the code gives; the ``- field:``
    lines describe fields as before, and a schema without such a line keeps the code's."""
    described = THINGS.replace(
        "### Thing\n\n- name:", "### Thing\n\nA thing, in one line\nof two.\n\n- name:"
    )
    document = copy.deepcopy(DOCUMENT)
    document["components"]["schemas"]["Thing"]["description"] = "In code (0.9 K1)."
    schemas = merge_content(document, content(tmp_path, **{"things.md": described}))["components"][
        "schemas"
    ]
    assert schemas["Thing"]["description"] == "A thing, in one line of two."
    assert schemas["Thing"]["properties"]["name"]["description"] == "What it is called."
    assert "description" not in schemas["ApiErrorResponse"]
    area = parse_area(described, "things.md")
    assert area.descriptions == {"Thing": "A thing, in one line of two."}
    # Two descriptions for one schema are refused; a description for a schema the document lacks too.
    twice = described + "\n### Thing\n\nAgain.\n"
    with pytest.raises(ContentError, match="two descriptions"):
        parse_area(twice, "things.md")
    with pytest.raises(ContentError, match="has no schema 'Gadget'"):
        merged(tmp_path, **{"things.md": THINGS + "\n### Gadget\n\nA gadget.\n"})


def test_an_operation_without_a_section_keeps_what_the_code_says(tmp_path):
    post = merged(tmp_path)["paths"]["/things"]["post"]
    assert post["description"] == "Makes a thing." and "401" in post["responses"]


@pytest.mark.parametrize(
    ("files", "message"),
    [
        (
            {"things.md": THINGS + "\n## GET /gone\n\nNo such route.\n"},
            "'GET /gone' is not an operation",
        ),
        (
            {"things.md": THINGS + "\n## DELETE /things\n\nNo such method.\n"},
            "'DELETE /things' is not",
        ),
        ({"things.md": THINGS.replace("# things", "# nothing", 1)}, "no operation with this tag"),
        ({"things.md": THINGS.replace("GET /things", "GET /others")}, "not tagged 'things'"),
        ({"things.md": THINGS.replace("404 GONE", "404 LOST")}, "'LOST' has no entry"),
        ({"things.md": THINGS + "\n## GET /things\n\nTwice.\n"}, "has two sections"),
        ({"things.md": THINGS.replace("- 404 GONE:", "- GONE")}, "an errors line reads"),
        ({"things.md": "About things.\n"}, "starts with '# <tag>'"),
        ({"errors.md": ERRORS + "\n### GONE\n\nAgain.\n"}, "has two entries"),
        ({"errors.md": ERRORS.replace("NO_TOKEN", "not a code")}, "is not an error code"),
        ({"index.md": INDEX.replace("NO_TOKEN", "UNLISTED")}, "'UNLISTED' has no entry"),
        ({"things.md": THINGS.replace("- size:", "- depth:")}, "has no parameter 'depth'"),
        ({"things.md": THINGS.replace("### Thing", "### Gadget")}, "has no schema 'Gadget'"),
        ({"things.md": THINGS.replace("- name:", "- colour:")}, "has no field 'colour'"),
        ({"things.md": THINGS.replace("- size: How many.", "size How many.")}, "a note reads"),
    ],
)
def test_text_that_does_not_match_the_document_fails_loudly(tmp_path, files, message):
    with pytest.raises(ContentError, match=re.escape(message)):
        merged(tmp_path, **files)


def test_text_for_something_the_document_lacks_is_skipped_unless_strict(tmp_path):
    stale = {
        "things.md": THINGS
        + "\n## GET /gone\n\nNo such route.\n\n### Errors\n\n- 404 GONE\n"
        + "\n## Schemas\n\n### Gadget\n\n- name: x\n\n### Thing\n\n- colour: x\n",
        "later.md": "# later\n\nNo such tag.\n\n## GET /gone\n\nNo such route.\n",
        "examples/get-gone.json": {"operation": "GET /gone", "name": "x", "request": {}},
    }
    directory = content(tmp_path, **stale)
    skipped = merge_content(copy.deepcopy(DOCUMENT), directory, strict=False)
    assert skipped["paths"]["/things"]["get"]["description"] == "Lists things."
    assert "later" not in {tag["name"] for tag in skipped["tags"]}
    with pytest.raises(ContentError):
        merge_content(copy.deepcopy(DOCUMENT), directory)


def test_a_code_without_an_entry_fails_even_when_not_strict(tmp_path):
    files = {"things.md": THINGS.replace("404 GONE", "404 LOST")}
    with pytest.raises(ContentError, match="'LOST' has no entry"):
        merge_content(copy.deepcopy(DOCUMENT), content(tmp_path, **files), strict=False)


def test_headings_inside_a_code_fence_are_text(tmp_path):
    fenced = THINGS.replace(
        "Lists things.", "Lists things.\n\n```\n## GET /gone\n# nothing\n```\n\nAfter."
    )
    assert (
        "## GET /gone"
        in merged(tmp_path, **{"things.md": fenced})["paths"]["/things"]["get"]["description"]
    )


EXAMPLE = {
    "operation": "POST /things",
    "name": "first",
    "summary": "A first thing",
    "request": {"body": {"name": "a"}},
    "response": {"status": 201, "body": {"id": "1"}},
    "notes": ["`items`: the first 2 of 9 items are shown."],
}


def test_an_example_is_merged_as_named_openapi_examples(tmp_path):
    document = merged(
        tmp_path,
        **{
            "examples/post-things.json": EXAMPLE,
            "examples/get-things.json": {
                "operation": "GET /things",
                "name": "small",
                "request": {"query": {"size": 2}},
                "response": {"status": 200, "body": {"items": []}},
            },
        },
    )
    post, get = document["paths"]["/things"]["post"], document["paths"]["/things"]["get"]
    sent = post["requestBody"]["content"]["application/json"]["examples"]["first"]
    # Bodies are referenced, not inlined: the page and the static build serve them as files.
    assert sent["externalValue"] == "docs/api/examples/post-things/request.json"
    assert "value" not in sent and sent["summary"] == "A first thing"
    assert "first 2 of 9" in sent["description"]
    assert get["parameters"][0]["examples"]["small"]["value"] == 2
    small = get["responses"]["200"]["content"]["application/json"]["examples"]["small"]
    assert small["externalValue"] == "docs/api/examples/get-things/response.json"
    served = {(slug, part): body for slug, part, body in example_bodies(tmp_path)}
    assert served == {
        ("post-things", "request"): {"name": "a"},
        ("post-things", "response"): {"id": "1"},
        ("get-things", "response"): {"items": []},
    }
    assert example_file_name("GET", "/api/v1/workspaces/{workspace_key}") == (
        "get-api-v1-workspaces-workspace_key.json"
    )


@pytest.mark.parametrize(
    ("file", "example", "message"),
    [
        ("post-things", {**EXAMPLE, "operation": "POST /gone"}, "is named for"),
        ("post-gone", {**EXAMPLE, "operation": "POST /gone"}, "is not an operation"),
        ("get-things", {**EXAMPLE, "operation": "GET /things"}, "takes no JSON request body"),
        (
            "post-things",
            {**EXAMPLE, "response": {"status": 200, "body": {}}},
            "has no 200 response body",
        ),
    ],
)
def test_an_example_that_does_not_match_the_document_fails_loudly(tmp_path, file, example, message):
    with pytest.raises(ContentError, match=message):
        merged(tmp_path, **{f"examples/{file}.json": example})


# --- the shipped content, against the application's document ---------------------------------------

_IDENTIFIER = re.compile(
    r"\b(ADR-\d+|[A-Z]{1,3}-D\d+|D\d{2,3}|0\.\d{1,2} [A-Z]{1,3}\d[\w-]*|[A-Z]{1,2}\d[a-z]?-\d+)\b"
)


def _texts():
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(CONTENT_DIR.glob("*.md"))
        if path.name != "README.md"
    }


def _areas():
    return [
        parse_area(text, name)
        for name, text in _texts().items()
        if name not in {"index.md", "errors.md"}
    ]


def test_every_operation_of_an_area_with_text_has_its_section_and_example():
    # Every optional surface on: the text covers routes an instance may switch off.
    from app.management.reference import static_site

    document = static_site._management_document()
    for area in _areas():
        documented = {(s.method, s.path) for s in area.operations}
        expected = {
            (method.upper(), path)
            for path, item in document["paths"].items()
            for method, operation in item.items()
            # An operation with several tags is written in the file of its first tag.
            if (operation.get("tags") or ["untagged"])[0] == area.tag
        }
        assert documented == expected, area.tag
        for method, path in expected:
            assert (CONTENT_DIR / "examples" / example_file_name(method, path)).is_file(), (
                method,
                path,
            )
        for section in area.operations:
            assert section.description and section.title, (
                section.method,
                section.path,
            )


def test_every_listed_code_has_an_entry():
    texts = _texts()
    entries = set(re.findall(r"^### ([A-Z][A-Z0-9_]*)$", texts["errors.md"], re.MULTILINE))
    document = app.openapi()
    listed = set()
    for item in document["paths"].values():
        for operation in item.values():
            for response in operation["responses"].values():
                listed |= set(
                    re.findall(
                        r"\[`([A-Z0-9_]+)`\]\(#management/description/", response["description"]
                    )
                )
    assert listed <= entries, listed - entries


def test_the_text_names_no_package_or_decision_and_the_catalogue_anchors_resolve():
    for name, text in _texts().items():
        assert not _IDENTIFIER.search(text), (name, _IDENTIFIER.search(text).group(0))
    document = app.openapi()
    headings = {
        "#management/description/" + title.lower().replace("_", "-")
        for title in re.findall(
            r"^### ([A-Z][A-Z0-9_]*)$", document["info"]["description"], re.MULTILINE
        )
    }
    for item in document["paths"].values():
        for operation in item.values():
            for response in operation["responses"].values():
                for anchor in re.findall(
                    r"\]\((#management/description/[a-z0-9-]+)\)", response["description"]
                ):
                    assert anchor in headings, anchor


def test_the_text_keeps_to_the_shape_the_guidance_page_sets():
    """An overview is short, an operation says what it does without listing the object's fields and an
    error line says when in a few words (content/README.md)."""
    for area in _areas():
        assert len(area.overview.split()) <= 130, area.tag
        for section in area.operations:
            where = (area.tag, section.method, section.path)
            assert len(section.description.split()) <= 90, where
            assert all(len(line.text.split()) <= 12 for line in section.errors), where


def test_the_page_serves_the_example_bodies_the_document_references():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    found = client.get("/docs/api/examples/get-api-v1-workspaces-workspace_key/response.json")
    assert found.status_code == 200 and found.json()["key"] == "graubuenden"
    assert client.get("/docs/api/examples/nothing/response.json").status_code == 404
    reference = app.openapi()["paths"]["/api/v1/workspaces/{workspace_key}"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["examples"]["graubuenden"]["externalValue"]
    assert reference == "docs/api/examples/get-api-v1-workspaces-workspace_key/response.json"


def test_the_example_addresses_follow_a_root_path():
    """The document's example addresses are relative to the document, so an instance under a prefix
    resolves them under it, and the files answer there."""
    from urllib.parse import urljoin

    from fastapi.testclient import TestClient

    client = TestClient(app, root_path="/rdm")
    reference = app.openapi()["paths"]["/api/v1/workspaces/{workspace_key}"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["examples"]["graubuenden"]["externalValue"]
    resolved = urljoin("https://engine.example/rdm/openapi.json", reference)
    assert resolved == (
        "https://engine.example/rdm/docs/api/examples/"
        "get-api-v1-workspaces-workspace_key/response.json"
    )
    assert client.get(reference_path := "/" + reference).status_code == 200
    assert reference_path.startswith("/docs/api/examples/")


def test_a_note_can_name_a_parameter_with_placeholders():
    """``filter.<field>.<operator>`` is one parameter, whose name holds placeholders."""
    area = parse_area(
        "# t\n\n## GET /x\n\nDoes.\n\n### Parameters\n\n- filter.<field>.<operator>: Repeatable.\n"
        "- related:<key>: A key.\n",
        "t.md",
    )
    assert area.operations[0].parameters == {
        "filter.<field>.<operator>": "Repeatable.",
        "related:<key>": "A key.",
    }


def test_the_shipped_text_matches_the_document_of_every_capability_switched_on():
    from app.management.reference import static_site

    static_site._management_document(strict=True)


@pytest.mark.parametrize(
    "setting",
    [
        "INTEGRATION_JOBS_ENABLED",
        "MODEL_ADMIN_MUTATIONS_ENABLED",
        "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        "CONSUMER_SUBSCRIPTIONS_ENABLED",
        "ALL",
    ],
)
def test_the_document_builds_with_an_optional_surface_off(setting):
    from app.management.reference import static_site

    off = {name: "false" for name in _SURFACES} if setting == "ALL" else {setting: "false"}
    document = static_site._management_document(**off)
    full = static_site._management_document()
    assert _operations(document) <= _operations(full)
    if setting != "ALL":
        assert _operations(document) < _operations(full), setting


def _operations(document):
    return {(path, method) for path, item in document["paths"].items() for method in item}


_SURFACES = (
    "INTEGRATION_JOBS_ENABLED",
    "MODEL_ADMIN_MUTATIONS_ENABLED",
    "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
    "CONSUMER_SUBSCRIPTIONS_ENABLED",
)
