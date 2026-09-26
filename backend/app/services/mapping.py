"""View-configured, batched mapping queries within one database snapshot."""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, String, cast, func, literal, or_, select, update
from sqlalchemy.orm import Bundle, Session, aliased
from sqlalchemy.sql.selectable import Subquery

from ..errors import api_error
from ..models.api import (
    MappingCandidatePage,
    MappingCoveragePage,
    MappingCoverageRow,
    MappingListPage,
    MappingListRow,
    MappingObjectSummary,
    MappingReplacementRequest,
    MappingReplacementResponse,
    MappingTargetPage,
    MappingTargetSummary,
    RelationCreate,
)
from ..models.database import (
    AttributeValue,
    ObjectRelation,
    RdmObject,
    RelationSetVersion,
    Workspace,
    WorkspaceDraft,
    WorkspaceDraftRelation,
)
from ..models.schema import EngineModel, MappingGridViewConfig, MappingGridViewDefinition
from .attributes import VALUE_COLUMNS, load_attribute_values
from .audit import record_audit_event
from .mapping_projection import draft_mapping_projection, revision_mapping_projection
from .model.registry import ModelSnapshot, resolve_request_model
from .pagination import (
    FIRST_PAGE,
    Page,
    PageRequest,
    paginate_sequence,
    paginate_statement,
    text_key,
)
from .relation_set_versions import claim_set_version, increment_single_set_version
from .relations import (
    ensure_relation_mutable,
    find_allowed_relation,
    validate_relation_attributes,
    validate_unique_to_ancestor,
)
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
    revision_id: str | None
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
        if self.draft_id or self.revision_id:
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
        if self.revision_id:
            # Revisions are immutable and do not need a mutable-set concurrency token.
            # Zero is stable within the revision-bound continuation context.
            return {object_id: 0 for object_id in ids}
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
    session: Session,
    workspace_key: str,
    application_key: str | None,
    view_key: str | None,
    draft_id: str | None,
    *,
    revision_id: str | None = None,
    binding_config: MappingGridViewConfig | None = None,
) -> MappingRead:
    # sqlite's legacy transaction mode does not BEGIN on SELECT. Begin before
    # resolving authority so fields, edges, counts and tokens share a snapshot.
    connection = session.connection()
    if connection.dialect.name == "sqlite":
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN")
    elif connection.dialect.name == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
    return _mapping_read_in_transaction(
        session,
        workspace_key,
        application_key,
        view_key,
        draft_id,
        revision_id=revision_id,
        binding_config=binding_config,
    )


def _mapping_read_in_transaction(
    session,
    workspace_key,
    application_key,
    view_key,
    draft_id,
    *,
    revision_id=None,
    binding_config=None,
):
    resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(session, workspace_key, draft_id, revision_id)
    application = next(
        (row for row in snapshot.model.applications if row.key == application_key), None
    )
    view = (
        next((row for row in application.views if row.key == view_key), None)
        if application
        else None
    )
    if binding_config is None and not isinstance(view, MappingGridViewDefinition):
        raise api_error(
            404, "mapping_view_not_found", "Mapping view not found in the selected model"
        )
    if draft_id:
        objects, relations = draft_mapping_projection(session, draft_id)
    elif revision_id:
        objects, relations = revision_mapping_projection(session, revision_id)
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
    config = binding_config or view.config
    return MappingRead(
        session,
        workspace_key,
        draft_id,
        revision_id,
        snapshot,
        config,
        {
            "workspaceKey": workspace_key,
            "workspaceDraftId": draft_id,
            "workspaceRevisionId": revision_id,
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


def validate_parent_scope(read: MappingRead, parent_object_id: str | None) -> None:
    """Require a real, model-authorized direct parent for contextual coverage."""
    if parent_object_id is None:
        return
    parent = read.session.execute(
        select(read.objects.c.id, read.objects.c.object_type_key).where(
            read.objects.c.id == parent_object_id
        )
    ).one_or_none()
    if parent is None:
        raise api_error(
            404,
            "mapping_parent_not_found",
            "Parent object not found in the selected context",
        )
    source = read.snapshot.model.object_type(read.source_type)
    parent_relations = set(source.behavior.get("parentRelationTypeKeys", ())) if source else set()
    compatible = any(
        binding.fromObjectTypeKey == parent.object_type_key
        and binding.toObjectTypeKey == read.source_type
        and binding.relationTypeKey in parent_relations
        and bool(read.snapshot.model.relation_type(binding.relationTypeKey).features.get("parentOf"))
        for binding in read.snapshot.model.objectTypeRelations
    )
    if not compatible:
        raise api_error(
            422,
            "mapping_parent_scope_mismatch",
            "Parent object type cannot contain sources for the selected mapping view",
        )


def object_page(
    read: MappingRead,
    object_type: str,
    fields: tuple[str, ...],
    search: str | None,
    page: PageRequest,
    page_size: int,
    *,
    candidates: bool = False,
    parent_object_id: str | None = None,
    mapping_state: str | None = None,
) -> Page[Any]:
    fields = tuple(
        field
        for field in fields
        if field == "name" or read.snapshot.model.attribute_type(field) is not None
    )
    if not candidates and "name" not in fields:
        fields = ("name", *fields)
    filters = {
        **read.filters,
        "objectTypeKey": object_type,
        "search": search,
        "fields": fields,
        "parentObjectId": parent_object_id,
        "state": mapping_state,
    }
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
    if not candidates:
        statement = statement.where(
            read.objects.c.application_key == read.filters["applicationKey"]
        )
    if parent_object_id is not None:
        statement = statement.where(read.objects.c.parent_object_id == parent_object_id)
    if mapping_state is not None:
        state_edges = read.edge_statement().subquery("mapping_state_edges")
        state_anchor = (
            state_edges.c.from_object_id
            if read.config.direction == "outgoing"
            else state_edges.c.to_object_id
        )
        target_count = (
            select(func.count())
            .select_from(state_edges)
            .where(state_anchor == read.objects.c.id)
            .correlate(read.objects)
            .scalar_subquery()
        )
        if mapping_state == "unmapped":
            statement = statement.where(target_count == 0)
        elif mapping_state == "mapped":
            statement = statement.where(target_count == 1)
        else:
            statement = statement.where(target_count > 1)
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
            elif read.draft_id or read.revision_id:
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
        # Sources and candidates list by name (D22), so ``seek`` jumps to a name.
        keys=(
            text_key("name", read.objects.c.name, "name"),
            text_key("id", read.objects.c.id, "id"),
        ),
        scope="mapping-candidates" if candidates else "mapping-coverage",
        filters=filters,
        page=page,
        page_size=page_size,
    )


def coverage(
    read: MappingRead,
    search: str | None,
    page: PageRequest,
    page_size: int | None,
    parent_object_id: str | None = None,
    mapping_state: str | None = None,
) -> MappingCoveragePage:
    validate_parent_scope(read, parent_object_id)
    source_page = object_page(
        read,
        read.source_type,
        read.config.sourceColumns,
        search,
        page,
        page_size or read.config.pageSize,
        parent_object_id=parent_object_id,
        mapping_state=mapping_state,
    )
    objects = source_page.items
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
        preview = paginate_sequence(
            previews[key],
            lambda row: (row.id,),
            scope="mapping-targets",
            filters=read.target_filters(key, version),
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
                targets=[summaries[row.id] for row in preview.items],
                targetsNextCursor=preview.next_cursor,
            )
        )
    return MappingCoveragePage(items=rows, **source_page.links())


