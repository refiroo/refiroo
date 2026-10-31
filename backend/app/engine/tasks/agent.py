"""An assistant task run by Claude Code (Product 0.16, the user's decision of 2026-10-31).

The person's words, the workbook, the workspace's model and the API's OpenAPI document go to one
Claude Code session, which works through the API under a client that may read and load in this
workspace and author and install a model, and no more. It is told where to stop, nothing about how
to work. First it builds a model draft and checks every row with the draft's dry
run; the person reads that, edits the draft or says what to change, and the same session goes on.
When the person accepts, it installs one release and loads into a change set. It never activates or
publishes: the person does, from the change set.

The session is a process of the assistant worker in a folder of its own, kept for the task's next turn. Its
stream says what it is doing now; what it has reached is read from what the engine recorded of it.
"""

import json
import os
import re
import shlex
import shutil
import signal
import ssl
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ...config import get_settings
from ...models.commands import ClientCreate, GrantCreate, GrantPrincipal, GrantScope, RoleCreate
from ...models.database import (
    AiTask,
    AuditEvent,
    AuthorizationState,
    ChangeSet,
    Job,
    ModelDraft,
    ModelRelease,
    OAuthClient,
    Role,
)
from ..authorization.administration import create_grant, create_role, delete_grant
from ..authorization.permissions import permissions_of
from ..identity import tokens
from ..identity.clients import create_client
from ..identity.settings import IdentitySettings
from ..model.workspace_models import load_assignment
from .store import finish, load_task, note

TIMEOUT_SECONDS = 1800
LAST_LINE = "CHANGE_SET:"
DEFAULT_WORDS = "Create a model for this or map it to the current model, and import it."
PROPOSAL = "proposal.json"
_CALL = re.compile(r"(?:-X\s*(GET|POST|PUT|PATCH|DELETE)\b[^\n]*?)?/api/v1/([A-Za-z0-9_\-/{}$.]+)")


def enabled() -> bool:
    return bool(os.environ.get("AI_AGENT_COMMAND", "").strip())


def _connection(workspace: str, url: str, *, workbook: bool = True) -> str:
    file = "workbook.xlsx is the file, " if workbook else "There is no file: the words are about the stored records. "
    data = "The data comes from this workbook alone. " if workbook else ""
    return (
        f"{file}model.json the workspace's model, openapi.json the API of the "
        f"engine at {url}, with the header 'Authorization: Bearer $REFIROO_TOKEN' (curl -k --noproxy ''). "
        f"{data}Work only in the workspace {workspace}: no other "
        "workspace is read or changed. Where the data gives one thing two names or values, that "
        "is intended: keep them all as they are, correct nothing and do not keep only the most "
        "common; you may raise it as a question."
    )


def _propose_prompt(words: str | None, workspace: str, url: str, *, workbook: bool = True) -> str:
    check = (
        "Build the model in a model draft and check every row with the draft's dry run"
        if workbook
        else "Put any model change in a model draft, with the workspace's model unchanged if none is "
        "needed, and work out every record the words touch"
    )
    return (
        f"{(words or '').strip() or DEFAULT_WORDS}\n\n"
        f"{_connection(workspace, url, workbook=workbook)} {check}; install, activate, load and "
        f"publish nothing yet: the person reviews first. Then write {PROPOSAL}: "
        '{"draftId": ..., "summary": two sentences a person reads, "questions": [{"text", "options", '
        '"assumed"}] for what only a person can decide}.'
    )


_ACCEPTED = (
    "The person accepted. They may have edited the draft in the model editor: read it again. Install "
    "it as exactly one new release and do not activate it, make the change (a workbook's rows, or "
    "what the words ask of the stored records) in a new change set "
    f"on that release, do not publish it, and end with the line {LAST_LINE} <its id>."
)


