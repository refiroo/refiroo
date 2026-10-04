"""``engine/jobs/batches.py``: a batch's items decided by the single writes' rules and written in bulk.

The journeys J11 and J24 walk a batch through the API (outcomes, policies, upserts, change sets,
idempotency). Here are the module's own edge cases: references by a unique value and where their
refusals point, the parent an item leaves out, upserts and claims beside equal values, a delete
item, an atomic batch in a change set, the matrix states a batch keeps, a bulk write redone item by
item, relationship items and a set replacement keeping the matrix states, and the one context a
request names. Records are named by their structure (``R``, ``H``);
a refusal is asserted by its code and pointer.
"""

from itertools import product
from typing import Any
from uuid import uuid4

import pytest
from scenario import W1, W2, W3
from sqlalchemy import func, select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.indexes import matrix_states
from app.engine.jobs.batches import check_batch_context, open_batch_context, run_batch
from app.engine.model.registry import resolve_model_snapshot
from app.engine.records.writes import LiveWrites
from app.errors import ApiError
from app.models.commands import BatchRequest
from app.models.database import AuditEvent, ChangeSet, ChangeSetObject, ObjectRelation, RdmObject


def _attributes(world, structure: str, values: dict[str, Any]) -> list[dict[str, Any]]:
    filled = world.required_values(structure)
    filled.update({world.key(k): v for k, v in values.items()})
    return [{"attributeTypeKey": k, "value": v} for k, v in filled.items()]


def create(world, structure: str, name: str, **values: Any) -> dict[str, Any]:
    """A create item; ``values`` keyed by structure with ``_`` for ``.`` (``R_u``)."""
    return {
        "op": "create",
        "applicationKey": world.app(structure),
        "objectTypeKey": world.key(structure),
        "name": name,
        "attributes": _attributes(
            world, structure, {k.replace("_", "."): v for k, v in values.items()}
        ),
    }


def upsert(world, structure: str, name: str, **values: Any) -> dict[str, Any]:
    return {
        **create(world, structure, name, **values),
        "op": "upsert",
        "key": {"attributeTypeKey": world.key(f"{structure}.u")},
    }


def by_u(world, structure: str, value: Any, attribute: str | None = None) -> dict[str, Any]:
    return {
        "objectTypeKey": world.key(structure),
        "key": {"attributeTypeKey": world.key(attribute or f"{structure}.u"), "value": value},
    }


def run(world, items, *, policy="independent", change_set: str | None = None, **body) -> list:
    """Run the items inline as the route does, commit, and return the outcomes."""
    context = (
        {"changeSetId": change_set, "expectedChangeSetVersion": version(change_set)}
        if change_set
        else {"workspaceKey": W1}
    )
    request = BatchRequest.model_validate(
        {"policy": policy, "run": "inline", "items": items, **context, **body}
    )
    with SessionLocal() as session:
        outcomes = run_batch(session, open_batch_context(session, request), request, str(uuid4()))
        session.commit()
    return outcomes


def summary(outcomes) -> list[tuple[str, str]]:
    return [
        (o.status, o.fields.get("action") or o.fields.get("reason") or o.fields["error"]["code"])
        for o in outcomes
    ]


def pointers(outcomes) -> list[str | None]:
    return [
        o.fields["error"]["details"]["pointer"] if o.status == "rejected" else None
        for o in outcomes
    ]


def stored(object_id: str) -> RdmObject:
    with SessionLocal() as session:
        return session.scalar(select(RdmObject).where(RdmObject.id == object_id))


def names(world, structure: str, workspace: str = W1) -> list[str]:
    with SessionLocal() as session:
        return sorted(
            session.scalars(
                select(RdmObject.name).where(
                    RdmObject.workspace_key == workspace,
                    RdmObject.object_type_key == world.key(structure),
                )
            )
        )


def new_change_set() -> str:
    with SessionLocal() as session:
        release = resolve_model_snapshot(session).release_db_id
        return create_change_set(session, W1, release, source="currentLive").id


def version(change_set: str) -> int:
    with SessionLocal() as session:
        return session.scalar(select(ChangeSet.version).where(ChangeSet.id == change_set))


