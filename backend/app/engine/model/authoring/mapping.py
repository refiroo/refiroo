"""The source and mapping kinds: a draft's import profile edited by operations (0.10 A5, D76, D77).

They change the draft's profile only, never its model, and are additive. Each names a source by
the ``id`` the draft's profile gives it (``addSource`` generates one from the sheet and the type,
A-D6), a column by its header text and a sheet by its name in the draft's profiled source file;
a sheet or column the file lacks is refused ``unknownElement``, as is any mapping kind on a draft
without a profiled file. Bindings are written in the import profile's own vocabulary (API.md,
import profiles), so what an integrator reads back is what ``POST /imports`` takes.

Every kind's inverse is ``restoreElements`` with the logged reversal of what it changed, so its
undo is exact (ADR-041). A kind names the source it changes (``source:<id>``) and the model
elements its binding names, so undoing a model step a mapping relies on is refused with its
dependants (D8).
"""

import copy
from typing import Any

from pydantic import ValidationError

from ....models.imports import ColumnBinding
from . import profile_side
from .document import Refusal
from .keys import key_from_label
from .kinds import Applied, Context, Params, atom, kind, restoring

READINGS = ("text", "lookup", "relation", "relationFlag")


def _ensure_profile(context: Context) -> None:
    """The draft's profile, started on the first mapping kind: its key and name from the file."""
    profile = context.profile
    if "sources" in profile.data:
        return
    label = (context.file_name or "import").rsplit(".", 1)[0]
    profile.set([], "key", key_from_label(label, ()))
    profile.set([], "name", label)
    profile.set([], "sources", [])
    profile.set([], "valueMaps", {})


def _sheet(context: Context, name: Any, field: str = "sheet") -> Any:
    if context.sheets is None:
        raise Refusal(field, "unknownElement", "The draft has no profiled source file")
    if not isinstance(name, str) or name not in context.sheets:
        raise Refusal(field, "unknownElement", f"The source file has no sheet '{name}'")
    return context.sheets[name]


def _source(context: Context, source_id: Any, field: str = "source") -> dict[str, Any]:
    if not isinstance(source_id, str):
        raise Refusal(field, "invalidValue", "'source' is a source's id")
    found = context.profile.find(["sources", {"id": source_id}])
    if found is None:
        raise Refusal(field, "unknownElement", f"The draft's profile has no source '{source_id}'")
    return found


def _column(context: Context, source: dict[str, Any], column: Any, field: str = "column") -> str:
    sheet = _sheet(context, source.get("sheet"), field)
    if not isinstance(column, str) or column not in sheet.headers:
        raise Refusal(field, "unknownElement", f"Sheet '{sheet.name}' has no column '{column}'")
    return column


def _named(source: dict[str, Any], binding: dict[str, Any] | None = None) -> set[str]:
    """The source and the model elements a binding names (D8)."""
    own = source.get("objectTypeKey", "")
    named = {f"source:{source['id']}", atom("objectType", own)}
    if not binding:
        return named
    if "attributeTypeKey" in binding:
        named |= {atom("attributeType", binding["attributeTypeKey"]), atom("attributeBinding", own, binding["attributeTypeKey"])}
    for part in ("parent", "relation", "relationFlags", "relatedRecord"):
        inner = binding.get(part)
        if not isinstance(inner, dict):
            continue
        if inner.get("objectTypeKey"):
            named.add(atom("objectType", inner["objectTypeKey"]))
        if inner.get("relationTypeKey"):
            named.add(atom("relationType", inner["relationTypeKey"]))
            ends = (own, inner.get("objectTypeKey", ""))
            if inner.get("direction", "outgoing") == "incoming":
                ends = ends[::-1]
            named.add(atom("relationBinding", inner["relationTypeKey"], *ends))
    return named


