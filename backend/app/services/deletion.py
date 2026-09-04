from __future__ import annotations

from dataclasses import dataclass

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ..models.database import AttributeValue, AuditEvent, ObjectRelation, RdmObject
from ..models.schema import EngineModel, ObjectTypeRelationDefinition


@dataclass
class DeletePlan:
    root_id: str
    objects: dict[str, RdmObject]
    object_reasons: dict[str, dict]
    relations: dict[str, ObjectRelation]
    non_parent_relation_ids: set[str]

    @property
    def has_dependents(self) -> bool:
        return len(self.objects) > 1 or bool(self.non_parent_relation_ids)


def build_delete_plan(
    session: Session, model: EngineModel, root: RdmObject, *, cascade: bool
) -> DeletePlan:
    objects = {root.id: root}
    reasons: dict[str, dict] = {}
    relations: dict[str, ObjectRelation] = {}
    non_parent_relation_ids: set[str] = set()
    pending = [root]

    while pending:
        current = pending.pop()
        children = list(
            session.scalars(select(RdmObject).where(RdmObject.parent_object_id == current.id))
        )
        for child in children:
            if child.id not in objects:
                objects[child.id] = child
                reasons[child.id] = {"reason": "child", "viaObjectId": current.id}
                pending.append(child)

        incident = list(
            session.scalars(
                select(ObjectRelation).where(
                    or_(
                        ObjectRelation.from_object_id == current.id,
                        ObjectRelation.to_object_id == current.id,
                    )
                )
            )
        )
        for relation in incident:
            relations[relation.id] = relation
            from_object = _load_object(session, objects, relation.from_object_id)
            to_object = _load_object(session, objects, relation.to_object_id)
            if _is_parent_relation(model, relation, from_object, to_object):
                continue
            non_parent_relation_ids.add(relation.id)
            allowed = _allowed_relation(model, relation, from_object, to_object)
            if (
                cascade
                and current.id == relation.from_object_id
                and allowed is not None
                and _is_fk_pk_relation(model, allowed)
                and to_object.id not in objects
            ):
                objects[to_object.id] = to_object
                reasons[to_object.id] = {
                    "reason": "fkDependent",
                    "viaObjectId": current.id,
                    "relationTypeKey": relation.relation_type_key,
                }
                pending.append(to_object)

    # Include every edge that the database will remove, including edges between two planned objects
    # that were not encountered before the related object entered the traversal.
    planned_ids = set(objects)
    if planned_ids:
        for relation in session.scalars(
            select(ObjectRelation).where(
                or_(
                    ObjectRelation.from_object_id.in_(planned_ids),
                    ObjectRelation.to_object_id.in_(planned_ids),
                )
            )
        ):
            relations[relation.id] = relation
            from_object = _load_object(session, objects, relation.from_object_id)
            to_object = _load_object(session, objects, relation.to_object_id)
            if not _is_parent_relation(model, relation, from_object, to_object):
                non_parent_relation_ids.add(relation.id)

    return DeletePlan(root.id, objects, reasons, relations, non_parent_relation_ids)


def delete_plan_details(session: Session, model: EngineModel, plan: DeletePlan) -> dict:
    object_summaries = {
        object_id: _object_summary(item) for object_id, item in plan.objects.items()
    }
    dependencies = [
        {**object_summaries[object_id], **reason}
        for object_id, reason in plan.object_reasons.items()
    ]
    relationships = []
    for relation_id in sorted(plan.non_parent_relation_ids):
        relation = plan.relations[relation_id]
        from_object = _load_object(session, plan.objects, relation.from_object_id)
        to_object = _load_object(session, plan.objects, relation.to_object_id)
        allowed = _allowed_relation(model, relation, from_object, to_object)
        relationships.append(
            {
                "id": relation.id,
                "relationTypeKey": relation.relation_type_key,
                "fromObject": _object_summary(from_object),
                "toObject": _object_summary(to_object),
                "fkPk": allowed is not None and _is_fk_pk_relation(model, allowed),
                "relatedObjectWillBeDeleted": (
                    relation.from_object_id in plan.objects
                    and relation.to_object_id in plan.objects
                ),
            }
        )
    return {
        "rootObject": object_summaries[plan.root_id],
        "objectsToDelete": dependencies,
        "relationshipsToRemove": relationships,
        "objectCount": len(plan.objects),
        "relationshipCount": len(plan.relations),
    }


