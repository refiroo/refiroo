/**
 * Where a dragged record may land in a tree (Base 0.8 B5, D34). A drop names a new parent: a node,
 * a type heading's parent, or the branch a gap between rows belongs to. Whether the record may move
 * there is the model's containment rule (the one Add child uses) plus the refusals Move to…'s
 * candidates carry. The server stays the authority; this only says early what it would refuse.
 *
 * The top level is a target too (B5b, D36), written as no parent: a record of one of the tree's root
 * types may move there. Another type, even one the model lets stand at the top, would leave the tree.
 */

import { childObjectTypeKeys } from "@/model/collections";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";

export type MoveRefusal = "self" | "descendant" | "currentParent" | "application" | "type" | "notRoot";

type Placed = Pick<ObjectItem, "id" | "objectTypeKey" | "applicationKey" | "parentObjectId" | "path">;

/**
 * Why `record` cannot move into `parent`, or undefined when the move is allowed. A `null` parent is
 * the top level of a tree whose top shows `rootObjectTypeKeys`.
 */
export function moveRefusal(
  model: EngineModel,
  application: ApplicationDefinition,
  record: Placed,
  parent: Placed | null,
  rootObjectTypeKeys: readonly string[],
): MoveRefusal | undefined {
  if (parent === null) {
    if (record.parentObjectId === null) return "currentParent";
    return rootObjectTypeKeys.includes(record.objectTypeKey) ? undefined : "notRoot";
  }
  if (parent.id === record.id) return "self";
  if (parent.path.some((part) => part.id === record.id)) return "descendant";
  if (record.parentObjectId === parent.id) return "currentParent";
  if (parent.applicationKey !== record.applicationKey) return "application";
  if (!childObjectTypeKeys(model, application, parent.objectTypeKey).includes(record.objectTypeKey)) return "type";
  return undefined;
}

/** B2's words for the refusals Move to…'s candidates carry. */
export const MOVE_REFUSAL_TEXT: Record<"self" | "descendant" | "currentParent", string> = {
  self: "The record itself",
  descendant: "Inside the record",
  currentParent: "Current location",
};

/** A refusal as the user reads it; `type` names the records the parent cannot contain. */
export function moveRefusalText(model: EngineModel, reason: MoveRefusal, record: Pick<ObjectItem, "objectTypeKey">) {
  if (reason === "application") return "In another application";
  if (reason === "notRoot") return "Not shown at the top of this tree";
  if (reason === "type") {
    const plural = objectTypeFor(model, record.objectTypeKey)?.pluralName ?? record.objectTypeKey;
    return `Can't contain ${plural.toLowerCase()}`;
  }
  return MOVE_REFUSAL_TEXT[reason];
}

/** A drawn row's place: its level (1 at the top) and the records above it, outermost first. */
export interface RowPlace<T> {
  level: number;
  /** One per level above the row, so `parents.length === level - 1`. */
  parents: T[];
}

/** A branch a gap can drop into: its parent (`null` at the top level), and its children's level. */
export interface GapBranch<T> {
  level: number;
  parent: T | null;
}

/**
 * The branches a gap between two drawn rows belongs to, deepest first. Between rows of one branch
 * (or above a branch's first row) it is that branch. Where the next row is shallower, the gap ends
 * each branch from the row above's down to the next row's, and the pointer chooses among them.
 * The top level is the branch at level 1, with no parent.
 */
export function gapBranches<T>(above?: RowPlace<T>, below?: RowPlace<T>): GapBranch<T>[] {
  const branch = (place: RowPlace<T>, level: number): GapBranch<T>[] =>
    level === 1
      ? [{ level, parent: null }]
      : place.parents[level - 2] !== undefined
        ? [{ level, parent: place.parents[level - 2] }]
        : [];
  if (!above) return below ? branch(below, below.level) : [];
  if (below && below.level >= above.level) return branch(below, below.level);
  const branches: GapBranch<T>[] = [];
  for (let level = above.level; level >= (below?.level ?? 1); level -= 1) branches.push(...branch(above, level));
  return branches;
}

/**
 * The branch the pointer's horizontal position picks among a gap's branches: the deepest whose
 * rows start at or left of the pointer, else the shallowest. `indentOf` is where a level's rows start.
 */
export function chooseGapBranch<T>(
  branches: GapBranch<T>[],
  x: number,
  indentOf: (level: number) => number,
): GapBranch<T> | undefined {
  return branches.find((branch) => indentOf(branch.level) <= x) ?? branches.at(-1);
}
