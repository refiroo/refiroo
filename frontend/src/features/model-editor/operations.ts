/**
 * The model editor's operations (0.10 A4a, D38): one descriptor per menu action over the A2 kinds
 * (API.md § Kinds), naming the element it acts on, the fields its dialog asks for and the request it
 * sends. One dialog renders every descriptor (`OperationDialog`), so a kind gains a menu entry here,
 * never a component. The view and panel verbs are A4b's; `replaceModel` and `restoreElements` are
 * the server's own.
 *
 * A draft-only kind on an element of the base release stays listed and marked; choosing it sends
 * the request, which always applies. Where stored data holds the element, or the key changes, the
 * step is marked as needing a migration, which installing the draft states (0.13 MG).
 */

import type {
  ConsumerDefinition,
  DraftOperation,
  ModelDraftOutline,
  OutlineRelation,
  OutlineRelationType,
} from "@/types";
import type { ChoiceOption } from "@/features/model-editor/ChoiceListField";
import type { ActionMenuItem } from "@/ui/ActionMenu";
import type { IconName } from "@/ui/Icon";
import { cleaned, type Candidates, type End } from "@/features/model-editor/candidates";
import {
  actionHint,
  actionOptions,
  addMatrix,
  cellFieldOptions,
  cellHint,
  cellOptions,
  changeMatrix,
  columnLabelOptions,
  columnOptions,
  followMatrix,
  matrixPreview,
  matrixValues,
  newMatrixValues,
  rowColumnOptions,
  rowOptions,
  type MatrixPreview,
} from "@/features/model-editor/matrixView";
import {
  addTable,
  attributeOptions,
  bindingOptions,
  endColumnOptions,
  followTable,
  newTableValues,
} from "@/features/model-editor/relationTableView";
import {
  exposesOf,
  FILTER_VERBS,
  filtersOf,
  fieldRow,
  filterReads,
  matchOptions,
  offers,
  parseList,
  parsePairs,
  pointer,
  relatedOf,
  ROLE_OPTIONS,
  relatedFieldOptions,
  relatedTypesOf,
  setField,
  sortOptions,
  sourceOptions,
  throughOptions,
  viaOptions,
  watchOptions,
  writeField,
} from "@/features/model-editor/consumer";
import {
  addView,
  changeView,
  followGrid,
  GRID_ROWS,
  gridBindingOptions,
  gridSearchOptions,
  gridSourceOptions,
  gridTargetOptions,
  gridValues,
  newGridValues,
  newTreeValues,
  tableTypeOptions,
  treeAvailabilityOptions,
  treeFieldOptions,
  treeRootOptions,
  treeValues,
  VIEW_KIND_OPTIONS,
} from "@/features/model-editor/viewKinds";
import {
  applicationsOf,
  attributeTypeOf,
  collectionsOf,
  entryName,
  entryRefId,
  groupEntries,
  groupOfEntry,
  isReleased,
  consumerApiOf,
  keyFromLabel,
  keysOf,
  matricesOf,
  objectTypeOf,
  relationTypeOf,
  sameName,
  typeLabel,
  typeName,
} from "@/features/model-editor/outline";

/** What an operation acts on, named as operations name elements. */
export type OperationTarget =
  | { on: "draft" }
  | { on: "application"; applicationKey: string }
  /** With the application it is read in, where a row of that application's types opened it. */
  | { on: "objectType"; objectType: string; applicationKey?: string }
  | { on: "view"; applicationKey: string; view: string }
  | { on: "attribute"; objectType: string; attributeType: string }
  | { on: "attributeType"; attributeType: string }
  | { on: "relationType"; relationType: string }
  | { on: "relation"; relationType: string; from: string; to: string }
  | { on: "group"; applicationKey: string; group: string }
  /** An entry of a navigation group: a collection (its type) or a relation matrix (its view). */
  | { on: "groupEntry"; applicationKey: string; group: string; collection?: string; view?: string }
  /** The Consumer APIs tab's ＋ (0.10 A4c). */
  | { on: "consumerApis" }
  /** A consumer API, with its definition as the draft holds it. */
  | { on: "consumerApi"; consumerApi: string; definition: ConsumerDefinition }
  /** A member or item of a consumer API definition: a field, a list, a filter, a rule… */
  | {
      on: "consumerItem";
      consumerApi: string;
      pointer: string;
      label: string;
      index: number;
      count: number;
      value: unknown;
      /** The definition it belongs to, where an operation offers what the definition holds. */
      definition?: ConsumerDefinition;
    };

export type FieldValue = string | boolean | string[] | Candidates;
export type FieldValues = Record<string, FieldValue>;

export type OperationField = {
  name: string;
  label: string;
  /** Shown only while it returns true for the values entered so far. */
  when?: (values: FieldValues) => boolean;
  /** May follow the values entered so far (what the chosen option means). */
  hint?: string | ((values: FieldValues) => string | undefined);
} & (
  | { type: "text"; required?: boolean }
  /** Options may follow the values chosen so far (a related record's fields after its block). */
  | { type: "select"; options: ChoiceOption[] | ((values: FieldValues) => ChoiceOption[]); required?: boolean }
  | { type: "checkbox" }
  /** A JSON document edited as text (a consumer API definition or a part of it). */
  | { type: "json"; required?: boolean }
  /** Several items chosen from a grouped picklist: in order (a field's sources) or as a set (a
   * filter's match fields); the options may follow the values chosen so far (0.10 A4c). */
  | {
      type: "choices";
      ordered: boolean;
      options: ChoiceOption[] | ((values: FieldValues) => ChoiceOption[]);
      /** What none chosen means. */
      empty?: string;
      required?: boolean;
    }
  /** Output names each reading a source picked from a list, as `output=source` (a related block). */
  | { type: "pairs"; options: ChoiceOption[] | ((values: FieldValues) => ChoiceOption[]); required?: boolean }
  | {
      type: "checkboxes";
      options: ChoiceOption[] | ((values: FieldValues) => ChoiceOption[]);
      required?: boolean;
      /** A search box over the options' names, with this placeholder. */
      search?: string;
    }
  /** Which records a relationship may choose (0.9 K7), per end; an end without a type offers its name. */
  | { type: "criteria"; ends: Record<End, { typeKey?: string; label: string }> }
);

export interface OperationSpec {
  id: string;
  on: OperationTarget["on"];
  /** The menu's words; may name the target ("Make required" or "Make optional"). */
  label: (target: never, outline: ModelDraftOutline) => string;
  /** The dialog's title; the label without its ellipsis when absent. */
  title?: (target: never, outline: ModelDraftOutline) => string;
  /** Whether the menu offers it for this element. */
  available?: (target: never, outline: ModelDraftOutline) => boolean;
  /** Whether it changes the element in a way that needs a migration once the element is released. */
  draftOnly?: (target: never, outline: ModelDraftOutline) => boolean;
  /** The question a removal asks instead of a form. */
  confirm?: (target: never, outline: ModelDraftOutline) => string;
  /** A move opens Move to… rather than a form (D40). */
  move?: "attribute" | "objectType";
  /** Applied straight from the menu, with neither form nor question. */
  direct?: boolean;
  fields?: (target: never, outline: ModelDraftOutline) => OperationField[];
  initial?: (target: never, outline: ModelDraftOutline) => FieldValues;
  /** The values after `changed` moved, for what depends on it beyond a select's own options. */
  follow?: (next: FieldValues, previous: FieldValues, changed: string, outline: ModelDraftOutline) => FieldValues;
  /** What the form will make, shown beside it. */
  preview?: (values: FieldValues, target: never, outline: ModelDraftOutline) => MatrixPreview | undefined;
  build: (values: FieldValues, target: never, outline: ModelDraftOutline) => DraftOperation[];
  /** The words of the dialog's send button for the values chosen so far ("Apply" when absent). */
  submit?: (values: FieldValues) => string;
}

export const VALUE_TYPES = [
  { value: "text", label: "Text" },
  { value: "longText", label: "Long text" },
  { value: "integer", label: "Whole number" },
  { value: "decimal", label: "Decimal number" },
  { value: "boolean", label: "Yes or no" },
  { value: "date", label: "Date" },
  { value: "dateTime", label: "Date and time" },
  { value: "json", label: "JSON" },
];

export const CARDINALITIES = [
  { value: "many-to-one", label: "Many to one" },
  { value: "one-to-many", label: "One to many" },
  { value: "one-to-one", label: "One to one" },
  { value: "many-to-many", label: "Many to many" },
];

export function valueTypeLabel(valueType: string | null | undefined): string {
  return VALUE_TYPES.find((item) => item.value === valueType)?.label ?? valueType ?? "Text";
}

export function cardinalityLabel(cardinality: string | null | undefined): string {
  return CARDINALITIES.find((item) => item.value === cardinality)?.label ?? cardinality ?? "Many to many";
}

const text = (values: FieldValues, name: string) => {
  const value = values[name];
  return typeof value === "string" ? value.trim() : typeof value === "boolean" ? String(value) : "";
};
const criteria = (values: FieldValues, name: string) => {
  const value = values[name];
  return value && typeof value === "object" && !Array.isArray(value) ? cleaned(value) : null;
};
const flag = (values: FieldValues, name: string) => values[name] === true;
const optional = (value: string) => (value ? value : undefined);
const NEW = "__new__";

function spec<T extends OperationTarget>(
  item: Omit<
    OperationSpec,
    "label" | "title" | "available" | "draftOnly" | "confirm" | "fields" | "initial" | "preview" | "build"
  > & {
    on: T["on"];
    label: string | ((target: T, outline: ModelDraftOutline) => string);
    title?: (target: T, outline: ModelDraftOutline) => string;
    available?: (target: T, outline: ModelDraftOutline) => boolean;
    draftOnly?: boolean | ((target: T, outline: ModelDraftOutline) => boolean);
    confirm?: (target: T, outline: ModelDraftOutline) => string;
    fields?: (target: T, outline: ModelDraftOutline) => OperationField[];
    initial?: (target: T, outline: ModelDraftOutline) => FieldValues;
    preview?: (values: FieldValues, target: T, outline: ModelDraftOutline) => MatrixPreview | undefined;
    build: (values: FieldValues, target: T, outline: ModelDraftOutline) => DraftOperation[];
  },
): OperationSpec {
  const { label, draftOnly } = item;
  return {
    ...item,
    label: (typeof label === "string" ? () => label : label) as OperationSpec["label"],
    draftOnly: (typeof draftOnly === "boolean" ? () => draftOnly : draftOnly) as OperationSpec["draftOnly"],
  } as OperationSpec;
}

type On<K extends OperationTarget["on"]> = Extract<OperationTarget, { on: K }>;

const applicationOptions = (outline: ModelDraftOutline) =>
  outline.applications.map((item) => ({ value: item.key, label: item.name }));

const typeOptions = (outline: ModelDraftOutline, except?: string) =>
  outline.objectTypes
    .filter((item) => item.key !== except)
    .map((item) => ({ value: item.key, label: typeLabel(outline, item.key) }));

/** What choosing a type that shares its name means: the types are separate, whatever they read. */
const typeHint = (outline: ModelDraftOutline, key: unknown) => {
  const count = typeof key === "string" ? sameName(outline, key).length : 0;
  return count > 1
    ? `${count} types have this name. They are separate types, each with its own records; this one's key is ${String(key)}.`
    : undefined;
};

const relationPairs = (outline: ModelDraftOutline, relationType: string) =>
  outline.relations.filter((item) => item.relationType === relationType);

const firstTwo = (names: string[]) =>
  names.length > 2 ? `${names.slice(0, 2).join(", ")} +${names.length - 2}` : names.join(", ");

/** A relation type's name with the types it stands between, which tell apart those sharing a name. */
function relationTypeLabel(outline: ModelDraftOutline, relationType: OutlineRelationType) {
  const pairs = relationPairs(outline, relationType.key);
  if (!pairs.length) return `${relationType.name}: not used yet`;
  const ends = (end: "from" | "to") => [...new Set(pairs.map((pair) => typeLabel(outline, pair[end])))];
  return `${relationType.name}: ${firstTwo(ends("from"))} → ${firstTwo(ends("to"))}`;
}

const pairRules = (outline: ModelDraftOutline, pair: OutlineRelation) => {
  const rules = [pair.required && "required", pair.uniquePer && `one per ${typeName(outline, pair.uniquePer)}`].filter(
    Boolean,
  );
  return rules.length ? ` (${rules.join(", ")})` : "";
};

/** What the chosen relation type already does, or what a new one leaves out of those towards `to`. */
function relationTypeHint(outline: ModelDraftOutline, values: FieldValues) {
  const chosen = String(values.relationType ?? "");
  const to = String(values.to ?? "");
  if (!chosen || chosen === NEW) {
    const towards = [
      ...new Set(
        outline.relations.filter((item) => item.to === to && !item.containment).map((item) => item.relationType),
      ),
    ].map((key) => relationTypeOf(outline, key)?.name ?? key);
    return towards.length
      ? `A new relation type stands apart from those already reaching ${typeName(outline, to)} (${firstTwo([...new Set(towards)])}): records and views of one do not include the other.`
      : undefined;
  }
  const relationType = relationTypeOf(outline, chosen);
  const pairs = relationPairs(outline, chosen);
  const used = pairs.map(
    (pair) => `${typeLabel(outline, pair.from)} → ${typeLabel(outline, pair.to)}${pairRules(outline, pair)}`,
  );
  const reverse = relationType?.reverseName ? `Reads "${relationType.reverseName}" in reverse. ` : "";
  const carried = pairs.some((pair) => pair.uniquePer) ? " A new pair does not take over the one-per rule." : "";
  return `${reverse}${used.length ? `Used for ${used.join("; ")}.` : "Not used by any types yet."}${carried}`;
}

