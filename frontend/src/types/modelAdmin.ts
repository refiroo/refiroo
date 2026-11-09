/**
 * Model administration contracts: capabilities, drafts, immutable releases, validation and
 * compilation diagnostics, semantic diffs and runtime activation state.
 */

import type { EngineModel, ModelPlacements } from "./model";
import type { Actor, Principal } from "@/types/security";

import type { AiSystemInfo } from "@/types/ai";
import type { MigrationProposal } from "./integration";

export interface ModelAdminCapabilities {
  readReleases: boolean;
  manageDrafts: boolean;
  install: boolean;
  activate: boolean;
  /** The deployment setting that enables this group's mutations. */
  setting: string;
}

export interface WorkspaceAdminCapabilities {
  manageWorkspaces: boolean;
  /** The deployment setting that enables workspace create, rename, retire, delete and set default. */
  setting: string;
}

export interface JobLimits {
  batchMaxItems: number;
  batchMaxBytes: number;
  atomicJobMaxItems: number;
  backgroundJobMaxItems: number;
  backgroundBatchMaxBytes: number;
  chunkItems: number;
  retentionDays: number;
  /** The largest import file (`IMPORT_MAX_BYTES`, 0.9 J2). */
  importMaxBytes: number;
  /** The most items a preview of an import or a batch runs (`JOB_PREVIEW_MAX_ITEMS`; 0.9 J3, K2). */
  previewMaxItems: number;
}

export interface IntegrationJobCapabilities {
  createJobs: boolean;
  runModes: ("inline" | "background")[];
  limits: JobLimits;
  setting: string;
}

export interface WebhookDeliveryLimits {
  /** The most events a subscription may batch in a request. */
  maxEventsPerBatch: number;
  maxBytes: number;
  timeoutSeconds: number;
  retryWaitsSeconds: number[];
  laterWaitSeconds: number;
  retryHours: number;
}

export interface ConsumerSubscriptionCapabilities {
  manageSubscriptions: boolean;
  /** Days the delivery log keeps a request (`CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`). */
  logRetentionDays: number;
  delivery: WebhookDeliveryLimits;
  setting: string;
}

export interface CapabilitiesResponse {
  modelAdmin: ModelAdminCapabilities;
  workspaceAdmin: WorkspaceAdminCapabilities;
  integrationJobs: IntegrationJobCapabilities;
  changeFeed: { retentionDays: number };
  consumerApi: { resolveMaxItems: number; setting: string };
  consumerSubscriptions: ConsumerSubscriptionCapabilities;
}

/** A deployment setting as `GET /system` reports it; a secret carries no value or default. */
export interface SystemSetting {
  name: string;
  group: "runtime" | "capabilities" | "limits" | "webhooks" | "ai";
  description: string;
  value: unknown;
  default: unknown;
  source: "environment" | "default";
}

/** What the deployment runs, for anyone signed in (`GET /api/v1/system`, D246). */
export interface SystemResponse {
  engine: { version: string; managementApi: string; license: string; sourceCode: string };
  schemaLanguages: string[];
  activeModelRelease: {
    id: string;
    key: string;
    name: string;
    version: string;
    schemaVersion: string;
    activatedAt: string;
  };
  /** The instance's product, readable without a workspace (0.12 HM1, D338); null when unavailable. */
  product?: { name: string; description: string | null } | null;
  /** The AI provider, if one is set (0.16 AP1). */
  ai: AiSystemInfo;
  /** Whether assistants can reach the instance (0.16 AG1). */
  mcp: { enabled: boolean };
}

/** How the deployment is configured, for operators (`GET /api/v1/system/configuration`, D246). */
export interface SystemConfiguration {
  database: { revision: string | null };
  settings: SystemSetting[];
}

export interface ModelDiagnostic {
  severity: "error" | "warning";
  code: string;
  path: string;
  message: string;
  count?: number;
}

export interface ModelCompatibility {
  classification: "compatible" | "migration_required" | "invalid";
  activeReleaseId: string;
  diagnostics: ModelDiagnostic[];
}

/** Activating a candidate into one workspace running its model (0.11 D25). */
export interface WorkspaceCompatibility {
  workspaceKey: string;
  releaseId: string;
  classification: "compatible" | "migration_required";
  diagnostics: ModelDiagnostic[];
}

/** Into the default workspace, and into each workspace running the candidate's model (D37). */
export interface CandidateCompatibility extends ModelCompatibility {
  workspaces: WorkspaceCompatibility[];
}

export interface ModelChange {
  kind: "added" | "changed" | "removed";
  path: string;
  before?: unknown;
  after?: unknown;
}

