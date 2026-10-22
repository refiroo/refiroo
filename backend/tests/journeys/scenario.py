"""The world a journey test runs in: a configuration's seeded data, served by the application.

Each configuration (``configurations.py``) has a ``scenario`` seed in the seed store (``seeds.py``),
built once through the public API and reused until the model, this module or the engine's bootstrap
changes. A test gets a clone of it, an application started on the clone and a :class:`World`, which
names records by their role in the seed (``h4``, ``k07``) and types by their structure (``H``,
``Bnn``), never by a configuration's keys.

The seed holds what many journeys share and what is slow to build: the workspaces, a self-hierarchy
two branches wide and six levels deep with a copy in the second workspace, a set of records of
another application related to one record, and a subtree too large to restructure. A test arranges
the rest of what it needs through the API, so its given steps read as a user's.
"""

import copy
import json
import os
import shutil
import tempfile
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import seeds
from configurations import Configuration, application_of
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import URL, create_engine, text
from sqlalchemy.pool import NullPool

SOURCE = Path(__file__).resolve()
MODELS = Path(tempfile.gettempdir()) / "rdm-journey-models"
# Workspaces of the seed: W1 is the default one.
W1, W2, W3 = "default", "second-site", "closed-site"
# H: two branches; branch one six levels deep (h1…h6), branch two three (j1…j3).
DEPTH = 6
RELATED = 30
LARGE_SUBTREE = 520  # L2 records under one L1: moving it under an L1 retypes 521 records


def model_path(configuration: Configuration) -> Path:
    MODELS.mkdir(exist_ok=True)
    path = MODELS / f"{configuration.name}.json"
    # As built: a consumer API's fields are read in the order written (C-D140).
    text_ = json.dumps(configuration.model)
    if not path.exists() or path.read_text() != text_:
        # Moved into place whole: workers starting one configuration together never read it half
        # written (S1).
        partial = path.with_name(f"{path.name}.{uuid4().hex}")
        partial.write_text(text_)
        partial.replace(path)
    return path


