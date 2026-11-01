"""An import profile checked against a model and its sources ordered (``engine/imports/profiles.py``).

The model is generated A of the journey configurations. Each binding kind is checked for the
mistakes it can hold, each at its JSON pointer; several mistakes are all reported; the sources load
after the sources whose types they reference, and a cycle is a problem.
"""

import pytest
from configurations import all_configurations

from app.engine.imports.profiles import check_profile, source_order
from app.engine.model.compiler import parse_model
from app.models.imports import ImportProfileDefinition

CONFIGURATION = all_configurations()["generated-a"]
MODEL = parse_model(CONFIGURATION.model)


def k(structure):
    return CONFIGURATION.key(structure)


def app(structure):
    return next(
        a["key"] for a in CONFIGURATION.model["applications"] if k(structure) in a["objectTypeKeys"]
    )


def source(structure, *columns, **extra):
    return {
        "applicationKey": app(structure),
        "objectTypeKey": k(structure),
        "columns": list(columns) or [{"column": "Name", "field": "name"}],
        **extra,
    }


def problems(*sources, **extra):
    profile = ImportProfileDefinition.model_validate({"sources": list(sources), **extra})
    return {(p.path, p.code) for p in check_profile(MODEL, profile)}


def by_name():
    return {"field": "name"}


@pytest.mark.parametrize(
    ("binding", "expected"),
    [
        ({"column": "A", "attributeTypeKey": "nope"}, ("/attributeTypeKey", "UNKNOWN_ATTRIBUTE")),
        (
            {"column": "A", "attributeTypeKey": k("K.code")},
            ("/attributeTypeKey", "ATTRIBUTE_NOT_BOUND"),
        ),
        (
            {"column": "A", "attributeTypeKey": k("R.ro")},
            ("/attributeTypeKey", "ATTRIBUTE_READ_ONLY"),
        ),
        (
            {"column": "A", "attributeTypeKey": k("R.n"), "valueMap": "missing"},
            ("/valueMap", "UNKNOWN_VALUE_MAP"),
        ),
        (
            {"column": "A", "parent": {"objectTypeKey": k("H"), "matchBy": by_name()}},
            ("/parent", "PARENT_NOT_ALLOWED"),
        ),
        (
            {"column": "A", "parent": {"objectTypeKey": "nope", "matchBy": by_name()}},
            ("/parent/objectTypeKey", "UNKNOWN_OBJECT_TYPE"),
        ),
        (
            {
                "column": "A",
                "relation": {
                    "relationTypeKey": "nope",
                    "objectTypeKey": k("K"),
                    "matchBy": by_name(),
                },
            },
            ("/relation/relationTypeKey", "UNKNOWN_RELATION_TYPE"),
        ),
        (
            {
                "column": "A",
                "relation": {
                    "relationTypeKey": k("Bnn"),
                    "objectTypeKey": k("K"),
                    "matchBy": by_name(),
                },
            },
            ("/relation", "RELATION_NOT_ALLOWED"),
        ),
        (
            {
                "column": "A",
                "relation": {
                    "relationTypeKey": k("B11"),
                    "objectTypeKey": k("K"),
                    "matchBy": {"attributeTypeKey": k("H.code")},
                },
            },
            ("/relation/matchBy/attributeTypeKey", "ATTRIBUTE_NOT_BOUND"),
        ),
        (
            {
                "columns": ["A", "B"],
                "relationFlags": {
                    "relationTypeKey": k("B1n"),
                    "objectTypeKey": k("K"),
                    "matchBy": by_name(),
                    "targets": {"A": "One"},
                },
            },
            ("/relationFlags/targets", "FLAG_WITHOUT_TARGET"),
        ),
        (
            {
                "column": "A",
                "relatedRecord": {
                    "relationTypeKey": k("Bown"),
                    "applicationKey": app("D"),
                    "objectTypeKey": k("D"),
                    "parent": {"objectTypeKey": k("R"), "matchBy": by_name(), "value": "x"},
                    "attributeTypeKey": k("K.code"),
                },
            },
            ("/relatedRecord/parent", "PARENT_NOT_ALLOWED"),
        ),
        (
            {
                "column": "A",
                "relatedRecord": {
                    "relationTypeKey": k("Bown"),
                    "direction": "incoming",
                    "applicationKey": app("D"),
                    "objectTypeKey": k("D"),
                    "parent": {"objectTypeKey": k("G"), "matchBy": by_name(), "value": "x"},
                    "attributeTypeKey": k("K.code"),
                },
            },
            ("/relatedRecord", "RELATION_NOT_ALLOWED"),
        ),
    ],
)
def test_each_binding_kind_is_refused_at_its_pointer(binding, expected):
    path, code = expected
    found = problems(source("R", {"column": "Name", "field": "name"}, binding), valueMaps={})
    assert found == {(f"/sources/0/columns/1{path}", code)}