def candidates(
    read: MappingRead,
    object_type: str,
    search: str | None,
    page: PageRequest,
    page_size: int | None,
) -> MappingCandidatePage:
    if object_type != read.target_type:
        raise api_error(
            422,
            "mapping_candidate_type_mismatch",
            "Candidate type must match the target side of the mapping view",
        )
    candidate_page = object_page(
        read,
        object_type,
        read.config.candidateSearchFields,
        search,
        page,
        page_size or read.config.pageSize,
        candidates=True,
    )
    return MappingCandidatePage(
        items=list(
            read.summary(candidate_page.items, read.config.targetDisplayColumns).values()
        ),
        **candidate_page.links(),
    )


DEFAULT_LIST_PAGE_SIZE = 20


def _default_summary(obj: Any) -> MappingObjectSummary:
    return MappingObjectSummary(
        id=obj.id, objectTypeKey=obj.object_type_key, name=obj.name, fields={}
    )


def list_mappings(
    session: Session,
    workspace_key: str,
    *,
    draft_id: str | None = None,
    application_key: str | None = None,
    view_key: str | None = None,
    relation_type_key: str | None = None,
    from_object_type_key: str | None = None,
    to_object_type_key: str | None = None,
    direction: str | None = None,
    search: str | None = None,
    page: PageRequest = FIRST_PAGE,
    page_size: int | None = None,
) -> MappingListPage:
    connection = session.connection()
    if connection.dialect.name == "sqlite":
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN")
    elif connection.dialect.name == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

    resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(session, workspace_key, draft_id, None)

    config = None
    if application_key is not None and view_key is not None:
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
        config = view.config
    elif application_key is not None or view_key is not None:
        raise api_error(
            422,
            "incomplete_view_identity",
            "Both applicationKey and viewKey are required when either is supplied",
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

    directions = [direction] if direction else ["outgoing", "incoming"]
    parts = []
    from_obj = objects.alias("from_obj")
    to_obj = objects.alias("to_obj")
    for d in directions:
        source_col = relations.c.from_object_id if d == "outgoing" else relations.c.to_object_id
        target_col = relations.c.to_object_id if d == "outgoing" else relations.c.from_object_id
        part = (
            select(
                relations.c.id.label("relation_id"),
                relations.c.attributes.label("relation_attributes"),
                relations.c.relation_type_key,
                literal(d).label("direction"),
                source_col.label("source_id"),
                target_col.label("target_id"),
                relations.c.from_object_id,
                relations.c.to_object_id,
            )
            .join(from_obj, from_obj.c.id == relations.c.from_object_id)
            .join(to_obj, to_obj.c.id == relations.c.to_object_id)
        )
        if relation_type_key:
            part = part.where(relations.c.relation_type_key == relation_type_key)
        if from_object_type_key:
            part = part.where(from_obj.c.object_type_key == from_object_type_key)
        if to_object_type_key:
            part = part.where(to_obj.c.object_type_key == to_object_type_key)
        if search:
            source_obj_search = from_obj if d == "outgoing" else to_obj
            target_obj_search = to_obj if d == "outgoing" else from_obj
            part = part.where(
                or_(
                    source_obj_search.c.name.icontains(search, autoescape=True),
                    target_obj_search.c.name.icontains(search, autoescape=True),
                )
            )
        parts.append(part)

    from sqlalchemy import union_all as sa_union_all

    combined = sa_union_all(*parts).subquery("mapping_list")
    statement = select(projection_bundle(combined))
    effective_size = page_size or (config.pageSize if config else DEFAULT_LIST_PAGE_SIZE)
    cursor_filters = {
        "workspaceKey": workspace_key,
        "workspaceDraftId": draft_id,
        "relationTypeKey": relation_type_key,
        "fromObjectTypeKey": from_object_type_key,
        "toObjectTypeKey": to_object_type_key,
        "direction": direction,
        "search": search,
    }
    edge_page = paginate_statement(
        session,
        statement,
        keys=(
            text_key("relationId", combined.c.relation_id, "relation_id"),
            text_key("direction", combined.c.direction, "direction"),
        ),
        scope="mapping-list",
        filters=cursor_filters,
        page=page,
        page_size=effective_size,
    )
    page = edge_page.items

    all_ids = list(dict.fromkeys(oid for row in page for oid in (row.source_id, row.target_id)))
    obj_rows = (
        list(session.scalars(select(projection_bundle(objects)).where(objects.c.id.in_(all_ids))))
        if all_ids
        else []
    )

    if config:
        read_for_summary = MappingRead(
            session,
            workspace_key,
            draft_id,
            None,
            snapshot,
            config,
            {},
            objects,
            relations,
        )
        all_summaries_source = read_for_summary.summary(obj_rows, config.sourceColumns)
        all_summaries_target = read_for_summary.summary(obj_rows, config.targetDisplayColumns)
    else:
        all_summaries_source = {obj.id: _default_summary(obj) for obj in obj_rows}
        all_summaries_target = all_summaries_source

    version_index: dict[tuple[str, str, str, str, str, str], int] = {}
    anchor_keys = set()
    for row in page:
        anchor_keys.add(
            (
                row.relation_type_key,
                row.from_object_id,
                row.to_object_id,
                row.source_id,
                row.direction,
            )
        )
    if anchor_keys:
        version_rows = session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == workspace_key,
                RelationSetVersion.workspace_draft_id == draft_id
                if draft_id is not None
                else RelationSetVersion.workspace_draft_id.is_(None),
            )
        )
        for v in version_rows:
            key = (
                v.relation_type_key,
                v.from_object_type_key,
                v.to_object_type_key,
                v.anchor_object_id,
                v.direction,
            )
            version_index[key] = v.version

    def _get_version(row: Any) -> int:
        src_obj = all_summaries_source.get(row.source_id) or all_summaries_target.get(row.source_id)
        tgt_obj = all_summaries_target.get(row.target_id) or all_summaries_source.get(row.target_id)
        if not src_obj or not tgt_obj:
            return 0
        if row.direction == "outgoing":
            ft, tt = src_obj.objectTypeKey, tgt_obj.objectTypeKey
        else:
            ft, tt = tgt_obj.objectTypeKey, src_obj.objectTypeKey
        return version_index.get((row.relation_type_key, ft, tt, row.source_id, row.direction), 0)

    rows = []
    for row in page:
        rows.append(
            MappingListRow(
                relationId=row.relation_id,
                relationTypeKey=row.relation_type_key,
                direction=row.direction,
                source=all_summaries_source.get(row.source_id)
                or all_summaries_target[row.source_id],
                target=all_summaries_target.get(row.target_id)
                or all_summaries_source[row.target_id],
                attributes=row.relation_attributes or {},
                mappingVersion=_get_version(row),
            )
        )
    return MappingListPage(items=rows, **edge_page.links())


