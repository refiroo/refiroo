"""The parameters of a model draft's operation kinds, described for the OpenAPI document.

One table per kind, beside the registry in ``engine/model/authoring/kinds.py`` (``PARAMETERS``): for
each parameter its JSON schema type, whether the kind refuses its absence (``missingParameter``) and
what it is. A test holds the two together: every registry parameter is described, none is extra, and
a kind that names a parameter required refuses an operation without it.
"""

from dataclasses import replace

from .operation_description import (
    ANY,
    BOOLEAN,
    INTEGER,
    OBJECT,
    TEXT,
    Param,
    array,
    cond,
    either,
    nullable,
    one_of,
    opt,
    req,
    shape,
)

_VALUE_TYPES = ("text", "longText", "integer", "decimal", "boolean", "date", "dateTime", "json")
_CARDINALITIES = ("one-to-one", "one-to-many", "many-to-one", "many-to-many")

_ADD_POSITION = (
    "Where it goes in the list, counting from 0; the end when left out. Beyond the end it is "
    "refused as `outOfRange`."
)
_MOVE_POSITION = "The new place in the list, counting from 0; `outOfRange` beyond the last place."

_NULL_OFF = "`null` leaves the setting off."


def _app(what: str = "Key of the application.") -> Param:
    return req(TEXT, what)


def _type(what: str = "Key of the object type.") -> Param:
    return req(TEXT, what)


_OPEN_KEY = opt(
    TEXT,
    "The new element's key. Generated from its name when left out; refused as `keyTaken` when it "
    "is already used.",
)

_TARGET_WHEN = "The target is named by `view`, by `detail`, or by `panel` together with `detail`."
# The target a view-item kind names: a view, a detail page or one panel of a detail page.
_TARGET: dict[str, Param] = {
    "applicationKey": _app(),
    "view": cond(TEXT, "Key of the view, when the target is a view.", _TARGET_WHEN),
    "detail": cond(
        TEXT,
        "Key of the object type whose detail page it is, when the target is a detail page or a panel.",
        _TARGET_WHEN,
    ),
    "panel": cond(
        TEXT, "Key of the panel, when the target is a panel of the page `detail`.", _TARGET_WHEN
    ),
}

_ELEMENT = shape(
    {
        "applicationKey": opt(
            TEXT, "Key of an application, or of the application holding the view, panel or group."
        ),
        "objectType": opt(TEXT, "Key of an object type."),
        "attributeType": opt(TEXT, "Key of an attribute type."),
        "relationType": opt(TEXT, "Key of a relation type."),
        "view": opt(TEXT, "Key of a view of the application."),
        "detail": opt(TEXT, "Key of the object type whose detail page holds the panel."),
        "panel": opt(TEXT, "Key of a panel of that detail page."),
        "group": opt(TEXT, "Key of a navigation group of the application."),
    },
    "Names the element by its keys, in exactly one of these shapes: `{applicationKey}`, "
    "`{objectType}`, `{attributeType}`, `{relationType}`, `{applicationKey, view}`, "
    "`{applicationKey, detail, panel}` or `{applicationKey, group}`.",
)

_RELATION_NEW = shape(
    {
        "name": req(TEXT, "Name read from the first type to the second."),
        "reverseName": req(TEXT, "Name read from the second type back to the first."),
        "key": opt(TEXT, "Key of the new relation type; generated when left out."),
        "reverseKey": opt(TEXT, "Key of its reverse side; generated when left out."),
        "isOriented": opt(BOOLEAN, "Whether the relation type is oriented (default true)."),
    },
    "A new relation type to add.",
)

_PARENT = nullable(
    shape(
        {
            "objectTypes": req(array(TEXT), "Keys of the parent object types; at least one."),
            "relationType": req(
                either(TEXT, _RELATION_NEW),
                "The containment relation type: the key of an existing one, or a new one "
                "(`name` and `reverseName`, optionally `key` and `reverseKey`).",
            ),
            "optional": opt(
                BOOLEAN,
                "Whether a record may also stand at the top level, without a parent (default false).",
            ),
        },
        "Where records of the type stand: under one of these parent types. `null` is the top level.",
    )
)

_SOURCE_KEY = nullable(
    shape(
        {
            "attributeTypeKey": opt(TEXT, "Key of a unique attribute that finds a row's record."),
            "column": opt(TEXT, "Header of a column holding the record's public ID."),
            "field": opt(one_of("name"), "`name`: the record is found by its name."),
        },
        "What finds a row's existing record: exactly one of `attributeTypeKey`, `column` or "
        "`field`. `null` takes the key away.",
    )
)

