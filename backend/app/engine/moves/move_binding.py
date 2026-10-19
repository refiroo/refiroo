"""A move's binding: the selection read through the mapping into the target's batch items and the
rows of what cannot move (Product 0.11 X2, D115, D118, D119).

Python compiles the mapping, a few dozen entries, into small tables (types, attributes, defaults,
value maps, relationships, the target's required relationships); everything about records is a set
statement over them, in the job's one transaction:

1. **What is read.** The selected records of the source (live data or a publication) with their
   values, every relationship one of them holds (containment is the parent, not a relationship),
   and the records those relationships and parents name that are not selected ("others").
2. **What each record becomes** (D118): its mapped type; its values through the value map, then
   ``rdm_convert_value``, then the mapping's defaults, with what is left behind per attribute
   (``ATTRIBUTE_NOT_MAPPED``, ``VALUE_NOT_CONVERTIBLE``, ``ATTRIBUTE_READ_ONLY``,
   ``EFFECTIVE_PERIOD_DROPPED``); found in the target by its origins (a record moved back finds
   its original, ``updateOriginal``, or is created again under the original's ID when that is
   gone, X3 D133), else by its counterpart (``rdm_counterpart``, D120), else by the mapping's
   ``match``, else created under its counterpart ID.
3. **Where it stands.** Under its source parent's target record (moved along, found, or created
   when the mapping says ``missing: create``), or under one record named by the mapping, or at the
   top; otherwise not moved (``PARENT_NOT_FOUND``, ``PARENT_TYPE_NOT_MAPPED``). A record under one
   that does not move does not move either (``RECORD_NOT_MOVED``), level by level.
4. **Its relationships.** Carried between records that move or are found in the target; otherwise
   not moved (``RELATION_NOT_MAPPED``, ``RELATION_TARGET_LEFT_BEHIND``), or the record refused when
   the mapping says ``missing: refuse``. A relationship the target requires into a record it
   creates is carried on that record's create, so the target's rule sees it (I20).
5. **The rows.** Records in the order they must be created (a parent, and the record a required
   relationship comes from, before the record), then relationships. A row the mapping decides
   (``notMoved``, an ambiguous match) is the job's outcome at once; every other row waits as an
   input holding its batch item, which the preview runs (``move_job.py``).

The statements per move do not grow with its records: the two loops (records under one that does
not move, and the creation order) run once per level of the source's hierarchy.
"""

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import cast, column, insert, literal, select, table, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...models.database import Job
from ...models.moves import MoveSelection
from ..reads.context_sets import record_source, relation_source
from ..reads.snapshot_reads import SnapshotContext
from .selection import selected_ids
from .sides import Side

# The records' levels and the records under one that does not move are walked at most this deep;
# deeper than any hierarchy a model allows a record (a self-hierarchy included) in practice.
MAX_LEVELS = 1_000
# Possible duplicates and ambiguous matches name at most this many target records (API.md).
NAMED_RECORDS = 10

_TABLES = (
    """CREATE TEMPORARY TABLE mv_types (source_type text PRIMARY KEY, target_type text NOT NULL,
        match_attr text, match_name boolean NOT NULL, parent_kind text, parent_type text,
        parent_value text, parent_missing text) ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_target_types (type_key text PRIMARY KEY, app text NOT NULL)
        ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_attrs (source_type text, source_attr text, from_type text,
        target_attr text, to_type text, value_map text, status text NOT NULL,
        PRIMARY KEY (source_type, source_attr)) ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_defaults (source_type text, target_attr text, value jsonb)
        ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_value_maps (name text, source text, value jsonb,
        PRIMARY KEY (name, source)) ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_rel_map (source_type text, relation text, target_relation text,
        direction text, missing text, attrs jsonb NOT NULL, PRIMARY KEY (source_type, relation))
        ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_required (relation text, from_type text, to_type text)
        ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_records (object_id text PRIMARY KEY, selected boolean NOT NULL,
        along boolean NOT NULL DEFAULT false, source_type text, name text, parent_id text,
        attributes jsonb NOT NULL DEFAULT '{}', target_type text, target_app text, target_id text,
        target_version integer, found text, matched jsonb, outcome text,
        reasons jsonb NOT NULL DEFAULT '[]', left_behind jsonb NOT NULL DEFAULT '[]',
        target_values jsonb NOT NULL DEFAULT '{}', parent_row text,
        set_parent boolean NOT NULL DEFAULT false, target_parent_id text, duplicates jsonb,
        level integer NOT NULL DEFAULT 0, row_index integer, source_version integer,
        recreated boolean NOT NULL DEFAULT false) ON COMMIT DROP""",
    "CREATE INDEX ON mv_records (parent_row)",
    "CREATE INDEX ON mv_records (target_id)",
    """CREATE TEMPORARY TABLE mv_values (object_id text, source_attr text, target_attr text,
        before jsonb, after jsonb, status text) ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_fixed (source_type text PRIMARY KEY, parent_type text,
        parent_value text, missing text, found integer, first_id text, synthetic text)
        ON COMMIT DROP""",
    """CREATE TEMPORARY TABLE mv_relations (relation_id text PRIMARY KEY, relation_type text,
        from_id text, to_id text, attributes jsonb NOT NULL DEFAULT '{}', target_relation text,
        direction text, missing text, attrs jsonb, t_from text, t_to text, t_from_type text,
        t_to_type text, rider text, target_values jsonb NOT NULL DEFAULT '{}',
        left_behind jsonb NOT NULL DEFAULT '[]', outcome text,
        reasons jsonb NOT NULL DEFAULT '[]', row_index integer) ON COMMIT DROP""",
    "CREATE INDEX ON mv_relations (from_id)",
    "CREATE INDEX ON mv_relations (to_id)",
    "CREATE TEMPORARY TABLE mv_deps (child text, parent text) ON COMMIT DROP",
)