def target_details(
    read: MappingRead, source_id: str, version: int, page: PageRequest, page_size: int
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
    target_page = paginate_statement(
        read.session,
        select(projection_bundle(edges)),
        keys=(text_key("relationId", edges.c.id, "id"),),
        scope="mapping-targets",
        filters=read.target_filters(source_id, version),
        page=page,
        page_size=page_size,
    )
    return MappingTargetPage(
        mappingVersion=version,
        targetCount=count,
        items=read.target_summaries(target_page.items),
        **target_page.links(),
    )


# ---------------------------------------------------------------------------
# WP-5: Atomic mapping replacement
# ---------------------------------------------------------------------------


def replace_mapping(
    session: Session, workspace_key: str, request: MappingReplacementRequest
) -> MappingReplacementResponse:
    # Claim active status before reading the graph. SQLite acquires its write lock here;
    # retirement cannot invalidate the active-status decision during this transaction.
    result = session.execute(
        update(Workspace)
        .where(Workspace.key == workspace_key, Workspace.status == "active")
        .values(updated_at=Workspace.updated_at)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        resolve_workspace(session, workspace_key, require_active=True)
    if request.workspaceDraftId:
        return _replace_draft_mapping(session, workspace_key, request)
    return _replace_live_mapping(session, workspace_key, request)


def _source_target_types(
    request: MappingReplacementRequest,
) -> tuple[str, str]:
    if request.direction == "outgoing":
        return request.fromObjectTypeKey, request.toObjectTypeKey
    return request.toObjectTypeKey, request.fromObjectTypeKey


def _validate_binding_for_replacement(model: EngineModel, request: MappingReplacementRequest):
    allowed = find_allowed_relation(
        model, request.relationTypeKey, request.fromObjectTypeKey, request.toObjectTypeKey
    )
    ensure_relation_mutable(model, request.relationTypeKey, request.toObjectTypeKey)
    if allowed.required and allowed.cardinality in {"one-to-one", "one-to-many"}:
        raise api_error(
            422,
            "required_ownership_binding",
            "Mapping replacement is not permitted on required-ownership bindings",
        )
    return allowed


def _validate_clear_attributes(request: MappingReplacementRequest) -> None:
    if request.targetObjectId is None and request.attributes:
        raise api_error(
            422,
            "invalid_clear_attributes",
            "Clearing a mapping permits omitted or empty attributes only",
        )


def _needs_cross_cardinality_check(allowed, direction: str) -> bool:
    return allowed.cardinality == "one-to-one" or (
        allowed.cardinality == "one-to-many" and direction == "outgoing"
    )


def _get_set_version(
    session: Session,
    workspace_key: str,
    draft_id: str | None,
    request: MappingReplacementRequest,
    source_id: str,
) -> int:
    draft_filter = (
        RelationSetVersion.workspace_draft_id == draft_id
        if draft_id is not None
        else RelationSetVersion.workspace_draft_id.is_(None)
    )
    row = session.scalar(
        select(RelationSetVersion).where(
            RelationSetVersion.workspace_key == workspace_key,
            draft_filter,
            RelationSetVersion.relation_type_key == request.relationTypeKey,
            RelationSetVersion.from_object_type_key == request.fromObjectTypeKey,
            RelationSetVersion.to_object_type_key == request.toObjectTypeKey,
            RelationSetVersion.anchor_object_id == source_id,
            RelationSetVersion.direction == request.direction,
        )
    )
    return row.version if row else 0


def _conflict_target_summaries(
    session: Session, edges: list[ObjectRelation], direction: str
) -> list[MappingTargetSummary]:
    if not edges:
        return []
    target_ids = list(dict.fromkeys(_edge_other_id(e, direction) for e in edges[:PREVIEW_SIZE]))
    objects = {
        row.id: row
        for row in session.scalars(select(RdmObject).where(RdmObject.id.in_(target_ids)))
    }
    result = []
    for edge in edges[:PREVIEW_SIZE]:
        obj = objects.get(_edge_other_id(edge, direction))
        if obj:
            result.append(
                MappingTargetSummary(
                    relationId=edge.id,
                    attributes=edge.attributes or {},
                    object=MappingObjectSummary(
                        id=obj.id,
                        objectTypeKey=obj.object_type_key,
                        name=obj.name,
                        fields={},
                    ),
                )
            )
    return result


def _conflict_continuation(session, workspace_key, request, source_id, version, count):
    if count <= PREVIEW_SIZE:
        return {}
    draft_id = str(request.workspaceDraftId) if request.workspaceDraftId else None
    model = resolve_request_model(session, workspace_key, draft_id, None).model
    for app in model.applications:
        for view in app.views:
            if not isinstance(view, MappingGridViewDefinition):
                continue
            config = view.config
            if (
                config.relationTypeKey,
                config.fromObjectTypeKey,
                config.toObjectTypeKey,
                config.direction,
            ) != (
                request.relationTypeKey,
                request.fromObjectTypeKey,
                request.toObjectTypeKey,
                request.direction,
            ):
                continue
            read = _mapping_read_in_transaction(session, workspace_key, app.key, view.key, draft_id)
            page = target_details(read, source_id, version, FIRST_PAGE, PREVIEW_SIZE)
            return {
                "targets": [item.model_dump(mode="json") for item in page.items],
                "targetsNextCursor": page.nextCursor,
                "applicationKey": app.key,
                "viewKey": view.key,
            }
    config = MappingGridViewConfig(
        relationTypeKey=request.relationTypeKey,
        fromObjectTypeKey=request.fromObjectTypeKey,
        toObjectTypeKey=request.toObjectTypeKey,
        direction=request.direction,
        sourceColumns=("name",),
        targetDisplayColumns=("name",),
        candidateSearchFields=("name",),
        pageSize=20,
    )
    read = _mapping_read_in_transaction(
        session, workspace_key, None, None, draft_id, binding_config=config
    )
    page = target_details(read, source_id, version, FIRST_PAGE, PREVIEW_SIZE)
    return {
        "targets": [item.model_dump(mode="json") for item in page.items],
        "targetsNextCursor": page.nextCursor,
        "applicationKey": None,
        "viewKey": None,
    }


def _raise_version_conflict(
    session: Session,
    workspace_key: str,
    request: MappingReplacementRequest,
    source_id: str,
    actual_version: int,
    edges: list[ObjectRelation],
) -> None:
    raise api_error(
        409,
        "mapping_version_conflict",
        "Mapping version has changed; refresh mapping coverage before retrying",
        {
            "mappingVersion": actual_version,
            "targetCount": len(edges),
            "targets": [
                t.model_dump(mode="json")
                for t in _conflict_target_summaries(session, edges, request.direction)
            ],
            "targetsNextCursor": None,
            **_conflict_continuation(
                session, workspace_key, request, source_id, actual_version, len(edges)
            ),
        },
    )


def _claim_mapping_set(session, workspace_key, draft_id, request, source_id):
    base = {
        "workspace_key": workspace_key,
        "workspace_draft_id": draft_id,
        "relation_type_key": request.relationTypeKey,
        "from_object_type_key": request.fromObjectTypeKey,
        "to_object_type_key": request.toObjectTypeKey,
    }
    if not claim_set_version(
        session,
        **base,
        anchor_object_id=source_id,
        direction=request.direction,
        expected=request.expectedMappingVersion,
    ):
        session.rollback()
        actual = _get_set_version(session, workspace_key, draft_id, request, source_id)
        if draft_id:
            from .workspace_revisions import effective_draft_membership

            membership = effective_draft_membership(session, draft_id)
            objects = {item.object_id: item for item in membership.objects}
            edges = _draft_edges(
                membership, request, source_id, _source_target_types(request)[1], objects
            )
            _raise_draft_version_conflict(session, request, source_id, actual, edges, objects)
        edges = _live_edges(
            session, request, source_id, _source_target_types(request)[1], workspace_key
        )
        _raise_version_conflict(session, workspace_key, request, source_id, actual, edges)


def _increment_affected_set_versions(
    session: Session,
    workspace_key: str,
    draft_id: str | None,
    request: MappingReplacementRequest,
    source_id: str,
    affected_target_ids: set[str],
) -> None:
    opposite = "incoming" if request.direction == "outgoing" else "outgoing"
    base = {
        "workspace_key": workspace_key,
        "workspace_draft_id": draft_id,
        "relation_type_key": request.relationTypeKey,
        "from_object_type_key": request.fromObjectTypeKey,
        "to_object_type_key": request.toObjectTypeKey,
    }
    for target_id in affected_target_ids:
        increment_single_set_version(
            session, **base, anchor_object_id=target_id, direction=opposite
        )


def _edge_other_id(edge: ObjectRelation, direction: str) -> str:
    return edge.to_object_id if direction == "outgoing" else edge.from_object_id


def _record_transition(
    session: Session,
    source_id: str,
    request: MappingReplacementRequest,
    new_version: int,
    old_targets: list[dict[str, Any]],
    new_target: dict[str, Any] | None,
    object_ids: list[str],
) -> None:
    record_audit_event(
        session,
        aggregate_type="mapping",
        aggregate_id=source_id,
        action="transition",
        version=new_version,
        changes={
            "relationTypeKey": request.relationTypeKey,
            "fromObjectTypeKey": request.fromObjectTypeKey,
            "toObjectTypeKey": request.toObjectTypeKey,
            "direction": request.direction,
            "workspaceDraftId": str(request.workspaceDraftId) if request.workspaceDraftId else None,
            "previousTargets": old_targets,
            "newTarget": new_target,
        },
        object_ids=object_ids,
    )


def _replace_live_mapping(
    session: Session, workspace_key: str, request: MappingReplacementRequest
) -> MappingReplacementResponse:
    resolve_workspace(session, workspace_key, require_active=True)
    model = resolve_request_model(session, workspace_key, None, None).model
    allowed = _validate_binding_for_replacement(model, request)
    source_type, target_type = _source_target_types(request)
    _validate_clear_attributes(request)

    source = _load_live_endpoint(session, workspace_key, str(request.sourceObjectId), source_type)
    target = (
        _load_live_endpoint(session, workspace_key, str(request.targetObjectId), target_type)
        if request.targetObjectId
        else None
    )

    source_id = source.id
    target_id = target.id if target else None

    actual_version = _get_set_version(session, workspace_key, None, request, source_id)
    edges = _live_edges(session, request, source_id, target_type, workspace_key)

    if request.expectedMappingVersion != actual_version:
        _raise_version_conflict(session, workspace_key, request, source_id, actual_version, edges)

    if target is None:
        if allowed.required:
            raise api_error(422, "required_relation", "A required relationship cannot be cleared")
        if not edges:
            return MappingReplacementResponse(
                sourceObjectId=source_id,
                mappingVersion=actual_version,
                state="unmapped",
            )
        return _execute_live_clear(session, model, workspace_key, request, source, edges)

    if _needs_cross_cardinality_check(allowed, request.direction):
        _check_live_cross_cardinality(session, request, source_id, target_id)

    retained = next((e for e in edges if _edge_other_id(e, request.direction) == target_id), None)
    obsolete = [e for e in edges if e.id != (retained.id if retained else None)]
    physical_source, physical_target = (
        (source, target) if request.direction == "outgoing" else (target, source)
    )
    validate_unique_to_ancestor(
        session,
        allowed,
        RelationCreate(
            relationTypeKey=request.relationTypeKey,
            fromObjectId=physical_source.id,
            toObjectId=physical_target.id,
        ),
        physical_target,
        exclude_relation_ids={edge.id for edge in edges},
    )

    if retained:
        if request.attributes is not None:
            new_attrs = validate_relation_attributes(model, allowed, request.attributes)
        else:
            new_attrs = dict(retained.attributes or {})
        if not obsolete and new_attrs == dict(retained.attributes or {}):
            return MappingReplacementResponse(
                sourceObjectId=source_id,
                mappingVersion=actual_version,
                state="mapped",
                relationId=retained.id,
            )
        return _execute_live_replace_with_retained(
            session, model, workspace_key, request, source, target, retained, obsolete, new_attrs
        )

    if request.attributes is not None:
        new_attrs = validate_relation_attributes(model, allowed, request.attributes)
    else:
        new_attrs = validate_relation_attributes(model, allowed, {})
    return _execute_live_replace_new(
        session, model, workspace_key, request, source, target, obsolete, new_attrs
    )


def _load_live_endpoint(
    session: Session, workspace_key: str, object_id: str, expected_type: str
) -> RdmObject:
    obj = session.scalar(select(RdmObject).where(RdmObject.id == object_id))
    if obj is None or obj.workspace_key != workspace_key:
        raise api_error(404, "mapping_endpoint_not_found", "Mapping endpoint not found")
    if obj.object_type_key != expected_type:
        raise api_error(
            422, "mapping_endpoint_type_mismatch", "Mapping endpoint type does not match binding"
        )
    return obj


def _live_edges(
    session: Session,
    request: MappingReplacementRequest,
    source_id: str,
    target_type: str,
    workspace_key: str,
) -> list[ObjectRelation]:
    if request.direction == "outgoing":
        anchor_col = ObjectRelation.from_object_id
        other_col = ObjectRelation.to_object_id
    else:
        anchor_col = ObjectRelation.to_object_id
        other_col = ObjectRelation.from_object_id
    other_obj = aliased(RdmObject)
    return list(
        session.scalars(
            select(ObjectRelation)
            .join(other_obj, other_obj.id == other_col)
            .where(
                ObjectRelation.relation_type_key == request.relationTypeKey,
                anchor_col == source_id,
                other_obj.object_type_key == target_type,
                other_obj.workspace_key == workspace_key,
            )
            .order_by(ObjectRelation.id)
        )
    )


def _check_live_cross_cardinality(
    session: Session, request: MappingReplacementRequest, source_id: str, target_id: str
) -> None:
    if request.direction == "outgoing":
        conflict = session.scalar(
            select(ObjectRelation.id)
            .where(
                ObjectRelation.relation_type_key == request.relationTypeKey,
                ObjectRelation.to_object_id == target_id,
                ObjectRelation.from_object_id != source_id,
            )
            .limit(1)
        )
    else:
        conflict = session.scalar(
            select(ObjectRelation.id)
            .where(
                ObjectRelation.relation_type_key == request.relationTypeKey,
                ObjectRelation.from_object_id == target_id,
                ObjectRelation.to_object_id != source_id,
            )
            .limit(1)
        )
    if conflict:
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")


def _old_target_audit(edge: ObjectRelation, direction: str) -> dict[str, Any]:
    return {
        "relationId": edge.id,
        "objectId": _edge_other_id(edge, direction),
        "attributes": edge.attributes or {},
    }


def _execute_live_clear(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    request: MappingReplacementRequest,
    source: RdmObject,
    edges: list[ObjectRelation],
) -> MappingReplacementResponse:
    _claim_mapping_set(session, workspace_key, None, request, source.id)
    old_targets = [_old_target_audit(e, request.direction) for e in edges]
    affected_ids: set[str] = set()
    for edge in edges:
        record_audit_event(
            session,
            aggregate_type="relation",
            aggregate_id=edge.id,
            action="deleted",
            version=edge.version + 1,
            changes={
                "relationTypeKey": edge.relation_type_key,
                "fromObjectId": edge.from_object_id,
                "toObjectId": edge.to_object_id,
            },
            object_ids=[edge.from_object_id, edge.to_object_id],
        )
        affected_ids.add(_edge_other_id(edge, request.direction))
        session.delete(edge)
    session.flush()
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(session, workspace_key, None, request, source.id, affected_ids)
    _record_transition(
        session,
        source.id,
        request,
        new_version,
        old_targets,
        None,
        [source.id, *sorted(affected_ids)],
    )
    session.commit()
    return MappingReplacementResponse(
        sourceObjectId=source.id, mappingVersion=new_version, state="unmapped"
    )


def _execute_live_replace_with_retained(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    request: MappingReplacementRequest,
    source: RdmObject,
    target: RdmObject,
    retained: ObjectRelation,
    obsolete: list[ObjectRelation],
    new_attrs: dict[str, Any],
) -> MappingReplacementResponse:
    _claim_mapping_set(session, workspace_key, None, request, source.id)
    old_targets = [_old_target_audit(e, request.direction) for e in [retained, *obsolete]]
    affected_ids: set[str] = set()
    attrs_changed = new_attrs != dict(retained.attributes or {})
    if attrs_changed:
        retained.attributes = new_attrs
        retained.version += 1
        record_audit_event(
            session,
            aggregate_type="relation",
            aggregate_id=retained.id,
            action="updated",
            version=retained.version,
            changes={"attributes": new_attrs},
            object_ids=[retained.from_object_id, retained.to_object_id],
        )
        affected_ids.add(target.id)
    for edge in obsolete:
        record_audit_event(
            session,
            aggregate_type="relation",
            aggregate_id=edge.id,
            action="deleted",
            version=edge.version + 1,
            changes={
                "relationTypeKey": edge.relation_type_key,
                "fromObjectId": edge.from_object_id,
                "toObjectId": edge.to_object_id,
            },
            object_ids=[edge.from_object_id, edge.to_object_id],
        )
        affected_ids.add(_edge_other_id(edge, request.direction))
        session.delete(edge)
    session.flush()
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(session, workspace_key, None, request, source.id, affected_ids)
    _record_transition(
        session,
        source.id,
        request,
        new_version,
        old_targets,
        {"relationId": retained.id, "objectId": target.id, "attributes": new_attrs},
        [source.id, *sorted(affected_ids | {target.id})],
    )
    session.commit()
    return MappingReplacementResponse(
        sourceObjectId=source.id,
        mappingVersion=new_version,
        state="mapped",
        relationId=retained.id,
    )


def _execute_live_replace_new(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    request: MappingReplacementRequest,
    source: RdmObject,
    target: RdmObject,
    obsolete: list[ObjectRelation],
    new_attrs: dict[str, Any],
) -> MappingReplacementResponse:
    _claim_mapping_set(session, workspace_key, None, request, source.id)
    old_targets = [_old_target_audit(e, request.direction) for e in obsolete]
    affected_ids: set[str] = set()
    for edge in obsolete:
        record_audit_event(
            session,
            aggregate_type="relation",
            aggregate_id=edge.id,
            action="deleted",
            version=edge.version + 1,
            changes={
                "relationTypeKey": edge.relation_type_key,
                "fromObjectId": edge.from_object_id,
                "toObjectId": edge.to_object_id,
            },
            object_ids=[edge.from_object_id, edge.to_object_id],
        )
        affected_ids.add(_edge_other_id(edge, request.direction))
        session.delete(edge)
    if request.direction == "outgoing":
        from_id, to_id = source.id, target.id
    else:
        from_id, to_id = target.id, source.id
    new_relation = ObjectRelation(
        relation_type_key=request.relationTypeKey,
        from_object_id=from_id,
        to_object_id=to_id,
        attributes=new_attrs,
    )
    session.add(new_relation)
    session.flush()
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=new_relation.id,
        action="created",
        version=1,
        changes={
            "relationTypeKey": new_relation.relation_type_key,
            "fromObjectId": from_id,
            "toObjectId": to_id,
            "attributes": new_attrs,
        },
        object_ids=[from_id, to_id],
    )
    affected_ids.add(target.id)
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(session, workspace_key, None, request, source.id, affected_ids)
    _record_transition(
        session,
        source.id,
        request,
        new_version,
        old_targets,
        {"relationId": new_relation.id, "objectId": target.id, "attributes": new_attrs},
        [source.id, *sorted(affected_ids)],
    )
    session.commit()
    return MappingReplacementResponse(
        sourceObjectId=source.id,
        mappingVersion=new_version,
        state="mapped",
        relationId=new_relation.id,
    )


# ---------------------------------------------------------------------------
# Draft mapping replacement
# ---------------------------------------------------------------------------


def _replace_draft_mapping(
    session: Session, workspace_key: str, request: MappingReplacementRequest
) -> MappingReplacementResponse:
    from .workspace_revisions import (
        claim_draft_version,
        effective_draft_membership,
        ensure_draft_writable,
        pinned_model,
        validate_draft_relation,
    )

    draft_id = str(request.workspaceDraftId)
    draft = ensure_draft_writable(session, draft_id)
    if draft.workspace_key != workspace_key:
        raise api_error(404, "workspace_draft_not_found", "Workspace draft not found")
    _, model = pinned_model(session, draft_id)
    allowed = _validate_binding_for_replacement(model, request)
    source_type, target_type = _source_target_types(request)
    _validate_clear_attributes(request)

    membership = effective_draft_membership(session, draft_id)
    objects = {item.object_id: item for item in membership.objects}
    source = objects.get(str(request.sourceObjectId))
    if source is None or source.object_type_key != source_type:
        raise api_error(404, "mapping_endpoint_not_found", "Mapping source not found in draft")
    source_id = source.object_id
    target, target_id = None, None
    if request.targetObjectId:
        target = objects.get(str(request.targetObjectId))
        if target is None or target.object_type_key != target_type:
            raise api_error(404, "mapping_endpoint_not_found", "Mapping target not found in draft")
        target_id = target.object_id

    actual_version = _get_set_version(session, workspace_key, draft_id, request, source_id)
    edges = _draft_edges(membership, request, source_id, target_type, objects)

    if request.expectedMappingVersion != actual_version:
        _raise_draft_version_conflict(session, request, source_id, actual_version, edges, objects)

    if request.expectedWorkspaceDraftVersion is None:
        raise api_error(
            409,
            "workspace_draft_required",
            "expectedWorkspaceDraftVersion is required when targeting a workspace draft",
        )

    if draft.version != request.expectedWorkspaceDraftVersion:
        raise api_error(
            409, "workspace_draft_version_conflict", "Workspace draft version has changed"
        )

    if target is None:
        if allowed.required:
            raise api_error(422, "required_relation", "A required relationship cannot be cleared")
        if not edges:
            return MappingReplacementResponse(
                sourceObjectId=source_id,
                mappingVersion=actual_version,
                state="unmapped",
                workspaceDraftVersion=draft.version,
            )
        claim_draft_version(session, draft, request.expectedWorkspaceDraftVersion)
        _claim_mapping_set(session, workspace_key, draft_id, request, source_id)
        return _execute_draft_clear(
            session, workspace_key, draft, request, source_id, edges, membership
        )

    if _needs_cross_cardinality_check(allowed, request.direction):
        _check_draft_cross_cardinality(membership, request, source_id, target_id, objects)

    retained = next(
        (e for e in edges if _draft_edge_other_id(e, request.direction) == target_id), None
    )
    obsolete = [e for e in edges if e.relation_id != (retained.relation_id if retained else None)]
    from_id, to_id = (
        (source_id, target_id) if request.direction == "outgoing" else (target_id, source_id)
    )
    validate_draft_relation(
        model,
        membership,
        request.relationTypeKey,
        from_id,
        to_id,
        request.attributes
        if request.attributes is not None
        else dict(retained.attributes or {})
        if retained
        else {},
        exclude_ids={edge.relation_id for edge in edges},
    )

    if retained:
        if request.attributes is not None:
            new_attrs = validate_relation_attributes(model, allowed, request.attributes)
        else:
            new_attrs = dict(retained.attributes or {})
        if not obsolete and new_attrs == dict(retained.attributes or {}):
            return MappingReplacementResponse(
                sourceObjectId=source_id,
                mappingVersion=actual_version,
                state="mapped",
                relationId=retained.relation_id,
                workspaceDraftVersion=draft.version,
            )
        claim_draft_version(session, draft, request.expectedWorkspaceDraftVersion)
        _claim_mapping_set(session, workspace_key, draft_id, request, source_id)
        return _execute_draft_replace_with_retained(
            session,
            workspace_key,
            draft,
            model,
            allowed,
            request,
            source_id,
            target_id,
            retained,
            obsolete,
            new_attrs,
            membership,
        )

    claim_draft_version(session, draft, request.expectedWorkspaceDraftVersion)
    _claim_mapping_set(session, workspace_key, draft_id, request, source_id)
    if request.attributes is not None:
        new_attrs = validate_relation_attributes(model, allowed, request.attributes)
    else:
        new_attrs = validate_relation_attributes(model, allowed, {})
    return _execute_draft_replace_new(
        session,
        workspace_key,
        draft,
        request,
        source_id,
        target_id,
        obsolete,
        new_attrs,
        membership,
    )


def _draft_edges(membership, request, source_id, target_type, objects):
    result = []
    for relation in membership.relations:
        if relation.relation_type_key != request.relationTypeKey:
            continue
        if request.direction == "outgoing":
            if relation.from_object_id != source_id:
                continue
            other_id = relation.to_object_id
        else:
            if relation.to_object_id != source_id:
                continue
            other_id = relation.from_object_id
        other = objects.get(other_id)
        if other and other.object_type_key == target_type:
            result.append(relation)
    return result


def _draft_edge_other_id(edge, direction: str) -> str:
    return edge.to_object_id if direction == "outgoing" else edge.from_object_id


def _raise_draft_version_conflict(session, request, source_id, actual_version, edges, objects):
    targets = []
    for edge in edges[:PREVIEW_SIZE]:
        other_id = _draft_edge_other_id(edge, request.direction)
        obj = objects.get(other_id)
        if obj:
            targets.append(
                MappingTargetSummary(
                    relationId=edge.relation_id,
                    attributes=edge.attributes or {},
                    object=MappingObjectSummary(
                        id=obj.object_id,
                        objectTypeKey=obj.object_type_key,
                        name=obj.name,
                        fields={},
                    ),
                ).model_dump(mode="json")
            )
    raise api_error(
        409,
        "mapping_version_conflict",
        "Mapping version has changed; refresh mapping coverage before retrying",
        {
            "mappingVersion": actual_version,
            "targetCount": len(edges),
            "targets": targets,
            "targetsNextCursor": None,
            **_conflict_continuation(
                session,
                session.scalar(
                    select(WorkspaceDraft.workspace_key).where(
                        WorkspaceDraft.id == str(request.workspaceDraftId)
                    )
                ),
                request,
                source_id,
                actual_version,
                len(edges),
            ),
        },
    )


def _check_draft_cross_cardinality(membership, request, source_id, target_id, objects):
    for relation in membership.relations:
        if relation.relation_type_key != request.relationTypeKey:
            continue
        if request.direction == "outgoing":
            if relation.to_object_id == target_id and relation.from_object_id != source_id:
                raise api_error(
                    409, "cardinality_violation", "Relation cardinality would be violated"
                )
        else:
            if relation.from_object_id == target_id and relation.to_object_id != source_id:
                raise api_error(
                    409, "cardinality_violation", "Relation cardinality would be violated"
                )


def _materialize_draft_relation(session, draft_id, base_relation):
    row = session.scalar(
        select(WorkspaceDraftRelation).where(
            WorkspaceDraftRelation.draft_id == draft_id,
            WorkspaceDraftRelation.relation_id == base_relation.relation_id,
        )
    )
    if row is not None:
        return row
    row = WorkspaceDraftRelation(
        draft_id=draft_id,
        relation_id=base_relation.relation_id,
        relation_type_key=base_relation.relation_type_key,
        from_object_id=base_relation.from_object_id,
        to_object_id=base_relation.to_object_id,
        attributes=dict(base_relation.attributes or {}),
        version=base_relation.version,
    )
    session.add(row)
    session.flush()
    return row


def _draft_old_target_audit(edge, direction):
    return {
        "relationId": edge.relation_id,
        "objectId": _draft_edge_other_id(edge, direction),
        "attributes": edge.attributes or {},
    }


def _record_draft_relation_change(session, draft_id, row, action):
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=row.relation_id,
        action=action,
        version=row.version,
        changes={
            "workspaceDraftId": draft_id,
            "relationTypeKey": row.relation_type_key,
            "fromObjectId": row.from_object_id,
            "toObjectId": row.to_object_id,
            "attributes": dict(row.attributes or {}),
        },
        object_ids=[row.from_object_id, row.to_object_id],
    )


