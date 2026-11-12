/**
 * The draft compiled as the engine would run it, read again after every step (0.17 PL3b): the board
 * reads each list's filters from its table view, which the outline does not carry. A draft that does
 * not compile has none; the canvas then shows no filters rather than guessing them.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { EngineModel } from "@/types/model";

export function useDraftModel(draftId: string, version: number | undefined): EngineModel | undefined {
  const [read, setRead] = useState<{ version: number; model?: EngineModel }>();
  useEffect(() => {
    if (version === undefined) return;
    let cancelled = false;
    api
      .modelDraftModel(draftId)
      .then((next) => !cancelled && setRead({ version, model: next.model }))
      .catch(() => !cancelled && setRead({ version }));
    return () => {
      cancelled = true;
    };
  }, [draftId, version]);
  return read && read.version === version ? read.model : undefined;
}
