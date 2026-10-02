"""The write rules, live and in a change set: what each context refuses, and how (E2 inventory).

Every case provokes one rule violation through the API, once live and once in a change set, on the
example model and on its renamed copy. ``EXPECTED`` pins the status, code, message and details each
context returns. Where the contexts differ, the difference is the context's own refusal wording
(``engine/records/rules.py``); decision E-D4 settles each one. IDs in messages and details read as
the labels the case gave the records, and renamed keys read as the example's.

The batch context (0.9.0-alpha.1 PG3b, PG-D13): every create and update case again with each
write sent as a one-item batch, decided through the batch lookup. An item is refused with its
single write's code, message and details; it carries no HTTP status, and its details point into
the item (``pointer``, left out here).
"""

import re
import uuid
from typing import Any

import pytest
from test_type_changes import WORKSPACE, attr, starter  # noqa: F401 - fixture

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class Context:
    """Writes in one context: live, or one change set with its claims kept current."""

    def __init__(self, client, k, kind: str) -> None:
        self.client, self.k, self.kind = client, k, kind
        self.labels: dict[str, str] = {}
        self.change_set = None
        if kind == "change_set":
            response = client.post(
                f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}
            )
            assert response.status_code == 201, response.text
            self.change_set = response.json()["id"]

    def _claims(self) -> dict[str, Any]:
        if self.change_set is None:
            return {}
        version = self.client.get(f"/api/v1/change-sets/{self.change_set}").json()["version"]
        return {"changeSetId": self.change_set, "expectedChangeSetVersion": version}

    def _params(self) -> dict[str, Any]:
        return {"changeSetId": self.change_set} if self.change_set else {"workspaceKey": WORKSPACE}

    def read(self, record: dict) -> dict:
        response = self.client.get(
            f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}", params=self._params()
        )
        assert response.status_code == 200, response.text
        return response.json()

    def create(self, label, app, type_key, attributes, parent=None, relations=None, **extra):
        k = self.k
        payload = {
            "applicationKey": k(app),
            "objectTypeKey": k(type_key),
            "name": label,
            "attributes": [attr(k(key), value) for key, value in attributes.items()],
            **extra,
            **(self._claims() or {"workspaceKey": WORKSPACE}),
        }
        if parent is not None:
            payload["parentObjectId"] = parent["id"]
        if relations:
            payload["initialRelations"] = [
                {"relationTypeKey": k(key), "direction": direction, "otherObjectId": other["id"]}
                for key, direction, other in relations
            ]
        response = self.client.post("/api/v1/objects", json=payload)
        if response.status_code == 201:
            self.labels[response.json()["id"]] = label
        return response

    def made(self, *args, **kwargs) -> dict:
        response = self.create(*args, **kwargs)
        assert response.status_code == 201, response.text
        return response.json()

    def update(self, record, **fields):
        current = self.read(record)
        body = {"expectedVersion": current["version"], **self._claims()}
        if "attributes" in fields:
            body["attributes"] = [
                attr(self.k(key), value) for key, value in fields.pop("attributes").items()
            ]
        if "parent" in fields:
            body["parentObjectId"] = fields.pop("parent")["id"]
        body.update(fields)
        return self.client.patch(
            f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}", json=body
        )

    def relate(self, relation_type, source, target):
        response = self.client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": self.k(relation_type),
                "fromObjectId": source["id"],
                "toObjectId": target["id"],
                **self._claims(),
            },
        )
        if response.status_code == 201:
            self.labels[response.json()["id"]] = f"{source['name']}->{target['name']}"
        return response

    def relations(self, record, relation_type) -> list[dict]:
        response = self.client.get(
            "/api/v1/relations",
            params={
                "objectId": record["id"],
                "relationTypeKey": self.k(relation_type),
                **self._params(),
            },
        )
        assert response.status_code == 200, response.text
        return [item.get("relation", item) for item in response.json()["items"]]

    def delete_relation(self, relation):
        claims = self._claims()
        return self.client.delete(
            f"/api/v1/relations/{relation['id']}",
            params={"expectedVersion": relation["version"], **claims},
        )

    def patch_attribute(self, record, key, value):
        current = self.read(record)
        return self.client.patch(
            f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}/attributes/{self.k(key)}",
            json={"value": value, "expectedVersion": current["version"], **self._claims()},
        )

    def delete_attribute(self, record, key):
        current = self.read(record)
        return self.client.delete(
            f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}/attributes/{self.k(key)}",
            params={"expectedVersion": current["version"], **self._claims()},
        )

    def outcome(self, response) -> tuple:
        if response.status_code < 400:
            return (response.status_code,)
        error = response.json()["error"]
        return (
            response.status_code,
            error["code"],
            self._normal(error["message"]),
            self._normal(error.get("details")),
        )

    def _normal(self, value: Any) -> Any:
        if isinstance(value, str):
            value = UUID.sub(lambda match: self.labels.get(match.group(0), "<id>"), value)
            return value.replace("zq-", "")
        if isinstance(value, list):
            return [self._normal(item) for item in value]
        if isinstance(value, dict):
            return {key: self._normal(item) for key, item in value.items()}
        return value


