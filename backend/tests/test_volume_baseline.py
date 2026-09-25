"""Base 0.8 S1: the volume fixture is faithful to real persistence, and read budgets hold.

The budgets are deterministic: the number of SQL statements a request executes must not change
when the dataset grows fourfold, and a request may materialise at most ``ROWS_PER_LISTED_ROW`` ORM
rows per row of a full page, at either scale. Row counts vary by a few with page content (records
on one page can share a parent), so they are bounded rather than compared. Wall-time figures at full volume come from
``volume_baseline.py`` and are recorded in docs/BASE_0_8_IMPLEMENTATION_PLAN.md.

Live reads meet the budgets, and since S2 so do draft and history reads, which answer in SQL. Draft
writes still load the whole membership (D7), so their budget test is a strict expected failure
until the scoped follow-up slice lands.
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from volume_baseline import PAGE_SIZE, run_scenarios
from volume_fixture import (
    GROUP,
    ITEM,
    ITEM_CITES_GROUP,
    NODE,
    WORKSPACE,
    scaled_shape,
    volume_app,
    volume_model,
)

from app.db import get_engine
from app.models.database import (
    ObjectRelation,
    RdmObject,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)

SMALL, LARGE = scaled_shape(0.01), scaled_shape(0.04)
ROWS_PER_LISTED_ROW = 6


@pytest.fixture(scope="module")
def baselines(_migrated_template, tmp_path_factory) -> dict[str, object]:
    """The scenario measurements at the small and the four-times-larger scale."""
    results = {}
    for label, shape in (("small", SMALL), ("large", LARGE)):
        directory = tmp_path_factory.mktemp(f"volume-{label}")
        with volume_app(_migrated_template, directory, shape) as (client, dataset):
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
        if worst > ROWS_PER_LISTED_ROW * PAGE_SIZE:
            failures.append(
                f"{label}: rows {small.rows_loaded:,} → {large.rows_loaded:,} at 4× data, "
                f"over {ROWS_PER_LISTED_ROW * PAGE_SIZE} for a {PAGE_SIZE}-row page"
            )
    return failures


def test_live_reads_and_writes_do_not_grow_with_the_dataset(baselines):
    assert not _over_budget(baselines, {"live"})
    assert not _over_budget(baselines, {"live"}, writes=True)


def test_draft_and_history_reads_hold_the_live_budget(baselines):
    assert not _over_budget(baselines, {"draft", "history"})


@pytest.mark.xfail(
    strict=True, reason="D7: draft writes load the whole membership; S2 scopes a follow-up"
)
def test_draft_writes_hold_the_live_budget(baselines):
    assert not _over_budget(baselines, {"draft"}, writes=True)


def test_fixture_matches_its_shape_and_is_reproducible(_migrated_template, tmp_path, baselines):
    with volume_app(_migrated_template, tmp_path, SMALL) as (client, dataset):
        # Identical shape and seed give identical data, public IDs included.
        assert dataset == baselines["small-dataset"]
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
            # Revision 1 holds exactly the live membership.
            live = set(
                connection.execute(
                    select(RdmObject.id, RdmObject.name, RdmObject.parent_object_id)
                )
            )
            revision = set(
                connection.execute(
                    select(
                        WorkspaceRevisionObject.object_id,
                        WorkspaceRevisionObject.name,
                        WorkspaceRevisionObject.parent_object_id,
                    ).where(WorkspaceRevisionObject.revision_id == dataset.revision_id)
                )
            )
            assert live == revision
            assert count(select(WorkspaceRevisionRelation)) == count(select(ObjectRelation))

        # The deep node's ancestor path is its group plus every hierarchy level.
        deep = client.get(
            f"/api/v1/objects/{NODE}/{dataset.deep_node_id}", params={"workspaceKey": WORKSPACE}
        )
        assert deep.status_code == 200, deep.text
        assert len(deep.json()["path"]) == SMALL.node_depth + 1 >= 7

        # The draft is a valid graph, so the app accepts the bulk rows as its own.
        validation = client.post(f"/api/v1/workspace-drafts/{dataset.draft_id}/validation")
        assert validation.json() == {"valid": True, "diagnostics": []}
        edited = client.get(
            f"/api/v1/objects/{ITEM}",
            params={"workspaceDraftId": dataset.draft_id, "search": "(edited)", "pageSize": 500},
        )
        assert edited.status_code == 200, edited.text
        assert len(edited.json()["items"]) == dataset.counts["draftEdited"]
        assert dataset.counts["draftDeleted"] > 0 and dataset.counts["draftNew"] > 0


def test_volume_model_uses_no_starter_key():
    starter = json.loads(
        (Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text()
    )

    def keys(model) -> set[str]:
        sections = ("attributeTypes", "objectTypes", "relationTypes", "applications")
        return {item["key"] for section in sections for item in model[section]}

    assert not keys(volume_model()) & keys(starter)
