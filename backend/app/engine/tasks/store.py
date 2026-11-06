"""Assistant tasks: a workbook read against a workspace and planned into a load (Product 0.16
AP6a, AP-D23 to AP-D26).

A task is created with its workbook, which it owns as a source file, and one ``aiTask`` job that
reads it. Every change a person asks for claims the task's ``version``. A task is visible to its
requester and to those who administer its workspace (AP-D23); anyone else reads ``404
AI_TASK_NOT_FOUND``. A task is kept ``AI_TASK_RETENTION_DAYS`` after it finished or was last changed
(AP-D24), then it and its file are deleted by the worker's sweep.

The state follows the job the task waits for (``job_id``): :func:`sync` carries a failed or
cancelled job to the task, and a finished import to ``loaded``, wherever the task is read.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, or_, select, text, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import AiTask, Job, ModelDraft, OAuthClient, SourceFile
from ..authorization.permissions import Permissions, PrincipalKind
from ..authorization.writes import requester_of

KINDS = ("note", "warning", "refused")
# States in which the task waits for a job, and the ones that end it.
WAITING = ("reading", "checking", "loading")
ENDED = ("loaded", "failed", "cancelled", "stopped")


def held_counts(session: Session, workspace: str) -> dict[str, int]:
    return dict(
        session.execute(
            text(
                "SELECT object_type_key, count(*) FROM objects WHERE workspace_key = :w GROUP BY 1"
            ),
            {"w": workspace},
        ).all()
    )


_KEYS = (integer_key("id", AiTask.id, "id", descending=True),)


def create_task(
    session: Session,
    *,
    workspace_key: str,
    words: str | None,
    retention_days: int,
) -> AiTask:
    """The task, flushed, requested by the session's caller; the caller adds its file and job."""
    now = datetime.now(UTC)
    task = AiTask(
        workspace_key=workspace_key,
        words=words,
        state="reading",
        version=1,
        notes=[],
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(days=retention_days),
    )
    requester = requester_of(session)
    if requester is not None:
        if requester[0] == "user":
            task.requested_by_user_id = requester[1]
        else:
            task.requested_by_client_id = requester[1]
    session.add(task)
    session.flush()
    return task


def load_task(session: Session, task_id: str, *, for_update: bool = False) -> AiTask:
    statement = select(AiTask).where(AiTask.public_id == task_id)
    if for_update:
        statement = statement.with_for_update()
    task = session.scalar(statement)
    if task is None:
        raise not_found(task_id)
    return task


def not_found(task_id: str) -> Exception:
    return api_error(404, "AI_TASK_NOT_FOUND", f"AI task '{task_id}' not found")


def requested_by(task: AiTask) -> tuple[str, int] | None:
    if task.requested_by_user_id is not None:
        return "user", task.requested_by_user_id
    if task.requested_by_client_id is not None:
        return "client", task.requested_by_client_id
    return None


def may_see(task: AiTask, permissions: Permissions, kind: PrincipalKind, row_id: int) -> bool:
    """The requester, and whoever administers the task's workspace (AP-D23)."""
    return requested_by(task) == (kind, row_id) or permissions.allows(
        "workspace-admin", task.workspace_key
    )


def visible(permissions: Permissions, kind: PrincipalKind, row_id: int) -> Any:
    """The same rule as a condition over tasks."""
    own = (
        AiTask.requested_by_user_id if kind == "user" else AiTask.requested_by_client_id
    ) == row_id
    keys = permissions.workspaces(frozenset({"workspace-admin"}))
    if keys is None:
        return None
    return or_(own, AiTask.workspace_key.in_(sorted(keys))) if keys else own


def task_page(
    session: Session,
    *,
    visible_to: Any,
    page: PageRequest,
    page_size: int,
) -> Page[AiTask]:
    """Tasks newest first."""
    statement = select(AiTask)
    if visible_to is not None:
        statement = statement.where(visible_to)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="ai-tasks",
        filters={},
        page=page,
        page_size=page_size,
        message="AI task cursor is invalid",
    )


def claim(task: AiTask, expected_version: int) -> None:
    """``409 AI_TASK_VERSION_CONFLICT`` unless the task is at ``expected_version``."""
    if task.version != expected_version:
        raise api_error(
            409,
            "AI_TASK_VERSION_CONFLICT",
            f"AI task '{task.public_id}' is at version {task.version}, not {expected_version}",
            {"currentVersion": task.version},
        )


def require_state(task: AiTask, *allowed: str) -> None:
    if task.state not in allowed:
        raise api_error(
            409,
            "AI_TASK_STATE",
            f"AI task '{task.public_id}' is {task.state}; this is allowed when it is "
            f"{' or '.join(allowed)}",
            {"state": task.state},
        )


def touch(task: AiTask, retention_days: int, *, bump: bool = True) -> None:
    """A change: the task's version moves and its retention starts over (AP-D24)."""
    now = datetime.now(UTC)
    if bump:
        task.version += 1
    task.updated_at = now
    task.expires_at = now + timedelta(days=retention_days)


def finish(task: AiTask, state: str, retention_days: int) -> None:
    task.state = state
    task.finished_at = datetime.now(UTC)
    touch(task, retention_days)


def note(task: AiTask, kind: str, text: str) -> None:
    """Add a note the person reads (a new list: the column is JSON)."""
    if kind not in KINDS:
        raise ValueError(kind)
    at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    task.notes = [*task.notes, {"kind": kind, "text": text, "at": at}]


def has_proposal(task: AiTask) -> bool:
    """Whether a proposal the person can go back to stands: the draft, and what the session or the
    rules said about it."""
    design = task.design or {}
    # A words task whose model does not change has no draft: its proposal is only the design.
    drafted = task.draft_id is not None or bool(design.get("modelUnchanged"))
    return drafted and bool(design.get("origin") or design.get("match"))


