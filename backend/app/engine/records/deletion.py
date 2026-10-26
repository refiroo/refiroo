"""Deleting records with what depends on them, as set work in PostgreSQL (0.9 K2b, D120–D123,
PG-D18).

A record's impact is its closure: its containment descendants and the targets of an oriented,
required ``one-to-one`` or ``one-to-many`` relation from it, recursively, with every relationship
incident to them. Without ``cascade`` a record with dependants or a relationship other than its
containment edges is refused ``OBJECT_HAS_DEPENDANTS`` with its impact and a
``deletionPreviewToken``; with ``cascade`` the token must still match the impact as it is now
(``DELETION_PREVIEW_REQUIRED``, ``DELETION_PREVIEW_CHANGED``). The token signs a digest of the
impact's records and relationships with their versions, bound to the context, the record and the
model, so one record's token is the same whether the single ``DELETE`` or a batch item gave it.

One path serves the single ``DELETE`` (a run of one) and a batch's run of delete items, live and in
a change set (D123). A run is decided together in a few statements, whatever its size: the
closures of all its records in one recursive query into a temporary table, each record of a closure
belonging to the earliest item that reaches it, as deleting the items in order would leave it; the
relationships they touch in a second table; each item's counts and digest in one query. Python
decides each item from those rows; when it refuses an item whose closure overlaps a later one's,
the run is decided again without it, since the later item's impact then grows. The accepted items
are then written as set statements: the audit entries with their subjects and feed positions, the
relation sets they advance, and the records and relationships removed live or tombstoned in the
change set.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Integer,
    String,
    and_,
    column,
    func,
    insert,
    literal,
    null,
    or_,
    select,
    table,
    text,
    true,
    union_all,
    values,
)
from sqlalchemy.orm import Session

from ...common.cursors import decode_cursor, encode_cursor
from ...errors import ApiError, api_error
from ...models.database import AuditEvent, ChangeSet, ObjectRelation, RdmObject
from ...models.schema import EngineModel
from ..authorization.writes import allowance, refuse_types
from ..indexes import matrix_states
from ..reads.snapshot_reads import (
    change_set_context,
    effective_object_value,
    object_projection,
    relation_projection,
)
from ..workspaces.catalogue import resolve_workspace
from .audit import audit_actor_of, audit_cause_of
from .context import load_object
from .feed import take_positions
from .writes import LiveWrites

_TABLES = """
CREATE TEMPORARY TABLE IF NOT EXISTS deletion_roots (
    item integer PRIMARY KEY, object_id varchar(36) NOT NULL, object_type_key text NOT NULL
) ON COMMIT DROP;
CREATE TEMPORARY TABLE IF NOT EXISTS deletion_reach (
    item integer NOT NULL, object_id varchar(36) NOT NULL, object_type_key text NOT NULL,
    reason text NOT NULL
) ON COMMIT DROP;
CREATE INDEX IF NOT EXISTS deletion_reach_object ON deletion_reach (object_id);
CREATE TEMPORARY TABLE IF NOT EXISTS deletion_objects (
    object_id varchar(36) PRIMARY KEY, item integer NOT NULL, reason text NOT NULL,
    application_key text, object_type_key text, name text, parent_object_id varchar(36),
    attributes json, version integer, workspace_key text
) ON COMMIT DROP;
CREATE INDEX IF NOT EXISTS deletion_objects_item ON deletion_objects (item);
CREATE TEMPORARY TABLE IF NOT EXISTS deletion_relations (
    relation_id varchar(36) PRIMARY KEY, item integer NOT NULL, relation_type_key text,
    from_object_id varchar(36), to_object_id varchar(36), attributes json, version integer,
    from_type text, to_type text, from_application text, to_application text,
    from_item integer, to_item integer, from_workspace text,
    to_workspace text, containment boolean NOT NULL
) ON COMMIT DROP;
"""

_ROOTS = table(
    "deletion_roots",
    column("item", Integer),
    column("object_id", String),
    column("object_type_key", String),
)
_REACH = table(
    "deletion_reach",
    column("item", Integer),
    column("object_id", String),
    column("object_type_key", String),
    column("reason", String),
)
_OBJECTS = table(
    "deletion_objects",
    column("object_id", String),
    column("item", Integer),
    column("reason", String),
    column("application_key", String),
    column("object_type_key", String),
    column("name", String),
    column("parent_object_id", String),
    column("attributes", JSON),
    column("version", Integer),
    column("workspace_key", String),
)
_RELATIONS = table(
    "deletion_relations",
    column("relation_id", String),
    column("item", Integer),
    column("relation_type_key", String),
    column("from_object_id", String),
    column("to_object_id", String),
    column("attributes", JSON),
    column("version", Integer),
    column("from_type", String),
    column("to_type", String),
    column("from_application", String),
    column("to_application", String),
    column("from_item", Integer),
    column("to_item", Integer),
    column("from_workspace", String),
    column("to_workspace", String),
    column("containment", String),
)

# Each item's counts, its root's owner (another item when an earlier one reaches it) and its
# digest: the records and relationships of its impact with their versions, in one canonical order.
_SUMMARY = text(
    """
    WITH counted AS (
        SELECT item, object_type_key, count(*) AS n,
            bool_or(workspace_key IS DISTINCT FROM :workspace) AS offside
        FROM deletion_objects GROUP BY item, object_type_key
    ), objects AS (
        SELECT item, sum(n)::integer AS objects, json_object_agg(object_type_key, n) AS by_type,
            bool_or(offside) AS offside
        FROM counted GROUP BY item
    ), relations AS (
        SELECT item, count(*)::integer AS relationships,
            (count(*) FILTER (WHERE from_item IS DISTINCT FROM item
                OR to_item IS DISTINCT FROM item))::integer AS retained,
            (count(*) FILTER (WHERE NOT containment))::integer AS linked,
            (count(*) FILTER (WHERE containment))::integer AS contained,
            bool_or(from_workspace IS DISTINCT FROM :workspace
                OR to_workspace IS DISTINCT FROM :workspace) AS offside
        FROM deletion_relations GROUP BY item
    ), lines AS (
        SELECT item, 'o|' || object_id || '|' || version || '|' || coalesce(parent_object_id, '')
            AS line FROM deletion_objects
        UNION ALL
        SELECT item, 'r|' || relation_id || '|' || version || '|' || relation_type_key || '|'
            || from_object_id || '|' || to_object_id FROM deletion_relations
    ), digests AS (
        SELECT item, encode(sha256(convert_to(
            string_agg(line, ',' ORDER BY line COLLATE "C"), 'UTF8')), 'hex') AS digest
        FROM lines GROUP BY item
    )
    SELECT root.item, owner.item AS owner, objects.objects, objects.by_type,
        coalesce(relations.relationships, 0), coalesce(relations.retained, 0),
        coalesce(relations.linked, 0), coalesce(relations.contained, 0),
        coalesce(objects.offside, false) OR coalesce(relations.offside, false), digests.digest
    FROM deletion_roots root
    LEFT JOIN deletion_objects owner ON owner.object_id = root.object_id
    LEFT JOIN objects ON objects.item = root.item
    LEFT JOIN relations ON relations.item = root.item
    LEFT JOIN digests ON digests.item = root.item
    ORDER BY root.item
    """
)

# The items a refused earlier item touches: their closures share a record, or a relationship joins
# their records. Once the refused item stays, their impacts are not what this round read.
_OVERLAPS = text(
    """
    SELECT later.item FROM deletion_reach refused
    JOIN deletion_reach later ON later.object_id = refused.object_id AND later.item > refused.item
    WHERE refused.item = ANY(:refused)
    UNION
    SELECT greatest(from_item, to_item) FROM deletion_relations
    WHERE item = ANY(:refused) AND from_item <> to_item
    """
)

_LIVE_AUDIT = text(
    """
    WITH entries AS (
        SELECT r.item, 0 AS rank, r.relation_id AS id, 'relation' AS aggregate_type, r.version,
            json_build_object('relationTypeKey', r.relation_type_key,
                'fromObjectId', r.from_object_id, 'toObjectId', r.to_object_id,
                'cascadeRootObjectId', root.object_id) AS changes,
            NOT r.containment AS feed,
            json_build_object('relationTypeKey', r.relation_type_key,
                'fromObjectId', r.from_object_id, 'toObjectId', r.to_object_id) AS subject
        FROM deletion_relations r JOIN deletion_roots root ON root.item = r.item
        UNION ALL
        SELECT o.item, 1, o.object_id, 'object', o.version,
            json_build_object('objectTypeKey', o.object_type_key,
                'cascadeRootObjectId', root.object_id),
            true,
            json_build_object('objectTypeKey', o.object_type_key,
                'applicationKey', o.application_key, 'parentObjectId', o.parent_object_id)
        FROM deletion_objects o JOIN deletion_roots root ON root.item = o.item
    ), placed AS (
        SELECT entries.*, CASE WHEN feed THEN CAST(:first AS integer) - 1 + sum(feed::integer) OVER (
            ORDER BY item, rank, id COLLATE "C" ROWS UNBOUNDED PRECEDING) END AS position
        FROM entries
    ), inserted AS (
        INSERT INTO audit_events (event_id, aggregate_type, aggregate_id, action, version,
            changes, occurred_at, cause_kind, cause_id, workspace_key, feed_position,
            model_release_id, subject, actor_kind, actor_user_id, actor_client_id)
        SELECT gen_random_uuid()::text, aggregate_type, id, 'deleted', version, changes,
            CAST(:now AS timestamptz), CAST(:cause_kind AS varchar), CAST(:cause_id AS varchar),
            CAST(:workspace AS varchar), position,
            CASE WHEN feed THEN CAST(:release AS integer) END, subject,
            CAST(:actor_kind AS varchar), CAST(:actor_user_id AS integer),
            CAST(:actor_client_id AS integer)
        FROM placed ORDER BY item, rank, id COLLATE "C"
        RETURNING sequence_id, aggregate_type, aggregate_id, changes
    )
    INSERT INTO audit_event_subjects (audit_event_id, object_id)
    SELECT sequence_id, aggregate_id FROM inserted WHERE aggregate_type = 'object'
    UNION ALL
    SELECT sequence_id, changes ->> 'fromObjectId' FROM inserted WHERE aggregate_type = 'relation'
    UNION ALL
    SELECT sequence_id, changes ->> 'toObjectId' FROM inserted
    WHERE aggregate_type = 'relation' AND changes ->> 'toObjectId' <> changes ->> 'fromObjectId'
    """
)

# A change set's deletions are audited per record, as its creates and updates are; they belong to
# the workspace but change no live data, so they take no feed position (0.12 Z6, D341).
_CHANGE_SET_AUDIT = text(
    """
    WITH inserted AS (
        INSERT INTO audit_events (event_id, aggregate_type, aggregate_id, action, version,
            changes, occurred_at, cause_kind, cause_id, workspace_key, subject, actor_kind,
            actor_user_id, actor_client_id)
        SELECT gen_random_uuid()::text, 'change-set-object', o.object_id, 'deleted',
            o.version + 1,
            json_build_object('changeSetId', CAST(:change_set AS varchar),
                'objectTypeKey', o.object_type_key, 'cascadeRootObjectId', root.object_id),
            CAST(:now AS timestamptz), CAST(:cause_kind AS varchar), CAST(:cause_id AS varchar),
            CAST(:workspace AS varchar),
            json_build_object('objectTypeKey', o.object_type_key,
                'applicationKey', o.application_key, 'parentObjectId', o.parent_object_id),
            CAST(:actor_kind AS varchar), CAST(:actor_user_id AS integer),
            CAST(:actor_client_id AS integer)
        FROM deletion_objects o JOIN deletion_roots root ON root.item = o.item
        ORDER BY o.item, o.object_id COLLATE "C"
        RETURNING sequence_id, aggregate_id
    )
    INSERT INTO audit_event_subjects (audit_event_id, object_id)
    SELECT sequence_id, aggregate_id FROM inserted
    """
)

_SETS = """
    INSERT INTO relation_set_versions (workspace_key, change_set_id, relation_type_key,
        from_object_type_key, to_object_type_key, anchor_object_id, direction, version,
        created_at, updated_at)
    SELECT CAST(:workspace AS varchar), CAST(:change_set AS varchar), relation_type_key,
        from_type, to_type, anchor, direction, count(*), CAST(:now AS timestamptz),
        CAST(:now AS timestamptz)
    FROM (
        SELECT relation_type_key, from_type, to_type, from_object_id AS anchor,
            'outgoing' AS direction FROM deletion_relations
        UNION ALL
        SELECT relation_type_key, from_type, to_type, to_object_id, 'incoming'
        FROM deletion_relations
    ) ends
    GROUP BY relation_type_key, from_type, to_type, anchor, direction
    ORDER BY relation_type_key, from_type, to_type, anchor, direction
    {conflict} DO UPDATE SET version = relation_set_versions.version + EXCLUDED.version,
        updated_at = EXCLUDED.updated_at
