"""The source and mapping kinds: a draft's import profile edited by operations (0.10 A5, D76, D77).

They change the draft's profile only, never its model, and are additive. Each names a source by
the ``id`` the draft's profile gives it (``addSource`` generates one from the sheet and the type,
A-D6), a column by its header text (``column``) or its sheet letter (``letter``, 0.13 AQ) and a
sheet by its name in the draft's profiled source file;
a sheet or column the file lacks is refused ``unknownElement``, as is any mapping kind on a draft
without a profiled file. Bindings are written in the import profile's own vocabulary (API.md,
import profiles), so what an integrator reads back is what ``POST /imports`` takes.

Every kind's inverse is ``restoreElements`` with the logged reversal of what it changed, so its
undo is exact (ADR-041). A kind names the source it changes (``source:<id>``) and the model
elements its binding names, so undoing a model step a mapping relies on is refused with its
dependants (D8).
"""

import copy
import re
from typing import Any

from openpyxl.utils.cell import column_index_from_string
from pydantic import ValidationError

from ....models.imports import COLUMN_LETTERS, ColumnBinding, FixedParent, Source
from . import profile_side
from .document import Refusal
from .keys import key_from_label
from .kinds import Applied, Context, Params, atom, kind, restoring

READINGS = ("text", "lookup", "relation", "relationFlag")


class Letter(str):
    """A column named by its sheet letter: it reaches a column whose header cell is empty (0.13 AQ).
    A column named by its header is a plain ``str``."""


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


def _repeated(headers: tuple[str, ...]) -> set[str]:
    """The names the import's reader gives a header that repeats: ``Checklist #2``, ``#3``."""
    seen: dict[str, int] = {}
    names: set[str] = set()
    for header in headers:
        seen[header] = seen.get(header, 0) + 1
        if seen[header] > 1:
            names.add(f"{header} #{seen[header]}")
    return names


def _column(context: Context, source: dict[str, Any], column: Any, field: str = "column") -> str:
    sheet = _sheet(context, source.get("sheet"), field)
    own_row = source.get("headerRow")
    # A source moved to another header row maps the headers of that row (0.10 A8b, D126).
    if (
        isinstance(column, str)
        and column not in sheet.headers
        and sheet.row is not None
        and isinstance(own_row, int)
        and column in sheet.row(own_row).values()
    ):
        return column
    if not isinstance(column, str) or (
        column not in sheet.headers and column not in _repeated(sheet.headers)
    ):
        raise Refusal(field, "unknownElement", f"Sheet '{sheet.name}' has no column '{column}'")
    return column


def _ref(context: Context, source: dict[str, Any], raw: dict[str, Any], field: str = "column") -> str:
    """The column an operation names, by ``column`` (its header) or ``letter`` (its sheet letter,
    a :class:`Letter`); exactly one of the two."""
    letter = raw.get("letter")
    if letter is None:
        return _column(context, source, raw.get("column"), field)
    if raw.get("column") is not None:
        raise Refusal("letter", "invalidValue", "Name the column by 'column' or by 'letter', not both")
    sheet = _sheet(context, source.get("sheet"), "letter")
    if not isinstance(letter, str) or not re.fullmatch(COLUMN_LETTERS, letter):
        raise Refusal("letter", "invalidValue", "'letter' is a sheet column letter, such as AJ")
    if sheet.letters and letter not in sheet.letters:
        raise Refusal("letter", "unknownElement", f"Sheet '{sheet.name}' has no column {letter}")
    return Letter(letter)


def _is(binding: dict[str, Any], column: str) -> bool:
    """Whether ``binding`` is the one of ``column``, named as it names its column."""
    if isinstance(column, Letter):
        return binding.get("letter") == column
    return binding.get("column") == column or column in (binding.get("columns") or [])


def _naming(column: str, binding: dict[str, Any]) -> dict[str, Any]:
    """``binding`` with the member that names ``column``, first."""
    rest = {k: v for k, v in binding.items() if k not in ("column", "letter")}
    return {"letter": str(column), **rest} if isinstance(column, Letter) else {"column": column, **rest}


def _unnamed(binding: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in binding.items() if k not in ("column", "letter")}