def test_items_see_the_items_before_them_and_a_refused_item_writes_nothing(seeded):
    world = seeded
    outcomes = run(
        world,
        [
            {**create(world, "R", "P", R_u="P"), "ref": "row-1"},
            {**create(world, "R2", "Child of P", R2_u="C1"), "parent": by_u(world, "R", "P")},
            create(world, "R", "Clash", R_u="P"),
            {**create(world, "R2", "Child of none", R2_u="C2"), "parent": by_u(world, "R", "NONE")},
            {
                **create(world, "R2", "Cites a token", R2_u="C3"),
                "parent": by_u(world, "R", "P"),
                "initialRelations": [
                    {
                        "relationTypeKey": world.key("Bnn"),
                        "direction": "outgoing",
                        "object": {"id": world.ids["k01"]},
                    }
                ],
            },
        ],
    )
    assert summary(outcomes) == [
        ("applied", "created"),
        ("applied", "created"),
        ("rejected", "DUPLICATE_ATTRIBUTE_VALUE"),
        ("rejected", "REFERENCE_NOT_FOUND"),
        ("rejected", "INVALID_RELATION_PAIR"),
    ]
    assert pointers(outcomes)[2:4] == ["/items/2/attributes", "/items/3/parent"]
    # An outcome carries its item's ref and only its status's fields.
    assert [o.ref for o in outcomes[:2]] == ["row-1", None]
    assert set(outcomes[0].fields) == {"action", "id", "objectTypeKey", "version"}
    assert set(outcomes[2].fields) == {"error"}
    assert stored(outcomes[1].fields["id"]).parent_object_id == outcomes[0].fields["id"]
    assert names(world, "R").count("P") == 1 and "Clash" not in names(world, "R")
    assert names(world, "R2") == ["Child of P"]
    # Nothing applied: the job applies nothing.
    assert summary(run(world, [create(world, "R", "Clash again", R_u="P")])) == [
        ("rejected", "DUPLICATE_ATTRIBUTE_VALUE")
    ]


def test_references_name_a_record_by_a_unique_value_and_refusals_point_at_them(seeded):
    world = seeded
    [holder] = run(world, [create(world, "R", "Holder", R_u="HOLDER", R_n=4)])
    child = create(world, "R2", "Child", R2_u="X")
    outcomes = run(
        world,
        [
            {**child, "parent": by_u(world, "R", 4, attribute="R.n")},
            {**child, "parent": by_u(world, "R", "NOBODY")},
            {**upsert(world, "R", "No key value"), "attributes": []},
            {**upsert(world, "R", "Key not unique"), "key": {"attributeTypeKey": world.key("R.n")}},
            {**child, "parent": by_u(world, "R", 7)},
            {**child, "parent": by_u(world, "R", "HOLDER")},
            {
                "op": "update",
                "target": by_u(world, "R", "HOLDER"),
                "expectedVersion": 1,
                "name": "Renamed",
            },
            {"op": "delete", "target": by_u(world, "R", "GONE"), "expectedVersion": 1},
        ],
    )
    assert list(zip(summary(outcomes), pointers(outcomes), strict=True)) == [
        (("rejected", "INVALID_RECORD_KEY"), "/items/0/parent/key/attributeTypeKey"),
        (("rejected", "REFERENCE_NOT_FOUND"), "/items/1/parent"),
        (("rejected", "MISSING_RECORD_KEY"), "/items/2/attributes"),
        (("rejected", "INVALID_RECORD_KEY"), "/items/3/key/attributeTypeKey"),
        (("rejected", "INVALID_ATTRIBUTE_VALUE"), "/items/4/parent/key/value"),
        (("applied", "created"), None),
        (("applied", "updated"), None),
        (("rejected", "REFERENCE_NOT_FOUND"), "/items/7/target"),
    ]
    assert stored(outcomes[5].fields["id"]).parent_object_id == holder.fields["id"]
    assert stored(holder.fields["id"]).name == "Renamed"


def test_a_reference_finding_a_record_of_another_type_is_refused(seeded):
    """``R.u`` is unique across ``R`` and ``R2``, which both bind it: a reference naming ``R`` by a
    value an ``R2`` holds is refused with that record's ID, never taken as the other type."""
    world = seeded
    [ledger] = run(world, [create(world, "R", "Ledger", R_u="L-1")])
    [entry] = run(
        world,
        [
            {
                **create(world, "R2", "Entry", R2_u="E-1", R_u="SHARED"),
                "parent": {"id": ledger.fields["id"]},
            }
        ],
    )
    outcomes = run(
        world,
        [
            {
                **create(world, "R2", "Under the entry", R2_u="E-2"),
                "parent": by_u(world, "R", "SHARED"),
            }
        ],
    )
    assert (summary(outcomes), pointers(outcomes)) == (
        [("rejected", "REFERENCE_TYPE_MISMATCH")],
        ["/items/0/parent"],
    )
    assert outcomes[0].fields["error"]["details"]["id"] == entry.fields["id"]


