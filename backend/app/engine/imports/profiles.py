"""Import profiles: checked against the model and stored (Base 0.9 J2, INTEGRATION_API §J3).

A profile is checked against a model release when it is saved, when it is read under another active
release and when an import starts. Every problem is reported at its JSON pointer into the profile,
never only the first, so a client fixes a profile in one pass:

- a source's application and type, and the type in that application;
- each column's attribute bound to the type and writable; a key attribute bound and ``unique``;
- a parent the type can stand under, bound by a column or fixed by the source (not both); a relationship the two types allow in that direction, and not
  a containment (a parent is its own binding); a related record's type, its parent and relation;
- each ``matchBy`` attribute bound to the type it matches;
- each value map named;
- the sources' order: a source whose parent, relationship or related record's parent names a type
  another source loads runs after it, and a cycle is a problem (``SOURCE_CYCLE``).

Profiles are instance-wide (D65): ``key`` is unique, writes are versioned (optimistic concurrency).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, paginate_statement, text_key
from ...errors import api_error
from ...models.database import ImportProfile, ModelRelease
from ...models.imports import (
    FixedParent,
    ImportProfileCreate,
    ImportProfileDefinition,
    ImportProfileUpdate,
    MatchBy,
    ParentBinding,
    Source,
)
from ...models.schema import EngineModel
from ..model.registry import resolve_model_snapshot
from ..model.traversal import parent_type_keys

_PROFILE_KEYS = (text_key("key", ImportProfile.key, "key"),)


@dataclass(frozen=True)
class Problem:
    path: str
    code: str
    message: str

    def body(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


def check_profile(model: EngineModel, profile: ImportProfileDefinition) -> list[Problem]:
    """Every problem of ``profile`` against ``model``, in the profile's order; none when valid."""
    problems: list[Problem] = []
    for index, source in enumerate(profile.sources):
        problems += _source_problems(model, profile, source, f"/sources/{index}")
    if source_order(model, profile) is None:
        problems.append(
            Problem(
                "/sources",
                "SOURCE_CYCLE",
                "The sources reference each other's types in a cycle, so none can load first; "
                "keep each parent, relationship or related record's parent on one side",
            )
        )
    return problems


def require_valid(model: EngineModel, profile: ImportProfileDefinition) -> None:
    problems = check_profile(model, profile)
    if problems:
        raise invalid_profile(problems)


def invalid_profile(problems: list[Problem]) -> Any:
    return api_error(
        422,
        "INVALID_IMPORT_PROFILE",
        f"The import profile has {len(problems)} problem(s) against the active model release",
        {"problems": [problem.body() for problem in problems]},
    )


def referenced_types(source: Source) -> set[str]:
    """The types a source's rows point at: parents, relationship ends and related records'
    parents."""
    found: set[str] = {source.parent.objectTypeKey} if source.parent is not None else set()
    for binding in source.columns:
        if binding.parent is not None:
            found.add(binding.parent.objectTypeKey)
        if binding.relation is not None:
            found.add(binding.relation.objectTypeKey)
        if binding.relationFlags is not None:
            found.add(binding.relationFlags.objectTypeKey)
        if binding.relatedRecord is not None:
            found.add(binding.relatedRecord.parent.objectTypeKey)
    return found


def source_order(model: EngineModel, profile: ImportProfileDefinition) -> list[int] | None:
    """The sources in the order they load, each after the sources whose types it references (a
    stable order: otherwise as written); ``None`` when they reference each other in a cycle."""
    count = len(profile.sources)
    needs: dict[int, set[int]] = {}
    for index, source in enumerate(profile.sources):
        wanted = referenced_types(source) - {source.objectTypeKey}
        needs[index] = {
            other
            for other, loader in enumerate(profile.sources)
            if other != index and loader.objectTypeKey in wanted
        }
    order: list[int] = []
    while len(order) < count:
        ready = [i for i in range(count) if i not in order and needs[i] <= set(order)]
        if not ready:
            return None
        order.append(ready[0])
    return order


