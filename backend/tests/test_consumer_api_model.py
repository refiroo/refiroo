"""Base 0.9 C1: consumer API definitions in schema 0.8 (CONSUMER_API "Definition shape").

Schema 0.8 accepts ``consumerApis`` and nothing else yet; every reference a definition makes is
checked against its release and refused at its JSON pointer; the definition compiles into the
immutable release; and a candidate release that changes what an active definition's consumers read
is reported by draft compile and release diff and refused at activation until the definition's
``contractVersion`` is raised (C-D2, C-D4, C-D17–C-D20). Model checks run on the starter and on a
copy with every key renamed, so no rule depends on a key.
"""

import copy
import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from model_support import MODEL_PATH, renamed_model

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.compiler import compile_model, parse_model
from app.engine.model.consumer_contract import contract_diagnostics, output_contract
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.database import ModelRuntimeState
from app.models.schema import EngineModel

Keys = Callable[[str], str]
API = "/consumerApis/rdm"


def definition(k: Keys) -> dict[str, Any]:
    """CONSUMER_API's reference definition, reduced to the starter's types."""
    system, language = k("system"), k("language")
    return {
        "key": "rdm",
        "name": "RDM consumer API",
        "contractVersion": 1,
        "objectTypes": {
            k("master-value"): {"publicName": "CodelistValue"},
            k("codelist"): {"publicName": "Codelist"},
            k("domain"): {"publicName": "Domain"},
        },
        "object": {
            "id": {"output": "masterId", "source": [k("master-id"), "id"]},
            "code": {"output": "code", "source": [k("value-code"), k("codelist-code"), k("domain-code")]},
            "name": {"output": "name", "source": ["name"]},
            "active": {"output": "isActive", "source": [k("active")], "default": True},
            "validFrom": {"output": "validFrom", "source": [k("valid-from")]},
            "validTo": {"output": "validTo", "source": [k("valid-to")]},
            "attributes": {
                "valueName": {"source": [k("value-name")]},
                "sortOrder": {"source": [k("sort-order")], "default": 0},
                "description": {"source": [k("description")]},
            },
            "parent": {"output": "parent", "fields": ["objectType", "id", "code", "name"]},
            "path": "path",
            "hierarchy": "hierarchy",
        },
        "projections": {
            "systemVariants": {
                "from": {"relation": k("system-value-maps-to-master"), "direction": "incoming"},
                "fields": {
                    "system": f"ancestor:{system}.name",
                    "value": "name",
                    "valueCode": k("value-code"),
                    "externalId": k("external-id"),
                    "isActive": k("active"),
                },
            },
            "translations": {
                "from": {"relation": k("object-has-translation"), "direction": "outgoing"},
                "fields": {
                    "languageCode": f"ancestor:{language}.{k('language-code')}",
                    "translatedName": k("translated-name"),
                },
            },
        },
        "match": {
            "own": [
                {"field": k("master-id"), "exact": 1000},
                {"field": k("value-code"), "exact": 500, "contains": 40},
                {"field": "name", "exact": 200, "contains": 30},
            ],
            "promoted": [
                {
                    "projection": "systemVariants",
                    "firstMatch": [{"field": "name", "exact": 80}, {"field": k("external-id"), "exact": 75}],
                    "preferTargetTypes": [k("master-value")],
                }
            ],
        },
        "parameters": {
            "type": {"kind": "objectType"},
            "system": {
                "kind": "projection",
                "projection": "systemVariants",
                "matchFields": [f"ancestor:{system}.name", f"ancestor:{system}.{k('system-code')}"],
                "scoresFrom": True,
                "requireMatch": True,
                "targetable": True,
            },
            "codelist": {"kind": "ancestor", "objectTypes": [k("codelist")], "matchFields": ["name", k("codelist-code")]},
            "sameSystem": {
                "kind": "related",
                "objectTypes": [k("master-value")],
                "matchFields": [k("master-id")],
                "via": ["self", "sharedProjection:systemVariants"],
            },
            "language": {
                "kind": "projection",
                "projection": "translations",
                "matchFields": [f"ancestor:{language}.{k('language-code')}"],
                "requireMatch": True,
            },
        },
        "lists": [
            {"key": "codelists", "objectType": k("codelist"), "parentParameter": {"name": "domain", "objectTypes": [k("domain")]}},
            {"key": "values", "objectType": k("master-value"), "parentParameter": {"name": "codelist", "objectTypes": [k("codelist")]}},
            {"key": "all-values", "objectType": k("master-value")},
        ],
    }