"""
_LIVE_SETS = text(
    _SETS.format(
        conflict="ON CONFLICT (workspace_key, relation_type_key, from_object_type_key, "
        "to_object_type_key, anchor_object_id, direction) WHERE change_set_id IS NULL"
    )
)
_CHANGE_SET_SETS = text(_SETS.format(conflict="ON CONFLICT ON CONSTRAINT uq_relation_set_version"))

_LIVE_REMOVAL = (
    text("DELETE FROM object_relations WHERE id IN (SELECT relation_id FROM deletion_relations)"),
    text(
        "DELETE FROM attribute_values WHERE object_id IN (SELECT object_id FROM deletion_objects)"
    ),
    # The parent key is RESTRICT: the closure's records are detached from each other first.
    text(
        "UPDATE objects SET parent_object_id = NULL WHERE parent_object_id IS NOT NULL"
        " AND id IN (SELECT object_id FROM deletion_objects)"
    ),
    text("DELETE FROM objects WHERE id IN (SELECT object_id FROM deletion_objects)"),
)

_CHANGE_SET_TOMBSTONES = (
    text(
        """
        INSERT INTO change_set_objects (change_set_id, object_id, application_key,
            object_type_key, name, parent_object_id, attributes, version, is_deleted)
        SELECT CAST(:change_set AS varchar), object_id, application_key, object_type_key, name,
            parent_object_id, coalesce(attributes, '{}'::json), version + 1, true
        FROM deletion_objects
        ON CONFLICT ON CONSTRAINT uq_change_set_object
        DO UPDATE SET version = EXCLUDED.version, is_deleted = true
        """
    ),
    text(
        """
        INSERT INTO change_set_relations (change_set_id, relation_id, relation_type_key,
            from_object_id, to_object_id, attributes, version, is_deleted)
        SELECT CAST(:change_set AS varchar), relation_id, relation_type_key, from_object_id,
            to_object_id, coalesce(attributes, '{}'::json), version + 1, true
        FROM deletion_relations
        ON CONFLICT ON CONSTRAINT uq_change_set_relation
        DO UPDATE SET version = EXCLUDED.version, is_deleted = true
        """
    ),
    # The typed value index holds no row of a tombstone (``snapshot_values``).
    text(
        "DELETE FROM snapshot_attribute_values WHERE owner_kind = 'change_set'"
        " AND owner_id = :change_set"
        " AND object_id IN (SELECT object_id FROM deletion_objects)"
    ),
)


@dataclass(frozen=True)
class Deletion:
    """One record to delete: the item it stands for (its index in a job; 0 for a single delete),
    whether it cascades, and the token confirming the impact it was shown. In a preview a cascade
    needs no token: the preview gives it.

    ``own_links``: a record a load deletes because its file no longer names it (0.10 A5c, D104),
    deleted with its own relationships and no token, since they cannot outlive it; a record others
    depend on (a child, a record it owns) is refused with its impact, never deleted with it."""

    item: int
    object_id: str
    object_type_key: str
    cascade: bool
    token: str | None = None
    own_links: bool = False


@dataclass
class Deleted:
    """What became of one deletion: ``error`` when refused; otherwise its ``impact``, or
    ``deleted_with`` when an earlier item's impact holds its record (D122)."""

    item: int
    error: ApiError | None = None
    impact: dict[str, Any] | None = None
    deleted_with: int | None = None


