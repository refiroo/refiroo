"""Base 0.9 C1 and C18: consumer API definitions (CONSUMER_API "Definition shape"), in schema 0.9.

Every reference a definition makes is checked against its release and refused at its JSON pointer
in the authored document; the definition compiles into the immutable release; and a candidate
release that changes what an active definition's consumers read is reported by draft compile and
release diff and refused at activation until the definition's ``contractVersion`` is raised (C-D2,
C-D4, C-D17–C-D20, C-D132). Model checks run on the starter and on a copy with every key renamed, so
no rule depends on a key.
"""

import copy
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from harness_identity import TestClient
from model_support import MODEL_PATH, renamed_model
from workspace_model_support import DEFAULT_ACTIVATION, default_model

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.compiler import compile_authored_model, compile_model, parse_model
from app.engine.model.consumer_contract import contract_diagnostics, output_contract
from app.engine.model.consumer_definitions import consumer_apis
from app.engine.model.consumer_expansion import expand
from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.model.consumer_rendering import expanded_definition
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.schema import ConsumerApiDocument, EngineModel

Keys = Callable[[str], str]
API = "/consumerApis/rdm"
FIXTURES_08 = Path(__file__).parent / "fixtures" / "consumer_08"
STARTER_08 = FIXTURES_08 / "rdm-starter-0.9.2.json"
# The shipped models and their schema 0.8 originals, kept as C18 rewrote them (C-D138).
# The example model left its 0.8 form in 0.9 K3a (a many-to-one binding, which 0.8 cannot say); its
# conversion was proved equal when C18 made it.
SHIPPED = [(MODEL_PATH, STARTER_08)]


def definition(k: Keys) -> dict[str, Any]:
    """CONSUMER_API's reference definition, reduced to the starter's types."""
    system, language = k("system"), k("language")
    return {
        "key": "rdm",
        "name": "RDM consumer API",
        "contractVersion": 1,
        "exposes": [k("master-value"), k("codelist"), k("domain")],
        "publicNames": {k("master-value"): "CodelistValue", k("codelist"): "Codelist", k("domain"): "Domain"},
        "object": {
            "fields": {
                "masterId": {"role": "id"},
                "code": {"role": "code", "from": [k("value-code"), k("codelist-code"), k("domain-code")]},
                "name": {"role": "name", "from": "name"},
                "isActive": {"role": "active", "from": k("active"), "default": True},
                "validFrom": {"role": "validFrom", "from": k("valid-from")},
                "validTo": {"role": "validTo", "from": k("valid-to")},
                "valueName": k("value-name"),
                "sortOrder": {"from": k("sort-order"), "default": 0},
                "description": k("description"),
            },
            "parent": ["objectType", "id", "code", "name"],
            "path": True,
            "hierarchy": True,
            "related": {
                "systemVariants": {
                    "via": k("master-value-represented-by-system-value"),
                    "fields": {
                        "system": f"ancestor:{system}.name",
                        "value": "name",
                        "valueCode": k("value-code"),
                        "externalId": k("external-id"),
                        "isActive": k("active"),
                    },
                },
                "translations": {
                    "via": k("object-has-translation"),
                    "fields": {
                        "languageCode": f"ancestor:{language}.{k('language-code')}",
                        "translatedName": k("translated-name"),
                    },
                },
            },
        },
        "operations": {
            "objects": {},
            "xref": {
                "matchOn": [
                    {"field": k("master-id"), "exact": 1000},
                    {"field": k("value-code"), "exact": 500, "contains": 40},
                    {"field": "name", "exact": 200, "contains": 30},
                ],
                "alsoMatchThrough": [
                    {
                        "related": "systemVariants",
                        "firstOf": [{"field": "name", "exact": 80}, {"field": k("external-id"), "exact": 75}],
                        "preferTypes": [k("master-value")],
                    }
                ],
            },
            "resolve": {},
            "lists": {
                "codelists": {"of": k("codelist"), "within": {"filter": "domain", "types": [k("domain")]}},
                "values": {"of": k("master-value"), "within": {"filter": "codelist"}},
                "all-values": {"of": k("master-value")},
            },
        },
        "filters": {
            "type": {"byType": True},
            "system": {
                "onRelated": "systemVariants",
                "matchOn": [f"ancestor:{system}.name", f"ancestor:{system}.{k('system-code')}"],
                "keepOnlyMatching": True,
                "scoreOnlyMatching": True,
                "crosswalk": True,
            },
            "codelist": {"under": [k("codelist")], "matchOn": ["name", k("codelist-code")]},
            "sameSystem": {
                "linkedTo": [k("master-value")],
                "through": ["itself", "sharedWith:systemVariants"],
                "matchOn": [k("master-id")],
            },
            "language": {
                "onRelated": "translations",
                "matchOn": [f"ancestor:{language}.{k('language-code')}"],
                "keepOnlyMatching": True,
            },
        },
    }


