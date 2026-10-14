"""A stored profile's last load (0.10 A5c): the latest import job naming the profile, and what
became of what it loaded.

A load into a change set leaves the change set until it is published or discarded, and both delete
it; a publication's audit entry names the change set it came from, a discard leaves nothing. So the
outcome is ``live`` (loaded into live data), ``inChangeSet`` (its change set still holds it),
``published`` (a publication's entry names its change set) or ``discarded`` (the change set is gone
and no publication of it is on record); none while the job has not completed. Three statements per
read, whatever the number of profiles. A job past its retention is no longer found.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import AuditEvent, ChangeSet, Job

_COUNTS = ("created", "updated", "deleted", "rejected")


def last_loads(session: Session, keys: list[str]) -> dict[str, dict[str, Any]]:
    """Each of ``keys``' last load, by profile key; a profile never loaded is left out."""
    if not keys:
        return {}
    key = Job.parameters["profile"]["key"].as_string()
    jobs = session.scalars(
        select(Job)
        .where(Job.kind == "import", key.in_(keys))
        .distinct(key)
        .order_by(key, Job.sequence_id.desc())
    ).all()
    change_sets = {job.change_set_id for job in jobs if job.change_set_id is not None}
    open_sets = set(
        session.scalars(select(ChangeSet.id).where(ChangeSet.id.in_(change_sets)))
        if change_sets
        else ()
    )
    gone = change_sets - open_sets
    published: dict[str, str] = {}
    if gone:
        source = AuditEvent.changes["changeSetId"].as_string()
        for change_set_id, publication_id in session.execute(
            select(source, AuditEvent.aggregate_id).where(
                AuditEvent.aggregate_type == "publication",
                AuditEvent.action == "published",
                source.in_(gone),
            )
        ):
            published[change_set_id] = publication_id
    found: dict[str, dict[str, Any]] = {}
    for job in jobs:
        parameters = job.parameters
        outcome, publication_id = None, None
        if job.state == "completed":
            if job.change_set_id is None:
                outcome = "live"
            elif job.change_set_id in open_sets:
                outcome = "inChangeSet"
            elif job.change_set_id in published:
                outcome, publication_id = "published", published[job.change_set_id]
            else:
                outcome = "discarded"
        counts = job.counts or {}
        found[parameters["profile"]["key"]] = {
            "jobId": job.id,
            "state": job.state,
            "fileName": (parameters.get("file") or {}).get("name"),
            "sourceFileId": parameters.get("sourceFileId"),
            "workspaceKey": job.workspace_key,
            "changeSetId": job.change_set_id,
            "createdAt": job.created_at,
            "finishedAt": job.finished_at,
            "counts": {name: counts.get(name, 0) for name in _COUNTS},
            "outcome": outcome,
            "publicationId": publication_id,
        }
    return found
