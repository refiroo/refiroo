from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
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


class FrozenDict(dict[str, Any]):
    """A JSON-compatible mapping that rejects mutation after model validation."""

    @staticmethod
    def _immutable(*args: Any, **kwargs: Any) -> None:
        raise TypeError("Model definitions are immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


class ModelDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)


class AttributeTypeDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    description: str | None = None
    valueType: ValueType = "text"
    default: Any | None = None
    features: Mapping[str, Any] = Field(default_factory=dict)
    validation: Mapping[str, Any] = Field(default_factory=dict)
    ui: Mapping[str, Any] = Field(default_factory=dict)


class ObjectTypeAttributeDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    attributeTypeKey: str
    required: bool = False
    readOnly: bool = False
    order: int = 0
    ui: Mapping[str, Any] = Field(default_factory=dict)


class ObjectTypeDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    pluralName: str
    description: str | None = None
    icon: str | None = None
    displayAttributeTypeKey: str | None = None
    attributes: tuple[ObjectTypeAttributeDefinition, ...] = ()
    features: Mapping[str, Any] = Field(default_factory=dict)
    behavior: Mapping[str, Any] = Field(default_factory=dict)
    validation: Mapping[str, Any] = Field(default_factory=dict)


class RelationTypeDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    key: str
    reverseKey: str
    name: str
    reverseName: str
    isOriented: bool = True
    features: Mapping[str, Any] = Field(default_factory=dict)


class ObjectTypeRelationDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    cardinality: Cardinality = "many-to-many"
    required: bool = False
    attributeTypeKeys: tuple[str, ...] = ()
    features: Mapping[str, Any] = Field(default_factory=dict)


class ViewDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    type: Literal["table", "form", "dashboard", "mappingGrid", "tree"]
    objectTypeKey: str | None = None
    config: Mapping[str, Any] = Field(default_factory=dict)


