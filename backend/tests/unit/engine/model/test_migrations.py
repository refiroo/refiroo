"""``engine/model/migrations.py``: a migration's plan and its value conversions (0.11 V1).

The plan decides from two models alone what each type, attribute value and relationship becomes
(D68, D70). ``rdm_convert_value`` converts one stored value between value types (D69): text reads
as an import reads a cell (``imports/cells.py``), so every sample is checked against that reading;
the other pairs convert only what they can carry without loss.
"""

import copy
import itertools
import json
from typing import Any

import pytest
from configurations import all_configurations
from sqlalchemy import text

from app.db import SessionLocal
from app.engine.imports.cells import attribute_value
from app.engine.model.compiler import parse_model
from app.engine.model.migrations import (
    TypeMapping,
    plan_migration,
    publication_refusal_items,
    relaxed,
)
from app.errors import ApiError
from app.models.schema import AttributeTypeDefinition

CONFIGURATION = all_configurations()["generated-a"]
KEYS = CONFIGURATION.keys
VALUE_TYPES = ("text", "longText", "integer", "decimal", "boolean", "date", "dateTime", "json")

# Stored values of each type, in their JSON form (``rdm_value_json``).
SAMPLES: dict[str, list[Any]] = {
    "text": [
        "12", " -7 ", "1e3", "3.50", "true", "False", "2026-02-28", "2026-02-30",
        "2026-02-28T10:15:00+02:00", "2026-02-28 10:15", "{\"a\": 1}", "[1, 2]", "twelve", "",
        "99999999999",
    ],
    "integer": [0, -12, 2147483647],
    "decimal": ["12", "12.5", "-0.25", "3000000000"],
    "boolean": [True, False],
    "date": ["2026-02-28"],
    "dateTime": ["2026-02-28T00:00:00+00:00", "2026-02-28T10:15:30.500000+00:00"],
    "json": [{"a": 1}, [1, 2], "x", 3],
}


def _convert(session, value: Any, from_type: str, to_type: str) -> Any:
    found = session.scalar(
        text("SELECT rdm_convert_value(CAST(:value AS json), :from, :to)"),
        {"value": json.dumps(value), "from": from_type, "to": to_type},
    )
    return found


def _as_import_reads(value: str, to_type: str) -> Any:
    """What an import stores for a cell holding ``value`` (``None``: refused)."""
    definition = AttributeTypeDefinition(key="probe", name="Probe", valueType=to_type)
    try:
        return attribute_value(definition, value)
    except ApiError:
        return None


def test_text_converts_as_an_import_reads_a_cell(seeded):
    """Every text sample to every type agrees with the import's reading of the same cell; an
    empty text converts to nothing, as an empty cell is no value."""
    with SessionLocal() as session:
        for value, to_type in itertools.product(SAMPLES["text"], VALUE_TYPES):
            if to_type in {"text", "longText"}:
                assert _convert(session, value, "text", to_type) == value
                continue
            expected = _as_import_reads(value, to_type) if value.strip() else None
            if to_type == "json":
                # Any text parsing as JSON, as a cell's JSON column reads; the reading is the value.
                assert _convert(session, value, "text", "json") == expected, value
                continue
            if to_type == "integer" and expected is not None and abs(expected) > 2**31 - 1:
                expected = None  # the column holds 32-bit integers
            assert _convert(session, value, "text", to_type) == expected, (value, to_type)


@pytest.mark.parametrize("from_type", [t for t in VALUE_TYPES if t not in {"text", "longText"}])
def test_every_value_reads_as_text_and_back(seeded, from_type):
    """Any value converts to text as its stored form reads; that text converts back to the value
    (JSON as its text, every other type through the import's reading)."""
    with SessionLocal() as session:
        for value in SAMPLES[from_type]:
            as_text = _convert(session, value, from_type, "text")
            if from_type == "json" or isinstance(value, bool):
                expected_text = json.dumps(value)
            else:
                expected_text = str(value)
            assert as_text == expected_text, (value, as_text)
            assert _convert(session, as_text, "text", from_type) == value, (value, from_type)