def test_an_item_that_leaves_out_its_parent_keeps_the_record_where_it_stands(seeded):
    world = seeded
    record = stored(world.ids["h2"])
    [kept] = run(
        world,
        [
            {
                "op": "update",
                "target": {"id": record.id},
                "expectedVersion": record.version,
                "name": "Renamed",
            }
        ],
    )
    assert summary([kept]) == [("applied", "updated")]
    assert stored(record.id).parent_object_id == world.ids["h1"]
    [moved] = run(
        world,
        [
            {
                "op": "update",
                "target": {"id": record.id},
                "expectedVersion": record.version + 1,
                "parent": None,
            }
        ],
    )
    assert summary([moved]) == [("applied", "updated")]
    assert stored(record.id).parent_object_id is None


def test_a_claim_beside_equal_values_and_an_overwrite_on_record(seeded):
    """Equal values are ``unchanged`` whatever the claim; a stale claim on a change is refused at
    ``expectedVersion``; a declared overwrite is audited with the version it replaced."""
    world = seeded
    [created] = run(world, [upsert(world, "R", "Feed", R_u="FEED")])
    record_id = created.fields["id"]
    renamed = upsert(world, "R", "Feed renamed", R_u="FEED")
    [overwritten] = run(world, [renamed], onExisting="overwrite")
    assert (overwritten.fields["version"], overwritten.fields["previousVersion"]) == (2, 1)
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditEvent).where(
                AuditEvent.aggregate_id == record_id, AuditEvent.action == "updated"
            )
        )
        assert audit.changes["overwrite"] == {"previousVersion": 1}

    stale = run(world, [{**upsert(world, "R", "Feed v3", R_u="FEED"), "expectedVersion": 1}])
    assert (summary(stale), pointers(stale)) == (
        [("rejected", "VERSION_CONFLICT")],
        ["/items/0/expectedVersion"],
    )
    same = run(world, [{**renamed, "expectedVersion": 1}])
    assert summary(same) == [("applied", "unchanged")] and same[0].fields["version"] == 2
    update = {
        "op": "update",
        "target": {"id": record_id},
        "expectedVersion": 1,
        "name": "Feed renamed",
    }
    assert summary(run(world, [update])) == [("applied", "unchanged")]
    assert stored(record_id).version == 2


def test_an_upserts_initial_relations_apply_only_when_it_creates(seeded):
    world = seeded
    item = {
        **upsert(world, "R", "Lists a token", R_u="LISTS"),
        "initialRelations": [
            {
                "relationTypeKey": world.key("B1n"),
                "direction": "outgoing",
                "object": {"id": world.ids["k02"]},
            }
        ],
    }
    [created] = run(world, [item])
    assert summary(run(world, [item])) == [("applied", "unchanged")]
    with SessionLocal() as session:
        relations = session.scalar(
            select(func.count())
            .select_from(ObjectRelation)
            .where(ObjectRelation.from_object_id == created.fields["id"])
        )
    assert relations == 1


def test_a_delete_item_with_dependants_is_refused_without_a_preview_token(seeded):
    world = seeded
    record = stored(world.ids["h1"])
    outcomes = run(
        world, [{"op": "delete", "target": {"id": record.id}, "expectedVersion": record.version}]
    )
    assert summary(outcomes) == [("rejected", "OBJECT_HAS_DEPENDANTS")]
    assert "deletionPreviewToken" not in outcomes[0].fields["error"]["details"]
    assert stored(record.id) is not None


