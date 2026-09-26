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
type Publication = {
  id: string;
  number: number;
  modelReleaseId: string;
  derivedFromPublicationId: string | null;
  supersedesPublicationId: string | null;
  graph: Graph;
  publicationState: "inactive" | "active" | "withdrawn";
};
type ChangeSet = {
  id: string;
  version: number;
  modelReleaseId: string;
  derivedFromPublicationId: string | null;
  graph: Graph;
};

const ids = {
  modelRelease06: "06000000-0000-4000-8000-000000000001",
  modelReleaseChanged: "06000000-0000-4000-8000-000000000002",
  domainConnections: "10000000-0000-4000-8000-000000000001",
  codelistTimetables: "20000000-0000-4000-8000-000000000001",
  translationTimetable: "30000000-0000-4000-8000-000000000001",
  relationTranslation: "40000000-0000-4000-8000-000000000001",
  publication3: "50000000-0000-4000-8000-000000000003",
  publication4: "50000000-0000-4000-8000-000000000004",
  publication5: "50000000-0000-4000-8000-000000000005",
  changeSetRoot: "60000000-0000-4000-8000-000000000001",
  changeSetFromActive: "60000000-0000-4000-8000-000000000002",
  changeSetFromHistory: "60000000-0000-4000-8000-000000000003",
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
  publications: {
    publication3: {
      id: ids.publication3,
      number: 3,
      modelReleaseId: ids.modelRelease06,
      derivedFromPublicationId: null,
      supersedesPublicationId: null,
      graph,
      publicationState: "active",
    },
    publication4: {
      id: ids.publication4,
      number: 4,
      modelReleaseId: ids.modelRelease06,
      derivedFromPublicationId: ids.publication3,
      supersedesPublicationId: ids.publication3,
      graph,
      publicationState: "inactive",
    },
    publication5: {
      id: ids.publication5,
      number: 5,
      modelReleaseId: ids.modelRelease06,
      derivedFromPublicationId: ids.publication3,
      supersedesPublicationId: ids.publication4,
      graph,
      publicationState: "inactive",
    },
  } satisfies Record<string, Publication>,
  changeSets: {
    root: {
      id: ids.changeSetRoot,
      version: 1,
      modelReleaseId: ids.modelRelease06,
      derivedFromPublicationId: null,
      graph,
    },
    fromActive: {
      id: ids.changeSetFromActive,
      version: 3,
      modelReleaseId: ids.modelRelease06,
      derivedFromPublicationId: ids.publication4,
      graph,
    },
    fromHistory: {
      id: ids.changeSetFromHistory,
      version: 2,
      modelReleaseId: ids.modelRelease06,
      derivedFromPublicationId: ids.publication3,
      graph,
    },
  } satisfies Record<string, ChangeSet>,
  publicationWithdrawal: {
    expectedActivePublicationId: ids.publication5 as string | null,
    after: {
      activePublicationId: null,
      workspaceIdentityRetained: true,
      publicationsRetained: true,
      objectIdentitiesRetained: true,
    },
  },
  publish: {
    expectedActivePublicationId: ids.publication4 as string | null,
    outcome: { publicationId: ids.publication5, publicationState: "active" },
  },
  cursors: {
    boundTo: { publicationId: ids.publication5, query: "timetable" },
    invalidatedBy: "publication_changed",
  },
  errors: {
    changeSetVersionConflict: "change_set_version_conflict",
    activePublicationConflict: "workspace_active_publication_conflict",
    modelReleaseConflict: "change_set_model_release_conflict",
    cursorInvalid: "workspace_cursor_invalid",
  },
  conflicts: {
    recordVersion: { errorCode: "version_conflict", preserve: ["recordFields", "changeSetContext"] },
    changeSetVersion: { errorCode: "change_set_version_conflict", preserve: ["completeGraph"] },
    activePublication: {
      errorCode: "workspace_active_publication_conflict",
      preserve: ["savedChangeSet", "derivedFromPublicationId"],
    },
    uniqueness: { errorCode: "duplicate_attribute_value", preserve: ["completeGraph"] },
    pinnedModel: {
      errorCode: "change_set_model_release_conflict",
      preserve: ["persistedChangeSet", "unsavedBrowserInput"],
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
      title: "Create and publish a root change set",
      actions: ["create change set", "validate", "publish"],
      observe: ["immutable active publication is installed"],
    },
    {
      id: "J4",
      title: "Edit and publish one coherent workspace graph",
      actions: ["edit change set graph", "publish"],
      observe: ["objects, containment and independent relations publish together"],
    },
    {
      id: "J5",
      title: "Branch from an earlier publication",
      actions: ["select publication", "derive change set", "publish"],
      observe: ["lineage and model-release pin are retained"],
    },
    {
      id: "J6",
      title: "Withdraw a publication and derive new work from it",
      actions: ["withdraw publication", "confirm designation removal", "derive and publish changes"],
      observe: ["live data and immutable publications remain available"],
    },
    {
      id: "J7",
      title: "Recover without losing change-set input",
      actions: ["submit stale change set", "reload current change set", "retry"],
      observe: ["named conflict preserves complete change set input"],
    },
  ],
} as const;
export type Base06AcceptanceFixtures = typeof base06AcceptanceFixtures;
