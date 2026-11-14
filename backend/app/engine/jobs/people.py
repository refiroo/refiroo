"""A workbook for people (Base 0.9 J6, D179–D190).

One type's collection as a workbook a person edits and imports back: the main sheet holds the
columns the table shows, in its order and labels (D180), relation columns flattened to every
related record's name or field, "; " between them (D181, D190); a sheet per chosen relationship
holds the records the exported ones own, or the relationships with their values (D182). Header
frozen and filtered, the name and relation columns in their types' hues (D184), the record's ID
and version in hidden columns, and a hidden sheet holding the import profile that reads the
workbook back (D185, D186), so an import without a profile reads it as written.

**What loads back** (D183, D187). A main-sheet value, a relation column of names or of a unique,
required field of one related type (its list replaces the record's set, under the set's version
held in a hidden column), an owned record's row, a relationship row (it adds or changes, never
removes). Every other column is a summary: written, its header marked ``(not imported)``, bound
as ``ignore``: a built-in column, a read-only value, a field that identifies nothing, a
relationship over several types, one with a sheet of its own, one whose records a sheet of the
workbook holds (its source would reference the sheet's and the sheet's it: a cycle, D183), and one
whose longest cell does not fit a cell (D189: it then gets a sheet of its own).

**Reading** (D190). The export's snapshot and scope (``exports.py``): the records go into
``export_records``; each relationship a column or sheet shows goes into ``people_links`` and the
records at their far ends, with their ancestors, into ``people_records``; each relation column's
cells are one ``string_agg`` per column into ``people_cells``. The sheets then stream from those
tables through server-side cursors; Python formats cells and never holds a set.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from psycopg import sql
from sqlalchemy import (
    JSON,
    Integer,
    MetaData,
    String,
    Text,
    exists,
    func,
    insert,
    literal,
    select,
    text,
    union_all,
)
from sqlalchemy import Column as CoreColumn
from sqlalchemy import Table as CoreTable
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.exports import ExportRequest, PeopleLayout
from ...models.imports import ImportProfileDefinition
from ...models.schema import BUILT_IN_COLUMNS, EngineModel
from ..imports.binding import NOT_LOADED
from ..imports.profiles import check_profile, source_order
from ..imports.readers import PROFILE_MARK, PROFILE_SHEET
from ..model.registry import ModelSnapshot
from ..model.related_columns import (
    RELATED_FIELD_PREFIX,
    RelatedColumn,
    RelatedKeyError,
    narrow_to,
    related_column,
    related_field_column,
)
from ..model.traversal import ancestor_type_keys, parent_type_keys
from ..reads.context_sets import record_source, relation_source
from ..reads.model_query import candidate_ids
from ..reads.snapshot_reads import SnapshotContext
from . import xlsx

LAYOUT = "people"
SUMMARY = "(not imported)"
# A people column that shows a record's parent: ``parent:<type key>``.
PARENT_PREFIX = "parent:"
ANCESTOR_PREFIX = "ancestor:"
SPLIT = "; "
ID_LABEL = "Record ID"
VERSION_LABEL = "Record version"
RELATED_ID_LABEL = "Related record ID"
OWNER_ID_LABEL = "Owner ID"
RELATION_VERSION_LABEL = "Relationship version"
YES_NO = "yes-no"
# A cell's text is cut into pieces of this many characters on the profile sheet.
PROFILE_CHUNK = 30_000
WIDTH_MIN, WIDTH_MAX = 8.0, 60.0
FETCH_ROWS = 2_000
# The eight type hues as fill and ink, mirroring ``tokens.css``'s light theme (``--hue-N-fill``,
# ``--hue-N-ink``): Excel has no dark theme. The slot is the type's position in the model, as
# ``model/hues.ts`` (D184).
HUES = (
    ("FFDDF4EF", "FF0B6E62"),
    ("FFE3EEFC", "FF1D5BB8"),
    ("FFFBE6F6", "FF972178"),
    ("FFEEF2D4", "FF525D10"),
    ("FFFDE8EE", "FFA3254F"),
    ("FFFDEBE2", "FFA2441B"),
    ("FFDCF2F8", "FF0B6278"),
    ("FFE9EDF2", "FF3F4B5C"),
)
BUILT_IN_LABELS = {
    "id": "ID",
    "name": "Name",
    "path": "Path",
    "createdAt": "Created",
    "updatedAt": "Updated",
}


def invalid_layout(message: str, path: str) -> Any:
    return api_error(422, "INVALID_EXPORT_LAYOUT", message, {"path": path})


def text_too_long(sheet: str, row: int, record: str | None, field: str, length: int) -> Any:
    """An export's text that a cell of a workbook cannot hold whole: the record and the field it
    sits in, so the text can be shortened where it is stored."""
    who = f"record {record}" if record else f"row {row}"
    return api_error(
        422,
        "EXPORT_TEXT_TOO_LONG",
        f"The text of {field} on {who} (sheet '{sheet}') has {length:,} characters; a workbook"
        f" cell holds {xlsx.CELL_CHARACTERS:,}. Shorten it, take the field out of the export, or"
        " export as CSV or JSON Lines",
        {
            "sheet": sheet,
            "row": row,
            "recordId": record,
            "field": field,
            "length": length,
            "limit": xlsx.CELL_CHARACTERS,
        },
    )


# --- the plan ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MainColumn:
    """One column of the main sheet: what it shows and whether it loads back."""

    key: str
    label: str
    kind: str  # name, attribute, builtin, related, parent, ancestor
    value_type: str = "text"
    editable: bool = True
    related: RelatedColumn | None = None
    field: str | None = None  # the related records' field; None shows their names
    hue: str | None = None  # the object type whose hue fills the column


@dataclass(frozen=True)
class OwnedLayout:
    """Owned records as columns per parent (0.9 J6a, D191, D192): the parents added to those
    holding an owned record, and the fields each parent gets a column of."""

    parents: tuple[str, ...]
    fields: tuple[str, ...]


@dataclass(frozen=True)
class SheetPlan:
    """A relationship's own sheet: the records the exported ones own (``owned``), as rows or as
    ``columns`` per parent, or the relationships; ``editable`` when its rows load back."""

    key: str
    related: RelatedColumn
    owned: bool
    editable: bool
    columns: OwnedLayout | None = None
    # A relationships table's sheet (0.17 EX1): its title, the relationship values it shows (the
    # binding's own when ``None``) and the columns of either end it shows beside them, for reading.
    title: str | None = None
    attributes: tuple[str, ...] | None = None
    orientation_from: tuple[str, ...] = ()
    orientation_to: tuple[str, ...] = ()


@dataclass(frozen=True)
class PeoplePlan:
    object_type_key: str
    application_key: str
    columns: tuple[MainColumn, ...]
    sheets: tuple[SheetPlan, ...]
    # The relationships whose pointer cells offer a list; ``None`` for every one (D196, D197).
    lists: frozenset[str] | None = None
    # The types the workbook has a sheet each of, in load order (empty for one type's workbook).
    sheet_types: tuple[str, ...] = ()
    # Whether the type's own sheet is written; a relationships table writes only its sheet.
    main: bool = True


class ViewSheets(Protocol):
    """What a matrix, a relationships table or a grid adds to a workbook (0.17 EX1): the rows it
    reads, the sheets it writes and what the About sheet says of them. ``export_view_sheets``."""

    def prepare(
        self, session: Session, workspace_key: str, context: SnapshotContext | None
    ) -> None: ...

    def write(self, writer: SheetWriter) -> ViewWritten: ...


@dataclass
class ViewWritten:
    """The sheets a view wrote, the profile sources that read them back, what each holds and how it
    loads back (About), and the records and relationships by type and relation."""

    titles: list[str]
    sources: list[dict[str, Any]]
    counts: dict[str, int]
    relations: dict[str, int]
    holds: list[tuple[str, str, str | None]]
    loads: list[tuple[str, str, str | None]]
    extra: list[tuple[str, list[tuple[str, str, str | None]]]] = field(default_factory=list)
    value_maps: dict[str, dict[str, Any]] = field(default_factory=dict)


# The About sheet's steps for typing in a list's cells in Numbers, which turns a cell list into a
# pop-up menu taking only its items (PP-D27; Apple's Numbers guide, "Add checkboxes ... and other
# controls"); every workbook whose cells offer lists of records says them.
NUMBERS_STEPS: tuple[tuple[str, str, str | None], ...] = (
    (
        "Why",
        (
            "Numbers turns each list of a sheet into a pop-up menu, which takes only its items; in"
            " Excel the list is a drop-down"
        ),
        None,
    ),
    (
        "To type other values",
        (
            "Select the cells or the column, open Format (the paintbrush), Cell, and set Data"
            " Format from Pop-Up Menu to Automatic; the values stay and the cells take any text,"
            f" such as several names separated by '{SPLIT.strip()}'"
        ),
        None,
    ),
    (
        "Or add one choice",
        "With the cells selected, under Data Format, Pop-Up Menu, click + and type the new name",
        None,
    ),
)


# The About sheet's lines on lists, the same in every workbook for people.
CHOOSE_A_RECORD = "Choose a record"
CHOOSE_A_RECORD_TEXT = (
    "A cell naming a record offers a drop-down of the records it may name (a pop-up menu in"
    " Numbers); a typed name is checked on import. A cell that may name several records takes"
    f" them separated by '{SPLIT.strip()}', after a warning in Excel."
)
LIST_SHEETS_TEXT = "The records each drop-down offers, with their path, for reading; not imported."


@dataclass(frozen=True)
class WorkbookPlan:
    """A workbook for people: a sheet set per type, or one view's sheets."""

    types: tuple[PeoplePlan, ...]
    view: ViewSheets | None = None


def plan_people(
    model: EngineModel, request: ExportRequest, ready: WorkbookPlan | None = None
) -> WorkbookPlan | None:
    """The request's workbook for people checked against the model; ``None`` for the technical
    layout. Every refusal is ``422 INVALID_EXPORT_LAYOUT`` at its pointer (D188).

    A sheet per type (0.17 EX1, PP-D21): the scope's types, parents' types first, each the type's own
    people sheet; ``people`` options describe one type's workbook (0.9 J6) and so allow one type. A
    matrix, a relationships table or grid brings its own sheets (``ready``)."""
    if request.layout != LAYOUT:
        if request.people is not None:
            raise invalid_layout(
                'people describes a workbook for people: send layout "people"', "/people"
            )
        return None
    if request.format != "xlsx":
        raise invalid_layout("A workbook for people is an XLSX file", "/format")
    if ready is not None:
        if request.people is not None:
            raise invalid_layout(
                "A view of this kind is exported as it is shown: it takes no people options",
                "/people",
            )
        return ready
    keys = [item.objectTypeKey for item in request.scope.types]
    for index, key in enumerate(keys):
        if model.object_type(key) is None:
            raise api_error(
                422,
                "INVALID_QUERY",
                f"Unknown object type '{key}'",
                {"path": f"/scope/types/{index}/objectTypeKey"},
            )
    if request.people is not None:
        if len(keys) != 1:
            raise invalid_layout(
                "A workbook for people with columns and sheets holds one type's collection",
                "/scope/types",
            )
        return WorkbookPlan((plan_type(model, keys[0], request.people),))
    order = type_order(model, keys)
    return WorkbookPlan(tuple(plan_type(model, key, None, sheet_types=order) for key in order))


