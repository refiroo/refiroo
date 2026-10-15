"""Shared HTTP + direct-persistence helpers for WP8 lifecycle packages.

These helpers mirror the in-file helpers used by ``test_wp8_change_set_lifecycle.py`` so later packages
(publishing, withdrawal, publications) can reuse one small support module.  Every object/relation create
through the canonical CRUD routers carries the explicit ``changeSetId`` and
``expectedChangeSetVersion`` claims, and ``change set["version"]`` is kept in sync from the response
so a caller always knows the latest aggregate concurrency token.
"""

import json
from uuid import uuid4

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models.database import (
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    ModelRelease,
    Publication,
    Workspace,
    WorkspaceModel,
)


def unique_key(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def create_workspace(client, key: str) -> dict:
    response = client.post("/api/v1/workspaces", json={"key": key, "label": key})
    assert response.status_code == 201, response.text
    return response.json()


def create_change_set(
    client,
    workspace_key: str,
    *,
    name: str | None = None,
    derived_from_publication_id: str | None = None,
    source: str | None = None,
    expected_status: int = 201,
):
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if derived_from_publication_id is not None:
        payload["derivedFromPublicationId"] = derived_from_publication_id
    if source is not None:
        payload["source"] = source
    response = client.post(f"/api/v1/workspaces/{workspace_key}/change-sets", json=payload)
    assert response.status_code == expected_status, response.text
    return response


def attribute(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def create_object(
    client,
    change_set: dict,
    application_key: str,
    object_type_key: str,
    name: str,
    *,
    attributes=None,
    parent_object_id: str | None = None,
    initial_relations=None,
    expected_status: int = 201,
):
    payload = {
        "applicationKey": application_key,
        "objectTypeKey": object_type_key,
        "name": name,
        "attributes": attributes or [],
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
    }
    if parent_object_id is not None:
        payload["parentObjectId"] = parent_object_id
    if initial_relations is not None:
        payload["initialRelations"] = initial_relations
    response = client.post("/api/v1/objects", json=payload)
    assert response.status_code == expected_status, response.text
    if response.status_code == 201:
        change_set["version"] = response.json()["changeSetVersion"]
    return response


def update_object(
    client,
    change_set: dict,
    object_type_key: str,
    object_id: str,
    *,
    payload: dict,
    expected_status: int = 200,
):
    body = {
        **payload,
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
    }
    response = client.patch(
        f"/api/v1/objects/{object_type_key}/{object_id}", json=body
    )
    assert response.status_code == expected_status, response.text
    if response.status_code == 200:
        change_set["version"] = response.json()["changeSetVersion"]
    return response


def create_relation(
    client,
    change_set: dict,
    relation_type_key: str,
    from_object_id: str,
    to_object_id: str,
    *,
    attributes=None,
    expected_status: int = 201,
):
    response = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": relation_type_key,
            "fromObjectId": from_object_id,
            "toObjectId": to_object_id,
            "attributes": attributes or {},
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert response.status_code == expected_status, response.text
    if response.status_code == 201:
        change_set["version"] = response.json()["changeSetVersion"]
    return response


def validate_change_set(client, change_set_id: str):
    response = client.post(f"/api/v1/change-sets/{change_set_id}/validation")
    assert response.status_code == 200, response.text
    return response.json()


def publish_change_set(
    client,
    change_set_id: str,
    *,
    expected_change_set_version: int,
    expected_active_publication_id: str | None = None,
    explicit_null_active_publication: bool = False,
    expected_status: int = 200,
):
    """POST the activation route, asserting the caller's claimed active publication.

    ``expected_active_publication_id=None`` with ``explicit_null_active_publication=False`` omits the claim
    entirely; pass ``explicit_null_active_publication=True`` to send an explicit ``null`` claim (the
    route treats both identically, but the explicit form is what "no active publication" callers send).
    """
    payload = {"expectedChangeSetVersion": expected_change_set_version}
    if explicit_null_active_publication:
        payload["expectedActivePublicationId"] = None
    elif expected_active_publication_id is not None:
        payload["expectedActivePublicationId"] = expected_active_publication_id
    response = client.post(f"/api/v1/change-sets/{change_set_id}/publication", json=payload)
    assert response.status_code == expected_status, response.text
    return response


def withdraw_publication(client, publication_id: str, *, expected_status: int = 204):
    """POST the publication-withdrawal route; the path id is the claimed current publication.

    Returns the raw ``requests``/``TestClient`` response so callers can assert body fields for
    conflict cases; on success the route returns 204 with no body.
    """
    response = client.post(f"/api/v1/publications/{publication_id}/withdrawal")
    assert response.status_code == expected_status, response.text
    return response


def workspace_row(workspace_key: str) -> Workspace:
    with SessionLocal() as session:
        workspace = session.scalar(select(Workspace).where(Workspace.key == workspace_key))
        assert workspace is not None, f"Workspace '{workspace_key}' not found"
        return workspace


def workspace_active_publication_id(workspace_key: str) -> str | None:
    return workspace_row(workspace_key).active_publication_id


def change_sets(workspace_key: str) -> list[Publication]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(Publication)
                .where(Publication.workspace_key == workspace_key)
                .order_by(Publication.publication_number)
            )
        )


