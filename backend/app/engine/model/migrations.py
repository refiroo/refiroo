"""A workspace's data migrated to another release (Base 0.11 V1, D68–D78, API.md).

A migration is a ``migration`` job of one workspace naming a target installed release, of the
workspace's model or another, and optionally what the current model's types became in it
(``typeMappings``, D70). It runs in two stages, as an import's preview does:

**Preview.** The plan (:func:`plan_migration`) decides, from the two models alone, what each
record's type becomes (or that its records are lost), where each attribute's values go and in which
value type, and which relationships keep a place. The job then writes, in PostgreSQL, every item
the plan changes as one row: a value converted (D69, ``rdm_convert_value``) or carried to another
attribute, a record whose type changes, and every loss: records of a type the target lacks with
what they contain, values without a place or that do not convert, relationships without a place
(D68). It then applies the migration under a savepoint and checks the result against the target
release in full, every rule a record can break (``compatibility.analyze_compatibility`` against
the target with its rules taken out, listing the records behind each count, D72), and rolls the
savepoint back. The refusals found, and the containment edges the target has no place for, become
rows too. Nothing has changed; the job waits for confirmation with its counts, the workspace's
assignment version and its feed position.

**Confirmation** (``POST /jobs/{id}/confirm``, :func:`check_confirmation`) binds the reviewed
assignment version and feed position (D74): a workspace written or activated since is
``MIGRATION_REVIEW_STALE``; refusals are ``MIGRATION_HAS_REFUSALS``; a loss needs ``acceptLoss``.
The worker then executes it in one transaction: it holds the workspace row and its assignment,
checks both again, recomputes the rows, applies the migration with an audit entry and feed position
for every record and relationship it changes (D73), checks again that nothing is refused and that
the counts are the reviewed ones, and switches the assignment as activation does
(``releases.switch_workspace_release``). A failure anywhere rolls everything back.

**A change set published with it** (V2, D79–D83). A migration may name an open change set of the
workspace pinned to a release the workspace no longer runs; the target is then that release. The
preview also merges the change set over the migrated data under the target, inside the same
savepoint, and lists what would stop its publication as refused rows: each record or relationship
changed both in the change set and live since its base (``CHANGE_SET_CONFLICT``) and each rule the
merged graph breaks. The confirmation binds the change set's version and the workspace's active
publication too, and the execution publishes the change set after the switch, in the same
transaction (``publish.apply_publication``).

The refusals of a preview leave its savepoint through Python, the one place a migration's data
passes through the process: they must survive the rollback, and no statement can carry rows past
it. They are bounded by what must be fixed before the migration can run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, select, text
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import ChangeSet, Job, ModelRelease, Workspace
from ...models.schema import EngineModel
from ..change_sets.publish import apply_publication, publication_findings
from ..indexes import matrix_states
from ..jobs.store import (
    LeaseLost,
    await_confirmation,
    complete_job,
    confirm_job,
    load_job,
    start_job,
)
from ..records.feed import take_positions
from ..records.values import WIDENINGS
from .compatibility import analyze_compatibility, is_parent_pair
from .compiler import SCHEMA_VERSIONS, SUPPORTED_SCHEMA_VERSIONS
from .consumer_contract import contract_diagnostics
from .registry import model_registry, resolve_pinned_release
from .releases import (
    ConsumerContractVersionRequired,
    lock_what_activation_changes,
    switch_workspace_release,
)
from .workspace_models import load_assignment

logger = logging.getLogger(__name__)

OUTCOMES = ("conversion", "reclassified", "loss", "refused")


# --- the plan ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeMapping:
    """What a type of the current model became in the target (D70): its records keep their IDs
    under ``to_type``; ``attributes`` names, for attributes of the new type, the attribute of the
    old type its values come from (``None``: none)."""

    from_type: str
    to_type: str
    attributes: tuple[tuple[str, str | None], ...] = ()


@dataclass
class MigrationPlan:
    """Rows of the plan's temporary tables, decided from the two models alone."""

    # (application, type, target application, target type, loss code)
    types: list[tuple[str, str, str | None, str | None, str | None]] = field(default_factory=list)
    # (type, attribute, target attribute or None, its value type or None)
    values: list[tuple[str, str, str | None, str | None]] = field(default_factory=list)
    # (relation type, from type, to type, kept, containment, parent kept)
    pairs: list[tuple[str, str, str, bool, bool, bool]] = field(default_factory=list)
    # (relation type, from type, to type, attribute, target value type or None)
    relation_values: list[tuple[str, str, str, str, str | None]] = field(default_factory=list)


def parse_type_mappings(raw: Sequence[dict[str, Any]]) -> tuple[TypeMapping, ...]:
    """The request's ``typeMappings`` in the plan's form."""
    return tuple(
        TypeMapping(
            item["fromObjectTypeKey"],
            item["toObjectTypeKey"],
            tuple(
                (attribute["attributeTypeKey"], attribute.get("from"))
                for attribute in item.get("attributes") or ()
            ),
        )
        for item in raw
    )


def _invalid(pointer: str, message: str) -> ApiError:
    return api_error(422, "INVALID_MIGRATION_MAPPING", message, {"pointer": pointer})


def plan_migration(
    current: EngineModel, target: EngineModel, mappings: Sequence[TypeMapping]
) -> MigrationPlan:
    """Decide the migration from ``current`` to ``target``. A mapping naming what neither model
    holds is ``422 INVALID_MIGRATION_MAPPING`` at its pointer into the request."""
    mapped: dict[str, TypeMapping] = {}
    for index, mapping in enumerate(mappings):
        at = f"/typeMappings/{index}"
        if current.object_type(mapping.from_type) is None:
            raise _invalid(
                f"{at}/fromObjectTypeKey",
                f"The workspace's model has no type '{mapping.from_type}'",
            )
        if mapping.from_type in mapped:
            raise _invalid(f"{at}/fromObjectTypeKey", f"Type '{mapping.from_type}' is mapped twice")
        new_type = target.object_type(mapping.to_type)
        if new_type is None:
            raise _invalid(
                f"{at}/toObjectTypeKey", f"The target release has no type '{mapping.to_type}'"
            )
        old_bound = {b.attributeTypeKey for b in current.object_type(mapping.from_type).attributes}
        new_bound = {b.attributeTypeKey for b in new_type.attributes}
        targets: set[str] = set()
        sources: set[str] = set()
        for position, (key, source) in enumerate(mapping.attributes):
            where = f"{at}/attributes/{position}"
            if key not in new_bound or key in targets:
                raise _invalid(
                    f"{where}/attributeTypeKey",
                    f"'{key}' is not an attribute of '{mapping.to_type}', or is named twice",
                )
            if source is not None and (source not in old_bound or source in sources):
                raise _invalid(
                    f"{where}/from",
                    f"'{source}' is not an attribute of '{mapping.from_type}', or is a source twice",
                )
            targets.add(key)
            if source is not None:
                sources.add(source)
        mapped[mapping.from_type] = mapping

    def becomes(type_key: str) -> str | None:
        if type_key in mapped:
            return mapped[type_key].to_type
        return type_key if target.object_type(type_key) is not None else None

    plan = MigrationPlan()
    target_apps = {item.key: item for item in target.applications}
    seen: set[tuple[str, str]] = set()
    for application in current.applications:
        for type_key in application.objectTypeKeys:
            if (application.key, type_key) in seen:
                continue
            seen.add((application.key, type_key))
            new_type = becomes(type_key)
            if new_type is None:
                plan.types.append((application.key, type_key, None, None, "OBJECT_TYPE_IN_USE"))
                continue
            same = target_apps.get(application.key)
            if same is not None and new_type in same.objectTypeKeys:
                plan.types.append((application.key, type_key, application.key, new_type, None))
                continue
            holders = [a.key for a in target.applications if new_type in a.objectTypeKeys]
            if type_key in mapped and len(holders) == 1:
                plan.types.append((application.key, type_key, holders[0], new_type, None))
            else:
                code = "APPLICATION_IN_USE" if same is None else "APPLICATION_OBJECT_TYPE_IN_USE"
                plan.types.append((application.key, type_key, None, None, code))

    for object_type in current.objectTypes:
        new_key = becomes(object_type.key)
        new_type = target.object_type(new_key) if new_key else None
        old_bound = {b.attributeTypeKey for b in object_type.attributes}
        if new_type is None:
            continue
        chosen = dict(mapped[object_type.key].attributes) if object_type.key in mapped else {}
        claimed: dict[str, str] = {}
        for binding in new_type.attributes:
            key = binding.attributeTypeKey
            if key in chosen:
                source = chosen[key]
            elif key in old_bound and key not in claimed:
                source = key
            else:
                source = None
            if source is not None and source not in claimed:
                claimed[source] = key
        # ADR-034's display rule for a type that changes: display attribute to display attribute,
        # when nothing else took either and the value types match or widen.
        display_from, display_to = (
            object_type.displayAttributeTypeKey,
            new_type.displayAttributeTypeKey,
        )
        if (
            new_key != object_type.key
            and display_from in old_bound
            and display_to
            and display_from not in claimed
            and display_to not in claimed.values()
            and display_to not in chosen
        ):
            old_kind = current.attribute_type(display_from).valueType
            new_kind = target.attribute_type(display_to).valueType
            if old_kind == new_kind or (old_kind, new_kind) in WIDENINGS:
                claimed[display_from] = display_to
        for key in sorted(old_bound):
            goes = claimed.get(key)
            plan.values.append(
                (
                    object_type.key,
                    key,
                    goes,
                    target.attribute_type(goes).valueType if goes else None,
                )
            )

    for pair in current.objectTypeRelations:
        new_from, new_to = becomes(pair.fromObjectTypeKey), becomes(pair.toObjectTypeKey)
        kept_pair = (
            target.allowed_relation(pair.relationTypeKey, new_from, new_to)
            if new_from and new_to
            else None
        )
        containment = is_parent_pair(current, pair)
        parent_kept = (
            kept_pair is not None
            and pair.relationTypeKey in target.containment_relation_keys(new_to)
        )
        plan.pairs.append(
            (
                pair.relationTypeKey,
                pair.fromObjectTypeKey,
                pair.toObjectTypeKey,
                kept_pair is not None,
                containment,
                parent_kept or not containment,
            )
        )
        if kept_pair is None:
            continue
        for key in pair.attributeTypeKeys:
            plan.relation_values.append(
                (
                    pair.relationTypeKey,
                    pair.fromObjectTypeKey,
                    pair.toObjectTypeKey,
                    key,
                    target.attribute_type(key).valueType
                    if key in kept_pair.attributeTypeKeys
                    else None,
                )
            )
    return plan


