"""The management API's reference is complete, and stays so (V-D6).

The reference text (``app/management/reference/content/``) documents every operation of the management
API, with every optional surface switched on. These tests fail when something is added without its text:

- every operation has a section in its area's file and a recorded example;
- every parameter and every schema field has a description;
- text, examples and notes that name something the document does not have fail when it is built
  (``ContentError``), so no unknown name is left behind;
- no description of the document carries a package, decision or release number (the reader never sees the
  builders' vocabulary);
- every code the backend raises has a catalogue entry, or is listed here as unreachable with the reason;
- every catalogue entry is listed on at least one operation, unless it is badged "Not a response status"
  (job item reasons, notices, problem codes) or is listed below as answered outside this document;
  every code an operation lists has an entry;
- every link of the guide's pages to a tag or an operation of the reference names one the document has;
- no recorded example holds a secret.
"""

import re
from pathlib import Path
from urllib.parse import unquote

import pytest
from test_api_journeys import raised_codes

from app.management.reference import static_site
from app.management.reference.content import CONTENT_DIR, METHODS, example_file_name, parse_area

APP = Path(__file__).resolve().parents[1] / "app"
GUIDE = Path(__file__).resolve().parents[2] / "guide" / "src" / "content"
# Raised in the code, never answered: each has no entry.
UNREACHABLE = {
    "AI_ASSISTANT_ROLE_CHANGED": "caught in a background job; only its message is kept",
    "CHANGE_SET_SOURCE_INVALID": "the request schema refuses the same cases first",
    "CHILD_TYPE_NOT_ALLOWED": "reported inside a restructuring plan under another name",
    "REQUIRED_RELATION_WITHOUT_PLACE": "reported inside a restructuring plan under another name",
    "ROUTE_NOT_DECLARED": "every route declares its action; the contract test refuses one that does not",
    "WRITER_UNKNOWN": "an internal guard: the writer is always set first",
}
# Answered, and in the catalogue, but by no operation of this document.
CONSUMER_READ = [
    "AMBIGUOUS_MATCH",
    "AMBIGUOUS_TARGET",
    "INVALID_AS_OF",
    "INVALID_EXPECT",
    "INVALID_PAGE_SIZE",
    "INVALID_PAYLOAD",
    "LIST_NOT_FOUND",
    "MULTIPLE_TARGETS",
    "NO_MATCH",
    "OPERATION_NOT_OFFERED",
    "PUBLICATION_CONTRACT_MISMATCH",
    "QUERY_OR_ID_REQUIRED",
    "QUERY_REQUIRED",
    "QUERY_TOO_BROAD",
    "TARGET_NOT_FOUND",
    "TOO_MANY_TERMS",
    "UNKNOWN_INCLUDE",
]
ANSWERED_ELSEWHERE = {
    **dict.fromkeys(
        CONSUMER_READ, "the consumer read API (`/api/consumer`), which this reference leaves out"
    ),
    **dict.fromkeys(
        ["INVALID_DATE", "RESOURCE_NOT_FOUND", "LIST_REQUIRED", "OBJECT_ID_REQUIRED"],
        "the assistant tools (MCP), which are not management operations",
    ),
    "TOO_MANY_PASSKEYS": "the sign-in page's passkey endpoint, not a management operation",
}
_LINK = re.compile(r"#tag/([^)\s\"'>]+)")
_BADGE = re.compile(
    r"^### ([A-Z][A-Z0-9_]*)\n\n<span class=\"rdm-status [^\"]*\">(.*?)</span>", re.MULTILINE
)
_LISTED = re.compile(r"\[`([A-Z0-9_]+)`\]\(#management/description/")
# The conditional forms the journeys' extraction does not read: ``409 if stale else 422, "CODE"`` and
# ``"CODE_A" if cond else "CODE_B"``.
_CONDITIONAL_STATUS = re.compile(
    r"(?:[Ee]rror|[Rr]efusal|_refuse)\(\s*(?:status_code=)?\d{3}\s+if\s+[^,]+?\s+else\s+\d{3}\s*,"
    r"\s*(?:code=)?[\"']([A-Z][A-Z_]+)[\"']"
)
_CONDITIONAL_CODE = re.compile(
    r"[\"']([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)[\"']\s+if\s+[^\n]*?\s+else\s+"
    r"[\"']([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)[\"']"
)
# What the builders call things, which no description may carry: a release number (``0.12``), a schema
# version (``Schema 0.7``), a decision (``D310``, ``C-D103``, ``PP-D28``), an ADR, a package (``U5a``,
# ``AP2``), a document (``CONSUMER_API``) or a section sign. Code spans are left out: they hold values.
_BUILDERS = re.compile(
    r"(?<![\w.:!/-])0\.\d{1,2}(?![\.\d\w])"
    r"|[Ss]chema 0\.\d+"
    r"|\b(?:[A-Z]{1,3}-)?D\d{1,3}[a-z]?\b"
    r"|\bADR-\d+"
    r"|(?<![\w.:!/-])[A-Z]{1,3}\d{1,3}[a-z]?(?![\w:!])"
    r"|\b(?:CONSUMER|INTEGRATION)_API\b(?!_)"
    r"|§"
)
_CODE_SPAN = re.compile(r"`[^`]*`")
_SECRETS = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.|-----BEGIN|Bearer [A-Za-z0-9._-]{10,}|rdmwh_(?!example-signing-secret)"
)