_RECORDS = table(
    "mv_records",
    column("object_id"),
    column("selected"),
    column("source_type"),
    column("name"),
    column("parent_id"),
    column("attributes"),
    column("source_version"),
)
_RELATIONS = table(
    "mv_relations",
    column("relation_id"),
    column("relation_type"),
    column("from_id"),
    column("to_id"),
    column("attributes"),
)


def _reason(code: str, message: str, action: str | None, details: str = "NULL") -> str:
    """A reason as a JSON array of one, in SQL; ``message`` and ``details`` are SQL expressions."""
    act = f"'{action}'" if action else "NULL"
    return (
        f"jsonb_build_array(jsonb_strip_nulls(jsonb_build_object('code', '{code}', "
        f"'message', {message}, 'action', {act}, 'details', {details})))"
    )


def _moving(alias: str) -> str:
    """Whether the record ``alias`` moves: created or updated in the target."""
    return f"COALESCE({alias}.outcome IN ('create', 'update'), false)"


def _escaped(key: str) -> str:
    """A key as a JSON pointer token, in SQL."""
    return f"replace(replace({key}, '~', '~0'), '/', '~1')"


_MATCH_AMBIGUOUS = _reason(
    "MATCH_AMBIGUOUS",
    "c.n || ' records of the target match it'",
    "setMatch",
    "jsonb_build_object('count', c.n, 'candidates', to_jsonb(c.ids))",
)
_TYPE_NOT_MAPPED = _reason(
    "TYPE_NOT_MAPPED", "'The mapping maps no target type for ' || source_type", "mapType"
)

# --- what each record becomes ----------------------------------------------------------------------

_STEPS_RECORDS = (
    # Its mapped type and the target's application of it.
    """UPDATE mv_records r SET target_type = t.target_type, target_app = a.app
    FROM mv_types t JOIN mv_target_types a ON a.type_key = t.target_type
    WHERE t.source_type = r.source_type""",
    # Each value: through the value map, then converted; what is left behind, by why.
    """INSERT INTO mv_values
    SELECT r.object_id, e.key, a.target_attr, e.value,
        CASE WHEN a.status = 'carry' AND m.name IS NULL
            THEN rdm_convert_value(e.value::json, a.from_type, a.to_type)::jsonb
            WHEN a.status = 'carry' AND jsonb_typeof(m.value) <> 'null'
            THEN rdm_convert_value(m.value::json, a.from_type, a.to_type)::jsonb END,
        CASE WHEN a.source_attr IS NULL THEN 'unmapped' WHEN a.status <> 'carry' THEN a.status
            WHEN m.name IS NOT NULL AND jsonb_typeof(m.value) = 'null' THEN 'cleared'
            ELSE 'carry' END
    FROM mv_records r CROSS JOIN LATERAL jsonb_each(r.attributes) e
    LEFT JOIN mv_attrs a ON a.source_type = r.source_type AND a.source_attr = e.key
    LEFT JOIN mv_value_maps m ON m.name = a.value_map AND m.source = (e.value #>> '{}')
    WHERE r.target_type IS NOT NULL AND jsonb_typeof(e.value) <> 'null'""",
    """UPDATE mv_values SET status = 'lost'
    WHERE status = 'carry' AND (after IS NULL OR jsonb_typeof(after) = 'null')""",
    f"""UPDATE mv_records r SET target_values = v.carried, left_behind = v.left_behind FROM (
        SELECT object_id,
            COALESCE(jsonb_object_agg(target_attr, after) FILTER (WHERE status = 'carry'), '{{}}')
                AS carried,
            COALESCE(jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
                'code', CASE status WHEN 'unmapped' THEN 'ATTRIBUTE_NOT_MAPPED'
                    WHEN 'lost' THEN 'VALUE_NOT_CONVERTIBLE'
                    WHEN 'readOnly' THEN 'ATTRIBUTE_READ_ONLY'
                    ELSE 'EFFECTIVE_PERIOD_DROPPED' END,
                'attributeTypeKey', source_attr, 'targetAttributeTypeKey', target_attr,
                'pointer', '/attributes/' || {_escaped("source_attr")}, 'value', before))
                ORDER BY source_attr)
                FILTER (WHERE status IN ('unmapped', 'lost', 'readOnly', 'period')), '[]')
                AS left_behind
        FROM mv_values GROUP BY object_id) v
    WHERE v.object_id = r.object_id""",
    # The mapping's defaults for a target attribute the record gives no value.
    """UPDATE mv_records r SET target_values = d.defaults || r.target_values FROM (
        SELECT source_type, jsonb_object_agg(target_attr, value) AS defaults FROM mv_defaults
        WHERE jsonb_typeof(value) <> 'null' GROUP BY source_type) d
    WHERE d.source_type = r.source_type AND r.target_type IS NOT NULL""",
    # Found by its origin (I3, D133): the nearest record of the target along its chain of
    # origins, of the mapped type; or, when that original is gone and its ID free, created again
    # under its ID (``recreated``, which counts as not in the target).
    f"""WITH RECURSIVE chain (start_id, workspace_key, object_id, depth) AS (
        SELECT r.object_id, o.origin_workspace_key, o.origin_object_id, 1
        FROM mv_records r JOIN record_origins o ON o.object_id = r.object_id
        WHERE r.target_type IS NOT NULL
        UNION ALL
        SELECT c.start_id, o.origin_workspace_key, o.origin_object_id, c.depth + 1
        FROM chain c JOIN record_origins o ON o.object_id = c.object_id
        WHERE c.workspace_key <> :target AND c.depth < {MAX_LEVELS}),
    nearest AS (SELECT DISTINCT ON (start_id) start_id, object_id FROM chain
        WHERE workspace_key = :target ORDER BY start_id, depth)
    UPDATE mv_records r SET target_id = n.object_id, target_version = o.version,
        found = CASE WHEN o.id IS NOT NULL THEN 'origin' END, recreated = o.id IS NULL
    FROM nearest n LEFT JOIN objects o ON o.id = n.object_id AND o.workspace_key = :target
    WHERE r.object_id = n.start_id AND (o.object_type_key = r.target_type
        OR (o.id IS NULL AND NOT EXISTS (SELECT 1 FROM objects x WHERE x.id = n.object_id)))""",
    # Else found by its counterpart (I2).
    """UPDATE mv_records r SET target_id = o.id, target_version = o.version, found = 'counterpart',
        recreated = false
    FROM objects o
    WHERE r.target_type IS NOT NULL AND r.found IS NULL AND o.workspace_key = :target
        AND o.id = rdm_counterpart(:target, r.object_id)""",
    # Else found by the mapping's match: a unique attribute's value, or the name (I12).
    f"""WITH candidates AS (
        SELECT r.object_id, count(*) AS n, min(o.id) AS first,
            (array_agg(o.id ORDER BY o.id))[1:{NAMED_RECORDS}] AS ids
        FROM mv_records r JOIN mv_types t ON t.source_type = r.source_type
        JOIN attribute_values a ON a.attribute_type_key = t.match_attr
            AND rdm_value_json(a.value_type, a.text_value, a.integer_value, a.decimal_value,
                a.boolean_value, a.date_value, a.datetime_value, a.json_value)::jsonb
                = r.target_values -> t.match_attr
        JOIN objects o ON o.id = a.object_id AND o.workspace_key = :target
            AND o.object_type_key = r.target_type
        WHERE r.found IS NULL AND t.match_attr IS NOT NULL GROUP BY r.object_id
        UNION ALL
        SELECT r.object_id, count(*), min(o.id), (array_agg(o.id ORDER BY o.id))[1:{NAMED_RECORDS}]
        FROM mv_records r JOIN mv_types t ON t.source_type = r.source_type AND t.match_name
        JOIN objects o ON o.workspace_key = :target AND o.object_type_key = r.target_type
            AND o.name = r.name
        WHERE r.found IS NULL GROUP BY r.object_id)
    UPDATE mv_records r SET
        matched = CASE WHEN t.match_name THEN jsonb_build_object('field', 'name')
            ELSE jsonb_build_object('attributeTypeKey', t.match_attr) END,
        found = CASE WHEN c.n = 1 THEN 'match' END, recreated = false,
        target_id = CASE WHEN c.n = 1 THEN c.first END,
        target_version = CASE WHEN c.n = 1 THEN o.version END,
        outcome = CASE WHEN c.n > 1 THEN 'refused' END,
        reasons = CASE WHEN c.n > 1 THEN {_MATCH_AMBIGUOUS} ELSE r.reasons END
    FROM candidates c JOIN mv_types t ON true LEFT JOIN objects o ON o.id = c.first
    WHERE c.object_id = r.object_id AND t.source_type = r.source_type""",
    # A selected record's outcome before the target's rules.
    f"""UPDATE mv_records SET
        outcome = CASE WHEN target_type IS NULL THEN 'notMoved'
            WHEN found IS NOT NULL THEN 'update' ELSE 'create' END,
        reasons = CASE WHEN target_type IS NULL THEN {_TYPE_NOT_MAPPED} ELSE reasons END,
        target_id = CASE WHEN target_type IS NULL THEN NULL
            ELSE COALESCE(target_id, rdm_counterpart(:target, object_id)) END
    WHERE selected AND outcome IS NULL""",
)

