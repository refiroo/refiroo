"""Running one turn of the assistant session: starting it, the progress read from its stream, ending the
process group, recording a turn or an interruption, and the undo of a load that was cut short."""

import contextlib
import json
import logging
import os
import signal
import ssl
import stat
import subprocess
import threading
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from ....config import get_settings
from ....errors import ApiError
from ....models.database import AiCall, AuditEvent, ChangeSet, Grant, Job, ModelDraft
from ...authorization.administration import delete_grant
from ...change_sets.lifecycle import discard_change_set
from ...jobs.batches import JobCancelled
from ..store import finish, load_task, note
from .files import drop, ensure_tmp, retention
from .sandbox import (
    ResetFailed,
    SessionUserError,
    access,
    agent_root,
    as_assistant,
    base_command,
    check_network,
    close_gate,
    close_gates_of,
    container,
    loopback,
    open_gate,
    reset,
    safeguards,
    session_environment,
    slots_of,
    take_session_user,
)
from .words import CALL, LAST_LINE, PROMPT_VERSION, PROPOSAL, THEN_LINE, VOICE, without_files

log = logging.getLogger(__name__)


class SessionTimedOut(JobCancelled):
    """A turn ran longer than ``AI_AGENT_TIMEOUT_SECONDS`` (0.13 AQ). It ends as a person's Stop does
    (AP-D55): the worker stops the job as cancelled, the task goes back to its last point, and the
    task's note says the session took longer than the limit."""


class SessionLogTooLarge(Exception):
    """The session's stream log passed ``LOG_LIMIT`` bytes: the turn is stopped and fails (FX2)."""


# The most a turn's stream log may hold; the usual turn's is a few megabytes. A line is read up to
# ``LINE_LIMIT`` bytes and a longer one is skipped, so one line cannot fill the engine's memory.
LOG_LIMIT = 512 * 1024 * 1024
LINE_LIMIT = 8 * 1024 * 1024


def timeout_seconds() -> int:
    """The longest one turn of the session may take."""
    return get_settings().ai_agent_timeout_seconds


def _end(session: Session, grants: list[str]) -> None:
    """Delete the turn's grants; one already gone is no error, as the turn may end twice."""
    for grant in grants:
        if session.scalar(select(Grant.id).where(Grant.public_id == grant)) is not None:
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
        if time.monotonic() - started > timeout_seconds():
            # Through the stop path: the jobs are cancelled and a partial load is undone (R-F19).
            raise SessionTimedOut("The session's jobs took too long")
        time.sleep(2)
    session.commit()


def api_url() -> str:
    return os.environ.get("AI_AGENT_API_URL", "").strip() or get_settings().public_url


def openapi(url: str) -> bytes:
    context = ssl.create_default_context()
    if loopback(url):
        # This machine's own certificate is its own to vouch for; any other address is verified.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(f"{url}/openapi.json", context=context, timeout=30) as answer:
        return answer.read()


def _call_in_words(command: str) -> str:
    """A call in a person's words: the command itself is never shown."""
    found = CALL.search(command)
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


