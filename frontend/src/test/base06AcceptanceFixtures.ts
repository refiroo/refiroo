/**
 * Canonical Base 0.6 acceptance data for the seven journeys frozen in
 * docs/BASE_0_6_INTERACTION_SPEC.md.
 *
 * This intentionally uses a small behavior-only shape instead of anticipated API response types.
 * Later work packages may adapt it at test boundaries without making this fixture a second contract.
 */

type WorkspaceFixture = {
  key: string;
  label: string;
  status: "active" | "retired";
  isDefault: boolean;
  version: number;
};

type RevisionFixture = {
  id: string;
  logicalObjectId: string;
  number: number;
  lifecycle: "active" | "retired";
  modelReleaseId: string;
  derivedFromRevisionId: string | null;
  supersedesRevisionId: string | null;
  snapshot: {
    name: string;
    parentObjectId: string | null;
    attributes: Record<string, unknown>;
    requiredRelationships: Array<{
      relationTypeKey: string;
      direction: "incoming" | "outgoing";
      otherObjectId: string;
    }>;
  };
};

type DraftFixture = {
  id: string;
  logicalObjectId: string;
  version: number;
  modelReleaseId: string;
  derivedFromRevisionId: string | null;
  content: RevisionFixture["snapshot"];
};

type JourneyFixture = {
  id: `J${number}`;
  title: string;
  start: string;
  actions: readonly string[];
  observe: readonly string[];
};

const ids = {
  modelRelease06: "06000000-0000-4000-8000-000000000001",
  modelReleaseChanged: "06000000-0000-4000-8000-000000000002",
  domainConnections: "10000000-0000-4000-8000-000000000001",
  domainFinance: "10000000-0000-4000-8000-000000000002",
  codelistTimetables: "20000000-0000-4000-8000-000000000001",
  codelistRevision1: "21000000-0000-4000-8000-000000000001",
  codelistRevision2: "21000000-0000-4000-8000-000000000002",
  codelistDraftFromActive: "22000000-0000-4000-8000-000000000001",
  codelistDraftFromHistory: "22000000-0000-4000-8000-000000000002",
  languageCzech: "30000000-0000-4000-8000-000000000001",
  translationGroupConnections: "31000000-0000-4000-8000-000000000001",
  translationRetired: "32000000-0000-4000-8000-000000000001",
  translationRevision1: "33000000-0000-4000-8000-000000000001",
  newTranslation: "35000000-0000-4000-8000-000000000001",
  translationRootDraft: "34000000-0000-4000-8000-000000000001",
  translationReactivationDraft: "34000000-0000-4000-8000-000000000002",
} as const;