def _source_problems(
    model: EngineModel, profile: ImportProfileDefinition, source: Source, path: str
) -> list[Problem]:
    problems: list[Problem] = []
    if source.rowsWithoutKey == "skip" and source.key is None:
        problems.append(
            Problem(
                f"{path}/rowsWithoutKey",
                "SKIP_NEEDS_KEY",
                "rowsWithoutKey: skip skips rows whose key is empty, and the source has no key",
            )
        )
    application = next((a for a in model.applications if a.key == source.applicationKey), None)
    object_type = model.object_type(source.objectTypeKey)
    if application is None:
        problems.append(
            Problem(
                f"{path}/applicationKey",
                "UNKNOWN_APPLICATION",
                f"Application '{source.applicationKey}' is not in the model",
            )
        )
    if object_type is None:
        problems.append(
            Problem(
                f"{path}/objectTypeKey",
                "UNKNOWN_OBJECT_TYPE",
                f"Object type '{source.objectTypeKey}' is not in the model",
            )
        )
        return problems
    if application is not None and source.objectTypeKey not in application.objectTypeKeys:
        problems.append(
            Problem(
                f"{path}/objectTypeKey",
                "TYPE_NOT_IN_APPLICATION",
                f"Object type '{source.objectTypeKey}' is not in application "
                f"'{source.applicationKey}'",
            )
        )
    if source.key is not None and source.key.attributeTypeKey is not None:
        key = source.key.attributeTypeKey
        problems += _attribute_problems(
            model, source.objectTypeKey, key, f"{path}/key/attributeTypeKey"
        )
        definition = model.attribute_type(key)
        if definition is not None and not definition.features.get("unique"):
            problems.append(
                Problem(
                    f"{path}/key/attributeTypeKey",
                    "KEY_NOT_UNIQUE",
                    f"Attribute '{key}' is not declared unique, so it cannot find one record; "
                    "match by it in a parent or relationship instead",
                )
            )
        if not any(binding.attributeTypeKey == key for binding in source.columns):
            problems.append(
                Problem(
                    f"{path}/key/attributeTypeKey",
                    "KEY_NOT_BOUND",
                    f"No column of the source binds the key attribute '{key}'",
                )
            )
    if source.parent is not None:
        problems += _parent_problems(model, source.objectTypeKey, source.parent, f"{path}/parent")
        if any(binding.parent is not None for binding in source.columns):
            problems.append(
                Problem(
                    f"{path}/parent",
                    "PARENT_BOUND_TWICE",
                    "The source sets every row's parent, so no column of it can bind a parent",
                )
            )
    if source.key is not None and source.key.field == "name" and not any(
        binding.field == "name" for binding in source.columns
    ):
        problems.append(
            Problem(
                f"{path}/key/field",
                "KEY_NOT_BOUND",
                "No column of the source binds the name the key finds records by",
            )
        )
    for index, binding in enumerate(source.columns):
        at = f"{path}/columns/{index}"
        if binding.valueMap is not None and binding.valueMap not in profile.valueMaps:
            problems.append(
                Problem(
                    f"{at}/valueMap",
                    "UNKNOWN_VALUE_MAP",
                    f"Value map '{binding.valueMap}' is not defined",
                )
            )
        if binding.attributeTypeKey is not None:
            problems += _attribute_problems(
                model,
                source.objectTypeKey,
                binding.attributeTypeKey,
                f"{at}/attributeTypeKey",
                writable=True,
            )
        elif binding.parent is not None:
            problems += _parent_problems(model, source.objectTypeKey, binding.parent, f"{at}/parent")
        elif binding.relation is not None or binding.relationFlags is not None:
            relation = binding.relation or binding.relationFlags
            name = "relation" if binding.relation is not None else "relationFlags"
            problems += _relation_problems(
                model,
                source.objectTypeKey,
                relation.relationTypeKey,
                relation.direction,
                relation.objectTypeKey,
                f"{at}/{name}",
            )
            if model.object_type(relation.objectTypeKey) is not None:
                problems += _match_problems(
                    model, relation.objectTypeKey, relation.matchBy, f"{at}/{name}/matchBy"
                )
            problems += _create_problems(relation.missing, relation.matchBy, f"{at}/{name}")
            if binding.relation is not None and binding.relation.attributes:
                problems += _relation_value_problems(
                    model, source.objectTypeKey, binding.relation, f"{at}/relation/attributes"
                )
            if binding.relationFlags is not None:
                missing = [
                    c for c in binding.columns or [] if c not in binding.relationFlags.targets
                ]
                if missing:
                    problems.append(
                        Problem(
                            f"{at}/relationFlags/targets",
                            "FLAG_WITHOUT_TARGET",
                            f"Columns without a target: {', '.join(missing)}",
                        )
                    )
        elif binding.relatedRecord is not None:
            problems += _related_problems(
                model, source.objectTypeKey, binding.relatedRecord, f"{at}/relatedRecord"
            )
    return problems