def _said_prompt(said: str) -> str:
    return (
        f"The person says:\n{said}\n\nThey may have edited the draft in the model editor: read it "
        f"again. Change the draft as they say, check every row again and write {PROPOSAL} again."
    )


def _identity() -> IdentitySettings:
    settings = get_settings()
    return IdentitySettings(
        encryption_key=settings.secrets_encryption_key,
        issuer=settings.public_url,
        access_token_seconds=settings.access_token_minutes * 60,
        signing_key_days=settings.token_signing_key_days,
        browser_origins=settings.cors_origins,
        session_idle_hours=settings.session_idle_hours,
        session_days=settings.session_days,
        password_reset_hours=settings.password_reset_hours,
        password_min_length=settings.password_min_length,
    )


DATA_ROLE = "AI assistant: data"
MODEL_ROLE = "AI assistant: model"
CLIENT = "AI assistant"
DATA_GROUPS = ["browse", "change-sets", "bulk"]
MODEL_GROUPS = ["model-authoring", "model-install"]


def _role(session: Session, name: str, groups: list[str]) -> str:
    found = session.scalar(select(Role).where(Role.name == name))
    if found is None:
        found = create_role(session, RoleCreate(name=name, actionGroups=groups))
    return found.key


def _access(session: Session, job: Job, workspace: str) -> tuple[str, list[str]]:
    """A token that can only do the session's work: read and load in this workspace, author and
    install a model, and no more of it than who asked may do. Publishing and activating are refused
    by the engine, whatever the session tries. The grants end with the turn."""
    kind, row = (
        ("client", job.requested_by_client_id)
        if job.requested_by_client_id is not None
        else ("user", job.requested_by_user_id)
    )
    if row is None:
        raise ValueError("The task names no one who asked for it")
    generation = session.scalar(select(AuthorizationState.generation)) or 0
    asked = permissions_of(session, kind, row, generation)
    data = _role(session, DATA_ROLE, DATA_GROUPS)
    model = _role(session, MODEL_ROLE, MODEL_GROUPS)
    client = session.scalar(select(OAuthClient).where(OAuthClient.name == CLIENT))
    if client is None:
        client, _ = create_client(session, ClientCreate(name=CLIENT))
    principal = GrantPrincipal(kind="client", id=client.public_id)
    grants = [
        create_grant(
            session,
            GrantCreate(principal=principal, role=data, scope=GrantScope(workspaceKey=workspace)),
        ).grant.public_id
    ]
    if asked.allows("model-authoring", None) and (
        asked.allows("model-release", workspace) or asked.allows("model-install", None)
    ):
        grants.append(
            create_grant(
                session, GrantCreate(principal=principal, role=model, scope=GrantScope(instance=True))
            ).grant.public_id
        )
    token = tokens.issue(
        session, _identity(), subject=client.public_id, kind="client", audience="management"
    )
    return token, grants


TOOLS = "Bash,Read,Write,Edit,Glob,Grep"


def _base_command() -> list[str]:
    """The configured command, without a permission mode: the engine sets that itself."""
    words = shlex.split(os.environ["AI_AGENT_COMMAND"].strip().strip("\"'"))
    kept: list[str] = []
    skip = False
    for word in words:
        if skip:
            skip = False
        elif word == "--permission-mode":
            skip = True
        elif word != "--dangerously-skip-permissions" and not word.startswith("--permission-mode="):
            kept.append(word)
    return kept


