"""Publishing a change set onto live data, and withdrawing a publication (ADR-026/027/031)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
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
from ..indexes import matrix_states
from ..records.attributes import load_attribute_values
from ..records.relation_set_versions import merge_change_set_relation_set_versions_to_live
from ..records.writes import ChangeSetWrites, LiveWrites
from ..workspaces.workspace_audit import record_change_set_published, record_publication_withdrawn
from .access import EffectiveChangeSetMembership, load_change_set
from .lifecycle import delete_change_set_and_base
from .validation import graph_diagnostics, is_parent_pair


@dataclass(frozen=True)
class _MergedObject:
    object_id: str
    application_key: str
    object_type_key: str
    name: str
    parent_object_id: str | None
    attributes: dict[str, Any]
    version: int


@dataclass(frozen=True)
class _MergedRelation:
    relation_id: str
    relation_type_key: str
    from_object_id: str
    to_object_id: str
    attributes: dict[str, Any]
    version: int


@dataclass
class _LiveMerge:
    membership: EffectiveChangeSetMembership
    authored_object_ids: set[str]
    authored_relation_ids: set[str]
    removed_object_ids: set[str]
    removed_relation_ids: set[str]


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
                "change_set_base_invalid",
                "Change set current-live base is missing or belongs to another workspace",
            )
        return (
            {
                item.object_id: item
                for item in session.scalars(
                    select(ChangeSetBaseObject).where(
                        ChangeSetBaseObject.base_id == base.id
                    )
                )
            },
            {
                item.relation_id: item
                for item in session.scalars(
                    select(ChangeSetBaseRelation).where(
                        ChangeSetBaseRelation.base_id == base.id
                    )
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
        "code": "version_mismatch",
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
            "code": "mapping_set_changed",
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
) -> _LiveMerge:
    """Compute the live content that would result from applying the change set's delta.

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
    attribute_rows = load_attribute_values(session, object_ids)
    merged_objects: dict[str, _MergedObject] = {}
    for object_id in object_ids:
        live = live_objects[object_id]
        merged_objects[object_id] = _MergedObject(
            object_id=object_id,
            application_key=live.application_key,
            object_type_key=live.object_type_key,
            name=live.name,
            parent_object_id=live.parent_object_id,
            attributes={key: value for key, (_row_id, value) in attribute_rows[object_id].items()},
            version=live.version,
        )
    live_relations: dict[str, ObjectRelation] = {}
    if object_ids:
        live_relations = {
            item.id: item
            for item in session.scalars(
                select(ObjectRelation).where(
                    or_(
                        ObjectRelation.from_object_id.in_(object_ids),
                        ObjectRelation.to_object_id.in_(object_ids),
                    )
                )
            )
        }
    merged_relations: dict[str, _MergedRelation] = {
        relation_id: _MergedRelation(
            relation_id=relation_id,
            relation_type_key=relation.relation_type_key,
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
            attributes=dict(relation.attributes or {}),
            version=relation.version,
        )
        for relation_id, relation in live_relations.items()
    }

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
    global_object_ids = set(
        session.scalars(select(RdmObject.id).where(RdmObject.id.in_(change_set_objects)))
    )
    for object_id, row in change_set_objects.items():
        base = base_objects.get(object_id)
        if row.is_deleted:
            if base is None:
                continue  # created then deleted inside the change set: never reached live
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
        authored = _MergedObject(
            object_id=object_id,
            application_key=row.application_key,
            object_type_key=row.object_type_key,
            name=row.name,
            parent_object_id=row.parent_object_id,
            attributes=dict(row.attributes or {}),
            version=row.version,
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
                        "code": "id_collision",
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
        session.scalars(select(ObjectRelation.id).where(ObjectRelation.id.in_(change_set_relations)))
    )
    for relation_id, row in change_set_relations.items():
        base = base_relations.get(relation_id)
        if row.is_deleted:
            if base is None:
                continue
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
        authored = _MergedRelation(
            relation_id=relation_id,
            relation_type_key=row.relation_type_key,
            from_object_id=row.from_object_id,
            to_object_id=row.to_object_id,
            attributes=dict(row.attributes or {}),
            version=row.version,
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
                        "code": "id_collision",
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
                    "code": "duplicate_edge",
                    "message": "Change set and live both define the same directed relation",
                }
            )
        else:
            seen_edges[edge] = relation_id

    if conflicts:
        raise api_error(
            409,
            "version_conflict",
            "Change set conflicts with the live active data",
            {
                "conflicts": conflicts,
                "mappingSetConflictCount": len(mapping_conflicts),
                "mappingSetConflictsTruncated": len(mapping_conflicts) > 20,
            },
        )
    membership = EffectiveChangeSetMembership(
        change_set=change_set,
        objects=tuple(sorted(merged_objects.values(), key=lambda item: item.object_id)),
        relations=tuple(sorted(merged_relations.values(), key=lambda item: item.relation_id)),
    )
    return _LiveMerge(
        membership=membership,
        authored_object_ids=authored_object_ids,
        authored_relation_ids=authored_relation_ids,
        removed_object_ids=set(live_objects) - set(merged_objects),
        removed_relation_ids=set(live_relations) - set(merged_relations),
    )