class BatchedContext(Context):
    """The same writes in the same context, each create and update sent as a batch of one."""

    def create(self, label, app, type_key, attributes, parent=None, relations=None, **extra):
        k = self.k
        item: dict[str, Any] = {
            "op": "create",
            "applicationKey": k(app),
            "objectTypeKey": k(type_key),
            "name": label,
            "attributes": [attr(k(key), value) for key, value in attributes.items()],
        }
        if "id" in extra:
            item["id"] = extra.pop("id")
        assert not extra, extra
        if parent is not None:
            item["parent"] = {"id": parent["id"]}
        if relations:
            item["initialRelations"] = [
                {"relationTypeKey": k(key), "direction": direction, "object": {"id": other["id"]}}
                for key, direction, other in relations
            ]
        response = self._send(item, 201)
        if response.status_code == 201:
            self.labels[response.json()["id"]] = label
        return response

    def update(self, record, **fields):
        current = self.read(record)
        item: dict[str, Any] = {
            "op": "update",
            "target": {"id": record["id"]},
            "expectedVersion": current["version"],
        }
        if "attributes" in fields:
            item["attributes"] = [
                attr(self.k(key), value) for key, value in fields.pop("attributes").items()
            ]
        if "parent" in fields:
            item["parent"] = {"id": fields.pop("parent")["id"]}
        item.update(fields)
        return self._send(item, 200)

    def _send(self, item: dict, status: int) -> ItemResponse:
        response = self.client.post(
            "/api/v1/batches",
            json={
                "policy": "atomic",
                "run": "inline",
                "items": [item],
                **(self._claims() or {"workspaceKey": WORKSPACE}),
            },
        )
        assert response.status_code == 200, response.text
        (outcome,) = response.json()["items"]
        if outcome["status"] != "applied":
            return ItemResponse(None, {"error": outcome["error"]})
        return ItemResponse(status, self.read(outcome))

    def outcome(self, response) -> tuple:
        if response.status_code is not None:
            return (response.status_code,)
        error = response.json()["error"]
        details = {key: value for key, value in error["details"].items() if key != "pointer"}
        return (error["code"], self._normal(error["message"]), self._normal(details or None))


class ItemResponse:
    """A batch item's outcome, read as its single write's response."""

    def __init__(self, status_code: int | None, body: dict) -> None:
        self.status_code, self._body = status_code, body
        self.text = str(body)

    def json(self) -> dict:
        return self._body


def _code(tag: str) -> str:
    return f"{tag}-{uuid.uuid4().hex[:8]}"


def _domain(c: Context, label: str, code: str | None = None) -> dict:
    return c.made(label, "rdm-master", "domain", {"domain-code": code or _code(label)})


def _translation_setup(c: Context, tag: str):
    """Language L > group G, and the domain D a translation under G belongs to."""
    domain = _domain(c, f"{tag}-D")
    language = c.made(f"{tag}-L", "rdm-translations", "language", {"language-code": _code(tag)})
    group = c.made(
        f"{tag}-G", "rdm-translations", "translation-group", {"group-code": "g"}, language
    )
    return domain, language, group


def _translation(c: Context, label, group, domain, *, active=True, **extra):
    return c.create(
        label,
        "rdm-translations",
        "translation",
        {"translated-name": label, "active": active},
        group,
        [("object-has-translation", "incoming", domain)] if domain is not None else None,
        **extra,
    )


