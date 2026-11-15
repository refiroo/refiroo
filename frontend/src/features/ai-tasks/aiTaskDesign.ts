/**
 * The assistant's design in the words a steward reads (0.16 AP6): the model-draft operations as
 * what changes in the model and a profile source's columns in plain words. Unknown shapes read as what they are, never fail.
 */

import { record, text } from "@/lib/coerce";
import type { AiTask, AiTaskDesign, AiTaskDesignSource, AiTaskOperation, EngineModel } from "@/types";
import { shown } from "./aiTaskText";

/** Operations that change the model; `setRelease` only names the release. */
export const modelOperations = (design: AiTaskDesign) => design.operations.filter((op) => op.kind !== "setRelease");

/** Whether loading the design installs and activates a model change first. */
export const changesModel = (design: AiTaskDesign) => modelOperations(design).length > 0;

/** The model's names for keys: the active model's, then what the design adds; the key when there is none. */
export interface ModelNames {
  type: (key: unknown) => string;
  typePlural: (key: unknown) => string;
  attribute: (key: unknown) => string;
  /** The relationship name, read the other way when `incoming`. */
  relation: (key: unknown, direction?: string) => string;
}

export function modelNames(model: EngineModel | undefined, operations: AiTaskOperation[]): ModelNames {
  const types = new Map<string, { name: string; plural: string }>();
  const attributes = new Map<string, string>();
  const relations = new Map<string, string>();
  const reverses = new Map<string, string>();
  for (const type of model?.objectTypes ?? []) types.set(type.key, { name: type.name, plural: type.pluralName });
  for (const attribute of model?.attributeTypes ?? []) attributes.set(attribute.key, attribute.name);
  for (const relation of model?.relationTypes ?? []) {
    relations.set(relation.key, relation.name);
    reverses.set(relation.key, relation.reverseName);
  }
  for (const op of operations) {
    const key = text(op.key);
    const name = text(op.name);
    if (!key || !name) continue;
    if (op.kind === "addObjectType") types.set(key, { name, plural: text(op.pluralName) || name });
    else if (op.kind === "addAttributeType") attributes.set(key, name);
    else if (op.kind === "addRelationType") {
      relations.set(key, name);
      if (text(op.reverseName)) reverses.set(key, text(op.reverseName));
    }
  }
  return {
    type: (key) => types.get(text(key))?.name || text(key),
    typePlural: (key) => types.get(text(key))?.plural || text(key),
    attribute: (key) => attributes.get(text(key)) || text(key),
    relation: (key, direction) =>
      (direction === "incoming" ? reverses.get(text(key)) : undefined) || relations.get(text(key)) || text(key),
  };
}

export interface ModelChange {
  /** "New application", "New type", "New relationship", "Other change", "Removed". */
  change: string;
  /** The subject of the change. */
  name: string;
  /** What it is, in a sentence. */
  detail: string;
}

const CARDINALITY: Record<string, string> = {
  "one-to-one": "one to one",
  "one-to-many": "one to many",
  "many-to-one": "many to one",
  "many-to-many": "many to many",
};
/** What a type's changed fields are called to a reader: the key of a field is never shown. */
const TYPE_FIELDS: Record<string, string> = {
  name: "its name",
  pluralName: "its plural name",
  description: "its description",
  icon: "its icon",
  displayAttributeTypeKey: "the attribute that names its records",
};
const fieldWords = (field: unknown): string => {
  const key = text(field);
  // A field this list does not know reads as its key's words ("sortOrder" as "sort order").
  return (
    TYPE_FIELDS[key] ??
    key
      .replace(/Key$/, "")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .toLowerCase()
  );
};
const cardinality = (value: unknown) => CARDINALITY[text(value)] ?? text(value);

