"""The ``aiProposal`` job: targets for the unmapped sources of a mapping view, written into a change
set (Product 0.16 AP2, AP2-D1 to AP2-D6).

``queue`` checks the request and creates the job (and the change set, when the request names one to
create). The worker's first step binds: every unmapped source of the view becomes an input, with the
candidates it may take (``mapping_selection``), in PostgreSQL. Each later step takes ``BATCH``
inputs, builds the provider's request, ends its transaction, asks, and then writes what the answer
chose in a transaction of its own: through the same rules as a hand edit (the set replacement of the
mapping PUT, decided over a batch lookup and written by the write unit), each source's set version
token being the one bound with its input, so a source mapped meanwhile is refused and counted. The
change set's version is claimed once per step, from its current version, so a person editing
meanwhile never stops the job. Cancelling keeps what earlier steps wrote.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import Job
from ...models.schema import MappingGridViewConfig, MappingGridViewDefinition
from ..authorization.requesters import requested_by
from ..change_sets.access import change_set_model, ensure_change_set_writable
from ..change_sets.lifecycle import create_change_set
from ..change_sets.pinning import pinned_model
from ..indexes import matrix_states
from ..jobs.store import complete_job, load_inputs, start_job
from ..model import registry
from ..model.registry import resolve_model_snapshot
from ..model.workspace_models import load_assignment
from ..reads.mapping_projection import change_set_mapping_projection
from ..reads.mapping_scope import MappingScope
from ..records.audit import audit_cause
from ..records.batch_lookup import ChangeSetBatchLookup
from ..records.bulk import write_change_set
from ..records.relation_sets import SetBinding, SetTarget, decide_set_replacement
from ..records.writes import ChangeSetWrites
from ..workspaces.catalogue import resolve_workspace
from . import calls
from .mapping_selection import bind as bind_inputs
from .mapping_targets import (
    BATCH,
    PROMPT_VERSION,
    Choices,
    batch_of,
    chosen,
    fits,
    has_candidates,
    request,
    sized,
)
from .registry import AiConfiguration

KIND = "aiProposal"
# The warnings a job keeps: a provider failing every call would otherwise fill the report.
MAX_WARNINGS = 10


@dataclass
class Tally:
    """What the job has done so far; ``report["aiProposal"]`` as it reads."""

    proposed: int = 0
    unmatched: int = 0
    changed: int = 0
    refused: int = 0
    not_answered: int = 0
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def of(cls, report: dict[str, Any]) -> Tally:
        found = report.get("aiProposal") or {}
        return cls(
            found.get("proposed", 0),
            found.get("unmatched", 0),
            found.get("changed", 0),
            found.get("refused", 0),
            found.get("notAnswered", 0),
            list(found.get("warnings", [])),
        )

    def warn(self, message: str) -> None:
        if message not in self.warnings and len(self.warnings) < MAX_WARNINGS:
            self.warnings.append(message)

    def result(self, change_set_id: str) -> dict[str, Any]:
        return {
            "proposed": self.proposed,
            "unmatched": self.unmatched,
            "changed": self.changed,
            "refused": self.refused,
            "notAnswered": self.not_answered,
            "changeSetId": change_set_id,
            "warnings": self.warnings,
        }


def queue(
    session: Session,
    workspace_key: str,
    *,
    application_key: str,
    view_key: str,
    search: str | None,
    parent_object_id: str | None,
    change_set_id: str | None,
    expected_change_set_version: int | None,
    change_set_name: str | None,
    send_level: str | None,
    retention_days: int,
) -> Job:
    """Queue the proposal job and commit it; creates the change set when ``change_set_name`` is
    given. Refused before a job exists: ``404 CHANGE_SET_NOT_FOUND``, ``409
    CHANGE_SET_VERSION_CONFLICT``, ``404 MAPPING_VIEW_NOT_FOUND``, ``404 MAPPING_PARENT_NOT_FOUND``
    and the change set's own refusals (a retired workspace)."""
    resolve_workspace(session, workspace_key, require_active=True)
    if change_set_id is not None:
        change_set = ensure_change_set_writable(session, change_set_id)
        if change_set.workspace_key != workspace_key:
            raise api_error(404, "CHANGE_SET_NOT_FOUND", "Change set not found")
        if change_set.version != expected_change_set_version:
            raise api_error(409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed")
    else:
        active_release_id = load_assignment(session, workspace_key)[1].id
        resolve_model_snapshot(session, workspace_key)
        change_set = create_change_set(
            session,
            workspace_key,
            active_release_id,
            name=change_set_name,
            source="currentLive",
            expected_model_runtime_release_id=active_release_id,
        )
    model = change_set_model(session, change_set)
    config = view_config(model, application_key, view_key)
    if parent_object_id is not None:
        objects, _ = change_set_mapping_projection(session, change_set.id)
        if (
            session.execute(
                objects.select().where(objects.c.id == parent_object_id).limit(1)
            ).first()
            is None
        ):
            raise api_error(
                404,
                "MAPPING_PARENT_NOT_FOUND",
                "Parent object not found in the selected context",
            )
    job = start_job(
        session,
        kind=KIND,
        workspace_key=workspace_key,
        change_set_id=change_set.id,
        model_release_id=change_set.model_release_id,
        parameters={
            "applicationKey": application_key,
            "viewKey": view_key,
            "relationTypeKey": config.relationTypeKey,
            "parentObjectId": parent_object_id,
            "search": search,
            "sendLevel": send_level,
            "promptVersion": PROMPT_VERSION,
        },
        total=None,
        retention_days=retention_days,
        queued=True,
        change_set_version=change_set.version,
    )
    session.commit()
    return job


def view_config(model: Any, application_key: str, view_key: str) -> MappingGridViewConfig:
    application = next((row for row in model.applications if row.key == application_key), None)
    view = (
        next((row for row in application.views if row.key == view_key), None)
        if application
        else None
    )
    if not isinstance(view, MappingGridViewDefinition):
        raise api_error(
            404, "MAPPING_VIEW_NOT_FOUND", "Mapping view not found in the selected model"
        )
    return view.config


def _scope(session: Session, job: Job) -> MappingScope:
    assert job.change_set_id is not None
    change_set, model = pinned_model(session, job.change_set_id)
    config = view_config(model, job.parameters["applicationKey"], job.parameters["viewKey"])
    objects, relations = change_set_mapping_projection(session, change_set.id)
    return MappingScope(
        session, change_set.workspace_key, change_set.id, None, model, config, objects, relations
    )


def bind(session: Session, job: Job, context_tokens: int | None = None) -> None:
    """The job's first step: its inputs, its total and its first tally (the caller completes the
    job when there is nothing to ask about, and commits)."""
    assert job.change_set_id is not None
    scope = _scope(session, job)
    selection = bind_inputs(
        session,
        job,
        scope,
        application_key=job.parameters["applicationKey"],
        parent_object_id=job.parameters.get("parentObjectId"),
        search=job.parameters.get("search"),
        fits_whole_list=lambda whole: _first_fits(session, job, whole, context_tokens),
    )
    job.total = selection.total
    job.processed = 0
    job.stage = "proposing"
    report = dict(job.report or {})
    report["aiProposal"] = Tally().result(job.change_set_id)
    if selection.whole_list is not None:
        report["candidates"] = selection.whole_list
    job.report = report


def _first_fits(
    session: Session, job: Job, whole: list[dict[str, Any]], context_tokens: int | None
) -> bool:
    """Whether a call about one source with the whole list fits the model's window."""
    if context_tokens is None:
        return True
    probe = {"sourceId": "", "mappingVersion": 0, "name": "", "fields": {}}
    return fits(batch_of([probe], whole), context_tokens)


def step(
    session: Session,
    job: Job,
    ai: AiConfiguration,
    *,
    record: Any,
    hold: Any,
    retention_days: int,
    lease_seconds: int,
) -> None:
    """One step of a bound job: ``BATCH`` sources asked about and written; the caller has set the
    writer. ``hold(cancellable=True)`` locks the job row for the commit, holding the lease, and
    raises when the job was cancelled meanwhile, so nothing of the step is written then."""
    if ai.provider is None or not ai.offers("mappingTarget"):
        raise api_error(
            409,
            "AI_NOT_CONFIGURED",
            "The AI provider is no longer set up for this feature (AI_PROVIDER, AI_SEND_LEVEL); "
            "the proposals written before stay",
        )
    report = dict(job.report or {})
    whole_list = report.get("candidates")
    inputs = load_inputs(session, job, BATCH)
    # As many as fit the model's window (AI_CONTEXT_TOKENS, AP-D8); the rest wait for the next step.
    inputs = inputs[: sized([item for _, item in inputs], whole_list, ai.context_tokens)]
    tally = Tally.of(report)
    # A source with no candidate cannot be given one: it is not sent, and is left unmapped.
    empty = [item["sourceId"] for _, item in inputs if not has_candidates(item, whole_list)]
    asked = [item for _, item in inputs if has_candidates(item, whole_list)]
    batch = batch_of(asked, whole_list)
    too_large = bool(asked) and not fits(batch, ai.context_tokens)
    requester = calls.Requester(job.requested_by_user_id, job.requested_by_client_id)
    job_id, change_set_id = job.id, job.change_set_id
    assert change_set_id is not None
    proposed_by = (requested_by(session, job) or {}).get("id")
    # A provider may take minutes: end this transaction first, so none is held open while it
    # waits (J48.8). Nothing has been written in it.
    if session.new or session.dirty or session.deleted:
        raise RuntimeError("The proposal job wrote before asking the provider")
    session.commit()
    tally.unmatched += len(empty)
    choices = Choices([], [], list(batch.sources.values()))
    outcome = None
    if too_large:
        tally.warn(
            f"{len(asked)} source with its candidates is larger than half of AI_CONTEXT_TOKENS "
            f"({ai.context_tokens}); it is left unmapped"
        )
        tally.not_answered += len(asked)
    elif asked:
        outcome = calls.ask(ai, request(batch), record=record, requester=requester, job_id=job_id)
    if outcome is not None and outcome.answer is None:
        tally.warn(
            f"The AI provider failed for {len(asked)} sources ({outcome.failure}); "
            "they are left unmapped"
        )
        tally.not_answered += len(asked)
    elif outcome is not None:
        choices = chosen(outcome.answer, batch, ai.min_confidence)  # type: ignore[arg-type]
        tally.unmatched += len(choices.unmatched)
        tally.not_answered += len(choices.unanswered)
        if choices.unanswered:
            tally.warn("The AI provider left some sources without an answer; they stay unmapped")
    versions = {item["sourceId"]: item["mappingVersion"] for _, item in inputs}
    origins = {
        found.source_id: {
            "kind": "ai",
            "provider": outcome.provider,
            "model": outcome.model,
            "promptVersion": PROMPT_VERSION,
            "confidence": found.confidence,
            "reason": found.reason,
            "proposedBy": proposed_by,
        }
        for found in choices.chosen
    }
    written = _write(session, job, choices, versions, origins)
    tally.proposed += written.proposed
    tally.changed += written.changed
    tally.refused += written.refused
    for message in written.warnings:
        tally.warn(message)

    job.processed += len(inputs)
    counts = dict(job.counts)
    counts["applied"] = counts["created"] = tally.proposed
    counts["rejected"] = job.processed - tally.proposed
    job.counts = counts
    job.report = {**(job.report or {}), "aiProposal": tally.result(change_set_id)}
    hold(cancellable=True)
    if written.version is not None:
        job.change_set_version = written.version
    if job.processed >= (job.total or 0):
        complete_job(session, job, retention_days=retention_days)
    else:
        job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)
    session.commit()