# One function per rule: set up in the context, then the request that breaks the rule.
def create_unknown_object_type(c):
    return c.create("X", "rdm-master", "no-such-type", {})


def create_unknown_application(c):
    return c.create("X", "no-such-application", "domain", {"domain-code": _code("x")})


def create_type_not_in_application(c):
    return c.create("X", "rdm-master", "system", {"system-code": _code("x")})


def create_unknown_attribute(c):
    return c.create("X", "rdm-master", "domain", {"domain-code": _code("x"), "language-code": "x"})


def create_missing_required_attribute(c):
    return c.create("X", "rdm-master", "domain", {"description": "no code"})


def create_invalid_value(c):
    return c.create("X", "rdm-master", "domain", {"domain-code": _code("x"), "active": "yes"})


def create_at_least_one_of(c):
    domain, _language, group = _translation_setup(c, "alo")
    return c.create(
        "T",
        "rdm-translations",
        "translation",
        {"active": True},
        group,
        [("object-has-translation", "incoming", domain)],
    )


def update_at_least_one_of(c):
    domain, _language, group = _translation_setup(c, "ualo")
    translation = _translation(c, "T", group, domain).json()
    return c.update(translation, attributes={"translated-name": ""})


def create_missing_required_relation(c):
    _domain_record, _language, group = _translation_setup(c, "req")
    return _translation(c, "T", group, None)


def create_existing_id(c):
    existing = _domain(c, "E")
    return c.create(
        "X", "rdm-master", "domain", {"domain-code": _code("x")}, id=existing["id"]
    )


def create_parent_required(c):
    return c.create("X", "rdm-master", "codelist", {"codelist-code": _code("x")})


def create_parent_missing(c):
    return c.create(
        "X", "rdm-master", "codelist", {"codelist-code": _code("x")}, {"id": str(uuid.uuid4())}
    )


def create_parent_wrong_scope(c):
    domain = _domain(c, "D")
    codelist = c.made("C", "rdm-master", "codelist", {"codelist-code": _code("c")}, domain)
    return c.create(
        "X",
        "rdm-systems",
        "master-value",
        {"master-id": _code("m"), "value-code": "v", "value-name": "v"},
        codelist,
    )


def create_invalid_parent_type(c):
    system = c.made("S", "rdm-systems", "system", {"system-code": _code("s")})
    return c.create("X", "rdm-systems", "codelist", {"codelist-code": _code("x")}, system)


def update_parent_cycle(c):
    domain = _domain(c, "D")
    codelist = c.made("C", "rdm-master", "codelist", {"codelist-code": _code("c")}, domain)
    values = {"value-code": "v", "value-name": "v"}
    upper = c.made(
        "M1", "rdm-master", "master-value", {"master-id": _code("m"), **values}, codelist
    )
    lower = c.made("M2", "rdm-master", "master-value", {"master-id": _code("m"), **values}, upper)
    return c.update(upper, parent=lower)


def _master_value(c, label, **dates):
    domain = _domain(c, f"{label}-D")
    codelist = c.made(f"{label}-C", "rdm-master", "codelist", {"codelist-code": _code("c")}, domain)
    values = {"master-id": _code("m"), "value-code": "v", "value-name": "v", **dates}
    return c.create(label, "rdm-master", "master-value", values, codelist)


def create_invalid_effective_period(c):
    return _master_value(c, "M", **{"valid-from": "2026-07-01", "valid-to": "2026-07-01"})


def update_invalid_effective_period(c):
    record = _master_value(c, "M", **{"valid-from": "2026-07-01"}).json()
    return c.update(record, attributes={"valid-to": "2026-06-30"})


def patch_invalid_effective_period(c):
    record = _master_value(c, "M", **{"valid-from": "2026-06-01", "valid-to": "2026-07-01"}).json()
    return c.patch_attribute(record, "valid-from", "2026-08-01")


def create_duplicate_unique(c):
    code = _code("dup")
    _domain(c, "D1", code)
    return c.create("D2", "rdm-master", "domain", {"domain-code": code})


def update_duplicate_unique(c):
    code = _code("dup")
    _domain(c, "D1", code)
    second = _domain(c, "D2")
    return c.update(second, attributes={"domain-code": code})


def patch_duplicate_unique(c):
    code = _code("dup")
    _domain(c, "D1", code)
    second = _domain(c, "D2")
    return c.patch_attribute(second, "domain-code", code)