class Api:
    """The management API at ``/api/v1``, as an integrator calls it."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def _call(self, method: str, path: str, **kwargs: Any) -> Response:
        url = (
            path
            if path.startswith(("/api/", "/health", "/metrics", "/docs", "/openapi.json"))
            else f"/api/v1{path}"
        )
        return self.client.request(method, url, **kwargs)

    def get(self, path: str, **params: Any) -> Response:
        return self._call("GET", path, params=_params(params))

    def post(
        self, path: str, body: Any = None, headers: dict[str, str] | None = None, **params: Any
    ) -> Response:
        return self._call("POST", path, json=body, params=_params(params), headers=headers)

    def patch(
        self, path: str, body: Any, headers: dict[str, str] | None = None, **params: Any
    ) -> Response:
        return self._call("PATCH", path, json=body, params=_params(params), headers=headers)

    def put(self, path: str, body: Any, **params: Any) -> Response:
        return self._call("PUT", path, json=body, params=_params(params))

    def delete(self, path: str, **params: Any) -> Response:
        return self._call("DELETE", path, params=_params(params))

    def upload(
        self,
        path: str,
        files: dict[str, tuple[str, bytes, str]],
        data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> Response:
        """A ``multipart/form-data`` request, as a client sends a file with its request."""
        return self._call("POST", path, files=files, data=data, headers=headers)


def _params(params: dict[str, Any]) -> list[tuple[str, Any]]:
    """Query parameters; a list value repeats the parameter, ``None`` leaves it out, and a key
    written with ``__`` stands for ``.`` (``filter__code__eq`` is ``filter.code.eq``)."""
    pairs = []
    for key, value in params.items():
        name = key.replace("__", ".")
        for item in value if isinstance(value, list) else [value]:
            if item is None:
                continue
            pairs.append((name, str(item).lower() if isinstance(item, bool) else item))
    return pairs


def ok(response: Response, status: int = 200) -> Any:
    assert response.status_code == status, f"{response.status_code}: {response.text}"
    return response.json() if response.content else None


def refused(response: Response, status: int, code: str) -> dict[str, Any]:
    """The error a refusal carries, after checking its status and code."""
    assert response.status_code == status, f"{response.status_code}: {response.text}"
    error = response.json()["error"]
    assert error["code"] == code, error
    return error


@dataclass
class World:
    configuration: Configuration
    api: Api
    database: URL
    ids: dict[str, str] = field(default_factory=dict)

    # --- the model ---

    def key(self, structure: str) -> str:
        return self.configuration.key(structure)

    def app(self, structure: str) -> str:
        return application_of(self.configuration, structure)

    def holds(self, structure: str) -> bool:
        return self.configuration.holds((structure,))

    def _type(self, structure: str) -> dict[str, Any]:
        key = self.key(structure)
        return next(item for item in self.configuration.model["objectTypes"] if item["key"] == key)

    def attribute_name(self, structure: str) -> str:
        key = self.key(structure)
        types = self.configuration.model["attributeTypes"]
        return next(item["name"] for item in types if item["key"] == key)

    def required_values(self, structure: str) -> dict[str, Any]:
        """Values for every attribute the type requires, and the first of an at-least-one-of set:
        what a client fills in so a record can be created at all."""
        object_type = self._type(structure)
        attribute_types = {item["key"]: item for item in self.configuration.model["attributeTypes"]}
        values = {}
        wanted = [b["attributeTypeKey"] for b in object_type["attributes"] if b.get("required")]
        wanted += object_type.get("validation", {}).get("atLeastOneOf", [])[:1]
        for key in wanted:
            values[key] = _value_for(attribute_types[key], key)
        return values

    # --- records ---

    def create(
        self,
        structure: str,
        name: str,
        *,
        parent: str | None = None,
        values: dict[str, Any] | None = None,
        relations: list[dict[str, Any]] | None = None,
        workspace: str | None = W1,
        change_set: dict[str, Any] | None = None,
        id: str | None = None,
        fill: bool = True,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """``POST /objects`` for a record of ``structure``; ``values`` are keyed by structure
        (``R.n``) or by attribute key, and fill the type's required values unless ``fill`` is off."""
        attributes = self.required_values(structure) if fill else {}
        for key, value in (values or {}).items():
            attributes[self.key(key) if key in self.configuration.keys else key] = value
        body: dict[str, Any] = {
            "applicationKey": self.app(structure),
            "objectTypeKey": self.key(structure),
            "name": name,
            "attributes": [{"attributeTypeKey": k, "value": v} for k, v in attributes.items()],
        }
        if workspace is not None and change_set is None:
            body["workspaceKey"] = workspace
        if parent is not None:
            body["parentObjectId"] = parent
        if relations:
            body["initialRelations"] = relations
        if change_set is not None:
            body["changeSetId"] = change_set["id"]
            body["expectedChangeSetVersion"] = change_set["version"]
        if id is not None:
            body["id"] = id
        return self.api.post("/objects", body, headers=headers)

    def made(self, structure: str, name: str, **kwargs: Any) -> dict[str, Any]:
        """A record created as :meth:`create` does, which must succeed."""
        return ok(self.create(structure, name, **kwargs), 201)

    def read(self, structure: str, object_id: str, **params: Any) -> Response:
        return self.api.get(f"/objects/{self.key(structure)}/{object_id}", **params)

    def record(self, structure: str, object_id: str, **params: Any) -> dict[str, Any]:
        return ok(self.read(structure, object_id, **params))

    def update(self, structure: str, object_id: str, version: int, **changes: Any) -> Response:
        """``PATCH /objects/{type}/{id}``; ``values`` keyed by structure, ``parent`` a record ID or
        ``None`` for the top level."""
        body: dict[str, Any] = {"expectedVersion": version}
        if "name" in changes:
            body["name"] = changes["name"]
        if "parent" in changes:
            body["parentObjectId"] = changes["parent"]
        if "values" in changes:
            body["attributes"] = [
                {"attributeTypeKey": self.key(k) if k in self.configuration.keys else k, "value": v}
                for k, v in changes["values"].items()
            ]
        return self.api.patch(f"/objects/{self.key(structure)}/{object_id}", body)

    def relate(
        self,
        structure: str,
        source: str,
        target: str,
        values: dict[str, Any] | None = None,
        **extra: Any,
    ) -> Response:
        body = {
            "relationTypeKey": self.key(structure),
            "fromObjectId": source,
            "toObjectId": target,
            "attributes": {
                self.key(k) if k in self.configuration.keys else k: v
                for k, v in (values or {}).items()
            },
            **extra,
        }
        return self.api.post("/relations", body)

    def owner(self, structure: str, source: str) -> dict[str, Any]:
        """The initial relation that makes a new record a dependant of ``source``."""
        return {
            "relationTypeKey": self.key(structure),
            "direction": "incoming",
            "otherObjectId": source,
        }

    def dependant_parent(self, g: str, workspace: str = W1) -> str:
        """Where a ``D`` record stands under the ``G`` record ``g``: ``g`` itself, or a new ``M``
        container under it where ``D`` stands only in a container (the ``deep-scope`` shape)."""
        if "deep-scope" not in self.configuration.shapes:
            return g
        return self.made("M", f"Container {uuid4().hex[:6]}", parent=g, workspace=workspace)["id"]

    def value(self, record: dict[str, Any], structure: str) -> Any:
        key = self.key(structure)
        return next(
            (a["value"] for a in record["attributes"] if a["attributeTypeKey"] == key), None
        )

    def names(self, page: dict[str, Any]) -> list[str]:
        return [item["name"] for item in page["items"]]

    # --- change sets ---

    def change_set(self, workspace: str = W1, **body: Any) -> dict[str, Any]:
        body.setdefault("source", "currentLive")
        return ok(self.api.post(f"/workspaces/{workspace}/change-sets", body), 201)

    def current(self, change_set: dict[str, Any]) -> dict[str, Any]:
        return ok(self.api.get(f"/change-sets/{change_set['id']}"))

    def publish(self, change_set: dict[str, Any], workspace: str = W1) -> dict[str, Any]:
        active = ok(self.api.get(f"/workspaces/{workspace}/publications", pageSize=1))["items"]
        current = [item for item in active if item.get("status") == "active"]
        body = {
            "expectedChangeSetVersion": self.current(change_set)["version"],
            "expectedActivePublicationId": current[0]["id"] if current else None,
        }
        return ok(self.api.post(f"/change-sets/{change_set['id']}/publication", body))

    # --- model releases ---

    def install(self, model: dict[str, Any], name: str = "Candidate") -> dict[str, Any]:
        """A model installed as a release through a draft (never activated)."""
        draft = ok(self.api.post("/model-drafts", {"name": name, "model": model}), 201)
        installation = {"expectedVersion": draft["version"]}
        return ok(self.api.post(f"/model-drafts/{draft['id']}/installation", installation), 201)

    def workspace_model(self, workspace: str = W1) -> dict[str, Any]:
        """The release ``workspace`` runs and its assignment's version (``GET …/model``)."""
        return ok(self.api.get(f"/workspaces/{workspace}/model"))

    def activate(self, release_id: str, workspace: str = W1) -> Response:
        """``release_id`` activated into ``workspace``, claiming its current assignment."""
        current = ok(self.api.get(f"/workspaces/{workspace}/model"))
        body = {
            "releaseId": release_id,
            "expectedVersion": current["version"],
            "expectedReleaseId": current["releaseId"],
        }
        return self.api.post(f"/workspaces/{workspace}/model/activation", body)

    def activate_everywhere(self, release_id: str) -> Response:
        """``release_id`` activated into the default workspace and then into every other active
        workspace running the release it ran: what one activation did before 0.11. The default
        workspace's answer; a refusal there activates nothing else."""
        before = self.workspace_model()["releaseId"]
        answer = self.activate(release_id)
        if answer.status_code != 200:
            return answer
        running = ok(self.api.get("/workspace-models", releaseId=before, pageSize=500))["items"]
        for item in running:
            other = self.activate(release_id, item["workspaceKey"])
            if other.status_code != 200:
                refused(other, 409, "WORKSPACE_RETIRED")
        return answer

    def candidate(self, kind: str) -> tuple[dict[str, Any], str]:
        """A model derived from the configuration's, with its new release version, and the key of
        the attribute the change concerns.

        ``compatible``: R gains an optional text attribute, R's application a new type and its first
        view a new name; live content fits it. ``incompatible``: an attribute R binds as optional, which R records
        created without it lack, becomes required.
        """
        model = copy.deepcopy(self.configuration.model)
        release = model["release"]
        r_type = next(t for t in model["objectTypes"] if t["key"] == self.key("R"))
        if kind == "compatible":
            key = f"{self.key('R')}-added-field"
            model["attributeTypes"].append({"key": key, "name": "Added field"})
            r_type["attributes"].append({"attributeTypeKey": key, "order": 999})
            application = next(a for a in model["applications"] if a["key"] == self.app("R"))
            application["views"][0]["name"] = "Renamed view"
            added_type = f"{self.key('R')}-added-type"
            model["objectTypes"].append(
                {
                    "key": added_type,
                    "name": "Added type",
                    "pluralName": "Added types",
                    "attributes": [],
                    "features": {"rootCreatable": True},
                }
            )
            application["objectTypeKeys"].append(added_type)
            release["version"] = f"{release['version']}-next"
        else:
            defaults = {a["key"] for a in model["attributeTypes"] if a.get("default") is not None}
            binding = next(
                b
                for b in r_type["attributes"]
                if not b.get("required")
                and not b.get("readOnly")
                and b["attributeTypeKey"] not in defaults
            )
            binding["required"] = True
            key = binding["attributeTypeKey"]
            release["version"] = f"{release['version']}-strict"
        return model, key

    # --- two actors at once ---

    @contextmanager
    def holding(self, workspace: str, *, as_write: bool = False) -> Iterator[Held]:
        """Hold the workspace's row from the test's own connection while the block runs.

        Requests started with ``Held.start`` that write the workspace wait for it; ``Held.waiting``
        returns once PostgreSQL shows that many of them waiting (watched with autocommit, because
        ``pg_stat_activity`` is a snapshot per transaction). The row is let go when the block ends,
        before anything waits for the requests, so a failure cannot leave the test and the requests
        waiting on each other.
        """
        engine = create_engine(self.database, poolclass=NullPool)
        pool = ThreadPoolExecutor(4)
        holder = engine.connect()
        held = Held(pool, engine)
        try:
            # Held for update, every request touching the workspace waits, change set writes
            # (key share) too. ``as_write`` holds it as a live write does (FOR NO KEY UPDATE), for
            # an activation to run meanwhile, as it does beside a live write (0.11 R, R-F12).
            lock = "FOR NO KEY UPDATE" if as_write else "FOR UPDATE"
            holder.execute(
                text(f"SELECT 1 FROM workspaces WHERE key = :k {lock}"), {"k": workspace}
            )
            yield held
        finally:
            holder.rollback()
            holder.close()
            held.close()

    def race(self, workspace: str, *calls: Callable[[], Response]) -> list[Response]:
        """Run ``calls`` at once, each in flight before any commits: the engine then decides them one
        after another, as it would requests from clients that arrived together."""
        with self.holding(workspace) as held:
            futures = [held.start(call) for call in calls]
            held.waiting(len(calls))
        return [future.result(timeout=30) for future in futures]

    # --- consumer API definitions ---

    def with_consumer_api(
        self,
        model: dict[str, Any],
        *,
        version: int = 1,
        drop_flag: bool = False,
        extra: bool = False,
    ) -> dict[str, Any]:
        """``model`` declaring one consumer API over R besides the ones it has: an ID, a name, R's
        unique value and (unless dropped) its boolean as fields, related records over B1n to K and a
        list; ``extra`` adds a field and a second list."""
        fields: dict[str, Any] = {"id": {"role": "id"}, "name": {"role": "name", "from": "name"}}
        fields["number"] = self.key("R.u")
        if not drop_flag:
            fields["flag"] = self.key("R.b")
        if extra:
            fields["due"] = self.key("R.dt")
        lists = {"ledgers": {"of": self.key("R")}}
        if extra:
            lists["tokens"] = {"of": self.key("K")}
        relation = next(item for item in model["relationTypes"] if item["key"] == self.key("B1n"))
        others = [item for item in model.get("consumerApis", []) if item["key"] != "journey-api"]
        model["consumerApis"] = others + [
            {
                "key": "journey-api",
                "name": "Journey API",
                "contractVersion": version,
                "exposes": [self.key("R"), self.key("K")],
                "publicNames": {self.key("R"): "Ledger", self.key("K"): "Token"},
                "object": {
                    "fields": fields,
                    "related": {
                        "tokens": {"via": relation["key"], "fields": {"tokenName": "name"}},
                        # From K a one-to-many relationship gives one ledger; many-to-many, a list.
                        "ledger": {"via": relation["reverseKey"], "fields": {"ledgerName": "name"}},
                    },
                },
                "operations": {"objects": {}, "xref": {}, "resolve": {}, "lists": lists},
                "filters": {"type": {"byType": True}},
            }
        ]
        return model