def test_the_other_pairs_convert_only_without_loss(seeded):
    """Numbers widen and narrow only when whole; a date is midnight UTC and an instant at midnight
    UTC is its date; anything is JSON; nothing else converts."""
    cases = [
        (12, "integer", "decimal", "12"),
        ("12", "decimal", "integer", 12),
        ("12.5", "decimal", "integer", None),
        ("3000000000", "decimal", "integer", None),
        ("2026-02-28", "date", "dateTime", "2026-02-28T00:00:00+00:00"),
        ("2026-02-28T00:00:00+00:00", "dateTime", "date", "2026-02-28"),
        ("2026-02-28T10:15:30.500000+00:00", "dateTime", "date", None),
        (True, "boolean", "json", True),
        (7, "integer", "json", 7),
        ({"a": 1}, "json", "integer", None),
        (True, "boolean", "integer", None),
        (1, "integer", "boolean", None),
        ("2026-02-28", "date", "integer", None),
        (None, "integer", "text", None),
    ]
    with SessionLocal() as session:
        for value, from_type, to_type, expected in cases:
            assert _convert(session, value, from_type, to_type) == expected, (value, from_type, to_type)


def _models(change):
    current = copy.deepcopy(CONFIGURATION.model)
    target = copy.deepcopy(CONFIGURATION.model)
    target["release"]["version"] += "-next"
    change(target)
    return parse_model(current), parse_model(target)


def _type(document, structure):
    return next(t for t in document["objectTypes"] if t["key"] == KEYS[structure])


def _drop_type(document, structure):
    key = KEYS[structure]
    document["objectTypes"] = [t for t in document["objectTypes"] if t["key"] != key]
    for application in document["applications"]:
        application["objectTypeKeys"] = [k for k in application["objectTypeKeys"] if k != key]
        application["views"] = [v for v in application.get("views", []) if key not in json.dumps(v)]
        if application.get("defaultView") not in {v["key"] for v in application["views"]}:
            application["defaultView"] = application["views"][0]["key"]
    document["objectTypeRelations"] = [
        p for p in document["objectTypeRelations"] if key not in (p["fromObjectTypeKey"], p["toObjectTypeKey"])
    ]


def test_the_plan_decides_each_type_value_and_relationship():
    """A type the target lacks is lost with its relationships; a binding the target drops leaves
    its values without a place; a changed value type converts to it; the other types, values and
    relationships stay as they are."""
    def change(document):
        _drop_type(document, "N")
        r_type = _type(document, "R")
        r_type["attributes"] = [b for b in r_type["attributes"] if b["attributeTypeKey"] != KEYS["R.ro"]]
        next(a for a in document["attributeTypes"] if a["key"] == KEYS["R.n"])["valueType"] = "decimal"

    current, target = _models(change)
    plan = plan_migration(current, target, ())
    types = {(app, kind): (new_app, new_kind, code) for app, kind, new_app, new_kind, code in plan.types}
    lost = {kind: code for (_app, kind), (_a, _k, code) in types.items() if code}
    assert lost == {KEYS["N"]: "OBJECT_TYPE_IN_USE"}
    assert all(new_kind == kind for (_app, kind), (_a, new_kind, code) in types.items() if not code)
    values = {(kind, key): (goes, value_type) for kind, key, goes, value_type in plan.values}
    assert values[(KEYS["R"], KEYS["R.ro"])] == (None, None)
    assert values[(KEYS["R"], KEYS["R.n"])] == (KEYS["R.n"], "decimal")
    assert values[(KEYS["R"], KEYS["R.u"])] == (KEYS["R.u"], "text")
    pairs = {(rel, f, t): kept for rel, f, t, kept, *_rest in plan.pairs}
    assert pairs[(KEYS["Breq"], KEYS["H"], KEYS["N"])] is False
    assert pairs[(KEYS["B11"], KEYS["R"], KEYS["K"])] is True
    assert pairs[(KEYS["Bown"], KEYS["R"], KEYS["D"])] is True


def test_a_type_mapping_keeps_the_records_and_names_attribute_sources():
    """A renamed type mapped to its new key stays, in the application that lists it; an attribute
    named in the mapping takes its values from the source named, ``None`` from none."""
    renamed = f"{KEYS['C2']}-renamed"

    def change(document):
        def renaming(node):
            if isinstance(node, dict):
                return {key: renaming(value) for key, value in node.items()}
            if isinstance(node, list):
                return [renaming(value) for value in node]
            return renamed if node == KEYS["C2"] else node

        document.update(renaming({k: v for k, v in document.items() if k != "release"}))

    current, target = _models(change)
    unmapped = plan_migration(current, target, ())
    assert {kind: code for _a, kind, _na, _nk, code in unmapped.types if code} == {
        KEYS["C2"]: "OBJECT_TYPE_IN_USE"
    }
    display = target.object_type(renamed).displayAttributeTypeKey
    mapped = plan_migration(current, target, (TypeMapping(KEYS["C2"], renamed, ((display, None),)),))
    assert {kind: (new_kind, code) for _a, kind, _na, new_kind, code in mapped.types}[KEYS["C2"]] == (
        renamed,
        None,
    )
    assert {(kind, key): goes for kind, key, goes, _vt in mapped.values}[(KEYS["C2"], display)] is None


