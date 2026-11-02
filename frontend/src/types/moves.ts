/**
 * Model mappings and moves (0.11 X1–X3), as the move editor reads them (0.11 X4): a mapping between
 * two models with its problems and coverage, its steps, the inference's proposals, and a move's dry
 * run with its summary and rows.
 */

import type { ExportCriterion } from "@/types/integration";
import type { Principal } from "@/types/security";

export interface MappingAttributeEntry {
  source: string;
  target?: string;
  valueMap?: string;
  ignore?: boolean;
}

export interface MappingRelationEntry {
  source: string;
  target: string;
  direction: "outgoing" | "incoming";
  attributes?: { source: string; target: string }[];
  missing?: "create" | "refuse";
}

/** Where a source type's records stand in the target: under the moved parent, or under one record. */
export type MappingParent =
  | { from: "source"; relationTypeKey?: string; missing?: "create" | "refuse" }
  | { objectTypeKey: string; value: string; relationTypeKey?: string; missing?: "create" | "refuse" };

export type MappingMatch = { attributeTypeKey: string } | { field: "name" };

export interface MappingTypeEntry {
  source: string;
  target: string;
  attributes: MappingAttributeEntry[];
  relations: MappingRelationEntry[];
  defaults: Record<string, unknown>;
  parent?: MappingParent | null;
  match?: MappingMatch | null;
}

export interface MappingProblem {
  code: "ELEMENT_NOT_IN_RELEASE" | "BINDING_NOT_ALLOWED" | "VALUE_TYPES_NOT_CONVERTIBLE" | "ATTRIBUTE_FILLED_TWICE";
  pointer: string;
  side: "source" | "target";
  message: string;
}

export interface MappingCoverage {
  types: string[];
  attributes: Record<string, string>[];
  relations: Record<string, string>[];
  required: Record<string, string>[];
  requiredRelations: Record<string, string>[];
  parents: Record<string, unknown>[];
}

export interface ModelMappingSummary {
  key: string;
  name: string;
  sourceModelKey: string;
  targetModelKey: string;
  sourceReleaseId: string;
  targetReleaseId: string;
  version: number;
  updatedAt: string;
}

export interface ModelMapping extends ModelMappingSummary {
  types: MappingTypeEntry[];
  valueMaps: Record<string, Record<string, unknown>>;
  problems: MappingProblem[];
  coverage: MappingCoverage;
  createdAt: string;
}

export interface ModelMappingPage {
  items: ModelMappingSummary[];
  nextCursor: string | null;
}

/** One mapping operation (D107), by its `kind` and parameters. */
export type MappingOperation = { kind: string } & Record<string, unknown>;

/** One operation in a mapping's history (D105). */
export interface ModelMappingOperationEntry {
  sequence: number;
  step: number;
  kind: string;
  parameters: Record<string, unknown>;
  mappingVersion: number;
  author: Principal | null;
  at: string;
  undone: boolean;
  origin: { type: string } & Record<string, unknown>;
}

export interface ModelMappingStep {
  version: number;
  entries: { sequence: number; step: number; kind: string; mappingVersion: number }[];
  problems: MappingProblem[];
}

export interface MappingInference {
  jobId: string;
  state: "checking" | "completed" | "failed" | "cancelled" | "expired";
  mappingVersion: number;
  sourceWorkspaceKey: string;
  targetWorkspaceKey: string;
  counts: { open: number; applied: number; held: number; rejected: number };
  warnings: string[];
  error: { code: string; message: string } | null;
}

export interface MappingProposal {
  id: string;
  position: number;
  kind: "type" | "relation";
  sourceType: string;
  relation: string | null;
  target: string;
  score: number;
  summary: string;
  evidence: Record<string, unknown>[];
  operations: MappingOperation[];
  alternatives: { target: string; score: number; label: string; operations: MappingOperation[] }[];
  requires: string[];
  status: "open" | "applied" | "held" | "rejected";
}

/** What moves (I7, D116): every given part selects; nothing given, the whole workspace. */
export interface MoveSelection {
  types?: { objectTypeKey: string; where: ExportCriterion[] }[];
  parentObjectId?: string;
  objectIds?: string[];
}

export interface MoveRequest {
  sourceWorkspaceKey: string;
  targetWorkspaceKey: string;
  mapping: { key: string; expectedVersion: number };
  selection: MoveSelection;
  mode: "copy" | "move";
  stage?: "preview" | "execute";
}

export interface MoveCounts {
  create: number;
  update: number;
  updateOriginal: number;
  refused: number;
  notMoved: number;
}

export type MoveOutcome = keyof MoveCounts;

/** A move's dry run summary (D122), with what its load opened (X3). */
export interface MoveSummary {
  coverage: "complete";
  rows: number;
  counts: MoveCounts;
  types: { sourceType: string; targetType?: string; counts: MoveCounts }[];
  relationships: { relationTypeKey: string; targetRelationTypeKey?: string; counts: MoveCounts }[];
  reasons: { code: string; count: number }[];
  attributesNotCarried: { sourceType: string; attributeTypeKey: string; code: string; count: number }[];
  possibleDuplicates: number;
  mapping: { key: string; version: number };
  sourceWorkspaceKey: string;
  targetWorkspaceKey: string;
  /** The releases the two workspaces ran when the move read them. */
  sourceReleaseId?: string;
  targetReleaseId?: string;
  mode: "copy" | "move";
  targetChangeSetId: string | null;
  sourceChangeSetId: string | null;
  source?: { deleted: number; kept: number };
}

export interface MoveReason {
  code: string;
  message: string;
  action?: string;
  details?: Record<string, unknown>;
}

export interface MoveRow {
  index: number;
  kind: "record" | "relationship";
  outcome: MoveOutcome;
  reasons: MoveReason[];
  leftBehind: { code: string; attributeTypeKey: string; pointer: string; value?: unknown }[];
  sourceType?: string;
  sourceId?: string;
  name?: string;
  selected?: boolean;
  targetId?: string;
  targetType?: string;
  foundBy?: "origin" | "counterpart" | "match";
  relationTypeKey?: string;
  targetRelationTypeKey?: string;
  /** The end of the relationship the record that holds it stands at. */
  direction?: "outgoing" | "incoming";
  fromId?: string;
  toId?: string;
  /** A relationship's records by their names as they are now (0.11 X4). */
  fromName?: string;
  toName?: string;
}

export interface MoveRowPage {
  items: MoveRow[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
}
