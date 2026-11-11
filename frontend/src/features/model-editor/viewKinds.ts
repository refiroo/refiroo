/**
 * The views other than the relation matrix that an application's Add view… and a view's Change…
 * build (0.13 ED): a table of one type, a tree of the types that contain each other, and a mapping
 * grid between two types a relationship joins. Each form offers only what the model's validation
 * would accept (`application_rules._check_tree_view`, `_check_mapping_grid_view`), and a view is
 * changed property by property, as a matrix is (`matrixView.changeMatrix`).
 */
import { ancestorColumnOptions } from "@/features/model-editor/matrixView";
import { keyFromLabel, objectTypeOf, relationTypeOf, typeLabel, typeName } from "@/features/model-editor/outline";
import type { DraftOperation, ModelDraftOutline, OutlineApplication, OutlineView } from "@/types";

type Values = Record<string, unknown>;
type Option = { value: string; label: string };

export const VIEW_KIND_OPTIONS: Option[] = [
  { value: "table", label: "Table: the records of one type in rows" },
  { value: "tree", label: "Tree: records under the records that contain them" },
  { value: "mappingGrid", label: "Mapping grid: records of one type matched to records of another" },
  { value: "relationMatrix", label: "Relation matrix: rows and columns with the related records in the cells" },
  { value: "relationTable", label: "Relationships table: each relationship in a row, with its own attributes" },
];

const list = (value: unknown): string[] => (Array.isArray(value) ? (value as string[]) : []);
const text = (value: unknown) => (typeof value === "string" ? value.trim() : "");
const SCALAR = new Set(["text", "longText", "integer", "decimal", "boolean", "date", "dateTime"]);

const applicationOf = (outline: ModelDraftOutline, key: string): OutlineApplication | undefined =>
  outline.applications.find((item) => item.key === key);

const NONE: Option = { value: "", label: "None" };

// --- a table ---

export function tableTypeOptions(outline: ModelDraftOutline): Option[] {
  return outline.objectTypes.map((type) => ({ value: type.key, label: typeLabel(outline, type.key) }));
}

// --- a tree ---

/** The types that may stand at the top of a tree: those a record can exist without a parent. */
export function treeRootOptions(outline: ModelDraftOutline, applicationKey: string): Option[] {
  const listed = applicationOf(outline, applicationKey)?.objectTypeKeys ?? [];
  return outline.objectTypes
    .filter((type) => listed.includes(type.key) && type.rootCreatable)
    .map((type) => ({ value: type.key, label: typeLabel(outline, type.key) }));
}

/** The roots and every type the application lists that sits under them, at any depth. */
export function treeNodeTypes(outline: ModelDraftOutline, applicationKey: string, roots: string[]): string[] {
  const listed = applicationOf(outline, applicationKey)?.objectTypeKeys ?? [];
  const nodes = [...roots];
  for (let grown = true; grown;) {
    grown = false;
    for (const type of outline.objectTypes)
      if (listed.includes(type.key) && !nodes.includes(type.key) && type.parents.some((p) => nodes.includes(p))) {
        nodes.push(type.key);
        grown = true;
      }
  }
  return nodes;
}

/** The fields every type in `types` has: the name, then the attributes they all bind. */
function sharedFields(outline: ModelDraftOutline, types: string[], keep: (valueType: string) => boolean) {
  const attributes = (key: string) => objectTypeOf(outline, key)?.attributes ?? [];
  const first = types.length ? attributes(types[0]) : [];
  return first
    .filter(
      (item) =>
        keep(String(item.valueType)) &&
        types.every((key) => attributes(key).some((a) => a.attributeType === item.attributeType)),
    )
    .map((item) => ({ value: item.attributeType, label: item.name }));
}

export function treeFieldOptions(outline: ModelDraftOutline, applicationKey: string, values: Values): Option[] {
  const nodes = treeNodeTypes(outline, applicationKey, list(values.roots));
  return [{ value: "name", label: "Name" }, ...sharedFields(outline, nodes, (valueType) => SCALAR.has(valueType))];
}

export function treeAvailabilityOptions(outline: ModelDraftOutline, applicationKey: string, values: Values): Option[] {
  const nodes = treeNodeTypes(outline, applicationKey, list(values.roots));
  return [NONE, ...sharedFields(outline, nodes, (valueType) => valueType === "boolean")];
}