# --- the consumer API ---


def consumer_object(
    world: World, object_id: str, *, version: int = 1, api: str | None = None, **params: Any
) -> Response:
    """``GET /api/consumer/{consumerApi}/v{version}/objects/{id}`` of ``Capi`` (or ``api``)."""
    key = api if api is not None else world.key("Capi")
    return world.api.get(f"/api/consumer/{key}/v{version}/objects/{object_id}", **params)


def consumer_list(
    world: World, list_key: str, *, version: int = 1, api: str | None = None, **params: Any
) -> Response:
    """``GET /api/consumer/{consumerApi}/v{version}/lists/{listKey}`` of ``Capi`` (or ``api``)."""
    key = api if api is not None else world.key("Capi")
    return world.api.get(f"/api/consumer/{key}/v{version}/lists/{list_key}", **params)


def consumer_list_typed(world: World, list_key: str, query: str, *, version: int = 1) -> Response:
    """The list read with ``query`` exactly as a client types it into the URL: an HTTP library given
    parameters would percent-encode the commas that separate values (C3b)."""
    url = f"/api/consumer/{world.key('Capi')}/v{version}/lists/{list_key}?{query}"
    return world.api.client.get(url)


def consumer_xref(world: World, *, version: int = 1, **params: Any) -> Response:
    """``GET /api/consumer/{consumerApi}/v{version}/xref`` of ``Capi``."""
    return world.api.get(f"/api/consumer/{world.key('Capi')}/v{version}/xref", **params)


