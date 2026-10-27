"""The consumer API kinds (0.10 A4c, D51–D53, [API.md § Kinds](../../../../docs/API.md)).

A consumer API definition (schema 0.9, CONSUMER_API "Definition shape") changes by two
whole-definition kinds and four part verbs, as a view changes by the view verbs: each part verb names
the part by a JSON **pointer** below the definition (``/object/fields``, ``/operations/lists/<key>``,
``/filters/<name>/matchOn/0``). A keyed map (fields, related blocks, lists, filters, public names)
keeps its members in written order, which is the order fields are served in, so an insert or a move
places a member at a position as in a list.

A change is refused when the definition would no longer have the schema 0.9 shape (D52): it is
re-read as ``ConsumerApiDocument`` after the change. What it names (sources, relations, types) is the
compiler's to report after the step, at the author's pointers, so the rules stay in one place
(``validation/consumer_api_rules.py``). Definitions are not released elements: a change to one the
base release declares is not refused; the contract check at activation protects its consumers (D55).
"""

import copy
import re
from typing import Any

from pydantic import ValidationError

from ....models.schema import ConsumerApiDocument
from .document import Path, Refusal, identity
from .keys import key_from_label
from .kinds import Applied, Context, Params, atom, kind

# Output names the engine serves itself (CONSUMER_API "Output names").
_RESERVED_OUTPUTS = {"objectType", "matchScore", "target", "parent", "path", "hierarchy"}


def _definitions(context: Context) -> list[dict[str, Any]]:
    return [item for item in context.document.items("consumerApis") if isinstance(item, dict)]


def _definition_path(context: Context, key: Any, name: str = "consumerApi") -> Path:
    if not isinstance(key, str) or not key:
        raise Refusal(name, "invalidValue", f"'{name}' must be a consumer API's key")
    if not any(item.get("key") == key for item in _definitions(context)):
        raise Refusal(name, "unknownElement", f"No consumer API '{key}'")
    return ["consumerApis", {"key": key}]


def _segments(pointer: Any) -> list[str]:
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise Refusal("pointer", "invalidValue", "'pointer' is a JSON pointer below the definition, such as /object/fields")
    if not pointer:
        return []
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer.split("/")[1:]]


def _pointer(segments: list[str | int]) -> str:
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in segments)


def _resolve(node: Any, segments: list[str]) -> tuple[list[str | int], Any]:
    """The path to the node the segments name (array indices as numbers) and the node itself."""
    resolved: list[str | int] = []
    for segment in segments:
        if isinstance(node, dict) and segment in node:
            resolved.append(segment)
            node = node[segment]
        elif isinstance(node, list) and segment.isdigit() and int(segment) < len(node):
            resolved.append(int(segment))
            node = node[int(segment)]
        else:
            raise Refusal("pointer", "unknownElement", f"The definition has nothing at {_pointer([*resolved, segment])}")
    return resolved, node


def _checked(context: Context, path: Path, parameter: str) -> None:
    """Refuses a definition no longer in the schema 0.9 shape, naming where (D52)."""
    definition = context.document.at(path)
    try:
        ConsumerApiDocument.model_validate(definition)
    except ValidationError as error:
        first = error.errors()[0]
        where = _pointer(list(first["loc"]))
        raise Refusal(parameter, "invalidValue", f"Not a consumer API definition at {where or '/'}: {first['msg']}") from error


def _replace(context: Context, path: Path, segments: list[str | int], value: Any) -> None:
    """Puts ``value`` at ``segments`` below the definition, replacing its parent's member or item
    through the logged document."""
    *above, last = segments
    owner = path + list(above)
    if isinstance(last, int):
        items = copy.deepcopy(context.document.at(owner))
        items[last] = value
        _set_container(context, path, above, items)
    else:
        context.document.set(owner, last, value)