def type_order(model: EngineModel, keys: Sequence[str]) -> tuple[str, ...]:
    """The types in the order their sheets load: a type after the types it stands under, otherwise as
    the model orders them (a ring of types that contain each other keeps its model order)."""
    wanted = [item.key for item in model.objectTypes if item.key in keys]
    placed: list[str] = []
    while len(placed) < len(wanted):
        ready = [
            key
            for key in wanted
            if key not in placed
            and (set(parent_type_keys(model, key)) & set(wanted)) - {key} <= set(placed)
        ]
        placed.append((ready or [key for key in wanted if key not in placed])[0])
    return tuple(placed)


def relationship_keys(model: EngineModel, type_key: str) -> list[str]:
    """The relation key of each binding the type is at the ``from`` end of, the reverse key of each it
    is at the ``to`` end of, each once, a parent relationship left out: the relationships a type's
    people sheet shows as columns of names."""
    keys: list[str] = []
    for binding in model.objectTypeRelations:
        relation = model.relation_type(binding.relationTypeKey)
        if relation is None:
            continue
        if any(
            relation.key in model.containment_relation_keys(end)
            for end in (binding.fromObjectTypeKey, binding.toObjectTypeKey)
        ):
            continue
        if binding.fromObjectTypeKey == type_key:
            keys.append(relation.key)
        if binding.toObjectTypeKey == type_key:
            keys.append(relation.reverseKey)
    return list(dict.fromkeys(keys))


def plan_type(
    model: EngineModel,
    type_key: str,
    people: PeopleLayout | None,
    *,
    sheet_types: Sequence[str] = (),
) -> PeoplePlan:
    """One type's sheets. Without ``people`` and with ``sheet_types`` (a sheet per type), the type's
    fields, its parent by name and its relationships by name; ``sheet_types`` also makes a
    relationship load back from one side only, the later sheet's, so the sources never wait on each
    other."""
    definition = model.object_type(type_key)
    if definition is None:
        raise api_error(
            422,
            "INVALID_QUERY",
            f"Unknown object type '{type_key}'",
            {"path": "/scope/types/0/objectTypeKey"},
        )
    bindings = sorted(definition.attributes, key=lambda item: item.order)
    requested = (
        list(people.columns)
        if people is not None and people.columns
        else [
            "name",
            *(item.attributeTypeKey for item in bindings),
            *(
                [
                    *(f"{PARENT_PREFIX}{key}" for key in sorted(parent_type_keys(model, type_key))),
                    *(f"{RELATED_FIELD_PREFIX}{key}" for key in relationship_keys(model, type_key)),
                ]
                if people is None and sheet_types
                else []
            ),
        ]
    )
    sheet_keys = list(people.sheets) if people is not None else []
    fields = dict(people.columnFields) if people is not None else {}

    sheets: list[SheetPlan] = []
    for index, key in enumerate(sheet_keys):
        at = f"/people/sheets/{index}"
        if key in sheet_keys[:index]:
            raise invalid_layout(f"Relationship '{key}' has one sheet", at)
        try:
            column = related_column(model, type_key, key)
        except RelatedKeyError as error:
            raise invalid_layout(str(error), at) from None
        if is_containment(model, type_key, column):
            raise invalid_layout(
                f"'{key}' is a parent relationship; a record's parent is its own field", at
            )
        sheets.append(plan_sheet(model, type_key, key, column))
    owned_types = {sheet.related.target_type_keys[0] for sheet in sheets if sheet.owned}
    sheets = [
        replace(sheet, editable=False)
        if not sheet.owned and set(sheet.related.target_type_keys) & owned_types
        else sheet
        for sheet in sheets
    ]
    if people is not None:
        sheets = _owned_layouts(model, sheets, people.ownedColumns)
    sheet_relations = {
        (sheet.related.relation_type_key, sheet.related.direction) for sheet in sheets
    }

    for column_key in fields:
        if column_key not in requested or not column_key.startswith(RELATED_FIELD_PREFIX):
            raise invalid_layout(
                f"'{column_key}' is not a relation column of the workbook",
                f"/people/columnFields/{column_key}",
            )
    attached = {item.attributeTypeKey: item for item in bindings}
    columns: list[MainColumn] = []
    for index, key in enumerate(requested):
        at = f"/people/columns/{index}"
        if key in requested[:index]:
            raise invalid_layout(f"Column '{key}' is named twice", at)
        if key == "name":
            columns.append(MainColumn(key, "Name", "name", hue=type_key))
        elif key in BUILT_IN_COLUMNS:
            columns.append(MainColumn(key, BUILT_IN_LABELS[key], "builtin", editable=False))
        elif key in attached:
            attribute = model.attribute_type(key)
            columns.append(
                MainColumn(
                    key,
                    attribute.name,
                    "attribute",
                    attribute.valueType,
                    editable=not attached[key].readOnly,
                )
            )
        elif key.startswith(RELATED_FIELD_PREFIX):
            text_ = key.removeprefix(RELATED_FIELD_PREFIX)
            chosen = fields.get(key)
            try:
                column = related_field_column(model, type_key, text_)
                if chosen is not None:
                    if column.field is not None or column.key != text_:
                        raise RelatedKeyError(f"Column '{key}' shows a field already")
                    column = related_field_column(model, type_key, f"{text_}.{chosen}")
                if people is not None and key in people._targets:
                    column = narrow_to(column, people._targets[key])
            except RelatedKeyError as error:
                path = f"/people/columnFields/{key}" if chosen is not None else at
                raise invalid_layout(str(error), path) from None
            columns.append(
                _related_main_column(
                    model, type_key, key, column, sheet_relations, owned_types, sheet_types
                )
            )
        elif key.startswith(PARENT_PREFIX) and key.removeprefix(PARENT_PREFIX) in parent_type_keys(
            model, type_key
        ):
            parent = model.object_type(key.removeprefix(PARENT_PREFIX))
            several = len(parent_type_keys(model, type_key)) > 1
            columns.append(
                MainColumn(
                    key,
                    f"Parent: {parent.name}" if several else parent.name,
                    "parent",
                    hue=parent.key,
                )
            )
        elif key.startswith(ANCESTOR_PREFIX) and key.removeprefix(ANCESTOR_PREFIX) in (
            ancestor_type_keys(model, type_key)
        ):
            ancestor = model.object_type(key.removeprefix(ANCESTOR_PREFIX))
            columns.append(
                MainColumn(key, ancestor.name, "ancestor", editable=False, hue=ancestor.key)
            )
        else:
            raise invalid_layout(
                f"'{key}' is no column a table of '{type_key}' can show: name, id, path, createdAt,"
                " updatedAt, an attribute the type binds, related:<key>[.<field>], parent:<type>"
                " or ancestor:<type> of a type the record can sit under",
                at,
            )
    lists = None
    if people is not None and people.referenceLists is not None:
        named = {column.related.key for column in columns if column.related is not None}
        named |= {sheet.key for sheet in sheets}
        for index, key in enumerate(people.referenceLists):
            if key not in named:
                raise invalid_layout(
                    f"'{key}' is no relationship the workbook names: a relation column or a sheet",
                    f"/people/referenceLists/{index}",
                )
        lists = frozenset(people.referenceLists)
    application = next(
        (item.key for item in model.applications if type_key in item.objectTypeKeys), ""
    )
    return PeoplePlan(
        type_key, application, tuple(columns), tuple(sheets), lists, tuple(sheet_types)
    )


def _owned_layouts(
    model: EngineModel, sheets: list[SheetPlan], layouts: dict[str, Any]
) -> list[SheetPlan]:
    """The sheets ``ownedColumns`` lays out as columns per parent, checked against the model; the
    parents are checked against the data by :func:`check_parents`."""
    sheets = list(sheets)
    for key, spec in layouts.items():
        at = f"/people/ownedColumns/{key}"
        index = next((i for i, sheet in enumerate(sheets) if sheet.key == key), None)
        if index is None or not sheets[index].owned:
            raise invalid_layout(
                f"'{key}' is no sheet of owned records in the workbook: columns per parent lay out"
                " the sheet of a relationship that owns its records",
                at,
            )
        owned_key = sheets[index].related.target_type_keys[0]
        definition = model.object_type(owned_key)
        writable = [
            item.attributeTypeKey
            for item in sorted(definition.attributes, key=lambda item: item.order)
            if not item.readOnly
        ]
        chosen = list(spec.fields) if spec.fields else (writable or ["name"])
        for position, field_ in enumerate(chosen):
            if (field_ != "name" and field_ not in writable) or field_ in chosen[:position]:
                raise invalid_layout(
                    f"'{field_}' is no writable field of '{owned_key}' (name or an attribute it"
                    " binds), or it is named twice",
                    f"{at}/fields/{position}",
                )
        sheets[index] = replace(
            sheets[index],
            columns=OwnedLayout(tuple(str(parent) for parent in spec.parents), tuple(chosen)),
        )
    return sheets


def check_parents(
    session: Session,
    model: EngineModel,
    workbook: WorkbookPlan,
    workspace_key: str,
    context: SnapshotContext | None,
) -> None:
    """Each added parent is a record of the context that the owned type can stand under."""
    for sheet in (sheet for plan in workbook.types for sheet in plan.sheets):
        if sheet.columns is None or not sheet.columns.parents:
            continue
        owned_key = sheet.related.target_type_keys[0]
        allowed = parent_type_keys(model, owned_key)
        records = record_source(workspace_key, context, None)
        found = dict(
            session.execute(
                select(records.c.object_id, records.c.object_type_key).where(
                    records.c.object_id.in_(sheet.columns.parents)
                )
            ).all()
        )
        for index, parent in enumerate(sheet.columns.parents):
            at = f"/people/ownedColumns/{sheet.key}/parents/{index}"
            if parent not in found:
                raise invalid_layout(f"Record '{parent}' is not in the exported context", at)
            if found[parent] not in allowed:
                raise invalid_layout(
                    f"A '{owned_key}' record cannot stand under a '{found[parent]}' record", at
                )


def plan_sheet(model: EngineModel, type_key: str, key: str, column: RelatedColumn) -> SheetPlan:
    """An owning relationship (one binding, outgoing, required: the far records exist only through
    it, D182) gets a sheet of the owned records; any other a sheet of the relationships, editable
    when it reaches one type."""
    binding = column.bindings[0]
    owned = (
        len(column.bindings) == 1
        and column.direction == "outgoing"
        and binding.required
        and binding.toObjectTypeKey != type_key
    )
    return SheetPlan(key, column, owned, owned or len(column.target_type_keys) == 1)


