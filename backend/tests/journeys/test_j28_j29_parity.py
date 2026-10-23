"""Consumer API parity (Base 0.9 C8): the reference deployment's answers, reproduced from a definition.

CONSUMER_API's C8 scenarios on the ``parity`` fixture (``configurations.parity``, C-D72): the starter
extended as the reference deployment's model is, with CONSUMER_API's printed definition. Each J28 and
J29 mechanism has its own journey test on generated A and B; here the calls are the ones integration
flows make (XREF with ``system``, take the top result, read a field), and every answer is checked
against the reference shape: valid against the definition's own OpenAPI document, with the keys of
CONSUMER_API's "The shared object" as "Behavior the engine does not carry over" maps them.

The dataset is a seed of its own, built once through ``POST /batches`` and reused (seed once):

- Transport (HC) › Timetable types (MOT) › Train (CONS), Follow-up (FUP), Tram
  (VAC), Standard (STD); › Durations (DUR) › 30 minutes (D30); › Stations (CLIN) › Central Station
  (CEN, operator BR1), North Station (NOR). Train's alternative is Follow-up; its duration 30
  minutes.
- Finance (FIN) › Currencies (CUR) › Swiss franc (CHF, master ID MV-0001), Euro (EUR), Standard (STD).
- SAP: CHF (external ID 1001) maps to Swiss franc, LOC-9 (9001) only to North Station, FU-1 to
  Follow-up and Central Station. Oracle: SFR (O-77) maps to Swiss franc.
- Train is available at Central Station, Tram at North Station.
- German: Eisenbahn (Train), Schweizer Franken (Swiss franc). Spanish: Cita médica
  (Train).
"""

import copy
import re
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
import seeds
from configurations import parity
from model_support import without_relation_columns
from openapi_schema_validator import OAS31Validator
from scenario import SOURCE, W1, application, derive_events, ok, refused
from sqlalchemy import URL

from app.db import SessionLocal
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.compiler import parse_model
from app.engine.model.consumer_definitions import consumer_apis

API = "/api/consumer/rdm/v1"
CONFIGURATION = parity()

# CONSUMER_API "The shared object", as "Behavior the engine does not carry over" maps it: the
# reference's master ID is the attribute formerId and masterId the object ID (C-D24); description is
# in XREF too; matchScore only in XREF. The reference's duration and alternative are declared by the
# fixture's definition as they appear there.
REFERENCE_KEYS = {
    "objectType", "masterId", "code", "name", "valueName", "sortOrder", "isActive", "internalOnly",
    "validFrom", "validTo", "systemVariants", "translations", "availableAt", "duration",
    "alternative", "path", "parent", "hierarchy", "description", "formerId",
}
PARENT_KEYS = {"objectType", "masterId", "code", "name"}


# --- the dataset ---------------------------------------------------------------------------------


def _record(ids, items, name, app, type_key, values, parent=None, **extra):
    record_id = ids.setdefault(name, str(uuid4()))
    item = {
        "op": "create",
        "id": record_id,
        "applicationKey": app,
        "objectTypeKey": type_key,
        "name": name,
        "attributes": [{"attributeTypeKey": key, "value": value} for key, value in values.items()],
        **extra,
    }
    if parent is not None:
        item["parent"] = {"id": ids[parent]}
    items.append(item)


def _relate(ids, items, relation, source, target):
    items.append(
        {"op": "createRelation", "relationTypeKey": relation, "from": {"id": ids[source]}, "to": {"id": ids[target]}}
    )


