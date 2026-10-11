/**
 * The model editor's operations (0.10 A4a, D38): one descriptor per menu action over the A2 kinds
 * (API.md § Kinds), naming the element it acts on, the fields its dialog asks for and the request it
 * sends. One dialog renders every descriptor (`OperationDialog`), so a kind gains a menu entry here,
 * never a component. The view and panel verbs are A4b's; `replaceModel` and `restoreElements` are
 * the server's own.
 *
 * A draft-only kind on an element of the base release stays listed, marked as needing a migration;
 * choosing it sends the request and the server's refusal says what it would affect (D39).
 */

import type { DraftOperation, ModelDraftOutline } from "@/types";
import type { ActionMenuItem } from "@/ui/ActionMenu";
import type { IconName } from "@/ui/Icon";
import { cleaned, type Candidates, type End } from "@/features/model-editor/candidates";
import {
  applicationsOf,
  attributeTypeOf,
  isReleased,
  keyFromLabel,
  keysOf,
  objectTypeOf,
  relationTypeOf,
  typeName,
} from "@/features/model-editor/outline";

/** What an operation acts on, named as operations name elements. */
export type OperationTarget =
  | { on: "draft" }
  | { on: "application"; applicationKey: string }
  | { on: "objectType"; objectType: string }
  | { on: "attribute"; objectType: string; attributeType: string }
  | { on: "attributeType"; attributeType: string }
  | { on: "relationType"; relationType: string }
  | { on: "relation"; relationType: string; from: string; to: string }
  | { on: "group"; applicationKey: string; group: string };

export type FieldValue = string | boolean | string[] | Candidates;
export type FieldValues = Record<string, FieldValue>;

export type OperationField = {
  name: string;
  label: string;
  /** Shown only while it returns true for the values entered so far. */
  when?: (values: FieldValues) => boolean;
  hint?: string;
} & (
  | { type: "text"; required?: boolean }
  | { type: "select"; options: { value: string; label: string }[]; required?: boolean }
  | { type: "checkbox" }
  | { type: "checkboxes"; options: { value: string; label: string }[] }
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
  build: (values: FieldValues, target: never, outline: ModelDraftOutline) => DraftOperation[];
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
    "label" | "title" | "available" | "draftOnly" | "confirm" | "fields" | "initial" | "build"
  > & {
    on: T["on"];
    label: string | ((target: T, outline: ModelDraftOutline) => string);
    title?: (target: T, outline: ModelDraftOutline) => string;
    available?: (target: T, outline: ModelDraftOutline) => boolean;
    draftOnly?: boolean | ((target: T, outline: ModelDraftOutline) => boolean);
    confirm?: (target: T, outline: ModelDraftOutline) => string;
    fields?: (target: T, outline: ModelDraftOutline) => OperationField[];
    initial?: (target: T, outline: ModelDraftOutline) => FieldValues;
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
  outline.objectTypes.filter((item) => item.key !== except).map((item) => ({ value: item.key, label: item.name }));

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
        ...containment.map((r) => ({ value: r.key, label: r.name })),
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
  { name: "to", label: "To", type: "select", options: typeOptions(outline), required: true },
  {
    name: "relationType",
    label: "Relation type",
    type: "select",
    options: [
      { value: NEW, label: "A new relation type" },
      ...outline.relationTypes.filter((r) => !r.containment).map((r) => ({ value: r.key, label: r.name })),
    ],
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

  // --- an object type ---
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
      { name: "from", label: "From", type: "select", options: typeOptions(o), required: true },
      { name: "to", label: "To", type: "select", options: typeOptions(o), required: true },
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
    available: (t, o) => !relationOf(t, o)?.containment,
    confirm: (t, o) =>
      `Stop allowing ${relationTypeOf(o, t.relationType)?.name ?? t.relationType} from ${typeName(o, t.from)} to ${typeName(o, t.to)}?`,
    build: (_, t) => [{ kind: "disallowRelation", relationType: t.relationType, from: t.from, to: t.to }],
  }),

  // --- a navigation group ---
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
      `Remove the group ${groupOf(t, o)?.label ?? t.group}? Its collections return to the top of the sidebar.`,
    build: (_, t) => [{ kind: "removeNavigationGroup", applicationKey: t.applicationKey, group: t.group }],
  }),
];

function relationOf(t: On<"relation">, o: ModelDraftOutline) {
  return o.relations.find((r) => r.relationType === t.relationType && r.from === t.from && r.to === t.to);
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
present("Change", "filter", ["relation-candidates"]);
present("Move", "arrow-right", ["type-move", "attribute-move"]);
present("Move", "list", ["type-group"]);
present("Move", "sort-ascending", ["attribute-up", "group-up"]);
present("Move", "sort-descending", ["attribute-down", "group-down"]);
present("Reshape", "swap", ["type-split"]);
present("Reshape", "replace", ["type-merge"]);
present("Reshape", "list", ["attribute-list"]);
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
      ? "Needs a migration: the server says what it affects"
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

/** The values a dialog starts with: the descriptor's, and each select's first option. */
export function initialValues(item: OperationSpec, target: OperationTarget, outline: ModelDraftOutline): FieldValues {
  const values: FieldValues = { ...(item.initial?.(target as never, outline) ?? {}) };
  for (const field of item.fields?.(target as never, outline) ?? []) {
    if (field.type === "select" && values[field.name] === undefined && field.required)
      values[field.name] = field.options[0]?.value ?? "";
  }
  return values;
}
