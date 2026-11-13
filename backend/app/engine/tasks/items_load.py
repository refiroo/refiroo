"""Accepting a task whose proposal holds a dry run of items (Product 0.13 AB, AB-D2, AB-D4).

The assistant's session sent its items to the draft's dry run (``sources/items_summary.py``) and the
person read what they do. Accepting runs exactly those items, with no assistant turn: the draft is
installed as one release (what ``POST /model-drafts/{id}/installation`` does), a change set is made
on it over the workspace's live data (on the workspace's current release when the model does not
change), and the kept items run into it as one atomic batch, the batch executor the worker uses.
The task ends ``loaded`` with the change set and its counts, or ``failed`` with the refused items
named, the change set discarded (an atomic batch wrote nothing), and the words box offered. Nothing
is activated or published.

A draft the person changed after the check is checked again first, every item, and a refusal then
fails the task before anything is installed.
"""

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...errors import ApiError
from ...models.database import ChangeSet, Job, ModelDraft, ModelRelease
from ..change_sets.lifecycle import create_change_set, discard_change_set
from ..change_sets.pinning import selected_change_set_release
from ..jobs.background import open_job_context
from ..jobs.batches import JobCancelled, run_items
from ..jobs.store import ItemOutcome, complete_job, record_outcomes, start_job, stop_job
from ..model.compiler import compile_model
from ..model.release_lifecycle import delete_release
from ..model.releases import ReleaseIdentityConflict
from ..model.workspace_models import load_assignment
from ..sources import draft_profile
from ..sources.dry_run import inputs_of, is_items_run, preview_again, superseded
from . import agent, design_job, draft_plan
from .store import finish, load_task, note

SHOWN_REFUSALS = 5

_REFUSED = """
SELECT o.ref, o.outcome -> 'error' ->> 'message' AS message,
    i.item ->> 'name' AS name, i.item ->> 'objectTypeKey' AS type_key
FROM job_items o
LEFT JOIN job_inputs i ON i.job_id = :previewed AND i.item_index = o.item_index
WHERE o.job_id = :job AND o.status = 'rejected' ORDER BY o.item_index LIMIT :limit
"""


def _show(session: Session, task_id: str, now: str, *, installed: bool, loading: bool) -> None:
    """What the task page shows while the engine works (the milestones of a session's load)."""
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    design["progress"] = {
        "now": now,
        "seconds": 0,
        "refused": None,
        "milestones": [
            {
                "key": "install",
                "label": "Release installed" if installed else "Installing the release",
                "done": installed,
                "running": not installed,
            },
            {
                "key": "load",
                "label": "Loading into the change set" if loading else "Load not started",
                "done": False,
                "running": loading,
            },
        ],
    }
    task.design = design
    session.commit()


def _fail(session: Session, task_id: str, words: str) -> None:
    """The task ends ``failed`` with the reason; it is offered the words box (``queue_retry``)."""
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    design.pop("progress", None)
    task.design = design
    task.result = None
    note(task, "warning", words)
    finish(task, "failed", agent.retention(None))
    session.commit()


def _refusal_words(session: Session, job: Job, previewed: Job, total: int) -> str:
    """The refused items of the load in a person's terms: where they came from and why. (The load's
    inputs are gone with it; the kept items of the check give the names.)"""
    shown = session.execute(
        text(_REFUSED),
        {"job": job.sequence_id, "previewed": previewed.sequence_id, "limit": SHOWN_REFUSALS},
    ).all()
    lines = [
        f"{(row.name or row.type_key or 'An item')}"
        f"{' (' + row.ref + ')' if row.ref else ''}: {row.message or 'refused'}"
        for row in shown
    ]
    more = total - len(shown)
    return (
        f"The engine refused {agent.plural(total, 'record')} of the load; the data may have "
        "changed since the check, so nothing was loaded. "
        + "; ".join(lines)
        + (f"; and {more:,} more" if more > 0 else "")
        + ". Give the assistant other words to go on."
    )


def _stopped(ctx: Any) -> bool:
    try:
        ctx.check()
    except JobCancelled:
        return True
    return False


def _discard(session: Session, change_set_id: str) -> None:
    """The change set goes, claimed at the version the database holds (a batch rolled back leaves the
    session's copy ahead of it)."""
    found = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if found is not None:
        session.refresh(found)
        discard_change_set(session, found.id, found.version)