@dataclass
class _Row:
    """One item's summary: the item that owns its record (itself, or an earlier one reaching it),
    its records (by type) and relationships, those reaching records that stay, those not
    containment edges, whether it crosses into another workspace, and its impact's digest."""

    deletion: Deletion
    item: int
    owner: int | None
    objects: int | None
    by_type: dict[str, int]
    relationships: int
    retained: int
    linked: int
    contained: int
    offside: bool
    digest: str | None


class DeletionScope:
    """Where a run deletes: live data of a workspace, or one change set."""

    session: Session
    model: EngineModel
    workspace_key: str
    token_scope: str

    def objects(self) -> Any:
        """The context's records: ``object_id``, ``application_key``, ``object_type_key``,
        ``name``, ``parent_object_id``, ``attributes``, ``version`` and ``workspace_key``."""
        raise NotImplementedError

    def relations(self) -> Any:
        """The context's relationships: ``relation_id``, ``relation_type_key``,
        ``from_object_id``, ``to_object_id``, ``attributes`` and ``version``."""
        raise NotImplementedError

    def object_type_of(self, object_id: Any) -> Any:
        """The type of the context's record ``object_id`` (an expression), as a keyed lookup;
        null when the context does not hold it."""
        raise NotImplementedError

    def token_context(self, deletion: Deletion) -> dict[str, object]:
        raise NotImplementedError

    def write(self, rows: list[_Row]) -> None:
        raise NotImplementedError


