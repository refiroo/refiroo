"""J47.1 — every operation answers as the permission catalogue says (0.12 E1, phase A).

The operations are read from the application's own OpenAPI document, so a new route is covered the
day it declares its action. The oracle is the catalogue (``catalogue.py``: ``PREDEFINED_ROLES``,
``JOB_GROUPS``) and the operation's declared groups and scope, never the code that checks them: a
caller holding groups G is allowed an operation naming groups A when A is empty or A and G share a
group held where the request lands (an instance grant lands everywhere, a workspace grant only in
its workspace and never on an instance action). Allowed means "not 403"; refused means ``403
FORBIDDEN`` naming the action. A caller with no token is ``401`` on every route but the open ones.

No call can change data. Every body is ``[]`` (JSON that no operation's body accepts) and a form
operation sends no file, so a call that is allowed stops at validation (``422``) after
authorization. A call expected to be refused names the real change set, publication, job and
subscription its scope resolves (refused, it changes nothing); a call expected to be allowed with
nothing to validate it (a body-less write) names ones that do not exist. The few operations that
cannot be probed so are in ``SWEEP_EXCEPTIONS``.
"""

import json
import re
import threading
from dataclasses import dataclass
from uuid import uuid4

import httpx2
import pytest
from harness_identity import TestClient, request_token
from scenario import W1, W2, ok
from security_oracle import EXPECTED_GROUPS
from test_j24_job_stream import served  # noqa: F401 - a fixture
from test_j30_consumer_events import LEDGER, _activate
from test_j30_subscriptions import SUBSCRIPTIONS, _subscribe
from test_j39_sign_in import _browser, _person, _sign_in
from test_j40_authorization import _client
from test_j41_consumer_grants import STRUCTURES, _consumer, _grant, _with_other
from test_openapi_contract import OPEN_OPERATIONS

from app.engine.authorization.catalogue import ACTIONS, GROUPS, JOB_GROUPS, PREDEFINED_ROLES

NO_GRANTS = "no grants"
ROLES = [*PREDEFINED_ROLES, NO_GRANTS]

# Operations that cannot be called when the oracle says "allowed", each because a call with nothing
# to make it invalid could do what it names. They are still called when the caller is refused, and
# without a token. The sweep computes the set of such operations (a write with no body, no path
# parameter and no required query) and requires it to equal this table, so a new one is decided here.
# Writes that name the workspace in their path but do something only for a person: the sweep's
# callers are clients, so they are always refused `403 NOT_A_PERSON` and change nothing (0.16 AO3).
PERSON_ONLY_WRITES = {
    ("put", "/api/v1/me/followed-workspaces/{workspace_key}"),
    ("delete", "/api/v1/me/followed-workspaces/{workspace_key}"),
}

# Opening the workspace's model draft: when the caller is allowed it creates a draft in the real
# workspace, so it is probed only where the caller is refused (0.16 WM1).
OPENS_A_DRAFT = {("post", "/api/v1/workspaces/{workspace_key}/model/draft")}

# A write the route allows for Work in change sets alone, though its action also names live edits:
# a proposal always goes into a change set (0.16 AP2).
CHANGE_SET_ONLY = {("post", "/api/v1/workspaces/{workspace_key}/mapping-proposals")}

SWEEP_EXCEPTIONS = {
    # Signed in, so every caller is allowed: the call ends the caller's own sessions.
    ("delete", "/api/v1/me/sessions"): "ends the caller's own sessions; nothing makes it invalid",
    # Signed in, so every caller is allowed: the call starts the caller's second-factor enrolment.
    ("post", "/api/v1/me/second-factor"): "starts the caller's enrolment; nothing makes it invalid",
    # Security administration: the call removes the instance's mail settings.
    ("delete", "/api/v1/mail-settings"): "removes the mail settings; nothing makes it invalid",
    # Operations: the call sends the AI provider a test request (0.16 AP1); with none set it is
    # refused with 409, which J48.4 walks.
    ("post", "/api/v1/ai/test"): "sends the AI provider a test request; nothing makes it invalid",
}

# Streams that never end, so a call the caller is allowed cannot be probed and read back by the
# sweep: refused callers are still probed. The inbox stream's class (any signed-in person, never a
# `consumer` token) is probed over HTTP by `test_the_inbox_stream_answers_as_its_class_says`; what it
# sends is walked in J42 (0.12 A2).
SWEEP_STREAMS = {("get", "/api/v1/me/notifications/events")}

