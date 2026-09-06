from __future__ import annotations

from collections.abc import Mapping, Sequence
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

BUILT_IN_COLUMNS = {"id", "name", "path", "createdAt", "updatedAt"}
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


class TableViewConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    columns: tuple[str, ...] = Field(min_length=1)
    filterFields: tuple[str, ...] = Field(min_length=1)
    sortFields: tuple[str, ...] = Field(min_length=1)
    defaultSort: str
    pageSize: int = Field(ge=1, le=100)


class TableViewDefinition(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    type: Literal["table"]
    objectTypeKey: str
    config: TableViewConfig


ViewDefinition = TableViewDefinition


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

    schemaVersion: Literal["0.5"]
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
    def index_definitions(self) -> EngineModel:
        """Index top-level definitions by key and freeze the graph against later mutation.

        Cross-reference rules deliberately live outside this validator, in
        ``app.services.model.validation``: they need to report the JSON pointer of the node that
        failed, which a Pydantic ``ValueError`` cannot carry. Use
        ``app.services.model.compiler.compile_model`` or ``parse_model`` to obtain a model whose
        references are also known to resolve.
        """
        self._attribute_types_by_key = FrozenDict(_last_by_key(self.attributeTypes))
        self._object_types_by_key = FrozenDict(_last_by_key(self.objectTypes))
        self._relation_types_by_key = FrozenDict(_last_by_key(self.relationTypes))

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


def _last_by_key(items: Sequence[Any]) -> dict[str, Any]:
    """Index by key without rejecting duplicates; duplicate keys are a validation rule."""
    return {item.key: item for item in items}