def consumer_resolve(world: World, body: Any, *, version: int = 1, **params: Any) -> Response:
    """``POST /api/consumer/{consumerApi}/v{version}/resolve`` of ``Capi`` with ``body``."""
    return world.api.post(f"/api/consumer/{world.key('Capi')}/v{version}/resolve", body, **params)


def consumer_publications(world: World, *, version: int = 1, **params: Any) -> Response:
    """``GET /api/consumer/{consumerApi}/v{version}/publications`` of ``Capi``."""
    return world.api.get(f"/api/consumer/{world.key('Capi')}/v{version}/publications", **params)


def consumer_events(world: World, *, version: int = 1, **params: Any) -> Response:
    """``GET /api/consumer/{consumerApi}/v{version}/events`` of ``Capi``."""
    return world.api.get(f"/api/consumer/{world.key('Capi')}/v{version}/events", **params)


def derive_events(world: World) -> int:
    """Run the application's event deriver until every workspace is derived to its head (C10);
    the journey application does not start its thread."""
    return world.api.client.app.state.event_deriver.run_until_idle()


def dispatch(world: World, now: datetime | None = None) -> int:
    """Run the application's webhook dispatcher until nothing more is due at ``now`` (C12); the
    journey application does not start its thread. ``now`` is the dispatcher's clock: a test moves
    it forward instead of waiting."""
    return world.api.client.app.state.consumer_dispatcher.run_until_idle(now)


