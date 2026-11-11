"""The management API's reference examples, recorded from a run on the guide's reference data.

An integrator who signs in as an administrator to an instance holding the guide's reference model and
its ``docs`` set (``guide/samples``, the Graubünden stops: 598 records) sets up a workspace for a
timetable change and tidies it away again. Each step names the operation it calls, asserts the status
and code it records and nothing else, and may record its exchange as that operation's example.

Recording is off. With ``RDM_RECORD_EXAMPLES=1`` the steps write ``content/examples/<operation>.json``
(``app/management/reference/content/``), normalised so the files read the same on every run and the
diff of a regenerated file shows only what the route changed:

- every ID (a UUID) becomes ``00000000-0000-4000-8000-0000000000NN`` in the order it first appears, the
  same one wherever it reappears, so a created ID is the next request's ID; it stays a valid UUID;
- every time becomes a fixed one, ``2026-11-02T09:00:00Z`` plus seven minutes per moment, in the real
  order of the moments (times less than half a second apart are one moment; a recording run waits a
  second between steps); every cursor becomes ``cursor-N``;
- the person who made the changes is a neutral name and address;
- an array of more than three items keeps its first two, and the example says so in its notes.

The seed (the model installed, the workspace made, the set loaded through the public API by
``guide/samples/load.py``) is built once and reused until the model, the data, the loader or this
module changes (``tests/seeds.py``).

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest -m reference -q
"""

import importlib.util
import json
import os
import re
import shutil
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
import seeds
from harness_identity import HARNESS_PERSON, TestClient
from sqlalchemy import URL

from app.management.reference.content import CONTENT_DIR, example_file_name

SOURCE = Path(__file__).resolve()
SAMPLES = Path(__file__).resolve().parents[2] / "guide" / "samples"
RECORDING = os.environ.get("RDM_RECORD_EXAMPLES", "").strip().lower() in {"1", "true", "yes"}
EXAMPLES = CONTENT_DIR / "examples"
SEED = "reference-docs"
# The browser address the sign-in accepts by default (CORS_ORIGINS): the loader signs in as the browser does.
BASE = "http://localhost:5173"
SETTINGS = {"MODEL_ADMIN_MUTATIONS_ENABLED": "true"}


