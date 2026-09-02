from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ValueType = Literal[
    "text",
    "longText",
    "integer",
    "decimal",
    "boolean",
    "date",
    "dateTime",
    "json",
]
Cardinality = Literal["one-to-one", "one-to-many", "many-to-many"]

BUILT_IN_COLUMNS = {"id", "name", "state", "path", "createdAt", "updatedAt"}
DETAIL_FIELD_KEYS = BUILT_IN_COLUMNS | {"objectType"}


class AttributeTypeDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    description: str | None = None
    valueType: ValueType = "text"
    default: Any | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    ui: dict[str, Any] = Field(default_factory=dict)


class ObjectTypeAttributeDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    attributeTypeKey: str
    required: bool = False
    readOnly: bool = False
    order: int = 0
    ui: dict[str, Any] = Field(default_factory=dict)


class ObjectTypeDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    pluralName: str
    description: str | None = None
    icon: str | None = None
    displayAttributeTypeKey: str | None = None
    attributes: list[ObjectTypeAttributeDefinition] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)
    behavior: dict[str, Any] = Field(default_factory=dict)


class RelationTypeDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    reverseKey: str
    name: str
    reverseName: str
    isOriented: bool = True
    features: dict[str, Any] = Field(default_factory=dict)


class ObjectTypeRelationDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    cardinality: Cardinality = "many-to-many"
    required: bool = False
    attributeTypeKeys: list[str] = Field(default_factory=list)
    features: dict[str, Any] = Field(default_factory=dict)


class ViewDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    type: Literal["table", "form", "dashboard", "mappingGrid", "tree"]
    objectTypeKey: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class BreadcrumbDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    showApplication: bool = True
    showObjectType: bool = True
    showAncestors: bool = True


class DetailHeaderDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titleField: str = "name"
    subtitleField: str | None = None
    showObjectType: bool = True


class AttributesPanelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[str] = Field(default_factory=list)


class ChildrenPanelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectTypeKeys: list[str]
    columns: list[str] = Field(default_factory=lambda: ["name"])
    pageSize: int = Field(default=20, ge=1, le=100)


class RelationsPanelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKeys: list[str]
    direction: Literal["outgoing", "incoming", "both"] = "both"
    columns: list[str] = Field(default_factory=lambda: ["name", "objectType"])


class TablePanelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    columns: list[str] = Field(default_factory=lambda: ["name"])
    filterByParent: bool = False
    pageSize: int = Field(default=20, ge=1, le=100)


class HierarchyPanelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    showParent: bool = True
    showAncestors: bool = True


class PanelDefinitionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    region: Literal["main", "side"] = "main"
    order: int = 0
    visible: bool = True


class AttributesPanelDefinition(PanelDefinitionBase):
    type: Literal["attributes"]
    config: AttributesPanelConfig


class ChildrenPanelDefinition(PanelDefinitionBase):
    type: Literal["children"]
    config: ChildrenPanelConfig


class RelationsPanelDefinition(PanelDefinitionBase):
    type: Literal["relations"]
    config: RelationsPanelConfig


class TablePanelDefinition(PanelDefinitionBase):
    type: Literal["table"]
    config: TablePanelConfig


class HierarchyPanelDefinition(PanelDefinitionBase):
    type: Literal["hierarchy"]
    config: HierarchyPanelConfig = Field(default_factory=HierarchyPanelConfig)


PanelDefinition = Annotated[
    AttributesPanelDefinition
    | ChildrenPanelDefinition
    | RelationsPanelDefinition
    | TablePanelDefinition
    | HierarchyPanelDefinition,
    Field(discriminator="type"),
]


class DetailViewDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    breadcrumbs: BreadcrumbDefinition = Field(default_factory=BreadcrumbDefinition)
    header: DetailHeaderDefinition = Field(default_factory=DetailHeaderDefinition)
    panels: list[PanelDefinition]


class ApplicationDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    state: Literal["draft", "active", "retired"] = "active"
    objectTypeKeys: list[str]
    defaultView: str
    views: list[ViewDefinition]
    details: list[DetailViewDefinition] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ProductDefinition(BaseModel):
    name: str
    description: str | None = None


class ModelReleaseDefinition(BaseModel):
    key: str
    name: str
    version: str


class EngineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str
    release: ModelReleaseDefinition
    product: ProductDefinition
    attributeTypes: list[AttributeTypeDefinition]
    objectTypes: list[ObjectTypeDefinition]
    relationTypes: list[RelationTypeDefinition]
    objectTypeRelations: list[ObjectTypeRelationDefinition]
    applications: list[ApplicationDefinition]

    @model_validator(mode="after")
    def validate_references(self) -> EngineModel:
        attribute_map = _unique_map(self.attributeTypes, "attribute type")
        object_map = _unique_map(self.objectTypes, "object type")
        relation_map = _unique_map(self.relationTypes, "relation type")
        _unique_map(self.applications, "application")

        relation_keys: set[str] = set()
        for relation in self.relationTypes:
            for key in (relation.key, relation.reverseKey):
                if key in relation_keys:
                    raise ValueError(f"Duplicate relation or reverse key '{key}'")
                relation_keys.add(key)

        allowed_relation_keys: set[tuple[str, str, str]] = set()
        for object_type in self.objectTypes:
            bindings = _unique_binding_map(object_type.attributes, object_type.key)
            for binding in object_type.attributes:
                if binding.attributeTypeKey not in attribute_map:
                    raise ValueError(
                        f"Object type '{object_type.key}' references unknown attribute type "
                        f"'{binding.attributeTypeKey}'"
                    )
            display_key = object_type.displayAttributeTypeKey
            if display_key and display_key not in bindings:
                raise ValueError(
                    f"Object type '{object_type.key}' display attribute '{display_key}' "
                    "is not attached"
                )

        for allowed in self.objectTypeRelations:
            if allowed.relationTypeKey not in relation_map:
                raise ValueError(
                    f"Object-type relation references unknown relation type "
                    f"'{allowed.relationTypeKey}'"
                )
            if allowed.fromObjectTypeKey not in object_map:
                raise ValueError(
                    f"Object-type relation has unknown source '{allowed.fromObjectTypeKey}'"
                )
            if allowed.toObjectTypeKey not in object_map:
                raise ValueError(
                    f"Object-type relation has unknown target '{allowed.toObjectTypeKey}'"
                )
            unknown_attributes = set(allowed.attributeTypeKeys) - set(attribute_map)
            if unknown_attributes:
                raise ValueError(
                    f"Object-type relation '{allowed.relationTypeKey}' has unknown attributes: "
                    f"{sorted(unknown_attributes)}"
                )
            identity = (
                allowed.relationTypeKey,
                allowed.fromObjectTypeKey,
                allowed.toObjectTypeKey,
            )
            if identity in allowed_relation_keys:
                raise ValueError(f"Duplicate object-type relation {identity}")
            allowed_relation_keys.add(identity)

        for object_type in self.objectTypes:
            parent_relations = object_type.behavior.get("parentRelationTypeKeys", [])
            for parent_relation in parent_relations:
                if not any(
                    item.relationTypeKey == parent_relation
                    and item.toObjectTypeKey == object_type.key
                    for item in self.objectTypeRelations
                ):
                    raise ValueError(
                        f"Object type '{object_type.key}' has incompatible parent relation "
                        f"'{parent_relation}'"
                    )

        for application in self.applications:
            unknown = set(application.objectTypeKeys) - set(object_map)
            if unknown:
                raise ValueError(
                    f"Application '{application.key}' references unknown object types: "
                    f"{sorted(unknown)}"
                )
            views = _unique_map(application.views, f"view in {application.key}")
            if application.defaultView not in views:
                raise ValueError(
                    f"Application '{application.key}' has unknown default view "
                    f"'{application.defaultView}'"
                )
            for view in application.views:
                if view.objectTypeKey and view.objectTypeKey not in object_map:
                    raise ValueError(
                        f"View '{application.key}.{view.key}' references unknown object type "
                        f"'{view.objectTypeKey}'"
                    )
                if view.objectTypeKey:
                    attached = {
                        binding.attributeTypeKey
                        for binding in object_map[view.objectTypeKey].attributes
                    }
                    columns = set(view.config.get("columns", [])) - BUILT_IN_COLUMNS
                    unknown_columns = columns - attached
                    if unknown_columns:
                        raise ValueError(
                            f"View '{application.key}.{view.key}' has columns not attached to "
                            f"'{view.objectTypeKey}': {sorted(unknown_columns)}"
                        )

            detail_type_keys: set[str] = set()
            for detail in application.details:
                detail_path = f"Application '{application.key}' detail '{detail.objectTypeKey}'"
                if detail.objectTypeKey in detail_type_keys:
                    raise ValueError(f"{detail_path} is duplicated")
                detail_type_keys.add(detail.objectTypeKey)
                if detail.objectTypeKey not in object_map:
                    raise ValueError(f"{detail_path} references an unknown object type")
                if detail.objectTypeKey not in application.objectTypeKeys:
                    raise ValueError(f"{detail_path} is not available in the application")

                detail_type = object_map[detail.objectTypeKey]
                _validate_detail_fields(
                    [detail.header.titleField, detail.header.subtitleField],
                    [detail_type],
                    f"{detail_path} header",
                )
                panel_keys: set[str] = set()
                for panel in detail.panels:
                    panel_path = f"{detail_path} panel '{panel.key}'"
                    if panel.key in panel_keys:
                        raise ValueError(f"{panel_path} is duplicated")
                    panel_keys.add(panel.key)
                    if isinstance(panel, AttributesPanelDefinition):
                        _validate_detail_fields(panel.config.fields, [detail_type], panel_path)
                    elif isinstance(panel, ChildrenPanelDefinition):
                        _validate_panel_object_types(
                            panel.config.objectTypeKeys,
                            application,
                            object_map,
                            panel_path,
                        )
                        child_types = [object_map[key] for key in panel.config.objectTypeKeys]
                        _validate_detail_fields(panel.config.columns, child_types, panel_path)
                        for child_type in child_types:
                            parent_keys = set(
                                child_type.behavior.get("parentRelationTypeKeys", [])
                            )
                            if not any(
                                allowed.fromObjectTypeKey == detail.objectTypeKey
                                and allowed.toObjectTypeKey == child_type.key
                                and allowed.relationTypeKey in parent_keys
                                for allowed in self.objectTypeRelations
                            ):
                                raise ValueError(
                                    f"{panel_path} object type '{child_type.key}' is not a "
                                    f"configured child of '{detail.objectTypeKey}'"
                                )
                    elif isinstance(panel, RelationsPanelDefinition):
                        related_types: list[ObjectTypeDefinition] = []
                        for relation_key in panel.config.relationTypeKeys:
                            if relation_key not in relation_map:
                                raise ValueError(
                                    f"{panel_path} references unknown relation type "
                                    f"'{relation_key}'"
                                )
                            matches = [
                                allowed
                                for allowed in self.objectTypeRelations
                                if allowed.relationTypeKey == relation_key
                                and (
                                    panel.config.direction in {"outgoing", "both"}
                                    and allowed.fromObjectTypeKey == detail.objectTypeKey
                                    or panel.config.direction in {"incoming", "both"}
                                    and allowed.toObjectTypeKey == detail.objectTypeKey
                                )
                            ]
                            if not matches:
                                raise ValueError(
                                    f"{panel_path} relation '{relation_key}' is incompatible "
                                    f"with '{detail.objectTypeKey}' and direction "
                                    f"'{panel.config.direction}'"
                                )
                            for allowed in matches:
                                related_key = (
                                    allowed.toObjectTypeKey
                                    if allowed.fromObjectTypeKey == detail.objectTypeKey
                                    else allowed.fromObjectTypeKey
                                )
                                related_types.append(object_map[related_key])
                        _validate_detail_fields(panel.config.columns, related_types, panel_path)
                    elif isinstance(panel, TablePanelDefinition):
                        _validate_panel_object_types(
                            [panel.config.objectTypeKey],
                            application,
                            object_map,
                            panel_path,
                        )
                        _validate_detail_fields(
                            panel.config.columns,
                            [object_map[panel.config.objectTypeKey]],
                            panel_path,
                        )

        return self

    def attribute_type(self, key: str) -> AttributeTypeDefinition | None:
        return next((item for item in self.attributeTypes if item.key == key), None)

    def object_type(self, key: str) -> ObjectTypeDefinition | None:
        return next((item for item in self.objectTypes if item.key == key), None)

    def relation_type(self, key: str) -> RelationTypeDefinition | None:
        return next((item for item in self.relationTypes if item.key == key), None)


