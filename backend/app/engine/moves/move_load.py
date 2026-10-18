"""The move into a reviewed change set (Product 0.11 X3, D128–D137, API.md § Moves).

A move's dry run (``move_job.py``) waits for confirmation with ``stage: preview``; with ``stage:
execute`` it loads at once. Confirming (``confirm_move``) checks again what the dry run relied on
(D131): the mapping at the version it ran with, both workspaces active, the target on the release
the job pinned and a live source on the one it was read under, and something to create or update.
A refusal leaves the job waiting.

The worker then loads **what was previewed** (D129): the stored items, decided again against the
target, in chunks, into a **new change set of the target** opened at the first step (D130), never
live data. Each chunk's created records get their origin in ``record_origins`` in the chunk's
transaction (D132), and its outcomes replace the preview's rows. Once every item has run, the rows
settle as in the dry run, and a ``mode: move`` opens a change set of the source deleting every
selected record that loaded, deepest first and each with its own relationships, unless it changed
since it was read (``SOURCE_CHANGED``) or a record that stays depends on it (D134). That change set
waits for the target's to publish first (D135). Nothing reaches either workspace's feed or consumers
until a change set is published (D20).
"""

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.commands import BatchDeleteItem, RecordReference
from ...models.database import ChangeSet, Job, Workspace, WorkspaceModel
from ..change_sets.access import change_set_model
from ..change_sets.lifecycle import open_job_change_set
from ..jobs.background import open_job_context
from ..jobs.batches import BatchContext, run_items
from ..jobs.store import complete_job, confirm_job, load_job
from ..workspaces.catalogue import resolve_workspace
from . import move_job
from .mappings import Releases, load_mapping


def loading(job: Job) -> bool:
    """Whether the move loads now: confirmed, or sent with ``stage: execute``."""
    return job.confirmed_at is not None or job.parameters.get("stage") == "execute"


def confirm_move(session: Session, job_id: str) -> Job:
    """Confirm a move's dry run and commit: it is queued to load. A move confirmed before answers
    unchanged; a refusal leaves it waiting."""
    job = load_job(session, job_id)

    def check(job: Job) -> None:
        check_current(session, job)
        loadable = session.scalar(
            text(
                "SELECT count(*) FROM job_items WHERE job_id = :job AND status = 'applied'"
                " AND outcome ->> 'outcome' IN ('create', 'update', 'updateOriginal')"
            ),
            {"job": job.sequence_id},
        )
        if not loadable:
            raise api_error(
                422,
                "MOVE_NOTHING_TO_MOVE",
                "Nothing in this move's dry run would be created or updated in the target; "
                "change the mapping or the selection and send the move again",
                {"jobId": job.id},
            )

    if confirm_job(session, job, check, keep_items=True):
        session.commit()
    else:
        session.rollback()
    session.refresh(job)
    return job


def check_current(session: Session, job: Job) -> None:
    """What the dry run relied on is still so (D131, I31, I32): refuses otherwise."""
    parameters = job.parameters
    mapping = load_mapping(session, parameters["mapping"]["key"])
    if mapping.version != parameters["mapping"]["version"]:
        raise api_error(
            409,
            "MOVE_MAPPING_CHANGED",
            f"Model mapping '{mapping.key}' changed since the move's dry run (version "
            f"{parameters['mapping']['version']}, now {mapping.version}); send the move again",
            {
                "currentVersion": mapping.version,
                "expectedVersion": parameters["mapping"]["version"],
            },
        )
    for key in (parameters["sourceWorkspaceKey"], parameters["targetWorkspaceKey"]):
        if resolve_workspace(session, key).status == "retired":
            raise api_error(409, "WORKSPACE_RETIRED", f"Workspace '{key}' is retired")
    target = session.scalar(
        select(WorkspaceModel.model_release_id).where(
            WorkspaceModel.workspace_key == parameters["targetWorkspaceKey"]
        )
    )
    source_moved = parameters["sourceAt"] == "live" and (
        Releases(session).of_workspace(parameters["sourceWorkspaceKey"]).release_id
        != parameters["sourceReleaseId"]
    )
    if target != job.model_release_id or source_moved:
        workspace = parameters["sourceWorkspaceKey" if source_moved else "targetWorkspaceKey"]
        raise api_error(
            409,
            "MODEL_RELEASE_CHANGED",
            f"Workspace '{workspace}' runs another release than at the move's dry run; send the "
            "move again",
            {"workspaceKey": workspace},
        )