class BreadcrumbDefinition(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    showApplication: bool = True
    showObjectType: bool = True
    showAncestors: bool = True


class DetailHeaderDefinition(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    titleField: str = "name"
    subtitleField: str | None = None
    showObjectType: bool = True


class AttributesPanelConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    fields: tuple[str, ...] = ()


class ChildrenPanelConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    objectTypeKeys: tuple[str, ...]
    columns: tuple[str, ...] = ("name",)
    pageSize: int = Field(default=20, ge=1, le=100)


class RelationsPanelConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    relationTypeKeys: tuple[str, ...]
    direction: Literal["outgoing", "incoming", "both"] = "both"
    columns: tuple[str, ...] = ("name", "objectType")
    showRelationshipColumn: bool = True


class TablePanelConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    columns: tuple[str, ...] = ("name",)
    filterByParent: bool = False
    pageSize: int = Field(default=20, ge=1, le=100)


class HierarchyPanelConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    showParent: bool = True
    showAncestors: bool = True


class PanelDefinitionBase(ModelDefinition):
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


class DetailViewDefinition(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    breadcrumbs: BreadcrumbDefinition = Field(default_factory=BreadcrumbDefinition)
    header: DetailHeaderDefinition = Field(default_factory=DetailHeaderDefinition)
    panels: tuple[PanelDefinition, ...]


class ApplicationDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    key: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    state: Literal["draft", "active", "retired"] = "active"
    objectTypeKeys: tuple[str, ...]
    defaultView: str
    views: tuple[ViewDefinition, ...]
    details: tuple[DetailViewDefinition, ...] = ()
    settings: Mapping[str, Any] = Field(default_factory=dict)


class ProductDefinition(ModelDefinition):
    name: str
    description: str | None = None


class ModelReleaseDefinition(ModelDefinition):
    key: str
    name: str
    version: str


class EngineModel(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str
    release: ModelReleaseDefinition
    product: ProductDefinition
    attributeTypes: tuple[AttributeTypeDefinition, ...]
    objectTypes: tuple[ObjectTypeDefinition, ...]
    relationTypes: tuple[RelationTypeDefinition, ...]
    objectTypeRelations: tuple[ObjectTypeRelationDefinition, ...]
    applications: tuple[ApplicationDefinition, ...]

    _attribute_types_by_key: dict[str, AttributeTypeDefinition] = {}
    _object_types_by_key: dict[str, ObjectTypeDefinition] = {}
    _relation_types_by_key: dict[str, RelationTypeDefinition] = {}

    @model_validator(mode="after")
    def validate_references(self) -> EngineModel:
        attribute_map = _unique_map(self.attributeTypes, "attribute type")
        object_map = _unique_map(self.objectTypes, "object type")
        relation_map = _unique_map(self.relationTypes, "relation type")
        _unique_map(self.applications, "application")

        for attribute in self.attributeTypes:
            if attribute.features.get("unique") and attribute.valueType == "json":
                raise ValueError(
                    f"Attribute type '{attribute.key}' declares 'unique' but valueType "
                    f"'{attribute.valueType}' does not support uniqueness"
                )
            for bound in ("minimum", "maximum"):
                if bound not in attribute.validation:
                    continue
                if attribute.valueType not in {"integer", "decimal"}:
                    raise ValueError(
                        f"Attribute type '{attribute.key}' declares 'validation.{bound}' "
                        f"but valueType '{attribute.valueType}' does not support numeric bounds"
                    )
                value = attribute.validation[bound]
                if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                    raise ValueError(  # noqa: TRY004 - Pydantic validators must raise ValueError.
                        f"Attribute type '{attribute.key}' validation.{bound} must be a "
                        "finite number"
                    )
                try:
                    numeric_value = Decimal(str(value))
                except (InvalidOperation, ValueError):
                    numeric_value = Decimal("NaN")
                if not numeric_value.is_finite():
                    raise ValueError(
                        f"Attribute type '{attribute.key}' validation.{bound} must be a "
                        "finite number"
                    )
            minimum = attribute.validation.get("minimum")
            maximum = attribute.validation.get("maximum")
            if (
                minimum is not None
                and maximum is not None
                and Decimal(str(minimum)) > Decimal(str(maximum))
            ):
                raise ValueError(
                    f"Attribute type '{attribute.key}' validation.minimum must not exceed "
                    "validation.maximum"
                )

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
            at_least_one = object_type.validation.get("atLeastOneOf", [])
            if at_least_one:
                if not isinstance(at_least_one, list) or not all(
                    isinstance(key, str) for key in at_least_one
                ):
                    raise ValueError(
                        f"Object type '{object_type.key}' validation.atLeastOneOf must be a "
                        "list of attribute keys"
                    )
                if len(at_least_one) != len(set(at_least_one)):
                    raise ValueError(
                        f"Object type '{object_type.key}' validation.atLeastOneOf has duplicate keys"
                    )
                unknown = set(at_least_one) - set(bindings)
                if unknown:
                    raise ValueError(
                        f"Object type '{object_type.key}' validation.atLeastOneOf references "
                        f"unbound attributes: {sorted(unknown)}"
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
            unique_ancestor = allowed.features.get("uniqueToAncestorTypeKey")
            if unique_ancestor is not None and (
                not isinstance(unique_ancestor, str) or unique_ancestor not in object_map
            ):
                raise ValueError(
                    f"Object-type relation '{allowed.relationTypeKey}' references unknown unique "
                    f"ancestor object type '{unique_ancestor}'"
                )
            unique_condition = allowed.features.get("uniqueWhenToAttributeEquals")
            if unique_condition is not None:
                target_bindings = {
                    binding.attributeTypeKey
                    for binding in object_map[allowed.toObjectTypeKey].attributes
                }
                if (
                    not isinstance(unique_condition, dict)
                    or set(unique_condition) != {"attributeTypeKey", "value"}
                    or unique_condition.get("attributeTypeKey") not in target_bindings
                ):
                    raise ValueError(
                        f"Object-type relation '{allowed.relationTypeKey}' has an invalid "
                        "uniqueWhenToAttributeEquals condition"
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
                    _validate_detail_fields(
                        view.config.get("columns", []),
                        [object_map[view.objectTypeKey]],
                        f"View '{application.key}.{view.key}'",
                        object_map,
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
                    object_map,
                )
                panel_keys: set[str] = set()
                for panel in detail.panels:
                    panel_path = f"{detail_path} panel '{panel.key}'"
                    if panel.key in panel_keys:
                        raise ValueError(f"{panel_path} is duplicated")
                    panel_keys.add(panel.key)
                    if isinstance(panel, AttributesPanelDefinition):
                        _validate_detail_fields(
                            panel.config.fields, [detail_type], panel_path, object_map
                        )
                    elif isinstance(panel, ChildrenPanelDefinition):
                        _validate_panel_object_types(
                            panel.config.objectTypeKeys,
                            application,
                            object_map,
                            panel_path,
                        )
                        child_types = [object_map[key] for key in panel.config.objectTypeKeys]
                        _validate_detail_fields(
                            panel.config.columns, child_types, panel_path, object_map
                        )
                        for child_type in child_types:
                            parent_keys = set(child_type.behavior.get("parentRelationTypeKeys", []))
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
                        _validate_detail_fields(
                            panel.config.columns, related_types, panel_path, object_map
                        )
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
                            object_map,
                        )

        self._attribute_types_by_key = FrozenDict(attribute_map)
        self._object_types_by_key = FrozenDict(object_map)
        self._relation_types_by_key = FrozenDict(relation_map)

        _freeze_model_graph(self)

        return self

    def attribute_type(self, key: str) -> AttributeTypeDefinition | None:
        return self._attribute_types_by_key.get(key)

    def object_type(self, key: str) -> ObjectTypeDefinition | None:
        return self._object_types_by_key.get(key)

    def relation_type(self, key: str) -> RelationTypeDefinition | None:
        return self._relation_types_by_key.get(key)


def _freeze_model_graph(value: Any) -> Any:
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            object.__setattr__(value, field_name, _freeze_model_graph(getattr(value, field_name)))
        if value.__pydantic_extra__:
            object.__setattr__(
                value,
                "__pydantic_extra__",
                _freeze_model_graph(value.__pydantic_extra__),
            )
        return value
    if isinstance(value, Mapping):
        return FrozenDict({key: _freeze_model_graph(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_model_graph(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze_model_graph(item) for item in value)
    return value


def _unique_map(items: Sequence[Any], label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        if item.key in result:
            raise ValueError(f"Duplicate {label} key '{item.key}'")
        result[item.key] = item
    return result


def _unique_binding_map(
    items: Sequence[ObjectTypeAttributeDefinition], object_type_key: str
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
    object_map: dict[str, ObjectTypeDefinition],
) -> None:
    present = [field for field in fields if field is not None]
    if len(present) != len(set(present)):
        raise ValueError(f"{path} has duplicate fields")
    attached = {
        binding.attributeTypeKey
        for object_type in object_types
        for binding in object_type.attributes
    }
    ancestor_fields = {field for field in present if field.startswith("ancestor:")}
    for field in ancestor_fields:
        ancestor_type_key = field.removeprefix("ancestor:")
        if not ancestor_type_key or ancestor_type_key not in object_map:
            raise ValueError(f"{path} references unknown ancestor object type '{ancestor_type_key}'")
    unknown = set(present) - ancestor_fields - attached - DETAIL_FIELD_KEYS
    if unknown:
        raise ValueError(f"{path} references unavailable fields: {sorted(unknown)}")
