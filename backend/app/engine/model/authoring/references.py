"""Where a model document names its elements (0.10 A2): the reference index.

Keys of different kinds may be equal (a view and a panel, an attribute and a column), so a reference is
found by the document's structure, never by matching text. :func:`slots` walks every place that holds
a key, with the kind of element it names:

- ``objectType``, ``attributeType``, ``relationType`` (a relation type's ``key``), ``application``
  and ``view``: a string holding that key;
- ``objectTypeMapKey``: a member name that is an object type key (a tree's ``childSort``);
- ``field``: a field reference read against ``types``, the object types it is a field of: a built-in
  field or attribute key, ``ancestor:<type>`` or ``ancestor:<type>.<field>``, or ``related:<key>``
  and ``related:<key>.<field>`` (a relation type's key or reverse key, ADR-029, 0.9 K5), or in a
  relationships table ``from:<field>``, ``to:<field>`` and ``relation:<attribute>`` (0.13 RV); a sort
  may lead with ``-``.

``setKey`` rewrites what the slots name; removals find what names a removed element; D8 reads which
elements an operation names. Consumer API definitions name elements in their own grammar;
:func:`consumer_slots` walks it for ``setKey``, which rewrites a definition as it rewrites a view
(0.10 A4c, D54). Removals leave a definition naming a removed element alone: the draft's issues then
point at it, since only the author can say what the API should serve instead.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ....models.schema import DETAIL_FIELD_KEYS as BUILT_IN_FIELDS
from ..relation_table import PLACES
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
            # The collections whose entry opens on a chosen view (a view named there is read by
            # cascade._drop_orphan_navigation and by rename, which know the entries of a group too).
            opens = navigation.get("opens")
            if isinstance(opens, dict):
                for type_key in opens:
                    yield Slot(
                        app + ["navigation", "opens"], type_key, "objectTypeMapKey", member=type_key
                    )


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
    elif kind == "relationTable":
        yield Slot(path + ["config"], "relationTypeKey", "relationType")
        yield Slot(path + ["config"], "fromObjectTypeKey", "objectType")
        yield Slot(path + ["config"], "toObjectTypeKey", "objectType")
        source, target = config.get("fromObjectTypeKey"), config.get("toObjectTypeKey")
        yield from _fields(path + ["config"], config, "fromColumns", (source,))
        yield from _fields(path + ["config"], config, "toColumns", (target,))
        yield from _strings(path + ["config"], config, "attributeColumns", "attributeType")
        for name in ("filterFields", "sortFields"):
            for position, value in enumerate(_list(config, name)):
                if isinstance(value, str):
                    yield _placed(path + ["config"], name, value, source, target, position)
        if isinstance(config.get("defaultSort"), str):
            yield _placed(path + ["config"], "defaultSort", config["defaultSort"], source, target)
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


def _placed(
    path: Path, name: str, value: str, source: Any, target: Any, index: int | None = None
) -> Slot:
    """A relationships table's field reference, read against the end its place names."""
    place = value.removeprefix("-").partition(":")[0]
    types = _keys((source,) if place == "from" else (target,) if place == "to" else ())
    return Slot(path, name, "field", index=index, types=types)


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
    place, separator, rest = body.partition(":")
    if separator and rest and place in PLACES:
        return FieldRef(
            "placed",
            name=place,
            field=FieldRef("plain", name=rest),
            descending=descending,
        )
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
    if ref.kind == "placed" and ref.field:
        return f"{sign}{ref.name}:{format_field(ref.field)}"
    head = f"ancestor:{ref.type_key}" if ref.kind == "ancestor" else f"related:{ref.relation_key}"
    return f"{sign}{head}" + (f".{format_field(ref.field)}" if ref.field else "")


def field_names(ref: FieldRef) -> Iterator[tuple[str, str]]:
    """The elements a field reference names, as ``(kind, key)``: a plain non-built-in name is an
    attribute; a related key a relation type key or reverse key (``relationKey``)."""
    if ref.kind == "plain":
        if ref.name not in BUILT_IN_FIELDS:
            yield ("attributeType", ref.name)
    elif ref.kind == "placed":
        if ref.field is not None:
            yield from field_names(ref.field)
        return
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
    if ref.kind == "placed":
        return FieldRef("placed", name=ref.name, field=inner, descending=ref.descending)
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


