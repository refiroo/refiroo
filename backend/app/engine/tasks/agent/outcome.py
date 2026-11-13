"""What the assistant session reached: the proposal landed, the release it installed, the change set it
loaded, and the recovery of a load; the entry points that start a turn and act on the result."""

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ....errors import ApiError
from ....models.database import (
    AiTask,
    AuditEvent,
    ChangeSet,
    ImportProfile,
    Job,
    ModelDraft,
    ModelRelease,
    SourceFile,
    WorkspaceModel,
)
from ....models.imports import ImportProfileDefinition
from ...change_sets.lifecycle import discard_change_set
from ...identity.clients import retire_session_client
from ...imports.profiles import model_key_of, save_for_release
from ...model.authoring.draft_migration import derive
from ...model.compiler import canonical_model, compile_model, parse_model
from ...model.consumer_contract import contract_diagnostics, raised_contracts
from ...model.diagnostics import ModelValidationError
from ...model.migrations import LandingRefusal, Mappings, check_landing, plan_migration
from ...model.release_lifecycle import set_release_status
from ...model.workspace_models import load_assignment
from ...sources.dry_run import is_items_run
from ...sources.profile_export import definition as exported_profile
from ..cell_coverage import cells_left_out
from ..store import finish, held_by_another, held_counts, load_task, note, title_of
from .files import (
    drop,
    ensure_folder,
    folder_of,
    make_folders,
    put,
    read_work,
    remove_folder,
    retention,
)
from .run import (
    Progress,
    api_url,
    closing_words,
    counts_of,
    holds_changes,
    openapi,
    provider,
    run_turn,
)
from .words import (
    ACCEPTED,
    ACCEPTED_UNCHANGED,
    LAST_LINE,
    MOVED,
    PROMPT_VERSION,
    PROPOSAL,
    RELEASE_LINE,
    REMOVAL_KINDS,
    THEN_LINE,
    attribute_changes,
    contract_prompt,
    contract_words,
    counted,
    loss_prompt,
    loss_words,
    not_its_draft_prompt,
    plain,
    plural,
    propose_prompt,
    refusal_prompt,
    refusal_words,
    reprompt,
    said_prompt,
    type_names,
)


def profile_not_stored(read_by: dict[str, Any] | None, stored: dict[str, Any] | None) -> str | None:
    """Why the profile a check read the workbook by is not the one the draft holds, or ``None`` when
    it is (0.17 PL3b). A session may send a dry run its profile inline and store none on the draft;
    the person then accepts a design whose check no stored profile reproduces. ``read_by`` is the
    definition the check's dry run bound, ``stored`` the draft's own as it exports it; ``None`` for
    a check that read no workbook through a profile."""
    if not read_by:
        return None
    if not stored:
        return (
            "The assistant checked the workbook through a profile it sent with the check and "
            "stored none on the model draft, so the design would have no profile to load by. "
            "Give the assistant other words to check again."
        )
    if _profile_parts(read_by) != _profile_parts(stored):
        return (
            "The profile the assistant checked the workbook by is not the one stored on the model "
            "draft, so the check says nothing about what the design would load. Give the "
            "assistant other words to check again."
        )
    return None


def _profile_parts(definition: dict[str, Any]) -> str:
    """A definition's sources and value maps, as the import reads them."""
    parsed = ImportProfileDefinition.model_validate(definition)
    return json.dumps(
        parsed.model_dump(mode="json", exclude_none=True, include={"sources", "valueMaps"}),
        sort_keys=True,
    )


def _unstored_profile(
    session: Session, draft: ModelDraft, check: dict[str, Any] | None
) -> str | None:
    """:func:`profile_not_stored` for the draft's latest check (a dry run of a source file)."""
    job = session.scalar(select(Job).where(Job.id == (check or {}).get("dryRunJobId")))
    if job is None or is_items_run(job.parameters):
        return None
    stored, _ = exported_profile(draft.profile_json)
    return profile_not_stored((job.parameters.get("profile") or {}).get("definition"), stored)


def _previewed_elsewhere(session: Session, task: Any, check: dict[str, Any]) -> bool:
    """Whether the dry run of items the check comes from was made against another workspace."""
    job = session.scalar(select(Job).where(Job.id == check.get("dryRunJobId")))
    return job is not None and job.workspace_key != task.workspace_key


def _shape(
    model: dict[str, Any], base: dict[str, Any], records: dict[str, int]
) -> list[dict[str, Any]]:
    """The proposal's shape from the draft and its dry run, not from the session's account: each type
    it adds, changes or loads, with its attributes and the records the check would write. A type is
    changed only when its attributes differ in meaning (added, removed, required or read-only), and
    the entry says which."""
    before = {found.get("key"): found for found in base.get("objectTypes") or []}
    names = {a.get("key"): a.get("name") or a.get("key") for a in model.get("attributeTypes") or []}
    shape = []
    for found in model.get("objectTypes") or []:
        key = found.get("key")
        attributes = found.get("attributes") or []
        earlier = before.get(key)
        change: str | None = None
        if earlier is None:
            change = "New type"
        else:
            added, removed, altered = attribute_changes(names, attributes, earlier)
            said = [
                *([f"adds {', '.join(added)}"] if added else []),
                *([f"drops {', '.join(removed)}"] if removed else []),
                *([f"changes how {', '.join(altered)} is filled in"] if altered else []),
            ]
            if said:
                change = f"Changed type ({'; '.join(said)})"
        written = records.get(key, 0)
        if change is None and not written:
            continue
        parts = [*([change] if change else []), plural(len(attributes), "attribute")]
        if written:
            parts.append(plural(written, "record"))
        shape.append(
            {"objectTypeKey": key, "name": found.get("name") or key, "text": ", ".join(parts)}
        )
    return shape


