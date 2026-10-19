"""A model draft's inference (Product 0.10 A6, D86–D98): the job that proposes, the reads, and the
application of its proposals.

``POST /model-drafts/{id}/inference`` queues a job of kind ``inference`` for the draft's current
source file. The worker reads the file's profile and the facts between its columns (``facts.py``),
finds the table patterns (``patterns.py``), builds a proposal of each (``build.py``) and compares it
with what the draft holds and whose it is (``compare.py``, D92):

- a proposal of an **anchor** no step applied yet is ``open``, unless a column it binds is bound
  already (``held``, with a disagreement where it reads the column otherwise) or the same proposal
  was undone before (``rejected``);
- a proposal an earlier step applied keeps that proposal's ID: while everything it created is
  still the engine's, what changed since is ``open`` again (``applied`` when nothing did); once the
  administrator changed any of it, nothing is proposed and where it reads a column otherwise it is
  a **disagreement**, naming the step that decided it.

The proposals replace the draft's earlier ones. Applying them (D89) writes each as one step of
origin ``proposal`` through ``history.apply_steps``; the origin carries the anchor, the keys, the
elements created and a snapshot of what the step touched, which is how later reads tell the
engine's elements from the administrator's.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import cast, delete, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ....common.pagination import Page, PageRequest, integer_key, paginate_statement
from ....db import lock_job_subject
from ....errors import api_error
from ....models.database import (
    Job,
    ModelDraft,
    ModelDraftOperation,
    ModelDraftProposal,
    SourceFile,
)
from ....models.sources import InferenceApplicationRequest, InferenceRequest
from ...jobs.store import job_parameter, start_job
from ...model.authoring import history
from ...model.authoring.kinds import Applied
from ...model.authoring.released import base_release, released_atoms
from ...model.compiler import compile_authored_model
from ...model.diagnostics import ModelDiagnostic
from ...model.drafts import load_draft, load_draft_for_update
from ...model.registry import resolve_model_snapshot
from ...workspaces.catalogue import resolve_workspace
from ..draft_profile import current_source
from ..profiling import PLACEHOLDER_VALUES
from ..store import compared_workspace, require_profile
from . import assistant as assistants
from .build import Builder, Proposal
from .compare import (
    bound,
    created_elements,
    element_state,
    holds,
    kind_of,
    model_elements,
    profile_elements,
    referenced_elements,
    snapshot,
)
from .facts import staged_workbook
from .patterns import find

KIND = "inference"
RUNNING = ("queued", "running")
STATUSES = ("open", "applied", "held", "rejected")
_KEYS = (integer_key("position", ModelDraftProposal.position, "position"),)


class InvalidDraft(Exception):
    """The draft does not compile; its diagnostics say why."""

    def __init__(self, diagnostics: Any) -> None:
        super().__init__("The model draft is invalid")
        self.diagnostics = diagnostics


# --- submitting -----------------------------------------------------------------------------------


def submit_inference(session: Session, draft_id: str, request: InferenceRequest, *, retention_days: int) -> Job:
    """Queue the draft's inference and stop an earlier one still running; commits."""
    draft = load_draft(session, draft_id)
    source = current_source(session, draft)
    if source is None:
        raise api_error(404, "SOURCE_FILE_NOT_FOUND", f"Model draft '{draft_id}' has no source file")
    require_profile(session, source)
    compiled = compile_authored_model(draft.model_json)
    if not compiled.valid:
        raise InvalidDraft(compiled.diagnostics)
    applications = {a.get("key") for a in draft.model_json.get("applications") or []}
    if request.mode == "extend" and request.applicationKey and request.applicationKey not in applications:
        raise api_error(
            422,
            "INVALID_INFERENCE_REQUEST",
            f"The draft has no application '{request.applicationKey}' for new types",
            {"pointer": "/applicationKey"},
        )
    if request.mode == "newApplication" and request.applicationKey in applications:
        raise api_error(
            422,
            "INVALID_INFERENCE_REQUEST",
            f"Application '{request.applicationKey}' exists; a new application needs a key no application has",
            {"pointer": "/applicationKey"},
        )
    lock_job_subject(session, KIND, draft.public_id)
    session.execute(
        update(Job)
        .where(Job.kind == KIND, Job.state.in_(RUNNING), job_parameter("draftId") == draft.public_id)
        .values(cancel_requested_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    job = start_job(
        session,
        kind=KIND,
        workspace_key=(workspace_key := resolve_workspace(session, source.workspace_key).key),
        change_set_id=None,
        model_release_id=resolve_model_snapshot(session, workspace_key).release_db_id,
        parameters={
            "draftId": draft.public_id,
            "draftVersion": draft.version,
            "sourceFileId": source.public_id,
            "mode": request.mode,
            "applicationKey": request.applicationKey,
            "applicationName": request.applicationName,
            "file": {"name": source.name, "format": source.format, "bytes": source.bytes},
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )
    session.commit()
    return job


# --- what history says ----------------------------------------------------------------------------


@dataclass(frozen=True)
class ProposalStep:
    step: int
    origin: dict[str, Any]
    undone: bool


def _rows(session: Session, draft: ModelDraft) -> list[ModelDraftOperation]:
    return list(
        session.scalars(
            select(ModelDraftOperation).where(ModelDraftOperation.draft_id == draft.id).order_by(ModelDraftOperation.sequence)
        )
    )


def proposal_steps(rows: list[ModelDraftOperation]) -> list[ProposalStep]:
    steps: dict[int, ProposalStep] = {}
    for row in rows:
        origin = row.origin or {}
        if origin.get("type") != "proposal":
            continue
        current = steps.get(row.step)
        undone = row.undone_by_step is not None or (current.undone if current else False)
        steps[row.step] = ProposalStep(row.step, origin, undone)
    return [steps[s] for s in sorted(steps)]


def engine_elements(
    steps: list[ProposalStep],
    model: dict[str, Any],
    profile: dict[str, Any] | None,
    rows: Sequence[ModelDraftOperation] = (),
) -> dict[str, dict[str, Any]]:
    """Every element still as the latest proposal step touching it left it, with that step's
    origin (D92). An element another step created after that proposal is the administrator's,
    even when it is made as the proposal made it (0.10 A8b: a list removed and loaded again)."""
    latest: dict[str, tuple[Any, dict[str, Any], int]] = {}
    for step in steps:
        if step.undone:
            continue
        for element, state in (step.origin.get("snapshot") or {}).items():
            latest[element] = (state, step.origin, step.step)
    recreated: dict[str, int] = {}
    for row in rows:
        if (row.origin or {}).get("type") == "proposal" or row.undone_by_step is not None:
            continue
        for element in (row.effects or {}).get("created") or []:
            recreated[element] = max(recreated.get(element, 0), row.step)
    return {
        element: origin
        for element, (state, origin, at) in latest.items()
        if state is not None and element_state(model, profile, element) == state and recreated.get(element, 0) < at
    }


def _ownable(element: str) -> bool:
    return element.partition(":")[0] not in ("application",)


# --- the job ----------------------------------------------------------------------------------------


def run_inference(
    session: Session,
    job: Job,
    *,
    assistant_setting: str = "",
    assistant_rows: int = 20,
    check: Callable[[], None] = lambda: None,
) -> None:
    """Find, build and compare the proposals of the job's draft and store them; the job completes.
    The caller commits. ``check`` is called between the phases (reading, finding, building, the
    assistant) and raises to stop: it renews the job's lease and looks for a cancel request, as a
    newer inference of the draft sends (0.10 R-F6)."""
    parameters = job.parameters
    draft = load_draft(session, parameters["draftId"])
    source = session.scalar(select(SourceFile).where(SourceFile.public_id == parameters["sourceFileId"]))
    if source is None:
        raise api_error(404, "SOURCE_FILE_NOT_FOUND", f"Source file '{parameters['sourceFileId']}' was deleted")
    model, profile = draft.model_json, draft.profile_json or {}
    workbook = staged_workbook(session, source)
    check()
    workspace = compared_workspace(session, source)
    findings = find(workbook)
    check()
    rows = _rows(session, draft)
    steps = proposal_steps(rows)
    applied = [s for s in steps if not s.undone]
    earlier = {s.origin.get("anchor"): s for s in applied}
    rejected = {s.origin.get("signature") for s in steps if s.undone} - {s.origin.get("signature") for s in applied}
    base = base_release(session, draft)
    released = released_atoms(base.model_json if base else None)
    builder = Builder(
        model,
        profile,
        workbook,
        mode=parameters["mode"],
        file_name=source.name,
        application_key=parameters.get("applicationKey"),
        application_name=parameters.get("applicationName"),
        reuse={anchor: dict(step.origin.get("keys") or {}) for anchor, step in earlier.items() if anchor},
        released=released.__contains__,
        identifiers=_identifiers(session, source, workbook, workspace) if parameters["mode"] == "extend" and workspace else {},
        stored=StoredRecords(session, source, workbook, workspace) if parameters["mode"] == "extend" and workspace else None,
    )
    proposals = builder.build(findings)
    check()
    engine = engine_elements(steps, model, profile, rows)
    disagreements: list[dict[str, Any]] = []
    for proposal in proposals:
        disagreements += _decide(proposal, earlier.get(proposal.anchor), rejected, engine, model, profile, rows)
    _requirements(proposals)
    warnings = [
        f"Sheet '{name}' holds several blocks and no table, and has too many rows to read list by list; it proposes nothing"
        for name in workbook.skipped
    ]
    warnings += [
        f"Sheet '{name}' is read by its table {table}; {', '.join(others)} beside it {'is' if len(others) == 1 else 'are'} left for later"
        for name, table, others in workbook.partial
    ]
    warnings += [
        f"Sheet '{name}' has a second column {header!r} ({letter}); it is left out, since columns are bound by their header: give it a header of its own"
        for name, header, letter in getattr(workbook, "repeated", [])
    ]
    warnings += builder.warnings
    if not proposals:
        warnings.append("No sheet showed a shape to propose from: nothing is proposed, map the workbook by hand")
    if assistant_setting:
        proposals, warning = _assisted(session, source, workbook, proposals, assistant_setting, assistant_rows)
        if warning:
            warnings.append(warning)
        check()
    session.execute(delete(ModelDraftProposal).where(ModelDraftProposal.draft_id == draft.id))
    session.flush()
    for position, proposal in enumerate(proposals):
        session.add(
            ModelDraftProposal(
                public_id=proposal.id,
                draft_id=draft.id,
                inference_id=job.id,
                position=position,
                pattern=proposal.pattern,
                signature=proposal.signature,
                body=proposal.body(),
            )
        )
    job.report = {
        **(job.report or {}),
        "inference": {"proposals": len(proposals), "disagreements": disagreements, "warnings": warnings},
    }


class StoredRecords:
    """D112 in extend mode: what a column of the file holds that the workspace's records do not,
    each question one statement over the staged cells and the records (principle 6)."""

    def __init__(self, session: Session, source: SourceFile, workbook: Any, workspace: str) -> None:
        self.session = session
        self.source = source
        self.workspace = workspace
        self.columns = {(t.name, c.header): (t.index, c.number, t.header_row) for t in workbook.sheets for c in t.columns}

    def _cells(self, sheet: str, column: str) -> dict[str, Any]:
        index, number, header = self.columns[(sheet, column)]
        return {"file": self.source.id, "sheet": index, "column": number, "header": header, "workspace": self.workspace}

    def holds_records(self, type_key: str) -> bool:
        return bool(
            self.session.scalar(
                text("SELECT EXISTS (SELECT 1 FROM objects WHERE workspace_key = :workspace AND object_type_key = :type)"),
                {"workspace": self.workspace, "type": type_key},
            )
        )

    def missing(self, sheet: str, column: str, type_key: str, attribute: str | None) -> list[dict[str, Any]]:
        stored = (
            "SELECT 1 FROM attribute_values a JOIN objects o ON o.id = a.object_id"
            " AND o.workspace_key = :workspace AND o.object_type_key = :type"
            " WHERE a.attribute_type_key = :attribute AND a.text_value = c.text"
            if attribute
            else "SELECT 1 FROM objects o WHERE o.workspace_key = :workspace AND o.object_type_key = :type AND o.name = c.text"
        )
        found = self.session.execute(
            text(
                f"""
                SELECT c.text, count(*) AS n FROM source_file_cells c
                WHERE c.source_file_id = :file AND c.sheet_index = :sheet AND c.column_number = :column
                  AND c.row_number > :header AND lower(btrim(c.text)) <> ALL(:placeholders)
                  AND NOT EXISTS ({stored})
                GROUP BY c.text ORDER BY n DESC, c.text
                """
            ),
            self._cells(sheet, column) | {"type": type_key, "attribute": attribute, "placeholders": list(PLACEHOLDER_VALUES)},
        )
        return [{"value": value, "rows": rows} for value, rows in found]

    def drift(self, sheet: str, code: str, name: str, type_key: str, attribute: str) -> list[dict[str, Any]]:
        names = self._cells(sheet, name)
        found = self.session.execute(
            text(
                """
                WITH pairs AS (
                    SELECT a.text AS code, b.text AS name, count(*) AS n FROM source_file_cells a
                    JOIN source_file_cells b ON b.source_file_id = a.source_file_id
                        AND b.sheet_index = a.sheet_index AND b.row_number = a.row_number
                        AND b.column_number = :name_column
                    WHERE a.source_file_id = :file AND a.sheet_index = :sheet
                      AND a.column_number = :column AND a.row_number > :header
                    GROUP BY a.text, b.text),
                stored AS (
                    SELECT v.text_value AS code, o.name FROM attribute_values v
                    JOIN objects o ON o.id = v.object_id AND o.workspace_key = :workspace
                        AND o.object_type_key = :type
                    WHERE v.attribute_type_key = :attribute)
                SELECT p.code, s.name, json_agg(json_build_object('value', p.name, 'count', p.n)
                                                ORDER BY p.n DESC, p.name)
                FROM pairs p JOIN stored s ON s.code = p.code
                GROUP BY p.code, s.name HAVING bool_or(p.name IS DISTINCT FROM s.name)
                ORDER BY p.code
                """
            ),
            self._cells(sheet, code) | {"name_column": names["column"], "type": type_key, "attribute": attribute},
        )
        return [{"code": value, "stored": stored, "names": listed} for value, stored, listed in found]


def _identifiers(session: Session, source: SourceFile, workbook: Any, workspace: str) -> dict[tuple[str, str], dict[str, str]]:
    """D96 in extend mode: for a column whose values are at least half an existing type's unique
    attribute values in the file's workspace (its profile's overlaps, D69), the type, the attribute
    and the one parent record those records stand under (a system's mappings stand under the
    system), read with one statement per such column."""
    found: dict[tuple[str, str], dict[str, str]] = {}
    for table in workbook.sheets:
        for column in table.columns:
            overlaps = [o for o in column.overlaps if o.get("attributeTypeKey") and o.get("share", 0) >= 0.5]
            if not overlaps:
                continue
            best = max(overlaps, key=lambda o: o["share"])
            parents = session.execute(
                text(
                    """
                    SELECT DISTINCT p.object_type_key, p.name FROM attribute_values a
                    JOIN objects o ON o.id = a.object_id AND o.workspace_key = :workspace
                        AND o.object_type_key = :type
                    JOIN objects p ON p.id = o.parent_object_id
                    WHERE a.attribute_type_key = :attribute AND a.text_value IN (
                        SELECT text FROM source_file_cells WHERE source_file_id = :file
                          AND sheet_index = :sheet AND column_number = :column AND row_number > :header)
                    LIMIT 2
                    """
                ),
                {
                    "workspace": workspace,
                    "type": best["objectTypeKey"],
                    "attribute": best["attributeTypeKey"],
                    "file": source.id,
                    "sheet": table.index,
                    "column": column.number,
                    "header": table.header_row,
                },
            ).all()
            if len(parents) == 1:
                found[(table.name, column.header)] = {
                    "type": best["objectTypeKey"],
                    "attribute": best["attributeTypeKey"],
                    "parentType": parents[0][0],
                    "parent": parents[0][1],
                }
    return found


def _decide(
    proposal: Proposal,
    earlier: ProposalStep | None,
    rejected: set[str],
    engine: dict[str, dict[str, Any]],
    model: dict[str, Any],
    profile: dict[str, Any],
    rows: list[ModelDraftOperation],
) -> list[dict[str, Any]]:
    """The proposal's state and the operations still to apply; its disagreements (D92)."""
    if earlier is None:
        if proposal.signature in rejected:
            proposal.state = "rejected"
            proposal.created = created_elements(proposal.operations)
            return []
        taken = _bound_columns(proposal, profile)
        if taken:
            proposal.state = "held"
            proposal.operations = []
            return _disagreements(proposal, taken, rows)
        proposal.operations = [o for o in proposal.operations if not holds(o, model, profile)]
        proposal.state = "open" if proposal.operations else "held"
        proposal.created = created_elements(proposal.operations)
        return []
    proposal.id = earlier.origin["proposalId"]
    created = [e for e in earlier.origin.get("created") or [] if _ownable(e)]
    if all(e in engine for e in created):
        remaining = [o for o in proposal.operations if not holds(o, model, profile)]
        wanted = created_elements(proposal.operations)
        for element in created:
            if element.startswith("column:") and element not in wanted:
                source_id, _, header = element[len("column:") :].partition("/")
                operation = {"kind": "unmapColumn", "source": source_id, "column": header}
                if not holds(operation, model, profile):
                    remaining.append(operation)
        proposal.operations = remaining
        proposal.state = "open" if remaining else "applied"
        proposal.created = created_elements(remaining)
        return []
    proposal.state = "applied"
    proposal.operations = []
    current = {
        column: kind_of(bound(next((s for s in profile.get("sources") or [] if s.get("id") == source), None), column))
        for column, (source, _) in proposal.binds.items()
    }
    taken = {column: kind for column, kind in current.items() if kind and kind != "ignore"}
    return _disagreements(proposal, taken, rows)


def _bound_columns(proposal: Proposal, profile: dict[str, Any]) -> dict[str, str]:
    """The columns the proposal binds that a source of its sheet binds already, with how."""
    found: dict[str, str] = {}
    for column in proposal.binds:
        for source in profile.get("sources") or []:
            if source.get("sheet") != proposal.sheet:
                continue
            binding = bound(source, column)
            if binding is not None:
                found[column] = kind_of(binding)
    for sheet in profile.get("ignoredSheets") or []:
        if sheet == proposal.sheet:
            found.update({column: "ignore" for column in proposal.binds})
    return found


def _disagreements(proposal: Proposal, current: dict[str, str], rows: list[ModelDraftOperation]) -> list[dict[str, Any]]:
    found = []
    for column, kind in current.items():
        wanted = proposal.binds[column][1]
        if kind in ("", "ignore") or kind == wanted:
            continue
        found.append(
            {
                "proposalId": proposal.id,
                "pattern": proposal.pattern,
                "sheet": proposal.sheet,
                "column": column,
                "source": proposal.binds[column][0],
                "binding": kind,
                "proposed": wanted,
                "found": proposal.summary,
                "step": _decided_by(rows, column),
            }
        )
    return found


def _decided_by(rows: list[ModelDraftOperation], column: str) -> int | None:
    """The latest step not of a proposal, not undone, that changed ``column``."""
    steps = [
        row.step
        for row in rows
        if (row.origin or {}).get("type") != "proposal"
        and row.undone_by_step is None
        and isinstance(row.parameters, dict)
        and row.parameters.get("column") == column
    ]
    return max(steps) if steps else None


def _requirements(proposals: list[Proposal]) -> None:
    """Each open proposal requires the earlier open proposals creating what it names."""
    creators: dict[str, str] = {}
    for proposal in proposals:
        if proposal.state != "open":
            continue
        named = referenced_elements(proposal.operations)
        proposal.requires = sorted({creators[e] for e in named if e in creators and creators[e] != proposal.id})
        for element in proposal.created:
            creators.setdefault(element, proposal.id)


def _assisted(
    session: Session, source: SourceFile, workbook: Any, proposals: list[Proposal], setting: str, rows: int
) -> tuple[list[Proposal], str | None]:
    try:
        assistant = assistants.load_assistant(setting)
    except Exception as exc:  # noqa: BLE001 - a misconfigured plug-in is a warning, not a failure
        return proposals, f"The assistant '{setting}' could not be loaded ({type(exc).__name__})"
    if assistant is None:
        return proposals, None
    sheets = []
    for table in workbook.sheets:
        found = session.execute(
            text(
                """
                SELECT row_number, column_number, text FROM source_file_cells
                WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
                  AND row_number <= :header + :rows
                ORDER BY row_number, column_number
                """
            ),
            {"file": source.id, "sheet": table.index, "header": table.header_row, "rows": rows},
        )
        by_row: dict[int, dict[int, str]] = {}
        for row_number, column_number, value in found:
            by_row.setdefault(row_number, {})[column_number] = value
        numbers = [c.number for c in table.columns]
        sheets.append(
            assistants.AssistantSheet(
                table.name, [c.header for c in table.columns], [[cells.get(n) for n in numbers] for _, cells in sorted(by_row.items())]
            )
        )
    types = [
        assistants.AssistantType(p.id, o["key"], o["name"])
        for p in proposals
        if p.state == "open"
        for o in p.operations
        if o.get("kind") == "addObjectType"
    ]
    suggested, warning = assistants.suggestions(assistant, assistants.AssistantRequest(sheets, types))
    names = {(t.proposal, t.key): t.name for t in types}
    for suggestion in suggested:
        body = assistants.proposal_body(suggestion, names[(suggestion.proposal, suggestion.key)])
        proposals.append(
            Proposal(
                pattern="assistant",
                sheet=None,
                columns=[],
                summary=body["summary"],
                evidence=body["evidence"],
                operations=body["operations"],
                anchor=f"assistant|{suggestion.key}",
                signature=f"assistant|{suggestion.key}|{suggestion.name}",
                requires=[suggestion.proposal],
            )
        )
    return proposals, warning


# --- reads ----------------------------------------------------------------------------------------


def latest_inference(session: Session, draft: ModelDraft) -> Job | None:
    return session.scalar(
        select(Job)
        .where(Job.kind == KIND, job_parameter("draftId") == draft.public_id)
        .order_by(Job.sequence_id.desc())
        .limit(1)
    )


def require_inference(session: Session, draft: ModelDraft) -> Job:
    job = latest_inference(session, draft)
    if job is None:
        raise api_error(404, "INFERENCE_NOT_FOUND", f"Model draft '{draft.public_id}' has no inference yet")
    return job


def statuses(session: Session, draft: ModelDraft, job: Job, rows: list[ModelDraftOperation] | None = None) -> dict[str, str]:
    """Each stored proposal's status: ``applied`` once a step of this inference applies it (or an
    earlier one did and nothing is left), as stored otherwise."""
    rows = rows if rows is not None else _rows(session, draft)
    applied_now = {
        s.origin.get("proposalId") for s in proposal_steps(rows) if not s.undone and s.origin.get("inferenceId") == job.id
    }
    found = {}
    for proposal_id, body in session.execute(
        select(ModelDraftProposal.public_id, ModelDraftProposal.body).where(ModelDraftProposal.draft_id == draft.id)
    ):
        stored = body.get("state", "open")
        found[proposal_id] = "applied" if proposal_id in applied_now else stored
    return found


def read_inference(session: Session, draft: ModelDraft) -> dict[str, Any]:
    """``GET /model-drafts/{id}/inference``: the latest inference's state, its counts by status,
    disagreements and warnings, and the elements still as proposed (the editor's marks)."""
    job = require_inference(session, draft)
    rows = _rows(session, draft)
    report = (job.report or {}).get("inference") or {}
    counts = dict.fromkeys(STATUSES, 0)
    if job.state == "completed":
        for status in statuses(session, draft, job, rows).values():
            counts[status] = counts.get(status, 0) + 1
    steps = proposal_steps(rows)
    engine = engine_elements(steps, draft.model_json, draft.profile_json, rows)
    # Each element with the proposal that created it: a later proposal naming it (a navigation
    # group listing a list) is not why it is there.
    created_by = {
        element: step.origin
        for step in steps
        if not step.undone
        for element in step.origin.get("created") or []
        if _ownable(element)
    }
    proposed = [
        {"element": element, "proposalId": created_by[element].get("proposalId"), "pattern": created_by[element].get("pattern")}
        for element in sorted(engine)
        if element in created_by
    ]
    return {
        "jobId": job.id,
        "state": "checking" if job.state in RUNNING else job.state,
        "mode": job.parameters.get("mode"),
        "draftVersion": job.parameters.get("draftVersion"),
        "sourceFileId": job.parameters.get("sourceFileId"),
        "counts": counts,
        "disagreements": report.get("disagreements") or [],
        "warnings": report.get("warnings") or [],
        "proposed": proposed,
        "error": job.error,
    }


def proposal_page(
    session: Session, draft: ModelDraft, page: PageRequest, page_size: int, *, sheet: str | None, column: str | None
) -> tuple[Page[ModelDraftProposal], dict[str, str]]:
    job = require_inference(session, draft)
    if job.state != "completed":
        raise api_error(409, "INFERENCE_NOT_READY", f"The draft's inference is {job.state}", {"state": job.state})
    statement = select(ModelDraftProposal).where(ModelDraftProposal.draft_id == draft.id)
    if sheet is not None:
        statement = statement.where(ModelDraftProposal.body["sheet"].as_string() == sheet)
    if column is not None:
        statement = statement.where(cast(ModelDraftProposal.body["columns"], JSONB).contains([column]))
    found = paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="draft-proposals",
        filters={"draftId": draft.public_id, "sheet": sheet, "column": column},
        page=page,
        page_size=page_size,
        message="Proposal list cursor is invalid",
    )
    return found, statuses(session, draft, job)


# --- applying (D89) -------------------------------------------------------------------------------


def apply_inference(session: Session, draft_id: str, request: InferenceApplicationRequest, *, max_items: int) -> history.StepResult:
    """The proposals asked for (every open one by default), each one step of origin ``proposal``,
    in their order, all or none. The draft is locked first, as its steps lock it: an inference
    storing its proposals waits for the application, or the application for it, and never reads
    one job's proposals under another's (0.10 R-F10)."""
    draft = load_draft_for_update(session, draft_id)
    job = require_inference(session, draft)
    if job.state != "completed":
        raise api_error(409, "INFERENCE_NOT_READY", f"The draft's inference is {job.state}", {"state": job.state})
    rows = _rows(session, draft)
    since = job.parameters.get("draftVersion", 0)
    for row in rows:
        origin = row.origin or {}
        if row.draft_version > since and not (origin.get("type") == "proposal" and origin.get("inferenceId") == job.id):
            raise api_error(
                409,
                "INFERENCE_STALE",
                "The draft changed after its inference; propose again before applying",
                {"inferenceDraftVersion": since, "draftVersion": draft.version},
            )
    stored = list(
        session.scalars(
            select(ModelDraftProposal).where(ModelDraftProposal.draft_id == draft.id).order_by(ModelDraftProposal.position)
        )
    )
    by_id = {p.public_id: p for p in stored}
    status = statuses(session, draft, job, rows)
    if request.proposals is None:
        wanted = [p for p in stored if status[p.public_id] == "open"]
        if not wanted:
            raise api_error(409, "NOTHING_TO_APPLY", "No proposal of the draft's inference is open")
    else:
        for proposal_id in request.proposals:
            if proposal_id not in by_id:
                raise api_error(404, "PROPOSAL_NOT_FOUND", f"The draft's inference has no proposal '{proposal_id}'", {"proposal": proposal_id})
            if status[proposal_id] == "applied":
                raise api_error(409, "PROPOSAL_ALREADY_APPLIED", f"Proposal '{proposal_id}' is applied", {"proposal": proposal_id})
        asked = set(request.proposals)
        wanted = [p for p in stored if p.public_id in asked]
    names = {p.public_id for p in wanted}
    for proposal in wanted:
        for requirement in proposal.body.get("requires") or []:
            if requirement not in names and status.get(requirement) != "applied":
                raise api_error(
                    422,
                    "PROPOSAL_REQUIREMENT_MISSING",
                    f"Proposal '{proposal.public_id}' needs proposal '{requirement}' applied first or with it",
                    {"proposal": proposal.public_id, "requirement": requirement},
                )
    steps = [(p.public_id, list(p.body.get("operations") or []), _origin_of(p, job)) for p in wanted]
    return history.apply_steps(session, draft_id, request.expectedVersion, steps, max_items)


def _origin_of(proposal: ModelDraftProposal, job: Job) -> Callable[[list[Applied], dict[str, Any], dict[str, Any] | None], dict[str, Any]]:
    body = proposal.body
    operations = list(body.get("operations") or [])

    def origin(applied: list[Applied], model: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
        made = {a for item in applied for a in item.created}
        named = {a for item in applied for a in item.named}
        created = sorted((model_elements(made) | profile_elements(operations)) & _present(model, profile, made, operations))
        touched = model_elements(made | named) | profile_elements(operations) | _source_columns(operations, profile)
        return {
            "type": "proposal",
            "proposalId": proposal.public_id,
            "inferenceId": job.id,
            "pattern": proposal.pattern,
            "summary": body.get("summary"),
            "anchor": body.get("anchor"),
            "signature": proposal.signature,
            "keys": body.get("keys") or {},
            "created": created,
            "snapshot": snapshot(model, profile, touched),
        }

    return origin


def _present(model: dict[str, Any], profile: dict[str, Any] | None, made: set[str], operations: list[dict[str, Any]]) -> set[str]:
    return {e for e in model_elements(made) | profile_elements(operations) if element_state(model, profile, e) is not None}


def _source_columns(operations: list[dict[str, Any]], profile: dict[str, Any] | None) -> set[str]:
    """Every column binding of the sources the operations touch: a flag column's step changes the
    binding its set's other columns share."""
    sources = {o.get("source") for o in operations if o.get("source")} | {o.get("id") for o in operations if o.get("kind") == "addSource"}
    found: set[str] = set()
    for source in (profile or {}).get("sources") or []:
        if source.get("id") not in sources:
            continue
        for binding in source.get("columns") or []:
            for column in [binding.get("column"), *(binding.get("columns") or [])]:
                if column:
                    found.add(f"column:{source['id']}/{column}")
    return found


# --- disagreements as profile warnings ------------------------------------------------------------


def disagreement_diagnostics(session: Session, draft: ModelDraft) -> list[ModelDiagnostic]:
    """The latest inference's disagreements that still hold, as ``INFERENCE_DISAGREES`` warnings at
    the source they concern; they never block anything."""
    job = latest_inference(session, draft)
    if job is None or job.state != "completed":
        return []
    profile = draft.profile_json or {}
    sources = profile.get("sources") or []
    found = []
    for item in ((job.report or {}).get("inference") or {}).get("disagreements") or []:
        index = next((i for i, s in enumerate(sources) if s.get("id") == item.get("source")), None)
        binding = bound(sources[index], item["column"]) if index is not None else None
        if binding is None or kind_of(binding) != item.get("binding"):
            continue
        position = sources[index]["columns"].index(binding)
        decided = f" in step {item['step']}" if item.get("step") else ""
        found.append(
            ModelDiagnostic(
                "warning",
                "INFERENCE_DISAGREES",
                f"/profile/sources/{index}/columns/{position}",
                f"'{item['column']}' of sheet '{item['sheet']}' is read as {item['binding']}{decided}; "
                f"the workbook reads it as {item['proposed']} ({item['pattern']}). Nothing was changed",
            )
        )
    return found

