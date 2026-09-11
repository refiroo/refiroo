import { useEffect, useRef, useState } from "react";
import { errorMessage } from "@/api/errors";
import type { CursorPage } from "@/lib/hooks/useCursorFeed";

export interface CursorPages<T> {
  items: T[];
  loading: boolean;
  error: string;
  /** One-based number of the successfully loaded page, or the initial requested page. */
  pageNumber: number;
  hasNext: boolean;
  next: () => void;
  previous: () => void;
  /** Repeats the requested page, including a failed next-page request. */
  retry: () => void;
}

/**
 * Owns forward/backward cursor movement. Query changes reset local paging and hide
 * the previous query's data. Failed reads retain the last successful page of the
 * same query. Optional controlled cursors let a collection persist its position
 * in its route; callers reset those cursors when changing the query.
 */
export function useCursorPages<T>(
  fetchPage: ((cursor?: string) => Promise<CursorPage<T>>) | null,
  deps: React.DependencyList,
  position?: { cursors: string[]; onChange: (cursors: string[]) => void },
  refreshToken = 0,
): CursorPages<T> {
  const key = JSON.stringify(deps);
  const [paging, setPaging] = useState<{ key: string; cursors: string[] }>({ key, cursors: [] });
  const cursors = position?.cursors ?? (paging.key === key ? paging.cursors : []);
  const cursor = cursors.at(-1);
  const index = cursors.length;
  const [result, setResult] = useState<{ key: string; index: number; page: CursorPage<T> }>();
  const [retryToken, setRetryToken] = useState(0);
  const requestKey = JSON.stringify([key, cursors, retryToken, refreshToken]);
  const [status, setStatus] = useState({ requestKey, loading: true, error: "" });
  const fetchRef = useRef(fetchPage);
  const enabled = fetchPage !== null;

  useEffect(() => {
    fetchRef.current = fetchPage;
  });

  useEffect(() => {
    const load = fetchRef.current;
    if (!load) return;
    let alive = true;
    setStatus({ requestKey, loading: true, error: "" });
    load(cursor)
      .then((page) => {
        if (!alive) return;
        setResult({ key, index, page });
        setStatus({ requestKey, loading: false, error: "" });
      })
      .catch((cause) => {
        if (alive) setStatus({ requestKey, loading: false, error: errorMessage(cause) });
      });
    return () => {
      alive = false;
    };
  }, [key, index, cursor, requestKey, enabled]);

  const loaded = enabled && result?.key === key ? result : undefined;
  const loading = enabled && (status.requestKey !== requestKey || status.loading);
  const error = enabled && status.requestKey === requestKey ? status.error : "";
  function move(next: string[]) {
    if (position) position.onChange(next);
    else setPaging({ key, cursors: next });
  }

  return {
    items: loaded?.page.items ?? [],
    loading,
    error,
    pageNumber: (loaded?.index ?? index) + 1,
    hasNext: !loading && !error && Boolean(loaded?.page.nextCursor),
    next: () => {
      if (!loading && !error && loaded?.page.nextCursor) move([...cursors, loaded.page.nextCursor]);
    },
    previous: () => {
      if (!loading) move(cursors.slice(0, -1));
    },
    retry: () => setRetryToken((token) => token + 1),
  };
}
