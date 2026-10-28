"""What a mapping view reads, in one context: the edges of its binding, the records meeting its
candidate criteria and the sources it leaves unmapped (Product 0.9 K7, 0.16 AP2).

The mapping read (``management/projections/mapping.py``) and the AI proposal job
(``proposals/mapping_selection.py``) both need "the targets a source may be given": one definition,
here, so a proposal never offers a target the candidate list would not.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Select, String, cast, exists, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from ...models.schema import EngineModel, MappingGridViewConfig
from .model_query import candidate_ids
from .snapshot_reads import change_set_context, publication_context


@dataclass
class MappingScope:
    session: Session
    workspace_key: str
    change_set_id: str | None
    publication_id: str | None
    model: EngineModel
    config: MappingGridViewConfig
    # The shapes ``mapping_projection.context_projection`` gives.
    objects: Subquery
    relations: Subquery

    @property
    def outgoing(self) -> bool:
        return self.config.direction == "outgoing"

    @property
    def source_type(self) -> str:
        return self.config.fromObjectTypeKey if self.outgoing else self.config.toObjectTypeKey

    @property
    def target_type(self) -> str:
        return self.config.toObjectTypeKey if self.outgoing else self.config.fromObjectTypeKey

    @property
    def anchor_column(self) -> Any:
        return self.relations.c.from_object_id if self.outgoing else self.relations.c.to_object_id

    @property
    def other_column(self) -> Any:
        return self.relations.c.to_object_id if self.outgoing else self.relations.c.from_object_id

    def edge_statement(self) -> Select[Any]:
        """The relations of the view's binding between records of its two types."""
        source, target = self.objects.alias("source"), self.objects.alias("target")
        return (
            select(*self.relations.c)
            .join(source, source.c.id == self.anchor_column)
            .join(target, target.c.id == self.other_column)
            .where(
                source.c.object_type_key == self.source_type,
                target.c.object_type_key == self.target_type,
                self.relations.c.relation_type_key == self.config.relationTypeKey,
            )
        )

    def eligible_clauses(self, object_type: str) -> list[ColumnElement[bool]]:
        """What a record of ``object_type`` (the target type) must meet to be chosen: not already
        the target of an edge when the binding lets a target hold one (an anti-join, 0.11 Q1,
        D177), and the binding's candidate criteria (0.9 K7, D171). Each clause is over
        ``objects.c.id``."""
        end = "to" if self.outgoing else "from"
        allowed = self.model.allowed_relation(
            self.config.relationTypeKey, self.config.fromObjectTypeKey, self.config.toObjectTypeKey
        )
        clauses: list[ColumnElement[bool]] = []
        if allowed.holds_one(end):
            edges = self.edge_statement().subquery()
            other = edges.c.to_object_id if self.outgoing else edges.c.from_object_id
            clauses.append(~exists().where(other == self.objects.c.id))
        criteria = allowed.candidates_at(end)
        if criteria:
            clauses.append(self.objects.c.id.in_(self._meeting(object_type, criteria)))
        return clauses

    def source_clauses(self) -> list[ColumnElement[bool]]:
        """What a record of the source type must meet to be a source of the view: the binding's
        criteria at the source end (D171), or an edge of the binding already held (made before the
        criteria, kept, D175). Each clause is over ``objects.c.id``; none when the binding has no
        criteria at that end."""
        end = "from" if self.outgoing else "to"
        allowed = self.model.allowed_relation(
            self.config.relationTypeKey, self.config.fromObjectTypeKey, self.config.toObjectTypeKey
        )
        criteria = allowed.candidates_at(end)
        if not criteria:
            return []
        edges = self.edge_statement().subquery("mapping_source_edges")
        anchor = edges.c.from_object_id if self.outgoing else edges.c.to_object_id
        return [
            or_(
                self.objects.c.id.in_(self._meeting(self.source_type, criteria)),
                exists().where(anchor == self.objects.c.id),
            )
        ]

    def _meeting(self, object_type: str, criteria: tuple[Any, ...]) -> Select[Any]:
        """The records of ``object_type`` meeting ``criteria`` in the context."""
        context = (
            change_set_context(self.session, self.change_set_id)
            if self.change_set_id
            else publication_context(self.session, self.publication_id)
            if self.publication_id
            else None
        )
        definition = self.model.object_type(object_type)
        assert definition is not None
        return candidate_ids(
            self.model, definition, criteria, workspace_key=self.workspace_key, context=context
        )

    def eligible_targets(self) -> Select[Any]:
        """The records a source may be given: ``id``, ``name`` and ``attributes``."""
        return select(self.objects.c.id, self.objects.c.name, self.objects.c.attributes).where(
            self.objects.c.object_type_key == self.target_type,
            *self.eligible_clauses(self.target_type),
        )

    def unmapped_sources(
        self, application_key: str, parent_object_id: str | None, search: str | None
    ) -> Select[Any]:
        """The sources of the view with no target, in a change set or publication context (the
        attributes are the projection's JSON): narrowed to a parent and a search as coverage is."""
        statement = select(self.objects.c.id, self.objects.c.name, self.objects.c.attributes).where(
            self.objects.c.object_type_key == self.source_type,
            self.objects.c.application_key == application_key,
            *self.source_clauses(),
        )
        if parent_object_id is not None:
            statement = statement.where(self.objects.c.parent_object_id == parent_object_id)
        edges = self.edge_statement().subquery("mapping_state_edges")
        anchor = edges.c.from_object_id if self.outgoing else edges.c.to_object_id
        statement = statement.where(~exists().where(anchor == self.objects.c.id))
        if search:
            clauses = [self.objects.c.name.icontains(search, autoescape=True)]
            clauses += [
                cast(self.objects.c.attributes[column].as_string(), String).icontains(
                    search, autoescape=True
                )
                for column in self.attribute_columns(self.config.sourceColumns)
            ]
            statement = statement.where(or_(*clauses))
        return statement

    def attribute_columns(self, columns: tuple[str, ...]) -> list[str]:
        """The columns that are attributes of the model (the rest are built-ins of the grid)."""
        return [
            column
            for column in columns
            if column != "name" and self.model.attribute_type(column) is not None
        ]
