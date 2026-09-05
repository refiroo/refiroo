"""Behavior of the shared keyset paginator, including the cases each endpoint depends on."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.errors import ApiError
from app.models.database import ModelDraft
from app.services.cursors import encode_cursor
from app.services.pagination import (
    _keyset_predicate,
    cursor_sort,
    datetime_key,
    integer_key,
    paginate_sequence,
    paginate_statement,
    text_key,
)

_DRAFT_KEYS = (
    datetime_key("updatedAt", ModelDraft.updated_at, "updated_at", descending=True),
    text_key("publicId", ModelDraft.public_id, "public_id"),
)


def test_cursor_sort_encodes_direction():
    assert cursor_sort(_DRAFT_KEYS) == ("-updatedAt", "publicId")
    assert cursor_sort(
        (integer_key("sequenceId", ModelDraft.id, "id"),)
    ) == ("sequenceId",)


def test_keyset_predicate_follows_each_key_direction():
    """Mixed directions are valid: every key compares in the direction it is ordered by.

    The drafts keyset descends on updatedAt and ascends on publicId, so the predicate must be
    ``updated_at < v0 OR (updated_at = v0 AND public_id > v1)``. Comparing a key against its
    sibling's direction is what would skip or repeat rows across a page boundary.
    """
    predicate = str(
        _keyset_predicate(_DRAFT_KEYS, [datetime(2026, 9, 5, tzinfo=UTC), "abc"])
    )
    assert "model_drafts.updated_at < " in predicate
    assert "model_drafts.public_id > " in predicate
    assert _DRAFT_KEYS[-1].column is ModelDraft.public_id, "the last key must be unique"


def test_paginate_sequence_walks_every_item_exactly_once():
    items = [{"key": f"item-{index:02d}"} for index in range(7)]
    seen = []
    cursor = None
    while True:
        page, cursor = paginate_sequence(
            items,
            lambda item: (item["key"],),
            scope="test",
            cursor=cursor,
            page_size=2,
        )
        seen.extend(item["key"] for item in page)
        if cursor is None:
            break
    assert seen == sorted(item["key"] for item in items)


def test_paginate_sequence_rejects_a_cursor_from_another_scope():
    items = [{"key": "a"}, {"key": "b"}]
    _page, cursor = paginate_sequence(
        items, lambda item: (item["key"],), scope="one", cursor=None, page_size=1
    )
    with pytest.raises(ApiError) as excinfo:
        paginate_sequence(
            items, lambda item: (item["key"],), scope="two", cursor=cursor, page_size=1
        )
    assert excinfo.value.code == "invalid_cursor"


def test_paginate_sequence_rejects_a_cursor_from_different_filters():
    items = [{"key": "a"}, {"key": "b"}]
    _page, cursor = paginate_sequence(
        items,
        lambda item: (item["key"],),
        scope="one",
        filters={"state": ["active"]},
        cursor=None,
        page_size=1,
    )
    with pytest.raises(ApiError) as excinfo:
        paginate_sequence(
            items,
            lambda item: (item["key"],),
            scope="one",
            filters={"state": ["retired"]},
            cursor=cursor,
            page_size=1,
        )
    assert excinfo.value.code == "invalid_cursor"


def test_paginate_statement_rejects_an_unparseable_cursor_before_querying():
    with SessionLocal() as session, pytest.raises(ApiError) as excinfo:
        paginate_statement(
            session,
            select(ModelDraft),
            keys=_DRAFT_KEYS,
            scope="model-drafts",
            filters={},
            cursor="not-a-cursor",
            page_size=1,
            message="Metadata cursor is invalid",
        )
    assert excinfo.value.code == "invalid_cursor"
    assert excinfo.value.message == "Metadata cursor is invalid"


def test_statement_paginator_accepts_the_historical_draft_cursor_identity():
    legacy_cursor = encode_cursor(
        (datetime(2026, 9, 5, tzinfo=UTC).isoformat(), "draft-id"),
        scope="model-drafts",
        sort=("updatedAt", "publicId"),
        filters={},
    )
    with SessionLocal() as session:
        paginate_statement(
            session,
            select(ModelDraft),
            keys=_DRAFT_KEYS,
            scope="model-drafts",
            filters={},
            cursor=legacy_cursor,
            page_size=1,
            cursor_sort_tokens=("updatedAt", "publicId"),
            message="Metadata cursor is invalid",
        )


def test_paginate_statement_requires_at_least_one_key():
    with SessionLocal() as session, pytest.raises(ValueError, match="at least one sort key"):
        paginate_statement(
            session,
            select(ModelDraft),
            keys=(),
            scope="model-drafts",
            filters={},
            cursor=None,
            page_size=1,
        )


def test_draft_paging_visits_every_row_when_timestamps_tie(monkeypatch):
    """Drafts sharing an updatedAt must page without loss or repetition."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    application = create_app()

    with TestClient(application) as client:
        model = client.get("/api/v1/model").json()
        created = []
        for index in range(4):
            response = client.post(
                "/api/v1/model-drafts",
                json={"name": f"Tied draft {index}", "model": model},
            )
            assert response.status_code == 201
            created.append(response.json()["id"])

        shared_timestamp = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)
        with SessionLocal() as session:
            for draft in session.scalars(
                select(ModelDraft).where(ModelDraft.public_id.in_(created))
            ):
                draft.updated_at = shared_timestamp
            session.commit()

        seen: list[str] = []
        cursor = None
        while True:
            params = {"pageSize": 1}
            if cursor:
                params["cursor"] = cursor
            page = client.get("/api/v1/model-drafts", params=params)
            assert page.status_code == 200
            body = page.json()
            seen.extend(item["id"] for item in body["items"])
            cursor = body["nextCursor"]
            if cursor is None:
                break

        tied = [draft_id for draft_id in seen if draft_id in created]
        assert sorted(tied) == sorted(created), "every tied draft appears exactly once"
        assert len(seen) == len(set(seen)), "no draft is repeated across pages"