def _dataset(world) -> dict[str, str]:
    ids: dict[str, str] = {}
    items: list[dict[str, Any]] = []
    master, systems, translations = "rdm-master", "rdm-systems", "rdm-translations"

    def value(name, code, master_id, parent, **values):
        _record(
            ids, items, name, master, "master-value",
            {"master-id": master_id, "value-code": code, "value-name": name, **values}, parent,
        )

    _record(ids, items, "Transport", master, "domain", {"domain-code": "HC"})
    _record(ids, items, "Timetable types", master, "codelist", {"codelist-code": "MOT"}, "Transport")
    value("Train", "CONS", "MV-0101", "Timetable types", **{"sort-order": 1})
    value("Follow-up", "FUP", "MV-0102", "Timetable types")
    value("Tram", "VAC", "MV-0103", "Timetable types")
    value("Standard", "STD", "MV-0104", "Timetable types")
    _record(ids, items, "Durations", master, "codelist", {"codelist-code": "DUR"}, "Transport")
    value("30 minutes", "D30", "MV-0201", "Durations")
    _record(ids, items, "Stations", master, "codelist", {"codelist-code": "CLIN"}, "Transport")
    for name, code, master_id in (("Central Station", "CEN", "LC-0001"), ("North Station", "NOR", "LC-0002")):
        values = {"master-id": master_id, "value-code": code, "value-name": name}
        if code == "CEN":
            values["operator-code"] = "BR1"
        _record(ids, items, name, master, "location", values, "Stations")
    _record(ids, items, "Finance", master, "domain", {"domain-code": "FIN"})
    _record(ids, items, "Currencies", master, "codelist", {"codelist-code": "CUR"}, "Finance")
    value("Swiss franc", "CHF", "MV-0001", "Currencies")
    value("Euro", "EUR", "MV-0002", "Currencies")
    ids["Standard (timetable)"] = ids.pop("Standard")
    value("Standard", "STD", "MV-0003", "Currencies")
    ids["Standard (currency)"] = ids.pop("Standard")

    _record(ids, items, "SAP", systems, "system", {"system-code": "SAP"})
    _record(ids, items, "Oracle", systems, "system", {"system-code": "ORA"})
    for name, code, external, system in (
        ("CHF", "CHF", "1001", "SAP"),
        ("LOC-9", "LOC9", "9001", "SAP"),
        ("FU-1", "FU1", "7001", "SAP"),
        ("SFR", "SFR", "O-77", "Oracle"),
    ):
        values = {"value-code": code, "value-name": f"{system} {code}", "external-id": external}
        _record(ids, items, name, systems, "system-value", values, system)

    _record(ids, items, "German", translations, "language", {"language-code": "de"})
    _record(ids, items, "Spanish", translations, "language", {"language-code": "es"})
    for language, code in (("German", "DE"), ("Spanish", "ES")):
        _record(ids, items, f"{language} values", translations, "translation-group", {"group-code": code}, language)
    for name, of, group in (
        ("Eisenbahn", "Train", "German values"),
        ("Schweizer Franken", "Swiss franc", "German values"),
        ("Cita médica", "Train", "Spanish values"),
    ):
        relation = {"relationTypeKey": "object-has-translation", "direction": "incoming", "object": {"id": ids[of]}}
        _record(
            ids, items, name, translations, "translation", {"translated-name": name}, group,
            initialRelations=[relation],
        )

    _relate(ids, items, "system-value-maps-to-master", "CHF", "Swiss franc")
    _relate(ids, items, "system-value-maps-to-master", "SFR", "Swiss franc")
    _relate(ids, items, "system-value-maps-to-master", "LOC-9", "North Station")
    _relate(ids, items, "system-value-maps-to-master", "FU-1", "Follow-up")
    _relate(ids, items, "system-value-maps-to-master", "FU-1", "Central Station")
    _relate(ids, items, "available-at-location", "Train", "Central Station")
    _relate(ids, items, "available-at-location", "Tram", "North Station")
    _relate(ids, items, "has-duration", "Train", "30 minutes")
    _relate(ids, items, "alternative-for", "Train", "Follow-up")

    body = {"workspaceKey": W1, "policy": "atomic", "run": "inline", "items": items}
    result = ok(world.api.post("/batches", body))
    assert result["job"]["result"] == "applied", result
    return ids


