/**
 * Source files, their profiles, a draft's import profile and its dry run (0.10 A3, A5): the
 * contracts of `/source-files`, `/model-drafts/{id}/profile` and `/model-drafts/{id}/dry-run`
 * (API.md, "Source files and their profiles", "The dry-run summary", "A draft's import profile").
 */

import type { DraftOperation, ModelDiagnostic } from "@/types/modelAdmin";

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

/** A note under a list's header (0.10 A8a, D119) and what it says of the list. */
export interface SourceBlockNote {
  row: number;
  text: string;
  meaning: "many" | "one" | "free" | "heading";
}

export interface SourceBlock {
  index: number;
  range: string;
  firstColumn: string;
  lastColumn: string;
  headerRow: number | null;
  lastRow: number;
  rows: number;
  /** The titles above a list of a sheet laid out for reading, the outermost first (0.10 A8a). */
  titles?: string[];
  note?: SourceBlockNote | null;
}

export interface SourceSheet {
  index: number;
  name: string;
  rows: number;
  headerRow: number | null;
  /** Laid out for reading: read list by list (0.10 A8a, D115). */
  laidOut?: boolean;
  blocks: SourceBlock[];
}

/** Another column, or a field of a type's records in a workspace, holding the column's values (D69). */
export interface SourceOverlap {
  values: number;
  share: number;
  sheet?: string | null;
  column?: string | null;
  /** The other column's block, on a sheet laid out for reading (0.10 A8a). */
  block?: number | null;
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

/** A staged cell: its text as an import matches it and its value type (0.10 A8b, D124). */
export interface SourceCell {
  text: string;
  kind: string;
}

/** A row of a range of a sheet holding a cell, its cells by column letter. */
export interface SourceCellRow {
  row: number;
  cells: Record<string, SourceCell>;
}

/** A rectangle of a sheet as a source takes it: its header row and block. */
export interface SourceRectangle {
  headerRow: number;
  block: { firstColumn: string; lastColumn: string; lastRow: number };
}

/** `POST /model-drafts/{id}/inference/list` (0.10 A8b, D128): a rectangle read as a list, not stored. */
export interface ListProposal {
  pattern: string;
  sheet: string | null;
  columns: string[];
  summary: string;
  evidence: Record<string, unknown>;
  operations: DraftOperation[];
  alternatives: { label: string; operations: DraftOperation[] }[];
}

/** A table of the draft's file and, optionally, one of its columns, by header or sheet letter (0.17 PL3b). */
export interface JoinColumnRef {
  sheet: string;
  headerRow?: number;
  block?: { firstColumn: string; lastColumn: string; lastRow?: number };
  column?: string;
  letter?: string;
}

/** `POST /model-drafts/{id}/join-candidates` (PP-D8): `column` compared with `against`, over every row. */
export interface JoinCandidatesRequest {
  column: JoinColumnRef;
  against: JoinColumnRef;
}

/** A column of the compared table with its figures over every row. */
export interface JoinCandidate {
  sheet: string;
  letter: string;
  header: string | null;
  rows: number;
  distinct: number;
  /** The dropped column's different values the column holds. */
  matchedValues: number;
  /** The dropped column's rows whose value the column holds. */
  matchedRows: number;
  /** `matchedRows` over the dropped column's rows, 0 to 1. */
  share: number;
  /** Every filled cell differs: it reads as a list to link to. */
  unique: boolean;
}

/** The answer: candidates best first. On a `tie`, `best` is null and the client asks which of `tied`. */
export interface JoinCandidates {
  column: { sheet: string; letter: string; header: string | null; rows: number; distinct: number };
  candidates: JoinCandidate[];
  best: string | null;
  tie: boolean;
  tied: string[];
}

/** Where a card sits on the canvas board. */
export interface CanvasPosition {
  x: number;
  y: number;
}

/** What the board shows (0.17 CE1, PP-D81): every list, only what the draft changed, or the workbook's. */
export type CanvasScope = "model" | "changed" | "workbook";

/**
 * `GET`/`PATCH /model-drafts/{id}/canvas`: card key to position, the folded cards' keys and the chosen
 * scope (`null`: the default); not part of the draft's version or history.
 */
export interface Canvas {
  positions: Record<string, CanvasPosition>;
  /** Always sent by the server; optional here for a caller that builds one. */
  folded?: string[];
  scope?: CanvasScope | null;
}

/** The body of `PATCH /model-drafts/{id}/canvas`: any of the parts, at least one. */
export interface CanvasUpdate {
  positions?: Record<string, CanvasPosition | null>;
  /** `true` folds a card, `false` or `null` unfolds it; merged by key. */
  folded?: Record<string, boolean | null>;
  /** Replaces the chosen scope; `null` is the default. */
  scope?: CanvasScope | null;
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
  /** A unique attribute, an ID column, or the record's name (`field: "name"`, 0.10 A8a, D117). */
  key?: { attributeTypeKey?: string; column?: string; field?: "name" } | null;
  record?: "existing" | null;
  /** What a load does with the records no row names: report them (absent) or delete them in a change set (0.17 CE1, PP-D82). */
  missing?: "report" | "delete" | null;
  /** Every row's parent: the record found for `value` (0.10 A8c, D141). */
  parent?: {
    objectTypeKey: string;
    matchBy: { field?: string; attributeTypeKey?: string };
    value: string;
    missing?: "create" | "refuse";
  } | null;
  columns: ProfileBinding[];
  /** Rows holding only a heading are the parent of the rows beneath them (0.17 PL3b, PP-D7). */
  headings?: HeadingRows | null;
  /** Columns repeated by blanks: an empty cell takes the filled cell above it (PP-D7). */
  fillDown?: string[] | null;
  /** A wide table read as rows (PP-D6). */
  unpivot?: Unpivot | null;
}

/** A wide table read as rows: each filled cell of `columns` is a row, its header in `nameColumn`, its cell in `valueColumn`. */
export interface Unpivot {
  columns: string[];
  nameColumn: string;
  valueColumn: string;
}

/** A row holding only `column` is a heading; its text fills the new column `into` on the rows beneath it. */
export interface HeadingRows {
  column: string;
  into: string;
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
  /** A key no stored profile holds, offered when the profile's key belongs to another model. */
  freeKey?: string | null;
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
  /** Rows without a key the source skips (rowsWithoutKey: skip, 0.10 A7, D110). */
  skippedRows?: number;
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
