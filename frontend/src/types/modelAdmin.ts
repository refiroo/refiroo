/**
 * Model administration contracts: capabilities, drafts, immutable releases, validation and
 * compilation diagnostics, semantic diffs and runtime activation state.
 */

export interface ModelAdminCapabilities {
  readReleases: boolean;
  manageDrafts: boolean;
  install: boolean;
  activate: boolean;
}

export interface CapabilitiesResponse {
  modelAdmin: ModelAdminCapabilities;
  workspaceAdmin: {
    manageWorkspaces: boolean;
  };
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
