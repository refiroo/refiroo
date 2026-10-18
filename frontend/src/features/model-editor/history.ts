/**
 * The model editor's history in plain words (0.10 A4a): each step of a draft's history (A2) as one
 * line, from its entries' kinds and parameters, and what the history says about undo and redo.
 */

import type { EditorSelection, ModelDraftOperationEntry } from "@/types";
import type { ElementKind } from "@/features/model-editor/outline";
import { describeConsumerOperation } from "@/features/model-editor/consumer";
import { describeMappingOperation } from "@/features/model-editor/mapping";

/** What steps are read from: a draft's history entry, or a model mapping's (0.11 X4), which share one history. */
interface StepEntry {
  step: number;
  sequence: number;
  at: string;
  undone: boolean;
  origin: { type: string };
}

/** One step of the history: its entries, oldest first. */
export interface HistoryStep<E extends StepEntry = ModelDraftOperationEntry> {
  step: number;
  entries: E[];
  at: string;
  origin: E["origin"];
  undone: boolean;
}

type Names = (kind: ElementKind, key: string, applicationKey?: string) => string;

const str = (value: unknown) => (typeof value === "string" ? value : "");

function elementWords(element: unknown, names: Names): string {
  const item = (element ?? {}) as Record<string, string>;
  if (item.group) return `group ${names("group", item.group, item.applicationKey)}`;
  if (item.view) return `view ${item.view}`;
  if (item.objectType) return names("objectType", item.objectType);
  if (item.attributeType) return names("attributeType", item.attributeType);
  if (item.relationType) return names("relationType", item.relationType);
  if (item.applicationKey) return names("application", item.applicationKey);
  return "an element";
}

/** A view, a detail page or a panel, as a layout operation names it (D19). */
function layoutTarget(p: Record<string, unknown>, names: Names): string {
  if (p.view) return `view ${str(p.view)}`;
  const page = `the page of ${names("objectType", str(p.detail))}`;
  return p.panel ? `panel ${str(p.panel)} on ${page}` : page;
}

/** A list item: a field or column by its name, a panel by its title. */
function itemWords(item: unknown, names: Names): string {
  if (item && typeof item === "object")
    return `panel ${str((item as { title?: string }).title) || str((item as { key?: string }).key)}`;
  const key = str(item);
  if (key === "name") return "Name";
  return names("attributeType", key);
}

const LISTS: Record<string, string> = {
  columns: "the columns of",
  filterFields: "the filters of",
  sortFields: "the sort fields of",
  fields: "the fields of",
};

function listWords(p: Record<string, unknown>, names: Names): string {
  if (str(p.list) === "panels") return layoutTarget(p, names);
  return `${LISTS[str(p.list)] ?? `${str(p.list)} of`} ${layoutTarget(p, names)}`;
}

function propertyWords(p: Record<string, unknown>, names: Names): string {
  const target = layoutTarget(p, names);
  const value = p.value;
  if (p.property === "visible") return `${value === false ? "Hid" : "Showed"} ${target}`;
  if (p.property === "region") return `Moved ${target} to the ${str(value)} region`;
  if (p.property === "title" || p.property === "name") return `Renamed ${target} to ${str(value)}`;
  if (p.property === "defaultSort") {
    const field = str(value).replace(/^-/, "");
    return `Sorted ${target} by ${itemWords(field, names)}${str(value).startsWith("-") ? ", descending" : ""}`;
  }
  return `Set ${str(p.property)} of ${target}`;
}

/** One operation in words. Unknown kinds fall back to their name, so a later kind still reads.
 * `inverse`, the entry's, holds what a rename replaced: the element is named as it was. */
