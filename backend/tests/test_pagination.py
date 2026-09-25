"""Behavior of the shared keyset paginator, including the cases each endpoint depends on."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.errors import ApiError
from app.models.database import ModelDraft
from app.services.cursors import encode_cursor
from app.services.pagination import (
    FIRST_PAGE,
    PageRequest,
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
        _keyset_predicate(
            _DRAFT_KEYS, [datetime(2026, 9, 5, tzinfo=UTC), "abc"], backward=False, inclusive=False
        )
    )
    assert "model_drafts.updated_at < " in predicate
    assert "model_drafts.public_id > " in predicate
    assert _DRAFT_KEYS[-1].column is ModelDraft.public_id, "the last key must be unique"


def test_paginate_sequence_walks_every_item_exactly_once():
    items = [{"key": f"item-{index:02d}"} for index in range(7)]
    seen = []
    cursor = None
    while True:
        page = paginate_sequence(
            items,
            lambda item: (item["key"],),
            scope="test",
            page=PageRequest(cursor=cursor),
            page_size=2,
        )
        cursor = page.next_cursor
        seen.extend(item["key"] for item in page.items)
        if cursor is None:
            break
    assert seen == sorted(item["key"] for item in items)


def test_paginate_sequence_rejects_a_cursor_from_another_scope():
    items = [{"key": "a"}, {"key": "b"}]
    cursor = paginate_sequence(
        items, lambda item: (item["key"],), scope="one", page_size=1
    ).next_cursor
    with pytest.raises(ApiError) as excinfo:
        paginate_sequence(
            items,
            lambda item: (item["key"],),
            scope="two",
            page=PageRequest(cursor=cursor),
            page_size=1,
        )
    assert excinfo.value.code == "invalid_cursor"


def test_paginate_sequence_rejects_a_cursor_from_different_filters():
    items = [{"key": "a"}, {"key": "b"}]
    cursor = paginate_sequence(
        items,
        lambda item: (item["key"],),
        scope="one",
        filters={"state": ["active"]},
        page_size=1,
    ).next_cursor
    with pytest.raises(ApiError) as excinfo:
        paginate_sequence(
            items,
            lambda item: (item["key"],),
            scope="one",
            filters={"state": ["retired"]},
            page=PageRequest(cursor=cursor),
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
            page=PageRequest(cursor="not-a-cursor"),
            page_size=1,
            message="Metadata cursor is invalid",
        )
    assert excinfo.value.code == "invalid_cursor"
    assert excinfo.value.message == "Metadata cursor is invalid"


def test_statement_paginator_accepts_the_historical_draft_cursor_identity(
    migrated_database, monkeypatch
):
    # Owns a migrated database so the result does not depend on an earlier test's bootstrap.
    monkeypatch.setenv("DATABASE_URL", migrated_database())
    reload_settings()
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
            page=PageRequest(cursor=legacy_cursor),
            page_size=1,
            cursor_sort_tokens=("updatedAt", "publicId"),
            message="Metadata cursor is invalid",
        )
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()


def test_paginate_statement_requires_at_least_one_key():
    with SessionLocal() as session, pytest.raises(ValueError, match="at least one sort key"):
        paginate_statement(
            session,
            select(ModelDraft),
            keys=(),
            scope="model-drafts",
            filters={},
            page=FIRST_PAGE,
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


_ITEMS = [{"key": f"item-{index:02d}"} for index in range(7)]


def _sequence_page(page: PageRequest, *, descending: bool = False):
    return paginate_sequence(
        _ITEMS,
        lambda item: (item["key"],),
        scope="test",
        page=page,
        page_size=3,
        descending=descending,
    )


def _keys(page) -> list[str]:
    return [item["key"] for item in page.items]


@pytest.mark.parametrize("descending", [False, True])
def test_sequence_pages_backward_from_the_end_to_the_start(descending):
    expected = sorted((item["key"] for item in _ITEMS), reverse=descending)
    last = _sequence_page(PageRequest(from_end=True, include_total=True), descending=descending)
    assert _keys(last) == expected[4:]
    assert (last.next_cursor, last.total_count, last.start_index) == (None, 7, 4)
    seen = _keys(last)
    page = last
    while page.prev_cursor is not None:
        page = _sequence_page(PageRequest(cursor=page.prev_cursor), descending=descending)
        seen = _keys(page) + seen
    assert seen == expected
    # Walking back from the end, the first page holds the remainder, in list order.
    assert _keys(page) == expected[:1]
    assert page.prev_cursor is None and page.next_cursor is not None


def test_sequence_anchor_reopens_the_same_page():
    middle = _sequence_page(PageRequest(position=2))
    assert _keys(middle) == ["item-02", "item-03", "item-04"]
    assert _keys(_sequence_page(PageRequest(cursor=middle.anchor))) == _keys(middle)
    assert middle.prev_cursor is not None and middle.next_cursor is not None


def test_sequence_position_past_the_end_continues_backward_from_the_last_row():
    page = _sequence_page(PageRequest(position=20, include_total=True))
    assert page.items == [] and page.next_cursor is None and page.anchor is None
    assert (page.total_count, page.start_index) == (7, 7)
    assert _keys(_sequence_page(PageRequest(cursor=page.prev_cursor))) == [
        "item-04",
        "item-05",
        "item-06",
    ]


def test_sequence_refuses_seek():
    with pytest.raises(ApiError) as excinfo:
        _sequence_page(PageRequest(seek="item-03"))
    assert excinfo.value.code == "invalid_seek"


@pytest.mark.parametrize(
    "arguments",
    [
        {"cursor": "x", "position": 1},
        {"cursor": "x", "from_end": True},
        {"seek": "a", "position": 0},
        {"seek": "a", "from_end": True},
    ],
)
def test_a_page_is_selected_one_way_only(arguments):
    with pytest.raises(ApiError) as excinfo:
        PageRequest(**arguments)
    assert excinfo.value.code == "conflicting_page_parameters"
    assert len(excinfo.value.details["parameters"]) == 2


def test_a_cursor_issued_before_directions_still_continues_forward():
    legacy = encode_cursor(("item-02",), scope="test", sort=("key",), filters={})
    assert _keys(_sequence_page(PageRequest(cursor=legacy))) == ["item-03", "item-04", "item-05"]
