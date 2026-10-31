"""The expected action groups of every operation, written from docs/API.md § Security (0.12 R, R-F14).

The J47 sweep and the OpenAPI contract read an operation's groups from the route's own declaration
(``x-action-groups``), so they prove that enforcement equals declaration, not that a declaration is
right. This table is the independent oracle: it was written from the documentation's catalogue (the
"Allows" column of the action-group table, the "Jobs" and "Instance-wide resources" rules, and the
per-route notes), not from the code. ``test_j47_security_sweep.py`` requires that every operation of
the document is named here and that its declared groups equal the table's; a new route fails until
this file says what it needs, and a route whose declaration drifts from the documentation fails too.

An entry is a tuple of the groups that allow the operation (any of them does); ``()`` means any
signed-in caller (the answer is then filtered by what the caller may browse); ``None`` means an open
operation that declares no action (it is also listed in ``OPEN_OPERATIONS``).
"""

BROWSE = ("browse",)
EDIT = ("edit-live", "change-sets")
CHANGE_SETS = ("change-sets",)
PUBLISH = ("publish",)
APPROVE = ("approve",)
BULK = ("bulk",)
COPY_MOVE = ("copy-move",)
AUTHORING = ("model-authoring",)
RELEASE = ("model-release",)
READ_RELEASES = ("model-authoring", "model-release")
WORKSPACE_ADMIN = ("workspace-admin",)
INTEGRATION = ("integration-admin",)
FEED = ("feed",)
OPERATIONS = ("operations",)
SECURITY = ("security-admin",)
SIGNED_IN = ()
# Docs "Jobs": a job is read, followed, cancelled and confirmed by its requester, or by a holder in
# the job's workspace of the group that starts its kind: bulk (batches, imports), browse (exports),
# copy-move (moves), model-release (migrations), change-sets (a change set's migration), and
# model-authoring (a draft's dry run and inference, which are "on" the draft).
JOB = ("bulk", "browse", "copy-move", "model-release", "change-sets", "model-authoring")