def consumer_xref_typed(world: World, query: str, *, version: int = 1) -> Response:
    """XREF with ``query`` exactly as a client types it into the URL (C3b)."""
    return world.api.client.get(f"/api/consumer/{world.key('Capi')}/v{version}/xref?{query}")


class Held:
    """Requests started while a workspace is held (``World.holding``)."""

    def __init__(self, pool: ThreadPoolExecutor, engine: Any) -> None:
        self.pool, self.engine, self.futures = pool, engine, []

    def start(self, call: Callable[[], Response]) -> Any:
        future = self.pool.submit(call)
        self.futures.append(future)
        return future

    def waiting(self, count: int) -> None:
        with self.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as watcher:
            _wait_for_lock_waiters(watcher, count, self.futures)

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.engine.dispose()


def numbered(configuration: Configuration) -> dict[str, Any]:
    """The configuration's model as a release whose ``R.n`` (integer) and ``R.dt`` (date) are
    unique as well (0.11 Q2): unique values compared outside text."""
    model = copy.deepcopy(configuration.model)
    model["release"]["version"] += "-numbered"
    for item in model["attributeTypes"]:
        if item["key"] in (configuration.key("R.n"), configuration.key("R.dt")):
            item["features"] = {**item.get("features", {}), "unique": True}
    return model


