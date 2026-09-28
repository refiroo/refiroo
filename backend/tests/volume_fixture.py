"""Track S volume fixture (Base 0.8 S1): a generated model and a bulk-seeded dataset.

The model uses its own application, object-type and relation keys, so no volume check relies on
the starter model. A second application, ``vol-matrix`` (Base 0.8 A2), adds relation matrices over the
same groups: columns with a three-level container hierarchy, cells under it, a conditioned
one-to-many binding read outgoing and a many-to-many binding read incoming. :func:`seed_volume` writes the dataset straight into the persistence tables
(the HTTP API takes about 13 s per 1000 records), then records the same membership as publication 1
of the workspace and derives a change set from that publication with edits, tombstones and new records
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
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    ModelRuntimeState,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    Workspace,
)
from app.services import matrix_states
from app.services.snapshot_values import insert_value_rows, release_value_types, value_rows

APPLICATION = "vol-catalogue"
WORKSPACE = "vol-workspace"
GROUP, ITEM, NODE = "vol-group", "vol-item", "vol-node"
GROUP_CONTAINS_ITEM = "vol-group-contains-item"
GROUP_CONTAINS_NODE = "vol-group-contains-node"
NODE_HAS_CHILD = "vol-node-has-child"
ITEM_CITES_GROUP = "vol-item-cites-group"
CODE, RANK = "vol-code", "vol-rank"

# Base 0.8 A2: relation matrices over the groups.
MATRIX_APPLICATION = "vol-matrix"
COLUMN, SHELF, CELL = "vol-column", "vol-shelf", "vol-cell"
COLUMN_CONTAINS_SHELF = "vol-column-contains-shelf"
SHELF_HAS_CHILD = "vol-shelf-has-child"
SHELF_CONTAINS_CELL = "vol-shelf-contains-cell"
GROUP_HAS_CELL = "vol-group-has-cell"
CELL_MARKS_GROUP = "vol-cell-marks-group"
ACTIVE = "vol-active"
CELLS_BY_COLUMN, MARKS_BY_COLUMN = "cells-by-column", "marks-by-column"
MATRIX_COLUMNS = 30
CELLS_PER_GROUP = 15  # in every other column, so half of each row's cells are empty
SHELF_DEPTH, SHELF_FANOUT = 3, 2

_INSERT_BATCH = 5000


def volume_model() -> dict[str, Any]:
    """A schema 0.7 model shaped like the starter model but with no starter key."""

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

    def object_type(
        key: str, parents: list[str], root: bool, extra: tuple[str, ...] = ()
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "key": key,
            "name": key,
            "pluralName": f"{key}s",
            "displayAttributeTypeKey": CODE,
            "attributes": [
                {"attributeTypeKey": CODE, "required": True, "order": 10},
                {"attributeTypeKey": RANK, "order": 20},
                *({"attributeTypeKey": field, "order": 30} for field in extra),
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

    def matrix(key: str, relation: str, direction: str, actions: list[str]) -> dict[str, Any]:
        return {
            "key": key,
            "name": key,
            "type": "relationMatrix",
            "config": {
                "relationTypeKey": relation,
                "direction": direction,
                "rowObjectTypeKey": GROUP,
                "columnObjectTypeKey": COLUMN,
                "cellObjectTypeKey": CELL,
                "rowColumns": ["name", CODE],
                "columnLabelField": CODE,
                "cellFields": [CODE, ACTIVE],
                "searchFields": ["name", CODE],
                "cellActions": actions,
                "pageSize": 20,
            },
        }

    return {
        "schemaVersion": "0.7",
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
            {
                "key": ACTIVE,
                "name": "Active",
                "valueType": "boolean",
                "default": True,
                "features": {"filterable": True},
            },
        ],
        "objectTypes": [
            object_type(GROUP, [], True),
            object_type(ITEM, [GROUP_CONTAINS_ITEM], False),
            object_type(NODE, [GROUP_CONTAINS_NODE, NODE_HAS_CHILD], False),
            object_type(COLUMN, [], True),
            object_type(SHELF, [COLUMN_CONTAINS_SHELF, SHELF_HAS_CHILD], False),
            object_type(CELL, [SHELF_CONTAINS_CELL], False, (ACTIVE,)),
        ],
        "relationTypes": [
            relation_type(GROUP_CONTAINS_ITEM, parentOf=True),
            relation_type(GROUP_CONTAINS_NODE, parentOf=True),
            relation_type(NODE_HAS_CHILD, parentOf=True, hierarchical=True),
            relation_type(ITEM_CITES_GROUP),
            relation_type(COLUMN_CONTAINS_SHELF, parentOf=True),
            relation_type(SHELF_HAS_CHILD, parentOf=True, hierarchical=True),
            relation_type(SHELF_CONTAINS_CELL, parentOf=True),
            relation_type(GROUP_HAS_CELL),
            relation_type(CELL_MARKS_GROUP),
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
            {
                "relationTypeKey": COLUMN_CONTAINS_SHELF,
                "fromObjectTypeKey": COLUMN,
                "toObjectTypeKey": SHELF,
                "cardinality": "one-to-many",
            },
            {
                "relationTypeKey": SHELF_HAS_CHILD,
                "fromObjectTypeKey": SHELF,
                "toObjectTypeKey": SHELF,
                "cardinality": "one-to-many",
            },
            {
                "relationTypeKey": SHELF_CONTAINS_CELL,
                "fromObjectTypeKey": SHELF,
                "toObjectTypeKey": CELL,
                "cardinality": "one-to-many",
            },
            {
                # The translation shape: required, one active cell per group and column.
                "relationTypeKey": GROUP_HAS_CELL,
                "fromObjectTypeKey": GROUP,
                "toObjectTypeKey": CELL,
                "cardinality": "one-to-many",
                "required": True,
                "features": {
                    "uniqueToAncestorTypeKey": COLUMN,
                    "uniqueWhenToAttributeEquals": {"attributeTypeKey": ACTIVE, "value": True},
                },
            },
            {
                "relationTypeKey": CELL_MARKS_GROUP,
                "fromObjectTypeKey": CELL,
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
                "views": [
                    table("groups", GROUP),
                    {
                        # Base 0.8 B1: mixed types under a group, then the deep node self-hierarchy.
                        "key": "hierarchy",
                        "name": "hierarchy",
                        "type": "tree",
                        "config": {
                            "rootObjectTypeKeys": [GROUP],
                            "objectTypeKeys": [GROUP, ITEM, NODE],
                            "labelField": "name",
                            "secondaryField": CODE,
                            "childSort": {NODE: RANK},
                            "pageSize": 50,
                            "actions": ["createChild", "rename", "move"],
                        },
                    },
                    table("items", ITEM),
                    table("nodes", NODE),
                ],
            },
            {
                "key": MATRIX_APPLICATION,
                "name": "Volume matrix",
                "objectTypeKeys": [GROUP, COLUMN, SHELF, CELL],
                "defaultView": "columns",
                "views": [
                    table("columns", COLUMN),
                    matrix(CELLS_BY_COLUMN, GROUP_HAS_CELL, "outgoing", ["create", "edit"]),
                    matrix(MARKS_BY_COLUMN, CELL_MARKS_GROUP, "incoming", ["link", "unlink"]),
                ],
            },
        ],
    }


@dataclass(frozen=True)
class VolumeShape:
    """Dataset dimensions. The skew and change set-edit spacing are fixed so shapes stay comparable."""

    groups: int
    items: int
    heavy_items: int  # items under the heavy group; the rest spread unevenly over other groups
    citations: int  # ITEM_CITES_GROUP relations onto the cited group
    node_depth: int  # levels of the NODE self-hierarchy under the heavy group
    node_fanout: int
    change_set_edit_every: int = 97  # every n-th item is edited in the change set
    change_set_delete_every: int = 211  # every n-th item is tombstoned in the change set
    change_set_new_items: int = 50
    seed: int = 8
    # Base 0.8 A2: CELLS_PER_GROUP cells per group; every n-th cell is inactive, every n-th was
    # deleted live after publication 1 (history only), every n-th also marks the next group, and
    # every n-th group holds an extra inactive cell beside an active one.
    matrix_inactive_every: int = 10
    matrix_retired_every: int = 50
    matrix_second_mark_every: int = 7
    matrix_extra_every: int = 100


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
        change_set_new_items=max(5, round(FULL_SHAPE.change_set_new_items * factor)),
    )


@dataclass
class VolumeDataset:
    """Public identifiers a measurement or test addresses in the seeded data."""

    shape: VolumeShape
    publication_id: str
    change_set_id: str
    heavy_group_id: str  # holds ``heavy_items`` items and the root of the NODE hierarchy
    cited_group_id: str  # target of ``citations`` ITEM_CITES_GROUP relations
    small_group_id: str  # a group holding a handful of items
    deep_node_id: str  # a NODE at ``node_depth`` levels below the heavy group
    edited_item_id: str  # an item edited in the change set
    live_item_id: str  # an item neither edited nor deleted in the change set
    counts: dict[str, int] = field(default_factory=dict)
    matrix_column_ids: list[str] = field(default_factory=list)  # in name order


def seed_volume(engine: Engine, shape: VolumeShape) -> VolumeDataset:
    """Bulk-write live data, publication 1 and a derived change set into an app-migrated database.

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

    # Its own random stream, so the catalogue's public IDs stay those of the S1 fixture. The heavy,
    # cited and small groups keep only the relations the S1-S8 checks count.
    matrix = _matrix_data(shape, groups[3:], now)

    _bulk_insert(engine, Workspace, [{"key": WORKSPACE, "label": "Volume", "version": 1}])
    _bulk_insert(engine, RdmObject, [*objects, *matrix.objects])
    for key in (CODE, RANK):
        _bulk_insert(engine, AttributeValue, _attribute_rows(attributes, new_id, key))
    for key in (CODE, RANK, ACTIVE):
        live = {row["id"]: matrix.attributes[row["id"]] for row in matrix.objects}
        _bulk_insert(engine, AttributeValue, _attribute_rows(live, matrix.new_id, key))
    _bulk_insert(engine, ObjectRelation, [*relations, *matrix.relations])

    with Session(engine) as session:
        release_id = session.scalar(select(ModelRuntimeState.active_model_release_id))
        assert release_id is not None, "The volume model must be active before seeding"
        publication = Publication(
            id=new_id(),
            workspace_key=WORKSPACE,
            model_release_id=release_id,
            publication_number=1,
            status="active",
            created_at=now,
            published_at=now,
        )
        session.add(publication)
        session.flush()
        session.get(Workspace, WORKSPACE).active_publication_id = publication.id
        change_set = ChangeSet(
            id=new_id(),
            workspace_key=WORKSPACE,
            model_release_id=release_id,
            derived_from_publication_id=publication.id,
            name="Volume change set",
        )
        session.add(change_set)
        session.commit()
        publication_id, change_set_id = publication.id, change_set.id

    by_id = {row["id"]: row for row in objects}
    # Publication 1 holds the live membership plus the matrix cells deleted live since.
    published = [*objects, *matrix.objects, *matrix.retired_objects]
    all_attributes = {**attributes, **matrix.attributes}
    _bulk_insert(
        engine,
        PublicationObject,
        [_membership_row(row, all_attributes, publication_id=publication_id) for row in published],
    )
    _bulk_insert(
        engine,
        PublicationRelation,
        [
            _relation_row(row, publication_id=publication_id)
            for row in (*relations, *matrix.relations, *matrix.retired_relations)
        ],
    )
    _index_values(
        engine,
        "publication",
        release_id,
        ((publication_id, row["id"], all_attributes[row["id"]]) for row in published),
    )

    # Change set edits land across the whole name range, not in one block.
    containment = {
        row["to_object_id"]: row for row in relations if row["relation_type_key"] == GROUP_CONTAINS_ITEM
    }
    cited_items = set(citing)
    change_set_objects: list[dict[str, Any]] = []
    change_set_relations: list[dict[str, Any]] = []
    edited = [
        item for index, item in enumerate(items) if index % shape.change_set_edit_every == 1
    ]
    edited_items = set(edited)
    deleted = [
        item
        for index, item in enumerate(items)
        if index % shape.change_set_delete_every == 2
        and item not in cited_items
        and item not in edited_items
    ]
    for item in edited:
        row = _membership_row(by_id[item], attributes, change_set_id=change_set_id)
        row["name"] += " (edited)"
        row["attributes"] = {**row["attributes"], RANK: row["attributes"][RANK] + 1}
        row["version"] = 2
        row["is_deleted"] = False
        change_set_objects.append(row)
    for item in deleted:
        change_set_objects.append(
            {**_membership_row(by_id[item], attributes, change_set_id=change_set_id), "is_deleted": True}
        )
        change_set_relations.append(
            {**_relation_row(containment[item], change_set_id=change_set_id), "is_deleted": True}
        )
    for offset in range(shape.change_set_new_items):
        parent = groups[rng.randrange(len(groups))]
        number = shape.items + offset
        new_item = new_id()
        change_set_objects.append(
            {
                "change_set_id": change_set_id,
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
        change_set_relations.append(
            {
                "change_set_id": change_set_id,
                "relation_id": new_id(),
                "relation_type_key": GROUP_CONTAINS_ITEM,
                "from_object_id": parent,
                "to_object_id": new_item,
                "attributes": {},
                "version": 1,
                "is_deleted": False,
            }
        )
    for row in matrix.change_set_objects:
        change_set_objects.append({"change_set_id": change_set_id, **row})
    for row in matrix.change_set_relations:
        change_set_relations.append({"change_set_id": change_set_id, **row})
    _bulk_insert(engine, ChangeSetObject, change_set_objects)
    _index_values(
        engine,
        "change_set",
        release_id,
        (
            (change_set_id, row["object_id"], row["attributes"])
            for row in change_set_objects
            if not row["is_deleted"]
        ),
    )
    _bulk_insert(engine, ChangeSetRelation, change_set_relations)

    # The bulk rows bypass the ORM hooks that maintain stored matrix cell states: build them (A3b).
    with Session(engine) as session:
        matrix_states.sync_all(session)
        session.commit()

    touched = edited_items | set(deleted) | cited_items
    untouched = next(item for item in items if item not in touched)
    return VolumeDataset(
        shape=shape,
        publication_id=publication_id,
        change_set_id=change_set_id,
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
            "changeSetObjects": len(change_set_objects),
            "changeSetRelations": len(change_set_relations),
            "changeSetEdited": len(edited),
            "changeSetDeleted": len(deleted),
            "changeSetNew": shape.change_set_new_items,
            **matrix.counts,
        },
        matrix_column_ids=matrix.column_ids,
    )


@dataclass
class _MatrixData:
    """The ``vol-matrix`` rows: live, deleted live after publication 1, and new in the change set."""

    new_id: Any
    objects: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    retired_objects: list[dict[str, Any]] = field(default_factory=list)
    retired_relations: list[dict[str, Any]] = field(default_factory=list)
    attributes: dict[str, dict[str, Any]] = field(default_factory=dict)
    change_set_objects: list[dict[str, Any]] = field(default_factory=list)
    change_set_relations: list[dict[str, Any]] = field(default_factory=list)
    column_ids: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def _matrix_data(shape: VolumeShape, groups: list[str], now: datetime) -> _MatrixData:
    """Columns with a three-level shelf hierarchy each, and CELLS_PER_GROUP cells per group.

    Group ``g`` (by creation index) has cells in the columns of its own parity, ``g, g + 2, ...``
    modulo MATRIX_COLUMNS, so every row has as many empty cells as filled ones.
    """
    rng = random.Random(shape.seed + 1)

    def new_id() -> str:
        return str(UUID(int=rng.getrandbits(128), version=4))

    data = _MatrixData(new_id)

    def add_object(target: list, object_type: str, prefix: str, number: int, parent: str | None, **extra) -> str:
        object_id = new_id()
        target.append(
            {
                "id": object_id,
                "workspace_key": WORKSPACE,
                "application_key": MATRIX_APPLICATION,
                "object_type_key": object_type,
                "parent_object_id": parent,
                "name": f"{prefix} {number:07d}",
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )
        data.attributes[object_id] = {CODE: f"{prefix.upper()}-{number:07d}", RANK: number % 1000, **extra}
        return object_id

    def add_relation(target: list, relation_type: str, source: str, destination: str) -> None:
        target.append(
            {
                "id": new_id(),
                "relation_type_key": relation_type,
                "from_object_id": source,
                "to_object_id": destination,
                "attributes": {},
                "version": 1,
                "created_at": now,
                "updated_at": now,
            }
        )

    leaves: list[list[str]] = []
    shelf_number = 0
    for number in range(MATRIX_COLUMNS):
        column_id = add_object(data.objects, COLUMN, "Column", number, None)
        data.column_ids.append(column_id)
        level = [column_id]
        for depth in range(SHELF_DEPTH):
            next_level = []
            for parent in level:
                for _ in range(SHELF_FANOUT):
                    shelf = add_object(data.objects, SHELF, "Shelf", shelf_number, parent)
                    shelf_number += 1
                    relation = COLUMN_CONTAINS_SHELF if depth == 0 else SHELF_HAS_CHILD
                    add_relation(data.relations, relation, parent, shelf)
                    next_level.append(shelf)
            level = next_level
        leaves.append(level)

    cell_number = 0
    retired = inactive = 0

    def add_cell(group_index: int, column: int, *, active: bool) -> None:
        nonlocal cell_number, retired, inactive
        number = cell_number
        cell_number += 1
        gone = number % shape.matrix_retired_every == shape.matrix_retired_every // 2
        objects, relations = (
            (data.retired_objects, data.retired_relations) if gone else (data.objects, data.relations)
        )
        retired += gone
        inactive += not active
        shelf = leaves[column][(group_index + number) % len(leaves[column])]
        group = groups[group_index]
        cell = add_object(objects, CELL, "Cell", number, shelf, **{ACTIVE: active})
        add_relation(relations, SHELF_CONTAINS_CELL, shelf, cell)
        add_relation(relations, GROUP_HAS_CELL, group, cell)
        add_relation(relations, CELL_MARKS_GROUP, cell, group)
        if number % shape.matrix_second_mark_every == 3:
            add_relation(relations, CELL_MARKS_GROUP, cell, groups[(group_index + 1) % len(groups)])

    for group_index in range(len(groups)):
        for step in range(CELLS_PER_GROUP):
            active = cell_number % shape.matrix_inactive_every != shape.matrix_inactive_every - 1
            add_cell(group_index, (group_index + 2 * step) % MATRIX_COLUMNS, active=active)
        if group_index % shape.matrix_extra_every == 0:
            add_cell(group_index, group_index % MATRIX_COLUMNS, active=False)

    # The change set fills one of each chosen row's empty cells.
    for offset in range(shape.change_set_new_items):
        group_index = (offset * 37) % len(groups)
        column = (group_index + 1) % MATRIX_COLUMNS
        shelf, group = leaves[column][0], groups[group_index]
        cell = new_id()
        number = cell_number + offset
        data.attributes[cell] = {CODE: f"CELL-{number:07d}", RANK: number % 1000, ACTIVE: True}
        data.change_set_objects.append(
            {
                "object_id": cell,
                "application_key": MATRIX_APPLICATION,
                "object_type_key": CELL,
                "name": f"Cell {number:07d}",
                "parent_object_id": shelf,
                "attributes": dict(data.attributes[cell]),
                "version": 1,
                "is_deleted": False,
            }
        )
        for relation_type, source, destination in (
            (SHELF_CONTAINS_CELL, shelf, cell),
            (GROUP_HAS_CELL, group, cell),
            (CELL_MARKS_GROUP, cell, group),
        ):
            data.change_set_relations.append(
                {
                    "relation_id": new_id(),
                    "relation_type_key": relation_type,
                    "from_object_id": source,
                    "to_object_id": destination,
                    "attributes": {},
                    "version": 1,
                    "is_deleted": False,
                }
            )
    data.counts = {
        "matrixColumns": MATRIX_COLUMNS,
        "matrixShelves": shelf_number,
        "matrixCells": cell_number,
        "matrixInactiveCells": inactive,
        "matrixRetiredCells": retired,
        "matrixRelations": len(data.relations) + len(data.retired_relations),
    }
    return data


def _attribute_rows(
    attributes: dict[str, dict[str, Any]], new_id, key: str
) -> Iterator[dict[str, Any]]:
    """Typed live value rows for one attribute; executemany needs one key set per pass."""
    value_type, column = {
        CODE: ("text", "text_value"),
        RANK: ("integer", "integer_value"),
        ACTIVE: ("boolean", "boolean_value"),
    }[key]
    for object_id, values in attributes.items():
        if key not in values:
            continue
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
    publication_id: str | None = None,
    change_set_id: str | None = None,
) -> dict[str, Any]:
    owner = {"publication_id": publication_id} if publication_id else {"change_set_id": change_set_id}
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
    row: dict[str, Any], *, publication_id: str | None = None, change_set_id: str | None = None
) -> dict[str, Any]:
    owner = {"publication_id": publication_id} if publication_id else {"change_set_id": change_set_id}
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