@pytest.fixture(scope="module")
def document() -> dict:
    # Strict: a section, example or note naming something the all-capabilities document lacks fails here.
    return static_site._management_document(strict=True)


def _operations(document: dict):
    for path, item in document["paths"].items():
        for method, operation in item.items():
            if method.upper() in METHODS:
                yield method.upper(), path, operation


def _entries() -> dict[str, str]:
    """Each catalogue entry's code and the badge it carries."""
    return dict(_BADGE.findall((CONTENT_DIR / "errors.md").read_text(encoding="utf-8")))


def _listed(document: dict) -> set[str]:
    """The codes the operations list in their responses."""
    return {
        code
        for _, _, operation in _operations(document)
        for response in operation.get("responses", {}).values()
        for code in _LISTED.findall(response.get("description", ""))
    }


# The codes of a model compatibility check and of a migration's items are not raised: the first are handed
# to ``_append_counted`` and ``_append_records``, the second are written in the migration's SQL
# (``THEN 'CODE'``, ``lost_code = 'CODE'``, ``'code', 'CODE'``) and in a constant. A publication's
# merge conflict names its code in a dict.
_DIAGNOSTICS = re.compile(
    r"_append_(?:counted|records)\((?:[^\"'()]|\([^()]*\))*?\"([A-Z][A-Z_]+)\""
)
_MIGRATION_ITEM = re.compile(
    r"(?:THEN|ELSE|lost_code\s*=|'code',)\s*'([A-Z][A-Z0-9_]{3,})'|^[A-Z_]+ = \"([A-Z][A-Z_]{5,})\"$",
    re.MULTILINE,
)
_DICT_CODE = re.compile(r"\"code\":\s*\"([A-Z][A-Z_]+)\"")
_REASON = re.compile(
    r"(?:_reason|problem|ModelReferenceError|ModelDiagnostic)\(\s*(?:\"warning\",\s*)?\"([A-Z][A-Z_]+)\""
)
_REASON_KEY = re.compile(r"\"reason\":\s*\"([A-Z][A-Z_]+)\"")
_DB_CODE = re.compile(r"(?:,\s*|code: str = )\"((?:DATABASE_[A-Z_]+))\"")
_REFUSED = re.compile(r"(?:'code',\s*|\bor )[\"']?(REFUSED)[\"']?")
_FAMILIES = {
    # compatibility, migration items, the publication's merge conflict and whole-graph check
    "engine/model/compatibility.py": (_DIAGNOSTICS,),
    "engine/model/migrations.py": (_MIGRATION_ITEM,),
    "engine/model/change_set_migrations.py": (_MIGRATION_ITEM,),
    "engine/change_sets/publish.py": (_DICT_CODE,),
    "engine/change_sets/validation.py": (_DICT_CODE,),
    # a move's reasons and left-behind values, a mapping's problems
    "engine/moves/move_binding.py": (_REASON, _MIGRATION_ITEM),
    "engine/moves/move_job.py": (_MIGRATION_ITEM,),
    "engine/moves/move_load.py": (_DICT_CODE,),
    "engine/moves/mapping_check.py": (_REASON, _REASON_KEY),
    # an import's row errors
    "engine/imports/binding.py": (_MIGRATION_ITEM,),
    # a draft's profile warnings, the assistant's check, the dry run of items
    "engine/sources/draft_profile.py": (_REASON,),
    "engine/sources/inference/run.py": (_REASON,),
    "engine/tasks/draft_plan.py": (_DICT_CODE,),
    "engine/tasks/design_job.py": (_DICT_CODE,),
    "engine/sources/items_summary.py": (_REFUSED,),
    "engine/model/authoring/draft_migration.py": (_DICT_CODE,),
    # a model's own findings: consumer contracts, validation, a subscription's suspension, a rehearsal
    "engine/model/consumer_contract.py": (_MIGRATION_ITEM,),
    "engine/model/validation/application_rules.py": (_REASON,),
    "engine/model/validation/consumer_api_rules.py": (_REASON,),
    "engine/model/consumer_expansion.py": (_REASON,),
    "engine/events/subscription_rules.py": (_MIGRATION_ITEM,),
    "db.py": (_DB_CODE,),
    "engine/backups/rehearsal.py": (_MIGRATION_ITEM,),
}


