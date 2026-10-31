"""The engine's match of a workbook with its workspace, before any AI call (Product 0.16 AP7).

Every column of every table the reading found is compared with what the workspace stores, in
PostgreSQL, row by row through the record its key finds: which column identifies the records (a
field whose stored values are unique for its type, the type with the most of the row's other
columns agreeing), where each other column belongs (an attribute, the parent, a relationship), what
differs from what is stored, the rows that are new, the placeholders and the values that contradict
each other. From that it drafts the import profile of what it could place, and it lists what it
could not: that, and the person's words, are all the AI is asked about. It knows no file, no sheet
and no name.
"""

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models.schema import EngineModel
from .catalog import Types, type_infos
from .reading import LAST_ROW

# Of a column's distinct values, the share a stored field must hold to identify or refer to records.
MATCH_SHARE = 0.9
# Of a column's rows, the share that must agree with a place for the column to belong there.
AGREE_SHARE = 0.4
# A column with this few distinct values agrees with any flag by chance: its header must say so too.
LOW_VARIETY = 3
PLACEHOLDER = re.compile(r"^(n/?a\b.*|none|null|-+|/)$", re.IGNORECASE)
NAME = "@name"
# Differences a question names; the rest are counted.
EXAMPLES = 3

_CELLS = text(
    """
CREATE TEMP TABLE match_cell ON COMMIT DROP AS
SELECT row_number AS r, column_number AS col, btrim(text) AS v, lower(btrim(text)) AS nv
FROM source_file_cells
WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
  AND row_number <= :last AND row_number <> :note AND column_number = ANY(:columns)
  AND btrim(text) <> ''
"""
)

_FACTS = text(
    """
CREATE TEMP TABLE match_fact ON COMMIT DROP AS
SELECT o.id AS oid, o.object_type_key AS t, '@name' AS f, lower(btrim(o.name)) AS nv,
    btrim(o.name) AS v, o.parent_object_id AS parent
FROM objects o WHERE o.workspace_key = :workspace
UNION ALL
SELECT o.id, o.object_type_key, a.attribute_type_key, lower(btrim(x.v)), btrim(x.v),
    o.parent_object_id
FROM attribute_values a JOIN objects o ON o.id = a.object_id
CROSS JOIN LATERAL (SELECT coalesce(a.text_value, a.integer_value::text, a.decimal_value::text,
    a.boolean_value::text, a.date_value::text) AS v) x
WHERE o.workspace_key = :workspace AND x.v IS NOT NULL
"""
)

# Fields whose stored values identify one record of their type.
_IDENTIFYING = text(
    """
CREATE TEMP TABLE match_identifying ON COMMIT DROP AS
SELECT t, f FROM match_fact GROUP BY t, f
HAVING count(*) = count(DISTINCT nv) AND count(*) >= 2
"""
)

_CANDIDATES = text(
    """
SELECT c.col, f.t, f.f, count(DISTINCT c.nv) AS hit
FROM (SELECT DISTINCT col, nv FROM match_cell) c
JOIN match_fact f ON f.nv = c.nv
JOIN match_identifying i ON i.t = f.t AND i.f = f.f
GROUP BY c.col, f.t, f.f
"""
)

_EVIDENCE = text(
    """
WITH hit AS (SELECT c.r, f.oid FROM match_cell c JOIN match_fact f
    ON f.nv = c.nv AND f.t = :t AND f.f = :f WHERE c.col = :col)
SELECT x.col, count(DISTINCT x.r) FROM hit
JOIN match_cell x ON x.r = hit.r AND x.col <> :col
JOIN match_fact g ON g.oid = hit.oid AND g.nv = x.nv
GROUP BY x.col
"""
)

_ROWS_OF_KEY = text(
    """
CREATE TEMP TABLE match_row ON COMMIT DROP AS
SELECT c.r, f.oid, f.parent, c.v AS key FROM match_cell c
JOIN match_fact f ON f.nv = c.nv AND f.t = :t AND f.f = :f WHERE c.col = :col
"""
)

_AS_FIELD = text(
    """
SELECT g.f, count(DISTINCT x.r) FROM match_row h
JOIN match_cell x ON x.r = h.r AND x.col = :col
JOIN match_fact g ON g.oid = h.oid AND g.nv = x.nv GROUP BY 1 ORDER BY 2 DESC
"""
)

