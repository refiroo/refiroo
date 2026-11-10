/** Loading a workbook with the AI assistant (0.16 AP6a): the task, its design, check and result. */

import type { AiOrigin } from "@/types/ai";
import type { PageNavigation } from "@/types/runtime";
import type { MigrationListConversion, MigrationRelationTypeMapping, MigrationSplit } from "@/types/integration";
import type { Principal } from "@/types/security";

export type AiTaskState =
  "reading" | "checking" | "checked" | "loading" | "loaded" | "failed" | "cancelled" | "stopped";
export type AiTaskPhase = "profiling" | "reading" | "designing" | "checking";
/** Who made a choice: the rules, the assistant, or the person (a person's choice is never overwritten). */
export type AiTaskOwner = "rules" | "assistant" | "person";
/** What a table is: an update of a type's records, new data (not loaded in this version) or notes for people. */
export type AiTaskReadingKind = "update" | "newData" | "notData";

export interface AiTaskChoice<T> {
  value: T;
  owner: AiTaskOwner;
}

export interface AiTaskChoices {
  newRecords: AiTaskChoice<"create" | "leaveOut">;
  names: AiTaskChoice<"file" | "stored">;
  missing: AiTaskChoice<"leave" | "remove">;
  load: AiTaskChoice<boolean>;
}

export interface AiTaskKeyOption {
  column: string;
  header: string;
  key: { attributeTypeKey?: string; field?: string };
  matched: number;
}

export interface AiTaskMeaning {
  value: string;
  record: { id: string; name: string };
  to: string;
  reason: string;
  confidence: number;
  origin: AiOrigin;
}

export interface AiTaskColumn {
  column: string;
  header: string;
  binding: Record<string, unknown> | null;
  /** The binding's kind (`field`, `attributeTypeKey`, `parent`, `relation`, `relatedRecord`, `ignore`, `other`...). */
  kind?: string | null;
  /** A plain sentence of what the column fills. */
  label?: string;
  /** Why the column is not loaded, when the type has no such column. */
  leftOut: string | null;
  /** A column the followed profile does not read and its earlier file had too: needs no decision. */
  known?: boolean;
  owner: AiTaskOwner;
  origin?: AiOrigin | null;
}

/** What still needs the person on a table; empty when nothing does or the person has decided. */
export type AiTaskAttention =
  "newKeys" | "namesDiffer" | "missing" | "meaning" | "leftOutColumns" | "notLoaded" | "noParent";

export interface AiTaskLeftOut {
  column: string;
  header: string;
  reason: string;
}

/** A stored import profile the reading (or one table of it) follows. */
export interface AiTaskProfileRef {
  key: string;
  name: string;
  version: number;
  source?: string;
}

export interface AiTaskTable {
  table: string;
  sheet: string;
  range: string | null;
  list: number | null;
  rows: number;
  as: AiTaskReadingKind;
  objectTypeKey: string | null;
  applicationKey: string | null;
  /** The types this type may be contained in, to group a type's tables under its parent's. */
  parentTypeKeys?: string[];
  typeName: string | null;
  reason: string;
  evidence: string;
  owner: AiTaskOwner;
  origin?: AiOrigin | null;
  profile?: AiTaskProfileRef | null;
  /** The source's fixed parent, when the type is contained in another. */
  parent?: { objectTypeKey: string; matchBy?: unknown; value?: string; source?: string } | null;
  notes?: string[];
  attention?: AiTaskAttention[];
  leftOut?: AiTaskLeftOut[];
  keyColumn: string | null;
  key: { attributeTypeKey?: string; field?: string } | null;
  keyOptions: AiTaskKeyOption[];
  matched: number;
  new: number;
  missing: number;
  namesDiffer: number;
  meaning: AiTaskMeaning[];
  columns: AiTaskColumn[];
  choices: AiTaskChoices;
}

export interface AiTaskSheet {
  sheet: string;
  rows: number;
  as: "notData";
  reason: string;
}

/** A block of a header with no rows below it: a title, not a table. */
export interface AiTaskTitle {
  sheet: string;
  range: string;
  text: string;
}

export interface AiTaskReadingSummary {
  tables: number;
  /** Every sheet of the file. */
  sheets: number;
  updates: number;
  notLoaded: number;
  needDecision: number;
  types: number;
  applications: number;
}

export interface AiTaskReading {
  tables: AiTaskTable[];
  sheets: AiTaskSheet[];
  titles?: AiTaskTitle[];
  /** The stored import profile the reading follows, else null. */
  profile?: AiTaskProfileRef | null;
  summary?: AiTaskReadingSummary;
}