def _seed() -> str:
    name = "scenario-parity"

    def build(url: URL) -> dict[str, Any]:
        with application(CONFIGURATION, url) as world:
            return {"ids": _dataset(world)}

    def inputs() -> list[Any]:
        import json

        return [json.dumps(CONFIGURATION.model, sort_keys=True), SOURCE, __file__, seeds.APP / "engine" / "model" / "bootstrap.py"]

    seeds.register(seeds.Seed(name, build, inputs, base="schema"))
    return name


class Parity:
    """The fixture's world: the consumer API as a flow calls it, every answer checked against the
    definition's OpenAPI document."""

    def __init__(self, world, ids: dict[str, str]) -> None:
        self.world = world
        self.ids = ids
        self.document = ok(world.api.get(f"{API}/openapi.json"))
        self._templates = [
            (
                re.compile(
                    "^"
                    + "/".join("[^/]+" if part.startswith("{") else re.escape(part) for part in path.split("/"))
                    + "$"
                ),
                path,
            )
            for path in self.document["paths"]
        ]

    def call(self, method: str, path: str, body: Any = None, **params: Any):
        api = self.world.api
        response = api.get(f"{API}{path}", **params) if method == "get" else api.post(f"{API}{path}", body, **params)
        if response.status_code == 200:
            self.conforms(f"{API}{path}", method, response.json())
        return response

    def get(self, path: str, **params: Any):
        return self.call("get", path, **params)

    def conforms(self, url: str, method: str, answer: Any) -> None:
        template = next(path for pattern, path in self._templates if pattern.match(url))
        operation = self.document["paths"][template][method]
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        OAS31Validator({**schema, "components": self.document["components"]}).validate(answer)

    def typed(self, path_and_query: str) -> dict[str, Any]:
        """A read with the query exactly as a flow types it, commas unencoded (C3b)."""
        answer = ok(self.world.api.client.get(f"{API}{path_and_query}"))
        self.conforms(f"{API}{path_and_query.partition('?')[0]}", "get", answer)
        return answer

    def xref(self, **params: Any) -> dict[str, Any]:
        return ok(self.get("/xref", **params))

    def top(self, **params: Any) -> dict[str, Any]:
        return ok(self.get("/xref", expect="one", **params))

    def object(self, name: str, **params: Any) -> dict[str, Any]:
        return ok(self.get(f"/objects/{self.ids[name]}", **params))

    def listed(self, list_key: str, **params: Any) -> list[str]:
        return [item["name"] for item in ok(self.get(f"/lists/{list_key}", pageSize=100, **params))["items"]]


@pytest.fixture
def fixture() -> Iterator[Parity]:
    name = _seed()
    payload = seeds.ensure(name)
    url = seeds.clone(name)
    try:
        with application(CONFIGURATION, url) as world:
            yield Parity(world, dict(payload["ids"]))
    finally:
        seeds.drop(url.database)


def _scored(page: dict[str, Any]) -> list[tuple[str, int]]:
    return [(item["name"], item["matchScore"]) for item in page["results"]]


# --- the scenarios -------------------------------------------------------------------------------


@pytest.mark.journey("J29", "J29.2")
def test_an_id_a_code_a_partial_name_and_several_terms(fixture):
    """Scenarios 1 and 5. The global ID (master-id) MV-0001 scores Swiss franc 1000. CHF finds it first
    with its code's 500; its SAP value's promoted 80 adds nothing, the higher wins. "franc" finds it by
    contains only, below any exact score. CHF,EUR finds both currencies, each with its best term."""
    assert _scored(fixture.xref(query="MV-0001")) == [("Swiss franc", 1000)]
    assert _scored(fixture.xref(query="CHF"))[0] == ("Swiss franc", 500)
    found = _scored(fixture.xref(query="franc"))
    assert [name for name, _score in found] == ["Swiss franc"]
    assert 0 < found[0][1] < 200
    assert _scored(fixture.typed("/xref?query=CHF,EUR")) == [("Euro", 500), ("Swiss franc", 500)]