@contextmanager
def planned(
    chosen: Callable[[str], bool], *, ordered: bool = False
) -> Iterator[list[dict[str, Any]]]:
    """The plans of the statements ``chosen`` picks while the block runs, planned with sequential
    scans off so a plan shows whether an index applies whatever the tables' size (as
    ``test_schema_drift`` checks the job indexes). ``ordered`` also turns a full sort off, so the
    plan shows whether an index can give the statement's order. Only explained: each statement
    still runs once."""
    from sqlalchemy import event

    from app.db import get_engine

    plans: list[dict[str, Any]] = []

    def explain(connection, cursor, statement, parameters, context, executemany):
        if chosen(statement):
            cursor.execute("SET enable_seqscan = off")
            if ordered:
                cursor.execute("SET enable_sort = off")
            cursor.execute("EXPLAIN (FORMAT JSON) " + statement, parameters)
            plans.append(cursor.fetchone()[0][0]["Plan"])
            cursor.execute("RESET enable_seqscan")
            cursor.execute("RESET enable_sort")

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", explain)
    try:
        yield plans
    finally:
        event.remove(engine, "before_cursor_execute", explain)


def plan_reads(plan: dict[str, Any]) -> set[str]:
    """The tables and indexes a plan reads, its children's included."""
    own = {plan[name] for name in ("Relation Name", "Index Name") if name in plan}
    return own.union(*(plan_reads(child) for child in plan.get("Plans", [])))


def _wait_for_lock_waiters(watcher: Any, count: int, futures: list[Any]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        waiting = watcher.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                "AND wait_event_type = 'Lock'"
            )
        ).scalar_one()
        if waiting >= count:
            return
        finished = [future for future in futures if future.done()]
        if finished:
            raise AssertionError(f"a call finished without waiting: {finished[0].result().text}")
        time.sleep(0.02)
    raise AssertionError(f"{count} calls never waited for the workspace together")