_SOURCE_PARENT = nullable(
    shape(
        {
            "objectTypeKey": req(TEXT, "Key of the parent's object type."),
            "matchBy": req(
                shape(
                    {
                        "field": opt(
                            one_of("name", "id"), "Match the record's name or its public ID."
                        ),
                        "attributeTypeKey": opt(TEXT, "Match the value of this attribute."),
                    },
                    "Exactly one of `field` or `attributeTypeKey`.",
                ),
                "How the parent record is found.",
            ),
            "value": req(TEXT, "The value that finds the parent record, the same for every row."),
            "missing": opt(
                one_of("create", "refuse"),
                "`create` makes the parent when none matches (match by name only); `refuse`, the "
                "default, refuses every row.",
            ),
        },
        "The one parent every row of the source's records stands under. `null` takes it away.",
    )
)

_BLOCK = nullable(
    shape(
        {
            "firstColumn": req(TEXT, "Letter of the block's first column, such as `B`."),
            "lastColumn": req(TEXT, "Letter of the block's last column."),
            "lastRow": opt(
                INTEGER, "Number of the block's last row; the sheet's end when left out."
            ),
        },
        "The rectangle of the sheet the source reads; its first row is the header row. `null` is "
        "the whole sheet.",
    )
)

_COLUMN_WHEN = "The column is named by `column` or by `letter`, not both."
_COLUMN = cond(TEXT, "Header text of the column.", _COLUMN_WHEN)
_LETTER = cond(
    TEXT,
    "Sheet letter of the column (one to three capitals, such as `AJ`), which reaches a column whose "
    "header cell is empty.",
    _COLUMN_WHEN,
)
_SOURCE = req(TEXT, "Id of the source in the draft's import profile.")

_NO_DEFINITION = "Needed unless `definition` is given."
_ENTRY_WHEN = "The entry is named by `collection` or by `view`, not both."
_DIRECTION = one_of("outgoing", "incoming")