def _loader() -> Any:
    """``guide/samples/load.py``, which holds the sample's loader and uses only the standard library."""
    spec = importlib.util.spec_from_file_location("guide_samples_load", SAMPLES / "load.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _send(client: TestClient) -> Callable[..., tuple[int, Any]]:
    """``load.py``'s ``send``: a request to the application in this process."""

    def send(method, path, body=None, headers=None, form=None):
        kwargs: dict[str, Any] = {"headers": {"Origin": BASE, **(headers or {})}}
        if body is not None:
            kwargs["json"] = body
        if form is not None:
            kwargs["data"] = form
        response = client.request(method, path, **kwargs)
        try:
            return response.status_code, response.json() if response.content else None
        except ValueError:
            return response.status_code, {"raw": response.text}

    return send


@contextmanager
def _application(database: URL, settings: dict[str, str] | None = None) -> Iterator[TestClient]:
    """The application on ``database``; ``settings`` switches on what a recording needs beyond the
    reference's own (the webhooks' capability)."""
    from app.config import reload_settings
    from app.main import create_app

    files = Path(tempfile.gettempdir()) / "rdm-reference-job-files" / str(database.database)
    wanted = {**SETTINGS, **(settings or {}), "JOB_FILE_DIR": str(files)}
    saved = {key: os.environ.get(key) for key in wanted}
    os.environ.update(wanted)
    try:
        with seeds.application_environment(database, SAMPLES / "model.json"):
            application = create_app()
            application.state.run_event_deriver = False
            application.state.run_consumer_dispatcher = False
            application.state.run_process_heartbeat = False
            application.state.run_mail_sender = False
            with TestClient(application, authenticated=False) as client:
                yield client
    finally:
        shutil.rmtree(files, ignore_errors=True)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload_settings()


def _register_seed() -> None:
    def build(url: URL) -> dict[str, Any]:
        loader = _loader()
        with _application(url) as client:
            api = loader.Api(
                _send(client),
                base=BASE,
                email=HARNESS_PERSON["email"],
                password=HARNESS_PERSON["password"],
                log=lambda text: None,
            )
            loader.load_set(api, "docs", changeset=False)
        return {"set": "docs"}

    def inputs() -> list[str | Path]:
        return [
            (SAMPLES / "model.json").read_text(),
            (SAMPLES / "load.py").read_text(),
            *(path.read_text() for path in sorted((SAMPLES / "data" / "docs").glob("*.json"))),
            SOURCE,
            seeds.APP / "engine" / "model" / "bootstrap.py",
        ]

    seeds.register(seeds.Seed(SEED, build, inputs, base="schema"))


_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")
_FIRST_TIME = datetime(2026, 11, 2, 9, 0, 0, tzinfo=UTC)
_CURSORS = {"nextCursor", "prevCursor", "anchor"}
_PERSON = {
    HARNESS_PERSON["email"]: "admin@example.org",
    "Test harness person": "Reference Administrator",
}
_KEPT, _TRIM_ABOVE = 2, 3
_SAME_MOMENT = 0.5
_DATABASE = re.compile(r"postgresql\+psycopg://\S+")
_PATH = re.compile(r"/Users/[^\s\"']+")
_TEXT_LINES = 12
# A secret never reaches an example: these keys are replaced wherever they appear, whatever their
# value, by a fixed and obviously invented one. A key that means a secret only in some answers
# (``secret`` is a client's secret or an authenticator's seed) is masked by the call that records it.
SECRET_MASKS = {
    "password": "example-password",
    "currentPassword": "example-password",
    "newPassword": "example-new-password",
    "clientSecret": "example-client-secret",
    "signingSecret": "rdmwh_example-signing-secret",
    "client_secret": "example-client-secret",
    "access_token": "example-access-token",
    "refresh_token": "example-refresh-token",
    "otpauthUri": "otpauth://totp/Example:user@example.org?secret=JBSWY3DPEHPK3PXP&issuer=Example",
    "qrSvg": '<svg xmlns="http://www.w3.org/2000/svg"><!-- the QR code --></svg>',
    "hint": "cret",
    "requestId": "example-request-id",
}
_ISSUER_HOST = re.compile(r"http://127\.0\.0\.1:\d+")
_RESET_TOKEN = re.compile(r"token=[A-Za-z0-9_-]{16,}")


class Normaliser:
    """Stable placeholders for what differs between runs, the same one wherever a value reappears."""

    def __init__(self, texts: list[str]) -> None:
        """``texts`` is everything that will be written, for the times in it: they are ranked by their
        real order, so a record created before another stays earlier in the examples."""
        self.ids: dict[str, str] = {}
        self.cursors: dict[str, str] = {}
        self.notes: list[str] = []
        self.kids: dict[str, str] = {}
        moments = sorted(
            (
                (datetime.fromisoformat(found), found)
                for found in {found for text in texts for found in _TIME.findall(text)}
            ),
        )
        # Times less than half a second apart (a record's created and updated times) are one moment.
        self.times, rank, previous = {}, -1, None
        for moment, found in moments:
            if previous is None or (moment - previous).total_seconds() >= _SAME_MOMENT:
                rank += 1
            previous = moment
            self.times[found] = (_FIRST_TIME + timedelta(minutes=7 * rank)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    def _id(self, found: re.Match[str]) -> str:
        key = found.group(0).lower()
        return self.ids.setdefault(key, f"00000000-0000-4000-8000-{len(self.ids) + 1:012d}")

    def _time(self, found: re.Match[str]) -> str:
        return self.times[found.group(0)]

    def text(self, value: str) -> str:
        for real, neutral in _PERSON.items():
            value = value.replace(real, neutral)
        # Where this machine keeps its database and files is not part of an example.
        value = _DATABASE.sub("postgresql+psycopg://rdm@db.example.org/rdm", value)
        value = _ISSUER_HOST.sub("https://id.example.org", value)
        value = _RESET_TOKEN.sub("token=example-reset-token", value)
        value = _PATH.sub("/srv/rdm", value)
        return _TIME.sub(self._time, _UUID.sub(self._id, value))

    def value(self, value: Any, where: str = "", key: str = "") -> Any:
        if isinstance(value, dict):
            # A key that is an ID (a grid's relationships by column record) is one too.
            return {
                self.text(k): self.value(v, f"{where}.{k}" if where else k, k)
                for k, v in value.items()
            }
        if isinstance(value, list):
            if len(value) > _TRIM_ABOVE:
                self.notes.append(f"`{where}`: the first {_KEPT} of {len(value)} items are shown.")
                value = value[:_KEPT]
            return [self.value(item, f"{where}[{index}]", key) for index, item in enumerate(value)]
        if isinstance(value, str):
            if key == "commit":  # the build's commit changes with every commit
                return "3f2a9c1e"
            if key in SECRET_MASKS:
                return SECRET_MASKS[key]
            if key == "kid":
                return self.kids.setdefault(value, f"signing-key-{len(self.kids) + 1}")
            if key in _CURSORS:
                return self.cursors.setdefault(value, f"cursor-{len(self.cursors) + 1}")
            return self.text(value)
        return value


def masked(value: Any, masks: dict[str, Any] | None) -> Any:
    """A copy of ``value`` with each key in ``masks`` set to its placeholder (a list for a list)."""
    if not masks:
        return value
    if isinstance(value, dict):
        return {k: (masks[k] if k in masks else masked(v, masks)) for k, v in value.items()}
    if isinstance(value, list):
        return [masked(item, masks) for item in value]
    return value


class Scenario:
    """The signed-in administrator's calls, each optionally recorded as its operation's example."""

    def __init__(self, client: TestClient) -> None:
        loader = _loader()
        self.client = client
        self.api = loader.Api(
            _send(client),
            base=BASE,
            email=HARNESS_PERSON["email"],
            password=HARNESS_PERSON["password"],
            log=lambda text: None,
        )
        self.api.login()
        self.exchanges: list[dict[str, Any]] = []

    def call(
        self,
        method: str,
        route: str,
        *,
        path: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        body: Any = None,
        status: int,
        code: str | None = None,
        record: str | None = None,
        summary: str = "",
        signed_in: bool = True,
        notes: list[str] | None = None,
        headers: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        mask: dict[str, Any] | None = None,
    ) -> Any:
        """One call. It asserts the status (and the error code of a refusal) and returns the body.
        ``form`` sends a form (the token endpoint's); ``mask`` replaces the values of those keys in the
        recorded copy only (an answer's secrets)."""
        url = route
        for name, value in (path or {}).items():
            url = url.replace("{" + name + "}", quote(str(value), safe=""))
        if query:
            # A list is a repeated parameter.
            parts = [
                f"{key}={quote(str(item).lower() if isinstance(item, bool) else str(item), safe='')}"
                for key, val in query.items()
                for item in (val if isinstance(val, list) else [val])
            ]
            url += "?" + "&".join(parts)
        got, out = self.api.raw(method, url, body, headers=headers, form=form, auth=signed_in)
        assert got == status, f"{method} {url}: {got} {json.dumps(out)[:600]}"
        if code is not None:
            assert out["error"]["code"] == code, out
        if record:
            self._record(
                method,
                route,
                record,
                summary,
                path or {},
                query or {},
                masked(body, mask),
                got,
                masked(out, mask),
                notes,
            )
        if RECORDING and record:
            time.sleep(1.1)  # the times of one step are then a moment of their own in the examples
        return out

    def _record(
        self, method, route, name, summary, path, query, body, status, out, notes=None
    ) -> None:
        if isinstance(out, dict) and set(out) == {"raw"}:  # a text answer, as the metrics are
            lines = out["raw"].splitlines()
            out = "\n".join(lines[:_TEXT_LINES]) + ("\n..." if len(lines) > _TEXT_LINES else "")
        if RECORDING:
            self.exchanges.append(
                {
                    "operation": f"{method} {route}",
                    "name": name,
                    "summary": summary,
                    "request": {
                        key: value
                        for key, value in (("path", path), ("query", query), ("body", body))
                        if value not in ({}, None)
                    },
                    "response": {"status": status, **({} if out is None else {"body": out})},
                    **({"notes": notes} if notes else {}),
                }
            )

    def write_examples(self) -> list[str]:
        """Write each recorded exchange as its operation's example file, normalised together so an
        ID or a time reads the same in every file. Nothing is written unless recording is on."""
        norm = Normaliser([json.dumps(item) for item in self.exchanges])
        EXAMPLES.mkdir(parents=True, exist_ok=True)
        written = []
        for item in self.exchanges:
            norm.notes = []
            request = {
                key: norm.value(value, "request" if key == "body" else "")
                for key, value in item["request"].items()
            }
            response = {"status": item["response"]["status"]}
            if "body" in item["response"]:
                response["body"] = norm.value(item["response"]["body"])
            document = {**{k: item[k] for k in ("operation", "name", "summary")}}
            document |= {"request": request, "response": response}
            if item.get("notes") or norm.notes:
                document["notes"] = [*item.get("notes", []), *norm.notes]
            method, _, route = item["operation"].partition(" ")
            target = EXAMPLES / example_file_name(method, route)
            target.write_text(
                json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            written.append(item["operation"])
        return written


@pytest.fixture(scope="module")
def scenario() -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def test_an_administrator_sets_up_a_workspace_for_a_timetable_change_and_removes_it(scenario):
    """The ``workspaces`` area: read what the instance holds, make a workspace, rename it, make it the
    default and back, retire it and delete it. Each step records the operation's main successful use."""
    s = scenario
    runtime = s.call(
        "GET",
        "/api/v1/workspace-runtime-state",
        status=200,
        record="current",
        summary="The default workspace is the Graubünden workspace",
    )
    assert runtime["defaultWorkspaceKey"] == "graubuenden"

    workspace = s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "graubuenden"},
        status=200,
        record="graubuenden",
        summary="The Graubünden workspace, available and not deletable",
    )
    assert workspace["status"] == "active" and workspace["deletable"] is False
    assert workspace["deleteBlockedBy"] == "default"
    release_id = workspace["model"]["releaseId"]

    model = s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/model",
        path={"workspace_key": "graubuenden"},
        status=200,
        record="graubuenden",
        summary="The release the Graubünden workspace runs",
    )
    assert model["releaseId"] == release_id

    assigned = s.call(
        "GET",
        "/api/v1/workspace-models",
        query={"releaseKey": model["releaseKey"], "pageSize": 2},
        status=200,
        record="runningTheRelease",
        summary="The workspaces that run the release, in key order",
    )
    assert {item["workspaceKey"] for item in assigned["items"]} == {"default", "graubuenden"}

    feed = s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/feed",
        path={"workspace_key": "graubuenden"},
        query={"after": 0, "pageSize": 3},
        status=200,
        record="fromTheStart",
        summary="The first three changes to the workspace's live data",
    )
    assert len(feed["items"]) == 3 and feed["headPosition"] > 3
    assert feed["nextAfter"] == feed["items"][-1]["position"]

    mine = s.call(
        "GET",
        "/api/v1/me/workspaces",
        status=200,
        record="mine",
        summary="The workspaces the administrator may browse, the default first",
    )
    assert mine["items"][0]["key"] == "graubuenden" and mine["items"][0]["isDefault"] is True

    created = s.call(
        "POST",
        "/api/v1/workspaces",
        body={
            "key": "winter-timetable",
            "label": "Winter timetable 2027",
            "modelReleaseId": release_id,
        },
        status=201,
        record="winterTimetable",
        summary="A workspace for the winter timetable, running the same release",
    )
    assert created["version"] == 1 and created["deletable"] is True
    assert created["model"]["releaseId"] == release_id

    renamed = s.call(
        "PATCH",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        body={"expectedVersion": 1, "label": "Winter timetable 2027/28"},
        status=200,
        record="rename",
        summary="Rename the workspace; its key stays",
    )
    assert renamed["version"] == 2 and renamed["key"] == "winter-timetable"

    page = s.call(
        "GET",
        "/api/v1/workspaces",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first page of the active workspaces, in key order",
    )
    assert [item["key"] for item in page["items"]] == ["default", "graubuenden"]
    assert page["nextCursor"]
    rest = s.call(
        "GET", "/api/v1/workspaces", query={"cursor": page["nextCursor"], "pageSize": 2}, status=200
    )
    assert [item["key"] for item in rest["items"]] == ["winter-timetable"] and rest[
        "nextCursor"
    ] is None
    assert "deletable" not in page["items"][0]

    # The default workspace: switch to the new one, which is then neither deletable nor retirable.
    state = s.call(
        "PATCH",
        "/api/v1/workspace-runtime-state",
        body={"defaultWorkspaceKey": "winter-timetable", "expectedVersion": runtime["version"]},
        status=200,
        record="makeWinterTheDefault",
        summary="Make the winter workspace the default",
    )
    assert (
        state["defaultWorkspaceKey"] == "winter-timetable"
        and state["version"] == runtime["version"] + 1
    )
    s.call(
        "DELETE",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        query={"expectedVersion": 2},
        status=409,
        code="WORKSPACE_IS_DEFAULT",
    )
    s.call(
        "PATCH",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        body={"expectedVersion": 2, "status": "retired"},
        status=409,
        code="DEFAULT_WORKSPACE_CANNOT_BE_RETIRED",
    )
    not_empty = s.call(
        "DELETE",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "graubuenden"},
        query={"expectedVersion": 1},
        status=409,
        code="WORKSPACE_NOT_EMPTY",
    )
    assert (
        not_empty["error"]["details"]["objectCount"] > 0
        and "changeSetCount" in not_empty["error"]["details"]
    )
    back = s.call(
        "PATCH",
        "/api/v1/workspace-runtime-state",
        body={"defaultWorkspaceKey": "graubuenden", "expectedVersion": state["version"]},
        status=200,
    )
    s.call(
        "PATCH",
        "/api/v1/workspace-runtime-state",
        body={"defaultWorkspaceKey": "default", "expectedVersion": state["version"]},
        status=409,
        code="VERSION_CONFLICT",
    )

    # Retire the workspace: still readable, no longer the default's candidate, and its key stays taken.
    retired = s.call(
        "PATCH",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        body={"expectedVersion": 2, "status": "retired"},
        status=200,
    )
    assert retired["status"] == "retired" and retired["version"] == 3
    s.call(
        "PATCH",
        "/api/v1/workspace-runtime-state",
        body={"defaultWorkspaceKey": "winter-timetable", "expectedVersion": back["version"]},
        status=409,
        code="WORKSPACE_RETIRED",
    )
    assert "winter-timetable" not in [
        i["key"] for i in s.call("GET", "/api/v1/workspaces", status=200)["items"]
    ]
    assert "winter-timetable" in [
        i["key"]
        for i in s.call("GET", "/api/v1/workspaces", query={"status": "all"}, status=200)["items"]
    ]
    s.call(
        "POST",
        "/api/v1/workspaces",
        body={"key": "winter-timetable", "label": "Again"},
        status=409,
        code="WORKSPACE_ALREADY_EXISTS",
    )
    s.call(
        "PATCH",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        body={"expectedVersion": 2, "label": "Stale"},
        status=409,
        code="VERSION_CONFLICT",
    )

    s.call(
        "DELETE",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        query={"expectedVersion": 3},
        status=204,
        record="emptyWorkspace",
        summary="Delete the workspace; nothing referred to it",
    )
    s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "winter-timetable"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )


def test_the_administrator_reads_the_state_of_the_instance_and_its_changes(scenario):
    """The ``system`` and ``changes`` areas and the two health checks: what an operator or an
    integration reads to see that the instance is up and what changed in it."""
    s = scenario
    s.call(
        "GET",
        "/health",
        status=200,
        record="healthy",
        summary="The instance and its workspaces are served",
        signed_in=False,
    )
    s.call(
        "GET",
        "/health/live",
        status=200,
        record="alive",
        summary="The process answers",
        signed_in=False,
    )
    info = s.call(
        "GET",
        "/api/v1/system",
        status=200,
        record="instance",
        summary="What this instance is and which optional surfaces it has",
    )
    assert "version" in json.dumps(info)
    s.call(
        "GET",
        "/api/v1/system/configuration",
        status=200,
        record="settings",
        summary="The settings in force, by group",
    )
    s.call(
        "GET",
        "/api/v1/system/processes",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The engine's processes",
    )
    s.call(
        "GET",
        "/api/v1/system/readiness",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="Whether each active workspace is served",
    )
    s.call(
        "GET",
        "/api/v1/system/summary",
        status=200,
        record="summary",
        summary="The operator's summary of the instance",
    )
    s.call(
        "GET",
        "/api/v1/system/backup-rehearsals",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The recorded backup rehearsals",
    )
    s.call(
        "GET",
        "/metrics",
        status=200,
        record="metrics",
        summary="The metrics in the Prometheus text format",
    )
    changes = s.call(
        "GET",
        "/api/v1/changes",
        query={"workspaceKey": "graubuenden", "kind": "record", "pageSize": 3},
        status=200,
        record="recentRecordChanges",
        summary="The latest changes to records of one workspace",
    )
    assert (
        changes["items"] and changes["items"][0]["workspaceKey"] == "graubuenden"
        if "workspaceKey" in changes["items"][0]
        else changes["items"]
    )


