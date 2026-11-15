/**
 * The model editor's history in plain words (0.10 A4a): each step of a draft's history (A2) as one
 * line, from its entries' kinds and parameters, and what the history says about undo and redo.
 */

import { text } from "@/lib/coerce";
import { counted } from "@/lib/count";
import type { EditorSelection, ModelDraftOperationEntry, RemovedElement } from "@/types";
import type { ElementKind } from "@/model/outline";
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
  if (p.view) return `view ${text(p.view)}`;
  const page = `the page of ${names("objectType", text(p.detail))}`;
  return p.panel ? `panel ${text(p.panel)} on ${page}` : page;
}

/** A list item: a field or column by its name, a panel by its title. */
function itemWords(item: unknown, names: Names): string {
  if (item && typeof item === "object")
    return `panel ${text((item as { title?: string }).title) || text((item as { key?: string }).key)}`;
  const key = text(item);
  if (key === "name") return "Name";
  return names("attributeType", key);
}

const LISTS: Record<string, string> = {
  columns: "the columns of",
  filterFields: "the filters of",
  sortFields: "the sort fields of",
  fields: "the fields of",
};

const PROPERTY_WORDS: Record<string, string> = {
  minimum: "minimum",
  maximum: "maximum",
  hidden: "visibility",
  helpText: "help text",
  displayAttributeTypeKey: "display attribute",
  effectivePeriod: "effective period",
  atLeastOneOf: "attributes of which one must be filled",
  parentRelationTypeKeys: "parent relationships",
};

function listWords(p: Record<string, unknown>, names: Names): string {
  if (text(p.list) === "panels") return layoutTarget(p, names);
  return `${LISTS[text(p.list)] ?? `${text(p.list)} of`} ${layoutTarget(p, names)}`;
}

function propertyWords(p: Record<string, unknown>, names: Names): string {
  const target = layoutTarget(p, names);
  const value = p.value;
  if (p.property === "visible") return `${value === false ? "Hid" : "Showed"} ${target}`;
  if (p.property === "region") return `Moved ${target} to the ${text(value)} region`;
  if (p.property === "title" || p.property === "name") return `Renamed ${target} to ${text(value)}`;
  if (p.property === "defaultSort") {
    const field = text(value).replace(/^-/, "");
    return `Sorted ${target} by ${itemWords(field, names)}${text(value).startsWith("-") ? ", descending" : ""}`;
  }
  return `Set ${text(p.property)} of ${target}`;
}

/** One operation in words. Unknown kinds fall back to their name, so a later kind still reads.
 * `inverse`, the entry's, holds what a rename replaced: the element is named as it was. */