# --- where it stands -------------------------------------------------------------------------------

_PARENT_TYPE_NOT_MAPPED = _reason(
    "PARENT_TYPE_NOT_MAPPED",
    "'Its parent''s type ' || p.source_type || ' is not mapped and the parent is not in the target'",
    "mapType",
    "jsonb_build_object('parentId', p.object_id)",
)
_PARENT_NOT_FOUND = _reason(
    "PARENT_NOT_FOUND",
    "'Its parent ' || p.object_id || ' is neither moved along nor in the target'",
    "select",
    "jsonb_build_object('parentId', p.object_id)",
)
_FIXED_NOT_FOUND = _reason(
    "PARENT_NOT_FOUND",
    "f.found || ' records of ' || f.parent_type || ' named ' || f.parent_value"
    " || ' are in the target'",
    "setParent",
    "jsonb_build_object('objectTypeKey', f.parent_type, 'value', f.parent_value, 'count', f.found)",
)
_FIXED_FITS = "(f.found = 1 OR (f.found = 0 AND f.missing = 'create'))"

_STEPS_PARENTS = (
    # Under the target record of its source parent: which row that is.
    f"""UPDATE mv_records r SET set_parent = true, parent_row = r.parent_id FROM mv_types t
    WHERE t.source_type = r.source_type AND t.parent_kind = 'source' AND r.selected
        AND {_moving("r")}""",
    # A parent neither selected nor in the target, created when the mapping says so.
    f"""UPDATE mv_records p SET along = true, outcome = 'create',
        target_id = COALESCE(p.target_id, rdm_counterpart(:target, p.object_id))
    FROM mv_records r JOIN mv_types t ON t.source_type = r.source_type
    WHERE r.parent_row = p.object_id AND NOT p.selected AND p.found IS NULL
        AND p.target_type IS NOT NULL AND t.parent_missing = 'create' AND {_moving("r")}""",
    f"""UPDATE mv_records r SET outcome = 'notMoved', reasons = CASE
        WHEN p.target_type IS NULL THEN {_PARENT_TYPE_NOT_MAPPED} ELSE {_PARENT_NOT_FOUND} END
    FROM mv_records p
    WHERE r.parent_row = p.object_id AND NOT p.selected AND p.found IS NULL AND NOT p.along
        AND {_moving("r")}""",
    # Under one record the mapping names: found by type and name, or created.
    """INSERT INTO mv_fixed
    SELECT t.source_type, t.parent_type, t.parent_value, t.parent_missing,
        (SELECT count(*) FROM objects o WHERE o.workspace_key = :target
            AND o.object_type_key = t.parent_type AND o.name = t.parent_value),
        (SELECT min(o.id) FROM objects o WHERE o.workspace_key = :target
            AND o.object_type_key = t.parent_type AND o.name = t.parent_value),
        'fixed:' || t.parent_type || '/' || t.parent_value
    FROM mv_types t WHERE t.parent_kind = 'fixed'""",
    f"""INSERT INTO mv_records
        (object_id, selected, along, name, target_type, target_app, target_id, outcome)
    SELECT DISTINCT f.synthetic, false, true, f.parent_value, f.parent_type, a.app,
        rdm_counterpart(:target, f.synthetic), 'create'
    FROM mv_fixed f JOIN mv_target_types a ON a.type_key = f.parent_type
    WHERE f.found = 0 AND f.missing = 'create' AND EXISTS (SELECT 1 FROM mv_records r
        WHERE r.source_type = f.source_type AND r.selected AND {_moving("r")})
    ON CONFLICT (object_id) DO NOTHING""",
    f"""UPDATE mv_records r SET set_parent = true,
        parent_row = CASE WHEN f.found = 0 AND f.missing = 'create' THEN f.synthetic END,
        target_parent_id = CASE WHEN f.found = 1 THEN f.first_id END,
        outcome = CASE WHEN {_FIXED_FITS} THEN r.outcome ELSE 'notMoved' END,
        reasons = CASE WHEN {_FIXED_FITS} THEN r.reasons ELSE {_FIXED_NOT_FOUND} END
    FROM mv_fixed f
    WHERE f.source_type = r.source_type AND r.selected AND {_moving("r")}""",
)

