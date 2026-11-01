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
import logging
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
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ...config import get_settings
from ...errors import ApiError
from ...models.commands import GrantCreate, GrantPrincipal, GrantScope, RoleCreate
from ...models.database import (
    AiCall,
    AiTask,
    AuditEvent,
    AuthorizationState,
    ChangeSet,
    ImportProfile,
    Job,
    ModelDraft,
    ModelRelease,
    OAuthClient,
    Role,
    SourceFile,
    WorkspaceModel,
)
from ..authorization.administration import create_grant, create_role, delete_grant
from ..authorization.permissions import permissions_of
from ..identity import tokens
from ..identity.clients import create_session_client, retire_session_client
from ..identity.settings import IdentitySettings
from ..imports.profiles import model_key_of, save_for_release
from ..jobs.batches import JobCancelled
from ..model.compiler import parse_model
from ..model.diagnostics import ModelValidationError
from ..model.migrations import parse_type_mappings, plan_migration
from ..model.release_lifecycle import set_release_status
from ..model.workspace_models import load_assignment
from .store import finish, held_by_another, held_counts, load_task, note

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 1800
PROMPT_VERSION = "agent/5"
LAST_LINE = "CHANGE_SET:"
THEN_LINE = "THEN_RELEASE:"
RELEASE_LINE = "RELEASE:"
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
        "The network is reached with curl: Python cannot open a socket in the sandbox. The "
        "language of a model is components.schemas.EngineModel in openapi.json. "
        f"{data}Work only in the workspace {workspace}: no other "
        "workspace is read or changed. Where the data gives one thing two names or values, that "
        "is intended: keep them all as they are, correct nothing and do not keep only the most "
        "common; you may raise it as a question."
    )


def _starting_point(held: dict[str, int]) -> str:
    """Whether the session adds to the model or may start anew: what the workspace holds decides."""
    total = sum(held.values())
    if total:
        return (
            f"The workspace holds {total} records: keep its model and add to it, unless the words "
            "ask otherwise."
        )
    return (
        "The workspace holds no records: if the words ask for a model, it may be a new one with "
        "only what this needs."
    )


_KEYS = (
    "Give each source of a load a key that finds its records in the next file, of several columns "
    "(attributeTypeKeys) if no one column does; if the file has none, raise that as a question. "
    "An empty cell is no value: never call its row skipped or left out."
)


_SHAPE = (
    "What the file repeats across columns or rows becomes types of its own, related to each other, "
    "unless the words ask otherwise; if you keep such a repetition flat, raise that as a question."
)


_RECORDS = (
    "A record changes type and keeps its ID, values, relationships and history through a change set's "
    "restructurings or, for every record of a type, through the proposal's moves; creating new "
    "records and removing the old ones loses them."
)


_WORDS = (
    "Build everything the words ask for, as they place it, also what the file has no data for (an "
    "empty type): the words go before the file's shape, and a question does not replace building. "
    "What the words name as a group holds its members as records under it; a field's candidate "
    "filter can name that group by a fixed value of an ancestor (ancestor:<type>.<field>). Say a "
    "thing cannot be built only after trying it on the draft."
)


def _propose_prompt(
    words: str | None, workspace: str, url: str, held: dict[str, int], *, workbook: bool = True
) -> str:
    check = (
        "Build the model in a model draft and check every row with the draft's dry run"
        if workbook
        else "Put any model change in a model draft, with the workspace's model unchanged if none is "
        "needed, and work out every record the words touch"
    )
    return (
        f"{(words or '').strip() or DEFAULT_WORDS}\n\n"
        f"{_connection(workspace, url, workbook=workbook)} {_starting_point(held)} "
        f"{_WORDS} {_RECORDS} {_SHAPE + ' ' + _KEYS + ' ' if workbook else ''}{check}; install, "
        "activate, load and publish nothing yet: the person reviews first. Then write "
        f'{PROPOSAL}: {{"draftId": ..., "summary": two sentences a person reads, "questions": '
        '[{"text", "options", "assumed"}] for what only a person can decide, "moves": '
        '[{"from": a type key, "to": its type key in the draft, "attributes": [{"attributeTypeKey", '
        '"from"}]}] only for a whole type that becomes another, kept in order}.'
    )