def _set_container(context: Context, path: Path, segments: list[str | int], value: Any) -> None:
    """Writes a whole list or map at ``segments`` (the definition itself when empty)."""
    if not segments:
        definition = context.document.at(path)
        for name in [name for name in definition if name not in value]:
            context.document.set(path, name, None)
        for name, item in value.items():
            context.document.set(path, name, item)
        return
    *above, last = segments
    if isinstance(last, int):
        items = copy.deepcopy(context.document.at(path + list(above)))
        items[last] = value
        _set_container(context, path, above, items)
    else:
        context.document.set(path + list(above), last, value)


def _placed(container: dict[str, Any], key: str, value: Any, position: int) -> dict[str, Any]:
    items = list(container.items())
    items.insert(position, (key, value))
    return dict(items)


def _position(params: Params, size: int, default: int) -> int:
    position = params.optional("position", int)
    if position is None:
        return default
    if not 0 <= position <= size:
        raise Refusal("position", "outOfRange", f"Position {position} is outside 0–{size}")
    return position


@kind("setConsumerApiPart")
def set_consumer_api_part(context: Context, raw: dict[str, Any]) -> Applied:
    """The member or item at ``pointer`` set to ``value`` (created when its parent object lacks it);
    ``null`` takes an optional member out; the empty pointer replaces the definition."""
    Params(raw, ("consumerApi", "pointer", "value"))
    key = raw.get("consumerApi")
    path = _definition_path(context, key)
    segments = _segments(raw.get("pointer"))
    value = copy.deepcopy(raw.get("value"))
    definition = context.document.at(path)
    if not segments:
        if not isinstance(value, dict):
            raise Refusal("value", "invalidValue", "The whole definition is an object")
        old = copy.deepcopy(definition)
        new_key = value.get("key", key)
        _rekeyable(context, key, new_key)
        _set_container(context, path, [], value)
        path = ["consumerApis", {"key": new_key}]
        _checked(context, path, "value")
        return Applied(raw, {"kind": "setConsumerApiPart", "consumerApi": new_key, "pointer": "", "value": old}, named={atom("consumerApi", key)})
    resolved, owner = _resolve(definition, segments[:-1])
    last = segments[-1]
    if isinstance(owner, dict):
        old = copy.deepcopy(owner.get(last))
        target: list[str | int] = [*resolved, last]
    elif isinstance(owner, list) and last.isdigit() and int(last) < len(owner):
        if value is None:
            raise Refusal("value", "invalidValue", "An item of a list is taken out by removeConsumerApiPart")
        old = copy.deepcopy(owner[int(last)])
        target = [*resolved, int(last)]
    else:
        raise Refusal("pointer", "unknownElement", f"The definition has nothing at {_pointer([*resolved, last])}")
    new_key = key
    if target == ["key"]:
        if not isinstance(value, str):
            raise Refusal("value", "invalidValue", "A consumer API's key is text")
        _rekeyable(context, key, value)
        new_key = value
    _replace(context, path, target, value)
    path = ["consumerApis", {"key": new_key}]
    _checked(context, path, "value")
    return Applied(
        raw,
        {"kind": "setConsumerApiPart", "consumerApi": new_key, "pointer": _pointer(target), "value": old},
        named={atom("consumerApi", key)},
        rekeyed={atom("consumerApi", new_key)} if new_key != key else set(),
    )


def _rekeyable(context: Context, old: str, new: Any) -> None:
    if not isinstance(new, str) or not new:
        raise Refusal("value", "invalidValue", "A consumer API's key is text")
    if new != old and any(item.get("key") == new for item in _definitions(context)):
        raise Refusal("value", "keyTaken", f"Key '{new}' is already used")


