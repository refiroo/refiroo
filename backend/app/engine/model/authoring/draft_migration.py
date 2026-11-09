"""The migration a draft states (MG, MG-D3): which type becomes which, which attribute and relation
type becomes which, which application a moved type goes to, the parent its records get, and the
records a split or an attribute turned into a list type creates.

It is derived each time it is read, from the entries of the draft's history that stand now (an undone
step takes its part away) and from the draft's model set against its base release's. A step gives
the identity of an element (a key change, a merge, a split, a conversion); the two models give where
each type stands now. Nothing is stored, so the migration always matches the steps.

The result is the input of a workspace migration (``typeMappings``, ``relationTypeMappings``,
``splits``, ``listConversions``) with ``rows`` describing what each part does, ``keyChanges`` with the
consumer APIs of the base release that name the old key, and the steps that need a migration.
"""

from typing import Any

from sqlalchemy.orm import Session

from ....errors import ApiError
from ....models.database import ModelDraft, ModelRelease
from ..compiler import compile_model
from ..migrations import arrived_applications, check_landing
from ..registry import resolve_pinned_release
from ..workspace_models import load_assignment
from .history import effective_entries
from .kinds import element_of
from .references import consumer_slots, known_keys, names_in_slot
from .released import base_release, impact, released_atoms