export function treeValues(view: Pick<OutlineView, "name" | "config">): Values {
  const config = (view.config ?? {}) as Record<string, unknown>;
  const childSort = (config.childSort ?? {}) as Record<string, string>;
  return {
    name: view.name,
    roots: list(config.rootObjectTypeKeys),
    label: text(config.labelField) || "name",
    secondary: text(config.secondaryField),
    order: (Object.values(childSort)[0] ?? "name").replace(/^-/, ""),
    availability: text(config.availabilityField),
  };
}

export function newTreeValues(outline: ModelDraftOutline, applicationKey: string): Values {
  const roots = treeRootOptions(outline, applicationKey)
    .slice(0, 1)
    .map((item) => item.value);
  return { name: "", roots, label: "name", secondary: "", order: "name", availability: "" };
}

/**
 * A tree's configuration from the form. Given the tree as it stands (`before`), only what the form
 * moved changes: actions the form does not offer (Create, Rename, Move…) and the per-type or
 * descending orders it does not show stay as they are.
 */
function treeConfig(
  outline: ModelDraftOutline,
  applicationKey: string,
  values: Values,
  before?: Record<string, unknown>,
) {
  const roots = list(values.roots);
  const nodes = treeNodeTypes(outline, applicationKey, roots);
  const order = text(values.order) || "name";
  const availability = text(values.availability);
  const declared = list(before?.actions);
  const actions = availability
    ? declared.includes("setAvailability")
      ? declared
      : [...declared, "setAvailability"]
    : declared.filter((action) => action !== "setAvailability");
  const sorted = (before?.childSort ?? {}) as Record<string, string>;
  const asked = text(values.order) ? order : undefined;
  const wasShown = (Object.values(sorted)[0] ?? "name").replace(/^-/, "");
  const childSort = Object.fromEntries(
    nodes
      .filter((key) => !roots.includes(key))
      .map((key) => {
        const current = sorted[key];
        if (current === undefined) return [key, order];
        if (asked === undefined || asked === wasShown) return [key, current];
        return [key, current.startsWith("-") ? `-${order}` : order];
      }),
  );
  return {
    rootObjectTypeKeys: roots,
    objectTypeKeys: nodes,
    labelField: text(values.label) || "name",
    secondaryField: text(values.secondary) || null,
    childSort,
    pageSize: 50,
    actions,
    availabilityField: availability || null,
  };
}

// --- a mapping grid ---

const binding = (relationType: string, from: string, to: string) => `${relationType}|${from}|${to}`;
export const parseBinding = (value: unknown) => {
  const [relationType = "", from = "", to = ""] = String(value ?? "").split("|");
  return { relationType, from, to };
};

/** The relationships a mapping grid can join: any but a containment. */
export function gridBindingOptions(outline: ModelDraftOutline): Option[] {
  return outline.relations
    .filter(
      (item) => !item.containment && !(item.required && ["one-to-one", "one-to-many"].includes(item.cardinality ?? "")),
    )
    .map((item) => ({
      value: binding(item.relationType, item.from, item.to),
      label: `${typeName(outline, item.from)} → ${typeName(outline, item.to)}, through ${relationTypeOf(outline, item.relationType)?.name ?? item.relationType}`,
    }));
}

/** The type whose records fill the rows, and the one matched to them. */
export function gridEnds(values: Values) {
  const { from, to } = parseBinding(values.binding);
  return values.rows === "to" ? { source: to, target: from } : { source: from, target: to };
}

export const GRID_ROWS: Option[] = [
  { value: "from", label: "The records of the first type" },
  { value: "to", label: "The records of the second type" },
];

function gridFields(outline: ModelDraftOutline, type: string, keep: (valueType: string) => boolean): Option[] {
  return [
    { value: "name", label: "Name" },
    ...(objectTypeOf(outline, type)?.attributes ?? [])
      .filter((item) => keep(String(item.valueType)))
      .map((item) => ({ value: item.attributeType, label: item.name })),
  ];
}

/** The row type's fields, and the types above it, as a matrix's row columns offer them. */
export const gridSourceOptions = (outline: ModelDraftOutline, values: Values): (Option & { group?: string })[] => [
  ...gridFields(outline, gridEnds(values).source, (valueType) => valueType !== "json"),
  ...ancestorColumnOptions(outline, gridEnds(values).source),
];
export const gridTargetOptions = (outline: ModelDraftOutline, values: Values) =>
  gridFields(outline, gridEnds(values).target, (valueType) => valueType !== "json");