_PART = (
    " If instead you move part of a type's records to other types, install the draft (the final "
    "model) and a second release that holds the final model with the old types beside it, make "
    "the change set on the second release (source currentLive, modelReleaseId), restructure the "
    f"records in it, and end with the lines {LAST_LINE} <its id> and {THEN_LINE} <the final "
    "release's id>."
)


_ACCEPTED = (
    "The person accepted. They may have edited the draft in the model editor: read it again. Install "
    "it as exactly one new release and do not activate it, make the change (a workbook's rows, or "
    "what the words ask of the stored records) in a new change set "
    f"on that release, do not publish it, and end with the line {LAST_LINE} <its id>.{_PART}"
)


_MOVED = (
    "The person accepted. They may have edited the draft in the model editor: read it again. Install "
    "it as exactly one new release and do not activate it, and end with the line "
    f"{RELEASE_LINE} <its id>. The records of the proposal's moves are moved by a migration the "
    "person confirms: do not move or create them."
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


MODEL_ROLE = "AI assistant: model"
CLIENT = "AI assistant"
DATA_GROUPS = ["browse", "change-sets", "bulk"]
MODEL_GROUPS = ["model-authoring", "model-install"]


def _role(session: Session, name: str, groups: list[str]) -> str:
    found = session.scalar(select(Role).where(Role.name == name))
    if found is None:
        found = create_role(session, RoleCreate(name=name, actionGroups=groups))
    return found.key


def _access(session: Session, job: Job, task: AiTask) -> tuple[str, int, list[str]]:
    """A token that can only do the session's work, as the task's own client (AP-D30): of reading
    and loading in this workspace and authoring and installing a model, what who asked may do, with
    the record types they are narrowed to (AP-D31). Publishing and activating are refused by the
    engine, whatever the session tries and whoever asked. The grants end with the turn."""
    workspace = task.workspace_key
    kind, row = (
        ("client", job.requested_by_client_id)
        if job.requested_by_client_id is not None
        else ("user", job.requested_by_user_id)
    )
    if row is None:
        raise ValueError("The task names no one who asked for it")
    generation = session.scalar(select(AuthorizationState.generation)) or 0
    asked = permissions_of(session, kind, row, generation)
    if task.client_id is None:
        task.client_id = create_session_client(session, CLIENT).id
    client = session.get(OAuthClient, task.client_id)
    principal = GrantPrincipal(kind="client", id=client.public_id)
    grants = []
    for group in DATA_GROUPS:
        narrowing = asked.narrowing(group, workspace)
        if narrowing is None:
            continue
        scope = GrantScope(
            workspaceKey=workspace,
            applications=sorted(narrowing.applications),
            recordTypes=sorted(narrowing.record_types),
        )
        role = _role(session, f"{CLIENT}: {group}", [group])
        grants.append(
            create_grant(session, GrantCreate(principal=principal, role=role, scope=scope)).grant.public_id
        )
    if asked.allows("model-authoring", None) and (
        asked.allows("model-release", workspace) or asked.allows("model-install", None)
    ):
        model = _role(session, MODEL_ROLE, MODEL_GROUPS)
        grants.append(
            create_grant(
                session, GrantCreate(principal=principal, role=model, scope=GrantScope(instance=True))
            ).grant.public_id
        )
    token = tokens.issue(
        session, _identity(), subject=client.public_id, kind="client", audience="management"
    )
    return token, client.id, grants


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


def _await_its_jobs(session: Session, ctx: Any, started: float, client: int) -> None:
    """The session has stopped: the jobs it queued run as its client, so its grants stay until they
    are done, or until the session's time is over."""
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


def _transcripts() -> Path:
    """Where Claude Code keeps a session's transcript: outside the folder and any retention."""
    home = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return (Path(home) if home else Path.home() / ".claude") / "projects"


def _transcript_name(folder: Path) -> str:
    """Claude Code names the directory after the folder's path, each other character a hyphen."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(folder))


def remove_folder(files: Any, task: AiTask) -> None:
    """The session's folder and its transcript (AP-D37). A session that ran and left no transcript
    where one is expected is said in the log: the name is Claude Code's, and may change."""
    folder = folder_of(files, task)
    transcript = _transcripts() / _transcript_name(folder)
    if (task.design or {}).get("agentSession") and _transcripts().is_dir() and not transcript.is_dir():
        log.warning("No transcript at %s for task %s", transcript, task.public_id)
    shutil.rmtree(folder, ignore_errors=True)
    shutil.rmtree(transcript, ignore_errors=True)
    for log_file in folder.parent.glob(f"{folder.name}.*.log"):
        log_file.unlink(missing_ok=True)


def sweep(session: Session, files: Any) -> None:
    """What no task holds any more: the folder of a task that expired, and a transcript of this
    instance's folders whose folder is gone (AP-D37). Removed after the expiry's commit."""
    root = Path(files.directory) / "agent"
    if root.is_dir():
        names = [path.name for path in root.iterdir() if path.is_dir()]
        known = set(session.scalars(select(AiTask.public_id).where(AiTask.public_id.in_(names))))
        for name in names:
            if name not in known:
                shutil.rmtree(root / name, ignore_errors=True)
        # A turn's log lies beside its folder, named after the task; it goes with the folder.
        for path in root.glob("*.log"):
            if not (root / path.name.split(".")[0]).is_dir():
                path.unlink(missing_ok=True)
    prefix = _transcript_name(root) + "-"
    if _transcripts().is_dir():
        for path in _transcripts().iterdir():
            if path.name.startswith(prefix) and not (root / path.name[len(prefix) :]).exists():
                shutil.rmtree(path, ignore_errors=True)


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
    session: Session, client: int, load: bool, drafted: bool, workspace: str, since: datetime
) -> tuple[list[dict[str, Any]], int | None]:
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
        self.model: str | None = None
        # Each message's usage by its ID, as the stream repeats a message while it grows (AP-D36).
        self.usage: dict[str, tuple[int, int]] = {}

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
                try:
                    moved = self._line(line) or moved
                except (AttributeError, TypeError, KeyError):
                    # The stream is another program's: a line of a shape not known only shows less.
                    log.warning("A session's log line could not be read", exc_info=True)
        return moved

    def tokens(self) -> tuple[int | None, int | None]:
        if not self.usage:
            return None, None
        # The stream's lines hold a message's output before it is written (939 of 27,542 on a real
        # run): the result line's figure stands, and a run stopped before it has only the stream's.
        written = (self.result.get("usage") or {}).get("output_tokens")
        return (
            sum(found[0] for found in self.usage.values()),
            written if written is not None else sum(found[1] for found in self.usage.values()),
        )

    def _line(self, line: str) -> bool:
        try:
            event = json.loads(line)
        except ValueError:
            return False
        if not isinstance(event, dict):
            return False
        if event.get("type") == "result":
            self.result = event
            return False
        if event.get("type") == "system" and event.get("model"):
            self.model = str(event["model"])
        # A system event's message is plain text (a permission refused, say): only an object is a turn.
        message = event.get("message")
        if not isinstance(message, dict):
            return False
        if message.get("id") and message.get("usage"):
            usage = message["usage"]
            self.usage[message["id"]] = (
                (usage.get("input_tokens") or 0)
                + (usage.get("cache_creation_input_tokens") or 0)
                + (usage.get("cache_read_input_tokens") or 0),
                usage.get("output_tokens") or 0,
            )
        moved = False
        content = message.get("content")
        for block in content if isinstance(content, list) else []:
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


