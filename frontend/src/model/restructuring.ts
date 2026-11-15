/**
 * Which restructurings the model makes possible for a record (Base 0.8 C4, ADR-034), kept to the types
 * a tree shows. The types a place can hold are the engine's (`model/placements`, served); the server
 * plans and refuses. This only decides what a tree offers, and names no type.
 */

import { typeName } from "@/model/lookup";
import { possibleTypes } from "@/model/placements";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";

/** Type names as a sentence lists them: "A", "A or B", "A, B or C". */
export function typeNames(model: EngineModel, keys: readonly string[]): string {
  const names = keys.map((key) => typeName(model, key));
  return names.length > 1 ? `${names.slice(0, -1).join(", ")} or ${names.at(-1)}` : (names[0] ?? "");
}

/** The type of a record's parent, from its path; `null` at the top level. */
export function parentTypeOf(item: Pick<ObjectItem, "path">): string | null {
  return item.path.at(-2)?.objectTypeKey ?? null;
}

/** What a tree shows: its types, and which of them stand at its top. */
export interface TreeTypes {
  nodeTypes: ReadonlySet<string>;
  rootTypes: readonly string[];
}

/**
 * The types a place in the tree can hold: the model's, kept to those the tree shows there. A record
 * moved to a place its type cannot stand becomes one of these.
 */
export function placeTypes(
  model: EngineModel,
  application: ApplicationDefinition,
  tree: TreeTypes,
  parentObjectTypeKey: string | null,
): string[] {
  return possibleTypes(model, application, parentObjectTypeKey).filter((key) =>
    parentObjectTypeKey === null ? tree.rootTypes.includes(key) : tree.nodeTypes.has(key),
  );
}

/** The refactorings a record's node menu offers, each only where the model makes it possible. */
export interface RestructuringChoices {
  /** Types the record can become under its own parent. */
  changeType: string[];
  /** Types a level inserted above the record can have: its parent's place holds them and they hold something. */
  insertLevel: string[];
  /** Whether the record is a level: its type can hold records in the tree. */
  removeLevel: boolean;
  /** Per type found below the record, the types its records can become there. */
  changeTypeUnder: { fromObjectTypeKey: string; objectTypeKeys: string[] }[];
}

export function restructuringChoices(
  model: EngineModel,
  application: ApplicationDefinition,
  tree: TreeTypes,
  item: Pick<ObjectItem, "objectTypeKey" | "path">,
): RestructuringChoices {
  const place = (parent: string | null) => placeTypes(model, application, tree, parent);
  const parentType = parentTypeOf(item);
  const holds = (key: string) => place(key).length > 0;

  // Types below the record, level by level, and the types each one can stand under there.
  const parentsOf = new Map<string, Set<string>>();
  const seen = new Set<string>([item.objectTypeKey]);
  const queue = [item.objectTypeKey];
  while (queue.length) {
    const parent = queue.shift()!;
    for (const child of place(parent)) {
      parentsOf.set(child, new Set([...(parentsOf.get(child) ?? []), parent]));
      if (!seen.has(child)) {
        seen.add(child);
        queue.push(child);
      }
    }
  }
  const changeTypeUnder = [...parentsOf].flatMap(([from, parents]) => {
    const targets = new Set([...parents].flatMap((parent) => place(parent)));
    targets.delete(from);
    const objectTypeKeys = application.objectTypeKeys.filter((key) => targets.has(key));
    return objectTypeKeys.length ? [{ fromObjectTypeKey: from, objectTypeKeys }] : [];
  });

  return {
    changeType: place(parentType).filter((key) => key !== item.objectTypeKey),
    insertLevel: place(parentType).filter(holds),
    removeLevel: holds(item.objectTypeKey),
    changeTypeUnder: application.objectTypeKeys.flatMap((key) =>
      changeTypeUnder.filter((entry) => entry.fromObjectTypeKey === key),
    ),
  };
}
