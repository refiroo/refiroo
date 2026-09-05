import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../../api/errors";

export interface CursorPage<T> {
  items: T[];
  nextCursor: string | null;
}

export interface CursorFeed<T> {
  /** Every item loaded so far, in page order. */
  items: T[];
  /** True while either the first page or a further page is in flight. */
  loading: boolean;
  /** Message from the most recent failure, or "" when the last attempt succeeded. */
  error: string;
  /** True when the server reported a cursor for a further page. */
  hasMore: boolean;
  /** Appends the next page. No-op when there is no further page. */
  loadMore: () => void;
  /** Repeats whichever request failed — the initial load or the further page. */
  retry: () => void;
  /** Discards what is loaded and fetches the first page again. */
  reload: () => void;
  /** Replaces the loaded items, for callers that mutate one in place. */
  setItems: React.Dispatch<React.SetStateAction<T[]>>;
}

/**
 * An append-on-demand feed over a cursor-paged collection.
 *
 * The first page loads whenever `deps` change and replaces what is held; `loadMore` appends. A
 * failure records which of the two it was, so `retry` repeats that request rather than silently
 * restarting the feed — reloading a feed the user has paged through would discard their position.
 *
 * `merge` lets a caller filter or deduplicate incoming items against those already held; it
 * defaults to plain concatenation. Every page passes through it, including the first, where
 * `previous` is empty — so a caller that excludes certain items writes that rule once. It is read
 * through a ref, so an inline closure does not need to be memoised by the caller.
 *
 * Collections that need backward movement through pages use `useCursorPages` instead.
 */
export function useCursorFeed<T>(
  fetchPage: (cursor?: string) => Promise<CursorPage<T>>,
  deps: React.DependencyList,
  merge: (previous: T[], incoming: T[]) => T[] = (previous, incoming) => [...previous, ...incoming],
): CursorFeed<T> {
  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  // The caller rebuilds both closures every render. Holding them in refs keeps the request
  // identity out of the dependency list, so the feed reloads only when `deps` say to.
  const fetchRef = useRef(fetchPage);
  fetchRef.current = fetchPage;
  const mergeRef = useRef(merge);
  mergeRef.current = merge;
  const failedMode = useRef<"reload" | "more">("reload");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    fetchRef
      .current(undefined)
      .then((page) => {
        if (!active) return;
        setItems(mergeRef.current([], page.items));
        setCursor(page.nextCursor ?? undefined);
      })
      .catch((cause) => {
        if (!active) return;
        failedMode.current = "reload";
        setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the caller declares the reload keys
  }, [...deps, reloadToken]);

  const loadMore = useCallback(() => {
    if (!cursor) return;
    setLoading(true);
    setError("");
    fetchRef
      .current(cursor)
      .then((page) => {
        setItems((current) => mergeRef.current(current, page.items));
        setCursor(page.nextCursor ?? undefined);
      })
      .catch((cause) => {
        failedMode.current = "more";
        setError(errorMessage(cause));
      })
      .finally(() => setLoading(false));
  }, [cursor]);

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);
  const retry = useCallback(() => {
    if (failedMode.current === "more") loadMore();
    else reload();
  }, [loadMore, reload]);

  return { items, loading, error, hasMore: Boolean(cursor), loadMore, retry, reload, setItems };
}
