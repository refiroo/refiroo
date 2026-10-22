"""A change set moved onto the release its workspace runs (Base 0.11 V3, D87–D96, API.md).

A change set left on a release its workspace no longer runs (ADR-028, D26) cannot publish. Moving
it is a ``migration`` job naming the change set (``parameters.moves: "changeSet"``), whose target is
the workspace's release (D87). It reuses V1's plan (``migrations.load_plan``: what each type
becomes, where each value goes and in which value type, which relationships keep a place) and
V1's preview, confirmation and outcomes, applied to the change set instead of live data:

- **The change set's own rows are converted** (D88): each value by D69's pairs, a record of a mapped
  type reclassified, and what the target has no place for listed as loss (D90): a value without a
  binding or that does not convert, a record the change set created of a type the target lacks with
  what it contains, a relationship of a pair the target lacks.
- **Its base becomes a capture of live data as it is now**, which already runs the target; its old
  base (a private capture or a publication) cannot be read under the target. A row's version moves
  with it, so a publication still raises every record's version.
- **A change it made conflicts by content** (D89): a record or relationship it changed or deleted
  is refused as ``CHANGE_SET_CONFLICT`` when live data differs from its old base converted by the
  same plan, and a relationship set it changed as ``MAPPING_SET_CHANGED`` when its live edges differ
  from its old base's. The workspace's own migration raised versions without changing anything
  else, so a version check would refuse every record it converted.
- **Every rule** the moved change set breaks under the target is refused, by the change set's own
  whole-graph validation (``graph_diagnostics``, the recorded exception publishing shares).

The preview applies the move under a savepoint, lists every item, and rolls back. The confirmation
binds the change set's version, the workspace's assignment version and its feed position (D92); the
execution applies the move again, checks that it still has no refusal and the reviewed counts, and
records one ``model-release-changed`` event on the change set (D94). Live data, the workspace's
release, its feed and its publications are never written.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import (
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    Job,
    ModelRelease,
    Workspace,
)
from ...models.schema import EngineModel
from ..change_sets.access import effective_change_set_membership
from ..change_sets.validation import graph_diagnostics
from ..indexes import matrix_states
from ..indexes.snapshot_values import copy_live, delete_owner_values, reindex_change_set
from ..jobs.store import LeaseLost, await_confirmation, complete_job, start_job
from ..records.audit import record_audit_event
from .migrations import (
    COUNTS,
    OUTCOMES,
    installed_release,
    load_plan,
    parse_type_mappings,
    plan_migration,
    publication_refusal_items,
    record_summary,
    require_reviewed,
)
from .registry import resolve_pinned_release
from .workspace_models import load_assignment

logger = logging.getLogger(__name__)

# --- the tables a move works through ---------------------------------------------------------

_TABLES = """
CREATE TEMPORARY TABLE move_base_objects (
    object_id varchar(36) PRIMARY KEY, application_key text, object_type_key text, name text,
    parent_object_id varchar(36), attributes json, version integer
) ON COMMIT DROP;
CREATE TEMPORARY TABLE move_base_relations (
    relation_id varchar(36) PRIMARY KEY, relation_type_key text, from_object_id varchar(36),
    to_object_id varchar(36), attributes json, version integer
) ON COMMIT DROP;
CREATE TEMPORARY TABLE move_objects (
    object_id varchar(36) PRIMARY KEY, application_key text, object_type_key text,
    target_application_key text, target_type_key text, name text, parent_object_id varchar(36),
    version integer, attributes json, deleted boolean, base_version integer, lost_code text,
    conflict boolean NOT NULL DEFAULT false
) ON COMMIT DROP;
CREATE INDEX move_objects_parent ON move_objects (parent_object_id);
CREATE TEMPORARY TABLE move_ends (
    object_id varchar(36) PRIMARY KEY, object_type_key text, lost boolean
) ON COMMIT DROP;
CREATE TEMPORARY TABLE move_relations (
    relation_id varchar(36) PRIMARY KEY, relation_type_key text, from_object_id varchar(36),
    to_object_id varchar(36), from_type text, to_type text, attributes json, version integer,
    deleted boolean, base_version integer, containment boolean, refused boolean, lost_code text,
    conflict boolean NOT NULL DEFAULT false
) ON COMMIT DROP;
CREATE TEMPORARY TABLE move_value_changes (
    object_id varchar(36), attribute_type_key text, target_key text, to_type text, before json,
    after json, outcome text, code text, PRIMARY KEY (object_id, attribute_type_key)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE move_relation_changes (
    relation_id varchar(36), attribute_type_key text, before json, after json, outcome text,
    code text, PRIMARY KEY (relation_id, attribute_type_key)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE move_set_conflicts (
    anchor_object_id varchar(36), relation_type_key text, direction text
) ON COMMIT DROP;
"""

# The change set's old base: a private capture (``:base``) or a publication (``:publication``).
_BASE_OBJECTS = """
    SELECT object_id, application_key, object_type_key, name, parent_object_id, attributes, version
    FROM change_set_base_objects WHERE base_id = CAST(:base AS varchar)
    UNION ALL
    SELECT object_id, application_key, object_type_key, name, parent_object_id, attributes, version
    FROM publication_objects WHERE publication_id = CAST(:publication AS varchar)
"""
_BASE_RELATIONS = """
    SELECT relation_id, relation_type_key, from_object_id, to_object_id, attributes, version
    FROM change_set_base_relations WHERE base_id = CAST(:base AS varchar)
    UNION ALL
    SELECT relation_id, relation_type_key, from_object_id, to_object_id, attributes, version
    FROM publication_relations WHERE publication_id = CAST(:publication AS varchar)
"""

# A JSON ``attributes`` map converted by the plan for records of type ``{type}``: the values that
# keep a place, under their target keys and in their target types; nulls left out.
_CONVERTED = """(
    SELECT coalesce(jsonb_object_agg(p.target_key,
        rdm_convert_value(e.value::json, vt.value_type, p.to_type)::jsonb)
        FILTER (WHERE p.target_key IS NOT NULL), '{{}}'::jsonb)
    FROM jsonb_each({attributes}::jsonb) e
    LEFT JOIN migration_values p ON p.object_type_key = {type} AND p.attribute_type_key = e.key
    LEFT JOIN migration_value_types vt ON vt.attribute_type_key = e.key
    WHERE jsonb_typeof(e.value) <> 'null'
)"""

_LIVE_VALUES = """(
    SELECT coalesce(jsonb_object_agg(a.attribute_type_key, rdm_value_json(a.value_type,
        a.text_value, a.integer_value, a.decimal_value, a.boolean_value, a.date_value,
        a.datetime_value, a.json_value)::jsonb), '{}'::jsonb)
    FROM attribute_values a WHERE a.object_id = l.id
)"""

_FILL = (
    # The old base's rows the change set changed or names as an end.
    f"""
    INSERT INTO move_base_objects
    SELECT b.* FROM ({_BASE_OBJECTS}) b
    WHERE b.object_id IN (
        SELECT object_id FROM change_set_objects WHERE change_set_id = :change_set
        UNION SELECT from_object_id FROM change_set_relations WHERE change_set_id = :change_set
        UNION SELECT to_object_id FROM change_set_relations WHERE change_set_id = :change_set
    )
    """,
    f"""
    INSERT INTO move_base_relations
    SELECT b.* FROM ({_BASE_RELATIONS}) b
    WHERE b.relation_id IN (
        SELECT relation_id FROM change_set_relations WHERE change_set_id = :change_set
    )
    """,
    # Every record row of the change set with its fate: its new type and application, or why it
    # is lost.
    """
    INSERT INTO move_objects
    SELECT c.object_id, c.application_key, c.object_type_key, t.target_application_key,
        t.target_type_key, c.name, c.parent_object_id, c.version, c.attributes, c.is_deleted,
        b.version,
        CASE WHEN t.target_type_key IS NULL THEN coalesce(t.code, 'OBJECT_TYPE_IN_USE') END, false
    FROM change_set_objects c
    LEFT JOIN move_base_objects b ON b.object_id = c.object_id
    LEFT JOIN migration_types t
        ON t.application_key = c.application_key AND t.object_type_key = c.object_type_key
    WHERE c.change_set_id = :change_set
    """,
    # What a lost record of the change set contains in it is lost with it.
    """
    WITH RECURSIVE lost AS (
        SELECT object_id FROM move_objects WHERE lost_code IS NOT NULL AND NOT deleted
        UNION
        SELECT child.object_id FROM move_objects child
        JOIN lost ON child.parent_object_id = lost.object_id
        WHERE NOT child.deleted
    )
    UPDATE move_objects m SET lost_code = 'PARENT_REMOVED'
    FROM lost WHERE m.object_id = lost.object_id AND m.lost_code IS NULL
    """,
    # Each end a relationship of the change set can name: its type in the current model and
    # whether it is lost.
    """
    INSERT INTO move_ends
    SELECT object_id, object_type_key, lost_code IS NOT NULL FROM move_objects
    UNION ALL
    SELECT b.object_id, b.object_type_key, t.target_type_key IS NULL
    FROM move_base_objects b
    LEFT JOIN migration_types t
        ON t.application_key = b.application_key AND t.object_type_key = b.object_type_key
    WHERE NOT EXISTS (SELECT 1 FROM move_objects o WHERE o.object_id = b.object_id)
    """,
    # Every relationship row of the change set with its fate, as V1's: a containment edge whose
    # child stays but which the target has no place for is refused, never lost.
    """
    INSERT INTO move_relations
    SELECT r.relation_id, r.relation_type_key, r.from_object_id, r.to_object_id,
        f.object_type_key, t.object_type_key, r.attributes, r.version, r.is_deleted, b.version,
        coalesce(p.containment, false),
        NOT r.is_deleted AND coalesce(p.containment, false) AND NOT t.lost AND NOT f.lost
            AND NOT coalesce(p.kept AND p.parent_kept, false),
        CASE
            WHEN coalesce(p.containment, false) AND NOT t.lost AND NOT f.lost THEN NULL
            WHEN NOT coalesce(p.kept, false) THEN 'RELATION_PAIR_IN_USE'
            WHEN f.lost OR t.lost THEN 'RELATION_END_REMOVED'
        END,
        false
    FROM change_set_relations r
    JOIN move_ends f ON f.object_id = r.from_object_id
    JOIN move_ends t ON t.object_id = r.to_object_id
    LEFT JOIN move_base_relations b ON b.relation_id = r.relation_id
    LEFT JOIN migration_pairs p ON p.relation_type_key = r.relation_type_key
        AND p.from_type = f.object_type_key AND p.to_type = t.object_type_key
    WHERE r.change_set_id = :change_set
    """,
    # Each value of a staying record row: carried as it is, converted, carried to another
    # attribute, or lost because it has no place or does not convert (D69).
    """
    INSERT INTO move_value_changes
    SELECT object_id, attribute_type_key, target_key, to_type, before, after,
        CASE WHEN after IS NULL THEN 'loss' ELSE 'conversion' END,
        CASE
            WHEN target_key IS NULL THEN 'ATTRIBUTE_BINDING_IN_USE'
            WHEN after IS NULL THEN 'VALUE_NOT_CONVERTIBLE'
            WHEN from_type <> to_type THEN 'VALUE_CONVERTED'
            ELSE 'VALUE_CARRIED'
        END
    FROM (
        SELECT o.object_id, e.key AS attribute_type_key, p.target_key, p.to_type,
            vt.value_type AS from_type, e.value::json AS before,
            CASE WHEN p.target_key IS NOT NULL
                THEN rdm_convert_value(e.value::json, vt.value_type, p.to_type) END AS after
        FROM move_objects o
        CROSS JOIN LATERAL jsonb_each(o.attributes::jsonb) e
        LEFT JOIN migration_values p
            ON p.object_type_key = o.object_type_key AND p.attribute_type_key = e.key
        LEFT JOIN migration_value_types vt ON vt.attribute_type_key = e.key
        WHERE o.lost_code IS NULL AND NOT o.deleted AND jsonb_typeof(e.value) <> 'null'
    ) value
    WHERE target_key IS NULL OR after IS NULL OR from_type IS DISTINCT FROM to_type
        OR target_key <> attribute_type_key
    """,
    # Each value of a staying relationship row, as a record's.
    """
    INSERT INTO move_relation_changes
    SELECT relation_id, key, before, after,
        CASE WHEN after IS NULL THEN 'loss' ELSE 'conversion' END,
        CASE
            WHEN to_type_value IS NULL THEN 'RELATION_ATTRIBUTE_IN_USE'
            WHEN after IS NULL THEN 'VALUE_NOT_CONVERTIBLE'
            ELSE 'VALUE_CONVERTED'
        END
    FROM (
        SELECT r.relation_id, e.key, e.value::json AS before, p.to_type_value,
            a.value_type AS from_type,
            rdm_convert_value(e.value::json, a.value_type, p.to_type_value) AS after
        FROM move_relations r
        CROSS JOIN LATERAL jsonb_each(r.attributes::jsonb) e
        LEFT JOIN migration_relation_values p ON p.relation_type_key = r.relation_type_key
            AND p.from_type = r.from_type AND p.to_type = r.to_type AND p.attribute_type_key = e.key
        LEFT JOIN migration_value_types a ON a.attribute_type_key = e.key
        WHERE r.lost_code IS NULL AND NOT r.refused AND NOT r.deleted
            AND jsonb_typeof(e.value) <> 'null'
    ) value
    WHERE to_type_value IS NULL OR after IS NULL OR from_type IS DISTINCT FROM to_type_value
    """,
    # D89: a record the change set changed or deleted conflicts when live data differs from its
    # old base converted by the plan (absent when the plan loses it).
    f"""
    WITH expected AS (
        SELECT b.object_id, t.target_type_key, t.target_application_key, b.name,
            b.parent_object_id, {_CONVERTED.format(attributes="b.attributes", type="b.object_type_key")}
                AS attributes
        FROM move_base_objects b
        JOIN move_objects o ON o.object_id = b.object_id
        LEFT JOIN migration_types t
            ON t.application_key = b.application_key AND t.object_type_key = b.object_type_key
    ), live AS (
        SELECT l.id, l.object_type_key, l.application_key, l.name, l.parent_object_id,
            {_LIVE_VALUES} AS attributes
        FROM objects l JOIN expected x ON x.object_id = l.id
        WHERE l.workspace_key = :workspace
    )
    UPDATE move_objects m SET conflict = true
    FROM expected x LEFT JOIN live l ON l.id = x.object_id
    WHERE m.object_id = x.object_id AND CASE
        WHEN x.target_type_key IS NULL THEN l.id IS NOT NULL
        ELSE l.id IS NULL OR l.object_type_key <> x.target_type_key
            OR l.application_key <> x.target_application_key OR l.name <> x.name
            OR l.parent_object_id IS DISTINCT FROM x.parent_object_id
            OR jsonb_strip_nulls(l.attributes) <> jsonb_strip_nulls(x.attributes)
    END
    """,
    # The same for a relationship: its old base, kept or lost by the plan, against live data.
    """
    WITH expected AS (
        SELECT b.relation_id, b.relation_type_key, b.from_object_id, b.to_object_id,
            coalesce(p.kept, false) AND NOT f.lost AND NOT t.lost AS kept,
            (
                SELECT coalesce(jsonb_object_agg(e.key, rdm_convert_value(e.value::json,
                    vt.value_type, v.to_type_value)::jsonb)
                    FILTER (WHERE v.to_type_value IS NOT NULL), '{}'::jsonb)
                FROM jsonb_each(b.attributes::jsonb) e
                LEFT JOIN migration_relation_values v ON v.relation_type_key = b.relation_type_key
                    AND v.from_type = bf.object_type_key AND v.to_type = bt.object_type_key
                    AND v.attribute_type_key = e.key
                LEFT JOIN migration_value_types vt ON vt.attribute_type_key = e.key
                WHERE jsonb_typeof(e.value) <> 'null'
            ) AS attributes
        FROM move_base_relations b
        JOIN move_base_objects bf ON bf.object_id = b.from_object_id
        JOIN move_base_objects bt ON bt.object_id = b.to_object_id
        JOIN move_ends f ON f.object_id = b.from_object_id
        JOIN move_ends t ON t.object_id = b.to_object_id
        LEFT JOIN migration_pairs p ON p.relation_type_key = b.relation_type_key
            AND p.from_type = bf.object_type_key AND p.to_type = bt.object_type_key
    )
    UPDATE move_relations m SET conflict = true
    FROM expected x LEFT JOIN object_relations l ON l.id = x.relation_id
    WHERE m.relation_id = x.relation_id AND CASE
        WHEN NOT x.kept THEN l.id IS NOT NULL
        ELSE l.id IS NULL OR l.relation_type_key <> x.relation_type_key
            OR l.from_object_id <> x.from_object_id OR l.to_object_id <> x.to_object_id
            OR jsonb_strip_nulls(l.attributes::jsonb) <> jsonb_strip_nulls(x.attributes)
    END
    """,
    # D89 for a relationship set the change set changed (``MAPPING_SET_CHANGED``, as publishing
    # names it): its old base's edges the plan keeps against live data's edges.
    f"""
    INSERT INTO move_set_conflicts
    SELECT s.anchor_object_id, s.relation_type_key, s.direction
    FROM relation_set_versions s
    JOIN migration_pairs p ON p.relation_type_key = s.relation_type_key
        AND p.from_type = s.from_object_type_key AND p.to_type = s.to_object_type_key
        AND p.kept AND NOT p.containment
    WHERE s.change_set_id = :change_set
        AND coalesce((
            SELECT array_agg(b.relation_id ORDER BY b.relation_id)
            FROM ({_BASE_RELATIONS}) b
            WHERE b.relation_type_key = s.relation_type_key
                AND CASE WHEN s.direction = 'outgoing' THEN b.from_object_id
                    ELSE b.to_object_id END = s.anchor_object_id
        ), '{{}}') IS DISTINCT FROM coalesce((
            SELECT array_agg(l.id ORDER BY l.id)
            FROM object_relations l
            WHERE l.relation_type_key = s.relation_type_key
                AND CASE WHEN s.direction = 'outgoing' THEN l.from_object_id
                    ELSE l.to_object_id END = s.anchor_object_id
        ), '{{}}')
    """,
)

# The rows of a preview or an execution, in one order: type changes, values, relationship values,
# lost records, lost relationships, refused containment edges, conflicts.
_ROWS = """
INSERT INTO job_items (job_id, item_index, ref, status, outcome)
SELECT CAST(:job AS integer), row_number() OVER (ORDER BY rank, a, b) - 1, NULL,
    CASE WHEN outcome ->> 'outcome' = 'refused' THEN 'rejected' ELSE 'applied' END, outcome
FROM (
    SELECT 0 AS rank, object_id AS a, '' AS b, json_strip_nulls(json_build_object(
        'outcome', 'reclassified', 'code', 'RECORD_RECLASSIFIED', 'objectId', object_id,
        'objectName', name, 'objectTypeKey', object_type_key,
        'targetObjectTypeKey', target_type_key, 'applicationKey', application_key,
        'targetApplicationKey', target_application_key)) AS outcome
    FROM move_objects
    WHERE lost_code IS NULL AND NOT deleted AND (target_type_key <> object_type_key
        OR target_application_key <> application_key)
    UNION ALL
    SELECT 1, c.object_id, c.attribute_type_key, json_strip_nulls(json_build_object(
        'outcome', c.outcome, 'code', c.code, 'objectId', c.object_id, 'objectName', o.name,
        'objectTypeKey', o.object_type_key, 'attributeTypeKey', c.attribute_type_key,
        'targetAttributeTypeKey', CASE WHEN c.target_key <> c.attribute_type_key
            THEN c.target_key END,
        'before', c.before, 'after', c.after))
    FROM move_value_changes c JOIN move_objects o ON o.object_id = c.object_id
    UNION ALL
    SELECT 2, r.relation_id, c.attribute_type_key, json_strip_nulls(json_build_object(
        'outcome', c.outcome, 'code', c.code, 'objectId', r.from_object_id,
        'relationId', r.relation_id, 'relationTypeKey', r.relation_type_key,
        'toObjectId', r.to_object_id, 'attributeTypeKey', c.attribute_type_key,
        'before', c.before, 'after', c.after))
    FROM move_relation_changes c JOIN move_relations r ON r.relation_id = c.relation_id
    UNION ALL
    SELECT 3, object_id, '', json_build_object(
        'outcome', 'loss', 'code', lost_code, 'objectId', object_id, 'objectName', name,
        'objectTypeKey', object_type_key)
    FROM move_objects WHERE lost_code IS NOT NULL AND NOT deleted
    UNION ALL
    SELECT 4, relation_id, '', json_build_object(
        'outcome', 'loss', 'code', lost_code, 'objectId', from_object_id,
        'relationId', relation_id, 'relationTypeKey', relation_type_key,
        'toObjectId', to_object_id)
    FROM move_relations WHERE lost_code IS NOT NULL AND NOT containment AND NOT deleted
    UNION ALL
    SELECT 5, to_object_id, relation_id, json_build_object(
        'outcome', 'refused', 'code', 'PARENT_RELATION_SEMANTICS_CHANGED',
        'objectId', to_object_id, 'relationTypeKey', relation_type_key,
        'message', 'The target release has no place for this record under its parent')
    FROM move_relations WHERE refused
    UNION ALL
    SELECT 6, object_id, '', json_strip_nulls(json_build_object(
        'outcome', 'refused', 'code', 'CHANGE_SET_CONFLICT', 'objectId', object_id,
        'objectName', name, 'objectTypeKey', object_type_key,
        'message', 'The record changed in live data since the change set started'))
    FROM move_objects WHERE conflict
    UNION ALL
    SELECT 7, relation_id, '', json_build_object(
        'outcome', 'refused', 'code', 'CHANGE_SET_CONFLICT', 'objectId', from_object_id,
        'relationId', relation_id, 'relationTypeKey', relation_type_key,
        'toObjectId', to_object_id,
        'message', 'The relationship changed in live data since the change set started')
    FROM move_relations WHERE conflict
    UNION ALL
    SELECT 8, anchor_object_id, relation_type_key || direction, json_build_object(
        'outcome', 'refused', 'code', 'MAPPING_SET_CHANGED', 'objectId', anchor_object_id,
        'relationTypeKey', relation_type_key,
        'message', 'Relationships of this record changed in live data since the change set '
            'started')
    FROM move_set_conflicts
) rows
"""

# Refusals of the moved change set's validation, written back once its savepoint is rolled back.
_REFUSALS = """
INSERT INTO job_items (job_id, item_index, ref, status, outcome)
SELECT CAST(:job AS integer), CAST(:offset AS integer) + listed.position - 1, NULL, 'rejected',
    json_strip_nulls(json_build_object(
        'outcome', 'refused', 'code', listed.code, 'objectId', listed.object_id,
        'objectName', c.name, 'objectTypeKey', c.object_type_key,
        'relationId', listed.relation_id, 'message', listed.message))
FROM unnest(CAST(:ids AS text[]), CAST(:relations AS text[]), CAST(:codes AS text[]),
    CAST(:messages AS text[])) WITH ORDINALITY AS listed(object_id, relation_id, code, message,
    position)
LEFT JOIN change_set_objects c
    ON c.change_set_id = :change_set AND c.object_id = listed.object_id
"""

_APPLY = (
    # Rows the target has no place for, and deletions of what live data no longer holds.
    """
    DELETE FROM change_set_relations c USING move_relations m
    WHERE c.change_set_id = :change_set AND c.relation_id = m.relation_id
        AND (m.lost_code IS NOT NULL
            OR (m.deleted AND NOT EXISTS (SELECT 1 FROM object_relations l WHERE l.id = m.relation_id)))
    """,
    """
    DELETE FROM change_set_objects c USING move_objects m
    WHERE c.change_set_id = :change_set AND c.object_id = m.object_id
        AND ((m.lost_code IS NOT NULL AND NOT m.deleted)
            OR (m.deleted AND NOT EXISTS (
                SELECT 1 FROM objects l WHERE l.id = m.object_id
                    AND l.workspace_key = :workspace)))
    """,
    # A row's version keeps its distance from its base, now live data (D88).
    """
    UPDATE change_set_objects c SET version = c.version - m.base_version + l.version
    FROM move_objects m JOIN objects l ON l.id = m.object_id
    WHERE c.change_set_id = :change_set AND c.object_id = m.object_id
        AND m.base_version IS NOT NULL
    """,
    """
    UPDATE change_set_relations c SET version = c.version - m.base_version + l.version
    FROM move_relations m JOIN object_relations l ON l.id = m.relation_id
    WHERE c.change_set_id = :change_set AND c.relation_id = m.relation_id
        AND m.base_version IS NOT NULL
    """,
    # The record rows under their new type, with their values converted, carried or removed.
    """
    UPDATE change_set_objects c SET object_type_key = m.target_type_key,
        application_key = m.target_application_key,
        attributes = (
            SELECT coalesce(json_object_agg(coalesce(v.target_key, e.key),
                coalesce(v.after, e.value::json))
                FILTER (WHERE v.outcome IS DISTINCT FROM 'loss'
                    AND jsonb_typeof(e.value) <> 'null'), '{}'::json)
            FROM jsonb_each(c.attributes::jsonb) e
            LEFT JOIN move_value_changes v
                ON v.object_id = c.object_id AND v.attribute_type_key = e.key
        )
    FROM move_objects m
    WHERE c.change_set_id = :change_set AND c.object_id = m.object_id AND m.lost_code IS NULL
    """,
    """
    UPDATE change_set_relations c SET attributes = (
        SELECT coalesce(json_object_agg(e.key, coalesce(v.after, e.value::json))
            FILTER (WHERE v.outcome IS DISTINCT FROM 'loss' AND jsonb_typeof(e.value) <> 'null'),
            '{}'::json)
        FROM jsonb_each(c.attributes::jsonb) e
        LEFT JOIN move_relation_changes v
            ON v.relation_id = c.relation_id AND v.attribute_type_key = e.key
    )
    WHERE c.change_set_id = :change_set
        AND c.relation_id IN (SELECT relation_id FROM move_relation_changes)
    """,
    # The relationship sets it changed, named by the target's types, or gone with their pair.
    """
    DELETE FROM relation_set_versions s USING migration_pairs p
    WHERE s.change_set_id = :change_set AND p.relation_type_key = s.relation_type_key
        AND p.from_type = s.from_object_type_key AND p.to_type = s.to_object_type_key
        AND NOT p.kept
    """,
    """
    UPDATE relation_set_versions s SET
        from_object_type_key = coalesce((SELECT DISTINCT t.target_type_key FROM migration_types t
            WHERE t.object_type_key = s.from_object_type_key AND t.target_type_key IS NOT NULL
            LIMIT 1), s.from_object_type_key),
        to_object_type_key = coalesce((SELECT DISTINCT t.target_type_key FROM migration_types t
            WHERE t.object_type_key = s.to_object_type_key AND t.target_type_key IS NOT NULL
            LIMIT 1), s.to_object_type_key)
    WHERE s.change_set_id = :change_set
    """,
)


# --- submission ----------------------------------------------------------------------------------


def submit_change_set_migration(
    session: Session,
    change_set_id: str,
    *,
    expected_change_set_version: int,
    target_release_id: str | None,
    type_mappings: list[dict[str, Any]],
    retention_days: int,
) -> Job:
    """Queue the preview of a move of the change set onto the release its workspace runs. Refused
    before a job exists: no such change set (``404 CHANGE_SET_NOT_FOUND``), one changed since
    ``expected_change_set_version`` (``409 CHANGE_SET_VERSION_CONFLICT``), a retired workspace
    (``409 WORKSPACE_RETIRED``), a target other than the workspace's release (``422
    MIGRATION_TARGET_NOT_WORKSPACE_RELEASE``), a change set on it already (``422
    MIGRATION_TARGET_IS_CURRENT``), an unsupported schema, a mapping naming what the models lack."""
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "CHANGE_SET_NOT_FOUND", f"Change set '{change_set_id}' not found")
    if change_set.version != expected_change_set_version:
        raise api_error(
            409,
            "CHANGE_SET_VERSION_CONFLICT",
            "Change set version has changed",
            {"changeSetId": change_set.id, "currentVersion": change_set.version},
        )
    workspace = session.get(Workspace, change_set.workspace_key)
    if workspace.status != "active":
        raise api_error(
            409,
            "WORKSPACE_RETIRED",
            f"Workspace '{workspace.key}' is retired; its change sets are not moved",
            {"workspaceKey": workspace.key},
        )
    _assignment, runs = load_assignment(session, change_set.workspace_key)
    if target_release_id is not None and target_release_id != runs.public_id:
        raise api_error(
            422,
            "MIGRATION_TARGET_NOT_WORKSPACE_RELEASE",
            f"Workspace '{workspace.key}' runs release '{runs.public_id}'; a change set is moved "
            "onto the release its workspace runs",
            {
                "workspaceKey": workspace.key,
                "workspaceReleaseId": runs.public_id,
                "releaseId": target_release_id,
            },
        )
    target = installed_release(session, runs.public_id)
    pinned = session.get(ModelRelease, change_set.model_release_id)
    if pinned.id == target.id:
        raise api_error(
            422,
            "MIGRATION_TARGET_IS_CURRENT",
            f"Change set '{change_set.id}' works under release '{target.public_id}' already",
            {"changeSetId": change_set.id, "releaseId": target.public_id},
        )
    current_model = resolve_pinned_release(session, pinned.id, require_ready=False).model
    target_model = resolve_pinned_release(session, target.id).model
    plan_migration(current_model, target_model, parse_type_mappings(type_mappings))
    return start_job(
        session,
        kind="migration",
        workspace_key=change_set.workspace_key,
        change_set_id=change_set.id,
        model_release_id=pinned.id,
        parameters={
            "stage": "preview",
            "moves": "changeSet",
            "changeSetId": change_set.id,
            "targetReleaseId": target.public_id,
            "typeMappings": type_mappings,
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )


# --- preview and execution -----------------------------------------------------------------------


@dataclass
class _Move:
    session: Session
    job: Job
    change_set: ChangeSet
    current: EngineModel
    target: EngineModel
    target_release: ModelRelease

    @classmethod
    def open(cls, session: Session, job: Job) -> _Move:
        change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == job.change_set_id))
        if change_set is None:
            raise api_error(
                409,
                "MIGRATION_REVIEW_STALE",
                f"Change set '{job.change_set_id}' was published or discarded; nothing was moved",
                {"changeSetId": job.change_set_id},
            )
        target_release = installed_release(session, job.parameters["targetReleaseId"])
        return cls(
            session,
            job,
            change_set,
            resolve_pinned_release(session, job.model_release_id, require_ready=False).model,
            resolve_pinned_release(session, target_release.id).model,
            target_release,
        )

    @property
    def _params(self) -> dict[str, Any]:
        return {
            "change_set": self.change_set.id,
            "workspace": self.change_set.workspace_key,
            "base": self.change_set.base_id,
            "publication": self.change_set.derived_from_publication_id,
        }

    def prepare(self) -> None:
        """The plan into its tables, and every row, value and conflict of the change set."""
        session = self.session
        load_plan(
            session,
            self.current,
            self.target,
            parse_type_mappings(self.job.parameters["typeMappings"]),
        )
        session.execute(text(_TABLES))
        for statement in _FILL:
            session.execute(text(statement), self._params)
        session.execute(
            text("ANALYZE move_objects, move_relations, move_value_changes, move_base_objects")
        )

    def write_rows(self) -> int:
        return self.session.execute(text(_ROWS), {"job": self.job.sequence_id}).rowcount

    def apply(self, assignment_version: int) -> str | None:
        """Move the change set as planned: its rows converted, its base replaced by a capture of
        live data, its release the target. The old private base's ID, removed afterwards."""
        session = self.session
        change_set = self.change_set
        for statement in _APPLY:
            session.execute(text(statement), self._params)
        old_base = change_set.base_id
        base = ChangeSetBase(
            workspace_key=change_set.workspace_key,
            model_release_id=self.target_release.id,
            model_runtime_version=assignment_version,
        )
        session.add(base)
        session.flush()
        copy_live(session, "base", base.id, change_set.workspace_key)
        for owner in (
            matrix_states.Owner("change_set", change_set.id, change_set.workspace_key),
            *(
                [matrix_states.Owner("base", old_base, change_set.workspace_key)]
                if old_base is not None
                else []
            ),
        ):
            matrix_states.drop_owner(session, owner)
        change_set.base_id = base.id
        change_set.derived_from_publication_id = None
        change_set.model_release_id = self.target_release.id
        session.flush()
        reindex_change_set(session, change_set.id, self.target_release.id)
        if old_base is not None:
            delete_owner_values(session, old_base)
            for table, column in (
                (ChangeSetBaseRelation, ChangeSetBaseRelation.base_id),
                (ChangeSetBaseObject, ChangeSetBaseObject.base_id),
                (ChangeSetBase, ChangeSetBase.id),
            ):
                session.execute(
                    delete(table)
                    .where(column == old_base)
                    .execution_options(synchronize_session=False)
                )
        session.expire_all()
        matrix_states.record_change_set(session, self.change_set_row())
        return old_base

    def change_set_row(self) -> ChangeSet:
        return self.session.scalar(select(ChangeSet).where(ChangeSet.id == self.job.change_set_id))

    def refusals(self) -> list[tuple[str, str, str, str]]:
        """Every rule the moved change set breaks under the target, by its own validation."""
        self.session.flush()
        membership = effective_change_set_membership(self.session, self.job.change_set_id)
        return publication_refusal_items(
            graph_diagnostics(membership, self.target, apply_defaults=False)
        )

    def write_refusals(self, refused: list[tuple[str, str, str, str]], offset: int) -> None:
        if not refused:
            return
        ids = [
            item.removeprefix("object:") if not item.startswith("relation:") else None
            for item, _code, _path, _message in refused
        ]
        relations = [
            item.removeprefix("relation:") if item.startswith("relation:") else None
            for item, _code, _path, _message in refused
        ]
        self.session.execute(
            text(_REFUSALS),
            {
                "job": self.job.sequence_id,
                "offset": offset,
                "change_set": self.job.change_set_id,
                "ids": [item or None for item in ids],
                "relations": relations,
                "codes": [code for _item, code, _path, _message in refused],
                "messages": [message for _item, _code, _path, message in refused],
            },
        )

    def counts(self) -> dict[str, int]:
        found = dict(self.session.execute(text(COUNTS), {"job": self.job.sequence_id}).all())
        return {outcome: int(found.get(outcome, 0)) for outcome in OUTCOMES}


def run_preview(
    session: Session,
    job: Job,
    *,
    retention_days: int,
    hold: Callable[[], None],
    renew: Callable[[], None] = lambda: None,
) -> None:
    """Preview the move and, once ``hold`` (the worker's lease) allows, leave the job waiting for
    confirmation; the caller commits."""
    move = _Move.open(session, job)
    assignment, _runs = load_assignment(session, job.workspace_key)
    workspace = session.get(Workspace, job.workspace_key)
    reviewed = {
        "targetReleaseId": move.target_release.public_id,
        "currentReleaseId": session.get(ModelRelease, job.model_release_id).public_id,
        "expectedVersion": assignment.version,
        "feedPosition": int(workspace.feed_position or 0),
        "changeSetId": move.change_set.id,
        "changeSetVersion": move.change_set.version,
        "activePublicationId": workspace.active_publication_id,
    }
    move.prepare()
    renew()
    written = move.write_rows()
    renew()
    savepoint = session.begin_nested()
    try:
        move.apply(assignment.version)
        renew()
        refused = move.refusals()
    finally:
        savepoint.rollback()
        session.expire_all()
    renew()
    move.write_refusals(refused, written)
    record_summary(job, move.counts(), **reviewed)
    hold()
    await_confirmation(
        session, job, job.report["migration"], retention_days=retention_days, key="migration"
    )


def run_execution(
    session: Session,
    job: Job,
    *,
    retention_days: int,
    hold: Callable[[], None],
    renew: Callable[[], None] = lambda: None,
) -> None:
    """Execute a confirmed move in the caller's transaction, which commits it. A failure leaves
    nothing changed: the caller rolls back."""
    summary = (job.report or {}).get("migration", {})
    # Lock order (ARCHITECTURE): the workspace, then the change set. The workspace row held in
    # share mode keeps live writes, which take its feed positions, out until the move commits.
    session.execute(
        select(Workspace.key).where(Workspace.key == job.workspace_key).with_for_update(read=True)
    )
    session.execute(select(ChangeSet.id).where(ChangeSet.id == job.change_set_id).with_for_update())
    # The assignment held too, last in the lock order: an activation of the workspace waits for the
    # move, or the move sees it and is stale, never pinning the change set to a release the
    # workspace just left (0.11 R, R-F8).
    require_reviewed(
        session,
        job,
        reviewed_version=summary["expectedVersion"],
        reviewed_feed_position=summary["feedPosition"],
        summary=summary,
        for_update=True,
    )
    move = _Move.open(session, job)
    session.execute(text("DELETE FROM job_items WHERE job_id = :job"), {"job": job.sequence_id})
    move.prepare()
    renew()
    move.write_rows()
    renew()
    counts = move.counts()
    old_release = session.get(ModelRelease, move.change_set.model_release_id)
    version = move.change_set.version
    move.apply(summary["expectedVersion"])
    renew()
    if counts["refused"] or move.refusals() or counts != summary.get("counts"):
        raise api_error(
            409,
            "MIGRATION_REVIEW_STALE",
            f"Change set '{job.change_set_id}' no longer moves as the preview said; nothing was "
            "moved. Preview the move again",
            {"changeSetId": job.change_set_id, "reviewed": summary.get("counts"), "now": counts},
        )
    record_change_set_moved(session, move.change_set_row(), old_release, move, version, counts)
    record_summary(job, counts)
    hold()
    complete_job(session, job, retention_days=retention_days)


def execute(
    session: Session,
    job: Job,
    *,
    retention_days: int,
    hold: Callable[[], None],
    renew: Callable[[], None] = lambda: None,
) -> None:
    """Run a confirmed move and commit it once ``hold`` (the worker's lease) allows; any failure
    rolls back and becomes ``MIGRATION_FAILED`` (or the refusal it was), nothing changed."""
    try:
        run_execution(session, job, retention_days=retention_days, hold=hold, renew=renew)
    except ApiError:
        session.rollback()
        raise
    except LeaseLost:
        raise
    except Exception as exc:
        session.rollback()
        correlation_id = uuid4().hex
        logger.exception(
            "Move of change set %s (job %s) failed and changed nothing (correlation ID %s)",
            job.change_set_id,
            job.id,
            correlation_id,
        )
        raise api_error(
            500,
            "MIGRATION_FAILED",
            f"The move of change set '{job.change_set_id}' failed and changed nothing: the change "
            "set keeps its release and its content. Preview it again; if it fails again, report "
            "the correlation ID",
            {"changeSetId": job.change_set_id, "correlationId": correlation_id},
        ) from exc
    session.commit()


def record_change_set_moved(
    session: Session,
    change_set: ChangeSet,
    old_release: ModelRelease,
    move: _Move,
    version: int,
    counts: dict[str, int],
) -> None:
    """The change set's version raised once and its ``model-release-changed`` event naming the
    job and its counts (D94), as a version change records."""
    change_set.version = version + 1
    session.flush()

    def identity(item: ModelRelease) -> dict[str, str]:
        return {"id": item.public_id, "key": item.release_key, "version": item.release_version}

    record_audit_event(
        session,
        aggregate_type="change-set",
        aggregate_id=change_set.id,
        action="model-release-changed",
        version=change_set.version,
        changes={
            "modelRelease": {"from": identity(old_release), "to": identity(move.target_release)},
            "migrationJobId": move.job.id,
            "migrated": counts,
        },
        object_ids=(),
    )