export function describeOperation(
  kind: string,
  p: Record<string, unknown>,
  names: Names,
  inverse?: Record<string, unknown> | null,
): string {
  const type = (key: unknown) => names("objectType", str(key));
  const attribute = (key: unknown) => names("attributeType", str(key));
  const relation = (key: unknown) => names("relationType", str(key));
  switch (kind) {
    case "setLabel": {
      const labels = [p.name, p.pluralName, p.reverseName, p.label, p.title].map(str).filter(Boolean);
      // The element by its name before the step: the current name is the new one (R, A6b's TODO).
      const was = str(inverse?.name) || elementWords(p.element, names);
      return labels.length
        ? `Renamed ${was} to ${labels.join(" / ")}`
        : `Changed the description of ${elementWords(p.element, names)}`;
    }
    case "setKey":
      return `Changed the key of ${elementWords(p.element, names)} to ${str(p.key)}`;
    case "setRelease":
      return `Set the release to ${[str(p.key), str(p.version)].filter(Boolean).join(" ")}`.trim();
    case "addApplication":
      return `Added application ${str(p.name)}`;
    case "removeApplication":
      return `Removed application ${names("application", str(p.applicationKey))}`;
    case "addObjectType": {
      const parent = (p.parent as { objectTypes?: string[] } | null)?.objectTypes?.[0];
      return parent ? `Added type ${str(p.name)} under ${type(parent)}` : `Added type ${str(p.name)} at the top level`;
    }
    case "removeObjectType":
      return `Removed type ${type(p.objectType)}`;
    case "splitObjectType":
      return `Split ${str(p.name)} out of ${type(p.objectType)}`;
    case "mergeObjectTypes":
      return `Merged ${type(p.from)} into ${type(p.into)}`;
    case "convertAttributeToListType":
      return `Turned ${attribute(p.attributeType)} on ${type(p.objectType)} into the list type ${str(p.name)}`;
    case "addAttributeType":
      return `Added attribute type ${str(p.name)}`;
    case "removeAttributeType":
      return `Removed attribute type ${attribute(p.attributeType)}`;
    case "setAttributeTypeFeatures":
      return `Changed the features of ${attribute(p.attributeType)}`;
    case "setValueType":
      return `Made ${attribute(p.attributeType)} ${str(p.valueType)}`;
    case "attachAttribute":
      return `Attached ${attribute(p.attributeType)} to ${type(p.objectType)}${p.required ? ", required" : ""}`;
    case "detachAttribute":
      return `Detached ${attribute(p.attributeType)} from ${type(p.objectType)}`;
    case "moveAttribute":
      return `Moved ${attribute(p.attributeType)} from ${type(p.from)} to ${type(p.to)}`;
    case "setAttributeBinding":
      if ("position" in p)
        return `Moved ${attribute(p.attributeType)} on ${type(p.objectType)} to place ${Number(p.position) + 1}`;
      if ("required" in p)
        return `Made ${attribute(p.attributeType)} on ${type(p.objectType)} ${p.required ? "required" : "optional"}`;
      return `Made ${attribute(p.attributeType)} on ${type(p.objectType)} ${p.readOnly ? "read-only" : "editable"}`;
    case "setContainment": {
      const parent = (p.parent as { objectTypes?: string[] } | null)?.objectTypes?.[0];
      return parent
        ? `Moved ${type(p.objectType)} under ${type(parent)}`
        : `Moved ${type(p.objectType)} to the top level`;
    }
    case "addRelationType":
      return `Added relation type ${str(p.name)}`;
    case "removeRelationType":
      return `Removed relation type ${relation(p.relationType)}`;
    case "allowRelation":
      return `Allowed ${type(p.from)} → ${type(p.to)} (${relation(p.relationType)}${p.cardinality ? `, ${str(p.cardinality)}` : ""})`;
    case "disallowRelation":
      return `Stopped allowing ${type(p.from)} → ${type(p.to)} (${relation(p.relationType)})`;
    case "setRelationRule":
      return `Changed the rule of ${type(p.from)} → ${type(p.to)} (${relation(p.relationType)})`;
    case "addNavigationGroup":
      return `Added navigation group ${str(p.label)}`;
    case "removeNavigationGroup":
      return `Removed navigation group ${names("group", str(p.group), str(p.applicationKey))}`;
    case "setNavigationGroup":
      return `Changed navigation group ${names("group", str(p.group), str(p.applicationKey))}`;
    case "placeCollection":
      return p.group
        ? `Placed ${type(p.collection)} in group ${names("group", str(p.group), str(p.applicationKey))}`
        : `Placed ${type(p.collection)} at the top of the sidebar`;
    case "addView":
      return `Added view ${str((p.view as { name?: string } | undefined)?.name) || str((p.view as { key?: string } | undefined)?.key)}`;
    case "removeView":
      return `Removed view ${str(p.view)}`;
    case "addDetailPage":
      return `Added a detail page for ${type(p.objectType)}`;
    case "removeDetailPage":
      return `Removed the detail page of ${type(p.objectType)}`;
    case "insertViewItem":
      return `Added ${itemWords(p.item, names)} to ${listWords(p, names)}`;
    case "moveViewItem":
      return `Moved ${itemWords(p.item, names)} to place ${Number(p.position) + 1} in ${listWords(p, names)}`;
    case "removeViewItem":
      return `Removed ${itemWords(p.item, names)} from ${listWords(p, names)}`;
    case "setViewProperty":
      return propertyWords(p, names);
    case "replaceModel":
      return "Edited the whole model as JSON";
    case "restoreElements":
      return "Put back what a step changed";
    default:
      return (
        describeMappingOperation(kind, p, names) ??
        describeConsumerOperation(kind, p, (key) => names("consumerApi", key)) ??
        kind
      );
  }
}