def _safeguards(url: str, folder: Path) -> list[str]:
    """What the session may touch, whatever its command says: its tools, its folder, and this
    engine on the network. The sandbox is the operating system's, so a script it writes is held too;
    a machine where it cannot run refuses to start the session."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    # In a container the container is the boundary: the sandbox's own isolation cannot run inside it.
    contained = os.environ.get("AI_AGENT_SANDBOX", "").strip().lower() == "container"
    settings = {
        "sandbox": {
            "enabled": not contained,
            "failIfUnavailable": not contained,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": True,
            "filesystem": {"denyRead": ["~/"], "allowRead": [str(folder), sys.prefix]},
            "network": {"allowedDomains": [host, f"{host}{port}"]},
        },
        "permissions": {"blockReadsOutsideWorkingDirectories": True},
    }
    return [
        "--restricted",
        "--tools",
        TOOLS,
        "--allowedTools",
        TOOLS,
        "--disallowedTools",
        "Agent",
        "WebFetch",
        "WebSearch",
        "mcp__*",
        "--strict-mcp-config",
        "--permission-mode",
        "dontAsk",
        "--settings",
        json.dumps(settings),
    ]


# Of the server's environment, only what Claude Code itself needs: never its database or secrets.
PASSED = re.compile(r"^(HOME|USER|LANG|LC_\w+|TMPDIR|SHELL|ANTHROPIC_\w+|CLAUDE_\w+|AWS_\w+|NODE_\w+)$")


def _session_environment(token: str) -> dict[str, str]:
    return {
        **{name: value for name, value in os.environ.items() if PASSED.match(name)},
        "REFIROO_TOKEN": token,
        "PATH": f"{Path(sys.prefix) / 'bin'}:{os.environ.get('PATH', '')}",
    }


def _end(session: Session, grants: list[str]) -> None:
    for grant in grants:
        delete_grant(session, grant)


def _await_its_jobs(session: Session, ctx: Any, started: float) -> None:
    """The session has stopped: the jobs it queued run as its client, so its grants stay until they
    are done, or until the session's time is over."""
    client = select(OAuthClient.id).where(OAuthClient.name == CLIENT).scalar_subquery()
    waiting = select(Job.id).where(
        Job.requested_by_client_id == client,
        Job.kind != "aiTask",
        Job.state.in_(("queued", "running")),
    )
    while session.scalar(waiting.limit(1)) is not None:
        session.commit()
        ctx.check()
        if time.monotonic() - started > TIMEOUT_SECONDS:
            return
        time.sleep(2)
    session.commit()


def _api_url() -> str:
    return os.environ.get("AI_AGENT_API_URL", "").strip() or get_settings().public_url


def _openapi(url: str) -> bytes:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(f"{url}/openapi.json", context=context, timeout=30) as answer:
        return answer.read()


def folder_of(ctx_files: Any, task: AiTask) -> Path:
    return Path(ctx_files.directory) / "agent" / task.public_id


def remove_folder(files: Any, task: AiTask) -> None:
    shutil.rmtree(folder_of(files, task), ignore_errors=True)


def _plain(command: str) -> str:
    """A call in a person's words."""
    found = _CALL.search(command)
    if not found:
        return "Working through the workbook" if "workbook" in command else "Working"
    method, path = found.group(1) or "GET", found.group(2).split("?")[0]
    parts = path.split("/")
    if parts[0] == "objects" and len(parts) > 1 and method == "GET":
        return f"Reading stored {parts[1].replace('-', ' ')} records"
    reading = "Reading" if method == "GET" else "Writing"
    return f"{reading} {parts[0].replace('-', ' ')}"


