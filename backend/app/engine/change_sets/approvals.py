"""Proposing a change and approving it (Product 0.12 A1, ADR-045, D424-D427).

A holder of Work in change sets submits a change set; a holder of Approve publications decides it:
``approve`` publishes it in the same transaction, ``sendBack`` (with a comment) returns it to open.
A workspace's policy can require an approval for every publication (``requireApproval``) and a
second person to give it (``secondPerson``). Each submission and each decision is a row of its own
(D242, D427). A submitted change set is frozen against edits (``submissions.freeze``, D426).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    ApprovalPolicy,
    ChangeSet,
    ChangeSetDecision,
    ChangeSetSubmission,
    Publication,
)
from ..authorization.catalogue import ACTIONS, group_names
from ..authorization.permissions import Permissions
from ..authorization.writes import requester_of
from ..identity import security_events
from ..identity.principals import Ref, columns, ref
from ..model.registry import resolve_model_snapshot
from ..records.proposed import asker_of
from ..workspaces.catalogue import load_workspace
from ..workspaces.workspace_audit import record_submission_event
from .access import change_set_model, load_change_set
from .announcements import APPROVED as ANNOUNCE_APPROVED
from .announcements import SENT_BACK as ANNOUNCE_SENT_BACK
from .announcements import SUBMITTED as ANNOUNCE_SUBMITTED
from .announcements import announce
from .publish import apply_publication, lock_workspace_for_publication
from .submissions import (
    APPROVED,
    SENT_BACK,
    SUBMITTED,
    open_submission,
    require_may_withdraw,
    withdraw,
)
from .validation import validate_change_set

POLICY_AGGREGATE = "approval-policy"
# How many diagnostics a ``CHANGE_SET_INVALID`` refusal carries; ``validation`` lists them all.
_DIAGNOSTICS_SHOWN = 20


# --- the policy ---------------------------------------------------------------------------------


def load_policy(
    session: Session, workspace_key: str, *, for_update: bool = False
) -> ApprovalPolicy | None:
    statement = select(ApprovalPolicy).where(ApprovalPolicy.workspace_key == workspace_key)
    return session.scalar(statement.with_for_update() if for_update else statement)


def policy_flags(session: Session, workspace_key: str) -> tuple[bool, bool]:
    """``(requireApproval, secondPerson)``; both off for a workspace without a policy row."""
    row = load_policy(session, workspace_key)
    return (row.require_approval, row.second_person) if row is not None else (False, False)


def write_policy(
    session: Session,
    workspace_key: str,
    require_approval: bool,
    second_person: bool,
    expected_version: int,
) -> tuple[bool, bool, int]:
    """Set a workspace's policy; commits. The version is 0 until a policy is first saved. Returns
    ``(requireApproval, secondPerson, version)``."""
    load_workspace(session, workspace_key)
    if second_person and not require_approval:
        raise api_error(
            422,
            "APPROVAL_POLICY_INVALID",
            "A second person can only be required when approval is required",
            {"field": "secondPerson"},
        )
    row = load_policy(session, workspace_key, for_update=True)
    current = row.version if row is not None else 0
    if expected_version != current:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "The approval policy has changed",
            {"currentVersion": current},
        )
    new = {"requireApproval": require_approval, "secondPerson": second_person}
    if row is None:
        row = ApprovalPolicy(
            workspace_key=workspace_key,
            require_approval=require_approval,
            second_person=second_person,
            version=1,
        )
        session.add(row)
        changed, action = list(new), "created"
    else:
        was = {"requireApproval": row.require_approval, "secondPerson": row.second_person}
        changed, action = [name for name in new if new[name] != was[name]], "updated"
        if changed:
            row.require_approval, row.second_person = require_approval, second_person
            row.version += 1
    if changed:
        session.flush()
        security_events.record(
            session,
            POLICY_AGGREGATE,
            workspace_key,
            action,
            version=row.version,
            details=security_events.changed(changed, **new),
        )
    session.commit()
    return row.require_approval, row.second_person, row.version


# --- submitting and withdrawing -------------------------------------------------------------------


def submit(
    session: Session, change_set_id: str, expected_version: int, comment: str | None
) -> ChangeSetSubmission:
    """Submit a change set for publication; commits. Needs the version the submitter read
    (``409 VERSION_CONFLICT``), a change set not yet submitted (``409 CHANGE_SET_SUBMITTED``) and
    one that validates (``409 CHANGE_SET_INVALID``)."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    if change_set.version != expected_version:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "The change set has changed since it was read",
            {"currentVersion": change_set.version},
        )
    if open_submission(session, change_set_id, for_update=True) is not None:
        raise api_error(
            409, "CHANGE_SET_SUBMITTED", "This change set is already submitted for publication"
        )
    diagnostics = validate_change_set(session, change_set_id, change_set_model(session, change_set))
    if diagnostics:
        raise api_error(
            409,
            "CHANGE_SET_INVALID",
            "The change set does not validate and cannot be submitted; "
            f"{len(diagnostics)} problem{'s' if len(diagnostics) > 1 else ''} to fix first",
            {"count": len(diagnostics), "diagnostics": diagnostics[:_DIAGNOSTICS_SHOWN]},
        )
    submission = ChangeSetSubmission(
        workspace_key=change_set.workspace_key,
        change_set_id=change_set.id,
        change_set_name=change_set.name,
        version_submitted=change_set.version,
        comment=comment,
        state=SUBMITTED,
        **columns(asker_of(session), "submitted_by"),
    )
    session.add(submission)
    session.flush()
    record_submission_event(
        session,
        submission=submission,
        action="submitted",
        version=change_set.version,
        changes={"submissionId": submission.id, "name": change_set.name},
    )
    announce(session, submission, ANNOUNCE_SUBMITTED, version=change_set.version)
    session.commit()
    return submission