export const base06AcceptanceFixtures = {
  viewports: {
    desktop: { width: 1280, height: 800 },
    narrow: { width: 390, height: 844 },
  },
  model: {
    schemaVersion: "0.5",
    releaseId: ids.modelRelease06,
    releaseVersion: "0.6.0",
    applications: {
      master: { key: "rdm-master", defaultViewKey: "codelists" },
      translations: { key: "rdm-translations", defaultViewKey: "translations" },
    },
    table: {
      key: "codelists",
      objectTypeKey: "codelist",
      columns: ["name", "codelist-code", "active"],
      filterFields: ["codelist-code", "active"],
      sortFields: ["name", "codelist-code"],
      defaultSort: "name",
      pageSize: 20,
    },
    attributeCapabilities: {
      "codelist-code": {
        valueType: "text",
        features: { searchable: true, filterable: true, sortable: true },
      },
      active: {
        valueType: "boolean",
        features: { filterable: true, sortable: false },
      },
    },
    ownershipConfigurations: {
      codelist: {
        objectTypeKey: "codelist",
        containment: {
          relationTypeKey: "domain-contains-codelist",
          parentObjectTypeKey: "domain",
        },
        requiredRelationships: [],
      },
      translation: {
        objectTypeKey: "translation",
        containment: {
          relationTypeKey: "translation-group-contains-translation",
          parentObjectTypeKey: "translation-group",
        },
        requiredRelationships: [
          {
            relationTypeKey: "object-has-translation",
            direction: "incoming",
            otherObjectTypeKeys: ["domain", "codelist", "master-value"],
          },
        ],
      },
    },
  },
  workspaces: [
    { key: "default", label: "Default", status: "active", isDefault: true, version: 1 },
    { key: "central-europe", label: "Central Europe", status: "active", isDefault: false, version: 3 },
    { key: "legacy-archive", label: "Legacy archive", status: "retired", isDefault: false, version: 4 },
  ] satisfies WorkspaceFixture[],
  objects: {
    parents: {
      connectionsDomain: { id: ids.domainConnections, objectTypeKey: "domain", name: "Connections" },
      financeDomain: { id: ids.domainFinance, objectTypeKey: "domain", name: "Finance" },
      czechLanguage: { id: ids.languageCzech, objectTypeKey: "language", name: "Czech" },
      connectionsTranslationGroup: {
        id: ids.translationGroupConnections,
        objectTypeKey: "translation-group",
        name: "Connections terms",
        parentObjectId: ids.languageCzech,
      },
    },
    codelist: {
      id: ids.codelistTimetables,
      workspaceKey: "central-europe",
      applicationKey: "rdm-master",
      objectTypeKey: "codelist",
      activeRevisionId: ids.codelistRevision2,
    },
    translationBeforeRetirement: {
      id: ids.translationRetired,
      workspaceKey: "central-europe",
      applicationKey: "rdm-translations",
      objectTypeKey: "translation",
      activeRevisionId: ids.translationRevision1,
    },
    translationAfterRetirement: {
      id: ids.translationRetired,
      workspaceKey: "central-europe",
      applicationKey: "rdm-translations",
      objectTypeKey: "translation",
      activeRevisionId: null,
    },
  },
  revisions: {
    codelistRevision1: {
      id: ids.codelistRevision1,
      logicalObjectId: ids.codelistTimetables,
      number: 1,
      lifecycle: "retired",
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: null,
      supersedesRevisionId: null,
      snapshot: {
        name: "Timetable codes",
        parentObjectId: ids.domainConnections,
        attributes: {
          "codelist-code": "MOT",
          description: "Timetable classification",
          hierarchical: false,
          "translations-enabled": true,
          active: true,
        },
        requiredRelationships: [],
      },
    },
    codelistRevision2: {
      id: ids.codelistRevision2,
      logicalObjectId: ids.codelistTimetables,
      number: 2,
      lifecycle: "active",
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.codelistRevision1,
      supersedesRevisionId: ids.codelistRevision1,
      snapshot: {
        name: "Timetable types",
        parentObjectId: ids.domainConnections,
        attributes: {
          "codelist-code": "MOT",
          description: "Governed timetable types",
          hierarchical: false,
          "translations-enabled": true,
          active: true,
        },
        requiredRelationships: [],
      },
    },
    translationRevision1: {
      id: ids.translationRevision1,
      logicalObjectId: ids.translationRetired,
      number: 1,
      lifecycle: "active",
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: null,
      supersedesRevisionId: null,
      snapshot: {
        name: "Czech timetable label",
        parentObjectId: ids.translationGroupConnections,
        attributes: {
          "translated-name": "Typy navstev",
          "translated-description": null,
          active: true,
        },
        requiredRelationships: [
          {
            relationTypeKey: "object-has-translation",
            direction: "incoming",
            otherObjectId: ids.codelistTimetables,
          },
        ],
      },
    },
  } satisfies Record<string, RevisionFixture>,
  drafts: {
    codelistFromActive: {
      id: ids.codelistDraftFromActive,
      logicalObjectId: ids.codelistTimetables,
      version: 3,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.codelistRevision2,
      content: {
        name: "Timetable categories",
        parentObjectId: ids.domainFinance,
        attributes: {
          "codelist-code": "MOT-CAT",
          description: "Categories used by scheduling",
          hierarchical: false,
          "translations-enabled": true,
          active: true,
        },
        requiredRelationships: [],
      },
    },
    codelistFromHistory: {
      id: ids.codelistDraftFromHistory,
      logicalObjectId: ids.codelistTimetables,
      version: 1,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.codelistRevision1,
      content: {
        name: "Timetable codes restored",
        parentObjectId: ids.domainConnections,
        attributes: {
          "codelist-code": "MOT",
          description: "Restored from the first revision",
          hierarchical: false,
          "translations-enabled": true,
          active: true,
        },
        requiredRelationships: [],
      },
    },
    translationRoot: {
      id: ids.translationRootDraft,
      logicalObjectId: ids.newTranslation,
      version: 1,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: null,
      content: {
        name: "Czech timetable description",
        parentObjectId: ids.translationGroupConnections,
        attributes: {
          "translated-name": "Typ navstevy",
          "translated-description": "Druh planovane navstevy",
          active: true,
        },
        requiredRelationships: [
          {
            relationTypeKey: "object-has-translation",
            direction: "incoming",
            otherObjectId: ids.domainFinance,
          },
        ],
      },
    },
    translationReactivation: {
      id: ids.translationReactivationDraft,
      logicalObjectId: ids.translationRetired,
      version: 1,
      modelReleaseId: ids.modelRelease06,
      derivedFromRevisionId: ids.translationRevision1,
      content: {
        name: "Czech timetable label restored",
        parentObjectId: ids.translationGroupConnections,
        attributes: {
          "translated-name": "Typy navstev",
          "translated-description": "Obnovena publikovana verze",
          active: true,
        },
        requiredRelationships: [
          {
            relationTypeKey: "object-has-translation",
            direction: "incoming",
            otherObjectId: ids.codelistTimetables,
          },
        ],
      },
    },
  } satisfies Record<string, DraftFixture>,
  transitions: {
    retireTranslation: {
      expectedActiveRevisionId: ids.translationRevision1,
      before: {
        activeRevisionId: ids.translationRevision1,
        revisionLifecycle: "active",
      },
      after: {
        activeRevisionId: null,
        revisionLifecycle: "retired",
        logicalIdentityRetained: true,
        historyRetained: true,
      },
    },
    activateDraftFromHistory: {
      draftId: ids.codelistDraftFromHistory,
      derivedFromRevisionId: ids.codelistRevision1,
      expectedActiveRevisionId: ids.codelistRevision2,
      expectedSupersedesRevisionId: ids.codelistRevision2,
    },
  },
  listState: {
    workspaceKey: "central-europe",
    applicationKey: "rdm-master",
    viewKey: "codelists",
    search: "timetable",
    filters: [
      { field: "codelist-code", operator: "startsWith", value: "AP" },
      { field: "active", operator: "eq", value: "true" },
    ],
    sort: "-codelist-code",
    pageSize: 20,
    cursor: null,
    url: "/apps/rdm-master/views/codelists?workspaceKey=central-europe&search=timetable&filter.codelist-code.startsWith=AP&filter.active.eq=true&sort=-codelist-code&pageSize=20",
  },
  conflicts: {
    draftVersion: {
      kind: "draft-version",
      errorCode: "version_conflict",
      expectedVersion: 3,
      currentVersion: 4,
      preserve: ["name", "parentObjectId", "attributes", "requiredRelationships"],
      recovery: "compare-local-and-latest-then-explicit-save",
    },
    activeRevision: {
      kind: "active-revision",
      expectedActiveRevisionId: ids.codelistRevision2,
      currentActiveRevisionId: "21000000-0000-4000-8000-000000000003",
      preserve: ["savedDraft", "derivedFromRevisionId"],
      recovery: "review-current-active-then-explicit-activation",
    },
    uniqueness: {
      kind: "uniqueness",
      errorCode: "duplicate_attribute_value",
      field: "codelist-code",
      value: "MOT",
      conflictingObjectId: "20000000-0000-4000-8000-000000000002",
      preserve: ["completeDraft"],
      recovery: "focus-field-and-edit",
    },
    pinnedModel: {
      kind: "pinned-model-release",
      errorCode: "draft_model_release_conflict",
      draftModelReleaseId: ids.modelRelease06,
      currentModelReleaseId: ids.modelReleaseChanged,
      preserve: ["persistedDraft", "unsavedBrowserInput"],
      recovery: "explain-no-automatic-rebase-and-offer-copy",
    },
  },
  journeys: [
    {
      id: "J1",
      title: "Keep workspace and application context",
      start: "/apps/rdm-master/views/codelists?workspaceKey=default&sort=name&pageSize=20",
      actions: [
        "select Central Europe from workspace catalogue",
        "open RDM Translations",
        "return to RDM Master",
        "reload the copied URL",
      ],
      observe: [
        "stable workspace key is in URL while label is visible",
        "application switches retain workspace",
        "return restores prior Master view and query",
        "retired workspace is readable and mutation-free",
      ],
    },
    {
      id: "J2",
      title: "Find, open and return to typed table state",
      start:
        "/apps/rdm-master/views/codelists?workspaceKey=central-europe&search=timetable&filter.codelist-code.startsWith=AP&filter.active.eq=true&sort=-codelist-code&pageSize=20",
      actions: ["apply fixture filters and sort", "open Timetable types", "use visible back action"],
      observe: ["typed query reaches server", "object context matches route", "exact list URL is restored"],
    },
    {
      id: "J3",
      title: "Create and activate a populated root draft",
      start: "/apps/rdm-translations/views/translations?workspaceKey=central-europe",
      actions: ["create Translation from translationRoot", "review activation", "activate with null active ID"],
      observe: ["no active projection exists before activation", "revision 1 contains parent attributes and target"],
    },
    {
      id: "J4",
      title: "Revise complete active content",
      start: `logical-object:${ids.codelistTimetables}`,
      actions: ["derive codelistFromActive", "edit complete form", "save draft", "review and activate"],
      observe: ["active content is unchanged before activation", "all projections publish atomically"],
    },
    {
      id: "J5",
      title: "Branch from an earlier retired revision",
      start: `revision:${ids.codelistRevision1}`,
      actions: ["derive codelistFromHistory", "activate while revision 2 is active"],
      observe: [`Created from is ${ids.codelistRevision1}`, `Superseded on activation is ${ids.codelistRevision2}`],
    },
    {
      id: "J6",
      title: "Retire without replacement and reactivate through a draft",
      start: `logical-object:${ids.translationRetired}`,
      actions: ["preview retirement", "cancel", "confirm retirement", "find retired object", "derive and activate"],
      observe: ["identity and history survive retirement", "new active revision derives from retired revision 1"],
    },
    {
      id: "J7",
      title: "Recover without losing input",
      start: `draft:${ids.codelistDraftFromActive}`,
      actions: ["exercise each conflict fixture independently", "follow its explicit recovery action"],
      observe: ["all entered fields remain", "no partial candidate publishes", "focus reaches conflict summary"],
    },
  ] satisfies JourneyFixture[],
} as const;

export type Base06AcceptanceFixtures = typeof base06AcceptanceFixtures;