/** The history's entries, newest step first, grouped by step. */
export function historySteps<E extends StepEntry = ModelDraftOperationEntry>(entries: E[]): HistoryStep<E>[] {
  const steps = new Map<number, HistoryStep<E>>();
  for (const entry of entries) {
    const step: HistoryStep<E> = steps.get(entry.step) ?? {
      step: entry.step,
      entries: [] as E[],
      at: entry.at,
      origin: entry.origin,
      undone: true,
    };
    step.entries.push(entry);
    step.undone = step.undone && entry.undone;
    steps.set(entry.step, step);
  }
  for (const step of steps.values()) step.entries.sort((a, b) => a.sequence - b.sequence);
  return [...steps.values()].sort((a, b) => b.step - a.step);
}

/** A step in one line. */
export function describeStep(step: HistoryStep, names: Names): string {
  if (step.origin.type === "undo") return `Undid step ${(step.origin.steps ?? []).join(" and ")}`;
  if (step.origin.type === "redo") return `Redid step ${step.origin.step ?? ""}`.trim();
  // A proposal applied (0.10 A6b): what the rule found, as the proposal said it.
  if (step.origin.type === "proposal" && step.origin.summary) return `Proposed: ${step.origin.summary}`;
  return step.entries.map((entry) => describeOperation(entry.kind, entry.parameters, names, entry.inverse)).join("; ");
}

/** Whether a step can be undone from its line: a change not undone yet (an undo is taken back by redo). */
export function undoable(step: Pick<HistoryStep<StepEntry>, "undone" | "origin">): boolean {
  return !step.undone && step.origin.type !== "undo";
}

/**
 * Whether redo has something to take back (D32): walking from the newest step, an undo not taken
 * back yet before any other change. A redo, or an undo already taken back, is passed over.
 */
export function canRedo(steps: Pick<HistoryStep<StepEntry>, "undone" | "origin">[]): boolean {
  for (const step of steps) {
    if (step.origin.type === "undo") {
      if (!step.undone) return true;
      continue;
    }
    if (step.origin.type === "redo") continue;
    return false;
  }
  return false;
}

/** Which member of a `setKey` element names each kind of selection (an element alone, no part of it). */
const SELECTED_BY: Partial<Record<NonNullable<EditorSelection["show"]>, string>> = {
  type: "objectType",
  attributeType: "attributeType",
  relationType: "relationType",
  application: "applicationKey",
  consumerApi: "consumerApi",
};

/**
 * The selection after a step that changed the selected element's key (0.10 A5b): the same element
 * under its new key, so the editor keeps showing it; `undefined` when the step left it alone.
 */
export function followKeyChange(
  selection: EditorSelection,
  entries: ModelDraftOperationEntry[],
): EditorSelection | undefined {
  const member = selection.show ? SELECTED_BY[selection.show] : undefined;
  if (!member || !("key" in selection)) return undefined;
  let key = selection.key;
  for (const entry of entries) {
    const element = (entry.parameters.element ?? {}) as Record<string, string>;
    if (entry.kind === "setKey" && Object.keys(element).length === 1 && element[member] === key)
      key = String(entry.parameters.key);
  }
  return key === selection.key ? undefined : ({ ...selection, key } as EditorSelection);
}