_PATH_SCOPE = "the path's workspace"
_PATH_SCOPES = (_PATH_SCOPE, "the change set, or the path's workspace")
_QUERY_SCOPES = (
    "the query's workspace",
    "the query's change set, publication or workspace",
    "the query's context, or the record's workspace",
    "the query's context, or the relationship's workspace",
)


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    action: str
    groups: tuple[str, ...]
    scope: str
    body: str | None  # "json", "form" or None
    mutating: bool
    required_query: bool
    queries: frozenset[str]

    @property
    def key(self) -> tuple[str, str]:
        return (self.method, self.path)

    @property
    def unsafe_when_allowed(self) -> bool:
        """A write whose valid form needs nothing the sweep leaves out."""
        return self.mutating and self.body is None and not self.required_query

    @property
    def has_path_parameters(self) -> bool:
        return "{" in self.path


def operations(app) -> tuple[list[Operation], list[tuple[str, str]]]:
    """Every operation the document declares an action for, and the ones that declare none."""
    declaring, open_ = [], []
    for path, methods in app.openapi()["paths"].items():
        for method, operation in methods.items():
            if method == "parameters":
                continue
            if "x-action" not in operation:
                open_.append((method, path))
                continue
            content = (operation.get("requestBody") or {}).get("content", {})
            body = None if not content else "form" if "multipart/form-data" in content else "json"
            required_query = any(
                parameter.get("required") and parameter["in"] == "query"
                for parameter in operation.get("parameters", [])
            )
            declaring.append(
                Operation(
                    method,
                    path,
                    operation["x-action"],
                    tuple(operation["x-action-groups"]),
                    operation["x-action-scope"],
                    body,
                    method != "get",
                    required_query,
                    frozenset(
                        parameter["name"]
                        for parameter in operation.get("parameters", [])
                        if parameter["in"] == "query"
                    ),
                )
            )
    return declaring, open_


@dataclass(frozen=True)
class Principal:
    """What a caller holds: groups at the instance, and groups in workspace A."""

    at_instance: frozenset[str]
    in_workspace: frozenset[str]

    @property
    def anywhere(self) -> frozenset[str]:
        return self.at_instance | self.in_workspace


def principal_of(role: str) -> Principal:
    """The catalogue's reading of a role: granted at the instance where any of its groups can only
    be held there, in workspace A otherwise (the plan's rule)."""
    if role == NO_GRANTS:
        return Principal(frozenset(), frozenset())
    groups = frozenset(PREDEFINED_ROLES[role])
    if any(GROUPS[group].reach == "instance" for group in groups):
        return Principal(groups, frozenset())
    return Principal(frozenset(), groups)


def grants_of(role: str) -> list[tuple[str, dict]]:
    if role == NO_GRANTS:
        return []
    scope = (
        {"instance": True}
        if any(GROUPS[group].reach == "instance" for group in PREDEFINED_ROLES[role])
        else {"workspaceKey": W1}
    )
    return [(role, scope)]


def needed(operation: Operation, variant: str) -> tuple[str, ...]:
    """The groups that allow the request as probed: the record writes name both of theirs and the
    request's change set picks one (D244); a job is used under the group that starts its kind
    (D285), and the sweep's job is an export."""
    if operation.key in CHANGE_SET_ONLY:
        return ("change-sets",)
    if operation.action == "records.write":
        return ("change-sets",) if variant == "change-set" else ("edit-live",)
    if operation.action == "jobs.use":
        return (JOB_GROUPS["export"],)
    return operation.groups


def allowed(principal: Principal, operation: Operation, variant: str, workspace: str) -> bool:
    groups = needed(operation, variant)
    if not groups:
        return True
    if operation.scope == "any scope":
        return bool(principal.anywhere.intersection(groups))
    if operation.scope == "instance":
        return bool(principal.at_instance.intersection(groups))
    reaches = principal.at_instance | (principal.in_workspace if workspace == W1 else frozenset())
    return bool(reaches.intersection(groups))