# --- relationships ---------------------------------------------------------------------------------

_RELATION_NOT_MAPPED = _reason(
    "RELATION_NOT_MAPPED", "'The mapping does not carry ' || relation_type", "mapRelation"
)
_REFUSED_FOR_RELATION = _reason(
    "RELATION_TARGET_LEFT_BEHIND",
    "'Its ' || x.relation_type || ' relationship names ' || e.object_id"
    " || ', which is neither moved along nor in the target'",
    "select",
    "jsonb_build_object('relationId', x.relation_id, 'objectId', e.object_id)",
)

_STEPS_RELATIONS = (
    """UPDATE mv_relations x SET target_relation = m.target_relation, direction = m.direction,
        missing = m.missing, attrs = m.attrs
    FROM mv_records f JOIN mv_rel_map m ON m.source_type = f.source_type
    WHERE f.object_id = x.from_id AND m.relation = x.relation_type""",
    f"""UPDATE mv_relations SET outcome = 'notMoved', reasons = {_RELATION_NOT_MAPPED}
    WHERE target_relation IS NULL""",
    # ``missing: refuse``: a selected record whose relationship's other end is left behind does
    # not move.
    f"""UPDATE mv_records r SET outcome = 'notMoved', reasons = {_REFUSED_FOR_RELATION}
    FROM mv_relations x JOIN mv_records e ON e.object_id IN (x.from_id, x.to_id)
    WHERE x.outcome IS NULL AND x.missing = 'refuse' AND r.object_id IN (x.from_id, x.to_id)
        AND e.object_id <> r.object_id AND r.selected AND {_moving("r")} AND NOT e.selected
        AND e.found IS NULL AND NOT e.along""",
)

# A record under one that does not move does not move either; run until nothing changes.
_CASCADE = f"""UPDATE mv_records c SET outcome = 'notMoved', reasons = {
    _reason(
        "RECORD_NOT_MOVED",
        "'Its parent ' || p.object_id || ' does not move'",
        None,
        "jsonb_build_object('parentId', p.object_id)",
    )
}
FROM mv_records p
WHERE c.parent_row = p.object_id AND p.selected AND p.outcome IN ('notMoved', 'refused')
    AND {_moving("c")}"""

_END_NOT_MOVED = _reason(
    "RECORD_NOT_MOVED",
    "'Its record ' || r.object_id || ' does not move'",
    None,
    "jsonb_build_object('objectId', r.object_id)",
)
_LEFT_BEHIND = _reason(
    "RELATION_TARGET_LEFT_BEHIND",
    "'It names ' || e.object_id || ', which is neither moved along nor in the target'",
    "select",
    "jsonb_build_object('objectId', e.object_id)",
)
_CONVERTED = "rdm_convert_value(e.value::json, p ->> 'fromType', p ->> 'toType')"