export function describeOperation(
  kind: string,
  p: Record<string, unknown>,
  names: Names,
  inverse?: Record<string, unknown> | null,
): string {
  const type = (key: unknown) => names("objectType", text(key));
  const attribute = (key: unknown) => names("attributeType", text(key));
  const relation = (key: unknown) => names("relationType", text(key));
  switch (kind) {
    case "setLabel": {
      const labels = [p.name, p.pluralName, p.reverseName, p.label, p.title].map(text).filter(Boolean);
      // The element by its name before the step: the current name is the new one (R, A6b's TODO).
      const was = text(inverse?.name) || elementWords(p.element, names);
      return labels.length
        ? `Renamed ${was} to ${labels.join(" / ")}`
        : `Changed the description of ${elementWords(p.element, names)}`;
    }
    case "setKey":
      return `Changed the key of ${elementWords(p.element, names)} to ${text(p.key)}`;
    case "setRelease":
      return `Set the release to ${[text(p.key), text(p.version)].filter(Boolean).join(" ")}`.trim();
    case "addApplication":
      return `Added application ${text(p.name)}`;
    case "removeApplication":
      return `Removed application ${names("application", text(p.applicationKey))}`;
    case "addObjectType": {
      const parent = (p.parent as { objectTypes?: string[] } | null)?.objectTypes?.[0];
      return parent
        ? `Added type ${text(p.name)} under ${type(parent)}`
        : `Added type ${text(p.name)} at the top level`;
    }
    case "removeObjectType":
      return `Removed type ${type(p.objectType)}`;
    case "splitObjectType":
      return `Split ${text(p.name)} out of ${type(p.objectType)}`;
    case "mergeObjectTypes":
      return `Merged ${type(p.from)} into ${type(p.into)}`;
    case "convertAttributeToListType":
      return `Turned ${attribute(p.attributeType)} on ${type(p.objectType)} into the list type ${text(p.name)}`;
    case "addAttributeType":
      return `Added attribute type ${text(p.name)}`;
    case "removeAttributeType":
      return `Removed attribute type ${attribute(p.attributeType)}`;
    case "setAttributeTypeFeatures":
      return `Changed the features of ${attribute(p.attributeType)}`;
    case "setAttributeTypeProperty":
      return `Changed the ${PROPERTY_WORDS[text(p.property)] ?? text(p.property)} of ${attribute(p.attributeType)}`;
    case "setObjectTypeProperty":
      return `Changed the ${PROPERTY_WORDS[text(p.property)] ?? text(p.property)} of ${type(p.objectType)}`;
    case "setRelationTypeProperty":
      return `Made ${relation(p.relationType)} ${p.value === false ? "not oriented" : "oriented"}`;
    case "setApplicationProperty":
      return `Set the default view of ${names("application", text(p.applicationKey))} to ${text(p.value)}`;
    case "setValueType":
      return `Made ${attribute(p.attributeType)} ${text(p.valueType)}`;
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
      if ("ui" in p) return `Changed how ${attribute(p.attributeType)} shows on ${type(p.objectType)}`;
      return `Made ${attribute(p.attributeType)} on ${type(p.objectType)} ${p.readOnly ? "read-only" : "editable"}`;
    case "setContainment": {
      const parent = (p.parent as { objectTypes?: string[] } | null)?.objectTypes?.[0];
      // With an application, a move there (2026-10-19): the step names it.
      const into = text(p.application) ? ` of ${names("application", text(p.application))}` : "";
      const there = text(p.application) ? ` in ${names("application", text(p.application))}` : "";
      if (parent) return `Moved ${type(p.objectType)} under ${type(parent)}${there}`;
      // Without a parent the move keeps where the type stands, in the other application.
      if (!("parent" in p)) return `Moved ${type(p.objectType)} to ${names("application", text(p.application))}`;
      return `Moved ${type(p.objectType)} to the top level${into}`;
    }
    case "addRelationType":
      return `Added relation type ${text(p.name)}`;
    case "removeRelationType":
      return `Removed relation type ${relation(p.relationType)}`;
    case "allowRelation":
      return `Allowed ${type(p.from)} → ${type(p.to)} (${relation(p.relationType)}${p.cardinality ? `, ${text(p.cardinality)}` : ""})`;
    case "disallowRelation":
      return `Stopped allowing ${type(p.from)} → ${type(p.to)} (${relation(p.relationType)})`;
    case "setRelationRule":
      return `Changed the rule of ${type(p.from)} → ${type(p.to)} (${relation(p.relationType)})`;
    case "addNavigationGroup":
      return `Added navigation group ${text(p.label)}`;
    case "removeNavigationGroup":
      return `Removed navigation group ${names("group", text(p.group), text(p.applicationKey))}`;
    case "setNavigationGroup":
      return `Changed navigation group ${names("group", text(p.group), text(p.applicationKey))}`;
    case "placeCollection": {
      const entry = p.view ? `the matrix ${text(p.view)}` : type(p.collection);
      return p.group
        ? `Placed ${entry} in group ${names("group", text(p.group), text(p.applicationKey))}`
        : p.view
          ? `Took ${entry} out of its group`
          : `Placed ${entry} at the top of the sidebar`;
    }
    case "setCollectionOpening":
      return p.view
        ? `Made ${type(p.collection)} open on ${text(p.view)}`
        : `Made ${type(p.collection)} open on the application's default view`;
    case "addView":
      return `Added view ${text((p.view as { name?: string } | undefined)?.name) || text((p.view as { key?: string } | undefined)?.key)}`;
    case "removeView":
      return `Removed view ${text(p.view)}`;
    case "listObjectType":
      return `Listed ${type(p.objectType)} in ${text(p.applicationKey)}`;
    case "unlistObjectType":
      return `Stopped listing ${type(p.objectType)} in ${text(p.applicationKey)}`;
    case "addDetailPage":
      return `Added a detail page for ${type(p.objectType)}`;
    case "removeDetailPage":
      return `Removed the detail page of ${type(p.objectType)}`;
    case "addPanel":
      return `Added panel ${text(p.title)} to ${type(p.detail)}`;
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

/**
 * What a step changes that needs a migration when the draft is installed (0.13 MG), for its mark in the
 * history: each element with what holds it, from the step's entries. Empty for a step that needs none.
 */
export function migrationWords(step: HistoryStep, names: Names): string {
  const found = new Map<string, string>();
  for (const entry of step.entries) {
    for (const item of entry.migration ?? []) {
      const held = [
        [item.impact.records, "record", "records"],
        [item.impact.values, "value", "values"],
        [item.impact.relationships, "relationship", "relationships"],
      ] as const;
      const parts = held.filter(([amount]) => amount !== 0).map(([amount, one, many]) => counted(amount, one, many));
      const holds = parts.length ? parts.join(", ") : "no stored data";
      const name = elementWords(item.element, names);
      found.set(name, `${name}: ${item.keyChange ? "the key changes, " : ""}${holds}`);
    }
  }
  return [...found.values()].join("; ");
}

/** A step in one line. */
export function describeStep(step: HistoryStep, names: Names): string {
  if (step.origin.type === "undo") return `Undid step ${(step.origin.steps ?? []).join(" and ")}`;
  if (step.origin.type === "redo") return `Redid step ${step.origin.step ?? ""}`.trim();
  // A proposal applied (0.10 A6b): what the rule found, as the proposal said it.
  if (step.origin.type === "proposal" && step.origin.summary) return `Proposed: ${step.origin.summary}`;
  const line = step.entries
    .map((entry) => describeOperation(entry.kind, entry.parameters, names, entry.inverse))
    .join("; ");
  const removed = step.entries.flatMap((entry) => entry.removed ?? []);
  return removed.length ? `${line}. ${removedWords(removed, names)}` : line;
}

/**
 * What a step could not keep, as the editor says it after the step and in its history: the views
 * and panels that could stand in no application once their types stood apart (a move between
 * applications, 2026-10-19).
 */
export function removedWords(removed: RemovedElement[], names: Names): string {
  const parts = removed.map((item) =>
    item.kind === "view"
      ? `${item.name} in ${names("application", item.applicationKey)}`
      : `the ${item.name} panel of ${names("objectType", item.detail ?? "")} in ${names("application", item.applicationKey)}`,
  );
  const listed = parts.length > 1 ? `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}` : parts[0];
  return `Removed, as their types no longer stand in one application: ${listed}. Undo puts them back.`;
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
  if (selection.show === "group") {
    // A group is renamed by a `setKey` naming its application and the group.
    let key = selection.key;
    for (const entry of entries) {
      const element = (entry.parameters.element ?? {}) as Record<string, string>;
      if (entry.kind === "setKey" && element.applicationKey === selection.application && element.group === key)
        key = String(entry.parameters.key);
    }
    return key === selection.key ? undefined : { ...selection, key };
  }
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
