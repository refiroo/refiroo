"""A change set submitted for publication, and what that freezes (Product 0.12 A1, D424-D427).

A change set is **submitted** while its latest submission is. Every write to a submitted change
set is refused ``409 CHANGE_SET_SUBMITTED`` unless the request carries ``withdrawSubmission=true``,
which withdraws the submission in the same transaction as the write (D426). The write unit's
version claim (``ChangeSetWrites.claim``) calls ``freeze``, so every path is covered once; this
module knows nothing of the write unit, so the unit can import it.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ChangeSet, ChangeSetSubmission
from ..workspaces.workspace_audit import record_submission_event

# The request's ``withdrawSubmission=true``, set on its session by the API tier (the engine imports
# no web framework).
_WITHDRAW = "withdraw_submission"

SUBMITTED = "submitted"
WITHDRAWN = "withdrawn"
APPROVED = "approved"
SENT_BACK = "sentBack"


def allow_withdrawal(session: Session, allowed: bool) -> None:
    """Let this session's writes to a submitted change set withdraw its submission."""
    if allowed:
        session.info[_WITHDRAW] = True
    else:
        session.info.pop(_WITHDRAW, None)


def open_submission(
    session: Session, change_set_id: str, *, for_update: bool = False
) -> ChangeSetSubmission | None:
    """The change set's submission while it is submitted, else None."""
    statement = select(ChangeSetSubmission).where(
        ChangeSetSubmission.change_set_id == change_set_id,
        ChangeSetSubmission.state == SUBMITTED,
    )
    return session.scalar(statement.with_for_update() if for_update else statement)


def withdraw(session: Session, submission: ChangeSetSubmission, version: int) -> None:
    """Mark a submission withdrawn and audit it, in the caller's transaction."""
    submission.state = WITHDRAWN
    session.flush()
    record_submission_event(
        session,
        submission=submission,
        action="withdrawn",
        version=version,
        changes={"submissionId": submission.id},
    )


def freeze(session: Session, change_set: ChangeSet) -> None:
    """Refuse a write to a submitted change set, or withdraw the submission when the request asked
    to (D426). Nothing for a change set that is not submitted."""
    submission = open_submission(session, change_set.id, for_update=True)
    if submission is None:
        return
    if not session.info.get(_WITHDRAW):
        raise api_error(
            409,
            "CHANGE_SET_SUBMITTED",
            "This change set is submitted for publication and cannot be changed; withdraw the "
            "submission, or send the change with withdrawSubmission=true to withdraw it",
            {"submissionId": submission.id, "withdraw": "withdrawSubmission=true"},
        )
    withdraw(session, submission, change_set.version)
