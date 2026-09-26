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
}

export interface RelationUpdateInput {
  attributes: Record<string, unknown>;
  expectedVersion: number;
}

export interface ObjectPage extends PageNavigation {
  items: ObjectItem[];
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

export interface MappingReplacementResponse {
  sourceObjectId: string;
  mappingVersion: number;
  state: "mapped" | "unmapped";
  relationId: string | null;
  changeSetVersion: number | null;
}
