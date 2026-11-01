/**
 * An export request from what the browser shows (0.9 J1u). A collection's filters become the
 * model-aware query's criteria for its type, with each value in the JSON type the query takes for
 * the field (D19); the search is not carried, since the query has no full-text search (D60).
 */

import { RELATED_FIELD_PREFIX, relatedColumn, relatedTargetTypes } from "@/model/lookup";
import type { CollectionFilter, EngineModel, ExportCriterion, PeopleLayout, ValueType } from "@/types";

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
