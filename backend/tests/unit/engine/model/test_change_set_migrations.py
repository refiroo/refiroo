"""``engine/model/change_set_migrations.py``: a change set moved onto its workspace's release (0.11
V3) and ``snapshot_values.reindex_change_set``, the set statement that indexes its moved rows.

A change it made conflicts by content (D89): only where live data differs from its old base
converted by the plan, so a record the workspace's migration only converted is not a conflict,
while a live edit, a live deletion and a relationship set changed live are.
"""

import copy
from typing import Any
from uuid import uuid4

from configurations import all_configurations
from scenario import W1
from sqlalchemy import func, insert, select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.indexes import matrix_states
from app.engine.indexes.snapshot_values import (
    reindex_change_set,
    release_value_types,
    value_rows,
)
from app.engine.jobs.batches import open_batch_context, run_batch
from app.engine.model import change_set_migrations, migrations
from app.engine.model.compiler import parse_model
from app.engine.model.releases import install_model_release
from app.engine.model.workspace_models import load_assignment
from app.models.commands import BatchRequest
from app.models.database import (
    AttributeTypeMeta,
    ChangeSet,
    ChangeSetObject,
    JobItem,
    RdmObject,
    SnapshotAttributeValue,
)

CONFIGURATION = all_configurations()["generated-a"]
KEYS = CONFIGURATION.keys

# Values of each type, and values that do not hold it, in a change set row's JSON form.
SAMPLES: dict[str, list[Any]] = {
    "text": ["plain", "", 5, None],
    "longText": ["long\ntext", True],
    "integer": [3, -2147483648, 3.5, "4", True],
    "decimal": [12.5, "12.50", "-0.250", " 7 ", "x", True],
    "boolean": [True, False, "true"],
    "date": ["2026-02-28", "2026-02-30", 5],
    "dateTime": ["2026-02-28T10:15:00+02:00", "2026-02-28T10:15:00Z", "nope"],
    "json": [{"a": 1}, [1, 2], "x", 3],
}


def _row(item: Any) -> dict[str, Any]:
    columns = (
        "value_type",
        "text_value",
        "integer_value",
        "decimal_value",
        "boolean_value",
        "date_value",
        "datetime_value",
        "json_value",
    )
    found = {
        column: getattr(item, column) if not isinstance(item, dict) else item[column]
        for column in columns
    }
    if found["decimal_value"] is not None:
        found["decimal_value"] = found["decimal_value"].normalize()
    return found


def test_the_index_statement_indexes_values_as_the_flush_hook_does(seeded):
    """Every sample under an attribute of its declared type, and one under a key the release does
    not declare, is indexed by the set statement as ``value_rows`` (the flush hook's) indexes it."""
    with SessionLocal() as session:
        _assignment, release = load_assignment(session, W1)
        keys: dict[str, str] = {}
        for key, value_type in session.execute(
            select(AttributeTypeMeta.key, AttributeTypeMeta.value_type).where(
                AttributeTypeMeta.model_release_id == release.id
            )
        ):
            keys.setdefault(value_type, key)
        change_set = create_change_set(session, W1, release.id, source="currentLive")
        rows = []
        width = max(len(values) for values in SAMPLES.values())
        for index in range(width):
            attributes = {
                keys[value_type]: values[index]
                for value_type, values in SAMPLES.items()
                if value_type in keys and index < len(values)
            }
            attributes["not-declared-anywhere"] = index
            rows.append(
                {
                    "change_set_id": change_set.id,
                    "object_id": str(uuid4()),
                    "application_key": "a",
                    "object_type_key": "t",
                    "name": f"sample {index}",
                    "attributes": attributes,
                    "version": 1,
                    "is_deleted": False,
                }
            )
        # Written past the ORM, as a move writes them.
        session.execute(insert(ChangeSetObject), rows)
        reindex_change_set(session, change_set.id, release.id)
        types = release_value_types(session.connection(), release.id)
        expected = {
            (item["object_id"], item["attribute_type_key"]): _row(item)
            for row in rows
            for item in value_rows(
                "change_set", change_set.id, row["object_id"], row["attributes"], types
            )
        }
        indexed = {
            (item.object_id, item.attribute_type_key): _row(item)
            for item in session.scalars(
                select(SnapshotAttributeValue).where(
                    SnapshotAttributeValue.owner_id == change_set.id
                )
            )
        }
        assert len(keys) >= 6, keys
        assert indexed == expected
        session.rollback()


