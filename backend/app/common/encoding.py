"""JSON-compatible values for stored JSON (audit changes, digests), without the web framework.

``to_jsonable`` gives what FastAPI's ``jsonable_encoder`` gives with its defaults for every type the
engine stores, so rows written before and after it are the same bytes
(``tests/test_encoding.py`` compares the two).
"""

import dataclasses
from collections import deque
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from types import GeneratorType
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def _decimal(value: Decimal) -> int | float:
    exponent = value.as_tuple().exponent
    return int(value) if isinstance(exponent, int) and exponent >= 0 else float(value)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return to_jsonable(value.model_dump(mode="json", by_alias=True))
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(dataclasses.asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PurePath):
        return str(value)
    if isinstance(value, (str, int, float, type(None))):
        return value
    if isinstance(value, dict):
        # SQLAlchemy instance state is never data.
        return {
            to_jsonable(key): to_jsonable(item)
            for key, item in value.items()
            if not (isinstance(key, str) and key.startswith("_sa"))
        }
    if isinstance(value, (list, set, frozenset, GeneratorType, tuple, deque)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Decimal):
        return _decimal(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode()
    try:
        data = dict(value)
    except (TypeError, ValueError):
        data = vars(value)
    return to_jsonable(data)