_AS_PARENT = text(
    """
SELECT p.object_type_key, count(DISTINCT x.r) FROM match_row h
JOIN objects p ON p.id = h.parent
JOIN match_cell x ON x.r = h.r AND x.col = :col AND lower(btrim(p.name)) = x.nv
GROUP BY 1 ORDER BY 2 DESC LIMIT 1
"""
)

# A relationship either way whose other end holds the cell, in its name or a field.
_AS_RELATION = text(
    """
SELECT e.relation_type_key, e.from_object_id = h.oid AS outgoing, z.t, z.f, count(DISTINCT x.r)
FROM match_row h
JOIN object_relations e ON h.oid IN (e.from_object_id, e.to_object_id)
JOIN match_fact z ON z.oid = CASE WHEN e.from_object_id = h.oid THEN e.to_object_id
    ELSE e.from_object_id END
JOIN match_cell x ON x.r = h.r AND x.col = :col AND z.nv = x.nv
GROUP BY 1, 2, 3, 4 ORDER BY 5 DESC, z.f = '@name' DESC LIMIT 1
"""
)

_DIFFERS_FIELD = text(
    """
SELECT h.key, x.v, g.v FROM match_row h JOIN match_cell x ON x.r = h.r AND x.col = :col
LEFT JOIN match_fact g ON g.oid = h.oid AND g.f = :f
WHERE g.nv IS DISTINCT FROM x.nv ORDER BY 1
"""
)

_DIFFERS_PARENT = text(
    """
SELECT h.key, x.v, p.name FROM match_row h JOIN match_cell x ON x.r = h.r AND x.col = :col
LEFT JOIN objects p ON p.id = h.parent
WHERE lower(btrim(p.name)) IS DISTINCT FROM x.nv ORDER BY 1
"""
)

_DIFFERS_RELATION = text(
    """
SELECT h.key, x.v, (SELECT string_agg(DISTINCT z.v, ', ') FROM object_relations e
    JOIN match_fact z ON z.oid IN (e.from_object_id, e.to_object_id) AND z.f = :f
    WHERE h.oid IN (e.from_object_id, e.to_object_id) AND z.oid <> h.oid
      AND e.relation_type_key = :relation)
FROM match_row h JOIN match_cell x ON x.r = h.r AND x.col = :col
WHERE NOT EXISTS (
    SELECT 1 FROM object_relations e JOIN match_fact z ON z.oid IN (e.from_object_id, e.to_object_id)
    WHERE h.oid IN (e.from_object_id, e.to_object_id) AND z.oid <> h.oid
      AND e.relation_type_key = :relation AND z.nv = x.nv)
ORDER BY 1
"""
)

_STORED_ROWS = text(
    """
SELECT count(*) FROM match_row h JOIN match_fact g ON g.oid = h.oid AND g.f = :f
"""
)

_ON_PARENT = text(
    """
SELECT g.f, count(DISTINCT x.r) FROM match_row h
JOIN match_cell x ON x.r = h.r AND x.col = :col
JOIN match_fact g ON g.oid = h.parent AND g.nv = x.nv AND g.f <> '@name'
GROUP BY 1 ORDER BY 2 DESC LIMIT 1
"""
)

_BOTH_FILLED = text(
    """
SELECT count(*) FROM match_cell a JOIN match_cell b ON b.r = a.r AND b.col = :b WHERE a.col = :a
"""
)

_REFERS = text(
    """
SELECT f.t, f.f, count(DISTINCT c.nv) FROM (SELECT DISTINCT nv FROM match_cell WHERE col = :col) c
JOIN match_fact f ON f.nv = c.nv
JOIN match_identifying i ON i.t = f.t AND i.f = f.f
GROUP BY 1, 2 ORDER BY 3 DESC, f.f = '@name' DESC LIMIT 1
"""
)

_NOT_EXACT = text(
    """
SELECT DISTINCT x.v, f.v FROM match_cell x JOIN match_fact f
    ON f.nv = x.nv AND f.t = :t AND f.f = :f
WHERE x.col = :col AND x.v <> f.v
"""
)