def relation_unknown_type(c):
    return c.relate("no-such-relation", _domain(c, "A"), _domain(c, "B"))


def relation_invalid_pair(c):
    return c.relate("system-value-maps-to-master", _domain(c, "A"), _domain(c, "B"))


def relation_immutable(c):
    domain = _domain(c, "D")
    codelist = c.made("C", "rdm-master", "codelist", {"codelist-code": _code("c")}, domain)
    return c.relate("domain-contains-codelist", _domain(c, "D2"), codelist)


def _system_value(c, label):
    system = c.made(f"{label}-S", "rdm-systems", "system", {"system-code": _code("s")})
    return c.made(
        label, "rdm-systems", "system-value", {"value-code": "v", "value-name": "v"}, system
    )


def relation_cardinality(c):
    value = _system_value(c, "V")
    first = c.relate("reference-has-system-representation", _domain(c, "A"), value)
    assert first.status_code == 201, first.text
    return c.relate("reference-has-system-representation", _domain(c, "B"), value)


def relation_missing_endpoint(c):
    return c.relate(
        "reference-has-system-representation",
        {"id": str(uuid.uuid4()), "name": "missing"},
        _system_value(c, "V"),
    )


def relation_duplicate_scope(c):
    domain, _language, group = _translation_setup(c, "scope")
    assert _translation(c, "T1", group, domain).status_code == 201
    return _translation(c, "T2", group, domain)


def relation_delete_required(c):
    domain, _language, group = _translation_setup(c, "delreq")
    translation = _translation(c, "T", group, domain).json()
    (relation,) = c.relations(translation, "object-has-translation")
    return c.delete_relation(relation)


def relation_delete_immutable(c):
    domain = _domain(c, "D")
    codelist = c.made("C", "rdm-master", "codelist", {"codelist-code": _code("c")}, domain)
    (relation,) = c.relations(codelist, "domain-contains-codelist")
    return c.delete_relation(relation)


def delete_required_attribute(c):
    return c.delete_attribute(_domain(c, "D"), "domain-code")


def delete_at_least_one_of(c):
    domain, _language, group = _translation_setup(c, "dalo")
    translation = _translation(c, "T", group, domain).json()
    return c.delete_attribute(translation, "translated-name")


def move_into_taken_scope(c):
    domain, language, group = _translation_setup(c, "move")
    other = c.made("G2", "rdm-translations", "translation-group", {"group-code": "g"}, language)
    other_language = c.made(
        "L2", "rdm-translations", "language", {"language-code": _code("l")}
    )
    far = c.made("G3", "rdm-translations", "translation-group", {"group-code": "g"}, other_language)
    assert _translation(c, "T1", group, domain).status_code == 201
    moving = _translation(c, "T2", far, domain).json()
    del other
    return c.update(moving, parent=group)


def activate_into_taken_scope(c):
    domain, _language, group = _translation_setup(c, "act")
    assert _translation(c, "T1", group, domain).status_code == 201
    inactive = _translation(c, "T2", group, domain, active=False).json()
    return c.update(inactive, attributes={"active": True})


def duplicate_initial_relation(c):
    domain, _language, group = _translation_setup(c, "dupinit")
    return c.create(
        "T",
        "rdm-translations",
        "translation",
        {"translated-name": "T", "active": True},
        group,
        [
            ("object-has-translation", "incoming", domain),
            ("object-has-translation", "incoming", domain),
        ],
    )


CASES = [
    create_unknown_object_type,
    create_unknown_application,
    create_type_not_in_application,
    create_unknown_attribute,
    create_missing_required_attribute,
    create_invalid_value,
    create_at_least_one_of,
    update_at_least_one_of,
    create_missing_required_relation,
    create_existing_id,
    create_parent_required,
    create_parent_missing,
    create_parent_wrong_scope,
    create_invalid_parent_type,
    update_parent_cycle,
    create_invalid_effective_period,
    update_invalid_effective_period,
    patch_invalid_effective_period,
    create_duplicate_unique,
    update_duplicate_unique,
    patch_duplicate_unique,
    relation_unknown_type,
    relation_invalid_pair,
    relation_immutable,
    relation_cardinality,
    relation_missing_endpoint,
    relation_duplicate_scope,
    relation_delete_required,
    relation_delete_immutable,
    delete_required_attribute,
    delete_at_least_one_of,
    move_into_taken_scope,
    activate_into_taken_scope,
    duplicate_initial_relation,
]

