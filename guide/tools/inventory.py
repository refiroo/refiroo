"""The guide's inventory of what refiroo can do, read from the code (CP step 1, 2 and 2a's list).

Run from anywhere with the backend's interpreter; no database and no server are needed:

    backend/.venv/bin/python guide/tools/inventory.py

It writes ``guide/_coverage/inventory/<kind>.json`` (one list of entries per kind) and
``guide/_coverage/inventory/gaps.md``. ``node guide/tools/check.mjs coverage`` reads the JSON.

An entry is ``{kind, key, labels[], source, section}`` plus optional fields:

* ``context``  words of which at least one must also stand on the page for a label to count (a weak
               label such as "Rename" or "--json" means nothing without the thing it belongs to);
* ``summary``  a human line (not matched);
* ``weak``     true where the labels are generic, so a "covered" result is only a hint.

``section`` is the guide section that owns the entry: run, administer, model, use, integrate, about.
The mapping is mine, kept in one place per kind below (SECTION_*); change it there.

    settings      group runtime/capabilities/limits/ai -> run; webhooks -> integrate
    management    by OpenAPI tag: security/mail/ai/agent-access -> administer; system, health -> run;
                  model, model mappings -> model; oauth -> integrate; everything else a person does
                  in a workspace -> use
    mcp           integrate          consumer: integrate          commands, deployment: run
    permissions   administer
    screens       workspace screens, menus, dialogs -> use; Settings pages by their topic (see
                  SETTINGS_PAGE_SECTION); model editor operations, tabs -> model
    model features  model

Coverage is by key or label text, so an API operation's label is its path (``{...}`` placeholders are
compared without their names), a setting's key is its name, and so on.
"""

from __future__ import annotations

import ast
import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
OUT = REPO / "guide" / "_coverage" / "inventory"
sys.path.insert(0, str(BACKEND))
# app.main builds the application at import and refuses to without these; nothing connects.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://inventory:inventory@localhost/inventory"
)
os.environ.setdefault("SECRETS_ENCRYPTION_KEY", "x" * 43 + "=")
# Every gated capability is on, so the inventory lists every operation the code can serve (model drafts,
# jobs and imports, consumer subscriptions...). Job files go to a scratch directory, never an instance's.
for _name in (
    "MODEL_ADMIN_MUTATIONS_ENABLED",
    "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
    "INTEGRATION_JOBS_ENABLED",
    "CONSUMER_SUBSCRIPTIONS_ENABLED",
):
    os.environ[_name] = "true"
os.environ["JOB_FILE_DIR"] = tempfile.mkdtemp(prefix="rdm-inventory-")
atexit.register(shutil.rmtree, os.environ["JOB_FILE_DIR"], ignore_errors=True)

SECTIONS = ("run", "administer", "model", "use", "integrate", "about")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def find_line(path: Path, *needles: str) -> int:
    """The first line of ``path`` holding any needle; 1 when none does."""
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if any(needle in line for needle in needles):
            return number
    return 1


def entry(kind: str, key: str, labels: list[str], source: str, section: str, **extra) -> dict:
    assert section in SECTIONS, (kind, key, section)
    return {
        "kind": kind,
        "key": key,
        "labels": sorted({label for label in labels if label}),
        "source": source,
        "section": section,
        **{name: value for name, value in extra.items() if value not in (None, [], "")},
    }


def words(text: str) -> int:
    return len(text.split())


# --- settings --------------------------------------------------------------------------------------

SECTION_SETTINGS = {
    "runtime": "run",
    "capabilities": "run",
    "limits": "run",
    "ai": "run",
    "webhooks": "integrate",
}


def settings() -> list[dict]:
    from app.config import SETTINGS_CATALOGUE

    path = BACKEND / "app" / "config.py"
    return [
        entry(
            "settings",
            item.name,
            [],
            f"{rel(path)}:{find_line(path, f'"{item.name}"')}",
            SECTION_SETTINGS[item.group],
            summary=item.description,
            group=item.group,
        )
        for item in SETTINGS_CATALOGUE
    ]


# --- management API and MCP --------------------------------------------------------------------------

SECTION_TAG = {
    "security": "administer",
    "mail": "administer",
    "ai": "administer",
    "agent-access": "administer",
    "system": "run",
    "model": "model",
    "model mappings": "model",
    "oauth": "integrate",
}


def management_section(tags: list[str], path: str) -> str:
    if path.startswith(("/health", "/.well-known")):
        return "run" if path.startswith("/health") else "integrate"
    for tag in tags:
        if tag in SECTION_TAG:
            return SECTION_TAG[tag]
    return "use"