def test_the_workspaces_operations_refuse_what_they_cannot_do(scenario):
    """Each refusal the area's text names, with the status and code it carries."""
    s = scenario
    s.call("GET", "/api/v1/workspaces", status=401, code="AUTHENTICATION_REQUIRED", signed_in=False)
    s.call("GET", "/api/v1/workspaces", query={"pagesize": 5}, status=422, code="UNKNOWN_PARAMETER")
    s.call(
        "GET",
        "/api/v1/workspaces",
        query={"pageSize": 0},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    s.call(
        "GET",
        "/api/v1/workspaces",
        query={"cursor": "not-a-cursor"},
        status=422,
        code="INVALID_CURSOR",
    )
    s.call(
        "GET",
        "/api/v1/workspaces",
        query={"cursor": "x", "position": 1},
        status=422,
        code="CONFLICTING_PAGE_PARAMETERS",
    )
    s.call(
        "GET",
        "/api/v1/workspaces",
        query={"position": -1},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    s.call(
        "GET",
        "/api/v1/workspaces",
        query={"holding": "no-such-group"},
        status=422,
        code="ACTION_GROUP_UNKNOWN",
    )
    s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/feed",
        path={"workspace_key": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/workspaces",
        body={"key": "Not A Key", "label": "x"},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    s.call(
        "POST",
        "/api/v1/workspaces",
        body={
            "key": "other",
            "label": "x",
            "modelReleaseId": "5f0c1c6e-6f35-4c9d-8d53-7a2f4e0a9b11",
        },
        status=404,
        code="MODEL_RELEASE_NOT_FOUND",
    )
    s.call(
        "PATCH",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "graubuenden"},
        body={"expectedVersion": 1},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    s.call(
        "PATCH",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "nowhere"},
        body={"expectedVersion": 1, "label": "x"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "PATCH",
        "/api/v1/workspace-runtime-state",
        body={"defaultWorkspaceKey": "nowhere", "expectedVersion": 1},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "DELETE",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "nowhere"},
        query={"expectedVersion": 1},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "DELETE",
        "/api/v1/workspaces/{workspace_key}",
        path={"workspace_key": "graubuenden"},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    head = s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/feed",
        path={"workspace_key": "graubuenden"},
        query={"pageSize": 1},
        status=200,
    )["headPosition"]
    ahead = s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/feed",
        path={"workspace_key": "graubuenden"},
        query={"after": head + 1},
        status=409,
        code="FEED_POSITION_AHEAD",
    )
    assert ahead["error"]["details"] == {"headPosition": head}
    s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/feed",
        path={"workspace_key": "graubuenden"},
        query={"after": -1},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
