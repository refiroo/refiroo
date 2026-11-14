"""Publishing a change set onto live data, and withdrawing a publication (ADR-026/027/031)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    AuditEvent,
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ChangeSetRelation,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    RelationSetVersion,
    Workspace,
)
from ..authorization.writes import requester_of
from ..identity.principals import columns
from ..indexes import matrix_states
from ..indexes.snapshot_values import copy_live
from ..notifications.following import announce_publication
from ..records.attributes import load_workspace_attribute_values
from ..records.audit import AuditEntry, audit_cause
from ..records.feed import object_subject, relation_subject
from ..records.relation_set_versions import merge_change_set_relation_set_versions_to_live
from ..records.writes import ChangeSetWrites, LiveWrites
from ..workspaces.workspace_audit import record_change_set_published, record_publication_withdrawn
from .access import EffectiveChangeSetMembership, load_change_set
from .lifecycle import delete_change_set_and_base
from .validation import cap_per_code, graph_diagnostics, is_parent_pair


@dataclass(frozen=True)
class MergedObject:
    object_id: str
    application_key: str
    object_type_key: str
    name: str
    parent_object_id: str | None
    attributes: dict[str, Any]
    version: int
    # Who proposed it when the AI did (0.16 AP9): copied into its audit entry.
    origin: dict[str, Any] | None = None


@dataclass(frozen=True)
class MergedRelation:
    relation_id: str
    relation_type_key: str
    from_object_id: str
    to_object_id: str
    attributes: dict[str, Any]
    version: int
    # Who proposed it when the AI did (0.16 AP2): copied into its audit entry.
    origin: dict[str, Any] | None = None


@dataclass
class LiveMerge:
    membership: EffectiveChangeSetMembership
    authored_object_ids: set[str]
    authored_relation_ids: set[str]
    removed_object_ids: set[str]
    removed_relation_ids: set[str]
    # Live data before the publish, for what it changes (D15, D32).
    live_objects: dict[str, MergedObject]
    live_relations: dict[str, MergedRelation]
    # Who proposed a removal when the AI did, by record or relation ID (0.16 AP9).
    removal_origins: dict[str, dict[str, Any]] = field(default_factory=dict)


def _with_origin(changes: dict[str, Any], origin: dict[str, Any] | None) -> dict[str, Any]:
    return {**changes, "origin": origin} if origin else changes


def _changed_values(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def publish_entries(merge: LiveMerge, model: Any) -> list[AuditEntry]:
    """The audit entries of what a publish changes in live data (Base 0.9 D15, D32): records
    created, changed or reclassified; relations removed; relations created or changed; records
    removed. Each names the fields and attribute types that changed, never values (D16). An
    authored row equal to live changes nothing and has none. A containment relation is the
    record's parent, which the record's entry names, as a live move does.
    """
    merged_objects = {item.object_id: item for item in merge.membership.objects}
    merged_relations = {item.relation_id: item for item in merge.membership.relations}

    def contains(relation: MergedRelation) -> bool:
        # Under the child's type before the publish or after it: a reclassified child's old
        # containment relation is removed and a new one added.
        children = (
            merged_objects.get(relation.to_object_id),
            merge.live_objects.get(relation.to_object_id),
        )
        return any(
            relation.relation_type_key in model.containment_relation_keys(child.object_type_key)
            for child in children
            if child is not None
        )

    entries: list[AuditEntry] = []
    for object_id in sorted(merge.authored_object_ids):
        after, before = merged_objects[object_id], merge.live_objects.get(object_id)
        if before is None:
            fields = ["name", "parentObjectId", "attributes"]
            entries.append(
                AuditEntry(
                    "object",
                    object_id,
                    "created",
                    after.version,
                    _with_origin(
                        {"changedFields": fields, "attributeTypeKeys": sorted(after.attributes)},
                        after.origin,
                    ),
                    (object_id,),
                    object_subject(after),
                )
            )
            continue
        retyped = (before.object_type_key, before.application_key) != (
            after.object_type_key,
            after.application_key,
        )
        values = _changed_values(before.attributes, after.attributes)
        fields = [
            field
            for field, changed in (
                ("objectType", retyped),
                ("name", before.name != after.name),
                ("parentObjectId", before.parent_object_id != after.parent_object_id),
                ("attributes", bool(values)),
            )
            if changed
        ]
        if not fields and before.version == after.version:
            continue
        entries.append(
            AuditEntry(
                "object",
                object_id,
                "reclassified" if retyped else "updated",
                after.version,
                _with_origin({"changedFields": fields, "attributeTypeKeys": values}, after.origin),
                (object_id,),
                object_subject(
                    after,
                    before.object_type_key if retyped else None,
                    previous_parent_object_id=before.parent_object_id,
                    moved=before.parent_object_id != after.parent_object_id,
                ),
            )
        )
    for relation_id in sorted(merge.removed_relation_ids):
        before = merge.live_relations[relation_id]
        if contains(before):
            continue
        entries.append(
            _relation_entry(before, "deleted", [], [], merge.removal_origins.get(relation_id))
        )
    for relation_id in sorted(merge.authored_relation_ids):
        after, before = merged_relations[relation_id], merge.live_relations.get(relation_id)
        if contains(after):
            continue
        if before is None:
            entries.append(
                _relation_entry(after, "created", ["attributes"], sorted(after.attributes))
            )
            continue
        values = _changed_values(before.attributes, after.attributes)
        if values or before.version != after.version:
            entries.append(
                _relation_entry(after, "updated", ["attributes"] if values else [], values)
            )
    for object_id in sorted(merge.removed_object_ids):
        before = merge.live_objects[object_id]
        entries.append(
            AuditEntry(
                "object",
                object_id,
                "deleted",
                before.version,
                _with_origin(
                    {"changedFields": [], "attributeTypeKeys": []},
                    merge.removal_origins.get(object_id),
                ),
                (object_id,),
                object_subject(before),
            )
        )
    return entries


def _relation_entry(
    relation: MergedRelation,
    action: str,
    fields: list[str],
    attribute_type_keys: list[str],
    origin: dict[str, Any] | None = None,
) -> AuditEntry:
    changes = _with_origin(
        {"changedFields": fields, "attributeTypeKeys": attribute_type_keys},
        origin or (relation.origin if action != "deleted" else None),
    )
    return AuditEntry(
        "relation",
        relation.relation_id,
        action,
        relation.version,
        changes,
        (relation.from_object_id, relation.to_object_id),
        relation_subject(
            relation.relation_type_key, relation.from_object_id, relation.to_object_id
        ),
    )


def _publication_snapshot_maps(
    session: Session, change_set: ChangeSet
) -> tuple[
    dict[str, PublicationObject | ChangeSetBaseObject],
    dict[str, PublicationRelation | ChangeSetBaseRelation],
]:
    """Index the immutable source snapshot by stable id (empty for a legacy root change set)."""
    if change_set.base_id is not None:
        base = session.get(ChangeSetBase, change_set.base_id)
        if base is None or base.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "CHANGE_SET_BASE_INVALID",
                "Change set current-live base is missing or belongs to another workspace",
            )
        return (
            {
                item.object_id: item
                for item in session.scalars(
                    select(ChangeSetBaseObject).where(ChangeSetBaseObject.base_id == base.id)
                )
            },
            {
                item.relation_id: item
                for item in session.scalars(
                    select(ChangeSetBaseRelation).where(ChangeSetBaseRelation.base_id == base.id)
                )
            },
        )
    if change_set.derived_from_publication_id is None:
        return {}, {}
    objects = {
        item.object_id: item
        for item in session.scalars(
            select(PublicationObject).where(
                PublicationObject.publication_id == change_set.derived_from_publication_id
            )
        )
    }
    relations = {
        item.relation_id: item
        for item in session.scalars(
            select(PublicationRelation).where(
                PublicationRelation.publication_id == change_set.derived_from_publication_id
            )
        )
    }
    return objects, relations


def _merge_version_conflict(
    kind: str, conflict_id: str, *, expected: int | None, actual: int | None
) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": conflict_id,
        "code": "VERSION_MISMATCH",
        "message": f"{kind.title()} changed live after the change set's base publication",
        "expectedVersion": expected,
        "actualVersion": actual,
    }


def _mapping_set_merge_conflicts(
    session: Session,
    change_set: ChangeSet,
    model: Any,
    base_objects: dict[str, Any],
    base_relations: dict[str, Any],
    live_objects: dict[str, RdmObject],
    live_relations: dict[str, ObjectRelation],
) -> list[dict[str, Any]]:
    """Compare the complete source/live sets touched by staged mutable relation writes.

    Edge identities and edge versions are the immutable source's fingerprint. This catches
    additions/removals elsewhere in a touched set, which individual COW-row checks miss.
    Containment/ownership retain the existing record and complete-graph merge semantics.
    """
    mutable_bindings = {
        (pair.relationTypeKey, pair.fromObjectTypeKey, pair.toObjectTypeKey)
        for pair in model.objectTypeRelations
        if not is_parent_pair(model, pair)
        and not (pair.required and pair.cardinality in {"one-to-one", "one-to-many"})
    }
    touched = {
        (
            row.relation_type_key,
            row.from_object_type_key,
            row.to_object_type_key,
            row.anchor_object_id,
            row.direction,
        )
        for row in session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == change_set.workspace_key,
                RelationSetVersion.change_set_id == change_set.id,
            )
        )
        if (row.relation_type_key, row.from_object_type_key, row.to_object_type_key)
        in mutable_bindings
    }
    if not touched:
        return []

    def fingerprints(objects, relations):
        result = {key: {} for key in touched}
        for relation_id, edge in relations.items():
            source, target = objects.get(edge.from_object_id), objects.get(edge.to_object_id)
            if source is None or target is None:
                continue
            binding = (edge.relation_type_key, source.object_type_key, target.object_type_key)
            for anchor, direction in (
                (edge.from_object_id, "outgoing"),
                (edge.to_object_id, "incoming"),
            ):
                key = (*binding, anchor, direction)
                if key in result:
                    result[key][relation_id] = edge.version
        return result

    expected = fingerprints(base_objects, base_relations)
    actual = fingerprints(live_objects, live_relations)
    return [
        {
            "kind": "mapping-set",
            "id": anchor,
            "anchorObjectId": anchor,
            "relationTypeKey": relation_type,
            "fromObjectTypeKey": from_type,
            "toObjectTypeKey": to_type,
            "direction": direction,
            "code": "MAPPING_SET_CHANGED",
            "expectedTargetCount": len(expected[key]),
            "actualTargetCount": len(actual[key]),
            "message": "Mapping relationships changed live since this change set's source. "
            "Review live mappings and reapply the intended changes in a change set created "
            "from current live data before retrying the publish.",
        }
        for key in sorted(touched)
        for relation_type, from_type, to_type, anchor, direction in [key]
        if expected[key] != actual[key]
    ]


def _merge_change_set_over_live(
    session: Session,
    change_set: ChangeSet,
    base_objects: dict[str, PublicationObject | ChangeSetBaseObject],
    base_relations: dict[str, PublicationRelation | ChangeSetBaseRelation],
    model: Any,
    *,
    collect: list[dict[str, Any]] | None = None,
) -> LiveMerge:
    """Compute the live content that would result from applying the change set's delta.

    With ``collect``, the per-record conflicts are added to it instead of refusing the merge, for
    a preview that lists them (0.11 V2, D82).

    The current live projection is authoritative and is the substrate; only records the change set
    actually authored (created / edited / tombstoned relative to its derived-from publication) are
    applied onto it.  A change set touch on a base record requires the live record to still sit at the
    exact base-publication version (no concurrent live edit since the snapshot), and an id created in the change set
    must not already exist live; any divergence is a per-record conflict (``409 version_conflict``)
    rather than an overwrite.  Live content the change set never touched is preserved untouched.
    """
    workspace_key = change_set.workspace_key
    live_objects = {
        item.id: item
        for item in session.scalars(
            select(RdmObject).where(RdmObject.workspace_key == workspace_key)
        )
    }
    object_ids = sorted(live_objects)
    attribute_rows = load_workspace_attribute_values(session, object_ids, workspace_key)
    merged_objects: dict[str, MergedObject] = {}
    for object_id in object_ids:
        live = live_objects[object_id]
        merged_objects[object_id] = MergedObject(
            object_id=object_id,
            application_key=live.application_key,
            object_type_key=live.object_type_key,
            name=live.name,
            parent_object_id=live.parent_object_id,
            attributes={key: value for key, (_row_id, value) in attribute_rows[object_id].items()},
            version=live.version,
        )
    live_relations: dict[str, ObjectRelation] = {}

    # One primary-key probe per end. ``IN (subquery) OR IN (subquery)`` cannot be hashed, and
    # PostgreSQL re-ran the subquery per relationship: 30 minutes at 258,000 records (0.9 T1).
    def in_workspace(end: Any) -> Any:
        return exists().where(RdmObject.id == end, RdmObject.workspace_key == workspace_key)

    if object_ids:
        live_relations = {
            item.id: item
            for item in session.scalars(
                select(ObjectRelation).where(
                    or_(
                        in_workspace(ObjectRelation.from_object_id),
                        in_workspace(ObjectRelation.to_object_id),
                    )
                )
            )
        }
    merged_relations: dict[str, MergedRelation] = {
        relation_id: MergedRelation(
            relation_id=relation_id,
            relation_type_key=relation.relation_type_key,
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
            attributes=dict(relation.attributes or {}),
            version=relation.version,
        )
        for relation_id, relation in live_relations.items()
    }

    live_state, live_relation_state = dict(merged_objects), dict(merged_relations)
    mapping_conflicts = _mapping_set_merge_conflicts(
        session, change_set, model, base_objects, base_relations, live_objects, live_relations
    )
    conflicts: list[dict[str, Any]] = mapping_conflicts[:20]
    authored_object_ids: set[str] = set()
    change_set_objects = {
        item.object_id: item
        for item in session.scalars(
            select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set.id)
        )
    }
    # Joined to the change set's rows rather than listed: a change set may hold more records than
    # PostgreSQL's 65,535 parameters (0.11 X5: a move's load of 110,000).
    global_object_ids = set(
        session.scalars(
            select(RdmObject.id)
            .join(ChangeSetObject, ChangeSetObject.object_id == RdmObject.id)
            .where(ChangeSetObject.change_set_id == change_set.id)
        )
    )
    removal_origins: dict[str, dict[str, Any]] = {}
    for object_id, row in change_set_objects.items():
        base = base_objects.get(object_id)
        if row.is_deleted:
            if base is None:
                continue  # created then deleted inside the change set: never reached live
            if row.origin:
                removal_origins[object_id] = row.origin
            live = live_objects.get(object_id)
            if live is not None and live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "object", object_id, expected=base.version, actual=live.version
                    )
                )
            merged_objects.pop(object_id, None)
            continue
        authored_object_ids.add(object_id)
        authored = MergedObject(
            object_id=object_id,
            application_key=row.application_key,
            object_type_key=row.object_type_key,
            name=row.name,
            parent_object_id=row.parent_object_id,
            attributes=dict(row.attributes or {}),
            version=row.version,
            origin=row.origin,
        )
        if base is not None:
            live = live_objects.get(object_id)
            if live is None or live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "object",
                        object_id,
                        expected=base.version,
                        actual=live.version if live is not None else None,
                    )
                )
            merged_objects[object_id] = authored
        else:
            if object_id in global_object_ids:
                conflicts.append(
                    {
                        "kind": "object",
                        "id": object_id,
                        "code": "ID_COLLISION",
                        "message": "The id of an object created in the change set already exists in live data",
                    }
                )
            merged_objects[object_id] = authored

    authored_relation_ids: set[str] = set()
    change_set_relations = {
        item.relation_id: item
        for item in session.scalars(
            select(ChangeSetRelation).where(ChangeSetRelation.change_set_id == change_set.id)
        )
    }
    global_relation_ids = set(
        session.scalars(
            select(ObjectRelation.id)
            .join(ChangeSetRelation, ChangeSetRelation.relation_id == ObjectRelation.id)
            .where(ChangeSetRelation.change_set_id == change_set.id)
        )
    )
    for relation_id, row in change_set_relations.items():
        base = base_relations.get(relation_id)
        if row.is_deleted:
            if base is None:
                continue
            if row.origin:
                removal_origins[relation_id] = row.origin
            live = live_relations.get(relation_id)
            if live is not None and live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "relation", relation_id, expected=base.version, actual=live.version
                    )
                )
            merged_relations.pop(relation_id, None)
            continue
        authored_relation_ids.add(relation_id)
        authored = MergedRelation(
            relation_id=relation_id,
            relation_type_key=row.relation_type_key,
            from_object_id=row.from_object_id,
            to_object_id=row.to_object_id,
            attributes=dict(row.attributes or {}),
            version=row.version,
            origin=row.origin,
        )
        if base is not None:
            live = live_relations.get(relation_id)
            if live is None or live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "relation",
                        relation_id,
                        expected=base.version,
                        actual=live.version if live is not None else None,
                    )
                )
            merged_relations[relation_id] = authored
        else:
            if relation_id in global_relation_ids:
                conflicts.append(
                    {
                        "kind": "relation",
                        "id": relation_id,
                        "code": "ID_COLLISION",
                        "message": "The id of a relation created in the change set already exists in live data",
                    }
                )
            merged_relations[relation_id] = authored

    # A tombstoned object drops its incident live relations even when the change set never saw them; a
    # live relation cannot outlive an endpoint.  Any other dangling endpoint would fail whole-graph
    # validation below and abort the publish before any row is touched.
    for relation_id in [
        relation_id
        for relation_id, relation in merged_relations.items()
        if relation.from_object_id not in merged_objects
        or relation.to_object_id not in merged_objects
    ]:
        merged_relations.pop(relation_id, None)

    # The live table enforces one directed edge per (type, from, to).  A change set edge duplicating a
    # live one (distinct ids) would violate that constraint mid-apply; surface it as a conflict
    # instead of leaking an IntegrityError out of the publish transaction.
    seen_edges: dict[tuple[str, str, str], str] = {}
    for relation_id in sorted(merged_relations):
        relation = merged_relations[relation_id]
        edge = (relation.relation_type_key, relation.from_object_id, relation.to_object_id)
        prior = seen_edges.get(edge)
        if prior is not None:
            conflicts.append(
                {
                    "kind": "relation",
                    "id": relation_id,
                    "conflictingRelationId": prior,
                    "code": "DUPLICATE_EDGE",
                    "message": "Change set and live both define the same directed relation",
                }
            )
        else:
            seen_edges[edge] = relation_id

    if collect is not None:
        collect.extend(conflicts)
    elif conflicts:
        listed, left_out = cap_per_code(conflicts)
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "Change set conflicts with the live active data",
            {
                "conflicts": listed,
                # How many of each code the list leaves out, present only when some are.
                **({"conflictsLeftOut": left_out} if left_out else {}),
                "mappingSetConflictCount": len(mapping_conflicts),
                "mappingSetConflictsTruncated": len(mapping_conflicts) > 20,
            },
        )
    membership = EffectiveChangeSetMembership(
        change_set=change_set,
        objects=tuple(sorted(merged_objects.values(), key=lambda item: item.object_id)),
        relations=tuple(sorted(merged_relations.values(), key=lambda item: item.relation_id)),
    )
    return LiveMerge(
        membership=membership,
        authored_object_ids=authored_object_ids,
        authored_relation_ids=authored_relation_ids,
        removed_object_ids=set(live_objects) - set(merged_objects),
        removed_relation_ids=set(live_relations) - set(merged_relations),
        removal_origins=removal_origins,
        live_objects=live_state,
        live_relations=live_relation_state,
    )


def publish_change_set(
    session: Session,
    change_set_id: str,
    model: Any,
    active_release_id: int,
    expected_change_set_version: int,
    expected_active_publication_id: str | None,
) -> Publication:
    publication = apply_publication(
        session,
        change_set_id,
        model,
        active_release_id,
        expected_change_set_version,
        expected_active_publication_id,
    )
    session.commit()
    return publication


def publication_findings(
    session: Session, change_set: ChangeSet, model: Any
) -> list[dict[str, Any]]:
    """What would stop the change set's publication over the current live data under ``model``,
    without changing anything: each merge conflict (``kind``, ``id``, ``code``, ``message``) and
    each whole-graph diagnostic (``code``, ``message``, ``details``). A migration's preview lists
    them as refused items (0.11 V2, D82)."""
    conflicts: list[dict[str, Any]] = []
    merged = _merge_change_set_over_live(
        session,
        change_set,
        *_publication_snapshot_maps(session, change_set),
        model,
        collect=conflicts,
    )
    return conflicts + graph_diagnostics(merged.membership, model)


def lock_workspace_for_publication(session: Session, change_set_id: str) -> Workspace:
    """Lock the change set's workspace row ``NO KEY UPDATE`` and answer it. Every path that
    publishes takes it before it locks the change set (ARCHITECTURE, lock order): the workspace
    row first, so live writes wait for the publication transaction (PG-D5), then the change set,
    claimed before the merge population is read. ``NO KEY UPDATE`` leaves other change sets'
    writes, which hold the workspace's key share lock, free to run beside the publication. Taking
    it again in the same transaction is harmless."""
    workspace_key = session.scalar(
        select(ChangeSet.workspace_key).where(ChangeSet.id == change_set_id)
    )
    if workspace_key is None:
        load_change_set(session, change_set_id)  # 404 change_set_not_found
    workspace = session.scalar(
        select(Workspace)
        .where(Workspace.key == workspace_key)
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    )
    if workspace is None:
        raise api_error(404, "WORKSPACE_NOT_FOUND", "Workspace not found")
    return workspace


def apply_publication(
    session: Session,
    change_set_id: str,
    model: Any,
    active_release_id: int,
    expected_change_set_version: int,
    expected_active_publication_id: str | None,
) -> Publication:
    """Publish the change set in the caller's transaction, which commits it: a publication, and a
    migration that publishes the change set after switching its workspace's release (0.11 V2)."""
    workspace = lock_workspace_for_publication(session, change_set_id)
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    if change_set.model_release_id != active_release_id:
        raise api_error(
            409,
            "CHANGE_SET_MODEL_RELEASE_CONFLICT",
            f"Change set is pinned to a release workspace '{change_set.workspace_key}' no longer "
            "runs",
            {"workspaceKey": change_set.workspace_key},
        )
    if change_set.waits_for_change_set_id is not None:
        _require_copy_published(session, change_set)
    writes.claim(expected_change_set_version, publishing=True)
    live = LiveWrites(session, change_set.workspace_key)
    live.permit_publication(change_set.id)
    if workspace.active_publication_id != expected_active_publication_id:
        raise api_error(
            409, "WORKSPACE_ACTIVE_PUBLICATION_CONFLICT", "Active publication has changed"
        )
    # The change set is applied as a delta onto the *current* live projection, then the merged graph is
    # validated whole before anything is written; live content newer than the change set base is preserved.
    merged = _merge_change_set_over_live(
        session,
        change_set,
        *_publication_snapshot_maps(session, change_set),
        model,
    )
    diagnostics = graph_diagnostics(merged.membership, model)
    if diagnostics:
        listed, left_out = cap_per_code(diagnostics)
        # ``details`` stays a list: each code left out gets one closing entry that counts them.
        listed += [
            {
                "code": "DIAGNOSTICS_LEFT_OUT",
                "message": f"{count} more {code} diagnostics are not listed",
                "details": {"leftOutCode": code, "count": count},
            }
            for code, count in left_out.items()
        ]
        raise api_error(
            422,
            "WORKSPACE_GRAPH_INVALID",
            "Change set failed complete graph validation over the live active data",
            listed,
        )
    number = (
        session.scalar(
            select(Publication.publication_number)
            .where(Publication.workspace_key == change_set.workspace_key)
            .order_by(Publication.publication_number.desc())
            .limit(1)
        )
        or 0
    ) + 1
    publication = Publication(
        workspace_key=change_set.workspace_key,
        model_release_id=change_set.model_release_id,
        publication_number=number,
        status="active",
        derived_from_publication_id=change_set.derived_from_publication_id,
        supersedes_publication_id=workspace.active_publication_id,
        **columns(requester_of(session), "published_by"),
    )
    session.add(publication)
    session.flush()
    # Apply only the delta onto the live projection: remove tombstoned rows, upsert the authored
    # objects and relations, and leave every untouched live row exactly as it is. What it changed
    # takes the next feed positions with the publication as cause, then the publication's own
    # entry (D15, D32), whose position is the publication's: live data at that position is the
    # publication (C-D15).
    live.apply_publication(model, merged)
    session.flush()
    copy_live(session, "publication", publication.id, change_set.workspace_key)
    with audit_cause(session, "publication", publication.id):
        live.record_all(publish_entries(merged, model))
    publication.feed_position = record_change_set_published(
        session,
        publication=publication,
        change_set=change_set,
        object_count=len(merged.membership.objects),
        relation_count=len(merged.membership.relations),
    ).feed_position
    if workspace.active_publication_id:
        old = session.scalar(
            select(Publication).where(Publication.id == workspace.active_publication_id)
        )
        old.status = "withdrawn"
        old.withdrawn_at = datetime.now(UTC)
        # Superseded by this publication: its publisher withdrew the old one (0.12 Z4).
        for column, value in columns(requester_of(session), "withdrawn_by").items():
            setattr(old, column, value)
    publication.published_at = datetime.now(UTC)
    workspace.active_publication_id = publication.id
    merge_change_set_relation_set_versions_to_live(session, change_set.id, change_set.workspace_key)
    # Those who follow the workspace are told, in this transaction, before the change set is gone.
    announce_publication(session, publication, change_set)
    delete_change_set_and_base(session, change_set)
    matrix_states.record_publication(session, publication)
    session.flush()
    return publication


