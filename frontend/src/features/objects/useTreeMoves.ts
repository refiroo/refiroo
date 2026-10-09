/**
 * Where a record of a tree may move, in words: the one rule the hierarchy lens and the sidebar's
 * tree both drag and Move to… by (UA9, U-D22; extracted from `TreeView`, 0.8 B5 and C4).
 *
 * The places come from the engine's placements (D45, `model/treeDrop.moveRefusal`). Where types
 * change (in a change set, where the tree allows it, D38), a place that holds the record only as
 * another type of the tree is accepted and says what the record becomes; live, such a place says a
 * change set could change the type.
 */

import { useCallback } from "react";
import { childObjectTypeKeys } from "@/model/placements";
import { placeTypes, typeNames, type TreeTypes } from "@/model/restructuring";
import { moveRefusal, moveRefusalText } from "@/model/treeDrop";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";

export function useTreeMoves({
  model,
  application,
  treeTypes,
  rootObjectTypeKeys,
  canMove,
  typeChanges,
  live,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  /** The types the tree shows, and those it lists at the top. */
  treeTypes: TreeTypes;
  rootObjectTypeKeys: readonly string[];
  /** Whether records of this tree move at all in this context. */
  canMove: boolean;
  /** Whether a move may change a record's type here. */
  typeChanges: boolean;
  live: boolean;
}) {
  /**
   * Whether a record of the type can move at all: some type of the application contains it, or, where
   * types can change, it can become one that stands somewhere.
   */
  const movable = useCallback(
    (objectTypeKey: string) =>
      typeChanges ||
      application.objectTypeKeys.some((key) => childObjectTypeKeys(model, application, key).includes(objectTypeKey)),
    [model, application, typeChanges],
  );
  /**
   * The types the record would become under `parent` (`null` is the top level), where its own type
   * cannot stand there but another type of the tree can; undefined otherwise.
   */
  const typeChangeAt = useCallback(
    (item: ObjectItem, parent: ObjectItem | null) => {
      const reason = moveRefusal(model, application, item, parent, rootObjectTypeKeys);
      if (reason !== "type" && reason !== "notRoot") return undefined;
      const types = placeTypes(model, application, treeTypes, parent?.objectTypeKey ?? null);
      return types.length ? types : undefined;
    },
    [model, application, rootObjectTypeKeys, treeTypes],
  );
  const becomesAt = useCallback(
    (item: ObjectItem, parent: ObjectItem | null) => (typeChanges ? typeChangeAt(item, parent) : undefined),
    [typeChanges, typeChangeAt],
  );
  /**
   * Why the record cannot move into `parent` (`null` is the top level), in words; undefined allows it.
   * Live, a place refused only for the record's type says a change set could change it (D38).
   */
  const refusalOf = useCallback(
    (item: ObjectItem, parent: ObjectItem | null) => {
      if (becomesAt(item, parent)) return undefined;
      const reason = moveRefusal(model, application, item, parent, rootObjectTypeKeys);
      if (!reason) return undefined;
      const text = moveRefusalText(model, reason, item);
      return live && canMove && typeChangeAt(item, parent) ? `${text} · a change set can change its type` : text;
    },
    [model, application, rootObjectTypeKeys, becomesAt, typeChangeAt, live, canMove],
  );
  const becomesText = useCallback(
    (item: ObjectItem, parent: ObjectItem | null) => {
      const types = becomesAt(item, parent);
      return types && `Becomes ${typeNames(model, types)}`;
    },
    [becomesAt, model],
  );
  return { movable, becomesAt, refusalOf, becomesText };
}