EXPECTED: dict[str, dict[str, tuple]] = {
    "create_unknown_object_type": {
        "live": (404, "unknown_object_type", "Object type 'no-such-type' not found", None),
        "change_set": (
            422,
            "unknown_object_type",
            "Object type 'no-such-type' is not in the pinned model",
            None,
        ),
    },
    "create_unknown_application": {
        "live": (404, "unknown_application", "Application 'no-such-application' not found", None),
        "change_set": (
            422,
            "object_type_not_in_application",
            "Object type 'domain' is not enabled in application 'no-such-application'",
            None,
        ),
    },
    "create_type_not_in_application": {
        "live": (
            422,
            "invalid_object_type_for_application",
            "Object type 'system' is not available in application 'rdm-master'",
            None,
        ),
        "change_set": (
            422,
            "object_type_not_in_application",
            "Object type 'system' is not enabled in application 'rdm-master'",
            None,
        ),
    },
    "create_unknown_attribute": {
        "live": (422, "unknown_attributes", "Unknown attributes: ['language-code']", None),
        "change_set": (422, "unknown_attributes", "Unknown attributes: ['language-code']", None),
    },
    "create_missing_required_attribute": {
        "live": (
            422,
            "missing_required_attributes",
            "Required fields are missing: Domain code",
            {"attributeTypeKeys": ["domain-code"]},
        ),
        "change_set": (
            422,
            "missing_required_attributes",
            "Required fields are missing: Domain code",
            {"attributeTypeKeys": ["domain-code"]},
        ),
    },
    "create_invalid_value": {
        "live": (422, "invalid_attribute_value", "Attribute 'active' must be boolean", None),
        "change_set": (422, "invalid_attribute_value", "Attribute 'active' must be boolean", None),
    },
    "create_at_least_one_of": {
        "live": (
            422,
            "object_attribute_rule_violation",
            "At least one of these attributes is required: ('translated-name', 'translated-description', 'translated-value')",
            {
                "rule": "atLeastOneOf",
                "attributeTypeKeys": ["translated-name", "translated-description", "translated-value"],
            },
        ),
        "change_set": (
            422,
            "object_attribute_rule_violation",
            "At least one of these attributes is required: ('translated-name', 'translated-description', 'translated-value')",
            {
                "rule": "atLeastOneOf",
                "attributeTypeKeys": ["translated-name", "translated-description", "translated-value"],
            },
        ),
    },
    "update_at_least_one_of": {
        "live": (
            422,
            "object_attribute_rule_violation",
            "At least one of these attributes is required: ('translated-name', 'translated-description', 'translated-value')",
            {
                "rule": "atLeastOneOf",
                "attributeTypeKeys": ["translated-name", "translated-description", "translated-value"],
            },
        ),
        "change_set": (200,),
    },
    "create_missing_required_relation": {
        "live": (
            422,
            "missing_required_relations",
            "Required relationships missing: ['object-has-translation']",
            {"relationTypeKeys": ["object-has-translation"]},
        ),
        "change_set": (
            422,
            "missing_required_relations",
            "Required relationships missing: ['object-has-translation']",
            {"relationTypeKeys": ["object-has-translation"]},
        ),
    },
    "create_existing_id": {
        "live": (409, "object_already_exists", "An object with ID 'E' already exists", None),
        "change_set": (409, "object_already_exists", "Object 'E' already exists", None),
    },
    "create_parent_required": {
        "live": (422, "parent_required", "This object type requires a parent", None),
        "change_set": (422, "parent_required", "This object type requires a parent", None),
    },
    "create_parent_missing": {
        "live": (404, "object_not_found", "Object '<id>' not found", None),
        "change_set": (422, "parent_wrong_scope", "Parent must exist in the change set", None),
    },
    "create_parent_wrong_scope": {
        "live": (
            422,
            "parent_wrong_scope",
            "Parent must be in the same application and workspace",
            None,
        ),
        "change_set": (
            422,
            "parent_wrong_scope",
            "Parent must be in the same application and workspace",
            None,
        ),
    },
    "create_invalid_parent_type": {
        "live": (
            422,
            "invalid_parent_type",
            "Parent type is not permitted for this object type",
            None,
        ),
        "change_set": (
            422,
            "invalid_parent_type",
            "Parent type is not permitted for this object type",
            None,
        ),
    },
    "update_parent_cycle": {
        "live": (422, "parent_cycle", "Parent selection would create a cycle", None),
        "change_set": (422, "parent_cycle", "Parent selection would create a cycle", None),
    },
    **{
        name: dict.fromkeys(
            ("live", "change_set"),
            (
                422,
                "invalid_effective_period",
                (
                    f"The effective period must end after it starts: 'valid-to' {end} is not"
                    f" after 'valid-from' {start}"
                ),
                {
                    "startAttributeTypeKey": "valid-from",
                    "endAttributeTypeKey": "valid-to",
                    "start": start,
                    "end": end,
                },
            ),
        )
        for name, start, end in (
            ("create_invalid_effective_period", "2026-07-01", "2026-07-01"),
            ("update_invalid_effective_period", "2026-07-01", "2026-06-30"),
            ("patch_invalid_effective_period", "2026-08-01", "2026-07-01"),
        )
    },
    "create_duplicate_unique": {
        "live": (409, "duplicate_attribute_value", "Attribute 'Domain code' must be unique", None),
        "change_set": (
            409,
            "duplicate_attribute_value",
            "Attribute 'domain-code' must be unique in the change set",
            {"attributeTypeKey": "domain-code", "conflictingObjectId": "D1"},
        ),
    },
    "update_duplicate_unique": {
        "live": (409, "duplicate_attribute_value", "Attribute 'Domain code' must be unique", None),
        "change_set": (
            409,
            "duplicate_attribute_value",
            "Attribute 'domain-code' must be unique in the change set",
            {"attributeTypeKey": "domain-code", "conflictingObjectId": "D1"},
        ),
    },
    "patch_duplicate_unique": {
        "live": (409, "duplicate_attribute_value", "Attribute 'Domain code' must be unique", None),
        "change_set": (
            409,
            "duplicate_attribute_value",
            "Attribute 'domain-code' must be unique in the change set",
            {"attributeTypeKey": "domain-code", "conflictingObjectId": "D1"},
        ),
    },
    "relation_unknown_type": {
        "live": (404, "unknown_relation_type", "Relation type 'no-such-relation' not found", None),
        "change_set": (
            422,
            "unknown_relation_type",
            "Relation type 'no-such-relation' is not in the pinned model",
            None,
        ),
    },
    "relation_invalid_pair": {
        "live": (
            422,
            "invalid_relation_pair",
            "Relation is not permitted between these object types",
            None,
        ),
        "change_set": (
            422,
            "invalid_relation_pair",
            "Relation is not permitted between these object types",
            None,
        ),
    },
    "relation_immutable": {
        "live": (
            422,
            "immutable_relation",
            "Engine-maintained relation cannot be created, updated or deleted directly",
            None,
        ),
        "change_set": (
            422,
            "immutable_relation",
            "Engine-maintained containment relations are changed through object edits",
            None,
        ),
    },
    "relation_cardinality": {
        "live": (409, "cardinality_violation", "Relation cardinality would be violated", None),
        "change_set": (
            409,
            "cardinality_violation",
            "Relation cardinality would be violated",
            None,
        ),
    },
    "relation_missing_endpoint": {
        "live": (404, "object_not_found", "Object '<id>' not found", None),
        "change_set": (
            422,
            "relation_endpoint_missing",
            "Relation endpoints must exist in the change set",
            None,
        ),
    },
    "relation_duplicate_scope": {
        "live": (
            409,
            "duplicate_relation_scope",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": "language",
                "ancestorObjectId": "scope-L",
                "conflictingObjectId": "T1",
                "conflictingRelationId": "<id>",
            },
        ),
        "change_set": (
            409,
            "duplicate_relation_scope",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": "language",
                "ancestorObjectId": "scope-L",
                "conflictingObjectId": "T1",
                "conflictingRelationId": "<id>",
            },
        ),
    },
    "relation_delete_required": {
        "live": (
            422,
            "required_relation",
            "A required relationship cannot be deleted independently",
            None,
        ),
        "change_set": (
            422,
            "required_relation",
            "Required relationships cannot be deleted directly",
            None,
        ),
    },
    "relation_delete_immutable": {
        "live": (
            422,
            "immutable_relation",
            "Engine-maintained relation cannot be created, updated or deleted directly",
            None,
        ),
        "change_set": (
            422,
            "immutable_relation",
            "Engine-maintained containment relations cannot be deleted directly",
            None,
        ),
    },
    "delete_required_attribute": {
        "live": (
            422,
            "cannot_delete_required_attribute",
            "Attribute 'domain-code' is required and cannot be deleted",
            None,
        ),
        "change_set": (
            422,
            "cannot_delete_required_attribute",
            "Attribute 'domain-code' is required and cannot be deleted",
            None,
        ),
    },
    "delete_at_least_one_of": {
        "live": (
            422,
            "object_attribute_rule_violation",
            "At least one of these attributes is required: ('translated-name', 'translated-description', 'translated-value')",
            {
                "rule": "atLeastOneOf",
                "attributeTypeKeys": ["translated-name", "translated-description", "translated-value"],
            },
        ),
        "change_set": (
            422,
            "object_attribute_rule_violation",
            "At least one of these attributes is required: ('translated-name', 'translated-description', 'translated-value')",
            {
                "rule": "atLeastOneOf",
                "attributeTypeKeys": ["translated-name", "translated-description", "translated-value"],
            },
        ),
    },
    "move_into_taken_scope": {
        "live": (
            409,
            "duplicate_relation_scope",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": "language",
                "ancestorObjectId": "move-L",
                "conflictingObjectId": "T1",
                "conflictingRelationId": "<id>",
            },
        ),
        "change_set": (
            409,
            "duplicate_relation_scope",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": "language",
                "ancestorObjectId": "move-L",
                "conflictingObjectId": "T1",
                "conflictingRelationId": "<id>",
            },
        ),
    },
    "activate_into_taken_scope": {
        "live": (
            409,
            "duplicate_relation_scope",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": "language",
                "ancestorObjectId": "act-L",
                "conflictingObjectId": "T1",
                "conflictingRelationId": "<id>",
            },
        ),
        "change_set": (
            409,
            "duplicate_relation_scope",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": "language",
                "ancestorObjectId": "act-L",
                "conflictingObjectId": "T1",
                "conflictingRelationId": "<id>",
            },
        ),
    },
    "duplicate_initial_relation": {
        "live": (409, "cardinality_violation", "Relation cardinality would be violated", None),
        "change_set": (
            422,
            "duplicate_initial_relation",
            "Initial relationships must not repeat",
            None,
        ),
    },
}