def test_a_named_source_wins_over_the_same_attribute_whatever_the_order():
    """An attribute the mapping names takes the source named, even when the same-named attribute
    comes first in the target type; the attribute it names keeps none (0.11 R, R-F1)."""
    current, target = _models(lambda document: None)
    keys = [b.attributeTypeKey for b in target.object_type(KEYS["R"]).attributes]
    first, later = next(
        (a, b)
        for a in keys
        for b in keys
        if keys.index(a) < keys.index(b)
        and target.attribute_type(a).valueType == target.attribute_type(b).valueType
    )
    plan = plan_migration(current, target, (TypeMapping(KEYS["R"], KEYS["R"], ((later, first),)),))
    goes = {(kind, key): to for kind, key, to, _vt in plan.values}
    assert goes[(KEYS["R"], first)] == later
    assert goes[(KEYS["R"], later)] is None


@pytest.mark.parametrize(
    "mapping, pointer",
    [
        (TypeMapping("no-such-type", "x"), "/typeMappings/0/fromObjectTypeKey"),
        (TypeMapping(KEYS["R"], "no-such-type"), "/typeMappings/0/toObjectTypeKey"),
        (TypeMapping(KEYS["R"], KEYS["R"], (("no-such", None),)), "/typeMappings/0/attributes/0/attributeTypeKey"),
        (TypeMapping(KEYS["R"], KEYS["R"], ((KEYS["R.u"], "no-such"),)), "/typeMappings/0/attributes/0/from"),
    ],
)
def test_a_mapping_naming_what_the_models_lack_is_refused_at_its_pointer(mapping, pointer):
    current, target = _models(lambda document: None)
    with pytest.raises(ApiError) as refused:
        plan_migration(current, target, (mapping,))
    assert refused.value.code == "INVALID_MIGRATION_MAPPING"
    assert refused.value.details == {"pointer": pointer}


def test_the_relaxed_target_keeps_every_element_and_drops_every_rule():
    """The model the migrated data is checked against holds the target's elements without a rule
    a record can break, so the analysis of the target against it checks all of them (D72)."""
    _current, target = _models(lambda document: None)
    loose = relaxed(target)
    assert [t.key for t in loose.objectTypes] == [t.key for t in target.objectTypes]
    assert not any(b.required for t in loose.objectTypes for b in t.attributes)
    assert all(t.features.get("rootCreatable") for t in loose.objectTypes)
    assert not any(t.effectivePeriod or t.validation.get("atLeastOneOf") for t in loose.objectTypes)
    assert not any(a.features.get("unique") or "minimum" in a.validation for a in loose.attributeTypes)
    assert all(p.cardinality == "many-to-many" and not p.required for p in loose.objectTypeRelations)