_STEPS_ENDS = (
    # ``missing: create``: the other end, neither selected nor in the target, created.
    f"""UPDATE mv_records e SET along = true, outcome = 'create',
        target_id = COALESCE(e.target_id, rdm_counterpart(:target, e.object_id))
    FROM mv_relations x JOIN mv_records r ON r.object_id IN (x.from_id, x.to_id)
    WHERE x.outcome IS NULL AND x.missing = 'create' AND e.object_id IN (x.from_id, x.to_id)
        AND e.object_id <> r.object_id AND r.selected AND {_moving("r")} AND NOT e.selected
        AND e.found IS NULL AND NOT e.along AND e.target_type IS NOT NULL""",
    # A selected end that does not move.
    f"""UPDATE mv_relations x SET outcome = 'notMoved', reasons = {_END_NOT_MOVED}
    FROM mv_records r
    WHERE x.outcome IS NULL AND r.object_id IN (x.from_id, x.to_id) AND r.selected
        AND NOT {_moving("r")}""",
    # An end neither moving nor in the target.
    f"""UPDATE mv_relations x SET outcome = 'notMoved', reasons = {_LEFT_BEHIND}
    FROM mv_records e
    WHERE x.outcome IS NULL AND e.object_id IN (x.from_id, x.to_id) AND NOT {_moving("e")}
        AND e.found IS NULL""",
    # The target's ends by the mapped direction.
    """UPDATE mv_relations x SET outcome = 'create',
        t_from = CASE WHEN x.direction = 'incoming' THEN t.target_id ELSE f.target_id END,
        t_to = CASE WHEN x.direction = 'incoming' THEN f.target_id ELSE t.target_id END,
        t_from_type = CASE WHEN x.direction = 'incoming' THEN t.target_type
            ELSE f.target_type END,
        t_to_type = CASE WHEN x.direction = 'incoming' THEN f.target_type ELSE t.target_type END
    FROM mv_records f, mv_records t
    WHERE x.outcome IS NULL AND f.object_id = x.from_id AND t.object_id = x.to_id""",
    # A relationship the target requires into a record it creates rides on that record's create.
    """UPDATE mv_relations x SET rider = r.object_id
    FROM mv_records r, mv_required q
    WHERE x.outcome = 'create' AND r.target_id = x.t_to AND r.outcome = 'create'
        AND q.relation = x.target_relation AND q.from_type = x.t_from_type
        AND q.to_type = x.t_to_type""",
    # Relation attributes, carried as attributes are.
    f"""UPDATE mv_relations x SET target_values = v.carried, left_behind = v.left_behind FROM (
        SELECT x.relation_id,
            COALESCE(jsonb_object_agg(p ->> 'target', {_CONVERTED}::jsonb)
                FILTER (WHERE p IS NOT NULL AND {_CONVERTED} IS NOT NULL), '{{}}') AS carried,
            COALESCE(jsonb_agg(jsonb_build_object(
                'code', CASE WHEN p IS NULL THEN 'ATTRIBUTE_NOT_MAPPED'
                    ELSE 'VALUE_NOT_CONVERTIBLE' END,
                'attributeTypeKey', e.key, 'pointer', '/attributes/' || {_escaped("e.key")},
                'value', e.value) ORDER BY e.key)
                FILTER (WHERE p IS NULL OR {_CONVERTED} IS NULL), '[]') AS left_behind
        FROM mv_relations x CROSS JOIN LATERAL jsonb_each(x.attributes) e
        LEFT JOIN LATERAL (SELECT q AS p FROM jsonb_array_elements(x.attrs) q
            WHERE q ->> 'source' = e.key) pair ON true
        WHERE x.outcome = 'create' AND jsonb_typeof(e.value) <> 'null'
        GROUP BY x.relation_id) v
    WHERE v.relation_id = x.relation_id""",
)

_STEPS_ORDER = (
    # Possible duplicates (I4): target records of the type and name a created record has.
    f"""UPDATE mv_records r SET duplicates = d.ids FROM (
        SELECT r.object_id, to_jsonb((array_agg(o.id ORDER BY o.id))[1:{NAMED_RECORDS}]) AS ids
        FROM mv_records r JOIN objects o ON o.workspace_key = :target
            AND o.object_type_key = r.target_type AND o.name = r.name AND o.id <> r.target_id
        WHERE r.outcome = 'create' GROUP BY r.object_id) d
    WHERE d.object_id = r.object_id""",
    # Each moving record's target parent.
    f"""UPDATE mv_records c SET target_parent_id = p.target_id FROM mv_records p
    WHERE c.parent_row = p.object_id AND {_moving("c")}
        AND (p.found IS NOT NULL OR {_moving("p")})""",
    # What a record waits for: its parent, and the records required relationships come from.
    f"""INSERT INTO mv_deps SELECT c.object_id, c.parent_row FROM mv_records c
    JOIN mv_records p ON p.object_id = c.parent_row WHERE {_moving("c")} AND {_moving("p")}""",
    f"""INSERT INTO mv_deps SELECT x.rider, e.object_id FROM mv_relations x
    JOIN mv_records e ON e.target_id = x.t_from AND {_moving("e")}
    WHERE x.rider IS NOT NULL AND x.outcome = 'create'""",
)

# A record's level is one more than the level of what it waits for; run until nothing changes.
_LEVEL = """UPDATE mv_records c SET level = s.level FROM (
    SELECT d.child, max(p.level) + 1 AS level FROM mv_deps d
    JOIN mv_records p ON p.object_id = d.parent GROUP BY d.child) s
WHERE s.child = c.object_id AND s.level > c.level"""

_STEPS_ROWS = (
    """UPDATE mv_records r SET row_index = n.i FROM (
        SELECT object_id, row_number() OVER (ORDER BY level, source_type NULLS FIRST, name,
            object_id) - 1 AS i
        FROM mv_records WHERE selected OR along) n
    WHERE n.object_id = r.object_id""",
    """UPDATE mv_relations x SET row_index = n.i FROM (
        SELECT relation_id, (SELECT count(*) FROM mv_records WHERE row_index IS NOT NULL)
            + row_number() OVER (ORDER BY relation_type, from_id, to_id, relation_id) - 1 AS i
        FROM mv_relations) n
    WHERE n.relation_id = x.relation_id""",
)