def _execute_draft_clear(session, workspace_key, draft, request, source_id, edges, membership):
    old_targets = [_draft_old_target_audit(e, request.direction) for e in edges]
    affected_ids: set[str] = set()
    for edge in edges:
        row = _materialize_draft_relation(session, draft.id, edge)
        row.version += 1
        row.is_deleted = True
        _record_draft_relation_change(session, draft.id, row, "deleted")
        affected_ids.add(_draft_edge_other_id(edge, request.direction))
    session.flush()
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(
        session, workspace_key, draft.id, request, source_id, affected_ids
    )
    _record_transition(
        session,
        source_id,
        request,
        new_version,
        old_targets,
        None,
        [source_id, *sorted(affected_ids)],
    )
    session.commit()
    return MappingReplacementResponse(
        sourceObjectId=source_id,
        mappingVersion=new_version,
        state="unmapped",
        workspaceDraftVersion=draft.version,
    )


def _execute_draft_replace_with_retained(
    session,
    workspace_key,
    draft,
    model,
    allowed,
    request,
    source_id,
    target_id,
    retained,
    obsolete,
    new_attrs,
    membership,
):
    old_targets = [_draft_old_target_audit(e, request.direction) for e in [retained, *obsolete]]
    affected_ids: set[str] = set()
    attrs_changed = new_attrs != dict(retained.attributes or {})
    if attrs_changed:
        row = _materialize_draft_relation(session, draft.id, retained)
        row.attributes = new_attrs
        row.version += 1
        row.is_deleted = False
        _record_draft_relation_change(session, draft.id, row, "updated")
        affected_ids.add(target_id)
    for edge in obsolete:
        row = _materialize_draft_relation(session, draft.id, edge)
        row.version += 1
        row.is_deleted = True
        _record_draft_relation_change(session, draft.id, row, "deleted")
        affected_ids.add(_draft_edge_other_id(edge, request.direction))
    session.flush()
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(
        session, workspace_key, draft.id, request, source_id, affected_ids
    )
    _record_transition(
        session,
        source_id,
        request,
        new_version,
        old_targets,
        {"relationId": retained.relation_id, "objectId": target_id, "attributes": new_attrs},
        [source_id, *sorted(affected_ids | {target_id})],
    )
    session.commit()
    return MappingReplacementResponse(
        sourceObjectId=source_id,
        mappingVersion=new_version,
        state="mapped",
        relationId=retained.relation_id,
        workspaceDraftVersion=draft.version,
    )


