/**
 * The running instance as Settings › Operations shows it (Product 0.11 O1, O2): every engine
 * process as it last reported itself, whether each workspace is served, the instance's figures and
 * the backup rehearsals recorded with `app.cli.restore_check`.
 */

import type { PageNavigation } from "@/types/runtime";

export type DatabaseReason = "poolExhausted" | "tooManyConnections" | "transactionEnded" | "unreachable" | "error";
export type UnavailableReason = "unsupportedSchema" | "invalid" | "notLoaded";

export interface ProcessThread {
  name:
    "jobWorker" | "exportWorker" | "assistantWorker" | "jobListener" | "eventDeriver" | "webhookDispatcher" | "mailSender" | "heartbeat";
  state: "running" | "failing" | "off";
  reason?: DatabaseReason | null;
  since?: string | null;
}

/** `GET /api/v1/system/processes`, one item. */
export interface EngineProcess {
  id: string;
  host: string;
  pid: number;
  engineVersion: string;
  startedAt: string;
  heartbeatAt: string;
  state: "live" | "silent";
  ready: boolean;
  threads: ProcessThread[];
  pool: { size: number; maxOverflow: number; inUse: number };
  unavailableReleases: { releaseId: string; schemaVersion: string; reason: UnavailableReason }[];
  counters: { requests: number; serverErrors: number; databaseUnavailable: Record<string, number> };
}

export interface ReleaseIdentity {
  id: string;
  key: string;
  version: string;
  schemaVersion: string;
}

/** `GET /api/v1/system/readiness`, one item. */
export interface WorkspaceReadiness {
  workspaceKey: string;
  release: ReleaseIdentity | null;
  state: "served" | "unavailable";
  unavailableIn: { processId: string; reason: UnavailableReason; schemaVersion: string }[];
}

/** `GET /api/v1/system/summary` (0.11 O2, D201). */
export interface SystemSummary {
  processes: { live: number; silent: number };
  workspaces: { served: number; unavailable: number };
  jobs: { kind: string; state: "queued" | "running" | "awaiting_confirmation"; count: number }[];
  webhookSubscriptions: { active: number; failing: number; suspended: number };
}

export interface RehearsalWorkspace {
  workspaceKey: string;
  release: ReleaseIdentity | null;
  state: "served" | "unavailable";
  reason: "unsupportedSchema" | "invalid" | "noRelease" | null;
  records: number;
  relations: number;
  openChangeSets: number;
  publications: number;
  liveRecords: number;
}

/** `GET /api/v1/system/backup-rehearsals`, one item (0.11 O2, D200). */
export interface BackupRehearsal {
  id: string;
  checkedAt: string;
  backup: string | null;
  dataAsOf: string | null;
  revisionBefore: string | null;
  revisionAfter: string | null;
  engineVersion: string;
  host: string;
  result: "passed" | "failed";
  failure: { code: string; message: string } | null;
  workspaces: RehearsalWorkspace[];
}

export interface BackupRehearsalPage extends PageNavigation {
  items: BackupRehearsal[];
}
