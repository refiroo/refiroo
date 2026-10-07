"""``engine/indexes/unique_values.py`` and the table PostgreSQL keeps for it (0.9 J2a, D75–D78).

J03.8, J06.4, J08.10 and J11.1 walk uniqueness through the API, where the write rules refuse a
duplicate before it is written. Here the backing itself: a duplicate written through the write
unit past the rules is refused at the end of the write, naming its holder, and by the database at
commit; which values have a row; one key for equal values; and the rows following the release
that is active.
"""

import copy

import pytest
from scenario import W1
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.engine.indexes import unique_values
from app.engine.model.compiler import parse_model
from app.engine.model.registry import resolve_model_snapshot
from app.engine.model.releases import activate_model_release, install_model_release
from app.engine.records.objects import apply_object_create
from app.engine.records.writes import LiveWrites
from app.errors import ApiError
from app.models.commands import ObjectCreate
from app.models.database import AttributeValue, ModelRuntimeState, UniqueAttributeValue


def _records(world) -> list[str]:
    """Two new R records of W1, with the unique values ``UV-1`` and ``UV-2``."""
    made = []
    with SessionLocal() as session:
        model = resolve_model_snapshot(session).model
        for number in (1, 2):
            values = {**world.required_values("R"), world.key("R.u"): f"UV-{number}"}
            payload = ObjectCreate(
                applicationKey=world.app("R"),
                objectTypeKey=world.key("R"),
                name=f"Holder {number}",
                workspaceKey=W1,
                attributes=[{"attributeTypeKey": k, "value": v} for k, v in values.items()],
            )
            made.append(apply_object_create(session, model, payload).id)
        session.commit()
    return made


def _value(session, object_id: str, key: str):
    return session.scalar(
        select(AttributeValue.text_value).where(
            AttributeValue.object_id == object_id, AttributeValue.attribute_type_key == key
        )
    )


def _rows(session, key: str, object_id: str | None = None) -> int:
    statement = select(func.count()).where(UniqueAttributeValue.attribute_type_key == key)
    if object_id is not None:
        statement = statement.where(UniqueAttributeValue.object_id == object_id)
    return session.scalar(statement)


def test_a_duplicate_written_past_the_rules_is_refused_naming_its_holder(seeded):
    world, u = seeded, seeded.key("R.u")
    holder, other = _records(world)
    with SessionLocal() as session:
        model = resolve_model_snapshot(session).model
        LiveWrites(session, W1).save_values(model, other, {u: _value(session, holder, u)})
        with pytest.raises(ApiError) as refused:
            unique_values.check(session, model, [other])
        assert refused.value.code == "DUPLICATE_ATTRIBUTE_VALUE"
        assert refused.value.details == {"attributeTypeKey": u, "conflictingObjectId": holder}
        with pytest.raises(IntegrityError) as error:
            session.commit()
        assert error.value.orig.diag.constraint_name == unique_values.CONSTRAINT


def test_which_values_have_a_row(seeded):
    """Empty text is no value (E-D4); a long text has a row; an attribute not unique has none."""
    world, u = seeded, seeded.key("R.u")
    first, second = _records(world)
    with SessionLocal() as session:
        model = resolve_model_snapshot(session).model
        writes = LiveWrites(session, W1)
        writes.save_values(model, first, {u: ""})
        writes.save_values(model, second, {u: ""})
        unique_values.check(session, model, [first, second])
        session.commit()
        assert _rows(session, u, first) == _rows(session, u, second) == 0
        writes.save_values(model, first, {u: "x" * 10_000})
        unique_values.check(session, model, [first])
        session.commit()
        assert _rows(session, u, first) == 1
        assert _rows(session, world.key("R.n")) == 0


@pytest.mark.parametrize(
    ("value_type", "column", "one", "other", "equal"),
    [
        ("decimal", "decimal_value", "1.0", "1.00", True),
        ("decimal", "decimal_value", "1.0", "1.01", False),
        (
            "dateTime",
            "datetime_value",
            "2024-02-29T12:00:00+00:00",
            "2024-02-29T14:00:00+02:00",
            True,
        ),
        ("date", "date_value", "2024-02-29", "2024-03-01", False),
        ("integer", "integer_value", "7", "7", True),
        ("boolean", "boolean_value", "true", "false", False),
        ("text", "text_value", "Code", "code", False),
        ("longText", "text_value", "a\nb", "a\nb", True),
    ],
)
def test_equal_values_have_one_key(seeded, value_type, column, one, other, equal):
    """The key compares as the write rule does: a decimal by its digits, an instant whatever its
    offset, text exactly."""
    types = {
        "text_value": "text",
        "integer_value": "integer",
        "decimal_value": "numeric",
        "boolean_value": "boolean",
        "date_value": "date",
        "datetime_value": "timestamptz",
    }

    def digest(session, value):
        arguments = ", ".join(
            f"CAST(:value AS {kind})" if name == column else f"NULL::{kind}"
            for name, kind in types.items()
        )
        return session.scalar(
            text(f"SELECT rdm_value_digest(:type, {arguments}, NULL::json)"),
            {"type": value_type, "value": value},
        )

    with SessionLocal() as session:
        first, second = digest(session, one), digest(session, other)
        assert first is not None and (first == second) is equal
        if value_type == "text":
            assert digest(session, "") is None


def test_the_rows_follow_the_active_release(seeded):
    """A release that drops ``unique`` releases the attribute's rows; activating the one that
    declares it again gives every stored value its row."""
    world, u = seeded, seeded.key("R.u")
    _records(world)
    with SessionLocal() as session:
        active = resolve_model_snapshot(session).release_id
    with SessionLocal() as session:
        held = session.scalar(
            select(func.count()).where(
                AttributeValue.attribute_type_key == u, AttributeValue.text_value != ""
            )
        )
        assert held and _rows(session, u) == held
        source = copy.deepcopy(world.configuration.model)
        attribute = next(a for a in source["attributeTypes"] if a["key"] == u)
        del attribute["features"]["unique"]
        source["release"]["version"] += "-not-unique"
        release, _ = install_model_release(session, parse_model(source))
        session.commit()

        def activate(release_id, active_id):
            state = session.get(ModelRuntimeState, 1)
            activate_model_release(
                session,
                release_id,
                expected_runtime_version=state.version,
                expected_active_release_id=active_id,
            )
            session.commit()

        activate(release.public_id, active)
        assert _rows(session, u) == 0
        activate(active, release.public_id)
        assert _rows(session, u) == held
