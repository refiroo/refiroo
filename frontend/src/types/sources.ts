/**
 * Source files, their profiles, a draft's import profile and its dry run (0.10 A3, A5): the
 * contracts of `/source-files`, `/model-drafts/{id}/profile` and `/model-drafts/{id}/dry-run`
 * (API.md, "Source files and their profiles", "The dry-run summary", "A draft's import profile").
 */

import type { ModelDiagnostic } from "@/types/modelAdmin";

/** Where a file's profile stands: `completed` once stored, otherwise its job's state. */
export interface SourceFileProfileState {
  state: "queued" | "running" | "completed" | "failed" | "cancelled" | "expired";
  jobId: string | null;
  error?: { code: string; message: string } | null;
}

/** A workbook or CSV file a draft or a stored import profile owns (D5). */
export interface SourceFile {
  id: string;
  name: string;
  format: "xlsx" | "csv";
  bytes: number;
  owner: { draftId: string | null; profileKey: string | null };
  workspaceKey: string | null;
  uploadedAt: string;
  supersededAt: string | null;
  version: number;
  profile: SourceFileProfileState;
}

export interface SourceFileUpload {
  owner: { draftId: string } | { profileKey: string };
  workspaceKey?: string;
}

export interface SourceBlock {
  index: number;
  range: string;
  firstColumn: string;
  lastColumn: string;
  headerRow: number | null;
  lastRow: number;
  rows: number;
}

export interface SourceSheet {
  index: number;
  name: string;
  rows: number;
  headerRow: number | null;
  blocks: SourceBlock[];
}

/** Another column, or a field of a type's records in a workspace, holding the column's values (D69). */
export interface SourceOverlap {
  values: number;
  share: number;
  sheet?: string | null;
  column?: string | null;
  header?: string | null;
  workspaceKey?: string | null;
  objectTypeKey?: string | null;
  field?: string | null;
  attributeTypeKey?: string | null;
}

/** A column's statistics over the rows below its block's header (D68–D70). */
export interface SourceColumn {
  sheet: string;
  letter: string;
  header: string | null;
  block: number;
  rows: number;
  filled: number;
  distinct: number;
  valueTypes: Record<string, number>;
  candidateKey: boolean;
  delimiters: { character: string; cells: number; share: number }[];
  placeholders: { value: string; count: number }[];
  /** The most frequent values with their counts (0.10 A6); absent on a file profiled before. */
  values?: { value: string; count: number }[];
  overlaps: SourceOverlap[];
}

export interface SourcePage<T> {
  items: T[];
  nextCursor: string | null;
}

/** How a column binding reaches another record: its relation, the type at its far end, the match. */
export interface ProfileRelation {
  relationTypeKey?: string;
  objectTypeKey?: string;
  direction?: "outgoing" | "incoming";
  matchBy?: { field?: string; attributeTypeKey?: string };
  split?: string;
  missing?: "create";
  targets?: Record<string, string>;
}

/**
 * A record related to the row's record under a parent record (a translation under its language),
 * whose name or one attribute the column fills (D70; the parent created by name, 0.10 A6, D93).
 */
export interface ProfileRelatedRecord {
  relationTypeKey?: string;
  direction?: "outgoing" | "incoming";
  applicationKey?: string;
  objectTypeKey?: string;
  parent?: {
    objectTypeKey?: string;
    matchBy?: { field?: string; attributeTypeKey?: string };
    value?: string;
    column?: string;
    missing?: "create";
  };
  field?: "name";
  attributeTypeKey?: string;
  matchBy?: { attributeTypeKey?: string };
}

/** One column binding of a source, in the import profile's vocabulary (API.md, import profiles). */
export interface ProfileBinding {
  column?: string;
  columns?: string[];
  field?: "name";
  attributeTypeKey?: string;
  parent?: ProfileRelation;
  relation?: ProfileRelation;
  relationFlags?: ProfileRelation;
  relatedRecord?: ProfileRelatedRecord;
  ignore?: boolean;
  valueMap?: string | null;
}

export interface ProfileSource {
  id: string;
  sheet: string;
  headerRow: number;
  block?: Record<string, unknown> | null;
  applicationKey: string | null;
  objectTypeKey: string;
  key?: { attributeTypeKey?: string; column?: string } | null;
  record?: "existing" | null;
  columns: ProfileBinding[];
}

/** A binding a model step took away (D78). */
export interface ProfileUnmapped {
  id: string;
  sheet: string;
  source: string;
  column?: string;
  columns?: string[];
  because?: { kind?: string };
}

/** The draft's import profile as the draft holds it (D75). */
export interface DraftProfileDocument {
  key: string;
  name: string;
  sources: ProfileSource[];
  valueMaps: Record<string, Record<string, string | number | boolean | null>>;
  ignoredSheets?: string[];
  unmapped?: ProfileUnmapped[];
}

