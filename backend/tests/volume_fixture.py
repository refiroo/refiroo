"""Track S volume fixture (Base 0.8 S1): a generated model and a bulk-seeded dataset.

The model uses its own application, object-type and relation keys, so no volume check relies on
the starter model. :func:`seed_volume` writes the dataset straight into the persistence tables
(the HTTP API takes about 13 s per 1000 records), then records the same membership as revision 1
of the workspace and derives a draft from that revision with edits, tombstones and new records
scattered through the data.

Every row is generated from a seeded ``random.Random``, so a shape always produces the same data,
public IDs included. :data:`FULL_SHAPE` is the plan's volume; tests use a scaled-down shape.
"""

import json
import random
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import event, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.database import (
    AttributeValue,
    Base,
    ModelRuntimeState,
    ObjectRelation,
    RdmObject,
    Workspace,
    WorkspaceDraft,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)
from app.services.snapshot_values import insert_value_rows, release_value_types, value_rows

APPLICATION = "vol-catalogue"
WORKSPACE = "vol-workspace"
GROUP, ITEM, NODE = "vol-group", "vol-item", "vol-node"
GROUP_CONTAINS_ITEM = "vol-group-contains-item"
GROUP_CONTAINS_NODE = "vol-group-contains-node"
NODE_HAS_CHILD = "vol-node-has-child"
ITEM_CITES_GROUP = "vol-item-cites-group"
CODE, RANK = "vol-code", "vol-rank"

_INSERT_BATCH = 5000


def volume_model() -> dict[str, Any]:
    """A schema 0.6 model shaped like the starter model but with no starter key."""

    def table(key: str, object_type: str) -> dict[str, Any]:
        return {
            "key": key,
            "name": key,
            "type": "table",
            "objectTypeKey": object_type,
            "config": {
                "columns": ["name", CODE, RANK],
                "filterFields": [CODE, RANK],
                "sortFields": ["name", CODE, RANK],
                "defaultSort": "name",
                "pageSize": 20,
            },
        }

    def object_type(key: str, parents: list[str], root: bool) -> dict[str, Any]:
        item: dict[str, Any] = {
            "key": key,
            "name": key,
            "pluralName": f"{key}s",
            "displayAttributeTypeKey": CODE,
            "attributes": [
                {"attributeTypeKey": CODE, "required": True, "order": 10},
                {"attributeTypeKey": RANK, "order": 20},
            ],
            "features": {"rootCreatable": root},
        }
        if parents:
            item["behavior"] = {"parentRelationTypeKeys": parents}
        return item

    def relation_type(key: str, **features: bool) -> dict[str, Any]:
        return {
            "key": key,
            "reverseKey": f"{key}-reverse",
            "name": key,
            "reverseName": f"{key} (reverse)",
            "features": features,
        }

    return {
        "schemaVersion": "0.6",
        "release": {"key": "vol-model", "name": "Volume model", "version": "0.8.0-s1"},
        "product": {"name": "Volume fixture", "description": "Generated Track S model"},
        "attributeTypes": [
            {
                "key": CODE,
                "name": "Code",
                "features": {
                    "searchable": True,
                    "unique": True,
                    "filterable": True,
                    "sortable": True,
                },
            },
            {
                "key": RANK,
                "name": "Rank",
                "valueType": "integer",
                "features": {"filterable": True, "sortable": True},
            },
        ],
        "objectTypes": [
            object_type(GROUP, [], True),
            object_type(ITEM, [GROUP_CONTAINS_ITEM], False),
            object_type(NODE, [GROUP_CONTAINS_NODE, NODE_HAS_CHILD], False),
        ],
        "relationTypes": [
            relation_type(GROUP_CONTAINS_ITEM, parentOf=True),
            relation_type(GROUP_CONTAINS_NODE, parentOf=True),
            relation_type(NODE_HAS_CHILD, parentOf=True, hierarchical=True),
            relation_type(ITEM_CITES_GROUP),
        ],
        "objectTypeRelations": [
            {
                "relationTypeKey": GROUP_CONTAINS_ITEM,
                "fromObjectTypeKey": GROUP,
                "toObjectTypeKey": ITEM,
                "cardinality": "one-to-many",
            },
            {
                "relationTypeKey": GROUP_CONTAINS_NODE,
                "fromObjectTypeKey": GROUP,
                "toObjectTypeKey": NODE,
                "cardinality": "one-to-many",
            },
            {
                "relationTypeKey": NODE_HAS_CHILD,
                "fromObjectTypeKey": NODE,
                "toObjectTypeKey": NODE,
                "cardinality": "one-to-many",
            },
            {
                "relationTypeKey": ITEM_CITES_GROUP,
                "fromObjectTypeKey": ITEM,
                "toObjectTypeKey": GROUP,
                "cardinality": "many-to-many",
            },
        ],
        "applications": [
            {
                "key": APPLICATION,
                "name": "Volume catalogue",
                "objectTypeKeys": [GROUP, ITEM, NODE],
                "defaultView": "groups",
                "views": [table("groups", GROUP), table("items", ITEM), table("nodes", NODE)],
            }
        ],
    }


