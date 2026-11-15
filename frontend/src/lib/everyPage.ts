/**
 * Every item of a short configuration list (profiles, workspaces, a workspace's change sets), read
 * page by page to its end (ADR-030). Not for record collections, which scroll in a window.
 *
 * A failed page rejects the whole read: nothing partial is returned. Two options end the read early
 * and answer what has been read so far: `signal`, once aborted (checked before each page and after
 * it; the caller tests the signal to tell a stop from an end), and `stop`, which is asked after
 * each page and ends the read at the first page it says true for (a first match).
 */
export async function everyPage<T>(
  read: (cursor?: string) => Promise<{ items: T[]; nextCursor: string | null }>,
  { signal, stop }: { signal?: AbortSignal; stop?: (page: { items: T[] }) => boolean } = {},
) {
  const items: T[] = [];
  let cursor: string | undefined;
  do {
    if (signal?.aborted) break;
    const page = await read(cursor);
    if (signal?.aborted) break;
    items.push(...page.items);
    if (stop?.(page)) break;
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return items;
}
