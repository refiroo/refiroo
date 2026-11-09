/**
 * Integration contracts the settings pages read: the consumer API index (`GET /api/consumer`), jobs
 * (`GET /api/v1/jobs`) and webhook subscriptions (`/api/v1/consumer-subscriptions`).
 */

import type { AiProposalTally } from "@/types/ai";
import type { MoveSummary } from "@/types/moves";
import type { Principal } from "@/types/security";

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
  /** `profile` and `dryRun` (0.10 A3): a source file's profile and a model draft's dry run. */
  kind:
    | "batch"
    | "import"
    | "export"
    | "profile"
    | "dryRun"
    | "inference"
    | "profileCheck"
    | "migration"
    | "mappingInference"
    | "move"
    | "aiProposal"
    | "aiTask";
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
  /** A migration's summary once previewed (0.11 V1): what its confirmation binds. */
  migration?: MigrationSummary | null;
  /** A move's dry run summary (0.11 X2), and what its load opened (X3). */
  move?: MoveSummary | null;
  /** An `aiProposal` job's tally, updated as it runs (0.16 AP2); null for other jobs. */
  aiProposal?: AiProposalTally | null;
  /** Who submitted it, whose permissions it runs with (0.12 Z2, Z4); null from before Z2. */
  requestedBy: Principal | null;
  /** The assistant task or model draft the job belongs to (0.13 JG); null for neither. */
  origin?: JobOrigin | null;
}

/** Where a job comes from (0.13 JG): an assistant task (and its session's jobs) or a model draft. */
export interface JobOrigin {
  kind: "aiTask" | "modelDraft";
  id: string;
  name: string;
}

/** A group of related jobs (`GET /jobs?grouped=true`, 0.13 JG): the jobs of one origin, per state. */
export interface JobGroup {
  origin: JobOrigin;
  jobs: number;
  states: Record<JobState, number>;
  latestAt: string;
}

/** A row of the grouped list: a group with its newest job, or a job of no origin (`group` null). */
export interface JobGroupRow {
  job: Job;
  group: JobGroup | null;
}

export interface JobGroupPage {
  items: JobGroupRow[];
  nextCursor: string | null;
}

/** A migration's items by outcome (0.11 V1, D68). */
export interface MigrationCounts {
  conversion: number;
  reclassified: number;
  loss: number;
  refused: number;
  /** Records and relationships a split or a list conversion creates (0.13 MG); named only then. */
  created?: number;
}

export type MigrationOutcome = keyof MigrationCounts;

/** What a migration's preview found, and the assignment version and feed position it read (D74). */
export interface MigrationSummary {
  targetReleaseId: string;
  currentReleaseId: string;
  expectedVersion: number;
  feedPosition: number;
  counts: MigrationCounts;
  /** A migration that publishes a change set (0.11 V2): the change set, its reviewed version and
   * the workspace's active publication the preview read; once executed, the new publication. */
  changeSetId?: string;
  changeSetVersion?: number;
  activePublicationId?: string;
  publicationId?: string;
}

/** One item a migration changes (D72). */
export interface MigrationRow {
  index: number;
  outcome: MigrationOutcome;
  code: string;
  objectId: string;
  objectName?: string;
  objectTypeKey?: string;
  targetObjectTypeKey?: string;
  applicationKey?: string;
  targetApplicationKey?: string;
  attributeTypeKey?: string;
  targetAttributeTypeKey?: string;
  relationId?: string;
  relationTypeKey?: string;
  toObjectId?: string;
  before?: unknown;
  after?: unknown;
  path?: string;
  message?: string;
}