_SECTIONS: list[tuple[tuple[str, ...] | None, list[str]]] = [
    (
        None,
        [
            "get /.well-known/oauth-authorization-server",
            "get /health",
            "get /health/live",
            "get /oauth/jwks",
            "post /oauth/revoke",
            "post /oauth/token",
        ],
    ),
    (
        SIGNED_IN,
        [
            "get /api/v1/ai/tasks",
            "get /api/v1/capabilities",
            "get /api/v1/changes",
            "get /api/v1/jobs",
            "get /api/v1/me",
            "get /api/v1/me/action-groups",
            "get /api/v1/me/change-sets",
            "get /api/v1/me/grants",
            "get /api/v1/me/notification-mail",
            "put /api/v1/me/notification-mail",
            "get /api/v1/me/notifications",
            "get /api/v1/me/notifications/events",
            "post /api/v1/me/notifications/read",
            "post /api/v1/me/notifications/removal",
            "get /api/v1/me/passkeys",
            "delete /api/v1/me/passkeys/{passkey_id}",
            "patch /api/v1/me/passkeys/{passkey_id}",
            "post /api/v1/me/password",
            "get /api/v1/me/permissions",
            "delete /api/v1/me/second-factor",
            "get /api/v1/me/second-factor",
            "post /api/v1/me/second-factor",
            "post /api/v1/me/second-factor/confirmation",
            "post /api/v1/me/second-factor/recovery-codes",
            "delete /api/v1/me/sessions",
            "get /api/v1/me/sessions",
            "delete /api/v1/me/sessions/{session_id}",
            "get /api/v1/me/workspaces",
            "get /api/v1/system",
            "get /api/v1/workspace-models",
            "get /api/v1/workspace-runtime-state",
            "get /api/v1/workspaces",
        ],
    ),
    (
        BROWSE,
        [
            "get /api/v1/applications",
            "get /api/v1/applications/{application_key}",
            "get /api/v1/attribute-types",
            "get /api/v1/attribute-types/{attribute_type_key}",
            "get /api/v1/change-sets/{change_set_id}",
            "get /api/v1/change-sets/{change_set_id}/object-changes",
            "get /api/v1/change-sets/{change_set_id}/relation-changes",
            "post /api/v1/exports",
            "get /api/v1/model",
            "get /api/v1/model/consumer-apis/{consumerApi}",
            "get /api/v1/model/placements",
            "get /api/v1/object-type-relations",
            "get /api/v1/object-types",
            "get /api/v1/object-types/{object_type_key}",
            "get /api/v1/objects",
            "get /api/v1/objects/{object_type_key}",
            "get /api/v1/objects/{object_type_key}/{object_id}",
            "get /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
            "get /api/v1/objects/{object_type_key}/{object_id}/history",
            "get /api/v1/objects/{object_type_key}/{object_id}/parent-candidates",
            "get /api/v1/publications/{publication_id}",
            "get /api/v1/relation-types",
            "get /api/v1/relation-types/{relation_type_key}",
            "get /api/v1/relations",
            "get /api/v1/relations/held",
            "get /api/v1/relations/{relation_id}",
            "get /api/v1/workspaces/{workspace_key}",
            "get /api/v1/workspaces/{workspace_key}/approval-policy",
            "get /api/v1/workspaces/{workspace_key}/change-sets",
            "get /api/v1/workspaces/{workspace_key}/mapping-candidates",
            "get /api/v1/workspaces/{workspace_key}/mapping-coverage",
            "get /api/v1/workspaces/{workspace_key}/mapping-targets",
            "get /api/v1/workspaces/{workspace_key}/model",
            "get /api/v1/workspaces/{workspace_key}/publication-requests",
            "get /api/v1/workspaces/{workspace_key}/publications",
            "post /api/v1/workspaces/{workspace_key}/queries/objects",
            "get /api/v1/workspaces/{workspace_key}/relation-matrix",
            "get /api/v1/workspaces/{workspace_key}/relation-matrix/containers",
            "get /api/v1/workspaces/{workspace_key}/relation-matrix/link-candidates",
            "get /api/v1/workspaces/{workspace_key}/relations",
        ],
    ),
    (
        EDIT,
        [
            "post /api/v1/objects",
            "delete /api/v1/objects/{object_type_key}/{object_id}",
            "patch /api/v1/objects/{object_type_key}/{object_id}",
            "delete /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
            "patch /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
            "post /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}",
            "post /api/v1/relations",
            "delete /api/v1/relations/{relation_id}",
            "patch /api/v1/relations/{relation_id}",
            "put /api/v1/workspaces/{workspace_key}/mappings",
            # Proposals are edits of a change set (0.16 AP2); Use AI proposals is checked in the
            # route as an option, never as its action.
            "post /api/v1/workspaces/{workspace_key}/mapping-proposals",
        ],
    ),
    (
        CHANGE_SETS,
        [
            "post /api/v1/workspaces/{workspace_key}/change-sets",
            "patch /api/v1/change-sets/{change_set_id}",
            "delete /api/v1/change-sets/{change_set_id}",
            "post /api/v1/change-sets/{change_set_id}/validation",
            "post /api/v1/change-sets/{change_set_id}/restructurings",
            "post /api/v1/change-sets/{change_set_id}/restructurings/preview",
            "patch /api/v1/change-sets/{change_set_id}/model-release",
            "post /api/v1/change-sets/{change_set_id}/model-migrations",
            "post /api/v1/change-sets/{change_set_id}/submission",
        ],
    ),
    # Docs: the submitter (Work in change sets) or a holder of Approve withdraws a submission.
    (("change-sets", "approve"), ["delete /api/v1/change-sets/{change_set_id}/submission"]),
    (
        PUBLISH,
        [
            "post /api/v1/change-sets/{change_set_id}/publication",
            "post /api/v1/publications/{publication_id}/withdrawal",
        ],
    ),
    (APPROVE, ["post /api/v1/change-sets/{change_set_id}/decisions"]),
    (
        BULK,
        [
            "post /api/v1/batches",
            "post /api/v1/imports",
            # An assistant task loads a workbook as an import does (0.16 AP6a).
            "post /api/v1/ai/tasks",
            "get /api/v1/ai/tasks/{task_id}",
            "get /api/v1/ai/tasks/{task_id}/changes",
            "post /api/v1/ai/tasks/{task_id}/plan",
            "post /api/v1/ai/tasks/{task_id}/answers",
            "post /api/v1/ai/tasks/{task_id}/model",
            "post /api/v1/ai/tasks/{task_id}/accept",
            "post /api/v1/ai/tasks/{task_id}/discard",
            "post /api/v1/ai/tasks/{task_id}/run",
            "post /api/v1/ai/tasks/{task_id}/cancel",
            "get /api/v1/import-profiles",
            "post /api/v1/import-profiles",
            "delete /api/v1/import-profiles/{profile_key}",
            "get /api/v1/import-profiles/{profile_key}",
            "put /api/v1/import-profiles/{profile_key}",
            "get /api/v1/import-profiles/{profile_key}/check",
            "post /api/v1/import-profiles/{profile_key}/check",
            "get /api/v1/import-profiles/{profile_key}/check/drift",
            "get /api/v1/import-profiles/{profile_key}/check/missing-records",
            "get /api/v1/import-profiles/{profile_key}/check/new-values",
            "get /api/v1/import-profiles/{profile_key}/check/rows",
            "get /api/v1/source-files",
            "post /api/v1/source-files",
            "delete /api/v1/source-files/{source_file_id}",
            "get /api/v1/source-files/{source_file_id}",
            "get /api/v1/source-files/{source_file_id}/profile/sheets",
            "get /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/cells",
            "get /api/v1/source-files/{source_file_id}/profile/sheets/{sheet}/columns",
        ],
    ),
    (
        COPY_MOVE,
        [
            "post /api/v1/moves",
            "get /api/v1/model-mappings",
            "post /api/v1/model-mappings",
            "delete /api/v1/model-mappings/{key}",
            "get /api/v1/model-mappings/{key}",
            "get /api/v1/model-mappings/{key}/inference",
            "post /api/v1/model-mappings/{key}/inference",
            "post /api/v1/model-mappings/{key}/inference/application",
            "get /api/v1/model-mappings/{key}/inference/proposals",
            "get /api/v1/model-mappings/{key}/operations",
            "post /api/v1/model-mappings/{key}/operations",
            "post /api/v1/model-mappings/{key}/redo",
            "post /api/v1/model-mappings/{key}/undo",
        ],
    ),
    (
        AUTHORING,
        [
            "post /api/v1/model-validations",
            "get /api/v1/model-drafts",
            "post /api/v1/model-drafts",
            "delete /api/v1/model-drafts/{draft_id}",
            "get /api/v1/model-drafts/{draft_id}",
            "patch /api/v1/model-drafts/{draft_id}",
            "post /api/v1/model-drafts/{draft_id}/compile",
            "get /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}",
            "get /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/example.json",
            "get /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/openapi.json",
            "get /api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}/schema.json",
            "get /api/v1/model-drafts/{draft_id}/dry-run",
            "post /api/v1/model-drafts/{draft_id}/dry-run",
            "get /api/v1/model-drafts/{draft_id}/dry-run/rows",
            "get /api/v1/model-drafts/{draft_id}/inference",
            "post /api/v1/model-drafts/{draft_id}/inference",
            "post /api/v1/model-drafts/{draft_id}/inference/application",
            "post /api/v1/model-drafts/{draft_id}/inference/list",
            "get /api/v1/model-drafts/{draft_id}/inference/proposals",
            "get /api/v1/model-drafts/{draft_id}/model",
            "get /api/v1/model-drafts/{draft_id}/operations",
            "post /api/v1/model-drafts/{draft_id}/operations",
            "get /api/v1/model-drafts/{draft_id}/outline",
            "get /api/v1/model-drafts/{draft_id}/profile",
            "post /api/v1/model-drafts/{draft_id}/redo",
            "post /api/v1/model-drafts/{draft_id}/undo",
        ],
    ),
    (
        READ_RELEASES,
        [
            "get /api/v1/model-releases",
            "get /api/v1/model-releases/{release_id}",
            "get /api/v1/model-releases/{release_id}/activations",
            "get /api/v1/model-releases/{release_id}/diff",
        ],
    ),
    (
        RELEASE,
        [
            "post /api/v1/model-drafts/{draft_id}/installation",
            "patch /api/v1/model-releases/{release_id}",
            "delete /api/v1/model-releases/{release_id}",
            "post /api/v1/model-releases/{release_id}/raising",
            "post /api/v1/workspaces/{workspace_key}/model/activation",
            "post /api/v1/workspaces/{workspace_key}/model/migrations",
        ],
    ),
    (
        WORKSPACE_ADMIN,
        [
            "patch /api/v1/workspace-runtime-state",
            "post /api/v1/workspaces",
            "delete /api/v1/workspaces/{workspace_key}",
            "patch /api/v1/workspaces/{workspace_key}",
            "put /api/v1/workspaces/{workspace_key}/approval-policy",
        ],
    ),
    (
        INTEGRATION,
        [
            "get /api/v1/consumer-subscriptions",
            "post /api/v1/consumer-subscriptions",
            "delete /api/v1/consumer-subscriptions/{subscription_id}",
            "get /api/v1/consumer-subscriptions/{subscription_id}",
            "patch /api/v1/consumer-subscriptions/{subscription_id}",
            "get /api/v1/consumer-subscriptions/{subscription_id}/deliveries",
            "get /api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}",
            "post /api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}/resend",
            "post /api/v1/consumer-subscriptions/{subscription_id}/resume",
            "post /api/v1/consumer-subscriptions/{subscription_id}/rotate-secret",
            "post /api/v1/consumer-subscriptions/{subscription_id}/suspend",
        ],
    ),
    (FEED, ["get /api/v1/workspaces/{workspace_key}/feed"]),
    (
        OPERATIONS,
        [
            "get /metrics",
            "get /api/v1/ai/calls",
            "get /api/v1/ai/status",
            "post /api/v1/ai/test",
            "get /api/v1/system/backup-rehearsals",
            "get /api/v1/system/configuration",
            "get /api/v1/system/processes",
            "get /api/v1/system/readiness",
            "get /api/v1/system/summary",
        ],
    ),
    (
        SECURITY,
        [
            "get /api/v1/action-groups",
            "get /api/v1/clients",
            "post /api/v1/clients",
            "get /api/v1/clients/{client_id}",
            "patch /api/v1/clients/{client_id}",
            "post /api/v1/clients/{client_id}/secrets",
            "delete /api/v1/clients/{client_id}/secrets/{secret_id}",
            "get /api/v1/grants",
            "post /api/v1/grants",
            "delete /api/v1/grants/{grant_id}",
            "get /api/v1/groups",
            "post /api/v1/groups",
            "delete /api/v1/groups/{group_id}",
            "get /api/v1/groups/{group_id}",
            "patch /api/v1/groups/{group_id}",
            "get /api/v1/groups/{group_id}/members",
            "post /api/v1/groups/{group_id}/members",
            "post /api/v1/groups/{group_id}/members/batch",
            "post /api/v1/groups/{group_id}/members/removal",
            "delete /api/v1/groups/{group_id}/members/{user_id}",
            "get /api/v1/mail-outbox",
            "post /api/v1/mail-outbox/{message_id}/stop",
            "delete /api/v1/mail-settings",
            "get /api/v1/mail-settings",
            "put /api/v1/mail-settings",
            "post /api/v1/mail-settings/test",
            "get /api/v1/roles",
            "post /api/v1/roles",
            "delete /api/v1/roles/{role_key}",
            "get /api/v1/roles/{role_key}",
            "patch /api/v1/roles/{role_key}",
            "get /api/v1/security-events",
            "get /api/v1/sign-in-providers",
            "post /api/v1/sign-in-providers",
            "get /api/v1/sign-in-providers/local",
            "patch /api/v1/sign-in-providers/local",
            "delete /api/v1/sign-in-providers/{key}",
            "get /api/v1/sign-in-providers/{key}",
            "patch /api/v1/sign-in-providers/{key}",
            "get /api/v1/token-signing-keys",
            "post /api/v1/token-signing-keys/rotation",
            "get /api/v1/users",
            "post /api/v1/users",
            "get /api/v1/users/{user_id}",
            "patch /api/v1/users/{user_id}",
            "get /api/v1/users/{user_id}/grants",
            "post /api/v1/users/{user_id}/identities",
            "delete /api/v1/users/{user_id}/identities/{provider}",
            "get /api/v1/users/{user_id}/passkeys",
            "delete /api/v1/users/{user_id}/passkeys/{passkey_id}",
            "post /api/v1/users/{user_id}/password-reset",
            "delete /api/v1/users/{user_id}/second-factor",
            "delete /api/v1/users/{user_id}/sessions",
            "get /api/v1/workspaces/{workspace_key}/access",
            "get /api/v1/workspaces/{workspace_key}/grant-options",
        ],
    ),
    (
        JOB,
        [
            "get /api/v1/jobs/{job_id}",
            "post /api/v1/jobs/{job_id}/cancel",
            "post /api/v1/jobs/{job_id}/confirm",
            "get /api/v1/jobs/{job_id}/events",
            "get /api/v1/jobs/{job_id}/items",
            "get /api/v1/jobs/{job_id}/output",
            "get /api/v1/jobs/{job_id}/rows",
        ],
    ),
]


def _build() -> dict[tuple[str, str], frozenset[str] | None]:
    table: dict[tuple[str, str], frozenset[str] | None] = {}
    for groups, routes in _SECTIONS:
        for route in routes:
            method, path = route.split(" ")
            assert (method, path) not in table, f"{route} is named twice"
            table[(method, path)] = None if groups is None else frozenset(groups)
    return table


EXPECTED_GROUPS = _build()