def _items(model: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return [item for item in model.get(name) or [] if isinstance(item, dict)]


def _key_of(value: Any) -> str | None:
    """A relation type argument as an operation stores it: a key, or an object holding its key."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("key"), str):
        return value["key"]
    return None


class _Identity:
    """Which base element is which element now: ``now[base key]`` is its key in the draft, or none
    once removed."""

    def __init__(self, keys: list[str]) -> None:
        self.now: dict[str, str | None] = {key: key for key in keys}
        self.renamed: set[str] = set()

    def rename(self, old: str, new: str) -> None:
        for base, current in self.now.items():
            if current == old:
                self.now[base] = new
                self.renamed.add(base)

    def merge(self, source: str, into: str) -> None:
        for base, current in self.now.items():
            if current == source:
                self.now[base] = into

    def remove(self, key: str) -> None:
        for base, current in self.now.items():
            if current == key:
                self.now[base] = None

    def base_of(self, current: str) -> str | None:
        return next((base for base, now in self.now.items() if now == current), None)


def derive(
    session: Session,
    draft: ModelDraft,
    *,
    workspace_key: str | None = None,
    against: ModelRelease | None = None,
    to: ModelRelease | None = None,
) -> dict[str, Any]:
    """The migration ``draft`` states against its base release; ``workspace_key`` counts what it
    moves in that one workspace instead of in every workspace running the model.

    Installing a draft bases it on the release it installed, so a migration read afterwards would
    be empty. ``against`` names the release the migration starts from (the one a workspace runs) and
    ``to`` the release it goes to (the one installed from the draft): the steps are read against the
    first, whatever the draft was based on when they were applied, and the models are the two
    releases'."""
    if against is None and workspace_key is not None:
        # The migration starts from the release the workspace runs: after an install the draft is
        # based on the release it installed, which a migration read would otherwise start from.
        running = load_assignment(session, workspace_key)[1]
        own = base_release(session, draft)
        if own is None or running.release_key == own.release_key:
            against = running
    release = against or base_release(session, draft)
    base = release.model_json if release is not None else {}
    model = (to.model_json if to is not None else draft.model_json) or {}
    model_key = release.release_key if release is not None else None
    types = _Identity([item["key"] for item in _items(base, "objectTypes")])
    attributes = _Identity([item["key"] for item in _items(base, "attributeTypes")])
    relations = _Identity([item["key"] for item in _items(base, "relationTypes")])
    applications = _Identity([item["key"] for item in _items(base, "applications")])
    splits: list[dict[str, Any]] = []
    conversions: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    notes: list[dict[str, str]] = []
    held = released_atoms(base)
    base_type_keys = {item["key"] for item in _items(base, "objectTypes")}

    for entry in effective_entries(session, draft):
        parameters = entry.parameters or {}
        marks = (entry.effects or {}).get("migration") or []
        if marks:
            steps.append(
                {
                    "step": entry.step,
                    "sequence": entry.sequence,
                    "kind": entry.kind,
                    "migration": marks,
                }
            )
        if entry.kind == "setKey":
            reference = parameters.get("element") or {}
            old = (entry.inverse or {}).get("key")
            new = parameters.get("key")
            if not isinstance(old, str) or not isinstance(new, str):
                continue
            if "objectType" in reference:
                types.rename(old, new)
                _rewrite(splits, conversions, "from", old, new)
                _rewrite(splits, conversions, "to", old, new)
            elif "attributeType" in reference:
                attributes.rename(old, new)
                _rewrite(splits, conversions, "attribute", old, new)
            elif "relationType" in reference:
                relations.rename(old, new)
                _rewrite(splits, conversions, "relation", old, new)
            elif "applicationKey" in reference:
                applications.rename(old, new)
        elif entry.kind == "mergeObjectTypes":
            types.merge(parameters["from"], parameters["into"])
            _rewrite(splits, conversions, "from", parameters["from"], parameters["into"])
            _rewrite(splits, conversions, "to", parameters["from"], parameters["into"])
        elif entry.kind == "removeObjectType":
            types.remove(parameters["objectType"])
        elif entry.kind == "removeAttributeType":
            attributes.remove(parameters["attributeType"])
        elif entry.kind == "removeRelationType":
            relations.remove(parameters["relationType"])
        elif entry.kind == "splitObjectType":
            if parameters.get("key") in base_type_keys:
                continue  # Its new type is in the release the migration starts from already.
            source = types.base_of(parameters["objectType"])
            moved = [attributes.base_of(a) for a in parameters.get("attributes") or []]
            relation = _key_of(parameters.get("relationType"))
            if source is not None and relation and all(moved):
                splits.append(
                    {
                        "fromObjectTypeKey": parameters["objectType"],
                        "toObjectTypeKey": parameters["key"],
                        "attributes": list(parameters.get("attributes") or []),
                        "relationTypeKey": relation,
                        "cardinality": parameters.get("cardinality") or "many-to-many",
                    }
                )
        elif entry.kind == "convertAttributeToListType":
            if parameters.get("key") in base_type_keys:
                continue
            source = types.base_of(parameters["objectType"])
            attribute = attributes.base_of(parameters["attributeType"])
            relation = _key_of(parameters.get("relationType"))
            if source is not None and attribute is not None and relation:
                conversions.append(
                    {
                        "fromObjectTypeKey": parameters["objectType"],
                        "attributeTypeKey": parameters["attributeType"],
                        "toObjectTypeKey": parameters["key"],
                        "relationTypeKey": relation,
                    }
                )
        elif entry.kind == "replaceModel":
            notes.append(
                {
                    "code": "MODEL_REPLACED",
                    "message": "A step replaced the whole model, so what became what before it is not "
                    "known; check the mappings against the types",
                }
            )

    # The spawns name the base keys the workspace's model holds.
    request_splits = []
    for item in splits:
        source = types.base_of(item["fromObjectTypeKey"])
        moved = [attributes.base_of(a) for a in item["attributes"]]
        if source is None or not all(moved):
            continue
        request_splits.append(
            {
                **item,
                "fromObjectTypeKey": source,
                "attributes": moved,
                "toObjectTypeKey": item["toObjectTypeKey"],
            }
        )
    request_conversions = []
    for item in conversions:
        source = types.base_of(item["fromObjectTypeKey"])
        attribute = attributes.base_of(item["attributeTypeKey"])
        if source is None or attribute is None:
            continue
        request_conversions.append(
            {**item, "fromObjectTypeKey": source, "attributeTypeKey": attribute}
        )

    base_types = {item["key"]: item for item in _items(base, "objectTypes")}
    draft_types = {item["key"]: item for item in _items(model, "objectTypes")}
    base_apps = {
        item["key"]: set(item.get("objectTypeKeys") or []) for item in _items(base, "applications")
    }
    draft_apps = {
        item["key"]: set(item.get("objectTypeKeys") or []) for item in _items(model, "applications")
    }

    type_mappings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for base_key, base_type in base_types.items():
        now = types.now.get(base_key)
        draft_type = draft_types.get(now) if now else None
        if draft_type is None:
            continue
        bound_before = {b["attributeTypeKey"] for b in base_type.get("attributes") or []}
        sources = []
        for binding in draft_type.get("attributes") or []:
            key = binding["attributeTypeKey"]
            origin = attributes.base_of(key)
            if origin is not None and origin != key and origin in bound_before:
                sources.append({"attributeTypeKey": key, "from": origin})
        was_in = {
            applications.now.get(app) for app, members in base_apps.items() if base_key in members
        }
        now_in = {app for app, members in draft_apps.items() if now in members}
        to_application = application_target(was_in, now_in)
        parent = _parent(base_type, draft_type)
        changed = (
            now != base_key or bool(sources) or to_application is not None or parent != "unchanged"
        )
        if not changed:
            continue
        mapping: dict[str, Any] = {
            "fromObjectTypeKey": base_key,
            "toObjectTypeKey": now,
            "attributes": sources,
        }
        if to_application is not None:
            mapping["toApplicationKey"] = to_application
        # A parent change alone needs no mapping: the migration reads it from the two models.
        if now != base_key or sources or to_application is not None:
            type_mappings.append(mapping)
        rows.append(
            {
                "fromObjectTypeKey": base_key,
                "toObjectTypeKey": now,
                "fromName": base_type.get("name") or base_key,
                "toName": draft_type.get("name") or now,
                "fromApplicationKeys": sorted(a for a in was_in if a),
                "toApplicationKeys": sorted(now_in),
                "toApplicationKey": to_application,
                "parent": parent,
                "attributes": sources,
                "records": _records(session, base_key, model_key, workspace_key),
            }
        )

    relation_mappings = [
        {"fromRelationTypeKey": base_key, "toRelationTypeKey": now}
        for base_key, now in relations.now.items()
        if now is not None and now != base_key
    ]

    return {
        "baseReleaseId": release.public_id if release is not None else None,
        "draftVersion": draft.version,
        "required": bool(
            (steps and against is None)
            or type_mappings
            or relation_mappings
            or request_splits
            or request_conversions
        ),
        "steps": steps,
        "typeMappings": type_mappings,
        "relationTypeMappings": relation_mappings,
        "splits": request_splits,
        "listConversions": request_conversions,
        "rows": rows,
        "keyChanges": _key_changes(base, held, types, attributes, relations, applications),
        "notes": notes,
    }


def _rewrite(
    splits: list[dict[str, Any]], conversions: list[dict[str, Any]], part: str, old: str, new: str
) -> None:
    """A later key change reaches the split or conversion an earlier step recorded."""
    fields = {
        "from": ("fromObjectTypeKey",),
        "to": ("toObjectTypeKey",),
        "relation": ("relationTypeKey",),
        "attribute": ("attributeTypeKey",),
    }[part]
    for item in (*splits, *conversions):
        for name in fields:
            if item.get(name) == old:
                item[name] = new
        if part == "attribute" and old in (item.get("attributes") or []):
            item["attributes"] = [new if key == old else key for key in item["attributes"]]


def application_target(was_in: set[str | None], now_in: set[str]) -> str | None:
    """The application the records of a type go to when it stands in another application now: the
    one it gained, where it left one. A type that left no application keeps its records where they
    are, and one that only left (the target lists it elsewhere) names no destination: the migration
    sends its records to the one application that lists it, or lists them as lost."""
    left = {app for app in was_in if app} - now_in
    arrived = arrived_applications(was_in, now_in)
    return arrived[0] if left and arrived else None


def _parent(before: dict[str, Any], after: dict[str, Any]) -> str:
    """What the records of a type get for a parent: ``unchanged``, ``topLevel`` (the type stands at
    the top now) or ``changed`` (it is under other types, so records the new parents do not hold are
    refused in the preview)."""
    was = set((before.get("behavior") or {}).get("parentRelationTypeKeys") or [])
    now = set((after.get("behavior") or {}).get("parentRelationTypeKeys") or [])
    if was and not now:
        return "topLevel"
    if was != now:
        return "changed"
    return "unchanged"


def _records(
    session: Session, type_key: str, model_key: str | None, workspace_key: str | None
) -> dict[str, int | str]:
    return impact(session, f"objectType:{type_key}", model_key, workspace_key)


def _key_changes(
    base: dict[str, Any],
    held: frozenset[str],
    types: _Identity,
    attributes: _Identity,
    relations: _Identity,
    applications: _Identity,
) -> list[dict[str, Any]]:
    """Each released element whose key changed, with the consumer APIs of the base release that name
    the old key: integrations naming it must change with it (MG-D2)."""
    known = known_keys(base)
    naming: dict[tuple[str, str], list[str]] = {}
    for slot in consumer_slots(base):
        api = (
            slot.path[1].get("key")
            if len(slot.path) > 1 and isinstance(slot.path[1], dict)
            else None
        )
        for kind, key in names_in_slot(base, slot, known):
            if api and api not in naming.setdefault((kind, key), []):
                naming[(kind, key)].append(api)
    apis = {item["key"]: item.get("name") or item["key"] for item in _items(base, "consumerApis")}
    found = []
    for label, atom_kind, identity, lookup in (
        ("objectType", "objectType", types, "objectType"),
        ("attributeType", "attributeType", attributes, "attributeType"),
        ("relationType", "relationType", relations, "relationKey"),
        ("applicationKey", "application", applications, ""),
    ):
        for old in sorted(identity.renamed):
            new = identity.now.get(old)
            if new is None or new == old or f"{atom_kind}:{old}" not in held:
                continue
            names = naming.get((lookup, old), []) if lookup else []
            if label == "relationType":
                reverse = next(
                    (
                        r.get("reverseKey")
                        for r in _items(base, "relationTypes")
                        if r.get("key") == old
                    ),
                    None,
                )
                names = (
                    sorted({*names, *naming.get(("relationKey", reverse), [])})
                    if reverse
                    else names
                )
            found.append(
                {
                    "element": element_of(f"{atom_kind}:{old}"),
                    "from": old,
                    "to": new,
                    "consumerApis": [{"key": api, "name": apis.get(api, api)} for api in names],
                }
            )
    return found


def landing(
    session: Session,
    draft: ModelDraft,
    workspace_key: str,
    migration: dict[str, Any],
    to: ModelRelease | None = None,
) -> dict[str, Any] | None:
    """What the migration would do to the live records of ``workspace_key`` if the draft's model
    were its target, every record checked and nothing written (the preview's own check): records that
    move, records and relationships it creates, what it would lose and what it would refuse. None
    when the draft is not valid or the workspace's model does not fit the mappings (a workspace on
    another model)."""
    compiled = compile_model(to.model_json if to is not None else draft.model_json)
    if not compiled.valid or compiled.model is None:
        return None
    _assignment, running = load_assignment(session, workspace_key)
    current = resolve_pinned_release(session, running.id).model
    try:
        found = check_landing(
            session,
            workspace_key,
            current,
            compiled.model,
            migration["typeMappings"],
            {
                "relationTypeMappings": migration["relationTypeMappings"],
                "splits": migration["splits"],
                "listConversions": migration["listConversions"],
            },
        )
    except ApiError:
        return None
    return {
        "workspaceKey": workspace_key,
        "moved": found.moved,
        "createdRecords": found.created_records,
        "createdRelationships": found.created_relationships,
        "losses": [
            {"objectTypeKey": key, **counts} for key, counts in sorted(found.losses.items())
        ],
        "refused": [
            {
                "objectTypeKey": item.type_key,
                "code": item.code,
                "message": item.message,
                "count": item.count,
                "examples": list(item.examples),
            }
            for item in found.refusals
        ],
    }
