/**
 * A relationships table as the editor's dialog builds it (0.13 RV): the binding chosen, then the
 * columns each end and the relationship offer, and only what the model's validation accepts
 * (`application_rules._check_relation_table_view`). Filters and sorts follow from the columns.
 */
import { keyFromLabel, objectTypeOf, relationTypeOf, typeLabel, typeName } from "@/model/outline";
import type { DraftOperation, ModelDraftOutline, OutlineApplication } from "@/types";

type Values = Record<string, unknown>;
type Option = { value: string; label: string };

const SCALAR = new Set(["text", "longText", "integer", "decimal", "boolean", "date", "dateTime"]);

const list = (value: unknown): string[] => (Array.isArray(value) ? (value as string[]) : []);
const bindingValue = (relationType: string, from: string, to: string) => `${relationType}|${from}|${to}`;

export function parseBinding(value: unknown) {
  const [relationType = "", from = "", to = ""] = String(value ?? "").split("|");
  return { relationType, from, to };
}

const bindingOf = (outline: ModelDraftOutline, value: unknown) => {
  const { relationType, from, to } = parseBinding(value);
  return outline.relations.find((item) => item.relationType === relationType && item.from === from && item.to === to);
};

/** The bindings a table can list: any but a containment. */
export function bindingOptions(outline: ModelDraftOutline): Option[] {
  return outline.relations
    .filter((relation) => !relation.containment)
    .map((relation) => ({
      value: bindingValue(relation.relationType, relation.from, relation.to),
      label: `${typeLabel(outline, relation.from)} → ${typeLabel(outline, relation.to)}, through ${
        relationTypeOf(outline, relation.relationType)?.name ?? relation.relationType
      }`,
    }));
}

/** An end's columns: its name and its scalar attributes. */
export function endColumnOptions(outline: ModelDraftOutline, binding: unknown, end: "from" | "to"): Option[] {
  const type = objectTypeOf(outline, parseBinding(binding)[end]);
  return [
    { value: "name", label: "Name" },
    ...(type?.attributes ?? [])
      .filter((item) => SCALAR.has(String(item.valueType)))
      .map((item) => ({ value: item.attributeType, label: item.name })),
  ];
}

/** The attributes the binding gives its relationships. */
export function attributeOptions(outline: ModelDraftOutline, binding: unknown): Option[] {
  return (bindingOf(outline, binding)?.attributeTypeKeys ?? []).map((key) => ({
    value: key,
    label: outline.attributeTypes.find((item) => item.key === key)?.name ?? key,
  }));
}

function defaultColumns(outline: ModelDraftOutline, binding: unknown, end: "from" | "to") {
  const attributes = objectTypeOf(outline, parseBinding(binding)[end])?.attributes ?? [];
  const told = attributes.find((item) => item.unique && SCALAR.has(String(item.valueType)));
  return ["name", ...(told ? [told.attributeType] : [])];
}

function defaultName(outline: ModelDraftOutline, values: Values) {
  const { from, to } = parseBinding(values.binding);
  return from && to ? `${typeName(outline, from)} to ${typeName(outline, to).toLowerCase()} relationships` : "";
}

/** The values after `changed` moved: what depends on it starts again, what was typed stays. */
export function followTable<V extends Values>(
  outline: ModelDraftOutline,
  next: V,
  previous: Values,
  changed: string,
): V {
  const values: Values = { ...next };
  if (changed === "binding") {
    values.fromColumns = defaultColumns(outline, values.binding, "from");
    values.toColumns = defaultColumns(outline, values.binding, "to");
    values.attributeColumns = attributeOptions(outline, values.binding).map((item) => item.value);
    if (previous.name === defaultName(outline, previous)) values.name = defaultName(outline, values);
  }
  return values as V;
}

export function newTableValues<V extends Values>(outline: ModelDraftOutline): V {
  const start = { binding: bindingOptions(outline)[0]?.value ?? "", name: "", groupBy: "", layout: "rows" };
  return followTable(outline, start, start, "binding") as unknown as V;
}

function configOf(outline: ModelDraftOutline, values: Values) {
  const { relationType, from, to } = parseBinding(values.binding);
  const features = (key: string) => outline.attributeTypes.find((item) => item.key === key)?.features ?? {};
  const fromColumns = list(values.fromColumns);
  const toColumns = list(values.toColumns);
  const attributes = list(values.attributeColumns);
  // The model's validation refuses a JSON attribute as a filter or a sort; it may still be a column.
  const json = (key: string) => outline.attributeTypes.find((item) => item.key === key)?.valueType === "json";
  const filterable = (ref: string, key: string) => (features(key).filterable === true && !json(key) ? [ref] : []);
  const sortable = (key: string) => (json(key) ? [] : [`relation:${key}`]);
  return {
    relationTypeKey: relationType,
    fromObjectTypeKey: from,
    toObjectTypeKey: to,
    fromColumns,
    toColumns,
    attributeColumns: attributes,
    filterFields: [
      ...attributes.flatMap((key) => filterable(`relation:${key}`, key)),
      ...fromColumns.filter((key) => key !== "name").flatMap((key) => filterable(`from:${key}`, key)),
      ...toColumns.filter((key) => key !== "name").flatMap((key) => filterable(`to:${key}`, key)),
    ],
    sortFields: [
      "from:name",
      ...fromColumns.filter((key) => key !== "name").map((key) => `from:${key}`),
      "to:name",
      ...toColumns.filter((key) => key !== "name").map((key) => `to:${key}`),
      ...attributes.flatMap(sortable),
    ],
    defaultSort: "from:name",
    groupBy: values.groupBy === "from" || values.groupBy === "to" ? values.groupBy : null,
    // The default layout is not written out.
    ...(values.layout === "grid" ? { layout: "grid" } : {}),
    pageSize: 20,
  };
}

/** The types the table needs that the application does not list yet. */
export function tableTypesToList(application: OutlineApplication | undefined, values: Values) {
  const { from, to } = parseBinding(values.binding);
  return [...new Set([from, to])].filter((key) => key && !(application?.objectTypeKeys ?? []).includes(key));
}

export function addTable(outline: ModelDraftOutline, applicationKey: string, values: Values): DraftOperation[] {
  const application = outline.applications.find((item) => item.key === applicationKey);
  const taken = new Set((application?.views ?? []).map((item) => item.key));
  const name = String(values.name ?? "");
  return [
    ...tableTypesToList(application, values).map((objectType): DraftOperation => ({
      kind: "listObjectType",
      applicationKey,
      objectType,
    })),
    {
      kind: "addView",
      applicationKey,
      view: { key: keyFromLabel(name, taken), name, type: "relationTable", config: configOf(outline, values) },
    },
  ];
}
