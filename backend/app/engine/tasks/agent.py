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

import ipaddress
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

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from ...config import get_settings
from ...errors import ApiError, api_error
from ...models.commands import GrantCreate, GrantPrincipal, GrantScope, RoleCreate
from ...models.database import (
    AiCall,
    AiTask,
    AuditEvent,
    AuthorizationState,
    ChangeSet,
    Grant,
    ImportProfile,
    Job,
    ModelDraft,
    ModelRelease,
    OAuthClient,
    Role,
    SourceFile,
    WorkspaceModel,
)
from ..authorization.administration import create_grant, create_role, delete_grant, groups_of
from ..authorization.permissions import permissions_of
from ..change_sets.lifecycle import discard_change_set
from ..identity import tokens
from ..identity.clients import create_session_client, retire_session_client
from ..identity.settings import IdentitySettings
from ..imports.profiles import model_key_of, save_for_release
from ..jobs.batches import JobCancelled
from ..model.authoring.draft_migration import derive
from ..model.compiler import parse_model
from ..model.consumer_contract import contract_diagnostics, raised_contracts
from ..model.diagnostics import ModelValidationError
from ..model.migrations import LandingRefusal, Mappings, check_landing, plan_migration
from ..model.release_lifecycle import set_release_status
from ..model.workspace_models import load_assignment
from .cell_coverage import cells_left_out
from .store import finish, held_by_another, held_counts, load_task, note

log = logging.getLogger(__name__)

PROMPT_VERSION = "agent/18"
LAST_LINE = "CHANGE_SET:"
THEN_LINE = "THEN_RELEASE:"
RELEASE_LINE = "RELEASE:"
DEFAULT_WORDS = "Create a model for this or map it to the current model, and import it."
PROPOSAL = "proposal.json"
_CALL = re.compile(r"(?:-X\s*(GET|POST|PUT|PATCH|DELETE)\b[^\n]*?)?/api/v1/([A-Za-z0-9_\-/{}$.]+)")


class SessionTimedOut(JobCancelled):
    """A turn ran longer than ``AI_AGENT_TIMEOUT_SECONDS`` (0.13 AQ). It ends as a person's Stop does
    (AP-D55): the worker stops the job as cancelled, the task goes back to its last point, and the
    task's note says the session took longer than the limit."""


def timeout_seconds() -> int:
    """The longest one turn of the session may take."""
    return get_settings().ai_agent_timeout_seconds


def enabled() -> bool:
    return bool(os.environ.get("AI_AGENT_COMMAND", "").strip())