@dataclass(frozen=True)
class Touched:
    """What a migration changed, which rules that did not change may still find broken: the
    attributes whose values it converted or carried, the (new) types of records whose values
    changed, the types records were reclassified into, the relation types it removed relationships
    of and those whose relationship values changed."""

    attributes: frozenset[str] = frozenset()
    valued_types: frozenset[str] = frozenset()
    retyped: frozenset[str] = frozenset()
    relations_removed: frozenset[str] = frozenset()
    relations_changed: frozenset[str] = frozenset()


def relaxed(
    target: EngineModel, current: EngineModel | None = None, touched: Touched | None = None
) -> EngineModel:
    """The target without the rules the migrated data must be checked against, so that the
    compatibility analysis of the target against it checks exactly those (D72): without ``current``
    every rule a record can break (no attribute unique, bounded or required, no ``atLeastOneOf`` or
    effective period, every type at the top, every relationship optional, many-to-many and
    unscoped); with ``current`` and ``touched`` only the rules that are new or changed in the target,
    as activation checks, and those over what the migration changed. A rule the workspace's
    current release holds unchanged over data the migration did not touch was checked when that
    data was written, so it keeps its place and is not checked again."""
    document = target.model_dump(mode="json", by_alias=True)
    before = current.model_dump(mode="json", by_alias=True) if current is not None else None
    touched = touched or Touched()

    def unchanged(kind: str, key: Any) -> dict[str, Any] | None:
        if before is None:
            return None
        if kind == "attribute":
            return next((a for a in before["attributeTypes"] if a["key"] == key), None)
        if kind == "type":
            return next((t for t in before["objectTypes"] if t["key"] == key), None)
        return next(
            (
                p
                for p in before["objectTypeRelations"]
                if (p["relationTypeKey"], p["fromObjectTypeKey"], p["toObjectTypeKey"]) == key
            ),
            None,
        )

    for attribute in document["attributeTypes"]:
        was = unchanged("attribute", attribute["key"])
        features = attribute.get("features") or {}
        validation = attribute.get("validation") or {}
        settled = was is not None and attribute["key"] not in touched.attributes
        if not (
            settled
            and bool((was.get("features") or {}).get("unique")) == bool(features.get("unique"))
        ):
            features.pop("unique", None)
        bounds_settled = (
            settled
            and was.get("valueType") == attribute.get("valueType")
            and all(
                (was.get("validation") or {}).get(bound) == validation.get(bound)
                for bound in ("minimum", "maximum")
            )
        )
        if not bounds_settled:
            for bound in ("minimum", "maximum"):
                validation.pop(bound, None)
    for object_type in document["objectTypes"]:
        was = unchanged("type", object_type["key"])
        if object_type["key"] in touched.retyped:
            was = None
        valued = object_type["key"] in touched.valued_types
        was_bindings = {b["attributeTypeKey"]: b for b in (was or {}).get("attributes") or ()}
        for binding in object_type.get("attributes") or ():
            held = was_bindings.get(binding["attributeTypeKey"])
            if not (held is not None and held.get("required") and not valued):
                binding["required"] = False
        validation = object_type.get("validation") or {}
        if (
            was is None
            or valued
            or (was.get("validation") or {}).get("atLeastOneOf") != validation.get("atLeastOneOf")
        ):
            validation.pop("atLeastOneOf", None)
        if (
            was is None
            or valued
            or was.get("effectivePeriod") != object_type.get("effectivePeriod")
        ):
            object_type.pop("effectivePeriod", None)
        if was is None or (was.get("features") or {}).get("rootCreatable", False):
            object_type["features"] = {**(object_type.get("features") or {}), "rootCreatable": True}
    for pair in document["objectTypeRelations"]:
        identity = (pair["relationTypeKey"], pair["fromObjectTypeKey"], pair["toObjectTypeKey"])
        was = unchanged("pair", identity)
        if touched.retyped & {pair["fromObjectTypeKey"], pair["toObjectTypeKey"]}:
            was = None
        if not (
            was is not None
            and was.get("required")
            and pair["relationTypeKey"] not in touched.relations_removed
        ):
            pair["required"] = False
        if was is None or was.get("cardinality", "many-to-many") != pair.get(
            "cardinality", "many-to-many"
        ):
            pair["cardinality"] = "many-to-many"
        features = pair.get("features") or {}
        condition = (features.get("uniqueWhenToAttributeEquals") or {}).get("attributeTypeKey")
        scope_settled = (
            was is not None
            and not touched.retyped
            and pair["relationTypeKey"] not in touched.relations_changed
            and condition not in touched.attributes
            and all(
                (was.get("features") or {}).get(name) == features.get(name)
                for name in ("uniqueToAncestorTypeKey", "uniqueWhenToAttributeEquals")
            )
        )
        if not scope_settled:
            features.pop("uniqueToAncestorTypeKey", None)
            features.pop("uniqueWhenToAttributeEquals", None)
    return type(target).model_validate(document)


_TOUCHED = """
SELECT 'attribute', target_key FROM migration_value_changes WHERE outcome = 'conversion'
UNION SELECT 'attribute', attribute_type_key FROM migration_relation_changes
    WHERE outcome = 'conversion'
UNION SELECT 'valued', o.target_type_key FROM migration_value_changes c
    JOIN migration_objects o ON o.object_id = c.object_id
UNION SELECT 'retyped', target_type_key FROM migration_objects
    WHERE lost_code IS NULL AND target_type_key <> object_type_key
UNION SELECT 'removed', relation_type_key FROM migration_relations WHERE lost_code IS NOT NULL
UNION SELECT 'changed', r.relation_type_key FROM migration_relation_changes c
    JOIN migration_relations r ON r.relation_id = c.relation_id
"""