def test_an_executed_migration_leaves_the_stored_matrix_states_true(seeded):
    """The seeded default workspace, with three ``R`` records scored, migrated to a release that
    converts ``R.n`` to a decimal and drops ``N``: the preview changes nothing, the execution converts and removes what it listed,
    takes a feed position for every record it changes, and the stored relation matrix cell states
    still match the records (ADR-033)."""
    from uuid import uuid4

    from scenario import W1
    from sqlalchemy import func, select

    from app.engine.indexes import matrix_states
    from app.engine.jobs.batches import open_batch_context, run_batch
    from app.engine.model.migrations import (
        check_confirmation,
        execute,
        run_preview,
        submit_migration,
    )
    from app.engine.model.releases import install_model_release
    from app.engine.model.workspace_models import load_assignment
    from app.models.commands import BatchRequest
    from app.models.database import AttributeValue, RdmObject, Workspace

    def change(document):
        _drop_type(document, "N")
        next(a for a in document["attributeTypes"] if a["key"] == KEYS["R.n"])["valueType"] = "decimal"
        # The consumer API exposes R.n: its contract changes, so its version rises (D75).
        for api in document["consumerApis"]:
            api["contractVersion"] += 1

    def item(structure, name, values):
        filled = {**seeded.required_values(structure), **values}
        return {
            "op": "create",
            "applicationKey": seeded.app(structure),
            "objectTypeKey": seeded.key(structure),
            "name": name,
            "attributes": [{"attributeTypeKey": k, "value": v} for k, v in filled.items()],
        }

    items = [
        item("R", f"Scored {n}", {KEYS["R.n"]: n * 10, KEYS["R.u"]: f"MIG-{n}"}) for n in range(3)
    ]
    request = BatchRequest.model_validate(
        {"policy": "atomic", "run": "inline", "items": items, "workspaceKey": W1}
    )
    with SessionLocal() as session:
        run_batch(session, open_batch_context(session, request), request, str(uuid4()))
        session.commit()

    _current, target = _models(change)
    with SessionLocal() as session:
        release, _created = install_model_release(session, target)
        session.commit()
        assignment, _current_release = load_assignment(session, W1)
        notices = session.scalar(
            select(func.count()).select_from(RdmObject).where(
                RdmObject.workspace_key == W1, RdmObject.object_type_key == KEYS["N"]
            )
        )
        job = submit_migration(
            session,
            W1,
            target_release_id=release.public_id,
            expected_version=assignment.version,
            type_mappings=[],
            retention_days=7,
        )
        session.commit()
        head = session.scalar(select(Workspace.feed_position).where(Workspace.key == W1))
        run_preview(session, job, retention_days=7, hold=lambda: None)
        session.commit()
        summary = job.report["migration"]
        assert summary["counts"]["refused"] == 0, summary
        assert summary["counts"]["loss"] >= notices
        assert summary["counts"]["conversion"] >= 3
        assert session.scalar(select(Workspace.feed_position).where(Workspace.key == W1)) == head
        assert check_confirmation(
            session,
            job,
            expected_version=summary["expectedVersion"],
            expected_feed_position=summary["feedPosition"],
            accept_loss=True,
        )
        session.commit()
        execute(session, job, retention_days=7, hold=lambda: None)

    with SessionLocal() as session:
        assert load_assignment(session, W1)[1].public_id == release.public_id
        assert not session.scalar(
            select(func.count()).select_from(RdmObject).where(
                RdmObject.workspace_key == W1, RdmObject.object_type_key == KEYS["N"]
            )
        )
        stored_as = set(
            session.scalars(
                select(AttributeValue.value_type)
                .join(RdmObject, RdmObject.id == AttributeValue.object_id)
                .where(RdmObject.workspace_key == W1, AttributeValue.attribute_type_key == KEYS["R.n"])
            )
        )
        assert stored_as <= {"decimal"}
        assert session.scalar(select(Workspace.feed_position).where(Workspace.key == W1)) > head
        assert matrix_states.verify(session) == []


def test_a_release_changing_a_consumer_contract_without_a_new_version_is_refused(seeded):
    """As activation does (D75): a target whose consumer API changes what the workspace's consumers
    read without a higher contract version is refused before a job exists; raising the version
    lets the migration start."""
    from scenario import W1

    from app.engine.model.migrations import submit_migration
    from app.engine.model.releases import ConsumerContractVersionRequired, install_model_release
    from app.engine.model.workspace_models import load_assignment

    def change(document, raise_version):
        next(a for a in document["attributeTypes"] if a["key"] == KEYS["R.n"])["valueType"] = "decimal"
        if raise_version:
            for api in document["consumerApis"]:
                api["contractVersion"] += 1
            document["release"]["version"] += "-contract"

    with SessionLocal() as session:
        version = load_assignment(session, W1)[0].version
        for raise_version in (False, True):
            _current, target = _models(lambda document, up=raise_version: change(document, up))
            release, _created = install_model_release(session, target)
            session.commit()
            arguments = {
                "target_release_id": release.public_id,
                "expected_version": version,
                "type_mappings": [],
                "retention_days": 7,
            }
            if raise_version:
                assert submit_migration(session, W1, **arguments).kind == "migration"
            else:
                # A frozen exception, which ``pytest.raises`` cannot carry a traceback through.
                try:
                    submit_migration(session, W1, **arguments)
                except ConsumerContractVersionRequired as refused:
                    assert refused.diagnostics[0].code == "CONSUMER_CONTRACT_VERSION_REQUIRED"
                else:
                    raise AssertionError("the migration started")


