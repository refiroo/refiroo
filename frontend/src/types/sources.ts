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

/** One column binding of a source, in the import profile's vocabulary (API.md, import profiles). */
export interface ProfileBinding {
  column?: string;
  columns?: string[];
  field?: "name";
  attributeTypeKey?: string;
  parent?: ProfileRelation;
  relation?: ProfileRelation;
  relationFlags?: ProfileRelation;
  relatedRecord?: Record<string, unknown>;
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
  records: { created: number; updated: number; unchanged: number };
  values: number;
  relationships: number;
  relatedRecords: number;
  rejections: { code: string; rows: number }[];
}

export interface DryRunDifference {
  source: number | null;
  objectTypeKey: string;
  sheet: string | null;
  figures: Record<string, { now: number; was: number }>;
}

/** A draft's latest dry run (D67, D79). */
export interface DryRun {
  jobId: string;
  state: "checking" | "completed" | "failed" | "cancelled" | "expired";
  draftId: string;
  draftVersion: number;
  sourceFileId: string;
  workspaceKey: string;
  summary: {
    coverage: "complete";
    rows: { total: number; run: number };
    sources: DryRunSource[];
    difference: DryRunDifference[] | null;
    previousJobId: string | null;
    ranAt: string;
  } | null;
  error: { code: string; message: string } | null;
}
