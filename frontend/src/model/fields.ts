/**
 * Projection of an object onto the field keys a view or panel declares.
 *
 * `attributeName` labels a key and `fieldValue` reads it, both handling the built-in keys (name,
 * path, ancestors and timestamps) alongside attached attribute types. `formatValue` renders a
 * read value; it renders JSX and so lives in `ui/formatValue` rather than here, keeping this
 * module free of presentation.
 */

import type { EngineModel, ObjectItem, ObjectTypeDefinition } from "@/types";
import { objectTypeFor } from "@/model/lookup";

export function attributeName(model: EngineModel, key: string) {
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

export function fieldValue(item: ObjectItem, key: string, model: EngineModel): unknown {
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

/** Built-in timestamps are recorded for live records only; drafts and history have none. */
const LIVE_ONLY_FIELDS = ["createdAt", "updatedAt"];

/** Whether a field (or a `-field` sort) can be filtered or sorted in this data context. */
export function isQueryableField(field: string, live: boolean) {
  return live || !LIVE_ONLY_FIELDS.includes(field.replace(/^-/, ""));
}

/**
 * Whether a list of records of `objectTypes` sorts by `field` in this data context: every data
 * column does (S4R3 revision) — the name, the ID, the object type, a scalar attribute bound to one
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