def consumer_slots(data: dict[str, Any]) -> Iterator[Slot]:
    """Every place a consumer API definition (schema 0.9) names a model element: the exposed types and
    the public names' members, field sources (``<attribute>``, ``ancestor:<type>.<field>``), a related
    block's ``via`` (a relation's key or reverse key) and fields, a list's type, ``within`` types and
    sort, XREF's match fields and preferred types, custom events' types, and the filters' types and
    match fields. Output names, list keys and filter names are the author's, never re-keyed."""
    for definition in _list(data, "consumerApis"):
        if not isinstance(definition, dict):
            continue
        path: Path = ["consumerApis", identity(definition)]
        exposed = _keys(tuple(definition.get("exposes") or ()))
        yield from _strings(path, definition, "exposes", "objectType")
        names = definition.get("publicNames")
        if isinstance(names, dict):
            for type_key in names:
                yield Slot(path + ["publicNames"], type_key, "objectTypeMapKey", member=type_key)
        shape = definition.get("object") if isinstance(definition.get("object"), dict) else {}
        fields = shape.get("fields")
        if isinstance(fields, dict):
            for name, value in fields.items():
                yield from _source(path + ["object", "fields"], fields, name, value, exposed)
        related = shape.get("related")
        if isinstance(related, dict):
            for name, block in related.items():
                if not isinstance(block, dict):
                    continue
                block_path = path + ["object", "related", name]
                if isinstance(block.get("via"), str):
                    yield Slot(block_path, "via", "relationType")
                inner = block.get("fields")
                if isinstance(inner, dict):
                    for output in inner:
                        yield from _field(block_path + ["fields"], inner, output, ())
        operations = definition.get("operations") if isinstance(definition.get("operations"), dict) else {}
        lists = operations.get("lists")
        if isinstance(lists, dict):
            for key, item in lists.items():
                if not isinstance(item, dict):
                    continue
                list_path = path + ["operations", "lists", key]
                if isinstance(item.get("of"), str):
                    yield Slot(list_path, "of", "objectType")
                yield from _field(list_path, item, "sortBy", _keys((item.get("of"),)))
                if isinstance(item.get("within"), dict):
                    yield from _strings(list_path + ["within"], item["within"], "types", "objectType")
        xref = operations.get("xref") if isinstance(operations.get("xref"), dict) else {}
        for position, rule in enumerate(_list(xref, "matchOn")):
            if isinstance(rule, dict):
                yield from _field(path + ["operations", "xref", "matchOn", position], rule, "field", exposed)
        for position, through in enumerate(_list(xref, "alsoMatchThrough")):
            if not isinstance(through, dict):
                continue
            through_path = path + ["operations", "xref", "alsoMatchThrough", position]
            yield from _strings(through_path, through, "preferTypes", "objectType")
            for index, rule in enumerate(_list(through, "firstOf")):
                if isinstance(rule, dict):
                    yield from _field(through_path + ["firstOf", index], rule, "field", ())
        events = operations.get("events") if isinstance(operations.get("events"), dict) else {}
        for position, event in enumerate(_list(events, "custom")):
            if isinstance(event, dict):
                yield from _strings(path + ["operations", "events", "custom", position], event, "objectTypes", "objectType")
        filters = definition.get("filters")
        if isinstance(filters, dict):
            for name, item in filters.items():
                if not isinstance(item, dict):
                    continue
                filter_path = path + ["filters", name]
                yield from _strings(filter_path, item, "under", "objectType")
                yield from _strings(filter_path, item, "linkedTo", "objectType")
                types = _keys(tuple(item.get("under") or item.get("linkedTo") or ()))
                yield from _fields(filter_path, item, "matchOn", types)


def _source(path: Path, fields: dict[str, Any], name: str, value: Any, types: tuple[str, ...]) -> Iterator[Slot]:
    """A consumer field's sources: one source, a list of them, or ``from`` of a written-out field."""
    if isinstance(value, str):
        yield Slot(path, name, "field", types=types)
    elif isinstance(value, list):
        yield from _fields(path, fields, name, types)
    elif isinstance(value, dict):
        source = value.get("from")
        if isinstance(source, str):
            yield Slot(path + [name], "from", "field", types=types)
        elif isinstance(source, list):
            yield from _fields(path + [name], value, "from", types)


def _segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