def _checked(context: Context, source: dict[str, Any], column: str, binding: dict[str, Any], field: str) -> dict[str, Any]:
    """A column binding in the profile's vocabulary, its shape checked as an import's and every
    element it names declared by the draft's model."""
    candidate = {**binding, "column": column} if "relationFlags" not in binding else binding
    try:
        ColumnBinding.model_validate(candidate)
    except ValidationError as exc:
        raise Refusal(field, "invalidValue", f"Not a column binding: {exc.errors()[0]['msg']}") from exc
    if binding.get("valueMap") and binding["valueMap"] not in (context.profile.data.get("valueMaps") or {}):
        raise Refusal(f"{field}/valueMap", "unknownElement", f"No value map '{binding['valueMap']}'")
    if not profile_side.binding_resolves(profile_side.facts(context.data), source, candidate):
        raise Refusal(field, "unknownElement", "The binding names an element the draft's model does not declare or allow")
    return candidate


def _unbind(context: Context, source: dict[str, Any], column: str) -> int | None:
    """Take ``column`` out of the source's bindings and unmapped entries; its old position."""
    profile = context.profile
    columns = [*profile_side.source_path(source), "columns"]
    position = None
    for index, binding in enumerate(list(source.get("columns") or [])):
        if binding.get("column") == column:
            position = index
            profile.remove(columns, profile.identity(binding))
        elif column in (binding.get("columns") or []):
            position = index
            remaining = [name for name in binding["columns"] if name != column]
            flags = copy.deepcopy(binding)
            profile.remove(columns, profile.identity(binding))
            if remaining:
                flags["columns"] = remaining
                flags["relationFlags"]["targets"].pop(column, None)
                profile.insert(columns, flags, index)
    for entry in list(profile.data.get("unmapped") or []):
        if entry.get("source") == source["id"] and column in (entry.get("column"), *(entry.get("columns") or [])):
            profile.remove(["unmapped"], {"id": entry["id"]})
    return position


def _bind(context: Context, source: dict[str, Any], column: str, binding: dict[str, Any], field: str) -> set[str]:
    checked = _checked(context, source, column, binding, field)
    position = _unbind(context, source, column)
    context.profile.insert([*profile_side.source_path(source), "columns"], checked, position)
    return _named(source, checked)


def _current(source: dict[str, Any], column: str) -> dict[str, Any] | None:
    for binding in source.get("columns") or []:
        if binding.get("column") == column or column in (binding.get("columns") or []):
            return binding
    return None


def _source_key(context: Context, raw: Any, source: dict[str, Any]) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or len(raw) != 1 or not ({"attributeTypeKey", "column"} >= set(raw)):
        raise Refusal("key", "invalidValue", "A source key is {attributeTypeKey} or {column}")
    if "column" in raw:
        _column(context, source, raw["column"], "key/column")
    elif not profile_side.facts(context.data).bound(source.get("objectTypeKey"), raw["attributeTypeKey"]):
        raise Refusal("key/attributeTypeKey", "unknownElement", f"'{source.get('objectTypeKey')}' does not bind '{raw['attributeTypeKey']}'")
    return dict(raw)


def _done(context: Context, raw: dict[str, Any], name: str, named: set[str], created: set[str] | None = None) -> Applied:
    return restoring(context, {"kind": name, **raw}, Applied(raw, {}, created=created or set(), named=named))


# --- sources ---


@kind("setProfile")
def set_profile(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("key", "name"))
    _ensure_profile(context)
    if "key" not in raw and "name" not in raw:
        raise Refusal("name", "missingParameter", "Name key or name")
    for name in ("key", "name"):
        if name in raw:
            context.profile.set([], name, params.text(name))
    return _done(context, raw, "setProfile", set())


