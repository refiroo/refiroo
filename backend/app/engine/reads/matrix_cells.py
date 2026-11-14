"""Relation matrix cells in SQL, for one matrix shape in one context (Base 0.8 A2, A3b).

A matrix shape is what a ``relationMatrix`` view declares and the model derives: the binding's
relation type and the end the row sits on, the row, column and cell types, the types a column
record can hold cell records through, and the binding's condition. Views with the same shape have
the same cells, so the page (``relation_matrix``) and the stored cell states (``matrix_states``)
resolve them with the statements here. Nothing here names a type or relation.

A cell record's column is its nearest ancestor of the column type. The statements read a context's
tables by keyed lookups: live records, a publication's or a private base's rows, or a change set's
base rows it does not replace plus its own rows.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    CTE,
    Select,
    String,
    and_,
    case,
    column,
    exists,
    func,
    literal,
    select,
    union_all,
    values,
)
from sqlalchemy.orm import Session, aliased

from ...common.encoding import canonical_json, sha256_hex
from ...models.database import (
    AttributeValue,
    ChangeSetObject,
    ChangeSetRelation,
    ObjectRelation,
    RdmObject,
    SnapshotAttributeValue,
)
from ...models.schema import (
    EngineModel,
    ObjectTypeRelationDefinition,
    RelationMatrixViewConfig,
    RelationMatrixViewDefinition,
)
from ..model.traversal import ancestor_type_keys
from ..records.values import VALUE_COLUMNS
from .snapshot_reads import SnapshotContext, effective_object_value, effective_record

# Containment is acyclic, but a walk along it stops here whatever the data holds.
MAX_DEPTH = 64


@dataclass(frozen=True)
class MatrixShape:
    """What decides a matrix's cells, independent of the view that declares it.

    ``condition`` is the binding's ``uniqueWhenToAttributeEquals`` as (attribute, value type,
    value), kept only when the row is the binding's ``from`` end: the condition describes the
    ``to`` end. The key hashes the definition, so equal shapes share stored states.
    """

    relation_type_key: str
    direction: str
    row_type: str
    column_type: str
    cell_type: str
    walk_types: tuple[str, ...]
    condition: tuple[str, str, Any] | None

    @property
    def outgoing(self) -> bool:
        return self.direction == "outgoing"

    @property
    def anchor_end(self) -> str:
        return "from_object_id" if self.outgoing else "to_object_id"

    @property
    def other_end(self) -> str:
        return "to_object_id" if self.outgoing else "from_object_id"

    def definition(self) -> dict[str, Any]:
        return {
            "relationTypeKey": self.relation_type_key,
            "direction": self.direction,
            "rowObjectTypeKey": self.row_type,
            "columnObjectTypeKey": self.column_type,
            "cellObjectTypeKey": self.cell_type,
            "walkTypes": list(self.walk_types),
            "condition": list(self.condition) if self.condition else None,
        }

    @property
    def key(self) -> str:
        return sha256_hex(canonical_json(self.definition()), 32)

    @classmethod
    def from_definition(cls, data: dict[str, Any]) -> MatrixShape:
        condition = data.get("condition")
        return cls(
            data["relationTypeKey"],
            data["direction"],
            data["rowObjectTypeKey"],
            data["columnObjectTypeKey"],
            data["cellObjectTypeKey"],
            tuple(data["walkTypes"]),
            tuple(condition) if condition else None,
        )

    @classmethod
    def of_view(
        cls, model: EngineModel, config: RelationMatrixViewConfig, binding: ObjectTypeRelationDefinition
    ) -> MatrixShape:
        column_type, cell_type = config.columnObjectTypeKey, config.cellObjectTypeKey
        containers = {
            key
            for key in ancestor_type_keys(model, cell_type)
            if key != column_type and column_type in ancestor_type_keys(model, key)
        }
        declared = (
            binding.features.get("uniqueWhenToAttributeEquals")
            if config.direction == "outgoing"
            else None
        )
        condition = None
        if declared:
            attribute = model.attribute_type(declared["attributeTypeKey"])
            condition = (attribute.key, attribute.valueType, declared["value"])
        return cls(
            config.relationTypeKey,
            config.direction,
            config.rowObjectTypeKey,
            column_type,
            cell_type,
            tuple(sorted(containers | {cell_type})),
            condition,
        )


def view_binding(model: EngineModel, config: RelationMatrixViewConfig) -> ObjectTypeRelationDefinition:
    """The view's one binding; model validation guarantees it."""
    from_key, to_key = (
        (config.rowObjectTypeKey, config.cellObjectTypeKey)
        if config.direction == "outgoing"
        else (config.cellObjectTypeKey, config.rowObjectTypeKey)
    )
    return model.allowed_relation(config.relationTypeKey, from_key, to_key)