def _steps(
    load: bool, drafted: bool, audited: dict[tuple[str, str], Any], jobs: list[Any]
) -> tuple[list[dict[str, Any]], int | None]:
    """What this turn has reached, from what the engine recorded of its client: the audit's last
    time per (type, action) and the turn's jobs, oldest first. A turn shows only what it can reach:
    the model and its check, or the release and the load. A check before the model's last change
    no longer counts, and a load counts once one applied without a refusal."""

    def step(key: str, label: str, done: bool = False, running: bool = False) -> dict[str, Any]:
        return {"key": key, "label": label, "done": done, "running": running}

    def waiting(job: Any) -> bool:
        return job.state in ("queued", "running")

    if load:
        loads = [job for job in jobs if job.kind != "dryRun"]
        loaded = any(
            job.state == "completed"
            and not (job.counts or {}).get("rejected")
            and (job.counts or {}).get("applied")
            for job in loads
        )
        loading = not loaded and any(waiting(job) for job in loads)
        return [
            step("install", "Release installed", ("model_release", "installed") in audited),
            step(
                "load",
                "Loading into the change set" if loading else "Loaded into the change set",
                loaded,
                loading,
            ),
        ], None
    changed = audited.get(("model_draft", "updated"))
    checks = [job for job in jobs if job.kind == "dryRun"]
    last = checks[-1] if checks else None
    current = last is not None and (changed is None or last.created_at >= changed)
    checking = last is not None and waiting(last)
    checked = current and last.state == "completed"
    return [
        step("draft", "Model draft started", drafted or ("model_draft", "created") in audited),
        step("operations", "Model changed", changed is not None),
        step("check", "Checking every row" if checking else "Every row checked", checked, checking),
    ], (last.counts or {}).get("rejected") if checked else None


def _reached(
    session: Session, load: bool, drafted: bool, workspace: str, since: datetime
) -> tuple[list[dict[str, Any]], int | None]:
    client = select(OAuthClient.id).where(OAuthClient.name == CLIENT).scalar_subquery()
    audited = session.execute(
        select(AuditEvent.aggregate_type, AuditEvent.action, func.max(AuditEvent.occurred_at))
        .where(
            AuditEvent.actor_client_id == client,
            AuditEvent.occurred_at >= since,
            AuditEvent.aggregate_type.in_(("model_draft", "model_release")),
        )
        .group_by(AuditEvent.aggregate_type, AuditEvent.action)
    ).all()
    jobs = session.execute(
        select(Job.kind, Job.state, Job.counts, Job.created_at)
        .where(
            Job.requested_by_client_id == client,
            Job.workspace_key == workspace,
            Job.created_at >= since,
            Job.kind.in_(("dryRun", "import", "batch")),
        )
        .order_by(Job.sequence_id)
    ).all()
    return _steps(load, drafted, {(kind, action): at for kind, action, at in audited}, list(jobs))