_RECORD_ROW = """(jsonb_strip_nulls(jsonb_build_object('kind', 'record',
        'sourceId', CASE WHEN r.source_type IS NULL THEN NULL ELSE r.object_id END,
        'sourceType', r.source_type, 'name', r.name, 'selected', r.selected,
        'targetId', r.target_id, 'targetType', r.target_type,
        'outcome', CASE WHEN r.found = 'origin' THEN 'updateOriginal' ELSE r.outcome END,
        'foundBy', CASE WHEN r.recreated THEN 'origin' ELSE r.found END,
        'origin', CASE WHEN r.outcome = 'create' AND NOT r.recreated AND r.source_type IS NOT NULL
            THEN jsonb_build_object('workspaceKey', CAST(:source AS text), 'objectId', r.object_id)
            END,
        'matchedBy', r.matched, 'targetParentId', r.target_parent_id,
        'parentRow', p.row_index, 'possibleDuplicates', r.duplicates))
    || jsonb_build_object('reasons', r.reasons, 'leftBehind', r.left_behind))"""

_RECORD_ITEM = """CASE r.outcome
    WHEN 'create' THEN jsonb_build_object('op', 'create', 'ref', r.row_index::text,
        'id', r.target_id, 'applicationKey', r.target_app, 'objectTypeKey', r.target_type,
        'name', r.name, 'attributes', a.list, 'initialRelations', COALESCE(i.list, '[]'))
        || CASE WHEN r.target_parent_id IS NOT NULL
            THEN jsonb_build_object('parent', jsonb_build_object('id', r.target_parent_id))
            ELSE '{}' END
    ELSE jsonb_build_object('op', 'update', 'ref', r.row_index::text,
        'target', jsonb_build_object('id', r.target_id), 'expectedVersion', r.target_version,
        'name', r.name, 'attributes', a.list)
        || CASE WHEN r.set_parent THEN jsonb_build_object('parent',
            CASE WHEN r.target_parent_id IS NULL THEN 'null'::jsonb
                ELSE jsonb_build_object('id', r.target_parent_id) END)
            ELSE '{}' END END"""

_INSERT_RECORDS = (
    f"""INSERT INTO job_inputs (job_id, item_index, ref, item)
    SELECT :job, r.row_index, r.row_index::text,
        jsonb_build_object('item', {_RECORD_ITEM}, 'row', {_RECORD_ROW},
            'sourceVersion', r.source_version)::json
    FROM mv_records r LEFT JOIN mv_records p ON p.object_id = r.parent_row
    CROSS JOIN LATERAL (SELECT COALESCE(jsonb_agg(jsonb_build_object('attributeTypeKey', k,
        'value', v) ORDER BY k), '[]') AS list FROM jsonb_each(r.target_values) kv(k, v)) a
    -- The relationships riding on each create, collected once: read per record, they scanned
    -- every relationship for every record (0.11 X5: 63 s for 11,000 records).
    LEFT JOIN (SELECT x.rider, jsonb_agg(jsonb_build_object(
            'relationTypeKey', x.target_relation, 'direction', 'incoming',
            'object', jsonb_build_object('id', x.t_from), 'attributes', x.target_values)
            ORDER BY x.relation_id) AS list
        FROM mv_relations x WHERE x.rider IS NOT NULL AND x.outcome = 'create'
        GROUP BY x.rider) i ON i.rider = r.object_id
    WHERE r.row_index IS NOT NULL AND {_moving("r")}""",
    f"""INSERT INTO job_items (job_id, item_index, ref, status, outcome)
    SELECT :job, r.row_index, r.row_index::text,
        CASE r.outcome WHEN 'refused' THEN 'rejected' ELSE 'unprocessed' END,
        {_RECORD_ROW}::json
    FROM mv_records r LEFT JOIN mv_records p ON p.object_id = r.parent_row
    WHERE r.row_index IS NOT NULL AND NOT {_moving("r")}""",
)

_RELATION_ROW = """(jsonb_strip_nulls(jsonb_build_object('kind', 'relationship',
        'relationId', x.relation_id, 'relationTypeKey', x.relation_type,
        'fromId', x.from_id, 'toId', x.to_id, 'targetRelationTypeKey', x.target_relation,
        'direction', x.direction, 'targetFromId', x.t_from, 'targetToId', x.t_to,
        'outcome', x.outcome, 'sourceType', f.source_type, 'rides', rr.row_index,
        'endRows', (SELECT jsonb_agg(e.row_index) FROM mv_records e
            WHERE e.object_id IN (x.from_id, x.to_id) AND e.row_index IS NOT NULL)))
    || jsonb_build_object('reasons', x.reasons, 'leftBehind', x.left_behind))"""

_INSERT_RELATIONS = (
    f"""INSERT INTO job_inputs (job_id, item_index, ref, item)
    SELECT :job, x.row_index, x.row_index::text, (CASE WHEN x.rider IS NULL
        THEN jsonb_build_object('item', jsonb_build_object('op', 'ensureRelation',
            'ref', x.row_index::text, 'from', jsonb_build_object('id', x.t_from),
            'to', jsonb_build_object('id', x.t_to), 'relationTypeKey', x.target_relation,
            'attributes', x.target_values))
        ELSE jsonb_build_object('rides', rr.row_index) END
        || jsonb_build_object('row', {_RELATION_ROW}))::json
    FROM mv_relations x LEFT JOIN mv_records f ON f.object_id = x.from_id
    LEFT JOIN mv_records rr ON rr.object_id = x.rider
    WHERE x.outcome = 'create'""",
    f"""INSERT INTO job_items (job_id, item_index, ref, status, outcome)
    SELECT :job, x.row_index, x.row_index::text, 'unprocessed', {_RELATION_ROW}::json
    FROM mv_relations x LEFT JOIN mv_records f ON f.object_id = x.from_id
    LEFT JOIN mv_records rr ON rr.object_id = x.rider
    WHERE x.outcome = 'notMoved'""",
)