_RAW_NOT_EXACT = text(
    """
SELECT DISTINCT c.text, f.v FROM source_file_cells c JOIN match_fact f
    ON f.nv = lower(btrim(c.text)) AND f.t = :t AND f.f = :f
WHERE c.source_file_id = :file AND c.sheet_index = :sheet AND c.column_number = :col
  AND c.row_number > :header AND c.text <> f.v
"""
)

_CONFLICTS = text(
    """
SELECT a.v, array_agg(DISTINCT b.v ORDER BY b.v) FROM match_cell a
JOIN match_cell b ON b.r = a.r AND b.col = :value
WHERE a.col = :key GROUP BY a.v HAVING count(DISTINCT b.nv) > 1 ORDER BY 1
"""
)

_PLACEHOLDERS = text(
    """
SELECT col, v, count(*) FROM match_cell
WHERE v ~* '^(n/?a\\y.*|none|null|-+|/)$' GROUP BY 1, 2
"""
)

_REPEATS = text(
    """
SELECT count(*) FROM (SELECT a.nv, b.nv FROM match_cell a JOIN match_cell b ON b.r = a.r
WHERE a.col = :owner AND b.col = :list GROUP BY 1, 2 HAVING count(*) > 1) d
"""
)

# Through the relationship the owner's record holds: which field of the other end each column fills
# and, per value of the list column, the parent those records stand under.
_RELATED_FIELD = text(
    """
SELECT e.relation_type_key, e.from_object_id = h.oid AS outgoing, z.t, z.f, count(DISTINCT x.r)
FROM match_row h
JOIN object_relations e ON h.oid IN (e.from_object_id, e.to_object_id)
JOIN match_fact z ON z.oid = CASE WHEN e.from_object_id = h.oid THEN e.to_object_id
    ELSE e.from_object_id END
JOIN match_cell x ON x.r = h.r AND x.col = :col AND z.nv = x.nv
WHERE z.f <> '@name'
GROUP BY 1, 2, 3, 4 ORDER BY 5 DESC LIMIT 1
"""
)

_LIST_PARENTS = text(
    """
SELECT DISTINCT ON (l.v) l.v, p.id, p.object_type_key, count(*) OVER (PARTITION BY l.v, p.id) AS n
FROM match_row h
JOIN match_cell l ON l.r = h.r AND l.col = :list
JOIN match_cell x ON x.r = h.r AND x.col = :col
JOIN object_relations e ON h.oid IN (e.from_object_id, e.to_object_id)
    AND e.relation_type_key = :relation
JOIN match_fact z ON z.oid = CASE WHEN e.from_object_id = h.oid THEN e.to_object_id
    ELSE e.from_object_id END AND z.f = :f AND z.nv = x.nv
JOIN objects p ON p.id = z.parent
ORDER BY l.v, n DESC
"""
)


def _words(value: Any) -> set[str]:
    return {w for w in re.split(r"[\s_\-/]+", str(value).lower()) if len(w) > 1}


def _header_names(header: str, key: str, label: str) -> bool:
    """Whether a header says the attribute: every word of its key or of its label is in it."""
    words = _words(header)
    return (bool(_words(key)) and _words(key) <= words) or (
        bool(_words(label)) and _words(label) <= words
    )


class _Table:
    def __init__(self, session: Session, table: dict[str, Any], file_id: int) -> None:
        self.session = session
        self.table = table
        self.file_id = file_id
        place = table.get("place") or {}
        self.place = place
        self.columns = {c["number"]: c for c in table["columns"] if c.get("header")}
        self.parameters = {
            "file": file_id,
            "sheet": place.get("sheetIndex"),
            "header": place.get("headerRow") or 1,
            "last": place.get("lastRow") or LAST_ROW,
            "note": place.get("note") or 0,
            "columns": list(self.columns),
        }

    def load(self) -> dict[int, tuple[int, int]]:
        """The table's cells as ``match_cell``; each column's filled and distinct counts."""
        self.session.execute(text("DROP TABLE IF EXISTS match_cell"))
        self.session.execute(text("DROP TABLE IF EXISTS match_row"))
        self.session.execute(_CELLS, self.parameters)
        self.session.execute(text("CREATE INDEX ON match_cell (col, nv)"))
        self.session.execute(text("CREATE INDEX ON match_cell (r)"))
        self.session.execute(text("ANALYZE match_cell"))
        return {
            col: (filled, distinct)
            for col, filled, distinct in self.session.execute(
                text("SELECT col, count(*), count(DISTINCT nv) FROM match_cell GROUP BY 1")
            )
        }


