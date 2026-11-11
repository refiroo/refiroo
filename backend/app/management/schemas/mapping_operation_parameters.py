"""The parameters of a model mapping's operation kinds, described for the OpenAPI document.

One table per kind, beside the registry in ``engine/moves/mapping_kinds.py`` (``PARAMETERS``): for
each parameter its JSON schema type, whether the kind refuses its absence (``missingParameter``) and
what it is. A test holds the two together, as it does for the model draft's kinds.
"""

from dataclasses import replace

from .operation_description import (
    ANY,
    BOOLEAN,
    OBJECT,
    TEXT,
    Param,
    array,
    cond,
    nullable,
    one_of,
    opt,
    req,
    shape,
)

_SOURCE_TYPE = req(TEXT, "Key of a type of the mapping's source release that the mapping maps.")
_MISSING = one_of("create", "refuse")
_DIRECTION = one_of("outgoing", "incoming")

PARAMETERS: dict[str, dict[str, Param]] = {
    "mapType": {
        "sourceType": req(TEXT, "Key of a type of the source release."),
        "targetType": req(TEXT, "Key of the type of the target release it becomes."),
    },
    "unmapType": {"sourceType": _SOURCE_TYPE},
    "mapAttribute": {
        "sourceType": _SOURCE_TYPE,
        "attribute": req(
            TEXT, "Key of the source attribute, which the source type must bind in its release."
        ),
        "target": cond(
            TEXT,
            "Key of the target attribute it fills, which the mapped target type must bind.",
            "Needed unless `ignore` is true.",
        ),
        "ignore": opt(
            BOOLEAN,
            "`true` leaves the attribute out of the load, with no `target` and no `valueMap`.",
        ),
        "valueMap": opt(
            TEXT, "Name of a value map of the mapping, applied to the value before it is converted."
        ),
    },
    "unmapAttribute": {
        "sourceType": _SOURCE_TYPE,
        "attribute": req(TEXT, "Key of the source attribute whose mapping goes."),
    },
    "mapRelation": {
        "sourceType": _SOURCE_TYPE,
        "relation": req(
            TEXT,
            "Key of the relation type the source type holds at its `from` end; not a containment.",
        ),
        "target": req(
            TEXT,
            "Key of the target relation type it becomes; not a containment, and allowed with the "
            "mapped target type at the `direction` end.",
        ),
        "direction": opt(
            _DIRECTION,
            "Which end of the target relation the mapped type stands at: `outgoing` (the default) "
            "or `incoming`.",
        ),
        "attributes": opt(
            array(
                shape(
                    {
                        "source": req(TEXT, "Key of an attribute the source relationship carries."),
                        "target": req(
                            TEXT, "Key of the attribute of the target relationship it fills."
                        ),
                    }
                )
            ),
            "The relationship's own attributes to carry over, each from a source attribute to a "
            "target one.",
        ),
        "missing": opt(
            nullable(_MISSING),
            "What happens when the related record is not in the target: `create` it by name or "
            "`refuse` the record; `null` is the default.",
        ),
    },
    "unmapRelation": {
        "sourceType": _SOURCE_TYPE,
        "relation": req(TEXT, "Key of the source relation type whose mapping goes."),
    },
    "setDefault": {
        "sourceType": _SOURCE_TYPE,
        "attribute": req(
            TEXT, "Key of the target attribute, which the mapped target type must bind."
        ),
        "value": opt(
            ANY,
            "The value the target attribute takes when the source record gives none; it must suit "
            "the attribute's value type. `null` removes the default.",
        ),
    },
    "setValueMap": {
        "name": req(TEXT, "Name of the value map."),
        "values": opt(
            nullable(OBJECT),
            "Source values mapped to the value they are read as, each a text, number or boolean, or "
            "`null` for no value. `null` removes the map, which no attribute may still use.",
        ),
    },
    "setParent": {
        "sourceType": _SOURCE_TYPE,
        "parent": opt(
            nullable(
                shape(
                    {
                        "from": opt(
                            one_of("source"),
                            "`source`: the record stands under the target record of its source "
                            "parent. Not with `objectTypeKey`.",
                        ),
                        "objectTypeKey": opt(
                            TEXT,
                            "Key of the target type of the parent record, which the mapped target "
                            "type may stand under.",
                        ),
                        "value": opt(
                            TEXT,
                            "With `objectTypeKey`: the name of the one parent record every record "
                            "stands under.",
                        ),
                        "relationTypeKey": opt(
                            TEXT,
                            "Key of the containment relation type, when the target type has "
                            "several.",
                        ),
                        "missing": opt(
                            _MISSING,
                            "`create` makes a parent that is not in the target; `refuse` refuses "
                            "the record.",
                        ),
                    },
                    'Either `{from: "source"}` or `{objectTypeKey, value}`, optionally with '
                    "`relationTypeKey` and `missing`.",
                )
            ),
            "Where a record stands in the target. `null`, or left out, puts it at the top.",
        ),
    },
    "setMatch": {
        "sourceType": _SOURCE_TYPE,
        "match": opt(
            nullable(
                shape(
                    {
                        "attributeTypeKey": opt(
                            TEXT,
                            "Key of a unique attribute of the mapped target type that finds the "
                            "record.",
                        ),
                        "field": opt(one_of("name"), "`name`: the record is found by its name."),
                    },
                    'Either `{attributeTypeKey}` or `{field: "name"}`.',
                )
            ),
            "How a target record that its counterpart or origin does not find is matched. `null`, "
            "or left out, matches none.",
        ),
    },
    "setMissing": {
        "sourceType": _SOURCE_TYPE,
        "relation": opt(
            TEXT,
            "Key of a mapped source relation type. Left out, the setting is the parent's.",
        ),
        "missing": opt(
            nullable(_MISSING),
            "What happens when the record a relationship or the parent names is not in the "
            "target: `create` it by name or `refuse` the record. `null`, or left out, is the "
            "default.",
        ),
    },
    "setReleases": {
        "sourceReleaseId": opt(
            TEXT,
            "Id of the installed release of the source model the mapping is checked against.",
        ),
        "targetReleaseId": opt(
            TEXT,
            "Id of the installed release of the target model the mapping is checked against.",
        ),
    },
}

for _name, _parameter in PARAMETERS["setReleases"].items():
    PARAMETERS["setReleases"][_name] = replace(
        _parameter, when="At least one of `sourceReleaseId` and `targetReleaseId` is needed."
    )