class LiveScope(DeletionScope):
    """Live data of a workspace, under its write lock (``LiveWrites``)."""

    token_scope = "live-deletion"

    def __init__(
        self, session: Session, model: EngineModel, workspace_key: str, model_identity: str
    ) -> None:
        self.session = session
        self.model = model
        self.workspace_key = workspace_key
        self.model_identity = model_identity

    def objects(self) -> Any:
        # Every workspace's records: an edge into another workspace is found and refused.
        return select(
            RdmObject.id.label("object_id"),
            RdmObject.application_key,
            RdmObject.object_type_key,
            RdmObject.name,
            RdmObject.parent_object_id,
            null().cast(JSON).label("attributes"),
            RdmObject.version,
            RdmObject.workspace_key,
        ).subquery()

    def object_type_of(self, object_id: Any) -> Any:
        return (
            select(RdmObject.object_type_key)
            .where(RdmObject.id == object_id)
            .correlate_except(RdmObject)
            .scalar_subquery()
        )

    def relations(self) -> Any:
        return select(
            ObjectRelation.id.label("relation_id"),
            ObjectRelation.relation_type_key,
            ObjectRelation.from_object_id,
            ObjectRelation.to_object_id,
            null().cast(JSON).label("attributes"),
            ObjectRelation.version,
        ).subquery()

    def token_context(self, deletion: Deletion) -> dict[str, object]:
        return {
            "workspaceKey": self.workspace_key,
            "objectTypeKey": deletion.object_type_key,
            "objectId": deletion.object_id,
            "model": self.model_identity,
        }

    def write(self, rows: list[_Row]) -> None:
        session = self.session
        now = datetime.now(UTC)
        cause_kind, cause_id = audit_cause_of(session)
        feed = sum((row.objects or 0) + row.linked for row in rows if row.owner == row.item)
        first, release_id = take_positions(session, self.workspace_key, feed) if feed else (1, None)
        session.execute(
            _LIVE_AUDIT,
            {
                "first": first,
                "now": now,
                "cause_kind": cause_kind,
                "cause_id": cause_id,
                "workspace": self.workspace_key,
                "release": release_id,
                **audit_actor_of(session),
            },
        )
        session.execute(
            _LIVE_SETS, {"workspace": self.workspace_key, "change_set": None, "now": now}
        )
        if matrix_states.has_built(session, "live", self.workspace_key):
            _note_matrix(session, None)
        for statement in _LIVE_REMOVAL:
            session.execute(statement)