export interface AiTaskRefusal {
  code: string | null;
  rows: number;
  column?: string | null;
  header?: string | null;
  /** The cell values most often refused. */
  values?: { value: unknown; count: number }[] | null;
  message?: string | null;
}

export interface AiTaskCheckTable {
  table: string;
  sheet: string;
  typeName: string | null;
  rows: number;
  changed: number;
  unchanged: number;
  created: number;
  removed: number;
  skipped: number;
  /** The related records (translations, language records) the load writes. */
  translations?: number;
  /** No change and no refusal. */
  nothingToDo?: boolean;
  refused: AiTaskRefusal[];
  leftOut: string[];
}

export interface AiTaskCheckSummary {
  changed: number;
  unchanged: number;
  created: number;
  removed: number;
  /** Rows refused. */
  refused: number;
  translations: number;
  tablesWithChanges: number;
}

export interface AiTaskFix {
  table: string;
  column: string;
  value: string;
  to: string | null;
  reason: string;
  origin?: AiOrigin | null;
}

export interface AiTaskCheck {
  dryRunJobId: string;
  ranAt: string;
  tables: AiTaskCheckTable[];
  summary?: AiTaskCheckSummary;
  fixes: AiTaskFix[];
  rounds: number;
}

/** One model-draft operation the assistant applied (0.16 AP6): its `kind` and the kind's own members. */
export interface AiTaskOperation {
  kind: string;
  [member: string]: unknown;
}

/** A source of the design's import profile: a sheet, the type it loads and its columns' bindings. */
export interface AiTaskDesignSource {
  sheet?: string | null;
  objectTypeKey: string;
  applicationKey?: string | null;
  key?: unknown;
  record?: "upsert" | "existing";
  columns: Record<string, unknown>[];
  [member: string]: unknown;
}

export interface AiTaskDesignProfile {
  sources: AiTaskDesignSource[];
  valueMaps?: Record<string, unknown>;
  [member: string]: unknown;
}

/** A question the assistant asks the steward, with the answer it assumed meanwhile. */
export interface AiTaskQuestion {
  text: string;
  options: string[];
  assumed: string | null;
}

/** The engine's last check of the design (draft errors, profile problems, model operations). */
export interface AiTaskDesignOutcome {
  draftErrors?: unknown[];
  profileProblems?: unknown[];
  modelOperations?: unknown[];
  [member: string]: unknown;
}

/** What the assistant designed for a workbook (0.16 AP6). */
export interface AiTaskDesignCheckItem {
  id: string;
  kind: "reuse" | "grouping" | "translations" | "bothEnds" | "leftOut" | "besideHeld" | "cellsLeftOut";
  text: string;
  /** Needs the person's attention. A `besideHeld` check warns that new records of a type the workspace holds may be an update that did not find its records. */
  open: boolean;
  explanation?: string;
}

/** A value of an example record in "What the load does". */
export interface AiTaskLoadValue {
  attributeTypeKey: string | null;
  value: unknown;
}

export interface AiTaskLoadLink {
  relationTypeKey: string | null;
  direction: "outgoing" | "incoming";
  objectTypeKey: string | null;
  name: string | null;
}

/** One item of a type, with the cells it came from (`ref`, as `Sheet!Q31:S31`). */
export interface AiTaskLoadExample {
  index: number;
  ref: string | null;
  objectTypeKey: string;
  action: "created" | "updated" | "unchanged" | "refused";
  name: string | null;
  id: string | null;
  values: AiTaskLoadValue[];
  links: AiTaskLoadLink[];
  error: { code: string | null; message: string | null } | null;
}

export interface AiTaskLoadType {
  objectTypeKey: string;
  new: number;
  matched: number;
  changed: number;
  removed: number;
  refused: number;
  linkedTo: string[];
  examples: AiTaskLoadExample[];
}

export interface AiTaskLoadFinding {
  kind: "nameTwice";
  objectTypeKey: string;
  name: string;
  count: number;
  /** The parent each record sits under, `null` at the root. */
  parents: ({ id: string; name: string; objectTypeKey: string } | null)[];
}

export interface AiTaskLoadPart {
  sheet: string;
  firstColumn: string;
  lastColumn: string;
  firstRow: number;
  lastRow: number;
  objectTypeKey: string | null;
  relationTypeKey: string | null;
  items: number;
}