def is_containment(model: EngineModel, type_key: str, column: RelatedColumn) -> bool:
    """Whether the column's relationship places records under their parents (in either
    direction), which a parent field sets, never a relationship binding."""
    return any(
        column.relation_type_key in model.containment_relation_keys(end)
        for end in (type_key, *column.target_type_keys)
    )


def _related_main_column(
    model: EngineModel,
    type_key: str,
    key: str,
    column: RelatedColumn,
    sheet_relations: set[tuple[str, str]],
    owned_types: set[str],
    sheet_types: Sequence[str] = (),
) -> MainColumn:
    far = column.target_type_keys
    relation = model.relation_type(column.relation_type_key)
    name = (
        relation.name
        if column.direction == "outgoing"
        else (getattr(relation, "reverseName", None) or relation.name)
    )
    label = f"{name} · {field_label(model, column.field)}" if column.field else name
    identifies = column.field is None or is_identifying(model, far, column.field)
    editable = (
        len(far) == 1
        and identifies
        and not is_containment(model, type_key, column)
        and (column.relation_type_key, column.direction) not in sheet_relations
        and not set(far) & owned_types
        and not _waits_for_later_sheet(type_key, far, sheet_types)
        and not _owns_records(column)
    )
    return MainColumn(
        key, label, "related", editable=editable, related=column, field=column.field, hue=far[0]
    )


def _owns_records(column: RelatedColumn) -> bool:
    """Whether a binding behind the column makes the records at its far end exist only through it
    (required, one-to-one or one-to-many): its set is never replaced from a cell, the owned records
    are edited on their own sheet."""
    return any(
        binding.required and binding.cardinality in {"one-to-one", "one-to-many"}
        for binding in column.bindings
    )


def _waits_for_later_sheet(type_key: str, far: Sequence[str], sheet_types: Sequence[str]) -> bool:
    """Whether the column names records of a type whose sheet loads after this type's: its source
    would wait for the sheet that waits for it, so the later sheet's reverse column loads the
    relationship (PP-D21)."""
    if type_key not in sheet_types:
        return False
    here = sheet_types.index(type_key)
    return any(key in sheet_types and sheet_types.index(key) > here for key in far)


def is_identifying(model: EngineModel, far: Sequence[str], field_: str) -> bool:
    """Whether a related record's field finds it: a unique attribute its one type requires (a
    record without the value could not be named, and a list replacing the set would drop it)."""
    attribute = model.attribute_type(field_)
    if len(far) != 1 or attribute is None or not attribute.features.get("unique"):
        return False
    definition = model.object_type(far[0])
    binding = next(
        (item for item in definition.attributes if item.attributeTypeKey == field_), None
    )
    return binding is not None and binding.required


def field_label(model: EngineModel, field_: str) -> str:
    if field_.startswith("ancestor:"):
        type_key, _, name = field_.removeprefix("ancestor:").partition(".")
        if name == "name":
            definition = model.object_type(type_key)
            return definition.name if definition else type_key
        field_ = name
    if field_ == "id":
        return "ID"
    attribute = model.attribute_type(field_)
    return attribute.name if attribute else field_


# --- the run -------------------------------------------------------------------------------------


_META = MetaData()
_LINKS = CoreTable(
    "people_links",
    _META,
    CoreColumn("part", Integer),
    CoreColumn("anchor_id", String(36)),
    CoreColumn("related_id", String(36)),
    CoreColumn("relation_id", String(36)),
    CoreColumn("version", Integer),
    CoreColumn("attributes", JSON),
)
_RECORDS = CoreTable(
    "people_records",
    _META,
    CoreColumn("object_id", String(36), primary_key=True),
    CoreColumn("object_type_key", Text),
    CoreColumn("name", Text),
    CoreColumn("parent_object_id", String(36)),
    CoreColumn("attributes", JSON),
    CoreColumn("version", Integer),
)
_CHOICES = CoreTable(
    "people_choices",
    _META,
    CoreColumn("list", Integer),
    CoreColumn("object_id", String(36)),
)
_TEMPORARY_TABLES = (
    (
        "CREATE TEMPORARY TABLE people_links (part integer, anchor_id varchar(36),"
        " related_id varchar(36), relation_id varchar(36), version integer, attributes json)"
        " ON COMMIT DROP"
    ),
    "CREATE INDEX ON people_links (part, anchor_id)",
    (
        "CREATE TEMPORARY TABLE people_records (object_id varchar(36) PRIMARY KEY,"
        " object_type_key text, name text, parent_object_id varchar(36), attributes json,"
        " version integer) ON COMMIT DROP"
    ),
    (
        "CREATE TEMPORARY TABLE people_ancestors (object_id varchar(36), ancestor_id varchar(36),"
        " level integer) ON COMMIT DROP"
    ),
    # Each list's records (0.9 J6a, D196); list -1 holds the parents added to columns per parent.
    "CREATE TEMPORARY TABLE people_choices (list integer, object_id varchar(36)) ON COMMIT DROP",
    "CREATE INDEX ON people_choices (list)",
    (
        "CREATE TEMPORARY TABLE people_grid (part integer, anchor_id varchar(36), cells jsonb,"
        " PRIMARY KEY (part, anchor_id)) ON COMMIT DROP"
    ),
    "CREATE INDEX ON people_ancestors (object_id)",
    (
        "CREATE TEMPORARY TABLE people_cells (object_id varchar(36), part integer, value text,"
        " PRIMARY KEY (part, object_id)) ON COMMIT DROP"
    ),
)


@dataclass
class CellSpec:
    """How one column of a sheet becomes its cells: its SQL text, its value type (``text``, an
    attribute's, ``number``, ``yesno``) and its style."""

    label: str
    expression: sql.Composable
    value_type: str = "text"
    style: int = 0
    hidden: bool = False
    header: int = 0
    list_: str | None = None
    # A cell holding several records: its list warns on typed text instead of refusing it.
    soft: bool = False


@dataclass
class PeopleOutcome:
    """The sheets written in order, the records and relationships they hold by type, and what the
    About sheet says of them (what each holds, how it loads back)."""

    titles: list[str]
    counts: dict[str, int]
    relations: dict[str, int]
    holds: list[tuple[str, str, str | None]] = field(default_factory=list)
    loads: list[tuple[str, str, str | None]] = field(default_factory=list)
    extra: list[tuple[str, list[tuple[str, str, str | None]]]] = field(default_factory=list)


