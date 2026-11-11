"""The operations that change a model mapping (0.11 X1, D107), as A5's kinds change a draft's profile.

Each kind checks its parameters against the mapping's two releases, changes the definition through
:class:`~..model.authoring.document.Document` and returns what it did; its inverse is
``restoreElements`` with the logged reversal, so undo puts back exactly what it changed (ADR-041).
An entry is named by its source element, never by position: a type entry by ``source``, its
attributes and relations by theirs. A kind names the entries it relies on (``type:<source type>``,
``valueMap:<name>``) and creates (``relation:<type>/<relation>``), so undoing a step a later one
relies on is refused with its dependants (D8).

A refusal names the parameter at fault: ``unknownElement`` (a release declares no such element, or
the mapping has no such entry), ``bindingNotAllowed`` (declared, but not bound to the mapped type,
not allowed at its end, not a containment of it), ``valueTypesNotConvertible`` (a pair of value
types no value crosses, ``values.conversion``), ``modelMismatch`` (a release of another model),
``inUse`` and ``invalidValue``.
"""

from collections.abc import Callable
from typing import Any

from ...errors import ApiError
from ..model.authoring.document import MODEL, Document, Refusal, apply_changes
from ..model.authoring.kinds import Applied, Params, check_names
from ..records.values import conversion, normalize_value, stored_json_value
from .sides import Side

# Entries in the definition's lists are named by their source element.
IDENTITIES: tuple[tuple[str, ...], ...] = (("source",),)
MISSING = ("create", "refuse")
DIRECTIONS = ("outgoing", "incoming")


class MappingContext:
    """The definition being changed and the two releases it is checked against. ``release`` gives
    a release's side by its public ID, with its model key, or ``None`` when no such release is
    installed; a re-pointing step changes the sides the next operations are checked against."""

    def __init__(
        self, document: Document, model_keys: tuple[str, str], release: Callable[[str], Side | None]
    ) -> None:
        self.document = document
        self.model_keys = model_keys
        self._release = release

    @property
    def data(self) -> dict[str, Any]:
        return self.document.data

    def side(self, name: str) -> Side:
        found = self._release(self.data[f"{name}ReleaseId"])
        assert found is not None
        return found

    @property
    def source(self) -> Side:
        return self.side("source")

    @property
    def target(self) -> Side:
        return self.side("target")

    def release(self, release_id: str) -> Side | None:
        return self._release(release_id)

    def entry(self, source_type: Any, field: str = "sourceType") -> dict[str, Any]:
        if not isinstance(source_type, str):
            raise Refusal(field, "invalidValue", f"'{field}' is a source type's key")
        found = self.document.find(["types", {"source": source_type}])
        if found is None:
            raise Refusal(
                field,
                "unknownElement",
                f"The mapping does not map type '{source_type}'; map it first",
            )
        return found


KindFunction = Callable[[MappingContext, dict[str, Any]], Applied]
KINDS: dict[str, KindFunction] = {}
# The parameter names each kind allows: the one place they are declared, checked before a kind runs
# and described in the OpenAPI document.
PARAMETERS: dict[str, tuple[str, ...]] = {}
# Kinds a request may not send: the server writes them (undo).
INTERNAL_KINDS = frozenset({"restoreElements"})


def kind(name: str, *, params: tuple[str, ...]) -> Callable[[KindFunction], KindFunction]:
    """Register an operation kind with the parameter names it allows; its docstring describes it."""

    def register(function: KindFunction) -> KindFunction:
        KINDS[name] = function
        PARAMETERS[name] = params
        return function

    return register


def apply_operation(context: MappingContext, operation: dict[str, Any]) -> Applied:
    name = operation.get("kind")
    if not isinstance(name, str) or name not in KINDS:
        raise Refusal("kind", "unknownKind", f"Unknown operation kind '{name}'")
    context.document.log.clear()
    parameters = {key: value for key, value in operation.items() if key != "kind"}
    check_names(parameters, PARAMETERS[name])
    applied = KINDS[name](context, parameters)
    if name not in INTERNAL_KINDS:
        applied.inverse = {
            "kind": "restoreElements",
            "undoes": operation,
            "changes": context.document.reversal(),
        }
    return applied


def _type(source_type: str) -> str:
    return f"type:{source_type}"


