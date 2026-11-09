"""The summary of a dry run of items (Product 0.13 AB).

A draft's dry run may carry batch items instead of a source file (``dry_run.py``). The worker
previews every item against the draft's model in a transaction it rolls back. Two things are read
from the database, set-wise:

- before the rollback, what only the loaded state shows: a name that appears more than once in one
  type once the load is in, with the parents its records sit under (:func:`name_twice`);
- after the outcomes are recorded, what each item did, from the job's inputs and outcomes
  (:func:`summarize`): per type the records new, matched (found, then updated or unchanged),
  changed and refused; the relationships per relation type; the types each type is linked to; up to
  :data:`EXAMPLES` example items per type with their cells; the places of the cells (an item's
  ``ref``, as ``Sheet!Q31:S31``) grouped into the parts of the file; and the rows read (the
  distinct sheet and row of the refs).

A refused item is an outcome with its ``ref``, as in a batch.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models.database import Job

EXAMPLES = 3
# Up to this many refused items, findings and parts of the file are listed; the totals are counted.
LISTED = 100
SHOWN_VALUES = 4

# Each item with its outcome; the queries below read it.
_RUN = """
run AS (
    SELECT i.item_index, i.ref, i.item::jsonb AS item, o.status, o.outcome::jsonb AS outcome
    FROM job_inputs i
    JOIN job_items o ON o.job_id = i.job_id AND o.item_index = i.item_index
    WHERE i.job_id = :job
)
"""

_RECORDS = f"""
WITH {_RUN}
SELECT coalesce(item ->> 'objectTypeKey', outcome ->> 'objectTypeKey', '') AS type_key,
    count(*) FILTER (WHERE status = 'applied' AND outcome ->> 'action' = 'created') AS new,
    count(*) FILTER (WHERE status = 'applied' AND item ->> 'op' <> 'create'
        AND outcome ->> 'action' IN ('updated', 'unchanged')) AS matched,
    count(*) FILTER (WHERE status = 'applied' AND item ->> 'op' <> 'create'
        AND outcome ->> 'action' = 'updated') AS changed,
    count(*) FILTER (WHERE status = 'applied' AND outcome ->> 'action' = 'deleted') AS removed,
    count(*) FILTER (WHERE status = 'rejected') AS refused
FROM run
WHERE item ->> 'op' IN ('create', 'upsert', 'update', 'delete')
GROUP BY 1
"""

_RELATIONS = f"""
WITH {_RUN},
direct AS (
    SELECT coalesce(item ->> 'relationTypeKey', '') AS relation_type_key, status,
        outcome ->> 'action' AS action
    FROM run
    WHERE item ->> 'op' IN ('createRelation', 'ensureRelation', 'ensureNoRelation',
        'updateRelation', 'deleteRelation')
),
initial AS (
    SELECT r ->> 'relationTypeKey' AS relation_type_key, 'applied' AS status, 'created' AS action
    FROM run, jsonb_array_elements(
        CASE WHEN jsonb_typeof(item -> 'initialRelations') = 'array'
            THEN item -> 'initialRelations' ELSE '[]'::jsonb END) AS r
    WHERE item ->> 'op' IN ('create', 'upsert') AND status = 'applied'
        AND outcome ->> 'action' = 'created'
)
SELECT relation_type_key,
    count(*) FILTER (WHERE status = 'applied' AND action = 'created') AS new,
    count(*) FILTER (WHERE status = 'applied' AND action IN ('updated', 'unchanged')) AS matched,
    count(*) FILTER (WHERE status = 'rejected') AS refused
FROM (SELECT * FROM direct UNION ALL SELECT * FROM initial) found
GROUP BY 1
"""

# The records the load creates under a parent: each one is a relationship of its own in the change
# set, and the load's counts include it, so the check counts it too.
_PARENT_LINKS = f"""
WITH {_RUN}
SELECT count(*) AS new FROM run
WHERE item ->> 'op' IN ('create', 'upsert') AND status = 'applied'
    AND outcome ->> 'action' = 'created' AND jsonb_typeof(item -> 'parent') = 'object'