def _related_problems(
    model: EngineModel, owner_type: str, related: Any, path: str
) -> list[Problem]:
    problems: list[Problem] = []
    application = next((a for a in model.applications if a.key == related.applicationKey), None)
    if application is None:
        problems.append(
            Problem(
                f"{path}/applicationKey",
                "UNKNOWN_APPLICATION",
                f"Application '{related.applicationKey}' is not in the model",
            )
        )
    if model.object_type(related.objectTypeKey) is None:
        return [*problems, _unknown_type(f"{path}/objectTypeKey", related.objectTypeKey)]
    if application is not None and related.objectTypeKey not in application.objectTypeKeys:
        problems.append(
            Problem(
                f"{path}/objectTypeKey",
                "TYPE_NOT_IN_APPLICATION",
                f"Object type '{related.objectTypeKey}' is not in application '{related.applicationKey}'",
            )
        )
    problems += _relation_problems(
        model, owner_type, related.relationTypeKey, related.direction, related.objectTypeKey, path
    )
    parent = related.parent
    if model.object_type(parent.objectTypeKey) is None:
        problems.append(_unknown_type(f"{path}/parent/objectTypeKey", parent.objectTypeKey))
    elif parent.objectTypeKey not in parent_type_keys(model, related.objectTypeKey):
        problems.append(
            Problem(
                f"{path}/parent",
                "PARENT_NOT_ALLOWED",
                f"A '{related.objectTypeKey}' record cannot stand under a '{parent.objectTypeKey}' record",
            )
        )
    else:
        problems += _match_problems(
            model, parent.objectTypeKey, parent.matchBy, f"{path}/parent/matchBy"
        )
    problems += _create_problems(parent.missing, parent.matchBy, f"{path}/parent")
    if related.attributeTypeKey is not None:
        problems += _attribute_problems(
            model,
            related.objectTypeKey,
            related.attributeTypeKey,
            f"{path}/attributeTypeKey",
            writable=True,
        )
    if related.matchBy is not None:
        problems += _attribute_problems(
            model,
            related.objectTypeKey,
            related.matchBy.attributeTypeKey,
            f"{path}/matchBy/attributeTypeKey",
        )
    return problems


def _relation_problems(
    model: EngineModel,
    own_type: str,
    relation_type: str,
    direction: str,
    other_type: str,
    path: str,
) -> list[Problem]:
    if model.relation_type(relation_type) is None:
        return [
            Problem(
                f"{path}/relationTypeKey",
                "UNKNOWN_RELATION_TYPE",
                f"Relation type '{relation_type}' is not in the model",
            )
        ]
    if model.object_type(other_type) is None:
        return [_unknown_type(f"{path}/objectTypeKey", other_type)]
    source, target = (own_type, other_type) if direction == "outgoing" else (other_type, own_type)
    containment = relation_type in model.containment_relation_keys(target)
    if model.allowed_relation(relation_type, source, target) is None or containment:
        return [
            Problem(
                path,
                "RELATION_NOT_ALLOWED",
                f"The model allows no '{relation_type}' relationship from '{source}' to '{target}'"
                + (" other than containment, which a parent binding sets" if containment else ""),
            )
        ]
    return []


