"""The dry run of a move between workspaces whose models differ (Product 0.11 X2, D114–D123,
API.md § Moves).

``POST /moves`` is checked before a job exists (D121): two workspaces, the target active; the
mapping at the version the client read, of the two workspaces' models and without problems
against the releases they run (or, for a publication, the release it was published under); a
selection the source can answer (D116); a publication of the source (D117). It then queues a job
of kind ``move`` in the target workspace, under the target's release, keeping the selection and
the mapping's definition at its version (D112).

The worker runs it in two steps, as an import's preview: it **binds** the selection through the
mapping (``move_binding.py``) and commits the rows the mapping decides and the inputs of the
others; then it **previews** every input through the batch path against the target's live data
(D115, D67) and rolls everything back. Each input's outcome becomes its row: ``create`` or
``update`` as planned, or ``refused`` with the target's refusal. A relationship riding on its
record's create takes that record's outcome; a record whose parent was refused, and a relationship
whose record was, does not move (``RECORD_NOT_MOVED``). The job then completes with its summary
(D122). Nothing reaches either workspace: no record, feed position, audit entry or change set.
X3 adds the load into a change set.
"""

import json
from collections.abc import Callable
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.commands import BatchItem
from ...models.database import Job, Workspace, WorkspaceModel
from ...models.moves import MoveRequest, MoveSelection
from ..jobs.background import open_job_context
from ..jobs.batches import run_items
from ..jobs.store import ItemOutcome, complete_job, start_job
from ..workspaces.catalogue import resolve_workspace
from .mapping_check import problems
from .mappings import Releases, load_mapping, mismatch
from .move_binding import bind_move, plan_move
from .selection import check_selection, source_context

KIND = "move"
_ITEM = TypeAdapter(BatchItem)


