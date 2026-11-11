"""A schema 0.9 consumer API definition expanded into the internal form (Base 0.9 C18,
``engine/model/consumer_expansion.py``): every default written out, ``code`` in place, ``via`` by
either key, the syntax refused at the author's pointers and the rules' pointers taken back there."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.engine.model.compiler import parse_model
from app.engine.model.consumer_expansion import expand, public_name
from app.engine.model.diagnostics import ModelReferenceError
from app.models.schema import ConsumerApiDocument

STARTER = Path(__file__).resolve().parents[5] / "model" / "rdm-starter.json"
BASE = "/consumerApis/api"


def _model():
    source = json.loads(STARTER.read_text())
    source.pop("consumerApis")
    return parse_model(source)


MODEL = _model()


def _document(**changes: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "key": "api",
        "name": "API",
        "contractVersion": 1,
        "exposes": ["domain", "codelist", "master-value"],
        "object": {
            "fields": {
                "id": {"role": "id"},
                "code": {"role": "code", "from": ["value-code", "codelist-code", "domain-code"]},
                "name": {"role": "name", "from": "name"},
                "masterId": "master-id",
            },
            "parent": ["objectType", "id", "code", "name"],
            "path": True,
            "related": {
                "variants": {"via": "master-value-represented-by-system-value", "fields": {"value": "name"}},
                "translations": {"via": "object-has-translation", "fields": {"text": "translated-name"}},
            },
        },
        "operations": {
            "objects": {},
            "xref": {"matchOn": [{"field": "id", "exact": 1000}, {"field": "code", "exact": 500, "contains": 40}]},
            "resolve": {},
            "lists": {"codelists": {"of": "codelist", "within": {"filter": "domain"}}},
            "events": {"perType": True},
        },
        "filters": {"domain": {"under": ["domain"]}, "codelist": {"under": ["codelist"], "matchOn": ["code", "name"]}},
    }
    document.update(changes)
    return document


def _expanded(document: dict[str, Any]):
    return expand(MODEL, ConsumerApiDocument.model_validate(document))


def _refusal(document: dict[str, Any]) -> tuple[str, str]:
    with pytest.raises(ModelReferenceError) as caught:
        _expanded(document)
    return caught.value.code, caught.value.path


def test_every_default_is_written_out():
    """A public name is the key in PascalCase; perType makes one event per exposed type in exposes
    order; a list within an under filter takes its types; an under filter matches on id, the code
    sources its types bind and name; the parent and path take their own names."""
    definition, _pointers = _expanded(_document())
    assert {key: item.publicName for key, item in definition.objectTypes.items()} == {
        "domain": "Domain", "codelist": "Codelist", "master-value": "MasterValue",
    }
    assert [(event.key, event.objectTypes, event.changes, event.watch) for event in definition.events] == [
        (f"{key}-changed", (key,), ("created", "updated", "deleted"), None) for key in ("domain", "codelist", "master-value")
    ]
    (codelists,) = definition.lists
    assert (codelists.parentParameter.name, codelists.parentParameter.objectTypes) == ("domain", ("domain",))
    assert definition.parameters["domain"].matchFields == ("id", "domain-code", "name")
    assert (definition.object.parent.output, definition.object.path) == ("parent", "path")
    assert definition.object.id.source == ("id",)
    assert all(definition.offers(name) for name in ("objects", "xref", "resolve", "lists", "events"))
    assert public_name("timetable-type") == "TimetableType"


def test_code_stands_for_each_code_source_in_place():
    """C-D135: in matchOn, one rule per source of the code field with the same weights, where code
    stood; in a filter's matchOn, the sources its types bind."""
    definition, pointers = _expanded(_document())
    assert [rule.model_dump(exclude_none=True) for rule in definition.match.own] == [
        {"field": "id", "exact": 1000},
        *({"field": source, "exact": 500, "contains": 40} for source in ("value-code", "codelist-code", "domain-code")),
    ]
    assert definition.parameters["codelist"].matchFields == ("codelist-code", "name")
    assert pointers.authored("/match/own/3/contains") == "/operations/xref/matchOn/1/contains"


