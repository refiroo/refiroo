from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, model_validator

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
Cardinality = Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"]
RelationEnd = Literal["from", "to"]
# The ends at which a record holds at most one relationship of a binding (0.9 K3a, D138).
_HOLDS_ONE: dict[str, frozenset[str]] = {
    "one-to-one": frozenset({"from", "to"}),
    "one-to-many": frozenset({"to"}),
    "many-to-one": frozenset({"from"}),
    "many-to-many": frozenset(),
}

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


class EffectivePeriodDefinition(ModelDefinition):
    """Schema 0.8 (Base 0.9 Q4, ADR-038): business validity from two ``date`` attributes.

    The start is inclusive and the end exclusive; either may be empty. The references are checked
    by ``engine/model/validation/object_type_rules.py``.
    """

    model_config = ConfigDict(extra="forbid")

    startAttributeTypeKey: str
    endAttributeTypeKey: str


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
    # Schema 0.8. Omitted from the canonical document when absent, so earlier hashes hold.
    effectivePeriod: EffectivePeriodDefinition | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class RelationTypeDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    key: str
    reverseKey: str
    name: str
    reverseName: str
    isOriented: bool = True
    features: Mapping[str, Any] = Field(default_factory=dict)


class CandidateCriterion(ModelDefinition):
    """One criterion a record at a binding's end must meet to be chosen (0.9 K7, D169): Q3's
    field criterion, over the record's own fields or an ancestor's (``ancestor:<type>.<field>``)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field: str
    op: str
    value: Any = None


class BindingCandidates(ModelDefinition):
    """Which records may be chosen at each end of a binding (0.9 K7, D168): criteria combined with
    AND, several ``eq`` on one field as alternatives; an end without criteria is unrestricted."""

    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True, validate_by_name=True)

    from_: tuple[CandidateCriterion, ...] = Field(default=(), alias="from")
    to: tuple[CandidateCriterion, ...] = ()

    def at(self, end: RelationEnd) -> tuple[CandidateCriterion, ...]:
        return self.from_ if end == "from" else self.to


class ObjectTypeRelationDefinition(ModelDefinition):
    model_config = ConfigDict(extra="allow")

    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    cardinality: Cardinality = "many-to-many"
    required: bool = False
    attributeTypeKeys: tuple[str, ...] = ()
    features: Mapping[str, Any] = Field(default_factory=dict)
    candidates: BindingCandidates | None = Field(default=None, exclude_if=lambda value: value is None)

    def holds_one(self, end: RelationEnd) -> bool:
        """Whether a record at ``end`` holds at most one relationship of this binding."""
        return end in _HOLDS_ONE[self.cardinality]

    def candidates_at(self, end: RelationEnd) -> tuple[CandidateCriterion, ...]:
        """The criteria a record at ``end`` must meet to be chosen; empty when unrestricted."""
        return self.candidates.at(end) if self.candidates else ()


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


MappingDirection = Literal["outgoing", "incoming"]


class MappingGridViewConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    direction: MappingDirection
    sourceColumns: tuple[str, ...] = Field(min_length=1)
    targetDisplayColumns: tuple[str, ...] = Field(min_length=1)
    candidateSearchFields: tuple[str, ...] = Field(min_length=1)
    pageSize: int = Field(ge=1, le=100)


class MappingGridViewDefinition(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    type: Literal["mappingGrid"]
    config: MappingGridViewConfig


RelationMatrixCellAction = Literal["create", "edit", "link", "unlink"]


class RelationMatrixViewConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: MappingDirection
    rowObjectTypeKey: str
    columnObjectTypeKey: str
    cellObjectTypeKey: str
    rowColumns: tuple[str, ...] = Field(min_length=1)
    columnLabelField: str
    cellFields: tuple[str, ...] = Field(min_length=1)
    searchFields: tuple[str, ...] = Field(min_length=1)
    cellActions: tuple[RelationMatrixCellAction, ...] = ()
    pageSize: int = Field(ge=1, le=100)


class RelationMatrixViewDefinition(ModelDefinition):
    """Schema 0.7: each row's related records, in columns by the ancestor record they sit under."""

    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    type: Literal["relationMatrix"]
    config: RelationMatrixViewConfig


TreeAction = Literal["createChild", "rename", "move", "setAvailability"]