/** What the load does (0.13 AB): the engine's summary of the dry run of the assistant's items; accepting loads exactly these. */
export interface AiTaskLoad {
  mode: "items";
  jobId: string;
  draftId: string;
  draftVersion: number;
  workspaceKey: string;
  items: number;
  figures: {
    recordsNew: number;
    recordsMatched: number;
    recordsChanged: number;
    recordsRemoved: number;
    relationshipsNew: number;
    /** How many of `relationshipsNew` are a new record's link to its parent. */
    parentLinksNew?: number;
    relationshipsMatched: number;
    refused: number;
    rowsRead: number;
  };
  types: AiTaskLoadType[];
  relationships: { relationTypeKey: string; new: number; matched: number; refused: number }[];
  sheets: { sheet: string; rows: number }[];
  parts: AiTaskLoadPart[];
  partsTotal: number;
  findings: AiTaskLoadFinding[];
  refused: { index: number; ref: string | null; key: string | null; code: string | null; message: string | null }[];
  refusedByCode: { code: string; items: number }[];
  ranAt: string;
}

export interface AiTaskDesign {
  /** What the load does, from the dry run of the assistant's items; accepting loads exactly these (0.13 AB). */
  load?: AiTaskLoad | null;
  /** Accepting runs the previewed items with no assistant turn (0.13 AB). */
  itemsLoad?: boolean;
  /** "model": the proposed model awaits the person; "load" (and absent): the sheets are mapped and checked. */
  stage?: "model" | "load";
  /** The types the proposal turns into others, with the records each holds. */
  moves?: AiTaskMove[];
  /** What the person's words explicitly ask to remove, with the engine's counts of what it deletes. */
  removals?: AiTaskRemoval[];
  /** The consumer APIs the proposal raises the contractVersion of, with what their consumers read differently. */
  consumerChanges?: AiTaskConsumerChange[];
  /** One plain sentence per proposed type. */
  outline?: { objectTypeKey: string; name?: string; text: string }[];
  checks?: AiTaskDesignCheckItem[];
  /** The person's corrections to the proposal, newest last. */
  corrections?: string[];
  /** The session this design belongs to, when Claude Code works on it. */
  agentSession?: string;
  /** A words task whose model does not change: the proposal has no draft ("No change to the model"). */
  modelUnchanged?: boolean;
  /** While a session works: what it does now and what the engine recorded of it. */
  progress?: {
    now: string;
    seconds: number;
    refused: number | null;
    milestones: { key: string; label: string; done: boolean; running: boolean }[];
  } | null;
  summary: string;
  operations: AiTaskOperation[];
  profile: AiTaskDesignProfile | null;
  questions: AiTaskQuestion[];
  answers: Record<string, string>;
  rounds: number;
  origin: { kind: "ai"; provider: string; model: string; promptVersion: string } | null;
  outcome: AiTaskDesignOutcome | null;
  /** The columns of the sheets it reads that no source loads, with the assistant's reason (null: none given). */
  leftOut?: { sheet: string; column: string; reason: string | null }[];
}

export interface AiTaskDesignCheckSheet {
  /** The source's index in the dry run's profile: the changed records are read by it. */
  source?: number | null;
  sheet: string | null;
  objectTypeKey: string | null;
  /** A sheet the engine added to load the records the structure needs. */
  structure: boolean;
  rows: number;
  created: number;
  updated: number;
  unchanged: number;
  refused: number;
  /** Rows of a source that skips rows without a key that wrote nothing. */
  skipped?: number;
}

export interface AiTaskDesignRefusal {
  sheet: string | null;
  objectTypeKey: string | null;
  code: string;
  rows: number;
  examples: { row: number; message: string; details: unknown }[];
}

/** The check of a designed load (the check of a task without a design is `AiTaskCheck`). */
export interface AiTaskDesignCheck {
  /** `null` for a design of relationships alone: no rows, no dry run. */
  dryRunJobId: string | null;
  ranAt: string;
  rounds: number;
  sheets: AiTaskDesignCheckSheet[];
  refused: AiTaskDesignRefusal[];
  summary: {
    created: number;
    updated: number;
    unchanged: number;
    refused: number;
    skipped?: number;
    relationships?: number;
  };
  /** The draft changed after this dry run, so it does not cover the model as it stands. */
  draftChanged?: boolean;
  /** `items`: the check of the assistant's items (0.13 AB); `design.load` holds the summary. */
  mode?: "items" | null;
}

export interface AiTaskNote {
  kind: "note" | "warning" | "refused";
  text: string;
  at: string;
}

