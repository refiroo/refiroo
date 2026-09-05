import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../../api/errors";
import type { CursorPage } from "./useCursorFeed";

export interface CursorPages<T> {
  /** Items on the page currently shown. */
  items: T[];
  loading: boolean;
  error: string;
  /** One-based number of the page currently shown. */
  pageNumber: number;
  /** True when the server reported a cursor for a further page. */
  hasNext: boolean;
  next: () => void;
  previous: () => void;
  /** Repeats the request for the current page. */
  retry: () => void;
}

/**
 * One page at a time over a cursor-paged collection, with backward movement.
 *
 * The API is forward-only, so moving back is served by remembering the cursor that opened each
 * page. `deps` identify the query; when they change the stack resets to the first page.
 *
 * That reset is derived during render rather than applied by an effect. Resetting in an effect
 * would leave one render in which a new query is paired with the previous query's cursor, and the
 * request for that pair would be sent before the correction landed.
 *
 * Pass `null` as `fetchPage` when the caller has nothing to query yet; the hook then holds its
 * empty state rather than issuing a request.
 *
 * Collections that only ever grow downwards use `useCursorFeed` instead.
 */
export function useCursorPages<T>(
  fetchPage: ((cursor?: string) => Promise<CursorPage<T>>) | null,
  deps: React.DependencyList,
): CursorPages<T> {
  const key = JSON.stringify(deps);
  const [paging, setPaging] = useState<{ key: string; cursors: Array<string | undefined>; index: number }>({
    key,
    cursors: [undefined],
    index: 0,
  });
  const active = paging.key === key ? paging : { key, cursors: [undefined], index: 0 };
  const cursor = active.cursors[active.index];

  const [page, setPage] = useState<CursorPage<T>>({ items: [], nextCursor: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryToken, setRetryToken] = useState(0);

  const fetchRef = useRef(fetchPage);
  fetchRef.current = fetchPage;
  const enabled = fetchPage !== null;

  useEffect(() => {
    setPaging({ key, cursors: [undefined], index: 0 });
  }, [key]);

  useEffect(() => {
    const load = fetchRef.current;
    if (!load) return;
    let alive = true;
    setLoading(true);
    setError("");
    load(cursor)
      .then((loaded) => {
        if (alive) setPage(loaded);
      })
      .catch((cause) => {
        if (alive) setError(errorMessage(cause));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the caller declares the query keys
  }, [key, active.index, cursor, retryToken, enabled]);

  return {
    items: page.items,
    loading,
    error,
    pageNumber: active.index + 1,
    hasNext: Boolean(page.nextCursor),
    next: () => {
      if (!page.nextCursor) return;
      setPaging({
        key,
        cursors: [...active.cursors.slice(0, active.index + 1), page.nextCursor],
        index: active.index + 1,
      });
    },
    previous: () => setPaging({ ...active, index: Math.max(0, active.index - 1) }),
    retry: () => setRetryToken((token) => token + 1),
  };
}
