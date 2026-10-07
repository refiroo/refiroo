"""Unique attribute values held by the database (ADR-010, 0.9 J2a, D75–D78).

``unique_attribute_values`` holds each live value of an attribute the active release declares
``unique`` once per workspace, under a deferred unique constraint; PostgreSQL triggers keep it
(revision ``20261007_07``) and no code writes it. The write rules refuse a duplicate before it is
written. A write that wrote one past them anyway (a defect) is refused at its end by
:func:`check`, with the rule's answer, inside the transaction where a batch can still redo its
items one by one; whatever no check covers, the constraint refuses at commit.
"""

from collections.abc import Iterable

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, aliased

from ...errors import ApiError
from ...models.database import UniqueAttributeValue
from ...models.schema import EngineModel
from ..records.refusals import duplicate_value

CONSTRAINT = "uq_unique_attribute_values"


class DuplicateValueWritten(ApiError):
    """The rule's ``409 DUPLICATE_ATTRIBUTE_VALUE`` for a value a write wrote past it, so a batch
    can tell it from a refusal decided before writing and redo its items one by one."""

    def __init__(self, error: ApiError) -> None:
        super().__init__(error.status, error.code, error.message, error.details, error.headers)


def check(session: Session, model: EngineModel, object_ids: Iterable[str]) -> None:
    """Refuse, as the unique rule does, a value of ``object_ids`` that another record holds.

    Values handed between records within the write pass: only the rows the write left count.
    """
    written = sorted(set(object_ids))
    if not written:
        return
    session.flush()
    mine, other = aliased(UniqueAttributeValue), aliased(UniqueAttributeValue)
    collision = session.execute(
        select(mine.attribute_type_key, mine.object_id, other.object_id)
        .join(
            other,
            and_(
                other.workspace_key == mine.workspace_key,
                other.attribute_type_key == mine.attribute_type_key,
                other.value_digest == mine.value_digest,
                other.value_id != mine.value_id,
            ),
        )
        .where(mine.object_id.in_(written))
        .order_by(mine.attribute_type_key, mine.object_id, other.object_id)
        .limit(1)
    ).first()
    if collision is not None:
        key, _object_id, holder = collision
        definition = model.attribute_type(key)
        name = (definition.name if definition else None) or key
        raise DuplicateValueWritten(duplicate_value(key, name, holder))