def _left_out(
    model: dict[str, Any],
    base: dict[str, Any],
    held: dict[str, int],
    moved: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Types the workspace holds records of and the proposed model no longer has: the person is told
    before accepting, whatever the session said. A type the proposal moves is not left out."""
    kept = {found.get("key") for found in model.get("objectTypes") or []} | moved
    names = {found.get("key"): found.get("name") for found in base.get("objectTypes") or []}
    gone = [
        f"{names.get(key) or key} ({count:,})"
        for key, count in sorted(held.items())
        if key not in kept
    ]
    if not gone:
        return []
    return [
        {
            "id": "types-left-out",
            "kind": "leftOut",
            "text": "This model leaves out types the workspace holds records of: "
            + ", ".join(gone),
            "open": True,
        }
    ]


def _cells_left_out(session: Session, task: AiTask, job_id: str | None) -> list[dict[str, Any]]:
    """Filled cells of the tables the design reads that no source of it covers (AP13): said before
    the person accepts, whatever the session said, as a column the profile cannot name is no error."""
    job = session.scalar(select(Job).where(Job.id == job_id)) if job_id else None
    if job is None or not (task.reading or {}).get("tables"):
        return []
    definition = (job.parameters.get("profile") or {}).get("definition")
    file_id = session.scalar(
        select(SourceFile.id).where(SourceFile.public_id == job.parameters.get("sourceFileId"))
    )
    if not definition or file_id is None:
        return []
    return [
        {
            "id": f"cells-left-out:{found['sheet']}",
            "kind": "cellsLeftOut",
            "text": f"{found['count']:,} filled cells of “{found['sheet']}” are read by no source of this "
            f"design (for example {', '.join(found['cells'])}): what they hold is not loaded",
            "open": True,
        }
        for found in cells_left_out(
            session, file_id=file_id, tables=task.reading["tables"], profile=definition
        )
    ]


def _beside_held(
    session: Session, job_id: str | None, model: dict[str, Any], held: dict[str, int]
) -> list[dict[str, Any]]:
    """New records of a type the workspace already holds: rows that did not find their records read
    as an update gone wrong, and the person is told before accepting (AP-D42)."""
    if job_id is None:
        return []
    created = session.execute(
        text(
            "SELECT i.outcome ->> 'objectTypeKey', count(*) FROM job_items i"
            " JOIN jobs j ON j.sequence_id = i.job_id"
            " WHERE j.id = :job AND i.outcome ->> 'action' = 'created'"
            " AND i.outcome ->> 'objectTypeKey' IS NOT NULL GROUP BY 1"
        ),
        {"job": job_id},
    ).all()
    names = {found.get("key"): found.get("name") for found in model.get("objectTypes") or []}
    return [
        {
            "id": f"beside-held-{key}",
            "kind": "besideHeld",
            "text": (
                f"{count:,} new {names.get(key) or key} beside the {held[key]:,} held. "
                "If this is an update, the rows did not find their records."
            ),
            "open": True,
        }
        for key, count in sorted(created)
        if held.get(key)
    ]


def _requested_moves(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    """The proposal's ``moves`` as a migration's ``typeMappings`` (AP-D47); anything else in it is
    not a move."""
    found = []
    raw = proposal.get("moves")
    for move in raw if isinstance(raw, list) else []:
        if not isinstance(move, dict):
            continue
        found.append(
            {
                "fromObjectTypeKey": str(move.get("from") or ""),
                "toObjectTypeKey": str(move.get("to") or ""),
                "attributes": [
                    {"attributeTypeKey": str(a.get("attributeTypeKey")), "from": a.get("from")}
                    for a in move.get("attributes") or []
                    if isinstance(a, dict)
                ],
            }
        )
    return found


_EXTRA_MAPPINGS = ("relationTypeMappings", "splits", "listConversions")


def _migration_of(
    session: Session,
    workspace_key: str,
    draft: ModelDraft | None,
    against: ModelRelease,
    to: ModelRelease | None,
    requested: list[dict[str, Any]],
) -> dict[str, Any]:
    """The migration the task hands over: what the draft states against the workspace's release (the
    engine's own ``derive``: application moves, relation type mappings, splits and list conversions
    as well as the types that become others) joined with the session's explicit ``moves``. A session
    move for a type is that type's mapping, keeping the application the draft sends it to; no type
    is mapped twice. ``notes`` are the engine's, such as that a step replaced the whole model."""
    found = (
        derive(session, draft, workspace_key=workspace_key, against=against, to=to)
        if draft is not None
        else {}
    )
    merged = {item["fromObjectTypeKey"]: dict(item) for item in found.get("typeMappings") or []}
    for move in requested:
        derived = merged.get(move["fromObjectTypeKey"], {})
        merged[move["fromObjectTypeKey"]] = {
            **derived,
            **move,
            "attributes": move.get("attributes") or derived.get("attributes") or [],
        }
    return {
        "typeMappings": list(merged.values()),
        **{name: list(found.get(name) or []) for name in _EXTRA_MAPPINGS},
        "notes": list(found.get("notes") or []),
    }


def _extra_of(migration: dict[str, Any]) -> dict[str, Any]:
    """The mappings beside the types, as the migration's request and its landing check take them."""
    return {name: migration[name] for name in _EXTRA_MAPPINGS if migration.get(name)}