def _discard_earlier(session: Session, task_id: str) -> None:
    """A change set an earlier run of this load made and did not finish (its worker stopped) goes."""
    task = load_task(session, task_id)
    earlier = (task.result or {}).get("changeSetId")
    if earlier:
        _discard(session, earlier)


def _install(session: Session, task_id: str, ctx: Any) -> Any | None:
    """The draft as one release: the release this task installed for this draft, or a new one (a
    version the draft names that is taken by another model is the next version)."""
    task = load_task(session, task_id)
    draft = session.get(ModelDraft, task.draft_id)
    assert draft is not None
    design = task.design or {}
    earlier = design.get("installed") or {}
    if earlier.get("draftVersion") == draft.version:
        found = session.scalar(
            select(ModelRelease).where(ModelRelease.public_id == earlier["releaseId"])
        )
        if found is not None:
            return found
    earlier_base = draft.base_model_release_id
    compiled = compile_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        raise ApiError(
            422, "INVALID_MODEL", "The assistant's model draft is invalid and cannot be installed"
        )
    try:
        release, created, _saved = draft_profile.install_draft(session, draft, compiled.model)
    except ReleaseIdentityConflict:
        session.rollback()
        draft = session.get(ModelDraft, task.draft_id)
        assert draft is not None
        named = draft.model_json.get("release") or {}
        applied = draft_plan.apply(
            session,
            draft,
            [
                {
                    "kind": "setRelease",
                    "version": design_job._next_version(
                        session, named.get("key", ""), str(named.get("version", "0.0.0"))
                    ),
                }
            ],
            ctx.max_operations,
        )
        if "refused" in applied:
            raise ApiError(409, "AI_TASK_STATE", "The draft's release could not be named") from None
        draft = session.get(ModelDraft, task.draft_id)
        assert draft is not None
        compiled = compile_model(draft.model_json)
        if not compiled.valid or compiled.model is None:
            raise ApiError(
                422,
                "INVALID_MODEL",
                "The assistant's model draft is invalid and cannot be installed",
            ) from None
        release, created, _saved = draft_profile.install_draft(session, draft, compiled.model)
    session.commit()
    task = load_task(session, task_id, for_update=True)
    draft = session.get(ModelDraft, task.draft_id)
    task.design = {
        **(task.design or {}),
        "modelBaseReleaseId": (task.design or {}).get("modelBaseReleaseId")
        or (draft.base_model_release_id if draft is not None else None),
        "installed": {
            "releaseId": release.public_id,
            "draftVersion": draft.version if draft else None,
            # Only a release this accept made is withdrawn when the load is refused, and the draft
            # goes back to the release it was based on.
            "created": created,
            "previousBase": earlier_base,
        },
    }
    session.commit()
    return release


def _withdraw(session: Session, task_id: str) -> str:
    """The release this accept installed goes with the refused load, when nothing refers to it
    (the engine's own delete, which refuses a release in use). The words to add to the task's note
    when it stays; empty otherwise. A retry for the same draft version installs it again."""
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    installed = design.pop("installed", None)
    task.design = design
    session.commit()
    if not installed or not installed.get("created"):
        return ""
    found = session.scalar(
        select(ModelRelease).where(ModelRelease.public_id == installed["releaseId"])
    )
    if found is None:
        return ""
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id is not None else None
    if draft is not None and draft.base_model_release_id == found.id:
        draft.base_model_release_id = installed.get("previousBase")
    # The refused load's batch job wrote nothing and refers to the release; it goes with it.
    session.execute(
        text(
            "DELETE FROM jobs WHERE kind = 'batch' AND model_release_id = :release"
            " AND parameters ->> 'taskId' = :task"
        ),
        {"release": found.id, "task": task_id},
    )
    try:
        delete_release(session, found.public_id, found.status_version)
        session.commit()
    except ApiError as refused:
        session.rollback()
        return f" The model release it installed stays ({refused.message})."
    return ""


def accepts(task: Any) -> bool:
    """Whether the accepted task's proposal holds a dry run of items, which the engine loads itself:
    not one that moves whole types (a migration the person confirms), not a session to start."""
    design = task.design or {}
    return bool(
        design.get("itemsLoad")
        and design.get("stage") == "load"
        and design.get("agentSession")
        and not design.get("startSession")
        and not design.get("moves")
    )