class ChangeSetScope(DeletionScope):
    """One change set: its records as it holds them over its base."""

    token_scope = "change-set-deletion"

    def __init__(self, session: Session, model: EngineModel, change_set: ChangeSet) -> None:
        self.session = session
        self.model = model
        self.change_set = change_set
        self.change_set_id = change_set.id
        self.workspace_key = change_set.workspace_key
        self.model_release_id = change_set.model_release_id
        self.context = change_set_context(session, change_set.id)

    def objects(self) -> Any:
        projection = object_projection(self.context)
        return select(
            projection.c.object_id,
            projection.c.application_key,
            projection.c.object_type_key,
            projection.c.name,
            projection.c.parent_object_id,
            projection.c.attributes,
            projection.c.version,
            literal(self.workspace_key, String).label("workspace_key"),
        ).subquery()

    def object_type_of(self, object_id: Any) -> Any:
        return effective_object_value(self.context, object_id, "object_type_key")[0]

    def relations(self) -> Any:
        projection = relation_projection(self.context)
        return select(
            projection.c.relation_id,
            projection.c.relation_type_key,
            projection.c.from_object_id,
            projection.c.to_object_id,
            projection.c.attributes,
            projection.c.version,
        ).subquery()

    def token_context(self, deletion: Deletion) -> dict[str, object]:
        return {
            "changeSetId": self.change_set_id,
            "objectTypeKey": deletion.object_type_key,
            "objectId": deletion.object_id,
            "modelReleaseId": self.model_release_id,
        }

    def write(self, rows: list[_Row]) -> None:
        session = self.session
        now = datetime.now(UTC)
        cause_kind, cause_id = audit_cause_of(session)
        session.execute(
            _CHANGE_SET_AUDIT,
            {
                "change_set": self.change_set_id,
                "workspace": self.workspace_key,
                "now": now,
                "cause_kind": cause_kind,
                "cause_id": cause_id,
                **audit_actor_of(session),
            },
        )
        session.execute(
            _CHANGE_SET_SETS,
            {"workspace": self.workspace_key, "change_set": self.change_set_id, "now": now},
        )
        if matrix_states.has_built(session, "change_set", self.change_set_id):
            _note_matrix(session, self.change_set_id)
        for statement in _CHANGE_SET_TOMBSTONES:
            session.execute(statement, {"change_set": self.change_set_id})


def delete_records(
    scope: DeletionScope,
    deletions: list[Deletion],
    *,
    previewing: bool = False,
    atomic: bool = False,
    single: bool = False,
) -> list[Deleted]:
    """Decide ``deletions`` together, in item order, and delete the accepted ones.

    ``previewing``: a cascade needs no token (a batch preview gives it). ``atomic``: the results
    end at the first refusal and nothing is written, since the caller rolls everything back.
    ``single``: a dependants refusal carries the single ``DELETE``'s lists (API.md).
    """
    if not deletions:
        return []
    session = scope.session
    session.flush()
    session.connection().exec_driver_sql(_TABLES)
    refused: dict[int, Deleted] = {}
    live = list(deletions)
    rows: list[_Row] = []
    results: dict[int, Deleted] = {}
    while live:
        rows = _decide(scope, live)
        results = {row.item: _verdict(scope, row, previewing) for row in rows}
        _refuse_unpermitted(scope, rows, results)
        failing = sorted(item for item, result in results.items() if result.error is not None)
        if not failing:
            break
        if atomic:
            return [results[item] for item in sorted(results) if item <= failing[0]]
        # A refused item's records stay, so a later item it touches is decided again without it;
        # a refused item no earlier refused one touches is refused for good.
        touched = _touched(session, failing)
        for item in failing:
            if item not in touched:
                refused[item] = results[item]
        live = [deletion for deletion in live if deletion.item not in refused]
    else:
        rows = []
    if rows:
        scope.write(rows)
        session.expire_all()
    outcomes = {**{row.item: results[row.item] for row in rows}, **refused}
    if single:
        # A run of one that is refused ends the loop with nothing left to decide again, so the
        # tables still hold its impact.
        for outcome in outcomes.values():
            if outcome.error is not None and outcome.error.code == "OBJECT_HAS_DEPENDANTS":
                outcome.error = _dependants_with_lists(scope, outcome)
    return [outcomes[deletion.item] for deletion in deletions]


def _decide(scope: DeletionScope, deletions: list[Deletion]) -> list[_Row]:
    """Fill the run's tables for ``deletions`` and read each item's summary."""
    session = scope.session
    session.execute(
        text("TRUNCATE deletion_roots, deletion_reach, deletion_objects, deletion_relations")
    )
    session.execute(
        insert(_ROOTS),
        [
            {
                "item": item.item,
                "object_id": item.object_id,
                "object_type_key": item.object_type_key,
            }
            for item in deletions
        ],
    )
    session.execute(_reach(scope))
    session.execute(_attributed(scope))
    session.execute(_incident(scope))
    by_item = {deletion.item: deletion for deletion in deletions}
    rows = []
    for found in session.execute(_SUMMARY, {"workspace": scope.workspace_key}):
        row = _Row(by_item[found[0]], *found)
        row.by_type = dict(row.by_type or {})
        rows.append(row)
    return rows


def _refuse_unpermitted(
    scope: DeletionScope, rows: list[_Row], results: dict[int, Deleted]
) -> None:
    """The write unit's narrowing check (D291) over each item's records and relationships: a
    writer whose grants do not name a deleted record's type, or either end of a deleted
    relationship, is refused ``403 FORBIDDEN`` before anything is written, ahead of the other
    verdicts so that a refusal reveals no impact. A record another item deletes is that item's."""
    session = scope.session
    mine = [row.item for row in rows if row.owner == row.item and not row.offside]
    if not mine:
        return
    try:
        if allowance(session, scope.workspace_key).everything:
            return
    except ApiError as error:
        results.update({item: Deleted(item, error=error) for item in mine})
        return
    records: dict[int, set[tuple[str, str]]] = {item: set() for item in mine}
    relations: dict[int, set[tuple[tuple[str, str], tuple[str, str]]]] = {
        item: set() for item in mine
    }
    for item, application, type_key in session.execute(
        select(_OBJECTS.c.item, _OBJECTS.c.application_key, _OBJECTS.c.object_type_key)
        .where(_OBJECTS.c.item.in_(mine))
        .distinct()
    ):
        records[item].add((application, type_key))
    for item, from_app, from_type, to_app, to_type in session.execute(
        select(
            _RELATIONS.c.item,
            _RELATIONS.c.from_application,
            _RELATIONS.c.from_type,
            _RELATIONS.c.to_application,
            _RELATIONS.c.to_type,
        )
        .where(_RELATIONS.c.item.in_(mine))
        .distinct()
    ):
        relations[item].add(((from_app, from_type), (to_app, to_type)))
    for item in mine:
        try:
            refuse_types(session, scope.workspace_key, records[item], relations[item])
        except ApiError as error:
            results[item] = Deleted(item, error=error)