@dataclass(frozen=True)
class VolumeShape:
    """Dataset dimensions. The skew and draft-edit spacing are fixed so shapes stay comparable."""

    groups: int
    items: int
    heavy_items: int  # items under the heavy group; the rest spread unevenly over other groups
    citations: int  # ITEM_CITES_GROUP relations onto the cited group
    node_depth: int  # levels of the NODE self-hierarchy under the heavy group
    node_fanout: int
    draft_edit_every: int = 97  # every n-th item is edited in the draft
    draft_delete_every: int = 211  # every n-th item is tombstoned in the draft
    draft_new_items: int = 50
    seed: int = 8


FULL_SHAPE = VolumeShape(
    groups=10_000,
    items=100_000,
    heavy_items=20_000,
    citations=1_500,
    node_depth=7,
    node_fanout=2,
)


def scaled_shape(factor: float) -> VolumeShape:
    """The full shape scaled by ``factor``; the hierarchy's depth and fan-out are not scaled."""
    return VolumeShape(
        groups=max(10, round(FULL_SHAPE.groups * factor)),
        items=max(100, round(FULL_SHAPE.items * factor)),
        heavy_items=max(20, round(FULL_SHAPE.heavy_items * factor)),
        # More than one 20-row page, so the first relation page is full at every scale.
        citations=max(25, round(FULL_SHAPE.citations * factor)),
        node_depth=FULL_SHAPE.node_depth,
        node_fanout=FULL_SHAPE.node_fanout,
        draft_new_items=max(5, round(FULL_SHAPE.draft_new_items * factor)),
    )


@dataclass
class VolumeDataset:
    """Public identifiers a measurement or test addresses in the seeded data."""

    shape: VolumeShape
    revision_id: str
    draft_id: str
    heavy_group_id: str  # holds ``heavy_items`` items and the root of the NODE hierarchy
    cited_group_id: str  # target of ``citations`` ITEM_CITES_GROUP relations
    small_group_id: str  # a group holding a handful of items
    deep_node_id: str  # a NODE at ``node_depth`` levels below the heavy group
    edited_item_id: str  # an item edited in the draft
    live_item_id: str  # an item neither edited nor deleted in the draft
    counts: dict[str, int] = field(default_factory=dict)