/** One removal the person asked for, in the person's words and the engine's counts. */
export interface AiTaskRemoval {
  kind: "objectType" | "application" | "attribute" | "relationType";
  key: string;
  words: string;
  name: string;
  records: number;
  values: number;
  relationships: number;
  /** "As you asked, the Drug list is deleted, deleting 16 records." */
  text: string;
}

/** What a proposal moves as whole types: the engine's own figures (AP-D47). */
export interface AiTaskMove {
  from: string;
  fromName: string;
  to: string;
  toName: string;
  /** The records the workspace holds of the type that moves. */
  records: number;
  attributes?: { attributeTypeKey: string; from: string | null }[];
  /** The application the records go to, when the type moves to another one. */
  toApplication?: string;
  toApplicationName?: string;
  /** What the migration would drop of this type, counted by the engine over every record. */
  lost?: { records?: number; values?: number; relationships?: number };
}

/** A consumer API whose contractVersion the proposal raises: the engine's account of the change. */
export interface AiTaskConsumerChange {
  api: string;
  name: string;
  from: number;
  to: number;
  changes: string[];
}

/** A task that moved whole types ends in a migration the person confirms, not in a change set (AP-D49). */
export interface AiTaskMigration {
  releaseId: string;
  typeMappings: {
    fromObjectTypeKey: string;
    toObjectTypeKey: string;
    attributes?: { attributeTypeKey: string; from: string | null }[];
    /** The application the type's records go to when the type moves between applications. */
    toApplicationKey?: string;
  }[];
  relationTypeMappings?: MigrationRelationTypeMapping[];
  splits?: MigrationSplit[];
  listConversions?: MigrationListConversion[];
}

export interface AiTaskResult {
  /** Absent when the task ended in a migration (`migration`). */
  changeSetId?: string | null;
  /** The final release of a part-of-a-type reshaping, activated last (AP-D48). */
  thenReleaseId?: string | null;
  /** The release the change set sits on; equal to `thenReleaseId` when the old types stay (two steps). */
  changeSetReleaseId?: string | null;
  migration?: AiTaskMigration | null;
  changeSetName?: string | null;
  importJobId?: string | null;
  profileKey?: string | null;
  counts?: Record<string, number> | null;
  /** The model release the load installed and activated, when the design changed the model. */
  releaseId?: string | null;
  /** Why a session's load left no saved profile (AP-D41), in words a person reads; absent when it did or the load is older. */
  profileNotSaved?: string | null;
  /** The change set was published (0.16 AP13); the task read noticed it. */
  published?: boolean;
  publicationId?: string | null;
}

export interface AiTask {
  id: string;
  workspaceKey: string;
  /** "" for an instruction without a workbook. */
  fileName: string;
  sourceFileId: string | null;
  words: string | null;
  /** A short title the task's session wrote with its first answer; null until then. */
  title?: string | null;
  state: AiTaskState;
  version: number;
  jobId: string | null;
  phase: AiTaskPhase | null;
  createdAt: string;
  updatedAt: string;
  requestedBy: Principal | null;
  reading: AiTaskReading | null;
  check: AiTaskCheck | AiTaskDesignCheck | null;
  /** The task's model draft, when the assistant designs. */
  draftId?: string | null;
  design?: AiTaskDesign | null;
  notes: AiTaskNote[];
  result: AiTaskResult | null;
  /** Whether the person may tell the assistant something now (0.16 AP13): its session goes on or starts again. */
  canTell?: boolean;
  /** While the task's job is queued: the assistant jobs before it (0.13 AQ); `null` once it runs. */
  ahead?: number | null;
}

/** `POST /ai/tasks`'s `request` part. */
export interface AiTaskRequest {
  workspaceKey: string;
  words?: string;
}

export interface AiTaskRunRequest {
  expectedVersion: number;
  changeSetName?: string;
  saveProfile?: { key: string; name: string };
}

/** `POST /ai/tasks/{id}/answers`: the answers by the question's text. */
export interface AiTaskAnswerRequest {
  expectedVersion: number;
  answers: Record<string, string>;
}

export interface AiTaskFieldChange {
  field: string;
  label: string;
  now: unknown;
  after: unknown;
}

/** A record the latest check would change, with the fields that differ. */
export interface AiTaskChange {
  recordId: string;
  name: string | null;
  table: string;
  fields: AiTaskFieldChange[];
}

export interface AiTaskChangePage extends PageNavigation {
  items: AiTaskChange[];
}