@kind("addSource")
def add_source(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("id", "sheet", "headerRow", "block", "applicationKey", "objectType", "key", "position"))
    sheet = _sheet(context, raw.get("sheet"))
    type_key = params.text("objectType")
    found = profile_side.facts(context.data)
    if type_key not in found.types:
        raise Refusal("objectType", "unknownElement", f"No object type '{type_key}'")
    apps = [app for app, types in found.applications.items() if type_key in types]
    app = params.optional("applicationKey") or (apps[0] if apps else None)
    if app not in apps:
        raise Refusal("applicationKey", "unknownElement", f"'{type_key}' is not in application '{app}'")
    _ensure_profile(context)
    taken = {s.get("id") for s in profile_side.sources(context.profile)}
    source_id = params.optional("id")
    if source_id is not None and source_id in taken:
        raise Refusal("id", "keyTaken", f"Source '{source_id}' already exists")
    source: dict[str, Any] = {
        "id": source_id or profile_side.new_source_id(context.profile, sheet.name, type_key),
        "sheet": sheet.name,
        "headerRow": params.optional("headerRow", int) or sheet.header_row or 1,
        "applicationKey": app,
        "objectTypeKey": type_key,
        "columns": [],
    }
    if params.optional("block", dict) is not None:
        source["block"] = raw["block"]
    key = _source_key(context, raw.get("key"), source)
    if key is not None:
        source["key"] = key
    position = params.optional("position", int)
    if position is not None and not 0 <= position <= len(profile_side.sources(context.profile)):
        raise Refusal("position", "outOfRange", f"Position {position} is outside the list")
    context.profile.insert(["sources"], source, position)
    for entry in list(context.profile.data.get("ignoredSheets") or []):
        if entry == sheet.name:
            context.profile.remove(["ignoredSheets"], {"value": entry})
    stored = {**raw, "id": source["id"]}
    return _done(context, stored, "addSource", _named(source), {f"source:{source['id']}"})


@kind("setSource")
def set_source(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("source", "sheet", "headerRow", "block", "applicationKey", "objectType", "key", "record"))
    source = _source(context, raw.get("source"))
    path = profile_side.source_path(source)
    found = profile_side.facts(context.data)
    if "sheet" in raw:
        context.profile.set(path, "sheet", _sheet(context, raw["sheet"]).name)
    if "headerRow" in raw:
        context.profile.set(path, "headerRow", params.required("headerRow", int))
    if "block" in raw:
        context.profile.set(path, "block", params.optional("block", dict))
    if "objectType" in raw:
        type_key = params.text("objectType")
        if type_key not in found.types:
            raise Refusal("objectType", "unknownElement", f"No object type '{type_key}'")
        context.profile.set(path, "objectTypeKey", type_key)
        if "applicationKey" not in raw and type_key not in found.applications.get(source.get("applicationKey"), set()):
            apps = [app for app, types in found.applications.items() if type_key in types]
            context.profile.set(path, "applicationKey", apps[0] if apps else None)
    if "applicationKey" in raw:
        app = params.text("applicationKey")
        if source["objectTypeKey"] not in found.applications.get(app, set()):
            raise Refusal("applicationKey", "unknownElement", f"'{source['objectTypeKey']}' is not in application '{app}'")
        context.profile.set(path, "applicationKey", app)
    if "key" in raw:
        context.profile.set(path, "key", _source_key(context, raw["key"], source))
    if "record" in raw:
        record = params.optional("record")
        if record not in (None, "upsert", "existing"):
            raise Refusal("record", "invalidValue", "'record' is upsert or existing")
        context.profile.set(path, "record", None if record == "upsert" else record)
    if len(raw) == 1:
        raise Refusal("source", "missingParameter", "Name what changes")
    return _done(context, raw, "setSource", _named(source))


@kind("removeSource")
def remove_source(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("source",))
    source = _source(context, raw.get("source"))
    context.profile.remove(["sources"], {"id": source["id"]})
    return _done(context, raw, "removeSource", _named(source))