def test_an_atomic_batch_in_a_change_set_applies_everything_or_nothing(seeded):
    world = seeded
    change_set = new_change_set()
    before, live = version(change_set), names(world, "R")
    items = [create(world, "R", "Staged", R_u="ST"), create(world, "R", "Clash", R_u="ST")]
    job = str(uuid4())
    request = BatchRequest.model_validate(
        {
            "policy": "atomic",
            "run": "inline",
            "items": items,
            "changeSetId": change_set,
            "expectedChangeSetVersion": before,
        }
    )
    with SessionLocal() as session:
        outcomes = run_batch(session, open_batch_context(session, request), request, job)
        session.commit()
    assert summary(outcomes) == [
        ("unprocessed", "BATCH_ROLLED_BACK"),
        ("rejected", "DUPLICATE_ATTRIBUTE_VALUE"),
    ]
    with SessionLocal() as session:
        assert not session.scalars(select(AuditEvent).where(AuditEvent.cause_id == job)).all()
        assert not session.scalars(
            select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set)
        ).all()
    assert version(change_set) == before

    applied = run(
        world,
        items[:1] + [create(world, "R", "Staged too", R_u="ST2")],
        policy="atomic",
        change_set=change_set,
    )
    assert summary(applied) == [("applied", "created")] * 2
    # One claim for the job, and the records are the change set's.
    assert version(change_set) == before + 1
    assert names(world, "R") == live


def test_batches_keep_the_stored_matrix_states_derived(seeded):
    """A dependant created with its owning relationship, one refused by the scope rule, one moved to
    another ancestor, and an atomic batch rolled back, live and in a change set: the stored cell
    states equal states rebuilt from the records."""
    world = seeded
    region, elsewhere = run(world, [create(world, "G", "Region"), create(world, "G", "Elsewhere")])
    [owner] = run(world, [create(world, "R", "Owner", R_u="OWNER")])

    def dependant(name: str) -> dict[str, Any]:
        return {
            **create(world, "D", name),
            "parent": {"id": region.fields["id"]},
            "initialRelations": [
                {
                    "relationTypeKey": world.key("Bown"),
                    "direction": "incoming",
                    "object": {"id": owner.fields["id"]},
                }
            ],
        }

    for change_set in (None, new_change_set()):
        first = run(world, [dependant("First"), dependant("Second")], change_set=change_set)
        assert summary(first)[0] == ("applied", "created")
        if change_set is None:
            assert summary(first)[1] == ("rejected", "DUPLICATE_RELATION_SCOPE")
        moved = first[0].fields
        run(
            world,
            [
                {
                    "op": "update",
                    "target": {"id": moved["id"]},
                    "expectedVersion": moved["version"],
                    "parent": {"id": elsewhere.fields["id"]},
                }
            ],
            change_set=change_set,
        )
        run(
            world,
            [dependant("Third"), create(world, "R", "Clash", R_u="OWNER")],
            policy="atomic",
            change_set=change_set,
        )
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []


def test_relation_items_keep_the_stored_matrix_states_derived(seeded):
    """Relationship items on a binding a relation matrix shows (created, changed through a set
    replacement, removed) and an atomic batch of them rolled back, live and in a change set: the
    stored cell states equal states rebuilt from the records."""
    world = seeded
    [region] = run(world, [create(world, "G", "Matrix region")])
    owners = run(world, [create(world, "R", f"Matrix owner {n}", R_u=f"MX-{n}") for n in (1, 2)])
    ids = [owner.fields["id"] for owner in owners]
    dependants = run(
        world,
        [
            {
                **create(world, "D", f"Matrix dependant {n}"),
                "parent": {"id": region.fields["id"]},
                "initialRelations": [
                    {
                        "relationTypeKey": world.key("Bown"),
                        "direction": "incoming",
                        "object": {"id": ids[n - 1]},
                    }
                ],
            }
            for n in (1, 2)
        ],
    )
    d1, d2 = (item.fields["id"] for item in dependants)

    def relate(source: str, target: str) -> dict[str, Any]:
        return {
            "op": "createRelation",
            "relationTypeKey": world.key("Bassoc"),
            "from": {"id": source},
            "to": {"id": target},
        }

    def replace(anchor: str, targets: list[str]) -> dict[str, Any]:
        return {
            "op": "replaceRelationSet",
            "relationTypeKey": world.key("Bassoc"),
            "fromObjectTypeKey": world.key("R"),
            "toObjectTypeKey": world.key("D"),
            "direction": "outgoing",
            "anchor": {"id": anchor},
            "targets": [{"object": {"id": target}} for target in targets],
        }

    for change_set in (None, new_change_set()):
        created = run(world, [relate(ids[0], d1), relate(ids[1], d1)], change_set=change_set)
        assert summary(created) == [("applied", "created")] * 2
        replaced = run(
            world, [replace(ids[1], [d2])], change_set=change_set, onExisting="overwrite"
        )
        assert summary(replaced) == [("applied", "updated")]
        first = created[0].fields
        removed = run(
            world,
            [{"op": "deleteRelation", "id": first["relationId"], "expectedVersion": 1}],
            change_set=change_set,
        )
        assert summary(removed) == [("applied", "deleted")]
        rolled_back = run(
            world,
            [relate(ids[0], d2), relate(ids[0], d2)],
            policy="atomic",
            change_set=change_set,
        )
        assert summary(rolled_back)[-1] == ("rejected", "DUPLICATE_RELATION")
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
        run(world, [replace(ids[1], [])], change_set=change_set, onExisting="overwrite")


