"""Publication requests as a read shows them (0.12 A1): a submission with its submitter and its
decisions' deciders named as they are now, a page's principals and decisions read in one statement
each."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from ...engine.identity.principals import names, ref
from ...models.database import ChangeSetDecision, ChangeSetSubmission
from ..schemas.approvals import DecisionResponse, PublicationRequestResponse


def latest_submissions(
    session: Session, change_set_ids: Iterable[str]
) -> dict[str, ChangeSetSubmission]:
    """Each change set's latest submission, whatever its state; none for one never submitted."""
    ids = list(change_set_ids)
    if not ids:
        return {}
    rows = session.scalars(
        select(ChangeSetSubmission)
        .where(ChangeSetSubmission.change_set_id.in_(ids))
        .ext(distinct_on(ChangeSetSubmission.change_set_id))
        .order_by(ChangeSetSubmission.change_set_id, ChangeSetSubmission.sequence_id.desc())
    )
    return {row.change_set_id: row for row in rows}


def request_responses(
    session: Session, rows: list[ChangeSetSubmission]
) -> list[PublicationRequestResponse]:
    decisions: dict[int, list[ChangeSetDecision]] = {}
    if rows:
        for decision in session.scalars(
            select(ChangeSetDecision)
            .where(ChangeSetDecision.submission_sequence_id.in_([row.sequence_id for row in rows]))
            .order_by(ChangeSetDecision.sequence_id)
        ):
            decisions.setdefault(decision.submission_sequence_id, []).append(decision)
    principals = names(
        session,
        [ref(row.submitted_by_user_id, row.submitted_by_client_id) for row in rows]
        + [
            ref(item.decided_by_user_id, item.decided_by_client_id)
            for items in decisions.values()
            for item in items
        ],
    )
    return [
        PublicationRequestResponse(
            id=row.id,
            workspaceKey=row.workspace_key,
            changeSetId=row.change_set_id,
            changeSetName=row.change_set_name,
            version=row.version_submitted,
            state=row.state,
            submitter=principals.get(ref(row.submitted_by_user_id, row.submitted_by_client_id)),
            comment=row.comment,
            submittedAt=row.submitted_at,
            publicationId=row.publication_id,
            decisions=[
                DecisionResponse(
                    id=item.id,
                    outcome=item.outcome,
                    version=item.version,
                    comment=item.comment,
                    decidedAt=item.decided_at,
                    decider=principals.get(ref(item.decided_by_user_id, item.decided_by_client_id)),
                )
                for item in decisions.get(row.sequence_id, [])
            ],
        )
        for row in rows
    ]


def submission_responses(
    session: Session, change_set_ids: Iterable[str]
) -> dict[str, PublicationRequestResponse]:
    """The ``submission`` of each change set that has one, by change set ID."""
    latest = latest_submissions(session, change_set_ids)
    found = request_responses(session, list(latest.values()))
    return dict(zip(latest, found, strict=True))
