"""The kinds of background job, one entry each (the shape of ``model/authoring/kinds.py`` and
``moves/mapping_kinds.py``): what runs it, which group its requester needs, whether it previews,
whether its items are a file's rows. A new kind is added here and nowhere else in the dispatch.

This module imports nothing, so the worker, the store, the authorization catalogue and the API
schemas can all read it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class JobKind:
    name: str
    # The group a job of this kind is used under in its workspace (D285), and how its step is named
    # in a refusal (D294).
    group: str
    action: str
    # Which worker claims it: the batch worker, the export worker or the assistant worker.
    worker: str = "batch"
    # The ``JobWorker`` method that runs one chunk of it; none for the kinds that bind, preview and
    # apply items (``batch``, ``import``, ``dryRun``, ``profileCheck``).
    step: str | None = None
    # Sent with ``stage: preview`` it runs as a preview and waits for confirmation (0.9 K2).
    previewed: bool = False
    # Its items are a file's rows, each outcome with its source and row (0.9 J3): an import, a
    # draft's dry run of one (0.10 A3) and a profile's check of its next file (0.10 A5c).
    rows: bool = False
    # It binds a source file's staged cells rather than a job file (0.10 A3, A5c): a dry run and a
    # profile's check run the whole file, and a cancel stops them before they write.
    staged: bool = False
    # The stage a claimed chunk shows: fixed, or "binding" first when ``binds`` and no total is
    # known yet; a kind with neither shows "previewing" while its preview runs and "applying" after.
    stage: str | None = None
    binds: bool = False
    # A preview of its own, not ``previewed``'s (a move's: ``moves/move_job.py``).
    previews_apart: bool = False


# In the order the API lists the kinds.
JOB_KINDS: tuple[JobKind, ...] = (
    JobKind("batch", "bulk", "bulk.write", previewed=True),
    JobKind("import", "bulk", "bulk.write", previewed=True, rows=True, binds=True),
    JobKind("export", "browse", "exports.create", worker="export"),
    JobKind("profile", "bulk", "source-files.manage", step="_profile", stage="profiling"),
    JobKind(
        "dryRun",
        "model-authoring",
        "model.author",
        previewed=True,
        rows=True,
        staged=True,
        binds=True,
    ),
    JobKind("inference", "model-authoring", "model.author", step="_infer", stage="inferring"),
    JobKind(
        "profileCheck",
        "bulk",
        "import-profiles.manage",
        previewed=True,
        rows=True,
        staged=True,
        binds=True,
    ),
    JobKind("migration", "model-release", "model.activate", previewed=True, step="_migrate"),
    JobKind(
        "mappingInference",
        "copy-move",
        "model-mappings.manage",
        step="_infer_mapping",
        stage="inferring",
    ),
    JobKind(
        "move",
        "copy-move",
        "moves.create",
        step="_move",
        binds=True,
        previews_apart=True,
    ),
    # Proposals are edits of a change set (0.16 AP2).
    JobKind(
        "aiProposal",
        "change-sets",
        "records.write",
        step="_propose_targets",
        stage="proposing",
        binds=True,
    ),
    # An assistant task reads and checks a workbook as an import does (0.16 AP6a); a session holds
    # its job for as long as it works, and waits on the jobs it queues.
    JobKind("aiTask", "bulk", "bulk.write", worker="assistant", step="_task", stage="reading"),
)

KINDS: dict[str, JobKind] = {kind.name: kind for kind in JOB_KINDS}
KIND_NAMES: tuple[str, ...] = tuple(kind.name for kind in JOB_KINDS)


def _named(**where: object) -> tuple[str, ...]:
    return tuple(
        kind.name
        for kind in JOB_KINDS
        if all(getattr(kind, field) == wanted for field, wanted in where.items())
    )


BATCH_KINDS = _named(worker="batch")
EXPORT_KINDS = _named(worker="export")
ASSISTANT_KINDS = _named(worker="assistant")
PREVIEWED_KINDS = _named(previewed=True)
ROW_KINDS = _named(rows=True)
STAGED_KINDS = _named(staged=True)
