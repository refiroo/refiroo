/**
 * Integration contracts the settings pages read: the consumer API index (`GET /api/consumer`), jobs
 * (`GET /api/v1/jobs`) and webhook subscriptions (`/api/v1/consumer-subscriptions`).
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
  error: { code: string; message: string; details?: unknown } | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  expiresAt: string;
  cancelRequestedAt: string | null;
  /** The kind's choices: for an export, its `context`, `scope`, `include` and `format`. */
  parameters: Record<string, unknown>;
  /** A completed export's manifest (0.9 J1, D52); null for other jobs and states. */
  output: ExportOutput | null;
  /** For a job in a change set, the version it holds: its claim while it waits. */
  changeSetVersion?: number | null;
  policy?: ImportPolicy | null;
  /** When a waiting preview was confirmed (0.9 J3; a batch's, 0.9 K2). */
  confirmedAt?: string | null;
  /** What a previewed import (0.9 J3) or batch (0.9 K2) would do; kept after it is confirmed. */
  preview?: JobPreview | null;
  /** Per source and column, what binding made of an import's cells, once bound (0.9 J3, D86). */
  bindingReport?: BindingReportSource[] | null;
  /** What an import's file as a whole means here, once bound (0.9 J4a), such as rows whose IDs
   * are another workspace's records. */
  notices?: JobNotice[] | null;
}