/** The fields of a new type, its application chosen or fixed. */
function newTypeFields(outline: ModelDraftOutline, applicationKey?: string): OperationField[] {
  const containment = outline.relationTypes.filter((item) => item.containment);
  return [
    ...(applicationKey
      ? []
      : [
          {
            name: "applicationKey",
            label: "Application",
            type: "select" as const,
            options: applicationOptions(outline),
            required: true,
          },
        ]),
    { name: "name", label: "Name", type: "text", required: true },
    { name: "pluralName", label: "Plural name", type: "text", hint: "Optional; the name with an s when left empty" },
    {
      name: "parent",
      label: "Stands",
      type: "select",
      options: [
        { value: "", label: "At the top level" },
        ...typeOptions(outline).map((o) => ({ ...o, label: `Under ${o.label}` })),
      ],
    },
    {
      name: "relationType",
      label: "Containment relation",
      type: "select",
      options: [
        { value: NEW, label: "A new containment relation" },
        ...containment.map((r) => ({ value: r.key, label: relationTypeLabel(outline, r) })),
      ],
      when: (values) => Boolean(values.parent),
    },
    {
      name: "relationName",
      label: "Relation name (from the parent)",
      type: "text",
      required: true,
      when: (values) => Boolean(values.parent) && values.relationType === NEW,
    },
    {
      name: "reverseName",
      label: "Reverse name (from the child)",
      type: "text",
      required: true,
      when: (values) => Boolean(values.parent) && values.relationType === NEW,
    },
  ];
}

/** A `parent` parameter (D30) from the form: `null`, or the parent and its containment relation. */
function parentOf(values: FieldValues) {
  const parent = text(values, "parent");
  if (!parent) return null;
  const relation = text(values, "relationType");
  return {
    objectTypes: [parent],
    relationType:
      relation && relation !== NEW
        ? relation
        : { name: text(values, "relationName"), reverseName: text(values, "reverseName") },
  };
}

function addType(values: FieldValues, applicationKey: string): DraftOperation[] {
  return [
    {
      kind: "addObjectType",
      applicationKey,
      name: text(values, "name"),
      ...(text(values, "pluralName") ? { pluralName: text(values, "pluralName") } : {}),
      parent: parentOf(values),
    },
  ];
}

const groupFields = (outline: ModelDraftOutline, applicationKey?: string): OperationField[] => [
  ...(applicationKey
    ? []
    : [
        {
          name: "applicationKey",
          label: "Application",
          type: "select" as const,
          options: applicationOptions(outline),
          required: true,
        },
      ]),
  { name: "label", label: "Label", type: "text", required: true },
  { name: "collapsed", label: "Folded when the sidebar opens", type: "checkbox" },
];

const addGroup = (values: FieldValues, applicationKey: string): DraftOperation[] => [
  { kind: "addNavigationGroup", applicationKey, label: text(values, "label"), collapsed: flag(values, "collapsed") },
];

const attributeTypeFields = (): OperationField[] => [
  { name: "name", label: "Name", type: "text", required: true },
  { name: "valueType", label: "Value type", type: "select", options: VALUE_TYPES, required: true },
  {
    name: "features",
    label: "Features",
    type: "checkboxes",
    options: [
      { value: "searchable", label: "Searchable" },
      { value: "filterable", label: "Filterable" },
      { value: "sortable", label: "Sortable" },
      { value: "unique", label: "Unique" },
    ],
  },
];

const featuresOf = (values: FieldValues) =>
  Object.fromEntries((Array.isArray(values.features) ? values.features : []).map((name) => [name, true]));

const keyField: OperationField = { name: "key", label: "Key", type: "text", required: true };

const typeReleased = (target: { objectType: string }, outline: ModelDraftOutline) =>
  isReleased(objectTypeOf(outline, target.objectType)?.mark);

const bindingReleased = (target: On<"attribute">, outline: ModelDraftOutline) =>
  isReleased(
    objectTypeOf(outline, target.objectType)?.attributes.find((a) => a.attributeType === target.attributeType)?.mark,
  );

const binding = (target: On<"attribute">, outline: ModelDraftOutline) =>
  objectTypeOf(outline, target.objectType)?.attributes.find((a) => a.attributeType === target.attributeType);

const relationFields = (outline: ModelDraftOutline, from: string): OperationField[] => [
  {
    name: "to",
    label: "To",
    type: "select",
    options: typeOptions(outline),
    required: true,
    hint: (values) => typeHint(outline, values.to),
  },
  {
    name: "relationType",
    label: "Relation type",
    type: "select",
    // Those already reaching the chosen type come first: reusing one is usually what is meant.
    options: (values) => {
      const reaching = new Set(outline.relations.filter((r) => r.to === values.to).map((r) => r.relationType));
      return [
        { value: NEW, label: "A new relation type" },
        ...outline.relationTypes
          .filter((r) => !r.containment)
          .map((r) => ({
            value: r.key,
            label: relationTypeLabel(outline, r),
            reaches: reaching.has(r.key),
          }))
          .sort((a, b) => Number(b.reaches) - Number(a.reaches))
          .map(({ reaches, ...option }) => ({
            ...option,
            group: reaches ? `Already reaching ${typeName(outline, String(values.to))}` : "Other relation types",
          })),
      ];
    },
    hint: (values) => relationTypeHint(outline, values),
  },
  {
    name: "name",
    label: `Name (from ${typeName(outline, from)})`,
    type: "text",
    required: true,
    when: (v) => v.relationType === NEW,
  },
  { name: "reverseName", label: "Reverse name", type: "text", required: true, when: (v) => v.relationType === NEW },
  { name: "cardinality", label: "Cardinality", type: "select", options: CARDINALITIES, required: true },
  { name: "required", label: "Required", type: "checkbox" },
];

/** The relation a type starts to another, a new relation type added in the same step when asked. */
export function allowRelation(values: FieldValues, from: string, outline: ModelDraftOutline): DraftOperation[] {
  let relationType = text(values, "relationType");
  const operations: DraftOperation[] = [];
  if (!relationType || relationType === NEW) {
    const taken = keysOf(outline);
    relationType = keyFromLabel(text(values, "name"), taken);
    const reverseKey = keyFromLabel(text(values, "reverseName"), new Set([...taken, relationType]));
    operations.push({
      kind: "addRelationType",
      key: relationType,
      reverseKey,
      name: text(values, "name"),
      reverseName: text(values, "reverseName"),
    });
  }
  operations.push({
    kind: "allowRelation",
    relationType,
    from,
    to: text(values, "to"),
    cardinality: text(values, "cardinality") || "many-to-many",
    required: flag(values, "required"),
  });
  return operations;
}

const viewOf = (t: On<"view">, o: ModelDraftOutline) =>
  o.applications.find((item) => item.key === t.applicationKey)?.views.find((item) => item.key === t.view);

const matrixFields = (outline: ModelDraftOutline): OperationField[] => [
  {
    name: "row",
    label: "Rows",
    type: "select",
    options: rowOptions(outline),
    required: true,
    hint: "Types connected to another type that sits under a parent.",
  },
  {
    name: "cell",
    label: "Each cell shows",
    type: "select",
    options: (v) => cellOptions(outline, String(v.row ?? "")),
    required: true,
    hint: (v) => cellHint(outline, v),
  },
  {
    name: "column",
    label: "Columns",
    type: "select",
    options: (v) => columnOptions(outline, v.cell),
    required: true,
    hint: "One column per record of a type the cell's records sit under.",
  },
  {
    name: "columnLabel",
    label: "Column heading",
    type: "select",
    options: (v) => columnLabelOptions(outline, v.column),
    required: true,
  },
  {
    name: "cellFields",
    label: "Fields in a cell",
    type: "choices",
    ordered: true,
    options: (v) => cellFieldOptions(outline, v.cell),
    required: true,
  },
  {
    name: "rowColumns",
    label: "Row columns",
    type: "choices",
    ordered: true,
    options: (v) => rowColumnOptions(outline, v.row),
    required: true,
  },
  {
    name: "actions",
    label: "What people can do in a cell",
    type: "checkboxes",
    options: (v) => actionOptions(outline, v),
    hint: (v) => actionHint(outline, v),
  },
  { name: "name", label: "Name", type: "text", required: true },
];

const boundAttributes = (outline: ModelDraftOutline, typeKey: string) =>
  objectTypeOf(outline, typeKey)?.attributes ?? [];

const dateAttributes = (outline: ModelDraftOutline, typeKey: string) =>
  boundAttributes(outline, typeKey).filter((item) => item.valueType === "date");

/** The relationships allowed to a type that can place its records under a parent. */
function parentRelationOptions(outline: ModelDraftOutline, typeKey: string): ChoiceOption[] {
  const seen = new Set<string>();
  return outline.relations
    .filter((item) => item.to === typeKey && !seen.has(item.relationType) && seen.add(item.relationType))
    .map((item) => ({
      value: item.relationType,
      label: `${relationTypeOf(outline, item.relationType)?.name ?? item.relationType}, from ${typeName(outline, item.from)}`,
    }));
}

/** Several fields shown for one kind of view only. */
const onlyFor = (kind: string, fields: OperationField[]): OperationField[] =>
  fields.map((field) => ({ ...field, when: (values) => values.kind === kind && (field.when?.(values) ?? true) }));

const nameField: OperationField = { name: "name", label: "Name", type: "text", required: true };

const treeFields = (outline: ModelDraftOutline, applicationKey: string): OperationField[] => [
  nameField,
  {
    name: "roots",
    label: "Top of the tree",
    type: "checkboxes",
    options: treeRootOptions(outline, applicationKey),
    // A tree with no top would not be a valid model.
    required: true,
    hint: "Types a record can have without a parent. The tree shows the types under them that the application lists.",
  },
  {
    name: "label",
    label: "Each record reads",
    type: "select",
    options: (v) => treeFieldOptions(outline, applicationKey, v),
    required: true,
    hint: "A field every type in the tree has.",
  },
  {
    name: "secondary",
    label: "Second line",
    type: "select",
    options: (v) => [{ value: "", label: "None" }, ...treeFieldOptions(outline, applicationKey, v)],
  },
  {
    name: "order",
    label: "Records under a record are ordered by",
    type: "select",
    options: (v) => treeFieldOptions(outline, applicationKey, v),
    required: true,
  },
  {
    name: "availability",
    label: "Switch a record on and off with",
    type: "select",
    options: (v) => treeAvailabilityOptions(outline, applicationKey, v),
    hint: "A yes-or-no field every type in the tree has; people then switch records on and off in the tree.",
  },
];

const gridFields = (outline: ModelDraftOutline): OperationField[] => [
  nameField,
  {
    name: "binding",
    label: "Matches records through",
    type: "select",
    options: gridBindingOptions(outline),
    required: true,
    hint: "A relationship between two types, other than a containment.",
  },
  { name: "rows", label: "Rows are", type: "select", options: GRID_ROWS, required: true },
  {
    name: "sourceColumns",
    label: "Columns of a row",
    type: "choices",
    ordered: true,
    options: (v) => gridSourceOptions(outline, v),
    required: true,
  },
  {
    name: "targetColumns",
    label: "Columns of the matched record",
    type: "choices",
    ordered: true,
    options: (v) => gridTargetOptions(outline, v),
    required: true,
  },
  {
    name: "search",
    label: "Find a record to match by",
    type: "choices",
    ordered: false,
    options: (v) => gridSearchOptions(outline, v),
    required: true,
  },
];

/** The kinds of view that can be added now: each needs something of the model to stand on. */
const addViewKinds = (outline: ModelDraftOutline, applicationKey: string): ChoiceOption[] =>
  VIEW_KIND_OPTIONS.filter((option) =>
    option.value === "relationMatrix"
      ? rowOptions(outline).length > 0
      : option.value === "tree"
        ? treeRootOptions(outline, applicationKey).length > 0
        : option.value === "mappingGrid"
          ? gridBindingOptions(outline).length > 0
          : option.value === "relationTable"
            ? bindingOptions(outline).length > 0
            : outline.objectTypes.length > 0,
  );

const addViewFields = (outline: ModelDraftOutline, applicationKey: string): OperationField[] => [
  {
    name: "kind",
    label: "Kind of view",
    type: "select",
    options: addViewKinds(outline, applicationKey),
    required: true,
  },
  ...onlyFor("relationMatrix", matrixFields(outline)),
  ...onlyFor("table", [
    { name: "type", label: "Type", type: "select", options: tableTypeOptions(outline), required: true },
    {
      ...nameField,
      hint: "Columns, filters and sorting start from the type's attributes; change them in its preview.",
    },
  ]),
  ...onlyFor("tree", treeFields(outline, applicationKey)),
  ...onlyFor("mappingGrid", gridFields(outline)),
  ...onlyFor("relationTable", tableFields(outline)),
];

const LAYOUT_OPTIONS = [
  { value: "rows", label: "One row per relationship" },
  { value: "grid", label: "Grid: each record once, a column group per related record" },
];

const tableFields = (outline: ModelDraftOutline): OperationField[] => [
  {
    name: "binding",
    label: "Relationships",
    type: "select",
    options: bindingOptions(outline),
    required: true,
    hint: "One declared relationship between two types; its own attributes become columns.",
  },
  {
    name: "fromColumns",
    label: "Columns of the from record",
    type: "choices",
    ordered: true,
    options: (v) => endColumnOptions(outline, v.binding, "from"),
    required: true,
  },
  {
    name: "toColumns",
    label: "Columns of the to record",
    type: "choices",
    ordered: true,
    options: (v) => endColumnOptions(outline, v.binding, "to"),
    required: true,
  },
  {
    name: "attributeColumns",
    label: "Attributes of the relationship",
    type: "checkboxes",
    options: (v) => attributeOptions(outline, v.binding),
  },
  {
    name: "layout",
    label: "Layout",
    type: "select",
    options: LAYOUT_OPTIONS,
    hint: "A grid shows each from record once, with a column group for each to record.",
  },
  {
    name: "groupBy",
    label: "Head the rows by",
    type: "select",
    options: [
      { value: "", label: "Nothing: one list" },
      { value: "from", label: "The from record" },
      { value: "to", label: "The to record" },
    ],
  },
  { name: "name", label: "Name", type: "text", required: true },
];

export const RELATION_DEFAULTS: FieldValues = { relationType: NEW, cardinality: "many-to-one" };