def _unique_map(items: list[Any], label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        if item.key in result:
            raise ValueError(f"Duplicate {label} key '{item.key}'")
        result[item.key] = item
    return result


def _unique_binding_map(
    items: list[ObjectTypeAttributeDefinition], object_type_key: str
) -> dict[str, ObjectTypeAttributeDefinition]:
    result: dict[str, ObjectTypeAttributeDefinition] = {}
    for item in items:
        if item.attributeTypeKey in result:
            raise ValueError(
                f"Duplicate attribute binding '{item.attributeTypeKey}' in '{object_type_key}'"
            )
        result[item.attributeTypeKey] = item
    return result


def _validate_panel_object_types(
    keys: list[str],
    application: ApplicationDefinition,
    object_map: dict[str, ObjectTypeDefinition],
    path: str,
) -> None:
    if not keys:
        raise ValueError(f"{path} requires at least one object type")
    if len(keys) != len(set(keys)):
        raise ValueError(f"{path} has duplicate object types")
    unknown = set(keys) - set(object_map)
    if unknown:
        raise ValueError(f"{path} references unknown object types: {sorted(unknown)}")
    unavailable = set(keys) - set(application.objectTypeKeys)
    if unavailable:
        raise ValueError(f"{path} uses object types outside the application: {sorted(unavailable)}")


def _validate_detail_fields(
    fields: list[str | None],
    object_types: list[ObjectTypeDefinition],
    path: str,
) -> None:
    present = [field for field in fields if field is not None]
    if len(present) != len(set(present)):
        raise ValueError(f"{path} has duplicate fields")
    attached = {
        binding.attributeTypeKey
        for object_type in object_types
        for binding in object_type.attributes
    }
    unknown = set(present) - attached - DETAIL_FIELD_KEYS
    if unknown:
        raise ValueError(f"{path} references unavailable fields: {sorted(unknown)}")
