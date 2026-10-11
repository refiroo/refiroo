"""Where a model document names its elements (0.10 A2): the reference index.

Keys of different kinds may be equal (a view and a panel, an attribute and a column), so a reference is
found by the document's structure, never by matching text. :func:`slots` walks every place that holds
a key, with the kind of element it names:

- ``objectType``, ``attributeType``, ``relationType`` (a relation type's ``key``), ``application``
  and ``view``: a string holding that key;
- ``objectTypeMapKey``: a member name that is an object type key (a tree's ``childSort``);
- ``field``: a field reference read against ``types``, the object types it is a field of: a built-in
  field or attribute key, ``ancestor:<type>`` or ``ancestor:<type>.<field>``, or ``related:<key>``
  and ``related:<key>.<field>`` (a relation type's key or reverse key, ADR-029, 0.9 K5); a sort may
  lead with ``-``.

``setKey`` rewrites what the slots name; removals find what names a removed element; D8 reads which
elements an operation names. Consumer API definitions are not walked: they name elements in their own
grammar, and an element they name is not re-keyed (D29); :func:`consumer_api_pointer` finds such a
name.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ....models.schema import DETAIL_FIELD_KEYS as BUILT_IN_FIELDS
from .document import Document, Path, identity


@dataclass
class Slot:
    """One place holding a key: the member ``field`` of the object at ``path`` (a string, or with
    ``index`` a string in a list there; ``member`` when the key is a member name of that object)."""

    path: Path
    field: str
    kind: str
    index: int | None = None
    types: tuple[str, ...] = ()
    member: str | None = None


def slots(data: dict[str, Any]) -> Iterator[Slot]:
    yield from _object_types(data)
    yield from _bindings(data)
    for application in _list(data, "applications"):
        app = ["applications", identity(application)]
        yield Slot(app, "key", "application")
        if isinstance(application.get("defaultView"), str):
            yield Slot(app, "defaultView", "view")
        yield from _strings(app, application, "objectTypeKeys", "objectType")
        for view in _list(application, "views"):
            yield from _view(app + ["views", identity(view)], view)
        for detail in _list(application, "details"):
            yield from _detail(app + ["details", identity(detail)], detail, data)
        navigation = application.get("navigation")
        if isinstance(navigation, dict):
            for group in _list(navigation, "groups"):
                path = app + ["navigation", "groups", identity(group)]
                yield from _strings(path, group, "collections", "objectType")


def _object_types(data: dict[str, Any]) -> Iterator[Slot]:
    for attribute_type in _list(data, "attributeTypes"):
        yield Slot(["attributeTypes", identity(attribute_type)], "key", "attributeType")
    for relation_type in _list(data, "relationTypes"):
        yield Slot(["relationTypes", identity(relation_type)], "key", "relationType")
    for object_type in _list(data, "objectTypes"):
        path = ["objectTypes", identity(object_type)]
        yield Slot(path, "key", "objectType")
        for binding in _list(object_type, "attributes"):
            yield Slot(path + ["attributes", identity(binding)], "attributeTypeKey", "attributeType")
        if isinstance(object_type.get("displayAttributeTypeKey"), str):
            yield Slot(path, "displayAttributeTypeKey", "attributeType")
        validation = object_type.get("validation")
        if isinstance(validation, dict):
            yield from _strings(path + ["validation"], validation, "atLeastOneOf", "attributeType")
        period = object_type.get("effectivePeriod")
        if isinstance(period, dict):
            for field in ("startAttributeTypeKey", "endAttributeTypeKey"):
                if isinstance(period.get(field), str):
                    yield Slot(path + ["effectivePeriod"], field, "attributeType")
        behavior = object_type.get("behavior")
        if isinstance(behavior, dict):
            yield from _strings(path + ["behavior"], behavior, "parentRelationTypeKeys", "relationType")


def _bindings(data: dict[str, Any]) -> Iterator[Slot]:
    for binding in _list(data, "objectTypeRelations"):
        path = ["objectTypeRelations", identity(binding)]
        yield Slot(path, "relationTypeKey", "relationType")
        yield Slot(path, "fromObjectTypeKey", "objectType")
        yield Slot(path, "toObjectTypeKey", "objectType")
        yield from _strings(path, binding, "attributeTypeKeys", "attributeType")
        features = binding.get("features")
        if isinstance(features, dict):
            if isinstance(features.get("uniqueToAncestorTypeKey"), str):
                yield Slot(path + ["features"], "uniqueToAncestorTypeKey", "objectType")
            condition = features.get("uniqueWhenToAttributeEquals")
            if isinstance(condition, dict) and isinstance(condition.get("attributeTypeKey"), str):
                yield Slot(
                    path + ["features", "uniqueWhenToAttributeEquals"], "attributeTypeKey", "attributeType"
                )
        candidates = binding.get("candidates")
        if isinstance(candidates, dict):
            for end, side in (("from", "fromObjectTypeKey"), ("to", "toObjectTypeKey")):
                for position, criterion in enumerate(_list(candidates, end)):
                    if isinstance(criterion, dict) and isinstance(criterion.get("field"), str):
                        yield Slot(
                            path + ["candidates", end, position],
                            "field",
                            "field",
                            types=(binding.get(side),),
                        )


def _view(path: Path, view: dict[str, Any]) -> Iterator[Slot]:
    config = view.get("config") if isinstance(view.get("config"), dict) else {}
    yield Slot(path, "key", "view")
    kind = view.get("type")
    if kind == "table":
        source = view.get("objectTypeKey")
        yield Slot(path, "objectTypeKey", "objectType")
        for name in ("columns", "filterFields", "sortFields"):
            yield from _fields(path + ["config"], config, name, (source,))
        yield from _field(path + ["config"], config, "defaultSort", (source,))
    elif kind == "mappingGrid":
        yield Slot(path + ["config"], "relationTypeKey", "relationType")
        yield Slot(path + ["config"], "fromObjectTypeKey", "objectType")
        yield Slot(path + ["config"], "toObjectTypeKey", "objectType")
        outgoing = config.get("direction") == "outgoing"
        source = config.get("fromObjectTypeKey") if outgoing else config.get("toObjectTypeKey")
        target = config.get("toObjectTypeKey") if outgoing else config.get("fromObjectTypeKey")
        yield from _fields(path + ["config"], config, "sourceColumns", (source,))
        yield from _fields(path + ["config"], config, "targetDisplayColumns", (target,))
        yield from _fields(path + ["config"], config, "candidateSearchFields", (target,))
    elif kind == "relationMatrix":
        yield Slot(path + ["config"], "relationTypeKey", "relationType")
        for name in ("rowObjectTypeKey", "columnObjectTypeKey", "cellObjectTypeKey"):
            yield Slot(path + ["config"], name, "objectType")
        row, column, cell = (config.get(name) for name in ("rowObjectTypeKey", "columnObjectTypeKey", "cellObjectTypeKey"))
        yield from _fields(path + ["config"], config, "rowColumns", (row,))
        yield from _field(path + ["config"], config, "columnLabelField", (column,))
        yield from _fields(path + ["config"], config, "cellFields", (cell,))
        yield from _fields(path + ["config"], config, "searchFields", (row,))
    elif kind == "tree":
        yield from _strings(path + ["config"], config, "rootObjectTypeKeys", "objectType")
        yield from _strings(path + ["config"], config, "objectTypeKeys", "objectType")
        nodes = tuple(config.get("objectTypeKeys") or ())
        for name in ("labelField", "secondaryField", "availabilityField"):
            yield from _field(path + ["config"], config, name, nodes)
        child_sort = config.get("childSort")
        if isinstance(child_sort, dict):
            for type_key in child_sort:
                yield Slot(path + ["config", "childSort"], type_key, "objectTypeMapKey", member=type_key)
                yield from _field(path + ["config", "childSort"], child_sort, type_key, (type_key,))


def _detail(path: Path, detail: dict[str, Any], data: dict[str, Any]) -> Iterator[Slot]:
    source = detail.get("objectTypeKey")
    yield Slot(path, "objectTypeKey", "objectType")
    header = detail.get("header")
    if isinstance(header, dict):
        for name in ("titleField", "subtitleField"):
            yield from _field(path + ["header"], header, name, (source,))
    for panel in _list(detail, "panels"):
        panel_path = path + ["panels", identity(panel)]
        config = panel.get("config") if isinstance(panel.get("config"), dict) else {}
        kind = panel.get("type")
        if kind == "attributes":
            yield from _fields(panel_path + ["config"], config, "fields", (source,))
        elif kind == "children":
            yield from _strings(panel_path + ["config"], config, "objectTypeKeys", "objectType")
            children = tuple(config.get("objectTypeKeys") or ())
            yield from _fields(panel_path + ["config"], config, "columns", children)
        elif kind == "relations":
            yield from _strings(panel_path + ["config"], config, "relationTypeKeys", "relationType")
            far = related_types(data, source, config.get("relationTypeKeys") or (), config.get("direction", "both"))
            for name in ("columns", "sortFields"):
                yield from _fields(panel_path + ["config"], config, name, far)
            yield from _field(panel_path + ["config"], config, "defaultSort", far)
        elif kind == "table":
            yield Slot(panel_path + ["config"], "objectTypeKey", "objectType")
            yield from _fields(panel_path + ["config"], config, "columns", (config.get("objectTypeKey"),))


def related_types(data: dict[str, Any], source: Any, relation_keys: Any, direction: str) -> tuple[str, ...]:
    """The types at the far end of ``source``'s bindings of ``relation_keys`` in ``direction``."""
    result: list[str] = []
    for binding in _list(data, "objectTypeRelations"):
        if binding.get("relationTypeKey") not in relation_keys:
            continue
        if direction in ("outgoing", "both") and binding.get("fromObjectTypeKey") == source:
            result.append(binding.get("toObjectTypeKey"))
        if direction in ("incoming", "both") and binding.get("toObjectTypeKey") == source:
            result.append(binding.get("fromObjectTypeKey"))
    return tuple(dict.fromkeys(result))