"""

# The types each type is linked to by the relationships the items make: the ends of a relation item,
# and a created record with its initial relations. An end is typed by its reference, by the record
# the load creates under that ID, or by the stored record.
_LINKS = f"""
WITH {_RUN},
made AS (
    SELECT item ->> 'id' AS id, item ->> 'objectTypeKey' AS type_key FROM run
    WHERE item ->> 'op' = 'create' AND item ? 'id'
    UNION ALL
    SELECT item -> 'key' ->> 'id', item ->> 'objectTypeKey' FROM run
    WHERE item ->> 'op' = 'upsert' AND item -> 'key' ? 'id'
),
ends AS (
    SELECT item -> 'from' AS f, item -> 'to' AS t FROM run
    WHERE item ->> 'op' IN ('createRelation', 'ensureRelation') AND status = 'applied'
    UNION ALL
    SELECT CASE WHEN r ->> 'direction' = 'outgoing'
            THEN jsonb_build_object('objectTypeKey', item ->> 'objectTypeKey') ELSE r -> 'object' END,
        CASE WHEN r ->> 'direction' = 'outgoing'
            THEN r -> 'object' ELSE jsonb_build_object('objectTypeKey', item ->> 'objectTypeKey') END
    FROM run, jsonb_array_elements(
        CASE WHEN jsonb_typeof(item -> 'initialRelations') = 'array'
            THEN item -> 'initialRelations' ELSE '[]'::jsonb END) AS r
    WHERE item ->> 'op' IN ('create', 'upsert') AND status = 'applied'
),
typed AS (
    SELECT coalesce(e.f ->> 'objectTypeKey', mf.type_key, xf.object_type_key) AS from_type,
        coalesce(e.t ->> 'objectTypeKey', mt.type_key, xt.object_type_key) AS to_type
    FROM ends e
    LEFT JOIN (SELECT DISTINCT ON (id) * FROM made) mf ON mf.id = e.f ->> 'id'
    LEFT JOIN objects xf ON xf.id = e.f ->> 'id'
    LEFT JOIN (SELECT DISTINCT ON (id) * FROM made) mt ON mt.id = e.t ->> 'id'
    LEFT JOIN objects xt ON xt.id = e.t ->> 'id'
)
SELECT DISTINCT from_type, to_type FROM typed WHERE from_type IS NOT NULL AND to_type IS NOT NULL
"""

# The cells the items come from: ``Sheet!Q31:S31`` (or one cell), by sheet, columns and type.
_PARSED = f"""
WITH {_RUN},
parsed AS (
    SELECT item_index, item, outcome,
        regexp_match(ref, '^(.+)!([A-Z]+)([0-9]+)(?::([A-Z]+)([0-9]+))?$') AS m
    FROM run WHERE ref IS NOT NULL
),
cells AS (
    SELECT item_index, m[1] AS sheet, m[2] AS first_column, coalesce(m[4], m[2]) AS last_column,
        m[3]::int AS first_row, coalesce(m[5], m[3])::int AS last_row,
        CASE WHEN item ->> 'op' IN ('create', 'upsert', 'update', 'delete')
            THEN coalesce(item ->> 'objectTypeKey', outcome ->> 'objectTypeKey') END AS type_key,
        CASE WHEN item ->> 'op' IN ('createRelation', 'ensureRelation', 'ensureNoRelation')
            THEN item ->> 'relationTypeKey' END AS relation_type_key
    FROM parsed WHERE m IS NOT NULL
)
"""

_PARTS = (
    _PARSED
    + """
SELECT sheet, first_column, last_column, type_key, relation_type_key,
    min(first_row) AS first_row, max(last_row) AS last_row, count(*) AS items
FROM cells
GROUP BY 1, 2, 3, 4, 5
ORDER BY sheet, length(first_column), first_column, min(first_row)
"""
)

_ROWS_READ = (
    _PARSED
    + """