def _provider() -> str:
    command = _base_command()
    return "claude-code" if Path(command[0]).name == "claude" else Path(command[0]).name


def _record_turn(
    session: Session,
    task_id: str,
    job_id: str | None,
    progress: _Progress,
    started_at: datetime,
    prompt: str,
    failure: tuple[str, str] | None,
) -> None:
    """One row per turn however it ended (AP-D36). The session reports its cost as a running total
    over its turns, so a turn's is the difference from the task's last figure; a run with no result
    line has none. With ``AI_LOG_CONTENT`` on, the prompt and the final answer, never the stream."""
    settings = get_settings()
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    total = progress.result.get("total_cost_usd")
    cost = None
    if total is not None:
        before = design.get("agentCost") or 0
        cost = total - before if total >= before else total
        design["agentCost"] = total
    model = progress.model or design.get("agentModel")
    if model:
        design["agentModel"] = model
    design.pop("agentProcess", None)
    task.design = design
    answer = str(progress.result.get("result") or "")
    tokens_in, tokens_out = progress.tokens()
    row = AiCall(
        public_id=str(uuid4()),
        purpose="assistantSession",
        provider=design.get("agentProvider") or _provider(),
        model=model or "unknown",
        send_level=settings.ai_send_level,
        prompt_version=PROMPT_VERSION,
        requested_by_user_id=task.requested_by_user_id,
        requested_by_client_id=task.requested_by_client_id,
        job_id=job_id,
        task_id=task.public_id,
        started_at=started_at,
        duration_ms=round((datetime.now(UTC) - started_at).total_seconds() * 1000),
        bytes_in=len(prompt.encode()),
        bytes_out=len(answer.encode()),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=Decimal(str(round(cost, 4))) if cost is not None else None,
        outcome="failed" if failure else "answered",
        failure_kind=failure[0] if failure else None,
        failure=failure[1] if failure else None,
    )
    if settings.ai_log_content:
        row.content = {"instructions": prompt, "context": None, "answer": answer}
        row.content_expires_at = started_at + timedelta(days=settings.ai_log_content_days)
    session.add(row)
    session.commit()


