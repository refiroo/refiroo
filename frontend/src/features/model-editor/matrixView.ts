/**
 * A relation matrix as the editor's dialog builds it: each choice narrows the next, and only what
 * the model's validation would accept is offered (application_rules._check_relation_matrix_view).
 */
import { keyFromLabel, objectTypeOf, relationTypeOf, typeLabel, typeName } from "@/features/model-editor/outline";
import type { DraftOperation, ModelDraftOutline, OutlineApplication, OutlineRelation } from "@/types";

type Values = Record<string, unknown>;
type Option = { value: string; label: string };

const AT_MOST_IN_A_CELL = 3;

const applicationOf = (outline: ModelDraftOutline, key: string): OutlineApplication | undefined =>
  outline.applications.find((item) => item.key === key);

const list = (value: unknown): string[] => (Array.isArray(value) ? (value as string[]) : []);

/** The types a type sits under, at any depth. */
function ancestorsOf(outline: ModelDraftOutline, key: string): string[] {
  const found: string[] = [];
  const walk = (type: string) => {
    for (const parent of objectTypeOf(outline, type)?.parents ?? [])
      if (parent !== key && !found.includes(parent)) {
        found.push(parent);
        walk(parent);
      }
  };
  walk(key);
  return found;
}

const cellValue = (relationType: string, direction: string, cell: string) => `${relationType}|${direction}|${cell}`;

export function parseCell(value: unknown) {
  const [relationType = "", direction = "", cell = ""] = String(value ?? "").split("|");
  return { relationType, direction, cell };
}

const bindingOf = (outline: ModelDraftOutline, row: string, value: unknown): OutlineRelation | undefined => {
  const { relationType, direction, cell } = parseCell(value);
  const [from, to] = direction === "outgoing" ? [row, cell] : [cell, row];
  return outline.relations.find((item) => item.relationType === relationType && item.from === from && item.to === to);
};

/** What a row type's cell can hold: a type related to it that sits under a parent, to give columns. */
export function cellOptions(outline: ModelDraftOutline, row: string): Option[] {
  return outline.relations.flatMap((relation) => {
    if (relation.containment) return [];
    const relationType = relationTypeOf(outline, relation.relationType);
    const ends = [
      ...(relation.from === row ? [{ cell: relation.to, direction: "outgoing", name: relationType?.name }] : []),
      ...(relation.to === row && relation.from !== row
        ? [{ cell: relation.from, direction: "incoming", name: relationType?.reverseName ?? relationType?.name }]
        : []),
    ];
    return ends
      .filter((end) => ancestorsOf(outline, end.cell).length > 0)
      .map((end) => ({
        value: cellValue(relation.relationType, end.direction, end.cell),
        label: `${typeLabel(outline, end.cell)}, through ${end.name ?? relation.relationType}`,
      }));
  });
}

export function rowOptions(outline: ModelDraftOutline): Option[] {
  return outline.objectTypes
    .filter((type) => cellOptions(outline, type.key).length > 0)
    .map((type) => ({ value: type.key, label: typeLabel(outline, type.key) }));
}

/** The furthest parents first: a top-level type usually gives the columns meant. */
export function columnOptions(outline: ModelDraftOutline, value: unknown): Option[] {
  return [...ancestorsOf(outline, parseCell(value).cell)]
    .reverse()
    .map((key) => ({ value: key, label: typeLabel(outline, key) }));
}

const SCALAR = new Set(["text", "longText", "integer", "decimal", "boolean", "date", "dateTime"]);

export function columnLabelOptions(outline: ModelDraftOutline, column: unknown): Option[] {
  const attributes = objectTypeOf(outline, String(column ?? ""))?.attributes ?? [];
  return [
    ...attributes
      .filter((item) => SCALAR.has(String(item.valueType)))
      .map((item) => ({ value: item.attributeType, label: item.name })),
    { value: "name", label: "Name" },
  ];
}

export function cellFieldOptions(outline: ModelDraftOutline, value: unknown): Option[] {
  return (objectTypeOf(outline, parseCell(value).cell)?.attributes ?? []).map((item) => ({
    value: item.attributeType,
    label: item.name,
  }));
}

/** The types above a type as columns (`ancestor:<type>`), shared by a matrix's rows and a mapping grid's. */
export function ancestorColumnOptions(outline: ModelDraftOutline, key: string): (Option & { group: string })[] {
  return ancestorsOf(outline, key).map((ancestor) => ({
    value: `ancestor:${ancestor}`,
    label: typeName(outline, ancestor),
    group: "From the parents",
  }));
}

export function rowColumnOptions(outline: ModelDraftOutline, row: unknown): (Option & { group?: string })[] {
  const key = String(row ?? "");
  return [
    { value: "name", label: "Name" },
    ...(objectTypeOf(outline, key)?.attributes ?? []).map((item) => ({ value: item.attributeType, label: item.name })),
    ...ancestorColumnOptions(outline, key),
  ];
}