def _planned_moves(
    migration: dict[str, Any],
    base: dict[str, Any],
    model: dict[str, Any],
    held: dict[str, int],
    losses: dict[str, dict[str, int]] | None = None,
    requested: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """What the migration would do, checked against the draft by the migration's own plan (AP-D47):
    each type mapping with the records the workspace holds of the type, and the application its
    records go to. A mapping the plan refuses raises its ``ApiError``; a model that does not
    compile, ``ModelValidationError``."""
    mappings = migration["typeMappings"]
    if not mappings and not _extra_of(migration):
        return []
    parsed = Mappings.of({"typeMappings": mappings, **_extra_of(migration)})
    plan_migration(
        parse_model(base), parse_model(model), parsed.types, parsed.relations, parsed.spawns
    )
    old = {found.get("key"): found.get("name") for found in base.get("objectTypes") or []}
    new = {found.get("key"): found.get("name") for found in model.get("objectTypes") or []}
    apps = {found.get("key"): found.get("name") for found in model.get("applications") or []}
    return [
        {
            "from": move["fromObjectTypeKey"],
            "fromName": old.get(move["fromObjectTypeKey"]) or move["fromObjectTypeKey"],
            "to": move["toObjectTypeKey"],
            "toName": new.get(move["toObjectTypeKey"]) or move["toObjectTypeKey"],
            "records": held.get(move["fromObjectTypeKey"], 0),
            "attributes": move["attributes"],
            "lost": (losses or {}).get(move["fromObjectTypeKey"], {}),
            "fromSession": move["fromObjectTypeKey"] in requested,
            **(
                {
                    "toApplication": move["toApplicationKey"],
                    "toApplicationName": apps.get(move["toApplicationKey"])
                    or move["toApplicationKey"],
                }
                if move.get("toApplicationKey")
                else {}
            ),
        }
        for move in mappings
    ]


def _contract_errors(base: dict[str, Any], model: dict[str, Any]) -> list[Any]:
    """What the draft breaks for the consumers of the workspace's model, which the migration's preview
    and an activation refuse (C-D17): the errors of the contract diagnostics."""
    return [
        found
        for found in contract_diagnostics(parse_model(base), parse_model(model))
        if found.severity == "error"
    ]


def _persons_text(task: AiTask) -> str:
    """Everything the person wrote to the task: the words and every correction and answer."""
    design = task.design or {}
    return "\n".join(
        [
            task.words or "",
            *(str(item) for item in design.get("corrections") or []),
            *(str(item) for item in (design.get("answers") or {}).values()),
        ]
    )


def _requested_removals(proposal: dict[str, Any], written: str) -> list[dict[str, Any]]:
    """What the person's words explicitly ask to remove, as the session listed it: each with the
    words that ask. An entry whose words the person never wrote (any part of a sentence of their
    own text, whatever the case, spacing or quote marks) is not an ask, so it is not kept."""
    found = []
    text = plain(written)
    raw = proposal.get("removals")
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        kind, key = item.get("kind"), str(item.get("key") or "").strip()
        words = str(item.get("words") or "").strip()
        owner = str(item.get("objectType") or "").strip()
        if (
            kind not in REMOVAL_KINDS
            or not key
            or not words
            or (kind == "attribute" and not owner)
            or not plain(words)
            or plain(words) not in text
        ):
            continue
        moved = item.get("movedTo")
        moved_to = (
            [str(key).strip() for key in moved if str(key).strip()]
            if kind == "objectType" and isinstance(moved, list)
            else []
        )
        found.append(
            {
                "kind": kind,
                "key": key,
                "words": words[:500],
                **({"objectType": owner} if owner else {}),
                **({"movedTo": moved_to} if moved_to else {}),
            }
        )
    return found


def _removal_account(
    landing: Any,
    removals: list[dict[str, Any]],
    base: dict[str, Any],
    final: dict[str, Any] | None = None,
) -> tuple[dict[str, dict[str, int]], list[dict[str, Any]]]:
    """Split what a migration would lose into what the person asked to remove and the rest. A loss
    is allowed only when it falls within a removal: the records of a removed type (or of the types
    of a removed application), the values of a removed field, and the relationships of a removed
    relation type or of records that are themselves removed. Returns the rest, per type, and one
    statement per removal with the counts it deletes and a plain sentence."""
    named = {
        kind: {
            item.get("key"): item.get("name") or item.get("key") for item in base.get(group) or []
        }
        for kind, group in (
            ("objectType", "objectTypes"),
            ("attribute", "attributeTypes"),
            ("relationType", "relationTypes"),
            ("application", "applications"),
        )
    }
    held = {
        item["key"]: set(item.get("objectTypeKeys") or [])
        for item in base.get("applications") or []
    }
    # The types each removal deletes the records of.
    reach: list[set[str]] = []
    for item in removals:
        if item["kind"] == "objectType":
            reach.append({item["key"]})
        elif item["kind"] == "application":
            reach.append(set(held.get(item["key"], ())))
        else:
            reach.append(set())
    counts = [{"records": 0, "values": 0, "relationships": 0} for _ in removals]
    removed_types = set().union(*reach) if reach else set()
    claimed: set[str] = set()
    for index, types in enumerate(reach):
        for type_key in sorted(types - claimed):
            counts[index]["records"] += landing.losses.get(type_key, {}).get("records", 0)
        claimed |= types
    rest: dict[str, dict[str, int]] = {}

    def left(type_key: str, kind: str, count: int) -> None:
        if count:
            slot = rest.setdefault(type_key, {})
            slot[kind] = slot.get(kind, 0) + count

    for type_key, found in landing.losses.items():
        if type_key not in removed_types:
            left(type_key, "records", found.get("records", 0))
    for (type_key, attribute), count in landing.value_losses.items():
        owner = next(
            (
                i
                for i, item in enumerate(removals)
                if item["kind"] == "attribute"
                and item["key"] == attribute
                and item.get("objectType") == type_key
            ),
            None,
        )
        if type_key in removed_types:
            continue  # it is the removed type's own (counted with its records)
        if owner is None:
            left(type_key, "values", count)
        else:
            counts[owner]["values"] += count
    for (relation, source, target), count in landing.relationship_losses.items():
        owner = next(
            (
                i
                for i, item in enumerate(removals)
                if (item["kind"] == "relationType" and item["key"] == relation)
                or source in reach[i]
                or target in reach[i]
            ),
            None,
        )
        if owner is None:
            left(source, "relationships", count)
        else:
            counts[owner]["relationships"] += count
    statements = []
    for item, found in zip(removals, counts, strict=True):
        name = named[item["kind"]].get(item["key"]) or item["key"]
        tail = [
            counted(found[kind], word)
            for kind, word in (
                ("records", "record"),
                ("values", "value"),
                ("relationships", "relationship"),
            )
            if found[kind]
        ]
        what = {
            "objectType": f"{name} is deleted",
            "application": f"the application {name} is removed",
            "attribute": f"the field {name} of "
            f"{named['objectType'].get(item.get('objectType'), item.get('objectType'))} is removed",
            "relationType": f"the relationship type {name} is removed",
        }[item["kind"]]
        sentence = f"As you asked, {what}" + (f", deleting {', '.join(tail)}." if tail else ".")
        if item["kind"] == "objectType" and item.get("movedTo"):
            # A partial move: the change set restructures the records into other types, so nothing
            # is deleted and their relationships go along with them.
            target_names = {
                found_item.get("key"): found_item.get("name") or found_item.get("key")
                for found_item in (final or {}).get("objectTypes") or []
            }
            targets = [target_names.get(key) or key for key in item["movedTo"]]
            where = (
                f"{', '.join(targets[:-1])} and {targets[-1]}" if len(targets) > 1 else targets[0]
            )
            records = found["records"]
            sentence = (
                f"As you asked, {name} is removed: "
                + (f"its {counted(records, 'record')} move" if records else "its records move")
                + f" to {where}."
            )
        statements.append({**item, "name": name, **found, "text": sentence})
    return rest, statements


def _consumer_changes(base: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    """The consumer APIs the draft raises the contractVersion of, from the engine's own diff."""
    try:
        return raised_contracts(parse_model(base), parse_model(model))
    except ModelValidationError:
        return []


def _records_per_type(session: Session, job_id: str | None) -> dict[str | None, int]:
    """What a dry run would write per type; under ``None``, the relationships, which have no type."""
    if job_id is None:
        return {}
    return dict(
        session.execute(
            text(
                "SELECT i.outcome ->> 'objectTypeKey', count(*) FROM job_items i"
                " JOIN jobs j ON j.sequence_id = i.job_id"
                " WHERE j.id = :job AND i.outcome ->> 'action' IN ('created', 'updated') GROUP BY 1"
            ),
            {"job": job_id},
        ).all()
    )


# How many times the engine's findings about a landed draft (the consumer contract, the records it
# would refuse to move) go back to the session before the task fails.
LANDING_ROUNDS = 2


def _send_back(
    session: Session,
    job: Job,
    ctx: Any,
    task_id: str,
    folder: Path,
    check_of: Any,
    prompt: str,
    round_: int,
) -> None:
    """Another turn of the session with the engine's findings; the proposal it writes lands again."""
    task = load_task(session, task_id)
    session_id = (task.design or {})["agentSession"]
    session.commit()
    drop(folder, PROPOSAL)
    again = run_turn(session, job, ctx, task_id, folder, prompt, session_id, first=False)
    if again is not None:
        _proposal_landed(session, ctx, task_id, folder, again, check_of, job, round_ + 1)


def _drafted_by(session: Session, task: AiTask, draft: ModelDraft) -> bool:
    """Whether the task's own client created this draft, as the engine recorded it."""
    if task.client_id is None:
        return False
    return (
        session.scalar(
            select(AuditEvent.sequence_id).where(
                AuditEvent.aggregate_type == "model_draft",
                AuditEvent.action == "created",
                AuditEvent.aggregate_id == draft.public_id,
                AuditEvent.actor_client_id == task.client_id,
            )
        )
        is not None
    )


QUESTION_MAX = 2000


def _question_text(text: str) -> str:
    """A question as the session wrote it: whole, so its ask is never cut off; only a runaway one is
    shortened, at a word, with an ellipsis."""
    text = text.strip()
    if len(text) <= QUESTION_MAX:
        return text
    return text[:QUESTION_MAX].rsplit(" ", 1)[0] + "…"


def _questions(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "text": _question_text(str(q.get("text"))),
            "options": [str(o) for o in q.get("options") or []],
            "assumed": q.get("assumed"),
        }
        for q in proposal.get("questions") or []
        if isinstance(q, dict) and q.get("text")
    ]


def _origin() -> dict[str, Any]:
    return {
        "kind": "ai",
        "provider": "claude-code",
        "model": None,
        "promptVersion": PROMPT_VERSION,
    }


def _without_model_change(session: Session, task: AiTask, proposal: Any) -> bool:
    """Whether the proposal is a words task's with an empty model part: the instruction is about the
    stored records, the session named no draft because none is needed, and it moves no type. A
    workbook task always needs a draft, for the types its rows go into."""
    if not isinstance(proposal, dict) or proposal.get("draftId") is not None:
        return False
    if proposal.get("moves") or not str(proposal.get("summary") or "").strip():
        return False
    return session.scalar(select(SourceFile.id).where(SourceFile.task_id == task.id)) is None


def _unchanged_landed(
    session: Session, ctx: Any, task: AiTask, proposal: dict[str, Any], progress: Progress
) -> None:
    """A proposal without a draft: the task shows the summary and the questions, the model as it is,
    and waits for the person. Accepting makes the change set on the live release."""
    design = dict(task.design or {})
    design.pop("progress", None)
    task.draft_id = None
    task.design = {
        **design,
        "stage": "model",
        "summary": str(proposal.get("summary") or ""),
        "modelUnchanged": True,
        "moves": [],
        "consumerChanges": [],
        "questions": _questions(proposal),
        "outline": [],
        "checks": [],
        "origin": _origin(),
        "outcome": {},
        "load": None,
        "itemsLoad": False,
    }
    task.check = None
    note(task, "note", closing_words(progress))
    finish(task, "checked", retention(ctx))
    task.finished_at = None
    session.commit()


def _proposal_landed(
    session: Session,
    ctx: Any,
    task_id: str,
    folder: Path,
    progress: Progress,
    check_of: Any,
    job: Job,
    round_: int = 0,
) -> None:
    """The proposal the session wrote: the task shows it and waits, or fails with what was said."""
    task = load_task(session, task_id, for_update=True)
    try:
        proposal = json.loads(read_work(folder, PROPOSAL) or "")
    except ValueError:
        proposal = None
    stated_title = title_of(proposal)
    if task.title is None and stated_title is not None:
        task.title = stated_title
    draft = (
        session.scalar(
            select(ModelDraft)
            .where(ModelDraft.public_id == str(proposal.get("draftId")))
            # The session corrects its draft through the API between rounds: read what is stored,
            # not the copy this session loaded in an earlier round.
            .execution_options(populate_existing=True)
        )
        if isinstance(proposal, dict) and proposal.get("draftId") is not None
        else None
    )
    if draft is not None and not _drafted_by(session, task, draft):
        # The ID is the session's word: a draft it did not create is a person's, not its to name (R-F3).
        # Trying again with the same draft cannot help: the session is told to make its own.
        if round_ < LANDING_ROUNDS:
            _send_back(session, job, ctx, task_id, folder, check_of, not_its_draft_prompt(), round_)
            return
        note(
            task,
            "warning",
            "The session kept proposing a draft that is not its own, which it may not use: it "
            "must make its own model draft. Leave the task out and start a new one",
        )
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    if draft is not None and held_by_another(session, draft.id, task.id):
        # Reading it is not refused, and a proposal must not name it either (AP-D44).
        note(task, "warning", "The session proposed a draft another task holds; try again")
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    if draft is None:
        if _without_model_change(session, task, proposal):
            _unchanged_landed(session, ctx, task, proposal, progress)
            return
        spoke = str(progress.result.get("result") or "").strip() and not progress.result.get(
            "is_error"
        )
        note(
            task,
            "warning",
            closing_words(progress)
            if spoke
            else "The session ended without a proposal and said nothing about why. Tell it how to "
            "go on, or try again as it was.",
        )
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    design = dict(task.design or {})
    design.pop("progress", None)
    design.pop("modelUnchanged", None)
    if task.title and not design.get("draftNamed"):
        # The draft is named by what the task asks, once; a person may rename it afterwards.
        draft.name = f"Assistant: {task.title}"[:300]
        design["draftNamed"] = True
    questions = _questions(proposal)
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    base = current.model_json
    errors: list[Any] = []
    requested = _requested_moves(proposal)
    try:
        migration = _migration_of(session, task.workspace_key, draft, current, None, requested)
    except ApiError as error:
        note(task, "warning", f"The draft's migration cannot be read: {error.message}")
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    mappings = migration["typeMappings"]
    extra = _extra_of(migration)
    # A draft on no release is a new model, compared with the workspace's only if it moves types.
    compared = bool(mappings or extra or proposal.get("moves") or draft.base_model_release_id)
    if compared:
        try:
            errors = _contract_errors(base, draft.model_json)
        except ModelValidationError:
            errors = []  # a draft that does not compile is the checks' to report
    if errors and round_ < LANDING_ROUNDS:
        # The session fixes the draft as it does any finding of the checks (AP-D47).
        _send_back(session, job, ctx, task_id, folder, check_of, contract_prompt(errors), round_)
        return
    if errors:
        note(
            task,
            "warning",
            f"The proposal still breaks consumers of the model: {contract_words(errors)}",
        )
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    held = held_counts(session, task.workspace_key)
    asked = frozenset(item["fromObjectTypeKey"] for item in requested)
    refusals: tuple[LandingRefusal, ...] = ()
    losses: dict[str, dict[str, int]] = {}
    unasked: dict[str, dict[str, int]] = {}
    removals = _requested_removals(proposal, _persons_text(task))
    stated: list[dict[str, Any]] = []
    try:
        moves = _planned_moves(migration, base, draft.model_json, held, requested=asked)
        if mappings or extra or draft.base_model_release_id:
            # The records are the engine's to check, as the migration's preview will (AP-D47), for
            # every kind of change: what the person's data would lose is measured on the migration
            # the task will hand over, whatever mappings, splits or conversions cause it.
            try:
                landing = check_landing(
                    session,
                    task.workspace_key,
                    parse_model(base),
                    parse_model(draft.model_json),
                    mappings,
                    extra,
                )
            except ApiError, ModelValidationError:
                if mappings or extra:
                    raise
                landing = (
                    None  # a draft with no mappings that does not check is not a migration yet
                )
            if landing is not None:
                refusals, losses = landing.refusals, landing.losses
                unasked, stated = _removal_account(landing, removals, base, draft.model_json)
                moves = _planned_moves(migration, base, draft.model_json, held, losses, asked)
    except (ApiError, ModelValidationError) as error:
        reason = error.message if isinstance(error, ApiError) else "the draft does not compile"
        note(task, "warning", f"The proposed moves cannot be made: {reason}")
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    if refusals:
        names = {
            item["key"]: item.get("name") or item["key"]
            for item in draft.model_json.get("objectTypes") or []
        }
        words = refusal_words(refusals, names)
        if round_ < LANDING_ROUNDS:
            _send_back(session, job, ctx, task_id, folder, check_of, refusal_prompt(words), round_)
            return
        note(
            task,
            "warning",
            f"The proposal still has records the engine would refuse to move: {words}",
        )
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    lost = loss_words(unasked, type_names(draft.model_json, base))
    if lost:
        # No migration that loses what the person did not ask to remove is offered (product rule,
        # 2026-11-09). The proposal records no removal the person asked for, so every loss counts.
        if round_ < LANDING_ROUNDS:
            _send_back(session, job, ctx, task_id, folder, check_of, loss_prompt(lost), round_)
            return
        note(
            task,
            "warning",
            f"The proposal would lose data: {lost}. Nothing was changed, and no migration is offered.",
        )
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    check = check_of(session, draft)
    # A dry run of items (0.13 AB) is what accepting loads: its summary is the task's, in the design.
    previewed = check.pop("itemsSummary", None) if check else None
    if previewed is not None and _previewed_elsewhere(session, task, check):
        # An items dry run can be made against any workspace; accepting loads into the task's
        # (R13-F6), so a check of another workspace's records is no check of this load.
        note(
            task,
            "warning",
            "The assistant checked its records against another workspace than this task's, so the "
            "check says nothing about this load and nothing was changed. Give the assistant other "
            "words to check again.",
        )
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    unstored = _unstored_profile(session, draft, check)
    if unstored is not None:
        note(task, "warning", unstored)
        finish(task, "failed", retention(ctx))
        session.commit()
        return
    records = _records_per_type(session, (check or {}).get("dryRunJobId"))
    related = records.pop(None, 0)
    if check and related and previewed is None:
        # The check counts a relationship as an item it creates; the person reads records and links.
        check["summary"]["created"] -= related
        check["summary"]["relationships"] = related
    task.draft_id = draft.id
    task.design = {
        **design,
        "stage": "model",
        "summary": str(proposal.get("summary") or ""),
        "moves": moves,
        "removals": stated,
        "consumerChanges": _consumer_changes(base, draft.model_json) if compared else [],
        "questions": questions,
        # A draft on no release is a new model: a type sharing a key with the old one is not a change.
        "outline": _shape(draft.model_json, base if draft.base_model_release_id else {}, records),
        "checks": [
            *_left_out(draft.model_json, base, held, frozenset(m["from"] for m in moves)),
            *(
                []
                if previewed is not None
                else _beside_held(session, (check or {}).get("dryRunJobId"), draft.model_json, held)
            ),
            *_cells_left_out(session, task, (check or {}).get("dryRunJobId")),
        ],
        "origin": _origin(),
        "outcome": {},
        "load": previewed,
        "itemsLoad": previewed is not None and not moves,
    }
    task.check = check
    for found in stated:
        note(task, "note", found["text"])
    if mappings or extra:
        for found in migration["notes"]:
            note(task, "note", found["message"])
    note(task, "note", closing_words(progress))
    finish(task, "checked", retention(ctx))
    task.finished_at = None
    session.commit()


def start(
    session: Session,
    job: Job,
    ctx: Any,
    task_id: str,
    workbook_path: Path | None,
    check_of: Any,
    extra: str | None = None,
) -> None:
    """The session's first turn: the workbook to a draft the person reviews. ``extra`` is what the
    person said when the session starts again on a task that had none, or whose first turn never ran."""
    ensure_folder(session, ctx.files, task_id)
    task = load_task(session, task_id)
    workspace = task.workspace_key
    words = task.words
    url = api_url()
    release = session.get(ModelRelease, load_assignment(session, workspace)[1].id)
    model_json = json.dumps(release.model_json)
    folder = folder_of(ctx.files, task)
    # The task's row is not held across the copy and the call to the engine's own API (R-F20).
    session.commit()
    make_folders(folder)
    # Made new in a folder a session may have shaped: never through a link in the way.
    if workbook_path is not None:
        put(folder, "workbook.xlsx", workbook_path.read_bytes())
    put(folder, "model.json", model_json.encode())
    put(folder, "openapi.json", openapi(url))
    task = load_task(session, task_id, for_update=True)
    session_id = str(uuid4())
    design = {key: value for key, value in (task.design or {}).items() if key != "agentCost"}
    task.design = {
        **design,
        "stage": "model",
        "agentSession": session_id,
        "agentProvider": provider(),
        "agentPrompt": PROMPT_VERSION,
    }
    task.state = "reading"
    session.commit()
    prompt = propose_prompt(
        words, workspace, url, held_counts(session, workspace), workbook=workbook_path is not None
    )
    if extra:
        prompt = f"{prompt}\n\nThe person adds:\n{extra}"
    progress = run_turn(session, job, ctx, task_id, folder, prompt, session_id, first=True)
    if progress is not None:
        _proposal_landed(session, ctx, task_id, folder, progress, check_of, job)


def said(session: Session, job: Job, ctx: Any, task_id: str, words: str, check_of: Any) -> None:
    """The person's answers or corrections: the same session goes on."""
    task = load_task(session, task_id)
    folder = folder_of(ctx.files, task)
    drop(folder, PROPOSAL)
    progress = run_turn(
        session,
        job,
        ctx,
        task_id,
        folder,
        said_prompt(words),
        (task.design or {})["agentSession"],
        first=False,
    )
    if progress is not None:
        _proposal_landed(session, ctx, task_id, folder, progress, check_of, job)


def _last_line(words: str, label: str) -> str | None:
    return next(
        (
            line.split(label, 1)[1].strip().strip("`*")
            for line in reversed(words.splitlines())
            if label in line
        ),
        None,
    )


def _installed_by(session: Session, task: AiTask, public_id: str | None) -> ModelRelease | None:
    """A release the task's own client installed (AP-D45): a session's word for an ID counts only
    if the engine recorded the installation."""
    if not public_id or task.client_id is None:
        return None
    done = session.scalar(
        select(AuditEvent.aggregate_id).where(
            AuditEvent.aggregate_type == "model_release",
            AuditEvent.action == "installed",
            AuditEvent.actor_client_id == task.client_id,
            AuditEvent.aggregate_id == public_id,
        )
    )
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == public_id))
    if done is None and release is not None and task.draft_id is not None:
        # Installing content the instance already holds returns that release and records no new
        # installation (found 2026-11-12: the same move made in a second workspace failed as "installed
        # no release"). It is the session's own when its content is the task's draft.
        draft = session.get(ModelDraft, task.draft_id)
        compiled = compile_model(draft.model_json) if draft is not None else None
        if (
            compiled is not None
            and compiled.model is not None
            and compiled.valid
            and canonical_model(compiled.model)[1] == release.model_hash
        ):
            return release
    return release if done is not None else None