@kind("insertConsumerApiPart")
def insert_consumer_api_part(context: Context, raw: dict[str, Any]) -> Applied:
    """``value`` into the list or keyed map at ``pointer`` (``key`` names a map's member) at
    ``position`` (the end when left out). A map or list its parent object lacks is started."""
    params = Params(raw, ("consumerApi", "pointer", "key", "value", "position"))
    key = raw.get("consumerApi")
    path = _definition_path(context, key)
    segments = _segments(raw.get("pointer"))
    if not segments:
        raise Refusal("pointer", "invalidValue", "Insert into a list or a map below the definition")
    definition = context.document.at(path)
    resolved, owner = _resolve(definition, segments[:-1])
    last = segments[-1]
    value = copy.deepcopy(raw.get("value"))
    if value is None:
        raise Refusal("value", "missingParameter", "'value' is required")
    member = raw.get("key")
    if isinstance(owner, dict) and last not in owner:
        container: Any = {} if member is not None else []
    else:
        resolved_last, container = _resolve(owner, [last])
        last = resolved_last[0]  # type: ignore[assignment]
    target: list[str | int] = [*resolved, last]
    if isinstance(container, dict):
        if not isinstance(member, str) or not member:
            raise Refusal("key", "missingParameter", "A member of a map needs its 'key'")
        if member in container:
            raise Refusal("key", "keyTaken", f"'{member}' is already in {_pointer(target)}")
        position = _position(params, len(container), len(container))
        _set_container(context, path, target, _placed(container, member, value, position))
        item: str | int = member
    elif isinstance(container, list):
        if member is not None:
            raise Refusal("key", "invalidValue", f"{_pointer(target)} is a list; its items have no key")
        position = _position(params, len(container), len(container))
        items = copy.deepcopy(container)
        items.insert(position, value)
        _set_container(context, path, target, items)
        item = position
    else:
        raise Refusal("pointer", "invalidValue", f"{_pointer(target)} is neither a list nor a map")
    _checked(context, path, "value")
    return Applied(
        raw,
        {"kind": "removeConsumerApiPart", "consumerApi": key, "pointer": _pointer([*target, item])},
        named={atom("consumerApi", key)},
    )


@kind("moveConsumerApiPart")
def move_consumer_api_part(context: Context, raw: dict[str, Any]) -> Applied:
    """The member or item at ``pointer`` moved to ``position`` within its list or map."""
    params = Params(raw, ("consumerApi", "pointer", "position"))
    key = raw.get("consumerApi")
    path = _definition_path(context, key)
    segments = _segments(raw.get("pointer"))
    if not segments:
        raise Refusal("pointer", "invalidValue", "Name a member or an item to move")
    resolved, _ = _resolve(context.document.at(path), segments)
    *above, last = resolved
    container = context.document.at(path + list(above))
    size = len(container)
    position = params.required("position", int)
    if not 0 <= position < size:
        raise Refusal("position", "outOfRange", f"Position {position} is outside 0–{size - 1}")
    if isinstance(container, dict):
        names = list(container)
        old = names.index(last)  # type: ignore[arg-type]
        rest = {name: value for name, value in container.items() if name != last}
        moved = _placed(rest, last, container[last], position)  # type: ignore[arg-type]
        new_item: str | int = last
    else:
        old = int(last)
        items = copy.deepcopy(container)
        items.insert(position, items.pop(old))
        moved = items
        new_item = position
    _set_container(context, path, list(above), copy.deepcopy(moved))
    _checked(context, path, "position")
    return Applied(
        raw,
        {"kind": "moveConsumerApiPart", "consumerApi": key, "pointer": _pointer([*above, new_item]), "position": old},
        named={atom("consumerApi", key)},
    )


@kind("removeConsumerApiPart")
def remove_consumer_api_part(context: Context, raw: dict[str, Any]) -> Applied:
    """The member or item at ``pointer`` taken out of its list or map."""
    Params(raw, ("consumerApi", "pointer"))
    key = raw.get("consumerApi")
    path = _definition_path(context, key)
    segments = _segments(raw.get("pointer"))
    if not segments:
        raise Refusal("pointer", "invalidValue", "Name a member or an item; removeConsumerApi removes the definition")
    resolved, value = _resolve(context.document.at(path), segments)
    *above, last = resolved
    container = context.document.at(path + list(above))
    inverse: dict[str, Any] = {"kind": "insertConsumerApiPart", "consumerApi": key, "pointer": _pointer(above), "value": copy.deepcopy(value)}
    if isinstance(container, dict):
        inverse["key"] = last
        inverse["position"] = list(container).index(last)  # type: ignore[arg-type]
        remaining: Any = {name: item for name, item in container.items() if name != last}
    else:
        inverse["position"] = int(last)
        remaining = [item for index, item in enumerate(container) if index != last]
    _set_container(context, path, list(above), copy.deepcopy(remaining))
    _checked(context, path, "pointer")
    return Applied(raw, inverse, named={atom("consumerApi", key)})