@pytest.mark.journey("J29.1", "J29.6", "J29.7")
def test_an_external_id_with_and_without_system(fixture):
    """Scenario 2. 1001, the SAP value's external ID, finds Swiss franc with 75; with system=SAP the
    same, its systemVariants holding only the SAP item; with system=Oracle nothing, since only Oracle
    values may then score (scoresFrom)."""
    assert _scored(fixture.xref(query="1001")) == [("Swiss franc", 75)]
    page = fixture.xref(query="1001", system="SAP")
    assert _scored(page) == [("Swiss franc", 75)]
    assert [item["system"] for item in page["results"][0]["systemVariants"]] == ["SAP"]
    assert fixture.xref(query="1001", system="Oracle")["results"] == []


@pytest.mark.journey("J29.1")
def test_a_system_value_mapped_to_a_location(fixture):
    """Scenario 3. 9001, the external ID of a SAP value mapped only to North Station, answers North
    Station with expect=one. FU-1, mapped to Central Station and to Follow-up, scores the location only
    (preferTargetTypes)."""
    found = fixture.top(query="9001")
    assert (found["objectType"], found["name"], found["matchScore"]) == ("Location", "North Station", 75)
    assert _scored(fixture.xref(query="FU-1")) == [("Central Station", 80)]


@pytest.mark.journey("J29.1")
def test_a_translated_name(fixture):
    """Scenario 4. Eisenbahn, Train's German name, finds it with 60; Berat with 12."""
    assert _scored(fixture.xref(query="Eisenbahn")) == [("Train", 60)]
    assert _scored(fixture.xref(query="Berat")) == [("Train", 12)]


@pytest.mark.journey("J29.6")
def test_codelist_and_domain_by_name_and_by_code(fixture):
    """Scenario 6. STD with codelist=MOT, codelist=Timetable types, domain=HC or domain=Transport
    keeps the timetable Standard only."""
    timetable = fixture.ids["Standard (timetable)"]
    for params in (
        {"codelist": "MOT"}, {"codelist": "Timetable types"}, {"domain": "HC"}, {"domain": "Transport"},
    ):
        page = fixture.xref(query="STD", **params)
        assert [item["masterId"] for item in page["results"]] == [timetable], params


@pytest.mark.journey("J28.8", "J29.6")
def test_location_by_availability_by_itself_and_by_a_shared_system_value(fixture):
    """Scenarios 7 and 8. On all-values, location=CEN keeps Train (available there) and
    Follow-up (sharing the SAP value FU-1 with it), not Tram or Standard; location=North Station
    keeps Tram. XREF for "Station" with location=CEN keeps Central Station itself (self), not
    North Station or the codelist Stations. With system=SAP added, location=CEN keeps Follow-up only."""
    assert fixture.listed("all-values", location="CEN") == ["Train", "Follow-up"]
    assert fixture.listed("all-values", location="North Station") == ["Tram"]
    assert {name for name, _score in _scored(fixture.xref(query="Station"))} >= {"Central Station", "North Station", "Stations"}
    assert [name for name, _score in _scored(fixture.xref(query="Station", location="CEN"))] == ["Central Station"]
    assert fixture.listed("all-values", location="CEN", system="SAP") == ["Follow-up"]


@pytest.mark.journey("J29.3", "J29.6")
def test_a_tie_at_the_top_score(fixture):
    """Scenario 9. STD with expect=one is 409 AMBIGUOUS_MATCH naming both Standards, in the documented
    order (score, public type, name, ID); with codelist=CUR it answers the currency's."""
    error = refused(fixture.get("/xref", query="STD", expect="one"), 409, "AMBIGUOUS_MATCH")
    both = sorted([fixture.ids["Standard (timetable)"], fixture.ids["Standard (currency)"]])
    assert [item["id"] for item in error["details"]["candidates"]] == both
    found = fixture.top(query="STD", codelist="CUR")
    assert found["masterId"] == fixture.ids["Standard (currency)"]


