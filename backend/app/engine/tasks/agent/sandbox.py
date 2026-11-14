"""The assistant session's sandbox: which operating-system user runs it, the slots and gates that hand the
users out, the container check, the safeguards, the environment and credentials that reach it, and
the command that starts it (RF5)."""

import fcntl
import grp
import ipaddress
import json
import logging
import os
import pwd
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from ....config import get_settings
from ....errors import api_error
from ....models.commands import GrantCreate, GrantPrincipal, GrantScope, RoleCreate
from ....models.database import AiTask, AuthorizationState, Grant, Job, OAuthClient, Role
from ...authorization.administration import create_grant, create_role, delete_grant, groups_of
from ...authorization.permissions import permissions_of
from ...identity import tokens
from ...identity.clients import create_session_client
from ...identity.settings import IdentitySettings
from .network import FAILED, RESTRICTED, proxy_reachable, proxy_variables, read_state

log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(os.environ.get("AI_AGENT_COMMAND", "").strip())


def loopback(url: str) -> bool:
    """Whether the API is reached on this machine, where a certificate of its own is no risk (R-F8).

    Kept apart from ``common.addresses.LOOPBACK`` (the three names a URL may use for this computer
    when an address is registered): this asks about the host of an address already in use, and any
    loopback address (all of 127.0.0.0/8) is this machine."""
    host = urlparse(url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


# Left on the token beyond a turn's longest length, for the jobs the session started and the end of the turn.
TOKEN_SLACK_SECONDS = 600


def _identity() -> IdentitySettings:
    settings = get_settings()
    return IdentitySettings(
        encryption_key=settings.secrets_encryption_key,
        issuer=settings.public_url,
        # The session's token lives at least as long as a turn may (AI_AGENT_TIMEOUT_SECONDS), or a
        # long turn would find its token expired.
        access_token_seconds=max(
            settings.access_token_minutes * 60,
            settings.ai_agent_timeout_seconds + TOKEN_SLACK_SECONDS,
        ),
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


def access(session: Session, job: Job, task: AiTask) -> tuple[str, int, list[str]]:
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


def base_command() -> list[str]:
    """The configured command, without a permission mode: the engine sets that itself."""
    try:
        words = shlex.split(os.environ.get("AI_AGENT_COMMAND", "").strip().strip("\"'"))
    except ValueError as error:
        raise OSError(f"it is not a command ({error})") from error
    if not words:
        raise OSError("it is empty")
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


ASSISTANT_GROUP = "assistant"
# The pool's users are named ``assistant-1`` to ``assistant-N`` (the image's ASSISTANT_USERS build
# argument), all in the one group, each with a home of its own (0.17 RF5).
_POOL_USER = re.compile(r"^assistant-(\d+)$")


class SessionUserError(OSError):
    """A turn cannot be given a session user, or its user's state cannot be reset."""


class NoSessionUser(SessionUserError):
    """Every user of the container's pool is running another turn."""


class ResetFailed(SessionUserError):
    """The reset between turns (``RESET_COMMAND``) did not finish."""


def container() -> bool:
    """In a container the container is the boundary: Claude Code's own sandbox cannot run inside it."""
    return os.environ.get("AI_AGENT_SANDBOX", "").strip().lower() == "container"


def _pool_users() -> list[str]:
    """The users the image made for sessions: those named ``assistant-<number>`` that are members of
    the group ``assistant``, in numeric order."""
    try:
        members = set(grp.getgrnam(ASSISTANT_GROUP).gr_mem)
    except KeyError:
        return []
    found = [
        (int(match.group(1)), user.pw_name)
        for user in pwd.getpwall()
        if user.pw_name in members and (match := _POOL_USER.match(user.pw_name))
    ]
    return [name for _, name in sorted(found)]


def take_session_user(slots: Path) -> tuple[str, Any]:
    """The pool user a turn runs as, and the open lock file that holds it: the caller closes it when
    the turn ends. A user is taken by an exclusive lock on a file of the same name in ``slots`` (a
    folder only the engine's user enters), so two turns never share one, and a process that dies
    frees its user (the turn's reset before the next one ends what it left running) (0.17 RF5)."""
    users = _pool_users()
    slots.mkdir(mode=0o700, parents=True, exist_ok=True)
    for user in users:
        handle = open(slots / user, "a")  # noqa: SIM115 - the caller closes it
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            continue
        return user, handle
    shown = (
        f"all {len(users)} assistant users are" if users else "no assistant user exists; none is"
    )
    raise NoSessionUser(
        f"No session user is free: {shown} running another session now. Raise the image's "
        "ASSISTANT_USERS build argument to at least the number of engine processes "
        "(WEB_CONCURRENCY) and build it again."
    )


# What runs as the session user between turns (``backend/refiroo-session-reset``, installed by the image).
RESET_COMMAND = "/usr/local/bin/refiroo-session-reset"
RESET_DONE = "refiroo-session-reset-done"


def reset(user: str, config: Path | None = None, work: Path | None = None) -> None:
    """Between turns, as the session user (never root): every process it runs ends, repeatedly, before
    anything else is done; then its home and its files in the machine's scratch folders are emptied;
    with the task's two folders given, its files in them become the group's to read and write; every
    process ends once more. The folders go in on standard input, not on the command line. The script
    survives its own kill, so its marker and its exit status are both the proof (0.17 RF5)."""
    command = ["sudo", "-n", "-u", user, "--", RESET_COMMAND]
    given = f"{config}\n{work}\n" if config is not None and work is not None else ""
    try:
        done = subprocess.run(
            command, input=given, capture_output=True, text=True, timeout=120, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ResetFailed(f"The reset of session user {user} could not run: {error}") from error
    if done.returncode != 0 or RESET_DONE not in done.stdout:
        reason = (done.stderr or "").strip().splitlines()[-1:] or ["no reason given"]
        raise ResetFailed(
            f"The reset of session user {user} did not finish ({reason[0][:200]}). "
            "Check that the image installs the reset command and lists it in its sudoers rule."
        )


def open_gate(gate: Path, user: str) -> None:
    """For the length of a turn, the task's folder belongs to the group of the user that runs it, and
    only that group may enter it: no other session user can, whatever names it knows."""
    descriptor = os.open(gate, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fchown(descriptor, -1, pwd.getpwnam(user).pw_gid)
        os.fchmod(descriptor, 0o710)
    finally:
        os.close(descriptor)


def close_gate(gate: Path) -> None:
    """Between turns the task's folder is the engine's alone."""
    descriptor = os.open(gate, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fchmod(descriptor, 0o700)
    finally:
        os.close(descriptor)


def close_gates_of(root: Path, user: str) -> None:
    """Before a turn opens its gate: every gate still open for this user's private group is closed.
    One is left open when an engine process was killed between opening it and closing it; the user's
    lock is held by the turn that calls this, so no turn of another process can have it open."""
    gid = pwd.getpwnam(user).pw_gid
    for path in root.iterdir():
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            continue
        try:
            found = os.fstat(descriptor)
            if found.st_gid == gid and found.st_mode & 0o070:
                os.fchmod(descriptor, 0o700)
        except OSError as error:
            raise ResetFailed(
                f"A task's folder still open for session user {user} could not be closed: {error}"
            ) from error
        finally:
            os.close(descriptor)


def close_idle_gates(root: Path, slots: Path) -> None:
    """A gate left open by an engine process that died is closed again, unless a turn of another
    process holds its user right now (a gate is open exactly while its user's lock is held). The gate
    is read again through its open descriptor once the user's lock is held, so a gate a turn of
    another process has just opened for another user is never closed."""
    for path in root.iterdir():
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            continue
        handle = None
        try:
            found = os.fstat(descriptor)
            if not found.st_mode & 0o070:
                continue
            try:
                owner = grp.getgrgid(found.st_gid).gr_name
            except KeyError:
                owner = ""
            if _POOL_USER.match(owner):
                slots.mkdir(mode=0o700, parents=True, exist_ok=True)
                handle = open(slots / owner, "a")  # noqa: SIM115 - closed below
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    continue
                again = os.fstat(descriptor)
                if again.st_gid != found.st_gid or not again.st_mode & 0o070:
                    continue
            os.fchmod(descriptor, 0o700)
        except OSError as error:
            log.warning("A task's folder could not be closed: %s", error)
        finally:
            if handle is not None:
                handle.close()
            os.close(descriptor)


def as_assistant(user: str) -> list[str]:
    """In a container the session runs as a user of its own, which cannot read the engine's
    environment or its job files (R-F45), nor another session's (0.17 RF5). ``sudo`` resets the
    environment and keeps only the names the image's sudoers rule lists; the token is passed that way
    and not on the command line, which any process of the container can read."""
    return ["sudo", "-n", "-u", user, "--"]


def agent_root(files: Any) -> Path:
    """Where the sessions' folders are. In a container they cannot lie in the job files, which only
    the engine's user may enter: they lie in a folder the session users may enter but not list, so a
    task's folder is found only by its name, which is long and random (0.17 RF5)."""
    if container():
        return Path(
            os.environ.get("AI_AGENT_FOLDERS", "").strip()
            or "/opt/refiroo/rdm-engine/data/assistant"
        )
    return Path(files.directory) / "agent"


def slots_of(root: Path) -> Path:
    """The folder of the pool's lock files, beside the sessions' root and the engine's alone."""
    return root.with_name(f"{root.name}-slots")


def safeguards(url: str, folder: Path) -> list[str]:
    """What the session may touch, whatever its command says: its tools, its folder, and this
    engine on the network. The sandbox is the operating system's, so a script it writes is held too;
    a machine where it cannot run refuses to start the session."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    # In a container the container is the boundary: the sandbox's own isolation cannot run inside it.
    contained = container()
    settings: dict[str, Any] = {
        "sandbox": {
            "enabled": not contained,
            "failIfUnavailable": not contained,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": True,
        },
    }
    # The sandbox's folder and network rules are inert in a container, and every process there reads
    # a command line: the folder's path stays off it (0.17 RF5).
    if not contained:
        settings["sandbox"]["filesystem"] = {
            "denyRead": ["~/"],
            "allowRead": [str(folder), sys.prefix],
        }
        settings["sandbox"]["network"] = {"allowedDomains": [host, f"{host}{port}"]}
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


# Of the server's environment, only what Claude Code itself needs, by name: never its database or
# secrets (0.17 RF5). The same names, with ``LC_*`` and the Bedrock names, are the sudoers rule's
# ``env_keep`` in ``backend/Dockerfile``; ``tests/unit/engine/tasks/test_agent.py`` holds the two equal.
PASSED_NAMES = (
    "REFIROO_TOKEN",
    "LANG",
    "TMPDIR",
    # The task's own Claude Code folder, set per session (a container's image sets none).
    "CLAUDE_CONFIG_DIR",
    # How Claude Code signs in: an API key, a gateway's token or a subscription's token.
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    # The model Claude Code uses, and what its aliases stand for.
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "NODE_EXTRA_CA_CERTS",
    # The proxy the session reaches the provider through when its network is restricted (SR-D6): set by
    # the engine from ``network.proxy_variables``, never taken from the engine's own environment.
    "HTTPS_PROXY",
    "NO_PROXY",
)
ENGINE_SET = ("HTTPS_PROXY", "NO_PROXY")
PASSED_PREFIXES = ("LC_",)
# Passed only when ``CLAUDE_CODE_USE_BEDROCK`` is on (``CLAUDE_CODE_USE_BEDROCK`` itself, when set).
BEDROCK_NAMES = (
    "CLAUDE_CODE_USE_BEDROCK",
    "AWS_REGION",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_PROFILE",
)
# Outside a container only: the session lives in the developer's own account and home.
HOST_NAMES = ("HOME", "USER", "SHELL")


def _passed(environ: dict[str, str]) -> dict[str, str]:
    """The named variables of ``environ`` that a session may see."""
    names = set(PASSED_NAMES) | {"CLAUDE_CODE_USE_BEDROCK"}
    if environ.get("CLAUDE_CODE_USE_BEDROCK", "").strip().lower() in ("1", "true", "yes", "on"):
        names |= set(BEDROCK_NAMES)
    if not container():
        names |= set(HOST_NAMES)
    return {
        name: value
        for name, value in environ.items()
        if (name in names and name not in ENGINE_SET) or name.startswith(PASSED_PREFIXES)
    }


def network_variables() -> dict[str, str]:
    """The proxy variables of a session whose container restricts its network."""
    if container() and read_state().state == RESTRICTED:
        return proxy_variables()
    return {}


class NetworkNotReady(SessionUserError):
    """The session's network rule failed to be set, or its proxy is gone: no turn starts (SR-D6)."""


def check_network() -> None:
    """In a container, a turn starts only when the network is as the start step left it: unrestricted
    (no ``NET_ADMIN``, told at start) or restricted with its proxy running. A setup that failed, or a
    proxy that is gone, would leave the session unrestricted or without a way out."""
    if not container():
        return
    found = read_state()
    if found.state == FAILED:
        raise NetworkNotReady(
            f"The assistant's network rule could not be set ({found.note}), so the assistant does not "
            "start: fix the cause and restart the engine"
        )
    if found.state == RESTRICTED and not proxy_reachable():
        raise NetworkNotReady(
            "The assistant's network proxy is not running, so the session could not reach the AI "
            "provider: restart the engine"
        )


def session_environment(
    token: str, folder: Path | None = None, config: Path | None = None
) -> dict[str, str]:
    """What the session's process sees. Its scratch folder (``TMPDIR``) lies inside its own folder:
    a session that kept files in the machine's scratch folder had its next turn's command refused for
    reading outside its folder, and the task failed (task 95). In a container ``config`` is the task's
    own Claude Code folder, where its transcripts are written. The engine makes no folder here: the
    session can replace what lies in its working folder, so ``ensure_tmp`` makes the scratch folder."""
    scratch: dict[str, str] = {}
    if folder is not None:
        scratch["TMPDIR"] = str(folder / "tmp")
    if config is not None:
        scratch["CLAUDE_CONFIG_DIR"] = str(config)
    network = network_variables()
    return {
        **_passed(dict(os.environ)),
        **scratch,
        **network,
        "REFIROO_TOKEN": token,
        "PATH": f"{Path(sys.prefix) / 'bin'}:{os.environ.get('PATH', '')}",
    }