def reference_codes() -> set[str]:
    """Every code the backend raises: the journeys' extraction, the conditional forms, the diagnostics of
    a compatibility check, a migration's, a move's and an import's item codes, a publication's conflicts and
    graph check, a draft's warnings and a rehearsal's failures (``_FAMILIES``: the files that write codes
    that are not raised)."""
    codes = set(raised_codes())
    for name, patterns in _FAMILIES.items():
        source = (APP / name).read_text(encoding="utf-8")
        for pattern in patterns:
            for found in pattern.findall(source):
                codes.update(
                    item for item in (found if isinstance(found, tuple) else (found,)) if item
                )
    for path in APP.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        codes.update(_CONDITIONAL_STATUS.findall(source))
        for pair in _CONDITIONAL_CODE.findall(source):
            codes.update(pair)
    return codes


def test_every_operation_has_its_section_and_its_example(document):
    sections = {
        (section.method, section.path)
        for path in CONTENT_DIR.glob("*.md")
        if path.name not in {"index.md", "errors.md", "README.md"}
        for section in parse_area(path.read_text(encoding="utf-8"), path.name).operations
    }
    lacking = []
    for method, path, _ in _operations(document):
        if (method, path) not in sections:
            lacking.append(f"{method} {path}: no section")
        if not (CONTENT_DIR / "examples" / example_file_name(method, path)).is_file():
            lacking.append(f"{method} {path}: no example")
    assert not lacking, lacking[:20]


def test_every_parameter_and_schema_field_is_described(document):
    lacking = []
    for method, path, operation in _operations(document):
        for parameter in operation.get("parameters", []):
            if not parameter.get("description"):
                lacking.append(f"{method} {path}: {parameter['name']}")
    for schema, body in document["components"]["schemas"].items():
        for field, definition in body.get("properties", {}).items():
            if not definition.get("description"):
                lacking.append(f"{schema}.{field}")
    assert not lacking, lacking[:20]