@pytest.mark.journey("J28.7", "J28.8")
def test_a_list_below_a_parent_with_and_without_language(fixture):
    """Scenario 10. values below Timetable types by its ID holds the four types; with language=de
    only Train, its translations limited to German. all-values with codelist=MOT or
    codelist=Timetable types (an ancestor parameter, C-D28) holds the same four. A code as the
    parent of values is 404 PARENT_NOT_FOUND."""
    timetables = fixture.ids["Timetable types"]
    four = ["Train", "Follow-up", "Standard", "Tram"]
    assert fixture.listed("values", codelist=timetables) == four
    page = ok(fixture.get("/lists/values", codelist=timetables, language="de"))
    assert [item["name"] for item in page["items"]] == ["Train"]
    assert [item["translatedName"] for item in page["items"][0]["translations"]] == ["Eisenbahn"]
    assert fixture.listed("all-values", codelist="MOT") == four
    assert fixture.listed("all-values", codelist="Timetable types") == four
    refused(fixture.get("/lists/values", codelist="MOT"), 404, "PARENT_NOT_FOUND")


@pytest.mark.journey("J29.8")
def test_batch_resolve_of_a_mixed_batch(fixture):
    """Scenario 11. CHF and 9001 each with system=SAP, a miss, STD and an item with both query and id:
    found, found, not_found, ambiguous, rejected, in item order; each found equals its xref?expect=one
    answer."""
    body = {
        "items": [
            {"ref": "currency", "query": "CHF", "system": "SAP"},
            {"ref": "station", "query": "9001", "system": "SAP"},
            {"ref": "miss", "query": "nothing-like-it"},
            {"ref": "tie", "query": "STD"},
            {"ref": "both", "query": "CHF", "id": fixture.ids["Swiss franc"]},
        ]
    }
    answer = ok(fixture.call("post", "/resolve", body))
    assert [item["status"] for item in answer["items"]] == ["found", "found", "not_found", "ambiguous", "rejected"]
    assert [item["ref"] for item in answer["items"]] == ["currency", "station", "miss", "tie", "both"]
    for item, outcome in zip(body["items"][:2], answer["items"][:2], strict=True):
        assert outcome["object"] == fixture.top(query=item["query"], system="SAP")


@pytest.mark.journey("J29.11", "J29.12")
def test_crosswalk_between_systems_and_to_a_translation(fixture):
    """Scenario 12. CHF in SAP to Oracle answers Swiss franc with target the SFR item; EUR to Oracle,
    which has no value for it, is 404 TARGET_NOT_FOUND; once a second Oracle value maps to Swiss franc
    the first read is 409 AMBIGUOUS_TARGET. CONS to German answers target the Eisenbahn item."""
    found = fixture.top(query="CHF", system="SAP", to__system="Oracle")
    assert found["name"] == "Swiss franc"
    assert found["target"]["value"] == "SFR"
    assert found["target"]["externalId"] == "O-77"
    refused(fixture.get("/xref", query="EUR", to__system="Oracle", expect="one"), 404, "TARGET_NOT_FOUND")

    translated = fixture.top(query="CONS", to__language="de")
    assert translated["target"]["translatedName"] == "Eisenbahn"

    world = fixture.world
    oracle = fixture.ids["Oracle"]
    second = ok(
        world.api.post(
            "/objects",
            {
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system-value",
                "name": "CHF-O",
                "workspaceKey": W1,
                "parentObjectId": oracle,
                "attributes": [
                    {"attributeTypeKey": "value-code", "value": "CHFO"},
                    {"attributeTypeKey": "value-name", "value": "Oracle CHFO"},
                ],
            },
        ),
        201,
    )
    body = {"relationTypeKey": "system-value-maps-to-master", "fromObjectId": second["id"], "toObjectId": fixture.ids["Swiss franc"]}
    ok(world.api.post("/relations", body), 201)
    error = refused(
        fixture.get("/xref", query="CHF", system="SAP", to__system="Oracle", expect="one"), 409, "AMBIGUOUS_TARGET"
    )
    assert error["details"]["count"] == 2