def _list(node: Any, name: str) -> list[Any]:
    value = node.get(name) if isinstance(node, dict) else None
    return value if isinstance(value, list) else []


def _strings(path: Path, node: dict[str, Any], name: str, kind: str) -> Iterator[Slot]:
    for position, value in enumerate(_list(node, name)):
        if isinstance(value, str):
            yield Slot(path, name, kind, index=position)


def _fields(path: Path, node: dict[str, Any], name: str, types: tuple[Any, ...]) -> Iterator[Slot]:
    for position, value in enumerate(_list(node, name)):
        if isinstance(value, str):
            yield Slot(path, name, "field", index=position, types=_keys(types))


def _field(path: Path, node: dict[str, Any], name: str, types: tuple[Any, ...]) -> Iterator[Slot]:
    if isinstance(node.get(name), str):
        yield Slot(path, name, "field", types=_keys(types))


def _keys(types: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(key for key in types if isinstance(key, str))


# --- field references ---


@dataclass(frozen=True)
class FieldRef:
    """A parsed field reference: ``plain`` (a built-in or attribute key), or ``ancestor`` with
    ``type_key``, or ``related`` with ``relation_key``; either with an inner ``field``."""

    kind: str
    name: str = ""
    type_key: str = ""
    relation_key: str = ""
    field: FieldRef | None = None
    descending: bool = False


def parse_field(text: str, known_types: set[str], relation_keys: set[str]) -> FieldRef:
    descending = text.startswith("-")
    body = text[1:] if descending else text
    if body.startswith("ancestor:"):
        head, inner = _split_known(body.removeprefix("ancestor:"), known_types)
        return FieldRef(
            "ancestor",
            type_key=head,
            field=parse_field(inner, known_types, relation_keys) if inner else None,
            descending=descending,
        )
    if body.startswith("related:"):
        head, inner = _split_known(body.removeprefix("related:"), relation_keys)
        return FieldRef(
            "related",
            relation_key=head,
            field=parse_field(inner, known_types, relation_keys) if inner else None,
            descending=descending,
        )
    return FieldRef("plain", name=body, descending=descending)


def _split_known(text: str, keys: set[str]) -> tuple[str, str]:
    """``key`` and the rest after its dot: the whole text when it is a key, otherwise the longest
    key it starts with followed by a dot (keys may contain dots), otherwise its first dot."""
    if text in keys:
        return text, ""
    matches = [key for key in keys if text.startswith(f"{key}.")]
    if matches:
        key = max(matches, key=len)
        return key, text[len(key) + 1 :]
    head, _, rest = text.partition(".")
    return head, rest


def format_field(ref: FieldRef) -> str:
    sign = "-" if ref.descending else ""
    if ref.kind == "plain":
        return f"{sign}{ref.name}"
    head = f"ancestor:{ref.type_key}" if ref.kind == "ancestor" else f"related:{ref.relation_key}"
    return f"{sign}{head}" + (f".{format_field(ref.field)}" if ref.field else "")


def field_names(ref: FieldRef) -> Iterator[tuple[str, str]]:
    """The elements a field reference names, as ``(kind, key)``: a plain non-built-in name is an
    attribute; a related key a relation type key or reverse key (``relationKey``)."""
    if ref.kind == "plain":
        if ref.name not in BUILT_IN_FIELDS:
            yield ("attributeType", ref.name)
    elif ref.kind == "ancestor":
        yield ("objectType", ref.type_key)
    else:
        yield ("relationKey", ref.relation_key)
    if ref.field is not None:
        yield from field_names(ref.field)


def rename_field(ref: FieldRef, kind: str, old: str, new: str) -> FieldRef:
    inner = rename_field(ref.field, kind, old, new) if ref.field else None
    if ref.kind == "plain" and kind == "attributeType" and ref.name == old:
        return FieldRef("plain", name=new, descending=ref.descending)
    if ref.kind == "ancestor":
        type_key = new if kind == "objectType" and ref.type_key == old else ref.type_key
        return FieldRef("ancestor", type_key=type_key, field=inner, descending=ref.descending)
    if ref.kind == "related":
        relation = new if kind == "relationKey" and ref.relation_key == old else ref.relation_key
        return FieldRef("related", relation_key=relation, field=inner, descending=ref.descending)
    return ref


def known_keys(data: dict[str, Any]) -> tuple[set[str], set[str]]:
    """The document's object type keys, and its relation types' keys and reverse keys."""
    types = {item.get("key") for item in _list(data, "objectTypes") if isinstance(item, dict)}
    relations: set[str] = set()
    for item in _list(data, "relationTypes"):
        if isinstance(item, dict):
            relations |= {item.get("key"), item.get("reverseKey")}
    return {key for key in types if isinstance(key, str)}, {key for key in relations if isinstance(key, str)}


def slot_value(data: dict[str, Any], slot: Slot) -> Any:
    node = Document(data).find(slot.path)
    if node is None:
        return None
    if slot.member is not None:
        return slot.member
    value = node.get(slot.field)
    return value[slot.index] if slot.index is not None and isinstance(value, list) else value


def names_in_slot(data: dict[str, Any], slot: Slot, known: tuple[set[str], set[str]]) -> Iterator[tuple[str, str]]:
    """The elements one slot names, as ``(kind, key)`` (``relationKey`` for a key or reverse key)."""
    value = slot_value(data, slot)
    if not isinstance(value, str):
        return
    if slot.kind == "field":
        yield from field_names(parse_field(value, *known))
    elif slot.kind == "objectTypeMapKey":
        yield ("objectType", value)
    else:
        yield (slot.kind, value)


def consumer_api_pointer(data: dict[str, Any], keys: set[str]) -> str | None:
    """The pointer of the first node in a consumer API definition that names one of ``keys``
    (as a string, a member name, or inside ``ancestor:``/``related:`` text), or ``None``."""

    def walk(node: Any, pointer: str) -> str | None:
        if isinstance(node, str):
            return pointer if any(_names(node, key) for key in keys) else None
        if isinstance(node, dict):
            for name, item in node.items():
                child = f"{pointer}/{_segment(name)}"
                if name in keys:
                    return child
                found = walk(item, child)
                if found:
                    return found
        if isinstance(node, list):
            for position, item in enumerate(node):
                found = walk(item, f"{pointer}/{position}")
                if found:
                    return found
        return None

    for position, definition in enumerate(_list(data, "consumerApis")):
        found = walk(definition, f"/consumerApis/{position}")
        if found:
            return found
    return None


def _names(text: str, key: str) -> bool:
    """Whether ``text`` names ``key``: the whole text, or a part between ``:`` and ``.`` (a key that
    holds a dot is matched whole), so a false match only refuses a rename, never misses one."""
    if text == key or text.removeprefix("-") == key:
        return True
    if key in text and ("." in key or ":" in key):
        return True
    return key in text.replace(":", ".").split(".")


def _segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