const CREATE = { value: "create", label: "Create" };
const EDIT = { value: "edit", label: "Edit" };
const LINK = { value: "link", label: "Link existing" };
const UNLINK = { value: "unlink", label: "Unlink" };

/** The cell actions that could succeed, as `_cell_action_refusal` reads them. */
export function actionOptions(outline: ModelDraftOutline, values: Values): Option[] {
  const { relationType, direction, cell } = parseCell(values.cell);
  const attributes = objectTypeOf(outline, cell)?.attributes ?? [];
  const fields = list(values.cellFields);
  const binding = bindingOf(outline, String(values.row ?? ""), values.cell);
  const canCreate =
    attributes.every((item) => !item.required || fields.includes(item.attributeType)) &&
    !outline.relations.some(
      (item) =>
        item.to === cell &&
        item.required &&
        !item.containment &&
        !(direction === "outgoing" && item.relationType === relationType),
    );
  const canEdit = attributes.some((item) => fields.includes(item.attributeType) && !item.readOnly);
  return [...(canCreate ? [CREATE] : []), ...(canEdit ? [EDIT] : []), LINK, ...(binding?.required ? [] : [UNLINK])];
}

export const cellHint = (outline: ModelDraftOutline, values: Values) => {
  const binding = bindingOf(outline, String(values.row ?? ""), values.cell);
  if (!binding) return undefined;
  const rules = [
    binding.required && "required",
    binding.uniquePer && `one per ${typeName(outline, binding.uniquePer)}`,
  ];
  const named = rules.filter(Boolean).join(", ");
  const others = outline.relations
    .filter((item) => item.relationType === binding.relationType && item !== binding)
    .map((item) => typeLabel(outline, item.from));
  return [
    named && `${named[0].toUpperCase()}${named.slice(1)}.`,
    others.length > 0 && `The same relation also serves ${[...new Set(others)].join(", ")}.`,
  ]
    .filter(Boolean)
    .join(" ");
};

export const actionHint = (outline: ModelDraftOutline, values: Values) =>
  bindingOf(outline, String(values.row ?? ""), values.cell)?.required
    ? "Unlink isn't offered: this relation is required."
    : undefined;

function defaultName(outline: ModelDraftOutline, values: Values) {
  const { cell } = parseCell(values.cell);
  const plural = objectTypeOf(outline, cell)?.pluralName;
  return values.row && plural ? `${typeName(outline, String(values.row))} ${plural.toLowerCase()}` : "";
}

function defaultRowColumns(outline: ModelDraftOutline, row: unknown) {
  const attributes = objectTypeOf(outline, String(row ?? ""))?.attributes ?? [];
  const told = attributes.find((item) => item.unique) ?? attributes[0];
  return ["name", ...(told ? [told.attributeType] : [])];
}

function defaultColumnLabel(outline: ModelDraftOutline, column: unknown) {
  const attributes = objectTypeOf(outline, String(column ?? ""))?.attributes ?? [];
  return attributes.find((item) => item.unique && SCALAR.has(String(item.valueType)))?.attributeType ?? "name";
}

function defaultCellFields(outline: ModelDraftOutline, value: unknown) {
  const attributes = objectTypeOf(outline, parseCell(value).cell)?.attributes ?? [];
  const required = attributes.filter((item) => item.required).map((item) => item.attributeType);
  const rest = attributes.filter((item) => !item.required).map((item) => item.attributeType);
  return [...required, ...rest].slice(0, Math.max(AT_MOST_IN_A_CELL, required.length));
}

/** The values after `changed` moved: what depends on it starts again, what was typed stays. */
export function followMatrix<V extends Values>(
  outline: ModelDraftOutline,
  next: V,
  previous: Values,
  changed: string,
): V {
  const values: Values = { ...next };
  const row = changed === "row";
  const cell = row || changed === "cell";
  const column = cell || changed === "column";
  if (row) values.cell = cellOptions(outline, String(values.row))[0]?.value ?? "";
  if (cell) {
    values.column = columnOptions(outline, values.cell)[0]?.value ?? "";
    values.cellFields = defaultCellFields(outline, values.cell);
  }
  if (column) values.columnLabel = defaultColumnLabel(outline, values.column);
  if (row) values.rowColumns = defaultRowColumns(outline, values.row);
  const offered = actionOptions(outline, values).map((item) => item.value);
  values.actions = cell
    ? offered.filter((item) => item === "create" || item === "edit")
    : list(values.actions).filter((item) => offered.includes(item));
  if (cell && previous.name === defaultName(outline, previous)) values.name = defaultName(outline, values);
  return values as V;
}