def _log_split(
    session: Session,
    task_id: str,
    client: int,
    since: datetime,
    started: float,
    progress: _Progress,
) -> None:
    """One line per turn: where its time went, as a load removes the folder and its log (AP11)."""
    jobs = session.scalar(
        select(
            func.coalesce(func.sum(func.extract("epoch", Job.finished_at - Job.started_at)), 0)
        ).where(
            Job.requested_by_client_id == client,
            Job.kind != "aiTask",
            Job.created_at >= since,
            Job.finished_at.is_not(None),
        )
    )
    model = (progress.result.get("duration_api_ms") or 0) / 1000
    log.info(
        "Session turn of task %s: total %.0f s, model %.0f s, jobs %.0f s",
        task_id,
        time.monotonic() - started,
        model,
        float(jobs or 0),
    )


def _record_interrupted(
    session: Session, task_id: str, folder: Path, earlier: dict[str, Any] | None
) -> None:
    """A worker that died recorded nothing of its turn: the next turn does, from its log."""
    if not earlier or not earlier.get("log") or not earlier.get("startedAt"):
        return
    progress = _Progress(folder.parent / str(earlier["log"]))
    progress.read()
    _record_turn(
        session,
        task_id,
        earlier.get("job"),
        progress,
        datetime.fromisoformat(earlier["startedAt"]),
        "",
        ("interrupted", "The worker stopped while the session ran."),
    )