export interface MigrationRowPage {
  items: MigrationRow[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
}

/** What a type of the workspace's model became in the target release (D70). */
export interface MigrationTypeMapping {
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  attributes?: { attributeTypeKey: string; from: string | null }[];
  /** The application its records go to, when the target lists the type in several (0.13 MG). */
  toApplicationKey?: string;
}

/** What a relation type of the workspace's model became in the target (0.13 MG). */
export interface MigrationRelationTypeMapping {
  fromRelationTypeKey: string;
  toRelationTypeKey: string;
}

/** A type split in the target: each record holding a moved value gets a record of the new type (MG). */
export interface MigrationSplit {
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  attributes: string[];
  relationTypeKey: string;
  cardinality?: string;
}

/** An attribute turned into a list type: its distinct values become records (MG). */
export interface MigrationListConversion {
  fromObjectTypeKey: string;
  attributeTypeKey: string;
  toObjectTypeKey: string;
  relationTypeKey: string;
}

/** What a model draft's steps imply for a workspace migration, as its request takes them (MG). */
export interface MigrationProposal {
  typeMappings: MigrationTypeMapping[];
  relationTypeMappings: MigrationRelationTypeMapping[];
  splits: MigrationSplit[];
  listConversions: MigrationListConversion[];
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
  /** A stored source file imported in place of a file sent (0.10 A3, D5). */
  sourceFileId?: string;
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
  /** What the batch's delete items would remove together (0.9 K2b, D121); none when nothing is deleted. */
  deletion?: DeletionTotals;
  result: "applied" | "partial" | "rejected";
  previewedAt: string;
}

/** Records by type, the relationships incident to them, and those reaching records that stay. */
export interface DeletionTotals {
  objectCount: number;
  objectsByType: Record<string, number>;
  relationshipCount: number;
  retainedAssociationCount: number;
}

/** One delete item's impact, with the token that confirms exactly it (0.9 K2b, D120). */
export interface DeletionImpact extends DeletionTotals {
  deletionPreviewToken: string;
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
  /** A delete item's impact (0.9 K2b). */
  impact?: DeletionImpact;
  /** A delete item whose record goes with this earlier item's impact (D122). */
  deletedWithItem?: number;
  /** A relationship item's relationship; absent when an `ensureNoRelation` found none (0.9 K3). */
  relationId?: string;
  /** The claimed or replaced set's version after the item. */
  relationSetVersion?: number;
  /** The set's version a replacement found, which confirming a preview claims (0.9 K3, D130). */
  previousRelationSetVersion?: number;
  /** A set replacement's relationships. */
  relationIds?: { created: string[]; kept: string[]; removed: string[] };
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
  attributes?: { attributeTypeKey: string; value: unknown }[];
  /** The new parent; `null` moves the record to the top level (UA9). */
  parent?: { id: string } | null;
}

/** A record deleted with what depends on it, confirmed by the preview (0.9 K2b, D120). */
export interface BatchDeleteItem {
  op: "delete";
  ref?: string;
  target: { id: string };
  expectedVersion: number;
  cascade: boolean;
}

/** A relationship ensured between two records; without values an existing one is unchanged (0.9 K3). */
export interface BatchEnsureRelationItem {
  op: "ensureRelation";
  ref?: string;
  relationTypeKey: string;
  from: { id: string };
  to: { id: string };
}

/** The relationship between two records removed, or unchanged when there is none (0.9 K3, D129). */
export interface BatchEnsureNoRelationItem {
  op: "ensureNoRelation";
  ref?: string;
  relationTypeKey: string;
  from: { id: string };
  to: { id: string };
}

/** A record's relationships of one binding and direction made exactly the targets (0.9 K3, D130). */
export interface BatchReplaceRelationSetItem {
  op: "replaceRelationSet";
  ref?: string;
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  direction: "outgoing" | "incoming";
  anchor: { id: string };
  targets: { object: { id: string } }[];
}

export type BatchRelationItem = BatchEnsureRelationItem | BatchEnsureNoRelationItem | BatchReplaceRelationSetItem;

/** `POST /api/v1/batches` as a bulk change sends it (0.9 K2): a background preview (D112–D114). */
/** A batch run inline: the finished job and the first page of its items' outcomes (UA9). */
export interface BatchResult {
  job: Job;
  items: JobItemOutcome[];
  nextCursor: string | null;
}

export interface BatchRequest {
  workspaceKey?: string;
  changeSetId?: string;
  expectedChangeSetVersion?: number;
  policy: ImportPolicy;
  run: "inline" | "background";
  stage: "execute" | "preview";
  items: BatchUpdateItem[] | BatchDeleteItem[] | BatchRelationItem[];
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

/** A profile's last load (0.10 A5c): the latest import naming it and what became of what it loaded. */
export interface ImportProfileLastLoad {
  jobId: string;
  state: string;
  fileName: string | null;
  sourceFileId: string | null;
  workspaceKey: string;
  changeSetId: string | null;
  createdAt: string;
  finishedAt: string | null;
  counts: { created: number; updated: number; deleted: number; rejected: number };
  outcome: "live" | "inChangeSet" | "published" | "discarded" | null;
  publicationId: string | null;
}

/** A stored import profile as the screens read it; the column bindings are left untyped. */
export interface ImportProfile {
  lastLoad?: ImportProfileLastLoad | null;
  key: string;
  name: string;
  version: number;
  checkedAgainst: string;
  /** The model the profile belongs to: its release key (0.11 D9). */
  modelKey: string;
  valid: boolean;
  problems: { path: string; code: string; message: string }[];
  createdAt: string;
  updatedAt: string;
  csv?: { delimiter: string } | null;
  sources: ImportProfileSource[];
  valueMaps: Record<string, Record<string, unknown>>;
}

export interface ImportProfileSource {
  sheet?: string | null;
  applicationKey: string;
  objectTypeKey: string;
  record?: "upsert" | "existing";
  key?: {
    attributeTypeKey?: string | null;
    column?: string | null;
    versionColumn?: string | null;
    nameColumn?: string | null;
  } | null;
  /** What a load does with the records no row names (0.10 A5c, D82); report when absent. */
  missing?: "report" | "delete" | null;
  /** What a load does with a row whose key is empty (0.10 A7, D110); refuse when absent. */
  rowsWithoutKey?: "refuse" | "skip" | null;
  columns: Record<string, unknown>[];
  [member: string]: unknown;
}

export interface ImportProfilePage {
  items: ImportProfile[];
  nextCursor: string | null;
}

export type ExportFormat = "jsonl" | "csv" | "xlsx";
/** The technical tables, or a workbook for people shaped by one collection (0.9 J6). */
export type ExportLayout = "technical" | "people";

/** What a workbook for people holds (0.9 J6, D188). */
export interface PeopleLayout {
  /** The main sheet's columns, as a table view names them. */
  columns: string[];
  /** The relationships (relation keys or reverse keys) that get a sheet of their own. */
  sheets: string[];
  /** A `related:<key>` column's field shown instead of the related records' names. */
  columnFields: Record<string, string>;
  /**
   * Owned records' sheets laid out as columns per parent (0.9 J6a): the parents added to those
   * already holding one, and the fields each parent gets a column of.
   */
  ownedColumns?: Record<string, { parents: string[]; fields?: string[] }>;
  /** The relationships whose cells offer a list to choose from; every one when omitted (D197). */
  referenceLists?: string[];
}
export type ExportRelations = "none" | "withinScope" | "all";

/**
 * One criterion of the model-aware query (`where`), as an export's type carries it: a field's, or a
 * relationship hop (`related`, 0.9 K6) inverted by `not`.
 */
export type ExportCriterion =
  | { field: string; op: string; value: unknown }
  | {
      related: { relationTypeKey: string; direction: "outgoing" | "incoming"; where: ExportCriterion[] };
      not?: boolean;
    };

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
  layout?: ExportLayout;
  people?: PeopleLayout;
}

/** What a completed export's file holds. */
export interface ExportOutput {
  format: ExportFormat;
  layout?: ExportLayout;
  /** A workbook for people's sheets, in order. */
  sheets?: string[];
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
  /** `workspace`: the workspace's change-set events, which name no consumer API (0.12 A2). */
  source: "consumerApi" | "workspace";
  consumerApi: string | null;
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
  /** The end of a rotation's overlap, while deliveries are signed with both keys (0.12 K1); null otherwise. */
  previousSigningKeyExpiresAt: string | null;
  /** Who created it; null for a subscription from before 0.12 Z3 (D310). */
  owner?: { kind: "user" | "client"; id: string; name: string } | null;
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