@pytest.fixture(params=["starter", "renamed"])
def base(request) -> tuple[dict[str, Any], Keys]:
    """The starter without its own consumer API, as it is or with every key renamed, and its key
    map; each test declares the definition it needs."""
    source = json.loads(MODEL_PATH.read_text())
    source.pop("consumerApis", None)
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
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
    # The canonical document is the definition as written, `from` included, and reparses to the
    # same hash; a model without definitions has none in its document.
    assert canonical["consumerApis"][0] == definition(k)
    assert compile_model(canonical).model_hash == compiled.model_hash
    assert "consumerApis" not in compile_model(source).canonical_model

    contract = output_contract(compiled.model, consumer_apis(compiled.model)[0])
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
        "parent": {"object": {"objectType": "text", "masterId": "text", "code": "text", "name": "text"}},  # C-D75
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


@pytest.mark.parametrize(("shipped", "original"), SHIPPED, ids=["starter"])
def test_the_shipped_models_rewritten_in_schema_0_9_are_the_same_definitions(shipped, original):
    """C18's proof of no change: each shipped model's definitions and its 0.8 original's compile to
    the same internal form, so every reader serves them alike, and each definition's OpenAPI
    document is the same apart from the release it names. Expanding the expanded read of either
    gives the definition back (C-D137)."""
    rewritten = parse_model(json.loads(shipped.read_text()))
    before = parse_model(json.loads(original.read_text()))
    assert (rewritten.schemaVersion, before.schemaVersion) == ("0.9", "0.8")
    assert consumer_apis(rewritten) == consumer_apis(before)

    def document(model, definition):
        built = consumer_openapi(model, definition, root_path="", resolve_max_items=1000, token_url="/oauth/token")
        release = f"{model.release.name} {model.release.version}"
        built["info"]["description"] = built["info"]["description"].replace(release, "<release>")
        return built

    for new, old in zip(consumer_apis(rewritten), consumer_apis(before), strict=True):
        assert document(rewritten, new) == document(before, old), new.key
        for model, definition in ((rewritten, new), (before, old)):
            read = ConsumerApiDocument.model_validate(expanded_definition(model, definition))
            assert expand(model, read)[0] == definition


def test_schema_0_8_definitions_are_read_as_stored_and_never_written_again():
    """C-D134: a stored 0.8 release compiles as it was, every operation offered; an author's 0.8
    document that declares consumerApis is refused at /schemaVersion, naming schema 0.9."""
    stored = json.loads(STARTER_08.read_text())
    compiled = compile_model(stored)
    assert compiled.valid, compiled.diagnostics
    (served,) = consumer_apis(compiled.model)
    assert all(served.offers(name) for name in ("objects", "xref", "resolve", "lists", "events"))
    assert compiled.canonical_model == compile_model(compiled.canonical_model).canonical_model

    refused = compile_authored_model(stored)
    assert [(d.code, d.path) for d in refused.diagnostics] == [("UNSUPPORTED_SCHEMA_VERSION", "/schemaVersion")]
    assert "schema 0.9" in refused.diagnostics[0].message
    stored.pop("consumerApis")
    assert compile_authored_model(stored).valid


def test_events_round_trip_and_leave_definitions_without_them_unchanged(base):
    """A definition's events (0.9 C9) keep their canonical form and hash; a definition without events
    has none in its document, so releases made before C9 keep their hash."""
    source, k = base
    without = compile_model(with_definition(source, definition(k)))
    assert "events" not in without.canonical_model["consumerApis"][0]["operations"]

    event = {
        "key": "reference-data-changed",
        "objectTypes": [k("master-value"), k("codelist")],
        "changes": ["created", "updated", "deleted"],
        "watch": {"fields": ["masterId", "code", "isActive"], "related": ["systemVariants"]},
    }
    unwatched = {"key": "domains", "objectTypes": [k("domain")], "changes": ["created"]}
    item = definition(k)
    item["operations"]["events"] = {"custom": [event, unwatched]}
    compiled = compile_model(with_definition(source, item))
    assert compiled.valid, compiled.diagnostics
    assert compiled.canonical_model["consumerApis"][0]["operations"]["events"] == {"custom": [event, unwatched]}
    assert compile_model(compiled.canonical_model).model_hash == compiled.model_hash
    assert compiled.model_hash != without.model_hash


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