def _migration_result(session: Session, task: AiTask, words: str) -> dict[str, Any] | None:
    """The end of a task whose proposal moved whole types (AP-D49): the release the session
    installed and the type mappings, re-checked against that release as the person may have edited
    the draft. ``None`` when the session installed nothing the mappings fit."""
    release = _installed_by(session, task, _last_line(words, RELEASE_LINE))
    if release is None:
        return None
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    draft = session.get(ModelDraft, task.draft_id) if task.draft_id else None
    requested = [
        {
            "fromObjectTypeKey": move["from"],
            "toObjectTypeKey": move["to"],
            "attributes": move.get("attributes") or [],
        }
        for move in (task.design or {}).get("moves") or []
        if move.get("fromSession", True)
    ]
    try:
        migration = _migration_of(session, task.workspace_key, draft, current, release, requested)
        mappings = migration["typeMappings"]
        extra = _extra_of(migration)
        parsed = Mappings.of({"typeMappings": mappings, **extra})
        plan_migration(
            parse_model(current.model_json),
            parse_model(release.model_json),
            parsed.types,
            parsed.relations,
            parsed.spawns,
        )
        errors = _contract_errors(current.model_json, release.model_json)
        landing = check_landing(
            session,
            task.workspace_key,
            parse_model(current.model_json),
            parse_model(release.model_json),
            mappings,
            extra,
        )
    except ApiError, ModelValidationError:
        return None
    if errors:
        note(
            task,
            "warning",
            f"The installed release breaks consumers of the model: {contract_words(errors)}",
        )
        return None
    unasked, stated = _removal_account(
        landing, (task.design or {}).get("removals") or [], current.model_json, release.model_json
    )
    lost = loss_words(unasked, type_names(current.model_json, release.model_json))
    if lost:
        # No migration is returned, so the person cannot confirm one: the data is as it was.
        note(
            task,
            "warning",
            f"The installed release would lose data: {lost}. No data was changed, and no migration "
            "is offered to confirm.",
        )
        task.design = {**(task.design or {}), "withheld": True}
        return None
    for found in stated:
        note(task, "note", found["text"])
    if landing.refusals:
        names = {item.key: item.name for item in parse_model(release.model_json).objectTypes}
        words = refusal_words(landing.refusals, names)
        note(
            task,
            "warning",
            f"The installed release has records the engine would refuse to move: {words}",
        )
        return None
    return {"migration": {"releaseId": release.public_id, "typeMappings": mappings, **extra}}