def _keys(
    session: Session, stats: dict[int, tuple[int, int]], types: Types
) -> list[dict[str, Any]]:
    """The fields that could identify a table's rows, best first: the most of a row's other columns
    agreeing with the record found, the larger share found, a value before a name."""
    found = []
    for col, type_key, field, hit in session.execute(_CANDIDATES):
        filled, distinct = stats[col]
        if type_key not in types or distinct < 2 or hit < MATCH_SHARE * distinct:
            continue
        agreeing = session.execute(_EVIDENCE, {"t": type_key, "f": field, "col": col}).all()
        found.append(
            {
                "col": col,
                "type": type_key,
                "field": field,
                "hit": hit,
                "distinct": distinct,
                "filled": filled,
                "unique": distinct == filled,
                "evidence": sum(1 for _, rows in agreeing if rows >= 0.5 * filled),
            }
        )
    found.sort(
        key=lambda k: (k["evidence"], k["hit"] / k["distinct"], k["field"] != NAME), reverse=True
    )
    return found


def _ambiguous(keys: list[dict[str, Any]], best: dict[str, Any]) -> list[dict[str, Any]]:
    """Other types the same evidence points at: the person says which it is."""
    return [
        k
        for k in keys
        if k is not best
        and k["unique"]
        and k["type"] != best["type"]
        and k["evidence"] == best["evidence"]
        and k["hit"] == best["hit"]
    ]


def _value_map(
    session: Session,
    match: _Table,
    col: int,
    type_key: str,
    field: str,
    maps: dict[str, dict[str, Any]],
    name: str,
) -> str | None:
    """A map from each cell's text to the stored text where they differ only by spaces or case; the
    import compares exactly."""
    found = {
        written: stored
        for written, stored in session.execute(
            _RAW_NOT_EXACT,
            {
                "file": match.file_id,
                "sheet": match.parameters["sheet"],
                "header": match.parameters["header"],
                "col": col,
                "t": type_key,
                "f": field,
            },
        )
    }
    if not found:
        return None
    maps[name] = found
    return name


def _match_by(field: str) -> dict[str, str]:
    return {"field": "name"} if field == NAME else {"attributeTypeKey": field}


def _question(words: str, options: list[str], assumed: str, kind: str) -> dict[str, Any]:
    return {"text": words[:500], "options": options, "assumed": assumed, "kind": kind}


def _examples(rows: list[Any]) -> str:
    shown = "; ".join(
        f"{key}: “{written}”" + (f", stored “{stored}”" if stored else "")
        for key, written, stored in rows[:EXAMPLES]
    )
    return shown + (f" and {len(rows) - EXAMPLES} more" if len(rows) > EXAMPLES else "")


FOLLOW, KEEP = "Follow the workbook", "Keep what is stored"
EMPTY, AS_WRITTEN = "Treat it as empty", "Load it as written"


def _about_ignored(question: dict[str, Any], sheet: str, bindings: list[dict[str, Any]]) -> bool:
    """A difference of a column another column of its relationship stands in for."""
    if question.get("kind") != "difference":
        return False
    return any(
        b.get("ignore") and f"in column “{b['column']}”" in question["text"]
        and f"of “{sheet}”" in question["text"]
        for b in bindings
    )