def write_people(
    session: Session,
    model: EngineModel,
    workbook: WorkbookPlan,
    *,
    snapshot: ModelSnapshot,
    workspace_key: str,
    context: SnapshotContext | None,
    path: Path,
    on_row: Callable[[], None],
    checkpoint: Callable[[], None],
    description: dict[str, Any],
    about: Callable[[PeopleOutcome], tuple[str, str, list[xlsx.AboutSection]]],
) -> PeopleOutcome:
    """Write the workbook for ``workbook`` over the records already in ``export_records``: a sheet
    set per type, then the view's sheets, the About sheet second, the profile last."""
    for statement in _TEMPORARY_TABLES:
        session.execute(text(statement))
    plans = workbook.types
    related = [
        (plan, column) for plan in plans for column in plan.columns if column.related is not None
    ]
    # Each relation column's relationships, then each sheet's, as a numbered part.
    parts = {
        (plan.object_type_key, column.key): number for number, (plan, column) in enumerate(related)
    }
    sheets = [
        (plan, sheet, len(related) + number)
        for number, (plan, sheet) in enumerate((p, s) for p in plans for s in p.sheets)
    ]
    for number, (plan, column) in enumerate(related):
        fill_links(session, number, column.related, workspace_key, context, plan.object_type_key)
    for plan, sheet, number in sheets:
        fill_links(session, number, sheet.related, workspace_key, context, plan.object_type_key)
    # A view with sheets of its own (a relationships table) offers lists as a type's sheets do.
    listing = [*plans, *(getattr(workbook.view, "list_plans", lambda: ())())]
    lists = _list_specs(model, listing)
    _fill_choices(session, model, listing, lists, workspace_key, context)
    parents = {
        (plan.object_type_key, column.key)
        for plan in plans
        for column in plan.columns
        if column.kind in ("parent", "ancestor")
    }
    if parents:
        # A parent column names the record's parent: those records are read with the far records.
        session.execute(
            text(
                "INSERT INTO people_choices (list, object_id) SELECT DISTINCT -3, parent_object_id"
                " FROM export_records WHERE parent_object_id IS NOT NULL"
            )
        )
    if workbook.view is not None:
        workbook.view.prepare(session, snapshot, workspace_key, context)
    # The walk below and every sheet join these; autovacuum never analyzes a temporary table, so
    # each is analyzed once filled (0.11 Q1, D178).
    session.execute(text("ANALYZE people_links, people_choices"))
    _fill_far_records(session, workspace_key, context)
    session.execute(text("ANALYZE people_records, people_ancestors"))
    for number, (plan, column) in enumerate(related):
        _fill_cells(session, model, number, column)
    checkpoint()
    # D189: a list that does not fit a cell is a summary, written in full on a sheet of its own.
    longest = dict(
        session.execute(
            text("SELECT part, max(length(value)) FROM people_cells GROUP BY part")
        ).all()
    )
    columns = {plan.object_type_key: list(plan.columns) for plan in plans}
    for number, (plan, column) in enumerate(related):
        if (longest.get(number) or 0) <= xlsx.CELL_CHARACTERS:
            continue
        found = columns[plan.object_type_key]
        found[found.index(column)] = replace(column, editable=False)
        has_sheet = any(
            (sheet.related.relation_type_key, sheet.related.direction)
            == (column.related.relation_type_key, column.related.direction)
            and owner.object_type_key == plan.object_type_key
            for owner, sheet, _ in sheets
        )
        if not has_sheet:
            # Its relationships are those of the column: the sheet reads the same part.
            sheets.append(
                (
                    plan,
                    plan_sheet(model, plan.object_type_key, column.related.key, column.related),
                    number,
                )
            )
    # A sheet of owned records makes every other reference to their type read-only (D183).
    for plan in plans:
        owned_types = {
            sheet.related.target_type_keys[0]
            for owner, sheet, _ in sheets
            if sheet.owned and owner is plan
        }
        columns[plan.object_type_key] = [
            replace(column, editable=False)
            if column.related is not None and set(column.related.target_type_keys) & owned_types
            else column
            for column in columns[plan.object_type_key]
        ]
        sheets = [
            (owner, replace(sheet, editable=False), number)
            if owner is plan
            and not sheet.owned
            and set(sheet.related.target_type_keys) & owned_types
            else (owner, sheet, number)
            for owner, sheet, number in sheets
        ]
    if len(plans) > 1 or (plans and plans[0].sheet_types):
        _demote_ambiguous_names(session, model, plans, columns, workspace_key, context)

    connection = session.connection().connection.driver_connection
    book = xlsx.Workbook(path, on_row)
    # The reader finds the profile by this title, so no data sheet takes it.
    book.titles.add(PROFILE_SHEET.lower())
    writer = SheetWriter(session, connection, book, model, workspace_key, context)
    # A main column made read-only above (a summary, names that clash) offers no list: a list only
    # its read-only columns would use is not written.
    editable = {
        (type_key, column.key)
        for type_key, found in columns.items()
        for column in found
        if column.editable
    }
    for spec in lists:
        spec.uses = [where for where in spec.uses if where[0] != "main" or where[1:] in editable]
    writer.rules = _reserve_lists(session, model, book, lists)
    profile_sources: list[dict[str, Any]] = []
    value_maps: dict[str, dict[str, Any]] = {YES_NO: {"Yes": True, "No": False}}
    counts: dict[str, int] = {}
    relations: dict[str, int] = {}
    titles: list[str] = []
    holds: list[tuple[str, str, str | None]] = []
    loads: list[tuple[str, str, str | None]] = []
    extra: list[tuple[str, list[tuple[str, str, str | None]]]] = []
    for plan in plans:
        if plan.main:
            main_titles, main_count, main_source = writer.main(
                plan, columns[plan.object_type_key], parts
            )
            profile_sources += [{**main_source, "sheet": title} for title in main_titles]
            checkpoint()
            counts[plan.object_type_key] = counts.get(plan.object_type_key, 0) + main_count
            titles += main_titles
            holds.append(
                (
                    main_titles[0],
                    f"{main_count} {model.object_type(plan.object_type_key).pluralName.lower()}; "
                    + ", ".join(
                        column.label
                        for column in columns[plan.object_type_key]
                        if column.kind != "builtin"
                    ),
                    None,
                )
            )
        for owner, sheet, number in sheets:
            if owner is not plan:
                continue
            written, count, source = (
                writer.owned_columns(plan, sheet, number)
                if sheet.owned and sheet.columns is not None
                else writer.owned(plan, sheet, number)
                if sheet.owned
                else writer.relationships(plan, sheet, number)
            )
            titles += written
            if sheet.owned:
                far = sheet.related.target_type_keys[0]
                counts[far] = counts.get(far, 0) + count
            else:
                relations[sheet.related.relation_type_key] = (
                    relations.get(sheet.related.relation_type_key, 0) + count
                )
            if source is not None:
                profile_sources += [{**source, "sheet": title} for title in written]
            holds.append(
                (written[0], f"{count} {'records' if sheet.owned else 'relationships'}", None)
            )
            checkpoint()
    if plans:
        loads += _type_loads(columns, sheets)
    if workbook.view is not None:
        done = workbook.view.write(writer)
        titles += done.titles
        profile_sources += done.sources
        value_maps.update(done.value_maps)
        for key, count in done.counts.items():
            counts[key] = counts.get(key, 0) + count
        for key, count in done.relations.items():
            relations[key] = relations.get(key, 0) + count
        holds += done.holds
        loads += done.loads
        extra += done.extra
        checkpoint()
    for number, spec in enumerate(lists):
        if spec.title is not None:
            titles += writer.reference(spec, number)
            checkpoint()
    profile = {"sources": profile_sources, "valueMaps": value_maps}
    definition = ImportProfileDefinition.model_validate(profile)
    problems = check_profile(model, definition)
    if problems or source_order(model, definition) is None:
        # The plan's rules keep this from happening; if one is missed, the job says what failed.
        raise api_error(
            422,
            "INVALID_EXPORT_LAYOUT",
            "The workbook's own import profile would not read it back; choose other columns or "
            "sheets, and report this layout",
            {"path": "/people", "problems": [problem.body() for problem in problems]},
        )
    serialized = json.dumps(
        definition.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    # Lists of records: how to choose and what the list sheets are, and how to type in Numbers; the
    # same words in every workbook for people (a link matrix says its own choose line).
    if writer.rules:
        said = {label for label, _, _ in loads}
        if "Choose a record" not in said:
            loads.append((CHOOSE_A_RECORD, CHOOSE_A_RECORD_TEXT, None))
        if any(spec.title is not None for spec in lists):
            loads.append(("List sheets", LIST_SHEETS_TEXT, None))
        if not any(heading == "Editing in Numbers" for heading, _ in extra):
            extra.append(("Editing in Numbers", list(NUMBERS_STEPS)))
    outcome = PeopleOutcome(titles, counts, relations, holds, loads, extra)
    title, what, sections = about(outcome)
    book.about(title, what, sections)
    book.text(
        PROFILE_SHEET,
        [
            [PROFILE_MARK, json.dumps(description, ensure_ascii=False)],
            *(
                [serialized[start : start + PROFILE_CHUNK]]
                for start in range(0, len(serialized), PROFILE_CHUNK)
            ),
        ],
        hidden=True,
    )
    book.close()
    return outcome


def _type_loads(
    columns: dict[str, list[MainColumn]], sheets: list[tuple[PeoplePlan, SheetPlan, int]]
) -> list[tuple[str, str, str | None]]:
    """How a type's sheets load back, in the About sheet's words."""
    rows = [
        (
            "Edit a cell",
            "Changes that record; refused if someone changed the record since this export.",
            None,
        ),
        (
            "Add a row",
            "Adds a record of that sheet's type, with the values of its cells and its parent as named.",
            None,
        ),
        ("Clear a cell", "Changes nothing. Removing a value is done in the app.", None),
    ]
    if any(
        column.related is not None and column.editable
        for found in columns.values()
        for column in found
    ):
        rows.append(
            (
                "A relationship column",
                (
                    "Its names become the record's relationships of that kind (the ones left out are"
                    " removed); refused if the set changed since this export."
                ),
                None,
            )
        )
    if sheets:
        rows.append(
            (
                "A relationship sheet",
                "Adds or changes the relationships it lists; removes none.",
                None,
            )
        )
    rows.append(("Columns marked (not imported)", "For reading only.", None))
    return rows


def _demote_ambiguous_names(
    session: Session,
    model: EngineModel,
    plans: Sequence[PeoplePlan],
    columns: dict[str, list[MainColumn]],
    workspace_key: str,
    context: SnapshotContext | None,
) -> None:
    """A column of names finds a record by its name, so it loads back only where no two records of
    its type share one; a sheet per type is written with every such column read-only, so an import
    of it unchanged refuses nothing (PP-D21). One statement per type."""
    clashing: dict[str, bool] = {}

    def clashes(type_key: str) -> bool:
        if type_key not in clashing:
            source = record_source(workspace_key, context, [type_key])
            total, distinct = session.execute(
                select(func.count(), func.count(func.distinct(source.c.name))).select_from(source)
            ).one()
            clashing[type_key] = total != distinct
        return clashing[type_key]

    for plan in plans:
        columns[plan.object_type_key] = [
            replace(column, editable=False)
            if column.related is not None
            and column.editable
            and column.field is None
            and clashes(column.related.target_type_keys[0])
            else replace(column, editable=not clashes(column.key.removeprefix(PARENT_PREFIX)))
            if column.kind == "parent"
            else column
            for column in columns[plan.object_type_key]
        ]


# --- set statements ----------------------------------------------------------------------------


def fill_links(
    session: Session,
    part: int,
    column: RelatedColumn,
    workspace_key: str,
    context: SnapshotContext | None,
    anchor_type: str,
) -> None:
    """The exported records' relationships one column or sheet shows, with the far record."""
    relation = relation_source(context)
    near, far = (
        (relation.c.from_object_id, relation.c.to_object_id)
        if column.direction == "outgoing"
        else (relation.c.to_object_id, relation.c.from_object_id)
    )
    records = record_source(workspace_key, context, list(column.target_type_keys))
    anchors = (
        select(text("object_id"))
        .select_from(text("export_records"))
        .where(text("object_type_key = :anchor").bindparams(anchor=anchor_type))
    )
    statement = (
        select(
            literal(part),
            near,
            far,
            relation.c.relation_id,
            relation.c.version,
            relation.c.attributes,
        )
        .join(records, records.c.object_id == far)
        .where(relation.c.relation_type_key == column.relation_type_key)
        .where(near.in_(anchors))
    )
    session.execute(
        insert(_LINKS).from_select(
            ["part", "anchor_id", "related_id", "relation_id", "version", "attributes"], statement
        )
    )


def restrict_links(session: Session, part: int, far_ids: Any) -> None:
    """Keep only the part's relationships whose far record is among ``far_ids`` (a select of IDs)."""
    session.execute(_LINKS.delete().where(_LINKS.c.part == part, ~_LINKS.c.related_id.in_(far_ids)))


def _fill_far_records(
    session: Session, workspace_key: str, context: SnapshotContext | None
) -> None:
    """The records at the far ends not read yet and every ancestor of them, with their values;
    then each one's ancestors as pairs (a related record's ``ancestor:`` field, an owned record's
    parent)."""
    tree = record_source(workspace_key, context, None)
    statement = pg_insert(_RECORDS).from_select(
        ["object_id", "object_type_key", "name", "parent_object_id", "attributes", "version"],
        select(
            tree.c.object_id,
            tree.c.object_type_key,
            tree.c.name,
            tree.c.parent_object_id,
            tree.c.attributes,
            tree.c.version,
        ).where(tree.c.object_id.in_(_walk_ids(tree))),
    )
    session.execute(statement.on_conflict_do_nothing())
    session.execute(text("DELETE FROM people_ancestors"))
    session.execute(
        text(
            "INSERT INTO people_ancestors (object_id, ancestor_id, level)"
            " WITH RECURSIVE up(object_id, ancestor_id, level) AS ("
            " SELECT object_id, parent_object_id, 1 FROM people_records"
            " WHERE parent_object_id IS NOT NULL"
            " UNION ALL SELECT up.object_id, p.parent_object_id, up.level + 1 FROM up"
            " JOIN people_records p ON p.object_id = up.ancestor_id WHERE p.parent_object_id IS NOT NULL)"
            " SELECT object_id, ancestor_id, level FROM up"
        )
    )


def _walk_ids(tree: Any) -> Any:
    """The far records and the lists' records not read yet, and their ancestors, as a recursive
    select of IDs."""
    wanted = union_all(
        select(_LINKS.c.related_id.label("object_id")),
        select(_CHOICES.c.object_id.label("object_id")),
    ).subquery("people_wanted")
    start = (
        select(wanted.c.object_id)
        # NOT EXISTS, an anti-join, not NOT IN, a subplan hashed only while it fits (0.11 Q1, D177).
        .where(~exists().where(_RECORDS.c.object_id == wanted.c.object_id))
        .cte("people_walk", recursive=True)
    )
    step = tree.alias("people_step")
    walk = start.union(
        select(step.c.parent_object_id)
        .join(start, step.c.object_id == start.c.object_id)
        .where(step.c.parent_object_id.is_not(None))
    )
    return select(walk.c.object_id)


def field_sql(model: EngineModel, alias: str, field_: str | None) -> sql.Composable:
    """A ``people_records`` row's field as text, as a cell shows it: the name; an attribute's
    canonical text (a boolean Yes or No, JSON as JSON text); an ancestor's field."""
    if field_ is None or field_ == "name":
        return sql.SQL("{}.name").format(sql.Identifier(alias))
    if field_ == "id":
        return sql.SQL("{}.object_id").format(sql.Identifier(alias))
    if field_.startswith("ancestor:"):
        type_key, _, name = field_.removeprefix("ancestor:").partition(".")
        # The ancestor of that type nearest the root, as a list and ``path`` show it (D209).
        return sql.SQL(
            "(SELECT {} FROM people_ancestors u JOIN people_records a ON a.object_id = u.ancestor_id"
            " WHERE u.object_id = {}.object_id AND a.object_type_key = {}"
            " ORDER BY u.level DESC LIMIT 1)"
        ).format(field_sql(model, "a", name), sql.Identifier(alias), sql.Literal(type_key))
    attribute = model.attribute_type(field_)
    value_type = attribute.valueType if attribute else "text"
    return value_sql(alias, field_, value_type, yes_no=True)


def value_sql(alias: str, key: str, value_type: str, *, yes_no: bool) -> sql.Composable:
    source = sql.Identifier(alias)
    if value_type == "json":
        return sql.SQL("({}.attributes -> {})::text").format(source, sql.Literal(key))
    value = sql.SQL("({}.attributes ->> {})").format(source, sql.Literal(key))
    if value_type == "boolean" and yes_no:
        return sql.SQL("(CASE {} WHEN 'true' THEN 'Yes' WHEN 'false' THEN 'No' END)").format(value)
    return value


# PostgreSQL's ``jsonb_build_object`` takes at most 100 arguments, 50 pairs.
_OBJECT_PAIRS = 40


def build_object(pairs: Sequence[tuple[sql.Composable, sql.Composable]]) -> sql.Composable:
    """A jsonb object of ``(key, value)`` pairs, built in groups joined by ``||`` so any number of
    pairs stays under ``jsonb_build_object``'s argument limit."""
    groups = [pairs[start : start + _OBJECT_PAIRS] for start in range(0, len(pairs), _OBJECT_PAIRS)]
    return sql.SQL(" || ").join(
        sql.SQL("jsonb_build_object({})").format(
            sql.SQL(", ").join(sql.SQL("{}, {}").format(key, value) for key, value in group)
        )
        for group in groups or [[]]
    )


def separator_safe(value: sql.Composable) -> sql.Composable:
    """A related record's name or field as a cell lists it: a ``;`` in it written as a comma, since
    the import cuts a cell at ``;`` (D181). The one guard of every export that lists records in a
    cell (a relation column here, a link matrix's cell)."""
    return sql.SQL("replace({}, ';', ',')").format(value)


def _fill_cells(session: Session, model: EngineModel, part: int, column: MainColumn) -> None:
    """One relation column's cells: every related record's name or field, in name order."""
    value = separator_safe(field_sql(model, "o", column.field))
    statement = sql.SQL(
        "INSERT INTO people_cells (object_id, part, value)"
        " SELECT l.anchor_id, {part}, string_agg({value}, {split} ORDER BY o.name, o.object_id)"
        " FROM people_links l JOIN people_records o ON o.object_id = l.related_id"
        " WHERE l.part = {part} GROUP BY l.anchor_id"
    ).format(part=sql.Literal(part), value=value, split=sql.Literal(SPLIT))
    connection = session.connection().connection.driver_connection
    with connection.cursor() as cursor:
        cursor.execute(statement)


# --- lists to choose from (0.9 J6a, D196–D198) ---------------------------------------------------


@dataclass
class ListSpec:
    """A reference sheet: the records of ``far`` an end's ``criteria`` let a relationship choose,
    the value its pointer cells hold (``field``, the name when ``None``), and where it is used."""

    far: str
    criteria: tuple[Any, ...]
    field: str | None
    relation: str | None  # the relationship's label when criteria narrow the list
    uses: list[tuple[str, ...]]
    title: str | None = None
    count: int = 0


def sheet_field(model: EngineModel, plan: PeoplePlan, sheet: SheetPlan) -> str | None:
    """The field a relationship sheet's related record cells hold: the identifying field its main
    column shows, the name otherwise (D198)."""
    return next(
        (
            column.field
            for column in plan.columns
            if column.related is not None
            and column.related.key == sheet.key
            and column.field is not None
            and is_identifying(model, sheet.related.target_type_keys, column.field)
        ),
        None,
    )


def _list_specs(model: EngineModel, plans: Sequence[PeoplePlan]) -> list[ListSpec]:
    """The lists the workbook's pointer cells offer (D197): a main column of one relationship
    holding one record, a relationship sheet's related record, an owned sheet's parent and owner;
    one list per far type, criteria and field, shared."""
    specs: list[ListSpec] = []

    def use(
        far: str,
        criteria: tuple[Any, ...],
        field_: str | None,
        label: str | None,
        where: tuple[str, ...],
    ) -> None:
        for spec in specs:
            if (spec.far, spec.criteria, spec.field) == (far, criteria, field_):
                spec.uses.append(where)
                return
        specs.append(ListSpec(far, criteria, field_, label if criteria else None, [where]))

    def far_criteria(column: RelatedColumn) -> tuple[Any, ...]:
        end = "to" if column.direction == "outgoing" else "from"
        return tuple(column.bindings[0].candidates_at(end))

    for plan in plans:
        type_key = plan.object_type_key

        def offered(key: str, plan: PeoplePlan = plan) -> bool:
            return plan.lists is None or key in plan.lists

        for column in plan.columns:
            if column.kind == "parent" and column.editable and plan.lists is None:
                use(
                    column.key.removeprefix(PARENT_PREFIX),
                    (),
                    None,
                    None,
                    ("main", type_key, column.key),
                )
                continue
            related = column.related
            if related is None or not column.editable or not offered(related.key):
                continue
            # A column holding several records offers the list too, as a soft one: pick one, or
            # type several separated as the cell lists them (the matrix's link cells do the same).
            if len(related.bindings) == 1:
                use(
                    related.target_type_keys[0],
                    far_criteria(related),
                    column.field,
                    relation_label(model, related),
                    ("main", type_key, column.key),
                )
        for sheet in plan.sheets:
            if not offered(sheet.key) or sheet.columns is not None or not sheet.editable:
                continue
            related = sheet.related
            if not sheet.owned:
                use(
                    related.target_type_keys[0],
                    far_criteria(related),
                    sheet_field(model, plan, sheet),
                    relation_label(model, related),
                    ("sheet", type_key, sheet.key),
                )
                # The row's own record, named on a new row: the records that end may choose.
                if len(related.bindings) == 1:
                    near = "from" if related.direction == "outgoing" else "to"
                    use(
                        type_key,
                        tuple(related.bindings[0].candidates_at(near)),
                        None,
                        relation_label(model, related),
                        ("anchor", type_key, sheet.key),
                    )
                continue
            owned_key = related.target_type_keys[0]
            for parent in sorted(parent_type_keys(model, owned_key)):
                use(parent, (), None, None, ("parent", type_key, sheet.key, parent))
            owner = tuple(related.bindings[0].candidates_at("from"))
            use(
                type_key,
                owner,
                None,
                relation_label(model, related),
                ("owner", type_key, sheet.key),
            )
    return specs


def _fill_choices(
    session: Session,
    model: EngineModel,
    plans: Sequence[PeoplePlan],
    specs: list[ListSpec],
    workspace_key: str,
    context: SnapshotContext | None,
) -> None:
    """Each list's records, the records its end may choose (K7's ``candidate_ids``), one statement
    per list; and the parents added to columns per parent, as list -1, so the walk reads them."""
    for number, spec in enumerate(specs):
        chosen = candidate_ids(
            model,
            model.object_type(spec.far),
            spec.criteria,
            workspace_key=workspace_key,
            context=context,
        ).subquery()
        session.execute(
            insert(_CHOICES).from_select(
                ["list", "object_id"], select(literal(number), chosen.c.id)
            )
        )
    added = [
        parent
        for plan in plans
        for sheet in plan.sheets
        if sheet.columns
        for parent in sheet.columns.parents
    ]
    if added:
        session.execute(insert(_CHOICES), [{"list": -1, "object_id": parent} for parent in added])


def _reserve_lists(
    session: Session, model: EngineModel, book: xlsx.Workbook, specs: list[ListSpec]
) -> dict[tuple[str, ...], str]:
    """Each list's sheet title, taken before the sheets that name it are written, and the list
    rule of each cell that uses it; a list without records offers none."""
    counts = dict(
        session.execute(
            text("SELECT list, count(*) FROM people_choices WHERE list >= 0 GROUP BY list")
        ).all()
    )
    rules: dict[tuple[str, ...], str] = {}
    for number, spec in enumerate(specs):
        spec.count = counts.get(number, 0)
        if not spec.count or not spec.uses:
            continue
        plural = model.object_type(spec.far).pluralName
        spec.title = book.reserve(
            # Not "·": Numbers makes no pop-up menu of a list on a sheet whose name holds it.
            f"List - {plural}" + (f" - {spec.relation}" if spec.relation else "")
        )
        quoted = spec.title.replace("'", "''")
        for where in spec.uses:
            rules[where] = f"'{quoted}'!$A$2:$A${spec.count + 1}"
    return rules


# --- the sheets ----------------------------------------------------------------------------------


class SheetWriter:
    def __init__(
        self,
        session: Session,
        connection: Any,
        book: xlsx.Workbook,
        model: EngineModel,
        workspace_key: str,
        context: SnapshotContext | None,
    ) -> None:
        self.session = session
        self.connection = connection
        self.book = book
        self.model = model
        self.workspace_key = workspace_key
        self.context = context
        styles = book.styles
        # Every written cell has a thin border (D199).
        self.base = styles.xf(border=True)
        self.date = styles.xf(date=True, border=True)
        self._fills: dict[str | None, int] = {}
        self.plain_header = styles.xf(bold=True, border=True)
        self.rules: dict[tuple[str, ...], str] = {}

    def hue(self, type_key: str | None) -> tuple[str, str] | None:
        if type_key is None:
            return None
        keys = [item.key for item in self.model.objectTypes]
        return HUES[keys.index(type_key) % len(HUES)] if type_key in keys else None

    def fill(self, type_key: str | None) -> int:
        if type_key not in self._fills:
            hue = self.hue(type_key)
            self._fills[type_key] = (
                self.book.styles.xf(fill=hue[0], ink=hue[1], border=True) if hue else self.base
            )
        return self._fills[type_key]

    def header(self, type_key: str) -> int:
        hue = self.hue(type_key)
        if hue is None:
            return self.plain_header
        return self.book.styles.xf(fill=hue[0], ink=hue[1], bold=True, border=True)

    def application_of(self, type_key: str, fallback: str) -> str:
        """The application the exported records of the type belong to (the one most of them do),
        else the model's first that lists the type: a record is written in its own application, and a
        type several applications list has records in each (0.17 EX1)."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT application_key FROM export_records WHERE object_type_key = %s"
                " GROUP BY application_key ORDER BY count(*) DESC, application_key LIMIT 1",
                (type_key,),
            )
            found = cursor.fetchone()
        return found[0] if found and found[0] else fallback

    def row_field_label(self, field: str) -> str:
        """A list column's label: the field's, as a table shows it."""
        if field == "name":
            return "Name"
        if field in BUILT_IN_LABELS:
            return BUILT_IN_LABELS[field]
        if field == "objectType":
            return "Type"
        if field.startswith("ancestor:") and "." not in field:
            held = self.model.object_type(field.removeprefix("ancestor:"))
            return held.name if held is not None else field
        return field_label(self.model, field)

    def row_field(self, alias: str, field: str, type_key: str) -> sql.Composable:
        """A list column of a record as text. ``alias`` is ``r`` (an ``export_records`` row: its
        values are on the row) or ``o`` (a ``people_records`` row, which also reads ancestors)."""
        if field == "name":
            return sql.SQL(f"{alias}.name")
        if field == "id":
            return sql.SQL(f"{alias}.object_id")
        if field == "objectType":
            return sql.Literal(self.model.object_type(type_key).name)
        if field == "path":
            return (
                sql.SQL("r.path")
                if alias == "r"
                else sql.SQL(
                    "(SELECT string_agg(a.name, ' / ' ORDER BY u.level DESC) FROM people_ancestors u"
                    " JOIN people_records a ON a.object_id = u.ancestor_id"
                    " WHERE u.object_id = o.object_id)"
                )
            )
        if field in ("createdAt", "updatedAt"):
            return built_in(field, alias)
        if field.startswith("ancestor:") and alias == "o":
            return field_sql(self.model, "o", f"{field}.name" if "." not in field else field)
        attribute = self.model.attribute_type(field)
        if attribute is None:
            return sql.SQL("NULL")
        return value_sql(alias, field, attribute.valueType, yes_no=True)

    # --- the main sheet ---

    def main(
        self, plan: PeoplePlan, columns: list[MainColumn], parts: dict[tuple[str, str], int]
    ) -> tuple[list[str], int, dict[str, Any]]:
        model = self.model
        header = self.header(plan.object_type_key)
        cells: list[CellSpec] = []
        bindings: list[dict[str, Any]] = []
        labels = Labels()
        set_versions: list[tuple[MainColumn, str]] = []
        for column in columns:
            label = labels.take(column.label if column.editable else f"{column.label} {SUMMARY}")
            if column.kind == "name":
                cells.append(
                    CellSpec(
                        label,
                        sql.SQL("r.name"),
                        style=self.fill(plan.object_type_key),
                        header=header,
                    )
                )
                bindings.append({"column": label, "field": "name"})
                continue
            if column.kind == "attribute":
                value_type = "yesno" if column.value_type == "boolean" else column.value_type
                cells.append(
                    CellSpec(
                        label,
                        value_sql("r", column.key, column.value_type, yes_no=True),
                        value_type,
                        style=self.date if column.value_type == "date" else 0,
                        header=header,
                        list_='"Yes,No"' if value_type == "yesno" else None,
                    )
                )
                if column.editable:
                    binding = {"column": label, "attributeTypeKey": column.key}
                    if column.value_type == "boolean":
                        binding["valueMap"] = YES_NO
                    bindings.append(binding)
                else:
                    bindings.append({"column": label, "ignore": True})
                continue
            if column.kind == "builtin":
                cells.append(CellSpec(label, built_in(column.key), header=header))
                bindings.append({"column": label, "ignore": True})
                continue
            if column.kind == "ancestor":
                # The nearest the root of that type among the record's ancestors, as ``path`` names it.
                cells.append(
                    CellSpec(
                        label,
                        sql.SQL(
                            "(SELECT a.name FROM (SELECT r.parent_object_id AS id, 0 AS level"
                            " UNION ALL SELECT u.ancestor_id, u.level FROM people_ancestors u"
                            " WHERE u.object_id = r.parent_object_id) up"
                            " JOIN people_records a ON a.object_id = up.id"
                            " WHERE a.object_type_key = {} ORDER BY up.level DESC LIMIT 1)"
                        ).format(sql.Literal(column.key.removeprefix(ANCESTOR_PREFIX))),
                        style=self.fill(column.hue),
                        header=header,
                    )
                )
                bindings.append({"column": label, "ignore": True})
                continue
            if column.kind == "parent":
                parent_key = column.key.removeprefix(PARENT_PREFIX)
                held = sql.SQL(
                    "EXISTS (SELECT 1 FROM people_records p WHERE p.object_id = r.parent_object_id"
                    " AND p.object_type_key = {})"
                ).format(sql.Literal(parent_key))
                cells.append(
                    CellSpec(
                        label,
                        sql.SQL(
                            "(SELECT p.name FROM people_records p WHERE p.object_id ="
                            " r.parent_object_id AND p.object_type_key = {})"
                        ).format(sql.Literal(parent_key)),
                        style=self.fill(column.hue),
                        header=header,
                        list_=self.rules.get(("main", plan.object_type_key, column.key))
                        if column.editable
                        else None,
                    )
                )
                if column.editable:
                    bindings.append(
                        {
                            "column": label,
                            "parent": {"objectTypeKey": parent_key, "matchBy": {"field": "name"}},
                        }
                    )
                else:
                    # Two parents share a name: the hidden ID finds the parent, the name is for reading.
                    bindings.append({"column": label, "ignore": True})
                    parent_id = labels.take(f"Parent ID: {column.label.removeprefix('Parent: ')}")
                    cells.append(
                        CellSpec(
                            parent_id,
                            sql.SQL("(CASE WHEN {} THEN r.parent_object_id END)").format(held),
                            hidden=True,
                            header=self.plain_header,
                        )
                    )
                    bindings.append(
                        {
                            "column": parent_id,
                            "parent": {"objectTypeKey": parent_key, "matchBy": {"field": "id"}},
                        }
                    )
                continue
            part = parts[(plan.object_type_key, column.key)]
            cells.append(
                CellSpec(
                    label,
                    # D189: a list past a cell's size is cut, and held whole on its own sheet.
                    sql.SQL(
                        "(SELECT CASE WHEN length(c.value) > {limit} THEN left(c.value, {cut}) || {more}"
                        " ELSE c.value END FROM people_cells c WHERE c.part = {part}"
                        " AND c.object_id = r.object_id)"
                    ).format(
                        limit=sql.Literal(xlsx.CELL_CHARACTERS),
                        cut=sql.Literal(xlsx.CELL_CHARACTERS - 100),
                        more=sql.Literal(" … (every one on the relationship's own sheet)"),
                        part=sql.Literal(part),
                    ),
                    style=self.fill(column.hue),
                    header=header,
                    list_=self.rules.get(("main", plan.object_type_key, column.key))
                    if column.editable
                    else None,
                    soft=not (
                        len(column.related.bindings) == 1
                        and column.related.bindings[0].holds_one(
                            "from" if column.related.direction == "outgoing" else "to"
                        )
                    ),
                )
            )
            if not column.editable:
                bindings.append({"column": label, "ignore": True})
                continue
            set_versions.append((column, label))
        for column, label in set_versions:
            relation = column.related
            binding = relation.bindings[0]
            version_label = labels.take(f"{label} version")
            cells.append(
                CellSpec(
                    version_label,
                    sql.SQL(
                        "coalesce((SELECT v.version FROM relation_set_versions v"
                        " WHERE v.workspace_key = {ws} AND v.change_set_id IS NOT DISTINCT FROM {cs}"
                        " AND v.relation_type_key = {rel} AND v.from_object_type_key = {source}"
                        " AND v.to_object_type_key = {target} AND v.direction = {direction}"
                        " AND v.anchor_object_id = r.object_id), 0)"
                    ).format(
                        ws=sql.Literal(self.workspace_key),
                        cs=sql.Literal(
                            self.context.change_set.id
                            if self.context and self.context.change_set
                            else None
                        ),
                        rel=sql.Literal(relation.relation_type_key),
                        source=sql.Literal(binding.fromObjectTypeKey),
                        target=sql.Literal(binding.toObjectTypeKey),
                        direction=sql.Literal(relation.direction),
                    ),
                    "number",
                    hidden=True,
                    header=self.plain_header,
                )
            )
            match = {"attributeTypeKey": column.field} if column.field else {"field": "name"}
            bindings.append(
                {
                    "column": label,
                    "relation": {
                        "relationTypeKey": relation.relation_type_key,
                        "direction": relation.direction,
                        "objectTypeKey": relation.target_type_keys[0],
                        "matchBy": match,
                        "split": SPLIT.strip(),
                        "replace": True,
                        "versionColumn": version_label,
                    },
                }
            )
        id_label, version_label = labels.take(ID_LABEL), labels.take(VERSION_LABEL)
        cells += [
            CellSpec(id_label, sql.SQL("r.object_id"), hidden=True, header=self.plain_header),
            CellSpec(
                version_label, sql.SQL("r.version"), "number", hidden=True, header=self.plain_header
            ),
        ]
        definition = model.object_type(plan.object_type_key)
        titles, count = self._sheet(
            definition.pluralName,
            cells,
            sql.SQL("export_records r WHERE r.object_type_key = {}").format(
                sql.Literal(plan.object_type_key)
            ),
            sql.SQL("r.name, r.object_id"),
        )
        source = {
            "headerRow": 1,
            "applicationKey": self.application_of(plan.object_type_key, plan.application_key),
            "objectTypeKey": plan.object_type_key,
            "key": {"column": id_label, "versionColumn": version_label},
            "columns": bindings or [{"column": id_label, "ignore": True}],
        }
        return titles, count, source

    # --- a sheet of relationships ---

    def relationships(
        self, plan: PeoplePlan, sheet: SheetPlan, part: int
    ) -> tuple[list[str], int, dict[str, Any] | None]:
        model = self.model
        relation = sheet.related
        far = relation.target_type_keys
        header = self.header(plan.object_type_key)
        labels = Labels()
        own_type = model.object_type(plan.object_type_key)
        own_label = labels.take(own_type.name)
        far_label = labels.take(
            model.object_type(far[0]).name if len(far) == 1 else "Related record"
        )
        shown = sheet_field(model, plan, sheet)
        cells = [
            CellSpec(
                own_label,
                sql.SQL("r.name"),
                style=self.fill(plan.object_type_key),
                header=header,
                list_=self.rules.get(("anchor", plan.object_type_key, sheet.key))
                if sheet.editable
                else None,
            ),
            CellSpec(
                far_label,
                field_sql(model, "o", shown),
                style=self.fill(far[0]),
                header=header,
                list_=self.rules.get(("sheet", plan.object_type_key, sheet.key))
                if sheet.editable
                else None,
            ),
        ]
        values = []
        carried = (
            list(sheet.attributes)
            if sheet.attributes is not None
            else list(
                dict.fromkeys(
                    key for binding in relation.bindings for key in binding.attributeTypeKeys
                )
            )
        )
        for key in carried:
            attribute = model.attribute_type(key)
            label = labels.take(attribute.name)
            value_type = "yesno" if attribute.valueType == "boolean" else attribute.valueType
            cells.append(
                CellSpec(
                    label,
                    value_sql("l", key, attribute.valueType, yes_no=True),
                    value_type,
                    style=self.date if attribute.valueType == "date" else 0,
                    header=header,
                    list_='"Yes,No"' if value_type == "yesno" else None,
                )
            )
            values.append(
                {"column": label, "attributeTypeKey": key}
                | ({"valueMap": YES_NO} if value_type == "yesno" else {})
            )
        ignored = []
        for type_key in () if sheet.title else far:
            display = model.object_type(type_key).displayAttributeTypeKey
            if display and display not in carried and display != "name":
                attribute = model.attribute_type(display)
                if attribute is None:
                    continue
                label = labels.take(f"{attribute.name} {SUMMARY}")
                if any(cell.label == label for cell in cells):
                    continue
                cells.append(CellSpec(label, field_sql(model, "o", display), header=header))
                ignored.append({"column": label, "ignore": True})
        for alias, fields, type_key in (
            ("r", sheet.orientation_from, plan.object_type_key),
            ("o", sheet.orientation_to, far[0]),
        ):
            type_name = model.object_type(type_key).name
            for orient in fields:
                if orient == "name":
                    continue
                label = labels.take(f"{type_name}: {self.row_field_label(orient)} {SUMMARY}")
                cells.append(
                    CellSpec(label, self.row_field(alias, orient, type_key), header=header)
                )
                ignored.append({"column": label, "ignore": True})
        own_id, far_id, version = (
            labels.take(ID_LABEL),
            labels.take(RELATED_ID_LABEL),
            labels.take(RELATION_VERSION_LABEL),
        )
        cells += [
            CellSpec(own_id, sql.SQL("r.object_id"), hidden=True, header=self.plain_header),
            CellSpec(far_id, sql.SQL("o.object_id"), hidden=True, header=self.plain_header),
            CellSpec(
                version, sql.SQL("l.version"), "number", hidden=True, header=self.plain_header
            ),
        ]
        title = sheet.title or relation_label(model, relation)
        titles, count = self._sheet(
            title,
            cells,
            sql.SQL(
                "export_records r JOIN people_links l ON l.anchor_id = r.object_id AND l.part = {}"
                " JOIN people_records o ON o.object_id = l.related_id"
            ).format(sql.Literal(part)),
            sql.SQL("r.name, r.object_id, o.name, o.object_id"),
        )
        if not sheet.editable:
            return titles, count, None
        source = {
            "headerRow": 1,
            "applicationKey": self.application_of(plan.object_type_key, plan.application_key),
            "objectTypeKey": plan.object_type_key,
            "record": "existing",
            "key": {"column": own_id, "nameColumn": own_label},
            "columns": [
                {
                    "column": far_label,
                    "relation": {
                        "relationTypeKey": relation.relation_type_key,
                        "direction": relation.direction,
                        "objectTypeKey": far[0],
                        "matchBy": {"attributeTypeKey": shown} if shown else {"field": "name"},
                        "idColumn": far_id,
                        "versionColumn": version,
                        **({"attributes": values} if values else {}),
                    },
                },
                *ignored,
            ],
        }
        return titles, count, source

    # --- a sheet of owned records ---

    def owned(
        self, plan: PeoplePlan, sheet: SheetPlan, part: int
    ) -> tuple[list[str], int, dict[str, Any] | None]:
        model = self.model
        relation = sheet.related
        owned_key = relation.target_type_keys[0]
        definition = model.object_type(owned_key)
        header = self.header(owned_key)
        labels = Labels()
        name_label = labels.take("Name")
        cells = [CellSpec(name_label, sql.SQL("o.name"), style=self.fill(owned_key), header=header)]
        bindings: list[dict[str, Any]] = [{"column": name_label, "field": "name"}]
        for binding in sorted(definition.attributes, key=lambda item: item.order):
            attribute = model.attribute_type(binding.attributeTypeKey)
            label = labels.take(
                attribute.name if not binding.readOnly else f"{attribute.name} {SUMMARY}"
            )
            value_type = "yesno" if attribute.valueType == "boolean" else attribute.valueType
            cells.append(
                CellSpec(
                    label,
                    value_sql("o", attribute.key, attribute.valueType, yes_no=True),
                    value_type,
                    style=self.date if attribute.valueType == "date" else 0,
                    header=header,
                    list_='"Yes,No"' if value_type == "yesno" else None,
                )
            )
            if binding.readOnly:
                bindings.append({"column": label, "ignore": True})
            else:
                entry = {"column": label, "attributeTypeKey": attribute.key}
                if attribute.valueType == "boolean":
                    entry["valueMap"] = YES_NO
                bindings.append(entry)
        parents = [
            item.key for item in model.objectTypes if item.key in parent_type_keys(model, owned_key)
        ]
        for parent in parents:
            parent_type = model.object_type(parent)
            label = labels.take(
                f"Parent: {parent_type.name}" if len(parents) > 1 else parent_type.name
            )
            cells.append(
                CellSpec(
                    label,
                    sql.SQL(
                        "(SELECT p.name FROM people_records p WHERE p.object_id = o.parent_object_id"
                        " AND p.object_type_key = {})"
                    ).format(sql.Literal(parent)),
                    style=self.fill(parent),
                    header=header,
                    list_=self.rules.get(("parent", plan.object_type_key, sheet.key, parent)),
                )
            )
            bindings.append(
                {"column": label, "parent": {"objectTypeKey": parent, "matchBy": {"field": "name"}}}
            )
        owner_type = model.object_type(plan.object_type_key)
        owner_label = labels.take(owner_type.name)
        cells.append(
            CellSpec(
                owner_label,
                sql.SQL("r.name"),
                style=self.fill(plan.object_type_key),
                header=header,
                list_=self.rules.get(("owner", plan.object_type_key, sheet.key)),
            )
        )
        id_label, version_label, owner_id = (
            labels.take(ID_LABEL),
            labels.take(VERSION_LABEL),
            labels.take(OWNER_ID_LABEL),
        )
        cells += [
            CellSpec(id_label, sql.SQL("o.object_id"), hidden=True, header=self.plain_header),
            CellSpec(
                version_label, sql.SQL("o.version"), "number", hidden=True, header=self.plain_header
            ),
            CellSpec(owner_id, sql.SQL("r.object_id"), hidden=True, header=self.plain_header),
        ]
        bindings.append(
            {
                "column": owner_label,
                "relation": {
                    "relationTypeKey": relation.relation_type_key,
                    "direction": "incoming",
                    "objectTypeKey": plan.object_type_key,
                    "matchBy": {"field": "name"},
                    "idColumn": owner_id,
                },
            }
        )
        titles, count = self._sheet(
            definition.pluralName,
            cells,
            sql.SQL(
                "export_records r JOIN people_links l ON l.anchor_id = r.object_id AND l.part = {}"
                " JOIN people_records o ON o.object_id = l.related_id"
            ).format(sql.Literal(part)),
            sql.SQL("r.name, r.object_id, o.name, o.object_id"),
        )
        application = next(
            (item.key for item in model.applications if owned_key in item.objectTypeKeys), ""
        )
        source = {
            "headerRow": 1,
            "applicationKey": application,
            "objectTypeKey": owned_key,
            "key": {"column": id_label, "versionColumn": version_label},
            "columns": bindings,
        }
        return titles, count, source

    # --- owned records as columns per parent (0.9 J6a) ---

    def owned_columns(
        self, plan: PeoplePlan, sheet: SheetPlan, part: int
    ) -> tuple[list[str], int, dict[str, Any] | None]:
        """One row per exported record and, for each parent (those holding an owned record of an
        exported one, then those added), a column per field (D191–D195). A cell holds its row's
        owned record under that parent; a pair with several holds them as a summary, its version
        cell ``not loaded`` so the import leaves it out (D195)."""
        model = self.model
        relation = sheet.related
        layout = sheet.columns
        owned_key = relation.target_type_keys[0]
        binding = relation.bindings[0]
        scope = (getattr(binding, "features", None) or {}).get("uniqueToAncestorTypeKey")
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "WITH chosen AS ("
                    " SELECT DISTINCT o.parent_object_id AS id FROM people_links l"
                    " JOIN people_records o ON o.object_id = l.related_id"
                    " WHERE l.part = {part} AND o.parent_object_id IS NOT NULL"
                    " UNION SELECT unnest({added}::text[]))"
                    " SELECT p.object_id, p.name, p.object_type_key,"
                    " (SELECT a.name FROM people_ancestors u JOIN people_records a"
                    "  ON a.object_id = u.ancestor_id WHERE u.object_id = p.object_id"
                    "  AND a.object_type_key = {scope} ORDER BY u.level DESC LIMIT 1)"
                    " FROM chosen c JOIN people_records p ON p.object_id = c.id"
                    " ORDER BY 4 NULLS FIRST, p.name, p.object_id"
                ).format(
                    part=sql.Literal(part),
                    added=sql.Literal(list(layout.parents)),
                    scope=sql.Literal(scope),
                )
            )
            parents = cursor.fetchall()
        # A sheet holds 16,384 columns: the owner, a column per parent and field, a version per
        # parent and the ID.
        needed = 2 + len(parents) * (len(layout.fields) + 1)
        if needed > xlsx.SHEET_COLUMNS:
            raise invalid_layout(
                f"Columns per parent would need {needed} columns ({len(parents)} parents); a sheet"
                f" holds {xlsx.SHEET_COLUMNS}. Choose fewer fields, or rows for this relationship",
                f"/people/ownedColumns/{sheet.key}",
            )
        self._fill_grid(part, layout.fields, [parent[0] for parent in parents])
        header = self.header(owned_key)
        labels = Labels()
        owner_label = labels.take(model.object_type(plan.object_type_key).name)
        cells = [
            CellSpec(
                owner_label, sql.SQL("r.name"), style=self.fill(plan.object_type_key), header=header
            )
        ]
        application = next(
            (item.key for item in model.applications if owned_key in item.objectTypeKeys), ""
        )
        bindings: list[dict[str, Any]] = []
        versions: list[CellSpec] = []
        for parent_id, parent_name, parent_type, scope_name in parents:
            # A parent's ancestor the owned records are unique within names a column when higher.
            named = (
                parent_name
                if scope_name is None or parent_type == scope
                else f"{parent_name} · {scope_name}"
            )
            version_label = labels.take(f"Version · {named}")
            for number, field_ in enumerate(layout.fields):
                attribute = None if field_ == "name" else model.attribute_type(field_)
                label = labels.take(f"{'Name' if attribute is None else attribute.name} · {named}")
                value_type = (
                    "text"
                    if attribute is None
                    else "yesno"
                    if attribute.valueType == "boolean"
                    else attribute.valueType
                )
                cells.append(
                    CellSpec(
                        label,
                        sql.SQL("(g.cells -> {} ->> {})").format(
                            sql.Literal(parent_id), sql.Literal(f"f{number}")
                        ),
                        value_type,
                        style=(
                            self.fill(owned_key)
                            if attribute is None
                            else self.date
                            if attribute.valueType == "date"
                            else self.base
                        ),
                        header=header,
                        list_='"Yes,No"' if value_type == "yesno" else None,
                    )
                )
                entry: dict[str, Any] = {
                    "column": label,
                    "relatedRecord": {
                        "relationTypeKey": relation.relation_type_key,
                        "direction": "outgoing",
                        "applicationKey": application,
                        "objectTypeKey": owned_key,
                        "parent": {
                            "objectTypeKey": parent_type,
                            "matchBy": {"field": "id"},
                            "value": parent_id,
                        },
                        **(
                            {"field": "name"} if attribute is None else {"attributeTypeKey": field_}
                        ),
                        "versionColumn": version_label,
                    },
                }
                if value_type == "yesno":
                    entry["valueMap"] = YES_NO
                bindings.append(entry)
            versions.append(
                CellSpec(
                    version_label,
                    sql.SQL("(g.cells -> {} ->> 'v')").format(sql.Literal(parent_id)),
                    "version",
                    hidden=True,
                    header=self.plain_header,
                )
            )
        id_label = labels.take(ID_LABEL)
        cells += [
            *versions,
            CellSpec(id_label, sql.SQL("r.object_id"), hidden=True, header=self.plain_header),
        ]
        titles, _ = self._sheet(
            model.object_type(owned_key).pluralName,
            cells,
            sql.SQL(
                "export_records r LEFT JOIN people_grid g ON g.part = {} AND g.anchor_id = r.object_id"
            ).format(sql.Literal(part)),
            sql.SQL("r.name, r.object_id"),
        )
        count = self.session.scalar(
            text("SELECT count(*) FROM people_links WHERE part = :part"), {"part": part}
        )
        source = {
            "headerRow": 1,
            "applicationKey": self.application_of(plan.object_type_key, plan.application_key),
            "objectTypeKey": plan.object_type_key,
            "record": "existing",
            "key": {"column": id_label, "nameColumn": owner_label},
            "columns": bindings or [{"column": owner_label, "ignore": True}],
        }
        return titles, count or 0, source if bindings else None

    def _fill_grid(self, part: int, fields: Sequence[str], parents: Sequence[str]) -> None:
        """Each exported record's cells per parent as one JSON value, in one statement: per parent
        its owned record's fields (``f0``…, several records' values joined as a summary) and its
        version (``v``; ``not loaded`` for several, D195). The sheet then reads each row by one join
        instead of a query per cell."""
        pairs = [
            (
                sql.Literal("v"),
                sql.SQL("CASE WHEN count(*) = 1 THEN max(o.version)::text ELSE {} END").format(
                    sql.Literal(NOT_LOADED)
                ),
            ),
            *(
                (
                    sql.Literal(f"f{number}"),
                    sql.SQL(
                        "CASE WHEN count(*) = 1 THEN max({value})"
                        " ELSE string_agg({value}, {split} ORDER BY o.name) END"
                    ).format(
                        value=field_sql(self.model, "o", None if field_ == "name" else field_),
                        split=sql.Literal(SPLIT),
                    ),
                )
                for number, field_ in enumerate(fields)
            ),
        ]
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "INSERT INTO people_grid (part, anchor_id, cells)"
                    " SELECT {part}, s.anchor_id, jsonb_object_agg(s.parent_id, s.cell) FROM ("
                    " SELECT l.anchor_id, o.parent_object_id AS parent_id, {object}"
                    " AS cell FROM people_links l JOIN people_records o ON o.object_id = l.related_id"
                    " WHERE l.part = {part} AND o.parent_object_id = ANY({parents}::text[])"
                    " GROUP BY l.anchor_id, o.parent_object_id) s GROUP BY s.anchor_id"
                ).format(
                    part=sql.Literal(part),
                    object=build_object(pairs),
                    parents=sql.Literal(list(parents)),
                )
            )

    # --- a list to choose from (0.9 J6a) ---

    def reference(self, spec: ListSpec, number: int) -> list[str]:
        """A list's sheet: the records its cells may name, by the value they hold, with the name,
        the display field and the path for orientation (D196). Not imported."""
        model = self.model
        definition = model.object_type(spec.far)
        labels = Labels()
        header = self.header(spec.far)
        value_label = labels.take("Name" if spec.field is None else field_label(model, spec.field))
        cells = [
            CellSpec(
                value_label,
                field_sql(model, "o", spec.field),
                style=self.fill(spec.far),
                header=header,
            )
        ]
        if spec.field is not None:
            cells.append(CellSpec(labels.take("Name"), sql.SQL("o.name"), header=header))
        display = definition.displayAttributeTypeKey
        if display and display not in (spec.field, "name") and model.attribute_type(display):
            cells.append(
                CellSpec(
                    labels.take(model.attribute_type(display).name),
                    field_sql(model, "o", display),
                    header=header,
                )
            )
        cells.append(
            CellSpec(
                labels.take("Path"),
                sql.SQL(
                    "(SELECT string_agg(a.name, ' / ' ORDER BY u.level DESC) FROM people_ancestors u"
                    " JOIN people_records a ON a.object_id = u.ancestor_id"
                    " WHERE u.object_id = o.object_id)"
                ),
                header=header,
            )
        )
        titles, _ = self._sheet(
            spec.title,
            cells,
            sql.SQL(
                "people_choices c JOIN people_records o ON o.object_id = c.object_id"
                " WHERE c.list = {}"
            ).format(sql.Literal(number)),
            sql.SQL("1, o.object_id"),
            reserved=True,
        )
        return titles

    # --- writing ---

    def _sheet(
        self,
        title: str,
        cells: list[CellSpec],
        source: sql.Composable,
        order: sql.Composable,
        *,
        reserved: bool = False,
        groups: Sequence[tuple[int, int, str, int]] = (),
        freeze_columns: int = 0,
        soft_lists: frozenset[str] = frozenset(),
        hidden_sheet: bool = False,
        table: str | None = None,
    ) -> tuple[list[str], int]:
        for cell in cells:
            cell.style = cell.style or self.base
            cell.header = cell.header or self.plain_header
        expressions = sql.SQL(", ").join(cell.expression for cell in cells)
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT count(*), {} FROM {}").format(
                    sql.SQL(", ").join(
                        sql.SQL("max(length(({})::text))").format(cell.expression) for cell in cells
                    ),
                    source,
                )
            )
            count, *longest = cursor.fetchone()
        widths = [
            min(WIDTH_MAX, max(WIDTH_MIN, len(cell.label) + 2, (size or 0) + 2))
            if cell.value_type != "date"
            else max(12.0, len(cell.label) + 2)
            for cell, size in zip(cells, longest, strict=True)
        ]
        letters = [xlsx.column(index) for index in range(1, len(cells) + 1)]
        with self.connection.cursor(name=f"people_{len(self.book.titles)}") as cursor:
            cursor.itersize = FETCH_ROWS
            cursor.execute(
                sql.SQL("SELECT {} FROM {} ORDER BY {}").format(expressions, source, order)
            )
            return self.book.plain(
                xlsx.PlainSheet(
                    title=title,
                    labels=[cell.label for cell in cells],
                    header_styles=[cell.header for cell in cells],
                    widths=widths,
                    hidden=[cell.hidden for cell in cells],
                    count=count,
                    rows=cursor,
                    encode=row_encoder(letters, cells, title),
                    lists=[
                        (letter, cell.list_)
                        for letter, cell in zip(letters, cells, strict=True)
                        if cell.list_
                    ],
                    reserved=reserved,
                    groups=groups,
                    freeze_columns=freeze_columns,
                    soft_lists=soft_lists
                    | {
                        letter
                        for letter, cell in zip(letters, cells, strict=True)
                        if cell.soft and cell.list_
                    },
                    hidden_sheet=hidden_sheet,
                    table=table,
                )
            ), count


def relation_label(model: EngineModel, column: RelatedColumn) -> str:
    relation = model.relation_type(column.relation_type_key)
    if column.direction == "incoming":
        return getattr(relation, "reverseName", None) or relation.name
    return relation.name


def built_in(key: str, alias: str = "r") -> sql.Composable:
    if key == "id":
        return sql.SQL(f"{alias}.object_id")
    if key == "path":
        return sql.SQL(f"{alias}.path")
    column = sql.Identifier("created_at" if key == "createdAt" else "updated_at")
    return sql.SQL(
        "(SELECT to_char(x.{} AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') FROM objects x"
        f" WHERE x.id = {alias}.object_id)"
    ).format(column)


def row_encoder(
    letters: Sequence[str], cells: Sequence[CellSpec], title: str = ""
) -> Callable[[Sequence[Any], int], str]:
    """Each row's cells, every one written with its style so its border shows (D199): typed by
    the column's value type; a summary of several values, or a version cell's mark, as text. A text
    a cell cannot hold is refused, naming the record (by the sheet's ID column) and the field."""
    id_index = next(
        (index for index, cell in enumerate(cells) if cell.label.startswith(ID_LABEL)), None
    )

    def encode(row: Sequence[Any], number: int) -> str:
        parts = []
        for index, cell in enumerate(cells):
            ref = f"{letters[index]}{number}"
            value = row[index]
            if isinstance(value, str) and len(value) > xlsx.CELL_CHARACTERS:
                raise text_too_long(
                    title,
                    number,
                    None if id_index is None else row[id_index],
                    cell.label,
                    len(value),
                )
            if value is None:
                parts.append(xlsx.text_cell(ref, None, cell.style))
            elif cell.value_type in {"number", "version"}:
                text_value = str(value)
                parts.append(
                    xlsx.number_cell(ref, text_value, cell.style)
                    if text_value.isdigit()
                    else xlsx.text_cell(ref, text_value, cell.style)
                )
            elif cell.value_type in {"text", "yesno", "longText", "dateTime", "json"} or (
                isinstance(value, str) and SPLIT in value
            ):
                parts.append(xlsx.text_cell(ref, str(value), cell.style))
            else:
                parts.append(xlsx.cell(ref, value, cell.value_type, cell.style))
        return "".join(parts)

    return encode


class Labels:
    """A sheet's header labels, each unlike the others (the import reads a column by its label)."""

    def __init__(self) -> None:
        self.taken: set[str] = set()

    def take(self, label: str) -> str:
        found, number = label, 1
        while found.lower() in self.taken:
            number += 1
            found = f"{label} {number}"
        self.taken.add(found.lower())
        return found


def described(
    *,
    collection: str,
    object_type_key: str | None,
    job_id: str,
    workspace_key: str,
    view: dict[str, str] | None = None,
) -> dict[str, Any]:
    """What the hidden sheet says about the workbook: whose collection it is and when it was
    written, which the import page shows (D185)."""
    return {
        "objectTypeKey": object_type_key,
        "collection": collection,
        "workspaceKey": workspace_key,
        "exportJobId": job_id,
        "exportedAt": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        **({"view": view} if view else {}),
    }
