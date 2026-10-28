"""View-configured, batched mapping queries within one database snapshot."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, String, cast, exists, func, literal, or_, select, union_all
from sqlalchemy.orm import Bundle, Session
from sqlalchemy.sql.selectable import Subquery

from ...common.pagination import (
    FIRST_PAGE,
    Page,
    PageRequest,
    paginate_sequence,
    paginate_statement,
    text_key,
)
from ...db import begin_snapshot_read
from ...engine.model.registry import ModelSnapshot, resolve_request_model
from ...engine.operations.mapping_replacement import PREVIEW_SIZE, MappingConflictSet
from ...engine.reads.mapping_projection import context_projection
from ...engine.reads.mapping_scope import MappingScope
from ...engine.records.attributes import load_attribute_values
from ...engine.records.values import VALUE_COLUMNS
from ...engine.workspaces.catalogue import resolve_workspace
from ...errors import api_error
from ...models.database import (
    AttributeValue,
    RelationSetVersion,
)
from ...models.schema import MappingGridViewConfig, MappingGridViewDefinition
from ..schemas.mapping import (
    MappingCandidatePage,
    MappingCoveragePage,
    MappingCoverageRow,
    MappingListPage,
    MappingListRow,
    MappingObjectSummary,
    MappingTargetPage,
    MappingTargetSummary,
)


def projection_bundle(projection: Subquery) -> Bundle:
    """Return each core projection as one named row for the shared paginator."""
    return Bundle("projection", *projection.c)


@dataclass
class MappingRead:
    session: Session
    workspace_key: str
    change_set_id: str | None
    publication_id: str | None
    snapshot: ModelSnapshot
    config: MappingGridViewConfig
    filters: dict[str, Any]
    objects: Subquery
    relations: Subquery

    @property
    def scope(self) -> MappingScope:
        return MappingScope(
            self.session,
            self.workspace_key,
            self.change_set_id,
            self.publication_id,
            self.snapshot.model,
            self.config,
            self.objects,
            self.relations,
        )

    @property
    def source_type(self) -> str:
        return self.scope.source_type

    @property
    def target_type(self) -> str:
        return self.scope.target_type

    @property
    def anchor_column(self) -> Any:
        return self.scope.anchor_column

    @property
    def other_column(self) -> Any:
        return self.scope.other_column

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
        if self.change_set_id or self.publication_id:
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
        return self.scope.edge_statement()

    def versions(self, ids: list[str]) -> dict[str, int]:
        if self.publication_id:
            # Publications are immutable and do not need a mutable-set concurrency token.
            # Zero is stable within the publication-bound continuation context.
            return {object_id: 0 for object_id in ids}
        rows = self.session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == self.workspace_key,
                RelationSetVersion.change_set_id == self.change_set_id,
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
                origin=row.origin,
            )
            for row in edges
        ]


def open_mapping_read(
    session: Session,
    workspace_key: str,
    application_key: str | None,
    view_key: str | None,
    change_set_id: str | None,
    *,
    publication_id: str | None = None,
    binding_config: MappingGridViewConfig | None = None,
) -> MappingRead:
    # Begin before resolving authority so fields, edges, counts and tokens share a snapshot.
    begin_snapshot_read(session)
    return _mapping_read_in_transaction(
        session,
        workspace_key,
        application_key,
        view_key,
        change_set_id,
        publication_id=publication_id,
        binding_config=binding_config,
    )


def _mapping_read_in_transaction(
    session,
    workspace_key,
    application_key,
    view_key,
    change_set_id,
    *,
    publication_id=None,
    binding_config=None,
):
    resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(session, workspace_key, change_set_id, publication_id)
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
            404, "MAPPING_VIEW_NOT_FOUND", "Mapping view not found in the selected model"
        )
    objects, relations = context_projection(
        session, workspace_key, change_set_id, publication_id
    )
    config = binding_config or view.config
    return MappingRead(
        session,
        workspace_key,
        change_set_id,
        publication_id,
        snapshot,
        config,
        {
            "workspaceKey": workspace_key,
            "changeSetId": change_set_id,
            "publicationId": publication_id,
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
        raise api_error(404, "MAPPING_BINDING_NOT_FOUND", "Mapping relation binding not found")
    if (relation_type, from_type, to_type, direction) != (
        read.config.relationTypeKey,
        read.config.fromObjectTypeKey,
        read.config.toObjectTypeKey,
        read.config.direction,
    ):
        raise api_error(
            422,
            "MAPPING_VIEW_BINDING_MISMATCH",
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
            "MAPPING_PARENT_NOT_FOUND",
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
            "MAPPING_PARENT_SCOPE_MISMATCH",
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
    proposed: bool = False,
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
        "proposed": proposed,
    }
    statement = select(projection_bundle(read.objects)).where(
        read.objects.c.object_type_key == object_type
    )
    if not candidates:
        statement = statement.where(
            read.objects.c.application_key == read.filters["applicationKey"],
            # Only records that can be mapped here, or already are (0.9 K7, D171, D175).
            *read.scope.source_clauses(),
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
    if proposed:
        # The sources with a target the AI proposed and nobody has changed since (0.16 AP2): the
        # change set's relation row still holds its origin.
        proposed_edges = read.edge_statement().subquery("mapping_proposed_edges")
        proposed_anchor = (
            proposed_edges.c.from_object_id
            if read.config.direction == "outgoing"
            else proposed_edges.c.to_object_id
        )
        statement = statement.where(
            exists().where(
                proposed_anchor == read.objects.c.id,
                proposed_edges.c.origin["kind"].as_string() == "ai",
            )
        )
    if candidates:
        # Only records the binding lets be chosen: not taken by a one-to-one end, meeting the
        # candidate criteria (0.9 K7, D171); one definition with the proposal job's (0.16 AP2).
        statement = statement.where(*read.scope.eligible_clauses(object_type))
    if search:
        clauses = []
        for field in fields:
            if field == "name":
                clauses.append(read.objects.c.name.icontains(search, autoescape=True))
            elif read.change_set_id or read.publication_id:
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
    proposed: bool = False,
) -> MappingCoveragePage:
    if proposed and read.change_set_id is None:
        raise api_error(
            422,
            "MAPPING_PROPOSED_NEEDS_CHANGE_SET",
            "proposed lists the sources whose target the AI proposed in a change set; "
            "send changeSetId",
        )
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
        proposed=proposed,
    )
    objects = source_page.items
    ids = [row.id for row in objects]
    sources = read.summary(objects, read.config.sourceColumns)
    versions = read.versions(ids)
    # Exact counts and bounded previews in one batched window query, in both
    # live and effective change set membership (including overlays and tombstones).
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
            "MAPPING_CANDIDATE_TYPE_MISMATCH",
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
    scope: str,
    change_set_id: str | None = None,
    publication_id: str | None = None,
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
    """The workspace edge list, published as ``/mappings`` and ``/relations``.

    ``scope`` names the route, so neither accepts the other's cursors.
    """
    begin_snapshot_read(session)
    resolve_workspace(session, workspace_key)
    snapshot = resolve_request_model(session, workspace_key, change_set_id, publication_id)

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
                404, "MAPPING_VIEW_NOT_FOUND", "Mapping view not found in the selected model"
            )
        config = view.config
    elif application_key is not None or view_key is not None:
        raise api_error(
            422,
            "INCOMPLETE_VIEW_IDENTITY",
            "Both applicationKey and viewKey are required when either is supplied",
        )

    objects, relations = context_projection(
        session, workspace_key, change_set_id, publication_id
    )

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

    combined = union_all(*parts).subquery("mapping_list")
    statement = select(projection_bundle(combined))
    effective_size = page_size or (config.pageSize if config else DEFAULT_LIST_PAGE_SIZE)
    cursor_filters = {
        "workspaceKey": workspace_key,
        "changeSetId": change_set_id,
        "publicationId": publication_id,
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
        scope=scope,
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
            change_set_id,
            publication_id,
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
    # A publication is immutable, so its sets carry version 0, as in MappingRead.versions.
    if anchor_keys and publication_id is None:
        version_rows = session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == workspace_key,
                RelationSetVersion.change_set_id == change_set_id
                if change_set_id is not None
                else RelationSetVersion.change_set_id.is_(None),
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
            404, "MAPPING_SOURCE_NOT_FOUND", "Mapping source not found in the selected context"
        )
    actual = read.versions([source_id]).get(source_id, 0)
    if actual != version:
        raise api_error(
            409,
            "MAPPING_VERSION_CONFLICT",
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


# ---------------------------------------------------------------------------
# Change set mapping replacement
# ---------------------------------------------------------------------------


def conflict_continuation(session: Session, conflict: MappingConflictSet) -> dict[str, Any]:
    """The first page of a conflicting set's targets, as the grid that shows the binding reads it.

    A binding no grid declares reads through a name-only grid configuration.
    """
    model = resolve_request_model(
        session, conflict.workspace_key, conflict.change_set_id, None
    ).model
    binding = (
        conflict.relation_type_key,
        conflict.from_object_type_key,
        conflict.to_object_type_key,
        conflict.direction,
    )
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
            ) != binding:
                continue
            read = _mapping_read_in_transaction(
                session, conflict.workspace_key, app.key, view.key, conflict.change_set_id
            )
            page = target_details(read, conflict.source_id, conflict.version, FIRST_PAGE, PREVIEW_SIZE)
            return {
                "targets": [item.model_dump(mode="json") for item in page.items],
                "targetsNextCursor": page.nextCursor,
                "applicationKey": app.key,
                "viewKey": view.key,
            }
    config = MappingGridViewConfig(
        relationTypeKey=conflict.relation_type_key,
        fromObjectTypeKey=conflict.from_object_type_key,
        toObjectTypeKey=conflict.to_object_type_key,
        direction=conflict.direction,
        sourceColumns=("name",),
        targetDisplayColumns=("name",),
        candidateSearchFields=("name",),
        pageSize=20,
    )
    read = _mapping_read_in_transaction(
        session, conflict.workspace_key, None, None, conflict.change_set_id, binding_config=config
    )
    page = target_details(read, conflict.source_id, conflict.version, FIRST_PAGE, PREVIEW_SIZE)
    return {
        "targets": [item.model_dump(mode="json") for item in page.items],
        "targetsNextCursor": page.nextCursor,
        "applicationKey": None,
        "viewKey": None,
    }