def _loopback(url: str) -> bool:
    """Whether the API is reached on this machine, where a certificate of its own is no risk (R-F8)."""
    host = urlparse(url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _connection(workspace: str, url: str, *, workbook: bool = True) -> str:
    file = (
        "workbook.xlsx is the file, "
        if workbook
        else "There is no file: the words are about the stored records. "
    )
    data = "The data comes from this workbook alone. " if workbook else ""
    return (
        f"{file}model.json the workspace's model, openapi.json the API of the "
        f"engine at {url}, with the header 'Authorization: Bearer $REFIROO_TOKEN' (curl{' -k' if _loopback(url) else ''} --noproxy ''). "
        "The network is reached with curl: Python cannot open a socket in the sandbox. The "
        "language of a model is components.schemas.EngineModel in openapi.json. Keep every file "
        "you make in this folder ($TMPDIR is in it) and name it by a relative path: nothing outside "
        "the folder can be read. A refused command is not the end of the turn: run it again that way. "
        f"{data}Work only in the workspace {workspace}: no other "
        "workspace is read or changed. Where the data gives one thing two names or values, that "
        "is intended: keep them all as they are, correct nothing and do not keep only the most "
        "common; say it in one line of the summary, never as a question."
    )


def _starting_point(held: dict[str, int]) -> str:
    """Whether the session adds to the model or may start anew: what the workspace holds decides."""
    total = sum(held.values())
    if total:
        return (
            f"The workspace holds {total} records in all its applications together: keep its model "
            "and add to it, unless the words ask otherwise."
        )
    return (
        "The workspace holds no records: if the words ask for a model, it may be a new one with "
        "only what this needs."
    )


_SHAPE = (
    "What the file repeats across columns or rows becomes types of its own, related to each other, "
    "unless the words ask otherwise; if you keep such a repetition flat, say so in one line of the "
    "summary."
)


_ITEMS = (
    "Load the file as the engine's batch items, not as an import profile: read the workbook in Python "
    "(layout, hidden rows and columns, blocks shifted against each other, notes), read the model and "
    "the workspace's records through the API, and change the draft where the file needs it. Write a "
    "script in your folder that turns the file into items (openapi.json, POST /batches; items only: "
    "send no batch and write nothing live): every new record gets an id you generate (uuid4) so later "
    "items can point to it; an existing record is found by reading the workspace's records and named by "
    "its ID; give each item a ref naming the cells it comes from, as Sheet!Q31:S31. Send the items to "
    "POST /model-drafts/{id}/dry-run as {workspaceKey, items} (no sourceFileId, no profile), read "
    "GET /model-drafts/{id}/dry-run until it completes, and read its items summary (per type: new, "
    "matched, changed, refused; the relationships; examples with their refs; the findings). Fix your "
    "items or the draft until nothing is refused and every finding is explained, then write the "
    "proposal. What you sent last is exactly what is loaded when the person accepts. An empty cell is "
    "no value: never call its row skipped or left out."
)


_QUESTIONS = (
    "Ask a question only about what the file and the words leave open, in the person's terms (what "
    "ends up in their data), the question first and each option an outcome, with the answer you "
    "assumed already in the draft and the items; never about the engine or how to load. What the data "
    "gives as it is (two names for one thing, likely typos, a repetition kept flat) and the findings "
    "are one line of the summary, never a question. The kinds of draft operation are in openapi.json."
)


_RECORDS = (
    "A record changes type and keeps its ID, values, relationships and history through a change set's "
    "restructurings or, for every record of a type, through the proposal's moves; creating new "
    "records and removing the old ones loses them. A consumer API that exposes a type the proposal "
    "moves or removes needs its contractVersion raised in the draft, and its definition to expose the "
    "new type where it exposed the old one: the engine refuses the release otherwise. A type that "
    "merges others must give their records the places they have now, their parents and "
    "relationships, or the engine refuses to move them; a migration creates no records."
)


_PARTIAL = (
    "When the words move only some of a type's records to other types, that is a partial move: put "
    "the final model in the draft, say so in the summary, and stage nothing now. Accepting is what "
    "prepares it, as steps the person takes: a release holding the final model with the old types "
    "beside it, a change set that restructures those records for review, and the release that "
    "removes the emptied types. Never tell the person to prepare a release or to restructure "
    "records by hand."
)


_WORDS = (
    "Build everything the words ask for, as they place it, also what the file has no data for (an "
    "empty type): the words go before the file's shape, and a question does not replace building. "
    "What the words name as a group holds its members as records under it; a field's candidate "
    "filter can name that group by a fixed value of an ancestor (ancestor:<type>.<field>). Say a "
    "thing cannot be built only after trying it on the draft."
)


_OWN_DRAFT = (
    "made with POST /model-drafts (name, model, and baseReleaseId the releaseId that "
    "GET /workspaces/{key}/model answers); never open the workspace's own draft (POST /workspaces/{key}/model/draft) and never "
    "use or change a draft you did not make, since it is a person's; on a later turn keep using "
    "the draft you made"
)


def _propose_prompt(
    words: str | None, workspace: str, url: str, held: dict[str, int], *, workbook: bool = True
) -> str:
    check = (
        f"Build the model in a model draft of your own, {_OWN_DRAFT}, and check what you load with "
        "the draft's dry run"
        if workbook
        else f"Put any model change the words need in a model draft of your own, {_OWN_DRAFT}; if "
        "the model does not change, make no draft and write draftId null. Work out every record the words touch, and write "
        "in the summary the change as what to do, in terms of the records; stage no change set"
    )
    return (
        f"{(words or '').strip() or DEFAULT_WORDS}\n\n"
        f"{_connection(workspace, url, workbook=workbook)} {_starting_point(held)} "
        f"{_WORDS} {_RECORDS} {_PARTIAL} {_SHAPE + ' ' + _ITEMS + ' ' + _QUESTIONS + ' ' if workbook else ''}{check}; install, "
        "activate, load and publish nothing yet: the person reviews first. Then write "
        f'{PROPOSAL}: {{"draftId": {"..." if workbook else "... (null when the model does not change)"}, "summary": two sentences a person reads, "questions": '
        '[{"text": the question itself first, at most three short sentences, "options", "assumed"}] '
        'for what only a person can decide, "moves": '
        '[{"from": a type key, "to": its type key in the draft, "attributes": [{"attributeTypeKey", '
        '"from"}]}] only for a whole type that becomes another, kept in order, "removals": '
        '[{"kind": "objectType", "application", "attribute" or "relationType", "key", "objectType" '
        '(the type that holds the field, for an attribute), "words": the person\'s own words that ask '
        "for it; for a type whose records the change set restructures into other types, also "
        "\"movedTo\": those types' keys}] listing only what the person's words explicitly ask "
        "to remove, quoted, never "
        "something you decided to drop: every other record, value, relationship and translation must "
        "come through, and a change that would lose any of them is not offered}."
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
    f"on that release, do not publish it, and end with the line {LAST_LINE} <its id>.{_PART} If "
    "the words ask nothing of the stored records (no workbook rows, no record changes), the model "
    "alone changes: install exactly one new release, do not activate it, make no change set, and "
    f"end with the line {RELEASE_LINE} <its id>."
)


_ACCEPTED_UNCHANGED = (
    "The person accepted. The model does not change: install no release and activate none. Make the "
    "change the words ask of the stored records in a new change set on the workspace's current live "
    "release (source currentLive), do not publish it, and end with the line "
    f"{LAST_LINE} <its id>."
)


_MOVED = (
    "The person accepted. They may have edited the draft in the model editor: read it again. Install "
    "it as exactly one new release and do not activate it, and end with the line "
    f"{RELEASE_LINE} <its id>. The records of the proposal's moves are moved by a migration the "
    "person confirms: do not move or create them."
)


def _again(prompt: str, words: str | None) -> str:
    """The load prompt of a second try: the person's words, and that what was loaded before is gone
    (a failed load, or a change set the person discarded to say this)."""
    if not words:
        return prompt
    return (
        f"{prompt}\n\nThe person adds:\n{words}\n\nWhat you loaded before, if anything, failed or was "
        "discarded: do the load again from the start, changing the draft first if the words ask for it."
    )


def _said_prompt(said: str) -> str:
    return (
        f"The person says:\n{said}\n\nThey may have edited the draft in the model editor: read it "
        f"again. Change the draft as they say (if the model does not change, there is none: change the "
        f"proposal as they say), check the records again (send the items to the dry run again) and "
        f"write {PROPOSAL} again."
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
    """The role the session's grants name, made once. Administration may edit a custom role, so its
    groups are checked on every use: a role changed from what the engine made refuses the turn (R-F6)."""
    found = session.scalar(select(Role).where(Role.name == name))
    if found is None:
        found = create_role(session, RoleCreate(name=name, actionGroups=groups))
    if set(groups_of(session, found)) != set(groups):
        raise api_error(
            409,
            "AI_ASSISTANT_ROLE_CHANGED",
            f"The role '{name}' no longer holds exactly {', '.join(groups)}, so the assistant "
            "was not started. Restore the role's action groups, or delete the role (it is made "
            "again), and try again.",
        )
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
    # A grant left by a turn that ended without its cleanup is not this turn's to keep (R-F5).
    for left in session.scalars(select(Grant.public_id).where(Grant.client_id == client.id)).all():
        delete_grant(session, left)
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
            create_grant(
                session, GrantCreate(principal=principal, role=role, scope=scope)
            ).grant.public_id
        )
    if asked.allows("model-authoring", None) and (
        asked.allows("model-release", workspace) or asked.allows("model-install", None)
    ):
        model = _role(session, MODEL_ROLE, MODEL_GROUPS)
        grants.append(
            create_grant(
                session,
                GrantCreate(principal=principal, role=model, scope=GrantScope(instance=True)),
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


ASSISTANT_USER = "assistant"


def _container() -> bool:
    """In a container the container is the boundary: Claude Code's own sandbox cannot run inside it."""
    return os.environ.get("AI_AGENT_SANDBOX", "").strip().lower() == "container"


def _as_assistant() -> list[str]:
    """In a container the session runs as a user of its own, which cannot read the engine's
    environment or its job files (R-F45). ``sudo`` resets the environment and keeps only the names the
    image's sudoers rule lists; the token is passed that way and not on the command line, which any
    process of the container can read."""
    return ["sudo", "-n", "-u", ASSISTANT_USER, "--"]


def _agent_root(files: Any) -> Path:
    """Where the sessions' folders are. In a container they cannot lie in the job files, which only
    the engine's user may enter: they lie in a folder shared by the group of the two users."""
    if _container():
        return Path(
            os.environ.get("AI_AGENT_FOLDERS", "").strip()
            or "/opt/refiroo/rdm-engine/data/assistant"
        )
    return Path(files.directory) / "agent"


def _share(path: Path, mode: int) -> None:
    """In a container the session's user, of the engine's group, may read and write it."""
    if _container():
        os.chmod(path, mode)


def _safeguards(url: str, folder: Path) -> list[str]:
    """What the session may touch, whatever its command says: its tools, its folder, and this
    engine on the network. The sandbox is the operating system's, so a script it writes is held too;
    a machine where it cannot run refuses to start the session."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    # In a container the container is the boundary: the sandbox's own isolation cannot run inside it.
    contained = _container()
    settings = {
        "sandbox": {
            "enabled": not contained,
            "failIfUnavailable": not contained,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": True,
            "filesystem": {"denyRead": ["~/"], "allowRead": [str(folder), sys.prefix]},
            "network": {"allowedDomains": [host, f"{host}{port}"]},
        },
    }
    # Claude Code's read block refuses any command that expands a variable inside a compound command
    # (a loop, `&&`, a pipe), `$REFIROO_TOKEN` in the Authorization header among them. Outside a
    # container the operating system's sandbox is the boundary for reads and the block stays; in a
    # container the `assistant` user is, and the block only ended sessions early.
    if not contained:
        settings["permissions"] = {"blockReadsOutsideWorkingDirectories": True}
    # Outside a container the operating system's sandbox auto-approves Bash, so Claude Code runs
    # restricted and in don't-ask mode. In a container the sandbox is off, and don't-ask mode then
    # refuses every compound or multi-line command even though Bash is allowed. There the
    # session runs with Claude Code's permission prompts off (bypassPermissions, which --restricted
    # refuses) and the separate `assistant` user is the boundary (0.16 R-F45). User, project and
    # local settings files stay ignored, as --restricted did, by loading no setting sources.
    mode = (
        ["--setting-sources", "", "--permission-mode", "bypassPermissions"]
        if contained
        else ["--restricted", "--permission-mode", "dontAsk"]
    )
    return [
        *mode,
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
        "--settings",
        json.dumps(settings),
    ]


# Of the server's environment, only what Claude Code itself needs: never its database or secrets.
PASSED = re.compile(
    r"^(HOME|USER|LANG|LC_\w+|TMPDIR|SHELL|ANTHROPIC_\w+|CLAUDE_\w+|AWS_\w+|NODE_\w+)$"
)


def _session_environment(token: str, folder: Path | None = None) -> dict[str, str]:
    """What the session's process sees. Its scratch folder (``TMPDIR``) lies inside its own folder:
    a session that kept files in the machine's scratch folder had its next turn's command refused for
    reading outside its folder, and the task failed (task 95)."""
    scratch: dict[str, str] = {}
    if folder is not None:
        temporary = folder / "tmp"
        temporary.mkdir(exist_ok=True)
        _share(temporary, 0o2770)
        scratch["TMPDIR"] = str(temporary)
    return {
        **{name: value for name, value in os.environ.items() if PASSED.match(name)},
        **scratch,
        "REFIROO_TOKEN": token,
        "PATH": f"{Path(sys.prefix) / 'bin'}:{os.environ.get('PATH', '')}",
    }


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


def _api_url() -> str:
    return os.environ.get("AI_AGENT_API_URL", "").strip() or get_settings().public_url


def _openapi(url: str) -> bytes:
    context = ssl.create_default_context()
    if _loopback(url):
        # This machine's own certificate is its own to vouch for; any other address is verified.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(f"{url}/openapi.json", context=context, timeout=30) as answer:
        return answer.read()


def resumable(files: Any, task: AiTask) -> bool:
    """Whether the task's session left a transcript Claude Code can resume. A session ended before
    it wrote one (a Stop in the first seconds) has nothing to go on from: its next turn starts
    again (0.13 DOC11 13)."""
    session_id = (task.design or {}).get("agentSession")
    if not session_id:
        return False
    if not os.environ.get("CLAUDE_CONFIG_DIR", "").strip():
        # Where Claude Code keeps transcripts is not this engine's to say (the image sets it).
        return True
    transcript = _transcripts() / _transcript_name(folder_of(files, task)) / f"{session_id}.jsonl"
    return transcript.exists()


def folder_of(ctx_files: Any, task: AiTask) -> Path:
    return _agent_root(ctx_files) / task.public_id


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
    if (
        (task.design or {}).get("agentSession")
        and _transcripts().is_dir()
        and not transcript.is_dir()
    ):
        log.warning("No transcript at %s for task %s", transcript, task.public_id)
    shutil.rmtree(folder, ignore_errors=True)
    shutil.rmtree(transcript, ignore_errors=True)
    for log_file in folder.parent.glob(f"{folder.name}.*.log"):
        log_file.unlink(missing_ok=True)


def sweep(session: Session, files: Any) -> None:
    """What no task holds any more: the folder of a task that expired, and a transcript of this
    instance's folders whose folder is gone (AP-D37). Removed after the expiry's commit."""
    root = _agent_root(files)
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


def _call_in_words(command: str) -> str:
    """A call in a person's words: the command itself is never shown."""
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
                except AttributeError, TypeError, KeyError:
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


def _folder_rule(folder: Path) -> str:
    """Where a turn's files are: the folder, and its scratch folder as ``$TMPDIR``."""
    return (
        f"Your folder is {folder} and $TMPDIR is {folder / 'tmp'}: nothing outside the folder can be "
        "read, and files an earlier turn kept elsewhere are under $TMPDIR now. Name files by a "
        "relative path or $TMPDIR, never by an absolute path elsewhere. A refused command is not the "
        "end of the turn: run it again that way."
    )


def _run_turn(
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
) -> _Progress | None:
    """One turn of the session, the task's progress written as it goes; ``None`` when it could not
    start, with the reason on the task."""
    task_key = task_id
    earlier = (load_task(session, task_key).design or {}).get("agentProcess")
    _stop_earlier(earlier)
    _record_interrupted(session, task_key, folder, earlier)
    if first:
        (folder / PROPOSAL).unlink(missing_ok=True)
    else:
        # A resumed session keeps the habits of its earlier turns: the folder rule is said every turn,
        # with the paths, or a command naming an old scratch path is refused and the turn is lost (task 95).
        prompt = f"{prompt}\n\n{_folder_rule(folder)}"
    try:
        token, client, opened = _access(session, job, load_task(session, task_key, for_update=True))
        session.commit()
    except ApiError as refused:
        session.rollback()
        task = load_task(session, task_key, for_update=True)
        note(task, "warning", refused.message)
        finish(task, "failed", _retention(ctx))
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


_VOICE = (
    "Your messages are shown to the person in the app. Write them in the person's terms: the model, "
    "its types and fields, the records and the change. Never name files (such as proposal.json), JSON "
    "keys or lists (such as draftId, moves, removals or movedTo: say what they hold, in words), ids, "
    "endpoints or commands, except the closing lines the instructions "
    f"ask for ({LAST_LINE} and {THEN_LINE}). Every count you give says plainly what it counts, so "
    "nobody can read it as something else: the records the change touches are counted for the "
    'types, lists or applications it touches, named (such as "the 179 records of the 20 lists that '
    'move"), and the rest of the workspace, if you mention it, is said apart (such as "the other '
    "4478 records of the workspace are not touched\"). Never give the workspace's total as if it "
    "were the size of the change."
)


def _command(folder: Path, prompt: str, session_id: str, first: bool) -> list[str]:
    """The session's command. The person's words are the last argument, after ``--``, so no word
    of them is read as an option (R-F9)."""
    command = [
        *_base_command(),
        *_safeguards(_api_url(), folder),
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--append-system-prompt",
        _VOICE,
        *(["--session-id", session_id] if first else ["--resume", session_id]),
        "--",
        prompt,
    ]
    return [*_as_assistant(), *command] if _container() else command


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
) -> _Progress | None:
    command = _command(folder, prompt, session_id, first)
    log = folder.parent / f"{folder.name}.session-{uuid4().hex[:8]}.log"
    progress = _Progress(log)
    started = time.monotonic()
    since = datetime.now(UTC)
    with log.open("w") as output:
        try:
            process = subprocess.Popen(
                command,
                cwd=folder,
                env=_session_environment(token, folder),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
            )
        except OSError as error:
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
            note(task, "warning", f"AI_AGENT_COMMAND could not start: {error}")
            finish(task, "failed", _retention(ctx))
            session.commit()
            return None
        failure: tuple[str, str] | None = None
        try:
            task = load_task(session, task_key, for_update=True)
            held = session.get(ModelDraft, task.draft_id) if task.draft_id is not None else None
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
                if isinstance(error, SessionTimedOut)
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
        if not _holds_changes(_counts(session, change_set.id)):
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


# The proposal file's own vocabulary: a sentence that names one of its keys or lists is the
# session talking about its file, not about the person's data.
_INTERNAL = re.compile(
    r"\b(draftId|movedTo|changeSetId|releaseId|thenReleaseId)\b"
    r"|\b(moves|removals|questions)\s+(list|entry|entries|array|field)\b"
    r"|\b(list|entry|entries)\s+of\s+(moves|removals)\b",
    re.IGNORECASE,
)


def _without_files(line: str) -> str:
    """A line of the session's closing words without the sentences that name its own file: the
    person reads the proposal on the page, not in a folder they cannot open."""
    sentences = re.split(r"(?<=[.!?])\s+", line)
    return " ".join(s for s in sentences if PROPOSAL not in s and not _INTERNAL.search(s))


def _said(progress: _Progress) -> str:
    result = progress.result
    cost = result.get("total_cost_usd")
    seconds = round((result.get("duration_ms") or 0) / 1000)
    # The closing lines carry ids for the engine; the person reads the rest.
    words = "\n".join(
        _without_files(line)
        for line in str(result.get("result") or "").splitlines()
        if LAST_LINE not in line and THEN_LINE not in line
    ).strip()
    return f"{words[:6000]} ({seconds} s" + (f", ${cost:.2f})" if cost else ")")


def _retention(_ctx: Any) -> int:
    return get_settings().ai_task_retention_days


def _plural(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def _binding(found: dict[str, Any]) -> tuple[bool, bool, str]:
    """What of an attribute binding is meaning, not form: required, read-only and the screen hints
    (a missing value reads as the default; the order of the list is not a change)."""
    return (
        bool(found.get("required")),
        bool(found.get("readOnly")),
        json.dumps(found.get("ui") or {}, sort_keys=True),
    )


def _attribute_changes(
    names: dict[str, Any], attributes: list[dict[str, Any]], earlier: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    """The attributes a type gains, loses and has changed (named), comparing meaning only."""
    now = {b.get("attributeTypeKey"): _binding(b) for b in attributes}
    was = {b.get("attributeTypeKey"): _binding(b) for b in earlier.get("attributes") or []}

    def label(keys: list[Any]) -> list[str]:
        return [str(names.get(k) or k) for k in keys]

    return (
        label([k for k in now if k not in was]),
        label([k for k in was if k not in now]),
        label([k for k in now if k in was and now[k] != was[k]]),
    )


def _shape(
    model: dict[str, Any], base: dict[str, Any], records: dict[str, int]
) -> list[dict[str, Any]]:
    """The proposal's shape from the draft and its dry run, not from the session's account: each type
    it adds, changes or loads, with its attributes and the records the check would write. A type is
    changed only when its attributes differ in meaning (added, removed, required or read-only), and
    the entry says which."""
    before = {found.get("key"): found for found in base.get("objectTypes") or []}
    names = {a.get("key"): a.get("name") or a.get("key") for a in model.get("attributeTypes") or []}
    shape = []
    for found in model.get("objectTypes") or []:
        key = found.get("key")
        attributes = found.get("attributes") or []
        earlier = before.get(key)
        change: str | None = None
        if earlier is None:
            change = "New type"
        else:
            added, removed, altered = _attribute_changes(names, attributes, earlier)
            said = [
                *([f"adds {', '.join(added)}"] if added else []),
                *([f"drops {', '.join(removed)}"] if removed else []),
                *([f"changes how {', '.join(altered)} is filled in"] if altered else []),
            ]
            if said:
                change = f"Changed type ({'; '.join(said)})"
        written = records.get(key, 0)
        if change is None and not written:
            continue
        parts = [*([change] if change else []), _plural(len(attributes), "attribute")]
        if written:
            parts.append(_plural(written, "record"))
        shape.append(
            {"objectTypeKey": key, "name": found.get("name") or key, "text": ", ".join(parts)}
        )
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
    gone = [
        f"{names.get(key) or key} ({count:,})"
        for key, count in sorted(held.items())
        if key not in kept
    ]
    if not gone:
        return []
    return [
        {
            "id": "types-left-out",
            "kind": "leftOut",
            "text": "This model leaves out types the workspace holds records of: "
            + ", ".join(gone),
            "open": True,
        }
    ]


def _cells_left_out(session: Session, task: AiTask, job_id: str | None) -> list[dict[str, Any]]:
    """Filled cells of the tables the design reads that no source of it covers (AP13): said before
    the person accepts, whatever the session said, as a column the profile cannot name is no error."""
    job = session.scalar(select(Job).where(Job.id == job_id)) if job_id else None
    if job is None or not (task.reading or {}).get("tables"):
        return []
    definition = (job.parameters.get("profile") or {}).get("definition")
    file_id = session.scalar(
        select(SourceFile.id).where(SourceFile.public_id == job.parameters.get("sourceFileId"))
    )
    if not definition or file_id is None:
        return []
    return [
        {
            "id": f"cells-left-out:{found['sheet']}",
            "kind": "cellsLeftOut",
            "text": f"{found['count']:,} filled cells of “{found['sheet']}” are read by no source of this "
            f"design (for example {', '.join(found['cells'])}): what they hold is not loaded",
            "open": True,
        }
        for found in cells_left_out(
            session, file_id=file_id, tables=task.reading["tables"], profile=definition
        )
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


_EXTRA_MAPPINGS = ("relationTypeMappings", "splits", "listConversions")


def _migration_of(
    session: Session,
    workspace_key: str,
    draft: ModelDraft | None,
    against: ModelRelease,
    to: ModelRelease | None,
    requested: list[dict[str, Any]],
) -> dict[str, Any]:
    """The migration the task hands over: what the draft states against the workspace's release (the
    engine's own ``derive``: application moves, relation type mappings, splits and list conversions
    as well as the types that become others) joined with the session's explicit ``moves``. A session
    move for a type is that type's mapping, keeping the application the draft sends it to; no type
    is mapped twice. ``notes`` are the engine's, such as that a step replaced the whole model."""
    found = (
        derive(session, draft, workspace_key=workspace_key, against=against, to=to)
        if draft is not None
        else {}
    )
    merged = {item["fromObjectTypeKey"]: dict(item) for item in found.get("typeMappings") or []}
    for move in requested:
        derived = merged.get(move["fromObjectTypeKey"], {})
        merged[move["fromObjectTypeKey"]] = {
            **derived,
            **move,
            "attributes": move.get("attributes") or derived.get("attributes") or [],
        }
    return {
        "typeMappings": list(merged.values()),
        **{name: list(found.get(name) or []) for name in _EXTRA_MAPPINGS},
        "notes": list(found.get("notes") or []),
    }


def _extra_of(migration: dict[str, Any]) -> dict[str, Any]:
    """The mappings beside the types, as the migration's request and its landing check take them."""
    return {name: migration[name] for name in _EXTRA_MAPPINGS if migration.get(name)}


def _planned_moves(
    migration: dict[str, Any],
    base: dict[str, Any],
    model: dict[str, Any],
    held: dict[str, int],
    losses: dict[str, dict[str, int]] | None = None,
    requested: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """What the migration would do, checked against the draft by the migration's own plan (AP-D47):
    each type mapping with the records the workspace holds of the type, and the application its
    records go to. A mapping the plan refuses raises its ``ApiError``; a model that does not
    compile, ``ModelValidationError``."""
    mappings = migration["typeMappings"]
    if not mappings and not _extra_of(migration):
        return []
    parsed = Mappings.of({"typeMappings": mappings, **_extra_of(migration)})
    plan_migration(
        parse_model(base), parse_model(model), parsed.types, parsed.relations, parsed.spawns
    )
    old = {found.get("key"): found.get("name") for found in base.get("objectTypes") or []}
    new = {found.get("key"): found.get("name") for found in model.get("objectTypes") or []}
    apps = {found.get("key"): found.get("name") for found in model.get("applications") or []}
    return [
        {
            "from": move["fromObjectTypeKey"],
            "fromName": old.get(move["fromObjectTypeKey"]) or move["fromObjectTypeKey"],
            "to": move["toObjectTypeKey"],
            "toName": new.get(move["toObjectTypeKey"]) or move["toObjectTypeKey"],
            "records": held.get(move["fromObjectTypeKey"], 0),
            "attributes": move["attributes"],
            "lost": (losses or {}).get(move["fromObjectTypeKey"], {}),
            "fromSession": move["fromObjectTypeKey"] in requested,
            **(
                {
                    "toApplication": move["toApplicationKey"],
                    "toApplicationName": apps.get(move["toApplicationKey"])
                    or move["toApplicationKey"],
                }
                if move.get("toApplicationKey")
                else {}
            ),
        }
        for move in mappings
    ]


def _contract_errors(base: dict[str, Any], model: dict[str, Any]) -> list[Any]:
    """What the draft breaks for the consumers of the workspace's model, which the migration's preview
    and an activation refuse (C-D17): the errors of the contract diagnostics."""
    return [
        found
        for found in contract_diagnostics(parse_model(base), parse_model(model))
        if found.severity == "error"
    ]


def _contract_words(errors: list[Any]) -> str:
    return "; ".join(found.message for found in errors)


def _contract_prompt(errors: list[Any]) -> str:
    return (
        "The engine refuses the draft for the consumers of the workspace's model: "
        f"{_contract_words(errors)}. Raise the contractVersion of each consumer API named, and make "
        "its definition expose the new type where it exposed a type the proposal moves or removes. "
        f"Check the draft again and write {PROPOSAL} again."
    )


def _not_its_draft_prompt() -> str:
    return (
        "The draft in your proposal is not one you made, so it is a person's and you may not "
        "propose, use or change it. Make your own model draft with POST /model-drafts (name, model, "
        "and baseReleaseId the releaseId that GET "
        "/workspaces/{key}/model answers), build the model in it, check it "
        f"with the draft's dry run, and write {PROPOSAL} again naming that draft."
    )


def _refusal_words(refusals: tuple[LandingRefusal, ...], names: dict[str, str]) -> str:
    """The engine's refusals with their counts per type and a few example records."""
    return "; ".join(
        f"{found.code}: {found.message} ({found.count} record{'s' if found.count != 1 else ''}"
        + (
            f" of type '{found.type_key}' ({names[found.type_key]})"
            if found.type_key in names
            else ""
        )
        + (
            f", for example {', '.join(repr(name) for name in found.examples)}"
            if found.examples
            else ""
        )
        + ")"
        for found in refusals
    )


def _refusal_prompt(words: str) -> str:
    return (
        "The engine refuses the draft for the records the workspace holds: "
        f"{words}. Change the draft so the records the proposal moves keep the places they have "
        "now: give the type they become the parents and relationships they have, as the types they "
        f"come from do. Check the draft again and write {PROPOSAL} again."
    )


_REMOVAL_KINDS = ("objectType", "application", "attribute", "relationType")


def _plain(text: str) -> str:
    """Text for comparing quotes: case, quote marks, punctuation and whitespace set aside."""
    return " ".join(re.sub(r"[\"'`“”‘’«».,;:!?()\[\]]+", " ", text.casefold()).split())


def _persons_text(task: AiTask) -> str:
    """Everything the person wrote to the task: the words and every correction and answer."""
    design = task.design or {}
    return "\n".join(
        [
            task.words or "",
            *(str(item) for item in design.get("corrections") or []),
            *(str(item) for item in (design.get("answers") or {}).values()),
        ]
    )


def _requested_removals(proposal: dict[str, Any], written: str) -> list[dict[str, Any]]:
    """What the person's words explicitly ask to remove, as the session listed it: each with the
    words that ask. An entry whose words the person never wrote (any part of a sentence of their
    own text, whatever the case, spacing or quote marks) is not an ask, so it is not kept."""
    found = []
    text = _plain(written)
    raw = proposal.get("removals")
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        kind, key = item.get("kind"), str(item.get("key") or "").strip()
        words = str(item.get("words") or "").strip()
        owner = str(item.get("objectType") or "").strip()
        if (
            kind not in _REMOVAL_KINDS
            or not key
            or not words
            or (kind == "attribute" and not owner)
            or not _plain(words)
            or _plain(words) not in text
        ):
            continue
        moved = item.get("movedTo")
        moved_to = (
            [str(key).strip() for key in moved if str(key).strip()]
            if kind == "objectType" and isinstance(moved, list)
            else []
        )
        found.append(
            {
                "kind": kind,
                "key": key,
                "words": words[:500],
                **({"objectType": owner} if owner else {}),
                **({"movedTo": moved_to} if moved_to else {}),
            }
        )
    return found


def _counted(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def _removal_account(
    landing: Any,
    removals: list[dict[str, Any]],
    base: dict[str, Any],
    final: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, int]], list[dict[str, Any]]]:
    """Split what a migration would lose into what the person asked to remove and the rest. A loss
    is allowed only when it falls within a removal: the records of a removed type (or of the types
    of a removed application), the values of a removed field, and the relationships of a removed
    relation type or of records that are themselves removed. Returns the rest, per type, and one
    statement per removal with the counts it deletes and a plain sentence."""
    named = {
        kind: {
            item.get("key"): item.get("name") or item.get("key") for item in base.get(group) or []
        }
        for kind, group in (
            ("objectType", "objectTypes"),
            ("attribute", "attributeTypes"),
            ("relationType", "relationTypes"),
            ("application", "applications"),
        )
    }
    held = {
        item["key"]: set(item.get("objectTypeKeys") or [])
        for item in base.get("applications") or []
    }
    # The types each removal deletes the records of.
    reach: list[set[str]] = []
    for item in removals:
        if item["kind"] == "objectType":
            reach.append({item["key"]})
        elif item["kind"] == "application":
            reach.append(set(held.get(item["key"], ())))
        else:
            reach.append(set())
    counts = [{"records": 0, "values": 0, "relationships": 0} for _ in removals]
    removed_types = set().union(*reach) if reach else set()
    claimed: set[str] = set()
    for index, types in enumerate(reach):
        for type_key in sorted(types - claimed):
            counts[index]["records"] += landing.losses.get(type_key, {}).get("records", 0)
        claimed |= types
    rest: dict[str, dict[str, int]] = {}

    def left(type_key: str, kind: str, count: int) -> None:
        if count:
            slot = rest.setdefault(type_key, {})
            slot[kind] = slot.get(kind, 0) + count

    for type_key, found in landing.losses.items():
        if type_key not in removed_types:
            left(type_key, "records", found.get("records", 0))
    for (type_key, attribute), count in landing.value_losses.items():
        owner = next(
            (
                i
                for i, item in enumerate(removals)
                if item["kind"] == "attribute"
                and item["key"] == attribute
                and item.get("objectType") == type_key
            ),
            None,
        )
        if type_key in removed_types:
            continue  # it is the removed type's own (counted with its records)
        if owner is None:
            left(type_key, "values", count)
        else:
            counts[owner]["values"] += count
    for (relation, source, target), count in landing.relationship_losses.items():
        owner = next(
            (
                i
                for i, item in enumerate(removals)
                if (item["kind"] == "relationType" and item["key"] == relation)
                or source in reach[i]
                or target in reach[i]
            ),
            None,
        )
        if owner is None:
            left(source, "relationships", count)
        else:
            counts[owner]["relationships"] += count
    statements = []
    for item, found in zip(removals, counts, strict=True):
        name = named[item["kind"]].get(item["key"]) or item["key"]
        tail = [
            _counted(found[kind], word)
            for kind, word in (
                ("records", "record"),
                ("values", "value"),
                ("relationships", "relationship"),
            )
            if found[kind]
        ]
        what = {
            "objectType": f"{name} is deleted",
            "application": f"the application {name} is removed",
            "attribute": f"the field {name} of "
            f"{named['objectType'].get(item.get('objectType'), item.get('objectType'))} is removed",
            "relationType": f"the relationship type {name} is removed",
        }[item["kind"]]
        sentence = f"As you asked, {what}" + (f", deleting {', '.join(tail)}." if tail else ".")
        if item["kind"] == "objectType" and item.get("movedTo"):
            # A partial move: the change set restructures the records into other types, so nothing
            # is deleted and their relationships go along with them.
            target_names = {
                found_item.get("key"): found_item.get("name") or found_item.get("key")
                for found_item in (final or {}).get("objectTypes") or []
            }
            targets = [target_names.get(key) or key for key in item["movedTo"]]
            where = (
                f"{', '.join(targets[:-1])} and {targets[-1]}" if len(targets) > 1 else targets[0]
            )
            records = found["records"]
            sentence = (
                f"As you asked, {name} is removed: "
                + (f"its {_counted(records, 'record')} move" if records else "its records move")
                + f" to {where}."
            )
        statements.append({**item, "name": name, **found, "text": sentence})
    return rest, statements


_LOSS_KINDS = (("records", "record"), ("values", "value"), ("relationships", "relationship"))


def _loss_words(losses: dict[str, dict[str, int]], names: dict[str, str]) -> str:
    """What a migration would lose, per type with counts, in plain words (records, values and
    relationships, translation links among them)."""
    parts = []
    for type_key, counts in sorted(losses.items()):
        things = [
            f"{counts[kind]} {word}{'s' if counts[kind] != 1 else ''}"
            for kind, word in _LOSS_KINDS
            if counts.get(kind)
        ]
        if things:
            parts.append(f"{names.get(type_key, type_key)}: {', '.join(things)}")
    return "; ".join(parts)


def _type_names(*models: dict[str, Any]) -> dict[str, str]:
    """Type keys with their names, the first model's name winning."""
    names: dict[str, str] = {}
    for model in reversed(models):
        for item in model.get("objectTypes") or []:
            names[item["key"]] = item.get("name") or item["key"]
    return names


def _loss_prompt(words: str) -> str:
    return (
        "The engine finds that the migration this draft needs would lose the person's data: "
        f"{words}. Nothing the person did not ask to remove may be lost: every record, value, "
        "relationship and translation comes through, except what the person's words explicitly ask "
        "to remove, which you list in removals with their words. Change the draft (and the moves, splits or "
        "conversions) so that none is lost, or, if that cannot be done, write the proposal with a "
        "question that says why. "
        f"Check the draft again and write {PROPOSAL} again."
    )


def _consumer_changes(base: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    """The consumer APIs the draft raises the contractVersion of, from the engine's own diff."""
    try:
        return raised_contracts(parse_model(base), parse_model(model))
    except ModelValidationError:
        return []


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


# How many times the engine's findings about a landed draft (the consumer contract, the records it
# would refuse to move) go back to the session before the task fails.
LANDING_ROUNDS = 2


def _send_back(
    session: Session,
    job: Job,
    ctx: Any,
    task_id: str,
    folder: Path,
    check_of: Any,
    prompt: str,
    round_: int,
) -> None:
    """Another turn of the session with the engine's findings; the proposal it writes lands again."""
    task = load_task(session, task_id)
    session_id = (task.design or {})["agentSession"]
    session.commit()
    (folder / PROPOSAL).unlink(missing_ok=True)
    again = _run_turn(session, job, ctx, task_id, folder, prompt, session_id, first=False)
    if again is not None:
        _proposal_landed(session, ctx, task_id, folder, again, check_of, job, round_ + 1)


def _drafted_by(session: Session, task: AiTask, draft: ModelDraft) -> bool:
    """Whether the task's own client created this draft, as the engine recorded it."""
    if task.client_id is None:
        return False
    return (
        session.scalar(
            select(AuditEvent.sequence_id).where(
                AuditEvent.aggregate_type == "model_draft",
                AuditEvent.action == "created",
                AuditEvent.aggregate_id == draft.public_id,
                AuditEvent.actor_client_id == task.client_id,
            )
        )
        is not None
    )


QUESTION_MAX = 2000


def _question_text(text: str) -> str:
    """A question as the session wrote it: whole, so its ask is never cut off; only a runaway one is
    shortened, at a word, with an ellipsis."""
    text = text.strip()
    if len(text) <= QUESTION_MAX:
        return text
    return text[:QUESTION_MAX].rsplit(" ", 1)[0] + "…"


def _questions(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "text": _question_text(str(q.get("text"))),
            "options": [str(o) for o in q.get("options") or []],
            "assumed": q.get("assumed"),
        }
        for q in proposal.get("questions") or []
        if isinstance(q, dict) and q.get("text")
    ]


def _origin() -> dict[str, Any]:
    return {
        "kind": "ai",
        "provider": "claude-code",
        "model": None,
        "promptVersion": PROMPT_VERSION,
    }


def _without_model_change(session: Session, task: AiTask, proposal: Any) -> bool:
    """Whether the proposal is a words task's with an empty model part: the instruction is about the
    stored records, the session named no draft because none is needed, and it moves no type. A
    workbook task always needs a draft, for the types its rows go into."""
    if not isinstance(proposal, dict) or proposal.get("draftId") is not None:
        return False
    if proposal.get("moves") or not str(proposal.get("summary") or "").strip():
        return False
    return session.scalar(select(SourceFile.id).where(SourceFile.task_id == task.id)) is None


def _unchanged_landed(
    session: Session, ctx: Any, task: AiTask, proposal: dict[str, Any], progress: _Progress
) -> None:
    """A proposal without a draft: the task shows the summary and the questions, the model as it is,
    and waits for the person. Accepting makes the change set on the live release."""
    design = dict(task.design or {})
    design.pop("progress", None)
    task.draft_id = None
    task.design = {
        **design,
        "stage": "model",
        "summary": str(proposal.get("summary") or ""),
        "modelUnchanged": True,
        "moves": [],
        "consumerChanges": [],
        "questions": _questions(proposal),
        "outline": [],
        "checks": [],
        "origin": _origin(),
        "outcome": {},
        "load": None,
        "itemsLoad": False,
    }
    task.check = None
    note(task, "note", _said(progress))
    finish(task, "checked", _retention(ctx))
    task.finished_at = None
    session.commit()


def _proposal_landed(
    session: Session,
    ctx: Any,
    task_id: str,
    folder: Path,
    progress: _Progress,
    check_of: Any,
    job: Job,
    round_: int = 0,
) -> None:
    """The proposal the session wrote: the task shows it and waits, or fails with what was said."""
    task = load_task(session, task_id, for_update=True)
    path = folder / PROPOSAL
    try:
        proposal = json.loads(path.read_text())
    except OSError, ValueError:
        proposal = None
    draft = (
        session.scalar(
            select(ModelDraft).where(ModelDraft.public_id == str(proposal.get("draftId")))
        )
        if isinstance(proposal, dict) and proposal.get("draftId") is not None
        else None
    )
    if draft is not None and not _drafted_by(session, task, draft):
        # The ID is the session's word: a draft it did not create is a person's, not its to name (R-F3).
        # Trying again with the same draft cannot help: the session is told to make its own.
        if round_ < LANDING_ROUNDS:
            _send_back(
                session, job, ctx, task_id, folder, check_of, _not_its_draft_prompt(), round_
            )
            return
        note(
            task,
            "warning",
            "The session kept proposing a draft that is not its own, which it may not use: it "
            "must make its own model draft. Leave the task out and start a new one",
        )
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    if draft is not None and held_by_another(session, draft.id, task.id):
        # Reading it is not refused, and a proposal must not name it either (AP-D44).
        note(task, "warning", "The session proposed a draft another task holds; try again")
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    if draft is None:
        if _without_model_change(session, task, proposal):
            _unchanged_landed(session, ctx, task, proposal, progress)
            return
        spoke = str(progress.result.get("result") or "").strip() and not progress.result.get(
            "is_error"
        )
        note(
            task,
            "warning",
            _said(progress)
            if spoke
            else "The session ended without a proposal and said nothing about why. Tell it how to "
            "go on, or try again as it was.",
        )
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    design = dict(task.design or {})
    design.pop("progress", None)
    design.pop("modelUnchanged", None)
    questions = _questions(proposal)
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    base = current.model_json
    errors: list[Any] = []
    requested = _requested_moves(proposal)
    try:
        migration = _migration_of(session, task.workspace_key, draft, current, None, requested)
    except ApiError as error:
        note(task, "warning", f"The draft's migration cannot be read: {error.message}")
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    mappings = migration["typeMappings"]
    extra = _extra_of(migration)
    # A draft on no release is a new model, compared with the workspace's only if it moves types.
    compared = bool(mappings or extra or proposal.get("moves") or draft.base_model_release_id)
    if compared:
        try:
            errors = _contract_errors(base, draft.model_json)
        except ModelValidationError:
            errors = []  # a draft that does not compile is the checks' to report
    if errors and round_ < LANDING_ROUNDS:
        # The session fixes the draft as it does any finding of the checks (AP-D47).
        _send_back(session, job, ctx, task_id, folder, check_of, _contract_prompt(errors), round_)
        return
    if errors:
        note(
            task,
            "warning",
            f"The proposal still breaks consumers of the model: {_contract_words(errors)}",
        )
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    held = held_counts(session, task.workspace_key)
    asked = frozenset(item["fromObjectTypeKey"] for item in requested)
    refusals: tuple[LandingRefusal, ...] = ()
    losses: dict[str, dict[str, int]] = {}
    unasked: dict[str, dict[str, int]] = {}
    removals = _requested_removals(proposal, _persons_text(task))
    stated: list[dict[str, Any]] = []
    try:
        moves = _planned_moves(migration, base, draft.model_json, held, requested=asked)
        if mappings or extra or draft.base_model_release_id:
            # The records are the engine's to check, as the migration's preview will (AP-D47), for
            # every kind of change: what the person's data would lose is measured on the migration
            # the task will hand over, whatever mappings, splits or conversions cause it.
            try:
                landing = check_landing(
                    session,
                    task.workspace_key,
                    parse_model(base),
                    parse_model(draft.model_json),
                    mappings,
                    extra,
                )
            except ApiError, ModelValidationError:
                if mappings or extra:
                    raise
                landing = (
                    None  # a draft with no mappings that does not check is not a migration yet
                )
            if landing is not None:
                refusals, losses = landing.refusals, landing.losses
                unasked, stated = _removal_account(landing, removals, base, draft.model_json)
                moves = _planned_moves(migration, base, draft.model_json, held, losses, asked)
    except (ApiError, ModelValidationError) as error:
        reason = error.message if isinstance(error, ApiError) else "the draft does not compile"
        note(task, "warning", f"The proposed moves cannot be made: {reason}")
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    if refusals:
        names = {
            item["key"]: item.get("name") or item["key"]
            for item in draft.model_json.get("objectTypes") or []
        }
        words = _refusal_words(refusals, names)
        if round_ < LANDING_ROUNDS:
            _send_back(session, job, ctx, task_id, folder, check_of, _refusal_prompt(words), round_)
            return
        note(
            task,
            "warning",
            f"The proposal still has records the engine would refuse to move: {words}",
        )
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    lost = _loss_words(unasked, _type_names(draft.model_json, base))
    if lost:
        # No migration that loses what the person did not ask to remove is offered (product rule,
        # 2026-11-09). The proposal records no removal the person asked for, so every loss counts.
        if round_ < LANDING_ROUNDS:
            _send_back(session, job, ctx, task_id, folder, check_of, _loss_prompt(lost), round_)
            return
        note(
            task,
            "warning",
            f"The proposal would lose data: {lost}. Nothing was changed, and no migration is offered.",
        )
        finish(task, "failed", _retention(ctx))
        session.commit()
        return
    check = check_of(session, draft)
    # A dry run of items (0.13 AB) is what accepting loads: its summary is the task's, in the design.
    previewed = check.pop("itemsSummary", None) if check else None
    records = _records_per_type(session, (check or {}).get("dryRunJobId"))
    related = records.pop(None, 0)
    if check and related and previewed is None:
        # The check counts a relationship as an item it creates; the person reads records and links.
        check["summary"]["created"] -= related
        check["summary"]["relationships"] = related
    task.draft_id = draft.id
    task.design = {
        **design,
        "stage": "model",
        "summary": str(proposal.get("summary") or ""),
        "moves": moves,
        "removals": stated,
        "consumerChanges": _consumer_changes(base, draft.model_json) if compared else [],
        "questions": questions,
        # A draft on no release is a new model: a type sharing a key with the old one is not a change.
        "outline": _shape(draft.model_json, base if draft.base_model_release_id else {}, records),
        "checks": [
            *_left_out(draft.model_json, base, held, frozenset(m["from"] for m in moves)),
            *(
                []
                if previewed is not None
                else _beside_held(session, (check or {}).get("dryRunJobId"), draft.model_json, held)
            ),
            *_cells_left_out(session, task, (check or {}).get("dryRunJobId")),
        ],
        "origin": _origin(),
        "outcome": {},
        "load": previewed,
        "itemsLoad": previewed is not None and not moves,
    }
    task.check = check
    for found in stated:
        note(task, "note", found["text"])
    if mappings or extra:
        for found in migration["notes"]:
            note(task, "note", found["message"])
    note(task, "note", _said(progress))
    finish(task, "checked", _retention(ctx))
    task.finished_at = None
    session.commit()


def start(
    session: Session,
    job: Job,
    ctx: Any,
    task_id: str,
    workbook_path: Path | None,
    check_of: Any,
    extra: str | None = None,
) -> None:
    """The session's first turn: the workbook to a draft the person reviews. ``extra`` is what the
    person said when the session starts again on a task that had none, or whose first turn never ran."""
    task = load_task(session, task_id)
    workspace = task.workspace_key
    words = task.words
    url = _api_url()
    release = session.get(ModelRelease, load_assignment(session, workspace)[1].id)
    model_json = json.dumps(release.model_json)
    folder = folder_of(ctx.files, task)
    # The task's row is not held across the copy and the call to the engine's own API (R-F20).
    session.commit()
    folder.mkdir(parents=True, exist_ok=True)
    _share(folder, 0o2770)
    if workbook_path is not None:
        shutil.copyfile(workbook_path, folder / "workbook.xlsx")
    (folder / "model.json").write_text(model_json)
    (folder / "openapi.json").write_bytes(_openapi(url))
    for name in ("workbook.xlsx", "model.json", "openapi.json"):
        if (folder / name).exists():
            _share(folder / name, 0o660)
    task = load_task(session, task_id, for_update=True)
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
    if extra:
        prompt = f"{prompt}\n\nThe person adds:\n{extra}"
    progress = _run_turn(session, job, ctx, task_id, folder, prompt, session_id, first=True)
    if progress is not None:
        _proposal_landed(session, ctx, task_id, folder, progress, check_of, job)


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
        _proposal_landed(session, ctx, task_id, folder, progress, check_of, job)


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
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id else None
    requested = [
        {
            "fromObjectTypeKey": move["from"],
            "toObjectTypeKey": move["to"],
            "attributes": move.get("attributes") or [],
        }
        for move in (task.design or {}).get("moves") or []
        if move.get("fromSession", True)
    ]
    try:
        migration = _migration_of(session, task.workspace_key, draft, current, release, requested)
        mappings = migration["typeMappings"]
        extra = _extra_of(migration)
        parsed = Mappings.of({"typeMappings": mappings, **extra})
        plan_migration(
            parse_model(current.model_json),
            parse_model(release.model_json),
            parsed.types,
            parsed.relations,
            parsed.spawns,
        )
        errors = _contract_errors(current.model_json, release.model_json)
        landing = check_landing(
            session,
            task.workspace_key,
            parse_model(current.model_json),
            parse_model(release.model_json),
            mappings,
            extra,
        )
    except ApiError, ModelValidationError:
        return None
    if errors:
        note(
            task,
            "warning",
            f"The installed release breaks consumers of the model: {_contract_words(errors)}",
        )
        return None
    unasked, stated = _removal_account(
        landing, (task.design or {}).get("removals") or [], current.model_json, release.model_json
    )
    lost = _loss_words(unasked, _type_names(current.model_json, release.model_json))
    if lost:
        # No migration is returned, so the person cannot confirm one: the data is as it was.
        note(
            task,
            "warning",
            f"The installed release would lose data: {lost}. No data was changed, and no migration "
            "is offered to confirm.",
        )
        task.design = {**(task.design or {}), "withheld": True}
        return None
    for found in stated:
        note(task, "note", found["text"])
    if landing.refusals:
        names = {item.key: item.name for item in parse_model(release.model_json).objectTypes}
        words = _refusal_words(landing.refusals, names)
        note(
            task,
            "warning",
            f"The installed release has records the engine would refuse to move: {words}",
        )
        return None
    return {"migration": {"releaseId": release.public_id, "typeMappings": mappings, **extra}}


def _change_set_of(session: Session, task: AiTask, change_set_id: str | None) -> ChangeSet | None:
    """The change set the session's last line names, when the task's own client made it: the line is
    the session's word, and a person's change set is not its to hand over (R-F4)."""
    if not change_set_id or task.client_id is None:
        return None
    return session.scalar(
        select(ChangeSet).where(
            ChangeSet.id == change_set_id, ChangeSet.created_by_client_id == task.client_id
        )
    )


def accepted(session: Session, job: Job, ctx: Any, task_id: str, words: str | None = None) -> None:
    """The person accepted: the same session installs one release and loads into a change set, or,
    when the proposal moved whole types, installs the release a migration will move to (AP-D46).
    ``words`` are the person's, on a second try (AP-D54). The folder and the client stay until the
    work is in the person's hands for good (AP-D56)."""
    task = load_task(session, task_id)
    folder = folder_of(ctx.files, task)
    moves = (task.design or {}).get("moves")
    unchanged = bool((task.design or {}).get("modelUnchanged"))
    progress = _run_turn(
        session,
        job,
        ctx,
        task_id,
        folder,
        _again(_MOVED if moves else _ACCEPTED_UNCHANGED if unchanged else _ACCEPTED, words),
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
            if not (task.design or {}).get("withheld"):
                note(task, "warning", "The session installed no release the moves fit")
            finish(task, "failed", _retention(ctx))
        else:
            task.result = result
            finish(task, "loaded", _retention(ctx))
        session.commit()
        return
    change_set_id = _last_line(words, LAST_LINE)
    change_set = _change_set_of(session, task, change_set_id)
    if (
        not unchanged
        and _last_line(words, RELEASE_LINE)
        and (
            change_set is None
            or (
                change_set.workspace_key == task.workspace_key
                and not _holds_changes(_counts(session, change_set.id))
            )
        )
    ):
        # The model alone changes: the migration ending with no type mappings (the records stay).
        result = _migration_result(session, task, words)
        if result is None and (task.design or {}).get("withheld"):
            finish(task, "failed", _retention(ctx))
            session.commit()
            return
        if result is not None:
            task.result = result
            finish(task, "loaded", _retention(ctx))
            if change_set is not None:
                # The empty change set the session made is not left dangling (commits).
                session.flush()
                discard_change_set(session, change_set.id, change_set.version)
            session.commit()
            return
    if not _land(session, task, words, change_set_id, change_set, _retention(ctx)):
        # The words stay: a later read lands the load under the rules of the day (:func:`recover_load`).
        task.design = {**(task.design or {}), "loadWords": words[-4000:]}
    session.commit()


def _landing(
    session: Session,
    task: AiTask,
    words: str,
    change_set_id: str | None,
    change_set: ChangeSet | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """What a load that ended well leaves on the task, or ``None`` and why not (the reason may be
    ``None`` when a note already says it). An empty change set is no load, whatever the session's
    last line says; one that holds only relationships is one."""
    unchanged = bool((task.design or {}).get("modelUnchanged"))
    counts = _counts(session, change_set.id) if change_set is not None else None
    if change_set is None:
        return None, (
            "The session named no change set of this task's own, so nothing was loaded"
            if change_set_id
            else "The session ended without naming the change set it loaded into, so nothing was loaded"
        )
    if change_set.workspace_key != task.workspace_key:
        return None, "The session's change set is in another workspace, so nothing was loaded"
    if not _holds_changes(counts):
        return None, (
            "The session's change set holds no record or relationship to add, change or remove, "
            "so nothing was loaded"
        )
    if (
        unchanged
        and change_set.model_release_id != load_assignment(session, task.workspace_key)[1].id
    ):
        # The model does not change: the change set is on the release the workspace runs, or it is not
        # the change the person accepted.
        return None, "The change set is not on the model the workspace runs"
    then = _then_release(session, task, words, change_set)
    if then is None:
        return None, None
    return {
        "changeSetId": change_set.id,
        "changeSetName": change_set.name,
        "counts": counts,
        **_saved_profile(session, task, change_set),
        **then,
        **_change_set_release(session, change_set, then),
    }, None


def _land(
    session: Session,
    task: AiTask,
    words: str,
    change_set_id: str | None,
    change_set: ChangeSet | None,
    retention_days: int,
) -> bool:
    """End a load: ``loaded`` with its result, or ``failed`` with the reason, keeping any change set
    the session did write reachable on the task (a person never lands on a task with no way
    forward). Whether it loaded."""
    result, reason = _landing(session, task, words, change_set_id, change_set)
    if result is None:
        if reason:
            note(task, "warning", reason)
        finish(task, "failed", retention_days)
        _keep_written(session, task, change_set)
        return False
    task.result = result
    finish(task, "loaded", retention_days)
    return True


def _keep_written(session: Session, task: AiTask, change_set: ChangeSet | None) -> None:
    """A failed load that left a change set holding changes: it stays on the task, to review or to
    discard, and is never orphaned by a second try."""
    if change_set is None or change_set.workspace_key != task.workspace_key:
        return
    counts = _counts(session, change_set.id)
    if _holds_changes(counts):
        task.result = {
            "changeSetId": change_set.id,
            "changeSetName": change_set.name,
            "counts": counts,
        }


def _session_change_sets(session: Session, task: AiTask) -> list[ChangeSet]:
    """The open change sets the task's own client made in its workspace, the most recent first."""
    return list(
        session.scalars(
            select(ChangeSet)
            .where(
                ChangeSet.created_by_client_id == task.client_id,
                ChangeSet.workspace_key == task.workspace_key,
            )
            .order_by(ChangeSet.created_at.desc(), ChangeSet.sequence_id.desc())
        )
    )


def recover_load(session: Session, task: AiTask, retention_days: int) -> None:
    """A failed task at the load stage whose session has not ended, read again: the rules may have
    moved on since it failed (a load that only linked records was once no load). When the session's own
    change set (the task's client made it, the most recent that holds changes) now passes the landing
    checks the task is ``loaded``; otherwise the change set stays reachable on the task. Idempotent."""
    design = task.design or {}
    if (
        task.state != "failed"
        or design.get("stage") != "load"
        or design.get("moves")
        or not design.get("agentSession")
        or design.get("sessionEnded")
        or task.client_id is None
    ):
        return
    kept = (task.result or {}).get("changeSetId")
    change_set = next(
        (c for c in _session_change_sets(session, task) if _holds_changes(_counts(session, c.id))),
        None,
    )
    if change_set is None:
        if kept and session.scalar(select(ChangeSet.id).where(ChangeSet.id == kept)) is None:
            # What the task kept was published or discarded elsewhere.
            task.result = None
            session.flush()
        return
    notes = task.notes
    result, _ = _landing(
        session, task, str(design.get("loadWords") or ""), change_set.id, change_set
    )
    if result is None:
        task.notes = notes
        if kept != change_set.id:
            _keep_written(session, task, change_set)
            session.flush()
        return
    task.notes = [n for n in notes if n.get("kind") != "warning"]
    task.result = result
    finish(task, "loaded", retention_days)
    session.flush()


def end_session(
    session: Session, files: Any, task: AiTask, *, retire_releases: bool = True
) -> None:
    """The session's work is in the person's hands for good (AP-D56): the change set was published or
    discarded, the migration confirmed, or the task discarded. Its folder, transcript and client go,
    and a release it installed that nothing runs is retired (not after a publication, which ran on
    one). The caller commits."""
    design = dict(task.design or {})
    if not design.get("agentSession") or design.get("sessionEnded"):
        return
    remove_folder(files, task)
    if retire_releases:
        retire_unused_releases(session, task)
    retire_session_client(session, task.client_id)
    task.design = {**design, "sessionEnded": True}


def lives(task: AiTask) -> bool:
    """Whether the task's session can still be told something."""
    design = task.design or {}
    return bool(design.get("agentSession")) and not design.get("sessionEnded")


def _change_set_release(
    session: Session, change_set: ChangeSet, then: dict[str, str]
) -> dict[str, str]:
    """The change set's own release, next to the final one: when they are the same, the old types
    stay and there is no third step."""
    if not then:
        return {}
    release = session.get(ModelRelease, change_set.model_release_id)
    return {"changeSetReleaseId": release.public_id} if release is not None else {}


def _final_release_found(
    session: Session, task: AiTask, change_set: ChangeSet
) -> ModelRelease | None:
    """The final release of a part-of-a-type reshaping, read from what the engine recorded rather than
    from the session's last line: the newest release the task's client installed, other than the
    change set's own, whose types are exactly the change set's release without the old types
    beside the new ones. ``None`` when there is no such release (a load that moves nothing)."""
    if task.client_id is None:
        return None
    own = session.get(ModelRelease, change_set.model_release_id)
    if own is None:
        return None
    beside = {item.get("key") for item in own.model_json.get("objectTypes") or []}
    installed = session.scalars(
        select(AuditEvent.aggregate_id)
        .where(
            AuditEvent.aggregate_type == "model_release",
            AuditEvent.action == "installed",
            AuditEvent.actor_client_id == task.client_id,
        )
        .order_by(AuditEvent.sequence_id.desc())
    ).all()
    for public_id in installed:
        if public_id == own.public_id:
            continue
        found = session.scalar(select(ModelRelease).where(ModelRelease.public_id == public_id))
        types = (
            {item.get("key") for item in (found.model_json.get("objectTypes") or [])}
            if found
            else set()
        )
        if found is not None and types < beside:
            return found
    return None


def _then_release(
    session: Session, task: AiTask, words: str, change_set: ChangeSet | None = None
) -> dict[str, str] | None:
    """The final release of a part-of-a-type reshaping: the third step, the person's, activates it
    once the old types hold no record (AP-D48). ``None`` when the engine would refuse that
    activation for the consumers of the model (C-D17); the warning names them."""
    named = _last_line(words, THEN_LINE)
    release = _installed_by(session, task, named)
    if release is None and change_set is not None:
        # The session's word is a hint: the engine finds the final release from what it recorded.
        release = _final_release_found(session, task, change_set)
    if release is None and named is None:
        if any(item.get("movedTo") for item in (task.design or {}).get("removals") or []):
            # A partial move without its final release has no steps to show: say so, not nothing.
            note(
                task,
                "warning",
                "The session did not name the final release, so the steps to finish the move are not "
                "shown. Tell the assistant to go on and name it.",
            )
        return {}
    if release is None:
        note(task, "warning", "The session named a final release it did not install")
        return {}
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    try:
        errors = _contract_errors(current.model_json, release.model_json)
    except ModelValidationError:
        errors = []
    if errors:
        note(
            task,
            "warning",
            f"The final release breaks consumers of the model: {_contract_words(errors)}",
        )
        return None
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
        return {
            "profileNotSaved": "This load did not import the workbook, so it cannot be repeated."
        }
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
        "valueMaps": {
            k: v for found in definitions for k, v in (found.get("valueMaps") or {}).items()
        },
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


def _holds_changes(counts: dict[str, int]) -> bool:
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