@dataclass
class MovePlan:
    """The mapping as the binding's small tables (rows of plain values)."""

    types: list[dict[str, Any]] = field(default_factory=list)
    target_types: list[dict[str, Any]] = field(default_factory=list)
    attributes: list[dict[str, Any]] = field(default_factory=list)
    defaults: list[dict[str, Any]] = field(default_factory=list)
    value_maps: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    required: list[dict[str, Any]] = field(default_factory=list)


def plan_move(definition: dict[str, Any], source: Side, target: Side) -> MovePlan:
    """What the mapping says, entry by entry, against the two releases the move runs under; a
    mapping with problems against them is refused before (``move_job``)."""
    plan = MovePlan()
    for application in target.model.applications:
        for type_key in application.objectTypeKeys:
            if type_key not in {row["type_key"] for row in plan.target_types}:
                plan.target_types.append({"type_key": type_key, "app": application.key})
    for entry in definition.get("types") or []:
        source_type, target_type = entry["source"], entry["target"]
        match = entry.get("match") or {}
        parent = entry.get("parent") or {}
        plan.types.append(
            {
                "source_type": source_type,
                "target_type": target_type,
                "match_attr": match.get("attributeTypeKey"),
                "match_name": match.get("field") == "name",
                "parent_kind": "source"
                if parent.get("from") == "source"
                else "fixed"
                if parent.get("objectTypeKey")
                else None,
                "parent_type": parent.get("objectTypeKey"),
                "parent_value": parent.get("value"),
                "parent_missing": parent.get("missing"),
            }
        )
        plan.attributes += _attributes(entry, source, target)
        for name, value in (entry.get("defaults") or {}).items():
            plan.defaults.append(
                {"source_type": source_type, "target_attr": name, "value": json.dumps(value)}
            )
        for item in entry.get("relations") or []:
            pairs = [
                {
                    "source": pair["source"],
                    "target": pair["target"],
                    "fromType": source.value_type(pair["source"]),
                    "toType": target.value_type(pair["target"]),
                }
                for pair in item.get("attributes") or []
            ]
            plan.relations.append(
                {
                    "source_type": source_type,
                    "relation": item["source"],
                    "target_relation": item["target"],
                    "direction": item.get("direction", "outgoing"),
                    "missing": item.get("missing"),
                    "attrs": json.dumps(pairs),
                }
            )
    for name, values in (definition.get("valueMaps") or {}).items():
        for key, value in (values or {}).items():
            plan.value_maps.append({"name": name, "source": key, "value": json.dumps(value)})
    for binding in target.model.objectTypeRelations:
        if binding.required and binding.relationTypeKey not in (
            target.model.containment_relation_keys(binding.toObjectTypeKey)
        ):
            plan.required.append(
                {
                    "relation": binding.relationTypeKey,
                    "from_type": binding.fromObjectTypeKey,
                    "to_type": binding.toObjectTypeKey,
                }
            )
    return plan


def _attributes(entry: dict[str, Any], source: Side, target: Side) -> list[dict[str, Any]]:
    """Each source attribute the type binds, with what the mapping does with it: carried (into a
    target attribute the target type does not hold read-only), ignored, read-only in the target,
    or an effective period's bound the target type has no period for (I24). The period's bounds
    carry onto the target's period, with nothing to map, when both types declare one."""
    source_type, target_type = entry["source"], entry["target"]
    explicit = {item["source"]: item for item in entry.get("attributes") or []}
    rows: dict[str, dict[str, Any]] = {}
    for attribute, item in explicit.items():
        row = {"source_type": source_type, "source_attr": attribute, "value_map": None}
        if item.get("ignore"):
            rows[attribute] = {**row, "status": "ignore"}
            continue
        binding = target.binding(target_type, item["target"])
        rows[attribute] = {
            **row,
            "from_type": source.value_type(attribute),
            "target_attr": item["target"],
            "to_type": target.value_type(item["target"]),
            "value_map": item.get("valueMap"),
            "status": "readOnly" if binding is not None and binding.readOnly else "carry",
        }
    source_definition = source.model.object_type(source_type)
    target_definition = target.model.object_type(target_type)
    source_period = source_definition.effectivePeriod if source_definition else None
    target_period = target_definition.effectivePeriod if target_definition else None
    if source_period is not None:
        bounds = (
            (
                (source_period.startAttributeTypeKey, target_period.startAttributeTypeKey),
                (source_period.endAttributeTypeKey, target_period.endAttributeTypeKey),
            )
            if target_period is not None
            else (
                (source_period.startAttributeTypeKey, None),
                (source_period.endAttributeTypeKey, None),
            )
        )
        for attribute, onto in bounds:
            if attribute in rows:
                continue
            rows[attribute] = (
                {
                    "source_type": source_type,
                    "source_attr": attribute,
                    "from_type": source.value_type(attribute),
                    "target_attr": onto,
                    "to_type": target.value_type(onto),
                    "value_map": None,
                    "status": "carry",
                }
                if onto is not None
                else {
                    "source_type": source_type,
                    "source_attr": attribute,
                    "value_map": None,
                    "status": "period",
                }
            )
    return [
        {"from_type": None, "target_attr": None, "to_type": None, **row} for row in rows.values()
    ]


@dataclass(frozen=True)
class Bound:
    """What binding found: the rows the mapping decided, and the inputs the preview runs."""

    rows: int
    decided: int