@pytest.mark.journey("J28.12")
def test_an_extract_pinned_to_the_latest_publication(fixture):
    """Scenario 13. After a publish, all-values pinned to latest names the publication; a value added
    and published between pages is not read, and every value of the first publication is read once."""
    world = fixture.world
    first = world.publish(world.change_set())["id"]
    page = ok(fixture.get("/lists/all-values", publication="latest", pageSize=2))
    assert page["publication"] == first
    names = [item["name"] for item in page["items"]]
    ok(
        world.api.post(
            "/objects",
            {
                "applicationKey": "rdm-master",
                "objectTypeKey": "master-value",
                "name": "Yen",
                "workspaceKey": W1,
                "parentObjectId": fixture.ids["Currencies"],
                "attributes": [
                    {"attributeTypeKey": "master-id", "value": "MV-0004"},
                    {"attributeTypeKey": "value-code", "value": "JPY"},
                    {"attributeTypeKey": "value-name", "value": "Yen"},
                ],
            },
        ),
        201,
    )
    second = world.publish(world.change_set())["id"]
    while page["nextCursor"]:
        page = ok(fixture.get("/lists/all-values", publication="latest", pageSize=2, cursor=page["nextCursor"]))
        assert page["publication"] == first
        names += [item["name"] for item in page["items"]]
    assert sorted(names) == sorted(fixture.listed("all-values", publication=first))
    assert "Yen" not in names
    assert "Yen" in fixture.listed("all-values", publication=second)


def _value(fixture, name: str, code: str, master_id: str, **period: str) -> None:
    attributes = {"master-id": master_id, "value-code": code, "value-name": name, **period}
    body = {
        "applicationKey": "rdm-master",
        "objectTypeKey": "master-value",
        "name": name,
        "workspaceKey": W1,
        "parentObjectId": fixture.ids["Currencies"],
        "attributes": [{"attributeTypeKey": key, "value": value} for key, value in attributes.items()],
    }
    ok(fixture.world.api.post("/objects", body), 201)


@pytest.mark.journey("J23.6", "J23.7")
def test_business_dates_on_each_side_of_a_boundary(fixture):
    """Scenario 15 (SC-11). Swiss franc ends on 1 July 2026, its replacement starts that day and a
    transitional value runs across it. The currencies listed for a date follow the boundary: the old
    value the day before, the replacement on the day itself, the transitional value on both. CHF looks
    up the value effective that day, naming the dated type, and a location is found undated; a
    location read by ID refuses a date, since its type declares no period."""
    world = fixture.world
    franc = ok(world.api.get(f"/objects/master-value/{fixture.ids['Swiss franc']}"))
    change = {"expectedVersion": franc["version"], "attributes": [{"attributeTypeKey": "valid-to", "value": "2026-07-01"}]}
    ok(world.api.patch(f"/objects/master-value/{franc['id']}", change))
    _value(fixture, "Swiss franc 2026", "CHF", "MV-0005", **{"valid-from": "2026-07-01"})
    _value(fixture, "Franc transition", "CHT", "MV-0006", **{"valid-from": "2026-06-15", "valid-to": "2026-07-15"})

    def on(day: str) -> list[str]:
        return sorted(fixture.listed("all-values", codelist="CUR", asOf=day))

    assert on("2026-06-30") == ["Euro", "Franc transition", "Standard", "Swiss franc"]
    assert on("2026-07-01") == ["Euro", "Franc transition", "Standard", "Swiss franc 2026"]
    assert on("2026-07-20") == ["Euro", "Standard", "Swiss franc 2026"]

    before = fixture.xref(query="CHF", asOf="2026-06-30")
    assert before["asOfApplied"] == ["CodelistValue"]
    found = [item["name"] for item in before["results"]]
    assert found[0] == "Swiss franc" and "Swiss franc 2026" not in found
    assert fixture.top(query="CHF", asOf="2026-07-01")["name"] == "Swiss franc 2026"
    assert fixture.top(query="CEN", asOf="2026-07-01")["name"] == "Central Station"
    error = refused(fixture.get(f"/objects/{fixture.ids['Central Station']}", asOf="2026-07-01"), 400, "AS_OF_NOT_SUPPORTED")
    assert error["details"]["objectTypes"] == ["Location"]


