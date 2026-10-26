"""Telling people and receivers of a step of a publication request (Product 0.12 A2, D233).

Each step of a request is announced in the transaction that makes it: a request **submitted** reaches
the inbox of every active person and client holding Approve publications in the workspace, except
the submitter; a request **approved** or **sent back** reaches the submitter's, unless they decided
it themselves. Any end of a request (withdrawn, approved, sent back) marks the "waiting for your
approval" notices of its change set read: it no longer waits. ``submitted``, ``approved`` and
``sent-back`` are also workspace events (``events.workspace_events``) for webhook subscriptions;
withdrawing is no event. The event is written last, before the caller's commit (its position is the
one lock taken late).
"""

from typing import Any

from sqlalchemy.orm import Session

from ...models.database import ChangeSetSubmission
from ..authorization.administration import holders_of
from ..events import workspace_events
from ..identity.principals import Ref, names, ref
from ..notifications import inbox

SUBMITTED, WITHDRAWN, APPROVED, SENT_BACK = "submitted", "withdrawn", "approved", "sent-back"
_EVENTS = {
    SUBMITTED: workspace_events.SUBMITTED,
    APPROVED: workspace_events.APPROVED,
    SENT_BACK: workspace_events.SENT_BACK,
}


def announce(
    session: Session,
    submission: ChangeSetSubmission,
    step: str,
    *,
    version: int,
    decider: Ref | None = None,
    comment: str | None = None,
    publication_id: str | None = None,
) -> None:
    """Announce ``step`` of ``submission`` (``comment`` is the decision's, a submission's own for
    ``submitted``); in the caller's transaction, last before its commit."""
    submitter = ref(submission.submitted_by_user_id, submission.submitted_by_client_id)
    if step != SUBMITTED:
        inbox.close_requests(session, submission.change_set_id)
    if step == WITHDRAWN:
        return
    comment = submission.comment if step == SUBMITTED else comment
    actor = submitter if step == SUBMITTED else decider
    people = names(session, [submitter, decider])
    if step == SUBMITTED:
        recipients = [
            found
            for found in holders_of(session, "approve", submission.workspace_key)
            if found != submitter
        ]
    else:
        recipients = [submitter] if submitter is not None and submitter != decider else []
    details: dict[str, Any] = {
        "changeSetName": submission.change_set_name,
        "version": version,
        "comment": comment,
        "actor": people.get(actor) if actor is not None else None,
        "publicationId": publication_id,
    }
    inbox.notify(
        session,
        recipients,
        kind=_EVENTS[step],
        workspace_key=submission.workspace_key,
        subject_kind="change-set",
        subject_id=submission.change_set_id,
        details=details,
    )
    workspace_events.record(
        session,
        submission.workspace_key,
        _EVENTS[step],
        submission.change_set_id,
        {
            "submissionId": submission.id,
            "changeSet": {
                "id": submission.change_set_id,
                "name": submission.change_set_name,
                "version": version,
            },
            "submitter": people.get(submitter) if submitter is not None else None,
            "decider": people.get(decider) if decider is not None else None,
            "comment": comment,
            "publicationId": publication_id,
        },
    )