def _change_set_of(session: Session, task: AiTask, change_set_id: str | None) -> ChangeSet | None:
    """The change set the session's last line names, when the task's own client made it: the line is
    the session's word, and a person's change set is not its to hand over (R-F4)."""
    if not change_set_id or task.client_id is None:
        return None
    return session.scalar(
        select(ChangeSet).where(
            ChangeSet.id == change_set_id, ChangeSet.created_by_client_id == task.client_id
        )
    )


def accepted(session: Session, job: Job, ctx: Any, task_id: str, words: str | None = None) -> None:
    """The person accepted: the same session installs one release and loads into a change set, or,
    when the proposal moved whole types, installs the release a migration will move to (AP-D46).
    ``words`` are the person's, on a second try (AP-D54). The folder and the client stay until the
    work is in the person's hands for good (AP-D56)."""
    task = load_task(session, task_id)
    folder = folder_of(ctx.files, task)
    moves = (task.design or {}).get("moves")
    unchanged = bool((task.design or {}).get("modelUnchanged"))
    progress = run_turn(
        session,
        job,
        ctx,
        task_id,
        folder,
        reprompt(MOVED if moves else ACCEPTED_UNCHANGED if unchanged else ACCEPTED, words),
        (task.design or {})["agentSession"],
        first=False,
        load=True,
    )
    if progress is None:
        return
    words = str(progress.result.get("result") or "")
    task = load_task(session, task_id, for_update=True)
    design = dict(task.design or {})
    design.pop("progress", None)
    task.design = design
    note(task, "note", closing_words(progress))
    if moves:
        # No change set, and the data is not touched: the person confirms the migration (AP-D49).
        result = _migration_result(session, task, words)
        if result is None:
            if not (task.design or {}).get("withheld"):
                note(task, "warning", "The session installed no release the moves fit")
            finish(task, "failed", retention(ctx))
        else:
            task.result = result
            finish(task, "loaded", retention(ctx))
        session.commit()
        return
    change_set_id = _last_line(words, LAST_LINE)
    change_set = _change_set_of(session, task, change_set_id)
    if (
        not unchanged
        and _last_line(words, RELEASE_LINE)
        and (
            change_set is None
            or (
                change_set.workspace_key == task.workspace_key
                and not holds_changes(counts_of(session, change_set.id))
            )
        )
    ):
        # The model alone changes: the migration ending with no type mappings (the records stay).
        result = _migration_result(session, task, words)
        if result is None and (task.design or {}).get("withheld"):
            finish(task, "failed", retention(ctx))
            session.commit()
            return
        if result is not None:
            task.result = result
            finish(task, "loaded", retention(ctx))
            if change_set is not None:
                # The empty change set the session made is not left dangling (commits).
                session.flush()
                discard_change_set(session, change_set.id, change_set.version)
            session.commit()
            return
    if not _land(session, task, words, change_set_id, change_set, retention(ctx)):
        # The words stay: a later read lands the load under the rules of the day (:func:`recover_load`).
        task.design = {**(task.design or {}), "loadWords": words[-4000:]}
    session.commit()