# --- the tables a migration works through ----------------------------------------------------------

# The plan's tables, which a change set's move (``change_set_migrations``) fills too.
PLAN_TABLES = """
CREATE TEMPORARY TABLE migration_types (
    application_key text, object_type_key text, target_application_key text,
    target_type_key text, code text, PRIMARY KEY (application_key, object_type_key)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE migration_values (
    object_type_key text, attribute_type_key text, target_key text, to_type text,
    PRIMARY KEY (object_type_key, attribute_type_key)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE migration_pairs (
    relation_type_key text, from_type text, to_type text, kept boolean, containment boolean,
    parent_kept boolean, PRIMARY KEY (relation_type_key, from_type, to_type)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE migration_relation_values (
    relation_type_key text, from_type text, to_type text, attribute_type_key text, to_type_value text,
    PRIMARY KEY (relation_type_key, from_type, to_type, attribute_type_key)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE migration_value_types (
    attribute_type_key text PRIMARY KEY, value_type text
) ON COMMIT DROP;
"""

_TABLES = """
CREATE TEMPORARY TABLE migration_objects (
    object_id varchar(36) PRIMARY KEY, application_key text, object_type_key text,
    target_application_key text, target_type_key text, name text, parent_object_id varchar(36),
    version integer, lost_code text, changed boolean NOT NULL DEFAULT false
) ON COMMIT DROP;
CREATE INDEX migration_objects_parent ON migration_objects (parent_object_id);
CREATE TEMPORARY TABLE migration_relations (
    relation_id varchar(36) PRIMARY KEY, relation_type_key text, from_object_id varchar(36),
    to_object_id varchar(36), from_type text, to_type text, attributes json, version integer,
    containment boolean, refused boolean, lost_code text
) ON COMMIT DROP;
CREATE TEMPORARY TABLE migration_value_changes (
    object_id varchar(36), attribute_type_key text, target_key text, to_type text, before json,
    after json, outcome text, code text, PRIMARY KEY (object_id, attribute_type_key)
) ON COMMIT DROP;
CREATE TEMPORARY TABLE migration_relation_changes (
    relation_id varchar(36), attribute_type_key text, before json, after json, outcome text,
    code text, PRIMARY KEY (relation_id, attribute_type_key)
) ON COMMIT DROP;
"""

_VALUE = (
    "rdm_value_json(a.value_type, a.text_value, a.integer_value, a.decimal_value, "
    "a.boolean_value, a.date_value, a.datetime_value, a.json_value)"
)

_FILL = (
    # Every record of the workspace with its fate: its new type and application, or why it is
    # lost; a type the current model no longer lists anywhere is lost as a removed type.
    """
    INSERT INTO migration_objects
    SELECT o.id, o.application_key, o.object_type_key, t.target_application_key,
        t.target_type_key, o.name, o.parent_object_id, o.version,
        CASE WHEN t.target_type_key IS NULL THEN coalesce(t.code, 'OBJECT_TYPE_IN_USE') END, false
    FROM objects o
    LEFT JOIN migration_types t
        ON t.application_key = o.application_key AND t.object_type_key = o.object_type_key
    WHERE o.workspace_key = :workspace
    """,
    # What a lost record contains is lost with it.
    """
    WITH RECURSIVE lost AS (
        SELECT object_id FROM migration_objects WHERE lost_code IS NOT NULL
        UNION
        SELECT child.object_id FROM migration_objects child
        JOIN lost ON child.parent_object_id = lost.object_id
    )
    UPDATE migration_objects m SET lost_code = 'PARENT_REMOVED'
    FROM lost WHERE m.object_id = lost.object_id AND m.lost_code IS NULL
    """,
    # Every relationship of the workspace with its fate. A containment edge whose child stays but
    # which the target has no place for is refused, never lost: the record cannot stay where it is.
    """
    INSERT INTO migration_relations
    SELECT r.id, r.relation_type_key, r.from_object_id, r.to_object_id, f.object_type_key,
        t.object_type_key, r.attributes, r.version, coalesce(p.containment, false),
        coalesce(p.containment, false) AND t.lost_code IS NULL AND f.lost_code IS NULL
            AND NOT coalesce(p.kept AND p.parent_kept, false),
        CASE
            WHEN coalesce(p.containment, false) AND t.lost_code IS NULL AND f.lost_code IS NULL
                THEN NULL
            WHEN NOT coalesce(p.kept, false) THEN 'RELATION_PAIR_IN_USE'
            WHEN f.lost_code IS NOT NULL OR t.lost_code IS NOT NULL THEN 'RELATION_END_REMOVED'
        END
    FROM object_relations r
    JOIN migration_objects f ON f.object_id = r.from_object_id
    JOIN migration_objects t ON t.object_id = r.to_object_id
    LEFT JOIN migration_pairs p ON p.relation_type_key = r.relation_type_key
        AND p.from_type = f.object_type_key AND p.to_type = t.object_type_key
    """,
    # Each value of a staying record: carried as it is, converted, carried to another attribute,
    # or lost because it has no place or does not convert (D69).
    f"""
    INSERT INTO migration_value_changes
    SELECT object_id, attribute_type_key, target_key, to_type, before, after,
        CASE WHEN after IS NULL THEN 'loss' ELSE 'conversion' END,
        CASE
            WHEN target_key IS NULL THEN 'ATTRIBUTE_BINDING_IN_USE'
            WHEN after IS NULL THEN 'VALUE_NOT_CONVERTIBLE'
            WHEN from_type <> to_type THEN 'VALUE_CONVERTED'
            ELSE 'VALUE_CARRIED'
        END
    FROM (
        SELECT o.object_id, a.attribute_type_key, p.target_key, p.to_type, a.value_type AS from_type,
            {_VALUE} AS before,
            CASE WHEN p.target_key IS NOT NULL
                THEN rdm_convert_value({_VALUE}, a.value_type, p.to_type) END AS after
        FROM attribute_values a
        JOIN migration_objects o ON o.object_id = a.object_id AND o.lost_code IS NULL
        LEFT JOIN migration_values p ON p.object_type_key = o.object_type_key
            AND p.attribute_type_key = a.attribute_type_key
    ) value
    WHERE before IS NOT NULL AND jsonb_typeof(before::jsonb) <> 'null'
        AND (target_key IS NULL OR after IS NULL OR from_type <> to_type
            OR target_key <> attribute_type_key)
    """,
    # The staying records the migration changes: retyped, or with a value changed. Marked once so the
    # writes join on it rather than testing each record against the set (0.11 V1 budget).
    """
    UPDATE migration_objects m SET changed = true
    WHERE m.lost_code IS NULL AND (m.target_type_key <> m.object_type_key
        OR m.target_application_key <> m.application_key)
    """,
    """
    UPDATE migration_objects m SET changed = true
    FROM (SELECT DISTINCT object_id FROM migration_value_changes) c
    WHERE c.object_id = m.object_id AND NOT m.changed
    """,
    # Each value of a staying relationship, as a record's.
    """
    INSERT INTO migration_relation_changes
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
        FROM migration_relations r
        CROSS JOIN LATERAL jsonb_each(r.attributes::jsonb) e
        LEFT JOIN migration_relation_values p ON p.relation_type_key = r.relation_type_key
            AND p.from_type = r.from_type AND p.to_type = r.to_type AND p.attribute_type_key = e.key
        LEFT JOIN (SELECT DISTINCT attribute_type_key, value_type FROM migration_value_types) a
            ON a.attribute_type_key = e.key
        WHERE r.lost_code IS NULL AND NOT r.refused AND jsonb_typeof(e.value) <> 'null'
    ) value
    WHERE to_type_value IS NULL OR after IS NULL OR from_type <> to_type_value
    """,
)