export const OPERATIONS: OperationSpec[] = [
  // --- the draft (the Add menu) ---
  spec<On<"draft">>({
    id: "add-application",
    on: "draft",
    label: "Application…",
    title: () => "Add an application",
    fields: () => [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "description", label: "Description", type: "text" },
    ],
    build: (values) => [
      {
        kind: "addApplication",
        name: text(values, "name"),
        ...(text(values, "description") ? { description: text(values, "description") } : {}),
      },
    ],
  }),
  spec<On<"draft">>({
    id: "add-type",
    on: "draft",
    label: "Object type…",
    title: () => "Add an object type",
    available: (_, outline) => outline.applications.length > 0,
    fields: (_, outline) => newTypeFields(outline),
    initial: (_, outline) => ({ applicationKey: outline.applications[0]?.key ?? "", relationType: NEW }),
    build: (values) => addType(values, text(values, "applicationKey")),
  }),
  spec<On<"draft">>({
    id: "add-attribute-type",
    on: "draft",
    label: "Attribute type…",
    title: () => "Add an attribute type",
    fields: attributeTypeFields,
    initial: () => ({ valueType: "text" }),
    build: (values) => [
      {
        kind: "addAttributeType",
        name: text(values, "name"),
        valueType: text(values, "valueType"),
        features: featuresOf(values),
      },
    ],
  }),
  spec<On<"draft">>({
    id: "add-relation-type",
    on: "draft",
    label: "Relation type…",
    title: () => "Add a relation type",
    fields: () => [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "reverseName", label: "Reverse name", type: "text", required: true },
    ],
    build: (values) => [
      { kind: "addRelationType", name: text(values, "name"), reverseName: text(values, "reverseName") },
    ],
  }),
  spec<On<"draft">>({
    id: "add-group",
    on: "draft",
    label: "Navigation group…",
    title: () => "Add a navigation group",
    available: (_, outline) => outline.applications.length > 0,
    fields: (_, outline) => groupFields(outline),
    initial: (_, outline) => ({ applicationKey: outline.applications[0]?.key ?? "" }),
    build: (values) => addGroup(values, text(values, "applicationKey")),
  }),

  // --- an application ---
  spec<On<"application">>({
    id: "application-rename",
    on: "application",
    label: "Rename…",
    title: (t, o) => `Rename ${o.applications.find((a) => a.key === t.applicationKey)?.name ?? t.applicationKey}`,
    fields: () => [{ name: "name", label: "Name", type: "text", required: true }],
    initial: (t, o) => ({ name: o.applications.find((a) => a.key === t.applicationKey)?.name ?? "" }),
    build: (values, t) => [
      { kind: "setLabel", element: { applicationKey: t.applicationKey }, name: text(values, "name") },
    ],
  }),
  spec<On<"application">>({
    id: "application-key",
    on: "application",
    label: "Change key…",
    draftOnly: true,
    fields: () => [keyField],
    initial: (t) => ({ key: t.applicationKey }),
    build: (values, t) => [{ kind: "setKey", element: { applicationKey: t.applicationKey }, key: text(values, "key") }],
  }),
  spec<On<"application">>({
    id: "application-add-type",
    on: "application",
    label: "Add an object type…",
    fields: (t, o) => newTypeFields(o, t.applicationKey),
    initial: () => ({ relationType: NEW }),
    build: (values, t) => addType(values, t.applicationKey),
  }),
  spec<On<"application">>({
    id: "application-add-view",
    on: "application",
    label: "Add a view…",
    title: (t, o) =>
      `Add a view to ${o.applications.find((a) => a.key === t.applicationKey)?.name ?? t.applicationKey}`,
    fields: (t, o) => addViewFields(o, t.applicationKey),
    initial: (t, o) => ({
      kind: addViewKinds(o, t.applicationKey)[0]?.value ?? "table",
      ...newTableValues<FieldValues>(o),
      ...newMatrixValues<FieldValues>(o),
      ...(newTreeValues(o, t.applicationKey) as FieldValues),
      ...(newGridValues(o) as FieldValues),
      type: o.objectTypes[0]?.key ?? "",
      name: "",
    }),
    follow: (next, previous, changed, o) =>
      next.kind === "relationMatrix"
        ? followMatrix(o, next, previous, changed)
        : next.kind === "mappingGrid"
          ? (followGrid(next, changed) as FieldValues)
          : next.kind === "relationTable"
            ? followTable(o, next, previous, changed === "kind" ? "binding" : changed)
            : next,
    preview: (values, t, o) =>
      values.kind === "relationMatrix" ? matrixPreview(o, t.applicationKey, values) : undefined,
    build: (values, t, o) =>
      values.kind === "relationMatrix"
        ? addMatrix(o, t.applicationKey, values)
        : values.kind === "relationTable"
          ? addTable(o, t.applicationKey, values)
          : addView(o, t.applicationKey, String(values.kind), values),
  }),
  spec<On<"application">>({
    id: "application-list-type",
    on: "application",
    label: "List an existing type…",
    title: (t, o) =>
      `List an existing type in ${o.applications.find((a) => a.key === t.applicationKey)?.name ?? t.applicationKey}`,
    available: (t, o) =>
      o.objectTypes.some(
        (type) => !o.applications.find((a) => a.key === t.applicationKey)?.objectTypeKeys.includes(type.key),
      ),
    fields: (t, o) => [
      {
        name: "objectType",
        label: "Type",
        type: "select",
        options: typeOptions(o).filter(
          (option) => !o.applications.find((a) => a.key === t.applicationKey)?.objectTypeKeys.includes(option.value),
        ),
        required: true,
        hint: "Its records stay in the application they stand in. Here it can be used in a relation matrix.",
      },
    ],
    build: (values, t) => [
      { kind: "listObjectType", applicationKey: t.applicationKey, objectType: text(values, "objectType") },
    ],
  }),
  spec<On<"application">>({
    id: "application-add-group",
    on: "application",
    label: "Add a navigation group…",
    fields: (t, o) => groupFields(o, t.applicationKey),
    build: (values, t) => addGroup(values, t.applicationKey),
  }),
  spec<On<"application">>({
    id: "application-remove",
    on: "application",
    label: "Remove application",
    draftOnly: true,
    confirm: (t, o) =>
      `Remove ${o.applications.find((a) => a.key === t.applicationKey)?.name ?? t.applicationKey}, with the types only it lists?`,
    build: (_, t) => [{ kind: "removeApplication", applicationKey: t.applicationKey }],
  }),

  // --- a view of an application ---
  spec<On<"view">>({
    id: "view-rename",
    on: "view",
    label: "Rename…",
    title: (t, o) => `Rename ${viewOf(t, o)?.name ?? t.view}`,
    fields: () => [{ name: "name", label: "Name", type: "text", required: true }],
    initial: (t, o) => ({ name: viewOf(t, o)?.name ?? "" }),
    build: (values, t) => [
      {
        kind: "setViewProperty",
        applicationKey: t.applicationKey,
        view: t.view,
        property: "name",
        value: text(values, "name"),
      },
    ],
  }),
  spec<On<"view">>({
    id: "view-matrix-change",
    on: "view",
    label: "Change…",
    title: (t, o) => `Change ${viewOf(t, o)?.name ?? t.view}`,
    available: (t, o) => viewOf(t, o)?.type === "relationMatrix",
    fields: (_, o) => matrixFields(o),
    initial: (t, o) => matrixValues<FieldValues>(viewOf(t, o) ?? { name: t.view }),
    follow: (next, previous, changed, o) => followMatrix(o, next, previous, changed),
    preview: (values, t, o) => matrixPreview(o, t.applicationKey, values),
    build: (values, t, o) => changeMatrix(o, t.applicationKey, t.view, values),
  }),
  spec<On<"view">>({
    id: "view-tree-change",
    on: "view",
    label: "Change…",
    title: (t, o) => `Change ${viewOf(t, o)?.name ?? t.view}`,
    available: (t, o) => viewOf(t, o)?.type === "tree",
    fields: (t, o) => treeFields(o, t.applicationKey),
    initial: (t, o) => treeValues(viewOf(t, o) ?? { name: t.view }) as FieldValues,
    build: (values, t, o) => {
      const view = viewOf(t, o);
      return view ? changeView(o, t.applicationKey, view, values) : [];
    },
  }),
  spec<On<"view">>({
    id: "view-grid-change",
    on: "view",
    label: "Change…",
    title: (t, o) => `Change ${viewOf(t, o)?.name ?? t.view}`,
    available: (t, o) => viewOf(t, o)?.type === "mappingGrid",
    fields: (_, o) => gridFields(o),
    initial: (t, o) => gridValues(viewOf(t, o) ?? { name: t.view }) as FieldValues,
    follow: (next, _previous, changed) => followGrid(next, changed) as FieldValues,
    build: (values, t, o) => {
      const view = viewOf(t, o);
      return view ? changeView(o, t.applicationKey, view, values) : [];
    },
  }),
  spec<On<"view">>({
    id: "view-group",
    on: "view",
    label: "Move to group…",
    title: (t, o) => `Place ${viewOf(t, o)?.name ?? t.view} in a navigation group`,
    available: (t, o) =>
      viewOf(t, o)?.type === "relationMatrix" &&
      (o.applications.find((a) => a.key === t.applicationKey)?.navigation.groups.length ?? 0) > 0,
    fields: (t, o) => {
      const application = o.applications.find((a) => a.key === t.applicationKey);
      const rowType = viewOf(t, o)?.collection;
      return [
        {
          name: "group",
          label: "Group",
          type: "select",
          options: [
            { value: "", label: `No group: inside ${rowType ? typeName(o, rowType) : "its row type"}` },
            ...(application?.navigation.groups ?? []).map((g) => ({ value: g.key, label: g.label })),
          ],
        },
      ];
    },
    initial: (t, o) => {
      const application = o.applications.find((a) => a.key === t.applicationKey);
      const group = application && groupOfEntry(application, { kind: "matrix", key: t.view });
      return { group: group?.key ?? "" };
    },
    build: (values, t) => [
      { kind: "placeCollection", applicationKey: t.applicationKey, view: t.view, group: text(values, "group") || null },
    ],
  }),
  spec<On<"view">>({
    id: "view-remove",
    on: "view",
    label: "Remove view",
    available: (t, o) => viewOf(t, o)?.type !== "relationMatrix",
    confirm: (t, o) => `Remove ${viewOf(t, o)?.name ?? t.view}? Types only it needed stop being listed here.`,
    build: (_, t) => [{ kind: "removeView", applicationKey: t.applicationKey, view: t.view, unlist: true }],
  }),
  spec<On<"view">>({
    id: "view-table-layout",
    on: "view",
    label: "Layout…",
    title: (t, o) => `Layout of ${viewOf(t, o)?.name ?? t.view}`,
    available: (t, o) => viewOf(t, o)?.type === "relationTable",
    fields: () => [{ name: "layout", label: "Layout", type: "select", options: LAYOUT_OPTIONS, required: true }],
    initial: (t, o) => ({
      layout: (viewOf(t, o)?.config as { layout?: string } | undefined)?.layout === "grid" ? "grid" : "rows",
    }),
    build: (values, t) => [
      {
        kind: "setViewProperty",
        applicationKey: t.applicationKey,
        view: t.view,
        property: "layout",
        value: text(values, "layout") === "grid" ? "grid" : "rows",
      },
    ],
  }),
  spec<On<"view">>({
    id: "view-table-remove",
    on: "view",
    label: "Remove relationships table",
    available: (t, o) => viewOf(t, o)?.type === "relationTable",
    confirm: (t, o) => `Remove ${viewOf(t, o)?.name ?? t.view}? Types only it needed stop being listed here.`,
    build: (_, t) => [{ kind: "removeView", applicationKey: t.applicationKey, view: t.view, unlist: true }],
  }),
  spec<On<"view">>({
    id: "view-matrix-remove",
    on: "view",
    label: "Remove relation matrix",
    available: (t, o) => viewOf(t, o)?.type === "relationMatrix",
    confirm: (t, o) => `Remove ${viewOf(t, o)?.name ?? t.view}? Types only it needed stop being listed here.`,
    build: (_, t) => [{ kind: "removeView", applicationKey: t.applicationKey, view: t.view, unlist: true }],
  }),

  // --- an object type ---
  spec<On<"objectType">>({
    id: "type-unlist",
    on: "objectType",
    label: "Stop listing in this application",
    available: (t, o) =>
      o.applications.find((a) => a.key === t.applicationKey)?.unlistable.includes(t.objectType) ?? false,
    confirm: (t, o) =>
      `Stop listing ${typeName(o, t.objectType)} in ${o.applications.find((a) => a.key === t.applicationKey)?.name ?? ""}? Its records and other applications are not affected.`,
    build: (_, t) => [{ kind: "unlistObjectType", applicationKey: t.applicationKey, objectType: t.objectType }],
  }),
  spec<On<"objectType">>({
    id: "type-rename",
    on: "objectType",
    label: "Rename…",
    title: (t, o) => `Rename ${typeName(o, t.objectType)}`,
    fields: () => [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "pluralName", label: "Plural name", type: "text", required: true },
    ],
    initial: (t, o) => ({
      name: typeName(o, t.objectType),
      pluralName: objectTypeOf(o, t.objectType)?.pluralName ?? "",
    }),
    build: (values, t) => [
      {
        kind: "setLabel",
        element: { objectType: t.objectType },
        name: text(values, "name"),
        pluralName: text(values, "pluralName"),
      },
    ],
  }),
  spec<On<"objectType">>({
    id: "type-key",
    on: "objectType",
    label: "Change key…",
    draftOnly: true,
    fields: () => [keyField],
    initial: (t) => ({ key: t.objectType }),
    build: (values, t) => [{ kind: "setKey", element: { objectType: t.objectType }, key: text(values, "key") }],
  }),
  spec<On<"objectType">>({
    id: "type-move",
    on: "objectType",
    label: "Move to…",
    draftOnly: true,
    move: "objectType",
    build: () => [],
  }),
  spec<On<"objectType">>({
    id: "type-group",
    on: "objectType",
    label: "Move to group…",
    title: (t, o) => `Place ${typeName(o, t.objectType)} in a navigation group`,
    available: (t, o) => applicationsOf(o, t.objectType).some((a) => a.navigation.groups.length > 0),
    fields: (t, o) => {
      const apps = applicationsOf(o, t.objectType).filter((a) => a.navigation.groups.length > 0);
      return [
        ...(apps.length > 1
          ? [
              {
                name: "applicationKey",
                label: "Application",
                type: "select" as const,
                options: apps.map((a) => ({ value: a.key, label: a.name })),
                required: true,
              },
            ]
          : []),
        {
          name: "group",
          label: "Group",
          type: "select",
          options: [
            { value: "", label: "No group: the top of the sidebar" },
            ...apps.flatMap((a) =>
              a.navigation.groups.map((g) => ({
                value: `${a.key}\u0000${g.key}`,
                label: apps.length > 1 ? `${a.name} › ${g.label}` : g.label,
              })),
            ),
          ],
        },
      ];
    },
    initial: (t, o) => {
      const app = applicationsOf(o, t.objectType).find((a) => a.navigation.groups.length > 0);
      const group = app?.navigation.groups.find((g) => g.collections.includes(t.objectType));
      return { applicationKey: app?.key ?? "", group: group && app ? `${app.key}\u0000${group.key}` : "" };
    },
    build: (values, t) => {
      const [chosenApp, group] = text(values, "group").split("\u0000");
      const applicationKey = group ? chosenApp : text(values, "applicationKey");
      return [{ kind: "placeCollection", applicationKey, collection: t.objectType, group: group ?? null }];
    },
  }),
  spec<On<"objectType">>({
    id: "type-new-attribute",
    on: "objectType",
    label: "New attribute…",
    title: (t, o) => `New attribute on ${typeName(o, t.objectType)}`,
    fields: () => [...attributeTypeFields(), { name: "required", label: "Required", type: "checkbox" }],
    initial: () => ({ valueType: "text", features: ["searchable", "filterable", "sortable"] }),
    build: (values, t, o) => {
      const key = keyFromLabel(text(values, "name"), keysOf(o));
      return [
        {
          kind: "addAttributeType",
          key,
          name: text(values, "name"),
          valueType: text(values, "valueType"),
          features: featuresOf(values),
        },
        { kind: "attachAttribute", objectType: t.objectType, attributeType: key, required: flag(values, "required") },
      ];
    },
  }),
  spec<On<"objectType">>({
    id: "type-attach",
    on: "objectType",
    label: "Attach an existing attribute…",
    title: (t, o) => `Attach an attribute to ${typeName(o, t.objectType)}`,
    available: (t, o) => o.attributeTypes.some((a) => !a.boundBy.includes(t.objectType)),
    fields: (t, o) => [
      {
        name: "attributeType",
        label: "Attribute type",
        type: "select",
        required: true,
        options: o.attributeTypes
          .filter((a) => !a.boundBy.includes(t.objectType))
          .map((a) => ({
            value: a.key,
            label: a.boundBy.length ? `${a.name} (on ${a.boundBy.map((k) => typeName(o, k)).join(", ")})` : a.name,
          })),
      },
      { name: "required", label: "Required", type: "checkbox" },
    ],
    build: (values, t) => [
      {
        kind: "attachAttribute",
        objectType: t.objectType,
        attributeType: text(values, "attributeType"),
        required: flag(values, "required"),
      },
    ],
  }),
  spec<On<"objectType">>({
    id: "type-allow",
    on: "objectType",
    label: "Allow a relation…",
    title: (t, o) => `Allow a relation from ${typeName(o, t.objectType)}`,
    fields: (t, o) => relationFields(o, t.objectType),
    initial: () => RELATION_DEFAULTS,
    build: (values, t, o) => allowRelation(values, t.objectType, o),
  }),
  spec<On<"objectType">>({
    id: "type-split",
    on: "objectType",
    label: "Split…",
    title: (t, o) => `Split ${typeName(o, t.objectType)}`,
    draftOnly: true,
    available: (t, o) => (objectTypeOf(o, t.objectType)?.attributes.length ?? 0) > 0,
    fields: (t, o) => [
      { name: "name", label: "New type's name", type: "text", required: true },
      { name: "pluralName", label: "Plural name", type: "text" },
      {
        name: "attributes",
        label: "Attributes that move to it",
        type: "checkboxes",
        options: (objectTypeOf(o, t.objectType)?.attributes ?? []).map((a) => ({
          value: a.attributeType,
          label: a.name,
        })),
      },
      {
        name: "relationName",
        label: `Relation name (from ${typeName(o, t.objectType)})`,
        type: "text",
        required: true,
      },
      { name: "reverseName", label: "Reverse name", type: "text", required: true },
      { name: "cardinality", label: "Cardinality", type: "select", options: CARDINALITIES, required: true },
    ],
    initial: () => ({ cardinality: "many-to-one" }),
    build: (values, t) => [
      {
        kind: "splitObjectType",
        objectType: t.objectType,
        name: text(values, "name"),
        ...(text(values, "pluralName") ? { pluralName: text(values, "pluralName") } : {}),
        attributes: Array.isArray(values.attributes) ? values.attributes : [],
        relationType: { name: text(values, "relationName"), reverseName: text(values, "reverseName") },
        cardinality: text(values, "cardinality"),
      },
    ],
  }),
  spec<On<"objectType">>({
    id: "type-merge",
    on: "objectType",
    label: "Merge into…",
    title: (t, o) => `Merge ${typeName(o, t.objectType)} into another type`,
    draftOnly: true,
    available: (_, o) => o.objectTypes.length > 1,
    fields: (t, o) => [
      {
        name: "into",
        label: "Into",
        type: "select",
        options: typeOptions(o, t.objectType),
        required: true,
        hint: "Its attributes, relations and layout join the chosen type",
      },
    ],
    build: (values, t) => [{ kind: "mergeObjectTypes", into: text(values, "into"), from: t.objectType }],
  }),
  spec<On<"objectType">>({
    id: "type-remove",
    on: "objectType",
    label: "Remove type",
    draftOnly: true,
    confirm: (t, o) =>
      `Remove ${typeName(o, t.objectType)} with its views, detail page and the relations at either end?`,
    build: (_, t) => [{ kind: "removeObjectType", objectType: t.objectType }],
  }),

  // --- an attribute of a type ---
  spec<On<"attribute">>({
    id: "attribute-rename",
    on: "attribute",
    label: "Rename…",
    title: (t, o) => `Rename ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType}`,
    fields: (t, o) => [
      {
        name: "name",
        label: "Name",
        type: "text",
        required: true,
        hint:
          (attributeTypeOf(o, t.attributeType)?.boundBy.length ?? 0) > 1
            ? "The attribute type is shared; every type shows the new name"
            : undefined,
      },
    ],
    initial: (t, o) => ({ name: attributeTypeOf(o, t.attributeType)?.name ?? "" }),
    build: (values, t) => [
      { kind: "setLabel", element: { attributeType: t.attributeType }, name: text(values, "name") },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-key",
    on: "attribute",
    label: "Change key…",
    draftOnly: (t, o) => isReleased(attributeTypeOf(o, t.attributeType)?.mark),
    fields: () => [keyField],
    initial: (t) => ({ key: t.attributeType }),
    build: (values, t) => [{ kind: "setKey", element: { attributeType: t.attributeType }, key: text(values, "key") }],
  }),
  spec<On<"attribute">>({
    id: "attribute-move",
    on: "attribute",
    label: "Move to…",
    draftOnly: bindingReleased,
    move: "attribute",
    build: () => [],
  }),
  spec<On<"attribute">>({
    id: "attribute-required",
    on: "attribute",
    label: (t, o) => (binding(t, o)?.required ? "Make optional" : "Make required"),
    draftOnly: bindingReleased,
    direct: true,
    build: (_, t, o) => [
      {
        kind: "setAttributeBinding",
        objectType: t.objectType,
        attributeType: t.attributeType,
        required: !binding(t, o)?.required,
      },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-read-only",
    on: "attribute",
    label: (t, o) => (binding(t, o)?.readOnly ? "Make editable" : "Make read-only"),
    draftOnly: bindingReleased,
    direct: true,
    build: (_, t, o) => [
      {
        kind: "setAttributeBinding",
        objectType: t.objectType,
        attributeType: t.attributeType,
        readOnly: !binding(t, o)?.readOnly,
      },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-unique",
    on: "attribute",
    label: (t, o) => (binding(t, o)?.unique ? "Allow repeated values" : "Make unique"),
    draftOnly: (t, o) => !binding(t, o)?.unique && isReleased(attributeTypeOf(o, t.attributeType)?.mark),
    direct: true,
    build: (_, t, o) => [
      {
        kind: "setAttributeTypeFeatures",
        attributeType: t.attributeType,
        features: { unique: !binding(t, o)?.unique },
      },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-value-type",
    on: "attribute",
    label: "Value type…",
    title: (t, o) => `Value type of ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType}`,
    draftOnly: (t, o) => isReleased(attributeTypeOf(o, t.attributeType)?.mark),
    fields: () => [{ name: "valueType", label: "Value type", type: "select", options: VALUE_TYPES, required: true }],
    initial: (t, o) => ({ valueType: attributeTypeOf(o, t.attributeType)?.valueType ?? "text" }),
    build: (values, t) => [
      { kind: "setValueType", attributeType: t.attributeType, valueType: text(values, "valueType") },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-list",
    on: "attribute",
    label: "Turn into a list type…",
    title: (t, o) => `Turn ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType} into a list type`,
    draftOnly: bindingReleased,
    fields: (t, o) => [
      { name: "name", label: "List type's name", type: "text", required: true },
      { name: "pluralName", label: "Plural name", type: "text" },
      {
        name: "relationName",
        label: `Relation name (from ${typeName(o, t.objectType)})`,
        type: "text",
        required: true,
      },
      { name: "reverseName", label: "Reverse name", type: "text", required: true },
      {
        name: "candidates",
        label: "Which records may be chosen",
        type: "criteria",
        ends: {
          from: {
            typeKey: t.objectType,
            label: objectTypeOf(o, t.objectType)?.pluralName ?? typeName(o, t.objectType),
          },
          to: { label: "Records of the list" },
        },
      },
    ],
    initial: (t, o) => ({ name: attributeTypeOf(o, t.attributeType)?.name ?? "", candidates: {} }),
    build: (values, t, o) => {
      // The step names the list type and its relation itself, so the criteria can follow in it.
      const taken = keysOf(o);
      const listKey = keyFromLabel(text(values, "name"), taken);
      const relationKey = keyFromLabel(text(values, "relationName"), new Set([...taken, listKey]));
      const reverseKey = keyFromLabel(text(values, "reverseName"), new Set([...taken, listKey, relationKey]));
      const chosen = criteria(values, "candidates");
      return [
        {
          kind: "convertAttributeToListType",
          objectType: t.objectType,
          attributeType: t.attributeType,
          key: listKey,
          name: text(values, "name"),
          ...(text(values, "pluralName") ? { pluralName: text(values, "pluralName") } : {}),
          relationType: {
            key: relationKey,
            reverseKey,
            name: text(values, "relationName"),
            reverseName: text(values, "reverseName"),
          },
        },
        ...(chosen
          ? [
              {
                kind: "setRelationRule",
                relationType: relationKey,
                from: t.objectType,
                to: listKey,
                candidates: chosen,
              },
            ]
          : []),
      ];
    },
  }),
  spec<On<"attribute">>({
    id: "attribute-up",
    on: "attribute",
    label: "Move up",
    direct: true,
    available: (t, o) =>
      (objectTypeOf(o, t.objectType)?.attributes.findIndex((a) => a.attributeType === t.attributeType) ?? 0) > 0,
    build: (_, t, o) => [
      {
        kind: "setAttributeBinding",
        objectType: t.objectType,
        attributeType: t.attributeType,
        position:
          (objectTypeOf(o, t.objectType)?.attributes.findIndex((a) => a.attributeType === t.attributeType) ?? 1) - 1,
      },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-down",
    on: "attribute",
    label: "Move down",
    direct: true,
    available: (t, o) => {
      const attributes = objectTypeOf(o, t.objectType)?.attributes ?? [];
      return attributes.findIndex((a) => a.attributeType === t.attributeType) < attributes.length - 1;
    },
    build: (_, t, o) => [
      {
        kind: "setAttributeBinding",
        objectType: t.objectType,
        attributeType: t.attributeType,
        position:
          (objectTypeOf(o, t.objectType)?.attributes.findIndex((a) => a.attributeType === t.attributeType) ?? 0) + 1,
      },
    ],
  }),
  spec<On<"attribute">>({
    id: "attribute-detach",
    on: "attribute",
    label: (t, o) => `Detach from ${typeName(o, t.objectType)}`,
    draftOnly: bindingReleased,
    confirm: (t, o) =>
      `Detach ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType} from ${typeName(o, t.objectType)}? It leaves the type's views and panels too.`,
    build: (_, t) => [{ kind: "detachAttribute", objectType: t.objectType, attributeType: t.attributeType }],
  }),

  // --- an attribute type, wherever it is bound ---
  spec<On<"attributeType">>({
    id: "attribute-type-rename",
    on: "attributeType",
    label: "Rename…",
    fields: () => [{ name: "name", label: "Name", type: "text", required: true }],
    initial: (t, o) => ({ name: attributeTypeOf(o, t.attributeType)?.name ?? "" }),
    build: (values, t) => [
      { kind: "setLabel", element: { attributeType: t.attributeType }, name: text(values, "name") },
    ],
  }),
  spec<On<"attributeType">>({
    id: "attribute-type-key",
    on: "attributeType",
    label: "Change key…",
    draftOnly: true,
    fields: () => [keyField],
    initial: (t) => ({ key: t.attributeType }),
    build: (values, t) => [{ kind: "setKey", element: { attributeType: t.attributeType }, key: text(values, "key") }],
  }),
  spec<On<"attributeType">>({
    id: "attribute-type-features",
    on: "attributeType",
    label: "Features…",
    draftOnly: (t, o) =>
      isReleased(attributeTypeOf(o, t.attributeType)?.mark) && !attributeTypeOf(o, t.attributeType)?.features.unique,
    fields: () => [attributeTypeFields()[2]],
    initial: (t, o) => ({
      features: Object.entries(attributeTypeOf(o, t.attributeType)?.features ?? {})
        .filter(([, on]) => on === true)
        .map(([name]) => name),
    }),
    build: (values, t) => {
      const chosen = new Set(Array.isArray(values.features) ? values.features : []);
      return [
        {
          kind: "setAttributeTypeFeatures",
          attributeType: t.attributeType,
          features: Object.fromEntries(
            ["searchable", "filterable", "sortable", "unique"].map((name) => [name, chosen.has(name)]),
          ),
        },
      ];
    },
  }),
  spec<On<"attributeType">>({
    id: "attribute-type-value-type",
    on: "attributeType",
    label: "Value type…",
    draftOnly: true,
    fields: () => [{ name: "valueType", label: "Value type", type: "select", options: VALUE_TYPES, required: true }],
    initial: (t, o) => ({ valueType: attributeTypeOf(o, t.attributeType)?.valueType ?? "text" }),
    build: (values, t) => [
      { kind: "setValueType", attributeType: t.attributeType, valueType: text(values, "valueType") },
    ],
  }),
  spec<On<"attributeType">>({
    id: "attribute-type-attach",
    on: "attributeType",
    label: "Attach to a type…",
    title: (t, o) => `Attach ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType} to a type`,
    available: (t, o) => o.objectTypes.some((type) => !attributeTypeOf(o, t.attributeType)?.boundBy.includes(type.key)),
    fields: (t, o) => [
      {
        name: "objectType",
        label: "Type",
        type: "select",
        required: true,
        options: o.objectTypes
          .filter((type) => !attributeTypeOf(o, t.attributeType)?.boundBy.includes(type.key))
          .map((type) => ({ value: type.key, label: type.name })),
      },
      { name: "required", label: "Required", type: "checkbox" },
    ],
    build: (values, t) => [
      {
        kind: "attachAttribute",
        objectType: text(values, "objectType"),
        attributeType: t.attributeType,
        required: flag(values, "required"),
      },
    ],
  }),
  spec<On<"attributeType">>({
    id: "attribute-type-remove",
    on: "attributeType",
    label: "Remove attribute type",
    draftOnly: true,
    available: (t, o) => (attributeTypeOf(o, t.attributeType)?.boundBy.length ?? 0) === 0,
    confirm: (t, o) => `Remove ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType}? No type uses it.`,
    build: (_, t) => [{ kind: "removeAttributeType", attributeType: t.attributeType }],
  }),

  // --- a relation type ---
  spec<On<"relationType">>({
    id: "relation-type-rename",
    on: "relationType",
    label: "Rename…",
    fields: () => [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "reverseName", label: "Reverse name", type: "text", required: true },
    ],
    initial: (t, o) => ({
      name: relationTypeOf(o, t.relationType)?.name ?? "",
      reverseName: relationTypeOf(o, t.relationType)?.reverseName ?? "",
    }),
    build: (values, t) => [
      {
        kind: "setLabel",
        element: { relationType: t.relationType },
        name: text(values, "name"),
        reverseName: text(values, "reverseName"),
      },
    ],
  }),
  spec<On<"relationType">>({
    id: "relation-type-key",
    on: "relationType",
    label: "Change keys…",
    draftOnly: true,
    fields: () => [keyField, { name: "reverseKey", label: "Reverse key", type: "text" }],
    initial: (t, o) => ({ key: t.relationType, reverseKey: relationTypeOf(o, t.relationType)?.reverseKey ?? "" }),
    build: (values, t) => [
      {
        kind: "setKey",
        element: { relationType: t.relationType },
        key: text(values, "key"),
        reverseKey: optional(text(values, "reverseKey")),
      },
    ],
  }),
  spec<On<"relationType">>({
    id: "relation-type-allow",
    on: "relationType",
    label: "Allow between two types…",
    title: (t, o) => `Allow ${relationTypeOf(o, t.relationType)?.name ?? t.relationType} between two types`,
    available: (t, o) => !relationTypeOf(o, t.relationType)?.containment && o.objectTypes.length > 0,
    fields: (_, o) => [
      {
        name: "from",
        label: "From",
        type: "select",
        options: typeOptions(o),
        required: true,
        hint: (values) => typeHint(o, values.from),
      },
      {
        name: "to",
        label: "To",
        type: "select",
        options: typeOptions(o),
        required: true,
        hint: (values) => typeHint(o, values.to),
      },
      { name: "cardinality", label: "Cardinality", type: "select", options: CARDINALITIES, required: true },
      { name: "required", label: "Required", type: "checkbox" },
    ],
    initial: () => ({ cardinality: "many-to-many" }),
    build: (values, t) => [
      {
        kind: "allowRelation",
        relationType: t.relationType,
        from: text(values, "from"),
        to: text(values, "to"),
        cardinality: text(values, "cardinality"),
        required: flag(values, "required"),
      },
    ],
  }),
  spec<On<"relationType">>({
    id: "relation-type-remove",
    on: "relationType",
    label: "Remove relation type",
    draftOnly: true,
    // In use, it goes with the pairs that allow it, in one step (the user, after A4a).
    confirm: (t, o) => {
      const name = relationTypeOf(o, t.relationType)?.name ?? t.relationType;
      const pairs = o.relations
        .filter((r) => r.relationType === t.relationType)
        .map((r) => `${typeName(o, r.from)} → ${typeName(o, r.to)}`);
      return pairs.length
        ? `Remove ${name}, and stop allowing it between ${pairs.join(", ")}?`
        : `Remove ${name}? No type pair allows it.`;
    },
    build: (_, t, o) => [
      ...o.relations
        .filter((r) => r.relationType === t.relationType)
        .map((r) => ({ kind: "disallowRelation", relationType: r.relationType, from: r.from, to: r.to })),
      { kind: "removeRelationType", relationType: t.relationType },
    ],
  }),

  // --- what a type, an attribute type and a relationship hold beyond their names (0.13 ED) ---
  spec<On<"objectType">>({
    id: "type-display-attribute",
    on: "objectType",
    label: "Display attribute…",
    title: (t, o) => `Which attribute names a ${typeName(o, t.objectType)} record`,
    available: (t, o) => (objectTypeOf(o, t.objectType)?.attributes.length ?? 0) > 0,
    fields: (t, o) => [
      {
        name: "attribute",
        label: "Attribute",
        type: "select",
        options: [
          { value: "", label: "None: records are named by their name" },
          ...boundAttributes(o, t.objectType).map((item) => ({ value: item.attributeType, label: item.name })),
        ],
        hint: "Shown wherever a record of this type is named: lists, links and the record's title.",
      },
    ],
    initial: (t, o) => ({ attribute: objectTypeOf(o, t.objectType)?.displayAttribute ?? "" }),
    build: (values, t) => [
      {
        kind: "setObjectTypeProperty",
        objectType: t.objectType,
        property: "displayAttributeTypeKey",
        value: optional(text(values, "attribute")) ?? null,
      },
    ],
  }),
  spec<On<"objectType">>({
    id: "type-effective-period",
    on: "objectType",
    label: "Effective period…",
    title: (t, o) => `When a ${typeName(o, t.objectType)} record is in force`,
    available: (t, o) =>
      Boolean(objectTypeOf(o, t.objectType)?.effectivePeriod) || dateAttributes(o, t.objectType).length >= 2,
    fields: (t, o) => {
      const dates = dateAttributes(o, t.objectType).map((item) => ({ value: item.attributeType, label: item.name }));
      return [
        {
          name: "start",
          label: "Starts on",
          type: "select",
          options: [{ value: "", label: "None: records have no effective period" }, ...dates],
          hint: "A date attribute. A record is in force from this date (inclusive) up to the end date (exclusive); an empty date is open.",
        },
        {
          name: "end",
          label: "Ends on",
          type: "select",
          options: dates,
          required: true,
          when: (v) => Boolean(v.start),
        },
      ];
    },
    initial: (t, o) => ({
      start: objectTypeOf(o, t.objectType)?.effectivePeriod?.startAttributeTypeKey ?? "",
      end:
        objectTypeOf(o, t.objectType)?.effectivePeriod?.endAttributeTypeKey ??
        dateAttributes(o, t.objectType)[1]?.attributeType ??
        "",
    }),
    build: (values, t) => [
      {
        kind: "setObjectTypeProperty",
        objectType: t.objectType,
        property: "effectivePeriod",
        value: text(values, "start")
          ? { startAttributeTypeKey: text(values, "start"), endAttributeTypeKey: text(values, "end") }
          : null,
      },
    ],
  }),
  spec<On<"objectType">>({
    id: "type-at-least-one",
    on: "objectType",
    label: "At least one of…",
    title: (t, o) => `Attributes of ${typeName(o, t.objectType)} of which one must be filled`,
    available: (t, o) => (objectTypeOf(o, t.objectType)?.attributes.length ?? 0) > 0,
    fields: (t, o) => [
      {
        name: "attributes",
        label: "Attributes",
        type: "checkboxes",
        options: boundAttributes(o, t.objectType).map((item) => ({ value: item.attributeType, label: item.name })),
        hint: "A record needs a value in at least one of them. Records that have none now are listed when the release is installed.",
      },
    ],
    initial: (t, o) => ({ attributes: objectTypeOf(o, t.objectType)?.atLeastOneOf ?? [] }),
    build: (values, t) => [
      {
        kind: "setObjectTypeProperty",
        objectType: t.objectType,
        property: "atLeastOneOf",
        value: Array.isArray(values.attributes) && values.attributes.length ? values.attributes : null,
      },
    ],
  }),
  spec<On<"objectType">>({
    id: "type-parent-relations",
    on: "objectType",
    label: "Parent relationships…",
    title: (t, o) => `Relationships that place a ${typeName(o, t.objectType)} record under a parent`,
    draftOnly: true,
    available: (t, o) => parentRelationOptions(o, t.objectType).length > 0,
    fields: (t, o) => [
      {
        name: "relations",
        label: "Relationships",
        type: "checkboxes",
        options: parentRelationOptions(o, t.objectType),
        hint: "A relationship chosen here makes the records it points from the parents of this type's records, in trees and relation matrices.",
      },
    ],
    initial: (t, o) => ({ relations: objectTypeOf(o, t.objectType)?.parentRelationTypeKeys ?? [] }),
    build: (values, t) => [
      {
        kind: "setObjectTypeProperty",
        objectType: t.objectType,
        property: "parentRelationTypeKeys",
        value: Array.isArray(values.relations) && values.relations.length ? values.relations : null,
      },
    ],
  }),
  spec<On<"attributeType">>({
    id: "attribute-type-limits",
    on: "attributeType",
    label: "Minimum and maximum…",
    title: (t, o) => `Smallest and largest ${attributeTypeOf(o, t.attributeType)?.name ?? t.attributeType} accepted`,
    available: (t, o) => ["integer", "decimal"].includes(attributeTypeOf(o, t.attributeType)?.valueType ?? ""),
    fields: () => [
      { name: "minimum", label: "Minimum", type: "text", hint: "Leave empty for no minimum." },
      { name: "maximum", label: "Maximum", type: "text", hint: "Leave empty for no maximum." },
    ],
    initial: (t, o) => ({
      minimum: String(attributeTypeOf(o, t.attributeType)?.minimum ?? ""),
      maximum: String(attributeTypeOf(o, t.attributeType)?.maximum ?? ""),
    }),
    build: (values, t, o) => {
      const current = attributeTypeOf(o, t.attributeType);
      const set = (property: "minimum" | "maximum"): DraftOperation[] => {
        const entered = text(values, property);
        const value = entered === "" ? null : Number.isFinite(Number(entered)) ? Number(entered) : entered;
        return value === (current?.[property] ?? null)
          ? []
          : [{ kind: "setAttributeTypeProperty", attributeType: t.attributeType, property, value }];
      };
      // Loosening goes first so a new minimum above the old maximum is not refused on the way.
      const [minimum, maximum] = [set("minimum"), set("maximum")];
      return Number(text(values, "minimum")) > Number(current?.maximum ?? Infinity)
        ? [...maximum, ...minimum]
        : [...minimum, ...maximum];
    },
  }),
  spec<On<"relation">>({
    id: "relation-attributes",
    on: "relation",
    label: "Attributes of the relationship…",
    title: (t, o) =>
      `Attributes carried by ${relationTypeOf(o, t.relationType)?.name ?? t.relationType}: ${typeName(o, t.from)} → ${typeName(o, t.to)}`,
    draftOnly: (t, o) => isReleased(relationOf(t, o)?.mark),
    available: (t, o) => !relationOf(t, o)?.containment && o.attributeTypes.length > 0,
    fields: (_, o) => [
      {
        name: "attributes",
        label: "Attributes",
        type: "checkboxes",
        options: o.attributeTypes.map((item) => ({ value: item.key, label: item.name })),
        hint: "A value each relationship of this kind holds, such as a date or a remark.",
      },
    ],
    initial: (t, o) => ({ attributes: relationOf(t, o)?.attributeTypeKeys ?? [] }),
    build: (values, t) => [
      {
        kind: "setRelationRule",
        relationType: t.relationType,
        from: t.from,
        to: t.to,
        attributeTypeKeys: Array.isArray(values.attributes) ? values.attributes : [],
      },
    ],
  }),

  // --- a relation allowed between two types ---
  spec<On<"relation">>({
    id: "relation-rule",
    on: "relation",
    label: "Cardinality and required…",
    title: (t, o) =>
      `${relationTypeOf(o, t.relationType)?.name ?? t.relationType}: ${typeName(o, t.from)} → ${typeName(o, t.to)}`,
    draftOnly: (t, o) => isReleased(relationOf(t, o)?.mark),
    fields: () => [
      { name: "cardinality", label: "Cardinality", type: "select", options: CARDINALITIES, required: true },
      { name: "required", label: "Required", type: "checkbox" },
    ],
    initial: (t, o) => ({
      cardinality: relationOf(t, o)?.cardinality ?? "many-to-many",
      required: relationOf(t, o)?.required ?? false,
    }),
    build: (values, t) => [
      {
        kind: "setRelationRule",
        relationType: t.relationType,
        from: t.from,
        to: t.to,
        cardinality: text(values, "cardinality"),
        required: flag(values, "required"),
      },
    ],
  }),
  spec<On<"relation">>({
    id: "relation-required",
    on: "relation",
    label: (t, o) => (relationOf(t, o)?.required ? "Make optional" : "Make required"),
    draftOnly: (t, o) => isReleased(relationOf(t, o)?.mark),
    available: (t, o) => !relationOf(t, o)?.containment,
    direct: true,
    build: (_, t, o) => [
      {
        kind: "setRelationRule",
        relationType: t.relationType,
        from: t.from,
        to: t.to,
        required: !relationOf(t, o)?.required,
      },
    ],
  }),
  spec<On<"relation">>({
    id: "relation-candidates",
    on: "relation",
    label: "Which records may be chosen…",
    title: (t, o) => `Which records ${relationTypeOf(o, t.relationType)?.name ?? t.relationType} may choose`,
    fields: (t, o) => [
      {
        name: "candidates",
        label: "Criteria",
        type: "criteria",
        ends: {
          from: { typeKey: t.from, label: objectTypeOf(o, t.from)?.pluralName ?? typeName(o, t.from) },
          to: { typeKey: t.to, label: objectTypeOf(o, t.to)?.pluralName ?? typeName(o, t.to) },
        },
      },
    ],
    initial: (t, o) => ({ candidates: (relationOf(t, o)?.candidates ?? {}) as Candidates }),
    build: (values, t) => [
      {
        kind: "setRelationRule",
        relationType: t.relationType,
        from: t.from,
        to: t.to,
        candidates: criteria(values, "candidates"),
      },
    ],
  }),
  spec<On<"relation">>({
    id: "relation-remove",
    on: "relation",
    label: "Remove relation",
    draftOnly: (t, o) => isReleased(relationOf(t, o)?.mark),
    // A parent link too (the user, after A4a): the child type then stands only where its other
    // parents or the top level allow, and the draft says so until it is placed again.
    confirm: (t, o) => {
      const name = relationTypeOf(o, t.relationType)?.name ?? t.relationType;
      if (!relationOf(t, o)?.containment)
        return `Stop allowing ${name} from ${typeName(o, t.from)} to ${typeName(o, t.to)}?`;
      const child = objectTypeOf(o, t.to);
      const others = (child?.parents ?? []).filter((parent) => parent !== t.from);
      const after = others.length
        ? `${typeName(o, t.to)} stays under ${others.map((key) => typeName(o, key)).join(", ")}.`
        : child?.rootCreatable
          ? `${typeName(o, t.to)} then stands at the top level only.`
          : `${typeName(o, t.to)} then has no place to stand, and the draft shows an issue until you place it with Move to….`;
      return `Stop placing ${typeName(o, t.to)} under ${typeName(o, t.from)} (${name})? ${after}`;
    },
    build: (_, t) => [{ kind: "disallowRelation", relationType: t.relationType, from: t.from, to: t.to }],
  }),

  // --- a navigation group ---
  // --- an entry of a navigation group ---
  spec<On<"groupEntry">>({
    id: "entry-up",
    on: "groupEntry",
    label: "Move up",
    direct: true,
    available: (t, o) => entryIndex(t, o) > 0,
    build: (_, t, o) => [placeEntry(t, t.group, entryIndex(t, o) - 1)],
  }),
  spec<On<"groupEntry">>({
    id: "entry-down",
    on: "groupEntry",
    label: "Move down",
    direct: true,
    available: (t, o) => entryIndex(t, o) < entryCount(t, o) - 1,
    build: (_, t, o) => [placeEntry(t, t.group, entryIndex(t, o) + 1)],
  }),
  spec<On<"groupEntry">>({
    id: "entry-move",
    on: "groupEntry",
    label: "Move to another group…",
    title: (t, o) => `Move ${entryTitle(t, o)} to another group`,
    available: (t, o) => otherGroups(t, o).length > 0,
    fields: (t, o) => [
      {
        name: "group",
        label: "Group",
        type: "select",
        options: otherGroups(t, o).map((group) => ({ value: group.key, label: group.label })),
        required: true,
      },
    ],
    build: (values, t) => [placeEntry(t, text(values, "group"))],
  }),
  spec<On<"groupEntry">>({
    id: "entry-out",
    on: "groupEntry",
    label: "Take out of the group",
    direct: true,
    build: (_, t) => [placeEntry(t, null)],
  }),
  spec<On<"group">>({
    id: "group-add",
    on: "group",
    label: "Add to group…",
    title: (t, o) => `Add to ${groupOf(t, o)?.label ?? t.group}`,
    fields: (t, o) => [entriesField(o, t.applicationKey, () => t.group)],
    submit: (values) => `Add ${chosenEntries(values).length}`,
    build: (values, t) => placeEntries(t.applicationKey, t.group, values),
  }),
  spec<On<"application">>({
    id: "application-group-add",
    on: "application",
    label: "Add to a group…",
    title: () => "Add to a group",
    available: (t, o) => (o.applications.find((a) => a.key === t.applicationKey)?.navigation.groups.length ?? 0) > 0,
    fields: (t, o) => [
      {
        name: "group",
        label: "Group",
        type: "select",
        options: (o.applications.find((a) => a.key === t.applicationKey)?.navigation.groups ?? []).map((group) => ({
          value: group.key,
          label: group.label,
        })),
        required: true,
      },
      entriesField(o, t.applicationKey, (values) => text(values, "group")),
    ],
    submit: (values) => `Add ${chosenEntries(values).length}`,
    build: (values, t) => placeEntries(t.applicationKey, text(values, "group"), values),
  }),
  spec<On<"group">>({
    id: "group-rename",
    on: "group",
    label: "Rename…",
    fields: () => [{ name: "label", label: "Label", type: "text", required: true }],
    initial: (t, o) => ({ label: groupOf(t, o)?.label ?? "" }),
    build: (values, t) => [
      { kind: "setNavigationGroup", applicationKey: t.applicationKey, group: t.group, label: text(values, "label") },
    ],
  }),
  spec<On<"group">>({
    id: "group-fold",
    on: "group",
    label: (t, o) => (groupOf(t, o)?.collapsed ? "Start unfolded" : "Start folded"),
    direct: true,
    build: (_, t, o) => [
      {
        kind: "setNavigationGroup",
        applicationKey: t.applicationKey,
        group: t.group,
        collapsed: !groupOf(t, o)?.collapsed,
      },
    ],
  }),
  spec<On<"group">>({
    id: "group-key",
    on: "group",
    label: "Change key…",
    fields: () => [keyField],
    initial: (t) => ({ key: t.group }),
    build: (values, t) => [
      { kind: "setKey", element: { applicationKey: t.applicationKey, group: t.group }, key: text(values, "key") },
    ],
  }),
  spec<On<"group">>({
    id: "group-up",
    on: "group",
    label: "Move up",
    direct: true,
    available: (t, o) => groupIndex(t, o) > 0,
    build: (_, t, o) => [
      { kind: "setNavigationGroup", applicationKey: t.applicationKey, group: t.group, position: groupIndex(t, o) - 1 },
    ],
  }),
  spec<On<"group">>({
    id: "group-down",
    on: "group",
    label: "Move down",
    direct: true,
    available: (t, o) => groupIndex(t, o) < groupCount(t, o) - 1,
    build: (_, t, o) => [
      { kind: "setNavigationGroup", applicationKey: t.applicationKey, group: t.group, position: groupIndex(t, o) + 1 },
    ],
  }),
  spec<On<"group">>({
    id: "group-remove",
    on: "group",
    label: "Remove group",
    confirm: (t, o) =>
      `Remove the group ${groupOf(t, o)?.label ?? t.group}? Its collections return to the top of the sidebar` +
      (groupOf(t, o)?.entries.some((entry) => entry.view)
        ? ", and its relation matrices go back inside their row type's entry."
        : "."),
    build: (_, t) => [{ kind: "removeNavigationGroup", applicationKey: t.applicationKey, group: t.group }],
  }),
  ...CONSUMER_OPERATIONS(),
];

/** A JSON field's value, read when the step is built; a mistake is said before anything is sent. */
function json(values: FieldValues, name: string): unknown {
  try {
    return JSON.parse(text(values, name));
  } catch {
    throw new Error("The JSON cannot be read. Check its brackets, quotes and commas.");
  }
}

const number = (values: FieldValues, name: string) => {
  const value = text(values, name);
  return value ? Number(value) : undefined;
};

/** The consumer API operations (0.10 A4c, D51): the six kinds, each part named by its pointer. */
function CONSUMER_OPERATIONS(): OperationSpec[] {
  type Api = On<"consumerApi">;
  type Item = On<"consumerItem">;
  const set = (t: { consumerApi: string }, path: string, value: unknown): DraftOperation => ({
    kind: "setConsumerApiPart",
    consumerApi: t.consumerApi,
    pointer: path,
    value,
  });
  const insert = (t: Api, path: string, value: unknown, key?: string): DraftOperation => ({
    kind: "insertConsumerApiPart",
    consumerApi: t.consumerApi,
    pointer: path,
    ...(key !== undefined ? { key } : {}),
    value,
  });
  const exposed = (t: Api, o: ModelDraftOutline) =>
    exposesOf(t.definition).map((key) => ({ value: key, label: typeName(o, key) }));
  const objectOf = (t: Api) => (t.definition.object ?? {}) as Record<string, unknown>;
  const version = (t: Api) => Number(t.definition.contractVersion ?? 1);
  /** An earlier contract version the definition keeps (DF3): the item at `/earlierVersions/<n>`. */
  const isEarlierVersion = (t: Item) => /^\/earlierVersions\/\d+$/.test(t.pointer);
  const earlierVersion = (t: Item) => Number((t.value as Record<string, unknown>).contractVersion);
  return [
    spec<On<"consumerApis">>({
      id: "consumer-add",
      on: "consumerApis",
      label: "Consumer API…",
      title: () => "New consumer API",
      available: (_, o) => o.objectTypes.length > 0,
      fields: (_, o) => [
        { name: "name", label: "Name", type: "text", required: true },
        {
          name: "key",
          label: "Key",
          type: "text",
          hint: "Its name in URLs: /api/consumer/<key>/v1. Made from the name when left empty; fixed once released.",
        },
        {
          name: "exposes",
          label: "Types to expose",
          type: "checkboxes",
          hint: "The server starts it with the ID, the name, a field per attribute these types bind, Get by ID and a list per type.",
          options: o.objectTypes.map((type) => ({ value: type.key, label: type.name })),
        },
      ],
      build: (values) => [
        {
          kind: "addConsumerApi",
          name: text(values, "name"),
          ...(text(values, "key") ? { key: text(values, "key") } : {}),
          exposes: Array.isArray(values.exposes) ? values.exposes : [],
        },
      ],
    }),
    // --- a consumer API: its additions, then its own changes ---
    spec<Api>({
      id: "consumer-expose",
      on: "consumerApi",
      label: "Expose a type…",
      available: (t, o) => o.objectTypes.some((type) => !exposesOf(t.definition).includes(type.key)),
      fields: (t, o) => [
        {
          name: "objectType",
          label: "Type",
          type: "select",
          required: true,
          options: o.objectTypes
            .filter((type) => !exposesOf(t.definition).includes(type.key))
            .map((type) => ({ value: type.key, label: type.name })),
        },
      ],
      build: (values, t) => [insert(t, "/exposes", text(values, "objectType"))],
    }),
    spec<Api>({
      id: "consumer-add-field",
      on: "consumerApi",
      label: "Add field…",
      fields: (t, o) => [
        { name: "output", label: "Output name", type: "text", required: true, hint: "The name consumers read." },
        sourcesField(sourceOptions(o, exposesOf(t.definition))),
        { name: "role", label: "Role", type: "select", options: ROLE_OPTIONS },
      ],
      build: (values, t) => [
        insert(
          t,
          pointer("object", "fields"),
          writeField({ sources: chosen(values, "sources"), role: text(values, "role") }),
          text(values, "output"),
        ),
      ],
    }),
    spec<Api>({
      id: "consumer-object-extras",
      on: "consumerApi",
      label: "Parent, path and hierarchy…",
      fields: () => [
        { name: "parent", label: "Serve the parent (objectType, id, code, name)", type: "checkbox" },
        { name: "path", label: "Serve the path", type: "checkbox" },
        { name: "hierarchy", label: "Serve the hierarchy", type: "checkbox" },
      ],
      initial: (t) => ({
        parent: Boolean(objectOf(t).parent),
        path: Boolean(objectOf(t).path),
        hierarchy: Boolean(objectOf(t).hierarchy),
      }),
      build: (values, t) => {
        const current = objectOf(t);
        const keep = (name: string, written: unknown) =>
          flag(values, name) ? (current[name] ? current[name] : written) : null;
        return [
          set(t, "/object/parent", keep("parent", ["objectType", "id", "code", "name"])),
          set(t, "/object/path", keep("path", true)),
          set(t, "/object/hierarchy", keep("hierarchy", true)),
        ];
      },
    }),
    spec<Api>({
      id: "consumer-add-related",
      on: "consumerApi",
      label: "Add related…",
      available: (t, o) => viaOptions(o, exposesOf(t.definition)).length > 0,
      fields: (t, o) => [
        { name: "output", label: "Output name", type: "text", required: true },
        { name: "via", label: "Via", type: "select", required: true, options: viaOptions(o, exposesOf(t.definition)) },
        {
          name: "fields",
          label: "Fields",
          type: "pairs",
          required: true,
          hint: "Each field's name for consumers and what it reads from the related record.",
          options: (v) =>
            relatedFieldOptions(o, relatedTypesOf(o, text(v, "via"), exposesOf(t.definition)), [], {
              via: text(v, "via"),
              exposes: exposesOf(t.definition),
            }),
        },
      ],
      initial: () => ({ fields: ["name=name"] }),
      build: (values, t) => [
        insert(
          t,
          pointer("object", "related"),
          { via: text(values, "via"), fields: pairsOf(values, "fields") },
          text(values, "output"),
        ),
      ],
    }),
    spec<Api>({
      id: "consumer-add-list",
      on: "consumerApi",
      label: "Add list…",
      fields: (t, o) => [
        { name: "key", label: "Key", type: "text", required: true, hint: "Its name in URLs: …/lists/<key>." },
        { name: "of", label: "Of", type: "select", required: true, options: exposed(t, o) },
        {
          name: "within",
          label: "Within the filter",
          type: "select",
          options: [
            { value: "", label: "None: every record of the type" },
            ...filtersOf(t.definition, o).map((f) => ({ value: f.name, label: f.name })),
          ],
        },
        { name: "sortBy", label: "Sorted by", type: "select", options: (v) => sortOptions(o, text(v, "of")) },
      ],
      build: (values, t) => [
        insert(
          t,
          pointer("operations", "lists"),
          {
            of: text(values, "of"),
            ...(text(values, "within") ? { within: { filter: text(values, "within") } } : {}),
            ...(text(values, "sortBy") ? { sortBy: text(values, "sortBy") } : {}),
          },
          text(values, "key"),
        ),
      ],
    }),
    spec<Api>({
      id: "consumer-add-rule",
      on: "consumerApi",
      label: "Add XREF rule…",
      available: (t) => offers(t.definition, "xref"),
      fields: (t, o) => [
        {
          name: "field",
          label: "Field",
          type: "select",
          required: true,
          options: matchOptions(o, t.definition, { verb: "under", types: exposesOf(t.definition) }),
        },
        { name: "exact", label: "Exact weight", type: "text" },
        { name: "contains", label: "Contains weight", type: "text" },
      ],
      build: (values, t) => [
        insert(t, pointer("operations", "xref", "matchOn"), {
          field: text(values, "field"),
          ...(number(values, "exact") !== undefined ? { exact: number(values, "exact") } : {}),
          ...(number(values, "contains") !== undefined ? { contains: number(values, "contains") } : {}),
        }),
      ],
    }),
    spec<Api>({
      id: "consumer-add-through",
      on: "consumerApi",
      label: "Add a match through a related block…",
      available: (t) => offers(t.definition, "xref") && relatedOf(t.definition).length > 0,
      fields: (t, o) => [
        {
          name: "related",
          label: "Related block",
          type: "select",
          required: true,
          options: relatedOf(t.definition).map((row) => ({ value: row.output, label: row.output })),
        },
        {
          name: "field",
          label: "Field of the related record",
          type: "select",
          required: true,
          options: (v) => {
            const block = relatedOf(t.definition).find((row) => row.output === text(v, "related"));
            return relatedFieldOptions(o, relatedTypesOf(o, block?.via ?? "", exposesOf(t.definition)), [], {
              via: block?.via ?? "",
              exposes: exposesOf(t.definition),
            });
          },
        },
        { name: "exact", label: "Exact weight", type: "text" },
        { name: "contains", label: "Contains weight", type: "text" },
        {
          name: "preferTypes",
          label: "Prefer records of these types",
          type: "checkboxes",
          options: exposed(t, o),
          hint: "When several records match, one of these types is chosen first. None chosen: no preference.",
        },
      ],
      build: (values, t) => [
        insert(t, pointer("operations", "xref", "alsoMatchThrough"), {
          related: text(values, "related"),
          ...(chosen(values, "preferTypes").length ? { preferTypes: chosen(values, "preferTypes") } : {}),
          firstOf: [
            {
              field: text(values, "field"),
              ...(number(values, "exact") !== undefined ? { exact: number(values, "exact") } : {}),
              ...(number(values, "contains") !== undefined ? { contains: number(values, "contains") } : {}),
            },
          ],
        }),
      ],
    }),
    spec<Api>({
      id: "consumer-add-event",
      on: "consumerApi",
      label: "Add custom event…",
      fields: (t, o) => [
        { name: "key", label: "Key", type: "text", required: true },
        { name: "objectTypes", label: "Types", type: "checkboxes", options: exposed(t, o) },
        {
          name: "changes",
          label: "Changes",
          type: "checkboxes",
          options: ["created", "updated", "deleted"].map((value) => ({ value, label: value })),
        },
        {
          name: "watch",
          label: "Watches",
          type: "choices",
          ordered: false,
          options: watchOptions(t.definition),
          empty: "Any change to what consumers read.",
        },
      ],
      initial: () => ({ changes: ["created", "updated", "deleted"] }),
      build: (values, t) => {
        const watch = chosen(values, "watch");
        const event = {
          key: text(values, "key"),
          objectTypes: Array.isArray(values.objectTypes) ? values.objectTypes : [],
          changes: Array.isArray(values.changes) ? values.changes : [],
          ...(watch.length ? { watch: watchOf(t, watch) } : {}),
        };
        const events = (t.definition.operations as Record<string, unknown> | undefined)?.events;
        return events
          ? [insert(t, pointer("operations", "events", "custom"), event)]
          : [set(t, pointer("operations", "events"), { custom: [event] })];
      },
    }),
    spec<Api>({
      id: "consumer-add-filter",
      on: "consumerApi",
      label: "Add filter…",
      fields: (t, o) => [
        { name: "name", label: "Name", type: "text", required: true, hint: "Its query parameter: ?<name>=…" },
        { name: "verb", label: "Verb", type: "select", required: true, options: [...FILTER_VERBS] },
        {
          name: "types",
          label: "Types",
          type: "checkboxes",
          when: (v) => v.verb === "under" || v.verb === "linkedTo",
          options: o.objectTypes.map((type) => ({ value: type.key, label: type.name })),
        },
        {
          name: "through",
          label: "Through",
          type: "choices",
          ordered: false,
          when: (v) => v.verb === "linkedTo",
          options: throughOptions(t.definition),
        },
        {
          name: "related",
          label: "Related block",
          type: "select",
          when: (v) => v.verb === "onRelated",
          options: relatedOf(t.definition).map((row) => ({ value: row.output, label: row.output })),
        },
        {
          name: "matchOn",
          label: "Matches on",
          type: "choices",
          ordered: false,
          when: (v) => v.verb !== "byType",
          options: (v) => matchOptions(o, t.definition, readsOf(v)),
          empty: "The defaults: id, code and name.",
        },
        {
          name: "options",
          label: "Options",
          type: "checkboxes",
          when: (v) => v.verb === "onRelated",
          options: [
            { value: "keepOnlyMatching", label: "Keep only matching records" },
            { value: "scoreOnlyMatching", label: "Score only matching items" },
            { value: "crosswalk", label: "Crosswalk (to.<name>)" },
          ],
        },
      ],
      initial: () => ({ through: ["itself"] }),
      build: (values, t) => [insert(t, pointer("filters"), filterOf(values), text(values, "name"))],
    }),
    spec<Api>({
      id: "consumer-rename",
      on: "consumerApi",
      label: "Rename…",
      fields: () => [{ name: "name", label: "Name", type: "text", required: true }],
      initial: (t) => ({ name: String(t.definition.name ?? "") }),
      build: (values, t) => [set(t, "/name", text(values, "name"))],
    }),
    spec<Api>({
      id: "consumer-describe",
      on: "consumerApi",
      label: "Describe…",
      fields: () => [
        { name: "description", label: "Description", type: "text", hint: "Carried into its OpenAPI document." },
      ],
      initial: (t) => ({ description: String(t.definition.description ?? "") }),
      build: (values, t) => [set(t, "/description", text(values, "description") || null)],
    }),
    spec<Api>({
      id: "consumer-raise",
      on: "consumerApi",
      label: (t) => `Raise contract version to ${version(t) + 1}`,
      direct: true,
      // The previous version stays served beside the new one (DF-D1).
      build: (_, t) => [{ kind: "raiseConsumerApiVersion", consumerApi: t.consumerApi }],
    }),
    spec<Api>({
      id: "consumer-raise-drop",
      on: "consumerApi",
      label: (t) => `Raise to ${version(t) + 1} and stop serving ${version(t)}`,
      confirm: (t) =>
        `Stop serving version ${version(t)} of ${String(t.definition.name ?? t.consumerApi)}? Once the draft is active, its consumers of version ${version(t)} get 404.`,
      build: (_, t) => [{ kind: "raiseConsumerApiVersion", consumerApi: t.consumerApi, keep: false }],
    }),
    spec<Api>({
      id: "consumer-key",
      on: "consumerApi",
      label: "Change key…",
      fields: () => [
        {
          ...keyField,
          hint: "A released API's consumers get 404 under the old key once this is active.",
        },
      ],
      initial: (t) => ({ key: t.consumerApi }),
      build: (values, t) => [set(t, "/key", text(values, "key"))],
    }),
    spec<Api>({
      id: "consumer-json",
      on: "consumerApi",
      label: "Edit as JSON…",
      title: (t) => `Edit ${String(t.definition.name ?? t.consumerApi)} as JSON`,
      fields: () => [{ name: "json", label: "Definition", type: "json", required: true, hint: "Applied as one step." }],
      initial: (t) => ({ json: JSON.stringify(t.definition, null, 2) }),
      build: (values, t) => [set(t, "", json(values, "json"))],
    }),
    spec<Api>({
      id: "consumer-remove",
      on: "consumerApi",
      label: "Remove consumer API",
      confirm: (t) =>
        `Remove ${String(t.definition.name ?? t.consumerApi)}? Once the draft is active, its consumers get 404 from /api/consumer/${t.consumerApi}.`,
      build: (_, t) => [{ kind: "removeConsumerApi", consumerApi: t.consumerApi }],
    }),
    // --- a member or item of a definition ---
    spec<Item>({
      id: "consumer-item-up",
      on: "consumerItem",
      label: "Move up",
      direct: true,
      available: (t) => t.index > 0,
      build: (_, t) => [
        { kind: "moveConsumerApiPart", consumerApi: t.consumerApi, pointer: t.pointer, position: t.index - 1 },
      ],
    }),
    spec<Item>({
      id: "consumer-item-down",
      on: "consumerItem",
      label: "Move down",
      direct: true,
      available: (t) => t.index < t.count - 1,
      build: (_, t) => [
        { kind: "moveConsumerApiPart", consumerApi: t.consumerApi, pointer: t.pointer, position: t.index + 1 },
      ],
    }),
    spec<Item>({
      id: "consumer-field-sources",
      on: "consumerItem",
      label: "Sources…",
      title: (t) => `Sources of ${t.label}`,
      available: (t) => isField(t) && fieldOf(t).role !== "id",
      fields: (t, o) => {
        const exposes = consumerApiOf(o, t.consumerApi)?.exposes.map((item) => item.objectType) ?? [];
        return [sourcesField(sourceOptions(o, exposes, fieldOf(t).sources))];
      },
      initial: (t) => ({ sources: fieldOf(t).sources }),
      build: (values, t) => setField(t.consumerApi, fieldOf(t), { sources: chosen(values, "sources") }),
    }),
    spec<Item>({
      id: "consumer-through-prefer",
      on: "consumerItem",
      label: "Preferred types…",
      title: (t) => `Types preferred by ${t.label}`,
      available: (t) => /^\/operations\/xref\/alsoMatchThrough\/\d+$/.test(t.pointer),
      fields: (t, o) => [
        {
          name: "preferTypes",
          label: "Prefer records of these types",
          type: "checkboxes",
          options: exposesOf(t.definition ?? {}).map((key) => ({ value: key, label: typeName(o, key) })),
          hint: "When several records match, one of these types is chosen first. None chosen: no preference.",
        },
      ],
      initial: (t) => ({ preferTypes: listOf(t.value, "preferTypes") }),
      build: (values, t) => [
        {
          kind: "setConsumerApiPart",
          consumerApi: t.consumerApi,
          pointer: `${t.pointer}/preferTypes`,
          value: chosen(values, "preferTypes").length ? chosen(values, "preferTypes") : null,
        },
      ],
    }),
    spec<Item>({
      id: "consumer-filter-match",
      on: "consumerItem",
      label: "Matches on…",
      title: (t) => `What ${t.label} matches on`,
      available: (t) => /^\/filters\/[^/]+$/.test(t.pointer) && filterReads(t.value).verb !== "byType",
      fields: (t, o) => [
        {
          name: "matchOn",
          label: "Matches on",
          type: "choices",
          ordered: false,
          options: matchOptions(o, t.definition ?? {}, filterReads(t.value), listOf(t.value, "matchOn")),
          empty: "The defaults: id, code and name.",
        },
      ],
      initial: (t) => ({ matchOn: listOf(t.value, "matchOn") }),
      build: (values, t) => {
        const fields = chosen(values, "matchOn");
        return [set(t, `${t.pointer}/matchOn`, fields.length ? fields : null)];
      },
    }),
    spec<Item>({
      id: "consumer-related-fields",
      on: "consumerItem",
      label: "Fields…",
      title: (t) => `Fields of ${t.label}`,
      available: (t) => /^\/object\/related\/[^/]+$/.test(t.pointer),
      fields: (t, o) => {
        const via = String((t.value as { via?: unknown } | null)?.via ?? "");
        const exposes = consumerApiOf(o, t.consumerApi)?.exposes.map((item) => item.objectType) ?? [];
        const current = Object.values(fieldsMapOf(t.value));
        return [
          {
            name: "fields",
            label: "Fields",
            type: "pairs",
            required: true,
            hint: "Each field's name for consumers and what it reads from the related record.",
            options: relatedFieldOptions(o, relatedTypesOf(o, via, exposes), current, { via, exposes }),
          },
        ];
      },
      initial: (t) => ({
        fields: Object.entries(fieldsMapOf(t.value)).map(([output, source]) => `${output}=${source}`),
      }),
      build: (values, t) => [set(t, `${t.pointer}/fields`, pairsOf(values, "fields"))],
    }),
    spec<Item>({
      id: "consumer-item-json",
      on: "consumerItem",
      label: "Edit as JSON…",
      title: (t) => `Edit ${t.label} as JSON`,
      fields: () => [{ name: "json", label: "Value", type: "json", required: true }],
      initial: (t) => ({ json: JSON.stringify(t.value, null, 2) }),
      build: (values, t) => [set(t, t.pointer, json(values, "json"))],
    }),
    spec<Item>({
      id: "consumer-version-sunset",
      on: "consumerItem",
      label: "Set sunset day…",
      title: (t) => `Sunset of version ${earlierVersion(t)}`,
      available: (t) => isEarlierVersion(t),
      fields: () => [
        {
          name: "sunset",
          label: "Sunset day",
          type: "text",
          hint: "Written YYYY-MM-DD, announced in the Sunset header. The engine serves the version until you stop it, whatever the day. Empty takes the announcement back.",
        },
      ],
      initial: (t) => ({ sunset: String((t.value as Record<string, unknown>).sunset ?? "") }),
      build: (values, t) => [
        {
          kind: "setConsumerApiSunset",
          consumerApi: t.consumerApi,
          version: earlierVersion(t),
          sunset: text(values, "sunset") || null,
        },
      ],
    }),
    spec<Item>({
      id: "consumer-version-stop",
      on: "consumerItem",
      label: "Stop serving",
      available: (t) => isEarlierVersion(t),
      confirm: (t) =>
        `Stop serving version ${earlierVersion(t)}? Once the draft is active, its consumers get 404 from /api/consumer/${t.consumerApi}/v${earlierVersion(t)}.`,
      build: (_, t) => [{ kind: "removeConsumerApiVersion", consumerApi: t.consumerApi, version: earlierVersion(t) }],
    }),
    spec<Item>({
      id: "consumer-item-remove",
      on: "consumerItem",
      label: (t) => `Remove ${t.label}`,
      confirm: (t) => `Remove ${t.label}? Undo puts it back.`,
      build: (_, t) => [{ kind: "removeConsumerApiPart", consumerApi: t.consumerApi, pointer: t.pointer }],
    }),
  ];
}

/** A consumer field's sources: chosen in order from what the exposed types offer (the user, A4c). */
function sourcesField(options: { value: string; label: string; group?: string }[]): OperationField {
  return {
    name: "sources",
    label: "Sources",
    type: "choices",
    ordered: true,
    required: true,
    options,
    hint: "Read in this order: the first that is not empty is served. Sources share one value type.",
  };
}

/** An ordered choice's items (a typed list when a test or an older client sends text). */
function chosen(values: FieldValues, name: string): string[] {
  const value = values[name];
  return Array.isArray(value) ? value : parseList(text(values, name));
}

const FIELD_POINTER = /^\/object\/fields\/([^/]+)$/;
const isField = (t: On<"consumerItem">) => FIELD_POINTER.test(t.pointer);
const fieldOf = (t: On<"consumerItem">) =>
  fieldRow((FIELD_POINTER.exec(t.pointer)?.[1] ?? "").replaceAll("~1", "/").replaceAll("~0", "~"), t.value, t.index);

/** A watch from the names typed: related blocks by their names, the rest output fields. */
function watchOf(t: On<"consumerApi">, names: string[]) {
  const related = new Set(relatedOf(t.definition).map((row) => row.output));
  const fields = names.filter((name) => !related.has(name));
  const blocks = names.filter((name) => related.has(name));
  return { ...(fields.length ? { fields } : {}), ...(blocks.length ? { related: blocks } : {}) };
}

/** What the filter being added reads, from the dialog's values. */
const readsOf = (values: FieldValues) => ({
  verb: text(values, "verb"),
  types: Array.isArray(values.types) ? values.types : [],
  related: text(values, "related") || undefined,
});

/** A related block's fields from a pairs field (`output=source`). */
function pairsOf(values: FieldValues, name: string): Record<string, string> {
  const value = values[name];
  return parsePairs(Array.isArray(value) ? value.join(", ") : text(values, name));
}

const listOf = (value: unknown, name: string): string[] => {
  const items = (value as Record<string, unknown> | null)?.[name];
  return Array.isArray(items) ? items.filter((item): item is string => typeof item === "string") : [];
};

const fieldsMapOf = (value: unknown): Record<string, string> => {
  const fields = (value as { fields?: unknown } | null)?.fields;
  return fields && typeof fields === "object" ? (fields as Record<string, string>) : {};
};

function filterOf(values: FieldValues): Record<string, unknown> {
  const verb = text(values, "verb");
  const matchOn = chosen(values, "matchOn");
  const types = Array.isArray(values.types) ? values.types : [];
  const options = Array.isArray(values.options) ? values.options : [];
  const match = matchOn.length ? { matchOn } : {};
  if (verb === "byType") return { byType: true };
  if (verb === "under") return { under: types, ...match };
  if (verb === "linkedTo") return { linkedTo: types, through: chosen(values, "through"), ...match };
  return {
    onRelated: text(values, "related"),
    ...match,
    ...Object.fromEntries(options.map((option) => [option, true])),
  };
}

function relationOf(t: On<"relation">, o: ModelDraftOutline) {
  return o.relations.find((r) => r.relationType === t.relationType && r.from === t.from && r.to === t.to);
}

const ENTRY_COLLECTION = "collection:";
const ENTRY_VIEW = "view:";

/** The entries chosen in the Add to group dialog, as `collection:<type>` and `view:<view>`. */
const chosenEntries = (values: FieldValues) =>
  Array.isArray(values.entries) ? values.entries.filter((item): item is string => typeof item === "string") : [];

function placeEntries(applicationKey: string, group: string, values: FieldValues): DraftOperation[] {
  return chosenEntries(values).map((entry) =>
    entry.startsWith(ENTRY_VIEW)
      ? { kind: "placeCollection", applicationKey, view: entry.slice(ENTRY_VIEW.length), group }
      : { kind: "placeCollection", applicationKey, collection: entry.slice(ENTRY_COLLECTION.length), group },
  );
}

/**
 * The checkbox list of the Add to group dialog: the application's collections and relation matrices
 * not already in the group, each with where it stands now, and where a chosen one moves from.
 */
function entriesField(
  outline: ModelDraftOutline,
  applicationKey: string,
  groupOf: (values: FieldValues) => string,
): OperationField {
  const application = outline.applications.find((item) => item.key === applicationKey);
  return {
    name: "entries",
    label: "Collections and relation matrices",
    type: "checkboxes",
    required: true,
    search: "Search collections and matrices",
    options: (values) => {
      if (!application) return [];
      const target = groupOf(values);
      const chosen = chosenEntries(values);
      const groupLabel = (key: string) =>
        application.navigation.groups.find((group) => group.key === key)?.label ?? key;
      const place = (entry: { kind: "collection" | "matrix"; key: string }, unplaced: string, id: string) => {
        const current = groupOfEntry(application, entry);
        if (current?.key === target) return undefined;
        if (!current) return unplaced;
        return chosen.includes(id) ? `Moves from ${groupLabel(current.key)}` : `In ${groupLabel(current.key)}`;
      };
      const options: ChoiceOption[] = [];
      for (const key of collectionsOf(application)) {
        const id = `${ENTRY_COLLECTION}${key}`;
        const note = place({ kind: "collection", key }, "Top of the sidebar", id);
        if (note) options.push({ value: id, label: typeName(outline, key), group: "Collections", note });
      }
      for (const view of matricesOf(application)) {
        const id = `${ENTRY_VIEW}${view.key}`;
        const row = view.collection ? typeName(outline, view.collection) : "its row type";
        const note = place({ kind: "matrix", key: view.key }, `Inside ${row}`, id);
        if (note) options.push({ value: id, label: view.name, group: "Relation matrices", note });
      }
      return options;
    },
  };
}

function entryApplication(t: On<"groupEntry">, o: ModelDraftOutline) {
  return o.applications.find((a) => a.key === t.applicationKey);
}

function entryRef(t: On<"groupEntry">) {
  return t.view
    ? ({ kind: "matrix", key: t.view } as const)
    : ({ kind: "collection", key: t.collection ?? "" } as const);
}

function entryIndex(t: On<"groupEntry">, o: ModelDraftOutline) {
  const application = entryApplication(t, o);
  return application
    ? groupEntries(application, t.group).findIndex((e) => entryRefId(e) === entryRefId(entryRef(t)))
    : -1;
}

function entryCount(t: On<"groupEntry">, o: ModelDraftOutline) {
  const application = entryApplication(t, o);
  return application ? groupEntries(application, t.group).length : 0;
}

function otherGroups(t: On<"groupEntry">, o: ModelDraftOutline) {
  return entryApplication(t, o)?.navigation.groups.filter((group) => group.key !== t.group) ?? [];
}

function entryTitle(t: On<"groupEntry">, o: ModelDraftOutline) {
  const application = entryApplication(t, o);
  return application ? entryName(o, application, entryRef(t)) : (t.view ?? t.collection ?? "the entry");
}

/** `placeCollection` for an entry: into `group` (at `position`), or out of its group when null. */
function placeEntry(t: On<"groupEntry">, group: string | null, position?: number): DraftOperation {
  return {
    kind: "placeCollection",
    applicationKey: t.applicationKey,
    ...(t.view ? { view: t.view } : { collection: t.collection }),
    group,
    ...(position === undefined ? {} : { position }),
  };
}

function groupsOf(t: On<"group">, o: ModelDraftOutline) {
  return o.applications.find((a) => a.key === t.applicationKey)?.navigation.groups ?? [];
}

function groupOf(t: On<"group">, o: ModelDraftOutline) {
  return groupsOf(t, o).find((g) => g.key === t.group);
}

function groupIndex(t: On<"group">, o: ModelDraftOutline) {
  return groupsOf(t, o).findIndex((g) => g.key === t.group);
}

function groupCount(t: On<"group">, o: ModelDraftOutline) {
  return groupsOf(t, o).length;
}

/** The operations the menu of an element offers, in menu order. */
export function operationsFor(target: OperationTarget, outline: ModelDraftOutline): OperationSpec[] {
  return OPERATIONS.filter((item) => item.on === target.on && (item.available?.(target as never, outline) ?? true));
}

export function operationById(id: string): OperationSpec | undefined {
  return OPERATIONS.find((item) => item.id === id);
}

/** Whether the element the operation acts on is released and the operation changes it as only a migration may. */
export function needsMigration(item: OperationSpec, target: OperationTarget, outline: ModelDraftOutline): boolean {
  if (!item.draftOnly?.(target as never, outline)) return false;
  switch (target.on) {
    case "application":
      return isReleased(outline.applications.find((a) => a.key === target.applicationKey)?.mark);
    case "objectType":
      return typeReleased(target, outline);
    case "attributeType":
      return isReleased(attributeTypeOf(outline, target.attributeType)?.mark);
    case "attribute":
    case "relation":
      // Their descriptors decide from the binding's or the attribute type's own mark.
      return true;
    case "relationType":
      return isReleased(relationTypeOf(outline, target.relationType)?.mark);
    default:
      return false;
  }
}

/** The menu's words for an operation on an element, with the migration it would need. */
/** How an operation shows in a menu: its glyph and the section it is listed under. */
const PRESENTATION: Record<string, { icon: IconName; section: string }> = {};
const present = (section: string, icon: IconName, ids: string[]) =>
  ids.forEach((id) => (PRESENTATION[id] = { icon, section }));
present("Add", "plus", [
  "add-application",
  "add-type",
  "add-attribute-type",
  "application-add-type",
  "type-new-attribute",
]);
present("Add", "mapping", ["add-relation-type", "type-allow"]);
present("Add", "list", ["add-group", "application-add-group"]);
present("Add", "link", ["type-attach", "attribute-type-attach"]);
present("Add", "mapping", ["relation-type-allow"]);
present("Change", "pencil", [
  "application-rename",
  "type-rename",
  "attribute-rename",
  "attribute-type-rename",
  "relation-type-rename",
  "group-rename",
]);
present("Change", "lock", [
  "application-key",
  "type-key",
  "attribute-key",
  "attribute-type-key",
  "relation-type-key",
  "group-key",
]);
present("Change", "toggle", ["attribute-required", "attribute-read-only", "attribute-unique", "group-fold"]);
present("Change", "type", ["attribute-value-type", "attribute-type-value-type"]);
present("Change", "sliders", ["attribute-type-features", "relation-rule"]);
present("Change", "toggle", ["relation-required"]);
present("Add", "plus", ["application-add-view"]);
present("Change", "sliders", [
  "type-display-attribute",
  "type-effective-period",
  "type-at-least-one",
  "type-parent-relations",
  "attribute-type-limits",
  "relation-attributes",
  "view-matrix-change",
  "view-tree-change",
  "view-grid-change",
]);
present("Remove", "trash", ["view-matrix-remove", "view-remove"]);
present("Change", "filter", ["relation-candidates"]);
present("Move", "arrow-right", ["type-move", "attribute-move"]);
present("Move", "list", ["type-group", "view-group"]);
present("Add", "plus", ["group-add", "application-group-add"]);
present("Order", "sort-ascending", ["entry-up"]);
present("Order", "sort-descending", ["entry-down"]);
present("Place", "list", ["entry-move"]);
present("Place", "arrow-left", ["entry-out"]);
present("Move", "sort-ascending", ["attribute-up", "group-up"]);
present("Move", "sort-descending", ["attribute-down", "group-down"]);
present("Reshape", "swap", ["type-split"]);
present("Reshape", "replace", ["type-merge"]);
present("Reshape", "list", ["attribute-list"]);
present("Add", "plus", [
  "consumer-add",
  "consumer-expose",
  "consumer-add-field",
  "consumer-add-related",
  "consumer-add-list",
  "consumer-add-rule",
  "consumer-add-through",
  "consumer-add-event",
  "consumer-add-filter",
]);
present("Change", "pencil", [
  "consumer-rename",
  "consumer-describe",
  "consumer-object-extras",
  "consumer-field-sources",
  "consumer-filter-match",
  "consumer-related-fields",
]);
present("Change", "number", ["consumer-raise", "consumer-raise-drop"]);
present("Change", "pencil", ["consumer-version-sunset"]);
present("Change", "pencil", ["consumer-through-prefer"]);
present("Change", "lock", ["consumer-key"]);
present("Change", "pencil", ["consumer-json", "consumer-item-json"]);
present("Move", "sort-ascending", ["consumer-item-up"]);
present("Move", "sort-descending", ["consumer-item-down"]);
present("Remove", "trash", ["consumer-remove", "consumer-item-remove", "consumer-version-stop"]);
present("Remove", "trash", [
  "application-remove",
  "type-remove",
  "attribute-detach",
  "attribute-type-remove",
  "relation-type-remove",
  "relation-remove",
  "group-remove",
]);

/** An element's operations as menu items: glyph, label, section, and the migration a released element would need (D39). */
export function menuItems(
  target: OperationTarget,
  outline: ModelDraftOutline,
  onAction: (item: OperationSpec) => void,
  { sections = true }: { sections?: boolean } = {},
): ActionMenuItem[] {
  return operationsFor(target, outline).map((item) => ({
    id: item.id,
    label: item.label(target as never, outline),
    icon: PRESENTATION[item.id]?.icon,
    section: sections ? PRESENTATION[item.id]?.section : undefined,
    description: needsMigration(item, target, outline)
      ? item.id.endsWith("-key")
        ? "Needs a migration when installed: integrations naming the key must change"
        : "Needs a migration when installed"
      : undefined,
    tone: item.confirm ? "danger" : "default",
    onAction: () => onAction(item),
  }));
}

/** The fields a dialog shows for the values entered so far. */
export function visibleFields(
  item: OperationSpec,
  target: OperationTarget,
  outline: ModelDraftOutline,
  values: FieldValues,
) {
  return (item.fields?.(target as never, outline) ?? []).filter((field) => field.when?.(values) ?? true);
}

/** The first required field left empty, or `undefined` when the form can be sent. */
export function missingField(
  item: OperationSpec,
  target: OperationTarget,
  outline: ModelDraftOutline,
  values: FieldValues,
) {
  return visibleFields(item, target, outline, values).find(
    (field) => "required" in field && field.required && !String(values[field.name] ?? "").trim(),
  );
}

/** A field's options for the values entered so far: they may follow an earlier choice. */
export function fieldOptions(
  field: Extract<OperationField, { options: unknown }>,
  values: FieldValues,
): ChoiceOption[] {
  return typeof field.options === "function" ? field.options(values) : field.options;
}

/** The values a dialog starts with: the descriptor's, and each select's first option. */
export function initialValues(item: OperationSpec, target: OperationTarget, outline: ModelDraftOutline): FieldValues {
  const values: FieldValues = { ...(item.initial?.(target as never, outline) ?? {}) };
  for (const field of item.fields?.(target as never, outline) ?? []) {
    if (field.type === "select" && values[field.name] === undefined && field.required)
      values[field.name] = fieldOptions(field, values)[0]?.value ?? "";
  }
  return values;
}