/** A new matrix's starting values: the first row that can have one, and what follows from it. */
export function newMatrixValues<V extends Values>(outline: ModelDraftOutline): V {
  const start = { row: rowOptions(outline)[0]?.value ?? "", name: "" };
  return followMatrix(outline, start, start, "row") as unknown as V;
}

export function matrixValues<V extends Values>(view: { name: string; matrix?: Record<string, unknown> | null }): V {
  const config = view.matrix ?? {};
  return {
    name: view.name,
    row: config.rowObjectTypeKey,
    cell: cellValue(String(config.relationTypeKey), String(config.direction), String(config.cellObjectTypeKey)),
    column: config.columnObjectTypeKey,
    columnLabel: config.columnLabelField,
    cellFields: list(config.cellFields),
    rowColumns: list(config.rowColumns),
    actions: list(config.cellActions),
  } as unknown as V;
}

function configOf(outline: ModelDraftOutline, values: Values) {
  const { relationType, direction, cell } = parseCell(values.cell);
  const row = String(values.row ?? "");
  const searchable = (objectTypeOf(outline, row)?.attributes ?? []).filter(
    (item) => outline.attributeTypes.find((type) => type.key === item.attributeType)?.features.searchable === true,
  );
  return {
    relationTypeKey: relationType,
    direction,
    rowObjectTypeKey: row,
    columnObjectTypeKey: String(values.column ?? ""),
    cellObjectTypeKey: cell,
    rowColumns: list(values.rowColumns),
    columnLabelField: String(values.columnLabel ?? ""),
    cellFields: list(values.cellFields),
    searchFields: ["name", ...searchable.map((item) => item.attributeType)],
    cellActions: list(values.actions),
    pageSize: 20,
  };
}

/** The types the matrix needs that the application does not list yet. */
export function typesToList(outline: ModelDraftOutline, applicationKey: string, values: Values) {
  const listed = applicationOf(outline, applicationKey)?.objectTypeKeys ?? [];
  const needed = [String(values.row ?? ""), String(values.column ?? ""), parseCell(values.cell).cell];
  return [...new Set(needed)].filter((key) => key && !listed.includes(key));
}

const listing = (outline: ModelDraftOutline, applicationKey: string, values: Values): DraftOperation[] =>
  typesToList(outline, applicationKey, values).map((objectType) => ({
    kind: "listObjectType",
    applicationKey,
    objectType,
  }));

export function addMatrix(outline: ModelDraftOutline, applicationKey: string, values: Values): DraftOperation[] {
  const name = String(values.name ?? "");
  const taken = new Set((applicationOf(outline, applicationKey)?.views ?? []).map((item) => item.key));
  return [
    ...listing(outline, applicationKey, values),
    {
      kind: "addView",
      applicationKey,
      view: {
        key: keyFromLabel(name, taken),
        name,
        type: "relationMatrix",
        config: configOf(outline, values),
      },
    },
  ];
}

/** A matrix changed in one step: what it now needs listed, then each property that moved. */
export function changeMatrix(
  outline: ModelDraftOutline,
  applicationKey: string,
  view: string,
  values: Values,
): DraftOperation[] {
  const before = applicationOf(outline, applicationKey)?.views.find((item) => item.key === view)?.matrix ?? {};
  const set = (property: string, value: unknown): DraftOperation => ({
    kind: "setViewProperty",
    applicationKey,
    view,
    property,
    value,
  });
  const config = configOf(outline, values);
  const moved = Object.entries(config).filter(
    ([name, value]) =>
      // A search kept as it was unless the rows changed; so is the page size.
      (name !== "searchFields" || config.rowObjectTypeKey !== before.rowObjectTypeKey) &&
      name !== "pageSize" &&
      JSON.stringify(value) !== JSON.stringify(before[name]),
  );
  return [
    ...listing(outline, applicationKey, values),
    set("name", String(values.name ?? "")),
    ...moved.map(([name, value]) => set(name, value)),
  ];
}

export type MatrixPreview = {
  title: string;
  rowColumns: string[];
  heading: string;
  cellFields: string[];
  columnType: string;
  listed: string[];
};

export function matrixPreview(outline: ModelDraftOutline, applicationKey: string, values: Values): MatrixPreview {
  const label = (options: { value: string; label: string }[], value: string) =>
    options.find((item) => item.value === value)?.label ?? value;
  return {
    title: String(values.name ?? ""),
    rowColumns: list(values.rowColumns).map((item) => label(rowColumnOptions(outline, values.row), item)),
    heading: label(columnLabelOptions(outline, values.column), String(values.columnLabel ?? "")),
    cellFields: list(values.cellFields).map((item) => label(cellFieldOptions(outline, values.cell), item)),
    columnType: typeName(outline, String(values.column ?? "")),
    listed: typesToList(outline, applicationKey, values).map((key) => typeName(outline, key)),
  };
}
