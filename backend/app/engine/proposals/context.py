"""The context builder (AP-D3): the only code that reads data for a provider.

``AI_SEND_LEVEL`` is the ceiling: ``structure`` sends keys, labels, headers, attribute names and
types and no value; ``samples`` adds values, at most ``AI_SAMPLE_VALUES`` per column (or rows per
sheet) whatever a feature asks for; ``values`` sends the values a feature asks for, as many as it
needs (0.16 AP-D14: an agent reads as much of a file as its task needs). A value is read only when
the level allows it, so nothing above the level is even loaded. A feature that needs more than the ceiling is not
offered (``FEATURE_LEVELS``).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...config import SEND_LEVELS, SendLevel
from ...models.database import SourceFile
from .provider import Purpose

# The least each purpose needs to be useful. The inference's names work from headers alone, and
# are better with rows.
FEATURE_LEVELS: dict[Purpose, SendLevel] = {
    "connectionTest": "structure",
    "modelNames": "structure",
    # Record names are values (AP2-D3).
    "mappingTarget": "values",
}


@dataclass(frozen=True)
class Policy:
    level: SendLevel
    samples: int

    def allows(self, needed: SendLevel) -> bool:
        return SEND_LEVELS.index(needed) <= SEND_LEVELS.index(self.level)

    def offers(self, purpose: Purpose) -> bool:
        return self.allows(FEATURE_LEVELS[purpose])

    def values(self, wanted: int) -> int:
        """How many of the ``wanted`` values (or rows) may be sent: none at ``structure``, at most
        ``AI_SAMPLE_VALUES`` at ``samples``, all of them at ``values``."""
        if not self.allows("samples"):
            return 0
        return wanted if self.allows("values") else min(wanted, self.samples)


def sheet(
    policy: Policy,
    name: str,
    headers: list[str],
    read_rows: Callable[[int], list[list[str | None]]],
    wanted: int,
) -> dict[str, Any]:
    """A sheet as a provider sees it: its name and headers, and the first of the ``wanted`` rows
    the level allows (``read_rows`` is called only when it allows any)."""
    shown: dict[str, Any] = {"name": name, "headers": list(headers)}
    allowed = policy.values(wanted)
    if allowed:
        shown["rows"] = [list(row) for row in read_rows(allowed)[:allowed]]
    return shown


def workbook_sheets(
    session: Session, policy: Policy, source: SourceFile, tables: list[Any], wanted: int
) -> list[dict[str, Any]]:
    """The profiled tables of a staged workbook (``inference.facts`` tables: index, name, header
    row, columns) as sheets, their rows read from the staged cells only at ``samples`` and up."""
    sheets = []
    for table in tables:
        numbers = [column.number for column in table.columns]

        def read_rows(
            limit: int, table: Any = table, numbers: list[int] = numbers
        ) -> list[list[str | None]]:
            found = session.execute(
                text(
                    """
                    SELECT row_number, column_number, text FROM source_file_cells
                    WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
                      AND row_number <= :header + :rows
                    ORDER BY row_number, column_number
                    """
                ),
                {
                    "file": source.id,
                    "sheet": table.index,
                    "header": table.header_row,
                    "rows": limit,
                },
            )
            by_row: dict[int, dict[int, str]] = {}
            for row_number, column_number, value in found:
                by_row.setdefault(row_number, {})[column_number] = value
            return [[cells.get(n) for n in numbers] for _, cells in sorted(by_row.items())]

        sheets.append(
            sheet(
                policy, table.name, [column.header for column in table.columns], read_rows, wanted
            )
        )
    return sheets