# The rows of a preview or an execution, in one order: type changes, values, relationship values,
# lost records, lost relationships, refused containment edges.
_ROWS = """
INSERT INTO job_items (job_id, item_index, ref, status, outcome)
SELECT CAST(:job AS integer), CAST(:offset AS integer) + row_number() OVER (ORDER BY rank, a, b) - 1,
    NULL, CASE WHEN outcome ->> 'outcome' = 'refused' THEN 'rejected' ELSE 'applied' END, outcome
FROM (
    SELECT 0 AS rank, object_id AS a, '' AS b, json_strip_nulls(json_build_object(
        'outcome', 'reclassified', 'code', 'RECORD_RECLASSIFIED', 'objectId', object_id,
        'objectName', name, 'objectTypeKey', object_type_key,
        'targetObjectTypeKey', target_type_key, 'applicationKey', application_key,
        'targetApplicationKey', target_application_key)) AS outcome
    FROM migration_objects
    WHERE lost_code IS NULL AND (target_type_key <> object_type_key
        OR target_application_key <> application_key)
    UNION ALL
    SELECT 1, c.object_id, c.attribute_type_key, json_strip_nulls(json_build_object(
        'outcome', c.outcome, 'code', c.code, 'objectId', c.object_id, 'objectName', o.name,
        'objectTypeKey', o.object_type_key, 'attributeTypeKey', c.attribute_type_key,
        'targetAttributeTypeKey', CASE WHEN c.target_key <> c.attribute_type_key
            THEN c.target_key END,
        'before', c.before, 'after', c.after))
    FROM migration_value_changes c JOIN migration_objects o ON o.object_id = c.object_id
    UNION ALL
    SELECT 2, r.relation_id, c.attribute_type_key, json_strip_nulls(json_build_object(
        'outcome', c.outcome, 'code', c.code, 'objectId', r.from_object_id,
        'relationId', r.relation_id, 'relationTypeKey', r.relation_type_key,
        'toObjectId', r.to_object_id, 'attributeTypeKey', c.attribute_type_key,
        'before', c.before, 'after', c.after))
    FROM migration_relation_changes c JOIN migration_relations r ON r.relation_id = c.relation_id
    UNION ALL
    SELECT 3, object_id, '', json_build_object(
        'outcome', 'loss', 'code', lost_code, 'objectId', object_id, 'objectName', name,
        'objectTypeKey', object_type_key)
    FROM migration_objects WHERE lost_code IS NOT NULL
    UNION ALL
    SELECT 4, relation_id, '', json_build_object(
        'outcome', 'loss', 'code', lost_code, 'objectId', from_object_id,
        'relationId', relation_id, 'relationTypeKey', relation_type_key,
        'toObjectId', to_object_id)
    FROM migration_relations WHERE lost_code IS NOT NULL AND NOT containment
    UNION ALL
    SELECT 5, r.to_object_id, r.relation_id, json_build_object(
        'outcome', 'refused', 'code', 'PARENT_RELATION_SEMANTICS_CHANGED',
        'objectId', r.to_object_id, 'objectName', o.name, 'objectTypeKey', o.object_type_key,
        'relationTypeKey', r.relation_type_key,
        'message', 'The target release has no place for this record under its parent')
    FROM migration_relations r JOIN migration_objects o ON o.object_id = r.to_object_id
    WHERE r.refused
) rows
"""

# Refusals found after the savepoint, written back once it is rolled back.
_REFUSALS = """
INSERT INTO job_items (job_id, item_index, ref, status, outcome)
SELECT CAST(:job AS integer), CAST(:offset AS integer) + listed.position - 1, NULL, 'rejected',
    json_strip_nulls(json_build_object(
        'outcome', 'refused', 'code', listed.code,
        'objectId', coalesce(listed.object_id, r.from_object_id, listed.relation_id),
        'objectName', o.name, 'objectTypeKey', o.object_type_key, 'relationId', listed.relation_id,
        'relationTypeKey', r.relation_type_key, 'toObjectId', r.to_object_id, 'path', listed.path,
        'message', listed.message))
FROM unnest(CAST(:ids AS text[]), CAST(:relations AS text[]), CAST(:codes AS text[]),
    CAST(:paths AS text[]), CAST(:messages AS text[]))
    WITH ORDINALITY AS listed(object_id, relation_id, code, path, message, position)
LEFT JOIN object_relations r ON r.id = listed.relation_id
LEFT JOIN objects o ON o.id = coalesce(listed.object_id, r.from_object_id)
"""

COUNTS = """
SELECT outcome ->> 'outcome', count(*) FROM job_items WHERE job_id = :job GROUP BY 1
"""

# The audit entries an execution records (D73), before anything changes: a record's values
# converted, carried or removed (``updated``), a record whose type changes (``reclassified``, with
# its full before state), a relationship whose values change (``updated``) or that is removed and
# a record removed (``deleted``, with its before state). Containment edges take no feed position.
_AUDIT_TABLE = """
CREATE TEMPORARY TABLE migration_audit (
    rank integer, id text, aggregate_type text, action text, version integer, changes json,
    feed boolean, subject json, from_id text, to_id text
) ON COMMIT DROP
"""
_AUDIT_ENTRIES = f"""
WITH before_values AS (
    SELECT a.object_id, json_object_agg(a.attribute_type_key, {_VALUE}) AS attributes
    FROM attribute_values a JOIN migration_objects o ON o.object_id = a.object_id
    WHERE o.lost_code IS NOT NULL OR o.target_type_key <> o.object_type_key
        OR o.target_application_key <> o.application_key
    GROUP BY a.object_id
), changed AS (
    SELECT object_id, json_object_agg(attribute_type_key, before) AS before,
        array_agg(DISTINCT attribute_type_key) || array_agg(DISTINCT target_key)
            FILTER (WHERE target_key IS NOT NULL) AS keys
    FROM migration_value_changes GROUP BY object_id
), relation_changed AS (
    SELECT relation_id, json_object_agg(attribute_type_key, before) AS before,
        array_agg(DISTINCT attribute_type_key) AS keys
    FROM migration_relation_changes GROUP BY relation_id
)
INSERT INTO migration_audit
SELECT 0 AS rank, o.object_id AS id, 'object' AS aggregate_type,
    CASE WHEN o.target_type_key <> o.object_type_key
        OR o.target_application_key <> o.application_key THEN 'reclassified' ELSE 'updated' END
        AS action,
    o.version + 1 AS version,
    json_build_object(
        'changedFields', CASE WHEN o.target_type_key <> o.object_type_key
            OR o.target_application_key <> o.application_key
            THEN CASE WHEN c.object_id IS NULL THEN json_build_array('objectType')
                ELSE json_build_array('objectType', 'attributes') END
            ELSE json_build_array('attributes') END,
        'attributeTypeKeys', coalesce(to_json(ARRAY(SELECT DISTINCT unnest(c.keys) ORDER BY 1)),
            '[]'::json),
        'objectType', CASE WHEN o.target_type_key <> o.object_type_key THEN json_build_object(
            'before', o.object_type_key, 'after', o.target_type_key) END,
        'migrationJobId', CAST(:job_id AS text),
        'before', json_build_object('name', o.name, 'parentObjectId', o.parent_object_id,
            'attributes', coalesce(b.attributes, c.before, '{{}}'::json))
    ) AS changes,
    true AS feed,
    json_strip_nulls(json_build_object('objectTypeKey', o.target_type_key,
        'applicationKey', o.target_application_key, 'parentObjectId', o.parent_object_id,
        'previousObjectTypeKey', CASE WHEN o.target_type_key <> o.object_type_key
            THEN o.object_type_key END)) AS subject,
    NULL::text AS from_id, NULL::text AS to_id
FROM migration_objects o
LEFT JOIN changed c ON c.object_id = o.object_id
LEFT JOIN before_values b ON b.object_id = o.object_id
WHERE o.lost_code IS NULL AND (c.object_id IS NOT NULL OR o.target_type_key <> o.object_type_key
    OR o.target_application_key <> o.application_key)
UNION ALL
SELECT 1, r.relation_id, 'relation', 'updated', r.version + 1,
    json_build_object('changedFields', json_build_array('attributes'),
        'attributeTypeKeys', to_json(c.keys), 'migrationJobId', CAST(:job_id AS text),
        'before', json_build_object('attributes', c.before)),
    NOT r.containment,
    json_build_object('relationTypeKey', r.relation_type_key, 'fromObjectId', r.from_object_id,
        'toObjectId', r.to_object_id),
    r.from_object_id, r.to_object_id
FROM migration_relations r JOIN relation_changed c ON c.relation_id = r.relation_id
UNION ALL
SELECT 2, r.relation_id, 'relation', 'deleted', r.version,
    json_build_object('changedFields', json_build_array(), 'attributeTypeKeys', json_build_array(),
        'relationTypeKey', r.relation_type_key, 'fromObjectId', r.from_object_id,
        'toObjectId', r.to_object_id, 'migrationJobId', CAST(:job_id AS text),
        'before', json_build_object('attributes', r.attributes)),
    NOT r.containment,
    json_build_object('relationTypeKey', r.relation_type_key, 'fromObjectId', r.from_object_id,
        'toObjectId', r.to_object_id),
    r.from_object_id, r.to_object_id
FROM migration_relations r WHERE r.lost_code IS NOT NULL
UNION ALL
SELECT 3, o.object_id, 'object', 'deleted', o.version,
    json_build_object('changedFields', json_build_array(), 'attributeTypeKeys', json_build_array(),
        'objectTypeKey', o.object_type_key, 'migrationJobId', CAST(:job_id AS text),
        'before', json_build_object('name', o.name, 'parentObjectId', o.parent_object_id,
            'attributes', coalesce(b.attributes, '{{}}'::json))),
    true,
    json_build_object('objectTypeKey', o.object_type_key, 'applicationKey', o.application_key,
        'parentObjectId', o.parent_object_id),
    NULL, NULL
FROM migration_objects o LEFT JOIN before_values b ON b.object_id = o.object_id
WHERE o.lost_code IS NOT NULL
"""