def _value_for(attribute: dict[str, Any], key: str) -> Any:
    kind = attribute.get("valueType", "text")
    minimum = attribute.get("validation", {}).get("minimum")
    if kind in {"integer", "decimal"}:
        return minimum if minimum is not None else 1
    if kind == "boolean":
        return True
    if kind == "date":
        return date(2026, 1, 1).isoformat()
    if kind == "dateTime":
        return "2026-01-01T00:00:00Z"
    return f"{key}-{uuid4().hex[:8]}"


# --- the seed -------------------------------------------------------------------------------------


def build(world: World) -> dict[str, str]:
    """The shared data, through the API, for the structures the configuration holds."""
    api = world.api
    ids: dict[str, str] = {}
    ok(api.post("/workspaces", {"key": W2, "label": "Second site"}), 201)
    closed = ok(api.post("/workspaces", {"key": W3, "label": "Closed site"}), 201)

    if world.configuration.holds(("H",)):
        parent = None
        for level in range(1, DEPTH + 1):
            record = world.made(
                "H",
                f"Level {level} north",
                parent=parent,
                values={"H.code": f"N{level}", "H.rank": level},
            )
            ids[f"h{level}"] = parent = record["id"]
        parent = None
        for level in range(1, 4):
            record = world.made(
                "H",
                f"Level {level} south",
                parent=parent,
                values={"H.code": f"S{level}", "H.rank": level},
            )
            ids[f"j{level}"] = parent = record["id"]
        parent = None
        for level in range(1, 6):
            record = world.made(
                "H",
                f"Level {level} north",
                parent=parent,
                workspace=W2,
                values={"H.code": f"N{level}", "H.rank": level},
            )
            ids[f"w2h{level}"] = parent = record["id"]

    if world.configuration.holds(("H", "K", "Bnn")):
        for index in range(1, RELATED + 1):
            values: dict[str, Any] = {"K.code": f"K{index:02d}"}
            if index % 5:  # every fifth leaves its rank unset
                values["K.rank"] = (index * 7) % 11
            record = world.made("K", f"Token {index:02d}", values=values)
            ids[f"k{index:02d}"] = record["id"]
            ok(world.relate("Bnn", ids["h5"], record["id"], {"Bnn.weight": index}), 201)

    if world.configuration.holds(("L1", "L2")):
        top = world.made("L1", "Large ladder", values={"L.code": "LARGE"})
        ids["large"] = top["id"]
        for index in range(LARGE_SUBTREE):
            world.made(
                "L2", f"Large {index:03d}", parent=top["id"], values={"L.code": f"LG{index:03d}"}
            )

    if world.configuration.holds(("V", "K", "Bvk")) and "k01" in ids:
        ids.update(_seed_articles(world, ids))

    if world.configuration.holds(("R",)):
        ids["w3r"] = world.made("R", "Closed ledger", workspace=W3)["id"]
    ok(api.patch(f"/workspaces/{W3}", {"expectedVersion": closed["version"], "status": "retired"}))
    return ids


# Settings every journey application starts with; a test may override them (``settings`` marker).
DEFAULT_SETTINGS = {"MODEL_ADMIN_MUTATIONS_ENABLED": "true"}


WORDS = (
    "amber",
    "birch",
    "cedar",
    "delta",
    "ember",
    "fjord",
    "grove",
    "harbor",
    "iris",
    "juniper",
    "kestrel",
    "lumen",
    "maple",
    "nectar",
    "onyx",
    "pine",
    "quartz",
    "raven",
    "sable",
    "tundra",
    "umber",
    "vale",
    "willow",
    "xenon",
    "yarrow",
    "zephyr",
)
ARTICLES = 250  # five tops and 49 children under each