def model_shapes(model: EngineModel) -> dict[str, MatrixShape]:
    """Every matrix shape the model's views declare, by key."""
    shapes = {}
    for application in model.applications:
        for view in application.views:
            if isinstance(view, RelationMatrixViewDefinition):
                shape = MatrixShape.of_view(model, view.config, view_binding(model, view.config))
                shapes[shape.key] = shape
    return shapes


@dataclass(frozen=True)
class _Arm:
    """One source of a context's effective rows: a table, its public ID column and the terms that
    select its rows. ``owner`` names the owner of its rows' typed values in a change set or
    publication."""

    entity: Any
    id: str
    where: Callable[[Any], list[Any]]
    owner: Any = None


@dataclass
class CellScope:
    """One matrix shape read in one context: live (``context`` is ``None``), a change set, or a
    publication-like owner of immutable rows (a publication or a private base)."""

    session: Session
    workspace_key: str
    shape: MatrixShape
    context: SnapshotContext | None

    @property
    def outgoing(self) -> bool:
        return self.shape.outgoing

    @property
    def anchor_end(self) -> str:
        return self.shape.anchor_end

    @property
    def other_end(self) -> str:
        return self.shape.other_end

    def walk_types(self) -> list[str]:
        """The types a walk down from a column record passes: containers of the cell type that
        can sit under the column type, and the cell type. Another column record ends a branch."""
        return list(self.shape.walk_types)

    def object_arms(self) -> list[_Arm]:
        context = self.context
        if context is None:
            workspace_key = self.workspace_key
            return [_Arm(RdmObject, "id", lambda row: [row.workspace_key == workspace_key])]
        # Only walks down read object arms: they seek each owner's rows by (owner, parent).
        return self._snapshot_arms(
            context, context.base and context.base.objects, ChangeSetObject, "object_id"
        )

    def relation_arms(self) -> list[_Arm]:
        context = self.context
        if context is None:
            return [_Arm(ObjectRelation, "id", lambda row: [])]
        return self._snapshot_arms(
            context, context.base and context.base.relations, ChangeSetRelation, "relation_id"
        )

    @staticmethod
    def _snapshot_arms(
        context: SnapshotContext, base_entity: Any, overlay: Any, identity: str
    ) -> list[_Arm]:
        """A publication's rows, or a change set's base rows it does not replace and its own
        non-deleted rows."""
        base = context.base
        arms = []
        if base is not None:
            owner_column, owner_id = base.owner_column, base.owner_id
            replaced = aliased(overlay)

            def base_where(row: Any) -> list[Any]:
                where = [getattr(row, owner_column) == owner_id]
                if context.kind == "change_set":
                    # Correlated, so PostgreSQL anti-joins on the overlay's key. `NOT IN (the change
                    # set's rows)` is a subplan it hashes only while they fit in `work_mem`; past that
                    # it scans them for every base row (0.9 R, R-F25).
                    where.append(
                        ~exists().where(
                            replaced.change_set_id == context.id,
                            getattr(replaced, identity) == getattr(row, identity),
                        )
                    )
                return where

            arms.append(_Arm(base_entity, identity, base_where, literal(owner_id, String)))
        if context.kind == "change_set":
            arms.append(
                _Arm(
                    overlay,
                    identity,
                    lambda row: [row.change_set_id == context.id, row.is_deleted.is_(False)],
                    literal(context.id, String),
                )
            )
        return arms

    def object_rows(self, columns: Sequence[str], name: str) -> Any:
        """The context's effective object rows as one selectable: ``id``, ``owner`` and
        ``columns``. A walk joins it in its one recursive term, which PostgreSQL requires; its
        join on ``parent_object_id`` reaches each arm's (owner, parent) index."""
        parts = []
        for arm in self.object_arms():
            row = aliased(arm.entity)
            parts.append(
                select(
                    getattr(row, arm.id).label("id"),
                    (arm.owner if arm.owner is not None else literal(None, String)).label("owner"),
                    *(getattr(row, column).label(column) for column in columns),
                ).where(*arm.where(row))
            )
        return (union_all(*parts) if len(parts) > 1 else parts[0]).subquery(name)

    def lookup(self, object_id: Any, name: str) -> Any:
        """One column of the context's record ``object_id`` (an expression), as a keyed lookup."""
        if self.context is not None:
            return effective_object_value(self.context, object_id, name)[0]
        record = aliased(RdmObject)
        return (
            select(getattr(record, name))
            .where(record.id == object_id)
            .correlate_except(record)
            .scalar_subquery()
        )

    def meets(self, object_id: Any, owner: Any, *, publication: bool = False) -> Any:
        """1 when the record meets the binding's condition, else 0; always 1 without one."""
        condition = self.shape.condition
        if not condition:
            return literal(1)
        attribute_key, value_type, expected = condition
        if self.context is None and not publication:
            value = aliased(AttributeValue)
            match = [value.object_id == object_id]
        else:
            value = aliased(SnapshotAttributeValue)
            match = [value.owner_id == owner, value.object_id == object_id]
        typed = getattr(value, VALUE_COLUMNS[value_type])
        held = exists(
            select(value.sequence_id)
            .where(
                *match,
                value.attribute_type_key == attribute_key,
                typed == literal(expected, typed.type),
            )
            .correlate_except(value)
        )
        return case((held, 1), else_=0)