class _Progress:
    """The session's stream as what it is doing now: read from the log, written when it moves."""

    def __init__(self, log: Path) -> None:
        self.log = log
        self.position = 0
        self.now = "Starting"
        self.result: dict[str, Any] = {}

    def read(self) -> bool:
        if not self.log.exists():
            return False
        moved = False
        with self.log.open() as handle:
            handle.seek(self.position)
            while True:
                line = handle.readline()
                if not line or not line.endswith("\n"):
                    break
                self.position = handle.tell()
                moved = self._line(line) or moved
        return moved

    def _line(self, line: str) -> bool:
        try:
            event = json.loads(line)
        except ValueError:
            return False
        if event.get("type") == "result":
            self.result = event
            return False
        moved = False
        for block in (event.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text", "").strip():
                self.now = block["text"].strip().split("\n")[0][:200]
                moved = True
            elif block.get("type") == "tool_use":
                command = str((block.get("input") or {}).get("command") or "")
                if command:
                    self.now = _plain(command)
                    moved = True
        return moved


def _stop_earlier(earlier: dict[str, Any] | None) -> None:
    """Ends a session left running by a worker that stopped: its job came back, and two sessions in
    one folder would overwrite each other. The process counts only if it still names its session,
    as its number may be another's by now."""
    if not earlier:
        return
    pid = int(earlier["pid"])
    shown = subprocess.run(
        ["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, check=False
    )
    if str(earlier["session"]) not in shown.stdout:
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _run_turn(
    session: Session, job: Job, ctx: Any, task_id: str, folder: Path, prompt: str, session_id: str, *, first: bool, load: bool = False
) -> _Progress | None:
    """One turn of the session, the task's progress written as it goes; ``None`` when it could not
    start, with the reason on the task."""
    task_key = task_id
    _stop_earlier((load_task(session, task_key).design or {}).get("agentProcess"))
    if first:
        (folder / PROPOSAL).unlink(missing_ok=True)
    token, opened = _access(session, job, load_task(session, task_key).workspace_key)
    session.commit()
    command = [
        *_base_command(),
        *_safeguards(_api_url(), folder),
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        *(["--session-id", session_id] if first else ["--resume", session_id]),
    ]
    log = folder / f"session-{uuid4().hex[:8]}.log"
    progress = _Progress(log)
    started = time.monotonic()
    since = datetime.now(UTC)
    with log.open("w") as output:
        try:
            process = subprocess.Popen(
                command,
                cwd=folder,
                env=_session_environment(token),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
        except OSError as error:
            _end(session, opened)
            task = load_task(session, task_key, for_update=True)
            note(task, "warning", f"AI_AGENT_COMMAND could not start: {error}")
            finish(task, "failed", ctx.ai.task_retention_days if ctx.ai else 90)
            session.commit()
            return None
        try:
            task = load_task(session, task_key, for_update=True)
            task.design = {
                **(task.design or {}),
                "agentProcess": {"pid": process.pid, "session": session_id},
            }
            session.commit()
            shown = -10.0
            while process.poll() is None:
                ctx.check()
                if time.monotonic() - started > TIMEOUT_SECONDS:
                    raise TimeoutError("The session took too long")
                moved = progress.read()
                if moved or time.monotonic() - shown >= 5:
                    shown = time.monotonic()
                    task = load_task(session, task_key, for_update=True)
                    milestones, refused = _reached(
                        session, load, task.draft_id is not None, task.workspace_key, since
                    )
                    task.design = {
                        **(task.design or {}),
                        "progress": {
                            "now": progress.now,
                            "seconds": round(time.monotonic() - started),
                            "refused": refused,
                            "milestones": milestones,
                        },
                    }
                    session.commit()
                time.sleep(2)
            _await_its_jobs(session, ctx, started)
        except BaseException:
            _stop_earlier({"pid": process.pid, "session": session_id})
            raise
        finally:
            _end(session, opened)
            session.commit()
    progress.read()
    return progress


def _said(progress: _Progress) -> str:
    result = progress.result
    cost = result.get("total_cost_usd")
    seconds = round((result.get("duration_ms") or 0) / 1000)
    words = str(result.get("result") or "")
    return f"{words[:6000]} ({seconds} s" + (f", ${cost:.2f})" if cost else ")")


def _retention(ctx: Any) -> int:
    return ctx.ai.task_retention_days if ctx.ai else 90


def _proposal_landed(
    session: Session, ctx: Any, task_id: str, folder: Path, progress: _Progress, check_of: Any
) -> None:
    """The proposal the session wrote: the task shows it and waits, or fails with what was said."""
    task = load_task(session, task_id, for_update=True)
    path = folder / PROPOSAL
    try:
        proposal = json.loads(path.read_text())
    except (OSError, ValueError):
        proposal = None
    draft = (
        session.scalar(select(ModelDraft).where(ModelDraft.public_id == str(proposal.get("draftId"))))
        if isinstance(proposal, dict)
        else None
    )
    if draft is None:
        note(task, "warning", _said(progress) or "The session ended without a proposal")
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    design = dict(task.design or {})
    design.pop("progress", None)
    questions = [
        {
            "text": str(q.get("text"))[:500],
            "options": [str(o) for o in q.get("options") or []],
            "assumed": q.get("assumed"),
        }
        for q in proposal.get("questions") or []
        if isinstance(q, dict) and q.get("text")
    ]
    task.draft_id = draft.id
    task.design = {
        **design,
        "stage": "model",
        "summary": str(proposal.get("summary") or ""),
        "questions": questions,
        "origin": {"kind": "ai", "provider": "claude-code", "model": None, "promptVersion": "agent/1"},
        "outcome": {},
    }
    task.check = check_of(session, draft)
    note(task, "note", _said(progress))
    finish(task, "checked", _retention(ctx))
    task.finished_at = None
    session.commit()


def start(session: Session, job: Job, ctx: Any, task_id: str, workbook_path: Path | None, check_of: Any) -> None:
    """The session's first turn: the workbook to a draft the person reviews."""
    task = load_task(session, task_id, for_update=True)
    workspace = task.workspace_key
    words = task.words
    url = _api_url()
    release = session.get(ModelRelease, load_assignment(session, workspace)[1].id)
    folder = folder_of(ctx.files, task)
    folder.mkdir(parents=True, exist_ok=True)
    if workbook_path is not None:
        shutil.copyfile(workbook_path, folder / "workbook.xlsx")
    (folder / "model.json").write_text(json.dumps(release.model_json))
    (folder / "openapi.json").write_bytes(_openapi(url))
    session_id = str(uuid4())
    task.design = {**(task.design or {}), "stage": "model", "agentSession": session_id}
    task.state = "reading"
    session.commit()
    prompt = _propose_prompt(words, workspace, url, workbook=workbook_path is not None)
    progress = _run_turn(session, job, ctx, task_id, folder, prompt, session_id, first=True)
    if progress is not None:
        _proposal_landed(session, ctx, task_id, folder, progress, check_of)


def said(session: Session, job: Job, ctx: Any, task_id: str, words: str, check_of: Any) -> None:
    """The person's answers or corrections: the same session goes on."""
    task = load_task(session, task_id)
    folder = folder_of(ctx.files, task)
    (folder / PROPOSAL).unlink(missing_ok=True)
    progress = _run_turn(
        session,
        job,
        ctx,
        task_id,
        folder,
        _said_prompt(words),
        (task.design or {})["agentSession"],
        first=False,
    )
    if progress is not None:
        _proposal_landed(session, ctx, task_id, folder, progress, check_of)


def accepted(session: Session, job: Job, ctx: Any, task_id: str) -> None:
    """The person accepted: the same session installs one release and loads into a change set."""
    task = load_task(session, task_id)
    workspace = task.workspace_key
    folder = folder_of(ctx.files, task)
    progress = _run_turn(
        session, job, ctx, task_id, folder, _ACCEPTED, (task.design or {})["agentSession"], first=False, load=True
    )
    if progress is None:
        return
    words = str(progress.result.get("result") or "")
    change_set_id = next(
        (
            line.split(LAST_LINE, 1)[1].strip().strip("`*")
            for line in reversed(words.splitlines())
            if LAST_LINE in line
        ),
        None,
    )
    change_set = (
        session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id)) if change_set_id else None
    )
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    design.pop("progress", None)
    task.design = design
    note(task, "note", _said(progress))
    counts = _counts(session, change_set.id) if change_set is not None else None
    # An empty change set is no load, whatever the session's last line says.
    if change_set is None or change_set.workspace_key != workspace or not counts["applied"]:
        finish(task, "failed", _retention(ctx))
    else:
        task.result = {
            "changeSetId": change_set.id,
            "changeSetName": change_set.name,
            "counts": counts,
        }
        finish(task, "loaded", _retention(ctx))
        remove_folder(ctx.files, task)
    session.commit()


def _counts(session: Session, change_set_id: str) -> dict[str, int]:
    """What the change set holds, as a load's counts: new records and changed ones."""
    created, updated = session.execute(
        text(
            "SELECT count(*) FILTER (WHERE o.id IS NULL), count(*) FILTER (WHERE o.id IS NOT NULL)"
            " FROM change_set_objects c LEFT JOIN objects o ON o.id = c.object_id"
            " WHERE c.change_set_id = :id AND NOT c.is_deleted"
        ),
        {"id": change_set_id},
    ).one()
    return {
        "applied": created + updated,
        "created": created,
        "updated": updated,
        "unchanged": 0,
        "rejected": 0,
    }
