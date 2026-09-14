"""View-configured, batched mapping queries within one database snapshot."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, String, cast, func, literal, or_, select
from sqlalchemy.orm import Bundle, Session
from sqlalchemy.sql.selectable import Subquery

from ..errors import api_error
from ..models.api import (
    MappingCandidatePage,
    MappingCoveragePage,
    MappingCoverageRow,
    MappingObjectSummary,
    MappingTargetPage,
    MappingTargetSummary,
)
from ..models.database import AttributeValue, ObjectRelation, RdmObject, RelationSetVersion
from ..models.schema import MappingGridViewConfig, MappingGridViewDefinition
from .attributes import VALUE_COLUMNS, load_attribute_values
from .mapping_projection import draft_mapping_projection
from .model.registry import ModelSnapshot, resolve_request_model
from .pagination import paginate_sequence, paginate_statement, text_key
from .workspaces import resolve_workspace

PREVIEW_SIZE = 20


def projection_bundle(projection: Subquery) -> Bundle:
    """Return each core projection as one named row for the shared paginator."""
    return Bundle("projection", *projection.c)


@dataclass
class MappingRead:
    session: Session
    workspace_key: str
    draft_id: str | None
    snapshot: ModelSnapshot
    config: MappingGridViewConfig
    filters: dict[str, Any]
    objects: Subquery
    relations: Subquery

    @property
    def source_type(self) -> str:
        return (
            self.config.fromObjectTypeKey
            if self.config.direction == "outgoing"
            else self.config.toObjectTypeKey
        )

    @property
    def target_type(self) -> str:
        return (
            self.config.toObjectTypeKey
            if self.config.direction == "outgoing"
            else self.config.fromObjectTypeKey
        )

    @property
    def anchor_column(self) -> Any:
        return (
            self.relations.c.from_object_id
            if self.config.direction == "outgoing"
            else self.relations.c.to_object_id
        )

    @property
    def other_column(self) -> Any:
        return (
            self.relations.c.to_object_id
            if self.config.direction == "outgoing"
            else self.relations.c.from_object_id
        )

    def paths(self, objects: list[Any]) -> dict[str, list[Any]]:
        """Fetch ancestors by hierarchy level, never once per mapping row."""
        known = {row.id: row for row in objects}
        frontier = {row.parent_object_id for row in objects if row.parent_object_id}
        while frontier:
            parents = list(
                self.session.scalars(
                    select(projection_bundle(self.objects)).where(self.objects.c.id.in_(frontier))
                )
            )
            known.update({row.id: row for row in parents})
            frontier = {
                row.parent_object_id
                for row in parents
                if row.parent_object_id and row.parent_object_id not in known
            }
        paths = {}
        for row in objects:
            path, seen, current = [], set(), row
            while current and current.id not in seen:
                seen.add(current.id)
                path.append(current)
                current = known.get(current.parent_object_id)
            paths[row.id] = list(reversed(path))
        return paths

    def summary(
        self, objects: list[Any], columns: tuple[str, ...]
    ) -> dict[str, MappingObjectSummary]:
        if self.draft_id:
            attrs = {row.id: row.attributes or {} for row in objects}
        else:
            values = load_attribute_values(self.session, [row.id for row in objects])
            attrs = {
                key: {name: value for name, (_, value) in fields.items()}
                for key, fields in values.items()
            }
        paths = (
            self.paths(objects)
            if any(key == "path" or key.startswith("ancestor:") for key in columns)
            else {}
        )
        result = {}
        for row in objects:
            definition = self.snapshot.model.object_type(row.object_type_key)
            builtins = {
                "id": row.id,
                "name": row.name,
                "objectType": definition.name,
                "createdAt": row.created_at,
                "updatedAt": row.updated_at,
                "path": " / ".join(part.name for part in paths.get(row.id, [])),
            }
            fields = {}
            for column in columns:
                if column in builtins:
                    value = builtins[column]
                elif column.startswith("ancestor:"):
                    value = next(
                        (
                            part.name
                            for part in paths.get(row.id, [])
                            if part.object_type_key == column.removeprefix("ancestor:")
                        ),
                        None,
                    )
                else:
                    value = attrs[row.id].get(column)
                    attribute = self.snapshot.model.attribute_type(column)
                    if value is not None and attribute.valueType == "decimal":
                        value = float(value)
                fields[column] = value
            result[row.id] = MappingObjectSummary(
                id=row.id, objectTypeKey=row.object_type_key, name=row.name, fields=fields
            )
        return result

    def edge_statement(self) -> Select:
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

    def versions(self, ids: list[str]) -> dict[str, int]:
        rows = self.session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == self.workspace_key,
                RelationSetVersion.workspace_draft_id == self.draft_id,
                RelationSetVersion.relation_type_key == self.config.relationTypeKey,
                RelationSetVersion.from_object_type_key == self.config.fromObjectTypeKey,
                RelationSetVersion.to_object_type_key == self.config.toObjectTypeKey,
                RelationSetVersion.direction == self.config.direction,
                RelationSetVersion.anchor_object_id.in_(ids),
            )
        )
        return {row.anchor_object_id: row.version for row in rows}

    def anchor(self, row: Any) -> str:
        return row.from_object_id if self.config.direction == "outgoing" else row.to_object_id

    def other(self, row: Any) -> str:
        return row.to_object_id if self.config.direction == "outgoing" else row.from_object_id

    def target_filters(self, source_id: str, version: int) -> dict[str, Any]:
        return {**self.filters, "sourceObjectId": source_id, "mappingVersion": version}

    def target_summaries(self, edges: list[Any]) -> list[MappingTargetSummary]:
        ids = {self.other(row) for row in edges}
        objects = (
            list(
                self.session.scalars(
                    select(projection_bundle(self.objects)).where(self.objects.c.id.in_(ids))
                )
            )
            if ids
            else []
        )
        summaries = self.summary(objects, self.config.targetDisplayColumns)
        return [
            MappingTargetSummary(
                relationId=row.id,
                attributes=row.attributes or {},
                object=summaries[self.other(row)],
            )
            for row in edges
        ]


def open_mapping_read(
    session: Session, workspace_key: str, application_key: str, view_key: str, draft_id: str | None
) -> MappingRead:
    # sqlite's legacy transaction mode does not BEGIN on SELECT. Begin before
    # resolving authority so fields, edges, counts and tokens share a snapshot.
    connection = session.connection()
    if connection.dialect.name == "sqlite":
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN")
    elif connection.dialect.name == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(session, workspace_key, draft_id, None)
    application = next(
        (row for row in snapshot.model.applications if row.key == application_key), None
    )
    view = (
        next((row for row in application.views if row.key == view_key), None)
        if application
        else None
    )
    if not isinstance(view, MappingGridViewDefinition):
        raise api_error(
            404, "mapping_view_not_found", "Mapping view not found in the selected model"
        )
    if draft_id:
        objects, relations = draft_mapping_projection(session, draft_id)
    else:
        objects = (
            select(
                RdmObject.id,
                RdmObject.application_key,
                RdmObject.object_type_key,
                RdmObject.name,
                RdmObject.parent_object_id,
                literal(None).label("attributes"),
                RdmObject.created_at,
                RdmObject.updated_at,
            )
            .where(RdmObject.workspace_key == workspace_key)
            .subquery("mapping_objects")
        )
        relations = select(
            ObjectRelation.id,
            ObjectRelation.relation_type_key,
            ObjectRelation.from_object_id,
            ObjectRelation.to_object_id,
            ObjectRelation.attributes,
        ).subquery("mapping_relations")
    config = view.config
    return MappingRead(
        session,
        workspace_key,
        draft_id,
        snapshot,
        config,
        {
            "workspaceKey": workspace_key,
            "workspaceDraftId": draft_id,
            "modelReleaseId": snapshot.release_id,
            "modelHash": snapshot.model_hash,
            "applicationKey": application_key,
            "viewKey": view_key,
            "config": config.model_dump(mode="json"),
        },
        objects,
        relations,
    )


def validate_binding(
    read: MappingRead, relation_type: str, from_type: str, to_type: str, direction: str
) -> None:
    if not any(
        row.relationTypeKey == relation_type
        and row.fromObjectTypeKey == from_type
        and row.toObjectTypeKey == to_type
        for row in read.snapshot.model.objectTypeRelations
    ):
        raise api_error(404, "mapping_binding_not_found", "Mapping relation binding not found")
    if (relation_type, from_type, to_type, direction) != (
        read.config.relationTypeKey,
        read.config.fromObjectTypeKey,
        read.config.toObjectTypeKey,
        read.config.direction,
    ):
        raise api_error(
            422,
            "mapping_view_binding_mismatch",
            "Binding and direction must match the selected mapping view",
        )


def object_page(
    read: MappingRead,
    object_type: str,
    fields: tuple[str, ...],
    search: str | None,
    cursor: str | None,
    page_size: int,
    *,
    candidates: bool = False,
) -> tuple[list[Any], str | None]:
    fields = tuple(
        field
        for field in fields
        if field == "name" or read.snapshot.model.attribute_type(field) is not None
    )
    if not candidates and "name" not in fields:
        fields = ("name", *fields)
    filters = {**read.filters, "objectTypeKey": object_type, "search": search, "fields": fields}
    allowed = next(
        row
        for row in read.snapshot.model.objectTypeRelations
        if row.relationTypeKey == read.config.relationTypeKey
        and row.fromObjectTypeKey == read.config.fromObjectTypeKey
        and row.toObjectTypeKey == read.config.toObjectTypeKey
    )
    statement = select(projection_bundle(read.objects)).where(
        read.objects.c.object_type_key == object_type
    )
    exclusive_target = candidates and (
        allowed.cardinality == "one-to-one"
        or (allowed.cardinality == "one-to-many" and read.config.direction == "outgoing")
    )
    if exclusive_target:
        edges = read.edge_statement().subquery()
        other = (
            edges.c.to_object_id if read.config.direction == "outgoing" else edges.c.from_object_id
        )
        statement = statement.where(~read.objects.c.id.in_(select(other)))
    if search:
        clauses = []
        for field in fields:
            if field == "name":
                clauses.append(read.objects.c.name.icontains(search, autoescape=True))
            elif read.draft_id:
                clauses.append(
                    cast(read.objects.c.attributes[field].as_string(), String).icontains(
                        search, autoescape=True
                    )
                )
            else:
                definition = read.snapshot.model.attribute_type(field)
                column = getattr(AttributeValue, VALUE_COLUMNS[definition.valueType])
                clauses.append(
                    select(AttributeValue.id)
                    .where(
                        AttributeValue.object_id == read.objects.c.id,
                        AttributeValue.attribute_type_key == field,
                        cast(column, String).icontains(search, autoescape=True),
                    )
                    .exists()
                )
        statement = statement.where(or_(*clauses))
    return paginate_statement(
        read.session,
        statement,
        keys=(text_key("id", read.objects.c.id, "id"),),
        scope="mapping-candidates" if candidates else "mapping-coverage",
        filters=filters,
        cursor=cursor,
        page_size=page_size,
    )


def coverage(
    read: MappingRead, search: str | None, cursor: str | None, page_size: int | None
) -> MappingCoveragePage:
    objects, next_cursor = object_page(
        read,
        read.source_type,
        read.config.sourceColumns,
        search,
        cursor,
        page_size or read.config.pageSize,
    )
    ids = [row.id for row in objects]
    sources = read.summary(objects, read.config.sourceColumns)
    versions = read.versions(ids)
    # Exact counts and bounded previews in one batched window query, in both
    # live and effective draft membership (including overlays and tombstones).
    ranked = (
        read.edge_statement()
        .where(read.anchor_column.in_(ids))
        .add_columns(
            func.count().over(partition_by=read.anchor_column).label("target_count"),
            func.row_number()
            .over(partition_by=read.anchor_column, order_by=read.relations.c.id)
            .label("position"),
        )
        .subquery()
    )
    result = (
        read.session.execute(
            select(projection_bundle(ranked))
            .where(ranked.c.position <= PREVIEW_SIZE + 1)
            .order_by(ranked.c.id)
        )
        .scalars()
        .all()
    )
    previews, counts = {key: [] for key in ids}, {key: 0 for key in ids}
    for edge in result:
        previews[read.anchor(edge)].append(edge)
        counts[read.anchor(edge)] = edge.target_count
    summaries = {
        item.relationId: item
        for item in read.target_summaries(
            [edge for rows in previews.values() for edge in rows[:PREVIEW_SIZE]]
        )
    }
    rows = []
    for key in ids:
        version = versions.get(key, 0)
        preview, continuation = paginate_sequence(
            previews[key],
            lambda row: (row.id,),
            scope="mapping-targets",
            filters=read.target_filters(key, version),
            cursor=None,
            page_size=PREVIEW_SIZE,
            sort=("relationId",),
        )
        count = counts[key]
        rows.append(
            MappingCoverageRow(
                source=sources[key],
                state="unmapped" if count == 0 else "mapped" if count == 1 else "ambiguous",
                mappingVersion=version,
                targetCount=count,
                targets=[summaries[row.id] for row in preview],
                targetsNextCursor=continuation,
            )
        )
    return MappingCoveragePage(items=rows, nextCursor=next_cursor)


def candidates(
    read: MappingRead,
    object_type: str,
    search: str | None,
    cursor: str | None,
    page_size: int | None,
) -> MappingCandidatePage:
    if object_type != read.target_type:
        raise api_error(
            422,
            "mapping_candidate_type_mismatch",
            "Candidate type must match the target side of the mapping view",
        )
    objects, next_cursor = object_page(
        read,
        object_type,
        read.config.candidateSearchFields,
        search,
        cursor,
        page_size or read.config.pageSize,
        candidates=True,
    )
    return MappingCandidatePage(
        items=list(read.summary(objects, read.config.targetDisplayColumns).values()),
        nextCursor=next_cursor,
    )


def target_details(
    read: MappingRead, source_id: str, version: int, cursor: str | None, page_size: int
) -> MappingTargetPage:
    exists = (
        read.session.scalar(
            select(read.objects.c.id).where(
                read.objects.c.id == source_id, read.objects.c.object_type_key == read.source_type
            )
        )
        is not None
    )
    if not exists:
        raise api_error(
            404, "mapping_source_not_found", "Mapping source not found in the selected context"
        )
    actual = read.versions([source_id]).get(source_id, 0)
    if actual != version:
        raise api_error(
            409,
            "mapping_version_conflict",
            "Mapping targets changed; refresh mapping coverage before continuing",
            {"mappingVersion": actual},
        )
    edges = read.edge_statement().where(read.anchor_column == source_id).subquery()
    count = read.session.scalar(select(func.count()).select_from(edges)) or 0
    page, next_cursor = paginate_statement(
        read.session,
        select(projection_bundle(edges)),
        keys=(text_key("relationId", edges.c.id, "id"),),
        scope="mapping-targets",
        filters=read.target_filters(source_id, version),
        cursor=cursor,
        page_size=page_size,
    )
    return MappingTargetPage(
        mappingVersion=version,
        targetCount=count,
        items=read.target_summaries(page),
        nextCursor=next_cursor,
    )
