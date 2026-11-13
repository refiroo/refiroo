"""The assistant task's folder and home: putting and reading the work files, the transcript, and sweeping
what is left behind."""

import grp
import logging
import os
import re
import secrets
import shutil
import stat
import time
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ....config import get_settings
from ....models.database import AiTask
from ..store import load_task
from .sandbox import ASSISTANT_GROUP, agent_root, close_idle_gates, container, slots_of

log = logging.getLogger(__name__)


def resumable(files: Any, task: AiTask) -> bool:
    """Whether the task's session left a transcript Claude Code can resume. A session ended before
    it wrote one (a Stop in the first seconds) has nothing to go on from: its next turn starts
    again (0.13 DOC11 13)."""
    session_id = (task.design or {}).get("agentSession")
    if not session_id:
        return False
    if not container() and not os.environ.get("CLAUDE_CONFIG_DIR", "").strip():
        # Where Claude Code keeps transcripts is not this engine's to say.
        return True
    transcript = (
        _transcripts(files, task) / _transcript_name(folder_of(files, task)) / f"{session_id}.jsonl"
    )
    return transcript.exists()


# Where a task's random folder name is kept, in its design (0.17 RF5).
FOLDER_KEY = "agentFolder"


def folder_of(ctx_files: Any, task: AiTask) -> Path:
    """The folder the session works in. In a container the task's folder has a long random name, kept
    in its design, and the working folder is ``work`` inside it, beside the task's own Claude Code
    folder and its logs; a task whose folder is not yet renamed (``ensure_folder``) is still at the
    name its ID gave it."""
    root = agent_root(ctx_files)
    name = (task.design or {}).get(FOLDER_KEY) if container() else None
    return root / name / "work" if name else root / task.public_id


def home_of(ctx_files: Any, task: AiTask) -> Path:
    """Everything the task keeps: in a container its random folder, otherwise the working folder."""
    folder = folder_of(ctx_files, task)
    return folder.parent if container() and (task.design or {}).get(FOLDER_KEY) else folder


def ensure_folder(session: Session, files: Any, task_id: str) -> None:
    """In a container, gives the task its random folder name before anything is written there, and
    moves a folder named by the task's ID (made before 0.17) into it. The name is kept with the task
    under its row lock and committed first, so two processes never give two names and a sweep that
    finds the old folder meanwhile finishes the move instead of removing it. A transcript the earlier
    version kept in the shared Claude Code folder is not moved: a task begun before the upgrade starts
    a new session when it is told something, with its workbook and files kept (0.17 RF5)."""
    if not container():
        return
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    if design.get(FOLDER_KEY):
        session.commit()
        return
    root = agent_root(files)
    _open_root(root)
    name = secrets.token_urlsafe(24)
    task.design = {**design, FOLDER_KEY: name}
    public_id = task.public_id
    session.commit()
    _adopt_legacy(root, public_id, name)


def _adopt_legacy(root: Path, public_id: str, name: str) -> None:
    """The folder a task had before it had a random name becomes the working folder of its new one.
    Idempotent: another process may be doing the same."""
    legacy = root / public_id
    if legacy.is_symlink():
        legacy.unlink()
        return
    if not legacy.is_dir():
        return
    home = root / name
    if (home / "work").exists():
        shutil.rmtree(legacy, ignore_errors=True)
        return
    _create_task_folders(home, work=False)
    try:
        os.rename(legacy, home / "work")
    except FileNotFoundError:
        pass


def _open_root(root: Path) -> None:
    """The tasks' folder in a container: the engine's, with the sessions' group allowed to enter it
    but not list it, whatever mode a volume of an earlier version kept (0.17 RF5)."""
    root.mkdir(parents=True, exist_ok=True)
    try:
        os.chown(root, -1, grp.getgrnam(ASSISTANT_GROUP).gr_gid)
        os.chmod(root, 0o2710)
    except (KeyError, OSError) as error:
        log.warning("The assistant's folder %s could not be closed to listing: %s", root, error)


def _shared_dir(path: Path) -> None:
    """A folder of the common group, set-group-ID: what a session user writes in it is the group's."""
    path.mkdir(exist_ok=True)
    os.chown(path, -1, grp.getgrnam(ASSISTANT_GROUP).gr_gid)
    os.chmod(path, 0o2770)


def _create_task_folders(home: Path, *, work: bool = True) -> None:
    """The task's folders, made once, before any session has run in them: the engine's own gate
    (``home``, 0700) holding ``work`` and ``claude`` (and Claude Code's ``sessions`` folder, which it
    makes readable by its user alone), shared with the session users' group, and later the engine's
    logs. The session cannot write in the gate, so it cannot replace any of them."""
    home.mkdir(exist_ok=True)
    os.chmod(home, 0o700)
    for path in (
        *((home / "work", home / "work" / "tmp") if work else ()),
        home / "claude",
        home / "claude" / "sessions",
    ):
        _shared_dir(path)


def make_folders(folder: Path) -> None:
    """The working folder of a task. In a container its folders are made once, with the gate around
    them; a task whose folders exist is left as it is (a session has run in them)."""
    if not container():
        folder.mkdir(parents=True, exist_ok=True)
    elif not folder.exists():
        _create_task_folders(folder.parent)