def test_via_names_a_relation_by_either_key():
    """A relation's key is the outgoing route, its reverseKey the incoming one; a name that is
    neither is refused at the via."""
    definition, _pointers = _expanded(_document())
    routes = {name: (item.from_.relation, item.from_.direction) for name, item in definition.projections.items()}
    assert routes == {
        "variants": ("system-value-maps-to-master", "incoming"),
        "translations": ("object-has-translation", "outgoing"),
    }
    document = _document()
    document["object"]["related"]["variants"]["via"] = "no-such-relation"
    assert _refusal(document) == ("INVALID_REFERENCE", f"{BASE}/object/related/variants/via")


def test_role_fields_stand_anywhere_and_are_output_first():
    """C-D140 as amended: role fields may follow other fields or stand out of role order, as a tool
    sorting JSON keys leaves them; the definition is the same, roles first in role order and the
    other fields in written order."""
    document = _document()
    fields = document["object"]["fields"]
    document["object"]["fields"] = {key: fields[key] for key in sorted(fields)}
    written, _pointers = _expanded(_document())
    sorted_keys, _pointers = _expanded(document)
    assert sorted_keys == written


def test_the_operations_offered_are_the_ones_listed():
    document = _document()
    for name in ("xref", "resolve", "lists", "events"):
        del document["operations"][name]
    definition, _pointers = _expanded(document)
    assert [name for name in ("objects", "xref", "resolve", "lists", "events") if definition.offers(name)] == ["objects"]


def _with(path: str, value: Any) -> dict[str, Any]:
    document = _document()
    *parents, last = path.split("/")
    node = document
    for part in parents:
        node = node[part]
    node[last] = value
    return document


@pytest.mark.parametrize(
    ("document", "pointer"),
    [
        (_with("filters/domain", {"under": ["domain"], "byType": True}), "/filters/domain"),
        (_with("filters/domain", {"under": ["domain"], "through": ["itself"]}), "/filters/domain/through"),
        (_with("filters/domain", {"onRelated": "variants"}), "/filters/domain"),
        (_with("filters/domain", {"linkedTo": ["domain"]}), "/filters/domain"),
        (_with("object/fields", {"id": {"role": "id"}, "name": {"role": "name", "from": "name"}, "label": {"role": "name", "from": "name"}}), "/object/fields/label/role"),
        (_with("object/fields", {"masterId": "master-id"}), "/object/fields"),
        (_with("object/fields/code", {"role": "code"}), "/object/fields/code"),
        (_with("publicNames", {"system": "System"}), "/publicNames/system"),
        (_with("operations/resolve", {}) | {"operations": {"objects": {}, "resolve": {}}}, "/operations/resolve"),
        (_with("operations/events", {}), "/operations/events"),
        (_with("operations/lists", {"values": {"of": "master-value", "within": {"filter": "type"}}}), "/operations/lists/values/within"),
        (
            _with("object/fields", {"id": {"role": "id"}, "name": {"role": "name", "from": "name"}})
            | {"filters": {"domain": {"under": ["domain"]}}},
            "/operations/xref/matchOn/1/field",
        ),
    ],
    ids=[
        "two verbs", "a part of another verb", "onRelated without matchOn", "linkedTo without through",
        "a role given twice", "no id role", "a field without from",
        "a public name of a type not exposed", "resolve without xref", "events declaring none",
        "within a filter that is not under, without types", "code without a code field",
    ],
)
def test_the_syntax_is_refused_at_the_authors_pointer(document, pointer):
    assert _refusal(document)[1] == f"{BASE}{pointer}"