def execute_delete_plan(session: Session, plan: DeletePlan) -> None:
    object_ids = set(plan.objects)
    relation_ids = set(plan.relations)

    for relation in plan.relations.values():
        session.add(
            AuditEvent(
                aggregate_type="relation",
                aggregate_id=relation.id,
                action="deleted",
                version=relation.version,
                changes=jsonable_encoder(
                    {
                        "relationTypeKey": relation.relation_type_key,
                        "fromObjectId": relation.from_object_id,
                        "toObjectId": relation.to_object_id,
                        "cascadeRootObjectId": plan.root_id,
                    }
                ),
            )
        )
    for item in plan.objects.values():
        session.add(
            AuditEvent(
                aggregate_type="object",
                aggregate_id=item.id,
                action="deleted",
                version=item.version,
                changes=jsonable_encoder(
                    {
                        "objectTypeKey": item.object_type_key,
                        "cascadeRootObjectId": plan.root_id,
                    }
                ),
            )
        )

    if relation_ids:
        session.execute(delete(ObjectRelation).where(ObjectRelation.id.in_(relation_ids)))
    session.execute(delete(AttributeValue).where(AttributeValue.object_id.in_(object_ids)))
    for item in sorted(
        plan.objects.values(), key=lambda value: _depth(value, plan.objects), reverse=True
    ):
        session.delete(item)


def _load_object(session: Session, loaded: dict[str, RdmObject], object_id: str) -> RdmObject:
    item = loaded.get(object_id)
    if item is None:
        item = session.scalar(select(RdmObject).where(RdmObject.id == object_id))
    if item is None:  # A relation FK should make this impossible.
        raise RuntimeError(f"Relation references missing object '{object_id}'")
    return item


def _allowed_relation(
    model: EngineModel,
    relation: ObjectRelation,
    from_object: RdmObject,
    to_object: RdmObject,
) -> ObjectTypeRelationDefinition | None:
    return next(
        (
            allowed
            for allowed in model.objectTypeRelations
            if allowed.relationTypeKey == relation.relation_type_key
            and allowed.fromObjectTypeKey == from_object.object_type_key
            and allowed.toObjectTypeKey == to_object.object_type_key
        ),
        None,
    )


def _is_parent_relation(
    model: EngineModel,
    relation: ObjectRelation,
    from_object: RdmObject,
    to_object: RdmObject,
) -> bool:
    target_type = model.object_type(to_object.object_type_key)
    return bool(
        target_type
        and relation.relation_type_key in target_type.behavior.get("parentRelationTypeKeys", [])
        and to_object.parent_object_id == from_object.id
    )


def _is_fk_pk_relation(model: EngineModel, allowed: ObjectTypeRelationDefinition) -> bool:
    relation_type = model.relation_type(allowed.relationTypeKey)
    return bool(
        relation_type
        and relation_type.isOriented
        and allowed.required
        and allowed.cardinality in {"one-to-one", "one-to-many"}
    )


def _object_summary(item: RdmObject) -> dict[str, str | None]:
    return {
        "id": item.id,
        "name": item.name,
        "objectTypeKey": item.object_type_key,
        "applicationKey": item.application_key,
        "parentObjectId": item.parent_object_id,
    }


def _depth(item: RdmObject, objects: dict[str, RdmObject]) -> int:
    depth = 0
    parent_id = item.parent_object_id
    seen = {item.id}
    while parent_id in objects and parent_id not in seen:
        seen.add(parent_id)
        depth += 1
        parent_id = objects[parent_id].parent_object_id
    return depth