def test_only_rules_that_changed_or_cover_what_the_migration_touched_are_checked():
    """D72 narrowed (2026-10-18): a rule the current release holds unchanged, over data the
    migration did not touch, keeps its place (it was checked when the data was written); a rule
    new in the target, or over a converted attribute, a type records were reclassified into or a
    relation type it removed relationships of, is checked."""
    from app.engine.model.migrations import Touched

    def stricter(document):
        r_type = _type(document, "R")
        next(b for b in r_type["attributes"] if b["attributeTypeKey"] == KEYS["R.b"])["required"] = True

    current, target = _models(stricter)
    unique = lambda model, key: bool(model.attribute_type(key).features.get("unique"))
    required = lambda model, key: next(
        b.required for b in model.object_type(KEYS["R"]).attributes if b.attributeTypeKey == key
    )

    untouched = relaxed(target, current, Touched())
    assert unique(untouched, KEYS["R.u"]) and required(untouched, KEYS["R.q"])
    assert not required(untouched, KEYS["R.b"]), "a rule new in the target is checked"
    assert untouched.model_dump() != relaxed(target).model_dump()

    converted = relaxed(target, current, Touched(attributes=frozenset({KEYS["R.u"]})))
    assert not unique(converted, KEYS["R.u"])
    valued = relaxed(target, current, Touched(valued_types=frozenset({KEYS["R"]})))
    assert not required(valued, KEYS["R.q"])
    retyped = relaxed(target, current, Touched(retyped=frozenset({KEYS["R"]})))
    assert not required(retyped, KEYS["R.q"])
    assert retyped.object_type(KEYS["R"]).features.get("rootCreatable")


def test_a_long_migration_step_stops_when_another_worker_holds_it(seeded):
    """A migration's steps look at the lease between their statements (0.11 V1): the worker
    holding the job goes on; a worker that does not hold it is told so (``LeaseLost``) and its step
    ends instead of running beside the holder's. The lease itself is kept by the worker's heartbeat
    (0.11 N2, D170)."""
    from scenario import W1

    from app.engine.jobs.store import LeaseLost
    from app.engine.jobs.worker import JobWorker, WorkerSettings
    from app.engine.model.migrations import submit_migration
    from app.engine.model.releases import install_model_release
    from app.engine.model.workspace_models import load_assignment

    _current, target = _models(lambda document: _drop_type(document, "N"))
    with SessionLocal() as session:
        release, _created = install_model_release(session, target)
        job = submit_migration(
            session,
            W1,
            target_release_id=release.public_id,
            expected_version=load_assignment(session, W1)[0].version,
            type_mappings=[],
            retention_days=7,
        )
        session.commit()
        sequence_id = job.sequence_id
    settings = WorkerSettings(chunk_items=10, lease_seconds=600, retention_days=7)
    holder = JobWorker(SessionLocal, settings, owner="holder")
    other = JobWorker(SessionLocal, settings, owner="other")
    assert holder._claim() == sequence_id

    holder._renew_lease(sequence_id)
    with pytest.raises(LeaseLost):
        other._renew_lease(sequence_id)


def test_what_would_stop_a_publication_becomes_refused_items_naming_their_subject():
    """A merge conflict names its record or relationship, a version mismatch reading as
    CHANGE_SET_CONFLICT and another conflict keeping its code; a graph diagnostic keeps its code
    and names the relationship or record in its details (0.11 V2, D82)."""
    findings = [
        {"kind": "object", "id": "o1", "code": "VERSION_MISMATCH", "message": "changed live"},
        {"kind": "relation", "id": "r1", "code": "DUPLICATE_EDGE", "message": "both define it"},
        {"code": "REQUIRED_ATTRIBUTE_MISSING", "message": "m", "details": {"objectId": "o2"}},
        {"code": "CARDINALITY_EXCEEDED", "message": "m", "details": {"relationId": "r2"}},
        {"code": "IDENTITY_COLLISION", "message": "m", "details": {"id": "o3"}},
    ]
    items = publication_refusal_items(findings)
    assert [(subject, code) for subject, code, _path, _message in items] == [
        ("object:o1", "CHANGE_SET_CONFLICT"),
        ("relation:r1", "DUPLICATE_EDGE"),
        ("object:o2", "REQUIRED_ATTRIBUTE_MISSING"),
        ("relation:r2", "CARDINALITY_EXCEEDED"),
        ("object:o3", "IDENTITY_COLLISION"),
    ]
