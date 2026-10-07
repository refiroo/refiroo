/**
 * An export request from what the browser shows (0.9 J1u). A collection's filters become the
 * model-aware query's criteria for its type, with each value in the JSON type the query takes for
 * the field (D19); the search is not carried, since the query has no full-text search (D60).
 */

import type { CollectionFilter, EngineModel, ExportCriterion, ValueType } from "@/types";

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

export function criteriaFromFilters(model: EngineModel, filters: CollectionFilter[]): ExportCriterion[] {
  return filters.map((filter) => {
    const valueType =
      BUILT_IN[filter.field] ?? model.attributeTypes.find((item) => item.key === filter.field)?.valueType;
    return { field: filter.field, op: filter.operator, value: queryValue(valueType, filter.operator, filter.value) };
  });
}

/** Which part of the dialog a refusal belongs to, from its JSON pointer into the request. */
export type ExportField = "types" | "asOf" | "scope" | "form";

export function exportField(pointer: unknown): ExportField {
  if (typeof pointer !== "string") return "form";
  if (pointer.startsWith("/scope/types")) return "types";
  if (pointer === "/scope/asOf") return "asOf";
  if (pointer === "/scope/parentObjectId") return "scope";
  return "form";
}

/** The model's object types an export of an application offers, in the model's order. */
export function exportableTypes(model: EngineModel, objectTypeKeys: readonly string[]) {
  return model.objectTypes.filter((item) => objectTypeKeys.includes(item.key));
}