def withdraw_submission(session: Session, change_set_id: str) -> None:
    """Withdraw the change set's submission; commits. The submitter, or a holder of Approve
    publications in the workspace, may (``submissions.require_may_withdraw``)."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    submission = _require_submitted(session, change_set_id)
    require_may_withdraw(session, submission, change_set.workspace_key)
    withdraw(session, submission, change_set.version)
    session.commit()


def _submitter(submission: ChangeSetSubmission) -> Ref | None:
    return ref(submission.submitted_by_user_id, submission.submitted_by_client_id)


def _require_submitted(session: Session, change_set_id: str) -> ChangeSetSubmission:
    submission = open_submission(session, change_set_id, for_update=True)
    if submission is None:
        raise api_error(409, "NOT_SUBMITTED", "This change set is not submitted for publication")
    return submission


# --- deciding -----------------------------------------------------------------------------------


def _record_decision(
    session: Session,
    submission: ChangeSetSubmission,
    outcome: str,
    version: int,
    comment: str | None,
) -> ChangeSetDecision:
    decision = ChangeSetDecision(
        submission_sequence_id=submission.sequence_id,
        outcome=outcome,
        version=version,
        comment=comment,
        **columns(requester_of(session), "decided_by"),
    )
    session.add(decision)
    session.flush()
    return decision


def _approved(
    session: Session,
    submission: ChangeSetSubmission,
    publication: Publication,
    version: int,
    comment: str | None,
) -> None:
    decision = _record_decision(session, submission, "approve", version, comment)
    submission.state = APPROVED
    submission.publication_id = publication.id
    session.flush()
    record_submission_event(
        session,
        submission=submission,
        action="approved",
        version=version,
        changes={
            "submissionId": submission.id,
            "decisionId": decision.id,
            "publicationId": publication.id,
        },
    )
    announce(
        session,
        submission,
        ANNOUNCE_APPROVED,
        version=version,
        decider=requester_of(session),
        comment=comment,
        publication_id=publication.id,
    )


def decide(
    session: Session,
    change_set_id: str,
    *,
    outcome: str,
    comment: str | None,
    expected_version: int,
    expected_active_publication_id: str | None,
) -> Publication | ChangeSet:
    """Decide a submitted change set; commits. ``approve`` publishes it in the same transaction,
    bound to the version and the active publication seen, and answers the publication;
    ``sendBack`` needs a comment and answers the change set, open again.

    Refused: ``422 COMMENT_REQUIRED``, ``409 NOT_SUBMITTED``, ``403 FORBIDDEN`` with
    ``details.reason`` ``ownApproval`` under ``secondPerson``, ``409 VERSION_CONFLICT`` for a change
    set changed since it was read, ``409 PUBLICATION_CONFLICT`` for a changed active publication.
    Nothing is recorded by a refusal."""
    comment = comment.strip() if comment else None
    if outcome == "sendBack" and not comment:
        raise api_error(
            422,
            "COMMENT_REQUIRED",
            "Sending a change set back needs a comment",
            {"field": "comment"},
        )
    if outcome != "sendBack":
        # A decision that publishes locks as a publication does: workspace, then change set.
        lock_workspace_for_publication(session, change_set_id)
    change_set = load_change_set(session, change_set_id, for_update=True)
    submission = _require_submitted(session, change_set_id)
    _require_second_person(session, submission)
    # The decision binds the version read and the version submitted: a change set that no longer
    # is what was submitted is not decided (0.12 R-F7).
    if change_set.version != expected_version or change_set.version != submission.version_submitted:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "The change set has changed since it was read",
            {"currentVersion": change_set.version},
        )
    if outcome == "sendBack":
        decision = _record_decision(session, submission, "sendBack", expected_version, comment)
        submission.state = SENT_BACK
        session.flush()
        record_submission_event(
            session,
            submission=submission,
            action="sent-back",
            version=change_set.version,
            changes={"submissionId": submission.id, "decisionId": decision.id},
        )
        announce(
            session,
            submission,
            ANNOUNCE_SENT_BACK,
            version=change_set.version,
            decider=requester_of(session),
            comment=comment,
        )
        session.commit()
        return change_set
    workspace_active = _active_publication_id(session, change_set.workspace_key)
    if workspace_active != expected_active_publication_id:
        raise api_error(
            409,
            "PUBLICATION_CONFLICT",
            "The workspace's active publication has changed since it was read",
            {"activePublicationId": workspace_active},
        )
    publication = _publish(session, change_set, expected_version, expected_active_publication_id)
    _approved(session, submission, publication, expected_version, comment)
    session.commit()
    return publication


def _publish(
    session: Session, change_set: ChangeSet, expected_version: int, expected_active: str | None
) -> Publication:
    """Publish the change set in the caller's transaction, as ``POST …/publication`` does."""
    snapshot = resolve_model_snapshot(session, change_set.workspace_key)
    return apply_publication(
        session,
        change_set.id,
        change_set_model(session, change_set),
        snapshot.release_db_id,
        expected_version,
        expected_active,
    )