def _directory(folder: Path) -> int:
    """The working folder as an open directory, never through a symbolic link at its end."""
    return os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def ensure_tmp(folder: Path) -> None:
    """The session's scratch folder, ``tmp`` in the working folder. A session can replace it, so a
    link or a file in its place is removed and never followed, and a folder that is there is left
    as it is: the engine changes nothing a session may have shaped."""
    descriptor = _directory(folder)
    try:
        try:
            found = os.stat("tmp", dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            found = None
        if found is not None and stat.S_ISDIR(found.st_mode):
            return
        if found is not None:
            os.unlink("tmp", dir_fd=descriptor)
        os.mkdir("tmp", 0o770, dir_fd=descriptor)
        made = os.open("tmp", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        try:
            if container():
                os.fchown(made, -1, grp.getgrnam(ASSISTANT_GROUP).gr_gid)
            os.fchmod(made, 0o2770 if container() else 0o770)
        finally:
            os.close(made)
    finally:
        os.close(descriptor)


def put(folder: Path, name: str, data: bytes) -> None:
    """A file the engine hands the session: made new, never through a link that is in its place."""
    descriptor = _directory(folder)
    try:
        try:
            os.unlink(name, dir_fd=descriptor)
        except FileNotFoundError:
            pass
        made = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o660,
            dir_fd=descriptor,
        )
        try:
            os.fchmod(made, 0o660)
            view = memoryview(data)
            while view:
                view = view[os.write(made, view) :]
        finally:
            os.close(made)
    finally:
        os.close(descriptor)


def drop(folder: Path, name: str) -> None:
    """Remove a file of the working folder: a link is removed, never followed."""
    descriptor = _directory(folder)
    try:
        os.unlink(name, dir_fd=descriptor)
    except FileNotFoundError, IsADirectoryError, PermissionError:
        pass
    finally:
        os.close(descriptor)


READ_LIMIT = 8 * 1024 * 1024


def read_work(folder: Path, name: str, limit: int = READ_LIMIT) -> str | None:
    """What the session wrote: a regular file of the working folder of at most ``limit`` bytes, opened
    without following a link; otherwise nothing."""
    try:
        descriptor = _directory(folder)
    except OSError:
        return None
    try:
        opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    except OSError:
        return None
    finally:
        os.close(descriptor)
    try:
        found = os.fstat(opened)
        if not stat.S_ISREG(found.st_mode) or found.st_size > limit:
            return None
        with os.fdopen(opened, "rb", closefd=False) as handle:
            return handle.read(limit + 1).decode(errors="replace")
    finally:
        os.close(opened)


def _transcripts(files: Any = None, task: AiTask | None = None) -> Path:
    """Where Claude Code keeps a session's transcript: outside the working folder and any retention.
    In a container each task has a folder of its own, inside the task's folder."""
    if container():
        return home_of(files, task) / "claude" / "projects"
    home = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return (Path(home) if home else Path.home() / ".claude") / "projects"


def _transcript_name(folder: Path) -> str:
    """Claude Code names the directory after the folder's path, each other character a hyphen."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(folder))


def remove_folder(files: Any, task: AiTask) -> None:
    """The session's folder and its transcript (AP-D37). A session that ran and left no transcript
    where one is expected is said in the log: the name is Claude Code's, and may change."""
    folder = folder_of(files, task)
    transcripts = _transcripts(files, task)
    transcript = transcripts / _transcript_name(folder)
    if (task.design or {}).get("agentSession") and transcripts.is_dir() and not transcript.is_dir():
        log.warning("No transcript at %s for task %s", transcript, task.public_id)
    shutil.rmtree(home_of(files, task), ignore_errors=True)
    if container() and home_of(files, task).exists():
        # A file of a mode the engine cannot remove (a folder a session user made for itself).
        log.warning("Task %s's folder could not be removed in full", task.public_id)
    if not container():
        shutil.rmtree(transcript, ignore_errors=True)
        for log_file in folder.parent.glob(f"{folder.name}.*.log"):
            log_file.unlink(missing_ok=True)


def sweep(session: Session, files: Any) -> None:
    """What no task holds any more: the folder of a task that expired, and a transcript of this
    instance's folders whose folder is gone (AP-D37). Removed after the expiry's commit. In a
    container a folder is known by the random name its task keeps, and one still named by a task's
    ID is renamed (``ensure_folder``): the first sweep after the upgrade does it."""
    root = agent_root(files)
    if container():
        _sweep_container(session, files, root)
        return
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


# A folder no task names is left alone this long: its task may be committing its name (0.17 RF5).
FRESH_SECONDS = 3600


def _sweep_container(session: Session, files: Any, root: Path) -> None:
    if not root.is_dir():
        return
    _open_root(root)
    names = [path.name for path in root.iterdir() if path.is_dir() and not path.is_symlink()]
    rows = session.execute(
        select(AiTask.public_id, AiTask.design[FOLDER_KEY].as_string()).where(
            or_(AiTask.public_id.in_(names), AiTask.design[FOLDER_KEY].as_string().in_(names))
        )
    ).all()
    named = {folder for _, folder in rows if folder}
    old_names = dict(rows)
    for name in names:
        if name in named:
            continue
        if name in old_names:
            # A task's folder under the name its ID gave it: moved into its random name, which is
            # committed first, or the task is given one now.
            if old_names[name]:
                _adopt_legacy(root, name, old_names[name])
            else:
                ensure_folder(session, files, name)
        elif time.time() - (root / name).lstat().st_mtime > FRESH_SECONDS:
            shutil.rmtree(root / name, ignore_errors=True)
    # The turns' logs lay beside the folders, named after the task, before 0.17.
    for path in root.glob("*.log"):
        path.unlink(missing_ok=True)
    close_idle_gates(root, slots_of(root))


def retention(_ctx: Any) -> int:
    return get_settings().ai_task_retention_days