# --- the worker's steps ----------------------------------------------------------------------------

_NEXT = text(
    """
    SELECT i.item_index, i.item FROM job_inputs i
    WHERE i.job_id = :job AND (i.item::jsonb) ? 'item'
        AND NOT EXISTS (SELECT 1 FROM job_items x WHERE x.job_id = :job
            AND x.item_index = i.item_index)
    ORDER BY i.item_index LIMIT :count
    """
)
_ORIGINS = text(
    """
    INSERT INTO record_origins (object_id, workspace_key, origin_workspace_key, origin_object_id,
        job_id)
    SELECT i.item::jsonb -> 'item' ->> 'id', :workspace,
        i.item::jsonb -> 'row' -> 'origin' ->> 'workspaceKey',
        i.item::jsonb -> 'row' -> 'origin' ->> 'objectId', :job_id
    FROM job_inputs i
    WHERE i.job_id = :job AND i.item_index = ANY(CAST(:applied AS integer[]))
        AND i.item::jsonb -> 'item' ->> 'op' = 'create' AND (i.item::jsonb -> 'row') ? 'origin'
    ON CONFLICT (object_id) DO NOTHING
    """
)


def load_step(
    session: Session,
    job: Job,
    *,
    chunk_items: int,
    hold: Callable[[], None],
    retention_days: int,
) -> None:
    """One step of the load, committed by the caller: its start (the target's change set opened),
    one chunk of items, or its end (the rows settled, the source's deletion, the summary)."""
    parameters = job.parameters
    report = job.report or {}
    if "sourceFeedPositionAtLoad" not in report:
        _start(session, job)
        return
    if job.change_set_id is not None:
        context = open_job_context(session, job)
        inputs = session.execute(_NEXT, {"job": job.sequence_id, "count": chunk_items}).all()
        if inputs:
            outcomes = run_items(
                session,
                context,
                [(index, move_job.ITEM.validate_python(item["item"])) for index, item in inputs],
                policy="independent",
                on_existing="reject",
                expected_change_set_version=job.change_set_version,
                job_id=job.id,
            )
            hold()
            move_job.insert_outcomes(session, job, outcomes)
            session.execute(
                _ORIGINS,
                {
                    "job": job.sequence_id,
                    "job_id": job.id,
                    "workspace": parameters["targetWorkspaceKey"],
                    "applied": [o.index for o in outcomes if o.status == "applied"],
                },
            )
            job.processed += len(outcomes)
            job.change_set_version = session.scalar(
                select(ChangeSet.version).where(ChangeSet.id == job.change_set_id)
            )
            return
    hold()
    move_job.settle(session, job)
    source = _delete_in_source(session, job) if parameters["mode"] == "move" else None
    complete_job(session, job, retention_days=retention_days)
    job.report = {**(job.report or {}), "sourceChangeSetId": source}
    summary = move_job.summary(session, job)
    if "source" in summary:
        job.counts = {**(job.counts or {}), "deleted": summary["source"]["deleted"]}
    job.report = {**job.report, "move": summary}


def _start(session: Session, job: Job) -> None:
    """The load's first step: checked again (a move sent with ``stage: execute`` was not), the
    preview's rows of the items replaced, and the target's change set opened when anything is to
    load; the source's feed position noted (D129)."""
    check_current(session, job)
    parameters = job.parameters
    session.execute(
        text(
            "DELETE FROM job_items x USING job_inputs i WHERE x.job_id = :job"
            " AND i.job_id = :job AND i.item_index = x.item_index"
        ),
        {"job": job.sequence_id},
    )
    job.processed = session.scalar(
        text("SELECT count(*) FROM job_items WHERE job_id = :job"), {"job": job.sequence_id}
    )
    if session.scalar(
        text("SELECT count(*) FROM job_inputs WHERE job_id = :job AND (item::jsonb) ? 'item'"),
        {"job": job.sequence_id},
    ):
        change_set = open_job_change_set(
            session,
            parameters["targetWorkspaceKey"],
            job.model_release_id,
            name=f"Move from {parameters['sourceWorkspaceKey']} ({job.id})",
        )
        job.change_set_id = change_set.id
        job.change_set_version = change_set.version
    position = session.scalar(
        select(Workspace.feed_position).where(Workspace.key == parameters["sourceWorkspaceKey"])
    )
    job.report = {**(job.report or {}), "sourceFeedPositionAtLoad": position}