def _run_turn(
    session: Session, job: Job, ctx: Any, task_id: str, folder: Path, prompt: str, session_id: str, *, first: bool, load: bool = False
) -> _Progress | None:
    """One turn of the session, the task's progress written as it goes; ``None`` when it could not
    start, with the reason on the task."""
    task_key = task_id
    earlier = (load_task(session, task_key).design or {}).get("agentProcess")
    _stop_earlier(earlier)
    _record_interrupted(session, task_key, folder, earlier)
    if first:
        (folder / PROPOSAL).unlink(missing_ok=True)
    token, client, opened = _access(session, job, load_task(session, task_key, for_update=True))
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
    log = folder.parent / f"{folder.name}.session-{uuid4().hex[:8]}.log"
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
            _record_turn(
                session, task_key, job.id, progress, since, prompt, ("failed", f"Could not start: {error}")
            )
            task = load_task(session, task_key, for_update=True)
            note(task, "warning", f"AI_AGENT_COMMAND could not start: {error}")
            finish(task, "failed", _retention(ctx))
            session.commit()
            return None
        failure: tuple[str, str] | None = None
        try:
            task = load_task(session, task_key, for_update=True)
            task.design = {
                **(task.design or {}),
                "agentProcess": {
                    "pid": process.pid,
                    "session": session_id,
                    "log": log.name,
                    "startedAt": since.isoformat(),
                    "job": job.id,
                },
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
                        session, client, load, task.draft_id is not None, task.workspace_key, since
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
            _await_its_jobs(session, ctx, started, client)
        except BaseException as error:
            _stop_earlier({"pid": process.pid, "session": session_id})
            failure = (
                ("timeout", "The session took too long.")
                if isinstance(error, TimeoutError)
                else ("cancelled", "Cancelled by a person.")
                if isinstance(error, JobCancelled)
                else ("failed", f"The session's turn failed ({type(error).__name__}).")
            )
            raise
        finally:
            session.rollback()
            _end(session, opened)
            session.commit()
            progress.read()
            if failure is None and (not progress.result or progress.result.get("is_error")):
                failure = ("failed", "The session ended without an answer.")
            _record_turn(session, task_key, job.id, progress, since, prompt, failure)
            _log_split(session, task_key, client, since, started, progress)
    return progress


def _said(progress: _Progress) -> str:
    result = progress.result
    cost = result.get("total_cost_usd")
    seconds = round((result.get("duration_ms") or 0) / 1000)
    words = str(result.get("result") or "")
    return f"{words[:6000]} ({seconds} s" + (f", ${cost:.2f})" if cost else ")")


def _retention(_ctx: Any) -> int:
    return get_settings().ai_task_retention_days


def _plural(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def _shape(model: dict[str, Any], base: dict[str, Any], records: dict[str, int]) -> list[dict[str, Any]]:
    """The proposal's shape from the draft and its dry run, not from the session's account: each type
    it adds, changes or loads, with its attributes and the records the check would write."""
    before = {found.get("key"): found for found in base.get("objectTypes") or []}
    shape = []
    for found in model.get("objectTypes") or []:
        key = found.get("key")
        attributes = found.get("attributes") or []
        earlier = before.get(key)
        change = (
            "New type"
            if earlier is None
            else None
            if (earlier.get("attributes") or []) == attributes
            else "Changed type"
        )
        written = records.get(key, 0)
        if change is None and not written:
            continue
        parts = [*([change] if change else []), _plural(len(attributes), "attribute")]
        if written:
            parts.append(_plural(written, "record"))
        shape.append({"objectTypeKey": key, "name": found.get("name") or key, "text": ", ".join(parts)})
    return shape


def _left_out(
    model: dict[str, Any],
    base: dict[str, Any],
    held: dict[str, int],
    moved: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Types the workspace holds records of and the proposed model no longer has: the person is told
    before accepting, whatever the session said. A type the proposal moves is not left out."""
    kept = {found.get("key") for found in model.get("objectTypes") or []} | moved
    names = {found.get("key"): found.get("name") for found in base.get("objectTypes") or []}
    gone = [f"{names.get(key) or key} ({count:,})" for key, count in sorted(held.items()) if key not in kept]
    if not gone:
        return []
    return [
        {
            "id": "types-left-out",
            "kind": "leftOut",
            "text": "This model leaves out types the workspace holds records of: " + ", ".join(gone),
            "open": True,
        }
    ]


def _beside_held(
    session: Session, job_id: str | None, model: dict[str, Any], held: dict[str, int]
) -> list[dict[str, Any]]:
    """New records of a type the workspace already holds: rows that did not find their records read
    as an update gone wrong, and the person is told before accepting (AP-D42)."""
    if job_id is None:
        return []
    created = session.execute(
        text(
            "SELECT i.outcome ->> 'objectTypeKey', count(*) FROM job_items i"
            " JOIN jobs j ON j.sequence_id = i.job_id"
            " WHERE j.id = :job AND i.outcome ->> 'action' = 'created'"
            " AND i.outcome ->> 'objectTypeKey' IS NOT NULL GROUP BY 1"
        ),
        {"job": job_id},
    ).all()
    names = {found.get("key"): found.get("name") for found in model.get("objectTypes") or []}
    return [
        {
            "id": f"beside-held-{key}",
            "kind": "besideHeld",
            "text": (
                f"{count:,} new {names.get(key) or key} beside the {held[key]:,} held. "
                "If this is an update, the rows did not find their records."
            ),
            "open": True,
        }
        for key, count in sorted(created)
        if held.get(key)
    ]


def _requested_moves(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    """The proposal's ``moves`` as a migration's ``typeMappings`` (AP-D47); anything else in it is
    not a move."""
    found = []
    raw = proposal.get("moves")
    for move in raw if isinstance(raw, list) else []:
        if not isinstance(move, dict):
            continue
        found.append(
            {
                "fromObjectTypeKey": str(move.get("from") or ""),
                "toObjectTypeKey": str(move.get("to") or ""),
                "attributes": [
                    {"attributeTypeKey": str(a.get("attributeTypeKey")), "from": a.get("from")}
                    for a in move.get("attributes") or []
                    if isinstance(a, dict)
                ],
            }
        )
    return found


def _planned_moves(
    mappings: list[dict[str, Any]],
    base: dict[str, Any],
    model: dict[str, Any],
    held: dict[str, int],
) -> list[dict[str, Any]]:
    """What the proposal's moves would do, checked against the draft by the migration's own plan
    (AP-D47): each with the records the workspace holds of the type. A move the plan refuses raises
    its ``ApiError``; a model that does not compile, ``ModelValidationError``."""
    if not mappings:
        return []
    plan_migration(parse_model(base), parse_model(model), parse_type_mappings(mappings))
    old = {found.get("key"): found.get("name") for found in base.get("objectTypes") or []}
    new = {found.get("key"): found.get("name") for found in model.get("objectTypes") or []}
    return [
        {
            "from": move["fromObjectTypeKey"],
            "fromName": old.get(move["fromObjectTypeKey"]) or move["fromObjectTypeKey"],
            "to": move["toObjectTypeKey"],
            "toName": new.get(move["toObjectTypeKey"]) or move["toObjectTypeKey"],
            "records": held.get(move["fromObjectTypeKey"], 0),
            "attributes": move["attributes"],
        }
        for move in mappings
    ]


def _records_per_type(session: Session, job_id: str | None) -> dict[str | None, int]:
    """What a dry run would write per type; under ``None``, the relationships, which have no type."""
    if job_id is None:
        return {}
    return dict(
        session.execute(
            text(
                "SELECT i.outcome ->> 'objectTypeKey', count(*) FROM job_items i"
                " JOIN jobs j ON j.sequence_id = i.job_id"
                " WHERE j.id = :job AND i.outcome ->> 'action' IN ('created', 'updated') GROUP BY 1"
            ),
            {"job": job_id},
        ).all()
    )


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
    if draft is not None and held_by_another(session, draft.id, task.id):
        # Reading it is not refused, and a proposal must not name it either (AP-D44).
        note(task, "warning", "The session proposed a draft another task holds; try again")
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
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
    check = check_of(session, draft)
    base = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id).model_json
    records = _records_per_type(session, (check or {}).get("dryRunJobId"))
    related = records.pop(None, 0)
    if check and related:
        # The check counts a relationship as an item it creates; the person reads records and links.
        check["summary"]["created"] -= related
        check["summary"]["relationships"] = related
    held = held_counts(session, task.workspace_key)
    try:
        moves = _planned_moves(_requested_moves(proposal), base, draft.model_json, held)
    except (ApiError, ModelValidationError) as error:
        reason = error.message if isinstance(error, ApiError) else "the draft does not compile"
        note(task, "warning", f"The proposed moves cannot be made: {reason}")
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    task.draft_id = draft.id
    task.design = {
        **design,
        "stage": "model",
        "summary": str(proposal.get("summary") or ""),
        "moves": moves,
        "questions": questions,
        # A draft on no release is a new model: a type sharing a key with the old one is not a change.
        "outline": _shape(draft.model_json, base if draft.base_model_release_id else {}, records),
        "checks": [
            *_left_out(draft.model_json, base, held, frozenset(m["from"] for m in moves)),
            *_beside_held(session, (check or {}).get("dryRunJobId"), draft.model_json, held),
        ],
        "origin": {"kind": "ai", "provider": "claude-code", "model": None, "promptVersion": PROMPT_VERSION},
        "outcome": {},
    }
    task.check = check
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
    design = {key: value for key, value in (task.design or {}).items() if key != "agentCost"}
    task.design = {
        **design,
        "stage": "model",
        "agentSession": session_id,
        "agentProvider": _provider(),
        "agentPrompt": PROMPT_VERSION,
    }
    task.state = "reading"
    session.commit()
    prompt = _propose_prompt(
        words, workspace, url, held_counts(session, workspace), workbook=workbook_path is not None
    )
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


def _last_line(words: str, label: str) -> str | None:
    return next(
        (
            line.split(label, 1)[1].strip().strip("`*")
            for line in reversed(words.splitlines())
            if label in line
        ),
        None,
    )


def _installed_by(session: Session, task: AiTask, public_id: str | None) -> ModelRelease | None:
    """A release the task's own client installed (AP-D45): a session's word for an ID counts only
    if the engine recorded the installation."""
    if not public_id or task.client_id is None:
        return None
    done = session.scalar(
        select(AuditEvent.aggregate_id).where(
            AuditEvent.aggregate_type == "model_release",
            AuditEvent.action == "installed",
            AuditEvent.actor_client_id == task.client_id,
            AuditEvent.aggregate_id == public_id,
        )
    )
    if done is None:
        return None
    return session.scalar(select(ModelRelease).where(ModelRelease.public_id == public_id))


def _migration_result(session: Session, task: AiTask, words: str) -> dict[str, Any] | None:
    """The end of a task whose proposal moved whole types (AP-D49): the release the session
    installed and the type mappings, re-checked against that release as the person may have edited
    the draft. ``None`` when the session installed nothing the mappings fit."""
    release = _installed_by(session, task, _last_line(words, RELEASE_LINE))
    if release is None:
        return None
    mappings = [
        {
            "fromObjectTypeKey": move["from"],
            "toObjectTypeKey": move["to"],
            "attributes": move.get("attributes") or [],
        }
        for move in (task.design or {}).get("moves") or []
    ]
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    try:
        plan_migration(
            parse_model(current.model_json),
            parse_model(release.model_json),
            parse_type_mappings(mappings),
        )
    except ApiError, ModelValidationError:
        return None
    return {"migration": {"releaseId": release.public_id, "typeMappings": mappings}}


def accepted(session: Session, job: Job, ctx: Any, task_id: str) -> None:
    """The person accepted: the same session installs one release and loads into a change set, or,
    when the proposal moved whole types, installs the release a migration will move to (AP-D46)."""
    task = load_task(session, task_id)
    workspace = task.workspace_key
    folder = folder_of(ctx.files, task)
    moves = (task.design or {}).get("moves")
    progress = _run_turn(
        session,
        job,
        ctx,
        task_id,
        folder,
        _MOVED if moves else _ACCEPTED,
        (task.design or {})["agentSession"],
        first=False,
        load=True,
    )
    if progress is None:
        return
    words = str(progress.result.get("result") or "")
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    design.pop("progress", None)
    task.design = design
    note(task, "note", _said(progress))
    if moves:
        # No change set, and the data is not touched: the person confirms the migration (AP-D49).
        result = _migration_result(session, task, words)
        if result is None:
            note(task, "warning", "The session installed no release the moves fit")
            finish(task, "failed", _retention(ctx))
        else:
            task.result = result
            finish(task, "loaded", _retention(ctx))
            remove_folder(ctx.files, task)
            retire_unused_releases(session, task)
            retire_session_client(session, task.client_id)
        session.commit()
        return
    change_set_id = _last_line(words, LAST_LINE)
    change_set = (
        session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        if change_set_id
        else None
    )
    counts = _counts(session, change_set.id) if change_set is not None else None
    # An empty change set is no load, whatever the session's last line says.
    if change_set is None or change_set.workspace_key != workspace or not counts["applied"]:
        finish(task, "failed", _retention(ctx))
    else:
        task.result = {
            "changeSetId": change_set.id,
            "changeSetName": change_set.name,
            "counts": counts,
            **_saved_profile(session, task, change_set),
            **_then_release(session, task, words),
        }
        finish(task, "loaded", _retention(ctx))
        remove_folder(ctx.files, task)
        retire_unused_releases(session, task)
        retire_session_client(session, task.client_id)
    session.commit()


def _then_release(session: Session, task: AiTask, words: str) -> dict[str, str]:
    """The final release of a part-of-a-type reshaping: the third step, the person's, activates it
    once the old types hold no record (AP-D48)."""
    named = _last_line(words, THEN_LINE)
    if named is None:
        return {}
    release = _installed_by(session, task, named)
    if release is None:
        note(task, "warning", "The session named a final release it did not install")
        return {}
    return {"thenReleaseId": release.public_id}


def _profile_key(session: Session, name: str, release: ModelRelease) -> str:
    """The file's name as a key; a key another model's profile holds gets the release's model too."""
    stem = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")[:100] or "workbook"
    found = session.scalar(select(ImportProfile).where(ImportProfile.key == stem))
    if found is None or model_key_of(session, found) == release.release_key:
        return stem
    return f"{stem}-{release.release_key}"[:160]


def _saved_profile(session: Session, task: AiTask, change_set: ChangeSet) -> dict[str, str]:
    """What the load leaves for the next file: the profile of the imports it ran on the task's
    workbook, saved by the engine whatever route the session took (AP-D41), or why there is none."""
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    if source is None:
        return {}
    jobs = list(
        session.scalars(
            select(Job)
            .where(
                Job.kind == "import",
                Job.state == "completed",
                Job.change_set_id == change_set.id,
                Job.parameters["file"]["sha256"].as_string() == source.sha256,
            )
            .order_by(Job.sequence_id)
        )
    )
    if not jobs:
        return {"profileNotSaved": "This load did not import the workbook, so it cannot be repeated."}
    definitions = [(job.parameters.get("profile") or {}).get("definition") for job in jobs]
    if not all(definitions):
        return {"profileNotSaved": "This load read the workbook through a profile already saved."}
    sources = [found for definition in definitions for found in definition["sources"]]
    keyless = sorted(
        {
            str(found.get("sheet") or "the file")
            for found in sources
            if not found.get("key") and found.get("record") != "existing"
        }
    )
    if keyless:
        names = ", ".join(f"“{sheet}”" for sheet in keyless)
        return {
            "profileNotSaved": f"Not saved as a profile: {names} has no key, so a second load would "
            "create its rows again."
        }
    definition = {
        **definitions[-1],
        "sources": sources,
        "valueMaps": {k: v for found in definitions for k, v in (found.get("valueMaps") or {}).items()},
    }
    release = session.get(ModelRelease, change_set.model_release_id)
    key = _profile_key(session, source.name, release)
    try:
        save_for_release(session, key, source.name[:200], definition, release)
    except ApiError as error:
        return {"profileNotSaved": f"Not saved as a profile: {error.message}"}
    # The import read this layout: the next file is compared with this one's headers, however the
    # session sent the file.
    for job in jobs:
        job.parameters = {
            **job.parameters,
            "sourceFileId": source.public_id,
            "profile": {**job.parameters["profile"], "key": key},
        }
    return {"profileKey": key}


def retire_unused_releases(session: Session, task: AiTask) -> None:
    """A release the task's client installed that no workspace or change set runs is retired, as
    "exactly one release" is only a prompt (AP-D45); history may name it, so it stays."""
    if task.client_id is None:
        return
    result = task.result or {}
    kept = {
        result.get("thenReleaseId"),
        (result.get("migration") or {}).get("releaseId"),
    } - {None}
    installed = select(AuditEvent.aggregate_id).where(
        AuditEvent.aggregate_type == "model_release",
        AuditEvent.action == "installed",
        AuditEvent.actor_client_id == task.client_id,
    )
    for release in session.scalars(
        select(ModelRelease).where(
            ModelRelease.public_id.in_(installed),
            ModelRelease.public_id.not_in(kept),
            ModelRelease.status != "retired",
            ~ModelRelease.id.in_(select(WorkspaceModel.model_release_id)),
            ~ModelRelease.id.in_(select(ChangeSet.model_release_id)),
        )
    ):
        set_release_status(session, release.public_id, "retired", release.status_version)


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