def publication_status(publication_id: str) -> str:
    with SessionLocal() as session:
        publication = session.scalar(
            select(Publication).where(Publication.id == publication_id)
        )
        assert publication is not None, f"Publication '{publication_id}' not found"
        return publication.status


def publication_counts(publication_id: str) -> tuple[int, int]:
    """Count the immutable snapshot rows (objects, relations) of a publication."""
    from app.models.database import PublicationObject, PublicationRelation

    with SessionLocal() as session:
        objects = session.scalar(
            select(func.count())
            .select_from(PublicationObject)
            .where(PublicationObject.publication_id == publication_id)
        )
        relations = session.scalar(
            select(func.count())
            .select_from(PublicationRelation)
            .where(PublicationRelation.publication_id == publication_id)
        )
    return int(objects or 0), int(relations or 0)


def published_object(client, workspace_key: str, object_type_key: str, object_id: str):
    """Return a published (active) object read, or None when it is not visible."""
    response = client.get(
        f"/api/v1/objects/{object_type_key}/{object_id}", params={"workspaceKey": workspace_key}
    )
    if response.status_code == 404:
        return None
    assert response.status_code == 200, response.text
    return response.json()


def published_relations(client, workspace_key: str, object_id: str) -> list[dict]:
    response = client.get(
        "/api/v1/relations",
        params={"objectId": object_id, "workspaceKey": workspace_key, "pageSize": 500},
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _graph_snapshot(client, context_params: dict, object_types) -> str:
    """Canonical JSON of a workspace graph read through one read context.

    ``context_params`` selects the read context for both object collections and the per-anchor
    relation feeds: ``{"workspaceKey": key}`` for the published active projection,
    ``{"publicationId": id}`` for an immutable publication snapshot, and
    ``{"changeSetId": id}`` for a mutable change set's effective membership.  Only structural fields
    are captured (never the fabricated request-time ``createdAt``/``updatedAt`` timestamps emitted by
    the change set/publication builders), so two snapshots are comparable across read contexts.
    """
    snapshot: dict[str, list] = {"objects": [], "relations": []}
    params = {"pageSize": 500, **context_params}
    for object_type in object_types:
        response = client.get(f"/api/v1/objects/{object_type}", params=params)
        assert response.status_code == 200, response.text
        for item in response.json()["items"]:
            snapshot["objects"].append(
                (
                    item["objectTypeKey"],
                    item["id"],
                    item["name"],
                    item["parentObjectId"],
                    tuple(
                        sorted((attribute["attributeTypeKey"], attribute["value"]) for attribute in item["attributes"])
                    ),
                )
            )
            anchor = client.get(
                "/api/v1/relations",
                params={"objectId": item["id"], **params},
            )
            assert anchor.status_code == 200, anchor.text
            for relation in anchor.json()["items"]:
                snapshot["relations"].append(
                    (
                        relation["direction"],
                        relation["relation"]["relationTypeKey"],
                        relation["relation"]["fromObjectId"],
                        relation["relation"]["toObjectId"],
                        tuple(
                            sorted(
                                (key, value)
                                for key, value in (relation["relation"]["attributes"] or {}).items()
                            )
                        ),
                    )
                )
    return json.dumps(snapshot, sort_keys=True, default=str)


def graph_snapshot_sets(snapshot_json: str) -> tuple[set, set]:
    """Return ``(objects, relations)`` as sets so order-insensitive content comparison is possible.

    ``json.dumps`` degrades the captured tuples into JSON arrays, so every nested array is converted
    back into a tuple before the entries become hashable set elements.
    """

    def object_entry(entry: list) -> tuple:
        return (
            entry[0],
            entry[1],
            entry[2],
            entry[3],
            tuple((pair[0], pair[1]) for pair in entry[4]),
        )

    def relation_entry(entry: list) -> tuple:
        return (
            entry[0],
            entry[1],
            entry[2],
            entry[3],
            tuple((pair[0], pair[1]) for pair in entry[4]),
        )

    payload = json.loads(snapshot_json)
    return {object_entry(entry) for entry in payload["objects"]}, {
        relation_entry(entry) for entry in payload["relations"]
    }


def published_graph_snapshot(
    client,
    workspace_key: str,
    object_types=("language", "translation-group", "translation", "domain", "codelist"),
) -> str:
    """Canonical JSON of the workspace's published active projection.

    Objects are captured from every ``object_types`` collection and relations from each visible
    anchor, so two snapshots are byte-comparable only when the complete effective graph is identical.
    """
    return _graph_snapshot(client, {"workspaceKey": workspace_key}, object_types)


def publication_graph_snapshot(
    client,
    publication_id: str,
    object_types=("language", "translation-group", "translation", "domain", "codelist"),
) -> str:
    """Canonical JSON of an immutable publication's object/relation snapshot read through the generic
    object/relation routers bound to ``publicationId``."""
    return _graph_snapshot(client, {"publicationId": publication_id}, object_types)


def change_set_graph_snapshot(
    client,
    change_set_id: str,
    object_types=("language", "translation-group", "translation", "domain", "codelist"),
) -> str:
    """Canonical JSON of a mutable change set's effective membership read through the generic object and
    relation routers bound to ``changeSetId``."""
    return _graph_snapshot(client, {"changeSetId": change_set_id}, object_types)


def translation_relation(target_id: str) -> list[dict]:
    return [
        {
            "relationTypeKey": "object-has-translation",
            "direction": "incoming",
            "otherObjectId": target_id,
        }
    ]


def create_domain(client, change_set: dict, suffix: str) -> dict:
    """Create a standalone rdm-master domain record inside a change set."""
    return create_object(
        client,
        change_set,
        "rdm-master",
        "domain",
        f"Domain {suffix}",
        attributes=[attribute("domain-code", f"dom-{suffix}-{uuid4().hex[:8]}")],
    ).json()


def build_complete_graph(client, workspace_key: str, suffix: str) -> tuple[dict, dict]:
    """Language -> group containment, domain -> codelist containment, one translation.

    Mirrors the complete graph the package-2 validation suite treats as valid: it carries typed
    containment edges across the rdm-translations and rdm-master applications plus one independent
    required ownership relation (``object-has-translation`` from the domain to the translation).
    """
    change_set = create_change_set(client, workspace_key, name=f"graph {suffix}").json()
    language = create_object(
        client,
        change_set,
        "rdm-translations",
        "language",
        f"Language {suffix}",
        attributes=[attribute("language-code", f"lang-{suffix}-{uuid4().hex[:8]}")],
    ).json()
    group = create_object(
        client,
        change_set,
        "rdm-translations",
        "translation-group",
        f"Group {suffix}",
        attributes=[attribute("group-code", f"grp-{suffix}-{uuid4().hex[:8]}")],
        parent_object_id=language["id"],
    ).json()
    domain = create_domain(client, change_set, unique_key(suffix))
    codelist = create_object(
        client,
        change_set,
        "rdm-master",
        "codelist",
        f"Codelist {suffix}",
        attributes=[attribute("codelist-code", f"cl-{uuid4().hex[:8]}")],
        parent_object_id=domain["id"],
    ).json()
    translation = create_object(
        client,
        change_set,
        "rdm-translations",
        "translation",
        f"Translation {suffix}",
        attributes=[attribute("translated-value", f"tv-{uuid4().hex[:8]}")],
        parent_object_id=group["id"],
        initial_relations=translation_relation(domain["id"]),
    ).json()
    return change_set, {
        "language": language,
        "group": group,
        "domain": domain,
        "codelist": codelist,
        "translation": translation,
    }


def publish_language_publication(
    client,
    workspace_key: str,
    suffix: str,
    *,
    expected_active_publication_id: str | None = None,
) -> dict:
    """Publish one change set containing a single language record into a publication."""
    change_set = create_change_set(client, workspace_key, name=f"seed {suffix}").json()
    language = create_object(
        client,
        change_set,
        "rdm-translations",
        "language",
        f"Language {suffix}",
        attributes=[attribute("language-code", f"lang-{suffix}-{uuid4().hex[:8]}")],
    ).json()
    publication = publish_change_set(
        client,
        change_set["id"],
        expected_change_set_version=change_set["version"],
        expected_active_publication_id=expected_active_publication_id,
    ).json()
    return {**publication, "language": language, "change_set": change_set}


def diagnostic_codes(result: dict) -> list[str]:
    return [item["code"] for item in result["diagnostics"]]


def inject_change_set_object(
    change_set_id: str,
    object_id: str,
    application_key: str,
    object_type_key: str,
    name: str,
    *,
    parent_object_id: str | None = None,
    attributes: dict | None = None,
    version: int = 1,
) -> None:
    with SessionLocal() as session:
        session.add(
            ChangeSetObject(
                change_set_id=change_set_id,
                object_id=object_id,
                application_key=application_key,
                object_type_key=object_type_key,
                name=name,
                parent_object_id=parent_object_id,
                attributes=attributes or {},
                version=version,
                is_deleted=False,
            )
        )
        session.commit()


def inject_change_set_relation(
    change_set_id: str,
    relation_id: str,
    relation_type_key: str,
    from_object_id: str,
    to_object_id: str,
    *,
    attributes: dict | None = None,
    version: int = 1,
) -> None:
    with SessionLocal() as session:
        session.add(
            ChangeSetRelation(
                change_set_id=change_set_id,
                relation_id=relation_id,
                relation_type_key=relation_type_key,
                from_object_id=from_object_id,
                to_object_id=to_object_id,
                attributes=attributes or {},
                version=version,
                is_deleted=False,
            )
        )
        session.commit()


def delete_change_set_relation(change_set_id: str, *, relation_type_key: str, to_object_id: str) -> None:
    with SessionLocal() as session:
        rows = list(
            session.scalars(
                select(ChangeSetRelation).where(
                    ChangeSetRelation.change_set_id == change_set_id,
                    ChangeSetRelation.relation_type_key == relation_type_key,
                    ChangeSetRelation.to_object_id == to_object_id,
                )
            )
        )
        for row in rows:
            session.delete(row)
        session.commit()


def change_set_membership_counts(change_set_id: str) -> tuple[int, int]:
    with SessionLocal() as session:
        objects = list(
            session.scalars(
                select(ChangeSetObject).where(
                    ChangeSetObject.change_set_id == change_set_id,
                    ChangeSetObject.is_deleted.is_(False),
                )
            )
        )
        relations = list(
            session.scalars(
                select(ChangeSetRelation).where(
                    ChangeSetRelation.change_set_id == change_set_id,
                    ChangeSetRelation.is_deleted.is_(False),
                )
            )
        )
        return len(objects), len(relations)


def rewire_change_set_to_release(change_set_id: str, release: ModelRelease) -> None:
    with SessionLocal() as session:
        change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        assert change_set is not None
        change_set.model_release_id = release.id
        session.commit()


def copy_active_model_release_as_unused() -> ModelRelease:
    """Insert a non-active twin release with a distinct release version and return it."""
    with SessionLocal() as session:
        active = session.scalar(
            select(ModelRelease)
            .join(WorkspaceModel, WorkspaceModel.model_release_id == ModelRelease.id)
            .limit(1)
        )
        assert active is not None, "No active model release installed"
        model_json = dict(active.model_json)
        model_json["release"] = {
            **model_json["release"],
            "version": f"0.6.0-unused-{uuid4().hex[:6]}",
        }
        twin = ModelRelease(
            release_key=active.release_key,
            release_name=active.release_name,
            release_version=model_json["release"]["version"],
            schema_version=active.schema_version,
            model_hash=uuid4().hex,
            model_json=model_json,
        )
        session.add(twin)
        session.commit()
        session.refresh(twin)
        return twin