# --- the source's deletion (D134) ------------------------------------------------------------------

_LOADED = text(
    """
    SELECT x.item_index, x.outcome ->> 'sourceId', x.outcome ->> 'sourceType',
        (i.item::jsonb ->> 'sourceVersion')::integer
    FROM job_items x JOIN job_inputs i ON i.job_id = x.job_id AND i.item_index = x.item_index
    WHERE x.job_id = :job AND x.status = 'applied' AND x.outcome ->> 'kind' = 'record'
        AND (x.outcome ->> 'selected')::boolean AND x.outcome ->> 'sourceId' IS NOT NULL
    ORDER BY x.item_index DESC
    """
)
_SOURCE = text(
    """
    UPDATE job_items x SET outcome = ((x.outcome::jsonb)
        || jsonb_build_object('source', CAST(s.source AS jsonb)))::json
    FROM unnest(CAST(:indexes AS integer[]), CAST(:sources AS text[])) AS s(idx, source)
    WHERE x.job_id = :job AND x.item_index = s.idx
    """
)
# A refusal meaning the record is no longer the one the move read.
_CHANGED = ("VERSION_CONFLICT", "OBJECT_NOT_FOUND")


def _delete_in_source(session: Session, job: Job) -> str | None:
    """A change set of the source deleting what loaded; its ID, or none when it deletes nothing.
    Each loaded record's row says what became of it in the source."""
    parameters = job.parameters
    loaded = session.execute(_LOADED, {"job": job.sequence_id}).all()
    if not loaded:
        return None
    workspace = parameters["sourceWorkspaceKey"]
    release = session.scalar(
        select(WorkspaceModel.model_release_id).where(WorkspaceModel.workspace_key == workspace)
    )
    savepoint = session.begin_nested()
    change_set = open_job_change_set(
        session,
        workspace,
        release,
        name=f"Move to {parameters['targetWorkspaceKey']} ({job.id})",
        waits_for_change_set_id=job.change_set_id,
    )
    context = BatchContext(
        workspace, change_set, change_set_model(session, change_set), release, None
    )
    outcomes = run_items(
        session,
        context,
        [
            (
                index,
                BatchDeleteItem(
                    op="delete",
                    ref=str(index),
                    target=RecordReference(id=object_id),
                    expectedVersion=version,
                ),
            )
            for index, object_id, _type, version in loaded
        ],
        policy="independent",
        on_existing="reject",
        expected_change_set_version=change_set.version,
        job_id=job.id,
        own_links=True,
    )
    sources = [_source_outcome(outcome.status, outcome.fields) for outcome in outcomes]
    deleted = any(source["outcome"] == "deleted" for source in sources)
    if deleted:
        savepoint.commit()
    else:
        savepoint.rollback()
        sources = [
            {**source, "outcome": "kept"} if source["outcome"] == "deleted" else source
            for source in sources
        ]
    session.execute(
        _SOURCE,
        {
            "job": job.sequence_id,
            "indexes": [outcome.index for outcome in outcomes],
            "sources": [json.dumps(source) for source in sources],
        },
    )
    return change_set.id if deleted else None


def _source_outcome(status: str, fields: dict[str, Any]) -> dict[str, Any]:
    if status == "applied":
        return {"outcome": "deleted", "reasons": []}
    error = fields.get("error") or {}
    if error.get("code") in _CHANGED:
        reason = {
            "code": "SOURCE_CHANGED",
            "message": "It changed in the source since the move read it; it was copied as read "
            "and stays in the source",
            "details": {"refusal": error},
        }
    else:
        reason = {key: error[key] for key in ("code", "message", "details") if key in error}
    return {"outcome": "kept", "reasons": [reason]}