def _active_publication_id(session: Session, workspace_key: str) -> str | None:
    return load_workspace(session, workspace_key).active_publication_id


def _require_second_person(session: Session, submission: ChangeSetSubmission) -> None:
    """Under ``secondPerson``, the person who submitted does not decide their own (D425)."""
    _, second_person = policy_flags(session, submission.workspace_key)
    if second_person and _submitter(submission) == requester_of(session):
        raise api_error(
            403,
            "FORBIDDEN",
            "This workspace requires a second person to decide a change set; you submitted this one",
            {
                "action": "change-sets.decide",
                "groups": ["approve"],
                "workspaceKey": submission.workspace_key,
                "reason": "ownApproval",
            },
        )


# --- publishing directly ------------------------------------------------------------------------


def require_direct_publication(
    session: Session, workspace_key: str, permissions: Permissions | None
) -> bool:
    """What publishing a change set directly needs in ``workspace_key``, for every path that
    publishes one (0.12 R-F3): Publish there (``403 FORBIDDEN``), and under the workspace's policy
    an approval (``409 APPROVAL_REQUIRED``) unless the caller holds Approve publications and no
    second person is required. ``permissions`` is None for the engine's own. Returns whether the
    policy requires approval."""
    if permissions is not None and not permissions.allows("publish", workspace_key):
        action = ACTIONS["change-sets.publish"]
        raise api_error(
            403,
            "FORBIDDEN",
            f"{action.doing} in workspace '{workspace_key}' needs {group_names(action.groups)}",
            {
                "action": action.key,
                "groups": list(action.groups),
                "workspaceKey": workspace_key,
            },
        )
    require_approval, second_person = policy_flags(session, workspace_key)
    if require_approval and (
        second_person
        or (permissions is not None and not permissions.allows("approve", workspace_key))
    ):
        raise api_error(
            409,
            "APPROVAL_REQUIRED",
            "This workspace requires an approval to publish: submit the change set for "
            "publication" + (", to be approved by someone else" if second_person else ""),
            {"workspaceKey": workspace_key, "secondPerson": second_person},
        )
    return require_approval


def close_request_on_publication(
    session: Session,
    change_set_id: str,
    workspace_key: str,
    name: str,
    publication: Publication,
    version: int,
    *,
    require_approval: bool,
) -> None:
    """After a direct publication, in the caller's transaction: the request still open for the
    change set is closed as approved by it, and under ``requireApproval`` one is made for it, so
    the publication records an approval as the publisher's own decision."""
    submission = open_submission(session, change_set_id, for_update=True)
    if submission is None and require_approval:
        submission = ChangeSetSubmission(
            workspace_key=workspace_key,
            change_set_id=change_set_id,
            change_set_name=name,
            version_submitted=version,
            state=SUBMITTED,
            **columns(requester_of(session), "submitted_by"),
        )
        session.add(submission)
        session.flush()
    if submission is not None:
        _approved(session, submission, publication, version, None)


def publish_directly(
    session: Session,
    change_set_id: str,
    permissions: Permissions,
    *,
    expected_version: int,
    expected_active_publication_id: str | None,
) -> Publication:
    """``POST /change-sets/{id}/publication`` under the workspace's policy (D425); commits.

    With ``requireApproval`` a caller holding Approve publications publishes in one step, which
    records an approval as their own decision (on the open request, or on one made for it), unless
    ``secondPerson`` is on; any other caller is refused ``409 APPROVAL_REQUIRED``. Without it
    nothing changes, except that a request still open for the change set is closed as approved by
    its publication."""
    change_set = load_change_set(session, change_set_id)
    workspace_key, name = change_set.workspace_key, change_set.name
    require_approval = require_direct_publication(session, workspace_key, permissions)
    publication = _publish(session, change_set, expected_version, expected_active_publication_id)
    close_request_on_publication(
        session,
        change_set_id,
        workspace_key,
        name,
        publication,
        expected_version,
        require_approval=require_approval,
    )
    session.commit()
    return publication