# One entry per public kind, in the registry's names.
PARAMETERS: dict[str, dict[str, Param]] = {
    "addApplication": {
        "key": _OPEN_KEY,
        "name": req(TEXT, "The application's name."),
        "description": opt(TEXT, "A short description."),
        "icon": opt(TEXT, "Name of the icon shown for it."),
        "color": opt(TEXT, "Its colour."),
        "position": opt(INTEGER, _ADD_POSITION),
    },
    "addAttributeType": {
        "key": _OPEN_KEY,
        "name": req(TEXT, "The attribute type's name."),
        "valueType": opt(
            one_of(*_VALUE_TYPES), "The kind of value it holds; `text` when left out."
        ),
        "features": opt(
            OBJECT,
            "Feature switches of the attribute type, such as `unique`, `searchable`, `filterable` or "
            "`sortable`, each true or false.",
        ),
        "validation": opt(
            OBJECT, "Limits its values must meet, such as `minimum` and `maximum` for numbers."
        ),
        "description": opt(TEXT, "A short description."),
    },
    "addConsumerApi": {
        "name": cond(TEXT, "The consumer API's name.", _NO_DEFINITION),
        "key": _OPEN_KEY,
        "exposes": cond(
            array(TEXT),
            "Keys of the object types the API exposes; at least one.",
            _NO_DEFINITION,
        ),
        "position": opt(INTEGER, _ADD_POSITION),
        "definition": opt(
            OBJECT,
            "A whole consumer API definition to put back as it was, with its own `key`. Used when "
            "undoing a removal; given, `name` and `exposes` are not.",
        ),
    },
    "addDetailPage": {
        "applicationKey": _app(),
        "objectType": _type("Key of the object type, which the application must list."),
        "page": opt(
            OBJECT,
            "The detail page as the model holds it (its `panels`, `header` and `breadcrumbs`). The "
            "standard page is generated when left out; `objectTypeKey` is set from `objectType`.",
        ),
        "position": opt(INTEGER, _ADD_POSITION),
    },
    "addNavigationGroup": {
        "applicationKey": _app(),
        "key": _OPEN_KEY,
        "label": req(TEXT, "The group's label in the navigation."),
        "collapsed": opt(BOOLEAN, "Whether the group starts collapsed (default false)."),
        "position": opt(INTEGER, _ADD_POSITION),
        "collections": opt(
            array(either(TEXT, shape({"view": req(TEXT, "Key of a view of the application.")}))),
            "The group's entries in order: object type keys (their collections), or `{view}` for a "
            "view of any kind. Empty when left out.",
        ),
    },
    "addObjectType": {
        "applicationKey": _app("Key of the application the type is listed in."),
        "key": _OPEN_KEY,
        "name": req(TEXT, "The object type's name."),
        "pluralName": opt(TEXT, "Its plural name; the name followed by `s` when left out."),
        "parent": req(
            _PARENT,
            "Where records of the type stand: under parent types through a containment relation "
            "type, or `null` for the top level. Always given.",
        ),
        "displayAttribute": opt(TEXT, "Key of the attribute type that names a record in lists."),
        "description": opt(TEXT, "A short description."),
        "icon": opt(TEXT, "Name of the icon shown for it."),
        "layout": opt(
            BOOLEAN,
            "Whether to add a table view and a detail page for the type (default true).",
        ),
    },
    "addPanel": {
        "applicationKey": _app(),
        "detail": req(TEXT, "Key of the object type whose detail page gets the panel."),
        "show": req(
            shape(
                {
                    "relations": opt(
                        shape(
                            {
                                "relation": req(TEXT, "Key of the relation type."),
                                "direction": req(
                                    _DIRECTION,
                                    "`outgoing` shows the relationships the type holds, "
                                    "`incoming` those it receives.",
                                ),
                            }
                        ),
                        "Show the records of one relationship of the type.",
                    ),
                    "children": opt(
                        shape(
                            {
                                "objectTypeKeys": req(
                                    array(TEXT),
                                    "Keys of the contained types to show, each once.",
                                )
                            }
                        ),
                        "Show the records the type contains.",
                    ),
                },
                "What the panel shows: exactly one of `relations` or `children`.",
            ),
            "What the panel shows: `{relations: {relation, direction}}` or "
            "`{children: {objectTypeKeys}}`.",
        ),
        "region": opt(one_of("main", "side"), "Where it stands on the page; `main` when left out."),
        "title": opt(TEXT, "The panel's title; not empty. A title is made when left out."),
        "key": opt(
            TEXT, "The panel's key; generated when left out, `keyTaken` when the page has it."
        ),
    },
    "addRelationType": {
        "key": _OPEN_KEY,
        "reverseKey": opt(
            TEXT, "Key of the reverse side; generated from `reverseName` when left out."
        ),
        "name": req(TEXT, "Name read from the first type to the second."),
        "reverseName": req(TEXT, "Name read from the second type back to the first."),
        "isOriented": opt(
            BOOLEAN,
            "Whether deleting a record removes the relationships it points to (default true).",
        ),
    },
    "addSource": {
        "id": opt(TEXT, "Id of the new source; generated from the sheet and type when left out."),
        "sheet": req(TEXT, "Name of the sheet in the draft's profiled source file."),
        "headerRow": opt(
            INTEGER, "Number of the sheet's header row, from 1; the row the file's profile found."
        ),
        "block": opt(_BLOCK, "Limits the source to a block of the sheet."),
        "applicationKey": opt(
            TEXT,
            "Application the records are loaded in; the first one listing the type when left out.",
        ),
        "objectType": _type("Key of the object type the rows load."),
        "key": opt(_SOURCE_KEY, "What finds a row's existing record."),
        "parent": opt(_SOURCE_PARENT, "The one parent every row stands under."),
        "position": opt(INTEGER, _ADD_POSITION),
    },
    "addValuesToList": {
        "source": _SOURCE,
        "column": _COLUMN,
        "letter": _LETTER,
        "create": opt(
            BOOLEAN,
            "`true` (the default) creates the records the column names that do not exist; "
            "`false` stops creating them.",
        ),
    },
    "addView": {
        "applicationKey": _app(),
        "view": req(
            shape(
                {
                    "key": opt(
                        TEXT, "The view's key; free in the application. Generated for a table."
                    ),
                    "name": opt(TEXT, "The view's name."),
                    "type": opt(TEXT, "The view's type, such as `table`; `table` when left out."),
                    "objectTypeKey": opt(TEXT, "Key of the object type a table view lists."),
                },
                "A view as the model holds it. Giving only a table's `objectTypeKey` (and optionally "
                "`key` and `name`) generates the standard table view.",
                closed=False,
            ),
            "The view to add.",
        ),
        "position": opt(INTEGER, _ADD_POSITION),
        "default": opt(
            BOOLEAN,
            "Whether it becomes the application's default view (default false; the first view "
            "always does).",
        ),
    },
    "allowRelation": {
        "relationType": req(TEXT, "Key of the relation type."),
        "from": _type("Key of the object type the relationship starts from."),
        "to": _type("Key of the object type it reaches."),
        "cardinality": opt(
            one_of(*_CARDINALITIES),
            "How many records each side may relate; `many-to-many` when left out.",
        ),
        "required": opt(
            BOOLEAN, "Whether a record of the `to` type needs the relationship (default false)."
        ),
        "layout": opt(
            BOOLEAN, "Whether to add the relationship to the types' detail pages (default true)."
        ),
    },
    "attachAttribute": {
        "objectType": _type(),
        "attributeType": req(TEXT, "Key of the attribute type to bind."),
        "required": opt(BOOLEAN, "Whether a record must hold a value (default false)."),
        "readOnly": opt(
            BOOLEAN, "Whether the value can no longer be edited by a person (default false)."
        ),
        "position": opt(INTEGER, _ADD_POSITION),
        "layout": opt(
            BOOLEAN, "Whether to add the attribute to the type's pages and views (default true)."
        ),
    },
    "convertAttributeToListType": {
        "objectType": _type("Key of the object type that holds the attribute."),
        "attributeType": req(TEXT, "Key of the attribute to turn into a list type."),
        "key": opt(TEXT, "Key of the new list type; generated from `name` when left out."),
        "name": req(TEXT, "Name of the new list type."),
        "pluralName": opt(TEXT, "Its plural name; the name followed by `s` when left out."),
        "relationType": req(
            either(TEXT, _RELATION_NEW),
            "The relation type that links the object type to the list type: the key of an existing "
            "one, or a new one (`name` and `reverseName`).",
        ),
    },
    "detachAttribute": {
        "objectType": _type(),
        "attributeType": req(TEXT, "Key of the attribute type to unbind."),
    },
    "disallowRelation": {
        "relationType": req(TEXT, "Key of the relation type."),
        "from": _type("Key of the object type the relationship starts from."),
        "to": _type("Key of the object type it reaches."),
    },
    "ignoreColumn": {"source": _SOURCE, "column": _COLUMN, "letter": _LETTER},
    "ignoreSheet": {"sheet": req(TEXT, "Name of the sheet in the draft's profiled source file.")},
    "insertConsumerApiPart": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "pointer": req(
            TEXT,
            "JSON pointer below the definition to the list or keyed map to insert into, such as "
            "`/object/fields`. Not empty.",
        ),
        "key": opt(TEXT, "The new member's name, when the target is a keyed map."),
        "value": req(ANY, "The member or item to insert. Not null."),
        "position": opt(INTEGER, "Where it goes, counting from 0; the end when left out."),
    },
    "insertViewItem": {
        **_TARGET,
        "list": req(
            TEXT,
            "Name of the list inside the target, such as `columns`, `fields` or, for a detail page, "
            "`panels`.",
        ),
        "item": req(
            ANY,
            "The item to insert: the field or key as text, or, for a detail page's `panels`, a "
            "panel object with a `key`.",
        ),
        "position": opt(INTEGER, _ADD_POSITION),
    },
    "listObjectType": {
        "applicationKey": _app("Key of the application that will list the type."),
        "objectType": _type("Key of the object type to list there."),
    },
    "mapColumn": {
        "source": _SOURCE,
        "column": _COLUMN,
        "letter": _LETTER,
        "binding": req(
            shape(
                {
                    "field": opt(one_of("name"), "`name`: the column fills the record's name."),
                    "attributeTypeKey": opt(TEXT, "Key of the attribute the column fills."),
                    "parent": opt(OBJECT, "The column names the record's parent."),
                    "relation": opt(OBJECT, "The column names the records to relate."),
                    "relatedRecord": opt(OBJECT, "The column fills a related record."),
                    "valueMap": opt(TEXT, "Name of a value map applied to the cell first."),
                },
                "What the column fills, as an import profile's column binding states it, without "
                "the column's own name: exactly one of `field`, `attributeTypeKey`, `parent`, "
                "`relation` or `relatedRecord`, optionally with `valueMap`.",
            ),
            "What the column fills.",
        ),
    },
    "mergeObjectTypes": {
        "into": _type("Key of the object type that stays."),
        "from": _type("Key of the object type merged into it; it goes."),
    },
    "moveAttribute": {
        "attributeType": req(TEXT, "Key of the attribute type whose binding moves."),
        "from": _type("Key of the object type it leaves."),
        "to": _type("Key of the object type it moves to."),
        "layout": opt(
            BOOLEAN, "Whether to place it on the target's pages and views (default true)."
        ),
    },
    "moveConsumerApiPart": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "pointer": req(TEXT, "JSON pointer below the definition to the member or item to move."),
        "position": req(INTEGER, "Its new place, counting from 0, within its list or map."),
    },
    "moveViewItem": {
        **_TARGET,
        "list": req(TEXT, "Name of the list inside the target, such as `columns` or `panels`."),
        "item": req(
            TEXT, "The item to move: the field or key as text, or a panel's key in `panels`."
        ),
        "position": req(INTEGER, _MOVE_POSITION),
    },
    "placeCollection": {
        "applicationKey": _app(),
        "collection": cond(
            TEXT,
            "Key of the object type whose collection to place.",
            _ENTRY_WHEN,
        ),
        "view": cond(
            TEXT,
            "Key of a view of the application to place (any kind).",
            _ENTRY_WHEN,
        ),
        "group": opt(
            nullable(TEXT),
            "Key of the navigation group to place it in; `null` takes the entry out of its group.",
        ),
        "position": opt(INTEGER, "Its place in the group, counting from 0; the end when left out."),
    },
    "raiseConsumerApiVersion": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "version": opt(
            INTEGER,
            "The new contract version, above the current one; the next one when left out.",
        ),
        "keep": opt(
            BOOLEAN,
            "`true` (the default) keeps the definition the base release served readable beside "
            "the new one; `false` stops serving it.",
        ),
        "deprecated": opt(
            TEXT, "The day the kept version was superseded, `YYYY-MM-DD`; today when left out."
        ),
    },
    "removeApplication": {"applicationKey": _app()},
    "removeAttributeType": {"attributeType": req(TEXT, "Key of the attribute type.")},
    "removeConsumerApi": {"consumerApi": req(TEXT, "Key of the consumer API.")},
    "removeConsumerApiPart": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "pointer": req(TEXT, "JSON pointer below the definition to the member or item to remove."),
    },
    "removeConsumerApiVersion": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "version": req(INTEGER, "The earlier contract version to stop serving."),
    },
    "removeDetailPage": {
        "applicationKey": _app(),
        "objectType": _type("Key of the object type whose detail page goes."),
    },
    "removeNavigationGroup": {
        "applicationKey": _app(),
        "group": req(TEXT, "Key of the navigation group."),
    },
    "removeObjectType": {"objectType": _type()},
    "removeRelationType": {"relationType": req(TEXT, "Key of the relation type.")},
    "removeSource": {"source": _SOURCE},
    "removeView": {
        "applicationKey": _app(),
        "view": req(TEXT, "Key of the view."),
        "unlist": opt(
            BOOLEAN,
            "Whether the object types only this view needed also leave the application's listing "
            "(default false).",
        ),
    },
    "removeViewItem": {
        **_TARGET,
        "list": req(TEXT, "Name of the list inside the target, such as `columns` or `panels`."),
        "item": req(
            TEXT, "The item to remove: the field or key as text, or a panel's key in `panels`."
        ),
    },
    "setApplicationProperty": {
        "applicationKey": _app(),
        "property": req(one_of("defaultView"), "The property to set."),
        "value": req(TEXT, "Key of one of the application's views."),
    },
    "setAttributeBinding": {
        "objectType": _type(),
        "attributeType": req(TEXT, "Key of the bound attribute type."),
        "required": opt(nullable(BOOLEAN), "Whether a record must hold a value. " + _NULL_OFF),
        "readOnly": opt(
            nullable(BOOLEAN), "Whether the value can no longer be edited by a person. " + _NULL_OFF
        ),
        "position": opt(INTEGER, _MOVE_POSITION),
        "ui": opt(
            shape(
                {
                    "hidden": opt(nullable(BOOLEAN), "Hide the attribute on forms and pages."),
                    "helpText": opt(nullable(TEXT), "Help text shown beside the attribute."),
                },
                "Display hints; a `null`, `false` or empty hint takes it away.",
            ),
            "Display hints for the attribute on this type.",
        ),
    },
    "setAttributeTypeFeatures": {
        "attributeType": req(TEXT, "Key of the attribute type."),
        "features": req(
            OBJECT,
            "Feature switches to set, such as `unique`, `searchable`, `filterable` or `sortable`. "
            "A feature set to `null` is taken away; the others are left as they are.",
        ),
    },
    "setAttributeTypeProperty": {
        "attributeType": req(TEXT, "Key of the attribute type."),
        "property": req(
            one_of("minimum", "maximum", "hidden", "helpText"),
            "`minimum` or `maximum` bound the values of an integer or decimal type; `hidden` and "
            "`helpText` are display hints.",
        ),
        "value": opt(
            ANY,
            "A number for `minimum` and `maximum` (the minimum must not exceed the maximum), true or "
            "false for `hidden`, text for `helpText`. `null` takes the setting away.",
        ),
    },
    "setCollectionOpening": {
        "applicationKey": _app(),
        "collection": req(TEXT, "Key of the object type whose collection it is."),
        "view": opt(
            nullable(TEXT),
            "Key of the view over that type the entry opens on; `null` is the application's "
            "default view.",
        ),
    },
    "setColumnReading": {
        "source": _SOURCE,
        "column": _COLUMN,
        "letter": _LETTER,
        "reading": req(
            one_of("text", "lookup", "relation", "relationFlag"),
            "How the column is read: as an attribute value (`text`), as the name of a related "
            "record (`lookup`), as one or more related records (`relation`) or as a flag that "
            "relates a record (`relationFlag`).",
        ),
        "attributeTypeKey": cond(
            TEXT, "Key of the attribute the column fills.", "Needed when `reading` is `text`."
        ),
        "relationTypeKey": opt(
            TEXT, "Key of the relation type; kept from the current binding when left out."
        ),
        "objectTypeKey": opt(
            TEXT,
            "Key of the object type the relation reaches; kept from the current binding when left out.",
        ),
        "direction": opt(
            _DIRECTION,
            "`outgoing` (the default) or `incoming`: which end of the relation the row's record is.",
        ),
        "matchBy": opt(
            shape(
                {
                    "field": opt(one_of("name", "id"), "Match the record's name or its public ID."),
                    "attributeTypeKey": opt(TEXT, "Match the value of this attribute."),
                },
                "Exactly one of `field` or `attributeTypeKey`.",
            ),
            "How a cell finds its record, for `relation` and `relationFlag`; by name when left out.",
        ),
        "target": cond(
            TEXT,
            "The record the flag column stands for: its value is matched by `matchBy`.",
            "Needed when `reading` is `relationFlag`.",
        ),
    },
    "setConsumerApiPart": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "pointer": req(
            TEXT,
            "JSON pointer below the definition to the member or item to set, such as "
            "`/object/fields/name`. The empty pointer replaces the whole definition.",
        ),
        "value": opt(
            ANY,
            "The new value. `null` takes an optional member out; for the empty pointer it must be a "
            "definition object.",
        ),
    },
    "setConsumerApiSunset": {
        "consumerApi": req(TEXT, "Key of the consumer API."),
        "version": req(INTEGER, "The earlier contract version whose sunset day is set."),
        "sunset": opt(
            nullable(TEXT),
            "The day that version stops, `YYYY-MM-DD`; `null` takes the announcement back.",
        ),
    },
    "setContainment": {
        "objectType": _type(),
        "parent": cond(
            _PARENT,
            "Where records of the type stand: under parent types, or `null` for the top level. Replaces "
            "the type's present parents.",
            "Needed unless `application` is given.",
        ),
        "application": opt(TEXT, "Key of the application the type moves to."),
        "fromApplication": opt(
            TEXT,
            "Key of the application it leaves; needed only when the type is listed in several.",
        ),
    },
    "setKey": {
        "element": req(
            _ELEMENT,
            "The element to re-key: an application, object type, attribute type, relation type, "
            "view, panel or navigation group. Only an element the draft's base release does not "
            "hold can be re-keyed.",
        ),
        "key": req(TEXT, "The new key; `keyTaken` when already used. References are rewritten."),
        "reverseKey": opt(TEXT, "For a relation type only: the new key of its reverse side."),
    },
    "setLabel": {
        "element": req(
            _ELEMENT,
            "The element whose labels change: an application, object type, attribute type, "
            "relation type, view, panel or navigation group.",
        ),
        "name": opt(
            nullable(TEXT),
            "The name (application, object type, attribute type, relation type, view).",
        ),
        "reverseName": opt(nullable(TEXT), "The reverse name (relation type)."),
        "description": opt(
            nullable(TEXT), "The description (application, object type, attribute type)."
        ),
        "icon": opt(nullable(TEXT), "The icon (application, object type)."),
        "color": opt(nullable(TEXT), "The colour (application)."),
        "pluralName": opt(nullable(TEXT), "The plural name (object type)."),
        "title": opt(nullable(TEXT), "The title (panel)."),
        "label": opt(nullable(TEXT), "The label (navigation group)."),
    },
    "setNavigationGroup": {
        "applicationKey": _app(),
        "group": req(TEXT, "Key of the navigation group."),
        "label": opt(TEXT, "The new label."),
        "collapsed": opt(BOOLEAN, "Whether the group starts collapsed."),
        "position": opt(INTEGER, _MOVE_POSITION),
    },
    "setObjectTypeProperty": {
        "objectType": _type(),
        "property": req(
            one_of(
                "displayAttributeTypeKey",
                "effectivePeriod",
                "atLeastOneOf",
                "parentRelationTypeKeys",
            ),
            "The setting to change: the display attribute, the effective period, the attributes of "
            "which one must be filled, or the parent relationships.",
        ),
        "value": opt(
            ANY,
            "For `displayAttributeTypeKey`, an attribute key bound to the type. For "
            "`effectivePeriod`, `{startAttributeTypeKey, endAttributeTypeKey}`, two different date "
            "attributes of the type. For `atLeastOneOf`, a list of attribute keys bound to the type. "
            "For `parentRelationTypeKeys`, a list of relation type keys allowed to the type. "
            "`null` takes the setting away.",
        ),
    },
    "setProfile": {
        "key": opt(TEXT, "The profile's key."),
        "name": opt(TEXT, "The profile's name."),
        "sources": opt(
            array(OBJECT),
            "The profile's whole list of sources, each as an import profile states one (sheet, "
            "type, columns). Replaces the present sources; ids are generated.",
        ),
        "valueMaps": opt(
            OBJECT,
            "The profile's whole set of value maps: each name maps cell texts to a value or `null`. "
            "Replaces the present maps.",
        ),
    },
    "setRelationRule": {
        "relationType": req(TEXT, "Key of the relation type."),
        "from": _type("Key of the object type the relationship starts from."),
        "to": _type("Key of the object type it reaches."),
        "cardinality": opt(one_of(*_CARDINALITIES), "How many records each side may relate."),
        "required": opt(
            nullable(BOOLEAN),
            "Whether a record of the `to` type needs the relationship. " + _NULL_OFF,
        ),
        "candidates": opt(
            nullable(OBJECT),
            "Which records may be chosen as the relationship's target; `null` allows any.",
        ),
        "uniqueToAncestorTypeKey": opt(
            nullable(TEXT),
            "Key of an ancestor type: each of its records may relate to a given record once; `null` "
            "takes the rule away.",
        ),
        "attributeTypeKeys": opt(
            nullable(array(TEXT)),
            "Keys of the attribute types the relationship itself carries; `null` or an empty list "
            "takes them away.",
        ),
    },
    "setRelationTypeProperty": {
        "relationType": req(TEXT, "Key of the relation type."),
        "property": req(one_of("isOriented"), "The property to set."),
        "value": req(
            nullable(BOOLEAN),
            "Whether deleting a record removes the relationships it points to. Always given; "
            "`null` is the default, oriented.",
        ),
    },
    "setRelease": {
        "key": opt(TEXT, "The release's key."),
        "name": opt(TEXT, "The release's name."),
        "version": opt(TEXT, "The release's version."),
        "schemaVersion": opt(one_of("0.10"), "The model schema version it is written in."),
    },
    "setUnpivot": {
        "source": _SOURCE,
        "columns": req(
            array(TEXT),
            "Header texts of the wide columns, at least two, each once.",
        ),
        "nameColumn": req(
            TEXT, "Name of the new column that holds the header of the column each row came from."
        ),
        "valueColumn": req(TEXT, "Name of the new column that holds the cell."),
    },
    "clearUnpivot": {"source": _SOURCE},
    "setFillDown": {
        "source": _SOURCE,
        "columns": req(array(TEXT), "Header texts of the columns repeated by blanks, each once."),
    },
    "clearFillDown": {"source": _SOURCE},
    "setHeadingRows": {
        "source": _SOURCE,
        "column": req(TEXT, "Header text of the column that holds the heading."),
        "into": req(TEXT, "Name of the new column that holds the heading on the rows beneath it."),
    },
    "clearHeadingRows": {"source": _SOURCE},
    "setSource": {
        "source": _SOURCE,
        "sheet": opt(TEXT, "Name of the sheet in the draft's profiled source file."),
        "headerRow": opt(INTEGER, "Number of the header row, from 1."),
        "block": opt(_BLOCK, "Limits the source to a block of the sheet."),
        "applicationKey": opt(TEXT, "Application the records are loaded in."),
        "objectType": opt(TEXT, "Key of the object type the rows load."),
        "key": opt(_SOURCE_KEY, "What finds a row's existing record."),
        "record": opt(
            nullable(one_of("upsert", "existing")),
            "`upsert` (the default, also `null`) creates and updates records; `existing` only "
            "updates the records found by the key.",
        ),
        "rowsWithoutKey": opt(
            nullable(one_of("refuse", "skip")),
            "What a load does with a row whose key is empty: `refuse` it (the default, also "
            "`null`) or `skip` it. `skip` needs a key.",
        ),
        "parent": opt(_SOURCE_PARENT, "The one parent every row stands under."),
    },
    "setValueMap": {
        "name": req(TEXT, "Name of the value map."),
        "entries": opt(
            nullable(OBJECT),
            "Cell texts mapped to a value, or to `null` for no value. `null` removes the map and "
            "its uses.",
        ),
        "source": opt(
            TEXT, "With `column` or `letter`: id of the source whose column reads through the map."
        ),
        "column": opt(TEXT, "Header of the column that reads through the map."),
        "letter": opt(TEXT, "Sheet letter of the column that reads through the map."),
    },
    "setMissing": {
        "source": _SOURCE,
        "missing": req(
            one_of("report", "delete"),
            "`report` (the default) only reports the type's records that no row names; `delete` "
            "removes them, in a change set only, and needs a source keyed by a column or attribute.",
        ),
    },
    "setValueType": {
        "attributeType": req(TEXT, "Key of the attribute type."),
        "valueType": req(
            nullable(one_of(*_VALUE_TYPES)),
            "The kind of value it holds. Always given; `null` is `text`.",
        ),
        "validation": opt(
            nullable(OBJECT), "Limits its values must meet; left out, they stay as they are."
        ),
    },
    "setViewProperty": {
        **_TARGET,
        "property": req(
            TEXT,
            "The property to set. For a view: `name` or any member of its configuration (not `type` "
            "or `key`). For a panel: `title`, `region`, `visible`, `order` or a member of its "
            "configuration. For a detail page: `header.<name>` or `breadcrumbs.<name>`.",
        ),
        "value": opt(ANY, "The new value."),
    },
    "splitColumn": {
        "source": _SOURCE,
        "column": _COLUMN,
        "letter": _LETTER,
        "delimiter": opt(
            TEXT,
            "The text a cell is cut at into several values; left empty or null, the column stops "
            "splitting. Only a column read as a relation can split.",
        ),
    },
    "splitObjectType": {
        "objectType": _type("Key of the object type to split."),
        "key": opt(TEXT, "Key of the new type; generated from `name` when left out."),
        "name": req(TEXT, "Name of the new type."),
        "pluralName": opt(TEXT, "Its plural name; the name followed by `s` when left out."),
        "attributes": req(array(TEXT), "Keys of the attribute types that move to the new type."),
        "relationType": req(
            either(TEXT, _RELATION_NEW),
            "The relation type that links the two types: the key of an existing one, or a new one "
            "(`name` and `reverseName`).",
        ),
        "cardinality": opt(
            one_of(*_CARDINALITIES),
            "How many records each side may relate; `many-to-many` when left out.",
        ),
    },
    "unlistObjectType": {
        "applicationKey": _app(),
        "objectType": _type("Key of the object type to take out of the listing."),
    },
    "unmapColumn": {"source": _SOURCE, "column": _COLUMN, "letter": _LETTER},
}


def _at_least_one(kind: str, *names: str) -> None:
    """The kind refuses an operation that names none of ``names``: each is needed under that
    condition, which its description says."""
    listed = ", ".join(f"`{name}`" for name in names)
    for name in names:
        PARAMETERS[kind][name] = replace(
            PARAMETERS[kind][name], when=f"At least one of {listed} is needed."
        )


_at_least_one("setAttributeBinding", "required", "readOnly", "position", "ui")
_at_least_one(
    "setLabel",
    "name",
    "reverseName",
    "description",
    "icon",
    "color",
    "pluralName",
    "title",
    "label",
)
_at_least_one("setNavigationGroup", "label", "collapsed", "position")
_at_least_one("setProfile", "key", "name", "sources", "valueMaps")
_at_least_one(
    "setRelationRule",
    "cardinality",
    "required",
    "candidates",
    "uniqueToAncestorTypeKey",
    "attributeTypeKeys",
)
_at_least_one("setRelease", "key", "name", "version", "schemaVersion")
_at_least_one(
    "setSource",
    "sheet",
    "headerRow",
    "block",
    "applicationKey",
    "objectType",
    "key",
    "record",
    "rowsWithoutKey",
    "parent",
)