def stopped(session: Session, task: AiTask, retention_days: int) -> None:
    """The person stopped the job the task waited for (AP-D55): the turn ends, not the task. The
    task goes back to its last proposal (the accepted one after a load), or, with none yet, is
    ``stopped`` and takes words. The caller has undone what a load wrote."""
    design = dict(task.design or {})
    design.pop("progress", None)
    undone = not design.pop("undoSkipped", False)
    loading = task.state == "loading"
    if loading:
        task.result = None
        task.state = "checked"
        task.finished_at = None
        touch(task, retention_days)
        note(
            task,
            "note",
            "You stopped the load. The change set it wrote was discarded."
            if undone
            else "You stopped the load.",
        )
    elif has_proposal(task):
        was_load = design.get("stage") == "load"
        design["stage"] = "model"
        task.state = "checked"
        task.finished_at = None
        touch(task, retention_days)
        note(
            task,
            "note",
            (
                "You stopped the assistant. What it had loaded was undone, and the proposal is as you accepted it."
                if undone
                else "You stopped the assistant, and the proposal is as you accepted it."
            )
            if was_load
            else "You stopped the assistant. Its last proposal is as it was; what you sent was not made.",
        )
        landed = design.get("turnDraftVersion")
        if landed is not None:
            draft = session.get(ModelDraft, task.draft_id)
            if draft is not None and draft.version != landed:
                note(
                    task,
                    "warning",
                    "The assistant had already changed the draft when you stopped it. Check the draft in "
                    "the model editor before you accept.",
                )
    else:
        design["stage"] = "model"
        finish(task, "stopped", retention_days)
        note(
            task,
            "note",
            "You stopped the assistant before it had a proposal. Tell it how to go on, or discard the task.",
        )
    task.design = design


def sync(session: Session, task: AiTask, retention_days: int) -> None:
    """Carry the state of the job the task waits for to the task: a failed job ends it, a stopped
    one returns it to where the person can go on (:func:`stopped`), and a finished import is
    ``loaded`` (one place, wherever a task is read)."""
    if task.state not in WAITING or task.job_id is None:
        return
    job = session.scalar(select(Job).where(Job.id == task.job_id))
    if job is None:
        return
    if job.state == "cancelled":
        stopped(session, task, retention_days)
    elif job.state in ("failed", "expired"):
        message = (job.error or {}).get("message") or "The job stopped"
        note(task, "warning", f"The task stopped: {message}")
        finish(task, "failed", retention_days)
    elif task.state == "loading" and job.state == "completed":
        if (task.result or {}).get("linksPending"):
            # A design's relationships follow its import; the worker queues them (0.16 AP6).
            return
        result = dict(task.result or {})
        result["counts"] = {
            key: value for key, value in (job.counts or {}).items() if isinstance(value, int)
        }
        task.result = result
        finish(task, "loaded", retention_days)
    session.flush()


def expire(session: Session, now: datetime) -> list[str]:
    """Delete the tasks past ``expires_at`` and, by cascade, their files; a design's model draft
    goes with its task, with its files and history (0.16 AP6; a release it was installed as
    stays), unless it remembers a workspace, whose person's edits it holds (WM1). The public IDs of
    the files, which the caller removes from disk once it committed (AP-D24)."""
    rows = session.execute(select(AiTask.id, AiTask.draft_id).where(AiTask.expires_at <= now)).all()
    if not rows:
        return []
    ids = [row.id for row in rows]
    drafts = list(
        session.scalars(
            select(ModelDraft.id).where(
                ModelDraft.id.in_([row.draft_id for row in rows if row.draft_id is not None]),
                ModelDraft.workspace_key.is_(None),
            )
        )
    )
    files = list(
        session.scalars(
            select(SourceFile.public_id).where(
                or_(SourceFile.task_id.in_(ids), SourceFile.draft_id.in_(drafts))
            )
        )
    )
    session.execute(
        update(OAuthClient)
        .where(OAuthClient.id.in_(select(AiTask.client_id).where(AiTask.id.in_(ids))))
        .values(active=False)
        .execution_options(synchronize_session=False)
    )
    session.execute(delete(AiTask).where(AiTask.id.in_(ids)))
    if drafts:
        session.execute(delete(ModelDraft).where(ModelDraft.id.in_(drafts)))
    return files


def held_by_another(session: Session, draft_id: int, task_id: int) -> bool:
    """Whether a task other than ``task_id`` holds the draft."""
    return (
        session.scalar(
            select(AiTask.id).where(AiTask.draft_id == draft_id, AiTask.id != task_id).limit(1)
        )
        is not None
    )


def refuse_draft_of_another_task(session: Session, draft_public_id: str, client_row: int) -> None:
    """A session writes no draft another task holds (AP-D44): one person may be reviewing it, and
    that task's end deletes it. ``409 AI_TASK_DRAFT_HELD``. Any other client is not asked about."""
    own = session.scalar(
        select(AiTask.id)
        .join(OAuthClient, OAuthClient.id == AiTask.client_id)
        .where(AiTask.client_id == client_row, OAuthClient.kind == "session")
    )
    if own is None:
        return
    draft = session.scalar(select(ModelDraft.id).where(ModelDraft.public_id == draft_public_id))
    if draft is not None and held_by_another(session, draft, own):
        raise api_error(
            409,
            "AI_TASK_DRAFT_HELD",
            "Another assistant task holds this draft: make a new draft, from the same release if "
            "it should start the same",
            {"draftId": draft_public_id},
        )