def run(session: Session, job: Job, ctx: Any, task_id: str) -> None:
    """Accept the task: see the module docstring."""
    task = load_task(session, task_id)
    check = task.check or {}
    previewed = session.scalar(select(Job).where(Job.id == check.get("dryRunJobId")))
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id is not None else None
    items = inputs_of(session, previewed) if previewed is not None else []
    if (
        draft is None
        or previewed is None
        or not is_items_run(previewed.parameters)
        or previewed.state != "completed"
        or not items
    ):
        _fail(
            session,
            task_id,
            "The check of the records is no longer kept, so nothing was loaded. Give the assistant "
            "other words to check again.",
        )
        return
    if previewed.workspace_key != task.workspace_key:
        # An items dry run can be made against any workspace; this load goes into the task's (R13-F6).
        _fail(
            session,
            task_id,
            "The check was made against another workspace than this task's, so nothing was loaded. "
            "Give the assistant other words to check again.",
        )
        return
    _discard_earlier(session, task_id)
    if superseded(session, previewed.parameters):
        # The draft changed after the check: every item is checked against it again first.
        _show(session, task_id, "Checking the records again", installed=False, loading=False)
        outcomes = preview_again(session, previewed, draft)
        refused = [o for o in outcomes if o.status == "rejected"]
        if refused:
            _fail(session, task_id, _again_words(refused))
            return
    _show(session, task_id, "Installing the release", installed=False, loading=False)
    try:
        task = load_task(session, task_id)
        draft = session.get(ModelDraft, task.draft_id)
        current = load_assignment(session, task.workspace_key)[1]
        if draft.base_model_release_id is None or design_job.changes_model(session, draft):
            release = _install(session, task_id, ctx)
        elif draft.base_model_release_id != current.id:
            # An earlier accept installed the draft's release and rebased the draft on it while the
            # workspace stays on its own: the items were checked against the draft's release, so the
            # change set is made on that one, not on the workspace's (R13-F7).
            release = session.get(ModelRelease, draft.base_model_release_id)
        else:
            release = None
        selected = (
            selected_change_set_release(session, release.public_id, kept=(current.id,))
            if release is not None
            else None
        )
        change_set = create_change_set(
            session,
            task.workspace_key,
            selected.id if selected is not None else current.id,
            name=_name(session, task),
            source="currentLive",
            expected_model_runtime_release_id=current.id,
            validate_selected_model=selected is not None,
        )
    except ApiError as refused:
        session.rollback()
        _fail(
            session, task_id, f"{refused.message}. Nothing was loaded.{_withdraw(session, task_id)}"
        )
        return
    task = load_task(session, task_id, for_update=True)
    task.state = "loading"
    task.result = {"changeSetId": change_set.id, "changeSetName": change_set.name}
    session.commit()
    _show(session, task_id, "Loading the records into the change set", installed=True, loading=True)
    try:
        batch = _batch(session, ctx, task_id, previewed, change_set)
        failure = _run_batch(session, ctx, batch, previewed, items)
    except JobCancelled:
        # The person's Stop: the change set and the release this accept installed go, as with a
        # refused load, before the stop is carried on (R13-F8).
        _discard(session, change_set.id)
        _withdraw(session, task_id)
        raise
    except ApiError as gone:
        session.rollback()
        _discard(session, change_set.id)
        _fail(session, task_id, f"{gone.message}. Nothing was loaded.{_withdraw(session, task_id)}")
        return
    if failure is not None:
        # An atomic batch that refused anything wrote nothing: the change set goes.
        _discard(session, change_set.id)
        _fail(session, task_id, failure + _withdraw(session, task_id))
        return
    counts = agent.counts_of(session, change_set.id)
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    design.pop("progress", None)
    task.design = design
    # A file whose content is all stored already is a normal outcome (0.13 AB): the task ends
    # ``loaded`` with zero counts, the records it matched counted as unchanged. The change set stays
    # (empty): the loaded page says nothing changed and offers to discard it.
    counts["unchanged"] = int(
        (session.get(Job, batch.sequence_id).counts or {}).get("unchanged", 0)
    )
    task.result = {
        "changeSetId": change_set.id,
        "changeSetName": change_set.name,
        "importJobId": batch.id,
        "counts": counts,
        **({"releaseId": release.public_id} if release is not None else {}),
    }
    finish(task, "loaded", agent.retention(ctx))
    session.commit()


