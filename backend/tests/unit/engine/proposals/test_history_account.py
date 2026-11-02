"""``engine/proposals/history_account.py``: the facts counted in the database, what the provider is
sent and the period (0.16 AO2, AO-D21 to AO-D25)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from scenario import W1

from app.db import SessionLocal
from app.engine.proposals import history_account as account
from app.engine.proposals import summaries
from app.models.database import AuditEvent

NOW = datetime(2030, 5, 6, 12, 0, tzinfo=UTC)
PERIOD = account.Period.of(NOW - timedelta(days=1), NOW + timedelta(days=1), "UTC")


def _entry(position: int, record: str, changes: dict, **more) -> AuditEvent:
    return AuditEvent(
        aggregate_type="object",
        aggregate_id=record,
        action="updated",
        version=2,
        changes=changes,
        subject={"objectTypeKey": "unit-type"},
        workspace_key=W1,
        feed_position=position,
        occurred_at=NOW,
        **more,
    )


def _planted(session):
    session.add_all(
        [
            # A single write names the attributes it changed by the keys of ``attributes`` and
            # carries their new values; a publication names ``attributeTypeKeys`` only.
            _entry(9_000_001, "r-1", {"attributes": {"unit-field": "a planted secret value"}}),
            _entry(
                9_000_002,
                "r-2",
                {"changedFields": ["attributes"], "attributeTypeKeys": ["unit-field"]},
            ),
            _entry(9_000_003, "r-2", {"attributes": {"unit-field": "again"}}),
            # Staged work stands beside the live entries and is not counted (AO-D21).
            AuditEvent(
                aggregate_type="change-set-object",
                aggregate_id="r-3",
                action="updated",
                version=2,
                changes={"attributes": {"unit-field": "staged"}, "changeSetId": "x"},
                subject={"objectTypeKey": "unit-type"},
                workspace_key=W1,
                occurred_at=NOW,
            ),
        ]
    )
    session.flush()


def _ours(facts, kind):
    return [f for f in facts if f.kind == kind and f.keys.get("objectTypeKey") == "unit-type"]


def test_both_shapes_of_an_entry_count_a_field_once_per_record_and_no_value_is_read(seeded):
    with SessionLocal() as session:
        _planted(session)
        facts = account.build_facts(session, account.Scope(W1), PERIOD)
        (field,) = _ours(facts, "fields")
        assert field.keys["attributeTypeKey"] == "unit-field" and field.count == 2
        (records,) = _ours(facts, "records")
        assert (records.keys["action"], records.count) == ("updated", 2)
        sent = json.dumps(
            summaries.context_of(facts, "en", account.KINDS, names=True), ensure_ascii=False
        )
        assert "planted secret value" not in sent and "staged" not in sent
        session.rollback()


def test_a_fact_keeps_its_id_between_two_runs(seeded):
    with SessionLocal() as session:
        _planted(session)
        first = account.build_facts(session, account.Scope(W1), PERIOD)
        second = account.build_facts(session, account.Scope(W1), PERIOD)
        assert [f.id for f in first] == [f.id for f in second] and first
        assert account.fact_id("fields", "a", "b") != account.fact_id("records", "a", "b")
        session.rollback()


def test_a_record_scope_counts_that_records_entries_only(seeded):
    with SessionLocal() as session:
        _planted(session)
        # An entry is read for a record through its subjects, as the record's history is.
        from app.models.database import AuditEventSubject

        for event in session.query(AuditEvent).filter(AuditEvent.aggregate_id == "r-2"):
            session.add(AuditEventSubject(audit_event_id=event.sequence_id, object_id="r-2"))
        session.flush()
        facts = account.build_facts(session, account.Scope(W1, "r-2"), PERIOD)
        (field,) = _ours(facts, "fields")
        assert field.count == 2
        session.rollback()


def test_names_go_in_the_context_only_when_asked_for():
    fact = summaries.Fact(
        "so-1",
        "source",
        "Import job, file.xlsx",
        None,
        3,
        plain="Import job",
        data={"file": "file.xlsx"},
    )
    quiet = summaries.context_of([fact], "en", account.KINDS)
    named = summaries.context_of([fact], "en", account.KINDS, names=True)
    assert quiet["facts"][0] == {"id": "so-1", "kind": "source", "text": "Import job", "count": 3}
    assert named["facts"][0]["data"] == {"file": "file.xlsx"}


@pytest.mark.parametrize(
    ("since", "until", "zone"),
    [
        (NOW, NOW, None),
        (NOW, NOW - timedelta(hours=1), None),
        (NOW - timedelta(hours=1), NOW, "Nowhere/Land"),
    ],
)
def test_an_empty_or_reversed_period_and_an_unknown_zone_are_refused(since, until, zone):
    with pytest.raises(account.PeriodInvalid):
        account.Period.of(since, until, zone)


def test_a_day_is_read_in_the_zone():
    period = account.Period.of(
        NOW - timedelta(days=1), NOW + timedelta(days=1), "Pacific/Kiritimati"
    )
    late = datetime(2030, 5, 6, 23, 30, tzinfo=UTC)
    assert period.day(late) == "Tuesday 7 May"
    assert account.Period.of(late - timedelta(days=1), late + timedelta(days=1), None).day(
        late
    ) == ("Monday 6 May")
