/**
 * An export request from what the browser shows (0.9 J1u). A collection's filters become the
 * model-aware query's criteria for its type, with each value in the JSON type the query takes for
 * the field (D19); the search is not carried, since the query has no full-text search (D60).
 */

import { holdsOne, RELATED_FIELD_PREFIX, relatedColumn, relatedTargetTypes } from "@/model/lookup";
import type {
  ApplicationDefinition,
  CollectionFilter,
  CollectionQueryState,
  EngineModel,
  ExportCriterion,
  ExportViewState,
  PeopleLayout,
  ValueType,
  ViewDefinition,
} from "@/types";

/** Built-in fields a collection filters by, as the query names them, with their value types. */
const BUILT_IN: Record<string, ValueType> = {
  id: "text",
  name: "text",
  parentObjectId: "text",
  createdAt: "dateTime",
  updatedAt: "dateTime",
};

/** The query's value for a filter's text: a boolean, a number or the text itself. */
function queryValue(valueType: ValueType | undefined, operator: string, value: string): unknown {
  if (operator === "isNull" || operator === "isUnset" || valueType === "boolean") return value === "true";
  if (valueType === "integer") return Number.parseInt(value, 10);
  return value;
}

export function criteriaFromFilters(
  model: EngineModel,
  filters: CollectionFilter[],
  /** The type of each record a "has none under" or "has any under" filter names, by ID. */
  records: ReadonlyMap<string, { objectTypeKey: string }> = new Map(),
): ExportCriterion[] {
  const related = filters.filter((filter) => filter.field.startsWith(RELATED_FIELD_PREFIX));
  const hops = [...new Set(related.map((filter) => filter.field))].flatMap((field) =>
    relatedCriteria(
      model,
      field,
      related.filter((filter) => filter.field === field),
      records,
    ),
  );
  return [
    ...hops,
    ...filters
      .filter((filter) => !filter.field.startsWith(RELATED_FIELD_PREFIX))
      .map((filter) => {
        const valueType =
          BUILT_IN[filter.field] ?? model.attributeTypes.find((item) => item.key === filter.field)?.valueType;
        return {
          field: filter.field,
          op: filter.operator,
          value: queryValue(valueType, filter.operator, filter.value),
        };
      }),
  ];
}

/**
 * A relationship filter (0.9 K6) as the query's `related` hop, as the list applies it: records
 * related to any of the chosen ones (their IDs as alternatives), or, for `isNull`, to none (`not`)
 * or to any. "Under" is a hop whose records stand below the named one, by the ancestor criterion of
 * the record's own type (0.16 AG4); a record of unknown type adds none, so callers wait for the names.
 */
function relatedCriteria(
  model: EngineModel,
  field: string,
  entries: CollectionFilter[],
  records: ReadonlyMap<string, { objectTypeKey: string }>,
): ExportCriterion[] {
  const column = relatedColumn(model, field);
  if (!column) return [];
  const hop = { relationTypeKey: column.relationTypeKey, direction: column.direction };
  const ids = entries.filter((entry) => entry.operator === "eq").map((entry) => entry.value);
  const flags = entries.filter((entry) => entry.operator === "isNull").map((entry) => entry.value);
  return [
    ...(ids.length ? [{ related: { ...hop, where: ids.map((id) => ({ field: "id", op: "eq", value: id })) } }] : []),
    ...flags.map((flag) => ({ related: { ...hop, where: [] }, ...(flag === "true" ? { not: true } : {}) })),
    ...entries
      .filter((entry) => entry.operator === "under" || entry.operator === "notUnder")
      .flatMap((entry) => {
        const type = records.get(entry.value)?.objectTypeKey;
        if (!type) return [];
        return [
          {
            related: { ...hop, where: [{ field: `ancestor:${type}`, op: "eq", value: entry.value }] },
            ...(entry.operator === "notUnder" ? { not: true } : {}),
          },
        ];
      }),
  ];
}

/** Which part of the dialog a refusal belongs to, from its JSON pointer into the request. */
export type ExportField = "types" | "asOf" | "scope" | "layout" | "form";

export function exportField(pointer: unknown): ExportField {
  if (typeof pointer !== "string") return "form";
  if (pointer.startsWith("/people")) return "layout";
  if (pointer.startsWith("/scope/types")) return "types";
  if (pointer === "/scope/asOf") return "asOf";
  if (pointer === "/scope/parentObjectId") return "scope";
  return "form";
}

/** The model's object types an export of an application offers, in the model's order. */
export function exportableTypes(model: EngineModel, objectTypeKeys: readonly string[]) {
  return model.objectTypes.filter((item) => objectTypeKeys.includes(item.key));
}