/** `GET /model-drafts/{id}/profile`. */
export interface DraftProfile {
  version: number;
  profile: DraftProfileDocument | null;
  definition: Record<string, unknown> | null;
  valid: boolean;
  diagnostics: ModelDiagnostic[];
  sourceFile: { id: string; name: string; profile: SourceFileProfileState["state"] } | null;
}

export interface DryRunSource {
  source: number;
  profileSource: number;
  sheet: string | null;
  objectTypeKey: string;
  rows: number;
  records: { created: number; updated: number; unchanged: number; deleted?: number };
  values: number;
  relationships: number;
  relatedRecords: number;
  /** Records of the type no row names (0.10 A5c, D82). */
  missingRecords?: number;
  rejections: { code: string; rows: number }[];
}

export interface DryRunDifference {
  source: number | null;
  objectTypeKey: string;
  sheet: string | null;
  figures: Record<string, { now: number; was: number }>;
}

/** The figures of a run through a profile: a draft's dry run, or a profile's check. */
export interface DryRunSummary {
  coverage: "complete";
  rows: { total: number; run: number };
  sources: DryRunSource[];
  difference: DryRunDifference[] | null;
  previousJobId: string | null;
  ranAt: string;
}

/** A draft's latest dry run (D67, D79). */
export interface DryRun {
  jobId: string;
  state: "checking" | "completed" | "failed" | "cancelled" | "expired";
  draftId: string;
  draftVersion: number;
  sourceFileId: string;
  workspaceKey: string;
  summary: DryRunSummary | null;
  error: { code: string; message: string } | null;
}

/** One source of a profile as its check found the next file (0.10 A5c, D83). */
export interface CheckSource {
  profileSource: number;
  /** Its position in the check's load order, as the lists and rows take it; null when not read. */
  source: number | null;
  sheet: string | null;
  objectTypeKey: string;
  missing: "report" | "delete";
  sheetFound: boolean;
  columns: {
    new: { column: string; letter: string }[];
    missing: { column: string }[];
    renamed: { from: string; to: string; letter: string; shared: number }[];
  } | null;
  newValues: number;
  drift: number;
  missingRecords: number;
}

/** `GET /import-profiles/{key}/check`: the check of the profile's latest file. */
export interface ProfileCheck {
  jobId: string;
  state: "checking" | "completed" | "failed" | "cancelled" | "expired";
  profileKey: string;
  profileVersion: number | null;
  sourceFileId: string;
  previousSourceFileId: string | null;
  workspaceKey: string;
  releaseId: string | null;
  valid: boolean | null;
  problems: { path: string; code: string; message: string }[];
  sources: CheckSource[];
  dryRun: DryRunSummary | null;
  error: { code: string; message: string } | null;
}

/** A value of a match column naming no record: created by the load, or refused. */
export interface CheckNewValue {
  source: number;
  column: string;
  value: unknown;
  created: boolean;
  cells: number;
}

/** A row whose key finds a record named otherwise. */
export interface CheckDrift {
  source: number;
  row: number;
  recordId: string;
  key: unknown;
  name: string;
  recordName: string | null;
}

/** A record of a source's type no row of the file names (D82). */
export interface CheckMissingRecord {
  source: number;
  recordId: string;
  name: string;
  key: unknown;
}

/** What an inference proposes from (0.10 A6, D87): a new application, or additions to the model. */
export interface InferenceRequest {
  mode: "newApplication" | "extend";
  applicationKey?: string;
  applicationName?: string;
}

/** A column the draft reads otherwise than a pattern does (D92). */
export interface InferenceDisagreement {
  proposalId: string;
  pattern: string;
  sheet: string | null;
  column: string;
  source: string;
  binding: string;
  proposed: string;
  found: string;
  step: number | null;
}

/** `GET /model-drafts/{id}/inference`: the draft's latest inference. */
export interface Inference {
  jobId: string;
  state: "checking" | "completed" | "failed" | "cancelled" | "expired";
  mode: InferenceRequest["mode"];
  draftVersion: number;
  sourceFileId: string;
  counts: { open: number; applied: number; held: number; rejected: number };
  disagreements: InferenceDisagreement[];
  warnings: string[];
  /** The elements still as a proposal step left them: the engine's, until changed (D92). */
  proposed: { element: string; proposalId: string | null; pattern: string | null }[];
  error: { code: string; message: string } | null;
}

/** A proposal of the latest inference (D89, D90). */
export interface Proposal {
  id: string;
  position: number;
  pattern: string;
  sheet: string | null;
  columns: string[];
  summary: string;
  evidence: Record<string, unknown>;
  operations: { kind: string; [name: string]: unknown }[];
  alternatives: { label: string; operations: { kind: string; [name: string]: unknown }[] }[];
  requires: string[];
  status: "open" | "applied" | "held" | "rejected";
}