def test_the_rules_pointers_are_taken_back_to_what_was_written():
    """The rules name the internal form's parts; each maps to the node the author wrote, a node
    written in one piece absorbing what lies below it."""
    _definition, pointers = _expanded(_document())
    assert pointers.authored("/objectTypes/master-value") == "/exposes/2"
    assert pointers.authored("/object/attributes/masterId/source/0") == "/object/fields/masterId"
    assert pointers.authored("/object/code/source/2") == "/object/fields/code/from/2"
    assert pointers.authored("/projections/variants/from/relation") == "/object/related/variants/via"
    assert pointers.authored("/projections/variants/fields/value") == "/object/related/variants/fields/value"
    assert pointers.authored("/parameters/domain/matchFields/1") == "/filters/domain"
    assert pointers.authored("/parameters/codelist/matchFields/0") == "/filters/codelist/matchOn/0"
    assert pointers.authored("/parameters/codelist/objectTypes/0") == "/filters/codelist/under/0"
    assert pointers.authored("/lists/codelists/parentParameter/objectTypes/0") == "/operations/lists/codelists/within/filter"
    assert pointers.authored("/events/codelist-changed/key") == "/operations/events/perType"
    assert pointers.authored("/contractVersion") == "/contractVersion"


def test_an_event_watches_related_blocks_by_name():
    """watch.related names related blocks, as the rest of the definition does; the rules' pointer
    into it is the authored one."""
    event = {
        "key": "values-changed",
        "objectTypes": ["master-value"],
        "changes": ["updated"],
        "watch": {"fields": ["code"], "related": ["variants"]},
    }
    definition, pointers = _expanded(_with("operations/events", {"custom": [event]}))
    (declared,) = definition.events
    assert (declared.watch.fields, declared.watch.projections) == (("code",), ("variants",))
    assert pointers.authored("/events/values-changed/watch/projections/0") == "/operations/events/custom/0/watch/related/0"


# --- the parent's fields and related blocks (0.17 CA1) ----------------------------------------------


def _parent_document(**parent: Any) -> dict[str, Any]:
    document = _document()
    document["object"]["parent"] = {
        "output": "category",
        "fields": {"kind": "objectType", "parentId": "id", "listCode": "codelist-code"},
        "related": {
            "variants": {
                "via": "reference-has-system-representation",
                "fields": {"value": "name"},
                "served": "onRequest",
            }
        },
        **parent,
    }
    return document


def test_the_parent_expands_with_its_blocks_and_their_pointers():
    """The parent's fields take any source and its blocks are written as the object's, ``served``
    included; a filter names one as ``parent.<block>``, and a rule's pointer is taken back to the
    parent's ``related``."""
    definition, pointers = _expanded(_parent_document())
    parent = definition.object.parent
    assert {name: field.source for name, field in parent.fields.items()} == {
        "kind": ("objectType",),
        "parentId": ("id",),
        "listCode": ("codelist-code",),
    }
    assert parent.projections["variants"].served == "onRequest"
    assert definition.projections["variants"].served == "always"
    assert set(definition.blocks()) == {"variants", "translations", "parent.variants"}
    assert definition.on_request() == ("parent.variants",)
    assert pointers.authored("/object/parent/projections/variants/from") == "/object/parent/related/variants/via"


def test_the_parent_has_no_parent_of_its_own():
    """One level: a ``parent`` inside the parent is no part of the syntax."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ConsumerApiDocument.model_validate(_parent_document(parent=["id"]))


def test_the_short_parent_list_names_a_source_by_its_camel_case_words():
    """The list form keys a built-in name by the output its role has on the object and any other
    source by its words in camelCase (``master-id`` is ``masterId``), as the editor proposes."""
    document = _parent_document(fields=["objectType", "id", "name", "codelist-code", "ancestor:domain.domain-code"])
    definition, _pointers = _expanded(document)
    assert list(definition.object.parent.fields) == ["objectType", "id", "name", "codelistCode", "domainCode"]
    assert definition.object.parent.fields["codelistCode"].source == ("codelist-code",)
