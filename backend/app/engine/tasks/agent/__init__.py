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

The package splits the task by concern: ``sandbox`` (the session's operating-system user, environment
and command), ``files`` (its folder and files), ``words`` (every prompt and refusal text), ``run`` (one
turn) and ``outcome`` (what the session reached, and the entry points). This module names what the rest
of the engine uses.
"""

from .files import ensure_folder, folder_of, home_of, remove_folder, resumable, retention, sweep
from .outcome import (
    accepted,
    end_session,
    lives,
    recover_load,
    retire_unused_releases,
    said,
    start,
)
from .run import SessionTimedOut, counts_of, timeout_seconds, undo_interrupted_load
from .sandbox import enabled

__all__ = [
    "SessionTimedOut",
    "accepted",
    "counts_of",
    "enabled",
    "end_session",
    "ensure_folder",
    "folder_of",
    "home_of",
    "lives",
    "recover_load",
    "remove_folder",
    "resumable",
    "retention",
    "retire_unused_releases",
    "said",
    "start",
    "sweep",
    "timeout_seconds",
    "undo_interrupted_load",
]