export interface ModelReleaseSummary {
  id: string;
  key: string;
  name: string;
  version: string;
  schemaVersion: string;
  modelHash: string;
  installedAt: string;
  /** Run by at least one workspace, and the keys of the workspaces running it (0.11 M1). */
  assigned: boolean;
  workspaces: string[];
  /** A retired release is not chosen again; what runs on it keeps running (0.12 MR1). */
  status: "active" | "retired";
  statusVersion: number;
  retiredAt?: string | null;
  /** Nothing refers to it, so it may be deleted; otherwise the first reason. */
  deletable: boolean;
  deleteBlockedBy?: "running" | "history" | "importProfile" | "mapping" | null;
}

export interface ModelRelease extends ModelReleaseSummary {
  model?: Record<string, unknown>;
}

/** An installation's answer: the release, and the import profile it saved from the draft's (0.10 A5, D80). */
export interface ModelInstallation extends ModelRelease {
  importProfile?: { key: string; version: number } | null;
}

export interface ModelReleasePage {
  items: ModelReleaseSummary[];
  nextCursor: string | null;
}

/** One recorded selection of a release as the active model, with the release it replaced. */
export interface ModelReleaseActivation {
  eventId: string;
  kind: "activated" | "schemaUpgraded";
  previousReleaseId: string;
  runtimeVersion: number;
  occurredAt: string;
  actor: Actor | null;
}

export interface ModelReleaseActivationPage {
  items: ModelReleaseActivation[];
  nextCursor: string | null;
}