def _verdict(scope: DeletionScope, row: _Row, previewing: bool) -> Deleted:
    deletion = row.deletion
    if row.owner is not None and row.owner != row.item:
        return Deleted(row.item, deleted_with=row.owner)
    if row.owner is None:
        # The root is not in the context: removed since the caller found it.
        if deletion.cascade:
            return Deleted(row.item, error=deletion_preview_changed())
        return Deleted(row.item, error=_not_found(deletion))
    if row.offside:
        return Deleted(row.item, error=_offside(scope, row))
    token = deletion_preview_token(
        scope=scope.token_scope, context=scope.token_context(deletion), digest=row.digest or ""
    )
    impact = {
        "objectCount": row.objects or 0,
        "objectsByType": row.by_type,
        "relationshipCount": row.relationships,
        "retainedAssociationCount": row.retained,
        "deletionPreviewToken": token,
    }
    if deletion.own_links and (row.objects or 0) <= 1:
        return Deleted(row.item, impact=impact)
    if not deletion.cascade:
        if (row.objects or 0) > 1 or row.linked:
            return Deleted(
                row.item,
                error=api_error(
                    409,
                    "OBJECT_HAS_DEPENDANTS",
                    "Object has dependant records or relationships; repeat with cascade=true",
                    {"impact": impact},
                ),
                impact=impact,
            )
        return Deleted(row.item, impact=impact)
    if deletion.token is None:
        if previewing:
            return Deleted(row.item, impact=impact)
        return Deleted(row.item, error=deletion_preview_required())
    if not _same_impact(scope, deletion, row.digest or ""):
        return Deleted(row.item, error=deletion_preview_changed())
    return Deleted(row.item, impact=impact)


def _touched(session: Session, refused: list[int]) -> set[int]:
    return {item for (item,) in session.execute(_OVERLAPS, {"refused": refused})}


def _reach(scope: DeletionScope) -> Any:
    """Every record each root reaches, with how: the root, a child, or a required owned record."""
    model = scope.model
    owning = [
        (binding.relationTypeKey, binding.fromObjectTypeKey, binding.toObjectTypeKey)
        for binding in model.objectTypeRelations
        if binding.required
        and binding.cardinality in {"one-to-one", "one-to-many"}
        and (relation_type := model.relation_type(binding.relationTypeKey)) is not None
        and relation_type.isOriented
    ]
    reach = select(
        _ROOTS.c.item,
        _ROOTS.c.object_id,
        _ROOTS.c.object_type_key,
        literal("root", String).label("reason"),
    ).cte("reach", recursive=True)
    child = scope.objects()
    arms = [
        select(
            child.c.object_id,
            child.c.object_type_key,
            literal("child", String).label("reason"),
        ).where(child.c.parent_object_id == reach.c.object_id)
    ]
    if owning:
        relation = scope.relations()
        # The owned record's type by its key, per relationship: joining the context's records
        # instead read every record of the owned type for each record reached, which a change set's
        # projection could not narrow (0.9 R, R-F26).
        target_type = scope.object_type_of(relation.c.to_object_id)
        owned = values(
            column("relation_type_key", String),
            column("from_type", String),
            column("to_type", String),
            name="owning",
        ).data(owning)
        arms.append(
            select(
                relation.c.to_object_id.label("object_id"),
                target_type.label("object_type_key"),
                literal("required-ownership", String).label("reason"),
            )
            .select_from(
                relation.join(
                    owned,
                    and_(
                        owned.c.relation_type_key == relation.c.relation_type_key,
                        owned.c.from_type == reach.c.object_type_key,
                    ),
                )
            )
            .where(relation.c.from_object_id == reach.c.object_id, owned.c.to_type == target_type)
        )
    step = (union_all(*arms) if len(arms) > 1 else arms[0]).lateral("step")
    reach = reach.union(
        select(reach.c.item, step.c.object_id, step.c.object_type_key, step.c.reason).select_from(
            reach.join(step, true())
        )
    )
    return insert(_REACH).from_select(
        ["item", "object_id", "object_type_key", "reason"],
        select(reach.c.item, reach.c.object_id, reach.c.object_type_key, reach.c.reason),
    )


def _attributed(scope: DeletionScope) -> Any:
    """Each reached record once, with the earliest item reaching it (its root first)."""
    source = scope.objects()
    ranked = (
        select(
            _REACH.c.object_id,
            _REACH.c.item,
            _REACH.c.reason,
            source.c.application_key,
            source.c.object_type_key,
            source.c.name,
            source.c.parent_object_id,
            source.c.attributes,
            source.c.version,
            source.c.workspace_key,
        )
        .join(source, source.c.object_id == _REACH.c.object_id)
        .distinct(_REACH.c.object_id)
        .order_by(_REACH.c.object_id, _REACH.c.item, _REACH.c.reason != "root")
    )
    return insert(_OBJECTS).from_select(
        [
            "object_id",
            "item",
            "reason",
            "application_key",
            "object_type_key",
            "name",
            "parent_object_id",
            "attributes",
            "version",
            "workspace_key",
        ],
        ranked,
    )