def test_a_bulk_write_that_fails_is_redone_item_by_item(seeded, monkeypatch):
    """Another workspace's writer takes an item's ID between the decision and the write, which the
    workspace lock does not cover (a state from outside this batch, made here by writing the row):
    each item is applied again alone, so that item is refused with its single create's code and
    the others are applied once."""
    world = seeded
    taken = str(uuid4())
    original = LiveWrites.write

    def taken_meanwhile(writes, model, changes):
        if taken in changes.records:
            with SessionLocal() as session:
                session.add(
                    RdmObject(
                        id=taken,
                        workspace_key=W2,
                        application_key=world.app("R"),
                        object_type_key=world.key("R"),
                        name="Taken elsewhere",
                    )
                )
                session.commit()
            monkeypatch.setattr(LiveWrites, "write", original)
        return original(writes, model, changes)

    monkeypatch.setattr(LiveWrites, "write", taken_meanwhile)
    outcomes = run(
        world,
        [
            create(world, "R", "One", R_u="B1"),
            {**create(world, "R", "Two", R_u="B2"), "id": taken},
            create(world, "R", "Three", R_u="B3"),
        ],
    )
    assert summary(outcomes) == [
        ("applied", "created"),
        ("rejected", "OBJECT_ALREADY_EXISTS"),
        ("applied", "created"),
    ]
    assert pointers(outcomes)[1] == "/items/1/id"
    assert [n for n in names(world, "R") if n in {"One", "Two", "Three"}] == ["One", "Three"]


@pytest.mark.parametrize(
    ("workspace", "refusal"), [("nowhere", "WORKSPACE_NOT_FOUND"), (W3, "WORKSPACE_RETIRED")]
)
def test_a_batch_writes_only_in_an_active_workspace(seeded, workspace, refusal):
    world = seeded
    request = BatchRequest.model_validate(
        {
            "policy": "atomic",
            "run": "inline",
            "workspaceKey": workspace,
            "items": [create(world, "R", "Nowhere", R_u="NOWHERE")],
        }
    )
    with SessionLocal() as session, pytest.raises(ApiError) as refused:
        open_batch_context(session, request)
    assert refused.value.code == refusal


@pytest.mark.parametrize(
    ("workspace", "change_set", "claim"), list(product((False, True), repeat=3))
)
def test_a_request_names_live_data_or_one_change_set_with_its_claim(workspace, change_set, claim):
    request = BatchRequest.model_validate(
        {
            "policy": "atomic",
            "run": "inline",
            "items": [{"op": "delete", "target": {"id": str(uuid4())}, "expectedVersion": 1}],
            **({"workspaceKey": W1} if workspace else {}),
            **({"changeSetId": str(uuid4())} if change_set else {}),
            **({"expectedChangeSetVersion": 3} if claim else {}),
        }
    )
    if workspace == change_set:
        expected = ("INVALID_BATCH_CONTEXT", "/workspaceKey" if workspace else "/changeSetId")
    elif workspace and claim:
        expected = ("INVALID_BATCH_CONTEXT", "/expectedChangeSetVersion")
    elif change_set and not claim:
        expected = ("CHANGE_SET_REQUIRED", None)
    else:
        check_batch_context(request)
        return
    with pytest.raises(ApiError) as refusal:
        check_batch_context(request)
    details = refusal.value.details or {}
    assert (refusal.value.code, details.get("pointer")) == expected
