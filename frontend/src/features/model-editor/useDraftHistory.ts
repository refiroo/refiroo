/**
 * The draft's steps as the editor's History lists them (0.10 A4a): read from the end, newest first, page by page,
 * and read again after every step the draft takes. One hook for the model editor and the canvas's drawer.
 */

import { api } from "@/api/client";
import { useCursorFeed, type CursorFeed } from "@/lib/hooks/useCursorFeed";
import type { ModelDraftOperationEntry } from "@/types";

export function useDraftHistory(draftId: string, version: number | undefined): CursorFeed<ModelDraftOperationEntry> {
  return useCursorFeed(
    async (cursor) => {
      const page = await api.modelDraftOperations(draftId, { cursor });
      // Read from the end: each page is oldest first, and its previous cursor reaches older steps.
      return { items: [...page.items].reverse(), nextCursor: page.prevCursor };
    },
    [draftId, version ?? 0],
    (previous, incoming) => {
      const seen = new Set(previous.map((item) => item.sequence));
      return [...previous, ...incoming.filter((item) => !seen.has(item.sequence))];
    },
  );
}
