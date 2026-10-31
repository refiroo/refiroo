"""Relationships made where a condition holds (Product 0.16 AP6, AP-D17, AP-D18).

A design may ask for relationships between the records two model-aware queries find ("relate
durations and stations, but only where a driver is assigned"): ``{relationTypeKey, from:
{objectTypeKey, where}, to: {objectTypeKey, where}}``, every record ``from`` finds related to every
record ``to`` finds. Each side is the query's own plan (``reads/model_query.py``, live records of the
workspace; one relation hop, ``not``, field and ancestor criteria, ANDed), checked against the
draft's model, so a query the engine cannot express is refused with the query's own reason. The
pairs are counted in PostgreSQL, and the load writes them as one background batch into the task's
change set, its inputs built by one ``INSERT … SELECT``: no record is read into Python. The
binding's cardinality decides the item: where a record may hold one record of the other end (the
``from`` side of many-to-one and one-to-one, the ``to`` side of one-to-many), the rule *gives* it
that record, a ``replaceRelationSet`` of that record's set, replacing what it held (counted as
``replaces``); a rule that would give such a record more than one is refused; otherwise each pair is
an ``ensureRelation``.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import String, func, insert, literal, select
from sqlalchemy.orm import Session, aliased

from ...errors import ApiError
from ...models.database import AttributeValue, Job, JobInput, ObjectRelation, RdmObject
from ...models.queries import ModelQuery
from ...models.schema import EngineModel
from ..jobs.store import start_job
from ..reads.model_query import plan_model_query

Parent = aliased(RdmObject)

# The most relationships one rule may make: a rule that pairs more is refused, to be narrowed.
MAX_PAIRS = 100_000


class LinkSide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    where: list[dict[str, Any]] = []


class LinkRule(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    relationTypeKey: str
    from_: LinkSide = Field(alias="from")
    to: LinkSide
    reason: str = Field(default="", max_length=500)


def _ids(model: EngineModel, workspace: str, side: LinkSide) -> Any:
    query = ModelQuery.model_validate({"objectTypeKey": side.objectTypeKey, "where": side.where})
    plan = plan_model_query(model, query, workspace_key=workspace, context=None)
    return plan.query.statement.with_only_columns(RdmObject.id).order_by(None).subquery()


def _single(model: EngineModel, rule: LinkRule) -> str | None:
    """The side whose record holds one record of the other end (``from`` or ``to``), or ``None``."""
    binding = model.allowed_relation(
        rule.relationTypeKey, rule.from_.objectTypeKey, rule.to.objectTypeKey
    )
    cardinality = binding.cardinality if binding is not None else "many-to-many"
    if cardinality in ("many-to-one", "one-to-one"):
        return "from"
    if cardinality == "one-to-many":
        return "to"
    return None


def check(session: Session, model: EngineModel, workspace: str, rule: LinkRule) -> dict[str, Any]:
    """How many relationships the rule makes and replaces, or why it is refused."""
    if (
        model.allowed_relation(
            rule.relationTypeKey, rule.from_.objectTypeKey, rule.to.objectTypeKey
        )
        is None
    ):
        return {
            "refused": f"The model allows no '{rule.relationTypeKey}' from "
            f"'{rule.from_.objectTypeKey}' to '{rule.to.objectTypeKey}'"
        }
    try:
        left, right = _ids(model, workspace, rule.from_), _ids(model, workspace, rule.to)
    except (ApiError, ValidationError) as error:
        message = error.message if isinstance(error, ApiError) else str(error)
        details = error.details if isinstance(error, ApiError) else None
        return {"refused": message, "details": details}
    found = session.execute(
        select(
            select(func.count()).select_from(left).scalar_subquery(),
            select(func.count()).select_from(right).scalar_subquery(),
        )
    ).one()
    pairs = found[0] * found[1]
    entry: dict[str, Any] = {"from": found[0], "to": found[1], "pairs": pairs}
    single = _single(model, rule)
    if single is not None:
        other = found[1] if single == "from" else found[0]
        anchors = left if single == "from" else right
        held = ObjectRelation.from_object_id if single == "from" else ObjectRelation.to_object_id
        if other > 1:
            side = rule.from_ if single == "from" else rule.to
            entry["refused"] = (
                f"Each {side.objectTypeKey} holds one '{rule.relationTypeKey}'; the rule finds "
                f"{other} records for it: narrow it to one"
            )
            return entry
        entry["replaces"] = (
            session.scalar(
                select(func.count(func.distinct(held))).where(
                    ObjectRelation.relation_type_key == rule.relationTypeKey,
                    held.in_(select(anchors.c.id)),
                )
            )
            or 0
        )
    if pairs > MAX_PAIRS:
        entry["refused"] = f"The rule makes {pairs} relationships, more than {MAX_PAIRS}: narrow it"
    return entry


def rules_of(design: dict[str, Any]) -> list[LinkRule]:
    return [LinkRule.model_validate(item) for item in design.get("links") or []]


def queue(
    session: Session,
    model: EngineModel,
    *,
    workspace: str,
    change_set: Any,
    model_release_id: int,
    rules: list[LinkRule],
    retention_days: int,
) -> Job | None:
    """One background batch of the rules' ``ensureRelation`` items into the change set, its inputs
    written by ``INSERT … SELECT``; ``None`` when the rules pair nothing. The caller commits."""
    selects = []
    for rule in rules:
        left, right = _ids(model, workspace, rule.from_), _ids(model, workspace, rule.to)
        single = _single(model, rule)
        if single is None:
            item = func.jsonb_build_object(
                literal("op"),
                literal("ensureRelation"),
                literal("relationTypeKey"),
                literal(rule.relationTypeKey),
                literal("from"),
                func.jsonb_build_object(literal("id"), left.c.id),
                literal("to"),
                func.jsonb_build_object(literal("id"), right.c.id),
            )
        else:
            # The record that holds one is given the other: its set replaced.
            anchor, target = (left, right) if single == "from" else (right, left)
            item = func.jsonb_build_object(
                literal("op"),
                literal("replaceRelationSet"),
                literal("relationTypeKey"),
                literal(rule.relationTypeKey),
                literal("fromObjectTypeKey"),
                literal(rule.from_.objectTypeKey),
                literal("toObjectTypeKey"),
                literal(rule.to.objectTypeKey),
                literal("direction"),
                literal("outgoing" if single == "from" else "incoming"),
                literal("anchor"),
                func.jsonb_build_object(literal("id"), anchor.c.id),
                literal("targets"),
                func.jsonb_build_array(
                    func.jsonb_build_object(
                        literal("object"), func.jsonb_build_object(literal("id"), target.c.id)
                    )
                ),
            )
        selects.append(select(item.label("item")).select_from(left.join(right, literal(True))))
    if not selects:
        return None
    union = (
        selects[0].union_all(*selects[1:]).subquery() if len(selects) > 1 else selects[0].subquery()
    )
    total = session.scalar(select(func.count()).select_from(union)) or 0
    if total == 0:
        return None
    job = start_job(
        session,
        kind="batch",
        workspace_key=workspace,
        change_set_id=change_set.id,
        model_release_id=model_release_id,
        parameters={
            "policy": "independent",
            "run": "background",
            "stage": "execute",
            "onExisting": "overwrite",
            "otherWorkspaceIds": "refuse",
        },
        total=total,
        retention_days=retention_days,
        queued=True,
        change_set_version=change_set.version,
    )
    numbered = select(
        literal(job.sequence_id).label("job_id"),
        (func.row_number().over() - 1).label("item_index"),
        union.c.item,
    )
    session.execute(insert(JobInput).from_select(["job_id", "item_index", "item"], numbered))
    return job


def query_read(session: Session, model: EngineModel, workspace: str, read: Any) -> dict[str, Any]:
    """A design's ``query`` read: the live records the criteria find, each with its id, name, its
    parent's name and the attributes asked for, at most ``read.limit``."""
    asked = read.model_dump(exclude_defaults=True)
    if not read.objectTypeKey:
        return {"read": asked, "error": "query needs objectTypeKey"}
    try:
        ids = _ids(model, workspace, LinkSide(objectTypeKey=read.objectTypeKey, where=read.where))
    except (ApiError, ValidationError) as error:
        return {
            "read": asked,
            "error": error.message if isinstance(error, ApiError) else str(error),
        }
    total = session.scalar(select(func.count()).select_from(ids)) or 0
    rows = session.execute(
        select(
            RdmObject.id,
            RdmObject.name,
            select(Parent.name).where(Parent.id == RdmObject.parent_object_id).scalar_subquery(),
        )
        .where(RdmObject.id.in_(select(ids.c.id)))
        .order_by(RdmObject.name, RdmObject.id)
        .limit(read.limit)
    ).all()
    found = [{"id": i, "name": n, "parent": parent} for i, n, parent in rows]
    if read.attributes and found:
        values = session.execute(
            select(
                AttributeValue.object_id,
                AttributeValue.attribute_type_key,
                func.coalesce(
                    AttributeValue.text_value,
                    func.cast(AttributeValue.integer_value, String),
                    func.cast(AttributeValue.decimal_value, String),
                    func.cast(AttributeValue.boolean_value, String),
                    func.cast(AttributeValue.date_value, String),
                ),
            ).where(
                AttributeValue.object_id.in_([f["id"] for f in found]),
                AttributeValue.attribute_type_key.in_(list(read.attributes)),
            )
        ).all()
        by_id = {f["id"]: f for f in found}
        for object_id, key, value in values:
            by_id[object_id].setdefault("attributes", {})[key] = value
    return {"read": asked, "total": total, "result": found}