/**
 * The relationships of a type a workbook for people can give a sheet of their own (0.9 J6, D182):
 * the relation key of each binding the type is at the `from` end of, the reverse key of each it is
 * at the `to` end of, each once; a parent relationship is left out (a record's parent is its own
 * field). Labelled as the type's relation columns are.
 */
export function sheetRelationships(model: EngineModel, objectTypeKey: string): { key: string; label: string }[] {
  const parentRelations = (typeKey: string) =>
    model.objectTypes.find((item) => item.key === typeKey)?.behavior?.parentRelationTypeKeys ?? [];
  const keys: string[] = [];
  for (const binding of model.objectTypeRelations) {
    const relation = model.relationTypes.find((item) => item.key === binding.relationTypeKey);
    if (!relation) continue;
    const containment = [binding.fromObjectTypeKey, binding.toObjectTypeKey].some((end) =>
      parentRelations(end).includes(binding.relationTypeKey),
    );
    if (containment) continue;
    if (binding.fromObjectTypeKey === objectTypeKey) keys.push(relation.key);
    if (binding.toObjectTypeKey === objectTypeKey) keys.push(relation.reverseKey);
  }
  return [...new Set(keys)].map((key) => ({
    key,
    label: relatedColumn(model, `${RELATED_FIELD_PREFIX}${key}`)?.name ?? key,
  }));
}

/**
 * Whether a table's `related:` column needs a sheet of its own to edit its relationships: it does
 * unless it shows the related record by name, each record holds at most one such relationship and
 * the relationship carries no fields of its own. Such a column edits them on the main sheet, with
 * the list to choose from.
 */
export function needsSheet(model: EngineModel, objectTypeKey: string, column: string): boolean {
  const related = relatedColumn(model, column);
  if (!related) return false;
  if (related.field) return true;
  const outgoing = related.direction === "outgoing";
  const bindings = model.objectTypeRelations.filter(
    (binding) =>
      binding.relationTypeKey === related.relationTypeKey &&
      (outgoing ? binding.fromObjectTypeKey : binding.toObjectTypeKey) === objectTypeKey,
  );
  return (
    bindings.length !== 1 ||
    !holdsOne(bindings[0], outgoing ? "from" : "to") ||
    (bindings[0].attributeTypeKeys?.length ?? 0) > 0
  );
}

/** The relation key a `related:` column reads (its key or reverse key, without a field). */
export function relationKeyOf(model: EngineModel, column: string): string | undefined {
  const related = relatedColumn(model, column);
  if (!related) return undefined;
  const relation = model.relationTypes.find((item) => item.key === related.relationTypeKey);
  if (!relation) return undefined;
  return related.direction === "outgoing" ? relation.key : relation.reverseKey;
}

/**
 * The fields a relation column of names may show instead in a workbook for people (D181): the
 * attributes of its one related type, unique ones first (a unique code loads back, others are
 * written as a summary). None for a column over several types or one that shows a field already.
 */
export function relationFields(
  model: EngineModel,
  objectTypeKey: string,
  column: string,
): { key: string; label: string }[] {
  const related = relatedColumn(model, column);
  if (!related || related.field) return [];
  const far = relatedTargetTypes(model, objectTypeKey, column);
  if (far.length !== 1) return [];
  const attributes = far[0].attributes
    .map((binding) => model.attributeTypes.find((item) => item.key === binding.attributeTypeKey))
    .filter((item) => item !== undefined && item.valueType !== "json");
  const unique = (item: (typeof attributes)[number]) => (item?.features?.unique ? 0 : 1);
  return [...attributes].sort((a, b) => unique(a) - unique(b)).map((item) => ({ key: item!.key, label: item!.name }));
}

/**
 * The type a relationship of `objectTypeKey` owns, as the engine decides it (D182): one binding,
 * from the type, required, to another type. Its sheet may be laid out as columns per parent.
 */
export function ownedType(model: EngineModel, objectTypeKey: string, key: string): string | undefined {
  const relation = model.relationTypes.find((item) => item.key === key);
  if (!relation) return undefined;
  const bindings = model.objectTypeRelations.filter(
    (binding) => binding.relationTypeKey === relation.key && binding.fromObjectTypeKey === objectTypeKey,
  );
  const [binding] = bindings;
  return bindings.length === 1 && binding.required && binding.toObjectTypeKey !== objectTypeKey
    ? binding.toObjectTypeKey
    : undefined;
}

/** How an owned relationship's sheet is laid out in the dialog (0.9 J6a). */
export interface OwnedChoice {
  columns: boolean;
  /** The parents added, by type. */
  parents: Record<string, { id: string; name: string }[]>;
  fields: string[];
}

/** One column the Advanced section lists: whether the main sheet holds it. */
export interface PeopleColumn {
  key: string;
  shown: boolean;
}

