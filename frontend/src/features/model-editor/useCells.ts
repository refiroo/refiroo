/**
 * The cells of a range of a sheet of the draft's file (0.10 A8b, D124), every page of it read: the
 * range is a list with a margin, so it is small. A newer range replaces an older one still reading.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { SourceCell } from "@/types";

export interface Cells {
  /** Each row's cells by column letter; a row with no cell in the range is absent. */
  rows: Map<number, Record<string, SourceCell>>;
  /** The range these rows are of, once read. */
  range?: string;
  error: string;
  retry: () => void;
}

export function useCells(fileId: string | undefined, sheet: string, range: string | undefined): Cells {
  const [read, setRead] = useState<{ key: string; rows: Map<number, Record<string, SourceCell>>; error: string }>();
  const [attempt, setAttempt] = useState(0);
  const key = `${fileId}|${sheet}|${range}|${attempt}`;
  useEffect(() => {
    if (!fileId || !range) return;
    let cancelled = false;
    void (async () => {
      const rows = new Map<number, Record<string, SourceCell>>();
      try {
        let cursor: string | undefined;
        do {
          const page = await api.sourceCells(fileId, sheet, range, cursor);
          for (const item of page.items) rows.set(item.row, item.cells);
          cursor = page.nextCursor ?? undefined;
        } while (cursor && !cancelled);
        if (!cancelled) setRead({ key, rows, error: "" });
      } catch (cause) {
        if (!cancelled) setRead({ key, rows, error: errorMessage(cause) });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fileId, sheet, range, key]);
  const retry = () => setAttempt((value) => value + 1);
  return read?.key === key
    ? { rows: read.rows, range, error: read.error, retry }
    : { rows: new Map(), error: "", retry };
}