def _append(path: str, value: Any) -> Mutation:
    def mutate(item: dict[str, Any], k: Keys) -> None:
        target: Any = item
        for part in path.split("/"):
            target = target[part]
        target.append(value(k) if callable(value) else value)

    return mutate


def _rename_list(old: str, new: str) -> Mutation:
    def mutate(item: dict[str, Any], _k: Keys) -> None:
        lists = item["operations"]["lists"]
        item["operations"]["lists"] = {new if key == old else key: value for key, value in lists.items()}

    return mutate


REFUSALS: list[tuple[str, Mutation, str, str]] = [
    ("unknown exposed type", _append("exposes", "unknown-type"), "UNKNOWN_OBJECT_TYPE", "/exposes/3"),
    ("repeated public name", _set("publicNames/@domain", "Codelist"), "DUPLICATE_KEY", "/publicNames/{domain}"),
    ("key outside the URL alphabet", _set("key", "RDM"), "INVALID_MODEL", "/consumerApis/RDM/key"),
    ("unknown source", _set("object/fields/code/from/1", "no-such-attribute"), "INVALID_REFERENCE", "/object/fields/code/from/1"),
    ("source no exposed type binds", _set("object/fields/code/from/1", lambda k: k("system-code")), "INVALID_REFERENCE", "/object/fields/code/from/1"),
    ("sources of different types (C-D19)", _set("object/fields/code/from/1", lambda k: k("sort-order")), "INVALID_MODEL", "/object/fields/code/from"),
    ("default of another type", _set("object/fields/isActive/default", "yes"), "INVALID_MODEL", "/object/fields/isActive/default"),
    ("identity other than the object ID (C-D24)", _set("object/fields/masterId/from", lambda k: k("value-code")), "INVALID_MODEL", "/object/fields/masterId/from"),
    ("reserved output name", _set("object/fields/matchScore", lambda k: k("value-name")), "INVALID_MODEL", "/object/fields/matchScore"),
    ("output name used twice", _set("object/fields/path", lambda k: k("value-name")), "DUPLICATE_KEY", "/object/path"),
    ("parent code without a code role", _drop("object/fields/code"), "INVALID_MODEL", "/object/parent"),
    ("related records over an unknown relation", _set("object/related/systemVariants/via", "no-such-relation"), "INVALID_REFERENCE", "/object/related/systemVariants/via"),
    ("related route no exposed type has", _set("object/related/systemVariants/via", lambda k: k("system-value-maps-to-master")), "INVALID_REFERENCE", "/object/related/systemVariants/via"),
    ("related field of a type that is no ancestor", _set("object/related/systemVariants/fields/system", lambda k: f"ancestor:{k('domain')}.name"), "INVALID_REFERENCE", "/object/related/systemVariants/fields/system"),
    ("related block named like an output field", _set("object/related/name", lambda k: {"via": k("object-has-translation"), "fields": {"n": "name"}}), "DUPLICATE_KEY", "/object/related/name"),
    ("match on a field neither searchable nor unique (C-D20)", _set("operations/xref/matchOn/0/field", lambda k: k("sort-order")), "INVALID_MODEL", "/operations/xref/matchOn/0/field"),
    ("match through an unknown related block", _set("operations/xref/alsoMatchThrough/0/related", "nothing"), "INVALID_REFERENCE", "/operations/xref/alsoMatchThrough/0/related"),
    ("preferred type not exposed", _set("operations/xref/alsoMatchThrough/0/preferTypes/0", lambda k: k("system")), "INVALID_REFERENCE", "/operations/xref/alsoMatchThrough/0/preferTypes/0"),
    ("reserved filter name", _set("filters/query", {"byType": True}), "INVALID_MODEL", "/filters/query"),
    ("crosswalk-like filter name", _set("filters/to.system", {"byType": True}), "INVALID_MODEL", "/filters/to.system"),
    ("under filter over a type that is no ancestor", _set("filters/codelist/under/0", lambda k: k("system")), "INVALID_REFERENCE", "/filters/codelist/under/0"),
    ("linkedTo filter over an unknown route", _set("filters/sameSystem/through/1", "sharedWith:nothing"), "INVALID_REFERENCE", "/filters/sameSystem/through/1"),
    ("onRelated filter on a field the related records lack", _set("filters/system/matchOn/1", lambda k: k("codelist-code")), "INVALID_REFERENCE", "/filters/system/matchOn/1"),
    ("list key outside the URL alphabet", _rename_list("all-values", "All_Values"), "INVALID_MODEL", "/operations/lists/All_Values"),
    ("list of a type not exposed", _set("operations/lists/all-values/of", lambda k: k("system")), "INVALID_REFERENCE", "/operations/lists/all-values/of"),
    ("list within a type that cannot contain it", _set("operations/lists/codelists/within/types/0", lambda k: k("master-value")), "INVALID_REFERENCE", "/operations/lists/codelists/within/types/0"),
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
    assert "Consumer API" in diagnostics[0].message or code == "INVALID_MODEL"


def test_shape_errors_name_the_body_part(base):
    source, k = base
    for mutate, path in (
        (_set("operations/xref/matchOn/0/exact", 0), "/consumerApis/0/operations/xref/matchOn/0/exact"),
        (_set("operations/xref/matchOn/1", {"field": "name"}), "/consumerApis/0/operations/xref/matchOn/1"),
        (_set("filters/system/kind", "location"), "/consumerApis/0/filters/system"),
        (_set("object/fields/code/role", "label"), "/consumerApis/0/object/fields/code/role"),
        (_set("contractVersion", 0), "/consumerApis/0/contractVersion"),
    ):
        item = definition(k)
        mutate(item, k)
        diagnostic = compile_model(with_definition(source, item)).diagnostics[0]
        assert diagnostic.path.startswith(path), (diagnostic.path, diagnostic.message)
    duplicate = compile_model({**with_definition(source, definition(k)), "consumerApis": [definition(k)] * 2})
    assert (duplicate.diagnostics[0].code, duplicate.diagnostics[0].path) == ("DUPLICATE_KEY", API)


def _both(*mutations: Mutation) -> Mutation:
    def mutate(item: dict[str, Any], k: Keys) -> None:
        for mutation in mutations:
            mutation(item, k)

    return mutate


def _stop_exposing(type_key: str) -> Mutation:
    def mutate(item: dict[str, Any], k: Keys) -> None:
        item["exposes"].remove(k(type_key))
        del item["publicNames"][k(type_key)]

    return mutate


BREAKING: list[tuple[str, Mutation, list[str]]] = [
    ("removes an output field", _drop("object/fields/sortOrder"), ["/object"]),
    ("retypes an output field", _set("object/fields/sortOrder", lambda k: k("value-name")), ["/object"]),
    ("removes a parent field", _set("object/parent", ["objectType", "id", "name"]), ["/object"]),
    ("renames a public type", _set("publicNames/@domain", "Area"), ["/publicNames/{domain}"]),
    (
        "stops exposing a type",
        _both(_stop_exposing("domain"), _set("object/fields/code/from", lambda k: [k("value-code"), k("codelist-code")])),
        ["/exposes"],
    ),
    (
        "removes related records and the filter over them",
        _both(_drop("object/related/translations"), _drop("filters/language")),
        ["/object/related", "/filters"],
    ),
    ("removes a related field", _drop("object/related/systemVariants/fields/externalId"), ["/object/related/systemVariants/fields"]),
    ("changes a weight (C-D4)", _set("operations/xref/matchOn/0/exact", 999), ["/operations/xref"]),
    ("removes the lists (C-D18)", _drop("operations/lists"), ["/operations/lists"] * 3),
    ("changes a list's within (C-D18)", _drop("operations/lists/values/within"), ["/operations/lists"]),
    ("removes a filter (C-D18)", _drop("filters/type"), ["/filters"]),
    (
        "changes a filter's verb (C-D18)",
        _set("filters/type", lambda k: {"under": [k("codelist")], "matchOn": ["name"]}),
        ["/filters/type"],
    ),
    ("stops offering an operation (C-D132)", _drop("operations/resolve"), ["/operations"]),
]


@pytest.mark.parametrize(("label", "mutate", "paths"), BREAKING, ids=[item[0] for item in BREAKING])
def test_breaking_changes_need_a_higher_contract_version(base, label, mutate, paths):
    source, k = base
    active = parse_model(with_definition(source, definition(k)))
    item = definition(k)
    mutate(item, k)
    candidate = parse_model(with_definition(source, item))
    diagnostics = contract_diagnostics(active, candidate)
    assert {(d.severity, d.code) for d in diagnostics} == {("error", "CONSUMER_CONTRACT_VERSION_REQUIRED")}, label
    assert [d.path for d in diagnostics] == [f"{API}{path.replace('{domain}', k('domain'))}" for path in paths]
    assert all("raise contractVersion above 1" in d.message for d in diagnostics)
    # The same change under a higher contract version is a new contract.
    item["contractVersion"] = 2
    assert contract_diagnostics(active, parse_model(with_definition(source, item))) == []


def test_additions_are_compatible_and_lower_versions_or_removals_are_reported(base):
    source, k = base
    active = parse_model(with_definition(source, definition(k)))
    item = definition(k)
    item["object"]["fields"]["validity"] = k("valid-to")
    item["object"]["related"]["systemVariants"]["fields"]["valueName"] = k("value-name")
    item["filters"]["domain"] = {"under": [k("domain")], "matchOn": ["name"]}
    item["operations"]["lists"]["domains"] = {"of": k("domain")}
    item["exposes"].append(k("language"))
    item["publicNames"][k("language")] = "Language"
    assert contract_diagnostics(active, parse_model(with_definition(source, item))) == []
    # Offering one more operation is compatible too (C-D132).
    fewer = definition(k)
    del fewer["operations"]["resolve"]
    assert contract_diagnostics(parse_model(with_definition(source, fewer)), active) == []

    lower = definition(k) | {"contractVersion": 1}
    higher_active = parse_model(with_definition(source, definition(k) | {"contractVersion": 3}))
    diagnostics = contract_diagnostics(higher_active, parse_model(with_definition(source, lower)))
    assert [(d.code, d.path) for d in diagnostics] == [("CONSUMER_CONTRACT_VERSION_DECREASED", f"{API}/contractVersion")]

    removed = contract_diagnostics(active, parse_model(source))
    assert [(d.severity, d.code, d.path) for d in removed] == [("warning", "CONSUMER_API_REMOVED", API)]


def test_a_cardinality_change_in_the_model_changes_a_projection_shape(base):
    source, k = base
    active = parse_model(with_definition(source, definition(k)))
    changed = with_definition(source, definition(k))
    for binding in changed["objectTypeRelations"]:
        if binding["relationTypeKey"] == k("system-value-maps-to-master"):
            binding["cardinality"] = "one-to-many"
    candidate = parse_model(changed)
    # One system value per master value now: the projection becomes an object or null.
    assert output_contract(candidate, consumer_apis(candidate)[0]).projections["systemVariants"]["shape"] == "one"
    diagnostics = contract_diagnostics(active, candidate)
    assert [(d.code, d.path) for d in diagnostics] == [
        ("CONSUMER_CONTRACT_VERSION_REQUIRED", f"{API}/object/related/systemVariants")
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
        state = default_model(session)
        assert state is not None
        version = state.version
    active = client.get("/api/v1/model").headers["X-Model-Release-Id"]
    return client.post(
        DEFAULT_ACTIVATION,
        json={"releaseId": release_id, "expectedVersion": version, "expectedReleaseId": active},
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
    """C-D17 at the API: draft compile and release diff report the check, activation refuses a break.
    The active model's own definitions stay as they are beside the test's, under a key of its own."""
    client = admin_client
    source = client.get("/api/v1/model").json()
    keys: Keys = lambda key: key
    api = "/consumerApis/c1"

    def with_own(item: dict[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(source)
        result["consumerApis"] = [*source.get("consumerApis", []), item | {"key": "c1"}]
        return result

    first = _install(with_own(definition(keys)), "0.9.0-c1-contract")
    activated = _activate(client, first)
    assert activated.status_code == 200, activated.text

    broken_definition = definition(keys)
    del broken_definition["object"]["fields"]["sortOrder"]
    broken = with_own(broken_definition)
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
        ("error", "CONSUMER_CONTRACT_VERSION_REQUIRED", f"{api}/object")
    ]

    broken_id = _install(broken, "0.9.0-c1-broken")
    diff = client.get(f"/api/v1/model-releases/{broken_id}/diff", params={"againstReleaseId": first}).json()
    assert diff["consumerContracts"]["classification"] == "version_required"

    refused = _activate(client, broken_id)
    assert refused.status_code == 409, refused.text
    error = refused.json()["error"]
    assert error["code"] == "CONSUMER_CONTRACT_VERSION_REQUIRED"
    assert [item["path"] for item in error["details"]] == [f"{api}/object"]
    assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == first

    raised_definition = broken_definition | {"contractVersion": 2}
    raised = _install(with_own(raised_definition), "0.9.0-c1-raised")
    accepted = _activate(client, raised)
    assert accepted.status_code == 200, accepted.text
    served = client.get("/api/v1/model").json()["consumerApis"]
    assert next(item for item in served if item["key"] == "c1")["contractVersion"] == 2
