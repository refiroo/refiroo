/** Loading a workbook with the AI assistant (0.16 AP6a): the task, its reading, plan, check and result. */

import type { AiOrigin } from "@/types/ai";
import type { PageNavigation } from "@/types/runtime";
import type { Principal } from "@/types/security";

export type AiTaskState = "reading" | "read" | "checking" | "checked" | "loading" | "loaded" | "failed" | "cancelled";
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

export interface AiTaskPlan {
  profile: Record<string, unknown>;
  steps: {
    kind: "profileSource" | "valueMap" | "destination";
    owner: AiTaskOwner;
    reason: string;
    origin?: AiOrigin | null;
    params: Record<string, unknown>;
  }[];
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

/** A record the structure needs, created in the same change set as the load. */
export interface AiTaskDesignRecord {
  ref: string;
  objectTypeKey: string;
  applicationKey: string | null;
  name: string;
  attributes: Record<string, unknown>;
  parent: { objectTypeKey: string; name: string } | null;
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
  links?: AiTaskLinkCheck[];
  [member: string]: unknown;
}

/** One criterion of a link rule's query: a field test, or a hop over a relationship (`not` negates either). */
export interface AiTaskCriterion {
  field?: string;
  op?: string;
  value?: unknown;
  related?: { relationTypeKey: string; direction?: "outgoing" | "incoming"; where?: AiTaskCriterion[] };
  not?: boolean;
}

/** Relationships between stored records where a condition holds (AP-D17/D18). */
export interface AiTaskLinkRule {
  relationTypeKey: string;
  from: { objectTypeKey: string; where?: AiTaskCriterion[] };
  to: { objectTypeKey: string; where?: AiTaskCriterion[] };
  reason?: string;
}

/** The engine's check of one link rule: the records each end finds and the pairs, or why it is refused. */
export interface AiTaskLinkCheck {
  rule: AiTaskLinkRule;
  from?: number;
  to?: number;
  pairs?: number;
  refused?: string;
}

/** What the assistant designed for a workbook (0.16 AP6). */
export interface AiTaskDesignCheckItem {
  id: string;
  kind: "reuse" | "grouping" | "translations" | "bothEnds";
  text: string;
  /** Needs the person's attention. */
  open: boolean;
  explanation?: string;
}

export interface AiTaskDesign {
  /** "model": the proposed model awaits the person; "load" (and absent): the sheets are mapped and checked. */
  stage?: "model" | "load";
  /** One plain sentence per proposed type. */
  outline?: { objectTypeKey: string; text: string }[];
  checks?: AiTaskDesignCheckItem[];
  /** The person's corrections to the proposal, newest last. */
  corrections?: string[];
  /** The session this design belongs to, when Claude Code works on it. */
  agentSession?: string;
  /** While a session works: what it does now and what the engine recorded of it. */
  progress?: {
    now: string;
    seconds: number;
    refused: number | null;
    milestones: { key: string; label: string; done: boolean; running: boolean }[];
  } | null;
  summary: string;
  operations: AiTaskOperation[];
  records: AiTaskDesignRecord[];
  profile: AiTaskDesignProfile | null;
  /** Relationships between stored records where a condition holds. */
  links?: AiTaskLinkRule[];
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
  links?: AiTaskLinkCheck[];
  summary: { created: number; updated: number; unchanged: number; refused: number; relationships?: number };
}

export interface AiTaskNote {
  kind: "note" | "warning" | "refused";
  text: string;
  at: string;
}

export interface AiTaskResult {
  changeSetId: string;
  changeSetName?: string | null;
  importJobId?: string | null;
  profileKey?: string | null;
  counts?: Record<string, number> | null;
  /** The model release the load installed and activated, when the design changed the model. */
  releaseId?: string | null;
  /** The background batch that writes the design's relationships after the import. */
  linksJobId?: string | null;
}

export interface AiTask {
  id: string;
  workspaceKey: string;
  /** "" for an instruction without a workbook. */
  fileName: string;
  sourceFileId: string | null;
  words: string | null;
  state: AiTaskState;
  version: number;
  jobId: string | null;
  phase: AiTaskPhase | null;
  createdAt: string;
  updatedAt: string;
  requestedBy: Principal | null;
  reading: AiTaskReading | null;
  plan: AiTaskPlan | null;
  check: AiTaskCheck | AiTaskDesignCheck | null;
  /** The task's model draft, when the assistant designs. */
  draftId?: string | null;
  design?: AiTaskDesign | null;
  notes: AiTaskNote[];
  result: AiTaskResult | null;
}

/** `POST /ai/tasks`'s `request` part. */
export interface AiTaskRequest {
  workspaceKey: string;
  words?: string;
}

/** The person's choices for one table in a plan: only what they changed. */
export interface AiTaskTableChoices {
  table: string;
  keyColumn?: string;
  newRecords?: "create" | "leaveOut";
  names?: "file" | "stored";
  missing?: "leave" | "remove";
  load?: boolean;
}

export interface AiTaskPlanRequest {
  expectedVersion: number;
  tables: AiTaskTableChoices[];
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