def variants(operation: Operation) -> list[tuple[str, str]]:
    """The ways one operation is probed: as it stands (in workspace A), in a change set for the
    record writes, and in workspace B where the request names its workspace."""
    found = [("default", W1)]
    if operation.action == "records.write":
        found.append(("change-set", W1))
    # A query context is probed only where the route declares ``workspaceKey``: every route refuses
    # a parameter it does not declare (D-3).
    names_it = operation.scope in _PATH_SCOPES or "workspaceKey" in operation.queries
    if operation.scope in (*_PATH_SCOPES, *_QUERY_SCOPES) and names_it:
        found.append(("other-workspace", W2))
    return found


def probe(
    client,
    operation: Operation,
    ids: dict[str, str],
    variant: str,
    *,
    real: bool,
    extra: dict[str, str] | None = None,
):
    """One call that cannot succeed: ``[]`` as the body, no file, and (unless ``real`` is off) the
    real identifiers the operation's scope resolves."""
    params: dict[str, str] = dict(extra or {})
    body: object = []

    def value(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "workspace_key":
            return W2 if variant == "other-workspace" else W1
        return ids[name] if real and name in ids else str(uuid4())

    path = re.sub(r"{(\w+)}", value, operation.path)
    if variant == "other-workspace" and operation.scope in _QUERY_SCOPES:
        params["workspaceKey"] = W2
    if variant == "change-set":
        if operation.body == "json":
            body = {"changeSetId": ids["change_set_id"] if real else str(uuid4())}
        else:
            params["changeSetId"] = ids["change_set_id"] if real else str(uuid4())
    if operation.body == "form":
        return client.request(operation.method, path, params=params, data={"request": "[]"})
    if operation.body == "json":
        return client.request(
            operation.method,
            path,
            params=params,
            content=json.dumps(body),
            headers={"content-type": "application/json"},
        )
    return client.request(operation.method, path, params=params)


def _fixtures(world) -> dict[str, str]:
    """What a refused call must name to get past the lookups that precede the check: a change set,
    a publication, a finished export, a subscription, a record's type and ID."""
    _activate(world, "events")
    subscription = _subscribe(world, W1)
    record = world.made("R", "Probed")
    change_set = world.change_set()
    publications = ok(world.api.get(f"/workspaces/{W1}/publications", pageSize=1))["items"]
    publication = (
        publications[0] if publications else world.publish(world.change_set(), workspace=W1)
    )
    export = {
        "workspaceKey": W1,
        "scope": {"types": [{"objectTypeKey": world.key("R")}]},
        "format": "jsonl",
    }
    job = ok(world.api.post("/exports", export), 202)
    world.api.client.app.state.export_worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    return {
        "change_set_id": change_set["id"],
        "publication_id": publication["id"],
        "subscription_id": subscription["id"],
        "job_id": job["id"],
        "object_type_key": world.key("R"),
        "object_id": record["id"],
    }


_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


@dataclass(frozen=True)
class Outcome:
    """What one call answered, and what the oracle said of it."""

    status: int
    code: str | None
    details: dict | None
    holds: bool
    problem: str | None

    @property
    def same_as(self) -> tuple:
        """What another principal holding the same groups must answer alike."""
        # The probes name a fresh ID in every call, which a refusal may echo.
        details = re.sub(_UUID, "<id>", json.dumps(self.details, sort_keys=True))
        return (self.status, self.code, details)


def _failure(operation, variant, workspace, holds, response) -> str | None:
    """What is wrong with the answer, or None."""
    where = f"{operation.method.upper()} {operation.path} [{variant}]"
    _, code, error = _error_of(response)
    if holds:
        if response.status_code == 401 or code == "FORBIDDEN" or response.status_code >= 500:
            return f"{where}: allowed, answered {response.status_code} {code}"
        return None
    if response.status_code != 403 or code != "FORBIDDEN":
        return f"{where}: refused expected, answered {response.status_code} {code}"
    details = error.get("details") or {}
    if details.get("action") != operation.action:
        return f"{where}: refused for {details.get('action')}, expected {operation.action}"
    return None


def _error_of(response) -> tuple[object, str | None, dict]:
    try:
        body = response.json()
    except ValueError:
        body = {}
    error = body.get("error") if isinstance(body, dict) else None
    error = error if isinstance(error, dict) else {}
    return body, error.get("code"), error


def collect(http, role: str, ids: dict[str, str], declared: list[Operation]) -> dict:
    """Call every operation with ``http`` (a client holding what ``role`` names) and return, by
    ``(method, path, variant)``, what each answered and whether the catalogue's oracle agrees."""
    principal = principal_of(role)
    # The calls that could do something when wrongly allowed go last, so a defect cannot change the
    # state the next call is probed in.
    ordered = sorted(declared, key=lambda operation: operation.unsafe_when_allowed)
    found: dict[tuple[str, str, str], Outcome] = {}
    for operation in ordered:
        for variant, workspace in variants(operation):
            holds = allowed(principal, operation, variant, workspace)
            if holds and (
                operation.key in SWEEP_EXCEPTIONS
                or operation.key in SWEEP_STREAMS
                or operation.key in OPENS_A_DRAFT
            ):
                continue
            # Allowed with nothing to make it invalid: name nothing that exists.
            real = not (holds and operation.unsafe_when_allowed)
            response = probe(http, operation, ids, variant, real=real)
            _, code, error = _error_of(response)
            found[(*operation.key, variant)] = Outcome(
                response.status_code,
                code,
                error.get("details"),
                holds,
                _failure(operation, variant, workspace, holds, response),
            )
    return found


def sweep(world, role: str, ids: dict[str, str], declared: list[Operation]) -> dict[str, int]:
    """Call every operation as a client holding ``role``; return the counts, raise with every
    difference."""
    _, caller = _client(world, f"Sweep {role}", *grants_of(role))
    found = collect(caller.api.client, role, ids, declared)
    problems = [outcome.problem for outcome in found.values() if outcome.problem]
    assert not problems, f"{role}: {len(problems)} differences\n" + "\n".join(problems[:60])
    excepted = sum(
        1
        for operation in declared
        for variant, workspace in variants(operation)
        if operation.key in SWEEP_EXCEPTIONS
        and allowed(principal_of(role), operation, variant, workspace)
    )
    allowed_count = sum(outcome.holds for outcome in found.values())
    return {
        "calls": len(found),
        "allowed": allowed_count,
        "refused": len(found) - allowed_count,
        "exceptions": excepted,
    }


@pytest.mark.journey("J47.1")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
@pytest.mark.parametrize("role", ROLES)
def test_every_operation_answers_as_the_catalogue_says(world, role):
    """Given a caller holding one predefined role (or nothing), when every operation the document
    declares an action for is called with a body that cannot be valid, then it is allowed (anything
    but `403`, and no `5xx`) where the catalogue allows the caller and `403 FORBIDDEN` naming the
    action where it does not, with workspace B refused to a workspace grant and an instance action
    refused to one."""
    declared, open_ = operations(world.api.client.app)
    assert set(open_) == OPEN_OPERATIONS, set(open_) ^ OPEN_OPERATIONS
    unsafe = [operation for operation in declared if operation.unsafe_when_allowed]
    assert not [
        op
        for op in unsafe
        if "{workspace_key}" in op.path and op.key not in PERSON_ONLY_WRITES | OPENS_A_DRAFT
    ], "a write with a real workspace"
    assert {op.key for op in unsafe if not op.has_path_parameters} == set(SWEEP_EXCEPTIONS)
    assert {operation.action for operation in declared} == set(ACTIONS)
    counts = sweep(world, role, _fixtures(world), declared)
    assert counts["calls"] > 200, counts


@pytest.mark.journey("J47.1")
def test_every_operation_needs_the_groups_the_documentation_says(monkeypatch):
    """Given the table `EXPECTED_GROUPS` (``security_oracle.py``), written from docs/API.md § Security
    and not from the code, and the application with every capability on. When each operation of its
    OpenAPI document is looked up, then it is named in the table, declares the groups the table
    expects (an open operation declares no action at all, and is one of `OPEN_OPERATIONS`), and no
    entry is left for an operation that does not exist: a route added without a decision fails
    here, and so does a declaration that drifts from the documentation. The sweep above proves
    enforcement equals declaration; this proves the declaration is the documented one."""
    from app.main import create_app

    for flag in (
        "MODEL_ADMIN_MUTATIONS_ENABLED",
        "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        "INTEGRATION_JOBS_ENABLED",
        "CONSUMER_SUBSCRIPTIONS_ENABLED",
    ):
        monkeypatch.setenv(flag, "true")
    document = create_app().openapi()["paths"]
    found = {
        (method, path): operation
        for path, methods in document.items()
        for method, operation in methods.items()
        if method != "parameters"
    }
    assert set(found) - set(EXPECTED_GROUPS) == set(), "operations the oracle does not name"
    assert set(EXPECTED_GROUPS) - set(found) == set(), "oracle entries for no operation"
    drifted = {}
    for key, operation in found.items():
        expected = EXPECTED_GROUPS[key]
        declared = None if "x-action" not in operation else frozenset(operation["x-action-groups"])
        if declared != expected:
            drifted[key] = (sorted(declared) if declared is not None else None,
                            sorted(expected) if expected is not None else None)  # fmt: skip
    assert not drifted, f"declared groups differ from the documented ones: {drifted}"
    assert {key for key, groups in EXPECTED_GROUPS.items() if groups is None} == set(
        OPEN_OPERATIONS
    )


def _opened(base: str, bearer: str | None) -> dict:
    """What the inbox stream answers a caller: its status, content type and, when it is a refusal,
    the body. The stream is opened on a thread and closed at once; nothing is asserted there."""
    answer: dict = {}

    def read() -> None:
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        try:
            with httpx2.stream(
                "GET", f"{base}/api/v1/me/notifications/events", headers=headers, timeout=15
            ) as response:
                answer["status"] = response.status_code
                answer["type"] = response.headers.get("content-type", "")
                if response.status_code != 200:
                    answer["body"] = response.read().decode()
        except httpx2.HTTPError as failure:
            answer["failure"] = repr(failure)

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    thread.join(20)
    assert not thread.is_alive(), "the stream did not answer"
    return answer


@pytest.mark.journey("J47.1")
def test_the_inbox_stream_answers_as_its_class_says(world, served):  # noqa: F811
    """Given the inbox stream, which the sweep cannot read back because it never ends. When a person
    with no role opens it, then it is served (`200`, an event stream: it asks for no action group);
    a client's `consumer` token is refused as the other API's (`401 TOKEN_INVALID`, `audience`); and
    with no token it is `401 AUTHENTICATION_REQUIRED`."""
    _person(world, "streamer")
    person = _sign_in(_browser(world), "streamer")
    served_person = _opened(served, person)
    assert served_person == {"status": 200, "type": served_person["type"]}
    assert served_person["type"].startswith("text/event-stream")

    client = ok(world.api.post("/clients", {"name": "Stream probe"}), 201)
    post = lambda path, **kwargs: httpx2.post(f"{served}{path}", **kwargs)
    consumer = ok(request_token(post, client["id"], client["secret"], "consumer"))["access_token"]
    wrong = _opened(served, consumer)
    assert wrong["status"] == 401, wrong
    error = json.loads(wrong["body"])["error"]
    assert error["code"] == "TOKEN_INVALID" and error["details"] == {"reason": "audience"}

    bare = _opened(served, None)
    assert bare["status"] == 401
    assert json.loads(bare["body"])["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.journey("J47.1")
@pytest.mark.settings(**SUBSCRIPTIONS, MCP_ENABLED="true")
@pytest.mark.structures(*LEDGER)
def test_without_a_token_every_operation_but_the_open_ones_is_refused(world):
    """Given no token, when every operation the document declares an action for is called, then each
    answers `401 AUTHENTICATION_REQUIRED` with `WWW-Authenticate: Bearer`; the open ones answer
    without one."""
    from harness_identity import TestClient

    declared, open_ = operations(world.api.client.app)
    anonymous = TestClient(world.api.client.app, authenticated=False)
    problems = []
    for operation in declared:
        response = probe(anonymous, operation, {}, "default", real=False)
        error = response.json().get("error") if response.status_code == 401 else None
        if (
            response.status_code != 401
            or error["code"] != "AUTHENTICATION_REQUIRED"
            or response.headers.get("www-authenticate") != "Bearer"
        ):
            problems.append(f"{operation.method.upper()} {operation.path}: {response.status_code}")
    assert not problems, problems[:30]
    for method, path in open_:
        if method == "get":
            assert anonymous.get(path).status_code == 200, path
    assert len(declared) > 200


# --- J47.6: the consumer routes ----------------------------------------------------------------------
# Oracle, from API.md ("Routes that need no token", the consumer routes' paragraph) and J41 (Z3, D306
# to D312), not from the code: a `consumer` token reads a consumer API in a workspace only with a grant
# of that API there (`403 FORBIDDEN` with `consumerApi` and `workspaceKey` otherwise, after the
# workspace's own `404` and before anything else); the index takes a `consumer` token (listing what it
# is granted there) or a `management` one holding Browse in the workspace; a `management` token on a
# data route is `401 TOKEN_INVALID` (`audience`); each API's OpenAPI document needs no token (D412);
# no token is `401 AUTHENTICATION_REQUIRED` on the rest. Managing roles never read consumer data.
CONSUMER = "/api/consumer"


def app_routes(app):
    """Every route the application serves, whether or not its document lists it (an included router
    is walked to its leaves)."""

    def walk(routes):
        for route in routes:
            if hasattr(route, "effective_candidates"):
                yield from walk(route.effective_candidates())
            else:
                yield route

    return list(walk(app.routes))


def _shape(path: str) -> str:
    """A consumer route with its API and version taken out, so the router's routes and a document's
    paths compare."""
    return re.sub(rf"^{CONSUMER}/[^/]+/v[^/]+", "{api}", path)


@dataclass(frozen=True)
class ConsumerOperation:
    api: str
    method: str
    path: str  # with the record id and workspace filled in by `consumer_url`
    kind: str  # "index", "openapi" or "data"
    required: frozenset[str]
    needs_id: bool


def consumer_operations(world) -> list[ConsumerOperation]:
    """The index and every operation of every API's own document, read the way a client reads them."""
    index = ok(world.api.get(CONSUMER))
    found = [ConsumerOperation("", "get", CONSUMER, "index", frozenset(), False)]
    for entry in index["items"]:
        document = ok(world.api.client.get(entry["openapi"]))
        for path, methods in document["paths"].items():
            for method, operation in methods.items():
                required = frozenset(
                    p["name"]
                    for p in operation.get("parameters", [])
                    if p.get("required") and p["in"] == "query"
                )
                kind = "openapi" if path.endswith("/openapi.json") else "data"
                found.append(
                    ConsumerOperation(
                        entry["consumerApi"], method, path, kind, required, "{id}" in path
                    )
                )
        openapi = entry["openapi"].split("?")[0]
        found.append(
            ConsumerOperation(entry["consumerApi"], "get", openapi, "openapi", frozenset(), False)
        )
    return found


def consumer_call(
    http, operation: ConsumerOperation, record_id: str, workspace: str | None, headers
):
    """One read-only call: a record that exists for a path with an ID, the document's own required
    values where it names a query, a body no resolve accepts for the one write-like route."""
    params = {} if workspace is None else {"workspace": workspace}
    for name in operation.required:
        params[name] = "Probed"
    path = operation.path.replace("{id}", record_id)
    if operation.method == "post":
        return http.post(
            path,
            params=params,
            content="[]",
            headers={**headers, "content-type": "application/json"},
        )
    return http.get(path, params=params, headers=headers)


@dataclass(frozen=True)
class Reader:
    """A caller of the consumer routes: the token it sends, what it holds in each workspace."""

    name: str
    audience: str | None  # "consumer", "management" or None for no token
    grants: dict[str, frozenset[str]]  # workspace -> consumer APIs granted
    browse: frozenset[str]  # workspaces where it holds Browse


def consumer_expectation(reader: Reader, operation: ConsumerOperation, workspace: str):
    """What the docs say of this call: ("ok",), ("denied", details), ("invalid", reason) or ("none",)."""
    if operation.kind == "openapi":
        return ("ok",)
    if reader.audience is None:
        return ("none",)
    if operation.kind == "index":
        if reader.audience == "consumer" or workspace in reader.browse:
            return ("ok",)
        return ("denied", {"action": "model.read", "groups": ["browse"], "workspaceKey": workspace})
    if reader.audience != "consumer":
        return ("invalid", "audience")
    if operation.api in reader.grants.get(workspace, frozenset()):
        return ("ok",)
    return ("denied", {"consumerApi": operation.api, "workspaceKey": workspace})


def _consumer_failure(reader, operation, workspace, shown, expected, response) -> str | None:
    where = f"{reader.name}: {operation.method.upper()} {operation.path} [{shown}]"
    _, code, error = _error_of(response)
    status = response.status_code
    match expected[0]:
        case "ok":
            if operation.kind == "openapi":
                return None if status == 200 else f"{where}: open document answered {status}"
            if status in (401, 403) or status >= 500:
                return f"{where}: allowed, answered {status} {code}"
            # Nothing makes a read fail but what it names: with no required value it answers.
            if operation.method == "get" and not operation.required and not operation.needs_id:
                return None if status == 200 else f"{where}: expected 200, answered {status}"
            if operation.method == "post" and status not in (400, 422):
                return f"{where}: an invalid body expected 400, answered {status}"
            if operation.kind == "index" and reader.audience == "consumer":
                granted = sorted(reader.grants.get(workspace, frozenset()))
                listed = sorted(item["consumerApi"] for item in response.json()["items"])
                return None if listed == granted else f"{where}: lists {listed}, granted {granted}"
            return None
        case "denied":
            if status != 403 or code != "FORBIDDEN":
                return f"{where}: refused expected, answered {status} {code}"
            if error.get("details") != expected[1]:
                return f"{where}: refusal names {error.get('details')}, expected {expected[1]}"
            return None
        case "invalid":
            if status != 401 or code != "TOKEN_INVALID":
                return f"{where}: expected 401 TOKEN_INVALID, answered {status} {code}"
            if error.get("details") != {"reason": expected[1]}:
                return f"{where}: reason {error.get('details')}, expected {expected[1]}"
            return None
        case _:
            if status != 401 or code != "AUTHENTICATION_REQUIRED":
                return f"{where}: expected 401, answered {status} {code}"
            if response.headers.get("www-authenticate") != "Bearer":
                return f"{where}: no WWW-Authenticate: Bearer"
            return None


@pytest.mark.journey("J47.6")
@pytest.mark.structures(*STRUCTURES)
def test_the_consumer_routes_follow_their_grants(world):
    """Given a Capi-like API X and another Y active in A and B, and clients granted X, granted Y,
    granted X in B only, holding Reader in A, holding nothing, and no token. When every route the
    consumer tier serves is called (the index, each API's document and each of its operations, in
    the default workspace and in B) with a `consumer` token, a `management` token and none, then only
    a grant of the API in that workspace reads (`200`); the rest is `403 FORBIDDEN` naming the API and
    the workspace, `401 TOKEN_INVALID` (`audience`) for a `management` token on a data route, `401`
    with no token; an index lists what the token is granted and a document needs no token."""
    _with_other(world, "sweep")
    app = world.api.client.app
    record = world.made("R", "Consumer probe")
    operations_ = consumer_operations(world)
    apis = sorted({op.api for op in operations_ if op.api})
    assert len(apis) == 2, apis
    x, y = apis

    # The routes the tier serves are exactly those the documents and the index declare, so a new
    # route the documents do not name fails here.
    declared_shapes = {(op.method, _shape(op.path)) for op in operations_ if op.kind != "index"} | {
        ("get", CONSUMER)
    }
    served_routes = set()
    for route in app_routes(app):
        if route.path == CONSUMER or route.path.startswith(CONSUMER + "/"):
            for method in route.methods - {"HEAD"}:
                served_routes.add((method.lower(), _shape(route.path)))
    generic = {path for _, path in served_routes}
    # The router names a list by its parameter; a document writes out each list it declares.
    covered = {
        (m, "{api}/lists/{list_key}") if p.startswith("{api}/lists/") else (m, p)
        for m, p in declared_shapes
    }
    assert {(m, p.replace("{object_id}", "{id}")) for m, p in served_routes} <= covered | {
        ("get", "{api}/events")
    }, served_routes ^ covered
    assert ("get", "{api}/objects/{id}") in covered and generic

    clients = {}
    holds: dict[str, dict[str, frozenset[str]]] = {}
    browse: dict[str, frozenset[str]] = {}

    def make(name, *apis_in: tuple[str, str], role: bool = False):
        client, caller = _consumer(world, name, *apis_in)
        if role:
            _grant(world, client, role="reader")
        clients[name] = (client, caller)
        grants: dict[str, set[str]] = {}
        for api, workspace in apis_in:
            grants.setdefault(workspace, set()).add(api)
        holds[name] = {k: frozenset(v) for k, v in grants.items()}
        browse[name] = frozenset({W1}) if role else frozenset()

    make("granted-x", (x, W1))
    make("granted-y", (y, W1))
    make("granted-x-in-b", (x, W2))
    make("reader", role=True)
    make("nobody")

    def token(name: str, audience: str) -> dict[str, str]:
        client = clients[name][0]
        answer = ok(request_token(anonymous.post, client["id"], client["secret"], audience))
        return {"Authorization": f"Bearer {answer['access_token']}"}

    anonymous = TestClient(app, authenticated=False)
    readers = []
    for name in clients:
        for audience in ("consumer", "management"):
            readers.append(
                (
                    Reader(f"{name}/{audience}", audience, holds[name], browse[name]),
                    token(name, audience),
                )
            )
    readers.append((Reader("no token", None, {}, frozenset()), {}))

    problems, calls, allowed_calls = [], 0, 0
    for reader, headers in readers:
        for operation in operations_:
            for workspace in (None, W2):
                effective = workspace or W1
                expected = consumer_expectation(reader, operation, effective)
                response = consumer_call(anonymous, operation, record["id"], workspace, headers)
                calls += 1
                allowed_calls += expected[0] == "ok" and operation.kind != "openapi"
                problem = _consumer_failure(
                    reader, operation, effective, workspace or "default", expected, response
                )
                if problem:
                    problems.append(problem)
    assert not problems, f"{len(problems)} differences\n" + "\n".join(problems[:40])
    assert calls > 300 and allowed_calls > 20, (calls, allowed_calls)

    # A workspace that does not exist is its own `404` for a token that holds a grant, before the
    # grant is looked at; a client holding nothing asking for a key no model declares is `403`, not
    # `404` (nothing is revealed about which APIs exist).
    granted = token("granted-x", "consumer")
    nowhere = anonymous.get(
        f"{CONSUMER}/{x}/v1/publications", params={"workspace": "nowhere"}, headers=granted
    )
    assert nowhere.status_code == 404 and nowhere.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"
    nobody = anonymous.get(
        f"{CONSUMER}/no-such-api/v1/publications", headers=token("nobody", "consumer")
    )
    assert nobody.status_code == 403
    assert nobody.json()["error"]["details"] == {"consumerApi": "no-such-api", "workspaceKey": W1}


# --- J47.8: a person holding a role is a client holding it ----------------------------------------------
PERSON_ROLES = ["reader", "contributor", "steward", "security-admin", NO_GRANTS]


@pytest.mark.journey("J47.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
@pytest.mark.parametrize("role", PERSON_ROLES)
def test_a_person_answers_as_a_client_with_the_same_role_does(world, role):
    """Given a client and a person (a local account, signed in through the public sign-in) holding
    the same role, or nothing. When each calls every operation the document declares an action for
    with the same probes, then the person is allowed and refused exactly as the catalogue says and its
    every answer (status, code and the refusal's details) equals the client's: a person's token never
    does more or less than a client's with the same grants."""
    app = world.api.client.app
    declared, _ = operations(app)
    ids = _fixtures(world)
    _, caller = _client(world, f"Twin client {role}", *grants_of(role))
    as_client = collect(caller.api.client, role, ids, declared)

    person = _person(world, "twin" + re.sub(r"[^a-z]", "", role))
    for name, scope in grants_of(role):
        _grant(world, person, kind="user", role=name, scope=scope)
    token = _sign_in(_browser(world), person["email"])
    http = TestClient(app, authenticated=False, headers={"Authorization": f"Bearer {token}"})
    as_person = collect(http, role, ids, declared)

    assert set(as_person) == set(as_client) and len(as_person) > 200
    problems = [outcome.problem for outcome in as_person.values() if outcome.problem]
    assert not problems, f"{role}, as a person: {len(problems)} differences\n" + "\n".join(
        problems[:40]
    )
    # The one documented difference (API.md: the caller's own sessions, password, second factor and
    # passkeys): a client is `403 NOT_A_PERSON` there, and the person, whom the oracle allows, is
    # answered by the route itself.
    personal = {key for key, outcome in as_client.items() if outcome.code == "NOT_A_PERSON"}
    assert personal and all(path.startswith("/api/v1/me/") for _, path, _ in personal), personal
    differences = [
        f"{key}: client {as_client[key].same_as}, person {as_person[key].same_as}"
        for key in as_client
        if as_client[key].same_as != as_person[key].same_as and key not in personal
    ]
    assert all(as_person[key].holds and as_person[key].code != "NOT_A_PERSON" for key in personal)
    assert not differences, f"{role}: {len(differences)} differ\n" + "\n".join(differences[:40])
