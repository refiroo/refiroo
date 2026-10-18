"""``engine/moves/move_binding.py``: what the mapping says of each source attribute, and in which
order a moved record finds its target record (0.11 X2, D118, I9, I24).

Generated A onto generated B, entries written by hand: an attribute the mapping names is carried,
or ignored; one the target type holds read-only is not written; an effective period's bounds carry
onto the target's period with nothing to map when both types declare one, and are dropped when only
the source does, unless the mapping names them.

On the seed, the default workspace and the second one run one model; the second holds hierarchy
records of the same names as the first's. A mapping of the hierarchy type onto itself, matching by
name, moves three of the first's records: one whose counterpart the second already holds (a
client may create a record under its counterpart ID) though a record of its name is there too, one
found only by its name, and one found by neither. The first updates its counterpart, the second the
record of its name, and the third is created under its counterpart ID.

A record's origins (0.11 X3, D133) come first: moved back, a record whose chain of origins reaches
a record of the target updates it, however many moves the chain has; one whose original is gone is
created again under the original's ID while that ID is free, and under its counterpart once the ID
is another record's.
"""

from uuid import uuid4

from configurations import all_configurations
from scenario import W1, W2
from sqlalchemy import text

from app.db import SessionLocal
from app.engine.jobs.batches import open_batch_context, run_items
from app.engine.jobs.store import start_job
from app.engine.model.compiler import parse_model
from app.engine.moves.mappings import Releases
from app.engine.moves.move_binding import bind_move, plan_move
from app.engine.moves.sides import Side
from app.engine.records.counterparts import counterpart
from app.models.commands import BatchCreateItem, BatchRequest
from app.models.moves import MoveSelection

A, B = all_configurations()["generated-a"], all_configurations()["generated-b"]
SOURCE, TARGET = Side(parse_model(A.model), "a"), Side(parse_model(B.model), "b")


def _definition(*entries):
    return {"sourceReleaseId": "a", "targetReleaseId": "b", "types": list(entries), "valueMaps": {}}


def _entry(structure, target=None, attributes=()):
    return {
        "source": A.key(structure),
        "target": B.key(target or structure),
        "attributes": [
            {"source": A.key(s), "target": B.key(t)} if t else {"source": A.key(s), "ignore": True}
            for s, t in attributes
        ],
        "relations": [],
        "defaults": {},
    }


def _statuses(plan):
    return {row["source_attr"]: (row["status"], row["target_attr"]) for row in plan.attributes}


def test_named_attributes_carry_or_are_ignored_and_read_only_ones_are_not_written():
    plan = plan_move(
        _definition(_entry("R", attributes=[("R.u", "R.u"), ("R.ro", "R.ro"), ("R.n", None)])),
        SOURCE,
        TARGET,
    )
    assert _statuses(plan) == {
        A.key("R.u"): ("carry", B.key("R.u")),
        A.key("R.ro"): ("readOnly", B.key("R.ro")),
        A.key("R.n"): ("ignore", None),
    }


def test_a_period_carries_onto_the_targets_period_or_is_dropped_without_one():
    both = plan_move(_definition(_entry("E")), SOURCE, TARGET)
    assert _statuses(both) == {
        A.key("E.from"): ("carry", B.key("E.from")),
        A.key("E.to"): ("carry", B.key("E.to")),
    }
    only_source = plan_move(_definition(_entry("E", target="F")), SOURCE, TARGET)
    assert _statuses(only_source) == {
        A.key("E.from"): ("period", None),
        A.key("E.to"): ("period", None),
    }
    named = plan_move(
        _definition(_entry("E", target="F", attributes=[("E.from", "E.from")])), SOURCE, TARGET
    )
    assert _statuses(named) == {
        A.key("E.from"): ("carry", B.key("E.from")),
        A.key("E.to"): ("period", None),
    }


def test_the_targets_required_relationships_and_applications_are_read_from_its_release():
    plan = plan_move(_definition(_entry("D")), SOURCE, TARGET)
    assert {"relation": B.key("Bown"), "from_type": B.key("R"), "to_type": B.key("D")} in (
        plan.required
    )
    assert {row["type_key"] for row in plan.target_types} == {
        item["key"] for item in B.model["objectTypes"]
    }