@kind("ignoreSheet")
def ignore_sheet(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("sheet",))
    sheet = _sheet(context, raw.get("sheet"))
    _ensure_profile(context)
    named: set[str] = set()
    for source in list(profile_side.sources(context.profile)):
        if source.get("sheet") == sheet.name:
            named |= _named(source)
            context.profile.remove(["sources"], {"id": source["id"]})
    if sheet.name in (context.profile.data.get("ignoredSheets") or []):
        raise Refusal("sheet", "alreadyPresent", f"Sheet '{sheet.name}' is already ignored")
    context.profile.insert(["ignoredSheets"], sheet.name)
    return _done(context, raw, "ignoreSheet", named)


# --- columns ---


@kind("mapColumn")
def map_column(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("source", "column", "binding"))
    source = _source(context, raw.get("source"))
    column = _column(context, source, raw.get("column"))
    binding = params.required("binding", dict)
    if {"column", "columns", "relationFlags", "ignore"} & set(binding):
        raise Refusal("binding", "invalidValue", "A binding without its column; flags and ignore have kinds of their own")
    return _done(context, raw, "mapColumn", _bind(context, source, column, copy.deepcopy(binding), "binding"))


@kind("setColumnReading")
def set_column_reading(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("source", "column", "reading", "attributeTypeKey", "relationTypeKey", "objectTypeKey", "direction", "matchBy", "target"))
    source = _source(context, raw.get("source"))
    column = _column(context, source, raw.get("column"))
    reading = params.text("reading")
    if reading not in READINGS:
        raise Refusal("reading", "invalidValue", f"'reading' is one of {list(READINGS)}")
    current = _current(source, column) or {}
    value_map = {"valueMap": current["valueMap"]} if current.get("valueMap") else {}
    if reading == "text":
        attribute = params.text("attributeTypeKey")
        return _done(context, raw, "setColumnReading", _bind(context, source, column, {"attributeTypeKey": attribute, **value_map}, "attributeTypeKey"))
    was = next((current[p] for p in ("relation", "relationFlags") if isinstance(current.get(p), dict)), {})
    relation = {
        "relationTypeKey": raw.get("relationTypeKey", was.get("relationTypeKey")),
        "objectTypeKey": raw.get("objectTypeKey", was.get("objectTypeKey")),
    }
    direction = raw.get("direction", was.get("direction"))
    if direction is not None:
        relation["direction"] = direction
    if not relation["relationTypeKey"] or not relation["objectTypeKey"]:
        raise Refusal("relationTypeKey", "missingParameter", "Name the relation and the type it reaches")
    if reading == "lookup":
        relation["matchBy"] = {"field": "name"}
        if was.get("missing"):
            relation["missing"] = was["missing"]
        return _done(context, raw, "setColumnReading", _bind(context, source, column, {"relation": relation, **value_map}, ""))
    if reading == "relation":
        relation["matchBy"] = params.optional("matchBy", dict) or was.get("matchBy") or {"field": "name"}
        for kept in ("split", "missing"):
            if was.get(kept):
                relation[kept] = was[kept]
        return _done(context, raw, "setColumnReading", _bind(context, source, column, {"relation": relation, **value_map}, ""))
    target = params.text("target")
    relation["matchBy"] = params.optional("matchBy", dict) or {"field": "name"}
    _unbind(context, source, column)
    same = next(
        (
            b
            for b in source.get("columns") or []
            if isinstance(b.get("relationFlags"), dict)
            and all(b["relationFlags"].get(k) == relation.get(k) for k in ("relationTypeKey", "objectTypeKey"))
            and b["relationFlags"].get("direction", "outgoing") == relation.get("direction", "outgoing")
        ),
        None,
    )
    columns_path = [*profile_side.source_path(source), "columns"]
    if same is None:
        flags = {"columns": [column], "relationFlags": {**relation, "targets": {column: target}}}
        _checked(context, source, column, flags, "")
        context.profile.insert(columns_path, flags)
        return _done(context, raw, "setColumnReading", _named(source, flags))
    joined = copy.deepcopy(same)
    joined["columns"].append(column)
    joined["relationFlags"]["targets"][column] = target
    index = source["columns"].index(same)
    context.profile.remove(columns_path, context.profile.identity(same))
    context.profile.insert(columns_path, joined, index)
    return _done(context, raw, "setColumnReading", _named(source, joined))


