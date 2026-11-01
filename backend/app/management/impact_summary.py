"""What a summary of a model change is made from, read for the routes (Product 0.16 AO1).

A release is compared with the release the workspace runs; a draft with the release it is based on,
as its compilation is. Either way the workspace's data is checked against the candidate as
activating it there would.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..engine.model.authoring.released import base_release
from ..engine.model.compatibility import analyze_compatibility
from ..engine.model.compiler import SCHEMA_VERSIONS, CompilationResult, compile_model
from ..engine.model.consumer_contract import contract_diagnostics
from ..engine.model.diagnostics import ModelDiagnostic
from ..engine.model.diff import SemanticChange, semantic_diff
from ..engine.model.drafts import load_draft, require_draft_version
from ..engine.model.registry import resolve_model_snapshot
from ..engine.proposals import impact_summary
from ..errors import api_error
from ..models.database import ModelRelease
from .presenters import diagnostic_details
from .schemas.ai import ImpactFact, ImpactStatement, ImpactSummaryResponse


@dataclass(frozen=True)
class Inputs:
    workspace_key: str
    baseline: dict[str, Any]
    candidate: dict[str, Any]
    changes: tuple[SemanticChange, ...]
    compatibility: tuple[ModelDiagnostic, ...]
    contract: list[ModelDiagnostic]


def _installed(release: ModelRelease) -> CompilationResult:
    """An installed release, compiled; one this version cannot read is refused as a diff refuses it."""
    compiled = compile_model(release.model_json)
    if compiled.valid and compiled.model is not None and compiled.canonical_model is not None:
        return compiled
    if compiled.unsupported_schema_version is not None:
        raise api_error(
            422,
            "UNSUPPORTED_SCHEMA_VERSION",
            f"Release '{release.public_id}' uses schema version"
            f" '{compiled.unsupported_schema_version}' which this deployment cannot interpret"
            " for comparison",
            {
                "releaseId": release.public_id,
                "schemaVersion": compiled.unsupported_schema_version,
                "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                "operation": "impact-summary",
            },
        )
    raise api_error(
        500,
        "INVALID_INSTALLED_MODEL",
        "An installed model release failed validation",
        diagnostic_details(compiled.diagnostics),
    )


def release_inputs(session: Session, release_id: str, workspace_key: str) -> Inputs:
    """``release_id`` against the release ``workspace_key`` runs."""
    snapshot = resolve_model_snapshot(session, workspace_key)
    rows = {
        row.public_id: row
        for row in session.scalars(
            select(ModelRelease).where(
                ModelRelease.public_id.in_([release_id, snapshot.release_id])
            )
        )
    }
    candidate_row = rows.get(release_id)
    if candidate_row is None:
        raise api_error(404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found")
    baseline_row = rows[snapshot.release_id]
    candidate, baseline = _installed(candidate_row), _installed(baseline_row)
    assert candidate.model and candidate.canonical_model and baseline.canonical_model
    return Inputs(
        snapshot.workspace_key or workspace_key,
        baseline.canonical_model,
        candidate.canonical_model,
        semantic_diff(baseline.canonical_model, candidate.canonical_model),
        analyze_compatibility(
            session, snapshot.model, candidate.model, snapshot.release_id, [workspace_key]
        ).diagnostics,
        contract_diagnostics(snapshot.model, candidate.model),
    )


def draft_inputs(
    session: Session, draft_id: str, expected_version: int, workspace_key: str
) -> Inputs:
    """A draft against the release it is based on; an invalid draft cannot be summarised."""
    draft = load_draft(session, draft_id)
    require_draft_version(draft, expected_version)
    compiled = compile_model(draft.model_json)
    if not compiled.valid or compiled.model is None or compiled.canonical_model is None:
        raise api_error(
            422,
            "IMPACT_SUMMARY_DRAFT_INVALID",
            "The draft is not valid, so what it changes cannot be summarised; its issues are"
            " listed by its compilation",
            diagnostic_details(compiled.diagnostics),
        )
    snapshot = resolve_model_snapshot(session, workspace_key)
    base = base_release(session, draft)
    baseline = _installed(base) if base is not None else None
    baseline_document = baseline.canonical_model if baseline and baseline.canonical_model else {}
    return Inputs(
        snapshot.workspace_key or workspace_key,
        baseline_document,
        compiled.canonical_model,
        semantic_diff(baseline_document, compiled.canonical_model),
        analyze_compatibility(
            session, snapshot.model, compiled.model, snapshot.release_id, [workspace_key]
        ).diagnostics,
        contract_diagnostics(baseline.model, compiled.model)
        if baseline is not None and baseline.model is not None
        else [],
    )


def facts_of(session: Session, inputs: Inputs) -> list[impact_summary.Fact]:
    return impact_summary.build_facts(
        session,
        workspace_key=inputs.workspace_key,
        baseline=inputs.baseline,
        candidate=inputs.candidate,
        changes=inputs.changes,
        compatibility=inputs.compatibility,
        contract=inputs.contract,
    )


def response(summary: impact_summary.Summary) -> ImpactSummaryResponse:
    return ImpactSummaryResponse(
        facts=[
            ImpactFact(id=fact.id, kind=fact.kind, text=fact.text, path=fact.path, count=fact.count)
            for fact in summary.facts
        ],
        statements=[
            ImpactStatement(text=item.text, factIds=list(item.fact_ids))
            for item in summary.statements
        ],
        removedStatements=summary.removed,
        failure=summary.failure,
        cached=summary.cached,
        callId=summary.call_id,
    )
