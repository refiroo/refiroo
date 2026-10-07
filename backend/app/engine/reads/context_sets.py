"""A context's records and relationships as set sources for whole-set statements (Base 0.9 J1, J2).

Live data, a change set or a publication read alike: each record with its values as one JSON object
(``rdm_value_json``, the canonical form a snapshot row holds), and each relationship with its ends.
An export selects its scope from them; an import matches cells against them.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import JSON, cast, func, literal, select

from ...models.database import AttributeValue, ObjectRelation, RdmObject
from .snapshot_reads import SnapshotContext, object_projection, relation_projection


def record_source(
    workspace_key: str, context: SnapshotContext | None, types: Sequence[str] | None
) -> Any:
    """The context's records with their values, narrowed to ``types`` when given. ``context`` is
    ``None`` for live data of ``workspace_key``."""
    if context is not None:
        projection = object_projection(context, object_type_keys=types)
        return select(
            projection.c.object_id,
            projection.c.application_key,
            projection.c.object_type_key,
            projection.c.name,
            projection.c.parent_object_id,
            projection.c.attributes,
            projection.c.version,
        ).subquery()
    values = AttributeValue
    attributes = (
        select(
            func.json_object_agg(
                values.attribute_type_key,
                func.rdm_value_json(
                    values.value_type,
                    values.text_value,
                    values.integer_value,
                    values.decimal_value,
                    values.boolean_value,
                    values.date_value,
                    values.datetime_value,
                    values.json_value,
                ),
            )
        )
        .where(values.object_id == RdmObject.id)
        .scalar_subquery()
    )
    statement = select(
        RdmObject.id.label("object_id"),
        RdmObject.application_key,
        RdmObject.object_type_key,
        RdmObject.name,
        RdmObject.parent_object_id,
        func.coalesce(attributes, cast(literal("{}"), JSON)).label("attributes"),
        RdmObject.version,
    ).where(RdmObject.workspace_key == workspace_key)
    if types is not None:
        statement = statement.where(RdmObject.object_type_key.in_(types))
    return statement.subquery()


def relation_source(context: SnapshotContext | None) -> Any:
    """The context's relationships. Live relationships are not narrowed to a workspace: a caller
    joins them to records of its workspace."""
    if context is not None:
        projection = relation_projection(context)
        return select(
            projection.c.relation_id,
            projection.c.relation_type_key,
            projection.c.from_object_id,
            projection.c.to_object_id,
            projection.c.attributes,
            projection.c.version,
        ).subquery()
    return select(
        ObjectRelation.id.label("relation_id"),
        ObjectRelation.relation_type_key,
        ObjectRelation.from_object_id,
        ObjectRelation.to_object_id,
        ObjectRelation.attributes,
        ObjectRelation.version,
    ).subquery()