def _named(source: dict[str, Any], binding: dict[str, Any] | None = None) -> set[str]:
    """The source and the model elements a binding names (D8)."""
    own = source.get("objectTypeKey", "")
    named = {f"source:{source['id']}", atom("objectType", own)}
    if isinstance(source.get("parent"), dict):
        named.add(atom("objectType", source["parent"].get("objectTypeKey", "")))
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
    candidate = _naming(column, binding) if "relationFlags" not in binding else binding
    try:
        ColumnBinding.model_validate(candidate)
    except ValidationError as exc:
        raise Refusal(field, "invalidValue", f"Not a column binding: {exc.errors()[0]['msg']}") from exc
    if binding.get("parent") and source.get("parent"):
        raise Refusal(f"{field}/parent", "invalidValue", f"Source '{source['id']}' sets every row's parent")
    if binding.get("valueMap") and binding["valueMap"] not in (context.profile.data.get("valueMaps") or {}):
        raise Refusal(f"{field}/valueMap", "unknownElement", f"No value map '{binding['valueMap']}'")
    if not profile_side.binding_resolves(profile_side.facts(context.data), source, candidate):
        raise Refusal(field, "unknownElement", "The binding names an element the draft's model does not declare or allow")
    return _replacing(context, source, candidate)


def _replacing(context: Context, source: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    """A lookup onto a relation the row's record holds one of replaces it (0.10 A5c, D105): the
    cell is that record, so a new value in the next file switches it rather than adding a second
    one the relation refuses. Left as given when the binding says ``replace``, splits its cell or
    carries one relationship per row (``idColumn``, ``attributes``)."""
    relation = binding.get("relation")
    if not isinstance(relation, dict) or any(
        relation.get(name) for name in ("replace", "split", "idColumn", "attributes")
    ) or "replace" in relation:
        return binding
    if not profile_side.holds_one(
        context.data,
        relation.get("relationTypeKey"),
        relation.get("direction") or "outgoing",
        source.get("objectTypeKey"),
        relation.get("objectTypeKey"),
    ):
        return binding
    return {**binding, "relation": {**relation, "replace": True}}


def _unbind(context: Context, source: dict[str, Any], column: str) -> int | None:
    """Take ``column`` out of the source's bindings and unmapped entries; its old position."""
    profile = context.profile
    columns = [*profile_side.source_path(source), "columns"]
    position = None
    for index, binding in enumerate(list(source.get("columns") or [])):
        if "columns" not in binding and _is(binding, column):
            position = index
            profile.remove(columns, profile.identity(binding))
        elif not isinstance(column, Letter) and column in (binding.get("columns") or []):
            position = index
            remaining = [name for name in binding["columns"] if name != column]
            flags = copy.deepcopy(binding)
            profile.remove(columns, profile.identity(binding))
            if remaining:
                flags["columns"] = remaining
                flags["relationFlags"]["targets"].pop(column, None)
                profile.insert(columns, flags, index)
    for entry in list(profile.data.get("unmapped") or []):
        if entry.get("source") == source["id"] and _is(entry, column):
            profile.remove(["unmapped"], {"id": entry["id"]})
    return position


def _bind(context: Context, source: dict[str, Any], column: str, binding: dict[str, Any], field: str) -> set[str]:
    checked = _checked(context, source, column, binding, field)
    position = _unbind(context, source, column)
    context.profile.insert([*profile_side.source_path(source), "columns"], checked, position)
    return _named(source, checked)


def _current(source: dict[str, Any], column: str) -> dict[str, Any] | None:
    for binding in source.get("columns") or []:
        if _is(binding, column):
            return binding
    return None


def _source_key(context: Context, raw: Any, source: dict[str, Any]) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or len(raw) != 1 or not ({"attributeTypeKey", "column", "field"} >= set(raw)):
        raise Refusal("key", "invalidValue", "A source key is {attributeTypeKey}, {column} or {field: name}")
    if "field" in raw:
        # 0.10 A8a (D117): records found by their name.
        if raw["field"] != "name":
            raise Refusal("key/field", "invalidValue", "A source key's field is 'name'")
    elif "column" in raw:
        _column(context, source, raw["column"], "key/column")
    elif not profile_side.facts(context.data).bound(source.get("objectTypeKey"), raw["attributeTypeKey"]):
        raise Refusal("key/attributeTypeKey", "unknownElement", f"'{source.get('objectTypeKey')}' does not bind '{raw['attributeTypeKey']}'")
    return dict(raw)


def _source_parent(context: Context, raw: Any, source: dict[str, Any]) -> dict[str, Any] | None:
    """A source's one parent for every row (0.10 A8c, D141), its shape an import's and its type one
    the source's records can stand under; ``None`` takes it away."""
    if raw is None:
        return None
    try:
        FixedParent.model_validate(raw)
    except ValidationError as exc:
        raise Refusal("parent", "invalidValue", f"Not a source's parent: {exc.errors()[0]['msg']}") from exc
    if any(binding.get("parent") for binding in source.get("columns") or []):
        raise Refusal("parent", "invalidValue", f"A column of source '{source['id']}' binds the parent")
    if not profile_side.parent_resolves(profile_side.facts(context.data), source, raw):
        raise Refusal("parent", "unknownElement", f"A '{source.get('objectTypeKey')}' record cannot stand under a '{raw['objectTypeKey']}' record")
    return dict(raw)


def _done(context: Context, raw: dict[str, Any], name: str, named: set[str], created: set[str] | None = None) -> Applied:
    return restoring(context, {"kind": name, **raw}, Applied(raw, {}, created=created or set(), named=named))


# --- sources ---


@kind("setProfile", params=("key", "name", "sources", "valueMaps"))
def set_profile(context: Context, raw: dict[str, Any]) -> Applied:
    """Set the draft's import profile: its key and name, or the whole profile (`sources` and `valueMaps`, as `GET /model-drafts/{id}/profile` answers them in `definition`) in one undoable step."""
    params = Params(raw)
    _ensure_profile(context)
    if not raw:
        raise Refusal("name", "missingParameter", "Name key, name, sources or valueMaps")
    for name in ("key", "name"):
        if name in raw:
            context.profile.set([], name, params.text(name))
    named: set[str] = set()
    created: set[str] = set()
    if "valueMaps" in raw:
        context.profile.set([], "valueMaps", _value_maps(params.required("valueMaps", dict)))
    if "sources" in raw:
        named, created = _replace_sources(context, params.required("sources", list))
    return _done(context, raw, "setProfile", named, created)


def _value_maps(maps: dict[str, Any]) -> dict[str, Any]:
    for name, entries in maps.items():
        if not isinstance(entries, dict):
            raise Refusal(f"valueMaps/{name}", "invalidValue", "A value map is an object of text to a value")
        for text_value, value in entries.items():
            if value is not None and not isinstance(value, str | int | float | bool):
                raise Refusal(f"valueMaps/{name}/{text_value}", "invalidValue", "A value map gives a value or null")
    return copy.deepcopy(maps)


def _whole_key(context: Context, key: dict[str, Any], source: dict[str, Any], found: Any, field: str) -> dict[str, Any]:
    """A source's key as the import profile states it (any form of it), its columns the file's and
    its attributes the type's."""
    for name in ("column", "versionColumn", "nameColumn"):
        if key.get(name) is not None:
            _column(context, source, key[name], f"{field}/{name}")
    attributes = [key["attributeTypeKey"]] if key.get("attributeTypeKey") else []
    for attribute in [*attributes, *(key.get("attributeTypeKeys") or [])]:
        if not found.bound(source["objectTypeKey"], attribute):
            raise Refusal(f"{field}/attributeTypeKey", "unknownElement", f"'{source['objectTypeKey']}' does not bind '{attribute}'")
    return copy.deepcopy(key)


def _replace_sources(context: Context, given: list[Any]) -> tuple[set[str], set[str]]:
    """The profile's sources replaced by ``given``, each checked as ``addSource`` and ``mapColumn``
    check theirs; a source's ``id`` is made from its sheet and type, one sent is ignored, and the
    profile's unmapped entries go with the sources they named (0.13 AQ)."""
    found = profile_side.facts(context.data)
    context.profile.set([], "sources", [])
    context.profile.set([], "unmapped", None)
    named: set[str] = set()
    created: set[str] = set()
    for position, item in enumerate(given):
        field = f"sources/{position}"
        if not isinstance(item, dict):
            raise Refusal(field, "invalidValue", "A source is an object")
        try:
            Source.model_validate({k: v for k, v in item.items() if k != "id"})
        except ValidationError as exc:
            first = exc.errors()[0]
            where = "/".join(str(part) for part in first["loc"])
            raise Refusal(f"{field}/{where}".rstrip("/"), "invalidValue", f"Not a source: {first['msg']}") from exc
        sheet = _sheet(context, item.get("sheet"), f"{field}/sheet")
        type_key = item["objectTypeKey"]
        if type_key not in found.types:
            raise Refusal(f"{field}/objectTypeKey", "unknownElement", f"No object type '{type_key}'")
        if type_key not in found.applications.get(item["applicationKey"], set()):
            raise Refusal(f"{field}/applicationKey", "unknownElement", f"'{type_key}' is not in application '{item['applicationKey']}'")
        source: dict[str, Any] = {
            "id": profile_side.new_source_id(context.profile, sheet.name, type_key),
            **{k: copy.deepcopy(v) for k, v in item.items() if k not in ("id", "key", "parent")},
        }
        for index, binding in enumerate(source["columns"]):
            where = f"{field}/columns/{index}"
            if "columns" in binding:
                for name in binding["columns"]:
                    _column(context, source, name, f"{where}/columns")
            else:
                _ref(context, source, binding, where)
            if not profile_side.binding_resolves(found, source, binding):
                raise Refusal(where, "unknownElement", "The binding names an element the draft's model does not declare or allow")
            named |= _named(source, binding)
        if item.get("key") is not None:
            source["key"] = _whole_key(context, item["key"], source, found, f"{field}/key")
        if item.get("parent") is not None:
            source["parent"] = _source_parent(context, item["parent"], source)
        context.profile.insert(["sources"], source)
        if sheet.name in (context.profile.data.get("ignoredSheets") or []):
            context.profile.remove(["ignoredSheets"], {"value": sheet.name})
        named |= _named(source)
        created.add(f"source:{source['id']}")
    return named, created


@kind("addSource", params=("id", "sheet", "headerRow", "block", "applicationKey", "objectType", "key", "parent", "position"))
def add_source(context: Context, raw: dict[str, Any]) -> Applied:
    """Add a source: the rows of a sheet (or a block of it) that load one object type, with no columns yet."""
    params = Params(raw)
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
    parent = _source_parent(context, raw.get("parent"), source)
    if parent is not None:
        source["parent"] = parent
    position = params.optional("position", int)
    if position is not None and not 0 <= position <= len(profile_side.sources(context.profile)):
        raise Refusal("position", "outOfRange", f"Position {position} is outside the list")
    context.profile.insert(["sources"], source, position)
    for entry in list(context.profile.data.get("ignoredSheets") or []):
        if entry == sheet.name:
            context.profile.remove(["ignoredSheets"], {"value": entry})
    stored = {**raw, "id": source["id"]}
    return _done(context, stored, "addSource", _named(source), {f"source:{source['id']}"})


@kind("setSource", params=("source", "sheet", "headerRow", "block", "applicationKey", "objectType", "key", "record", "rowsWithoutKey", "parent"))
def set_source(context: Context, raw: dict[str, Any]) -> Applied:
    """Change a source's sheet, header row, block, type, key, record handling or fixed parent."""
    params = Params(raw)
    source = _source(context, raw.get("source"))
    path = profile_side.source_path(source)
    found = profile_side.facts(context.data)
    placed = (source.get("sheet"), source.get("headerRow"), copy.deepcopy(source.get("block")))
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
        if raw["key"] is None and source.get("missing") is not None:
            # Missing records are found by the key: without one there are none (D82).
            context.profile.set(path, "missing", None)
        if raw["key"] is None and source.get("rowsWithoutKey") is not None:
            context.profile.set(path, "rowsWithoutKey", None)
    if "record" in raw:
        record = params.optional("record")
        if record not in (None, "upsert", "existing"):
            raise Refusal("record", "invalidValue", "'record' is upsert or existing")
        context.profile.set(path, "record", None if record == "upsert" else record)
    if "rowsWithoutKey" in raw:
        # What a load does with a row whose key is empty (0.10 A7, D110).
        rows = params.optional("rowsWithoutKey")
        if rows not in (None, "refuse", "skip"):
            raise Refusal("rowsWithoutKey", "invalidValue", "'rowsWithoutKey' is refuse or skip")
        if rows == "skip" and source.get("key") is None:
            raise Refusal("rowsWithoutKey", "invalidValue", f"Source '{source['id']}' has no key, so no row is without one")
        context.profile.set(path, "rowsWithoutKey", None if rows == "refuse" else rows)
    if "parent" in raw:
        context.profile.set(path, "parent", _source_parent(context, raw["parent"], source))
    if len(raw) == 1:
        raise Refusal("source", "missingParameter", "Name what changes")
    if "sheet" not in raw and ("headerRow" in raw or "block" in raw):
        _follow_columns(context, source, placed[1], placed[2])
    return _done(context, raw, "setSource", _named(source))


def _span(block: Any) -> tuple[int, int]:
    """The columns a source's ``block`` limits it to, by number (all of them without one)."""
    block = block or {}
    first = block.get("firstColumn")
    last = block.get("lastColumn")
    return (
        column_index_from_string(first) if first else 1,
        column_index_from_string(last) if last else 1 << 14,
    )


def _follow_columns(context: Context, source: dict[str, Any], header_row: Any, block: Any) -> None:
    """A source moved to another header row or narrowed keeps each binding on its column (0.10
    A8b, D126): the binding names the header its column letter holds on the new header row; a
    column outside the new block, or whose new header cell is empty, becomes an unmapped entry,
    as does a key column. Bindings name columns by header, so without this a moved header row
    leaves every binding naming a header the new row does not have."""
    source = _source(context, source["id"])
    sheet = _sheet(context, source.get("sheet"))
    if sheet.row is None or not isinstance(header_row, int):
        return
    old_first, old_last = _span(block)
    columns: dict[str, int] = {}
    for number, text in sorted(sheet.row(header_row).items()):
        if old_first <= number <= old_last:
            columns.setdefault(text, number)
    new_first, new_last = _span(source.get("block"))
    new_row = sheet.row(source.get("headerRow") or header_row)

    def moved(header: str) -> str | None | bool:
        """The header's column on the new row; ``None`` when it has none, ``False`` when the
        column was not on the old row (left as it is)."""
        number = columns.get(header)
        if number is None:
            return False
        if not new_first <= number <= new_last:
            return None
        return new_row.get(number)

    because = "setSource"
    taken: set[str] = set()
    renamed: list[tuple[int, dict[str, Any]]] = []
    for index, binding in enumerate(list(source.get("columns") or [])):
        names = [binding["column"]] if "column" in binding else list(binding.get("columns") or [])
        if not names:
            continue
        targets = [moved(name) for name in names]
        new_names = [name if target is False else target for name, target in zip(names, targets, strict=True)]
        if any(target is None for target in targets) or taken & set(new_names):
            profile_side.unmap(context.profile, source, binding, because)
            continue
        taken |= set(new_names)
        if new_names != names:
            context.profile.remove([*profile_side.source_path(source), "columns"], context.profile.identity(binding))
            changed = copy.deepcopy(binding)
            if "column" in changed:
                changed["column"] = new_names[0]
            else:
                changed["columns"] = new_names
            renamed.append((index, changed))
    for index, changed in renamed:
        bindings = _source(context, source["id"]).get("columns") or []
        context.profile.insert([*profile_side.source_path(source), "columns"], changed, min(index, len(bindings)))
    key = source.get("key")
    if isinstance(key, dict) and isinstance(key.get("column"), str):
        target = moved(key["column"])
        if target is None:
            profile_side.unmap_key(context.profile, source, because)
        elif target is not False and target != key["column"]:
            context.profile.set([*profile_side.source_path(source), "key"], "column", target)


@kind("removeSource", params=("source",))
def remove_source(context: Context, raw: dict[str, Any]) -> Applied:
    """Remove a source and its bindings from the profile."""
    source = _source(context, raw.get("source"))
    context.profile.remove(["sources"], {"id": source["id"]})
    return _done(context, raw, "removeSource", _named(source))


@kind("setMissing", params=("source", "missing"))
def set_missing(context: Context, raw: dict[str, Any]) -> Applied:
    """What a load does with the records of the source's type that no row names (0.10 A5c, D82):
    ``report`` them (the default) or ``delete`` them, in a change set only. Deleting needs a source
    that loads its records by a key."""
    params = Params(raw)
    source = _source(context, raw.get("source"))
    missing = params.text("missing")
    if missing not in ("report", "delete"):
        raise Refusal("missing", "invalidValue", "'missing' is report or delete")
    if missing == "delete" and (source.get("key") is None or source.get("record") == "existing"):
        raise Refusal(
            "missing",
            "invalidValue",
            f"Source '{source['id']}' has no key, or loads no records of its own, so no record is "
            "missing from it",
        )
    context.profile.set(profile_side.source_path(source), "missing", None if missing == "report" else missing)
    return _done(context, raw, "setMissing", _named(source))


@kind("ignoreSheet", params=("sheet",))
def ignore_sheet(context: Context, raw: dict[str, Any]) -> Applied:
    """Leave a sheet out of the load; its sources are removed."""
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


@kind("mapColumn", params=("source", "column", "letter", "binding"))
def map_column(context: Context, raw: dict[str, Any]) -> Applied:
    """Bind a column, named by header (`column`) or sheet letter (`letter`), to what it fills."""
    params = Params(raw)
    source = _source(context, raw.get("source"))
    column = _ref(context, source, raw)
    binding = params.required("binding", dict)
    if {"column", "letter", "columns", "relationFlags", "ignore"} & set(binding):
        raise Refusal("binding", "invalidValue", "A binding without its column; flags and ignore have kinds of their own")
    return _done(context, raw, "mapColumn", _bind(context, source, column, copy.deepcopy(binding), "binding"))


@kind("setColumnReading", params=("source", "column", "letter", "reading", "attributeTypeKey", "relationTypeKey", "objectTypeKey", "direction", "matchBy", "target"))
def set_column_reading(context: Context, raw: dict[str, Any]) -> Applied:
    """Change how a column is read: as text, a lookup, a relation or a relation flag."""
    params = Params(raw)
    source = _source(context, raw.get("source"))
    column = _ref(context, source, raw)
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
    if isinstance(column, Letter):
        raise Refusal("letter", "invalidValue", "A flag column is named by its header: name it in 'column'")
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


@kind("splitColumn", params=("source", "column", "letter", "delimiter"))
def split_column(context: Context, raw: dict[str, Any]) -> Applied:
    """Make a relation column split its cells at a delimiter, or stop splitting."""
    params = Params(raw)
    source = _source(context, raw.get("source"))
    column = _ref(context, source, raw)
    current = _current(source, column)
    if current is None or not isinstance(current.get("relation"), dict):
        raise Refusal("column", "invalidValue", "Only a column read as a relation is split")
    delimiter = params.optional("delimiter")
    changed = copy.deepcopy(current)
    if delimiter:
        changed["relation"]["split"] = delimiter
    else:
        changed["relation"].pop("split", None)
    return _done(context, raw, "splitColumn", _bind(context, source, column, _unnamed(changed), "delimiter"))


@kind("ignoreColumn", params=("source", "column", "letter"))
def ignore_column(context: Context, raw: dict[str, Any]) -> Applied:
    """Mark a column as ignored by the load."""
    source = _source(context, raw.get("source"))
    column = _ref(context, source, raw)
    position = _unbind(context, source, column)
    context.profile.insert([*profile_side.source_path(source), "columns"], _naming(column, {"ignore": True}), position)
    return _done(context, raw, "ignoreColumn", _named(source))


@kind("addValuesToList", params=("source", "column", "letter", "create"))
def add_values_to_list(context: Context, raw: dict[str, Any]) -> Applied:
    """A lookup or parent column creates the records it names that do not exist (D77); a flag
    column, the records its set's flags stand for, and a related record's column, the parent it
    names (0.10 A6, D93)."""
    params = Params(raw)
    source = _source(context, raw.get("source"))
    column = _ref(context, source, raw)
    current = _current(source, column)
    path: tuple[str, ...] | None = None
    for candidate in (("relation",), ("parent",), ("relationFlags",), ("relatedRecord", "parent")):
        inner: Any = current
        for name in candidate:
            inner = inner.get(name) if isinstance(inner, dict) else None
        if isinstance(inner, dict):
            path = candidate
            break
    target = current
    for name in path or ():
        target = target[name]
    if path is None or target.get("matchBy") != {"field": "name"}:
        raise Refusal("column", "invalidValue", "Only a column matched by name creates the records it names")
    changed = copy.deepcopy(current)
    inner = changed
    for name in path:
        inner = inner[name]
    if params.optional("create", bool, True):
        inner["missing"] = "create"
    else:
        inner.pop("missing", None)
    columns_path = [*profile_side.source_path(source), "columns"]
    if path == ("relationFlags",):
        index = source["columns"].index(current)
        context.profile.remove(columns_path, context.profile.identity(current))
        _checked(context, source, column, changed, "column")
        context.profile.insert(columns_path, changed, index)
        return _done(context, raw, "addValuesToList", _named(source, changed))
    return _done(context, raw, "addValuesToList", _bind(context, source, column, _unnamed(changed), "column"))


@kind("unmapColumn", params=("source", "column", "letter"))
def unmap_column(context: Context, raw: dict[str, Any]) -> Applied:
    """The column's binding taken out of the source, also for a column the file no longer has (a
    header renamed in a newer workbook, 0.10 A6); a column not bound is left as it is."""
    source = _source(context, raw.get("source"))
    if raw.get("letter") is not None:
        column = _ref(context, source, raw)
    else:
        column = raw.get("column")
        if not isinstance(column, str) or not column:
            raise Refusal("column", "invalidValue", "'column' is a column's header, or name it by 'letter'")
    _unbind(context, source, column)
    return _done(context, raw, "unmapColumn", _named(source))


# --- values ---


def _map_holder(context: Context) -> Any:
    """The profile, with its ``valueMaps`` object there to be written into."""
    if not isinstance(context.profile.data.get("valueMaps"), dict):
        context.profile.set([], "valueMaps", {})
    return context.profile


@kind("setValueMap", params=("name", "entries", "source", "column", "letter"))
def set_value_map(context: Context, raw: dict[str, Any]) -> Applied:
    """A named value map's entries (``null`` removes the map and its uses); with ``source`` and
    ``column``, that column reads through it."""
    params = Params(raw)
    name = params.text("name")
    entries = params.optional("entries", dict)
    _ensure_profile(context)
    maps = context.profile.data.get("valueMaps") or {}
    if entries is not None:
        for text_value, value in entries.items():
            if value is not None and not isinstance(value, str | int | float | bool):
                raise Refusal(f"entries/{text_value}", "invalidValue", "A value map gives a value or null")
        # The one map is the change, so its undo leaves the others as they are (0.13 AQ).
        _map_holder(context).set(["valueMaps"], name, entries)
    elif name in maps:
        for source in profile_side.sources(context.profile):
            for binding in source.get("columns") or []:
                if binding.get("valueMap") == name:
                    context.profile.set(profile_side.column_path(source, binding, context.profile), "valueMap", None)
        _map_holder(context).set(["valueMaps"], name, None)
    else:
        raise Refusal("name", "unknownElement", f"No value map '{name}'")
    named: set[str] = set()
    if "source" in raw or "column" in raw or "letter" in raw:
        if entries is None:
            raise Refusal("entries", "missingParameter", "A column reads through a map that exists")
        source = _source(context, raw.get("source"))
        column = _ref(context, source, raw)
        current = _current(source, column)
        if current is None or "columns" in current:
            raise Refusal("column", "invalidValue", "Map the column before it reads through a value map")
        context.profile.set(profile_side.column_path(source, current, context.profile), "valueMap", name)
        named = _named(source)
    return _done(context, raw, "setValueMap", named)
