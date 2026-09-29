/**
 * Models with the placements the engine serves beside them (`GET /model/placements`). The browser
 * derives no placement, so a test model states its own as data; the starter's is generated from the
 * engine (`starterPlacements.json`), and a backend test keeps the two equal.
 */

import starter from "../../../model/rdm-starter.json";
import starterPlacements from "./starterPlacements.json";
import type { EngineModel, ModelPlacementParent } from "@/types";

/** The starter model as the browser loads it. */
export const starterModel: EngineModel = { ...(starter as unknown as EngineModel), placements: starterPlacements };

/**
 * One application's placements from a compact table: per parent type, the types it contains and,
 * where they differ, the types a record can become under it.
 */
export function applicationPlacements(
  applicationKey: string,
  topLevelObjectTypeKeys: string[],
  parents: Record<string, string[] | { children: string[]; possible: string[] }>,
) {
  return {
    applicationKey,
    topLevelObjectTypeKeys,
    parents: Object.entries(parents).map(([objectTypeKey, value]): ModelPlacementParent => ({
      objectTypeKey,
      childObjectTypeKeys: Array.isArray(value) ? value : value.children,
      possibleObjectTypeKeys: Array.isArray(value) ? value : value.possible,
    })),
  };
}