def _path(source_type: str, *rest: Any) -> list[Any]:
    return ["types", {"source": source_type}, *rest]


def _replace(document: Document, path: list[Any], item: dict[str, Any]) -> bool:
    """``item`` in the list at ``path`` in place of the item of its source; ``True`` when new."""
    items = document.find(path) or []
    position = next(
        (i for i, other in enumerate(items) if other.get("source") == item["source"]), None
    )
    if position is not None:
        if items[position] == item:
            return False
        document.remove(path, {"source": item["source"]})
    document.insert(path, item, position)
    return position is None


def _missing(raw: Any, field: str) -> str | None:
    if raw is not None and raw not in MISSING:
        raise Refusal(field, "invalidValue", "'missing' is 'create' or 'refuse'")
    return raw


# --- types -----------------------------------------------------------------------------------------


@kind("mapType", params=("sourceType", "targetType"))
def map_type(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Map a source type to a target type; mapping it to another target type clears what was mapped under it."""
    params = Params(raw)
    source_type, target_type = params.text("sourceType"), params.text("targetType")
    if not context.source.has_type(source_type):
        raise Refusal(
            "sourceType", "unknownElement", f"The source release has no type '{source_type}'"
        )
    if not context.target.has_type(target_type):
        raise Refusal(
            "targetType", "unknownElement", f"The target release has no type '{target_type}'"
        )
    document = context.document
    entry = document.find(_path(source_type))
    if entry is None:
        empty = {
            "source": source_type,
            "target": target_type,
            "attributes": [],
            "relations": [],
            "defaults": {},
        }
        document.insert(["types"], empty)
        return Applied(dict(raw), {}, created={_type(source_type)}, named={_type(source_type)})
    if entry["target"] != target_type:
        # What named the old target means nothing for the new one.
        document.set(_path(source_type), "target", target_type)
        for name, empty in (("attributes", []), ("relations", []), ("defaults", {})):
            document.set(_path(source_type), name, empty)
        for name in ("parent", "match"):
            document.set(_path(source_type), name, None)
    return Applied(dict(raw), {}, named={_type(source_type)})


@kind("unmapType", params=("sourceType",))
def unmap_type(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Take a source type out of the mapping, with everything mapped under it."""
    params = Params(raw)
    source_type = params.text("sourceType")
    context.entry(source_type)
    context.document.remove(["types"], {"source": source_type})
    return Applied(dict(raw), {}, named={_type(source_type)})


# --- attributes ------------------------------------------------------------------------------------


@kind("mapAttribute", params=("sourceType", "attribute", "target", "ignore", "valueMap"))
def map_attribute(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Map a source attribute of a mapped type to a target attribute (optionally through a value map), or mark it ignored."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    attribute = params.text("attribute")
    source, target = context.source, context.target
    if not source.has_attribute(attribute):
        raise Refusal(
            "attribute", "unknownElement", f"The source release has no attribute '{attribute}'"
        )
    if not source.binding(source_type, attribute):
        raise Refusal(
            "attribute", "bindingNotAllowed", f"Type '{source_type}' does not bind '{attribute}'"
        )
    ignore = params.optional("ignore", bool)
    target_attribute = params.optional("target", str)
    value_map = params.optional("valueMap", str)
    named = {_type(source_type)}
    if ignore:
        if target_attribute is not None or value_map is not None:
            raise Refusal(
                "ignore", "invalidValue", "An ignored attribute names no target and no value map"
            )
        item: dict[str, Any] = {"source": attribute, "ignore": True}
    else:
        if target_attribute is None:
            raise Refusal("target", "missingParameter", "'target' or 'ignore: true' is required")
        if not target.has_attribute(target_attribute):
            raise Refusal(
                "target",
                "unknownElement",
                f"The target release has no attribute '{target_attribute}'",
            )
        if not target.binding(entry["target"], target_attribute):
            raise Refusal(
                "target",
                "bindingNotAllowed",
                f"Type '{entry['target']}' does not bind '{target_attribute}'",
            )
        from_type, to_type = source.value_type(attribute), target.value_type(target_attribute)
        if conversion(from_type, to_type) == "never":
            raise Refusal(
                "target", "valueTypesNotConvertible", f"No {from_type} value converts to {to_type}"
            )
        item = {"source": attribute, "target": target_attribute}
        if value_map is not None:
            if value_map not in (context.data.get("valueMaps") or {}):
                raise Refusal(
                    "valueMap", "unknownElement", f"The mapping has no value map '{value_map}'"
                )
            item["valueMap"] = value_map
            named.add(f"valueMap:{value_map}")
    _replace(context.document, _path(source_type, "attributes"), item)
    return Applied(dict(raw), {}, named=named)


@kind("unmapAttribute", params=("sourceType", "attribute"))
def unmap_attribute(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Take a source attribute's mapping out of a mapped type."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    attribute = params.text("attribute")
    if not any(item.get("source") == attribute for item in entry.get("attributes") or []):
        raise Refusal(
            "attribute",
            "unknownElement",
            f"The mapping does not map '{attribute}' of '{source_type}'",
        )
    context.document.remove(_path(source_type, "attributes"), {"source": attribute})
    return Applied(dict(raw), {}, named={_type(source_type)})


@kind("setDefault", params=("sourceType", "attribute", "value"))
def set_default(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Set the value a target attribute takes when the source record gives none; `null` removes the default."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    attribute = params.text("attribute")
    target = context.target
    definition = target.model.attribute_type(attribute)
    if definition is None:
        raise Refusal(
            "attribute", "unknownElement", f"The target release has no attribute '{attribute}'"
        )
    if not target.binding(entry["target"], attribute):
        raise Refusal(
            "attribute",
            "bindingNotAllowed",
            f"Type '{entry['target']}' does not bind '{attribute}'",
        )
    value = raw.get("value")
    if value is not None:
        try:
            value = stored_json_value(normalize_value(definition, value))
        except (ApiError, TypeError, ValueError) as exc:
            raise Refusal("value", "invalidValue", f"Not a {definition.valueType} value") from exc
    if "defaults" not in entry:
        context.document.set(_path(source_type), "defaults", {})
    context.document.set(_path(source_type, "defaults"), attribute, value)
    return Applied(dict(raw), {}, named={_type(source_type)})


@kind("setValueMap", params=("name", "values"))
def set_value_map(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Set a value map: source values read as others before conversion; `null` removes it."""
    params = Params(raw)
    name = params.text("name")
    values = raw.get("values")
    if values is not None and (
        not isinstance(values, dict) or any(isinstance(v, (dict, list)) for v in values.values())
    ):
        raise Refusal("values", "invalidValue", "'values' maps source values to single values")
    maps = context.data.get("valueMaps") or {}
    if "valueMaps" not in context.data:
        context.document.set([], "valueMaps", {})
    if values is None:
        if name not in maps:
            raise Refusal("name", "unknownElement", f"The mapping has no value map '{name}'")
        users = [
            entry["source"]
            for entry in context.data.get("types") or []
            if any(item.get("valueMap") == name for item in entry.get("attributes") or [])
        ]
        if users:
            raise Refusal("name", "inUse", f"Value map '{name}' is used by {', '.join(users)}")
    created = {f"valueMap:{name}"} if name not in maps else set()
    context.document.set(["valueMaps"], name, values)
    return Applied(dict(raw), {}, created=created, named={f"valueMap:{name}"})


# --- placement and matching ------------------------------------------------------------------------


@kind("setParent", params=("sourceType", "parent"))
def set_parent(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Set where a record stands in the target: under the target record of its source parent (`{"from": "source"}`) or under one record named by `objectTypeKey` and `value`, through `relationTypeKey` when the target type has several containments; `null` at the top."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    parent = raw.get("parent")
    if parent is not None:
        if not isinstance(parent, dict):
            raise Refusal("parent", "invalidValue", "'parent' is an object or null")
        unknown = set(parent) - {"from", "objectTypeKey", "value", "relationTypeKey", "missing"}
        if unknown:
            first = min(unknown)
            raise Refusal(f"parent/{first}", "unknownParameter", f"Unknown parameter '{first}'")
        own = context.target.parents(entry["target"])
        if (parent.get("from") == "source") == ("objectTypeKey" in parent):
            raise Refusal(
                "parent", "invalidValue", "A parent is {from: 'source'} or {objectTypeKey, value}"
            )
        if "objectTypeKey" in parent:
            if parent["objectTypeKey"] not in {p for _, p in own}:
                raise Refusal(
                    "parent/objectTypeKey",
                    "bindingNotAllowed",
                    f"'{entry['target']}' cannot stand under '{parent['objectTypeKey']}'",
                )
            if not isinstance(parent.get("value"), str) or not parent["value"].strip():
                raise Refusal("parent/value", "invalidValue", "'value' is the parent record's name")
        elif "value" in parent:
            raise Refusal("parent/value", "invalidValue", "A parent from the source names no value")
        relation = parent.get("relationTypeKey")
        if relation is not None and relation not in {r for r, _ in own}:
            raise Refusal(
                "parent/relationTypeKey",
                "bindingNotAllowed",
                f"'{relation}' does not contain '{entry['target']}'",
            )
        _missing(parent.get("missing"), "parent/missing")
        parent = {k: v for k, v in parent.items() if v is not None}
    context.document.set(_path(source_type), "parent", parent)
    return Applied(dict(raw), {}, named={_type(source_type)})


@kind("setMatch", params=("sourceType", "match"))
def set_match(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Set how a target record not found by its counterpart or origin is matched: by a unique attribute of the target type, by name, or not at all (`null`)."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    match = raw.get("match")
    if match is not None:
        if match == {"field": "name"}:
            pass
        elif isinstance(match, dict) and set(match) == {"attributeTypeKey"}:
            key = match["attributeTypeKey"]
            if not context.target.has_attribute(key):
                raise Refusal(
                    "match/attributeTypeKey",
                    "unknownElement",
                    f"The target release has no attribute '{key}'",
                )
            if not (context.target.binding(entry["target"], key) and context.target.unique(key)):
                raise Refusal(
                    "match/attributeTypeKey",
                    "bindingNotAllowed",
                    f"Type '{entry['target']}' binds no unique '{key}'",
                )
        else:
            raise Refusal(
                "match", "invalidValue", "A match is {attributeTypeKey}, {field: 'name'} or null"
            )
    context.document.set(_path(source_type), "match", match)
    return Applied(dict(raw), {}, named={_type(source_type)})


@kind("setMissing", params=("sourceType", "relation", "missing"))
def set_missing(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Set what happens when a record that a relationship (`relation`) or the parent names is not in the target: `create` it by name or `refuse` the record; `null` restores the default."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    missing = _missing(raw.get("missing"), "missing")
    relation = params.optional("relation", str)
    if relation is None:
        if not entry.get("parent"):
            raise Refusal(
                "sourceType", "unknownElement", f"The mapping sets no parent for '{source_type}'"
            )
        context.document.set(_path(source_type, "parent"), "missing", missing)
        return Applied(dict(raw), {}, named={_type(source_type)})
    if not any(item.get("source") == relation for item in entry.get("relations") or []):
        raise Refusal(
            "relation",
            "unknownElement",
            f"The mapping does not map '{relation}' of '{source_type}'",
        )
    context.document.set(_path(source_type, "relations", {"source": relation}), "missing", missing)
    return Applied(dict(raw), {}, named={_type(source_type), f"relation:{source_type}/{relation}"})


# --- relations -------------------------------------------------------------------------------------


@kind(
    "mapRelation", params=("sourceType", "relation", "target", "direction", "attributes", "missing")
)
def map_relation(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Carry a relationship the source type holds at its `from` end as a target relation, read from the mapped type's `direction` end, with its relation attributes."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    relation, target_relation = params.text("relation"), params.text("target")
    direction = params.optional("direction", str, "outgoing")
    if direction not in DIRECTIONS:
        raise Refusal("direction", "invalidValue", "'direction' is 'outgoing' or 'incoming'")
    source, target = context.source, context.target
    if not source.has_relation(relation):
        raise Refusal(
            "relation", "unknownElement", f"The source release has no relation '{relation}'"
        )
    source_ends = source.relation_ends(relation, source_type, "outgoing")
    if not source_ends or relation in source.containment:
        raise Refusal(
            "relation",
            "bindingNotAllowed",
            f"'{relation}' is not a relationship from '{source_type}'",
        )
    if not target.has_relation(target_relation):
        raise Refusal(
            "target", "unknownElement", f"The target release has no relation '{target_relation}'"
        )
    target_ends = target.relation_ends(target_relation, entry["target"], direction)
    if not target_ends or target_relation in target.containment:
        raise Refusal(
            "target",
            "bindingNotAllowed",
            f"'{target_relation}' is not allowed with '{entry['target']}' at its {direction} end",
        )
    item: dict[str, Any] = {"source": relation, "target": target_relation, "direction": direction}
    pairs = params.optional("attributes", list, [])
    if pairs:
        offered = {a for end in source_ends for a in end.attributeTypeKeys}
        allowed = {a for end in target_ends for a in end.attributeTypeKeys}
        checked = []
        for index, pair in enumerate(pairs):
            if not isinstance(pair, dict) or set(pair) != {"source", "target"}:
                raise Refusal(
                    f"attributes/{index}",
                    "invalidValue",
                    "A relation attribute is {source, target}",
                )
            if pair["source"] not in offered:
                raise Refusal(
                    f"attributes/{index}/source",
                    "bindingNotAllowed",
                    f"'{relation}' carries no '{pair['source']}'",
                )
            if pair["target"] not in allowed:
                raise Refusal(
                    f"attributes/{index}/target",
                    "bindingNotAllowed",
                    f"'{target_relation}' carries no '{pair['target']}'",
                )
            if (
                conversion(source.value_type(pair["source"]), target.value_type(pair["target"]))
                == "never"
            ):
                raise Refusal(
                    f"attributes/{index}/target",
                    "valueTypesNotConvertible",
                    "No value of the source attribute converts",
                )
            checked.append(dict(pair))
        item["attributes"] = checked
    missing = _missing(raw.get("missing"), "missing")
    if missing is not None:
        item["missing"] = missing
    created = _replace(context.document, _path(source_type, "relations"), item)
    atom = f"relation:{source_type}/{relation}"
    return Applied(
        dict(raw), {}, created={atom} if created else set(), named={_type(source_type), atom}
    )


@kind("unmapRelation", params=("sourceType", "relation"))
def unmap_relation(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Take a mapped relationship out of a mapped type."""
    params = Params(raw)
    source_type = params.text("sourceType")
    entry = context.entry(source_type)
    relation = params.text("relation")
    if not any(item.get("source") == relation for item in entry.get("relations") or []):
        raise Refusal(
            "relation",
            "unknownElement",
            f"The mapping does not map '{relation}' of '{source_type}'",
        )
    context.document.remove(_path(source_type, "relations"), {"source": relation})
    return Applied(dict(raw), {}, named={_type(source_type), f"relation:{source_type}/{relation}"})


# --- releases --------------------------------------------------------------------------------------


@kind("setReleases", params=("sourceReleaseId", "targetReleaseId"))
def set_releases(context: MappingContext, raw: dict[str, Any]) -> Applied:
    """Set the releases the mapping is checked against, each of its own model; what no longer resolves is reported in the mapping's problems, never removed."""
    params = Params(raw)
    given = {name: params.optional(f"{name}ReleaseId", str) for name in ("source", "target")}
    if not any(given.values()):
        raise Refusal("targetReleaseId", "missingParameter", "Name a source or a target release")
    for (name, release_id), model_key in zip(given.items(), context.model_keys, strict=True):
        if release_id is None:
            continue
        side = context.release(release_id)
        if side is None:
            raise Refusal(
                f"{name}ReleaseId", "unknownElement", f"No release '{release_id}' is installed"
            )
        if side.model_key != model_key:
            raise Refusal(
                f"{name}ReleaseId",
                "modelMismatch",
                f"Release '{release_id}' is of model '{side.model_key}', not '{model_key}'",
            )
        context.document.set([], f"{name}ReleaseId", release_id)
    return Applied(dict(raw), {}, named={"releases"})


@kind("restoreElements", params=("undoes", "changes"))
def restore_elements(context: MappingContext, raw: dict[str, Any]) -> Applied:
    changes, undoes = raw.get("changes"), raw.get("undoes")
    if not isinstance(changes, list) or not isinstance(undoes, dict):
        raise Refusal("changes", "invalidValue", "'changes' are the logged changes of an operation")
    try:
        apply_changes({MODEL: context.document}, changes)
    except LookupError as exc:
        raise Refusal(
            "changes", "conflict", f"The mapping no longer holds what this restores: {exc}"
        ) from exc
    return Applied(dict(raw), dict(undoes))