SELECT sheet, count(DISTINCT row_number) AS rows
FROM cells, generate_series(first_row, least(last_row, first_row + 9999)) AS row_number
GROUP BY sheet ORDER BY sheet
"""
)

# The first examples of each type: a refused item before an accepted one, then in order.
_EXAMPLES = f"""
WITH {_RUN},
ranked AS (
    SELECT run.*, coalesce(item ->> 'objectTypeKey', outcome ->> 'objectTypeKey', '') AS type_key,
        row_number() OVER (
            PARTITION BY coalesce(item ->> 'objectTypeKey', outcome ->> 'objectTypeKey', '')
            ORDER BY (status = 'rejected') DESC, item_index) AS place
    FROM run WHERE item ->> 'op' IN ('create', 'upsert', 'update')
)
SELECT item_index, ref, type_key, status, item, outcome,
    (SELECT x.name FROM objects x WHERE x.id = outcome ->> 'id') AS stored_name
FROM ranked WHERE place <= :examples ORDER BY type_key, place
"""

_REFUSED = f"""
WITH {_RUN}
SELECT item_index, ref, coalesce(item ->> 'objectTypeKey', item ->> 'relationTypeKey') AS key,
    outcome -> 'error' ->> 'code' AS code, outcome -> 'error' ->> 'message' AS message
FROM run WHERE status = 'rejected' ORDER BY item_index LIMIT :limit
"""

_REFUSED_BY_CODE = f"""
WITH {_RUN}
SELECT coalesce(outcome -> 'error' ->> 'code', 'REFUSED') AS code, count(*) AS items
FROM run WHERE status = 'rejected' GROUP BY 1 ORDER BY 2 DESC, 1
"""

# Relation items that touch an example record, to list its links.
_EXAMPLE_LINKS = f"""
WITH {_RUN}
SELECT item ->> 'relationTypeKey' AS relation_type_key, item -> 'from' AS from_ref,
    item -> 'to' AS to_ref
FROM run
WHERE item ->> 'op' IN ('createRelation', 'ensureRelation') AND status = 'applied'
    AND (item -> 'from' ->> 'id' = ANY(CAST(:ids AS text[]))
        OR item -> 'to' ->> 'id' = ANY(CAST(:ids AS text[])))
ORDER BY item_index
"""

# The name and type of records the examples point to: created by the load, or stored.
_NAMES = f"""
WITH {_RUN}
SELECT id, name, type_key FROM (
    SELECT item ->> 'id' AS id, item ->> 'name' AS name, item ->> 'objectTypeKey' AS type_key
    FROM run WHERE item ->> 'op' = 'create' AND item ? 'id'
    UNION ALL
    SELECT item -> 'key' ->> 'id', item ->> 'name', item ->> 'objectTypeKey'
    FROM run WHERE item ->> 'op' = 'upsert' AND item -> 'key' ? 'id'
    UNION ALL
    SELECT x.id, x.name, x.object_type_key FROM objects x WHERE x.id = ANY(CAST(:ids AS text[]))
) found WHERE id = ANY(CAST(:ids AS text[]))
"""

# A name that appears more than once in a type among the records the load touches, once the load
# is in, with the parents the records sit under. Read in the preview's transaction; ``applied`` are
# the items the preview accepted.
_NAME_TWICE = """
WITH touched AS (
    SELECT DISTINCT item ->> 'objectTypeKey' AS type_key, lower(btrim(item ->> 'name')) AS name
    FROM (SELECT item::jsonb AS item FROM job_inputs
        WHERE job_id = :job AND item_index = ANY(CAST(:applied AS integer[]))) accepted
    WHERE item ->> 'op' IN ('create', 'upsert') AND item ->> 'name' IS NOT NULL
)
SELECT x.object_type_key AS type_key, min(x.name) AS name, count(*) AS records,
    jsonb_agg(jsonb_build_object('id', p.id, 'name', p.name, 'objectTypeKey', p.object_type_key)
        ORDER BY p.name NULLS FIRST) AS parents