def bind_move(
    session: Session,
    job: Job,
    plan: MovePlan,
    *,
    source: Side,
    selection: MoveSelection,
    source_workspace: str,
    context: SnapshotContext | None,
) -> Bound:
    """Write the move's rows: those the mapping decides as the job's outcomes, the others as its
    inputs. The caller commits."""
    for statement in _TABLES:
        session.execute(text(statement))
    _fill(session, "mv_types", plan.types)
    _fill(session, "mv_target_types", plan.target_types)
    _fill(session, "mv_attrs", plan.attributes)
    _fill(session, "mv_defaults", plan.defaults, jsonb=("value",))
    _fill(session, "mv_value_maps", plan.value_maps, jsonb=("value",))
    _fill(session, "mv_rel_map", plan.relations, jsonb=("attrs",))
    _fill(session, "mv_required", plan.required)
    _read(session, source, selection, source_workspace, context)

    target = {"target": job.workspace_key}
    for statement in _STEPS_RECORDS + _STEPS_PARENTS + _STEPS_RELATIONS:
        session.execute(text(statement), target)
    _until_settled(session, _CASCADE)
    for statement in _STEPS_ENDS + _STEPS_ORDER:
        session.execute(text(statement), target)
    _until_settled(session, _LEVEL)
    for statement in _STEPS_ROWS:
        session.execute(text(statement))
    parameters = {"job": job.sequence_id}
    for statement in _INSERT_RECORDS:
        session.execute(text(statement), {**parameters, "source": source_workspace})
    for statement in _INSERT_RELATIONS:
        session.execute(text(statement), parameters)
    rows, decided = session.execute(
        text(
            "SELECT (SELECT count(*) FROM mv_records WHERE row_index IS NOT NULL)"
            " + (SELECT count(*) FROM mv_relations),"
            " (SELECT count(*) FROM job_items WHERE job_id = :job)"
        ),
        parameters,
    ).one()
    return Bound(rows, decided)


def _fill(
    session: Session, name: str, rows: Iterable[dict[str, Any]], jsonb: tuple[str, ...] = ()
) -> None:
    rows = list(rows)
    if not rows:
        return
    columns = list(rows[0])
    values = ", ".join(f"CAST(:{key} AS jsonb)" if key in jsonb else f":{key}" for key in columns)
    session.execute(text(f"INSERT INTO {name} ({', '.join(columns)}) VALUES ({values})"), rows)


def _read(
    session: Session,
    source: Side,
    selection: MoveSelection,
    workspace_key: str,
    context: SnapshotContext | None,
) -> None:
    """The selected records, every relationship they hold, and the records those relationships
    and their parents name."""
    records = record_source(workspace_key, context, None)
    chosen = selected_ids(source.model, selection, workspace_key, context)
    statement = select(
        records.c.object_id,
        literal(True),
        records.c.object_type_key,
        records.c.name,
        records.c.parent_object_id,
        cast(records.c.attributes, JSONB),
        records.c.version,
    )
    if chosen is not None:
        # The selection read once into a keyed set: as `IN (the selection's query)`, PostgreSQL
        # ran the query again for every record when its estimates were off, as just after the
        # records were written (0.11 X5: 4 s of a 2,000-record dry run).
        session.execute(
            text("CREATE TEMPORARY TABLE mv_chosen (object_id text PRIMARY KEY) ON COMMIT DROP")
        )
        picked = chosen.subquery()
        session.execute(
            insert(table("mv_chosen", column("object_id"))).from_select(
                ["object_id"], select(next(iter(picked.c))).distinct()
            )
        )
        session.execute(text("ANALYZE mv_chosen"))
        statement = statement.where(
            records.c.object_id.in_(select(column("object_id")).select_from(table("mv_chosen")))
        )
    session.execute(
        insert(_RECORDS).from_select(
            [
                "object_id",
                "selected",
                "source_type",
                "name",
                "parent_id",
                "attributes",
                "source_version",
            ],
            statement,
        )
    )
    containment = sorted(source.containment)
    relations = relation_source(context)
    held = select(column("object_id")).select_from(table("mv_records"))
    session.execute(
        insert(_RELATIONS).from_select(
            ["relation_id", "relation_type", "from_id", "to_id", "attributes"],
            select(
                relations.c.relation_id,
                relations.c.relation_type_key,
                relations.c.from_object_id,
                relations.c.to_object_id,
                cast(relations.c.attributes, JSONB),
            ).where(
                relations.c.from_object_id.in_(held) | relations.c.to_object_id.in_(held),
                relations.c.relation_type_key.not_in(containment),
            ),
        )
    )
    others = record_source(workspace_key, context, None)
    named = text(
        "SELECT parent_id FROM mv_records WHERE parent_id IS NOT NULL"
        " UNION SELECT from_id FROM mv_relations UNION SELECT to_id FROM mv_relations"
    ).columns(column("parent_id"))
    session.execute(
        insert(_RECORDS).from_select(
            [
                "object_id",
                "selected",
                "source_type",
                "name",
                "parent_id",
                "attributes",
                "source_version",
            ],
            select(
                others.c.object_id,
                literal(False),
                others.c.object_type_key,
                others.c.name,
                others.c.parent_object_id,
                cast(others.c.attributes, JSONB),
                others.c.version,
            ).where(
                others.c.object_id.in_(named.subquery().select()),
                others.c.object_id.not_in(held),
            ),
        )
    )


def _until_settled(session: Session, statement: str) -> None:
    """Run ``statement`` until it changes nothing: once per level of the hierarchy it walks."""
    for _level in range(MAX_LEVELS):
        if session.execute(text(statement)).rowcount == 0:  # type: ignore[attr-defined]
            return