/** The request's `people` from the dialog's choices (0.9 J6, D188). */
export function peopleLayout(
  columns: readonly PeopleColumn[],
  sheets: readonly string[],
  fields: Readonly<Record<string, string>>,
  owned: Readonly<Record<string, OwnedChoice>> = {},
  lists = true,
): PeopleLayout {
  const shown = columns.filter((column) => column.shown).map((column) => column.key);
  const laidOut = Object.entries(owned).filter(([key, choice]) => choice.columns && sheets.includes(key));
  return {
    columns: shown,
    sheets: [...sheets],
    columnFields: Object.fromEntries(
      Object.entries(fields).filter(([column, field]) => field && shown.includes(column)),
    ),
    ...(laidOut.length
      ? {
          ownedColumns: Object.fromEntries(
            laidOut.map(([key, choice]) => [
              key,
              {
                parents: Object.values(choice.parents).flatMap((items) => items.map((item) => item.id)),
                // None chosen: the engine's default, the owned type's writable attributes.
                ...(choice.fields.length ? { fields: choice.fields } : {}),
              },
            ]),
          ),
        }
      : {}),
    ...(lists ? {} : { referenceLists: [] }),
  };
}

/**
 * What the page showing a view holds (0.17 EX1, PP-D18), for the dialog's "This view": the view, the
 * type its rows are of and what the page narrowed it to, in the page's own terms. The dialog turns
 * it into the request's `view`; nothing here builds an API call.
 */
export interface ExportViewStart {
  applicationKey: string;
  viewKey: string;
  name: string;
  kind: ViewDefinition["type"];
  /** The type the view's rows are of: what "The type" exports. */
  typeKey: string;
  search?: string;
  filters: CollectionFilter[];
  /** A relationships table or grid: filters on the `to` records. */
  toFilters: CollectionFilter[];
  toSearch?: string;
  parentObjectId?: string;
  /** A table: the columns shown, in order. */
  columns?: string[];
  /** A tree: its node types, whose records the file holds. */
  typeKeys?: string[];
  /** A matrix's column records, or a grid's `to` records, shown; all when absent. */
  columnIds?: string[];
  cellState?: ExportViewState["cellState"];
  mappingState?: ExportViewState["mappingState"];
  /** What the page narrowed the view to that the file cannot follow, said in the dialog. */
  notCarried?: string;
  /** A matrix whose cells link records: the cell type, whose identifying fields a cell can list (PP-D25). */
  lists?: { cellTypeKey: string };
}

/** The type a view's rows are of. */
export function viewTypeKey(view: ViewDefinition): string {
  switch (view.type) {
    case "table":
      return view.objectTypeKey;
    case "tree":
      return view.config.rootObjectTypeKeys[0];
    case "relationMatrix":
      return view.config.rowObjectTypeKey;
    case "mappingGrid":
      return view.config.direction === "outgoing" ? view.config.fromObjectTypeKey : view.config.toObjectTypeKey;
    case "relationTable":
      return view.config.fromObjectTypeKey;
  }
}

/** A relationships table's filters by the end they name, the end's prefix removed. */
function byEnd(filters: CollectionFilter[], prefix: "from:" | "to:") {
  return filters
    .filter((filter) => filter.field.startsWith(prefix))
    .map((filter) => ({ ...filter, field: filter.field.slice(prefix.length) }));
}

/**
 * The page's state for the view kind that reads it (the same state the list routes take): a filter
 * or search a kind does not read is left out, as it does not narrow that page (lenses of one
 * collection share their address).
 */
export function exportViewStart(
  application: ApplicationDefinition,
  view: ViewDefinition,
  query: CollectionQueryState,
  columns?: readonly string[],
): ExportViewStart {
  const base = {
    applicationKey: application.key,
    viewKey: view.key,
    name: view.name,
    kind: view.type,
    typeKey: viewTypeKey(view),
    filters: [] as CollectionFilter[],
    toFilters: [] as CollectionFilter[],
  };
  const search = query.search || undefined;
  switch (view.type) {
    case "table":
      return {
        ...base,
        filters: query.filters,
        search,
        parentObjectId: query.parentObjectId,
        columns: columns ? [...columns] : undefined,
      };
    case "tree":
      return { ...base, typeKeys: [...view.config.objectTypeKeys] };
    case "relationMatrix": {
      const columnIds = query.matrixColumnIds?.length ? query.matrixColumnIds : undefined;
      return {
        ...base,
        search,
        parentObjectId: query.parentObjectId,
        columnIds,
        cellState: columnIds ? query.matrixState : undefined,
        lists:
          view.config.cellActions?.includes("link") || view.config.cellActions?.includes("unlink")
            ? { cellTypeKey: view.config.cellObjectTypeKey }
            : undefined,
      };
    }
    case "mappingGrid":
      return {
        ...base,
        search,
        parentObjectId: query.parentObjectId,
        mappingState: query.mappingProposed ? undefined : query.mappingState,
        notCarried: query.mappingProposed
          ? "The AI's proposals filter is not carried: every source is exported."
          : undefined,
      };
    case "relationTable": {
      const grid = view.config.layout === "grid";
      const dropped = query.filters.some((filter) => filter.field.startsWith("relation:"));
      return {
        ...base,
        search,
        filters: byEnd(query.filters, "from:"),
        toFilters: byEnd(query.filters, "to:"),
        toSearch: grid ? query.gridSearch || undefined : undefined,
        columnIds: grid && query.gridColumnIds?.length ? query.gridColumnIds : undefined,
        notCarried: dropped ? "A filter on the relationship's own values is not carried." : undefined,
      };
    }
  }
}