def _relation_value_problems(
    model: EngineModel, own_type: str, relation: Any, path: str
) -> list[Problem]:
    """A relationship's value columns name attributes its binding carries (0.9 J6)."""
    source, target = (
        (own_type, relation.objectTypeKey)
        if relation.direction == "outgoing"
        else (relation.objectTypeKey, own_type)
    )
    binding = model.allowed_relation(relation.relationTypeKey, source, target)
    if binding is None:
        return []
    return [
        Problem(
            f"{path}/{index}/attributeTypeKey",
            "ATTRIBUTE_NOT_BOUND",
            f"Relationship '{relation.relationTypeKey}' from '{source}' to '{target}' carries no "
            f"attribute '{value.attributeTypeKey}'",
        )
        for index, value in enumerate(relation.attributes)
        if value.attributeTypeKey not in binding.attributeTypeKeys
    ]


def _parent_problems(
    model: EngineModel, type_key: str, parent: ParentBinding | FixedParent, path: str
) -> list[Problem]:
    """A parent a column binds or a source fixes (0.10 A8c, D141): a type the source's records can
    stand under, matched by what it binds, created only by name."""
    problems: list[Problem] = []
    if model.object_type(parent.objectTypeKey) is None:
        problems.append(_unknown_type(f"{path}/objectTypeKey", parent.objectTypeKey))
    elif parent.objectTypeKey not in parent_type_keys(model, type_key):
        problems.append(
            Problem(
                path,
                "PARENT_NOT_ALLOWED",
                f"A '{type_key}' record cannot stand under a '{parent.objectTypeKey}' record",
            )
        )
    else:
        problems += _match_problems(model, parent.objectTypeKey, parent.matchBy, f"{path}/matchBy")
    return problems + _create_problems(parent.missing, parent.matchBy, path)


def _create_problems(missing: str, match: MatchBy, path: str) -> list[Problem]:
    """A record created for a cell takes the cell as its name, so only a match by name creates."""
    if missing == "create" and match.field != "name":
        return [
            Problem(
                f"{path}/missing",
                "CREATE_NEEDS_NAME_MATCH",
                "Only a match by name creates the records it does not find",
            )
        ]
    return []


def _match_problems(
    model: EngineModel, object_type: str, match: MatchBy, path: str
) -> list[Problem]:
    if match.attributeTypeKey is None:
        return []
    return _attribute_problems(
        model, object_type, match.attributeTypeKey, f"{path}/attributeTypeKey"
    )


def _attribute_problems(
    model: EngineModel, object_type: str, key: str, path: str, *, writable: bool = False
) -> list[Problem]:
    if model.attribute_type(key) is None:
        return [Problem(path, "UNKNOWN_ATTRIBUTE", f"Attribute '{key}' is not in the model")]
    definition = model.object_type(object_type)
    binding = (
        next((b for b in definition.attributes if b.attributeTypeKey == key), None)
        if definition
        else None
    )
    if binding is None:
        return [
            Problem(
                path,
                "ATTRIBUTE_NOT_BOUND",
                f"Object type '{object_type}' does not bind attribute '{key}'",
            )
        ]
    if writable and binding.readOnly:
        return [
            Problem(
                path, "ATTRIBUTE_READ_ONLY", f"Attribute '{key}' is read-only on '{object_type}'"
            )
        ]
    return []


def _unknown_type(path: str, key: str) -> Problem:
    return Problem(path, "UNKNOWN_OBJECT_TYPE", f"Object type '{key}' is not in the model")


# --- storage -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StoredProfile:
    """A stored profile with what reading it under the active release found."""

    profile: ImportProfile
    checked_against: str
    problems: list[Problem]


def definition_of(payload: ImportProfileDefinition) -> dict[str, Any]:
    return payload.model_dump(
        mode="json", include={"csv", "sources", "valueMaps"}, exclude_none=True
    )