def _incident(scope: DeletionScope) -> Any:
    """Every relationship touching a record of the run, with the earliest item holding an end, its
    ends' types and workspaces, and whether it is a containment edge."""
    relation = scope.relations()
    near_from = _OBJECTS.alias("near_from")
    near_to = _OBJECTS.alias("near_to")
    source = scope.objects()
    target = scope.objects()
    pairs = [
        (relation_type_key, object_type.key)
        for object_type in scope.model.objectTypes
        for relation_type_key in scope.model.containment_relation_keys(object_type.key)
    ]
    containment = values(
        column("relation_type_key", String), column("object_type_key", String), name="contained"
    ).data(pairs or [("", "")])
    statement = (
        select(
            relation.c.relation_id,
            func.least(near_from.c.item, near_to.c.item),
            relation.c.relation_type_key,
            relation.c.from_object_id,
            relation.c.to_object_id,
            relation.c.attributes,
            relation.c.version,
            source.c.object_type_key,
            target.c.object_type_key,
            source.c.application_key,
            target.c.application_key,
            near_from.c.item,
            near_to.c.item,
            source.c.workspace_key,
            target.c.workspace_key,
            containment.c.relation_type_key.is_not(None),
        )
        .select_from(
            relation.join(source, source.c.object_id == relation.c.from_object_id)
            .join(target, target.c.object_id == relation.c.to_object_id)
            .outerjoin(near_from, near_from.c.object_id == relation.c.from_object_id)
            .outerjoin(near_to, near_to.c.object_id == relation.c.to_object_id)
            .outerjoin(
                containment,
                and_(
                    containment.c.relation_type_key == relation.c.relation_type_key,
                    containment.c.object_type_key == target.c.object_type_key,
                ),
            )
        )
        # An end of the run is one its join to the run's records found. Not `IN (run) OR IN (run)`:
        # PostgreSQL hashes such a subplan only while the run's IDs fit in `work_mem`; past that it
        # scans them for every relationship (0.9 R, R-F23).
        .where(or_(near_from.c.object_id.is_not(None), near_to.c.object_id.is_not(None)))
    )
    return insert(_RELATIONS).from_select(
        [
            "relation_id",
            "item",
            "relation_type_key",
            "from_object_id",
            "to_object_id",
            "attributes",
            "version",
            "from_type",
            "to_type",
            "from_application",
            "to_application",
            "from_item",
            "to_item",
            "from_workspace",
            "to_workspace",
            "containment",
        ],
        statement,
    )


def _note_matrix(session: Session, change_set_id: str | None) -> None:
    """The stored matrix states follow the records and relationships removed (ADR-033)."""
    removed = [row for (row,) in session.execute(select(_OBJECTS.c.object_id))]
    relations = session.execute(
        select(
            _RELATIONS.c.relation_type_key, _RELATIONS.c.from_object_id, _RELATIONS.c.to_object_id
        )
    ).all()
    matrix_states.note_removed(session, removed, relations, change_set_id)


def _dependants_with_lists(scope: DeletionScope, outcome: Deleted) -> ApiError:
    """The single ``DELETE``'s refusal: the impact's records and relationships listed (API.md)."""
    session = scope.session
    impact = dict(outcome.impact or {})
    root = session.scalar(select(_ROOTS.c.object_id).where(_ROOTS.c.item == outcome.item))
    dependants = [
        {
            "id": row.object_id,
            "name": row.name,
            "objectTypeKey": row.object_type_key,
            "applicationKey": row.application_key,
            "parentObjectId": row.parent_object_id,
            "reason": row.reason,
        }
        for row in session.execute(
            select(_OBJECTS)
            .where(_OBJECTS.c.item == outcome.item, _OBJECTS.c.object_id != root)
            .order_by(_OBJECTS.c.object_id)
        )
    ]
    relationships = [
        {"id": row.relation_id, "relationTypeKey": row.relation_type_key}
        for row in session.execute(
            select(_RELATIONS.c.relation_id, _RELATIONS.c.relation_type_key)
            .where(_RELATIONS.c.item == outcome.item)
            .order_by(_RELATIONS.c.relation_id)
        )
    ]
    return api_error(
        409,
        "OBJECT_HAS_DEPENDANTS",
        "Object has dependant records or relationships; repeat with cascade=true",
        {
            "objectsToDelete": dependants,
            "objectsToRetire": dependants,
            "relationshipsToRemove": relationships,
            "objectCount": impact["objectCount"],
            "relationshipCount": impact["relationshipCount"],
            "retainedAssociationCount": impact["retainedAssociationCount"],
            "deletionPreviewToken": impact["deletionPreviewToken"],
        },
    )


