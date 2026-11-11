"""The management API's documentation text, merged into its OpenAPI document.

The routes hold no documentation text. It lives beside this module, in ``content/``, shipped as package
data, and ``merge_content`` puts it into the generated document when the application builds it
(``install``, FastAPI's documented ``app.openapi()`` override):

``content/README.md``
    The writer's guidance. It is not merged.
``content/index.md``
    The conventions every operation shares. It follows the document's one-line description in
    ``info.description``. Its section ``### Errors every operation can return`` is a list in the
    errors format below (the text after the code may be left out), added to every operation that needs a
    token. Its section ``### Headers every operation takes`` (``- Name: text``) describes those headers.
``content/errors.md``
    The error catalogue, appended to ``info.description``: one ``### CODE`` heading per code. A heading
    is the one anchor Scalar gives a piece of text (``#management/description/<code, lower case, - for _>``), so
    an operation's error list links each code to its entry.
``content/<area>.md``
    One file per tag. Its ``# <tag>`` heading names the tag exactly as the document does (guide pages
    link to ``#tag/<tag>``); the text under it, up to the first operation section, is the tag's
    description. Each operation has a section headed by its method and path as the public contract,
    ``## GET /api/v1/workspaces/{workspace_key}``, never by FastAPI's generated ``operationId``. Its
    first line may be ``Title: Delete a workspace``, the operation's name in the sidebar. The rest is the
    operation's description, which replaces the one the code gives. A ``### Parameters`` part
    (``- name: text``) replaces the description of those parameters. A ``### Errors`` part is read as the
    operation's error responses: one line per code, ``- 404 WORKSPACE_NOT_FOUND: when it happens``,
    grouped by status. A ``## Schemas`` section holds one ``### SchemaName`` (or several, separated by
    commas) per schema of ``components.schemas``. A line of plain text under the heading is the schema's
    own description, replacing the one in the code; ``- field: text`` describes a field, which becomes
    that property's description.
``content/examples/<method>-<path>.json``
    One operation's named example request and response, written by the recording (``tests/
    test_reference_recording.py``). Parameter examples are merged inline; the request and response
    bodies are referenced, as an Example Object's ``externalValue``, and served as files of their own
    (``example_bodies``; the page route and ``static_site``), so the document stays small. The reference
    is relative to the document (``docs/api/examples/...``), so under a root path it resolves with the
    prefix. Scalar loads a referenced example when it is on screen, and only against an absolute document
    address, which the page makes of its own.

Text for something the document does not have (a route, a tag, a schema, a field, a parameter) is
skipped when the application builds it, because an instance with an optional surface switched off
(``INTEGRATION_JOBS_ENABLED``, ``WORKSPACE_ADMIN_MUTATIONS_ENABLED``...) has fewer routes than the text
covers. ``merge_content(..., strict=True)`` raises ``ContentError`` for each such text instead; the tests
build the document of every capability switched on that way, so a renamed route cannot leave stale text
behind. A code with no catalogue entry, and text in the wrong shape, raise in both modes.
"""