@pytest.fixture(params=["starter", "renamed"])
def base(request) -> tuple[dict[str, Any], Keys]:
    """The starter on schema 0.8, as it is or with every key renamed, and its key map."""
    source = json.loads(MODEL_PATH.read_text())
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    source["schemaVersion"] = "0.8"
    return source, lambda key: names.get(key, key)


def with_definition(source: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(source)
    result["consumerApis"] = [item]
    return result


def test_definition_compiles_into_the_release_with_its_output_contract(base):
    source, k = base
    compiled = compile_model(with_definition(source, definition(k)))
    assert compiled.valid, compiled.diagnostics
    canonical = compiled.canonical_model
    # The canonical document keeps the definition's own spelling, `from` included, and reparses to
    # the same hash; a model without definitions has none in its document.
    projection = canonical["consumerApis"][0]["projections"]["systemVariants"]
    assert projection["from"] == {"relation": k("system-value-maps-to-master"), "direction": "incoming"}
    assert "from_" not in projection
    assert compile_model(canonical).model_hash == compiled.model_hash
    assert "consumerApis" not in compile_model(source).canonical_model

    contract = output_contract(compiled.model, compiled.model.consumerApis[0])
    assert contract.types == {k("master-value"): "CodelistValue", k("codelist"): "Codelist", k("domain"): "Domain"}
    assert contract.fields == {
        "masterId": "text",
        "code": "text",
        "name": "text",
        "isActive": "boolean",
        "validFrom": "date",
        "validTo": "date",
        "valueName": "text",
        "sortOrder": "integer",
        # description is longText, which outputs as text (C-D19).
        "description": "text",
        "parent": {"object": {"objectType": "text", "id": "text", "code": "text", "name": "text"}},
        "path": "text",
        "hierarchy": "text[]",
    }
    # Many system values map to a value; a value has many translations: arrays, derived from the model.
    assert contract.projections["systemVariants"]["shape"] == "many"
    assert contract.projections["translations"] == {
        "shape": "many",
        "fields": {"languageCode": "text", "translatedName": "text"},
    }
    assert contract.parameters == {
        "type": "objectType",
        "system": "projection",
        "codelist": "ancestor",
        "sameSystem": "related",
        "language": "projection",
    }


def test_consumer_apis_need_schema_0_8_and_events_wait_for_c9(base):
    source, k = base
    older = with_definition(source, definition(k))
    older["schemaVersion"] = "0.7"
    diagnostic = compile_model(older).diagnostics[0]
    assert (diagnostic.code, diagnostic.path) == ("invalid_model", "/consumerApis")
    assert "0.8" in diagnostic.message

    with_events = definition(k) | {"events": []}
    diagnostic = compile_model(with_definition(source, with_events)).diagnostics[0]
    assert (diagnostic.code, diagnostic.path) == ("unknown_field", "/consumerApis/0/events")


Mutation = Callable[[dict[str, Any], Keys], None]


def _set(path: str, value: Any) -> Mutation:
    """Set a nested key; list indexes and dict keys by '/'-separated path, keys through ``k``."""

    def mutate(item: dict[str, Any], k: Keys) -> None:
        parts = [k(part[1:]) if part.startswith("@") else part for part in path.split("/")]
        target: Any = item
        for part in parts[:-1]:
            target = target[int(part)] if isinstance(target, list) else target[part]
        last = parts[-1]
        resolved = value(k) if callable(value) else value
        if isinstance(target, list):
            target[int(last)] = resolved
        else:
            target[last] = resolved

    return mutate


def _drop(path: str) -> Mutation:
    def mutate(item: dict[str, Any], k: Keys) -> None:
        *parents, last = [k(part[1:]) if part.startswith("@") else part for part in path.split("/")]
        target: Any = item
        for part in parents:
            target = target[int(part)] if isinstance(target, list) else target[part]
        del target[last]

    return mutate


REFUSALS: list[tuple[str, Mutation, str, str]] = [
    ("unknown exposed type", _set("objectTypes/unknown-type", {"publicName": "X"}), "unknown_object_type", "/objectTypes/unknown-type"),
    ("repeated public name", _set("objectTypes/@domain", {"publicName": "Codelist"}), "duplicate_key", "/objectTypes/{domain}/publicName"),
    ("key outside the URL alphabet", _set("key", "RDM"), "invalid_model", "/consumerApis/RDM/key"),
    ("unknown source", _set("object/code/source/1", "no-such-attribute"), "invalid_reference", "/object/code/source/1"),
    ("source no exposed type binds", _set("object/code/source/1", lambda k: k("system-code")), "invalid_reference", "/object/code/source/1"),
    ("sources of different types (C-D19)", _set("object/code/source/1", lambda k: k("sort-order")), "invalid_model", "/object/code/source"),
    ("default of another type", _set("object/active/default", "yes"), "invalid_model", "/object/active/default"),
    ("identity that does not identify", _set("object/id/source/0", lambda k: k("value-code")), "invalid_model", "/object/id/source/0"),
    ("reserved output name", _set("object/attributes/matchScore", lambda k: {"source": [k("value-name")]}), "invalid_model", "/object/attributes/matchScore"),
    ("output name used twice", _set("object/attributes/name", lambda k: {"source": [k("value-name")]}), "duplicate_key", "/object/attributes/name"),
    ("parent code without a code role", _drop("object/code"), "invalid_model", "/object/parent/fields"),
    ("projection over an unknown relation", _set("projections/systemVariants/from/relation", "no-such-relation"), "invalid_reference", "/projections/systemVariants/from/relation"),
    ("projection route no exposed type has", _set("projections/systemVariants/from/direction", "outgoing"), "invalid_reference", "/projections/systemVariants/from"),
    ("projection field of a type that is no ancestor", _set("projections/systemVariants/fields/system", lambda k: f"ancestor:{k('domain')}.name"), "invalid_reference", "/projections/systemVariants/fields/system"),
    ("projection named like an output field", _set("projections/name", lambda k: {"from": {"relation": k("object-has-translation"), "direction": "outgoing"}, "fields": {"n": "name"}}), "duplicate_key", "/projections/name"),
    ("match on a field neither searchable nor unique (C-D20)", _set("match/own/0/field", lambda k: k("sort-order")), "invalid_model", "/match/own/0/field"),
    ("promotion from an unknown projection", _set("match/promoted/0/projection", "nothing"), "invalid_reference", "/match/promoted/0/projection"),
    ("preferred target type not exposed", _set("match/promoted/0/preferTargetTypes/0", lambda k: k("system")), "invalid_reference", "/match/promoted/0/preferTargetTypes/0"),
    ("reserved parameter name", _set("parameters/query", {"kind": "objectType"}), "invalid_model", "/parameters/query"),
    ("crosswalk-like parameter name", _set("parameters/to.system", {"kind": "objectType"}), "invalid_model", "/parameters/to.system"),
    ("ancestor parameter over a type that is no ancestor", _set("parameters/codelist/objectTypes/0", lambda k: k("system")), "invalid_reference", "/parameters/codelist/objectTypes/0"),
    ("related parameter over an unknown route", _set("parameters/sameSystem/via/1", "sharedProjection:nothing"), "invalid_reference", "/parameters/sameSystem/via/1"),
    ("projection parameter on a field the projection lacks", _set("parameters/system/matchFields/1", lambda k: k("codelist-code")), "invalid_reference", "/parameters/system/matchFields/1"),
    ("list key outside the URL alphabet", _set("lists/2/key", "All_Values"), "invalid_model", "/lists/All_Values/key"),
    ("list of a type not exposed", _set("lists/2/objectType", lambda k: k("system")), "invalid_reference", "/lists/all-values/objectType"),
    ("list parent that cannot contain the type", _set("lists/0/parentParameter/objectTypes/0", lambda k: k("master-value")), "invalid_reference", "/lists/codelists/parentParameter/objectTypes/0"),
]


@pytest.mark.parametrize(("label", "mutate", "code", "path"), REFUSALS, ids=[item[0] for item in REFUSALS])
def test_every_reference_is_refused_at_its_pointer(base, label, mutate, code, path):
    source, k = base
    item = definition(k)
    mutate(item, k)
    diagnostics = compile_model(with_definition(source, item)).diagnostics
    assert diagnostics, label
    expected = path.replace("{domain}", k("domain"))
    expected = expected if expected.startswith("/consumerApis/") else f"{API}{expected}"
    assert (diagnostics[0].code, diagnostics[0].path) == (code, expected), diagnostics[0].message
    assert "Consumer API" in diagnostics[0].message or code == "invalid_model"


def test_shape_errors_name_the_body_part(base):
    source, k = base
    for mutate, path in (
        (_set("match/own/0/exact", 0), "/consumerApis/0/match/own/0/exact"),
        (_set("match/own/1", {"field": "name"}), "/consumerApis/0/match/own/1"),
        (_set("parameters/system/kind", "location"), "/consumerApis/0/parameters/system"),
        (_set("contractVersion", 0), "/consumerApis/0/contractVersion"),
    ):
        item = definition(k)
        mutate(item, k)
        diagnostic = compile_model(with_definition(source, item)).diagnostics[0]
        assert diagnostic.path.startswith(path), (diagnostic.path, diagnostic.message)
    duplicate = compile_model({**with_definition(source, definition(k)), "consumerApis": [definition(k)] * 2})
    assert (duplicate.diagnostics[0].code, duplicate.diagnostics[0].path) == ("duplicate_key", API)


def _both(*mutations: Mutation) -> Mutation:
    def mutate(item: dict[str, Any], k: Keys) -> None:
        for mutation in mutations:
            mutation(item, k)

    return mutate


BREAKING: list[tuple[str, Mutation, list[str]]] = [
    ("removes an output field", _drop("object/attributes/sortOrder"), ["/object"]),
    ("retypes an output field", _set("object/attributes/sortOrder", lambda k: {"source": [k("value-name")]}), ["/object"]),
    ("removes a parent field", _set("object/parent/fields", ["objectType", "id", "name"]), ["/object"]),
    ("renames a public type", _set("objectTypes/@domain", {"publicName": "Area"}), ["/objectTypes/{domain}/publicName"]),
    (
        "stops exposing a type",
        _both(_drop("objectTypes/@domain"), _set("object/code/source", lambda k: [k("value-code"), k("codelist-code")])),
        ["/objectTypes"],
    ),
    (
        "removes a projection and the parameter over it",
        _both(_drop("projections/translations"), _drop("parameters/language")),
        ["/projections", "/parameters"],
    ),
    ("removes a projection field", _drop("projections/systemVariants/fields/externalId"), ["/projections/systemVariants/fields"]),
    ("changes a weight (C-D4)", _set("match/own/0/exact", 999), ["/match"]),
    ("removes the lists (C-D18)", _set("lists", []), ["/lists"] * 3),
    ("changes a list's parent parameter (C-D18)", _drop("lists/1/parentParameter"), ["/lists"]),
    ("removes a parameter (C-D18)", _drop("parameters/type"), ["/parameters"]),
    (
        "changes a parameter's kind (C-D18)",
        _set("parameters/type", lambda k: {"kind": "ancestor", "objectTypes": [k("codelist")], "matchFields": ["name"]}),
        ["/parameters/type/kind"],
    ),
]


@pytest.mark.parametrize(("label", "mutate", "paths"), BREAKING, ids=[item[0] for item in BREAKING])
def test_breaking_changes_need_a_higher_contract_version(base, label, mutate, paths):
    source, k = base
    active = parse_model(with_definition(source, definition(k)))
    item = definition(k)
    mutate(item, k)
    candidate = parse_model(with_definition(source, item))
    diagnostics = contract_diagnostics(active, candidate)
    assert {(d.severity, d.code) for d in diagnostics} == {("error", "consumer_contract_version_required")}, label
    assert [d.path for d in diagnostics] == [f"{API}{path.replace('{domain}', k('domain'))}" for path in paths]
    assert all("raise contractVersion above 1" in d.message for d in diagnostics)
    # The same change under a higher contract version is a new contract.
    item["contractVersion"] = 2
    assert contract_diagnostics(active, parse_model(with_definition(source, item))) == []


def test_additions_are_compatible_and_lower_versions_or_removals_are_reported(base):
    source, k = base
    active = parse_model(with_definition(source, definition(k)))
    item = definition(k)
    item["object"]["attributes"]["validity"] = {"source": [k("valid-to")]}
    item["projections"]["systemVariants"]["fields"]["valueName"] = k("value-name")
    item["parameters"]["domain"] = {"kind": "ancestor", "objectTypes": [k("domain")], "matchFields": ["name"]}
    item["lists"].append({"key": "domains", "objectType": k("domain")})
    item["objectTypes"][k("language")] = {"publicName": "Language"}
    assert contract_diagnostics(active, parse_model(with_definition(source, item))) == []

    lower = definition(k) | {"contractVersion": 1}
    higher_active = parse_model(with_definition(source, definition(k) | {"contractVersion": 3}))
    diagnostics = contract_diagnostics(higher_active, parse_model(with_definition(source, lower)))
    assert [(d.code, d.path) for d in diagnostics] == [("consumer_contract_version_decreased", f"{API}/contractVersion")]

    removed = contract_diagnostics(active, parse_model(source))
    assert [(d.severity, d.code, d.path) for d in removed] == [("warning", "consumer_api_removed", API)]


def test_a_cardinality_change_in_the_model_changes_a_projection_shape(base):
    source, k = base
    active = parse_model(with_definition(source, definition(k)))
    changed = with_definition(source, definition(k))
    for binding in changed["objectTypeRelations"]:
        if binding["relationTypeKey"] == k("system-value-maps-to-master"):
            binding["cardinality"] = "one-to-many"
    candidate = parse_model(changed)
    # One system value per master value now: the projection becomes an object or null.
    assert output_contract(candidate, candidate.consumerApis[0]).projections["systemVariants"]["shape"] == "one"
    diagnostics = contract_diagnostics(active, candidate)
    assert [(d.code, d.path) for d in diagnostics] == [
        ("consumer_contract_version_required", f"{API}/projections/systemVariants")
    ]
    assert "from an array to an object or null" in diagnostics[0].message


def _install(source: dict[str, Any], version: str) -> str:
    candidate = copy.deepcopy(source)
    candidate["release"]["version"] = version
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, EngineModel.model_validate(candidate))
        session.commit()
        return release.public_id