export interface ModelDraft {
  id: string;
  name: string;
  baseReleaseId: string | null;
  /** The workspace it was opened from, which it applies to (0.16 WM1). */
  workspaceKey?: string | null;
  model: Record<string, unknown>;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface ModelDraftPage {
  items: ModelDraft[];
  nextCursor: string | null;
}

export interface ModelValidation {
  valid: boolean;
  diagnostics: ModelDiagnostic[];
}

export interface ModelCompilation extends ModelValidation {
  model?: Record<string, unknown>;
  modelHash?: string;
  compatibility: CandidateCompatibility;
  /** The release the draft is compared with (D37); null for a new model. */
  againstReleaseId?: string | null;
  /** Empty for a draft that does not compile. */
  changes: ModelChange[];
  /** The draft's consumer API definitions against the release it is compared with's (0.9 C1, 0.11
   * D37); absent when invalid or for a new model. */
  consumerContracts?: ModelConsumerContracts;
}

/** Consumer API definitions checked against what the active release's consumers read (C-D17). */
export interface ModelConsumerContracts {
  classification: "compatible" | "version_required";
  activeReleaseId: string;
  diagnostics: ModelDiagnostic[];
}

export interface ModelReleaseDiff {
  againstReleaseId: string;
  releaseId: string;
  changes: ModelChange[];
  /** Activating the release into the workspace the diff names, the default one without (D52). */
  compatibility: CandidateCompatibility;
  consumerContracts?: ModelConsumerContracts;
}

/**
 * Raising a release of a schema language that left the window to the window's (0.12 UW1, D444):
 * the preview (`applied` false) changes nothing; the confirmed answer says what was rewritten.
 */
export interface ModelReleaseRaising {
  applied: boolean;
  releaseId: string;
  releaseKey: string;
  releaseVersion: string;
  schemaFrom: string;
  schemaTo: string;
  consumerApisRewritten: number;
  /** The hash a confirmation names as `expectedModelHash`. */
  modelHash: string;
  /** The workspaces that run the release and return once it is raised. */
  workspaces: { key: string; label: string }[];
}

/** The release a workspace runs and its assignment's version, which activation claims (0.11 M1). */
export interface WorkspaceModel {
  workspaceKey: string;
  releaseId: string;
  releaseKey: string;
  /** The release's name, which names the model to people (0.11 D53). */
  releaseName: string;
  releaseVersion: string;
  schemaVersion: string;
  modelHash: string;
  version: number;
  updatedAt: string;
}

/** A workspace's new assignment, and its change sets left on the release it no longer runs (D26). */
export interface WorkspaceModelActivation extends WorkspaceModel {
  changeSetsLeftBehind: { id: string; name: string | null; version: number }[];
}

/** One operation of a draft's history (0.10 A2, ADR-041). */
/** A view or panel an operation took away because it could stand in no application after it. */
export interface RemovedElement {
  kind: "view" | "panel";
  applicationKey: string;
  view?: string;
  detail?: string;
  panel?: string;
  name: string;
}

/** An element of the base release a step changes that needs a migration, and what holds it (0.13 MG). */
export interface DraftOperationMigration {
  element: Record<string, string>;
  keyChange: boolean;
  impact: { records: number | string; values: number | string; relationships: number | string };
}

export interface ModelDraftOperationEntry {
  sequence: number;
  step: number;
  kind: string;
  parameters: Record<string, unknown>;
  inverse: Record<string, unknown>;
  /** What the operation could not keep anywhere (a move between applications); empty mostly. */
  removed?: RemovedElement[];
  /** What the operation changes that needs a migration when the draft is installed (0.13 MG). */
  migration?: DraftOperationMigration[];
  draftVersion: number;
  /** Who applied it (0.12 Z4); null for an operation from before sign-in. */
  author: Principal | null;
  at: string;
  undone: boolean;
  origin: {
    type: "request" | "undo" | "redo" | "patch" | "proposal";
    steps?: number[];
    step?: number;
    /** A proposal step's (0.10 A6): the proposal, its pattern and its summary. */
    proposalId?: string;
    pattern?: string;
    summary?: string;
    /** A step a session made: who asked for it, named as they are now (0.16 AP9). */
    proposedBy?: string;
    proposedByName?: string;
    taskId?: string;
  };
}

export interface ModelDraftOperationPage {
  items: ModelDraftOperationEntry[];
  nextCursor: string | null;
  prevCursor: string | null;
}

/** A typed operation on a draft's model: its `kind` and parameters (API.md § Kinds). */
export type DraftOperation = { kind: string } & Record<string, unknown>;

/** The draft after a step: its version, the step's entries and the compiler's diagnostics. */
export interface ModelDraftStep {
  version: number;
  entries: ModelDraftOperationEntry[];
  valid: boolean;
  diagnostics: ModelDiagnostic[];
  /** The dry run the step queued (0.10 A5, D79), or null when it queued none. */
  dryRun?: { state: "checking"; jobId: string } | null;
}

/** Whether an element is absent from the draft's base release, declared differently, or as it was. */
export type OutlineMark = "new" | "changed" | "released";

/** An element as operations name it: `{objectType}`, `{objectType, attributeType}`, `{applicationKey, group}`, `{applicationKey, detail, panel}`… */
export type OutlineElement = Record<string, string>;

export interface OutlineTypeNode {
  objectType: string;
  children: OutlineTypeNode[];
}

export interface OutlineView {
  key: string;
  name: string;
  type?: string | null;
  /** The collection the view belongs to: its source type. */
  collection?: string | null;
  shows: string[];
  /** A relation matrix's configuration, as the model declares it. */
  matrix?: Record<string, unknown> | null;
  mark: OutlineMark;
}

/** An entry of a navigation group: a collection by its type, or a relation matrix by its view. */
export interface OutlineNavigationEntry {
  collection?: string;
  view?: string;
}

export interface OutlineNavigationGroup {
  key: string;
  label: string;
  collapsed: boolean;
  /** The group's collections only (types). */
  collections: string[];
  /** Collections and matrices in the group's one order. */
  entries: OutlineNavigationEntry[];
  mark: OutlineMark;
}

export interface OutlineApplication {
  key: string;
  name: string;
  icon?: string | null;
  color?: string | null;
  defaultView?: string | null;
  objectTypeKeys: string[];
  tree: OutlineTypeNode[];
  navigation: {
    groups: OutlineNavigationGroup[];
    ungrouped: string[];
    /** Collection key to the view its sidebar entry opens on. */
    opens: Record<string, string>;
  };
  views: OutlineView[];
  /** The types it could stop listing: unused here, listed elsewhere, not released here. */
  unlistable: string[];
  mark: OutlineMark;
}

export interface OutlineAttribute {
  attributeType: string;
  name: string;
  valueType?: string | null;
  required: boolean;
  readOnly: boolean;
  unique: boolean;
  sharedWith: string[];
  mark: OutlineMark;
}

export interface OutlineObjectType {
  key: string;
  name: string;
  pluralName: string;
  icon?: string | null;
  description?: string | null;
  rootCreatable: boolean;
  parents: string[];
  attributes: OutlineAttribute[];
  mark: OutlineMark;
}

export interface OutlineAttributeType {
  key: string;
  name: string;
  valueType?: string | null;
  features: Record<string, unknown>;
  boundBy: string[];
  mark: OutlineMark;
}

export interface OutlineRelationType {
  key: string;
  reverseKey?: string | null;
  name: string;
  reverseName?: string | null;
  containment: boolean;
  mark: OutlineMark;
}

export interface OutlineRelation {
  relationType: string;
  from: string;
  to: string;
  cardinality?: string | null;
  required: boolean;
  containment: boolean;
  /** The ancestor type under which a source may hold only one target; absent without the rule. */
  uniquePer?: string | null;
  /** Which records may be chosen at each end (0.9 K7); absent without criteria. */
  candidates?: {
    from?: { field: string; op: string; value: string | number | boolean }[];
    to?: { field: string; op: string; value: string | number | boolean }[];
  } | null;
  mark: OutlineMark;
}

export interface OutlineDiagnostic extends ModelDiagnostic {
  element: OutlineElement | null;
}

/**
 * A draft compiled as `GET /model` serves the active model, with its placements
 * (`GET /model-drafts/{id}/model`, 0.10 A4b, D43); no model when the draft does not compile.
 */
export interface ModelDraftModel {
  version: number;
  valid: boolean;
  diagnostics: OutlineDiagnostic[];
  model?: EngineModel;
  placements?: ModelPlacements;
}

/** A consumer API definition checked against what the active release's consumers read (0.10 A4c, D55). */
export interface OutlineConsumerContract {
  classification: "compatible" | "version_required";
  diagnostics: OutlineDiagnostic[];
}

/** A consumer API definition of the draft as the editor lists it (0.10 A4c); `contract` is null while
 * the draft does not compile. */
export interface OutlineConsumerApi {
  key: string;
  name: string;
  description?: string | null;
  contractVersion?: number | null;
  exposes: { objectType: string; publicName: string }[];
  counts: { fields: number; related: number; lists: number; filters: number; events: number };
  mark: OutlineMark;
  contract: OutlineConsumerContract | null;
}

/** A consumer API definition as written in the draft (schema 0.9, CONSUMER_API "Definition shape"). */
export type ConsumerDefinition = Record<string, unknown>;

/** `GET /model-drafts/{id}/consumer-apis/{consumerApi}` (0.10 A4c, D56). */
export interface ModelDraftConsumerApi {
  version: number;
  valid: boolean;
  definition: ConsumerDefinition;
  /** With every default written out, when the draft compiles. */
  expanded?: ConsumerDefinition;
  contract?: OutlineConsumerContract;
}

/** The documents an integration takes from a draft's consumer API (D56). */
export type ConsumerApiDocumentKind = "schema" | "example" | "openapi";

/** A draft's structure as the editor shows it (`GET /model-drafts/{id}/outline`, 0.10 A4a, D36). */
export interface ModelDraftOutline {
  version: number;
  baseReleaseId: string | null;
  release: { key?: string | null; name?: string | null; version?: string | null; schemaVersion?: string | null };
  baseRelease: { key?: string | null; name?: string | null; version?: string | null } | null;
  applications: OutlineApplication[];
  objectTypes: OutlineObjectType[];
  attributeTypes: OutlineAttributeType[];
  relationTypes: OutlineRelationType[];
  relations: OutlineRelation[];
  consumerApis: OutlineConsumerApi[];
  valid: boolean;
  diagnostics: OutlineDiagnostic[];
}

/** One type the draft's migration changes (0.13 MG). */
export interface DraftMigrationRow {
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  fromName: string;
  toName: string;
  fromApplicationKeys: string[];
  toApplicationKeys: string[];
  toApplicationKey: string | null;
  parent: "unchanged" | "topLevel" | "changed";
  attributes: { attributeTypeKey: string; from: string }[];
  records: { records: number | string; values: number | string; relationships: number | string };
}

/** A released element whose key changed, with the consumer APIs naming the old key. */
export interface DraftMigrationKeyChange {
  element: Record<string, string>;
  from: string;
  to: string;
  consumerApis: { key: string; name: string }[];
}

/** The migration a draft states against its base release (`GET /model-drafts/{id}/migration`, 0.13 MG). */
export interface DraftMigration extends MigrationProposal {
  baseReleaseId: string | null;
  draftVersion: number;
  required: boolean;
  /** The history entries that need a migration. */
  steps: { step: number; sequence: number; kind: string; migration: DraftOperationMigration[] }[];
  rows: DraftMigrationRow[];
  keyChanges: DraftMigrationKeyChange[];
  notes: { code: string; message: string }[];
  landing?: {
    workspaceKey: string;
    moved: number;
    createdRecords: number;
    createdRelationships: number;
    losses: { objectTypeKey: string; records?: number; values?: number; relationships?: number }[];
    refused: { objectTypeKey: string | null; code: string; message: string; count: number; examples: string[] }[];
  } | null;
}
