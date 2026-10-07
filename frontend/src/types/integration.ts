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