def _offside(scope: DeletionScope, row: _Row) -> ApiError:
    """An impact crossing into another workspace: stored data to repair, never deleted around."""
    session = scope.session
    found = session.execute(
        select(_OBJECTS.c.object_id, _OBJECTS.c.workspace_key, literal("parent"))
        .where(_OBJECTS.c.item == row.item, _OBJECTS.c.workspace_key != scope.workspace_key)
        .union_all(
            select(
                _RELATIONS.c.from_object_id, _RELATIONS.c.from_workspace, _RELATIONS.c.relation_id
            ).where(
                _RELATIONS.c.item == row.item, _RELATIONS.c.from_workspace != scope.workspace_key
            ),
            select(
                _RELATIONS.c.to_object_id, _RELATIONS.c.to_workspace, _RELATIONS.c.relation_id
            ).where(
                _RELATIONS.c.item == row.item, _RELATIONS.c.to_workspace != scope.workspace_key
            ),
        )
        .limit(1)
    ).first()
    object_id, other, edge = found if found is not None else (row.deletion.object_id, None, "")
    return api_error(
        409,
        "WORKSPACE_GRAPH_INVALID",
        "Object hierarchy crosses workspace boundaries; deletion was refused",
        {
            "workspaceKey": scope.workspace_key,
            "otherWorkspaceKey": other,
            "objectId": object_id,
            "edge": edge,
        },
    )


def _not_found(deletion: Deletion) -> ApiError:
    return api_error(404, "OBJECT_NOT_FOUND", f"Object '{deletion.object_id}' not found")


def deleted_by_job(session: Session, job_id: str, object_ids: list[str]) -> dict[str, str]:
    """Which of ``object_ids`` this job deleted, each with the record whose deletion took it (its
    audit entry's ``cascadeRootObjectId``): one statement (D122)."""
    if not object_ids:
        return {}
    rows = session.execute(
        select(AuditEvent.aggregate_id, AuditEvent.changes).where(
            AuditEvent.cause_kind == "job",
            AuditEvent.cause_id == job_id,
            AuditEvent.action == "deleted",
            AuditEvent.aggregate_type.in_(("object", "change-set-object")),
            AuditEvent.aggregate_id.in_(object_ids),
        )
    )
    return {
        object_id: str((changes or {}).get("cascadeRootObjectId") or object_id)
        for object_id, changes in rows
    }


# --- the confirmation token -------------------------------------------------------------------


def deletion_preview_token(*, scope: str, context: dict[str, object], digest: str) -> str:
    """Sign the digest of the impact a preview showed, bound to its context."""
    return encode_cursor((digest,), scope=scope, sort=("deletion-impact",), filters=context)


def _same_impact(scope: DeletionScope, deletion: Deletion, digest: str) -> bool:
    try:
        supplied = decode_cursor(
            deletion.token or "",
            scope=scope.token_scope,
            sort=("deletion-impact",),
            filters=scope.token_context(deletion),
            position_size=1,
            message="Deletion preview is invalid",
        )[0]
    except ApiError as exc:
        if exc.code != "INVALID_CURSOR":
            raise
        return False
    return hmac.compare_digest(supplied, digest)


def require_deletion_preview(token: str | None) -> None:
    """Require preview confirmation before looking up or claiming mutable graph state."""
    if token is None:
        raise deletion_preview_required()


def deletion_preview_required() -> ApiError:
    return api_error(
        409,
        "DELETION_PREVIEW_REQUIRED",
        "Deletion must be previewed before cascade confirmation",
    )


def deletion_preview_changed() -> ApiError:
    """Return the stable conflict shown when a confirmed deletion preview is stale."""
    return api_error(
        409,
        "DELETION_PREVIEW_CHANGED",
        "The object was modified by another session. Please retry.",
    )


# --- the single DELETE ------------------------------------------------------------------------


def delete_object_record(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    expected_version: int,
    *,
    cascade: bool = False,
    deletion_preview: str | None = None,
    model_identity: str,
) -> None:
    """Delete a live object and, with ``cascade``, its dependant closure, and commit."""
    apply_object_delete(
        session,
        model,
        object_type_key,
        object_id,
        expected_version,
        cascade=cascade,
        deletion_preview=deletion_preview,
        model_identity=model_identity,
    )
    session.commit()


def apply_object_delete(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    expected_version: int,
    *,
    cascade: bool = False,
    deletion_preview: str | None = None,
    model_identity: str,
) -> None:
    """Delete a live object as a run of one (D123); the caller commits.

    ``expected_version`` is checked under the workspace lock before the impact is read; a stale
    claim, or a delete without ``cascade`` of a record with dependants, raises with nothing written.
    """
    if cascade:
        require_deletion_preview(deletion_preview)
    try:
        root = load_object(session, object_id, object_type_key)
    except ApiError as exc:
        if cascade and exc.code == "OBJECT_NOT_FOUND":
            raise deletion_preview_changed() from None
        raise
    workspace_key = root.workspace_key
    resolve_workspace(session, workspace_key, require_active=True)
    # The workspace lock (PG-D5) holds every other live write of the workspace until this deletion
    # commits, so the confirmed impact cannot change while it is read, compared and deleted.
    LiveWrites(session, workspace_key)
    current = session.scalar(select(RdmObject.version).where(RdmObject.id == object_id))
    if current is None:
        if cascade:
            raise deletion_preview_changed()
        raise _not_found(Deletion(0, object_id, object_type_key, cascade))
    if current != expected_version:
        if cascade:
            raise deletion_preview_changed()
        raise api_error(
            409, "VERSION_CONFLICT", "Object version has changed", {"currentVersion": current}
        )
    (result,) = delete_records(
        LiveScope(session, model, workspace_key, model_identity),
        [Deletion(0, object_id, object_type_key, cascade, deletion_preview)],
        single=True,
    )
    if result.error is not None:
        raise result.error
