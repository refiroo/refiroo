/**
 * Every record a collection's list matches, read when a bulk change runs (0.9 K2, D102, D103): the
 * list's own query, 500 records a page, keeping each record's ID, name and version. The reader
 * reports how many it has read and stops between pages when `signal` is aborted. Not
 * `lib/everyPage`, which reads short configuration lists whole.
 */

import type { ObjectPage } from "@/types";
import type { SelectableRow } from "@/lib/recordSelection";

export const MATCHING_PAGE = 500;

export class ReadStopped extends Error {
  constructor() {
    super("Reading the records was stopped");
    this.name = "ReadStopped";
  }
}

export async function readMatching(
  read: (selector: { cursor?: string; pageSize: number; includeTotal: boolean }) => Promise<ObjectPage>,
  { signal, onProgress }: { signal?: AbortSignal; onProgress?: (read: number, total: number | undefined) => void } = {},
): Promise<SelectableRow[]> {
  const rows: SelectableRow[] = [];
  let cursor: string | undefined;
  let total: number | undefined;
  do {
    if (signal?.aborted) throw new ReadStopped();
    const page = await read({ cursor, pageSize: MATCHING_PAGE, includeTotal: cursor === undefined });
    if (signal?.aborted) throw new ReadStopped();
    total ??= page.totalCount;
    for (const item of page.items) rows.push({ id: item.id, version: item.version, name: item.name });
    onProgress?.(rows.length, total);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return rows;
}