def test_a_record_is_found_by_its_counterpart_then_by_the_match_then_created(seeded):
    world = seeded
    h = world.key("H")
    first, by_name, neither = world.ids["h1"], world.ids["h2"], world.ids["h6"]
    with SessionLocal() as session:
        held = BatchCreateItem(
            op="create",
            id=counterpart(W2, first),
            applicationKey=world.app("H"),
            objectTypeKey=h,
            name="Held under its counterpart",
            attributes=[
                {"attributeTypeKey": key, "value": value}
                for key, value in world.required_values("H").items()
            ],
        )
        request = BatchRequest(workspaceKey=W2, policy="atomic", run="inline", items=[held])
        [created] = run_items(
            session,
            open_batch_context(session, request),
            [(0, held)],
            policy="atomic",
            on_existing="reject",
            expected_change_set_version=None,
            job_id="unit",
        )
        assert created.status == "applied", created
        session.commit()

        side = Releases(session).of_workspace(W1)
        attributes = [
            {"source": b.attributeTypeKey, "target": b.attributeTypeKey}
            for b in side.bindings(h)
            if not b.readOnly
        ]
        definition = {
            "sourceReleaseId": side.release_id,
            "targetReleaseId": side.release_id,
            "types": [
                {
                    "source": h,
                    "target": h,
                    "attributes": attributes,
                    "relations": [],
                    "defaults": {},
                    "match": {"field": "name"},
                }
            ],
            "valueMaps": {},
        }
        job = start_job(
            session,
            kind="move",
            workspace_key=W2,
            change_set_id=None,
            model_release_id=session.scalar(
                text("SELECT model_release_id FROM workspace_models WHERE workspace_key = :w"),
                {"w": W2},
            ),
            parameters={},
            total=None,
            retention_days=1,
            queued=True,
        )
        bind_move(
            session,
            job,
            plan_move(definition, side, side),
            source=side,
            selection=MoveSelection(objectIds=[first, by_name, neither]),
            source_workspace=W1,
            context=None,
        )
        rows = {
            row["sourceId"]: row
            for row in session.scalars(
                text("SELECT item -> 'row' FROM job_inputs WHERE job_id = :job"),
                {"job": job.sequence_id},
            )
        }
        w2_level_2 = session.scalar(
            text("SELECT id FROM objects WHERE workspace_key = :w AND name = 'Level 2 north'"),
            {"w": W2},
        )
        session.rollback()

    assert (rows[first]["outcome"], rows[first]["foundBy"]) == ("update", "counterpart")
    assert rows[first]["targetId"] == counterpart(W2, first)
    assert (rows[by_name]["outcome"], rows[by_name]["foundBy"]) == ("update", "match")
    assert rows[by_name]["targetId"] == w2_level_2
    assert rows[by_name]["matchedBy"] == {"field": "name"}
    assert (rows[neither]["outcome"], rows[neither].get("foundBy")) == ("create", None)
    assert rows[neither]["targetId"] == counterpart(W2, neither)


def _hierarchy_mapping(side, h):
    return {
        "sourceReleaseId": side.release_id,
        "targetReleaseId": side.release_id,
        "types": [
            {
                "source": h,
                "target": h,
                "attributes": [
                    {"source": b.attributeTypeKey, "target": b.attributeTypeKey}
                    for b in side.bindings(h)
                    if not b.readOnly
                ],
                "relations": [],
                "defaults": {},
            }
        ],
        "valueMaps": {},
    }


def test_a_record_moved_back_finds_its_original_along_its_origins(seeded):
    world = seeded
    h = world.key("H")
    original = world.ids["h1"]
    with SessionLocal() as session:
        chained, gone, taken = session.scalars(
            text(
                "SELECT id FROM objects WHERE workspace_key = :w AND object_type_key = :h"
                " ORDER BY name LIMIT 3"
            ),
            {"w": W2, "h": h},
        ).all()
        missing = str(uuid4())
        # Moves as a client makes them: the original copied into a third workspace, that copy into
        # W2; another original since deleted; and one whose ID is now another record's.
        between = str(uuid4())
        session.execute(
            text(
                "INSERT INTO record_origins (object_id, workspace_key, origin_workspace_key,"
                " origin_object_id, job_id) VALUES"
                " (:between, 'third', :w1, :original, 'm1'), (:chained, :w2, 'third', :between, 'm2'),"
                " (:gone, :w2, :w1, :missing, 'm3'), (:taken, :w2, :w1, :held, 'm4')"
            ),
            {
                "w1": W1,
                "w2": W2,
                "original": original,
                "between": between,
                "chained": chained,
                "gone": gone,
                "missing": missing,
                "taken": taken,
                "held": chained,
            },
        )
        side = Releases(session).of_workspace(W2)
        job = start_job(
            session,
            kind="move",
            workspace_key=W1,
            change_set_id=None,
            model_release_id=session.scalar(
                text("SELECT model_release_id FROM workspace_models WHERE workspace_key = :w"),
                {"w": W1},
            ),
            parameters={},
            total=None,
            retention_days=1,
            queued=True,
        )
        bind_move(
            session,
            job,
            plan_move(_hierarchy_mapping(side, h), side, side),
            source=side,
            selection=MoveSelection(objectIds=[chained, gone, taken]),
            source_workspace=W2,
            context=None,
        )
        rows = {
            row["sourceId"]: row
            for row in session.scalars(
                text("SELECT item -> 'row' FROM job_inputs WHERE job_id = :job"),
                {"job": job.sequence_id},
            )
        }
        session.rollback()

    assert (rows[chained]["outcome"], rows[chained]["foundBy"]) == ("updateOriginal", "origin")
    assert rows[chained]["targetId"] == original
    assert (rows[gone]["outcome"], rows[gone]["foundBy"]) == ("create", "origin")
    assert rows[gone]["targetId"] == missing and "origin" not in rows[gone]
    assert (rows[taken]["outcome"], rows[taken].get("foundBy")) == ("create", None)
    assert rows[taken]["targetId"] == counterpart(W1, taken)
    assert rows[taken]["origin"] == {"workspaceKey": W2, "objectId": taken}
