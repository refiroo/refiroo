"""Exports (Base 0.9 J1, INTEGRATION_API §J4, D49–D56).

``POST /exports`` checks the request against the model and queues a job of kind ``export``; the
export worker (``worker.py``, a worker of its own, D53) runs it in one step:

1. **One snapshot.** A ``REPEATABLE READ`` transaction, rolled back at the end, reads everything the file holds,
   so a live export is a baseline: it records the workspace's feed head, which commits with its
   entries under the workspace lock, and a reader follows the feed from there (F5, D41).
2. **Set work in PostgreSQL.** The scope's records go into a temporary table in one statement,
   selected per type through the model query's own builders (``plan_model_query``), so a criterion,
   ``ancestor:``, a ``related`` hop and ``asOf`` select here what they select in
   ``POST …/queries/objects``, in every context. Depth, paths, relationships and the required
   relationships each record carries are set statements over it. JSON Lines and CSV rows are built
   by PostgreSQL; Python writes them to the file and never holds the set.
3. **The file.** Written as ``{jobId}.partial`` and renamed by the worker once the job completes,
   with the manifest (D52) stored on the job in that commit.

The snapshot cannot see a cancel request committed after it began, so cancel requests, the lease
and progress go through the worker's own short session (:class:`ExportControl`), consulted through
:func:`should_stop` once the snapshot is held, then every :data:`CHECK_ROWS` rows and between the
parts of the file. A crashed export restarts from the beginning when its lease expires (D53).

**Formats** (D49, D51). JSON Lines: one batch item per line, ``upsert`` items keyed by ID with the
record's version as ``expectedVersion``, then ``ensureRelation`` items, so the file sent back as a
batch changes nothing. CSV and XLSX share one table layout: records and relationships, columns named
by keys, attribute columns ``#{attributeTypeKey}`` (attribute types are global, so a column means one
thing in every row) and orientation columns ``~…`` that an import ignores.
"""

import csv
import hashlib
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from psycopg import sql
from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    String,
    Text,
    cast,
    exists,
    func,
    insert,
    literal,
    or_,
    select,
    text,
    tuple_,
    union_all,
    update,
)
from sqlalchemy import Table as CoreTable
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session, aliased

from ...errors import ApiError, api_error
from ...models.database import (
    AttributeValue,
    Job,
    ObjectRelation,
    Publication,
    RdmObject,
    Workspace,
)
from ...models.exports import ExportRequest
from ...models.queries import ModelQuery, QueryContext
from ...models.schema import EngineModel
from ..model.registry import resolve_request_model
from ..reads.model_query import plan_model_query
from ..reads.snapshot_reads import (
    SnapshotContext,
    change_set_context,
    find_object,
    object_projection,
    publication_context,
    relation_projection,
)
from ..workspaces.catalogue import resolve_workspace
from . import xlsx
from .store import start_job

CHECK_ROWS = 10_000
FETCH_ROWS = 2_000
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FORMATS = {
    "jsonl": ("application/x-ndjson", "jsonl"),
    "csv": ("text/csv; charset=utf-8", "csv"),
    "xlsx": (XLSX_TYPE, "xlsx"),
}
RECORD_COLUMNS = ("objectTypeKey", "id", "version", "name", "parentObjectId")
RELATION_COLUMNS = ("relationTypeKey", "id", "version", "fromId", "toId")
CSV_COLUMNS = (
    "objectTypeKey",
    "relationTypeKey",
    "id",
    "version",
    "name",
    "parentObjectId",
    "fromId",
    "toId",
)
RECORD_ORIENTATION = ("~parentPath",)
RELATION_ORIENTATION = ("~fromName", "~fromObjectTypeKey", "~toName", "~toObjectTypeKey")
LABELS = {
    "objectTypeKey": "Object type",
    "relationTypeKey": "Relationship type",
    "id": "ID",
    "version": "Version",
    "name": "Name",
    "parentObjectId": "Parent ID",
    "fromId": "From ID",
    "toId": "To ID",
    "~parentPath": "Parent path (not imported)",
    "~fromName": "From name (not imported)",
    "~fromObjectTypeKey": "From type (not imported)",
    "~toName": "To name (not imported)",
    "~toObjectTypeKey": "To type (not imported)",
}


class ExportCancelled(Exception):
    """A cancel request, or a lease lost, reached the export: it stops and leaves no file."""


@dataclass
class ExportControl:
    """The worker's side of a running export, through a short session of its own (see the module
    docstring). ``check(total, processed)`` records progress, renews the lease and answers whether
    to stop."""

    check: Callable[[int | None, int], bool]
    total: int | None = None
    processed: int = 0


