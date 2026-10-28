"""The permission catalogue: action groups, the actions routes declare, and the predefined roles
(Product 0.12 Z1, ADR-044, API.md § Security).

An administrator grants roles; a role is a set of action groups named after journeys (D227); every
route declares one action, and an action names the groups that allow it. A new route joins an
existing action or group without touching any role. "Approve publications" joined with A1 (D280,
D424).
"""

from dataclasses import dataclass
from typing import Literal

# Where a group can be granted: in a workspace (or at the instance, which covers every workspace),
# or only at the instance.
Reach = Literal["workspace", "instance"]


@dataclass(frozen=True)
class ActionGroup:
    key: str
    name: str
    description: str
    reach: Reach
    # Whether a grant's applications and record types narrow it (writes only, D243), enforced at
    # the write unit (Z2, D281, D290).
    narrowable: bool = False


GROUPS: dict[str, ActionGroup] = {
    group.key: group
    for group in (
        ActionGroup(
            "browse",
            "Browse",
            "Read a workspace: its model, records, relations, history, change sets and "
            "publications; export to a file",
            "workspace",
        ),
        ActionGroup(
            "edit-live",
            "Edit live",
            "Create, change and delete records, values and relationships without a change set",
            "workspace",
            narrowable=True,
        ),
        ActionGroup(
            "change-sets",
            "Work in change sets",
            "Create, change, validate and discard change sets, and edit records inside them",
            "workspace",
            narrowable=True,
        ),
        ActionGroup(
            "publish",
            "Publish",
            "Publish a change set; withdraw a publication",
            "workspace",
            narrowable=True,
        ),
        ActionGroup(
            "approve",
            "Approve publications",
            "Decide a submitted change set: approve it, which publishes it, or send it back",
            "workspace",
        ),
        ActionGroup(
            "bulk",
            "Bulk and import",
            "Batches and imports; import profiles and source files",
            "workspace",
            narrowable=True,
        ),
        ActionGroup(
            "copy-move",
            "Copy and move",
            "Model-to-model mappings, and moving records between workspaces",
            "workspace",
            narrowable=True,
        ),
        ActionGroup(
            "model-authoring",
            "Model authoring",
            "Model drafts and everything on them; reading model releases",
            "instance",
        ),
        ActionGroup(
            "model-release",
            "Model release",
            "Install a draft as a release, activate a release in a workspace, migrate a workspace",
            "workspace",
        ),
        ActionGroup(
            "workspace-admin",
            "Workspace administration",
            "Create, rename, retire and delete workspaces; set the default workspace",
            "instance",
        ),
        ActionGroup(
            "integration-admin",
            "Integration administration",
            "Consumer API subscriptions and their deliveries",
            "workspace",
        ),
        ActionGroup("feed", "Feed", "Read a workspace's change feed", "workspace"),
        ActionGroup(
            "operations",
            "Operations",
            "Processes, readiness, metrics, backup rehearsals and the deployment's settings",
            "instance",
        ),
        ActionGroup(
            "security-admin",
            "Security administration",
            "People, groups, roles, grants, clients and token signing keys",
            "instance",
        ),
        # Asking the proposal provider (0.16 AP-D7). A proposal is written by the person's own
        # request, so it still needs the group that allows writing what it proposes.
        ActionGroup(
            "ai-proposals",
            "Use AI proposals",
            "Ask the configured AI provider for proposals the person then edits, keeps or removes",
            "workspace",
        ),
    )
}


@dataclass(frozen=True)
class Action:
    key: str
    # The groups allowing it; empty for an action any signed-in caller may use. The record writes
    # name both of theirs; the request's changeSetId picks one (D244).
    groups: tuple[str, ...]
    description: str
    # How a refusal names it: "Reading records in workspace 'x' needs Browse".
    doing: str = ""