@pytest.mark.journey("J20.3")
def test_the_api_index_names_the_definition_and_its_document(fixture):
    """Scenario 16. The API index lists rdm with its OpenAPI URL, which answers a valid document."""
    from openapi_spec_validator import validate as validate_openapi

    index = ok(fixture.world.api.get("/api/consumer"))
    assert [(item["consumerApi"], item["openapi"]) for item in index["items"]] == [("rdm", f"{API}/openapi.json")]
    validate_openapi(ok(fixture.world.api.get(index["items"][0]["openapi"])))


@pytest.mark.journey("J28", "J29")
def test_the_reference_shape(fixture):
    """The reference's shared object, as the definition reproduces it. Train has the reference
    keys; alternative the object of Follow-up with its public type; availableAt an array with Central
    Station; duration an array; parent the codelist with the reference's parent keys; path and hierarchy
    from the walk. Swiss franc's alternative is null, Transport's parent null; booleans and dates are
    typed. The XREF result and the list item for Train are the get-by-ID object, with
    matchScore in XREF only."""
    train = fixture.object("Train")
    assert set(train) == REFERENCE_KEYS
    assert train["alternative"] == {
        "objectType": "CodelistValue",
        "masterId": fixture.ids["Follow-up"],
        "code": "FUP",
        "name": "Follow-up",
    }
    assert [item["locationName"] for item in train["availableAt"]] == ["Central Station"]
    assert train["availableAt"][0]["locationId"] == "LC-0001"
    assert [item["durationName"] for item in train["duration"]] == ["30 minutes"]
    assert train["path"] == "Transport/Timetable types"
    assert train["hierarchy"] == ["Transport", "Timetable types"]
    assert (train["formerId"], train["masterId"]) == ("MV-0101", fixture.ids["Train"])
    assert train["isActive"] is True
    assert train["internalOnly"] is False
    assert train["sortOrder"] == 1
    assert train["validFrom"] is None
    assert {item["languageCode"] for item in train["translations"]} == {"de", "es"}
    assert all(item["isActive"] is True for item in train["translations"])

    assert fixture.object("Swiss franc")["alternative"] is None
    assert fixture.object("Transport")["parent"] is None

    (found,) = fixture.xref(query="CONS")["results"]
    assert found == {**train, "matchScore": found["matchScore"]}
    page = ok(fixture.get("/lists/values", codelist=fixture.ids["Timetable types"]))
    assert next(item for item in page["items"] if item["name"] == "Train") == train
    assert set(train["parent"]) == PARENT_KEYS
    assert train["parent"]["masterId"] == fixture.ids["Timetable types"]
    assert (train["parent"]["objectType"], train["parent"]["code"]) == ("Codelist", "MOT")


# --- the definition rewritten (C18) --------------------------------------------------------------


SUBSCRIPTIONS = {"CONSUMER_SUBSCRIPTIONS_ENABLED": "true"}


def _stored_in_schema_0_8(model: dict[str, Any]) -> str:
    """``model`` installed as a release stored before C18: schema 0.8, its definitions in the 0.8
    shape, which is the engine's internal form written out. Installed below the API, which no longer
    takes such a document (C-D134), as the release was installed when it could."""
    legacy = copy.deepcopy(model)
    legacy["schemaVersion"] = "0.8"
    without_relation_columns(legacy)
    legacy["release"]["version"] += "-schema-0.8"
    legacy["consumerApis"] = [item.model_dump(mode="json") for item in consumer_apis(parse_model(model))]
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, parse_model(legacy))
        session.commit()
        return release.public_id


