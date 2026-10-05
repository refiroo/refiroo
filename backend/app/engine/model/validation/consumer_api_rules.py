"""Reference rules for consumer API definitions (schema 0.8, Base 0.9 C1).

CONSUMER_API.md "Definition shape" and its rules: every type, attribute, relation route, ancestor,
projection and parameter a definition names resolves in the same release; a field's sources share
one output type (C-D19) and a default has that type; a match rule reads a field that is ``name``,
``id``, or ``searchable`` or ``unique`` (C-D20), and a ``contains`` weight a text field (0.9 C4);
output, parameter and list names do not collide. A
failure is refused at the pointer ``/consumerApis/<key>/…`` of the part that is wrong.
"""

import re
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, NoReturn

from ....common.json_pointer import pointer_segment
from ....models.schema import (
    AncestorParameter,
    ConsumerApiDefinition,
    ConsumerMatchRule,
    EngineModel,
    ObjectTypeDefinition,
    ProjectionParameter,
    RelatedParameter,
)
from ..consumer_contract import (
    BUILT_IN_FIELDS,
    OBJECT_ROLES,
    binding_types,
    exposed_types,
    field_value_type,
    projection_field_type,
    projection_targets,
    reference_value_type,
    source_type,
    split_ancestor_reference,
)
from ..diagnostics import ModelReferenceError
from ..traversal import ancestor_type_keys
from .fields import require_schema
from .index import ModelIndex

# The API key and list keys appear in URLs: lowercase letters, digits and single hyphens.
_URL_KEY = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Request parameters the endpoints own (CONSUMER_API "Rules the validator enforces").
RESERVED_PARAMETERS = frozenset(
    {
        "query",
        "expect",
        "pageSize",
        "cursor",
        "position",
        "from",
        "seek",
        "includeTotal",
        "publication",
        "asOf",
        "workspace",
        "ref",
        "id",
    }
)
# Output fields the shared object carries whatever the definition says.
RESERVED_OUTPUTS = frozenset({"objectType", "matchScore", "target"})
_VIA_SELF = "self"
_VIA_SHARED = "sharedProjection:"


def check(model: EngineModel, _index: ModelIndex) -> None:
    if model.consumerApis is None:
        return
    require_schema(model, "0.8", "/consumerApis", "consumerApis")
    seen: set[str] = set()
    for definition in model.consumerApis:
        base = f"/consumerApis/{pointer_segment(definition.key)}"
        if definition.key in seen:
            raise ModelReferenceError("DUPLICATE_KEY", base, f"Duplicate consumer API key '{definition.key}'")
        seen.add(definition.key)
        if not _URL_KEY.match(definition.key):
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{base}/key",
                f"Consumer API key '{definition.key}' must use lowercase letters, digits and hyphens",
            )
        _Definition(model, definition, base).check()