ACTIONS: dict[str, Action] = {
    action.key: action
    for action in (
        Action(
            "signed-in", (), "Anything a signed-in caller may read about themselves or the engine"
        ),
        Action("workspaces.list", (), "List the workspaces the caller holds a role in (D288)"),
        Action(
            "changes.read",
            (),
            "Read the data and model changes the caller may see, across workspaces (Z6, D342)",
        ),
        Action("model.read", ("browse",), "Read a workspace's model", doing="Reading the model"),
        Action("workspace.read", ("browse",), "Read a workspace", doing="Reading the workspace"),
        Action(
            "records.read",
            ("browse",),
            "Read records, relationships, history and queries",
            doing="Reading records",
        ),
        Action(
            "change-sets.read",
            ("browse",),
            "Read change sets and their changes",
            doing="Reading change sets",
        ),
        Action("publications.read", ("browse",), "Read publications", doing="Reading publications"),
        Action(
            "exports.create", ("browse",), "Export records to a file", doing="Exporting records"
        ),
        Action(
            "records.write",
            ("edit-live", "change-sets"),
            "Change records, values and relationships: live, or in a change set",
            doing="Changing records",
        ),
        Action(
            "change-sets.write",
            ("change-sets",),
            "Create, change, validate and discard change sets",
            doing="Changing change sets",
        ),
        Action(
            "change-sets.publish",
            ("publish",),
            "Publish a change set",
            doing="Publishing a change set",
        ),
        Action(
            "change-sets.submit",
            ("change-sets",),
            "Submit a change set for publication, or withdraw its submission",
            doing="Submitting a change set",
        ),
        Action(
            "change-sets.withdraw",
            ("change-sets", "approve"),
            "Withdraw a change set's submission: the person who submitted it, or an approver",
            doing="Withdrawing a submission",
        ),
        Action(
            "change-sets.decide",
            ("approve",),
            "Approve a submitted change set, which publishes it, or send it back",
            doing="Deciding on a change set",
        ),
        Action(
            "approval-policy.write",
            ("workspace-admin",),
            "Change a workspace's approval policy",
            doing="Changing the approval policy",
        ),
        Action(
            "publications.withdraw",
            ("publish",),
            "Withdraw a publication",
            doing="Withdrawing a publication",
        ),
        Action(
            "bulk.write",
            ("bulk",),
            "Send a batch or an import",
            doing="Sending a batch or an import",
        ),
        Action(
            "import-profiles.manage",
            ("bulk",),
            "Read and change import profiles",
            doing="Using import profiles",
        ),
        Action(
            "source-files.manage",
            ("bulk",),
            "Upload, read and delete source files",
            doing="Using source files",
        ),
        Action(
            "model-mappings.manage",
            ("copy-move",),
            "Read and change model-to-model mappings",
            doing="Using model mappings",
        ),
        Action(
            "moves.create",
            ("copy-move",),
            "Move records into another workspace",
            doing="Moving records",
        ),
        Action(
            "model.author", ("model-authoring",), "Author model drafts", doing="Authoring models"
        ),
        Action(
            "model-releases.read",
            ("model-authoring", "model-release"),
            "Read model releases and their differences",
            doing="Reading model releases",
        ),
        Action(
            "model.install",
            ("model-release",),
            "Install a model draft as a release",
            doing="Installing a model release",
        ),
        Action(
            "model.activate",
            ("model-release",),
            "Activate a release in a workspace, or migrate it",
            doing="Changing the workspace's model",
        ),
        Action(
            "workspaces.manage",
            ("workspace-admin",),
            "Create, change and delete workspaces",
            doing="Administering workspaces",
        ),
        Action(
            "feed.read",
            ("feed",),
            "Read a workspace's change feed",
            doing="Reading the change feed",
        ),
        Action(
            "subscriptions.manage",
            ("integration-admin",),
            "Manage consumer API subscriptions",
            doing="Managing consumer subscriptions",
        ),
        Action(
            "operations.read",
            ("operations",),
            "Read the running service's state and settings",
            doing="Reading the service's operations",
        ),
        Action(
            "ai.test",
            ("operations",),
            "Send the AI provider a test request",
            doing="Testing the AI provider",
        ),
        Action(
            "security.manage",
            ("security-admin",),
            "Manage people, groups, roles, grants and keys",
            doing="Security administration",
        ),
        Action(
            "jobs.use",
            ("bulk", "browse", "copy-move", "model-release", "change-sets", "model-authoring"),
            "Read, follow, cancel and confirm a job, by the group that starts its kind (D285)",
            doing="Using this job",
        ),
    )
}


@dataclass(frozen=True)
class PredefinedRole:
    key: str
    groups: tuple[str, ...]


# The predefined roles' groups (D230, D257); their names and descriptions are the ``roles`` rows
# the migration inserted.
PREDEFINED_ROLES: dict[str, tuple[str, ...]] = {
    "reader": ("browse",),
    "contributor": ("browse", "change-sets"),
    "steward": ("browse", "edit-live", "change-sets", "publish", "bulk", "ai-proposals"),
    "owner": (
        "browse",
        "edit-live",
        "change-sets",
        "publish",
        "approve",
        "bulk",
        "feed",
        "copy-move",
        "ai-proposals",
    ),
    "model-admin": ("model-authoring", "model-release", "ai-proposals"),
    "workspace-admin": ("workspace-admin", "ai-proposals"),
    "integration-admin": ("integration-admin", "feed", "ai-proposals"),
    "operator": ("operations",),
    "security-admin": ("security-admin",),
}

# What the first administrator holds at the instance (D282); the migration granted the same to
# every principal that existed before Z1.
FIRST_ADMINISTRATOR_ROLES = (
    "security-admin",
    "owner",
    "model-admin",
    "workspace-admin",
    "integration-admin",
    "operator",
)

# Groups a route checks for an option of its request rather than as its action: asking the AI
# provider is part of a feature's own route (the inference's ``assistant``, 0.16 AP1), never a route
# of its own (AP-D1).
FEATURE_GROUPS: tuple[str, ...] = ("ai-proposals",)

# Which group a job of each kind is used under, in its workspace (D285).
JOB_GROUPS: dict[str, str] = {
    "batch": "bulk",
    "import": "bulk",
    "profile": "bulk",
    "profileCheck": "bulk",
    "export": "browse",
    "move": "copy-move",
    "mappingInference": "copy-move",
    # Proposals are edits of a change set (0.16 AP2).
    "aiProposal": "change-sets",
    "migration": "model-release",
    "dryRun": "model-authoring",
    "inference": "model-authoring",
}


def group_names(keys: tuple[str, ...] | list[str]) -> str:
    """``Edit live`` or ``Edit live or Work in change sets``, for a refusal's message."""
    return " or ".join(GROUPS[key].name for key in keys)