# --- whole definitions ---


@kind("addConsumerApi")
def add_consumer_api(context: Context, raw: dict[str, Any]) -> Applied:
    """A consumer API exposing ``exposes``, started by the server (D53), or, as
    ``removeConsumerApi``'s inverse, the stored ``definition``, at ``position``."""
    params = Params(raw, ("name", "key", "exposes", "position", "definition"))
    taken = {item.get("key") for item in _definitions(context)}
    stored = params.optional("definition", dict)
    if stored is not None:
        definition = copy.deepcopy(stored)
        if definition.get("key") in taken:
            raise Refusal("definition", "keyTaken", f"Key '{definition.get('key')}' is already used")
    else:
        name = params.text("name")
        exposes = params.required("exposes", list)
        if not exposes:
            raise Refusal("exposes", "invalidValue", "A consumer API exposes at least one type")
        for index, type_key in enumerate(exposes):
            context.object_type(type_key, f"exposes/{index}")
        key = context.new_key(params, "key", name, {k for k in taken if isinstance(k, str)})
        definition = starting_definition(context, key, name, exposes)
    items = _definitions(context)
    position = _position(params, len(items), len(items))
    context.document.insert(["consumerApis"], definition, position)
    _checked(context, ["consumerApis", identity(definition)], "definition" if stored is not None else "name")
    return Applied(
        {**raw, "definition": definition} if stored is None else raw,
        {"kind": "removeConsumerApi", "consumerApi": definition["key"]},
        created={atom("consumerApi", definition["key"])},
    )


@kind("removeConsumerApi")
def remove_consumer_api(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("consumerApi",))
    key = raw.get("consumerApi")
    _definition_path(context, key)
    position = next(index for index, item in enumerate(_definitions(context)) if item.get("key") == key)
    removed = context.document.remove(["consumerApis"], {"key": key})
    if not context.document.items("consumerApis"):
        context.document.set([], "consumerApis", None)
    return Applied(
        raw,
        {"kind": "addConsumerApi", "definition": removed, "position": position},
        named={atom("consumerApi", key)},
    )


def starting_definition(context: Context, key: str, name: str, exposes: list[str]) -> dict[str, Any]:
    """D53: the ID and the name, a field per attribute an exposed type binds (in binding order, named
    by its key in camelCase), Get by ID and a list per type; contract version 1."""
    fields: dict[str, Any] = {"id": {"role": "id"}, "name": {"role": "name", "from": "name"}}
    taken = {*fields, *_RESERVED_OUTPUTS}
    seen: set[str] = set()
    for type_key in exposes:
        for binding in context.object_type(type_key).get("attributes") or []:
            attribute = binding.get("attributeTypeKey")
            if not isinstance(attribute, str) or attribute in seen:
                continue
            seen.add(attribute)
            output = _free(camel_case(attribute), taken)
            taken.add(output)
            fields[output] = attribute
    lists: dict[str, Any] = {}
    for type_key in exposes:
        object_type = context.object_type(type_key)
        list_key = key_from_label(object_type.get("pluralName") or object_type.get("name") or type_key, set(lists))
        lists[list_key] = {"of": type_key}
    return {
        "key": key,
        "name": name,
        "contractVersion": 1,
        "exposes": list(exposes),
        "object": {"fields": fields},
        "operations": {"objects": {}, "lists": lists},
    }


def camel_case(key: str) -> str:
    parts = [part for part in re.split(r"[^0-9A-Za-z]+", key) if part]
    if not parts:
        return "field"
    head, *rest = parts
    text = head[:1].lower() + head[1:] + "".join(part[:1].upper() + part[1:] for part in rest)
    return text if text[:1].isalpha() else f"f{text}"


def _free(name: str, taken: set[str]) -> str:
    if name not in taken:
        return name
    number = 2
    while f"{name}{number}" in taken:
        number += 1
    return f"{name}{number}"