FROM objects x
JOIN touched t ON t.type_key = x.object_type_key AND t.name = lower(btrim(x.name))
LEFT JOIN objects p ON p.id = x.parent_object_id
WHERE x.workspace_key = :workspace
GROUP BY x.object_type_key, lower(btrim(x.name))
HAVING count(*) > 1
ORDER BY count(*) DESC, x.object_type_key, min(x.name)
LIMIT :limit
"""


def name_twice(session: Session, job: Job, applied: list[int]) -> list[dict[str, Any]]:
    """The finding the loaded state shows: a name that appears more than once in one type among the
    records the accepted items touch, with the parents they sit under (``null`` for a record at the
    root). Called inside the preview's transaction, before it is rolled back."""
    found = session.execute(
        text(_NAME_TWICE),
        {
            "job": job.sequence_id,
            "applied": applied,
            "workspace": job.workspace_key,
            "limit": LISTED,
        },
    ).all()
    return [
        {
            "kind": "nameTwice",
            "objectTypeKey": row.type_key,
            "name": row.name,
            "count": row.records,
            "parents": [
                {
                    "id": parent["id"],
                    "name": parent["name"],
                    "objectTypeKey": parent["objectTypeKey"],
                }
                if parent.get("id")
                else None
                for parent in row.parents
            ],
        }
        for row in found
    ]


def _values(item: dict[str, Any]) -> list[dict[str, Any]]:
    attributes = item.get("attributes")
    if not isinstance(attributes, list):
        return []
    return [
        {"attributeTypeKey": a.get("attributeTypeKey"), "value": a.get("value")}
        for a in attributes[:SHOWN_VALUES]
        if isinstance(a, dict)
    ]


def _example_links(session: Session, job: Job, examples: list[dict[str, Any]]) -> None:
    """Each example's links: its initial relations, and the relation items that name its ID."""
    ids = sorted({e["id"] for e in examples if e.get("id")})
    named_by: dict[str, list[dict[str, Any]]] = {}
    if ids:
        for row in session.execute(text(_EXAMPLE_LINKS), {"job": job.sequence_id, "ids": ids}):
            for own, other, direction in (
                (row.from_ref, row.to_ref, "outgoing"),
                (row.to_ref, row.from_ref, "incoming"),
            ):
                if own.get("id") in ids:
                    named_by.setdefault(own["id"], []).append(
                        {
                            "relationTypeKey": row.relation_type_key,
                            "direction": direction,
                            "object": other,
                        }
                    )
    for example in examples:
        example["found"] = [
            *(r for r in example.pop("initial") if isinstance(r.get("object"), dict)),
            *named_by.get(example.get("id") or "", []),
        ][:SHOWN_VALUES]
    wanted = sorted(
        {link["object"]["id"] for e in examples for link in e["found"] if link["object"].get("id")}
    )
    names = (
        {
            row.id: row
            for row in session.execute(text(_NAMES), {"job": job.sequence_id, "ids": wanted})
        }
        if wanted
        else {}
    )
    for example in examples:
        example["links"] = []
        for link in example.pop("found"):
            reference = link["object"]
            found = names.get(reference.get("id"))
            example["links"].append(
                {
                    "relationTypeKey": link["relationTypeKey"],
                    "direction": link["direction"],
                    "objectTypeKey": reference.get("objectTypeKey")
                    or (found.type_key if found else None),
                    "name": found.name if found else (reference.get("key") or {}).get("value"),
                }
            )