def submit_move(session: Session, request: MoveRequest, *, retention_days: int) -> Job:
    """Check the move and queue its dry run; commits. A refused move creates no job."""
    if request.sourceWorkspaceKey == request.targetWorkspaceKey:
        raise api_error(
            422,
            "MOVE_SAME_WORKSPACE",
            "A move takes records from one workspace into another; name two workspaces",
            {"path": "/targetWorkspaceKey"},
        )
    source_workspace = resolve_workspace(session, request.sourceWorkspaceKey)
    target_workspace = resolve_workspace(session, request.targetWorkspaceKey)
    for workspace in (source_workspace, target_workspace):
        if workspace.status == "retired":
            raise api_error(409, "WORKSPACE_RETIRED", f"Workspace '{workspace.key}' is retired")
    mapping = load_mapping(session, request.mapping.key)
    if mapping.version != request.mapping.expectedVersion:
        raise api_error(
            409,
            "MOVE_MAPPING_CHANGED",
            f"Model mapping '{mapping.key}' is at version {mapping.version}; read it again and "
            "send the move with that version",
            {"currentVersion": mapping.version, "expectedVersion": request.mapping.expectedVersion},
        )
    context, publication = source_context(session, source_workspace.key, request.sourceAt)
    releases = Releases(session)
    source = (
        releases.by_db_id(publication.model_release_id)
        if publication is not None
        else releases.of_workspace(source_workspace.key)
    )
    target = releases.of_workspace(target_workspace.key)
    if (source.model_key, target.model_key) != (mapping.source_model_key, mapping.target_model_key):
        raise mismatch(mapping, source.model_key, target.model_key)
    found = problems(mapping.definition, source, target)
    if found:
        raise api_error(
            422,
            "MOVE_MAPPING_HAS_PROBLEMS",
            f"Model mapping '{mapping.key}' names what the two workspaces' releases lack or do not "
            "allow; correct it, or re-point it, before moving",
            {"problems": found},
        )
    check_selection(session, source.model, request.selection, source_workspace.key, context)
    job = start_job(
        session,
        kind=KIND,
        workspace_key=target_workspace.key,
        change_set_id=None,
        model_release_id=session.scalar(
            select(WorkspaceModel.model_release_id).where(
                WorkspaceModel.workspace_key == target_workspace.key
            )
        ),
        parameters={
            "sourceWorkspaceKey": source_workspace.key,
            "targetWorkspaceKey": target_workspace.key,
            "mapping": {"key": mapping.key, "version": mapping.version},
            "mappingKey": mapping.key,
            "mappingDefinition": mapping.definition,
            "selection": request.selection.model_dump(mode="json", exclude_none=True),
            "sourceAt": request.sourceAt,
            "sourceReleaseId": source.release_id,
            "targetReleaseId": target.release_id,
            "mode": request.mode,
            "stage": request.stage,
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    session.commit()
    return job


# --- the worker's steps ----------------------------------------------------------------------------


def bind(session: Session, job: Job) -> None:
    """The selection through the mapping into the job's rows and inputs; the caller commits. The
    target's release must still be the one the job pinned, and the source's the one it was sent
    under."""
    open_job_context(session, job)
    parameters = job.parameters
    releases = Releases(session)
    context, publication = source_context(
        session, parameters["sourceWorkspaceKey"], parameters["sourceAt"]
    )
    source = releases.side(parameters["sourceReleaseId"])
    target = releases.side(parameters["targetReleaseId"])
    assert source is not None and target is not None
    if publication is None and releases.of_workspace(
        parameters["sourceWorkspaceKey"]
    ).release_id != (source.release_id):
        raise api_error(
            409,
            "MODEL_RELEASE_CHANGED",
            f"Workspace '{parameters['sourceWorkspaceKey']}' runs another release than when the "
            "move was sent; send it again",
        )
    position = None
    if publication is None:
        position = session.scalar(
            select(Workspace.feed_position).where(Workspace.key == parameters["sourceWorkspaceKey"])
        )
    bound = bind_move(
        session,
        job,
        plan_move(parameters["mappingDefinition"], source, target),
        source=source,
        selection=MoveSelection.model_validate(parameters["selection"]),
        source_workspace=parameters["sourceWorkspaceKey"],
        context=context,
    )
    job.total = bound.rows
    job.stage = "previewing"
    job.report = {**(job.report or {}), "sourceFeedPosition": position}


def preview(
    session: Session,
    job: Job,
    *,
    should_stop: Callable[[], bool],
    hold: Callable[[Session], Job],
    retention_days: int,
) -> None:
    """Run every input against the target's live data and roll back (D115); then, after ``hold``
    has taken the job's lease again in the clean session, record each row's outcome, complete the
    job with its summary and leave the commit to the caller."""
    context = open_job_context(session, job)
    inputs = session.execute(
        text(
            "SELECT item_index, item FROM job_inputs WHERE job_id = :job AND"
            " (item::jsonb) ? 'item' ORDER BY item_index"
        ),
        {"job": job.sequence_id},
    ).all()
    outcomes = (
        run_items(
            session,
            context,
            [(index, _ITEM.validate_python(item["item"])) for index, item in inputs],
            policy="independent",
            on_existing="reject",
            expected_change_set_version=None,
            job_id=job.id,
            should_stop=should_stop,
            previewing=True,
        )
        if inputs
        else []
    )
    session.rollback()
    job = hold(session)
    _record(session, job, outcomes)
    complete_job(session, job, retention_days=retention_days)
    job.report = {**(job.report or {}), "move": summary(session, job)}


_OUTCOMES = text(
    """
    INSERT INTO job_items (job_id, item_index, ref, status, outcome)
    SELECT :job, o.idx, i.ref, o.status, ((i.item::jsonb -> 'row') || CASE o.status
        WHEN 'applied' THEN jsonb_build_object('action', o.outcome::jsonb -> 'action')
        ELSE jsonb_build_object('outcome', 'refused',
            'reasons', jsonb_build_array(o.outcome::jsonb -> 'error')) END)::json
    FROM unnest(CAST(:indexes AS integer[]), CAST(:statuses AS text[]),
        CAST(:outcomes AS text[])) AS o(idx, status, outcome)
    JOIN job_inputs i ON i.job_id = :job AND i.item_index = o.idx
    """
)
_NOT_MOVED = (
    "jsonb_build_object('outcome', 'notMoved', 'reasons', jsonb_build_array(jsonb_build_object("
    "'code', 'RECORD_NOT_MOVED', 'message', {message}, 'details', {details})))"
)
_AFTER = (
    # A record refused because its parent was refused, or did not move, does not move either.
    "UPDATE job_items c SET status = 'unprocessed', outcome = ((c.outcome::jsonb) || "
    + _NOT_MOVED.format(
        message="'Its parent does not move'",
        details="jsonb_build_object('parentRow', p.item_index,"
        " 'refusal', c.outcome::jsonb -> 'reasons' -> 0)",
    )
    + ")::json FROM job_items p WHERE c.job_id = :job AND p.job_id = :job"
    " AND c.status = 'rejected' AND c.outcome ->> 'kind' = 'record'"
    " AND p.item_index = (c.outcome ->> 'parentRow')::integer AND p.status <> 'applied'",
    # A relationship riding on its record's create takes that record's outcome.
    "INSERT INTO job_items (job_id, item_index, ref, status, outcome)"
    " SELECT :job, i.item_index, i.ref, CASE WHEN r.status = 'applied' THEN 'applied'"
    "  ELSE 'unprocessed' END,"
    " ((i.item::jsonb -> 'row') || CASE WHEN r.status = 'applied'"
    "  THEN jsonb_build_object('action', 'created') ELSE "
    + _NOT_MOVED.format(
        message="'Its record does not move'", details="jsonb_build_object('row', r.item_index)"
    )
    + " END)::json FROM job_inputs i JOIN job_items r ON r.job_id = :job"
    " AND r.item_index = (i.item::jsonb ->> 'rides')::integer"
    " WHERE i.job_id = :job AND (i.item::jsonb) ? 'rides'",
    # A relationship refused because one of its records does not move does not move either.
    "UPDATE job_items x SET status = 'unprocessed', outcome = ((x.outcome::jsonb) || "
    + _NOT_MOVED.format(
        message="'One of its records does not move'",
        details="jsonb_build_object('refusal', x.outcome::jsonb -> 'reasons' -> 0)",
    )
    + ")::json WHERE x.job_id = :job AND x.status = 'rejected'"
    " AND x.outcome ->> 'kind' = 'relationship' AND EXISTS (SELECT 1 FROM job_items e"
    "  WHERE e.job_id = :job AND e.status <> 'applied' AND e.item_index IN"
    "  (SELECT value::integer FROM jsonb_array_elements_text(x.outcome::jsonb -> 'endRows')))",
)
_COUNTS = text(
    """
    SELECT count(*) FILTER (WHERE status = 'applied'), count(*) FILTER (WHERE status = 'rejected'),
        count(*) FILTER (WHERE status = 'unprocessed'),
        count(*) FILTER (WHERE status = 'applied' AND outcome ->> 'outcome' = 'create'),
        count(*) FILTER (WHERE status = 'applied' AND outcome ->> 'outcome' = 'update')
    FROM job_items WHERE job_id = :job
    """
)


def _record(session: Session, job: Job, outcomes: list[ItemOutcome]) -> None:
    session.execute(
        _OUTCOMES,
        {
            "job": job.sequence_id,
            "indexes": [outcome.index for outcome in outcomes],
            "statuses": [outcome.status for outcome in outcomes],
            "outcomes": [json.dumps(outcome.fields) for outcome in outcomes],
        },
    )
    for statement in _AFTER:
        session.execute(text(statement), {"job": job.sequence_id})
    applied, rejected, unprocessed, created, updated = session.execute(
        _COUNTS, {"job": job.sequence_id}
    ).one()
    job.processed = applied + rejected + unprocessed
    job.counts = {
        "applied": applied,
        "rejected": rejected,
        "unprocessed": unprocessed,
        "created": created,
        "updated": updated,
        "unchanged": 0,
        "deleted": 0,
    }


# --- the summary (D122) ----------------------------------------------------------------------------

_OUTCOME = (
    "CASE status WHEN 'applied' THEN outcome ->> 'outcome' WHEN 'rejected' THEN 'refused'"
    " ELSE 'notMoved' END"
)
_COUNTED = (
    f"jsonb_build_object('create', count(*) FILTER (WHERE {_OUTCOME} = 'create'),"
    f" 'update', count(*) FILTER (WHERE {_OUTCOME} = 'update'),"
    f" 'refused', count(*) FILTER (WHERE {_OUTCOME} = 'refused'),"
    f" 'notMoved', count(*) FILTER (WHERE {_OUTCOME} = 'notMoved'))"
)
_SUMMARY = {
    "counts": f"SELECT {_COUNTED} FROM job_items WHERE job_id = :job",
    "types": "SELECT COALESCE(jsonb_agg(t ORDER BY t ->> 'sourceType'), '[]') FROM ("
    " SELECT jsonb_strip_nulls(jsonb_build_object('sourceType', outcome ->> 'sourceType',"
    f" 'targetType', max(outcome ->> 'targetType'), 'counts', {_COUNTED})) AS t"
    " FROM job_items WHERE job_id = :job AND outcome ->> 'kind' = 'record'"
    " AND outcome ->> 'sourceType' IS NOT NULL GROUP BY outcome ->> 'sourceType') types",
    "relationships": "SELECT COALESCE(jsonb_agg(t ORDER BY t ->> 'relationTypeKey'), '[]') FROM ("
    " SELECT jsonb_strip_nulls(jsonb_build_object('relationTypeKey', outcome ->> 'relationTypeKey',"
    " 'targetRelationTypeKey', max(outcome ->> 'targetRelationTypeKey'),"
    f" 'counts', {_COUNTED})) AS t FROM job_items WHERE job_id = :job"
    " AND outcome ->> 'kind' = 'relationship' GROUP BY outcome ->> 'relationTypeKey') relations",
    "reasons": "SELECT COALESCE(jsonb_agg(jsonb_build_object('code', code, 'count', n)"
    " ORDER BY code), '[]') FROM (SELECT r ->> 'code' AS code, count(*) AS n FROM job_items,"
    " jsonb_array_elements(outcome::jsonb -> 'reasons') r WHERE job_id = :job GROUP BY 1) reasons",
    "attributesNotCarried": "SELECT COALESCE(jsonb_agg(jsonb_build_object('sourceType', st,"
    " 'attributeTypeKey', attr, 'code', code, 'count', n) ORDER BY st, attr, code), '[]') FROM ("
    " SELECT outcome ->> 'sourceType' AS st, l ->> 'attributeTypeKey' AS attr, l ->> 'code' AS code,"
    " count(*) AS n FROM job_items, jsonb_array_elements(outcome::jsonb -> 'leftBehind') l"
    " WHERE job_id = :job AND outcome ->> 'kind' = 'record' GROUP BY 1, 2, 3) attributes",
    "possibleDuplicates": "SELECT count(*) FROM job_items WHERE job_id = :job"
    " AND (outcome::jsonb) ? 'possibleDuplicates'",
}


def summary(session: Session, job: Job) -> dict[str, Any]:
    """What the dry run found, read from its rows: counts overall, by source type and by relation
    type; reasons with their counts; the attributes not carried per type; possible duplicates."""
    parameters = job.parameters
    found = {
        name: session.scalar(text(statement), {"job": job.sequence_id})
        for name, statement in _SUMMARY.items()
    }
    return {
        "coverage": "complete",
        "rows": job.total,
        **found,
        "mapping": parameters["mapping"],
        "sourceWorkspaceKey": parameters["sourceWorkspaceKey"],
        "targetWorkspaceKey": parameters["targetWorkspaceKey"],
        "sourceAt": parameters["sourceAt"],
        "sourceFeedPosition": (job.report or {}).get("sourceFeedPosition"),
        "sourceReleaseId": parameters["sourceReleaseId"],
        "targetReleaseId": parameters["targetReleaseId"],
        "mappingSourceReleaseId": parameters["mappingDefinition"]["sourceReleaseId"],
        "mappingTargetReleaseId": parameters["mappingDefinition"]["targetReleaseId"],
    }
