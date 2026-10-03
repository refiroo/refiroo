"""Base 0.8 S1: the volume fixture is faithful to real persistence, and read budgets hold.

The budgets are deterministic: the number of SQL statements a request executes must not change
when the dataset grows fourfold, and a request may materialise at most ``ROWS_PER_LISTED_ROW`` ORM
rows per row of a full page, at either scale. Row counts vary by a few with page content (records
on one page can share a parent), so they are bounded rather than compared. Wall-time figures at full volume come from
``volume_baseline.py`` and are recorded in docs/BASE_0_8_IMPLEMENTATION_PLAN.md.

Live reads meet the budgets, and since S2 so do change set and history reads, which answer in SQL. Since
S2b change set writes do too: they read only the records and relations they touch. Since A3b the
relation matrix's state filters read stored cell states, so a filtered page, its total and a
position jump cost the same statements at both scales and meet the 100 ms budget at full volume.
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import event, func, select
from volume_baseline import FEED_PAGE, PAGE_SIZE, run_scenarios
from volume_fixture import (
    CELL,
    CELLS_PER_GROUP,
    GROUP,
    ITEM,
    ITEM_CITES_GROUP,
    NODE,
    WORKSPACE,
    scaled_shape,
    seed_fresh,
    volume_app,
    volume_model,
)

from app.db import get_engine
from app.models.database import (
    ObjectRelation,
    PublicationObject,
    PublicationRelation,
    RdmObject,
)

SMALL, LARGE = scaled_shape(0.01), scaled_shape(0.04)
ROWS_PER_LISTED_ROW = 6


@pytest.fixture(scope="module")
def baselines(tmp_path_factory) -> dict[str, object]:
    """The scenario measurements at the small and the four-times-larger scale."""
    results = {}
    for label, shape in (("small", SMALL), ("large", LARGE)):
        directory = tmp_path_factory.mktemp(f"volume-{label}")
        with volume_app(directory, shape) as (client, dataset):
            results[label] = run_scenarios(client, get_engine(), dataset, repeat=0)
            results[f"{label}-dataset"] = dataset
    return results


def _pairs(baselines, contexts: set[str], *, writes: bool):
    large = {(item.context, item.scenario): item for item in baselines["large"]}
    for small in baselines["small"]:
        if small.context in contexts and small.scenario.startswith("write:") == writes:
            yield small, large[(small.context, small.scenario)]


def _over_budget(baselines, contexts: set[str], *, writes: bool = False) -> list[str]:
    failures = []
    for small, large in _pairs(baselines, contexts, writes=writes):
        label = f"{small.context} · {small.scenario}"
        if small.statements != large.statements:
            failures.append(f"{label}: statements {small.statements} → {large.statements} at 4× data")
        worst = max(small.rows_loaded, large.rows_loaded)
        page = FEED_PAGE if small.scenario.startswith("feed:") else PAGE_SIZE
        if worst > ROWS_PER_LISTED_ROW * page:
            failures.append(
                f"{label}: rows {small.rows_loaded:,} → {large.rows_loaded:,} at 4× data, "
                f"over {ROWS_PER_LISTED_ROW * page} for a {page}-row page"
            )
    return failures


def test_live_reads_and_writes_do_not_grow_with_the_dataset(baselines):
    assert not _over_budget(baselines, {"live"})
    assert not _over_budget(baselines, {"live"}, writes=True)


def test_change_set_and_history_reads_hold_the_live_budget(baselines):
    assert not _over_budget(baselines, {"change_set", "history"})


def test_change_set_writes_hold_the_live_budget(baselines):
    assert not _over_budget(baselines, {"change_set"}, writes=True)


def _largest_parameter_list(client, engine, dataset) -> dict[str, int]:
    """The most parameters one statement binds while a change set is captured from current live,
    one record is renamed in it, and it is published."""
    largest = {"capture": 0, "publish": 0}
    step = "capture"

    def on_execute(_conn, _cursor, _statement, parameters, _context, executemany) -> None:
        rows = parameters if executemany else [parameters]
        largest[step] = max(largest[step], *(len(row or ()) for row in rows))

    event.listen(engine, "before_cursor_execute", on_execute)
    try:
        created = client.post(
            f"/api/v1/workspaces/{WORKSPACE}/change-sets",
            json={"name": "Whole workspace", "source": "currentLive"},
        )
        assert created.status_code == 201, created.text
        change_set = created.json()
        item = client.get(
            f"/api/v1/objects/{ITEM}/{dataset.live_item_id}", params={"changeSetId": change_set["id"]}
        ).json()
        renamed = client.patch(
            f"/api/v1/objects/{ITEM}/{dataset.live_item_id}",
            json={
                "name": "Renamed for the publish",
                "expectedVersion": item["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert renamed.status_code == 200, renamed.text
        version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
        step = "publish"
        published = client.post(
            f"/api/v1/change-sets/{change_set['id']}/publication",
            json={
                "expectedChangeSetVersion": version,
                "expectedActivePublicationId": dataset.publication_id,
            },
        )
        assert published.status_code == 200, published.text
    finally:
        event.remove(engine, "before_cursor_execute", on_execute)
    return largest


def test_capturing_and_publishing_a_whole_workspace_bind_no_parameter_per_record(tmp_path):
    """0.9 T1 regression: capturing current live and publishing read the whole workspace's values and
    relations with a list of every record's ID, one parameter each; at 258,000 records PostgreSQL
    refused the statement (over 65,535 parameters) and both answered 500. No statement may bind more
    parameters when the workspace holds four times the records."""
    largest = {}
    # The two smallest seeded sizes, four times apart: capture and publish read the whole workspace.
    for label, shape in (("small", scaled_shape(0.005)), ("large", scaled_shape(0.02))):
        (tmp_path / label).mkdir()
        with volume_app(tmp_path / label, shape) as (client, dataset):
            largest[label] = _largest_parameter_list(client, get_engine(), dataset)
    assert largest["small"] == largest["large"]


def test_fixture_matches_its_shape_and_is_reproducible(tmp_path, baselines):
    # Identical shape and seed give identical data, public IDs included: seeding again into a new
    # database gives the seeded database's identifiers.
    assert seed_fresh(tmp_path, SMALL) == baselines["small-dataset"]
    with volume_app(tmp_path, SMALL) as (client, dataset):
        engine = get_engine()
        with engine.connect() as connection:

            def count(statement) -> int:
                return connection.scalar(select(func.count()).select_from(statement.subquery()))

            children = select(RdmObject.object_type_key).where(
                RdmObject.parent_object_id == dataset.heavy_group_id
            )
            assert count(children.where(RdmObject.object_type_key == ITEM)) == SMALL.heavy_items
            assert set(connection.scalars(children.distinct())) == {ITEM, NODE}
            assert count(select(RdmObject).where(RdmObject.object_type_key == GROUP)) == SMALL.groups
            assert count(select(RdmObject).where(RdmObject.object_type_key == ITEM)) == SMALL.items
            assert (
                count(
                    select(ObjectRelation).where(
                        ObjectRelation.to_object_id == dataset.cited_group_id,
                        ObjectRelation.relation_type_key == ITEM_CITES_GROUP,
                    )
                )
                == SMALL.citations
            )
            # Publication 1 holds the live membership and the matrix cells deleted live since.
            live = set(
                connection.execute(
                    select(RdmObject.id, RdmObject.name, RdmObject.parent_object_id)
                )
            )
            publication = set(
                connection.execute(
                    select(
                        PublicationObject.object_id,
                        PublicationObject.name,
                        PublicationObject.parent_object_id,
                    ).where(PublicationObject.publication_id == dataset.publication_id)
                )
            )
            retired = publication - live
            assert live < publication and len(retired) == dataset.counts["matrixRetiredCells"] > 0
            assert all(name.startswith("Cell ") for _, name, _ in retired)
            assert count(select(PublicationRelation)) > count(select(ObjectRelation))
            assert (
                count(select(RdmObject).where(RdmObject.object_type_key == CELL))
                + dataset.counts["matrixRetiredCells"]
                == dataset.counts["matrixCells"]
                >= (SMALL.groups - 3) * CELLS_PER_GROUP
            )

        # The deep node's ancestor path is its group plus every hierarchy level.
        deep = client.get(
            f"/api/v1/objects/{NODE}/{dataset.deep_node_id}", params={"workspaceKey": WORKSPACE}
        )
        assert deep.status_code == 200, deep.text
        assert len(deep.json()["path"]) == SMALL.node_depth + 1 >= 7

        # The change set is a valid graph, so the app accepts the bulk rows as its own.
        validation = client.post(f"/api/v1/change-sets/{dataset.change_set_id}/validation")
        assert validation.json() == {"valid": True, "diagnostics": []}
        edited = client.get(
            f"/api/v1/objects/{ITEM}",
            params={"changeSetId": dataset.change_set_id, "search": "(edited)", "pageSize": 500},
        )
        assert edited.status_code == 200, edited.text
        assert len(edited.json()["items"]) == dataset.counts["changeSetEdited"]
        assert dataset.counts["changeSetDeleted"] > 0 and dataset.counts["changeSetNew"] > 0


def test_volume_model_uses_no_starter_key():
    starter = json.loads(
        (Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text()
    )

    def keys(model) -> set[str]:
        sections = ("attributeTypes", "objectTypes", "relationTypes", "applications")
        return {item["key"] for section in sections for item in model[section]}

    assert not keys(volume_model()) & keys(starter)