def _require_copy_published(session: Session, change_set: ChangeSet) -> None:
    """A move's deletion in its source publishes only after the copy it waits for (0.11 X3,
    D135): the copy's change set gone, and a publication's entry naming it. Still open, or
    discarded, it is ``409 MOVE_COPY_NOT_PUBLISHED``."""
    waited = change_set.waits_for_change_set_id
    copy = session.execute(
        select(ChangeSet.id, ChangeSet.name, Workspace.label)
        .join(Workspace, Workspace.key == ChangeSet.workspace_key)
        .where(ChangeSet.id == waited)
    ).first()
    still_open = copy.id if copy is not None else None
    source = AuditEvent.changes["changeSetId"].as_string()
    published = still_open is None and session.scalar(
        select(AuditEvent.aggregate_id).where(
            AuditEvent.aggregate_type == "publication",
            AuditEvent.action == "published",
            source == waited,
        )
    )
    if published:
        return
    state = "open" if still_open is not None else "discarded"
    raise api_error(
        409,
        "MOVE_COPY_NOT_PUBLISHED",
        # Named as a person reads it (0.11 X5): the copy's change set and its workspace, not its ID.
        f"This change set deletes records a move copied into the change set “{copy.name}” of "
        f"workspace {copy.label}, which is not published yet; publish it first"
        if copy is not None
        else "This change set deletes records a move copied into a change set that was discarded; "
        "this deletion can only be discarded",
        {"changeSetId": waited, "state": state},
    )