def publish_change_set(
    session: Session,
    change_set_id: str,
    model: Any,
    active_release_id: int,
    expected_change_set_version: int,
    expected_active_publication_id: str | None,
) -> Publication:
    # Lock order (ARCHITECTURE): the workspace row first, so live writes wait for the
    # publication transaction (PG-D5), then the change set, claimed before the merge population
    # is read.
    workspace_key = session.scalar(
        select(ChangeSet.workspace_key).where(ChangeSet.id == change_set_id)
    )
    if workspace_key is None:
        load_change_set(session, change_set_id)  # 404 change_set_not_found
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    if change_set.model_release_id != active_release_id:
        raise api_error(
            409,
            "change_set_model_release_conflict",
            "Change set is pinned to a different application-model release",
        )
    writes.claim(expected_change_set_version)
    live = LiveWrites(session, change_set.workspace_key)
    if workspace.active_publication_id != expected_active_publication_id:
        raise api_error(
            409, "workspace_active_publication_conflict", "Active publication has changed"
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
        raise api_error(
            422,
            "workspace_graph_invalid",
            "Change set failed complete graph validation over the live active data",
            diagnostics,
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
    )
    session.add(publication)
    session.flush()
    for item in merged.membership.objects:
        session.add(
            PublicationObject(
                publication_id=publication.id,
                object_id=item.object_id,
                application_key=item.application_key,
                object_type_key=item.object_type_key,
                name=item.name,
                parent_object_id=item.parent_object_id,
                attributes=item.attributes,
                version=item.version,
            )
        )
    for item in merged.membership.relations:
        session.add(
            PublicationRelation(
                publication_id=publication.id,
                relation_id=item.relation_id,
                relation_type_key=item.relation_type_key,
                from_object_id=item.from_object_id,
                to_object_id=item.to_object_id,
                attributes=item.attributes,
                version=item.version,
            )
        )
    record_change_set_published(
        session,
        publication=publication,
        change_set=change_set,
        object_count=len(merged.membership.objects),
        relation_count=len(merged.membership.relations),
    )
    # Apply only the delta onto the live projection: remove tombstoned rows, upsert the authored
    # objects and relations, and leave every untouched live row exactly as it is.
    live.apply_publication(model, merged)
    if workspace.active_publication_id:
        old = session.scalar(
            select(Publication).where(Publication.id == workspace.active_publication_id)
        )
        old.status = "withdrawn"
        old.withdrawn_at = datetime.now(UTC)
    publication.published_at = datetime.now(UTC)
    workspace.active_publication_id = publication.id
    merge_change_set_relation_set_versions_to_live(session, change_set.id, change_set.workspace_key)
    delete_change_set_and_base(session, change_set)
    matrix_states.record_publication(session, publication)
    session.commit()
    return publication


def withdraw_publication(session: Session, publication_id: str) -> None:
    """Remove the current-publication designation; live data and history are unchanged."""
    publication = session.scalar(select(Publication).where(Publication.id == publication_id))
    if publication is None:
        raise api_error(404, "publication_not_found", "Publication not found")
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == publication.workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if workspace.status == "retired":
        raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")
    # The path names the publication to withdraw, so it is also the concurrency claim: a publication
    # that is no longer current (withdrawn or superseded meanwhile) is refused.
    if workspace.active_publication_id != publication_id:
        raise api_error(
            409, "workspace_active_publication_conflict", "Active publication has changed"
        )
    publication.status = "withdrawn"
    publication.withdrawn_at = datetime.now(UTC)
    workspace.active_publication_id = None
    # Record the withdrawal in the same transaction as the pointer clear so a rolled-back
    # withdrawal never leaves an orphan event (D3a).  The event is aggregated on the workspace key
    # and carries no AuditEventSubject rows.
    record_publication_withdrawn(session, publication=publication)
    session.commit()