def _served(parity: Parity) -> dict[str, Any]:
    """What a consumer reads: each answer's status, body and the headers it names, without the
    ``ETag`` values, which name the release (C-D65); the document without the release it names."""
    ids = parity.ids
    world = parity.world
    calls = {
        "object": ("get", f"/objects/{ids['Train']}", None, {}),
        "list": ("get", "/lists/values", None, {"codelist": ids["Timetable types"], "language": "de"}),
        "filtered": ("get", "/lists/all-values", None, {"codelist": "MOT", "type": "CodelistValue"}),
        "xref": ("get", "/xref", None, {"query": "CHF"}),
        "one": ("get", "/xref", None, {"query": "CHF", "system": "SAP", "expect": "one"}),
        "crosswalk": ("get", "/xref", None, {"query": "CHF", "system": "SAP", "to__system": "Oracle", "expect": "one"}),
        "resolve": ("post", "/resolve", {"items": [{"query": "CHF", "system": "SAP"}, {"id": ids["Euro"]}]}, {}),
        "events": ("get", "/events", None, {"after": "0", "pageSize": "100"}),
    }
    served: dict[str, Any] = {}
    for name, (method, path, body, params) in calls.items():
        response = parity.call(method, path, body, **params)
        named = {key: value for key, value in response.headers.items() if key.lower().startswith("rdm-")}
        served[name] = (response.status_code, response.json(), named, "etag" in response.headers)
    served["index"] = ok(world.api.get("/api/consumer"))
    document = ok(world.api.get(f"{API}/openapi.json"))
    description = document["info"]["description"]
    document["info"]["description"] = re.sub(r"declared by the model release .+? \S+\. ", "", description)
    served["document"] = document
    return served


@pytest.mark.journey("J25.5")
def test_rewriting_the_definition_in_schema_0_9_changes_nothing_it_serves():
    """Given the workspace active on the fixture's definition stored in schema 0.8, with a webhook on
    its event. When the same definition in schema 0.9 is compiled, installed and activated. Then no
    consumer contract changes, the webhook stays active, and get by ID, a list below a parent with a
    filter, a filtered list, XREF (a page, expect=one, a crosswalk), batch resolve, the pull feed and
    the API index answer the same bodies and headers apart from the ETag values; the definition's
    OpenAPI document differs only in the release it names."""
    name = _seed()
    payload = seeds.ensure(name)
    url = seeds.clone(name)
    try:
        with application(CONFIGURATION, url, SUBSCRIPTIONS) as world:
            ids = dict(payload["ids"])
            ok(world.activate(_stored_in_schema_0_8(CONFIGURATION.model)))
            webhook = {
                "name": "Reference data",
                "consumerApi": "rdm",
                "workspaceKey": W1,
                "events": ["reference-data-changed"],
                "url": "https://hooks.example.test/rdm",
            }
            subscription = ok(world.api.post("/consumer-subscriptions", webhook), 201)
            derive_events(world)
            before = _served(Parity(world, ids))
            assert before["events"][0] == 200 and before["events"][1]["items"], before["events"]

            model = copy.deepcopy(CONFIGURATION.model)
            model["release"]["version"] += "-schema-0.9"
            draft = ok(world.api.post("/model-drafts", {"name": "Rewritten", "model": model}), 201)
            compiled = ok(world.api.post(f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}))
            assert compiled["valid"] is True, compiled["diagnostics"]
            assert compiled["consumerContracts"]["classification"] == "compatible"
            assert compiled["consumerContracts"]["diagnostics"] == []
            ok(world.activate(world.install(model)["id"]))
            derive_events(world)

            assert ok(world.api.get(f"/consumer-subscriptions/{subscription['id']}"))["status"] == "active"
            after = _served(Parity(world, ids))
            for read in before:
                assert after[read] == before[read], read
    finally:
        seeds.drop(url.database)