def path_label(path: str) -> str:
    return path


def management() -> list[dict]:
    from app.main import app

    document = app.openapi()
    # Routers are included lazily: walk them to find the function behind each operation.
    found = []

    def collect(routes):
        for route in routes:
            inner = getattr(route, "original_router", None)
            if inner is not None:
                collect(inner.routes)
            elif getattr(route, "endpoint", None) is not None:
                found.append(route)

    collect(app.routes)

    def behind(method: str, path: str, operation_id: str):
        options = [
            route
            for route in found
            if method.upper() in (route.methods or ())
            and path.endswith(route.path)
            and operation_id.startswith(route.endpoint.__name__ + "_")
        ]
        return max(options, key=lambda route: len(route.path), default=None)

    entries = []
    for path, item in document["paths"].items():
        for method, operation in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            route = behind(method, path, operation.get("operationId", ""))
            source = "backend/app/main.py"
            endpoint = getattr(route, "endpoint", None)
            if endpoint is not None:
                code = endpoint.__code__
                source = f"{rel(Path(code.co_filename))}:{code.co_firstlineno}"
            entries.append(
                entry(
                    "management-api",
                    f"{method.upper()} {path}",
                    [path_label(path)],
                    source,
                    management_section(operation.get("tags", []), path),
                    operationId=operation.get("operationId"),
                    summary=operation.get("summary"),
                    # FastAPI words a summary from the function's name when the code gives none; a summary
                    # that differs from that form was written in the code.
                    writtenSummary=(
                        operation.get("summary") != endpoint.__name__.replace("_", " ").title()
                        if endpoint is not None
                        else None
                    ),
                    tags=operation.get("tags"),
                )
            )
    return entries


def mcp() -> list[dict]:
    from app.management import mcp_tools

    path = BACKEND / "app" / "management" / "mcp_tools.py"
    entries = []
    for tool in (*mcp_tools.TOOLS, mcp_tools.READ_RESOURCE):
        entries.append(
            entry(
                "mcp-tool",
                tool.name,
                [],
                f"{rel(path)}:{find_line(path, f'"{tool.name}"')}",
                "integrate",
                summary=tool.description,
                group=tool.group,
                writes=tool.writes,
            )
        )
    return entries


# --- consumer API ----------------------------------------------------------------------------------


def consumer() -> list[dict]:
    from pathlib import Path as P

    from app.consumer.router import PREFIX
    from app.engine.model.consumer_definitions import consumer_api
    from app.engine.model.consumer_openapi import consumer_openapi
    from app.engine.model.loader import load_model

    router = BACKEND / "app" / "consumer" / "router.py"
    entries = []
    text = router.read_text()
    for match in re.finditer(r'@router\.(get|post|put|patch|delete)\("([^"]*)"', text):
        method, route = match.groups()
        line = text[: match.start()].count("\n") + 1
        full = f"{PREFIX}{route}"
        entries.append(
            entry(
                "consumer-api",
                f"{method.upper()} {full}",
                [full],
                f"{rel(router)}:{line}",
                "integrate",
                generic=True,
            )
        )
    model_path = REPO / "guide" / "samples" / "model.json"
    assert model_path.is_file(), model_path
    model = load_model(P(model_path))
    definition = consumer_api(model, "stops")
    assert definition is not None, "the reference model has no consumer API 'stops'"
    document = consumer_openapi(
        model, definition, root_path="", resolve_max_items=50, token_url="/oauth/token"
    )
    for path, item in document["paths"].items():
        for method, operation in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            entries.append(
                entry(
                    "consumer-api",
                    f"{method.upper()} {path}",
                    [path],
                    f"{rel(model_path)} (consumer_openapi, api 'stops')",
                    "integrate",
                    summary=operation.get("summary"),
                )
            )
    return entries


# --- commands --------------------------------------------------------------------------------------


def commands() -> list[dict]:
    entries = []
    for path in sorted((BACKEND / "app" / "cli").glob("*.py")):
        if path.name == "__init__.py":
            continue
        module = path.stem
        key = f"app.cli.{module}"
        tree = ast.parse(path.read_text())
        doc = (ast.get_docstring(tree) or "").split("\n\n")[0].replace("\n", " ")
        entries.append(entry("command", key, [module], f"{rel(path)}:1", "run", summary=doc))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument":
                flags = [
                    a.value
                    for a in node.args
                    if isinstance(a, ast.Constant) and isinstance(a.value, str)
                ]
                help_text = next(
                    (
                        k.value.value
                        for k in node.keywords
                        if k.arg == "help" and isinstance(k.value, ast.Constant)
                    ),
                    "",
                )
                for flag in flags:
                    entries.append(
                        entry(
                            "command",
                            f"{key} {flag}",
                            [flag],
                            f"{rel(path)}:{node.lineno}",
                            "run",
                            context=[module, key],
                            summary=help_text,
                        )
                    )
    return entries


