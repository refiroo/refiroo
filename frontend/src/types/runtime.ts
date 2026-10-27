/**
 * Runtime data contracts: stored objects and relations, their pages, audit history and workspace
 * runtime state.
 */

import type { ValueType } from "@/types/model";
import type { WorkspaceModel } from "@/types/modelAdmin";
import type { Actor, Principal } from "@/types/security";

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
  /** The list's relation columns, one per `expand` in its order (0.9 K5); absent when none. */
  expanded?: ExpandedRelations[];
}

/** A row's first related records of one relationship in name order, and how many there are. */
export interface ExpandedRelations {
  relationTypeKey: string;
  direction: "outgoing" | "incoming";
  /** The field each record shows beside its name, when the column names one (0.9 K5a). */
  field?: string;
  count: number;
  items: Array<{
    relationId: string;
    object: { id: string; objectTypeKey: string; version: number; fields: { name: string } & Record<string, unknown> };
  }>;
  nextCursor: string | null;
}

export interface Workspace {
  key: string;
  label: string;
  status: "active" | "retired";
  version: number;
  createdAt: string;
  updatedAt: string;
  /** The release the workspace runs (0.11 M1). */
  model: Omit<WorkspaceModel, "workspaceKey">;
}

/** One workspace as a single-item read returns it; the paged list omits the deletion fields. */
export interface WorkspaceDetail extends Workspace {
  /** True when nothing refers to the workspace, so it may be deleted rather than retired. */
  deletable: boolean;
  /** Why the workspace cannot be deleted, when `deletable` is false. */
  deleteBlockedBy?: "default" | "published" | "notEmpty" | "subscribed" | null;
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

/** A relation set the listed record anchors and its version, which a claimed write names (0.9 B3). */
export interface RelationSetVersion {
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  direction: "outgoing" | "incoming";
  relationSetVersion: number;
}

export interface RelationPage extends PageNavigation {
  items: RelationItem[];
  /** Live and in a change set: every set the record anchors in the listed direction and types. */
  relationSets?: RelationSetVersion[];
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
  /**
   * With `includeTypeChanges` in a change set (C3): the types the record would be under the
   * candidate, its own where the candidate's type already contains it.
   */
  objectTypeKeys?: string[];
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
  /** Who made it (0.12 Z4); null for a change from before sign-in. */
  actor: Actor | null;
  /** What kind of change (0.12 RH1, D391). */
  kind?: HistoryKind;
  /** Each value it changed, with the one before (D389, D390); none where the entry kept names only. */
  values?: HistoryValue[];
  /** A relationship's other record, read from this record (D392). */
  related?: HistoryRelated;
}

export type HistoryKind = "values" | "relationships" | "structure";

export interface HistoryValue {
  /** `name`, `parent`, an attribute type's key or a relation type's. */
  field: string;
  kind: "name" | "parent" | "attribute" | "relation";
  from: unknown;
  to: unknown;
  /** False where the record's previous entry kept names only: the value before was not recorded. */
  fromKnown: boolean;
}

export interface HistoryRelated {
  relationTypeKey: string | null;
  direction: "outgoing" | "incoming";
  objectId?: string;
  /** Its current name; absent for a record no longer in live data. */
  name?: string;
  objectTypeKey?: string;
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
  /** Who created it (0.12 Z4); null for one from before sign-in. */
  createdBy: Principal | null;
  /** Its latest publication request, whatever its state; null if never submitted (0.12 A1). */
  submission?: PublicationRequest | null;
}

/** One decision on a publication request (0.12 A1, D242). */
export interface PublicationDecision {
  id: string;
  outcome: "approve" | "sendBack";
  version: number;
  comment: string | null;
  decidedAt: string;
  decider: Principal | null;
}

/** A change set's request to be published (0.12 A1, D232). */
export interface PublicationRequest {
  id: string;
  workspaceKey: string;
  changeSetId: string;
  changeSetName: string | null;
  version: number;
  state: "submitted" | "withdrawn" | "approved" | "sentBack";
  submitter: Principal | null;
  comment: string | null;
  submittedAt: string;
  publicationId: string | null;
  decisions: PublicationDecision[];
}

export interface PublicationRequestPage {
  items: PublicationRequest[];
  nextCursor: string | null;
}

/** A workspace's approval policy (0.12 A1); both off and version 0 until set. */
export interface ApprovalPolicy {
  workspaceKey: string;
  requireApproval: boolean;
  secondPerson: boolean;
  version: number;
  /** Active people and clients holding Approve publications here; a count, no names. */
  approverCount: number;
}

export interface ChangeSetPage {
  items: ChangeSet[];
  nextCursor: string | null;
}

/** One of the caller's open change sets, wherever it is (0.12 HM1, D333). */
export interface OwnChangeSet extends ChangeSet {
  workspaceLabel: string;
  /** The records and relations it adds, changes or removes. */
  changeCount: number;
}

export interface OwnChangeSetPage extends PageNavigation {
  items: OwnChangeSet[];
}

/** What a change was made to (0.12 Z6, D343). */
export type ChangeEntryKind = "record" | "relationship" | "change-set" | "publication" | "model";

/** What an entry changed, named as it is now; fields are present where they apply to its kind. */
export interface ChangeSubject {
  id: string;
  name?: string | null;
  number?: number;
  applicationKey?: string;
  objectTypeKey?: string;
  objectTypeName?: string;
  relationTypeKey?: string;
  relationTypeName?: string;
  fromObject?: { id: string; name: string | null };
  toObject?: { id: string; name: string | null };
  /** A record or relationship gone from where it was. */
  removed?: boolean;
}

/** One data or model change across workspaces (`GET /changes`, 0.12 Z6, D340). */
export interface ChangeEntry {
  id: string;
  occurredAt: string;
  kind: ChangeEntryKind;
  action: string;
  /** Null for model administration outside workspaces and a deleted workspace's entries. */
  workspace: { key: string; label: string } | null;
  /** The change set it was made in, or a publication published; `open` while it can be opened. */
  changeSet: { id: string; name: string | null; open: boolean } | null;
  subject: ChangeSubject;
  changedFields: string[];
  attributes: { key: string; name: string }[];
  cause: { kind: string; id?: string };
  actor: Actor | null;
}

export interface ChangeEntryPage extends PageNavigation {
  items: ChangeEntry[];
}

/** An application of a workspace's model, as the home page links it. */
export interface WorkspaceApplication {
  key: string;
  name: string;
  icon: string | null;
  color: string | null;
  defaultView: string;
}

/** A workspace the caller may browse, with what waits for them there (0.12 HM1, D332). */
export interface OwnWorkspace {
  key: string;
  label: string;
  isDefault: boolean;
  model: Omit<WorkspaceModel, "workspaceKey">;
  /** Empty when this version cannot serve the workspace's model. */
  applications: WorkspaceApplication[];
  /** The open change sets the caller created here. */
  ownChangeSets: number;
  /** Every open change set here, for a caller holding Publish; null otherwise. */
  openChangeSets: number | null;
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
  /** Who published it, and who withdrew it or published the one after it (0.12 Z4). */
  publishedBy: Principal | null;
  withdrawnBy: Principal | null;
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
  /** The side's type; it differs between the sides of a reclassified record (C1). */
  objectTypeKey: string;
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
  /** `objectType` (first), `name`, `parent` and attribute keys that differ between the sides. */
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

/* Restructuring (Base 0.8 Milestone C, ADR-034): a plan previewed, then applied in a change set. */

export type RestructuringOperation =
  | { kind: "move"; objectId: string; parentObjectId: string | null; objectTypeKey?: string }
  | { kind: "changeType"; objectId: string; objectTypeKey: string }
  | {
      kind: "insertLevel";
      parentObjectId: string | null;
      childObjectIds: string[];
      objectTypeKey: string;
      name: string;
    }
  | { kind: "removeLevel"; objectId: string }
  | { kind: "changeTypeUnder"; objectId: string; fromObjectTypeKey: string; objectTypeKey: string };

export interface RestructuringTypeChoice {
  objectTypeKey: string;
  parentObjectTypeKey: string | null;
  newObjectTypeKey: string;
}

export interface RestructuringMappingChoice {
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  /** `from` names a source attribute type, or null for no source; unlisted ones keep the suggestion. */
  attributes: { attributeTypeKey: string; from: string | null }[];
  restore: boolean;
}

export interface RestructuringRelationInput {
  relationTypeKey: string;
  direction: "outgoing" | "incoming";
  objectId: string;
}

export interface RestructuringInput {
  /** A record's ID, or `new` for the record `insertLevel` creates. */
  objectId: string;
  attributes: { attributeTypeKey: string; value: unknown }[];
  relations: RestructuringRelationInput[];
}

export interface RestructuringRequest {
  operation: RestructuringOperation;
  choices: { types: RestructuringTypeChoice[]; mappings: RestructuringMappingChoice[] };
  inputs: RestructuringInput[];
}

export type RestructuringOutcomeFilter =
  "typeChanged" | "moved" | "withoutPlace" | "restored" | "needsInput" | "refused";

export interface RestructuringSummary {
  recordCount: number;
  typeChangeCount: number;
  moveCount: number;
  createdCount: number;
  removedCount: number;
  valuesWithoutPlaceCount: number;
  relationshipsWithoutPlaceCount: number;
  restoredCount: number;
  inputsNeededCount: number;
  refusalCount: number;
}

export interface RestructuringRefusal {
  code: string;
  message: string;
  objectId?: string | null;
  conflictingObjectId?: string | null;
  details?: Record<string, unknown> | null;
}

export interface RestructuringTypeQuestion {
  objectTypeKey: string;
  parentObjectTypeKey: string | null;
  options: string[];
  chosen: string | null;
  recordCount: number;
}

export interface RestructuringPairAttribute {
  attributeTypeKey: string;
  from: string | null;
  rule: "sameType" | "display" | "uniqueRequired" | "choice" | "none";
  alternatives: string[];
  kept: number;
  mapped: number;
  restored: number;
  inputs: number;
  empty: number;
}

export interface RestructuringPair {
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  recordCount: number;
  restore: boolean;
  attributes: RestructuringPairAttribute[];
  withoutPlace: { attributeTypeKey: string; count: number }[];
  relations: {
    relationTypeKey: string;
    direction: "outgoing" | "incoming";
    outcome: "kept" | "withoutPlace";
    count: number;
  }[];
}

export interface RestructuringRelationship {
  relationId: string;
  relationTypeKey: string;
  direction: "outgoing" | "incoming";
  objectId: string;
  objectTypeKey: string;
  name: string;
}

export interface RestructuringInputNeeded {
  kind: "attribute" | "relation";
  key: string;
  reason: "required" | "invalidValue" | "atLeastOneOf" | "requiredRelation";
}

export interface RestructuringRecord {
  objectId: string;
  name: string;
  path: ObjectPathPart[];
  /** Null for the record `insertLevel` creates. */
  before: { objectTypeKey: string | null; parentObjectId: string | null } | null;
  /** Null for the record `removeLevel` deletes; its type is null while its question is open. */
  after: { objectTypeKey: string | null; parentObjectId: string | null } | null;
  outcomes: ("typeChanged" | "moved" | "created" | "removed")[];
  attributes: {
    attributeTypeKey: string;
    from: string | null;
    outcome: "kept" | "mapped" | "restored" | "input" | "default" | "empty";
    value: unknown;
  }[];
  withoutPlace: {
    attributes: { attributeTypeKey: string; value: unknown }[];
    relationships: RestructuringRelationship[];
  };
  restoredRelationships: RestructuringRelationship[];
  inputsNeeded: RestructuringInputNeeded[];
  refusals: RestructuringRefusal[];
}

export interface RestructuringPreview extends PageNavigation {
  changeSetId: string;
  changeSetVersion: number;
  planDigest: string;
  status: "ready" | "needsInput" | "refused";
  summary: RestructuringSummary;
  typeQuestions: RestructuringTypeQuestion[];
  pairs: RestructuringPair[];
  refusals: RestructuringRefusal[];
  refusalCount: number;
  refusalsTruncated: boolean;
  records: RestructuringRecord[];
}

export interface RestructuringResult {
  operationId: string;
  changeSetId: string;
  changeSetVersion: number;
  summary: RestructuringSummary;
  createdObjectId: string | null;
}