export interface JobNotice {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export type ImportPolicy = "atomic" | "independent";
export type ImportOnExisting = "reject" | "overwrite";
/** Whether IDs of another workspace's records stand for this workspace's own (0.9 J5, D96). */
export type OtherWorkspaceIds = "refuse" | "counterparts";

/** `POST /api/v1/imports`'s `request` part (0.9 J2, J3): one context, a stored profile or none. */
export interface ImportRequest {
  workspaceKey: string | null;
  changeSetId: string | null;
  expectedChangeSetVersion: number | null;
  profileKey: string | null;
  policy: ImportPolicy;
  onExisting: ImportOnExisting;
  otherWorkspaceIds: OtherWorkspaceIds;
  stage: "preview" | "execute";
}

export interface JobPreview {
  coverage: "complete" | "sample";
  items: { total: number; previewed: number };
  /** An import's rows of its file; a batch has none. */
  rows?: { total: number; previewed: number; rejected: number };
  counts: { created: number; updated: number; unchanged: number; deleted: number; rejected: number };
  result: "applied" | "partial" | "rejected";
  previewedAt: string;
}

export type BindingKind =
  "field" | "attributeTypeKey" | "key" | "parent" | "relation" | "relationFlags" | "relatedRecord";

/** One column's counts: value columns count conversions, match columns what their values found. */
export interface BindingReportColumn {
  column: string;
  binding: BindingKind;
  target: string | null;
  cells: number;
  empty: number;
  refused: number;
  converted?: number;
  valueMapped?: number;
  resolved?: number;
  notFound?: number;
  ambiguous?: number;
}

export interface BindingReportSource {
  sheet: string;
  objectTypeKey: string | null;
  rows: number;
  rejectedRows: number;
  columns: BindingReportColumn[];
}

/** An item's outcome (`GET /jobs/{id}/items`): an applied one names its record, a refused one
 * carries its error and an unprocessed one its reason. */
export interface JobItemOutcome {
  index: number;
  ref: string | null;
  status: "applied" | "rejected" | "unprocessed";
  action?: "created" | "updated" | "unchanged" | "deleted";
  id?: string;
  objectTypeKey?: string;
  /** The record's version after the item; none after a live delete. */
  version?: number;
  /** The ID the file gave, when the record written is its counterpart (0.9 J5). */
  sourceId?: string;
  error?: { code: string; message: string; details?: unknown };
  reason?: string;
}

export interface JobItemPage {
  items: JobItemOutcome[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
}

/** An update item of `POST /api/v1/batches`: only the values given change, `null` clears one. */
export interface BatchUpdateItem {
  op: "update";
  ref?: string;
  target: { id: string };
  expectedVersion: number;
  attributes: { attributeTypeKey: string; value: unknown }[];
}

/** `POST /api/v1/batches` as a bulk change sends it (0.9 K2): a background preview (D112–D114). */
export interface BatchRequest {
  workspaceKey?: string;
  changeSetId?: string;
  expectedChangeSetVersion?: number;
  policy: ImportPolicy;
  run: "inline" | "background";
  stage: "execute" | "preview";
  items: BatchUpdateItem[];
}

/** One row of an import's file with its items' outcomes gathered (0.9 J3, D84). */
export interface JobRow {
  ref: string;
  sheet: string | null;
  row: number;
  status: "applied" | "rejected" | "unprocessed";
  actions: { created: number; updated: number; unchanged: number; deleted: number };
  outcomes: JobItemOutcome[];
}

export interface JobRowPage {
  items: JobRow[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
}

/** A stored import profile as the dialog reads it; the column bindings are left untyped. */
export interface ImportProfile {
  key: string;
  name: string;
  version: number;
  valid: boolean;
  problems: { path: string; code: string; message: string }[];
  sources: {
    sheet?: string | null;
    applicationKey: string;
    objectTypeKey: string;
    record?: "upsert" | "existing";
    key?: { attributeTypeKey?: string | null; column?: string | null } | null;
  }[];
}

export interface ImportProfilePage {
  items: ImportProfile[];
  nextCursor: string | null;
}

export type ExportFormat = "jsonl" | "csv" | "xlsx";
export type ExportRelations = "none" | "withinScope" | "all";

/** One criterion of the model-aware query (`where`), as an export's type carries it. */
export interface ExportCriterion {
  field: string;
  op: string;
  value: unknown;
}

/** `POST /api/v1/exports` (0.9 J1). */
export interface ExportRequest {
  workspaceKey: string;
  context: { changeSetId: string | null; publicationId: string | null };
  scope: {
    types: { objectTypeKey: string; where: ExportCriterion[] }[];
    parentObjectId: string | null;
    asOf: string | null;
  };
  include: { relations: ExportRelations };
  format: ExportFormat;
}

/** What a completed export's file holds. */
export interface ExportOutput {
  format: ExportFormat;
  contentType: string;
  counts: { records: Record<string, number>; relations: Record<string, number> };
  context: {
    workspaceKey: string;
    changeSetId: string | null;
    changeSetVersion: number | null;
    publicationId: string | null;
  };
  feedPosition: number | null;
  asOf: string | null;
  asOfApplied: string[];
  modelReleaseId: string;
  bytes: number;
  sha256: string;
}

export interface JobPage {
  items: Job[];
  nextCursor: string | null;
}

export type SuspensionReason =
  | "SUSPENDED_BY_USER"
  | "MODEL_CHANGED"
  | "CONTRACT_VERSION_CHANGED"
  | "WORKSPACE_RETIRED"
  | "DELIVERY_FAILED"
  | "FILTER_MATCHES_NOTHING"
  | "EVENTS_EXPIRED";

/** Why an attempt failed (C-D107): `status` when the receiver answered; `message` at most 200 characters. */
export interface DeliveryError {
  kind: "status" | "redirect" | "timeout" | "connection" | "tls" | "address";
  status?: number;
  message: string;
}

/** A finding of the subscription checks: what is wrong, at its body pointer. */
export interface SubscriptionFinding {
  code: string;
  message: string;
  pointer?: string;
}

/** A webhook subscription (C11, C12). `signingSecret` is in the create answer only. */
export interface Subscription {
  id: string;
  name: string;
  consumerApi: string;
  contractVersion: number;
  workspaceKey: string;
  events: string[];
  filters: Record<string, string[]>;
  url: string;
  /** The most events a request carries; 1 sends one event per request. */
  maxEventsPerBatch: number;
  /** Each event with its object, or the notification only. */
  payload: "full" | "identity";
  format: "rdm" | "cloudevents";
  status: "active" | "suspended";
  suspension: {
    reason: SuspensionReason;
    message: string;
    /** Per reason (API.md, "Suspension reasons"). */
    details: Record<string, unknown> | null;
    suspendedAt: string;
  } | null;
  acknowledgedThrough: number;
  delivery: {
    lastDeliveredAt: string | null;
    pending: {
      deliveryId: string;
      throughPosition: number;
      attempts: number;
      failingSince: string;
      lastAttemptAt: string;
      nextAttemptAt: string | null;
      lastError: DeliveryError;
    } | null;
  };
  signingKeyCreatedAt: string;
  version: number;
  createdAt: string;
  updatedAt: string;
  signingSecret?: string;
}

export interface SubscriptionPage {
  items: Subscription[];
  nextCursor: string | null;
}

/** What a subscription asks for; a create adds the consumer API and workspace. */
export interface SubscriptionSettings {
  name: string;
  events: string[];
  filters: Record<string, string[]>;
  url: string;
  maxEventsPerBatch: number;
  payload: Subscription["payload"];
  format: Subscription["format"];
}

export interface SubscriptionCreate extends SubscriptionSettings {
  consumerApi: string;
  workspaceKey: string;
}

export type SubscriptionUpdate = Partial<SubscriptionSettings> & { expectedVersion: number };

export type DeliveryStatus = "queued" | "sending" | "retrying" | "succeeded" | "failed" | "dropped";

/** One event of a request (`GET /consumer-subscriptions/{id}/deliveries`). Rows of one request
 * share its status, attempts, answer and time. */
export interface DeliveryRow {
  deliveryId: string;
  eventId: string;
  event: string;
  change: string;
  objectType: string;
  objectId: string;
  position: number;
  status: DeliveryStatus;
  attempts: number;
  responseStatus: number | null;
  sentAt: string | null;
  nextAttemptAt: string | null;
  /** A resend by hand: the delivery ID of the request it repeats. */
  resendOf: string | null;
}

export interface DeliveryRowPage {
  items: DeliveryRow[];
  nextCursor: string | null;
}

export interface DeliveryAttempt {
  number: number;
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
  responseStatus: number | null;
  error: { kind: DeliveryError["kind"]; message: string } | null;
  /** Up to 4 KiB of the receiver's answer. */
  responseBody: string | null;
}

/** A request of a webhook batch with its body as sent and every attempt. */
export interface DeliveryDetail {
  deliveryId: string;
  batchId: string;
  status: DeliveryStatus;
  events: Omit<
    DeliveryRow,
    "deliveryId" | "status" | "attempts" | "responseStatus" | "sentAt" | "nextAttemptAt" | "resendOf"
  >[];
  requestBody: unknown;
  requestBytes: number | null;
  createdAt: string;
  nextAttemptAt: string | null;
  resendOf: string | null;
  attempts: DeliveryAttempt[];
}