class Progress:
    """The session's stream as what it is doing now: read from the log, written when it moves."""

    def __init__(self, log: Path) -> None:
        self.log = log
        self.handle: Any = None
        self.position = 0
        self.now = "Starting"
        self.result: dict[str, Any] = {}
        self.model: str | None = None
        # Each message's usage by its ID, as the stream repeats a message while it grows (AP-D36).
        self.usage: dict[str, tuple[int, int]] = {}
        # Inside a line longer than ``LINE_LIMIT``, which is skipped to its end.
        self.skipping = False

    def size(self) -> int:
        """Bytes in the log now, from the descriptor it was opened as."""
        return os.fstat(self.handle.fileno()).st_size if self.handle is not None else 0

    def _open(self) -> bool:
        """The log is opened once, as a regular file and not through a link, and read through that
        descriptor: the path may be replaced by anything later."""
        if self.handle is not None:
            return True
        try:
            descriptor = os.open(self.log, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError:
            return False
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            return False
        self.handle = os.fdopen(descriptor, "r")
        return True

    def read(self) -> bool:
        if not self._open():
            return False
        moved = False
        handle = self.handle
        handle.seek(self.position)
        while True:
            line = handle.readline(LINE_LIMIT)
            if not line:
                break
            complete = line.endswith("\n")
            if not complete and len(line) < LINE_LIMIT:
                break  # a line the session is still writing
            self.position = handle.tell()
            if self.skipping or not complete:
                self.skipping = not complete
                continue
            try:
                moved = self._line(line) or moved
            except AttributeError, TypeError, KeyError:
                # The stream is another program's: a line of a shape not known only shows less.
                log.warning("A session's log line could not be read", exc_info=True)
        return moved

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None

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
        except ValueError, RecursionError:
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
                    self.now = _call_in_words(command)
                    moved = True
        return moved


def _command_of(pid: int) -> str:
    """The command line of a process, or nothing when it is gone or cannot be read: from /proc where
    there is one (the engine's image has no ``ps``), otherwise from ``ps``."""
    try:
        return (
            Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        )
    except OSError:
        pass
    try:
        shown = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return shown.stdout


def _group_alive(pid: int) -> bool:
    """Whether the process still runs: a process that ended and is not yet collected does not."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[0] != "Z"
    except OSError, IndexError:
        pass
    try:
        os.killpg(pid, 0)
    except ProcessLookupError, PermissionError:
        return False
    return True


def _stop_earlier(earlier: dict[str, Any] | None) -> None:
    """Ends a session left running by a worker that stopped: its job came back, and two sessions in
    one folder would overwrite each other. The process counts only if it still names its session,
    as its number may be another's by now. It never raises: a Stop, or a failure the turn already
    has, must reach the task as what it was. In a container the group's leader is ``sudo``, which
    the engine's user may only ask to end (it passes the request on to the session): it is asked
    first, and the group is killed if it has not ended in five seconds."""
    if not earlier:
        return
    pid = int(earlier["pid"])
    if str(earlier["session"]) not in _command_of(pid):
        return
    for signal_number, wait in ((signal.SIGTERM, 5.0), (signal.SIGKILL, 0.0)):
        try:
            os.killpg(pid, signal_number)
        except ProcessLookupError, PermissionError:
            return
        deadline = time.monotonic() + wait
        while _group_alive(pid):
            if time.monotonic() >= deadline:
                break
            time.sleep(0.1)
        else:
            return


def _reap(process: subprocess.Popen[str]) -> None:
    """Collects the session the engine just ended, so it does not stay a zombie of the engine's
    process until it exits (and is not reported as still running when its handle goes); a session
    that has not gone yet is killed first. It never raises."""
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(process.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            process.wait(timeout=5)


def provider() -> str:
    try:
        command = base_command()
    except OSError:
        # A command that cannot start is recorded as the turn's failure, under no provider's name.
        return "unknown"
    return "claude-code" if Path(command[0]).name == "claude" else Path(command[0]).name


def _record_turn(
    session: Session,
    task_id: str,
    job_id: str | None,
    progress: Progress,
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
        provider=design.get("agentProvider") or provider(),
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
    progress: Progress,
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
    progress = Progress(folder.parent / str(earlier["log"]))
    progress.read()
    progress.close()
    _record_turn(
        session,
        task_id,
        earlier.get("job"),
        progress,
        datetime.fromisoformat(earlier["startedAt"]),
        "",
        ("interrupted", "The worker stopped while the session ran."),
    )


def _folder_rule(folder: Path) -> str:
    """Where a turn's files are: the folder, and its scratch folder as ``$TMPDIR``."""
    return (
        f"Your folder is {folder} and $TMPDIR is {folder / 'tmp'}: nothing outside the folder can be "
        "read, and files an earlier turn kept elsewhere are under $TMPDIR now. Name files by a "
        "relative path or $TMPDIR, never by an absolute path elsewhere. A refused command is not the "
        "end of the turn: run it again that way."
    )


def run_turn(
    session: Session,
    job: Job,
    ctx: Any,
    task_id: str,
    folder: Path,
    prompt: str,
    session_id: str,
    *,
    first: bool,
    load: bool = False,
) -> Progress | None:
    """One turn of the session, the task's progress written as it goes; ``None`` when it could not
    start, with the reason on the task."""
    task_key = task_id
    earlier = (load_task(session, task_key).design or {}).get("agentProcess")
    _stop_earlier(earlier)
    _record_interrupted(session, task_key, folder, earlier)
    if first:
        drop(folder, PROPOSAL)
    else:
        # A resumed session keeps the habits of its earlier turns: the folder rule is said every turn,
        # with the paths, or a command naming an old scratch path is refused and the turn is lost (task 95).
        prompt = f"{prompt}\n\n{_folder_rule(folder)}"
    try:
        token, client, opened = access(session, job, load_task(session, task_key, for_update=True))
        session.commit()
    except ApiError as refused:
        session.rollback()
        task = load_task(session, task_key, for_update=True)
        note(task, "warning", refused.message)
        finish(task, "failed", retention(ctx))
        session.commit()
        return None
    # From here whatever fails ends the turn's grants (R-F5).
    try:
        return _turn(
            session, job, ctx, task_key, folder, prompt, session_id, token, client, opened,
            first=first, load=load,
        )  # fmt: skip
    except BaseException:
        session.rollback()
        _end(session, opened)
        session.commit()
        raise


def _command(
    folder: Path, prompt: str, session_id: str, first: bool, user: str | None = None
) -> list[str]:
    """The session's command. Outside a container the person's words are the last argument, after
    ``--``, so no word of them is read as an option (R-F9). In a container every process reads a
    command line, so neither the words nor the folder's path are on it: the words go to the session's
    standard input (``_turn``). The session's ID stays: a stopped worker's session is found by it."""
    command = [
        *base_command(),
        *safeguards(api_url(), folder),
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--append-system-prompt",
        VOICE,
        *(["--session-id", session_id] if first else ["--resume", session_id]),
    ]
    if not container():
        return [*command, "--", prompt]
    return [*as_assistant(user or ""), *command]


def _reset_after(user: str | None, config: Path, work: Path) -> None:
    """The reset at the end of a turn, the gate still open for its files and closed right after: a
    failure is told in the log, as the turn has its own end, and the next turn under this user starts
    with a reset of its own, whose failure it does not survive."""
    if user is None:
        return
    try:
        reset(user, config, work)
    except ResetFailed as error:
        logging.getLogger(__name__).error("%s", error)


def _feed(process: subprocess.Popen[str], prompt: str) -> None:
    """The prompt to the session's standard input, then its end. A session that ends before it has
    read it all is no failure of this."""
    try:
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()
    except OSError, ValueError:
        pass


def _turn(
    session: Session,
    job: Job,
    ctx: Any,
    task_key: str,
    folder: Path,
    prompt: str,
    session_id: str,
    token: str,
    client: int,
    opened: list[str],
    *,
    first: bool,
    load: bool,
) -> Progress | None:
    """One turn. In a container the pool user's lock and the task's open gate are held until the turn
    ends, and its user is reset after it, last of all (``holder`` is what to undo, in reverse)."""
    holder: list[Any] = []
    try:
        return _turn_as(
            session, job, ctx, task_key, folder, prompt, session_id, token, client, opened,
            first=first, load=load, holder=holder,
        )  # fmt: skip
    finally:
        for undo in reversed(holder):
            try:
                undo()
            except Exception:
                logging.getLogger(__name__).exception(
                    "Assistant task %s: the end of its turn could not be completed", task_key
                )


def _turn_as(
    session: Session,
    job: Job,
    ctx: Any,
    task_key: str,
    folder: Path,
    prompt: str,
    session_id: str,
    token: str,
    client: int,
    opened: list[str],
    *,
    first: bool,
    load: bool,
    holder: list[Any],
) -> Progress | None:
    contained = container()
    user: str | None = None
    # In a container the stream lies in the task's own folder, which only its session can find; the
    # session never needs to read it (the engine does), so it is the engine's alone.
    log = (
        folder.parent / f"session-{uuid4().hex[:8]}.log"
        if contained
        else folder.parent / f"{folder.name}.session-{uuid4().hex[:8]}.log"
    )
    progress = Progress(log)
    started = time.monotonic()
    since = datetime.now(UTC)
    # Made new and never through a link, in the engine's own folder in a container.
    with os.fdopen(
        os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "w"
    ) as output:
        try:
            config = folder.parent / "claude" if contained else None
            check_network()
            if config is not None:
                user, lock = take_session_user(slots_of(agent_root(None)))
                holder.append(lock.close)
                gate = folder.parent
                # Whatever the last turn under this user left running ends first, the gate still
                # closed; only a reset that finished lets the gate open. After the turn the reset runs
                # first, the gate still open for the user's files, and the gate closes right after it
                # (what is undone last runs first: the reset, the gate, the lock), whether the turn
                # ended well or not.
                reset(user)
                close_gates_of(agent_root(None), user)
                holder.append(lambda: close_gate(gate))
                holder.append(lambda: _reset_after(user, config, folder))
                open_gate(gate, user)
            ensure_tmp(folder)
            command = _command(folder, prompt, session_id, first, user)
            process = subprocess.Popen(
                command,
                cwd=folder,
                env=session_environment(token, folder, config),
                stdin=subprocess.PIPE if contained else subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
            if contained:
                threading.Thread(target=_feed, args=(process, prompt), daemon=True).start()
        except OSError as error:
            if isinstance(error, SessionUserError):
                logging.getLogger(__name__).error("Assistant task %s: %s", task_key, error)
            _end(session, opened)
            _record_turn(
                session,
                task_key,
                job.id,
                progress,
                since,
                prompt,
                ("failed", f"Could not start: {error}"),
            )
            task = load_task(session, task_key, for_update=True)
            note(
                task,
                "warning",
                str(error)
                if isinstance(error, SessionUserError)
                else f"AI_AGENT_COMMAND could not start: {error}",
            )
            finish(task, "failed", retention(ctx))
            session.commit()
            return None
        failure: tuple[str, str] | None = None
        try:
            task = load_task(session, task_key, for_update=True)
            held = (
                session.get(ModelDraft, task.draft_id, populate_existing=True)
                if task.draft_id is not None
                else None
            )
            task.design = {
                **(task.design or {}),
                # The draft as the turn found it: a stop tells whether the turn had changed it.
                "turnDraftVersion": held.version if held is not None else None,
                # The session has run: a later turn resumes it; one that never ran starts again.
                "agentRan": True,
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
                if time.monotonic() - started > timeout_seconds():
                    raise SessionTimedOut("The session took too long")
                moved = progress.read()
                if progress.size() > LOG_LIMIT:
                    raise SessionLogTooLarge("The session's log grew too large")
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
                # Ends the moment the session's process exits, not up to 2 s later.
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=2)
            _await_its_jobs(session, ctx, started, client)
        except BaseException as error:
            _stop_earlier({"pid": process.pid, "session": session_id})
            _reap(process)
            failure = (
                ("timeout", "The session took too long.")
                if isinstance(error, SessionTimedOut)
                else ("cancelled", "Cancelled by a person.")
                if isinstance(error, JobCancelled)
                else ("failed", "The session's log grew past its limit.")
                if isinstance(error, SessionLogTooLarge)
                else ("failed", f"The session's turn failed ({type(error).__name__}).")
            )
            raise
        finally:
            session.rollback()
            _end(session, opened)
            session.commit()
            progress.read()
            progress.close()
            # The turn is recorded whatever the undo after it does (FX2).
            try:
                if load and failure is not None and failure[0] in ("cancelled", "timeout"):
                    _undo_load(session, task_key, client, since)
                if failure is not None and failure[0] == "timeout":
                    # One line, no traceback: the limit is an expected ending, not a fault (0.13 AQ).
                    logging.getLogger(__name__).warning(
                        "Assistant task %s: the session ran longer than %s seconds and was stopped",
                        task_key,
                        timeout_seconds(),
                    )
                    held = load_task(session, task_key, for_update=True)
                    held.design = {**(held.design or {}), "timedOut": timeout_seconds()}
                    session.commit()
                if failure is None and (not progress.result or progress.result.get("is_error")):
                    failure = ("failed", "The session ended without an answer.")
                if failure is not None and failure[0] == "failed":
                    # A turn that failed after the session made a change set (a correction of a load)
                    # leaves it with no task to link it. A failed load stage keeps a set that holds
                    # changes reachable (recover_load); the other turns undo what they began (0.13
                    # DOC11 F8).
                    if load:
                        _discard_empty_sets(session, client, since)
                    else:
                        _undo_load(session, task_key, client, since)
            except BaseException:
                session.rollback()
                raise
            finally:
                _record_turn(session, task_key, job.id, progress, since, prompt, failure)
                _log_split(session, task_key, client, since, started, progress)
    return progress


UNDO_SECONDS = 60


def _undo_load(session: Session, task_id: str, client: int, since: datetime) -> None:
    """The person stopped a load (AP-D55): what the session's client began in it is stopped, and the
    change sets it made in this turn are discarded, so the task returns to the accepted proposal
    with nothing loaded. A job still running after a minute is said, not forced."""
    session.execute(
        update(Job)
        .where(
            Job.requested_by_client_id == client,
            Job.kind != "aiTask",
            Job.state.in_(("queued", "running")),
        )
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    session.commit()
    waiting = select(Job.id).where(
        Job.requested_by_client_id == client,
        Job.kind != "aiTask",
        Job.state.in_(("queued", "running")),
    )
    deadline = time.monotonic() + UNDO_SECONDS
    while session.scalar(waiting.limit(1)) is not None and time.monotonic() < deadline:
        session.commit()
        time.sleep(1)
    session.commit()
    if session.scalar(waiting.limit(1)) is not None:
        note(
            load_task(session, task_id, for_update=True),
            "warning",
            "A job the assistant started was still running when you stopped it: discard its change set from the "
            "change sets list when it ends.",
        )
        task = load_task(session, task_id, for_update=True)
        # Said by the stop: what it had loaded was not undone (R-F21).
        task.design = {**(task.design or {}), "undoSkipped": True}
        session.commit()
        return
    for change_set in session.scalars(
        select(ChangeSet).where(
            ChangeSet.created_by_client_id == client, ChangeSet.created_at >= since
        )
    ).all():
        discard_change_set(session, change_set.id, change_set.version)


def _discard_empty_sets(session: Session, client: int, since: datetime) -> None:
    """The change sets the session's client made in a turn that failed and left empty: nothing in
    them is worth keeping, and no task would link them. Not while a job of the client still runs."""
    running = select(Job.id).where(
        Job.requested_by_client_id == client,
        Job.kind != "aiTask",
        Job.state.in_(("queued", "running")),
    )
    if session.scalar(running.limit(1)) is not None:
        return
    for change_set in session.scalars(
        select(ChangeSet).where(
            ChangeSet.created_by_client_id == client, ChangeSet.created_at >= since
        )
    ).all():
        if not holds_changes(counts_of(session, change_set.id)):
            discard_change_set(session, change_set.id, change_set.version)
    session.commit()


def undo_interrupted_load(session: Session, task_id: str) -> None:
    """A load turn whose worker stopped is run again: what it began is stopped and undone first, so
    the change set it made does not stay beside the new one (R-F18)."""
    task = load_task(session, task_id)
    earlier = (task.design or {}).get("agentProcess")
    if not earlier or task.client_id is None or not earlier.get("startedAt"):
        return
    _stop_earlier(earlier)
    _undo_load(session, task_id, task.client_id, datetime.fromisoformat(earlier["startedAt"]))


def closing_words(progress: Progress) -> str:
    result = progress.result
    cost = result.get("total_cost_usd")
    seconds = round((result.get("duration_ms") or 0) / 1000)
    # The closing lines carry ids for the engine; the person reads the rest.
    words = "\n".join(
        without_files(line)
        for line in str(result.get("result") or "").splitlines()
        if LAST_LINE not in line and THEN_LINE not in line
    ).strip()
    return f"{words[:6000]} ({seconds} s" + (f", ${cost:.2f})" if cost else ")")


def counts_of(session: Session, change_set_id: str) -> dict[str, int]:
    """What the change set holds, as a load's counts: new, changed and removed records, and new,
    changed and removed relationships (a load that only links records is a load)."""
    created, updated, deleted = session.execute(
        text(
            "SELECT count(*) FILTER (WHERE NOT c.is_deleted AND o.id IS NULL),"
            " count(*) FILTER (WHERE NOT c.is_deleted AND o.id IS NOT NULL),"
            " count(*) FILTER (WHERE c.is_deleted)"
            " FROM change_set_objects c LEFT JOIN objects o ON o.id = c.object_id"
            " WHERE c.change_set_id = :id"
        ),
        {"id": change_set_id},
    ).one()
    linked, relinked, unlinked = session.execute(
        text(
            "SELECT count(*) FILTER (WHERE NOT c.is_deleted AND r.id IS NULL),"
            " count(*) FILTER (WHERE NOT c.is_deleted AND r.id IS NOT NULL),"
            " count(*) FILTER (WHERE c.is_deleted)"
            " FROM change_set_relations c LEFT JOIN object_relations r ON r.id = c.relation_id"
            " WHERE c.change_set_id = :id"
        ),
        {"id": change_set_id},
    ).one()
    return {
        "applied": created + updated,
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "relationsCreated": linked,
        "relationsUpdated": relinked,
        "relationsRemoved": unlinked,
        "unchanged": 0,
        "rejected": 0,
    }


def holds_changes(counts: dict[str, int]) -> bool:
    """Whether the change set holds a change of any kind, records or relationships."""
    keys = (
        "created",
        "updated",
        "deleted",
        "relationsCreated",
        "relationsUpdated",
        "relationsRemoved",
    )
    return any(counts[key] for key in keys)
