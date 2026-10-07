/**
 * Integration contracts the settings pages read: the consumer API index (`GET /api/consumer`) and
 * jobs (`GET /api/v1/jobs`).
 */

/** One consumer API of the active release, as the API index lists it. */
export interface ConsumerApiIndexEntry {
  consumerApi: string;
  name: string;
  description?: string;
  contractVersion: number;
  /** The address of its OpenAPI document, below the engine's root path. */
  openapi: string;
}

/** The part of a consumer API's OpenAPI document the settings page reads: its operations. */
export interface ConsumerApiDocument {
  paths: Record<string, Record<string, { summary?: string; description?: string }>>;
}

export interface ConsumerApiIndexPage {
  items: ConsumerApiIndexEntry[];
  nextCursor: string | null;
}

export type JobState =
  "queued" | "running" | "awaiting_confirmation" | "completed" | "failed" | "cancelled" | "expired";

/** A job (`GET /api/v1/jobs`): `result` says whether every item applied. */
export interface Job {
  id: string;
  kind: "batch" | "import" | "export";
  workspaceKey: string;
  changeSetId: string | null;
  state: JobState;
  stage: string | null;
  progress: { total: number | null; processed: number };
  counts: {
    applied: number;
    rejected: number;
    unprocessed: number;
    created: number;
    updated: number;
    unchanged: number;
    deleted: number;
  };
  result: "applied" | "partial" | "rejected" | null;
  error: { code: string; message: string } | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  expiresAt: string;
  cancelRequestedAt: string | null;
}

export interface JobPage {
  items: Job[];
  nextCursor: string | null;
}
