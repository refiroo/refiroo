/**
 * Declarative model contracts.
 *
 * These mirror the versioned JSON model the engine serves from `/api/v1/model`: applications,
 * object types, globally reusable attribute types, relation types, permitted object-type
 * relationships, and the view and panel definitions the generic renderers consume.
 */

export type ValueType = "text" | "longText" | "integer" | "decimal" | "boolean" | "date" | "dateTime" | "json";

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
  /** Business validity from two date attributes (schema 0.8); records are read on a date by it. */
  effectivePeriod?: { startAttributeTypeKey: string; endAttributeTypeKey: string };
}

export interface RelationTypeDefinition {
  key: string;
  reverseKey: string;
  name: string;
  reverseName: string;
  isOriented: boolean;
  features: Record<string, unknown>;
}

/** One criterion a record at a binding's end must meet to be chosen (0.9 K7, D169). */
export interface CandidateCriterion {
  field: string;
  op: string;
  value?: unknown;
}

export interface ObjectTypeRelationDefinition {
  relationTypeKey: string;
  fromObjectTypeKey: string;
  toObjectTypeKey: string;
  cardinality: "one-to-one" | "one-to-many" | "many-to-one" | "many-to-many";
  required?: boolean;
  attributeTypeKeys?: string[];
  features?: Record<string, unknown>;
  /** Which records may be chosen at each end (0.9 K7, D168); an end without criteria takes any. */
  candidates?: { from?: CandidateCriterion[]; to?: CandidateCriterion[] };
}

export interface TableViewDefinition {
  key: string;
  name: string;
  type: "table";
  objectTypeKey: string;
  config: {
    columns: string[];
    filterFields: string[];
    sortFields: string[];
    defaultSort: string;
    pageSize: number;
  };
}

export interface MappingGridViewDefinition {
  key: string;
  name: string;
  type: "mappingGrid";
  config: {
    relationTypeKey: string;
    fromObjectTypeKey: string;
    toObjectTypeKey: string;
    direction: "outgoing" | "incoming";
    sourceColumns: string[];
    targetDisplayColumns: string[];
    candidateSearchFields: string[];
    pageSize: number;
  };
}

export type RelationMatrixCellAction = "create" | "edit" | "link" | "unlink";

/** Schema 0.7: each row's related records, in columns by the ancestor record they sit under. */
export interface RelationMatrixViewDefinition {
  key: string;
  name: string;
  type: "relationMatrix";
  config: {
    relationTypeKey: string;
    direction: "outgoing" | "incoming";
    rowObjectTypeKey: string;
    columnObjectTypeKey: string;
    cellObjectTypeKey: string;
    rowColumns: string[];
    columnLabelField: string;
    cellFields: string[];
    searchFields: string[];
    cellActions?: RelationMatrixCellAction[];
    pageSize: number;
  };
}

export type TreeAction = "createChild" | "rename" | "move" | "setAvailability";

/** Schema 0.7: a containment hierarchy as a tree, from its root types down through its node types. */
export interface TreeViewDefinition {
  key: string;
  name: string;
  type: "tree";
  config: {
    rootObjectTypeKeys: string[];
    objectTypeKeys: string[];
    labelField: string;
    secondaryField?: string | null;
    /** A branch's order per child type, as a list `sort` value; types without one sort by name. */
    childSort?: Record<string, string>;
    pageSize: number;
    actions?: TreeAction[];
    availabilityField?: string | null;
  };
}

export type ViewDefinition =
  TableViewDefinition | MappingGridViewDefinition | RelationMatrixViewDefinition | TreeViewDefinition;

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
    /** Schema 0.7: the related-record fields the panel sorts by; absent lists by name. */
    sortFields?: string[];
    /** Schema 0.7, with `sortFields`: one of them, `-` prefixed for descending. */
    defaultSort?: string;
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
  /** Sidebar sections of its collections (schema 0.10, 0.10 N1); presentation only. */
  navigation?: { groups: NavigationGroupDefinition[] };
}

/** A labelled, foldable sidebar section naming collections (object type keys) of its application. */
export interface NavigationGroupDefinition {
  key: string;
  label: string;
  collections: string[];
  collapsed?: boolean;
}

/** A type of an application as a parent (Base 0.8 C4, `GET /model/placements`). */
export interface ModelPlacementParent {
  objectTypeKey: string;
  /** The types a record of this type contains. */
  childObjectTypeKeys: string[];
  /** The types a record can become under one of this type (a restructuring, ADR-034). */
  possibleObjectTypeKeys: string[];
}

export interface ModelApplicationPlacements {
  applicationKey: string;
  topLevelObjectTypeKeys: string[];
  parents: ModelPlacementParent[];
}

/** Where the model lets records stand: the engine's one rule, served beside the model. */
export interface ModelPlacements {
  applications: ModelApplicationPlacements[];
}

export interface EngineModel {
  /**
   * Served by `GET /model/placements` and attached when the model is loaded (`api.model`); not part
   * of the declarative document. Every read of where records may stand goes through
   * `model/placements`, which reads this and derives nothing.
   */
  placements?: ModelPlacements;
  /**
   * The release the server served the model from (`X-Model-Release-Id`), attached by `api.model`;
   * a page names it on its data writes (0.11 M6a). Not part of the declarative document.
   */
  releaseId?: string;
  schemaVersion: string;
  release: { key: string; name: string; version: string };
  product: { name: string; description?: string };
  attributeTypes: AttributeTypeDefinition[];
  objectTypes: ObjectTypeDefinition[];
  relationTypes: RelationTypeDefinition[];
  objectTypeRelations: ObjectTypeRelationDefinition[];
  applications: ApplicationDefinition[];
  /** The consumer APIs the release declares, as written (schema 0.8 or 0.9): only what both share is
   * read from the document; the rest from `ConsumerApiDefinition`, the definition expanded (C18). */
  consumerApis?: ConsumerApiSummary[];
}

export interface ConsumerApiSummary {
  key: string;
  name: string;
  description?: string;
  contractVersion: number;
}

/** A change event a consumer API declares: the types it covers, the changes, what an update watches. */
export interface ConsumerEventDeclaration {
  key: string;
  objectTypes: string[];
  changes: ("created" | "updated" | "deleted")[];
  /** Watched outputs and related blocks (`object.related`), by the names consumers read. */
  watch?: { fields?: string[]; related?: string[] };
}

/** A consumer API filter, which a webhook subscription may use: one verb and what it takes. */
export interface ConsumerFilterDefinition {
  byType?: boolean;
  under?: string[];
  linkedTo?: string[];
  through?: string[];
  onRelated?: string;
  matchOn?: string[];
  keepOnlyMatching?: boolean;
  scoreOnlyMatching?: boolean;
  crosswalk?: boolean;
  description?: string;
}

/**
 * A consumer API definition expanded (`GET /model/consumer-apis/{consumerApi}`, C18): schema 0.9
 * with every default written out, so a client never repeats the expansion. The parts the UI reads.
 */
export interface ConsumerApiDefinition extends ConsumerApiSummary {
  exposes: string[];
  /** Every exposed type's public name (`objectType` in events). */
  publicNames: Record<string, string>;
  operations: {
    objects?: { description?: string };
    xref?: { description?: string };
    resolve?: { description?: string };
    lists?: Record<string, { of: string; within?: { filter: string; types: string[] }; sortBy?: string }>;
    /** The events, those `perType` makes written out under `custom`. */
    events?: { perType: boolean; custom: ConsumerEventDeclaration[]; description?: string };
  };
  filters: Record<string, ConsumerFilterDefinition>;
}
