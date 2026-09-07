/** Canonical behavior-only data for the ADR-024 Base 0.6 journeys. */

type Graph = {
  objects: Array<{
    id: string;
    objectTypeKey: string;
    name: string;
    parentObjectId: string | null;
    attributes: Record<string, unknown>;
  }>;
  relations: Array<{
    id: string;
    relationTypeKey: string;
    fromObjectId: string;
    toObjectId: string;
    kind: "containment" | "independent";
  }>;
};
type Revision = {
  id: string;
  number: number;
  modelReleaseId: string;
  derivedFromRevisionId: string | null;
  supersedesRevisionId: string | null;
  graph: Graph;
  publicationState: "inactive" | "active" | "retired";
};
type Draft = {
  id: string;
  version: number;
  modelReleaseId: string;
  derivedFromRevisionId: string | null;
  graph: Graph;
};

const ids = {
  modelRelease06: "06000000-0000-4000-8000-000000000001",
  modelReleaseChanged: "06000000-0000-4000-8000-000000000002",
  domainConnections: "10000000-0000-4000-8000-000000000001",
  codelistTimetables: "20000000-0000-4000-8000-000000000001",
  translationTimetable: "30000000-0000-4000-8000-000000000001",
  relationTranslation: "40000000-0000-4000-8000-000000000001",
  workspaceRevision3: "50000000-0000-4000-8000-000000000003",
  workspaceRevision4: "50000000-0000-4000-8000-000000000004",
  workspaceRevision5: "50000000-0000-4000-8000-000000000005",
  draftRoot: "60000000-0000-4000-8000-000000000001",
  draftFromActive: "60000000-0000-4000-8000-000000000002",
  draftFromHistory: "60000000-0000-4000-8000-000000000003",
} as const;
const graph = {
  objects: [
    {
      id: ids.domainConnections,
      objectTypeKey: "domain",
      name: "Connections",
      parentObjectId: null,
      attributes: { active: true },
    },
    {
      id: ids.codelistTimetables,
      objectTypeKey: "codelist",
      name: "Timetable types",
      parentObjectId: ids.domainConnections,
      attributes: { "codelist-code": "MOT", active: true },
    },
    {
      id: ids.translationTimetable,
      objectTypeKey: "translation",
      name: "Czech timetable label",
      parentObjectId: null,
      attributes: { "translated-name": "Typy navstev", active: true },
    },
  ],
  relations: [
    {
      id: ids.relationTranslation,
      relationTypeKey: "object-has-translation",
      fromObjectId: ids.codelistTimetables,
      toObjectId: ids.translationTimetable,
      kind: "independent",
    },
    {
      id: "40000000-0000-4000-8000-000000000002",
      relationTypeKey: "contains-object",
      fromObjectId: ids.domainConnections,
      toObjectId: ids.codelistTimetables,
      kind: "containment",
    },
  ],
} satisfies Graph;

export const base06AcceptanceFixtures = {
  viewports: { desktop: { width: 1280, height: 800 }, narrow: { width: 390, height: 844 } },
  workspaces: [
    { key: "default", label: "Default", status: "active", isDefault: true },
    { key: "central-europe", label: "Central Europe", status: "active", isDefault: false },
    { key: "legacy-archive", label: "Legacy archive", status: "retired", isDefault: false },
  ],
  revisions: {
    revision3: {
      id: ids.workspaceRevision3,
      number: 3,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: null,
      supersedesRevisionId: null,
      graph,
      publicationState: "active",
    },
    revision4: {
      id: ids.workspaceRevision4,
      number: 4,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.workspaceRevision3,
      supersedesRevisionId: ids.workspaceRevision3,
      graph,
      publicationState: "inactive",
    },
    revision5: {
      id: ids.workspaceRevision5,
      number: 5,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.workspaceRevision3,
      supersedesRevisionId: ids.workspaceRevision4,
      graph,
      publicationState: "inactive",
    },
  } satisfies Record<string, Revision>,
  drafts: {
    root: { id: ids.draftRoot, version: 1, modelReleaseId: ids.modelRelease06, derivedFromRevisionId: null, graph },
    fromActive: {
      id: ids.draftFromActive,
      version: 3,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.workspaceRevision4,
      graph,
    },
    fromHistory: {
      id: ids.draftFromHistory,
      version: 2,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.workspaceRevision3,
      graph,
    },
  } satisfies Record<string, Draft>,
  publicationRetirement: {
    expectedActiveRevisionId: ids.workspaceRevision5 as string | null,
    after: {
      activeRevisionId: null,
      workspaceIdentityRetained: true,
      historyRetained: true,
      objectIdentitiesRetained: true,
    },
  },
  activation: {
    expectedActiveRevisionId: ids.workspaceRevision4 as string | null,
    outcome: { revisionId: ids.workspaceRevision5, publicationState: "active" },
  },
  cursors: {
    boundTo: { workspaceRevisionId: ids.workspaceRevision5, query: "timetable" },
    invalidatedBy: "workspace_revision_changed",
  },
  errors: {
    workspaceDraftVersionConflict: "workspace_draft_version_conflict",
    activeRevisionConflict: "workspace_active_revision_conflict",
    modelReleaseConflict: "workspace_draft_model_release_conflict",
    cursorInvalid: "workspace_cursor_invalid",
  },
  conflicts: {
    recordVersion: { errorCode: "version_conflict", preserve: ["recordFields", "draftContext"] },
    draftVersion: { errorCode: "workspace_draft_version_conflict", preserve: ["completeGraph"] },
    activeRevision: {
      errorCode: "workspace_active_revision_conflict",
      preserve: ["savedDraft", "derivedFromRevisionId"],
    },
    uniqueness: { errorCode: "duplicate_attribute_value", preserve: ["completeGraph"] },
    pinnedModel: {
      errorCode: "workspace_draft_model_release_conflict",
      preserve: ["persistedDraft", "unsavedBrowserInput"],
      currentModelReleaseId: ids.modelReleaseChanged,
    },
  },
  journeys: [
    {
      id: "J1",
      title: "Keep workspace and application context",
      actions: ["select workspace", "open application"],
      observe: ["workspace and application remain in route context"],
    },
    {
      id: "J2",
      title: "Find, open and return to typed table state",
      actions: ["search", "open object", "return to collection"],
      observe: ["typed filters and cursor state are restored"],
    },
    {
      id: "J3",
      title: "Create and activate a root workspace draft",
      actions: ["create draft", "validate", "activate"],
      observe: ["immutable active revision is installed"],
    },
    {
      id: "J4",
      title: "Edit and publish one coherent workspace graph",
      actions: ["edit draft graph", "publish"],
      observe: ["objects, containment and independent relations publish together"],
    },
    {
      id: "J5",
      title: "Branch from workspace history",
      actions: ["select historical revision", "derive draft", "activate"],
      observe: ["lineage and model-release pin are retained"],
    },
    {
      id: "J6",
      title: "Retire workspace publication and restore it",
      actions: ["retire workspace publication", "confirm", "derive and activate"],
      observe: ["workspace identity and revision history remain readable"],
    },
    {
      id: "J7",
      title: "Recover without losing workspace-draft input",
      actions: ["submit stale draft", "reload current draft", "retry"],
      observe: ["named conflict preserves complete draft input"],
    },
  ],
} as const;
export type Base06AcceptanceFixtures = typeof base06AcceptanceFixtures;