_AUDIT = """
WITH placed AS (
    SELECT migration_audit.*, CASE WHEN feed THEN CAST(:first AS integer) - 1
        + sum(feed::integer) OVER (ORDER BY rank, id COLLATE "C" ROWS UNBOUNDED PRECEDING) END
        AS position
    FROM migration_audit
), inserted AS (
    INSERT INTO audit_events (event_id, aggregate_type, aggregate_id, action, version, changes,
        occurred_at, cause_kind, cause_id, workspace_key, feed_position, model_release_id,
        feed_subject)
    SELECT gen_random_uuid()::text, aggregate_type, id, action, version, changes,
        CAST(:now AS timestamptz), 'job', CAST(:job_id AS varchar),
        CASE WHEN feed THEN CAST(:workspace AS varchar) END, position,
        CASE WHEN feed THEN CAST(:release AS integer) END, CASE WHEN feed THEN subject END
    FROM placed ORDER BY rank, id COLLATE "C"
    RETURNING sequence_id, aggregate_type, aggregate_id, feed_subject
)
INSERT INTO audit_event_subjects (audit_event_id, object_id)
SELECT sequence_id, aggregate_id FROM inserted WHERE aggregate_type = 'object'
UNION
SELECT i.sequence_id, a.from_id FROM inserted i
JOIN migration_audit a ON a.id = i.aggregate_id AND a.aggregate_type = 'relation'
WHERE i.aggregate_type = 'relation'
UNION
SELECT i.sequence_id, a.to_id FROM inserted i
JOIN migration_audit a ON a.id = i.aggregate_id AND a.aggregate_type = 'relation'
WHERE i.aggregate_type = 'relation'
"""

# The relation sets a removed relationship belonged to advance (0.9 B3), as a deletion's do.
_SETS = """
INSERT INTO relation_set_versions (workspace_key, change_set_id, relation_type_key,
    from_object_type_key, to_object_type_key, anchor_object_id, direction, version, created_at,
    updated_at)
SELECT CAST(:workspace AS varchar), NULL, relation_type_key, from_type, to_type, anchor, direction,
    count(*), CAST(:now AS timestamptz), CAST(:now AS timestamptz)
FROM (
    SELECT relation_type_key, from_type, to_type, from_object_id AS anchor,
        'outgoing' AS direction FROM migration_relations WHERE lost_code IS NOT NULL
    UNION ALL
    SELECT relation_type_key, from_type, to_type, to_object_id, 'incoming'
    FROM migration_relations WHERE lost_code IS NOT NULL
) ends
GROUP BY relation_type_key, from_type, to_type, anchor, direction
ORDER BY relation_type_key, from_type, to_type, anchor, direction
ON CONFLICT (workspace_key, relation_type_key, from_object_type_key, to_object_type_key,
    anchor_object_id, direction) WHERE change_set_id IS NULL
DO UPDATE SET version = relation_set_versions.version + EXCLUDED.version,
    updated_at = EXCLUDED.updated_at
"""

_APPLY = (
    (
        "DELETE FROM object_relations WHERE id IN "
        "(SELECT relation_id FROM migration_relations WHERE lost_code IS NOT NULL)"
    ),
    """
    DELETE FROM attribute_values a USING migration_value_changes c
    WHERE a.object_id = c.object_id AND a.attribute_type_key = c.attribute_type_key
        AND c.outcome = 'loss'
    """,
    """
    UPDATE attribute_values a SET attribute_type_key = c.target_key, value_type = c.to_type,
        text_value = CASE WHEN c.to_type IN ('text', 'longText') THEN c.after #>> '{}' END,
        integer_value = CASE WHEN c.to_type = 'integer' THEN (c.after #>> '{}')::integer END,
        decimal_value = CASE WHEN c.to_type = 'decimal' THEN (c.after #>> '{}')::numeric END,
        boolean_value = CASE WHEN c.to_type = 'boolean' THEN (c.after #>> '{}')::boolean END,
        date_value = CASE WHEN c.to_type = 'date' THEN (c.after #>> '{}')::date END,
        datetime_value = CASE WHEN c.to_type = 'dateTime'
            THEN (c.after #>> '{}')::timestamptz END,
        json_value = CASE WHEN c.to_type = 'json' THEN c.after END,
        version = a.version + 1
    FROM migration_value_changes c
    WHERE a.object_id = c.object_id AND a.attribute_type_key = c.attribute_type_key
        AND c.outcome = 'conversion'
    """,
    (
        "DELETE FROM attribute_values WHERE object_id IN "
        "(SELECT object_id FROM migration_objects WHERE lost_code IS NOT NULL)"
    ),
    # The parent key is RESTRICT: lost records are detached from each other first.
    (
        "UPDATE objects SET parent_object_id = NULL WHERE parent_object_id IS NOT NULL AND id IN "
        "(SELECT object_id FROM migration_objects WHERE lost_code IS NOT NULL)"
    ),
    (
        "DELETE FROM objects WHERE id IN "
        "(SELECT object_id FROM migration_objects WHERE lost_code IS NOT NULL)"
    ),
    """
    UPDATE objects o SET object_type_key = m.target_type_key,
        application_key = m.target_application_key, version = o.version + 1,
        updated_at = CAST(:now AS timestamptz)
    FROM migration_objects m
    WHERE o.id = m.object_id AND m.changed
    """,
    """
    UPDATE object_relations r SET version = r.version + 1, updated_at = CAST(:now AS timestamptz),
        attributes = (
            SELECT coalesce(json_object_agg(e.key, coalesce(c.after, e.value::json))
                FILTER (WHERE c.outcome IS DISTINCT FROM 'loss'), '{}'::json)
            FROM jsonb_each(r.attributes::jsonb) e
            LEFT JOIN migration_relation_changes c
                ON c.relation_id = r.id AND c.attribute_type_key = e.key
        )
    WHERE r.id IN (SELECT relation_id FROM migration_relation_changes)
    """,
)