import copy
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).resolve().parent / "content"
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
SHARED_ERRORS_HEADING = "Errors every operation can return"
SHARED_HEADERS_HEADING = "Headers every operation takes"
PAGE_FIELDS_HEADING = "Fields of every page"
SOURCE_SLUG = "management"
# The area file of the operations that carry no tag (``# untagged``); it has no overview.
UNTAGGED = "untagged"
# Where the page and the static build serve each example's request and response body. The address is
# relative, so it resolves against the document's own address and follows an instance's root path; the
# static build replaces it with its own absolute one.
EXAMPLES_URL = "docs/api/examples"
_ERROR_PLACEHOLDER = "ApiErrorResponse"

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^(#{1,6}) +(.+?) *$")
_OPERATION = re.compile(rf"^({'|'.join(METHODS)}) (/\S*)$")
_ERROR_LINE = re.compile(r"^- (\d{3}) ([A-Z][A-Z0-9_]*)(?:: (.+))?$")
_NOTE = re.compile(r"^- ([A-Za-z][\w.<>:-]*): (.+)$")
_TITLE = re.compile(r"^Title: (.+)$")


class ContentError(Exception):
    """The content does not match the document it documents."""


@dataclass(frozen=True)
class ErrorLine:
    status: str
    code: str
    text: str


def code_anchor(code: str) -> str:
    """Where a code's catalogue entry is: Scalar's anchor for the heading ``### CODE``, which on the
    page carries the slug of the source that holds the document (``management``, see ``consumer_sources``
    and ``static_site``)."""
    return f"#{SOURCE_SLUG}/description/" + code.lower().replace("_", "-")


def _headings(text: str) -> Iterator[tuple[int, str, int]]:
    """``(level, title, line index)`` of each Markdown heading outside a code fence."""
    fenced = False
    for index, line in enumerate(text.splitlines()):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            found = _HEADING.match(line)
            if found:
                yield len(found.group(1)), found.group(2), index


def _split(text: str, level: int) -> tuple[str, list[tuple[str, str]]]:
    """The text before the first heading of ``level``, and each such heading's title with its body (up to
    the next heading of that level or a higher one)."""
    lines = text.splitlines()
    marks = [(found, title, index) for found, title, index in _headings(text)]
    own = [
        (title, index, position)
        for position, (found, title, index) in enumerate(marks)
        if found == level
    ]
    head = "\n".join(lines[: own[0][1]] if own else lines).strip()
    sections = []
    for title, index, position in own:
        end = next((m[2] for m in marks[position + 1 :] if m[0] <= level), len(lines))
        sections.append((title, "\n".join(lines[index + 1 : end]).strip()))
    return head, sections


def _error_lines(block: str, where: str) -> list[ErrorLine]:
    lines = []
    for line in block.splitlines():
        if not line.strip():
            continue
        found = _ERROR_LINE.match(line)
        if found is None:
            raise ContentError(f"{where}: an errors line reads '- 404 CODE: text', not '{line}'")
        lines.append(ErrorLine(found.group(1), found.group(2), found.group(3) or ""))
    return lines


def _take(body: str, heading: str) -> tuple[str, str]:
    """The section's text without its ``### <heading>`` part, and that part's text."""
    lines = body.splitlines()
    marks = list(_headings(body))
    for position, (level, title, index) in enumerate(marks):
        if level == 3 and title == heading:
            end = next((m[2] for m in marks[position + 1 :] if m[0] <= 3), len(lines))
            kept = lines[:index] + lines[end:]
            return "\n".join(kept).strip(), "\n".join(lines[index + 1 : end])
    return body.strip(), ""


def _description(block: str) -> tuple[str, str]:
    """The plain text before a schema's ``- field: text`` lines, and those lines."""
    lines = block.splitlines()
    first = next((i for i, line in enumerate(lines) if line.startswith("- ")), len(lines))
    return " ".join(line.strip() for line in lines[:first] if line.strip()), "\n".join(
        lines[first:]
    )


def _notes(block: str, where: str) -> dict[str, str]:
    """``- name: text`` lines as a mapping."""
    notes = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        found = _NOTE.match(line)
        if found is None:
            raise ContentError(f"{where}: a note reads '- name: text', not '{line}'")
        notes[found.group(1)] = found.group(2)
    return notes


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    title: str | None
    description: str
    parameters: dict[str, str]
    errors: list[ErrorLine]


@dataclass(frozen=True)
class Area:
    tag: str
    overview: str
    operations: list[Operation]
    schemas: dict[str, dict[str, str]]
    # The schemas' own descriptions: the plain text under a ``### SchemaName`` heading.
    descriptions: dict[str, str] = field(default_factory=dict)


def parse_area(text: str, where: str) -> Area:
    head, _ = _split(text, 2)
    title = next(((level, name) for level, name, _ in _headings(text)), None)
    if title is None or title[0] != 1:
        raise ContentError(f"{where}: the file starts with '# <tag>', the tag's exact name")
    tag = title[1]
    overview = head.split("\n", 1)[1].strip() if "\n" in head else ""
    operations, seen, schemas, descriptions = [], set(), {}, {}
    for heading, body in _split(text, 2)[1]:
        if heading == "Schemas":
            for names, fields in _split(body, 3)[1]:
                text, bullets = _description(fields)
                described = _notes(bullets, f"{where}, {names}")
                for name in (item.strip() for item in names.split(",")):
                    schemas.setdefault(name, {}).update(described)
                    if text:
                        if name in descriptions:
                            raise ContentError(f"{where}: schema '{name}' has two descriptions")
                        descriptions[name] = text
            continue
        found = _OPERATION.match(heading)
        if found is None:
            overview = f"{overview}\n\n## {heading}\n\n{body}".strip()
            continue
        method, path = found.groups()
        if (method, path) in seen:
            raise ContentError(f"{where}: '{heading}' has two sections")
        seen.add((method, path))
        here = f"{where}, {heading}"
        rest, errors = _take(body, "Errors")
        rest, parameters = _take(rest, "Parameters")
        title = None
        first, _, remainder = rest.partition("\n")
        titled = _TITLE.match(first.strip())
        if titled:
            title, rest = titled.group(1).strip(), remainder.strip()
        operations.append(
            Operation(
                method, path, title, rest, _notes(parameters, here), _error_lines(errors, here)
            )
        )
    return Area(tag, overview, operations, schemas, descriptions)


def parse_catalogue(text: str) -> tuple[str, dict[str, str]]:
    """The catalogue's introduction and the text of each code, in file order."""
    entries: dict[str, str] = {}
    _, sections = _split(text, 3)
    for code, body in sections:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", code):
            raise ContentError(f"errors.md: '### {code}' is not an error code")
        if code in entries:
            raise ContentError(f"errors.md: '{code}' has two entries")
        entries[code] = body
    return text, entries


def shared_errors(index: str) -> list[ErrorLine]:
    for heading, body in _split(index, 3)[1]:
        if heading == SHARED_ERRORS_HEADING:
            lines = []
            for line in body.splitlines():
                if line.startswith("- "):
                    lines.append(line)
                else:
                    break
            return _error_lines("\n".join(lines), "index.md")
    return []


def shared_headers(index: str) -> dict[str, str]:
    for heading, body in _split(index, 3)[1]:
        if heading == SHARED_HEADERS_HEADING:
            return _notes(body, "index.md")
    return {}


def _describe_pages(document: dict[str, Any], notes: dict[str, str]) -> None:
    """The navigation fields every page schema (one with ``nextCursor`` and ``anchor``) has."""
    for schema in document.get("components", {}).get("schemas", {}).values():
        properties = schema.get("properties", {})
        if "nextCursor" in properties and "anchor" in properties:
            for field, text in notes.items():
                if field in properties:
                    properties[field]["description"] = text


def _status_description(lines: list[ErrorLine]) -> str:
    return "\n".join(
        f"- [`{line.code}`]({code_anchor(line.code)})" + (f": {line.text}" if line.text else "")
        for line in lines
    )


def _add_errors(operation: dict[str, Any], lines: list[ErrorLine], components: dict) -> None:
    by_status: dict[str, list[ErrorLine]] = {}
    for line in lines:
        by_status.setdefault(line.status, []).append(line)
    responses = operation.setdefault("responses", {})
    shape = (
        {"application/json": {"schema": {"$ref": f"#/components/schemas/{_ERROR_PLACEHOLDER}"}}}
        if _ERROR_PLACEHOLDER in components.get("schemas", {})
        else None
    )
    for status in sorted(by_status):
        response = responses.setdefault(status, {})
        listed = _status_description(by_status[status])
        response["description"] = (
            f"{response['description']}\n\n{listed}" if response.get("description") else listed
        )
        if shape is not None:
            response.setdefault("content", copy.deepcopy(shape))


def _describe_parameters(
    operation: dict[str, Any], notes: dict[str, str], where: str, *, strict: bool
) -> None:
    """Set the description of the parameters (or headers) ``notes`` names. A note for a parameter the
    operation does not take fails when ``strict``."""
    found = set()
    for parameter in operation.get("parameters", []):
        if parameter["name"] in notes:
            parameter["description"] = notes[parameter["name"]]
            # FastAPI repeats a ``Query(description=...)`` on the schema; the page would show both.
            parameter.get("schema", {}).pop("description", None)
            found.add(parameter["name"])
    if strict and set(notes) - found:
        raise ContentError(f"{where}: the operation has no parameter '{min(set(notes) - found)}'")


def _describe_schemas(document: dict[str, Any], area: Area, *, strict: bool) -> None:
    schemas = document.get("components", {}).get("schemas", {})
    for name, fields in area.schemas.items():
        where = f"{area.tag}.md, schema {name}"
        if name not in schemas:
            if strict:
                raise ContentError(f"{where}: the document has no schema '{name}'")
            continue
        if name in area.descriptions:
            schemas[name]["description"] = area.descriptions[name]
        properties = schemas[name].get("properties", {})
        for field_name, text in fields.items():
            if field_name not in properties:
                if strict:
                    raise ContentError(f"{where}: the schema has no field '{field_name}'")
                continue
            properties[field_name]["description"] = text


def _find(document: dict, method: str, path: str, where: str, *, strict: bool):
    operation = document.get("paths", {}).get(path, {}).get(method.lower())
    if operation is None:
        if not strict:
            return None
        raise ContentError(f"{where}: '{method} {path}' is not an operation of the document")
    return operation


def example_file_name(method: str, path: str) -> str:
    """``examples/get-api-v1-workspaces-workspace_key.json`` for ``GET /api/v1/workspaces/{workspace_key}``."""
    slug = re.sub(r"[^a-z0-9_]+", "-", path.lower().replace("{", "").replace("}", "")).strip("-")
    return f"{method.lower()}-{slug}.json"


def _add_example(operation: dict[str, Any], example: dict[str, Any], where: str) -> None:
    name = example["name"]
    summary = example.get("summary", name)
    notes = example.get("notes") or []
    described = {"summary": summary, **({"description": " ".join(notes)} if notes else {})}
    request = example.get("request", {})
    for kind in ("path", "query"):
        for parameter in operation.get("parameters", []):
            given = request.get(kind, {})
            if (
                parameter["in"] == kind
                and parameter["name"] in given
                and "example" not in parameter
            ):
                parameter.setdefault("examples", {})[name] = {
                    "summary": summary,
                    "value": given[parameter["name"]],
                }
    slug = example_file_name(*example["operation"].split(" ", 1))[: -len(".json")]
    if "body" in request:
        content = operation.get("requestBody", {}).get("content", {}).get("application/json")
        if content is None:
            raise ContentError(f"{where}: the operation takes no JSON request body")
        content.setdefault("examples", {})[name] = {
            **described,
            "externalValue": f"{EXAMPLES_URL}/{slug}/request.json",
        }
    response = example.get("response", {})
    if "body" in response:
        media = operation.get("responses", {}).get(str(response["status"]), {}).get("content", {})
        kind = "application/json" if "application/json" in media else next(iter(media), None)
        if kind is None:
            raise ContentError(f"{where}: the operation has no {response['status']} response body")
        if kind == "application/json":
            reference = {"externalValue": f"{EXAMPLES_URL}/{slug}/response.json"}
        else:  # a text body (the metrics) is short and stays in the document
            reference = {"value": response["body"]}
        media[kind].setdefault("examples", {})[name] = {**described, **reference}


def example_bodies(directory: Path = CONTENT_DIR) -> Iterator[tuple[str, str, Any]]:
    """``(slug, "request" or "response", body)`` of every example body, as the files the document
    references are served."""
    for path in sorted((directory / "examples").glob("*.json")):
        example = json.loads(path.read_text(encoding="utf-8"))
        for part in ("request", "response"):
            if "body" in example.get(part, {}) and not isinstance(example[part]["body"], str):
                yield path.name[: -len(".json")], part, example[part]["body"]


def merge_content(
    document: dict[str, Any], directory: Path = CONTENT_DIR, *, strict: bool = True
) -> dict[str, Any]:
    """The document with the content directory merged in. Raises ``ContentError`` for text that names
    a code the catalogue lacks and, when ``strict``, for text that names a route, a tag, a schema, a field
    or a parameter the document does not have; otherwise that text is skipped."""
    index_file, catalogue_file = directory / "index.md", directory / "errors.md"
    index = index_file.read_text(encoding="utf-8").strip() if index_file.is_file() else ""
    catalogue = (
        catalogue_file.read_text(encoding="utf-8").strip() if catalogue_file.is_file() else ""
    )
    _, entries = parse_catalogue(catalogue)
    shared = shared_errors(index)
    headers = shared_headers(index)
    areas = [
        parse_area(path.read_text(encoding="utf-8"), path.name)
        for path in sorted(directory.glob("*.md"))
        if path.name not in {"index.md", "errors.md", "README.md"}
    ]
    info = document.setdefault("info", {})
    info["description"] = "\n\n".join(
        part for part in (info.get("description", "").strip(), index, catalogue) if part
    )
    for code in {line.code for line in shared}:
        if code not in entries:
            raise ContentError(f"index.md: '{code}' has no entry in errors.md")

    first_seen: list[str] = []
    for item in document.get("paths", {}).values():
        for operation in item.values():
            for tag in operation.get("tags", []):
                if tag not in first_seen:
                    first_seen.append(tag)
    described = {item["name"]: item for item in document.get("tags", [])}
    for area in areas:
        if area.tag == UNTAGGED:
            if area.overview:
                raise ContentError(f"{area.tag}.md: the untagged operations have no overview")
            continue
        if area.tag not in first_seen:
            if strict:
                raise ContentError(f"{area.tag}: the document has no operation with this tag")
            continue
        described.setdefault(area.tag, {"name": area.tag})["description"] = area.overview
    document["tags"] = [described.get(tag, {"name": tag}) for tag in first_seen]

    components = document.get("components", {})
    own: dict[tuple[str, str], list[ErrorLine]] = {}
    for area in areas:
        for section in area.operations:
            where = f"{area.tag}.md, {section.method} {section.path}"
            operation = _find(document, section.method, section.path, where, strict=strict)
            if operation is None:
                for line in section.errors:
                    if line.code not in entries:
                        raise ContentError(f"{where}: '{line.code}' has no entry in errors.md")
                continue
            if (area.tag == UNTAGGED and operation.get("tags")) or (
                area.tag != UNTAGGED and area.tag not in operation.get("tags", [])
            ):
                raise ContentError(f"{where}: the operation is not tagged '{area.tag}'")
            # The written section replaces what the code says: that text names packages and decisions.
            operation["description"] = section.description
            if section.title:
                operation["summary"] = section.title
            _describe_parameters(operation, section.parameters, where, strict=strict)
            for line in section.errors:
                if line.code not in entries:
                    raise ContentError(f"{where}: '{line.code}' has no entry in errors.md")
            own[(section.method, section.path)] = section.errors
    for heading, body in _split(index, 3)[1]:
        if heading == PAGE_FIELDS_HEADING:
            _describe_pages(document, _notes(body, "index.md"))
    for area in areas:
        _describe_schemas(document, area, strict=strict)
    for method, path, operation in _operations(document):
        _describe_parameters(operation, headers, "index.md", strict=False)
        lines = own.get((method, path), [])
        if "x-action" in operation:
            lines = lines + [line for line in shared if line.code not in {x.code for x in lines}]
        if lines:
            _add_errors(operation, lines, components)

    for path in sorted((directory / "examples").glob("*.json")):
        example = json.loads(path.read_text(encoding="utf-8"))
        method, _, route = example["operation"].partition(" ")
        where = f"examples/{path.name}"
        if path.name != example_file_name(method, route):
            raise ContentError(f"{where}: the file is named for '{example['operation']}'")
        operation = _find(document, method, route, where, strict=strict)
        if operation is not None:
            _add_example(operation, example, where)
    return document


def _operations(document: dict) -> Iterator[tuple[str, str, dict]]:
    for path, item in document.get("paths", {}).items():
        for method, operation in item.items():
            if method.upper() in METHODS:
                yield method.upper(), path, operation


def install(application: Any, directory: Path = CONTENT_DIR) -> None:
    """Have ``application.openapi()`` answer the document with the content merged in, built once. The
    merge is not strict: an instance that switches an optional surface off has no routes for its text.
    ``application.state.generated_openapi`` keeps the unmerged generator for the tests' strict merge."""
    generate = application.openapi
    application.state.generated_openapi = generate

    def openapi() -> dict[str, Any]:
        if application.openapi_schema is None:
            document = generate()
            # Until the merge succeeds the generated document is not the answer: a failed merge raises
            # again on the next call instead of serving the document without its text.
            application.openapi_schema = None
            application.openapi_schema = merge_content(document, directory, strict=False)
        return application.openapi_schema

    application.openapi = openapi