def test_a_containment_is_a_parent_never_a_relationship():
    containment = next(key for key in MODEL.containment_relation_keys(k("C")))
    binding = {
        "column": "A",
        "relation": {
            "relationTypeKey": containment,
            "direction": "incoming",
            "objectTypeKey": k("P"),
            "matchBy": by_name(),
        },
    }
    assert problems(source("C", binding)) == {
        ("/sources/0/columns/0/relation", "RELATION_NOT_ALLOWED")
    }


def test_a_key_must_be_unique_and_bound():
    found = problems(
        source(
            "H",
            {"column": "Code", "attributeTypeKey": k("H.code")},
            key={"attributeTypeKey": k("H.code")},
        ),
        source("R", {"column": "Name", "field": "name"}, key={"attributeTypeKey": k("R.u")}),
    )
    assert found == {
        ("/sources/0/key/attributeTypeKey", "KEY_NOT_UNIQUE"),
        ("/sources/1/key/attributeTypeKey", "KEY_NOT_BOUND"),
    }


def test_a_type_outside_its_application_and_every_problem_are_reported():
    wrong = {**source("K"), "applicationKey": app("H")} if app("K") != app("H") else source("K")
    found = problems(
        wrong,
        source("R", {"column": "A", "attributeTypeKey": "nope"}),
        {
            "applicationKey": "nope",
            "objectTypeKey": "nope",
            "columns": [{"column": "A", "field": "name"}],
        },
    )
    assert ("/sources/0/objectTypeKey", "TYPE_NOT_IN_APPLICATION") in found
    assert ("/sources/1/columns/0/attributeTypeKey", "UNKNOWN_ATTRIBUTE") in found
    assert {
        ("/sources/2/applicationKey", "UNKNOWN_APPLICATION"),
        ("/sources/2/objectTypeKey", "UNKNOWN_OBJECT_TYPE"),
    } <= found


def _ordered(*sources):
    return source_order(MODEL, ImportProfileDefinition.model_validate({"sources": list(sources)}))


def test_sources_load_after_the_types_they_reference_and_otherwise_as_written():
    rooms = source(
        "C", {"column": "Estate", "parent": {"objectTypeKey": k("P"), "matchBy": by_name()}}
    )
    branches = source(
        "H",
        {
            "column": "T",
            "relation": {
                "relationTypeKey": k("Bnn"),
                "objectTypeKey": k("K"),
                "matchBy": by_name(),
            },
        },
        {"column": "Parent", "parent": {"objectTypeKey": k("H"), "matchBy": by_name()}},
    )
    assert _ordered(rooms, source("P"), branches, source("K"), source("R")) == [1, 0, 3, 2, 4]


def test_sources_referencing_each_other_have_no_order():
    branch_to_token = {
        "column": "T",
        "relation": {"relationTypeKey": k("Bnn"), "objectTypeKey": k("K"), "matchBy": by_name()},
    }
    token_from_branch = {
        "column": "B",
        "relation": {
            "relationTypeKey": k("Bnn"),
            "direction": "incoming",
            "objectTypeKey": k("H"),
            "matchBy": by_name(),
        },
    }
    assert _ordered(source("H", branch_to_token), source("K", token_from_branch)) is None
    assert problems(source("H", branch_to_token), source("K", token_from_branch)) == {
        ("/sources", "SOURCE_CYCLE")
    }


def test_a_key_of_several_attributes_needs_no_unique_one_but_each_must_be_bound():
    """AP-D43: the attributes of a combination are checked as a single key is, except that none
    needs to be declared unique."""
    both = {"attributeTypeKeys": [k("H.code"), k("H.rank")]}
    code = {"column": "Code", "attributeTypeKey": k("H.code")}
    rank = {"column": "Rank", "attributeTypeKey": k("H.rank")}
    assert problems(source("H", code, rank, key=both)) == set()
    assert problems(source("H", code, key=both)) == {
        ("/sources/0/key/attributeTypeKeys", "KEY_NOT_BOUND")
    }
    found = problems(
        source("H", code, rank, key={"attributeTypeKeys": [k("H.code"), "nope"]}),
        source("H", code, rank, key={"attributeTypeKeys": [k("H.code"), k("K.code")]}),
    )
    assert found == {
        ("/sources/0/key/attributeTypeKeys", "UNKNOWN_ATTRIBUTE"),
        ("/sources/0/key/attributeTypeKeys", "KEY_NOT_BOUND"),
        ("/sources/1/key/attributeTypeKeys", "ATTRIBUTE_NOT_BOUND"),
        ("/sources/1/key/attributeTypeKeys", "KEY_NOT_BOUND"),
    }