def _name(session: Session, task: Any) -> str:
    workbook = design_job.workbook_of(session, task)
    return f"Load of {workbook.name}" if workbook is not None else "Assistant's changes"


def _again_words(refused: list[ItemOutcome]) -> str:
    shown = refused[:SHOWN_REFUSALS]
    lines = [
        f"{(o.ref + ': ') if o.ref else ''}{((o.fields.get('error') or {}).get('message')) or 'refused'}"
        for o in shown
    ]
    more = len(refused) - len(shown)
    return (
        f"After the draft changed, the engine refused {agent.plural(len(refused), 'record')} of the "
        "load when it checked them again, so nothing was installed or loaded. "
        + "; ".join(lines)
        + (f"; and {more:,} more" if more > 0 else "")
        + ". Give the assistant other words to go on."
    )


def _batch(session: Session, ctx: Any, task_id: str, previewed: Job, change_set: ChangeSet) -> Job:
    """The load as a job of the engine: the kept items copied (in the database) as its inputs."""
    batch = start_job(
        session,
        kind="batch",
        workspace_key=change_set.workspace_key,
        change_set_id=change_set.id,
        model_release_id=change_set.model_release_id,
        parameters={
            "policy": "atomic",
            "run": "background",
            "stage": "execute",
            "onExisting": previewed.parameters.get("onExisting", "reject"),
            "otherWorkspaceIds": "refuse",
            "taskId": task_id,
        },
        total=previewed.total,
        retention_days=ctx.retention_days,
        change_set_version=change_set.version,
    )
    copied = session.execute(
        text(
            "INSERT INTO job_inputs (job_id, item_index, ref, item)"
            " SELECT :new, item_index, ref, item FROM job_inputs WHERE job_id = :old"
            " ORDER BY item_index"
        ),
        {"new": batch.sequence_id, "old": previewed.sequence_id},
    ).rowcount
    if copied != previewed.total:
        # A newer check of the draft took the checked items away while this accept ran (R13-F11).
        session.rollback()
        session.execute(
            text("DELETE FROM jobs WHERE sequence_id = :job"), {"job": batch.sequence_id}
        )
        session.commit()
        raise ApiError(
            409,
            "AI_TASK_STATE",
            "The checked records are gone: another check of the draft replaced them",
        )
    session.commit()
    return session.get(Job, batch.sequence_id)


def _run_batch(
    session: Session, ctx: Any, batch: Job, previewed: Job, items: list[tuple[int, Any]]
) -> str | None:
    """Run the items as one atomic batch in the change set; ``None`` when every item applied,
    otherwise the words for the person (the batch wrote nothing). A stop by the person ends the job
    cancelled and is raised on."""
    sequence_id = batch.sequence_id
    try:
        context = open_job_context(session, batch)
        outcomes = run_items(
            session,
            context,
            items,
            policy="atomic",
            on_existing=batch.parameters.get("onExisting", "reject"),
            other_workspace_ids="refuse",
            expected_change_set_version=batch.change_set_version,
            job_id=batch.id,
            should_stop=lambda: _stopped(ctx),
        )
        record_outcomes(session, batch, outcomes)
        batch.change_set_version = session.scalar(
            select(ChangeSet.version).where(ChangeSet.id == context.change_set.id)
        )
        complete_job(session, batch, retention_days=ctx.retention_days)
        session.commit()
    except BaseException as error:
        session.rollback()
        ended = session.get(Job, sequence_id)
        cancelled = isinstance(error, JobCancelled)
        if ended is not None and ended.state == "running":
            stop_job(
                session,
                ended,
                state="cancelled" if cancelled else "failed",
                reason="JOB_CANCELLED" if cancelled else "JOB_FAILED",
                error=None
                if cancelled
                else {"code": getattr(error, "code", "JOB_FAILED"), "message": str(error)},
                retention_days=ctx.retention_days,
            )
            session.commit()
        if isinstance(error, ApiError):
            return f"{error.message}. Nothing was loaded."
        raise
    rejected = [o for o in outcomes if o.status == "rejected"]
    if not rejected:
        return None
    return _refusal_words(session, session.get(Job, sequence_id), previewed, len(rejected))
