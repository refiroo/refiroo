/**
 * An export request from what the browser shows (0.9 J1u). A collection's filters become the
 * model-aware query's criteria for its type, with each value in the JSON type the query takes for
 * the field (D19); the search is not carried, since the query has no full-text search (D60).
 */

import { RELATED_FIELD_PREFIX, relatedColumn } from "@/model/lookup";
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
  const related = filters.filter((filter) => filter.field.startsWith(RELATED_FIELD_PREFIX));
  const hops = [...new Set(related.map((filter) => filter.field))].flatMap((field) =>
    relatedCriteria(
      model,
      field,
      related.filter((filter) => filter.field === field),
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
 * or to any.
 */
function relatedCriteria(model: EngineModel, field: string, entries: CollectionFilter[]): ExportCriterion[] {
  const column = relatedColumn(model, field);
  if (!column) return [];
  const hop = { relationTypeKey: column.relationTypeKey, direction: column.direction };
  const ids = entries.filter((entry) => entry.operator === "eq").map((entry) => entry.value);
  const flags = entries.filter((entry) => entry.operator === "isNull").map((entry) => entry.value);
  return [
    ...(ids.length ? [{ related: { ...hop, where: ids.map((id) => ({ field: "id", op: "eq", value: id })) } }] : []),
    ...flags.map((flag) => ({ related: { ...hop, where: [] }, ...(flag === "true" ? { not: true } : {}) })),
  ];
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
