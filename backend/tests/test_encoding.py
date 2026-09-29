"""The engine's JSON encoding gives what FastAPI's ``jsonable_encoder`` gave for stored data."""

from collections import deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import PurePosixPath
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.common.encoding import to_jsonable
from app.models.commands import AttributeInput, ObjectCreate


class Colour(Enum):
    RED = "red"


class Aliased(BaseModel):
    inner_name: str = Field(alias="innerName")
    when: datetime


@dataclass
class Point:
    x: Decimal
    at: date


class Plain:
    def __init__(self) -> None:
        self.name = "plain"
        self._sa_instance_state = object()


VALUES = [
    None,
    True,
    3,
    2.5,
    "text",
    Decimal(1),
    Decimal("1.50"),
    Decimal("1E+2"),
    date(2026, 9, 29),
    datetime(2026, 9, 29, 12, 30, tzinfo=UTC),
    datetime(2026, 9, 29, 12, 30),  # noqa: DTZ001 - naive values are encoded as they are
    time(8, 15),
    timedelta(minutes=3),
    UUID("12345678-1234-5678-1234-567812345678"),
    Colour.RED,
    PurePosixPath("/a/b"),
    b"bytes",
    {"k": [1, (2, 3)], 4: {"nested": {Decimal("2.0")}}, "_sa_hidden": 1},
    deque([1, 2]),
    frozenset({"only"}),
    Aliased(innerName="x", when=datetime(2026, 1, 1, tzinfo=UTC)),
    Point(Decimal("0.1"), date(2026, 1, 2)),
    Plain(),
    ObjectCreate(
        applicationKey="app",
        objectTypeKey="type",
        name="Name",
        attributes=[AttributeInput(attributeTypeKey="code", value=Decimal(10))],
    ),
]


def test_matches_fastapi_encoder():
    for value in VALUES:
        assert to_jsonable(value) == jsonable_encoder(value), value
        assert repr(to_jsonable(value)) == repr(jsonable_encoder(value)), value