def id_rows(ids: Sequence[str], name: str) -> Any:
    """Listed IDs as rows of a ``VALUES`` list named ``name``, with the column ``id``."""
    return values(column("id", String), name=name).data([(key,) for key in ids])


def cell_records(
    scope: CellScope,
    row_ids: Sequence[str] | None,
    *,
    rows_of_type: bool = False,
    relation_attributes: bool = False,
) -> CTE:
    """The rows' related cell records through the binding, one row per relation.

    ``row_ids`` drives the statement from the listed rows; ``None`` reads every relation of the
    relation type in the context. ``rows_of_type`` keeps relations whose row end is a record of
    the row type in the context, where the caller has not already chosen such rows.
    ``relation_attributes`` adds each relation's stored values as ``relation_attributes``; the state
    rebuild leaves them out, so it does not carry them through its walk.
    """
    shape = scope.shape
    edges = []
    for arm in scope.relation_arms():
        relation = aliased(arm.entity)
        where = list(arm.where(relation))
        if row_ids is None:
            where.append(relation.relation_type_key == shape.relation_type_key)
        else:
            where += [
                relation.relation_type_key == shape.relation_type_key,
                getattr(relation, scope.anchor_end).in_(row_ids),
            ]
        edges.append(
            select(
                getattr(relation, arm.id).label("relation_id"),
                relation.version.label("relation_version"),
                *([relation.attributes.label("relation_attributes")] if relation_attributes else []),
                getattr(relation, scope.anchor_end).label("row_id"),
                getattr(relation, scope.other_end).label("cell_id"),
            ).where(*where)
        )
    edge = (union_all(*edges) if len(edges) > 1 else edges[0]).subquery("matrix_edges")
    row_type = (
        [scope.lookup(edge.c.row_id, "object_type_key") == shape.row_type] if rows_of_type else []
    )
    if scope.context is None:
        record = aliased(RdmObject)
        statement = (
            select(
                edge.c.relation_id,
                edge.c.relation_version,
                *([edge.c.relation_attributes] if relation_attributes else []),
                edge.c.row_id,
                edge.c.cell_id,
                record.name.label("name"),
                record.version.label("version"),
                record.parent_object_id.label("parent_object_id"),
                literal(None, String).label("owner"),
                scope.meets(edge.c.cell_id, None).label("meets"),
            )
            .select_from(edge)
            .join(
                record,
                and_(
                    record.id == edge.c.cell_id,
                    record.workspace_key == scope.workspace_key,
                    record.object_type_key == shape.cell_type,
                ),
            )
            .where(*row_type)
        )
    else:
        record = effective_record(scope.context, edge.c.cell_id)
        statement = record.join(
            select(
                edge.c.relation_id,
                edge.c.relation_version,
                *([edge.c.relation_attributes] if relation_attributes else []),
                edge.c.row_id,
                edge.c.cell_id,
                record.column("name").label("name"),
                record.column("version").label("version"),
                record.column("parent_object_id").label("parent_object_id"),
                record.values_owner.label("owner"),
                scope.meets(edge.c.cell_id, record.values_owner).label("meets"),
            ).select_from(edge)
        ).where(
            record.present,
            record.column("object_type_key") == shape.cell_type,
            *row_type,
        )
    return statement.cte("matrix_cells")