/** The fields a person can search the candidates by: the name and the searchable attributes. */
export function gridSearchOptions(outline: ModelDraftOutline, values: Values): Option[] {
  const searchable = new Set(
    outline.attributeTypes.filter((item) => item.features.searchable === true).map((item) => item.key),
  );
  return gridFields(outline, gridEnds(values).target, () => true).filter(
    (item) => item.value === "name" || searchable.has(item.value),
  );
}

export function newGridValues(outline: ModelDraftOutline): Values {
  const first = gridBindingOptions(outline)[0]?.value ?? "";
  const values: Values = { name: "", binding: first, rows: "from" };
  return {
    ...values,
    sourceColumns: ["name"],
    targetColumns: ["name"],
    search: ["name"],
  };
}

export function gridValues(view: Pick<OutlineView, "name" | "config">): Values {
  const config = (view.config ?? {}) as Record<string, unknown>;
  return {
    name: view.name,
    binding: binding(text(config.relationTypeKey), text(config.fromObjectTypeKey), text(config.toObjectTypeKey)),
    rows: config.direction === "incoming" ? "to" : "from",
    sourceColumns: list(config.sourceColumns),
    targetColumns: list(config.targetDisplayColumns),
    search: list(config.candidateSearchFields),
  };
}

/** The columns follow the relationship or the rows chosen: they restart from the name. */
export function followGrid(next: Values, changed: string): Values {
  if (changed !== "binding" && changed !== "rows") return next;
  return { ...next, sourceColumns: ["name"], targetColumns: ["name"], search: ["name"] };
}

function gridConfig(values: Values) {
  const { relationType, from, to } = parseBinding(values.binding);
  return {
    relationTypeKey: relationType,
    fromObjectTypeKey: from,
    toObjectTypeKey: to,
    direction: values.rows === "to" ? "incoming" : "outgoing",
    sourceColumns: list(values.sourceColumns),
    targetDisplayColumns: list(values.targetColumns),
    candidateSearchFields: list(values.search),
    pageSize: 20,
  };
}

// --- adding and changing ---

/** The types a view needs that the application does not list yet. */
function typesToList(outline: ModelDraftOutline, applicationKey: string, kind: string, values: Values): string[] {
  const listed = applicationOf(outline, applicationKey)?.objectTypeKeys ?? [];
  const needed =
    kind === "table"
      ? [text(values.type)]
      : kind === "mappingGrid"
        ? [parseBinding(values.binding).from, parseBinding(values.binding).to]
        : [];
  return [...new Set(needed)].filter((key) => key && !listed.includes(key));
}

const listing = (outline: ModelDraftOutline, applicationKey: string, kind: string, values: Values): DraftOperation[] =>
  typesToList(outline, applicationKey, kind, values).map((objectType) => ({
    kind: "listObjectType",
    applicationKey,
    objectType,
  }));

/** A table, a tree or a mapping grid added to an application. */
export function addView(
  outline: ModelDraftOutline,
  applicationKey: string,
  kind: string,
  values: Values,
): DraftOperation[] {
  const name = text(values.name);
  const taken = new Set((applicationOf(outline, applicationKey)?.views ?? []).map((item) => item.key));
  const key = keyFromLabel(name, taken);
  const view =
    kind === "table"
      ? { key, name, type: "table", objectTypeKey: text(values.type) }
      : kind === "tree"
        ? { key, name, type: "tree", config: treeConfig(outline, applicationKey, values) }
        : { key, name, type: "mappingGrid", config: gridConfig(values) };
  return [...listing(outline, applicationKey, kind, values), { kind: "addView", applicationKey, view }];
}

/** A tree or a mapping grid changed in one step: the name, then each property that moved. */
export function changeView(
  outline: ModelDraftOutline,
  applicationKey: string,
  view: OutlineView,
  values: Values,
): DraftOperation[] {
  const kind = view.type ?? "";
  const before = (view.config ?? {}) as Record<string, unknown>;
  const config = kind === "tree" ? treeConfig(outline, applicationKey, values, before) : gridConfig(values);
  const set = (property: string, value: unknown): DraftOperation => ({
    kind: "setViewProperty",
    applicationKey,
    view: view.key,
    property,
    value,
  });
  const moved = Object.entries(config).filter(
    ([name, value]) => name !== "pageSize" && JSON.stringify(value) !== JSON.stringify(before[name] ?? null),
  );
  return [
    ...listing(outline, applicationKey, kind, values),
    ...(text(values.name) !== view.name ? [set("name", text(values.name))] : []),
    ...moved.map(([name, value]) => set(name, value)),
  ];
}