def load_plan(
    session: Session, current: EngineModel, target: EngineModel, mappings: Sequence[TypeMapping]
) -> MigrationPlan:
    """Decide the plan and write it into its temporary tables, with the value type each attribute
    holds in ``current`` (``migration_value_types``)."""
    plan = plan_migration(current, target, mappings)
    session.execute(text(PLAN_TABLES))
    insert_rows(session, "migration_types", plan.types)
    insert_rows(session, "migration_values", plan.values)
    insert_rows(session, "migration_pairs", plan.pairs)
    insert_rows(session, "migration_relation_values", plan.relation_values)
    insert_rows(
        session,
        "migration_value_types",
        [(item.key, item.valueType) for item in current.attributeTypes],
    )
    return plan


# --- submission ----------------------------------------------------------------------------------


def installed_release(session: Session, release_id: str) -> ModelRelease:
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == release_id))
    if release is None:
        raise api_error(404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found")
    if release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise api_error(
            422,
            "UNSUPPORTED_SCHEMA_VERSION",
            f"Schema version '{release.schema_version}' cannot be migrated to",
            {
                "releaseId": release.public_id,
                "schemaVersion": release.schema_version,
                "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                "operation": "migration",
            },
        )
    return release


def _change_set_of(session: Session, workspace_key: str, change_set_id: str) -> ChangeSet:
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None or change_set.workspace_key != workspace_key:
        raise api_error(
            404,
            "CHANGE_SET_NOT_FOUND",
            f"Workspace '{workspace_key}' has no open change set '{change_set_id}'",
            {"workspaceKey": workspace_key, "changeSetId": change_set_id},
        )
    return change_set


def submit_migration(
    session: Session,
    workspace_key: str,
    *,
    target_release_id: str | None,
    expected_version: int,
    type_mappings: list[dict[str, Any]],
    retention_days: int,
    change_set_id: str | None = None,
    expected_change_set_version: int | None = None,
) -> Job:
    """Queue the preview of a migration of ``workspace_key`` to the target release. Refused before
    a job exists: an unknown or retired workspace, an unknown target or one of an unsupported
    schema, the release the workspace runs already, an assignment changed since
    ``expected_version`` (``409 ACTIVATION_CONFLICT``), a mapping naming what the models lack, a
    consumer API whose contract changes without a new contract version
    (``ConsumerContractVersionRequired``). Naming a change set (V2): another workspace's or none
    (``404 CHANGE_SET_NOT_FOUND``), one changed since ``expected_change_set_version`` (``409
    CHANGE_SET_VERSION_CONFLICT``), a target other than its release (``422
    MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE``)."""
    workspace = session.get(Workspace, workspace_key)
    if workspace is None:
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace_key}' not found")
    if workspace.status != "active":
        raise api_error(
            409,
            "WORKSPACE_RETIRED",
            f"Workspace '{workspace_key}' is retired; its model is not changed",
            {"workspaceKey": workspace_key},
        )
    assignment, current = load_assignment(session, workspace_key)
    change_set = None
    if change_set_id is not None:
        change_set = _change_set_of(session, workspace_key, change_set_id)
        if change_set.version != expected_change_set_version:
            raise api_error(
                409,
                "CHANGE_SET_VERSION_CONFLICT",
                "Change set version has changed",
                {"changeSetId": change_set.id, "currentVersion": change_set.version},
            )
        pinned = session.get(ModelRelease, change_set.model_release_id)
        if target_release_id is not None and target_release_id != pinned.public_id:
            raise api_error(
                422,
                "MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE",
                f"Change set '{change_set.id}' works under release '{pinned.public_id}'; a "
                "migration that publishes it moves the workspace to that release",
                {
                    "changeSetId": change_set.id,
                    "changeSetReleaseId": pinned.public_id,
                    "releaseId": target_release_id,
                },
            )
        target_release_id = pinned.public_id
    assert target_release_id is not None
    target = installed_release(session, target_release_id)
    if assignment.version != expected_version:
        raise api_error(
            409,
            "ACTIVATION_CONFLICT",
            f"The model of workspace '{workspace_key}' changed since version {expected_version}",
            {
                "workspaceKey": workspace_key,
                "currentReleaseId": current.public_id,
                "currentVersion": assignment.version,
            },
        )
    if target.id == current.id:
        raise api_error(
            422,
            "MIGRATION_TARGET_IS_CURRENT",
            f"Workspace '{workspace_key}' runs release '{target.public_id}' already",
            {"workspaceKey": workspace_key, "releaseId": target.public_id},
        )
    current_model = resolve_pinned_release(session, current.id).model
    target_model = resolve_pinned_release(session, target.id).model
    plan_migration(current_model, target_model, parse_type_mappings(type_mappings))
    # The workspace's consumers read its release, so the target's definitions are the contract,
    # as on activation (C-D17, D75).
    contract_errors = tuple(
        item
        for item in contract_diagnostics(current_model, target_model)
        if item.severity == "error"
    )
    if contract_errors:
        raise ConsumerContractVersionRequired(contract_errors)
    return start_job(
        session,
        kind="migration",
        workspace_key=workspace_key,
        change_set_id=change_set.id if change_set is not None else None,
        model_release_id=current.id,
        parameters={
            "stage": "preview",
            "targetReleaseId": target.public_id,
            "typeMappings": type_mappings,
            **({"changeSetId": change_set.id} if change_set is not None else {}),
        },
        total=None,
        retention_days=retention_days,
        queued=True,
    )


# --- preview and execution -------------------------------------------------------------------------


