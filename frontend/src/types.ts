export type ValueType =
  | "text"
  | "longText"
  | "integer"
  | "decimal"
  | "boolean"
  | "date"
  | "dateTime"
  | "json";

export interface AttributeTypeDefinition {
  key: string;
  name: string;
  description?: string;
  valueType: ValueType;
  default?: unknown;
  features: Record<string, unknown>;
  validation: Record<string, unknown>;
  ui: Record<string, unknown>;
}

export interface ObjectTypeAttributeDefinition {
  attributeTypeKey: string;
  required: boolean;
  readOnly: boolean;
  order: number;
  ui: Record<string, unknown>;
}

export interface ObjectTypeDefinition {
  key: string;
  name: string;
  pluralName: string;
  description?: string;
  icon?: string;
  displayAttributeTypeKey?: string;
  attributes: ObjectTypeAttributeDefinition[];
  features: Record<string, unknown>;
  behavior: { parentRelationTypeKeys?: string[]; [key: string]: unknown };
  validation: { atLeastOneOf?: string[]; [key: string]: unknown };
}

export interface RelationTypeDefinition {
  key: string;
  reverseKey: string;
  name: string;
  reverseName: string;
  isOriented: boolean;
  features: Record<string, unknown>;
}

export interface ObjectTypeRelationDefinition {
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  cardinality: "one-to-one" | "one-to-many" | "many-to-many";
  required?: boolean;
  attributeTypeKeys?: string[];
  features?: Record<string, unknown>;
}

export interface ViewDefinition {
  key: string;
  name: string;
  type: "table" | "form" | "dashboard" | "mappingGrid" | "tree";
  objectTypeKey?: string;
  config: { columns?: string[]; [key: string]: unknown };
}

export interface BreadcrumbDefinition {
  showApplication: boolean;
  showObjectType: boolean;
  showAncestors: boolean;
}

export interface DetailHeaderDefinition {
  titleField: string;
  subtitleField?: string;
  showObjectType: boolean;
}

interface PanelDefinitionBase {
  key: string;
  title: string;
  region: "main" | "side";
  order: number;
  visible: boolean;
}

export interface AttributesPanelDefinition extends PanelDefinitionBase {
  type: "attributes";
  config: { fields: string[] };
}

export interface ChildrenPanelDefinition extends PanelDefinitionBase {
  type: "children";
  config: { objectTypeKeys: string[]; columns: string[]; pageSize: number };
}

export interface RelationsPanelDefinition extends PanelDefinitionBase {
  type: "relations";
  config: {
    relationTypeKeys: string[];
    direction: "outgoing" | "incoming" | "both";
    columns: string[];
    showRelationshipColumn?: boolean;
  };
}

export interface TablePanelDefinition extends PanelDefinitionBase {
  type: "table";
  config: {
    objectTypeKey: string;
    columns: string[];
    filterByParent: boolean;
    pageSize: number;
  };
}

export interface HierarchyPanelDefinition extends PanelDefinitionBase {
  type: "hierarchy";
  config: { showParent: boolean; showAncestors: boolean };
}

export type PanelDefinition =
  | AttributesPanelDefinition
  | ChildrenPanelDefinition
  | RelationsPanelDefinition
  | TablePanelDefinition
  | HierarchyPanelDefinition;

export interface DetailViewDefinition {
  objectTypeKey: string;
  breadcrumbs: BreadcrumbDefinition;
  header: DetailHeaderDefinition;
  panels: PanelDefinition[];
}

export interface ApplicationDefinition {
  key: string;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  state: "draft" | "active" | "retired";
  objectTypeKeys: string[];
  defaultView: string;
  views: ViewDefinition[];
  details: DetailViewDefinition[];
  settings: Record<string, unknown>;
}

export interface EngineModel {
  schemaVersion: string;
  release: { key: string; name: string; version: string };
  product: { name: string; description?: string };
  attributeTypes: AttributeTypeDefinition[];
  objectTypes: ObjectTypeDefinition[];
  relationTypes: RelationTypeDefinition[];
  objectTypeRelations: ObjectTypeRelationDefinition[];
  applications: ApplicationDefinition[];
}

export interface ObjectItem {
  id: string;
  workspaceKey: string;
  applicationKey: string;
  objectTypeKey: string;
  parentObjectId: string | null;
  state: string;
  name: string;
  path: Array<{ id: string; name: string; objectTypeKey: string }>;
  attributes: ObjectAttributeValue[];
  version: number;
  createdAt: string;
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

export type RouteState =
  | { kind: "list"; applicationKey: string; viewKey: string }
  | { kind: "detail"; applicationKey: string; objectTypeKey: string; objectId: string };

export interface ObjectPage {
  items: ObjectItem[];
  nextCursor: string | null;
}

export interface DeleteObjectSummary {
  id: string;
  name: string;
  objectTypeKey: string;
  applicationKey: string;
  parentObjectId: string | null;
}

export interface DeleteObjectDependency extends DeleteObjectSummary {
  reason: "child" | "fkDependent";
  viaObjectId: string;
  relationTypeKey?: string;
}

export interface DeleteRelationshipDependency {
  id: string;
  relationTypeKey: string;
  fromObject: DeleteObjectSummary;
  toObject: DeleteObjectSummary;
  fkPk: boolean;
  relatedObjectWillBeDeleted: boolean;
}

export interface DeleteImpact {
  rootObject: DeleteObjectSummary;
  objectsToDelete: DeleteObjectDependency[];
  relationshipsToRemove: DeleteRelationshipDependency[];
  objectCount: number;
  relationshipCount: number;
}
