/**
 * Runtime data contracts: stored objects and relations, their pages, audit history and workspace
 * runtime state.
 */

import type { ValueType } from "@/types/model";

/**
 * Navigation every collection page returns (ADR-030). The cursor fields other than `nextCursor`
 * and the counts, present only with `includeTotal=true` and otherwise omitted, are optional here so
 * that feeds reading forward only need not model them.
 */
export interface PageNavigation {
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
}

export interface ObjectItem {
  id: string;
  workspaceKey: string;
  applicationKey: string;
  objectTypeKey: string;
  parentObjectId: string | null;
  name: string;
  path: Array<{ id: string; name: string; objectTypeKey: string }>;
  attributes: ObjectAttributeValue[];
  version: number;
  /** Null in change sets and history, which do not record timestamps. */
  createdAt: string | null;
  updatedAt: string | null;
}

export interface Workspace {
  key: string;
  label: string;
  status: "active" | "retired";
  version: number;
  createdAt: string;
  updatedAt: string;
}

/** One workspace as a single-item read returns it; the paged list omits the deletion fields. */
export interface WorkspaceDetail extends Workspace {
  /** True when nothing refers to the workspace, so it may be deleted rather than retired. */
  deletable: boolean;
  /** Why the workspace cannot be deleted, when `deletable` is false. */
  deleteBlockedBy?: "default" | "published" | "notEmpty" | null;
}

export interface WorkspacePage {
  items: Workspace[];
  nextCursor: string | null;
}

export interface WorkspaceRuntimeState {
  defaultWorkspaceKey: string;
  version: number;
  updatedAt: string;
}

export interface ObjectAttributeInput {
  attributeTypeKey: string;
  value: unknown;
}

export interface ObjectDeletionImpact {
  objectsToDelete: Array<{ id: string; name: string; objectTypeKey: string }>;
  relationshipsToRemove: Array<{ id: string; relationTypeKey: string }>;
  objectCount: number;
  relationshipCount: number;
  retainedAssociationCount: number;
  deletionPreviewToken: string;
}

export interface InitialRelationInput {
  relationTypeKey: string;
  direction: "outgoing" | "incoming";
  otherObjectId: string;
  attributes: Record<string, unknown>;
}

export interface ObjectAttributeValue extends ObjectAttributeInput {
  id: string;
  name: string;
  valueType: ValueType;
}

export interface RelationRecord {
  id: string;
  relationTypeKey: string;
  fromObjectId: string;
  toObjectId: string;
  attributes: Record<string, unknown>;
  version: number;
  /** Null in change sets and history, which do not record timestamps. */
  createdAt?: string | null;
  updatedAt?: string | null;
  /** The claimed set's new version, on a create that claimed one. */
  relationSetVersion?: number | null;
}

export interface RelationItem {
  direction: "outgoing" | "incoming";
  relation: RelationRecord;
  object: ObjectItem;
}

export interface RelationPage extends PageNavigation {
  items: RelationItem[];
}

export interface AttributeValueResponse extends ObjectAttributeValue {
  objectVersion: number;
}

export interface RelationCreateInput {
  relationTypeKey: string;
  fromObjectId: string;
  toObjectId: string;
  attributes: Record<string, unknown>;
  /** With `relationSetDirection`: the write succeeds only while that end's set is at this version. */
  expectedRelationSetVersion?: number;
  relationSetDirection?: "outgoing" | "incoming";
}

/** A claim on one end's relation set (ADR-022), which a conditional single write names. */
export interface RelationSetClaim {
  expectedRelationSetVersion: number;
  relationSetDirection: "outgoing" | "incoming";
}

export interface RelationUpdateInput {
  attributes: Record<string, unknown>;
  expectedVersion: number;
}

export interface ObjectPage extends PageNavigation {
  items: ObjectItem[];
}

/**
 * A record a record could move under (Base 0.8 B2). An ineligible one stays listed, so pages and
 * totals remain truthful (D14), with why the move would refuse it or change nothing.
 */
export interface ParentCandidate {
  id: string;
  objectTypeKey: string;
  name: string;
  /** Root first, ending with the candidate itself. */
  path: Array<{ id: string; name: string; objectTypeKey: string }>;
  eligible: boolean;
  reason: "self" | "descendant" | "currentParent" | null;
}

export interface ParentCandidatePage extends PageNavigation {
  items: ParentCandidate[];
}

export interface AuditEventItem {
  id: string;
  aggregateType: string;
  aggregateId: string;
  action: string;
  version: number;
  changedFields: string[];
  attributeTypeKeys: string[];
  occurredAt: string;
}

export interface AuditEventPage {
  items: AuditEventItem[];
  nextCursor: string | null;
}

