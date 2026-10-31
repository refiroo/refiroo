"""What a draft has released, and what changing a released element would touch (D17, D33).

A draft is compared with its **base release**; without one, with the newest installed release of
its own model (its ``release.key``); with neither it is a new model and nothing of it is released
(0.11 D37). An element is released when that release declares it (D17). A draft-only operation on
a released element applies while its impact is nothing (AP-D28); otherwise it is refused with that
impact: the records, values and relationships that hold it, in live data and in the rows of every
change set (all change sets are open until published) of the workspaces running the draft's model,
each counted exactly up to :data:`IMPACT_LIMIT` (D33). A released key stays fixed whatever the
impact. Counts are set statements in PostgreSQL.
"""

from typing import Any

from sqlalchemy import Select, and_, cast, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, aliased

from ....errors import ApiError
from ....models.database import (
    AttributeValue,
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    ModelDraft,
    ModelRelease,
    ObjectRelation,
    RdmObject,
    WorkspaceModel,
)
from ....models.schema import EngineModel
from ..registry import model_registry
from .kinds import atom

IMPACT_LIMIT = 10_000


def base_release(session: Session, draft: ModelDraft) -> ModelRelease | None:
    """The release the draft is compared with: its base, or the newest installed release of its
    own model; none for a new model (D37)."""
    if draft.base_model_release_id is not None:
        release = session.get(ModelRelease, draft.base_model_release_id)
        if release is not None:
            return release
    return newest_of(session, draft_model_key(draft))


def base_model(session: Session, draft: ModelDraft) -> EngineModel | None:
    """The model of the release the draft is compared with, whose consumer contracts it is checked
    against (D37); none for a new model, or when that release cannot be read."""
    release = base_release(session, draft)
    if release is None:
        return None
    try:
        return model_registry.resolve_release(session, release.id, require_ready=False).model
    except ApiError:
        return None


def draft_model_key(draft: ModelDraft) -> str | None:
    """The model a draft is written for: its ``release.key``."""
    release = (draft.model_json or {}).get("release")
    return release.get("key") if isinstance(release, dict) else None


def newest_of(session: Session, model_key: str | None) -> ModelRelease | None:
    """The newest installed release of ``model_key``."""
    if not model_key:
        return None
    return session.scalar(
        select(ModelRelease)
        .where(ModelRelease.release_key == model_key)
        .order_by(ModelRelease.installed_at.desc(), ModelRelease.id.desc())
        .limit(1)
    )


def workspaces_of_model(model_key: str | None) -> Select[Any]:
    """The keys of the workspaces running a release of ``model_key``."""
    return (
        select(WorkspaceModel.workspace_key)
        .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
        .where(ModelRelease.release_key == model_key)
    )


def released_atoms(model: dict[str, Any] | None) -> frozenset[str]:
    """The elements a release declares that a draft-only operation may not change (D17)."""
    if not model:
        return frozenset()
    found = set()
    for item in model.get("applications") or []:
        found.add(atom("application", item["key"]))
    for item in model.get("attributeTypes") or []:
        found.add(atom("attributeType", item["key"]))
    for item in model.get("relationTypes") or []:
        found.add(atom("relationType", item["key"]))
    for item in model.get("objectTypes") or []:
        found.add(atom("objectType", item["key"]))
        for binding in item.get("attributes") or []:
            found.add(atom("attributeBinding", item["key"], binding["attributeTypeKey"]))
    for item in model.get("objectTypeRelations") or []:
        found.add(
            atom("relationBinding", item["relationTypeKey"], item["fromObjectTypeKey"], item["toObjectTypeKey"])
        )
    return frozenset(found)


