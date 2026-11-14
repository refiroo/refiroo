"""Rows written into a table by one ``COPY … FROM STDIN``, in chunks the caller flushes."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session


class CopyRows:
    """Rows for one table, collected with :meth:`add` and written by :meth:`flush`.

    A dict or list is written as compact JSON text (``ensure_ascii=False``); every other value is
    passed to the driver as it is. ``after_flush`` runs after a flush that wrote rows (a caller's
    cancel and lease check)."""

    def __init__(
        self,
        session: Session,
        table_name: str,
        columns: tuple[str, ...],
        *,
        after_flush: Callable[[], None] | None = None,
    ) -> None:
        self.session = session
        self.statement = f"COPY {table_name} ({', '.join(columns)}) FROM STDIN"
        self.after_flush = after_flush
        self.rows: list[tuple[Any, ...]] = []

    def __len__(self) -> int:
        return len(self.rows)

    def add(self, *values: Any) -> None:
        self.rows.append(tuple(_copy_value(value) for value in values))

    def flush(self) -> None:
        if not self.rows:
            return
        connection = self.session.connection().connection.driver_connection
        with connection.cursor() as cursor, cursor.copy(self.statement) as copy:
            for row in self.rows:
                copy.write_row(row)
        self.rows = []
        if self.after_flush is not None:
            self.after_flush()


def _copy_value(value: Any) -> Any:
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value