def _place_columns(
    session: Session,
    match: _Table,
    stats: dict[int, tuple[int, int]],
    key: dict[str, Any],
    types: Types,
    answers: dict[str, str],
    maps: dict[str, dict[str, Any]],
    questions: list[dict[str, Any]],
    placeholders: dict[int, list[tuple[str, int]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Each column's binding; the columns with no place; each place with what differs."""
    info = types[key["type"]]
    sheet = match.table["sheet"]
    writable = {k: (label, kind) for k, label, kind in info.writable}
    bindings: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []
    placed: list[dict[str, Any]] = []

    for col, (filled, distinct) in sorted(stats.items()):
        column = match.columns[col]
        header = column["header"]
        if col == key["col"]:
            continue
        by_field = session.execute(_AS_FIELD, {"col": col}).all()
        field, agree = next(((f, n) for f, n in by_field if f == NAME or f in writable), (None, 0))
        rows = session.scalar(text("SELECT count(*) FROM match_row")) or 1
        named = next(
            (k for k, (label, _) in writable.items() if _header_names(header, k, label)), None
        )
        if named is not None and named != field:
            # The model names this column and holds no values for it yet: nothing to agree with.
            stored = session.scalar(_STORED_ROWS, {"f": named}) or 0
            if stored < 0.5 * rows:
                field, agree = named, filled
        if distinct <= LOW_VARIETY and field not in (None, NAME) and agree < filled:
            # Yes and no agree with any flag by chance: the header must say it too.
            label = writable[field][0] if field in writable else field
            if not (_words(header) & (_words(field) | _words(label))):
                field, agree = None, 0
        parent = session.execute(_AS_PARENT, {"col": col}).first()
        on_parent = session.execute(_ON_PARENT, {"col": col}).first()
        if (
            agree < AGREE_SHARE * filled
            and on_parent is not None
            and on_parent[1] >= 0.9 * filled
            and (parent is None or parent[1] < AGREE_SHARE * filled)
        ):
            # A value of the parent repeated on its children's rows: it is stored there.
            placed.append({"column": header, "place": f"its parent's {on_parent[0]}", "agrees": on_parent[1], "differs": 0})
            bindings.append({"column": header, "ignore": True})
            continue
        # A flag's yes and no name no record: only a column with variety can be a link.
        relation = (
            session.execute(_AS_RELATION, {"col": col}).first() if distinct > LOW_VARIETY else None
        )
        if distinct <= LOW_VARIETY:
            parent = None
        # What the record itself holds wins when it agrees; else the better of its links.
        kind, agreeing = "field", agree
        if agree < MATCH_SHARE * filled:
            for option, count in (
                ("parent", parent[1] if parent is not None else 0),
                ("relation", relation[4] if relation is not None else 0),
            ):
                if count > agreeing:
                    kind, agreeing = option, count
        if agreeing < AGREE_SHARE * filled:
            row = session.execute(_REFERS, {"col": col}).first()
            unplaced.append(
                {
                    "sheet": sheet,
                    "column": header,
                    "letter": column.get("column"),
                    "filled": filled,
                    "distinct": distinct,
                    **(
                        {"refersTo": f"{row[0]}.{row[1]}"}
                        if row is not None and distinct >= 2 and row[2] >= MATCH_SHARE * distinct
                        else {}
                    ),
                }
            )
            continue
        binding: dict[str, Any] = {"column": header}
        differs: list[Any]
        place: str
        if kind == "parent":
            assert parent is not None
            binding["parent"] = {"objectTypeKey": parent[0], "matchBy": {"field": "name"}}
            differs = session.execute(_DIFFERS_PARENT, {"col": col}).all()
            place = "its parent"
        elif kind == "relation":
            assert relation is not None
            binding["relation"] = {
                "relationTypeKey": relation[0],
                "direction": "outgoing" if relation[1] else "incoming",
                "objectTypeKey": relation[2],
                "matchBy": _match_by(relation[3]),
                "replace": True,
            }
            differs = session.execute(
                _DIFFERS_RELATION, {"col": col, "relation": relation[0], "f": relation[3]}
            ).all()
            place = f"the relationship {relation[0]}"
        elif field == NAME:
            binding["field"] = "name"
            differs = session.execute(_DIFFERS_FIELD, {"col": col, "f": NAME}).all()
            place = "its name"
        else:
            binding["attributeTypeKey"] = field
            differs = session.execute(_DIFFERS_FIELD, {"col": col, "f": field}).all()
            place = f"its {writable[field][0] if field in writable else field}"

        written = placeholders.get(col) or []
        for value, rows in written:
            words = (
                f"Column “{header}” ({sheet}) holds “{value}” on {rows} rows. "
                "It looks like a placeholder, not a value."
            )
            choice = answers.get(words, EMPTY)
            questions.append(_question(words, [EMPTY, AS_WRITTEN], EMPTY, "placeholder"))
            if choice == EMPTY:
                name = f"{sheet}.{header}.empty"
                maps.setdefault(name, {})[value] = None
                binding["valueMap"] = name
        placeholder_values = {v.lower() for v, _ in written}
        differs = [
            d for d in differs if str(d[1]).lower() not in placeholder_values and d[2] is not None
        ]

        keep = False
        if differs:
            words = (
                f"{len(differs)} rows of “{sheet}” differ from {place} in column “{header}”: "
                f"{_examples(differs)}."
            )
            questions.append(_question(words, [FOLLOW, KEEP], FOLLOW, "difference"))
            keep = answers.get(words) == KEEP
        placed.append({"column": header, "place": place, "agrees": agreeing, "differs": len(differs)})
        if keep:
            bindings.append({"column": header, "ignore": True})
            continue
        # The import compares exactly: map what differs from the stored text only by spaces or case.
        target = None
        if "parent" in binding:
            target = (binding["parent"]["objectTypeKey"], NAME)
        elif "relation" in binding:
            match_by = binding["relation"]["matchBy"]
            target = (
                binding["relation"]["objectTypeKey"],
                NAME if "field" in match_by else match_by["attributeTypeKey"],
            )
        if target is not None and "valueMap" not in binding:
            name = _value_map(session, match, col, target[0], target[1], maps, f"{sheet}.{header}")
            if name is not None:
                binding["valueMap"] = name
        bindings.append(binding)
    # Two columns of one relationship (a code and its name): the one that agrees most binds it.
    agreeing_of = {p["column"]: p["agrees"] for p in placed}
    best: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        relation_key = (binding.get("relation") or {}).get("relationTypeKey")
        if relation_key is None:
            continue
        held = best.get(relation_key)
        if held is None:
            best[relation_key] = binding
            continue
        keep_new = agreeing_of[binding["column"]] > agreeing_of[held["column"]]
        loser = held if keep_new else binding
        if keep_new:
            best[relation_key] = binding
        name = loser["column"]
        loser.clear()
        loser.update({"column": name, "ignore": True})
    questions[:] = [q for q in questions if not _about_ignored(q, sheet, bindings)]
    return bindings, unplaced, placed


def _conflicts(
    session: Session,
    match: _Table,
    stats: dict[int, tuple[int, int]],
    key_col: int | None,
    questions: list[dict[str, Any]],
) -> None:
    """A column that names something, where one value has several in another column that names it
    too: the workbook contradicts itself."""
    sheet = match.table["sheet"]
    columns = [
        col
        for col, (filled, distinct) in stats.items()
        if col != key_col and 2 < distinct < 0.5 * max(filled, 1)
    ]
    for a in columns:
        for b in columns:
            if a == b or not 0.6 <= stats[b][1] / stats[a][1] <= 1.6:
                continue
            # Columns that name one thing are filled on the same rows.
            both = session.scalar(_BOTH_FILLED, {"a": a, "b": b}) or 0
            if both < 0.9 * max(stats[a][0], stats[b][0]):
                continue
            found = session.execute(_CONFLICTS, {"key": a, "value": b}).all()
            if not found or len(found) > max(2, stats[a][1] // 4) or any(
                len(v) > 2 for _, v in found
            ):
                continue
            header, other = match.columns[a]["header"], match.columns[b]["header"]
            shown = "; ".join(f"{k}: {' / '.join(v)}" for k, v in found[:EXAMPLES])
            questions.append(
                _question(
                    f"In “{sheet}”, one “{header}” has several “{other}”: {shown}. "
                    "Which is right? The stored records stay as they are until you say.",
                    ["Keep the stored records", "They are separate records"],
                    "Keep the stored records",
                    "conflict",
                )
            )


def _owner_rows(
    session: Session,
    match: _Table,
    stats: dict[int, tuple[int, int]],
    keys: list[dict[str, Any]],
    types: Types,
    maps: dict[str, dict[str, Any]],
    keyed: set[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """A table whose rows repeat a record per value of a list (a language, a period): the source
    writing the related records each column fills, with the columns it could not place."""
    sheet = match.table["sheet"]
    owners = [k for k in keys if k["field"] != NAME and not k["unique"] and k["distinct"] > 30]
    lists = [k for k in keys if k["distinct"] <= 30 and not k["unique"]]
    # The rows repeat records another sheet of the workbook is about, when there is one.
    owner = max(owners, key=lambda k: (k["type"] in keyed, k["hit"] / k["distinct"]), default=None)
    listing = next((k for k in lists if owner is None or k["col"] != owner["col"]), None)
    if owner is None or listing is None:
        return None, []
    if session.scalar(_REPEATS, {"owner": owner["col"], "list": listing["col"]}):
        return None, []
    session.execute(_ROWS_OF_KEY, {"t": owner["type"], "f": owner["field"], "col": owner["col"]})
    info = types[owner["type"]]
    identifying = set(session.execute(text("SELECT t, f FROM match_identifying")).tuples())
    owner_header = match.columns[owner["col"]]["header"]
    list_header = match.columns[listing["col"]]["header"]
    columns: list[dict[str, Any]] = [
        {"column": owner_header, "attributeTypeKey": owner["field"]},
        {"column": list_header, "ignore": True},
    ]
    unplaced: list[dict[str, Any]] = []
    filling = 0
    for col, (filled, distinct) in sorted(stats.items()):
        if col in (owner["col"], listing["col"]):
            continue
        header = match.columns[col]["header"]
        found = session.execute(_RELATED_FIELD, {"col": col}).first()
        if found is None or found[4] < AGREE_SHARE * filled:
            unplaced.append(
                {
                    "sheet": sheet,
                    "column": header,
                    "letter": match.columns[col].get("column"),
                    "filled": filled,
                    "distinct": distinct,
                }
            )
            continue
        relation, outgoing, target, field, _ = found
        if (target, field) in identifying:
            # It names the other record (an identifier), it fills nothing on it.
            columns.append({"column": header, "ignore": True})
            continue
        parents = session.execute(
            _LIST_PARENTS, {"list": listing["col"], "col": col, "relation": relation, "f": field}
        ).all()
        if not parents:
            continue
        map_name = f"{sheet}.{list_header}.parent"
        maps[map_name] = {value: parent for value, parent, _, _ in parents}
        columns.append(
            {
                "column": header,
                "relatedRecord": {
                    "relationTypeKey": relation,
                    "direction": "outgoing" if outgoing else "incoming",
                    "applicationKey": types[target].application,
                    "objectTypeKey": target,
                    "parent": {
                        "objectTypeKey": parents[0][2],
                        "matchBy": {"field": "id"},
                        "column": list_header,
                        "valueMap": map_name,
                    },
                    "attributeTypeKey": field,
                },
            }
        )
        filling += 1
    if not filling:
        return None, unplaced
    source = {
        "sheet": sheet,
        "headerRow": match.parameters["header"],
        **({"block": match.place["block"]} if match.place.get("block") else {}),
        "applicationKey": info.application,
        "objectTypeKey": owner["type"],
        "record": "existing",
        "key": {"attributeTypeKey": owner["field"], "storedUnique": True},
        "rowsWithoutKey": "skip",
        "columns": columns,
    }
    return source, unplaced


def run(
    session: Session,
    *,
    tables: list[dict[str, Any]],
    file_id: int,
    workspace: str,
    model: EngineModel,
    answers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The match of the task's tables with the workspace. The caller commits, which drops what
    this made: ``{tables, profile, questions, unplaced, facts}``."""
    answers = answers or {}
    types = type_infos(model)
    session.execute(text("DROP TABLE IF EXISTS match_fact"))
    session.execute(text("DROP TABLE IF EXISTS match_identifying"))
    session.execute(_FACTS, {"workspace": workspace})
    session.execute(text("CREATE INDEX ON match_fact (nv)"))
    session.execute(text("CREATE INDEX ON match_fact (oid, f)"))
    session.execute(text("ANALYZE match_fact"))
    session.execute(_IDENTIFYING)
    maps: dict[str, dict[str, Any]] = {}
    sources: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    unplaced: list[dict[str, Any]] = []
    unmatched: list[str] = []
    facts: list[dict[str, Any]] = []
    keyed: set[str] = set()

    # The tables with a key of their own first: rows that repeat a record follow what they name.
    for table in tables:
        match = _Table(session, table, file_id)
        if match.parameters["sheet"] is None or not match.columns:
            continue
        sheet = table["sheet"]
        stats = match.load()
        if not stats:
            continue
        rows = session.scalar(text("SELECT count(DISTINCT r) FROM match_cell")) or 0
        keys = _keys(session, stats, types)
        key = next(
            (k for k in keys if k["unique"] and k["field"] != NAME),
            next((k for k in keys if k["unique"]), None),
        )
        if key is None:
            source, left = _owner_rows(session, match, stats, keys, types, maps, keyed)
            if source is None:
                unmatched.append(sheet)
                facts.append({"sheet": sheet, "rows": rows, "found": "nothing it could match"})
                continue
            sources.append(source)
            unplaced += left
            facts.append(
                {
                    "sheet": sheet,
                    "rows": rows,
                    "found": f"rows repeat a stored {source['objectTypeKey']} per value of a list",
                }
            )
            continue
        for other in _ambiguous(keys, key):
            header = match.columns[other["col"]]["header"]
            questions.append(
                _question(
                    f"“{sheet}” could be {types[key['type']].plural} or "
                    f"{types[other['type']].plural}: “{header}” matches both as well. "
                    f"The design takes {types[key['type']].plural}.",
                    [types[key["type"]].plural, types[other["type"]].plural],
                    types[key["type"]].plural,
                    "ambiguous",
                )
            )
        keyed.add(key["type"])
        session.execute(_ROWS_OF_KEY, {"t": key["type"], "f": key["field"], "col": key["col"]})
        found = session.scalar(text("SELECT count(DISTINCT r) FROM match_row")) or 0
        placeholders: dict[int, list[tuple[str, int]]] = {}
        for col, value, count in session.execute(_PLACEHOLDERS):
            placeholders.setdefault(col, []).append((value, count))
        bindings, left, placed = _place_columns(
            session, match, stats, key, types, answers, maps, questions, placeholders
        )
        unplaced += left
        _conflicts(session, match, stats, key["col"], questions)
        header = match.columns[key["col"]]["header"]
        by_name = key["field"] == NAME
        bindings.insert(
            0,
            {"column": header, "field": "name"}
            if by_name
            else {"column": header, "attributeTypeKey": key["field"]},
        )
        info = types[key["type"]]
        declared = next((a for a, _ in info.unique if a == key["field"]), None)
        key_form: dict[str, Any] = (
            {"field": "name"}
            if by_name
            else {
                "attributeTypeKey": key["field"],
                **({} if declared else {"storedUnique": True}),
            }
        )
        gaps = [
            match.columns[c]["header"]
            for c, (filled, _) in stats.items()
            if 0 < rows - filled <= max(10, rows // 30)
        ]
        if rows - found:
            questions.append(
                _question(
                    f"{rows - found} rows of “{sheet}” have a “{header}” not stored yet: "
                    "they become new records.",
                    ["Create them", "Leave them out"],
                    "Create them",
                    "new",
                )
            )
        facts.append(
            {
                "sheet": sheet,
                "rows": rows,
                "type": key["type"],
                "key": header,
                "found": found,
                "new": rows - found,
                "columns": placed,
                "fewEmpty": gaps,
            }
        )
        sources.append(
            {
                "sheet": sheet,
                "headerRow": match.parameters["header"],
                **({"block": match.place["block"]} if match.place.get("block") else {}),
                "applicationKey": info.application,
                "objectTypeKey": key["type"],
                "record": "upsert",
                "key": key_form,
                "rowsWithoutKey": "skip",
                "columns": bindings,
            }
        )
    return {
        "profile": {"sources": sources, "valueMaps": maps},
        "questions": questions,
        "unplaced": unplaced,
        "unmatched": unmatched,
        "facts": facts,
    }


def needs_ai(found: dict[str, Any], words: str | None) -> bool:
    """Whether anything is left for the AI: the person's words, a column or a table with no place."""
    return bool(words and words.strip()) or bool(found["unplaced"]) or bool(found["unmatched"])
