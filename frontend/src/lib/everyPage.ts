/**
 * Every item of a short configuration list (profiles, workspaces, a workspace's change sets), read
 * page by page to its end (ADR-030). Not for record collections, which scroll in a window.
 */
export async function everyPage<T>(read: (cursor?: string) => Promise<{ items: T[]; nextCursor: string | null }>) {
  const items: T[] = [];
  let cursor: string | undefined;
  do {
    const page = await read(cursor);
    items.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return items;
}