def cell_columns(scope: CellScope, cells: CTE) -> Any:
    """Each cell record (a row of ``cells``, one per relation) with its column, ``column_id``.

    One depth-bounded walk up from each record to its nearest column-type ancestor carries the
    record's columns, so nothing joins the records back to the walk afterwards: a join of two
    unindexed CTEs, planned as a nested loop, was quadratic in the records.
    """
    column_type = scope.shape.column_type
    carried = [cells.c[column.name] for column in cells.c]
    walk = (
        select(*carried, cells.c.parent_object_id.label("node"), literal(1).label("depth"))
        .where(cells.c.parent_object_id.is_not(None))
        .cte("matrix_walk", recursive=True)
    )
    walk = walk.union_all(
        select(
            *(walk.c[column.name] for column in cells.c),
            scope.lookup(walk.c.node, "parent_object_id"),
            walk.c.depth + 1,
        ).where(
            walk.c.node.is_not(None),
            scope.lookup(walk.c.node, "object_type_key") != column_type,
            walk.c.depth < MAX_DEPTH,
        )
    )
    return (
        select(*(walk.c[column.name] for column in cells.c), walk.c.node.label("column_id"))
        .where(scope.lookup(walk.c.node, "object_type_key") == column_type)
        .subquery("matrix_columns")
    )


def cell_states(scope: CellScope, row_ids: Sequence[str] | None) -> Select[Any]:
    """(row, column, record count, matching count) for every non-empty cell of the rows, or of
    every row of the row type when ``row_ids`` is ``None``."""
    cells = cell_columns(scope, cell_records(scope, row_ids, rows_of_type=True))
    return select(
        cells.c.row_id,
        cells.c.column_id,
        func.count().label("record_count"),
        func.sum(cells.c.meets).label("matching_count"),
    ).group_by(cells.c.row_id, cells.c.column_id)


def descendants(scope: CellScope, anchor_ids: Sequence[str], types: Iterable[str]) -> Select[Any]:
    """The records of ``types`` under the listed records, at any depth through those types."""
    anchors = id_rows(anchor_ids, "matrix_anchors")
    walk = select(anchors.c.id.label("node"), literal(0).label("depth")).cte(
        "matrix_descendants", recursive=True
    )
    child = scope.object_rows(["parent_object_id", "object_type_key"], "matrix_descendant_rows")
    walk = walk.union_all(
        select(child.c.id, walk.c.depth + 1)
        .select_from(walk)
        .join(
            child,
            and_(
                child.c.parent_object_id == walk.c.node,
                child.c.object_type_key.in_(sorted(types)),
            ),
        )
        .where(walk.c.depth < MAX_DEPTH)
    )
    return select(walk.c.node).where(walk.c.depth > 0)


def related_rows(scope: CellScope, cell_ids: Sequence[str]) -> Select[Any]:
    """The row end of every relation of the binding's type whose other end is a listed record."""
    parts = []
    for arm in scope.relation_arms():
        relation = aliased(arm.entity)
        of_type = relation.relation_type_key == scope.shape.relation_type_key
        parts.append(
            select(getattr(relation, scope.anchor_end).label("row_id")).where(
                getattr(relation, scope.other_end).in_(cell_ids),
                of_type,
                *arm.where(relation),
            )
        )
    return union_all(*parts) if len(parts) > 1 else parts[0]