/** The operations as rows of "The model: what changes", in the order of their kinds. */
export function modelChanges(operations: AiTaskOperation[], names?: ModelNames): ModelChange[] {
  const applications = new Map<string, AiTaskOperation>();
  const types = new Map<string, AiTaskOperation>();
  const attributeNames = new Map<string, string>();
  const attached = new Map<string, string[]>();
  const relations = new Map<string, AiTaskOperation>();
  const allowed = new Map<string, string[]>();
  const other: ModelChange[] = [];
  for (const op of operations) {
    if (op.kind === "addApplication") applications.set(text(op.key), op);
    else if (op.kind === "addObjectType") types.set(text(op.key), op);
    else if (op.kind === "addAttributeType") attributeNames.set(text(op.key), text(op.name) || text(op.key));
    else if (op.kind === "addRelationType") relations.set(text(op.key), op);
  }
  const typeName = (key: unknown) => text(types.get(text(key))?.name) || names?.type(key) || text(key);
  const relationName = (key: unknown) => text(relations.get(text(key))?.name) || names?.relation(key) || text(key);
  const attributeName = (key: unknown) => attributeNames.get(text(key)) ?? names?.attribute(key) ?? text(key);
  for (const op of operations) {
    if (op.kind === "attachAttribute") {
      const label = `${attributeName(op.attributeType)}${op.required ? " (required)" : ""}`;
      attached.set(text(op.objectType), [...(attached.get(text(op.objectType)) ?? []), label]);
    } else if (op.kind === "allowRelation") {
      const line = `${typeName(op.from)} → ${typeName(op.to)}${op.cardinality ? ` (${cardinality(op.cardinality)})` : ""}`;
      allowed.set(text(op.relationType), [...(allowed.get(text(op.relationType)) ?? []), line]);
    } else if (op.kind === "setRelationRule") {
      other.push({
        change: "Other change",
        name: relationName(op.relationType),
        detail: `A rule of the relationship “${relationName(op.relationType)}” is set.`,
      });
    } else if (op.kind === "changeObjectType") {
      const fields = Array.isArray(op.fields) ? op.fields.map(fieldWords).join(", ") : "";
      other.push({
        change: "Other change",
        name: typeName(op.objectType),
        detail: `Changes ${fields || "its details"}.`,
      });
    } else if (op.kind === "changeAttachment") {
      other.push({
        change: "Other change",
        name: typeName(op.objectType),
        detail: `${attributeName(op.attributeType)} becomes ${op.required ? "required" : "optional"}.`,
      });
    } else if (op.kind === "detachAttribute") {
      other.push({
        change: "Other change",
        name: typeName(op.objectType),
        detail: `Loses the attribute ${attributeName(op.attributeType)}.`,
      });
    } else if (op.kind === "removeObjectType") {
      other.push({ change: "Removed", name: typeName(op.objectType), detail: "The type is removed." });
    } else if (op.kind === "removeAttributeType") {
      other.push({ change: "Removed", name: attributeName(op.attributeType), detail: "The attribute is removed." });
    } else if (op.kind === "removeRelationType") {
      other.push({ change: "Removed", name: relationName(op.relationType), detail: "The relationship is removed." });
    } else if (op.kind === "removeApplication") {
      other.push({ change: "Removed", name: text(op.applicationKey), detail: "The application is removed." });
    } else if (op.kind === "setLabel") {
      other.push({ change: "Other change", name: text(op.label) || "A label", detail: "A label is set." });
    }
  }
  const rows: ModelChange[] = [];
  for (const [key, op] of applications)
    rows.push({
      change: "New application",
      name: text(op.name) || key,
      detail: text(op.description) || "No description.",
    });
  for (const [key, op] of types) {
    const application = applications.get(text(op.applicationKey));
    const where = application ? text(application.name) || text(op.applicationKey) : text(op.applicationKey);
    const withAttributes = attached.get(key);
    const parentKey = text(op.parent) || text(record(op.parent).objectTypeKey);
    const parent = parentKey ? `, inside ${typeName(parentKey)}` : "";
    rows.push({
      change: "New type",
      name: text(op.name) || key,
      detail: `In ${where || "the model"}${parent}${withAttributes ? `, with ${withAttributes.join(", ")}` : ", without attributes"}.`,
    });
  }
  for (const [key, line] of attached) {
    if (types.has(key)) continue;
    rows.push({ change: "Other change", name: typeName(key), detail: `Gets the attributes ${line.join(", ")}.` });
  }
  for (const [key, op] of relations) {
    const name = text(op.name) || key;
    const reverse = text(op.reverseName);
    rows.push({
      change: "New relationship",
      name,
      detail: `${(allowed.get(key) ?? ["between types not yet named"]).join("; ")}${reverse ? `. Read the other way: ${reverse}` : ""}.`,
    });
  }
  for (const [key, lines] of allowed) {
    if (relations.has(key)) continue;
    rows.push({ change: "New relationship", name: relationName(key), detail: `Also allowed: ${lines.join("; ")}.` });
  }
  return [...rows, ...other];
}