@dataclass
class _Migration:
    session: Session
    job: Job
    current: EngineModel
    target: EngineModel
    target_release: ModelRelease

    @classmethod
    def open(cls, session: Session, job: Job) -> _Migration:
        target_release = installed_release(session, job.parameters["targetReleaseId"])
        return cls(
            session,
            job,
            resolve_pinned_release(session, job.model_release_id).model,
            resolve_pinned_release(session, target_release.id).model,
            target_release,
        )

    @property
    def workspace_key(self) -> str:
        return self.job.workspace_key

    def prepare(self) -> None:
        """The plan into its tables, and every record, relationship and value it changes."""
        session = self.session
        load_plan(
            session,
            self.current,
            self.target,
            parse_type_mappings(self.job.parameters["typeMappings"]),
        )
        session.execute(text(_TABLES))
        for statement in _FILL:
            session.execute(text(statement), {"workspace": self.workspace_key})
        # The tables were just filled: PostgreSQL plans the joins over them from their statistics,
        # not from a guess (0.10 R, R-F19).
        session.execute(
            text(
                "ANALYZE migration_objects, migration_relations, migration_value_changes, "
                "migration_relation_changes"
            )
        )

    @property
    def _touched(self) -> Touched:
        """What the migration changes, read from its tables (a few keys of each kind)."""
        found: dict[str, set[str]] = {}
        for kind, key in self.session.execute(text(_TOUCHED)):
            if key is not None:
                found.setdefault(kind, set()).add(key)
        return Touched(
            attributes=frozenset(found.get("attribute", ())),
            valued_types=frozenset(found.get("valued", ())),
            retyped=frozenset(found.get("retyped", ())),
            relations_removed=frozenset(found.get("removed", ())),
            relations_changed=frozenset(found.get("changed", ())),
        )

    def write_rows(self) -> int:
        """The plan's rows into the job's items; the number written."""
        return self.session.execute(
            text(_ROWS), {"job": self.job.sequence_id, "offset": 0}
        ).rowcount

    def apply(self, *, audit: bool) -> None:
        """Change the workspace's data as planned; with ``audit``, record each change first."""
        session = self.session
        now = datetime.now(UTC)
        if audit:
            session.execute(text(_AUDIT_TABLE))
            session.execute(text(_AUDIT_ENTRIES), {"job_id": self.job.id})
            session.execute(text("ANALYZE migration_audit"))
            feed = int(session.scalar(text("SELECT count(*) FROM migration_audit WHERE feed")) or 0)
            first, _release_id = take_positions(session, self.workspace_key, feed)
            session.execute(
                text(_AUDIT),
                {
                    "first": first,
                    "now": now,
                    "job_id": self.job.id,
                    "workspace": self.workspace_key,
                    "release": self.target_release.id,
                },
            )
            session.execute(text(_SETS), {"workspace": self.workspace_key, "now": now})
        for statement in _APPLY:
            session.execute(text(statement), {"now": now})

    def refusals(self, *, listing: bool) -> list[tuple[str, str, str, str]]:
        """Check the migrated data against the target release (D72): each refused record with
        the code, path and message of the rule it breaks (with ``listing``), or one entry per
        rule broken."""
        found: list[tuple[str, str, str, str]] = []

        def take(records: Select[Any], code: str, path: str, message: str) -> None:
            ids = self.session.scalars(select(records.subquery().c[0]).distinct())
            found.extend((str(item), code, path, message) for item in ids)

        result = analyze_compatibility(
            self.session,
            relaxed(self.target, self.current, self._touched),
            self.target,
            self.target_release.public_id,
            [self.workspace_key],
            listing=take if listing else None,
        )
        if listing:
            return found
        return [("", item.code, item.path, item.message) for item in result.diagnostics]

    def publication_refusals(self, change_set: ChangeSet) -> list[tuple[str, str, str, str]]:
        """What would stop the change set's publication over the migrated data (D82)."""
        self.session.expire_all()
        return publication_refusal_items(
            publication_findings(self.session, change_set, self.target)
        )

    def write_refusals(self, refused: list[tuple[str, str, str, str]], offset: int) -> None:
        """Refused items in order. An item's subject is a record's ID, or ``object:<id>`` or
        ``relation:<id>`` for a publication's refusal (a relationship's item names its source)."""
        if not refused:
            return
        ids, codes, paths, messages = (list(column) for column in zip(*refused, strict=True))
        objects = [
            item.removeprefix("object:") if not item.startswith("relation:") else None
            for item in ids
        ]
        relations = [
            item.removeprefix("relation:") if item.startswith("relation:") else None for item in ids
        ]
        self.session.execute(
            text(_REFUSALS),
            {
                "job": self.job.sequence_id,
                "offset": offset,
                "ids": objects,
                "relations": relations,
                "codes": codes,
                "paths": [path or None for path in paths],
                "messages": messages,
            },
        )

    def counts(self) -> dict[str, int]:
        found = dict(self.session.execute(text(COUNTS), {"job": self.job.sequence_id}).all())
        return {outcome: int(found.get(outcome, 0)) for outcome in OUTCOMES}


def publication_refusal_items(
    findings: Sequence[dict[str, Any]],
) -> list[tuple[str, str, str, str]]:
    """A publication's findings as refused items (D82): a merge conflict names its record or
    relationship, a record or relationship changed in both since the change set's base being
    ``CHANGE_SET_CONFLICT``; a whole-graph diagnostic keeps its code and names the record or
    relationship in its details. Subjects are ``object:<id>`` or ``relation:<id>``."""
    items = []
    for item in findings:
        details = item.get("details") or {}
        if "kind" in item:
            code = "CHANGE_SET_CONFLICT" if item["code"] == "VERSION_MISMATCH" else item["code"]
            subject = f"{item['kind']}:{item['id']}"
        else:
            code = item["code"]
            subject = (
                f"relation:{details['relationId']}"
                if "relationId" in details
                else f"object:{details.get('objectId') or details.get('id') or ''}"
            )
        items.append((subject, code, "", item["message"]))
    return items


def insert_rows(session: Session, table: str, rows: Sequence[tuple[Any, ...]]) -> None:
    """Rows into one of a migration's temporary tables."""
    if not rows:
        return
    width = len(rows[0])
    names = ", ".join(f":c{index}" for index in range(width))
    session.execute(
        text(f"INSERT INTO {table} VALUES ({names})"),
        [{f"c{index}": value for index, value in enumerate(row)} for row in rows],
    )


def record_summary(job: Job, counts: dict[str, int], **summary: Any) -> None:
    """The job's counts, items and migration summary."""
    total = sum(counts.values())
    job.total = total
    job.processed = total
    job.counts = {
        **dict(job.counts or {}),
        "applied": total - counts["refused"],
        "rejected": counts["refused"],
        "unprocessed": 0,
    }
    job.report = {
        **(job.report or {}),
        "migration": {**(job.report or {}).get("migration", {}), **summary, "counts": counts},
    }


def run_preview(
    session: Session,
    job: Job,
    *,
    retention_days: int,
    hold: Callable[[], None],
    renew: Callable[[], None] = lambda: None,
) -> None:
    """Preview the migration and, once ``hold`` (the worker's lease) allows, leave the job
    waiting for confirmation; the caller commits."""
    migration = _Migration.open(session, job)
    assignment, current = load_assignment(session, job.workspace_key)
    feed_position = session.scalar(
        select(Workspace.feed_position).where(Workspace.key == job.workspace_key)
    )
    workspace = session.get(Workspace, job.workspace_key)
    change_set = (
        _change_set_of(session, job.workspace_key, job.change_set_id)
        if job.change_set_id is not None
        else None
    )
    published = (
        {
            "changeSetId": change_set.id,
            "changeSetVersion": change_set.version,
            "activePublicationId": workspace.active_publication_id,
        }
        if change_set is not None
        else {}
    )
    migration.prepare()
    renew()
    written = migration.write_rows()
    renew()
    savepoint = session.begin_nested()
    try:
        migration.apply(audit=False)
        renew()
        refused = migration.refusals(listing=True)
        if change_set is not None:
            renew()
            refused += migration.publication_refusals(change_set)
    finally:
        savepoint.rollback()
    renew()
    migration.write_refusals(refused, written)
    record_summary(
        job,
        migration.counts(),
        targetReleaseId=migration.target_release.public_id,
        currentReleaseId=current.public_id,
        expectedVersion=assignment.version,
        feedPosition=int(feed_position or 0),
        **published,
    )
    hold()
    await_confirmation(
        session, job, job.report["migration"], retention_days=retention_days, key="migration"
    )


def check_confirmation(
    session: Session,
    job: Job,
    *,
    expected_version: int | None,
    expected_feed_position: int | None,
    accept_loss: bool,
) -> bool:
    """Confirm a waiting migration under the job's lock (D74), refused leaving it waiting: a
    workspace written or activated since the reviewed versions is ``409
    MIGRATION_REVIEW_STALE``, refusals ``409 MIGRATION_HAS_REFUSALS``, a loss without
    ``acceptLoss`` ``422 MIGRATION_LOSS_NOT_ACCEPTED``. Its preview's rows stay until the execution
    replaces them. ``False`` when it was confirmed before."""
    if expected_version is None or expected_feed_position is None:
        raise api_error(
            422,
            "REQUEST_VALIDATION_ERROR",
            "Confirming a migration names the reviewed expectedVersion and expectedFeedPosition",
        )

    def check(job: Job) -> None:
        summary = (job.report or {}).get("migration", {})
        require_reviewed(
            session,
            job,
            reviewed_version=expected_version,
            reviewed_feed_position=expected_feed_position,
            summary=summary,
        )
        counts = summary.get("counts", {})
        if counts.get("refused"):
            raise api_error(
                409,
                "MIGRATION_HAS_REFUSALS",
                f"The preview refused {counts['refused']} items; fix the workspace's data and "
                "preview the migration again",
                {"refused": counts["refused"]},
            )
        if counts.get("loss") and not accept_loss:
            raise api_error(
                422,
                "MIGRATION_LOSS_NOT_ACCEPTED",
                f"The migration removes {counts['loss']} items the preview lists; confirm with "
                "acceptLoss: true to remove them",
                {"loss": counts["loss"]},
            )

    if not confirm_job(session, job, check, keep_items=True):
        return False
    job.parameters = {**job.parameters, "acceptLoss": accept_loss}
    return True