# --- permissions -----------------------------------------------------------------------------------


def permissions() -> list[dict]:
    from app.engine.authorization import catalogue

    path = BACKEND / "app" / "engine" / "authorization" / "catalogue.py"
    entries = []
    for key, group in catalogue.GROUPS.items():
        entries.append(
            entry(
                "permission",
                f"group:{key}",
                [group.name, key],
                f"{rel(path)}:{find_line(path, f'"{key}",')}",
                "administer",
                summary=group.description,
                commonContext=["permission", "group", "role"],
            )
        )
    for key, action in catalogue.ACTIONS.items():
        entries.append(
            entry(
                "permission",
                f"action:{key}",
                [key, action.doing],
                f"{rel(path)}:{find_line(path, f'"{key}",')}",
                "administer",
                summary=action.description,
                groups=list(action.groups),
                commonContext=["permission", "action", "group", "role"],
            )
        )
    for key, groups in catalogue.PREDEFINED_ROLES.items():
        entries.append(
            entry(
                "permission",
                f"role:{key}",
                [key, key.replace("-", " ")],
                f"{rel(path)}:{find_line(path, f'    "{key}":')}",
                "administer",
                summary="Groups: " + ", ".join(groups),
                commonContext=["role", "group", "permission"],
            )
        )
    entries.append(
        entry(
            "permission",
            "agent-ceiling",
            ["ceiling"],
            f"{rel(path)}:{find_line(path, 'AGENT_CEILING')}",
            "administer",
            summary="The most an assistant token holds: "
            + ", ".join(sorted(catalogue.AGENT_CEILING)),
            context=["agent", "assistant"],
        )
    )
    return entries


# --- screens, editor operations, menus, dialogs ------------------------------------------------------

SETTINGS_PAGE_SECTION = {
    "index": "use",  # Settings opens on an index of its pages (0.17 SH1)
    "about": "run",
    "appearance": "use",
    "account": "use",
    "notifications": "use",
    "deployment": "run",
    "operations": "run",
    "ai": "run",
    "mail-template": "run",  # the e-mail template, an operator's page (0.17 MT1)
    "mail": "administer",
    "people": "administer",
    "groups": "administer",
    "roles": "administer",
    "clients": "administer",
    "sign-in": "administer",
    "signing-keys": "administer",
    "agent-access": "administer",
    "consumer-apis": "integrate",
    "api-reference": "integrate",
    "webhooks": "integrate",
    "model": "model",
    "workspaces": "model",
    "jobs": "use",
    "moves": "use",
    "import-profiles": "use",
    "ai-tasks": "use",
}
# The words a reader sees for a route that has no Settings label (kept here: the code has none).
ROUTE_LABELS = {
    "changeSets": ["Change sets"],
    "publications": ["Publications"],
    "home": ["Home"],
    "notifications": ["Notifications"],
    "changes": ["Changes"],
}
TAB_OWNER = {
    "ModelTab": ("model", "model"),
    "WorkspaceTab": ("workspace", "model"),
    "ConsumerApiTab": ("consumer API", "model"),
}
ON_WORDS = {
    "draft": ["model"],
    "application": ["application"],
    "objectType": ["type", "record type"],
    "view": ["view"],
    "attribute": ["attribute"],
    "attributeType": ["attribute type"],
    "relationType": ["relation type"],
    "relation": ["relation"],
    "group": ["navigation group", "group"],
    "consumerApis": ["consumer API"],
    "consumerApi": ["consumer API"],
    "consumerItem": ["consumer API"],
}


def file_section(source: str) -> str:
    low = source.lower()
    if "model-editor" in low or "settings/model" in low or "/model/" in low:
        return "model"
    if re.search(
        r"settings/(mail|people|group|role|client|signin|signingkey|agentaccess|security)", low
    ):
        return "administer"
    if re.search(r"settings/(webhook|consumerapi|apireference)", low):
        return "integrate"
    if re.search(r"settings/(deployment|operations|ai\b|aipage|about)", low):
        return "run"
    return "use"


