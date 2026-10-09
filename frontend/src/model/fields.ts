/**
 * Projection of an object onto the field keys a view or panel declares.
 *
 * `attributeName` labels a key and `fieldValue` reads it, both handling the built-in keys (name,
 * path, ancestors and timestamps) alongside attached attribute types. `formatValue` renders a
 * read value; it renders JSX and so lives in `ui/formatValue` rather than here, keeping this
 * module free of presentation.
 */

import type { EngineModel, ExpandedRelations, ObjectItem, ObjectTypeDefinition } from "@/types";
import {
  isSingleValuedRelatedColumn,
  objectTypeFor,
  RELATED_FIELD_PREFIX,
  relatedColumn,
  relatedFieldLabel,
} from "@/model/lookup";

export function attributeName(model: EngineModel, key: string) {
  if (key.startsWith(RELATED_FIELD_PREFIX)) {
    const column = relatedColumn(model, key);
    if (!column) return key;
    return column.field ? `${column.name} · ${relatedFieldLabel(model, column.field)}` : column.name;
  }
  if (key.startsWith("ancestor:")) {
    const objectTypeKey = key.slice("ancestor:".length);
    return objectTypeFor(model, objectTypeKey)?.name ?? objectTypeKey;
  }
  if (key === "name") return "Name";
  if (key === "path") return "Path";
  if (key === "objectType") return "Type";
  if (key === "id") return "ID";
  if (key === "createdAt") return "Created";
  if (key === "updatedAt") return "Updated";
  return model.attributeTypes.find((item) => item.key === key)?.name ?? key;
}

/** A row's related records in a `related:` column, as the list returned them (`expand`, K5). */
export function relatedRecords(item: ObjectItem, key: string, model: EngineModel): ExpandedRelations | undefined {
  const column = relatedColumn(model, key);
  return column
    ? item.expanded?.find(
        (entry) =>
          entry.relationTypeKey === column.relationTypeKey &&
          entry.direction === column.direction &&
          entry.field === column.field,
      )
    : undefined;
}

/** What a related record's chip says: its name, or its value of the column's field ("—" for none). */
export function relatedText(entry: ExpandedRelations["items"][number], field?: string): string {
  if (!field) return entry.object.fields.name;
  const value = entry.object.fields[field];
  if (value === undefined || value === null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

/** How many related records a list asks for per row and relation column: the API's maximum (K5b). */
export const RELATED_EXPAND_LIMIT = 20;

/** The `related:` columns among `columns`, as the list's `expand` names them (D146: the shown ones). */
export function relatedKeys(columns: readonly string[]): string[] {
  return columns
    .filter((column) => column.startsWith(RELATED_FIELD_PREFIX))
    .map((column) => column.slice(RELATED_FIELD_PREFIX.length));
}

export function fieldValue(item: ObjectItem, key: string, model: EngineModel): unknown {
  if (key.startsWith(RELATED_FIELD_PREFIX)) {
    const related = relatedRecords(item, key, model);
    return related?.items.length
      ? related.items.map((entry) => relatedText(entry, related.field)).join(", ")
      : undefined;
  }
  if (key.startsWith("ancestor:")) {
    const objectTypeKey = key.slice("ancestor:".length);
    return item.path.find((part) => part.objectTypeKey === objectTypeKey)?.name;
  }
  if (key === "name") return item.name;
  if (key === "path") return item.path.map((part) => part.name).join(" / ");
  if (key === "objectType") return objectTypeFor(model, item.objectTypeKey)?.name ?? item.objectTypeKey;
  if (key === "id") return item.id;
  if (key === "createdAt") return item.createdAt;
  if (key === "updatedAt") return item.updatedAt;
  return item.attributes.find((attribute) => attribute.attributeTypeKey === key)?.value;
}

/** Built-in timestamps are recorded for live records only; change sets and history have none. */
const LIVE_ONLY_FIELDS = ["createdAt", "updatedAt"];

/** Whether a field (or a `-field` sort) can be filtered or sorted in this data context. */
export function isQueryableField(field: string, live: boolean) {
  return live || !LIVE_ONLY_FIELDS.includes(field.replace(/^-/, ""));
}

/**
 * Whether a list of records of `objectTypes` sorts by `field` in this data context: every data
 * column does (S4R3 publication) — the name, the ID, the object type, a scalar attribute bound to one
 * of the types, and an ancestor when the list holds one type. The exceptions are what the server
 * cannot order: recorded timestamps outside live data, the computed path and JSON attributes. A
 * relation list also sorts by the `relationship` label its rows show.
 */
export function isSortableField(
  model: EngineModel,
  objectTypes: readonly ObjectTypeDefinition[],
  field: string,
  live: boolean,
  { relationList = false }: { relationList?: boolean } = {},
) {
  if (["name", "id", "objectType"].includes(field)) return true;
  if (field === "relationship") return relationList;
  if (field.startsWith(RELATED_FIELD_PREFIX))
    return !relationList && objectTypes.length === 1 && isSingleValuedRelatedColumn(model, objectTypes[0].key, field);
  if (LIVE_ONLY_FIELDS.includes(field)) return live;
  if (field.startsWith("ancestor:")) return objectTypes.length === 1;
  if (!objectTypes.some((type) => type.attributes.some((binding) => binding.attributeTypeKey === field))) return false;
  return model.attributeTypes.find((item) => item.key === field)?.valueType !== "json";
}

/**
 * The fields a list offers to sort by: its sortable columns in column order, then any further
 * fields the model declares for the sort menu (`sortFields`) that are sortable here.
 */
export function listSortFields(
  model: EngineModel,
  objectTypes: readonly ObjectTypeDefinition[],
  columns: readonly string[],
  declared: readonly string[],
  live: boolean,
  options?: { relationList?: boolean },
) {
  return [...new Set([...columns, ...declared])].filter((field) =>
    isSortableField(model, objectTypes, field, live, options),
  );
}