def _descriptions(value, where: str = ""):
    """Every description and summary of the document, with where it is."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("description", "summary") and isinstance(item, str):
                yield where, item
            elif key not in ("examples", "example", "default", "enum", "const", "title"):
                yield from _descriptions(item, f"{where}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _descriptions(item, f"{where}[{index}]")


def test_no_description_carries_a_package_or_decision_id(document):
    found = []
    for where, text in _descriptions(document):
        # Fenced samples hold JSON, and code spans hold values: neither names a package.
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for match in _BUILDERS.finditer(_CODE_SPAN.sub("", text)):
            found.append(f"{where}: {match.group(0)}")
    assert not found, found[:20]


def test_the_identifier_pattern_finds_what_it_is_for():
    for text in (
        "as it was (0.12 NT1)",
        "the rule (D310)",
        "the plan (C-D103)",
        "a request (U5a)",
        "the tier (CONSUMER_API)",
        "Schema 0.7: a tree",
        "see ADR-030",
        "the older reading (§B4)",
    ):
        assert _BUILDERS.search(text), text
    for text in (
        "a range such as A3:C12",
        "`0.10` is the version",
        "Prometheus text format 0.0.4",
        "the code CONSUMER_API_NOT_FOUND",
        "SHA-256 and UTF-8",
    ):
        assert not _BUILDERS.search(_CODE_SPAN.sub("", text)), text


def test_every_raised_code_has_a_catalogue_entry():
    entries = set(_entries())
    missing = sorted(reference_codes() - entries - set(UNREACHABLE))
    assert not missing, f"no entry in errors.md: {missing}"
    # The extraction finds the conditional forms and the families that are not raised.
    assert {
        "RELATION_BATCH_REFUSED",
        "APPLICATION_IN_USE",
        "REQUIRED_ATTRIBUTE_MISSING",
        "VALUE_NOT_CONVERTIBLE",
        "VERSION_MISMATCH",
        "ID_COLLISION",
        "RELATION_CARDINALITY_VIOLATION",
        "TYPE_NOT_MAPPED",
        "BINDING_NOT_ALLOWED",
        "REFERENCE_CYCLE",
        "INFERENCE_DISAGREES",
        "ROWS_SKIPPED",
        "DUPLICATE_KEY",
        "DELIVERY_FAILED",
        "WORKSPACES_NOT_SERVED",
        "DATABASE_COLLATION",
    } <= reference_codes()


def test_the_unreachable_codes_are_not_in_the_catalogue():
    assert not set(_entries()) & set(UNREACHABLE)
    assert set(UNREACHABLE) <= reference_codes()


def test_every_catalogue_entry_is_listed_on_an_operation_and_every_listed_code_has_an_entry(
    document,
):
    entries, listed = _entries(), _listed(document)
    assert not listed - set(entries), sorted(listed - set(entries))
    exempt = {code for code, badge in entries.items() if badge == "Not a response status"}
    unlisted = sorted(set(entries) - listed - exempt - set(ANSWERED_ELSEWHERE))
    assert not unlisted, f"listed on no operation: {unlisted}"
    # An exemption ends when the code is documented: it may not outlive it.
    assert set(ANSWERED_ELSEWHERE) <= set(entries)
    assert not set(ANSWERED_ELSEWHERE) & listed, sorted(set(ANSWERED_ELSEWHERE) & listed)
    assert not exempt & listed, sorted(exempt & listed)


def test_every_guide_link_to_the_reference_names_a_tag_or_operation_it_has(document):
    tags = {tag["name"] for tag in document["tags"]}
    operations = {
        (tag, method, path)
        for method, path, operation in _operations(document)
        for tag in operation.get("tags", [])
    }
    broken = []
    for page in sorted(GUIDE.rglob("*")):
        if not page.is_file():
            continue
        for link in _LINK.findall(page.read_text(encoding="utf-8", errors="ignore")):
            tag, _, rest = unquote(link).partition("/")
            where = page.relative_to(GUIDE).as_posix()
            if tag not in tags:
                broken.append(f"{where}: {tag}")
            elif rest:
                method, _, route = rest.partition("/")
                if (tag, method, "/" + route) not in operations:
                    broken.append(f"{where}: {tag}/{rest}")
    assert not broken, broken


def test_no_recorded_example_holds_a_secret():
    held = [
        f"{path.name}: {found.group(0)[:20]}"
        for path in sorted((CONTENT_DIR / "examples").glob("*.json"))
        if (found := _SECRETS.search(path.read_text(encoding="utf-8")))
    ]
    assert not held, held