class TreeViewConfig(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    rootObjectTypeKeys: tuple[str, ...] = Field(min_length=1)
    objectTypeKeys: tuple[str, ...] = Field(min_length=1)
    labelField: str
    secondaryField: str | None = None
    childSort: Mapping[str, str] = Field(default_factory=dict)
    pageSize: int = Field(ge=1, le=100)
    actions: tuple[TreeAction, ...] = ()
    availabilityField: str | None = None


class TreeViewDefinition(ModelDefinition):
    """Schema 0.7: a containment hierarchy as a tree, from its root types down through its node types."""

    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    type: Literal["tree"]
    config: TreeViewConfig


ViewDefinition = Annotated[
    TableViewDefinition
    | MappingGridViewDefinition
    | RelationMatrixViewDefinition
    | TreeViewDefinition,
    Field(discriminator="type"),
]


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
    # Schema 0.7. Omitted from the canonical document when absent, so 0.5 and 0.6 hashes hold.
    sortFields: tuple[str, ...] | None = Field(
        default=None, min_length=1, exclude_if=lambda value: value is None
    )
    defaultSort: str | None = Field(default=None, exclude_if=lambda value: value is None)


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


class NavigationGroupDefinition(ModelDefinition):
    """A labelled, collapsible sidebar section of an application's collections (schema 0.10, 0.10
    N1): presentation only, carrying no data, validation or permission."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    collections: tuple[str, ...] = ()
    collapsed: bool = False


class NavigationDefinition(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    groups: tuple[NavigationGroupDefinition, ...] = ()


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
    # Schema 0.10 (0.10 N1); omitted from the canonical document when absent, so earlier hashes hold.
    navigation: NavigationDefinition | None = Field(default=None, exclude_if=lambda value: value is None)


def _omitted() -> Any:
    """An optional field left out of the canonical document when absent."""
    return Field(default=None, exclude_if=lambda value: value is None)


# Schema 0.8 (Base 0.9 C1): consumer API definitions, CONSUMER_API.md "Definition shape". Shape only;
# every reference is checked by engine/model/validation/consumer_api_rules.py.


class ConsumerExposedType(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    publicName: str = Field(min_length=1)


class ConsumerField(ModelDefinition):
    """A role of the shared object: its output name and the first non-empty of its sources."""

    model_config = ConfigDict(extra="forbid")

    output: str = Field(min_length=1)
    source: tuple[str, ...] = Field(min_length=1)
    default: Any | None = _omitted()


class ConsumerAttributeField(ModelDefinition):
    """A further output field, named by its key in ``attributes``."""

    model_config = ConfigDict(extra="forbid")

    source: tuple[str, ...] = Field(min_length=1)
    default: Any | None = _omitted()


class ConsumerParentField(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    output: str = Field(min_length=1)
    fields: tuple[Literal["objectType", "id", "code", "name"], ...] = Field(min_length=1)


class ConsumerObjectDefinition(ModelDefinition):
    """The shared object's fixed roles, each under the output name the definition chooses."""

    model_config = ConfigDict(extra="forbid")

    id: ConsumerField
    code: ConsumerField | None = _omitted()
    name: ConsumerField | None = _omitted()
    active: ConsumerField | None = _omitted()
    validFrom: ConsumerField | None = _omitted()
    validTo: ConsumerField | None = _omitted()
    attributes: Mapping[str, ConsumerAttributeField] = Field(default_factory=dict)
    parent: ConsumerParentField | None = _omitted()
    path: str | None = _omitted()
    hierarchy: str | None = _omitted()


class ConsumerRelationRoute(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    relation: str
    direction: Literal["outgoing", "incoming"]


class ConsumerProjection(ModelDefinition):
    """A named block of related objects: output field name to a field of the related object."""

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True, validate_by_name=True)

    from_: ConsumerRelationRoute = Field(alias="from")
    fields: Mapping[str, str] = Field(min_length=1)


class ConsumerMatchRule(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    field: str
    exact: int | None = Field(default=None, ge=1, exclude_if=lambda value: value is None)
    contains: int | None = Field(default=None, ge=1, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def weigh_something(self) -> ConsumerMatchRule:
        if self.exact is None and self.contains is None:
            raise ValueError("A match rule needs an 'exact' or a 'contains' weight")
        return self


class ConsumerPromotedMatch(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    projection: str
    firstMatch: tuple[ConsumerMatchRule, ...] = Field(min_length=1)
    preferTargetTypes: tuple[str, ...] = ()


class ConsumerMatch(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    own: tuple[ConsumerMatchRule, ...] = ()
    promoted: tuple[ConsumerPromotedMatch, ...] = ()


class ObjectTypeParameter(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["objectType"]


class AncestorParameter(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["ancestor"]
    objectTypes: tuple[str, ...] = Field(min_length=1)
    matchFields: tuple[str, ...] = Field(min_length=1)


class RelatedParameter(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["related"]
    objectTypes: tuple[str, ...] = Field(min_length=1)
    matchFields: tuple[str, ...] = Field(min_length=1)
    # A projection name, "self", or "sharedProjection:<projection>".
    via: tuple[str, ...] = Field(min_length=1)


class ProjectionParameter(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["projection"]
    projection: str
    matchFields: tuple[str, ...] = Field(min_length=1)
    scoresFrom: bool = False
    requireMatch: bool = False
    targetable: bool = False


ConsumerParameter = Annotated[
    ObjectTypeParameter | AncestorParameter | RelatedParameter | ProjectionParameter,
    Field(discriminator="kind"),
]


class ConsumerListParent(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    objectTypes: tuple[str, ...] = Field(min_length=1)


class ConsumerList(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    key: str
    objectType: str
    parentParameter: ConsumerListParent | None = _omitted()
    # A scalar attribute the type binds; records without a value come last, then name (C-D29).
    sortBy: str | None = _omitted()


def _omitted_when_empty() -> Any:
    """An optional list left out of the canonical document when empty, so documents without it keep
    their hash."""
    return Field(default=(), exclude_if=lambda value: not value)


class ConsumerEventWatch(ModelDefinition):
    """What makes an object ``updated`` for an event: output names and projections (C-D81)."""

    model_config = ConfigDict(extra="forbid")

    fields: tuple[str, ...] = _omitted_when_empty()
    projections: tuple[str, ...] = _omitted_when_empty()


class ConsumerEvent(ModelDefinition):
    """A change event a definition declares (Base 0.9 C9, CONSUMER_API "Event definitions")."""

    model_config = ConfigDict(extra="forbid")

    key: str
    objectTypes: tuple[str, ...]
    changes: tuple[Literal["created", "updated", "deleted"], ...]
    # Without ``watch``, any change to the object's output counts.
    watch: ConsumerEventWatch | None = _omitted()


# The operations a definition can offer, by their route names (C-D132).
CONSUMER_OPERATIONS = ("objects", "xref", "resolve", "lists", "events")


class ConsumerApiDefinition(ModelDefinition):
    """One consumer API: its public name (``consumerApi`` in routes and contracts), contract version and shape.

    The schema 0.8 document shape, and the engine's internal form of every definition: a schema 0.9
    definition is expanded into it (C18), so every reader works on this one form.
    """

    model_config = ConfigDict(extra="forbid")

    key: str
    name: str = Field(min_length=1)
    description: str | None = _omitted()
    contractVersion: int = Field(ge=1)
    objectTypes: Mapping[str, ConsumerExposedType] = Field(min_length=1)
    object: ConsumerObjectDefinition
    projections: Mapping[str, ConsumerProjection] = Field(default_factory=dict)
    match: ConsumerMatch | None = _omitted()
    parameters: Mapping[str, ConsumerParameter] = Field(default_factory=dict)
    lists: tuple[ConsumerList, ...] = ()
    events: tuple[ConsumerEvent, ...] = _omitted_when_empty()

    # The operations among ``objects``, ``xref`` and ``resolve`` it offers: set by the expansion of a
    # schema 0.9 definition, all three for a schema 0.8 one. ``lists`` and ``events`` are offered
    # when it declares one, as before (an unknown list is a 404, no events EVENTS_NOT_DECLARED).
    # Private, so the 0.8 canonical document is unchanged, and compared by ``==``.
    _operations: frozenset[str] = frozenset(CONSUMER_OPERATIONS[:3])
    # Descriptions (C-D139) by the part they describe: ``operation:<name>``, ``list:<key>``,
    # ``filter:<name>``, ``related:<name>`` and ``field:<output>``.
    _descriptions: Mapping[str, str] = FrozenDict()

    def offers(self, operation: str) -> bool:
        if operation == "lists":
            return bool(self.lists)
        if operation == "events":
            return bool(self.events)
        return operation in self._operations

    def described(self, part: str) -> str | None:
        return self._descriptions.get(part)


# Schema 0.9 (Base 0.9 C18): consumer API definitions as authors write them, CONSUMER_API "Definition
# shape": what is exposed, which operations exist, what an object looks like, how it is found and
# filtered, and which changes are announced. Shape only: engine/model/consumer_expansion.py expands
# a definition into the internal form above (``ConsumerApiDefinition``), writing out every default,
# and the reference rules run on that. Optional parts left out stay out of the canonical document,
# so ``GET /model`` answers what the author wrote.

FieldRole = Literal["id", "code", "name", "active", "validFrom", "validTo"]
# The roles of the shared object, in output order: role fields come first, in this order (C-D140).
OBJECT_ROLES: tuple[str, ...] = ("id", "code", "name", "active", "validFrom", "validTo")
ParentFieldName = Literal["objectType", "id", "code", "name"]
def _omitted_false() -> Any:
    return Field(default=False, exclude_if=lambda value: value is False)


def _omitted_empty() -> Any:
    return Field(default=(), exclude_if=lambda value: not value)


class _Strict(ModelDefinition):
    model_config = ConfigDict(extra="forbid")


class _Described(_Strict):
    description: str | None = _omitted()


class FieldSpec(_Described):
    """An output field written out: its sources (``from``), default and role."""

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True, validate_by_name=True)

    from_: str | tuple[str, ...] | None = Field(default=None, alias="from", exclude_if=lambda value: value is None)
    default: Any | None = _omitted()
    role: FieldRole | None = _omitted()


def _field_form(value: Any) -> str:
    if isinstance(value, str):
        return "source"
    return "sources" if isinstance(value, (list, tuple)) else "spec"


# A field is one source, the sources in order (the first non-empty), or written out.
ObjectField = Annotated[
    Annotated[str, Tag("source")] | Annotated[tuple[str, ...], Tag("sources")] | Annotated[FieldSpec, Tag("spec")],
    Discriminator(_field_form),
]


class ParentSpec(_Strict):
    output: str = Field(min_length=1)
    fields: tuple[ParentFieldName, ...] = Field(min_length=1)


class RelatedSpec(_Described):
    """Related records under one output name, reached by a relation's ``key`` (outgoing) or
    ``reverseKey`` (incoming)."""

    via: str = Field(min_length=1)
    fields: Mapping[str, str] = Field(min_length=1)


class ObjectSpec(_Strict):
    fields: Mapping[str, ObjectField] = Field(min_length=1)
    parent: tuple[ParentFieldName, ...] | ParentSpec | None = _omitted()
    path: bool | str | None = _omitted()
    hierarchy: bool | str | None = _omitted()
    related: Mapping[str, RelatedSpec] = Field(default_factory=dict, exclude_if=lambda value: not value)


class AlsoMatchThrough(_Strict):
    related: str
    firstOf: tuple[ConsumerMatchRule, ...] = Field(min_length=1)
    preferTypes: tuple[str, ...] = _omitted_empty()


class Operation(_Described):
    pass


class XrefOperation(_Described):
    # Absent: XREF is offered and finds nothing until rules are declared.
    matchOn: tuple[ConsumerMatchRule, ...] | None = _omitted()
    alsoMatchThrough: tuple[AlsoMatchThrough, ...] = _omitted_empty()


class Within(_Strict):
    filter: str = Field(min_length=1)
    types: tuple[str, ...] | None = _omitted()


class ListSpec(_Described):
    of: str
    within: Within | None = _omitted()
    sortBy: str | None = _omitted()


class EventWatch(_Strict):
    """What makes an object ``updated`` for an event: output names and related blocks (C-D81)."""

    fields: tuple[str, ...] = _omitted_empty()
    related: tuple[str, ...] = _omitted_empty()


class EventSpec(_Strict):
    """An event a definition declares; without ``watch``, any change to the object's output counts."""

    key: str
    objectTypes: tuple[str, ...]
    changes: tuple[Literal["created", "updated", "deleted"], ...]
    watch: EventWatch | None = _omitted()


class EventsOperation(_Described):
    perType: bool = _omitted_false()
    custom: tuple[EventSpec, ...] = _omitted_empty()


class Operations(_Strict):
    objects: Operation | None = _omitted()
    xref: XrefOperation | None = _omitted()
    resolve: Operation | None = _omitted()
    lists: Mapping[str, ListSpec] | None = _omitted()
    events: EventsOperation | None = _omitted()


class FilterSpec(_Described):
    """A filter: exactly one of ``byType``, ``under``, ``linkedTo`` and ``onRelated``, with what it
    takes."""

    byType: bool | None = _omitted()
    under: tuple[str, ...] | None = _omitted()
    linkedTo: tuple[str, ...] | None = _omitted()
    through: tuple[str, ...] | None = _omitted()
    onRelated: str | None = _omitted()
    matchOn: tuple[str, ...] | None = _omitted()
    keepOnlyMatching: bool = _omitted_false()
    scoreOnlyMatching: bool = _omitted_false()
    crosswalk: bool = _omitted_false()


class ConsumerApiDocument(_Strict):
    """One consumer API definition in schema 0.9."""

    key: str
    name: str = Field(min_length=1)
    description: str | None = _omitted()
    contractVersion: int = Field(ge=1)
    exposes: tuple[str, ...] = Field(min_length=1)
    publicNames: Mapping[str, str] = Field(default_factory=dict, exclude_if=lambda value: not value)
    object: ObjectSpec
    operations: Operations
    filters: Mapping[str, FilterSpec] = Field(default_factory=dict, exclude_if=lambda value: not value)


class ProductDefinition(ModelDefinition):
    name: str
    description: str | None = None


class ModelReleaseDefinition(ModelDefinition):
    key: str
    name: str
    version: str


class EngineModel(ModelDefinition):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: Literal["0.5", "0.6", "0.7", "0.8", "0.9", "0.10"]
    release: ModelReleaseDefinition
    product: ProductDefinition
    attributeTypes: tuple[AttributeTypeDefinition, ...]
    objectTypes: tuple[ObjectTypeDefinition, ...]
    relationTypes: tuple[RelationTypeDefinition, ...]
    objectTypeRelations: tuple[ObjectTypeRelationDefinition, ...]
    applications: tuple[ApplicationDefinition, ...]
    # Schema 0.9 (C18); a document of schema 0.8 is read by ``LegacyEngineModel``
    # (engine/model/consumer_legacy.py). Omitted from the canonical document when absent, so earlier
    # hashes hold.
    consumerApis: tuple[ConsumerApiDocument, ...] | None = _omitted()
    # The internal definitions, expanded once (engine/model/consumer_definitions.py).
    _consumer_apis: Any = None

    _attribute_types_by_key: dict[str, AttributeTypeDefinition] = {}
    _object_types_by_key: dict[str, ObjectTypeDefinition] = {}
    _relation_types_by_key: dict[str, RelationTypeDefinition] = {}
    _bindings: dict[tuple[str, str, str], ObjectTypeRelationDefinition] = {}

    @model_validator(mode="after")
    def index_definitions(self) -> EngineModel:
        """Index top-level definitions by key and freeze the graph against later mutation.

        Cross-reference rules deliberately live outside this validator, in
        ``app.engine.model.validation``: they need to report the JSON pointer of the node that
        failed, which a Pydantic ``ValueError`` cannot carry. Use
        ``app.engine.model.compiler.compile_model`` or ``parse_model`` to obtain a model whose
        references are also known to resolve.
        """
        self._attribute_types_by_key = FrozenDict(_last_by_key(self.attributeTypes))
        self._object_types_by_key = FrozenDict(_last_by_key(self.objectTypes))
        self._relation_types_by_key = FrozenDict(_last_by_key(self.relationTypes))
        bindings: dict[tuple[str, str, str], ObjectTypeRelationDefinition] = {}
        for item in self.objectTypeRelations:
            key = (item.relationTypeKey, item.fromObjectTypeKey, item.toObjectTypeKey)
            bindings.setdefault(key, item)
        self._bindings = FrozenDict(bindings)

        freeze_model_graph(self)

        return self

    def attribute_type(self, key: str) -> AttributeTypeDefinition | None:
        return self._attribute_types_by_key.get(key)

    def object_type(self, key: str) -> ObjectTypeDefinition | None:
        return self._object_types_by_key.get(key)

    def relation_type(self, key: str) -> RelationTypeDefinition | None:
        return self._relation_types_by_key.get(key)

    def allowed_relation(
        self, relation_type_key: str, from_object_type_key: str, to_object_type_key: str
    ) -> ObjectTypeRelationDefinition | None:
        """The binding that permits this relation type from one object type to another."""
        return self._bindings.get((relation_type_key, from_object_type_key, to_object_type_key))

    def containment_relation_keys(self, object_type_key: str | None) -> frozenset[str]:
        """The relation types that place a record of this type under its parent."""
        definition = self.object_type(object_type_key) if object_type_key else None
        if definition is None:
            return frozenset()
        return frozenset((definition.behavior or {}).get("parentRelationTypeKeys", ()))


def freeze_model_graph(value: Any) -> Any:
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            object.__setattr__(value, field_name, freeze_model_graph(getattr(value, field_name)))
        if value.__pydantic_extra__:
            object.__setattr__(
                value,
                "__pydantic_extra__",
                freeze_model_graph(value.__pydantic_extra__),
            )
        return value
    if isinstance(value, Mapping):
        return FrozenDict({key: freeze_model_graph(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_model_graph(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_model_graph(item) for item in value)
    return value


def _last_by_key(items: Sequence[Any]) -> dict[str, Any]:
    """Index by key without rejecting duplicates; duplicate keys are a validation rule."""
    return {item.key: item for item in items}