def impact(session: Session, element: str, model_key: str | None) -> dict[str, int | str]:
    """The records, values and relationships holding ``element``, live and in change sets, in the
    workspaces running ``model_key``."""
    scope = workspaces_of_model(model_key)
    in_scope = RdmObject.workspace_key.in_(scope)
    change_sets = select(ChangeSet.id).where(ChangeSet.workspace_key.in_(scope))
    staged_objects = _staged_objects().where(ChangeSetObject.change_set_id.in_(change_sets))
    staged_values = _staged_values().where(ChangeSetObject.change_set_id.in_(change_sets))
    staged_relations = _staged_relations().where(ChangeSetRelation.change_set_id.in_(change_sets))
    kind, _, rest = element.partition(":")
    keys = rest.split("/")
    if kind in ("objectType", "application"):
        live = RdmObject.object_type_key == keys[0] if kind == "objectType" else RdmObject.application_key == keys[0]
        live = and_(live, in_scope)
        staged = (
            ChangeSetObject.object_type_key == keys[0]
            if kind == "objectType"
            else ChangeSetObject.application_key == keys[0]
        )
        return {
            "records": _sum(session, select(RdmObject.id).where(live), staged_objects.where(staged)),
            "values": _sum(
                session,
                select(AttributeValue.id).join(RdmObject, RdmObject.id == AttributeValue.object_id).where(live),
                staged_values.where(staged),
            ),
            "relationships": _sum(session, *_relationships(live, staged, staged_relations)),
        }
    if kind in ("attributeType", "attributeBinding"):
        attribute = keys[-1]
        live_values = (
            select(AttributeValue.id)
            .join(RdmObject, RdmObject.id == AttributeValue.object_id)
            .where(AttributeValue.attribute_type_key == attribute, in_scope)
        )
        staged_values = staged_objects.where(cast(ChangeSetObject.attributes, JSONB).has_key(attribute))
        if kind == "attributeBinding":
            live_values = live_values.where(RdmObject.object_type_key == keys[0])
            staged_values = staged_values.where(ChangeSetObject.object_type_key == keys[0])
        values = _sum(session, live_values, staged_values)
        return {"records": values, "values": values, "relationships": 0}
    if kind in ("relationType", "relationBinding"):
        live = select(ObjectRelation.id).where(
            ObjectRelation.relation_type_key == keys[0],
            ObjectRelation.from_object_id.in_(select(RdmObject.id).where(in_scope)),
        )
        staged = staged_relations.where(ChangeSetRelation.relation_type_key == keys[0])
        if kind == "relationBinding":
            live, staged = _binding_ends(live, staged, keys[1], keys[2])
        return {"records": 0, "values": 0, "relationships": _sum(session, live, staged)}
    return {"records": 0, "values": 0, "relationships": 0}


def _staged_objects() -> Select[Any]:
    return select(ChangeSetObject.sequence_id).where(ChangeSetObject.is_deleted.is_(False))


def _staged_values() -> Select[Any]:
    keys = func.jsonb_object_keys(cast(ChangeSetObject.attributes, JSONB)).table_valued("key")
    return (
        select(literal(1))
        .select_from(ChangeSetObject)
        .join(keys, true())
        .where(ChangeSetObject.is_deleted.is_(False))
    )


def _staged_relations() -> Select[Any]:
    return select(ChangeSetRelation.sequence_id).where(ChangeSetRelation.is_deleted.is_(False))


def _relationships(live: Any, staged: Any, staged_relations: Select[Any]) -> tuple[Select[Any], Select[Any]]:
    """Relationships with an end in the selected records, live and staged in change sets."""
    holder = select(RdmObject.id).where(live)
    staged_holder = select(ChangeSetObject.object_id).where(staged)
    return (
        select(ObjectRelation.id).where(
            or_(ObjectRelation.from_object_id.in_(holder), ObjectRelation.to_object_id.in_(holder))
        ),
        staged_relations.where(
            or_(
                ChangeSetRelation.from_object_id.in_(holder.union(staged_holder)),
                ChangeSetRelation.to_object_id.in_(holder.union(staged_holder)),
            )
        ),
    )


def _binding_ends(live: Select[Any], staged: Select[Any], source: str, target: str) -> tuple[Select[Any], Select[Any]]:
    from_object, to_object = aliased(RdmObject), aliased(RdmObject)
    live = (
        live.join(from_object, from_object.id == ObjectRelation.from_object_id)
        .join(to_object, to_object.id == ObjectRelation.to_object_id)
        .where(from_object.object_type_key == source, to_object.object_type_key == target)
    )

    def typed(column: Any, type_key: str) -> Any:
        return or_(
            column.in_(select(RdmObject.id).where(RdmObject.object_type_key == type_key)),
            column.in_(
                select(ChangeSetObject.object_id).where(
                    and_(
                        ChangeSetObject.object_type_key == type_key,
                        ChangeSetObject.change_set_id == ChangeSetRelation.change_set_id,
                    )
                )
            ),
        )

    staged = staged.where(
        typed(ChangeSetRelation.from_object_id, source), typed(ChangeSetRelation.to_object_id, target)
    )
    return live, staged


def _sum(session: Session, *statements: Select[Any]) -> int | str:
    total = 0
    for statement in statements:
        total += int(
            session.scalar(select(func.count()).select_from(statement.limit(IMPACT_LIMIT + 1).subquery())) or 0
        )
        if total > IMPACT_LIMIT:
            return f"{IMPACT_LIMIT}+"
    return total