def _create(seeded, structure: str, record_id: str, name: str, **values: Any) -> dict[str, Any]:
    filled = {**seeded.required_values(structure), **values}
    return {
        "op": "create",
        "id": record_id,
        "applicationKey": seeded.app(structure),
        "objectTypeKey": KEYS[structure],
        "name": name,
        "attributes": [{"attributeTypeKey": k, "value": v} for k, v in filled.items()],
    }


def _batch(session, items, change_set: ChangeSet | None = None) -> None:
    body: dict[str, Any] = {"policy": "atomic", "run": "inline", "items": items}
    if change_set is None:
        body["workspaceKey"] = W1
    else:
        session.refresh(change_set)
        body |= {"changeSetId": change_set.id, "expectedChangeSetVersion": change_set.version}
    request = BatchRequest.model_validate(body)
    run_batch(session, open_batch_context(session, request), request, str(uuid4()))
    session.commit()


def test_a_moved_change_set_conflicts_only_where_live_data_changed(seeded):
    """The default workspace with four R records and a branch citing a token; a change set renames
    each R and cites a second token from the branch; the workspace then migrates to a release
    turning ``R.n`` into a decimal, and afterwards one R is renamed live, one deleted live and the
    branch cites a third token live. The move's preview refuses exactly those three as conflicts
    (the relationship set by ``MAPPING_SET_CHANGED``) and not the R the migration only converted.
    Once the live changes are undone where they can be, a move executes: the change set runs the
    target, its rows' values read in the target's type, its index matches its rows and the stored
    matrix states still match the records."""
    r = [str(uuid4()) for _ in range(4)]
    branch, tokens = str(uuid4()), [str(uuid4()) for _ in range(3)]
    live = [_create(seeded, "R", r[n], f"R {n}", **{KEYS["R.n"]: 10 * n}) for n in range(4)]
    live.append(_create(seeded, "H", branch, "Branch"))
    live += [_create(seeded, "K", token, f"Token {n}") for n, token in enumerate(tokens)]
    cites = KEYS["Bnn"]
    with SessionLocal() as session:
        _batch(session, live)
        _batch(
            session,
            [
                {
                    "op": "createRelation",
                    "relationTypeKey": cites,
                    "from": {"id": branch},
                    "to": {"id": tokens[0]},
                }
            ],
        )
        _assignment, x1 = load_assignment(session, W1)
        change_set = create_change_set(session, W1, x1.id, source="currentLive")
        versions = dict(
            session.execute(
                select(RdmObject.id, RdmObject.version).where(RdmObject.id.in_(r))
            ).all()
        )
        _batch(
            session,
            [
                {
                    "op": "update",
                    "target": {"id": r[n]},
                    "expectedVersion": versions[r[n]],
                    "name": f"R {n} in the change set",
                }
                for n in range(4)
            ]
            + [
                {
                    "op": "createRelation",
                    "relationTypeKey": cites,
                    "from": {"id": branch},
                    "to": {"id": tokens[1]},
                }
            ],
            change_set,
        )

        change_set_id = change_set.id

    with SessionLocal() as session:
        target = copy.deepcopy(CONFIGURATION.model)
        target["release"]["version"] += "-decimal"
        next(a for a in target["attributeTypes"] if a["key"] == KEYS["R.n"])["valueType"] = (
            "decimal"
        )
        for api in target.get("consumerApis", []):
            api["contractVersion"] += 1
        x2, _created = install_model_release(session, parse_model(target))
        session.commit()
        assignment, _x1 = load_assignment(session, W1)
        job = migrations.submit_migration(
            session,
            W1,
            target_release_id=x2.public_id,
            expected_version=assignment.version,
            type_mappings=[],
            retention_days=7,
        )
        session.commit()
        migrations.run_preview(session, job, retention_days=7, hold=lambda: None)
        session.commit()
        summary = job.report["migration"]
        assert migrations.check_confirmation(
            session,
            job,
            expected_version=summary["expectedVersion"],
            expected_feed_position=summary["feedPosition"],
            accept_loss=True,
        )
        session.commit()
        migrations.execute(session, job, retention_days=7, hold=lambda: None)

    with SessionLocal() as session:
        versions = dict(
            session.execute(
                select(RdmObject.id, RdmObject.version).where(RdmObject.id.in_(r))
            ).all()
        )
        _batch(
            session,
            [
                {
                    "op": "update",
                    "target": {"id": r[1]},
                    "expectedVersion": versions[r[1]],
                    "name": "R 1 renamed live",
                },
                {"op": "delete", "target": {"id": r[2]}, "expectedVersion": versions[r[2]]},
                {
                    "op": "createRelation",
                    "relationTypeKey": cites,
                    "from": {"id": branch},
                    "to": {"id": tokens[2]},
                },
            ],
        )
        change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        move = change_set_migrations.submit_change_set_migration(
            session,
            change_set.id,
            expected_change_set_version=change_set.version,
            target_release_id=None,
            type_mappings=[],
            retention_days=7,
        )
        session.commit()
        change_set_migrations.run_preview(session, move, retention_days=7, hold=lambda: None)
        session.commit()
        refused = {
            (item.outcome["objectId"], item.outcome["code"])
            for item in session.scalars(
                select(JobItem).where(
                    JobItem.job_id == move.sequence_id, JobItem.status == "rejected"
                )
            )
        }
        assert refused == {
            (r[1], "CHANGE_SET_CONFLICT"),
            (r[2], "CHANGE_SET_CONFLICT"),
            (branch, "MAPPING_SET_CHANGED"),
        }

        # Undo what can be undone live, and give up the change set's deleted record's rename.
        versions = dict(
            session.execute(
                select(RdmObject.id, RdmObject.version).where(RdmObject.id.in_(r))
            ).all()
        )
        _batch(
            session,
            [
                {
                    "op": "update",
                    "target": {"id": r[1]},
                    "expectedVersion": versions[r[1]],
                    "name": "R 1",
                },
                {
                    "op": "ensureNoRelation",
                    "relationTypeKey": cites,
                    "from": {"id": branch},
                    "to": {"id": tokens[2]},
                },
            ],
        )
        session.execute(
            ChangeSetObject.__table__.delete().where(
                ChangeSetObject.change_set_id == change_set.id, ChangeSetObject.object_id == r[2]
            )
        )
        session.commit()
        session.refresh(change_set)
        move = change_set_migrations.submit_change_set_migration(
            session,
            change_set.id,
            expected_change_set_version=change_set.version,
            target_release_id=None,
            type_mappings=[],
            retention_days=7,
        )
        session.commit()
        change_set_migrations.run_preview(session, move, retention_days=7, hold=lambda: None)
        session.commit()
        summary = move.report["migration"]
        assert summary["counts"]["refused"] == 0, list(
            session.scalars(select(JobItem.outcome).where(JobItem.job_id == move.sequence_id))
        )
        assert summary["counts"]["conversion"] >= 2
        assert migrations.check_confirmation(
            session,
            move,
            expected_version=summary["expectedVersion"],
            expected_feed_position=summary["feedPosition"],
            accept_loss=True,
        )
        session.commit()
        change_set_migrations.execute(session, move, retention_days=7, hold=lambda: None)

    with SessionLocal() as session:
        moved = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        assert moved.model_release_id == x2.id
        rows = list(
            session.scalars(
                select(ChangeSetObject).where(ChangeSetObject.change_set_id == moved.id)
            )
        )
        types = release_value_types(session.connection(), x2.id)
        indexed = session.scalar(
            select(func.count())
            .select_from(SnapshotAttributeValue)
            .where(SnapshotAttributeValue.owner_id == moved.id)
        )
        assert indexed == sum(
            len(value_rows("change_set", moved.id, row.object_id, row.attributes, types))
            for row in rows
            if not row.is_deleted
        )
        assert {
            item.value_type
            for item in session.scalars(
                select(SnapshotAttributeValue).where(
                    SnapshotAttributeValue.owner_id == moved.id,
                    SnapshotAttributeValue.attribute_type_key == KEYS["R.n"],
                )
            )
        } <= {"decimal"}
        assert matrix_states.verify(session) == []