/** The request's view state from what the page holds; relationship filters need their records' types. */
export function exportViewState(
  model: EngineModel,
  start: ExportViewStart,
  records: ReadonlyMap<string, { objectTypeKey: string }> = new Map(),
): ExportViewState {
  const where = criteriaFromFilters(model, start.filters, records);
  const toWhere = criteriaFromFilters(model, start.toFilters, records);
  return {
    ...(start.search ? { search: start.search } : {}),
    ...(where.length ? { where } : {}),
    ...(toWhere.length ? { toWhere } : {}),
    ...(start.toSearch ? { toSearch: start.toSearch } : {}),
    ...(start.parentObjectId ? { parentObjectId: start.parentObjectId } : {}),
    ...(start.columns?.length ? { columns: start.columns } : {}),
    ...(start.columnIds?.length ? { columnIds: start.columnIds } : {}),
    ...(start.cellState ? { cellState: start.cellState } : {}),
    ...(start.mappingState ? { mappingState: start.mappingState } : {}),
  };
}

/**
 * The dialog's count line for "This view" (EX1): what the file holds, as the page counts it, and
 * where it is read from. Nothing is said of a size the page does not know.
 */
export function viewCountLine(
  size: { rows?: number; columns?: number; records?: number } | undefined,
  source: string,
): string | undefined {
  const plural = (count: number, one: string) => `${count.toLocaleString("en")} ${count === 1 ? one : `${one}s`}`;
  const parts =
    size?.records !== undefined
      ? [plural(size.records, "record")]
      : size?.rows !== undefined
        ? [
            size.columns !== undefined
              ? `${plural(size.rows, "row")} × ${plural(size.columns, "column")}`
              : plural(size.rows, "row"),
          ]
        : [];
  return parts.length ? `${parts[0]}, from ${source}` : undefined;
}

/**
 * The fields of a type that name one of its records, in the order offered (PP-D25): its name, its
 * display attribute, then its other text attributes (PP-D27: not only the unique ones). The engine decides the same from the
 * model and refuses any other field.
 */
export function identifyingFields(model: EngineModel, typeKey: string): { key: string; label: string }[] {
  const type = model.objectTypes.find((item) => item.key === typeKey);
  if (!type) return [];
  const bound = type.attributes.map((item) => item.attributeTypeKey);
  const found = ["name"];
  const display = type.displayAttributeTypeKey;
  if (display && display !== "name" && bound.includes(display)) found.push(display);
  for (const key of bound) {
    const attribute = model.attributeTypes.find((item) => item.key === key);
    if (!found.includes(key) && (attribute?.valueType === "text" || attribute?.valueType === "longText"))
      found.push(key);
  }
  return found.map((key) => ({
    key,
    label: key === "name" ? "Name" : (model.attributeTypes.find((item) => item.key === key)?.name ?? key),
  }));
}

/** The size of the file "This view" writes: the page's total, not what it has loaded. */
export interface ExportViewSize {
  rows?: number;
  columns?: number;
  /** A view of records (a tree, a mapping grid): the line says records, not rows. */
  records?: number;
}

export interface ExportStart {
  /** The workspace; none lets the user choose one. */
  workspaceKey?: string;
  changeSetId?: string;
  publicationId?: string;
  /** The types offered, in the model's order, and those chosen at first. */
  objectTypeKeys: readonly string[];
  selected: readonly string[];
  /** The collection's filters, for its type. */
  filters?: { objectTypeKey: string; filters: CollectionFilter[] };
  search?: string;
  /** The page's parent scope: records directly below this record, of the filtered type. */
  parentObjectId?: string;
  /**
   * The table's columns as its Display shows them, in order, and those it hides: given, the dialog
   * offers a workbook for people of the filtered type (0.9 J6).
   */
  columns?: { shown: readonly string[]; hidden: readonly string[] };
  /** The list view the page shows and what it was narrowed to: the dialog's "This view" (EX1). */
  view?: ExportViewStart;
  /** What that view held when the dialog opened: the file's size, for the count line (EX1). */
  size?: ExportViewSize;
  /** The open change set's name, for "from change set …". */
  changeSetName?: string;
}