def observe(client, k, kind: str) -> dict[str, tuple]:
    results = {}
    for case in CASES:
        context = Context(client, k, kind)
        results[case.__name__] = context.outcome(case(context))
    return results


@pytest.mark.parametrize("kind", ["live", "change_set"])
def test_rules_refuse_as_pinned(starter, kind):  # noqa: F811 - fixture
    client, k = starter
    observed = observe(client, k, kind)
    expected = {name: outcomes[kind] for name, outcomes in EXPECTED.items()}
    assert observed == expected


# Every case whose refused write is a record's create or update: the ones a batch item makes.
BATCH_CASES = [
    case
    for case in CASES
    if case.__name__.startswith(("create_", "update_", "move_", "activate_", "duplicate_"))
]
# A batch item names its records by reference, resolved before its write's rules run (§B2).
BATCH_REFUSALS = {
    "create_parent_missing": (
        "reference_not_found",
        "No record matches the reference in this batch's context",
        {"id": "<id>"},
    ),
}


@pytest.mark.parametrize("kind", ["live", "change_set"])
def test_batch_items_refuse_as_their_single_writes(starter, kind):  # noqa: F811 - fixture
    """PG3b: a create or update decided through the batch lookup is refused with its single
    write's code, message and details."""
    client, k = starter
    observed = {}
    for case in BATCH_CASES:
        context = BatchedContext(client, k, kind)
        observed[case.__name__] = context.outcome(case(context))
    expected = {}
    for case in BATCH_CASES:
        single = EXPECTED[case.__name__][kind]
        # A refusal without its HTTP status; a write the rules accept as it is.
        expected[case.__name__] = BATCH_REFUSALS.get(
            case.__name__, single[1:] if len(single) > 1 else single
        )
    assert observed == expected