def should_stop(control: ExportControl) -> bool:
    """Whether the export stops here: a cancel request, or the lease lost to another worker."""
    return control.check(control.total, control.processed)


def _checkpoint(control: ExportControl) -> None:
    if should_stop(control):
        raise ExportCancelled


# --- the request ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportPlan:
    """The request checked against the model: what the worker runs."""

    request: ExportRequest
    workspace_key: str
    change_set_id: str | None
    publication_id: str | None
    types: tuple[str, ...]
    dated: tuple[str, ...]


def submit_export(session: Session, request: ExportRequest, *, retention_days: int) -> Job:
    """Check the request and queue its job; a refused request stores nothing."""
    workspace = resolve_workspace(session, request.workspaceKey)
    plan = _plan_context(request, workspace.key)
    snapshot = resolve_request_model(
        session, workspace.key, plan.change_set_id, plan.publication_id
    )
    plan = _plan(snapshot.model, request, workspace.key)
    context = _context(session, plan)
    _scope_ids(snapshot.model, plan, context)
    if request.scope.parentObjectId is not None:
        _require_parent(session, plan, context)
    job = start_job(
        session,
        kind="export",
        workspace_key=workspace.key,
        change_set_id=plan.change_set_id,
        model_release_id=snapshot.release_db_id,
        parameters=request.model_dump(mode="json", exclude={"workspaceKey"}),
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    session.commit()
    return job


def _plan_context(request: ExportRequest, workspace_key: str) -> ExportPlan:
    return ExportPlan(
        request=request,
        workspace_key=workspace_key,
        change_set_id=_text(request.context.changeSetId),
        publication_id=_text(request.context.publicationId),
        types=(),
        dated=(),
    )


def _plan(model: EngineModel, request: ExportRequest, workspace_key: str) -> ExportPlan:
    keys = []
    for index, item in enumerate(request.scope.types):
        if model.object_type(item.objectTypeKey) is None:
            _invalid(
                f"Unknown object type '{item.objectTypeKey}'", f"/scope/types/{index}/objectTypeKey"
            )
        keys.append(item.objectTypeKey)
    as_of = request.scope.asOf
    dated: tuple[str, ...] = ()
    if as_of is not None:
        try:
            if len(as_of) != 10:
                raise ValueError(as_of)
            date.fromisoformat(as_of)
        except ValueError:
            _invalid("asOf must be a date (YYYY-MM-DD)", "/scope/asOf")
        dated = tuple(key for key in keys if _dated(model, key))
        if not dated:
            raise api_error(
                422,
                "AS_OF_NOT_SUPPORTED",
                "No exported object type declares an effective period, so asOf does not apply",
                {"path": "/scope/asOf", "objectTypeKeys": keys},
            )
    return ExportPlan(
        request=request,
        workspace_key=workspace_key,
        change_set_id=_text(request.context.changeSetId),
        publication_id=_text(request.context.publicationId),
        types=tuple(keys),
        dated=dated,
    )


def _dated(model: EngineModel, key: str) -> bool:
    definition = model.object_type(key)
    return definition is not None and definition.effectivePeriod is not None


def _scope_ids(model: EngineModel, plan: ExportPlan, context: SnapshotContext | None) -> Any:
    """The IDs of the scope's records as one statement: one select per type through the model
    query's builders. A criterion the model cannot answer is refused at its pointer in the body."""
    selects = []
    for index, item in enumerate(plan.request.scope.types):
        query = ModelQuery(
            objectTypeKey=item.objectTypeKey,
            context=QueryContext(changeSetId=plan.change_set_id, publicationId=plan.publication_id),
            asOf=plan.request.scope.asOf if item.objectTypeKey in plan.dated else None,
            where=item.where,
        )
        try:
            planned = plan_model_query(
                model, query, workspace_key=plan.workspace_key, context=context
            )
        except ApiError as error:
            if error.code != "INVALID_QUERY" or not error.details:
                raise
            path = str(error.details.get("path", ""))
            prefix = "/scope" if path == "/asOf" else f"/scope/types/{index}"
            raise api_error(
                422, "INVALID_QUERY", error.message, {**error.details, "path": prefix + path}
            ) from error
        record_id = planned.query.record.id
        selects.append(planned.query.statement.with_only_columns(record_id).order_by(None))
    return union_all(*selects) if len(selects) > 1 else selects[0]


def _context(session: Session, plan: ExportPlan) -> SnapshotContext | None:
    if plan.change_set_id is not None:
        return change_set_context(session, plan.change_set_id)
    if plan.publication_id is not None:
        return publication_context(session, plan.publication_id)
    return None


def _require_parent(session: Session, plan: ExportPlan, context: SnapshotContext | None) -> None:
    parent = str(plan.request.scope.parentObjectId)
    if context is None:
        found = session.scalar(
            select(RdmObject.id).where(
                RdmObject.id == parent, RdmObject.workspace_key == plan.workspace_key
            )
        )
    else:
        found = find_object(session, context, parent)
    if found is None:
        raise api_error(
            404,
            "PARENT_NOT_FOUND",
            f"Record '{parent}' is not in the exported context",
            {"path": "/scope/parentObjectId"},
        )


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _invalid(message: str, pointer: str) -> Any:
    raise api_error(422, "INVALID_QUERY", message, {"path": pointer})


# --- the run -------------------------------------------------------------------------------------


@dataclass
class ExportOutcome:
    """What the worker stores and serves once the file is written."""

    output: dict[str, Any]
    extension: str


@dataclass(frozen=True)
class _Columns:
    """Attribute columns of the tables, in the model's order, with each one's value type."""

    records: tuple[tuple[str, str], ...]
    relations: tuple[tuple[str, str], ...]
    names: dict[str, str] = field(default_factory=dict)

    @property
    def combined(self) -> tuple[tuple[str, str], ...]:
        seen = dict(self.records)
        seen.update(self.relations)
        return tuple((key, value_type) for key, value_type in seen.items())


_META = MetaData()
_RECORDS = CoreTable(
    "export_records",
    _META,
    Column("object_id", String(36), primary_key=True),
    Column("application_key", Text),
    Column("object_type_key", Text),
    Column("name", Text),
    Column("parent_object_id", String(36)),
    Column("attributes", JSON),
    Column("version", Integer),
    Column("depth", Integer),
    Column("path", Text),
)
_RELATIONS = CoreTable(
    "export_relations",
    _META,
    Column("relation_id", String(36), primary_key=True),
    Column("relation_type_key", Text),
    Column("from_id", String(36)),
    Column("to_id", String(36)),
    Column("attributes", JSON),
    Column("version", Integer),
    Column("from_name", Text),
    Column("from_type", Text),
    Column("to_name", Text),
    Column("to_type", Text),
)
_INITIAL = CoreTable(
    "export_initial",
    _META,
    Column("object_id", String(36)),
    Column("relation_type_key", Text),
    Column("from_id", String(36)),
    Column("attributes", JSON),
)
_TEMPORARY_TABLES = (
    (
        "CREATE TEMPORARY TABLE export_records (object_id varchar(36) PRIMARY KEY,"
        " application_key text, object_type_key text, name text, parent_object_id varchar(36),"
        " attributes json, version integer, depth integer NOT NULL DEFAULT 0, path text)"
        " ON COMMIT DROP"
    ),
    "CREATE INDEX ON export_records (parent_object_id)",
    (
        "CREATE TEMPORARY TABLE export_relations (relation_id varchar(36) PRIMARY KEY,"
        " relation_type_key text, from_id varchar(36), to_id varchar(36), attributes json,"
        " version integer, from_name text, from_type text, to_name text, to_type text)"
        " ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE export_initial (object_id varchar(36), relation_type_key text,"
        " from_id varchar(36), attributes json) ON COMMIT DROP"
    ),
    "CREATE INDEX ON export_initial (object_id)",
)


def run_export(session: Session, job: Job, path: Path, control: ExportControl) -> ExportOutcome:
    """Write the job's file to ``path`` from one snapshot, in a fresh ``session`` the caller rolls
    back. ``409 MODEL_RELEASE_CHANGED`` when the context's release is no longer the job's."""
    # Not READ ONLY: PostgreSQL refuses temporary tables there. The transaction writes only its
    # temporary tables, which go with it when the caller rolls it back.
    session.connection().exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    request = ExportRequest.model_validate({"workspaceKey": job.workspace_key, **job.parameters})
    plan = _plan_context(request, job.workspace_key)
    snapshot = resolve_request_model(
        session, job.workspace_key, plan.change_set_id, plan.publication_id
    )
    if snapshot.release_db_id != job.model_release_id:
        raise api_error(
            409,
            "MODEL_RELEASE_CHANGED",
            "The model release this export was requested under is no longer the one its context "
            "uses; request the export again",
        )
    model = snapshot.model
    plan = _plan(model, request, job.workspace_key)
    context = _context(session, plan)
    position = _feed_position(session, plan)
    for statement in _TEMPORARY_TABLES:
        session.execute(text(statement))
    _fill_records(session, model, plan, context)
    tabular = request.format != "jsonl"
    if tabular:
        _fill_paths(session, plan, context)
    if request.include.relations != "none":
        _fill_relations(session, model, plan, context, tabular=tabular)
    _fill_initial(session, model, plan, context)
    session.execute(text("ANALYZE export_records"))
    record_counts = dict(
        session.execute(
            select(_RECORDS.c.object_type_key, func.count()).group_by(_RECORDS.c.object_type_key)
        ).all()
    )
    relation_counts = dict(
        session.execute(
            select(_RELATIONS.c.relation_type_key, func.count())
            .group_by(_RELATIONS.c.relation_type_key)
            .order_by(_RELATIONS.c.relation_type_key)
        ).all()
    )
    control.total = sum(record_counts.values()) + sum(relation_counts.values())
    _checkpoint(control)

    type_order = [item.key for item in model.objectTypes]
    columns = _columns(model, plan, list(relation_counts))
    with path.open("wb") as file:
        if request.format == "jsonl":
            _write_jsonl(session, file, type_order, control)
        elif request.format == "csv":
            _write_csv(session, file, type_order, columns, control)
    if request.format == "xlsx":
        _write_xlsx(session, path, type_order, columns, plan, record_counts, relation_counts, control)

    digest, size = _digest(path)
    content_type, extension = FORMATS[request.format]
    change_set = context.change_set if context is not None else None
    return ExportOutcome(
        output={
            "format": request.format,
            "contentType": content_type,
            "counts": {
                "records": {key: record_counts.get(key, 0) for key in plan.types},
                "relations": relation_counts,
            },
            "context": {
                "workspaceKey": job.workspace_key,
                "changeSetId": plan.change_set_id,
                "changeSetVersion": change_set.version if change_set is not None else None,
                "publicationId": plan.publication_id,
            },
            "feedPosition": position,
            "asOf": request.scope.asOf,
            "asOfApplied": list(plan.dated),
            "modelReleaseId": snapshot.release_id,
            "bytes": size,
            "sha256": digest,
        },
        extension=extension,
    )


def _feed_position(session: Session, plan: ExportPlan) -> int | None:
    """The feed position the snapshot equals: the workspace's head live, the publication's own
    position for a publication (``None`` when it was published before positions existed), none for
    a change set, whose work is not in the feed."""
    if plan.change_set_id is not None:
        return None
    if plan.publication_id is not None:
        return session.scalar(
            select(Publication.feed_position).where(Publication.id == plan.publication_id)
        )
    return session.scalar(
        select(Workspace.feed_position).where(Workspace.key == plan.workspace_key)
    )


# --- set statements --------------------------------------------------------------------------------


def _record_source(plan: ExportPlan, context: SnapshotContext | None, types: Sequence[str] | None) -> Any:
    """The context's records with their values as one JSON object per record (``rdm_value_json``,
    the canonical form a snapshot row holds), narrowed to ``types`` when given."""
    if context is not None:
        projection = object_projection(context, object_type_keys=types)
        return select(
            projection.c.object_id,
            projection.c.application_key,
            projection.c.object_type_key,
            projection.c.name,
            projection.c.parent_object_id,
            projection.c.attributes,
            projection.c.version,
        ).subquery()
    values = AttributeValue
    attributes = (
        select(
            func.json_object_agg(
                values.attribute_type_key,
                func.rdm_value_json(
                    values.value_type,
                    values.text_value,
                    values.integer_value,
                    values.decimal_value,
                    values.boolean_value,
                    values.date_value,
                    values.datetime_value,
                    values.json_value,
                ),
            )
        )
        .where(values.object_id == RdmObject.id)
        .scalar_subquery()
    )
    statement = select(
        RdmObject.id.label("object_id"),
        RdmObject.application_key,
        RdmObject.object_type_key,
        RdmObject.name,
        RdmObject.parent_object_id,
        func.coalesce(attributes, cast(literal("{}"), JSON)).label("attributes"),
        RdmObject.version,
    ).where(RdmObject.workspace_key == plan.workspace_key)
    if types is not None:
        statement = statement.where(RdmObject.object_type_key.in_(types))
    return statement.subquery()


def _tree_source(plan: ExportPlan, context: SnapshotContext | None) -> Any:
    """Every record of the context with its parent and name, for walks up and down the tree."""
    if context is not None:
        projection = object_projection(context)
        return select(
            projection.c.object_id,
            projection.c.parent_object_id,
            projection.c.name,
            projection.c.object_type_key,
        ).subquery()
    record = aliased(RdmObject)
    return select(
        record.id.label("object_id"),
        record.parent_object_id,
        record.name,
        record.object_type_key,
    ).where(record.workspace_key == plan.workspace_key).subquery()


def _fill_records(
    session: Session, model: EngineModel, plan: ExportPlan, context: SnapshotContext | None
) -> None:
    source = _record_source(plan, context, plan.types)
    conditions = [source.c.object_id.in_(_scope_ids(model, plan, context))]
    parent = plan.request.scope.parentObjectId
    if parent is not None:
        down = _tree_source(plan, context)
        subtree = (
            select(down.c.object_id)
            .where(down.c.parent_object_id == str(parent))
            .cte("subtree", recursive=True)
        )
        below = _tree_source(plan, context)
        subtree = subtree.union_all(
            select(below.c.object_id).join(subtree, below.c.parent_object_id == subtree.c.object_id)
        )
        conditions.append(source.c.object_id.in_(select(subtree.c.object_id)))
    names = [
        "object_id",
        "application_key",
        "object_type_key",
        "name",
        "parent_object_id",
        "attributes",
        "version",
    ]
    session.execute(
        insert(_RECORDS).from_select(
            names, select(*(source.c[name] for name in names)).where(*conditions)
        )
    )
    # Depth inside the file: a record whose parent is not exported starts at 0, so every parent
    # in the file comes before its children.
    session.execute(
        text(
            "WITH RECURSIVE levels(object_id, depth) AS ("
            " SELECT r.object_id, 0 FROM export_records r"
            " WHERE r.parent_object_id IS NULL OR NOT EXISTS"
            " (SELECT 1 FROM export_records p WHERE p.object_id = r.parent_object_id)"
            " UNION ALL"
            " SELECT c.object_id, levels.depth + 1 FROM export_records c"
            " JOIN levels ON c.parent_object_id = levels.object_id)"
            " UPDATE export_records r SET depth = levels.depth FROM levels"
            " WHERE r.object_id = levels.object_id AND levels.depth > 0"
        )
    )


def _fill_paths(session: Session, plan: ExportPlan, context: SnapshotContext | None) -> None:
    """Each record's parent path, the names from the top down to its parent (orientation only)."""
    up = _tree_source(plan, context)
    ancestors = (
        select(
            _RECORDS.c.object_id,
            _RECORDS.c.parent_object_id.label("ancestor_id"),
            literal(1).label("level"),
        )
        .where(_RECORDS.c.parent_object_id.is_not(None))
        .cte("ancestors", recursive=True)
    )
    ancestors = ancestors.union_all(
        select(ancestors.c.object_id, up.c.parent_object_id, ancestors.c.level + 1)
        .join(up, up.c.object_id == ancestors.c.ancestor_id)
        .where(up.c.parent_object_id.is_not(None))
    )
    named = _tree_source(plan, context)
    paths = (
        select(
            ancestors.c.object_id,
            func.string_agg(
                named.c.name, aggregate_order_by(literal(" / "), ancestors.c.level.desc())
            ).label("path"),
        )
        .join(named, named.c.object_id == ancestors.c.ancestor_id)
        .group_by(ancestors.c.object_id)
        .subquery()
    )
    session.execute(
        update(_RECORDS)
        .values(path=paths.c.path)
        .where(_RECORDS.c.object_id == paths.c.object_id)
    )


def _relation_source(context: SnapshotContext | None) -> Any:
    if context is not None:
        projection = relation_projection(context)
        return select(
            projection.c.relation_id,
            projection.c.relation_type_key,
            projection.c.from_object_id,
            projection.c.to_object_id,
            projection.c.attributes,
            projection.c.version,
        ).subquery()
    return select(
        ObjectRelation.id.label("relation_id"),
        ObjectRelation.relation_type_key,
        ObjectRelation.from_object_id,
        ObjectRelation.to_object_id,
        ObjectRelation.attributes,
        ObjectRelation.version,
    ).subquery()


def _containment(model: EngineModel) -> set[str]:
    return {key for item in model.objectTypes for key in model.containment_relation_keys(item.key)}


def _fill_relations(
    session: Session,
    model: EngineModel,
    plan: ExportPlan,
    context: SnapshotContext | None,
    *,
    tabular: bool,
) -> None:
    """The exported records' relationships, containment left out (a parent is the record's own
    field): both ends exported (``withinScope``) or either (``all``)."""
    relation = _relation_source(context)
    has_from = exists().where(_RECORDS.c.object_id == relation.c.from_object_id)
    has_to = exists().where(_RECORDS.c.object_id == relation.c.to_object_id)
    ends = has_from & has_to if plan.request.include.relations == "withinScope" else or_(has_from, has_to)
    conditions = [ends]
    containment = _containment(model)
    if containment:
        conditions.append(relation.c.relation_type_key.not_in(sorted(containment)))
    columns = [
        relation.c.relation_id,
        relation.c.relation_type_key,
        relation.c.from_object_id,
        relation.c.to_object_id,
        relation.c.attributes,
        relation.c.version,
    ]
    names = ["relation_id", "relation_type_key", "from_id", "to_id", "attributes", "version"]
    statement = select(*columns).where(*conditions)
    if tabular:
        source, target = _tree_source(plan, context), _tree_source(plan, context)
        statement = (
            select(*columns, source.c.name, source.c.object_type_key, target.c.name, target.c.object_type_key)
            .outerjoin(source, source.c.object_id == relation.c.from_object_id)
            .outerjoin(target, target.c.object_id == relation.c.to_object_id)
            .where(*conditions)
        )
        names += ["from_name", "from_type", "to_name", "to_type"]
    session.execute(insert(_RELATIONS).from_select(names, statement))


def _fill_initial(
    session: Session, model: EngineModel, plan: ExportPlan, context: SnapshotContext | None
) -> None:
    """For each exported record, the relationships its type requires (a required binding into it
    that is not its containment), carried on its upsert so it can be created from the file (D49)."""
    pairs = sorted(
        {
            (binding.relationTypeKey, binding.toObjectTypeKey)
            for binding in model.objectTypeRelations
            if binding.required
            and binding.toObjectTypeKey in plan.types
            and binding.relationTypeKey not in model.containment_relation_keys(binding.toObjectTypeKey)
        }
    )
    if not pairs:
        return
    relation = _relation_source(context)
    statement = (
        select(_RECORDS.c.object_id, relation.c.relation_type_key, relation.c.from_object_id, relation.c.attributes)
        .join(relation, relation.c.to_object_id == _RECORDS.c.object_id)
        .where(tuple_(relation.c.relation_type_key, _RECORDS.c.object_type_key).in_(pairs))
    )
    session.execute(
        insert(_INITIAL).from_select(["object_id", "relation_type_key", "from_id", "attributes"], statement)
    )


# --- JSON Lines ----------------------------------------------------------------------------------

_RECORD_ORDER = (
    "ORDER BY r.depth, array_position(CAST(:types AS text[]), r.object_type_key), r.object_id"
)
def _upsert_line(parent: bool) -> str:
    """A record's upsert item; ``parent`` only for a record that has one, so a top-level record's
    line names none (an absent parent keeps a found record where it is, §B3)."""
    fields = [
        "'op', 'upsert'",
        "'objectTypeKey', r.object_type_key",
        "'applicationKey', r.application_key",
        "'key', json_build_object('id', r.object_id)",
        "'name', r.name",
        *(["'parent', json_build_object('id', r.parent_object_id)"] if parent else []),
        "'expectedVersion', r.version",
        (
            "'attributes', (SELECT coalesce(json_agg(json_build_object("
            "'attributeTypeKey', a.key, 'value', a.value) ORDER BY a.key), '[]'::json)"
            " FROM jsonb_each(r.attributes::jsonb) a WHERE jsonb_typeof(a.value) <> 'null')"
        ),
        (
            "'initialRelations', (SELECT coalesce(json_agg(json_build_object("
            "'relationTypeKey', i.relation_type_key, 'direction', 'incoming',"
            " 'object', json_build_object('id', i.from_id),"
            " 'attributes', coalesce(i.attributes, '{}'::json))"
            " ORDER BY i.relation_type_key, i.from_id), '[]'::json)"
            " FROM export_initial i WHERE i.object_id = r.object_id)"
        ),
    ]
    return f"json_build_object({', '.join(fields)})"


_JSONL_RECORDS = (
    f"SELECT (CASE WHEN r.parent_object_id IS NULL THEN {_upsert_line(False)}"
    f" ELSE {_upsert_line(True)} END)::text FROM export_records r {_RECORD_ORDER}"
)
_JSONL_RELATIONS = (
    "SELECT json_build_object("
    " 'op', 'ensureRelation',"
    " 'relationTypeKey', x.relation_type_key,"
    " 'from', json_build_object('id', x.from_id),"
    " 'to', json_build_object('id', x.to_id),"
    " 'attributes', coalesce(x.attributes, '{}'::json),"
    " 'expectedVersion', x.version"
    ")::text FROM export_relations x ORDER BY x.relation_type_key, x.relation_id"
)


def _write_jsonl(session: Session, file: Any, type_order: list[str], control: ExportControl) -> None:
    for statement in (_JSONL_RECORDS, _JSONL_RELATIONS):
        rows = session.execute(
            text(statement),
            {"types": type_order},
            execution_options={"stream_results": True, "yield_per": FETCH_ROWS},
        )
        for (line,) in rows:
            file.write(line.encode())
            file.write(b"\n")
            _counted(control)
        _checkpoint(control)


def _counted(control: ExportControl, rows: int = 1) -> None:
    before = control.processed
    control.processed += rows
    if control.processed // CHECK_ROWS != before // CHECK_ROWS:
        _checkpoint(control)


# --- CSV -----------------------------------------------------------------------------------------


def _columns(model: EngineModel, plan: ExportPlan, relation_types: Sequence[str]) -> _Columns:
    """The attribute columns: those the exported types bind, then those the exported relationship
    types' bindings carry, each in the model's order of attribute types."""
    bound: set[str] = set()
    for key in plan.types:
        definition = model.object_type(key)
        if definition is not None:
            bound.update(binding.attributeTypeKey for binding in definition.attributes)
    carried = {
        key
        for binding in model.objectTypeRelations
        if binding.relationTypeKey in relation_types
        for key in binding.attributeTypeKeys
    }
    ordered = model.attributeTypes
    return _Columns(
        records=tuple((item.key, item.valueType) for item in ordered if item.key in bound),
        relations=tuple((item.key, item.valueType) for item in ordered if item.key in carried),
        names={item.key: item.name for item in ordered},
    )


def _cell(source: str, key: str, value_type: str) -> sql.Composable:
    """An attribute's value as canonical text: a JSON value as JSON text, every other as the
    text of its JSON value (dates ISO 8601, decimals as the API writes them, true or false)."""
    operator = sql.SQL("->") if value_type == "json" else sql.SQL("->>")
    value = sql.SQL("({}.attributes {} {})").format(sql.Identifier(source), operator, sql.Literal(key))
    return sql.SQL("{}::text").format(value) if value_type == "json" else value


def _write_csv(
    session: Session, file: Any, type_order: list[str], columns: _Columns, control: ExportControl
) -> None:
    attributes = columns.combined
    header = [*CSV_COLUMNS, *(f"#{key}" for key, _ in attributes), *RECORD_ORIENTATION, *RELATION_ORIENTATION]
    text_header = io.StringIO()
    csv.writer(text_header, lineterminator="\n").writerow(header)
    file.write(b"\xef\xbb\xbf")
    file.write(text_header.getvalue().encode())
    null = sql.SQL("NULL")
    record_order = _record_order(type_order)
    record_values = dict(columns.records)
    relation_values = dict(columns.relations)
    record_cells = [
        sql.SQL("r.object_type_key, NULL, r.object_id, r.version, r.name, r.parent_object_id, NULL, NULL"),
        *(_cell("r", key, kind) if key in record_values else null for key, kind in attributes),
        sql.SQL("r.path, NULL, NULL, NULL, NULL"),
    ]
    relation_cells = [
        sql.SQL("NULL, x.relation_type_key, x.relation_id, x.version, NULL, NULL, x.from_id, x.to_id"),
        *(_cell("x", key, kind) if key in relation_values else null for key, kind in attributes),
        sql.SQL("NULL, x.from_name, x.from_type, x.to_name, x.to_type"),
    ]
    records = sql.SQL("COPY (SELECT {} FROM export_records r {}) TO STDOUT (FORMAT csv)").format(
        sql.SQL(", ").join(record_cells), record_order
    )
    relations = sql.SQL(
        "COPY (SELECT {} FROM export_relations x ORDER BY x.relation_type_key, x.relation_id)"
        " TO STDOUT (FORMAT csv)"
    ).format(sql.SQL(", ").join(relation_cells))
    connection = session.connection().connection.driver_connection
    for statement, table in ((records, _RECORDS), (relations, _RELATIONS)):
        rows = session.scalar(select(func.count()).select_from(table)) or 0
        with connection.cursor() as cursor, cursor.copy(statement) as copy:
            for chunk in copy:
                file.write(chunk)
        _counted(control, rows)
        _checkpoint(control)


# --- XLSX ----------------------------------------------------------------------------------------


def _record_order(type_order: Sequence[str]) -> sql.Composable:
    return sql.SQL(
        "ORDER BY r.depth, array_position(ARRAY[{}]::text[], r.object_type_key), r.object_id"
    ).format(sql.SQL(", ").join(sql.Literal(key) for key in type_order))


def _write_xlsx(
    session: Session,
    path: Path,
    type_order: list[str],
    columns: _Columns,
    plan: ExportPlan,
    record_counts: dict[str, int],
    relation_counts: dict[str, int],
    control: ExportControl,
) -> None:
    """A workbook of named tables (``engine/jobs/xlsx.py``): ``Records`` and ``Relationships``, the
    attributes extracted as canonical text by PostgreSQL as for CSV, read through server-side
    cursors and written as typed cells."""
    connection = session.connection().connection.driver_connection
    book = xlsx.Workbook(path, lambda: _counted(control))
    record_keys = [*RECORD_COLUMNS, *(f"#{key}" for key, _ in columns.records), *RECORD_ORIENTATION]
    relation_keys = [
        *RELATION_COLUMNS,
        *(f"#{key}" for key, _ in columns.relations),
        *RELATION_ORIENTATION,
    ]
    relation_types = sorted(relation_counts)
    records = sql.SQL(
        "SELECT r.object_type_key, r.object_id, r.version, r.name, r.parent_object_id{}, r.path"
        " FROM export_records r {}"
    ).format(
        sql.SQL("").join(sql.SQL(", {}").format(_cell("r", key, kind)) for key, kind in columns.records),
        _record_order(type_order),
    )
    relations = sql.SQL(
        "SELECT x.relation_type_key, x.relation_id, x.version, x.from_id, x.to_id{},"
        " x.from_name, x.from_type, x.to_name, x.to_type FROM export_relations x"
        " ORDER BY x.relation_type_key, x.relation_id"
    ).format(
        sql.SQL("").join(sql.SQL(", {}").format(_cell("x", key, kind)) for key, kind in columns.relations)
    )
    tables = (
        ("Records", "records", records, record_keys, columns.records, record_counts, plan.types, "A"),
        (
            "Relationships",
            "relationships",
            relations,
            relation_keys,
            columns.relations,
            relation_counts,
            relation_types,
            "B",
        ),
    )
    for title, table, query, keys, attributes, counts, type_list, list_column in tables:
        letters = [xlsx.column(index) for index in range(1, len(keys) + 1)]
        lists = (
            [(letters[0], f"Lists!${list_column}$1:${list_column}${len(type_list)}")]
            if type_list
            else []
        )
        lists += [
            (letters[len(RECORD_COLUMNS) + index], '"TRUE,FALSE"')
            for index, (_, kind) in enumerate(attributes)
            if kind == "boolean"
        ]
        with connection.cursor(name=f"export_{table}") as cursor:
            cursor.itersize = FETCH_ROWS
            cursor.execute(query)
            book.data(
                xlsx.Sheet(
                    title=title,
                    table=table,
                    keys=keys,
                    labels=[LABELS.get(key) or columns.names.get(key[1:], key) for key in keys],
                    count=sum(counts.values()),
                    rows=cursor,
                    encode=_xlsx_row(letters, [kind for _, kind in attributes]),
                    lists=lists,
                )
            )
        _checkpoint(control)
    book.lists([list(plan.types), relation_types])
    book.close()


def _xlsx_row(letters: Sequence[str], kinds: Sequence[str]) -> Callable[[Sequence[Any], int], str]:
    """How a row of the records or relationships query becomes its cells: five built-in columns
    (the third the version), the attributes by their value types, then the orientation columns."""
    built_in = len(RECORD_COLUMNS)
    attributes = list(enumerate(kinds, built_in))
    orientation = range(built_in + len(kinds), len(letters))

    def encode(row: Sequence[Any], number: int) -> str:
        parts = [
            xlsx.text_cell(f"{letters[0]}{number}", row[0]),
            xlsx.text_cell(f"{letters[1]}{number}", row[1]),
            xlsx.number_cell(f"{letters[2]}{number}", row[2]),
            xlsx.text_cell(f"{letters[3]}{number}", row[3]),
            xlsx.text_cell(f"{letters[4]}{number}", row[4]),
        ]
        parts += [
            xlsx.cell(f"{letters[index]}{number}", row[index], kind) for index, kind in attributes
        ]
        parts += [xlsx.text_cell(f"{letters[index]}{number}", row[index]) for index in orientation]
        return "".join(parts)

    return encode


def _digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as file:
        while chunk := file.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size