@kind("splitColumn")
def split_column(context: Context, raw: dict[str, Any]) -> Applied:
    params = Params(raw, ("source", "column", "delimiter"))
    source = _source(context, raw.get("source"))
    column = _column(context, source, raw.get("column"))
    current = _current(source, column)
    if current is None or not isinstance(current.get("relation"), dict):
        raise Refusal("column", "invalidValue", "Only a column read as a relation is split")
    delimiter = params.optional("delimiter")
    changed = copy.deepcopy(current)
    if delimiter:
        changed["relation"]["split"] = delimiter
    else:
        changed["relation"].pop("split", None)
    return _done(context, raw, "splitColumn", _bind(context, source, column, {k: v for k, v in changed.items() if k != "column"}, "delimiter"))


@kind("ignoreColumn")
def ignore_column(context: Context, raw: dict[str, Any]) -> Applied:
    Params(raw, ("source", "column"))
    source = _source(context, raw.get("source"))
    column = _column(context, source, raw.get("column"))
    position = _unbind(context, source, column)
    context.profile.insert([*profile_side.source_path(source), "columns"], {"column": column, "ignore": True}, position)
    return _done(context, raw, "ignoreColumn", _named(source))


@kind("addValuesToList")
def add_values_to_list(context: Context, raw: dict[str, Any]) -> Applied:
    """A lookup or parent column creates the records it names that do not exist (D77)."""
    params = Params(raw, ("source", "column", "create"))
    source = _source(context, raw.get("source"))
    column = _column(context, source, raw.get("column"))
    current = _current(source, column)
    part = next((p for p in ("relation", "parent") if current and isinstance(current.get(p), dict)), None)
    if part is None or current[part].get("matchBy") != {"field": "name"}:
        raise Refusal("column", "invalidValue", "Only a relation or parent column matched by name creates the values it names")
    changed = copy.deepcopy(current)
    if params.optional("create", bool, True):
        changed[part]["missing"] = "create"
    else:
        changed[part].pop("missing", None)
    return _done(context, raw, "addValuesToList", _bind(context, source, column, {k: v for k, v in changed.items() if k != "column"}, "column"))


# --- values ---


@kind("setValueMap")
def set_value_map(context: Context, raw: dict[str, Any]) -> Applied:
    """A named value map's entries (``null`` removes the map and its uses); with ``source`` and
    ``column``, that column reads through it."""
    params = Params(raw, ("name", "entries", "source", "column"))
    name = params.text("name")
    entries = params.optional("entries", dict)
    _ensure_profile(context)
    maps = context.profile.data.get("valueMaps") or {}
    if entries is not None:
        for text_value, value in entries.items():
            if value is not None and not isinstance(value, str | int | float | bool):
                raise Refusal(f"entries/{text_value}", "invalidValue", "A value map gives a value or null")
        context.profile.set([], "valueMaps", {**maps, name: entries})
    elif name in maps:
        for source in profile_side.sources(context.profile):
            for binding in source.get("columns") or []:
                if binding.get("valueMap") == name:
                    context.profile.set(profile_side.column_path(source, binding, context.profile), "valueMap", None)
        context.profile.set([], "valueMaps", {k: v for k, v in maps.items() if k != name})
    else:
        raise Refusal("name", "unknownElement", f"No value map '{name}'")
    named: set[str] = set()
    if "source" in raw or "column" in raw:
        if entries is None:
            raise Refusal("entries", "missingParameter", "A column reads through a map that exists")
        source = _source(context, raw.get("source"))
        column = _column(context, source, raw.get("column"))
        current = _current(source, column)
        if current is None or "column" not in current:
            raise Refusal("column", "invalidValue", "Map the column before it reads through a value map")
        context.profile.set(profile_side.column_path(source, current, context.profile), "valueMap", name)
        named = _named(source)
    return _done(context, raw, "setValueMap", named)