def _seed_articles(world: World, known: dict[str, str]) -> dict[str, str]:
    """250 V records in one atomic batch: five tops, 49 children each; names spread over the alphabet
    with duplicates; every value type set, and some left unset; one record related to 30 K records,
    a few to one."""
    ids: dict[str, str] = {}
    items = []
    for index in range(ARTICLES):
        top = index % 50 == 0
        record_id = str(uuid4())
        if top:
            ids[f"v_top{index // 50}"] = record_id
        values = {"V.code": f"A{index:03d}"}
        if index % 7:
            values["V.rank"] = (index * 13) % 97
        if index % 5:
            values["V.amount"] = f"{index * 1.25:.2f}"
        if index % 3:
            values["V.flag"] = index % 2 == 0
        values["V.on"] = f"2026-{(index % 12) + 1:02d}-{(index % 27) + 1:02d}"
        values["V.at"] = f"2026-03-{(index % 27) + 1:02d}T{index % 24:02d}:00:00Z"
        word = WORDS[index % len(WORDS)]
        item = {
            "op": "create",
            "id": record_id,
            "applicationKey": world.app("V"),
            "objectTypeKey": world.key("V"),
            "name": f"{word.title()} {index // 26:02d}" if index % 10 else f"{word.title()} shared",
            "attributes": [
                {"attributeTypeKey": world.key(k), "value": v} for k, v in values.items()
            ],
        }
        if not top:
            item["parent"] = {"id": ids[f"v_top{index // 50}"]}
        items.append(item)
        if index == 7:
            ids["v_many"] = record_id
        if index in (8, 9, 10):
            ids[f"v_one{index - 7}"] = record_id
    body = {"workspaceKey": W1, "policy": "atomic", "run": "inline", "items": items}
    result = ok(world.api.post("/batches", body))
    assert result["job"]["result"] == "applied", result["job"]
    for index in range(1, RELATED + 1):
        ok(world.relate("Bvk", ids["v_many"], known[f"k{index:02d}"]), 201)
    for one in (1, 2, 3):
        ok(world.relate("Bvk", ids[f"v_one{one}"], known[f"k{one:02d}"]), 201)
    return ids


@contextmanager
def application(
    configuration: Configuration, database: URL, settings: dict[str, str] | None = None
) -> Iterator[World]:
    from app.config import reload_settings
    from app.main import create_app

    # Each application keeps its job files apart, in a directory named after its database.
    files = Path(tempfile.gettempdir()) / "rdm-journey-job-files" / str(database.database)
    wanted = {**DEFAULT_SETTINGS, "JOB_FILE_DIR": str(files), **(settings or {})}
    saved = {key: os.environ.get(key) for key in wanted}
    os.environ.update(wanted)
    try:
        with seeds.application_environment(database, model_path(configuration)):
            app = create_app()
            app.state.run_job_worker = False
            app.state.run_event_deriver = False
            app.state.run_consumer_dispatcher = False
            app.state.run_process_heartbeat = False
            with TestClient(app) as client:
                yield World(configuration, Api(client), database)
    finally:
        shutil.rmtree(files, ignore_errors=True)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload_settings()


def scenario_seed(configuration: Configuration) -> str:
    """The name of the configuration's seed, registered on first use."""
    name = f"scenario-{configuration.name}"

    def build_seed(url: URL) -> dict[str, Any]:
        with application(configuration, url) as world:
            return {"ids": build(world)}

    def inputs() -> list[str | Path]:
        return [
            json.dumps(configuration.model, sort_keys=True),
            SOURCE,
            seeds.APP / "engine" / "model" / "bootstrap.py",
        ]

    seeds.register(seeds.Seed(name, build_seed, inputs, base="schema"))
    return name


@contextmanager
def world_for(
    configuration: Configuration, settings: dict[str, str] | None = None
) -> Iterator[World]:
    """A clone of the configuration's seed, the application on it, and the world it holds."""
    name = scenario_seed(configuration)
    payload = seeds.ensure(name)
    url = seeds.clone(name)
    try:
        with application(configuration, url, settings) as world:
            world.ids = dict(payload["ids"])
            yield world
    finally:
        seeds.drop(url.database)