export interface ChangeSet {
  id: string;
  workspaceKey: string;
  name: string | null;
  modelReleaseId: string;
  modelReleaseKey: string;
  modelReleaseVersion: string;
  source: "currentLive" | "publication" | "empty";
  derivedFromPublicationId: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface ChangeSetPage {
  items: ChangeSet[];
  nextCursor: string | null;
}

export interface Publication {
  id: string;
  workspaceKey: string;
  modelReleaseId: string;
  modelReleaseKey: string;
  modelReleaseVersion: string;
  publicationNumber: number;
  status: "active" | "withdrawn";
  derivedFromPublicationId: string | null;
  supersedesPublicationId: string | null;
  createdAt: string;
  publishedAt: string;
  withdrawnAt: string | null;
}

export interface PublicationPage {
  items: Publication[];
  nextCursor: string | null;
}

export interface ChangeSetValidation {
  valid: boolean;
  diagnostics: Array<Record<string, unknown>>;
}

export interface MappingObjectSummary {
  id: string;
  objectTypeKey: string;
  name: string;
  fields: Record<string, unknown>;
}

export interface MappingTargetSummary {
  relationId: string;
  attributes: Record<string, unknown>;
  object: MappingObjectSummary;
}

export interface MappingCoverageRow {
  source: MappingObjectSummary;
  state: "mapped" | "unmapped" | "ambiguous";
  mappingVersion: number;
  targetCount: number;
  targets: MappingTargetSummary[];
  targetsNextCursor: string | null;
}

export interface MappingCoveragePage extends PageNavigation {
  items: MappingCoverageRow[];
}

export interface MappingTargetPage {
  mappingVersion: number;
  targetCount: number;
  items: MappingTargetSummary[];
  nextCursor: string | null;
}

export interface MappingCandidatePage extends PageNavigation {
  items: MappingObjectSummary[];
}

export interface MappingReplacementRequest {
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  direction: "outgoing" | "incoming";
  sourceObjectId: string;
  targetObjectId: string | null;
  expectedMappingVersion: number;
  attributes?: Record<string, unknown>;
  changeSetId?: string;
  expectedChangeSetVersion?: number;
}

export type RelationMatrixCellState = "one" | "several" | "inactive" | "historyOnly" | "none";

export interface RelationMatrixCellRecord {
  id: string;
  name: string;
  version: number;
  relationId: string;
  relationVersion: number;
  /** Whether it meets the binding's condition; always true without one. */
  meetsCondition: boolean;
  /** The view's `cellFields`. */
  fields: Record<string, unknown>;
}

export interface RelationMatrixCell {
  columnId: string;
  state: RelationMatrixCellState;
  conflict: boolean;
  recordCount: number;
  matchingCount: number;
  /** At most five, those meeting the condition first. */
  records: RelationMatrixCellRecord[];
  /** The publication a `historyOnly` cell's records come from. */
  publication?: { id: string; number: number } | null;
}

export interface RelationMatrixRow {
  row: MappingObjectSummary;
  /** The row's version of the view's relation set, which a link or unlink from the row claims. */
  relationSetVersion: number;
  cells: RelationMatrixCell[];
}

export interface RelationMatrixColumn {
  id: string;
  name: string;
  /** The column record's `columnLabelField` value. */
  label: unknown;
}

export interface RelationMatrixPage extends PageNavigation {
  items: RelationMatrixRow[];
  columns: RelationMatrixColumn[];
  columnsNextCursor?: string | null;
  columnsPrevCursor?: string | null;
}

export interface RelationMatrixPathPart {
  id: string;
  name: string;
  objectTypeKey: string;
}

export interface RelationMatrixContainer {
  id: string;
  objectTypeKey: string;
  name: string;
  /** From below the column record down to this record; empty for the column record itself. */
  path: RelationMatrixPathPart[];
}

export interface RelationMatrixContainerPage extends PageNavigation {
  items: RelationMatrixContainer[];
  defaultContainerId: string | null;
}

export interface RelationMatrixLinkCandidate {
  id: string;
  objectTypeKey: string;
  name: string;
  version: number;
  path: RelationMatrixPathPart[];
  fields: Record<string, unknown>;
  eligible: boolean;
  reason: "alreadyLinked" | "rowCardinality" | "candidateCardinality" | "scopeTaken" | null;
}

export interface RelationMatrixLinkCandidatePage extends PageNavigation {
  items: RelationMatrixLinkCandidate[];
  relationSetVersion: number;
}

export interface MappingReplacementResponse {
  sourceObjectId: string;
  mappingVersion: number;
  state: "mapped" | "unmapped";
  relationId: string | null;
  changeSetVersion: number | null;
}

/** What a change set does to a record or relation against its source (Base 0.8 P2a, D31). */
export type ChangeKind = "added" | "changed" | "removed";

export interface ObjectChangeState {
  name: string;
  parentObjectId: string | null;
  attributes: ObjectAttributeValue[];
  version: number;
}

export interface ObjectPathPart {
  id: string;
  name: string;
  objectTypeKey: string;
}

export interface ObjectChange {
  kind: ChangeKind;
  objectId: string;
  objectTypeKey: string;
  applicationKey: string;
  /** Null for an added record. */
  before: ObjectChangeState | null;
  /** Null for a removed record. */
  after: ObjectChangeState | null;
  /** `name`, `parent` and attribute keys that differ between the sides. */
  changedFields: string[];
  /** Root first, ending with the record: where the change set puts it, or where the source held a removed one. */
  path: ObjectPathPart[];
  /** Where the source held a moved record; null unless `parent` changed. */
  beforePath?: ObjectPathPart[] | null;
}

export interface ObjectChangePage extends PageNavigation {
  items: ObjectChange[];
}

export interface RelationChangeEnd {
  objectId: string;
  objectTypeKey: string | null;
  name: string | null;
}

export interface RelationChangeState {
  attributes: Record<string, unknown>;
  version: number;
}

export interface RelationChange {
  kind: ChangeKind;
  relationId: string;
  relationTypeKey: string;
  /** An engine-maintained parent edge (D32). */
  containment: boolean;
  fromObject: RelationChangeEnd;
  toObject: RelationChangeEnd;
  before: RelationChangeState | null;
  after: RelationChangeState | null;
  changedFields: string[];
}

export interface RelationChangePage extends PageNavigation {
  items: RelationChange[];
}