@dataclass
class Written:
    proposed: int = 0
    changed: int = 0
    refused: int = 0
    warnings: list[str] = field(default_factory=list)
    version: int | None = None


def _write(
    session: Session,
    job: Job,
    choices: Choices,
    versions: dict[str, int],
    origins: dict[str, dict[str, Any]],
) -> Written:
    """Write the chosen targets into the job's change set, each as the mapping PUT would, deciding
    the step's sources together and writing once; then mark the relations written."""
    assert job.change_set_id is not None
    change_set = ensure_change_set_writable(session, job.change_set_id)
    written = Written(version=change_set.version)
    if not choices.chosen:
        return written
    config = view_config(
        change_set_model(session, change_set),
        job.parameters["applicationKey"],
        job.parameters["viewKey"],
    )
    model = change_set_model(session, change_set)
    set_ = SetBinding(
        config.relationTypeKey,
        config.fromObjectTypeKey,
        config.toObjectTypeKey,
        config.direction,
    )
    source_type = (
        config.fromObjectTypeKey if config.direction == "outgoing" else config.toObjectTypeKey
    )
    target_type = (
        config.toObjectTypeKey if config.direction == "outgoing" else config.fromObjectTypeKey
    )
    lookup = ChangeSetBatchLookup.of(session, change_set.id)
    lookup.prefetch_objects(
        [end for found in choices.chosen for end in (found.source_id, found.target_id)]
    )
    lookup.prefetch_set_versions([set_.key(found.source_id) for found in choices.chosen])
    relation_origins: dict[str, dict[str, Any]] = {}
    for found in choices.chosen:
        source, target = lookup.object(found.source_id), lookup.object(found.target_id)
        if (
            source is None
            or target is None
            or source.object_type_key != source_type
            or target.object_type_key != target_type
            or lookup.set_version(set_.key(found.source_id)) != versions[found.source_id]
        ):
            written.changed += 1
            continue
        try:
            with lookup.deciding():
                replaced = decide_set_replacement(
                    lookup,
                    model,
                    set_,
                    source,
                    [SetTarget(target, {})],
                    expected=versions[found.source_id],
                )
        except ApiError as error:
            if error.code == "RELATION_SET_VERSION_CONFLICT":
                written.changed += 1
            else:
                written.refused += 1
                written.warnings.append(
                    f"A proposed target was refused by the rules ({error.code}); "
                    "its source stays unmapped"
                )
            continue
        if not replaced.changed:
            written.changed += 1
            continue
        relation_origins[replaced.relations[found.target_id]] = origins[found.source_id]
        written.proposed += 1
    changes = lookup.changes()
    if not changes:
        return written
    outer = session.begin_nested()
    writes = ChangeSetWrites(session, change_set)
    with audit_cause(session, "job", job.id), matrix_states.deferred(session):
        writes.claim(change_set.version)
        write_change_set(writes, changes)
        writes.set_origins(relation_origins)
    registry.require_resolved_release(session)
    outer.commit()
    written.version = change_set.version
    return written


def result_of(job: Job) -> dict[str, Any] | None:
    return (job.report or {}).get("aiProposal")


__all__ = ["KIND", "Tally", "bind", "queue", "result_of", "step", "view_config"]