def confirm_migration(
    session: Session,
    job_id: str,
    *,
    expected_version: int | None,
    expected_feed_position: int | None,
    accept_loss: bool,
) -> Job:
    """Confirm a waiting migration and commit (:func:`check_confirmation`); confirmed before, it
    answers unchanged."""
    job = load_job(session, job_id)
    if check_confirmation(
        session,
        job,
        expected_version=expected_version,
        expected_feed_position=expected_feed_position,
        accept_loss=accept_loss,
    ):
        session.commit()
    else:
        session.rollback()
    session.refresh(job)
    return job


def require_reviewed(
    session: Session,
    job: Job,
    *,
    reviewed_version: int,
    reviewed_feed_position: int,
    summary: dict[str, Any],
    for_update: bool = False,
) -> None:
    """The workspace, and a named change set, as the preview read them (D74, D83, D92);
    otherwise ``409 MIGRATION_REVIEW_STALE``."""
    assignment, current = load_assignment(session, job.workspace_key, for_update=for_update)
    feed_position = int(
        session.scalar(select(Workspace.feed_position).where(Workspace.key == job.workspace_key))
        or 0
    )
    if "changeSetId" in summary:
        _require_change_set_reviewed(session, job, summary, for_update=for_update)
    if (
        reviewed_version != summary.get("expectedVersion")
        or reviewed_feed_position != summary.get("feedPosition")
        or assignment.version != reviewed_version
        or current.id != _workspace_release_id(session, job)
        or feed_position != reviewed_feed_position
    ):
        raise api_error(
            409,
            "MIGRATION_REVIEW_STALE",
            f"Workspace '{job.workspace_key}' changed after the preview you reviewed; nothing was "
            "migrated. Preview the migration again",
            {
                "workspaceKey": job.workspace_key,
                "reviewedVersion": summary.get("expectedVersion"),
                "currentVersion": assignment.version,
                "reviewedFeedPosition": summary.get("feedPosition"),
                "currentFeedPosition": feed_position,
            },
        )


def moves_change_set(job: Job) -> bool:
    """A ``migration`` job that moves one change set's content (V3, ``change_set_migrations``)
    rather than a workspace's data."""
    return (job.parameters or {}).get("moves") == "changeSet"


def _workspace_release_id(session: Session, job: Job) -> int:
    """The release the workspace ran when the preview read it: the job's current release, or for
    a change set's move the target, which is the workspace's release (D87)."""
    if moves_change_set(job):
        return installed_release(session, job.parameters["targetReleaseId"]).id
    return job.model_release_id


def _require_change_set_reviewed(
    session: Session, job: Job, summary: dict[str, Any], *, for_update: bool
) -> None:
    """The change set at the version the preview read, and the workspace's active publication as
    it was (D83); otherwise ``409 MIGRATION_REVIEW_STALE``."""
    query = select(ChangeSet).where(ChangeSet.id == summary["changeSetId"])
    change_set = session.scalar(query.with_for_update() if for_update else query)
    active = session.scalar(
        select(Workspace.active_publication_id).where(Workspace.key == job.workspace_key)
    )
    current_version = change_set.version if change_set is not None else None
    if current_version != summary.get("changeSetVersion") or active != summary.get(
        "activePublicationId"
    ):
        raise api_error(
            409,
            "MIGRATION_REVIEW_STALE",
            f"Change set '{summary['changeSetId']}' or the publications of workspace "
            f"'{job.workspace_key}' changed after the preview you reviewed; nothing was migrated. "
            "Preview the migration again",
            {
                "workspaceKey": job.workspace_key,
                "changeSetId": summary["changeSetId"],
                "reviewedChangeSetVersion": summary.get("changeSetVersion"),
                "currentChangeSetVersion": current_version,
                "reviewedActivePublicationId": summary.get("activePublicationId"),
                "currentActivePublicationId": active,
            },
        )


def run_execution(
    session: Session,
    job: Job,
    *,
    retention_days: int,
    hold: Callable[[], None],
    renew: Callable[[], None] = lambda: None,
) -> ModelRelease:
    """Execute a confirmed migration in the caller's transaction, which commits it: the target
    release, which the caller loads into the process after the commit. A failure leaves nothing
    changed: the caller rolls back."""
    summary = (job.report or {}).get("migration", {})
    session.execute(
        select(Workspace.key).where(Workspace.key == job.workspace_key).with_for_update()
    )
    if "changeSetId" in summary:
        # Lock order (ARCHITECTURE): the workspace, the change set, then the assignment.
        session.execute(
            select(ChangeSet.id).where(ChangeSet.id == summary["changeSetId"]).with_for_update()
        )
    migration = _Migration.open(session, job)
    current_release = session.get(ModelRelease, job.model_release_id)
    lock_what_activation_changes(
        session, job.workspace_key, migration.target_release.public_id, current_release.public_id
    )
    require_reviewed(
        session,
        job,
        reviewed_version=summary["expectedVersion"],
        reviewed_feed_position=summary["feedPosition"],
        summary=summary,
        for_update=True,
    )
    session.execute(text("DELETE FROM job_items WHERE job_id = :job"), {"job": job.sequence_id})
    migration.prepare()
    renew()
    migration.write_rows()
    renew()
    migration.apply(audit=True)
    renew()
    counts = migration.counts()
    if migration.refusals(listing=False) or counts != summary.get("counts"):
        raise api_error(
            409,
            "MIGRATION_REVIEW_STALE",
            f"Workspace '{job.workspace_key}' no longer migrates as the preview said; nothing was "
            "migrated. Preview the migration again",
            {"workspaceKey": job.workspace_key, "reviewed": summary.get("counts"), "now": counts},
        )
    switch_assignment(session, migration, current_release, summary["expectedVersion"])
    published = {}
    if "changeSetId" in summary:
        renew()
        publication = apply_publication(
            session,
            summary["changeSetId"],
            migration.target,
            migration.target_release.id,
            summary["changeSetVersion"],
            summary.get("activePublicationId"),
        )
        published = {"publicationId": publication.id}
    record_summary(job, counts, **published)
    hold()
    complete_job(session, job, retention_days=retention_days)
    return migration.target_release


def switch_assignment(
    session: Session, migration: _Migration, current_release: ModelRelease, version: int
) -> None:
    """Point the workspace at the target release, as activation does, with its live matrix states
    rebuilt from the migrated records."""
    matrix_states.drop_owner(
        session, matrix_states.Owner("live", migration.workspace_key, migration.workspace_key)
    )
    counts = (migration.job.report or {}).get("migration", {}).get("counts", {})
    switch_workspace_release(
        session,
        migration.workspace_key,
        current_release,
        migration.target_release,
        migration.target,
        version,
        changes={"migrationJobId": migration.job.id, "migrated": counts},
    )


def execute(
    session: Session,
    job: Job,
    *,
    retention_days: int,
    hold: Callable[[], None],
    renew: Callable[[], None] = lambda: None,
) -> None:
    """Run a confirmed migration and commit it once ``hold`` (the worker's lease) allows,
    loading the target release into the process; any failure rolls back and becomes
    ``MIGRATION_FAILED`` (or the refusal it was), nothing changed."""
    try:
        target = run_execution(session, job, retention_days=retention_days, hold=hold, renew=renew)
    except ApiError:
        session.rollback()
        raise
    except LeaseLost:
        raise
    except Exception as exc:
        session.rollback()
        correlation_id = uuid4().hex
        logger.exception(
            "Migration %s failed and changed nothing (correlation ID %s)", job.id, correlation_id
        )
        raise api_error(
            500,
            "MIGRATION_FAILED",
            f"The migration of workspace '{job.workspace_key}' failed and changed nothing: the "
            "workspace keeps its release and its data. Preview it again; if it fails again, "
            "report the correlation ID",
            {"workspaceKey": job.workspace_key, "correlationId": correlation_id},
        ) from exc
    session.commit()
    try:
        model_registry.warm(target.id)
    except Exception:
        model_registry.withdraw(target)
        logger.exception(
            "Migration %s committed, but this process could not load release %s",
            job.id,
            target.public_id,
        )