def ts() -> dict:
    result = subprocess.run(
        ["node", str(REPO / "guide" / "tools" / "inventory-ts.mjs")],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def screens(data: dict) -> list[dict]:
    entries = []
    routes = data["routes"]
    nav = {item["page"]: item for item in routes["navigation"]}
    seen = set()
    for item in routes["kinds"]:
        if item["value"] in seen or item["value"] == "settings":
            continue
        seen.add(item["value"])
        entries.append(
            entry(
                "screen",
                f"route:{item['value']}",
                ROUTE_LABELS.get(item["value"], []),
                item["source"],
                "use",
                routeKind=True,
                # A route's label is a page's name, often one word ("Home"): it counts where a page names it as a page.
                commonContext=["page", "screen"],
            )
        )
    for item in routes["pages"]:
        page = item["value"]
        labels = [nav[page]["label"]] if page in nav else []
        entries.append(
            entry(
                "screen",
                f"settings:{page}",
                labels,
                nav[page]["source"] if page in nav else item["source"],
                SETTINGS_PAGE_SECTION[page],
                context=["Settings"],
                weak=True if labels else None,
            )
        )
    for item in routes["tabs"]:
        owner, section = TAB_OWNER[item["owner"]]
        entries.append(
            entry(
                "screen",
                f"tab:{item['owner']}:{item['value']}",
                [item["value"].replace("-", " ").capitalize()],
                item["source"],
                section,
                context=[owner],
                weak=True,
            )
        )
    for op in data["operations"]:
        labels = list(op["labels"])
        labels += [title for title in op["titles"] if words(title) >= 2 and title not in labels]
        specific = [label for label in labels if words(label) >= 3]
        weak = not specific
        entries.append(
            entry(
                "screen",
                f"operation:{op['id']}",
                labels,
                op["source"],
                "model",
                context=None if specific else ON_WORDS.get(op["on"], []),
                weak=True if weak else None,
                on=op["on"],
                buildKinds=op["buildKinds"],
            )
        )
    taken: dict[str, int] = {}

    def unique(key: str) -> str:
        taken[key] = taken.get(key, 0) + 1
        return key if taken[key] == 1 else f"{key}#{taken[key]}"

    def file_of(source: str) -> str:
        return source.rsplit(":", 1)[0].split("/")[-1]

    for index, menu in enumerate(data["menus"]):
        key = unique(f"menu:{file_of(menu['source'])}:{menu['id'] or 'item'}")
        entries.append(
            entry(
                "screen",
                key,
                menu["labels"],
                menu["source"],
                file_section(menu["source"]),
                weak=True if all(words(l) < 2 for l in menu["labels"]) else None,
                commonContext=file_context(menu["source"]),
            )
        )
    for item in data["confirms"]:
        labels = item["confirmLabels"] + item["titles"]
        name = (item["confirmLabels"] or item["titles"] or ["dialog"])[0]
        entries.append(
            entry(
                "screen",
                unique(f"confirm:{file_of(item['source'])}:{name}"),
                labels,
                item["source"],
                file_section(item["source"]),
                commonContext=file_context(item["source"]),
            )
        )
    return entries


# --- model features --------------------------------------------------------------------------------

GENERIC_LEAVES = {
    "key",
    "name",
    "title",
    "description",
    "type",
    "order",
    "label",
    "id",
    "config",
    "visible",
    "region",
    "value",
    "kind",
    "labels",
    "fields",
    "items",
}


def flatten_schema() -> list[dict]:
    """Every property path of the model document: ``applications[].views[].config.pageSize``."""
    from app.models.schema import EngineModel

    schema = EngineModel.model_json_schema()
    defs = schema.get("$defs", {})
    found: dict[str, dict] = {}

    def resolve(node):
        while isinstance(node, dict) and "$ref" in node:
            node = defs[node["$ref"].split("/")[-1]]
        return node

    def variants(node):
        node = resolve(node)
        if not isinstance(node, dict):
            return []
        for combiner in ("anyOf", "oneOf", "allOf"):
            if combiner in node:
                return [v for sub in node[combiner] for v in variants(sub)]
        return [node]

    def describe(node) -> str:
        node = resolve(node) if isinstance(node, dict) else node
        if not isinstance(node, dict):
            return "any"
        if "const" in node:
            return f"const {node['const']!r}"
        if "enum" in node:
            return "one of " + ", ".join(map(str, node["enum"]))
        return node.get("type", "object")

    def walk(node, path: str, trail: tuple[str, ...], owner: str):
        for variant in variants(node):
            if variant.get("type") == "array" and "items" in variant:
                walk(variant["items"], path + "[]", trail, owner)
                continue
            props = variant.get("properties")
            if props is None:
                extra = variant.get("additionalProperties")
                if isinstance(extra, dict) and extra:
                    walk(extra, path + ".{}", trail, owner)
                continue
            title = variant.get("title", owner)
            if title in trail:
                continue
            for name, sub in props.items():
                child = f"{path}.{name}" if path else name
                kinds = [describe(v) for v in variants(sub)] or ["any"]
                slot = found.setdefault(
                    child,
                    {
                        "path": child,
                        "types": set(),
                        "owner": title,
                        "description": sub.get("description", ""),
                    },
                )
                slot["types"].update(kinds)
                walk(sub, child, trail + (title,), title)

    walk(schema, "", (), "EngineModel")
    return [found[path] for path in sorted(found)]


def model_features() -> list[dict]:
    path = BACKEND / "app" / "models" / "schema.py"
    text = path.read_text()
    entries = []
    for item in flatten_schema():
        leaf = item["path"].split(".")[-1].replace("[]", "")
        parent = re.sub(r"\[\]|\.\{\}", "", item["path"]).split(".")
        parent_name = parent[-2] if len(parent) > 1 else parent[0]
        generic = leaf in GENERIC_LEAVES
        lines = text.splitlines()
        start = next(
            (n for n, l in enumerate(lines) if re.match(rf"class {re.escape(item['owner'])}\b", l)),
            0,
        )
        line = next(
            (
                n
                for n, l in enumerate(lines[start:], start + 1)
                if re.match(rf"\s+{re.escape(leaf)}\s*:", l)
            ),
            start + 1,
        )
        entries.append(
            entry(
                "model-feature",
                item["path"],
                [leaf],
                f"{rel(path)}:{line} ({item['owner']})",
                "model",
                context=[parent_name, parent_name.rstrip("s")] if generic else None,
                weak=True if generic else None,
                commonContext=[parent_name, parent_name.rstrip("s")] if len(parent) > 1 else ["model"],
                types=sorted(item["types"]),
            )
        )
    return entries


# A label that is one common word ("Delete", "view", "security") proves nothing on its own: the check
# (``tools/check.mjs``) counts it only on a page that also names one of the entry's ``commonContext`` words.
GENERIC_FILE_WORDS = {"page", "panel", "view", "list", "detail", "board", "card", "pane", "dialog", "menu", "tab", "shell", "app", "tsx", "ts"}


def file_context(source: str) -> list[str]:
    """Words of the source file's name that say where a control stands (``ModelReleaseDetail.tsx`` ->
    model, release); ``menu`` for a file with none."""
    name = source.rsplit(":", 1)[0].split("/")[-1].split(".")[0]
    found = [w.lower() for w in re.findall(r"[A-Z][a-z0-9]+|[a-z0-9]+", name)]
    specific = [w for w in found if w not in GENERIC_FILE_WORDS]
    # A generic word beside a specific one still says where the control stands (PanelTools -> tools, panel).
    places = [w for w in found if w in GENERIC_FILE_WORDS and w not in {"tsx", "ts", "app", "shell"}]
    return specific + places if specific else ["menu"]


def mail_kinds() -> list[dict]:
    """The message kinds the engine sends (``KINDS`` in ``engine/mail/templates.py``)."""
    path = BACKEND / "app" / "engine" / "mail" / "templates.py"
    text = path.read_text()
    names = re.search(r"^KINDS = \(([^)]*)\)", text, re.MULTILINE).group(1)
    entries = []
    for constant in [n.strip() for n in names.split(",") if n.strip()]:
        match = re.search(rf'^{constant} = "([^"]+)"', text, re.MULTILINE)
        entries.append(
            entry(
                "mail-kind",
                f"mail:{match.group(1)}",
                [match.group(1)],
                f"{rel(path)}:{find_line(path, f'{constant} = ')}",
                "administer",
                context=None,
                commonContext=["mail", "message", "e-mail", "email"],
            )
        )
    return entries


def search_fields() -> list[dict]:
    """A search or find box of the frontend: a ``label``/``placeholder`` that starts with Find or Search."""
    pattern = re.compile(r'(?:label|placeholder)="((?:Find|Search)[^"{}]*)"')
    found: dict[str, dict] = {}
    for path in sorted((REPO / "frontend" / "src").rglob("*.tsx")):
        if path.name.endswith(".test.tsx"):
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            for label in pattern.findall(line):
                found.setdefault(
                    label,
                    entry(
                        "search-field",
                        f"search:{label}",
                        [label],
                        f"{rel(path)}:{number}",
                        file_section(rel(path)),
                        commonContext=file_context(rel(path)),
                    ),
                )
    return list(found.values())


def build_args() -> list[dict]:
    """The ``ARG`` lines of the Dockerfiles: values an operator may set when building the image."""
    entries = []
    for path in sorted(REPO.glob("*/Dockerfile")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            match = re.match(r"ARG ([A-Z][A-Z0-9_]*)(?:=(.*))?$", line)
            if match:
                entries.append(
                    entry(
                        "build-arg",
                        match.group(1),
                        [],
                        f"{rel(path)}:{number}",
                        "run",
                        summary=f"Docker build argument, default {match.group(2) or 'empty'}",
                    )
                )
    return entries


# --- deployment ------------------------------------------------------------------------------------


def deployment() -> list[dict]:
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    Loader.add_constructor("!reset", lambda loader, node: None)
    entries = []
    seen_env: dict[str, str] = {}
    for name in ("compose.yml", "compose.acme.yml"):
        path = REPO / name
        text = path.read_text()
        document = yaml.load(text, Loader=Loader)
        for service, body in (document.get("services") or {}).items():
            entries.append(
                entry(
                    "deployment",
                    f"service:{service}@{name}",
                    [],
                    f"{name}:{find_line(path, f'  {service}:')}",
                    "run",
                    summary=(body or {}).get("image") or "built from this repository",
                    aliases=[service],
                    context=["compose", "docker"],
                )
            )
            body = body or {}
            for volume in body.get("volumes") or []:
                if isinstance(volume, str):
                    host, _, rest = volume.partition(":")
                    if volume.startswith("${"):  # ${VAR:-default}:/path
                        inner, _, rest = volume[2:].partition("}:")
                        variable, _, default = inner.partition(":-")
                        labels = [variable, default]
                    else:
                        labels = [host]
                    target = rest.split(":")[0] if rest else host
                    entries.append(
                        entry(
                            "deployment",
                            f"mount:{service}:{target}@{name}",
                            labels,
                            f"{name}:{find_line(path, target)}",
                            "run",
                            context=["compose", "docker", service],
                        )
                    )
            for port in body.get("ports") or []:
                entries.append(
                    entry(
                        "deployment",
                        f"port:{service}:{port}@{name}",
                        [str(port).split(":")[-1]],
                        f"{name}:{find_line(path, str(port))}",
                        "run",
                        context=["compose", "docker"],
                    )
                )
            for profile in body.get("profiles") or []:
                entries.append(
                    entry(
                        "deployment",
                        f"profile:{profile}@{name}",
                        [profile],
                        f"{name}:{find_line(path, profile)}",
                        "run",
                    )
                )
        for volume in document.get("volumes") or {}:
            entries.append(
                entry(
                    "deployment",
                    f"volume:{volume}@{name}",
                    [volume],
                    f"{name}:{find_line(path, f'  {volume}:')}",
                    "run",
                    context=["volume"],
                )
            )
        # Every variable the file passes or reads: environment keys, ${VAR...} references, env_file.
        variables: dict[str, int] = {}
        for service, body in (document.get("services") or {}).items():
            environment = (body or {}).get("environment") or {}
            if isinstance(environment, list):
                environment = dict(item.split("=", 1) for item in environment)
            for var in environment:
                variables.setdefault(var, find_line(path, f"{var}:"))
        for match in re.finditer(r"\$\{([A-Z][A-Z0-9_]*)", text):
            variables.setdefault(match.group(1), text[: match.start()].count("\n") + 1)
        for var, line in sorted(variables.items()):
            seen_env.setdefault(var, f"{name}:{line}")
            entries.append(
                entry(
                    "deployment",
                    f"env:{var}@{name}",
                    [],
                    f"{name}:{line}",
                    "run",
                    aliases=[var],
                    summary="a variable the Compose file passes or reads",
                )
            )
    caddy = REPO / "caddy" / "Caddyfile"
    for number, line in enumerate(caddy.read_text().splitlines(), 1):
        code = line.split("#")[0].strip()
        if not code:
            continue
        token = code.split()[0].rstrip("{").strip()
        if token in ("}", "{"):
            continue
        entries.append(
            entry(
                "deployment",
                f"caddy:{token}",
                [token],
                f"{rel(caddy)}:{number}",
                "run",
                context=["Caddy"],
            )
        )
    comments = caddy.read_text()
    if "email" in comments:
        entries.append(
            entry(
                "deployment",
                "caddy:email",
                ["email"],
                f"{rel(caddy)}:{find_line(caddy, 'email')}",
                "run",
                context=["Caddy"],
                summary="named in a comment as the global option to be told of expiry",
            )
        )
    return entries


# --- gaps ------------------------------------------------------------------------------------------

OPS_FILES = (
    "operations.ts",
    "layout.ts",
    "matrixView.ts",
    "consumer.ts",
    "TypePreview.tsx",
    "candidates.ts",
)
JSON_OPERATIONS = ("consumer-json", "consumer-item-json")


def gaps(data: dict, features: list[dict], api: list[dict]) -> str:
    evidence = {Path(name).name: sets for name, sets in data["evidence"].items()}
    ops = data["operations"]
    field_ops: dict[str, list[str]] = {}
    for op in ops:
        for name in {f["name"] for f in op["fields"]} | set(op["buildKeys"]):
            field_ops.setdefault(name, []).append(op["id"])
    mentioned: dict[str, list[str]] = {}
    for name in OPS_FILES:
        sets = evidence.get(name, {"names": [], "strings": []})
        for token in set(sets["names"]) | set(sets["strings"]):
            mentioned.setdefault(token, []).append(name)

    matched, uncertain, missing = [], [], []
    keys = [f["key"] for f in features]
    containers = {k for k in keys if any(o.startswith((k + ".", k + "[")) for o in keys)}
    for feature in features:
        leaf = feature["labels"][0]
        path = feature["key"]
        if path in containers:
            continue
        ops_hit = sorted(set(field_ops.get(leaf, [])))
        files = sorted(mentioned.get(leaf, []))
        generic = leaf in GENERIC_LEAVES
        under_consumer = path.startswith("consumerApis")
        if not ops_hit and not files:
            missing.append((path, feature["source"], under_consumer))
        elif generic:
            uncertain.append(
                (
                    path,
                    feature["source"],
                    f"generic name '{leaf}'; ops {ops_hit or '-'}; files {files or '-'}",
                )
            )
        elif not ops_hit:
            uncertain.append(
                (
                    path,
                    feature["source"],
                    f"'{leaf}' appears only in {', '.join(files)} (no operation form field or build key of that name)",
                )
            )
        else:
            matched.append(path)
    # Management operations that change something and that no frontend call uses.
    used = frontend_calls()
    unused = []
    for item in api:
        method, path = item["key"].split(" ", 1)
        if (
            method == "GET"
            or any(tag in ("oauth",) for tag in item.get("tags", []))
            or path.startswith(("/health", "/.well-known", "/mcp"))
        ):
            continue
        if not is_used(method, path, used):
            unused.append(item)

    lines = [
        "# Gaps: what the screens cannot do",
        "",
        "Generated by `guide/tools/inventory.py`; do not edit.",
        "",
    ]
    lines += [
        "## (a) Model features no model editor operation sets",
        "",
        (
            "Matching rule. The model document's property paths come from `EngineModel.model_json_schema()` "
            "(`backend/app/models/schema.py`; `ModelDefinition` itself is only the base class and has no properties). "
            "A path counts as set when its last segment (the leaf name) is (1) the `name` of a form field or a key written by the "
            "`build` of an `OperationSpec` in `frontend/src/features/model-editor/operations.ts`, or (2) named in "
            f"{', '.join(OPS_FILES)} there. The matching is by name only: it does not know which element an operation acts on. "
            "A leaf found under (1) is listed as matched. A leaf found only under (2), or any generic leaf "
            f"({', '.join(sorted(GENERIC_LEAVES))}), is **uncertain** and listed separately. A leaf found nowhere is a **gap**. "
            "Consumer API paths are reachable as text through the `consumer-json` and `consumer-item-json` operations; "
            "a consumer path with no form field is marked 'JSON text only'."
        ),
        "",
        (
            f"Counts: {len(features)} paths, of which {len(containers)} are containers (a list or object whose members are the paths below it; "
            f"they are judged through their members) and {len(features) - len(containers)} are single settings; {len(matched)} matched; {len(uncertain)} uncertain; {len(missing)} gaps."
        ),
        "",
        f"### Gaps ({len(missing)})",
        "",
        "| Model path | Schema source | Note |",
        "| --- | --- | --- |",
    ]
    for path, source, under in missing:
        lines.append(
            f"| `{path}` | {source} | {'JSON text only (consumer-json / consumer-item-json)' if under else 'no operation, no layout code names it'} |"
        )
    lines += [
        "",
        f"### Uncertain ({len(uncertain)})",
        "",
        "| Model path | Schema source | Why uncertain |",
        "| --- | --- | --- |",
    ]
    for path, source, why in uncertain:
        lines.append(f"| `{path}` | {source} | {why} |")
    lines += [
        "",
        f"## (b) Management API operations that change something and no frontend call uses ({len(unused)})",
        "",
        (
            "Matching rule. Every string or template literal under `frontend/src` (tests excluded) that holds `/api/` is read; "
            '`${...}` becomes `{}`, the query string is cut, and its method is the `method: "X"` / `json("X"` found within '
            "the next 240 characters (GET when none). An OpenAPI operation counts as used when its method equals and its path "
            "matches segment by segment (a `{}` segment matches any segment; a final computed segment matches any tail). "
            "Methods other than GET are listed unless the tag is `oauth` or the path is a health, well-known or MCP path. "
            "Some listed operations are reads sent as POST (queries) or machine-only (token, webhook delivery); "
            "judge each by its summary."
        ),
        "",
        "| Operation | Tag | Summary | Code |",
        "| --- | --- | --- | --- |",
    ]
    for item in unused:
        lines.append(
            f"| `{item['key']}` | {', '.join(item.get('tags', []))} | {item.get('summary', '')} | {item['source']} |"
        )
    lines.append("")
    return "\n".join(lines)


def frontend_calls() -> list[tuple[str, list[str], bool]]:
    calls = []
    literal = re.compile(r"""(?:`([^`]*)`|"([^"\n]*)"|'([^'\n]*)')""", re.DOTALL)
    for path in sorted((REPO / "frontend" / "src").rglob("*.ts*")):
        if re.search(r"\.test\.tsx?$", path.name):
            continue
        text = path.read_text()
        for match in literal.finditer(text):
            value = next(g for g in match.groups() if g is not None)
            if "/api/" not in value:
                continue
            start = value.index("/api/")
            value = re.sub(r"\$\{[^}]*\}", "{}", value[start:]).split("?")[0]
            window = text[match.end() : match.end() + 240]
            method = re.search(
                r"""(?:method:\s*|json\()["'](GET|POST|PUT|PATCH|DELETE)["']""", window
            )
            segments = [s for s in value.split("/") if s]
            calls.append(
                (method.group(1) if method else "GET", segments, segments[-1:] == ["{}"] and False)
            )
    return calls


def is_used(method: str, path: str, calls) -> bool:
    segments = [s for s in re.sub(r"\{[^}]*\}", "{}", path).split("/") if s]
    for call_method, call_segments, _ in calls:
        if call_method != method:
            continue
        if len(call_segments) == len(segments) and all(
            a == b or "{}" in a or "{}" in b for a, b in zip(call_segments, segments)
        ):
            return True
        # a computed tail (`${route}`) at the end stands for any remaining segments
        if (
            call_segments
            and "{}" in call_segments[-1]
            and call_segments[-1] != "{}"
            and len(call_segments) <= len(segments)
            and all(a == b or "{}" in a or "{}" in b for a, b in zip(call_segments[:-1], segments))
        ):
            return True
    return False


def main() -> int:
    """Write the inventory; with ``--check``, write it to a scratch directory instead and fail when it differs
    from the committed JSON (``npm run verify`` runs this, so a stale inventory never passes)."""
    global OUT
    committed = OUT
    check = "--check" in sys.argv[1:]
    if check:
        OUT = Path(tempfile.mkdtemp(prefix="rdm-inventory-check-"))
        atexit.register(shutil.rmtree, OUT, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    data = ts()
    kinds = {
        "settings": settings(),
        "management-api": management(),
        "mcp-tool": mcp(),
        "consumer-api": consumer(),
        "command": commands(),
        "permission": permissions(),
        "screen": screens(data),
        "model-feature": model_features(),
        "deployment": deployment(),
        "mail-kind": mail_kinds(),
        "search-field": search_fields(),
        "build-arg": build_args(),
    }
    for old in OUT.glob("*.json"):
        old.unlink()
    for kind, entries in kinds.items():
        (OUT / f"{kind}.json").write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n")
        print(f"{kind}: {len(entries)}")
    (OUT / "gaps.md").write_text(gaps(data, kinds["model-feature"], kinds["management-api"]))
    if check:

        def content(path: Path) -> list:
            # Line numbers in ``source`` move with every edit of the code behind an entry; what must match
            # is which entries exist and what they say.
            return [
                {**item, "source": re.sub(r":\d+", "", item.get("source", ""))}
                for item in json.loads(path.read_text())
            ]

        names = {path.name for path in OUT.glob("*.json")} | {
            path.name for path in committed.glob("*.json")
        }
        stale = sorted(
            name
            for name in names
            if not (OUT / name).is_file()
            or not (committed / name).is_file()
            or content(OUT / name) != content(committed / name)
        )
        if stale:
            print(
                f"the committed inventory is stale ({', '.join(stale)}); run "
                "backend/.venv/bin/python guide/tools/inventory.py and commit the result",
                file=sys.stderr,
            )
            return 1
        print("the committed inventory matches the code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
