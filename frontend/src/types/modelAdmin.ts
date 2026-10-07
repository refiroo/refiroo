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