def parsed(profile: ImportProfile) -> ImportProfileDefinition:
    return ImportProfileDefinition.model_validate(profile.definition)


def create_profile(session: Session, payload: ImportProfileCreate) -> StoredProfile:
    snapshot = resolve_model_snapshot(session, None)
    require_valid(snapshot.model, payload)
    now = datetime.now(UTC)
    profile = ImportProfile(
        key=payload.key,
        name=payload.name,
        version=1,
        definition=definition_of(payload),
        checked_release_id=snapshot.release_db_id,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise api_error(
            409, "IMPORT_PROFILE_EXISTS", f"An import profile '{payload.key}' already exists"
        ) from None
    session.commit()
    return StoredProfile(profile, snapshot.release_id, [])


def load_profile(session: Session, key: str, *, for_update: bool = False) -> ImportProfile:
    statement = select(ImportProfile).where(ImportProfile.key == key)
    if for_update:
        statement = statement.with_for_update()
    profile = session.scalar(statement)
    if profile is None:
        raise api_error(404, "IMPORT_PROFILE_NOT_FOUND", f"Import profile '{key}' not found")
    return profile


def read_profile(session: Session, key: str) -> StoredProfile:
    return stored(session, load_profile(session, key))


def stored(session: Session, profile: ImportProfile) -> StoredProfile:
    """The profile with its problems under the active release, and the release it was saved
    against."""
    snapshot = resolve_model_snapshot(session, None)
    problems = check_profile(snapshot.model, parsed(profile))
    checked = session.scalar(
        select(ModelRelease.public_id).where(ModelRelease.id == profile.checked_release_id)
    )
    return StoredProfile(profile, checked, problems)


def stored_page(session: Session, profiles: list[ImportProfile]) -> list[StoredProfile]:
    """A page of profiles read under the active release, with one read of their releases."""
    snapshot = resolve_model_snapshot(session, None)
    releases = dict(
        session.execute(
            select(ModelRelease.id, ModelRelease.public_id).where(
                ModelRelease.id.in_({profile.checked_release_id for profile in profiles})
            )
        )
        .tuples()
        .all()
    )
    return [
        StoredProfile(
            profile,
            releases[profile.checked_release_id],
            check_profile(snapshot.model, parsed(profile)),
        )
        for profile in profiles
    ]


def profile_page(session: Session, page: PageRequest, page_size: int) -> Page[ImportProfile]:
    """Profiles in key order."""
    return paginate_statement(
        session,
        select(ImportProfile),
        keys=_PROFILE_KEYS,
        scope="import-profiles",
        filters={},
        page=page,
        page_size=page_size,
        message="Import profile list cursor is invalid",
    )


def update_profile(session: Session, key: str, payload: ImportProfileUpdate) -> StoredProfile:
    snapshot = resolve_model_snapshot(session, None)
    profile = load_profile(session, key, for_update=True)
    _claim(profile, payload.expectedVersion)
    require_valid(snapshot.model, payload)
    profile.name = payload.name
    profile.definition = definition_of(payload)
    profile.version += 1
    profile.checked_release_id = snapshot.release_db_id
    profile.updated_at = datetime.now(UTC)
    session.commit()
    return StoredProfile(profile, snapshot.release_id, [])


def delete_profile(session: Session, key: str, expected_version: int) -> None:
    resolve_model_snapshot(session, None)
    profile = load_profile(session, key, for_update=True)
    _claim(profile, expected_version)
    session.execute(delete(ImportProfile).where(ImportProfile.sequence_id == profile.sequence_id))
    session.commit()


def _claim(profile: ImportProfile, expected_version: int) -> None:
    if profile.version != expected_version:
        raise api_error(
            409,
            "IMPORT_PROFILE_VERSION_CONFLICT",
            f"Import profile '{profile.key}' is at version {profile.version}, not {expected_version}",
            {"currentVersion": profile.version},
        )