class _Definition:
    """One definition's checks, sharing its model, its exposed types and its pointer."""

    def __init__(self, model: EngineModel, definition: ConsumerApiDefinition, base: str) -> None:
        self.model = model
        self.definition = definition
        self.base = base
        self.types: list[ObjectTypeDefinition] = []

    def check(self) -> None:
        self._check_types()
        self.types = exposed_types(self.model, self.definition)
        outputs = self._check_object()
        self._check_projections(outputs)
        self._check_match()
        self._check_parameters()
        self._check_lists()

    def _fail(self, code: str, path: str, message: str) -> NoReturn:
        raise ModelReferenceError(code, f"{self.base}{path}", f"Consumer API '{self.definition.key}': {message}")

    def _check_types(self) -> None:
        public_names: dict[str, str] = {}
        for key, exposed in self.definition.objectTypes.items():
            path = f"/objectTypes/{pointer_segment(key)}"
            if self.model.object_type(key) is None:
                self._fail("UNKNOWN_OBJECT_TYPE", path, f"exposes unknown object type '{key}'")
            if exposed.publicName in public_names:
                self._fail(
                    "DUPLICATE_KEY",
                    f"{path}/publicName",
                    f"public name '{exposed.publicName}' is used by '{public_names[exposed.publicName]}' too",
                )
            public_names[exposed.publicName] = key

    def _check_object(self) -> set[str]:
        """The shared object's roles and attributes; returns the output names it uses."""
        shape = self.definition.object
        outputs: dict[str, str] = {}

        def claim(output: str, path: str) -> None:
            if output in RESERVED_OUTPUTS:
                self._fail("INVALID_MODEL", path, f"output name '{output}' is reserved")
            if output in outputs:
                self._fail("DUPLICATE_KEY", path, f"output name '{output}' is also used at {outputs[output]}")
            outputs[output] = path

        for role in OBJECT_ROLES:
            field = getattr(shape, role)
            if field is None:
                continue
            path = f"/object/{role}"
            claim(field.output, f"{path}/output")
            self._check_sources(field.source, field.default, path)
        # The identity is what get by ID looks up: the object ID, unique across the database (C-D24).
        # A former system's ID is published as an attribute field and found with XREF.
        if tuple(shape.id.source) != ("id",):
            self._fail(
                "INVALID_MODEL",
                "/object/id/source",
                "the identity's source is the object ID: ['id']; publish another identifier as an"
                " attribute field",
            )
        for name, attribute in shape.attributes.items():
            path = f"/object/attributes/{pointer_segment(name)}"
            claim(name, path)
            self._check_sources(attribute.source, attribute.default, path)
        if shape.parent is not None:
            claim(shape.parent.output, "/object/parent/output")
            if "code" in shape.parent.fields and shape.code is None:
                self._fail("INVALID_MODEL", "/object/parent/fields", "parent field 'code' needs an object 'code' role")
            if len(set(shape.parent.fields)) != len(shape.parent.fields):
                self._fail("DUPLICATE_KEY", "/object/parent/fields", "parent fields repeat")
        for role in ("path", "hierarchy"):
            output = getattr(shape, role)
            if output is not None:
                claim(output, f"/object/{role}")
        return set(outputs)

    def _check_sources(self, sources: Sequence[str], default: Any, path: str) -> None:
        for index, source in enumerate(sources):
            if field_value_type(self.model, self.types, source) is None:
                self._fail(
                    "INVALID_REFERENCE",
                    f"{path}/source/{index}",
                    f"source '{source}' is neither 'id', 'name' nor an attribute an exposed type binds",
                )
        value_type = source_type(self.model, self.types, sources)
        if value_type is None:
            kinds = sorted({str(field_value_type(self.model, self.types, item)) for item in sources})
            self._fail("INVALID_MODEL", f"{path}/source", f"sources have different value types {kinds}")
        if default is not None and not _matches_type(default, value_type):
            self._fail("INVALID_MODEL", f"{path}/default", f"default must be a {value_type} value")

    def _check_projections(self, outputs: set[str]) -> None:
        for name, projection in self.definition.projections.items():
            path = f"/projections/{pointer_segment(name)}"
            if name in outputs or name in RESERVED_OUTPUTS:
                self._fail("DUPLICATE_KEY", path, f"projection '{name}' collides with an output field")
            route = projection.from_
            if self.model.relation_type(route.relation) is None:
                self._fail("INVALID_REFERENCE", f"{path}/from/relation", f"unknown relation type '{route.relation}'")
            targets = projection_targets(self.model, self.definition, route.relation, route.direction)
            if not targets:
                self._fail(
                    "INVALID_REFERENCE",
                    f"{path}/from",
                    f"no exposed type has a {route.direction} binding of '{route.relation}'",
                )
            for output, source in projection.fields.items():
                if projection_field_type(self.model, self.definition, targets, source) is None:
                    self._fail(
                        "INVALID_REFERENCE",
                        f"{path}/fields/{pointer_segment(output)}",
                        f"field '{source}' is not 'id', 'name', an attribute of the related types,"
                        " 'ancestor:<type>.<field>' of an ancestor they can sit under, or 'objectType'"
                        " where the definition exposes every related type",
                    )

    def _check_match(self) -> None:
        match = self.definition.match
        if match is None:
            return
        for index, rule in enumerate(match.own):
            self._require_matchable(rule.field, self.types, f"/match/own/{index}/field")
            self._require_text_for_contains(rule, self.types, f"/match/own/{index}")
        for index, promoted in enumerate(match.promoted):
            path = f"/match/promoted/{index}"
            projection = self.definition.projections.get(promoted.projection)
            if projection is None:
                self._fail("INVALID_REFERENCE", f"{path}/projection", f"unknown projection '{promoted.projection}'")
            route = projection.from_
            targets = projection_targets(self.model, self.definition, route.relation, route.direction)
            for rule_index, rule in enumerate(promoted.firstMatch):
                self._require_matchable(rule.field, targets, f"{path}/firstMatch/{rule_index}/field")
                self._require_text_for_contains(rule, targets, f"{path}/firstMatch/{rule_index}")
            for type_index, key in enumerate(promoted.preferTargetTypes):
                if key not in self.definition.objectTypes:
                    self._fail(
                        "INVALID_REFERENCE",
                        f"{path}/preferTargetTypes/{type_index}",
                        f"preferred target type '{key}' is not exposed",
                    )

    def _require_matchable(self, field: str, types: Sequence[ObjectTypeDefinition], path: str) -> None:
        """``name``, ``id``, or an attribute of ``types`` that is searchable or unique (C-D20)."""
        if field in BUILT_IN_FIELDS:
            return
        definition = self.model.attribute_type(field)
        if definition is None or not binding_types(types, field):
            self._fail("INVALID_REFERENCE", path, f"field '{field}' is not 'id', 'name' or an attribute of those types")
        if not (definition.features.get("searchable") or definition.features.get("unique")):
            self._fail("INVALID_MODEL", path, f"field '{field}' is neither searchable nor unique")

    def _require_text_for_contains(
        self, rule: ConsumerMatchRule, types: Sequence[ObjectTypeDefinition], path: str
    ) -> None:
        """A ``contains`` weight reads a text field: ``name`` or a text attribute (0.9 C4). The object
        ID and typed values match exactly only, so a contains weight on them could never apply."""
        if rule.contains is None:
            return
        if rule.field != "id" and field_value_type(self.model, types, rule.field) == "text":
            return
        self._fail(
            "INVALID_MODEL",
            f"{path}/contains",
            f"field '{rule.field}' holds no text, so a 'contains' weight on it could never match",
        )

    def _check_parameters(self) -> None:
        for name, parameter in self.definition.parameters.items():
            path = f"/parameters/{pointer_segment(name)}"
            self._check_parameter_name(name, path)
            if isinstance(parameter, AncestorParameter):
                types = self._parameter_types(parameter.objectTypes, path)
                for type_index, key in enumerate(parameter.objectTypes):
                    if not any(key in ancestor_type_keys(self.model, item.key) for item in self.types):
                        self._fail(
                            "INVALID_REFERENCE",
                            f"{path}/objectTypes/{type_index}",
                            f"'{key}' is not an ancestor type of any exposed type",
                        )
                self._check_match_fields(parameter.matchFields, types, path)
            elif isinstance(parameter, RelatedParameter):
                types = self._parameter_types(parameter.objectTypes, path)
                self._check_match_fields(parameter.matchFields, types, path)
                for via_index, via in enumerate(parameter.via):
                    projection = via.removeprefix(_VIA_SHARED)
                    if via != _VIA_SELF and projection not in self.definition.projections:
                        self._fail(
                            "INVALID_REFERENCE",
                            f"{path}/via/{via_index}",
                            f"route '{via}' is not 'self', a projection or 'sharedProjection:<projection>'",
                        )
            elif isinstance(parameter, ProjectionParameter):
                projection = self.definition.projections.get(parameter.projection)
                if projection is None:
                    self._fail("INVALID_REFERENCE", f"{path}/projection", f"unknown projection '{parameter.projection}'")
                route = projection.from_
                targets = projection_targets(self.model, self.definition, route.relation, route.direction)
                for field_index, field in enumerate(parameter.matchFields):
                    if reference_value_type(self.model, targets, field) is None:
                        self._fail(
                            "INVALID_REFERENCE",
                            f"{path}/matchFields/{field_index}",
                            f"match field '{field}' is not a field of projection '{parameter.projection}'",
                        )
                if parameter.scoresFrom and not self._promotes(parameter.projection):
                    self._fail(
                        "INVALID_MODEL",
                        f"{path}/scoresFrom",
                        f"no match.promoted entry reads projection '{parameter.projection}', so"
                        " 'scoresFrom' could never limit a score",
                    )

    def _promotes(self, projection: str) -> bool:
        """A ``match.promoted`` entry reads ``projection`` (C-D45)."""
        match = self.definition.match
        return match is not None and any(item.projection == projection for item in match.promoted)

    def _check_parameter_name(self, name: str, path: str) -> None:
        if name in RESERVED_PARAMETERS or name.startswith("to."):
            self._fail("INVALID_MODEL", path, f"parameter name '{name}' is reserved")

    def _parameter_types(self, keys: Sequence[str], path: str) -> list[ObjectTypeDefinition]:
        types = []
        for index, key in enumerate(keys):
            item = self.model.object_type(key)
            if item is None:
                self._fail("UNKNOWN_OBJECT_TYPE", f"{path}/objectTypes/{index}", f"unknown object type '{key}'")
            types.append(item)
        return types

    def _check_match_fields(
        self, fields: Sequence[str], types: Sequence[ObjectTypeDefinition], path: str
    ) -> None:
        for index, field in enumerate(fields):
            if split_ancestor_reference(field) is not None:
                self._fail("INVALID_MODEL", f"{path}/matchFields/{index}", "an ancestor field is matched by an 'ancestor' parameter")
            self._require_matchable(field, types, f"{path}/matchFields/{index}")

    def _check_lists(self) -> None:
        keys: set[str] = set()
        for list_definition in self.definition.lists:
            path = f"/lists/{pointer_segment(list_definition.key)}"
            if list_definition.key in keys:
                self._fail("DUPLICATE_KEY", path, f"list '{list_definition.key}' is declared twice")
            keys.add(list_definition.key)
            if not _URL_KEY.match(list_definition.key):
                self._fail("INVALID_MODEL", f"{path}/key", "a list key uses lowercase letters, digits and hyphens")
            if list_definition.objectType not in self.definition.objectTypes:
                self._fail("INVALID_REFERENCE", f"{path}/objectType", f"type '{list_definition.objectType}' is not exposed")
            if list_definition.sortBy is not None:
                self._check_sort_by(list_definition.objectType, list_definition.sortBy, f"{path}/sortBy")
            parent = list_definition.parentParameter
            if parent is None:
                continue
            # A parent parameter may share a definition parameter's name, as CONSUMER_API's example
            # does for its parent list: on its list the name addresses the parent.
            self._check_parameter_name(parent.name, f"{path}/parentParameter/name")
            ancestors = ancestor_type_keys(self.model, list_definition.objectType)
            for index, key in enumerate(parent.objectTypes):
                if key not in ancestors:
                    self._fail(
                        "INVALID_REFERENCE",
                        f"{path}/parentParameter/objectTypes/{index}",
                        f"'{key}' cannot contain records of '{list_definition.objectType}'",
                    )


    def _check_sort_by(self, type_key: str, attribute: str, path: str) -> None:
        """A scalar attribute the list's type binds (C-D29)."""
        object_type = self.model.object_type(type_key)
        definition = self.model.attribute_type(attribute)
        if definition is None or object_type is None or not binding_types((object_type,), attribute):
            self._fail("INVALID_REFERENCE", path, f"'{attribute}' is not an attribute of '{type_key}'")
        if definition.valueType == "json":
            self._fail("INVALID_MODEL", path, f"'{attribute}' holds JSON and cannot be sorted")


def _matches_type(value: Any, value_type: str | None) -> bool:
    """Whether a default is a JSON value of the output type, as a write would accept it."""
    try:
        if value_type == "text":
            return isinstance(value, str)
        if value_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if value_type == "decimal":
            return not isinstance(value, bool) and Decimal(str(value)).is_finite()
        if value_type == "boolean":
            return isinstance(value, bool)
        if value_type == "date":
            date.fromisoformat(value)
            return True
        if value_type == "dateTime":
            datetime.fromisoformat(value)
            return True
    except (TypeError, ValueError, InvalidOperation):
        return False
    return value_type == "json"

