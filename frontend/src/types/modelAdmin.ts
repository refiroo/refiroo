/**
 * Model administration contracts: capabilities, drafts, immutable releases, validation and
 * compilation diagnostics, semantic diffs and runtime activation state.
 */

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
  group: "runtime" | "capabilities" | "limits" | "webhooks";
  description: string;
  value: unknown;
  default: unknown;
  source: "environment" | "default";
}

/** What the deployment runs and how it is configured (`GET /api/v1/system`). */
export interface SystemResponse {
  engine: { version: string; managementApi: string };
  schemaLanguages: string[];
  activeModelRelease: {
    id: string;
    key: string;
    name: string;
    version: string;
    schemaVersion: string;
    activatedAt: string;
  };
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
  active: boolean;
}

export interface ModelRelease extends ModelReleaseSummary {
  model?: Record<string, unknown>;
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
}

export interface ModelReleaseActivationPage {
  items: ModelReleaseActivation[];
  nextCursor: string | null;
}

export interface ModelDraft {
  id: string;
  name: string;
  baseReleaseId: string | null;
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
  compatibility: ModelCompatibility;
  againstReleaseId?: string;
  changes: ModelChange[];
}

export interface ModelReleaseDiff {
  againstReleaseId: string;
  releaseId: string;
  changes: ModelChange[];
  compatibility: ModelCompatibility;
}

export interface ModelRuntimeState {
  activeReleaseId: string;
  activeModelHash: string;
  version: number;
  updatedAt: string;
}

/** One operation of a draft's history (0.10 A2, ADR-041). */
export interface ModelDraftOperationEntry {
  sequence: number;
  step: number;
  kind: string;
  parameters: Record<string, unknown>;
  inverse: Record<string, unknown>;
  draftVersion: number;
  author: string | null;
  at: string;
  undone: boolean;
  origin: { type: "request" | "undo" | "redo" | "patch" | "proposal"; steps?: number[]; step?: number };
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
}

/** Whether an element is absent from the draft's base release, declared differently, or as it was. */
export type OutlineMark = "new" | "changed" | "released";

/** An element as operations name it: `{objectType}`, `{objectType, attributeType}`, `{applicationKey, group}`… */
export type OutlineElement = Record<string, string>;

export interface OutlineTypeNode {
  objectType: string;
  children: OutlineTypeNode[];
}

export interface OutlineApplication {
  key: string;
  name: string;
  icon?: string | null;
  color?: string | null;
  objectTypeKeys: string[];
  tree: OutlineTypeNode[];
  navigation: {
    groups: { key: string; label: string; collapsed: boolean; collections: string[]; mark: OutlineMark }[];
    ungrouped: string[];
  };
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
  valid: boolean;
  diagnostics: OutlineDiagnostic[];
}
