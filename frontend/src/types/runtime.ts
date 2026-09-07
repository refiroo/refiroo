/**
 * Runtime data contracts: stored objects and relations, their pages, audit history and workspace
 * runtime state.
 */

import type { ValueType } from "@/types/model";

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
  createdAt: string;
  updatedAt: string;
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
  createdAt?: string;
  updatedAt?: string;
}

export interface RelationItem {
  direction: "outgoing" | "incoming";
  relation: RelationRecord;
  object: ObjectItem;
}

export interface RelationPage {
  items: RelationItem[];
  nextCursor: string | null;
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

export interface ObjectPage {
  items: ObjectItem[];
  nextCursor: string | null;
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