def _activate(client: TestClient, release_id: str):
    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        version = state.version
    active = client.get("/api/v1/model").headers["X-Model-Release-Id"]
    return client.post(
        f"/api/v1/model-releases/{release_id}/activation",
        json={"expectedRuntimeVersion": version, "expectedActiveReleaseId": active},
    )


@pytest.fixture
def admin_client(monkeypatch, migrated_database) -> Iterator[TestClient]:
    """Model administration on a database of its own: the test leaves another release active."""
    monkeypatch.setenv("DATABASE_URL", migrated_database("consumer-contract.db"))
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    reload_settings()
    model_registry.clear()
    with TestClient(create_app()) as client:
        yield client
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def test_compile_diff_and_activation_hold_the_active_contract(admin_client):
    """C-D17 at the API: draft compile and release diff report the check, activation refuses a break."""
    client = admin_client
    source = client.get("/api/v1/model").json()
    source["schemaVersion"] = "0.8"
    keys: Keys = lambda key: key
    first = _install(with_definition(source, definition(keys)), "0.9.0-c1-contract")
    activated = _activate(client, first)
    assert activated.status_code == 200, activated.text

    broken_definition = definition(keys)
    del broken_definition["object"]["attributes"]["sortOrder"]
    broken = with_definition(source, broken_definition)
    broken["release"]["version"] = "0.9.0-c1-broken"
    draft = client.post("/api/v1/model-drafts", json={"name": "C1 break", "model": broken})
    assert draft.status_code == 201, draft.text
    compiled = client.post(f"/api/v1/model-drafts/{draft.json()['id']}/compile", json={"expectedVersion": 1}).json()
    assert compiled["valid"] is True
    assert compiled["compatibility"]["classification"] == "compatible"
    contracts = compiled["consumerContracts"]
    assert contracts["classification"] == "version_required"
    assert contracts["activeReleaseId"] == first
    assert [(d["severity"], d["code"], d["path"]) for d in contracts["diagnostics"]] == [
        ("error", "consumer_contract_version_required", f"{API}/object")
    ]

    broken_id = _install(broken, "0.9.0-c1-broken")
    diff = client.get(f"/api/v1/model-releases/{broken_id}/diff", params={"againstReleaseId": first}).json()
    assert diff["consumerContracts"]["classification"] == "version_required"

    refused = _activate(client, broken_id)
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["code"] == "consumer_contract_version_required"
    assert [item["path"] for item in error["details"]] == [f"{API}/object"]
    assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == first

    raised_definition = broken_definition | {"contractVersion": 2}
    raised = _install(with_definition(source, raised_definition), "0.9.0-c1-raised")
    accepted = _activate(client, raised)
    assert accepted.status_code == 200, accepted.text
    assert client.get("/api/v1/model").json()["consumerApis"][0]["contractVersion"] == 2