def seed_volume(engine: Engine, shape: VolumeShape) -> VolumeDataset:
    """Bulk-write live data, revision 1 and a derived draft into an app-migrated database.

    The database must already hold the volume model as its active release (start the app with
    ``RDM_MODEL_PATH`` pointing at :func:`volume_model`).
    """
    rng = random.Random(shape.seed)
    now = datetime(2026, 9, 25, tzinfo=UTC)

    def new_id() -> str:
        return str(UUID(int=rng.getrandbits(128), version=4))

    objects: list[dict[str, Any]] = []
    attributes: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []

    def add_object(object_type: str, prefix: str, number: int, parent: str | None) -> str:
        object_id = new_id()
        objects.append(
            {
                "id": object_id,
                "workspace_key": WORKSPACE,
                "application_key": APPLICATION,
                "object_type_key": object_type,
                "parent_object_id": parent,
                "name": f"{prefix} {number:06d}",
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )
        attributes[object_id] = {CODE: f"{prefix.upper()}-{number:06d}", RANK: number % 1000}
        return object_id

    def add_relation(relation_type: str, source: str, target: str) -> str:
        relation_id = new_id()
        relations.append(
            {
                "id": relation_id,
                "relation_type_key": relation_type,
                "from_object_id": source,
                "to_object_id": target,
                "attributes": {},
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )
        return relation_id

    # Creation order differs from name order, as it does after real editing.
    group_numbers = list(range(shape.groups))
    rng.shuffle(group_numbers)
    groups = [add_object(GROUP, "Group", number, None) for number in group_numbers]
    heavy, cited, small = groups[0], groups[1], groups[2]

    item_numbers = list(range(shape.items))
    rng.shuffle(item_numbers)
    item_parents = [heavy] * shape.heavy_items + [small] * 5
    others = groups[3:]
    while len(item_parents) < shape.items:
        # Skewed towards the first groups: a few hold thousands of items, most a few or none.
        item_parents.append(others[int(len(others) * rng.random() ** 3)])
    rng.shuffle(item_parents)
    items = []
    for number, parent in zip(item_numbers, item_parents, strict=True):
        item = add_object(ITEM, "Item", number, parent)
        add_relation(GROUP_CONTAINS_ITEM, parent, item)
        items.append(item)

    level = [heavy]
    node_number = 0
    for depth in range(shape.node_depth):
        next_level = []
        for parent in level:
            for _ in range(shape.node_fanout):
                node = add_object(NODE, "Node", node_number, parent)
                node_number += 1
                add_relation(GROUP_CONTAINS_NODE if depth == 0 else NODE_HAS_CHILD, parent, node)
                next_level.append(node)
        level = next_level
    deep_node = level[-1]

    citing = items[: shape.citations]
    for item in citing:
        add_relation(ITEM_CITES_GROUP, item, cited)

    _bulk_insert(engine, Workspace, [{"key": WORKSPACE, "label": "Volume", "version": 1}])
    _bulk_insert(engine, RdmObject, objects)
    for key in (CODE, RANK):
        _bulk_insert(engine, AttributeValue, _attribute_rows(attributes, new_id, key))
    _bulk_insert(engine, ObjectRelation, relations)

    with Session(engine) as session:
        release_id = session.scalar(select(ModelRuntimeState.active_model_release_id))
        assert release_id is not None, "The volume model must be active before seeding"
        revision = WorkspaceRevision(
            id=new_id(),
            workspace_key=WORKSPACE,
            model_release_id=release_id,
            revision_number=1,
            status="active",
            created_at=now,
            activated_at=now,
        )
        session.add(revision)
        session.flush()
        session.get(Workspace, WORKSPACE).active_revision_id = revision.id
        draft = WorkspaceDraft(
            id=new_id(),
            workspace_key=WORKSPACE,
            model_release_id=release_id,
            derived_from_revision_id=revision.id,
            name="Volume draft",
        )
        session.add(draft)
        session.commit()
        revision_id, draft_id = revision.id, draft.id

    by_id = {row["id"]: row for row in objects}
    _bulk_insert(
        engine,
        WorkspaceRevisionObject,
        [_membership_row(row, attributes, revision_id=revision_id) for row in objects],
    )
    _bulk_insert(
        engine,
        WorkspaceRevisionRelation,
        [_relation_row(row, revision_id=revision_id) for row in relations],
    )
    _index_values(
        engine,
        "revision",
        release_id,
        ((revision_id, row["id"], attributes[row["id"]]) for row in objects),
    )

    # Draft edits land across the whole name range, not in one block.
    containment = {
        row["to_object_id"]: row for row in relations if row["relation_type_key"] == GROUP_CONTAINS_ITEM
    }
    cited_items = set(citing)
    draft_objects: list[dict[str, Any]] = []
    draft_relations: list[dict[str, Any]] = []
    edited = [
        item for index, item in enumerate(items) if index % shape.draft_edit_every == 1
    ]
    edited_items = set(edited)
    deleted = [
        item
        for index, item in enumerate(items)
        if index % shape.draft_delete_every == 2
        and item not in cited_items
        and item not in edited_items
    ]
    for item in edited:
        row = _membership_row(by_id[item], attributes, draft_id=draft_id)
        row["name"] += " (edited)"
        row["attributes"] = {**row["attributes"], RANK: row["attributes"][RANK] + 1}
        row["version"] = 2
        row["is_deleted"] = False
        draft_objects.append(row)
    for item in deleted:
        draft_objects.append(
            {**_membership_row(by_id[item], attributes, draft_id=draft_id), "is_deleted": True}
        )
        draft_relations.append(
            {**_relation_row(containment[item], draft_id=draft_id), "is_deleted": True}
        )
    for offset in range(shape.draft_new_items):
        parent = groups[rng.randrange(len(groups))]
        number = shape.items + offset
        new_item = new_id()
        draft_objects.append(
            {
                "draft_id": draft_id,
                "object_id": new_item,
                "application_key": APPLICATION,
                "object_type_key": ITEM,
                "name": f"Item {number:06d}",
                "parent_object_id": parent,
                "attributes": {CODE: f"ITEM-{number:06d}", RANK: number % 1000},
                "version": 1,
                "is_deleted": False,
            }
        )
        draft_relations.append(
            {
                "draft_id": draft_id,
                "relation_id": new_id(),
                "relation_type_key": GROUP_CONTAINS_ITEM,
                "from_object_id": parent,
                "to_object_id": new_item,
                "attributes": {},
                "version": 1,
                "is_deleted": False,
            }
        )
    _bulk_insert(engine, WorkspaceDraftObject, draft_objects)
    _index_values(
        engine,
        "draft",
        release_id,
        (
            (draft_id, row["object_id"], row["attributes"])
            for row in draft_objects
            if not row["is_deleted"]
        ),
    )
    _bulk_insert(engine, WorkspaceDraftRelation, draft_relations)

    touched = edited_items | set(deleted) | cited_items
    untouched = next(item for item in items if item not in touched)
    return VolumeDataset(
        shape=shape,
        revision_id=revision_id,
        draft_id=draft_id,
        heavy_group_id=heavy,
        cited_group_id=cited,
        small_group_id=small,
        deep_node_id=deep_node,
        edited_item_id=edited[0],
        live_item_id=untouched,
        counts={
            "objects": len(objects),
            "attributeValues": 2 * len(objects),
            "relations": len(relations),
            "nodes": node_number,
            "draftObjects": len(draft_objects),
            "draftRelations": len(draft_relations),
            "draftEdited": len(edited),
            "draftDeleted": len(deleted),
            "draftNew": shape.draft_new_items,
        },
    )


def _attribute_rows(
    attributes: dict[str, dict[str, Any]], new_id, key: str
) -> Iterator[dict[str, Any]]:
    """Typed live value rows for one attribute; executemany needs one key set per pass."""
    value_type, column = ("text", "text_value") if key == CODE else ("integer", "integer_value")
    for object_id, values in attributes.items():
        yield {
            "id": new_id(),
            "object_id": object_id,
            "attribute_type_key": key,
            "value_type": value_type,
            column: values[key],
            "value_source": "own",
            "version": 1,
        }


def _membership_row(
    row: dict[str, Any],
    attributes: dict[str, dict[str, Any]],
    *,
    revision_id: str | None = None,
    draft_id: str | None = None,
) -> dict[str, Any]:
    owner = {"revision_id": revision_id} if revision_id else {"draft_id": draft_id}
    return {
        **owner,
        "object_id": row["id"],
        "application_key": row["application_key"],
        "object_type_key": row["object_type_key"],
        "name": row["name"],
        "parent_object_id": row["parent_object_id"],
        "attributes": dict(attributes[row["id"]]),
        "version": row["version"],
    }


def _relation_row(
    row: dict[str, Any], *, revision_id: str | None = None, draft_id: str | None = None
) -> dict[str, Any]:
    owner = {"revision_id": revision_id} if revision_id else {"draft_id": draft_id}
    return {
        **owner,
        "relation_id": row["id"],
        "relation_type_key": row["relation_type_key"],
        "from_object_id": row["from_object_id"],
        "to_object_id": row["to_object_id"],
        "attributes": {},
        "version": row["version"],
    }


def _index_values(engine: Engine, owner_kind: str, release_id: int, rows) -> None:
    """Write the typed value index the app's flush hook writes for ORM-inserted rows."""
    with engine.begin() as connection:
        value_types = release_value_types(connection, release_id)
        insert_value_rows(
            connection,
            (
                value
                for owner_id, object_id, values in rows
                for value in value_rows(owner_kind, owner_id, object_id, values, value_types)
            ),
        )


def _bulk_insert(engine: Engine, table: type[Base], rows) -> None:
    """Insert in batches. executemany takes its columns from the first row of a batch, so every
    row of one call must carry the same keys."""
    batch: list[dict[str, Any]] = []
    columns: set[str] | None = None
    with engine.begin() as connection:
        for row in rows:
            if columns is None:
                columns = set(row)
            elif set(row) != columns:
                raise ValueError(f"{table.__tablename__} rows differ in columns: {sorted(row)}")
            batch.append(row)
            if len(batch) == _INSERT_BATCH:
                connection.execute(insert(table), batch)
                batch = []
        if batch:
            connection.execute(insert(table), batch)


@dataclass
class RequestCost:
    """What one request cost the database: statements executed and ORM rows materialised."""

    statements: int = 0
    rows_loaded: int = 0
    seconds: float = 0.0


@contextmanager
def measure(engine: Engine) -> Iterator[RequestCost]:
    """Count SQL statements on ``engine`` and ORM instances loaded while the block runs.

    ``rows_loaded`` counts entities the ORM builds from result rows, which is where whole-set
    loading shows: a bounded page loads a page of rows, a whole-membership read loads the set.
    """
    cost = RequestCost()

    def on_execute(*_args: Any) -> None:
        cost.statements += 1

    def on_load(*_args: Any) -> None:
        cost.rows_loaded += 1

    event.listen(engine, "before_cursor_execute", on_execute)
    event.listen(Base, "load", on_load, propagate=True)
    started = time.perf_counter()
    try:
        yield cost
    finally:
        cost.seconds = time.perf_counter() - started
        event.remove(engine, "before_cursor_execute", on_execute)
        event.remove(Base, "load", on_load)


@contextmanager
def volume_app(template: Path, directory: Path, shape: VolumeShape) -> Iterator[tuple[Any, VolumeDataset]]:
    """A test client over a copy of the migrated ``template`` holding the seeded volume data."""
    # Imported here: the baseline script must set its database before the app is imported.
    import pytest
    from fastapi.testclient import TestClient

    from app.config import reload_settings
    from app.db import get_engine
    from app.main import create_app
    from app.services.model.registry import model_registry

    database = directory / "volume.db"
    shutil.copyfile(template, database)
    model_path = directory / "volume-model.json"
    model_path.write_text(json.dumps(volume_model()))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database}")
        patch.setenv("RDM_MODEL_PATH", str(model_path))
        model_registry.clear()
        try:
            with TestClient(create_app()) as client:
                yield client, seed_volume(get_engine(), shape)
        finally:
            get_engine().dispose()
    reload_settings()
    model_registry.clear()
