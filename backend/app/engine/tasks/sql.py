"""The statements a task's reading shares: the file's keys, a type's stored records and their key
(Product 0.16 AP6a).

A table of the file is a rectangle of a sheet (``place``: sheet, header row, last row and the row
of its note, which is no record: a note under a header, D119, or a second header row, D144). A key
is the text of the key column in a row, found among the stored records of a type by an attribute's
value, by name or by public ID.
"""

from typing import Any

# The last row of a table that has no list bound.
LAST_ROW = 2**31 - 1
# The key of a source keyed by a column of public IDs.
BY_ID = "@id"


def stored_query(attribute: str | None) -> str:
    """The stored records of the type in the workspace with their key and their parent, as a
    subquery: the value of ``attribute``, their public ID (:data:`BY_ID`) or their name."""
    if attribute is None:
        return (
            "SELECT o.id, o.name, o.name AS key, o.parent_object_id AS parent_id FROM objects o"
            " WHERE o.workspace_key = :workspace AND o.object_type_key = :type"
        )
    if attribute == BY_ID:
        return (
            "SELECT o.id, o.name, o.id AS key, o.parent_object_id AS parent_id FROM objects o"
            " WHERE o.workspace_key = :workspace AND o.object_type_key = :type"
        )
    return (
        "SELECT o.id, o.name, a.text_value AS key, o.parent_object_id AS parent_id FROM objects o"
        " JOIN attribute_values a ON a.object_id = o.id AND a.attribute_type_key = :attribute"
        " WHERE o.workspace_key = :workspace AND o.object_type_key = :type"
        " AND a.text_value IS NOT NULL"
    )


FILE_KEYS = """
SELECT k.text AS key, (array_agg(n.text ORDER BY k.row_number))[1] AS name
FROM source_file_cells k
LEFT JOIN source_file_cells n ON n.source_file_id = k.source_file_id
    AND n.sheet_index = k.sheet_index AND n.row_number = k.row_number
    AND n.column_number = CAST(:name_column AS integer)
WHERE k.source_file_id = :file AND k.sheet_index = :sheet AND k.column_number = :key_column
  AND k.row_number > :header AND k.row_number <= :last AND k.row_number <> :note
  AND btrim(k.text) <> ''
GROUP BY k.text
"""


def parameters_of(
    place: dict[str, Any],
    file_id: int,
    workspace: str,
    type_key: str,
    key_column: int,
    key: dict[str, Any],
    name_column: int | None,
) -> dict[str, Any]:
    return {
        "file": file_id,
        "sheet": place["sheetIndex"],
        "header": place["headerRow"],
        "last": place["lastRow"] or LAST_ROW,
        "note": place.get("note") or 0,
        "workspace": workspace,
        "type": type_key,
        "attribute": attribute_of(key),
        "key_column": key_column,
        "name_column": name_column,
    }


def attribute_of(key: dict[str, Any]) -> str | None:
    """The ``attribute`` parameter of a key: its attribute, :data:`BY_ID` for a column of IDs,
    ``None`` for names."""
    if "attributeTypeKey" in key:
        return key["attributeTypeKey"]
    return BY_ID if "column" in key else None
