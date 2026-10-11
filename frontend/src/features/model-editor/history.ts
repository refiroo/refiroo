/**
 * The model editor's history in plain words (0.10 A4a): each step of a draft's history (A2) as one
 * line, from its entries' kinds and parameters, and what the history says about undo and redo.
 */

import type { ModelDraftOperationEntry } from "@/types";
import type { ElementKind } from "@/features/model-editor/outline";

/** One step of the history: its entries, oldest first. */
export interface HistoryStep {
  step: number;
  entries: ModelDraftOperationEntry[];
  at: string;
  origin: ModelDraftOperationEntry["origin"];
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

/** One operation in words. Unknown kinds fall back to their name, so a later kind still reads. */
export function describeOperation(kind: string, p: Record<string, unknown>, names: Names): string {
  const type = (key: unknown) => names("objectType", str(key));
  const attribute = (key: unknown) => names("attributeType", str(key));
  const relation = (key: unknown) => names("relationType", str(key));
  switch (kind) {
    case "setLabel": {
      const labels = [p.name, p.pluralName, p.reverseName, p.label, p.title].map(str).filter(Boolean);
      return labels.length
        ? `Renamed ${elementWords(p.element, names)} to ${labels.join(" / ")}`
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
    case "replaceModel":
      return "Edited the whole model as JSON";
    case "restoreElements":
      return "Put back what a step changed";
    default:
      return kind;
  }
}

/** The history's entries, newest step first, grouped by step. */
export function historySteps(entries: ModelDraftOperationEntry[]): HistoryStep[] {
  const steps = new Map<number, HistoryStep>();
  for (const entry of entries) {
    const step = steps.get(entry.step) ?? {
      step: entry.step,
      entries: [],
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
  return step.entries.map((entry) => describeOperation(entry.kind, entry.parameters, names)).join("; ");
}

/** Whether a step can be undone from its line: a change not undone yet (an undo is taken back by redo). */
export function undoable(step: HistoryStep): boolean {
  return !step.undone && step.origin.type !== "undo";
}

/**
 * Whether redo has something to take back (D32): walking from the newest step, an undo not taken
 * back yet before any other change. A redo, or an undo already taken back, is passed over.
 */
export function canRedo(steps: HistoryStep[]): boolean {
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
