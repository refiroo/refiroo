"""Base 0.8 C4: where the model lets records stand, one rule for the engine and its clients.

``engine/model/placements.py`` answers, per application and place, the types a parent contains and
the types a record can become there (ADR-034); ``GET /model/placements`` serves it in the context's
model. The browser reads it instead of re-deriving it, and its starter-model fixture is generated from
it (``frontend/src/test/starterPlacements.json``), which the last test keeps equal.
"""

import copy
import json
from pathlib import Path

from model_support import renamed_model
from test_type_changes import (
    MODEL_PATH,
    start_change_set,
    starter,  # noqa: F401 - fixture
)

from app.engine.model.compiler import parse_model
from app.engine.model.placements import model_placements

FRONTEND_FIXTURE = Path(__file__).resolve().parents[2] / "frontend/src/test/starterPlacements.json"


def _starter() -> dict:
    return json.loads(MODEL_PATH.read_text())


def _places(source: dict, application: str) -> dict:
    found = next(
        item
        for item in model_placements(parse_model(source))["applications"]
        if item["applicationKey"] == application
    )
    return {
        "top": found["topLevelObjectTypeKeys"],
        **{
            item["objectTypeKey"]: (item["childObjectTypeKeys"], item["possibleObjectTypeKeys"])
            for item in found["parents"]
        },
    }


def test_placements_on_the_starter_model_and_its_renamed_copy():
    for source, names in ((_starter(), {}), renamed_model(_starter())):

        def k(key, names=names):
            return names.get(key, key)

        master = _places(source, k("rdm-master"))
        assert master["top"] == [k("domain")]
        assert master[k("domain")] == ([k("codelist")], [k("codelist")])
        assert master[k("master-value")] == ([k("master-value")], [k("master-value")])
        systems = _places(source, k("rdm-systems"))
        assert systems["top"] == [k("system")]
        both = [k("system-group"), k("system-value")]
        assert systems[k("system")] == (both, both)
        assert systems[k("system-group")] == (both, both)
        assert systems[k("system-value")] == ([], [])


def test_a_type_contained_through_two_parent_relations_is_not_a_possible_type():
    source = _starter()
    codelist = next(item for item in source["objectTypes"] if item["key"] == "codelist")
    codelist["behavior"]["parentRelationTypeKeys"].append("codelist-contains-value")
    source["objectTypeRelations"].append(
        {
            "relationTypeKey": "codelist-contains-value",
            "fromObjectTypeKey": "domain",
            "toObjectTypeKey": "codelist",
            "cardinality": "one-to-many",
        }
    )
    # A domain still contains codelists, but a record cannot become one there: which relation
    # would hold it is not decided by the model.
    assert _places(source, "rdm-master")["domain"] == (["codelist"], [])


def test_served_in_the_context_of_the_model(starter):  # noqa: F811
    client, k = starter
    live = client.get("/api/v1/model/placements", params={"workspaceKey": "default"})
    assert live.status_code == 200, live.text
    model = client.get("/api/v1/model", params={"workspaceKey": "default"})
    assert live.headers["ETag"] == model.headers["ETag"]
    by_application = {item["applicationKey"]: item for item in live.json()["applications"]}
    assert by_application[k("rdm-systems")]["topLevelObjectTypeKeys"] == [k("system")]
    change_set = start_change_set(client)
    staged = client.get("/api/v1/model/placements", params={"changeSetId": change_set["id"]})
    assert staged.status_code == 200 and staged.json() == live.json()
    missing = client.get("/api/v1/model/placements", params={"changeSetId": "nope"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "CHANGE_SET_NOT_FOUND"


def test_the_frontend_fixture_is_the_served_placements():
    """Regenerate from ``backend/tests`` with
    ``../.venv/bin/python -c "from test_model_placements import write; write()"``."""
    assert json.loads(FRONTEND_FIXTURE.read_text()) == model_placements(parse_model(_starter()))


def write() -> None:
    placements = model_placements(parse_model(copy.deepcopy(_starter())))
    FRONTEND_FIXTURE.write_text(json.dumps(placements, indent=2) + "\n")