def withdraw_publication(session: Session, publication_id: str) -> None:
    """Remove the current-publication designation; live data and history are unchanged."""
    publication = session.scalar(select(Publication).where(Publication.id == publication_id))
    if publication is None:
        raise api_error(404, "PUBLICATION_NOT_FOUND", "Publication not found")
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == publication.workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "WORKSPACE_NOT_FOUND", "Workspace not found")
    if workspace.status == "retired":
        raise api_error(409, "WORKSPACE_RETIRED", "Workspace is retired and cannot be mutated")
    # The path names the publication to withdraw, so it is also the concurrency claim: a publication
    # that is no longer current (withdrawn or superseded meanwhile) is refused.
    if workspace.active_publication_id != publication_id:
        raise api_error(
            409, "WORKSPACE_ACTIVE_PUBLICATION_CONFLICT", "Active publication has changed"
        )
    publication.status = "withdrawn"
    publication.withdrawn_at = datetime.now(UTC)
    for column, value in columns(requester_of(session), "withdrawn_by").items():
        setattr(publication, column, value)
    workspace.active_publication_id = None
    # Record the withdrawal in the same transaction as the pointer clear so a rolled-back
    # withdrawal never leaves an orphan event (D3a).  The event is aggregated on the workspace key
    # and carries no AuditEventSubject rows.
    record_publication_withdrawn(session, publication=publication)
    session.commit()