def _execute_draft_replace_new(
    session,
    workspace_key,
    draft,
    request,
    source_id,
    target_id,
    obsolete,
    new_attrs,
    membership,
):
    old_targets = [_draft_old_target_audit(e, request.direction) for e in obsolete]
    affected_ids: set[str] = set()
    for edge in obsolete:
        row = _materialize_draft_relation(session, draft.id, edge)
        row.version += 1
        row.is_deleted = True
        _record_draft_relation_change(session, draft.id, row, "deleted")
        affected_ids.add(_draft_edge_other_id(edge, request.direction))
    if request.direction == "outgoing":
        from_id, to_id = source_id, target_id
    else:
        from_id, to_id = target_id, source_id
    new_relation_id = str(uuid4())
    new_row = WorkspaceDraftRelation(
        draft_id=draft.id,
        relation_id=new_relation_id,
        relation_type_key=request.relationTypeKey,
        from_object_id=from_id,
        to_object_id=to_id,
        attributes=new_attrs,
        version=1,
    )
    session.add(new_row)
    session.flush()
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=new_relation_id,
        action="created",
        version=1,
        changes={
            "relationTypeKey": request.relationTypeKey,
            "fromObjectId": from_id,
            "toObjectId": to_id,
            "attributes": new_attrs,
            "workspaceDraftId": draft.id,
        },
        object_ids=[from_id, to_id],
    )
    affected_ids.add(target_id)
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(
        session, workspace_key, draft.id, request, source_id, affected_ids
    )
    _record_transition(
        session,
        source_id,
        request,
        new_version,
        old_targets,
        {"relationId": new_relation_id, "objectId": target_id, "attributes": new_attrs},
        [source_id, *sorted(affected_ids)],
    )
    session.commit()
    return MappingReplacementResponse(
        sourceObjectId=source_id,
        mappingVersion=new_version,
        state="mapped",
        relationId=new_relation_id,
        workspaceDraftVersion=draft.version,
    )