def _landing(
    session: Session,
    task: AiTask,
    words: str,
    change_set_id: str | None,
    change_set: ChangeSet | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """What a load that ended well leaves on the task, or ``None`` and why not (the reason may be
    ``None`` when a note already says it). An empty change set is no load, whatever the session's
    last line says; one that holds only relationships is one."""
    unchanged = bool((task.design or {}).get("modelUnchanged"))
    counts = counts_of(session, change_set.id) if change_set is not None else None
    if change_set is None:
        return None, (
            "The session named no change set of this task's own, so nothing was loaded"
            if change_set_id
            else "The session ended without naming the change set it loaded into, so nothing was loaded"
        )
    if change_set.workspace_key != task.workspace_key:
        return None, "The session's change set is in another workspace, so nothing was loaded"
    if not holds_changes(counts):
        return None, (
            "The session's change set holds no record or relationship to add, change or remove, "
            "so nothing was loaded"
        )
    if (
        unchanged
        and change_set.model_release_id != load_assignment(session, task.workspace_key)[1].id
    ):
        # The model does not change: the change set is on the release the workspace runs, or it is not
        # the change the person accepted.
        return None, "The change set is not on the model the workspace runs"
    then = _then_release(session, task, words, change_set)
    if then is None:
        return None, None
    return {
        "changeSetId": change_set.id,
        "changeSetName": change_set.name,
        "counts": counts,
        **_saved_profile(session, task, change_set),
        **then,
        **_change_set_release(session, change_set, then),
    }, None


def _land(
    session: Session,
    task: AiTask,
    words: str,
    change_set_id: str | None,
    change_set: ChangeSet | None,
    retention_days: int,
) -> bool:
    """End a load: ``loaded`` with its result, or ``failed`` with the reason, keeping any change set
    the session did write reachable on the task (a person never lands on a task with no way
    forward). Whether it loaded."""
    result, reason = _landing(session, task, words, change_set_id, change_set)
    if result is None:
        if reason:
            note(task, "warning", reason)
        finish(task, "failed", retention_days)
        _keep_written(session, task, change_set)
        return False
    task.result = result
    finish(task, "loaded", retention_days)
    return True


def _keep_written(session: Session, task: AiTask, change_set: ChangeSet | None) -> None:
    """A failed load that left a change set holding changes: it stays on the task, to review or to
    discard, and is never orphaned by a second try."""
    if change_set is None or change_set.workspace_key != task.workspace_key:
        return
    counts = counts_of(session, change_set.id)
    if holds_changes(counts):
        task.result = {
            "changeSetId": change_set.id,
            "changeSetName": change_set.name,
            "counts": counts,
        }


def _session_change_sets(session: Session, task: AiTask) -> list[ChangeSet]:
    """The open change sets the task's own client made in its workspace, the most recent first."""
    return list(
        session.scalars(
            select(ChangeSet)
            .where(
                ChangeSet.created_by_client_id == task.client_id,
                ChangeSet.workspace_key == task.workspace_key,
            )
            .order_by(ChangeSet.created_at.desc(), ChangeSet.sequence_id.desc())
        )
    )


def recover_load(session: Session, task: AiTask, retention_days: int) -> None:
    """A failed task at the load stage whose session has not ended, read again: the rules may have
    moved on since it failed (a load that only linked records was once no load). When the session's own
    change set (the task's client made it, the most recent that holds changes) now passes the landing
    checks the task is ``loaded``; otherwise the change set stays reachable on the task. Idempotent."""
    design = task.design or {}
    if (
        task.state != "failed"
        or design.get("stage") != "load"
        or design.get("moves")
        or not design.get("agentSession")
        or design.get("sessionEnded")
        or task.client_id is None
    ):
        return
    kept = (task.result or {}).get("changeSetId")
    change_set = next(
        (c for c in _session_change_sets(session, task) if holds_changes(counts_of(session, c.id))),
        None,
    )
    if change_set is None:
        if kept and session.scalar(select(ChangeSet.id).where(ChangeSet.id == kept)) is None:
            # What the task kept was published or discarded elsewhere.
            task.result = None
            session.flush()
        return
    notes = task.notes
    result, _ = _landing(
        session, task, str(design.get("loadWords") or ""), change_set.id, change_set
    )
    if result is None:
        task.notes = notes
        if kept != change_set.id:
            _keep_written(session, task, change_set)
            session.flush()
        return
    task.notes = [n for n in notes if n.get("kind") != "warning"]
    task.result = result
    finish(task, "loaded", retention_days)
    session.flush()


def end_session(
    session: Session, files: Any, task: AiTask, *, retire_releases: bool = True
) -> None:
    """The session's work is in the person's hands for good (AP-D56): the change set was published or
    discarded, the migration confirmed, or the task discarded. Its folder, transcript and client go,
    and a release it installed that nothing runs is retired (not after a publication, which ran on
    one). The caller commits."""
    design = dict(task.design or {})
    if not design.get("agentSession") or design.get("sessionEnded"):
        return
    remove_folder(files, task)
    if retire_releases:
        retire_unused_releases(session, task)
    retire_session_client(session, task.client_id)
    task.design = {**design, "sessionEnded": True}


def lives(task: AiTask) -> bool:
    """Whether the task's session can still be told something."""
    design = task.design or {}
    return bool(design.get("agentSession")) and not design.get("sessionEnded")


def _change_set_release(
    session: Session, change_set: ChangeSet, then: dict[str, str]
) -> dict[str, str]:
    """The change set's own release, next to the final one: when they are the same, the old types
    stay and there is no third step."""
    if not then:
        return {}
    release = session.get(ModelRelease, change_set.model_release_id)
    return {"changeSetReleaseId": release.public_id} if release is not None else {}


def _final_release_found(
    session: Session, task: AiTask, change_set: ChangeSet
) -> ModelRelease | None:
    """The final release of a part-of-a-type reshaping, read from what the engine recorded rather than
    from the session's last line: the newest release the task's client installed, other than the
    change set's own, whose types are exactly the change set's release without the old types
    beside the new ones. ``None`` when there is no such release (a load that moves nothing)."""
    if task.client_id is None:
        return None
    own = session.get(ModelRelease, change_set.model_release_id)
    if own is None:
        return None
    beside = {item.get("key") for item in own.model_json.get("objectTypes") or []}
    installed = session.scalars(
        select(AuditEvent.aggregate_id)
        .where(
            AuditEvent.aggregate_type == "model_release",
            AuditEvent.action == "installed",
            AuditEvent.actor_client_id == task.client_id,
        )
        .order_by(AuditEvent.sequence_id.desc())
    ).all()
    for public_id in installed:
        if public_id == own.public_id:
            continue
        found = session.scalar(select(ModelRelease).where(ModelRelease.public_id == public_id))
        types = (
            {item.get("key") for item in (found.model_json.get("objectTypes") or [])}
            if found
            else set()
        )
        if found is not None and types < beside:
            return found
    return None


def _then_release(
    session: Session, task: AiTask, words: str, change_set: ChangeSet | None = None
) -> dict[str, str] | None:
    """The final release of a part-of-a-type reshaping: the third step, the person's, activates it
    once the old types hold no record (AP-D48). ``None`` when the engine would refuse that
    activation for the consumers of the model (C-D17); the warning names them."""
    named = _last_line(words, THEN_LINE)
    release = _installed_by(session, task, named)
    if release is None and change_set is not None:
        # The session's word is a hint: the engine finds the final release from what it recorded.
        release = _final_release_found(session, task, change_set)
    if release is None and named is None:
        if any(item.get("movedTo") for item in (task.design or {}).get("removals") or []):
            # A partial move without its final release has no steps to show: say so, not nothing.
            note(
                task,
                "warning",
                "The session did not name the final release, so the steps to finish the move are not "
                "shown. Tell the assistant to go on and name it.",
            )
        return {}
    if release is None:
        note(task, "warning", "The session named a final release it did not install")
        return {}
    current = session.get(ModelRelease, load_assignment(session, task.workspace_key)[1].id)
    try:
        errors = _contract_errors(current.model_json, release.model_json)
    except ModelValidationError:
        errors = []
    if errors:
        note(
            task,
            "warning",
            f"The final release breaks consumers of the model: {contract_words(errors)}",
        )
        return None
    return {"thenReleaseId": release.public_id}


def _profile_key(session: Session, name: str, release: ModelRelease) -> str:
    """The file's name as a key; a key another model's profile holds gets the release's model too."""
    stem = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")[:100] or "workbook"
    found = session.scalar(select(ImportProfile).where(ImportProfile.key == stem))
    if found is None or model_key_of(session, found) == release.release_key:
        return stem
    return f"{stem}-{release.release_key}"[:160]


def _saved_profile(session: Session, task: AiTask, change_set: ChangeSet) -> dict[str, str]:
    """What the load leaves for the next file: the profile of the imports it ran on the task's
    workbook, saved by the engine whatever route the session took (AP-D41), or why there is none."""
    source = session.scalar(select(SourceFile).where(SourceFile.task_id == task.id))
    if source is None:
        return {}
    jobs = list(
        session.scalars(
            select(Job)
            .where(
                Job.kind == "import",
                Job.state == "completed",
                Job.change_set_id == change_set.id,
                Job.parameters["file"]["sha256"].as_string() == source.sha256,
            )
            .order_by(Job.sequence_id)
        )
    )
    if not jobs:
        return {
            "profileNotSaved": "This load did not import the workbook, so it cannot be repeated."
        }
    definitions = [(job.parameters.get("profile") or {}).get("definition") for job in jobs]
    if not all(definitions):
        return {"profileNotSaved": "This load read the workbook through a profile already saved."}
    sources = [found for definition in definitions for found in definition["sources"]]
    keyless = sorted(
        {
            str(found.get("sheet") or "the file")
            for found in sources
            if not found.get("key") and found.get("record") != "existing"
        }
    )
    if keyless:
        names = ", ".join(f"“{sheet}”" for sheet in keyless)
        return {
            "profileNotSaved": f"Not saved as a profile: {names} has no key, so a second load would "
            "create its rows again."
        }
    definition = {
        **definitions[-1],
        "sources": sources,
        "valueMaps": {
            k: v for found in definitions for k, v in (found.get("valueMaps") or {}).items()
        },
    }
    release = session.get(ModelRelease, change_set.model_release_id)
    key = _profile_key(session, source.name, release)
    try:
        save_for_release(session, key, source.name[:200], definition, release)
    except ApiError as error:
        return {"profileNotSaved": f"Not saved as a profile: {error.message}"}
    # The import read this layout: the next file is compared with this one's headers, however the
    # session sent the file.
    for job in jobs:
        job.parameters = {
            **job.parameters,
            "sourceFileId": source.public_id,
            "profile": {**job.parameters["profile"], "key": key},
        }
    return {"profileKey": key}


def retire_unused_releases(session: Session, task: AiTask) -> None:
    """A release the task's client installed that no workspace or change set runs is retired, as
    "exactly one release" is only a prompt (AP-D45); history may name it, so it stays."""
    if task.client_id is None:
        return
    result = task.result or {}
    kept = {
        result.get("thenReleaseId"),
        (result.get("migration") or {}).get("releaseId"),
    } - {None}
    installed = select(AuditEvent.aggregate_id).where(
        AuditEvent.aggregate_type == "model_release",
        AuditEvent.action == "installed",
        AuditEvent.actor_client_id == task.client_id,
    )
    for release in session.scalars(
        select(ModelRelease).where(
            ModelRelease.public_id.in_(installed),
            ModelRelease.public_id.not_in(kept),
            ModelRelease.status != "retired",
            ~ModelRelease.id.in_(select(WorkspaceModel.model_release_id)),
            ~ModelRelease.id.in_(select(ChangeSet.model_release_id)),
        )
    ):
        set_release_status(session, release.public_id, "retired", release.status_version)