/** "Key: code", "Key: the name", for a source's key. */
export function sourceKey(source: AiTaskDesignSource, names: ModelNames): string {
  const key = record(source.key);
  if (text(key.attributeTypeKey)) return names.attribute(key.attributeTypeKey);
  if (key.field === "name") return "Name";
  if (text(key.column)) return `column ${text(key.column)}`;
  return "none: every row creates a record";
}

/** What a match field or attribute reads as: "Name" or the attribute's name. */
const matchName = (match: unknown, names: ModelNames): string => {
  const by = record(match);
  if (text(by.attributeTypeKey)) return names.attribute(by.attributeTypeKey);
  return by.field === "name" ? "Name" : text(by.field);
};

/** The columns a profile source binds, one entry each: the header and what it fills, in the model's names. */
export function columnTargets(
  source: AiTaskDesignSource,
  names: ModelNames,
): { column: string; target: string; line: string }[] {
  return source.columns.map((raw) => {
    const column = record(raw);
    const named = Array.isArray(column.columns) ? column.columns.map(text).join(", ") : text(column.column);
    const relation = record(column.relation);
    const flags = record(column.relationFlags);
    const related = record(column.relatedRecord);
    let target = "Not recognised";
    if (column.ignore) target = "Left out";
    else if (column.field) target = column.field === "name" ? "Name" : shown(column.field);
    else if (column.attributeTypeKey) target = names.attribute(column.attributeTypeKey);
    else if (column.parent) target = `Parent: ${names.type(record(column.parent).objectTypeKey)}`;
    else if (column.relation) {
      const by = matchName(relation.matchBy, names);
      target = `Related ${names.type(relation.objectTypeKey)}${by ? ` by ${by}` : ""}`;
    } else if (column.relationFlags) target = `Yes or no per ${names.type(flags.objectTypeKey)}`;
    else if (column.relatedRecord)
      target = `${names.type(related.objectTypeKey)}: ${
        text(related.attributeTypeKey) ? names.attribute(related.attributeTypeKey) : "Name"
      }`;
    const header = named || "—";
    const same = header.trim().toLowerCase() === target.trim().toLowerCase();
    const own = same && (column.field ? "the record's name" : column.attributeTypeKey ? "its attribute" : "");
    return { column: header, target, line: `${header} → ${own || target}` };
  });
}

/** Why the engine could not apply the proposed model, or `null` when the proposal stands and can be accepted. */
export function proposalRefusal(task: AiTask): string | null {
  const outcome = task.design?.outcome;
  const refused = (outcome?.modelOperations as { refused?: { message?: string } } | undefined)?.refused;
  if (refused) return refused.message ?? "an operation was refused.";
  const errors = outcome?.draftErrors ?? [];
  return errors.length > 0 ? `the draft has ${errors.length} problem(s).` : null;
}