def summarize(session: Session, job: Job, *, found_names: list[dict[str, Any]]) -> dict[str, Any]:
    """The summary of the job's items, once their outcomes are recorded (module docstring)."""
    parameters = {"job": job.sequence_id}
    types: dict[str, dict[str, Any]] = {}
    for row in session.execute(text(_RECORDS), parameters):
        types[row.type_key] = {
            "objectTypeKey": row.type_key,
            "new": row.new,
            "matched": row.matched,
            "changed": row.changed,
            "removed": row.removed,
            "refused": row.refused,
            "linkedTo": [],
            "examples": [],
        }
    linked: dict[str, set[str]] = {}
    for row in session.execute(text(_LINKS), parameters):
        linked.setdefault(row.from_type, set()).add(row.to_type)
        linked.setdefault(row.to_type, set()).add(row.from_type)
    for key, entry in types.items():
        entry["linkedTo"] = sorted(linked.get(key, set()))
    examples: list[dict[str, Any]] = []
    for row in session.execute(text(_EXAMPLES), {**parameters, "examples": EXAMPLES}):
        item, outcome = row.item, row.outcome
        error = outcome.get("error") or {}
        example = {
            "index": row.item_index,
            "ref": row.ref,
            "objectTypeKey": row.type_key,
            "action": outcome.get("action") if row.status == "applied" else "refused",
            "name": item.get("name") or row.stored_name,
            "id": outcome.get("id") or item.get("id") or (item.get("key") or {}).get("id"),
            "values": _values(item),
            "error": {"code": error.get("code"), "message": error.get("message")}
            if row.status == "rejected"
            else None,
            "initial": [r for r in item.get("initialRelations") or [] if isinstance(r, dict)],
        }
        examples.append(example)
    _example_links(session, job, examples)
    for example in examples:
        types[example["objectTypeKey"]]["examples"].append(example)
    relationships = [
        {
            "relationTypeKey": row.relation_type_key,
            "new": row.new,
            "matched": row.matched,
            "refused": row.refused,
        }
        for row in session.execute(text(_RELATIONS), parameters)
    ]
    parent_links = session.scalar(text(_PARENT_LINKS), parameters) or 0
    sheets = [
        {"sheet": row.sheet, "rows": row.rows}
        for row in session.execute(text(_ROWS_READ), parameters)
    ]
    parts = [
        {
            "sheet": row.sheet,
            "firstColumn": row.first_column,
            "lastColumn": row.last_column,
            "firstRow": row.first_row,
            "lastRow": row.last_row,
            "objectTypeKey": row.type_key,
            "relationTypeKey": row.relation_type_key,
            "items": row.items,
        }
        for row in session.execute(text(_PARTS), parameters)
    ]
    refused = [
        {
            "index": row.item_index,
            "ref": row.ref,
            "key": row.key,
            "code": row.code,
            "message": row.message,
        }
        for row in session.execute(text(_REFUSED), {**parameters, "limit": LISTED})
    ]
    ordered = sorted(
        types.values(),
        key=lambda e: (-(e["new"] + e["matched"] + e["refused"]), e["objectTypeKey"]),
    )
    return {
        "mode": "items",
        "jobId": job.id,
        "draftId": job.parameters["draftId"],
        "draftVersion": job.parameters["draftVersion"],
        "workspaceKey": job.workspace_key,
        "items": job.total,
        "figures": {
            "recordsNew": sum(e["new"] for e in ordered),
            "recordsMatched": sum(e["matched"] for e in ordered),
            "recordsChanged": sum(e["changed"] for e in ordered),
            "recordsRemoved": sum(e["removed"] for e in ordered),
            # What the load counts as new relationships: the ones the items name and each new
            # record's link to its parent, so the figure accepted is the figure loaded.
            "relationshipsNew": sum(r["new"] for r in relationships) + parent_links,
            "parentLinksNew": parent_links,
            "relationshipsMatched": sum(r["matched"] for r in relationships),
            "refused": sum(e["refused"] for e in ordered)
            + sum(r["refused"] for r in relationships),
            "rowsRead": sum(s["rows"] for s in sheets),
        },
        "types": ordered,
        "relationships": sorted(relationships, key=lambda r: (-r["new"], r["relationTypeKey"])),
        "sheets": sheets,
        "parts": parts[:LISTED],
        "partsTotal": len(parts),
        "findings": found_names,
        "refused": refused,
        "refusedByCode": [
            {"code": row.code, "items": row.items}
            for row in session.execute(text(_REFUSED_BY_CODE), parameters)
        ],
        "ranAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
