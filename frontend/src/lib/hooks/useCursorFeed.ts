import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "@/api/errors";

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
  const key = JSON.stringify(deps);
  const [loadedKey, setLoadedKey] = useState<string>();
  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  // The caller rebuilds both closures every render. Holding them in refs keeps the request
  // identity out of the dependency list, so the feed reloads only when `deps` say to.
  const fetchRef = useRef(fetchPage);
  const mergeRef = useRef(merge);
  const failedMode = useRef<"reload" | "more">("reload");
  const requestGeneration = useRef(0);

  // Declared before the loading effect so React runs it first, leaving both refs on this render's
  // closures before anything reads them. Assigning during render would be a render-phase write.
  useEffect(() => {
    fetchRef.current = fetchPage;
    mergeRef.current = merge;
  });

  useEffect(() => {
    let active = true;
    const generation = ++requestGeneration.current;
    setLoading(true);
    setError("");
    fetchRef
      .current(undefined)
      .then((page) => {
        if (!active || requestGeneration.current !== generation) return;
        setLoadedKey(key);
        setItems(mergeRef.current([], page.items));
        setCursor(page.nextCursor ?? undefined);
      })
      .catch((cause) => {
        if (!active || requestGeneration.current !== generation) return;
        failedMode.current = "reload";
        setError(errorMessage(cause));
      })
      .finally(() => {
        if (active && requestGeneration.current === generation) setLoading(false);
      });
    return () => {
      active = false;
      if (requestGeneration.current === generation) requestGeneration.current += 1;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the caller declares the reload keys
  }, [...deps, reloadToken]);

  const loadMore = useCallback(() => {
    if (!cursor || loadedKey !== key || loading) return;
    const generation = requestGeneration.current;
    setLoading(true);
    setError("");
    fetchRef
      .current(cursor)
      .then((page) => {
        if (requestGeneration.current !== generation) return;
        setItems((current) => mergeRef.current(current, page.items));
        setCursor(page.nextCursor ?? undefined);
      })
      .catch((cause) => {
        if (requestGeneration.current !== generation) return;
        failedMode.current = "more";
        setError(errorMessage(cause));
      })
      .finally(() => {
        if (requestGeneration.current === generation) setLoading(false);
      });
  }, [cursor, key, loadedKey, loading]);

  const reload = useCallback(() => {
    requestGeneration.current += 1;
    setReloadToken((token) => token + 1);
  }, []);
  const retry = useCallback(() => {
    if (failedMode.current === "more") loadMore();
    else reload();
  }, [loadMore, reload]);

  return {
    items: loadedKey === key ? items : [],
    loading,
    error,
    hasMore: loadedKey === key && Boolean(cursor),
    loadMore,
    retry,
    reload,
    setItems,
  };
}
