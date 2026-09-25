import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import type { PageSelector } from "@/api/client";

/** Pages a window keeps (D2); beyond this the page furthest from the viewport is evicted. */
export const WINDOW_PAGES = 5;

/** The part of a collection page the window reads (ADR-030). */
export interface WindowedPage<T> {
  items: T[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number | null;
  startIndex?: number | null;
}

interface HeldPage<T> {
  items: T[];
  prevCursor: string | null;
  nextCursor: string | null;
  anchor: string | null;
  /** Absolute index of the page's first row in the filtered, sorted list. */
  startIndex: number;
}

/**
 * Where the view should scroll after the window was replaced or asked to move: the start, the end,
 * or the row at an absolute index brought to the top. `focus` asks the view to focus that row.
 */
export interface WindowLanding {
  token: number;
  target: "start" | "end" | number;
  focus?: "first" | "last" | "target";
}

export interface EdgeStatus {
  loading: boolean;
  error: string;
}

export interface CursorWindow<T> {
  /** The rows held, in list order. */
  items: T[];
  /** Absolute index of `items[0]`. */
  startIndex: number;
  /** Rows in the whole filtered list, when known. */
  totalCount: number | null;
  hasPrevious: boolean;
  hasNext: boolean;
  /** True while the first page, a jump or a refresh is in flight. */
  loading: boolean;
  /** Failure of the first page, a jump or a refresh; "" otherwise. */
  error: string;
  before: EdgeStatus;
  after: EdgeStatus;
  landing: WindowLanding | undefined;
  loadPrevious: () => void;
  loadNext: () => void;
  /** Brings the row at `index` to the top, with one position request unless it is already held. */
  jumpTo: (index: number, focus?: boolean) => void;
  jumpToStart: (focus?: boolean) => void;
  jumpToEnd: (focus?: boolean) => void;
  /** Starts at the first row whose sort value is at or after `value`. */
  seek: (value: string) => void;
  /** Repeats whichever request failed. */
  retry: () => void;
  /** Re-reads the page at the viewport, with totals, keeping the window's place. */
  reload: () => void;
  /** Records the absolute index of the first visible row; read by reloads and `anchorAt`. */
  setViewportIndex: (index: number) => void;
  /** The cursor that reopens the page holding `index`, or undefined on the first page. */
  anchorAt: (index: number) => string | undefined;
}

interface WindowState<T> {
  key: string;
  pages: HeldPage<T>[];
  totalCount: number | null;
  landing?: WindowLanding;
}

const IDLE: EdgeStatus = { loading: false, error: "" };

function hold<T>(page: WindowedPage<T>, startIndex: number): HeldPage<T> {
  return {
    items: page.items,
    prevCursor: page.prevCursor ?? null,
    nextCursor: page.nextCursor ?? null,
    anchor: page.anchor ?? null,
    startIndex,
  };
}

function append<T>(state: WindowState<T>, page: WindowedPage<T>): WindowState<T> {
  const last = state.pages.at(-1)!;
  const startIndex = last.startIndex + last.items.length;
  const end = startIndex + page.items.length;
  // Reaching the end counts the list exactly; until then totals only grow with what was seen.
  const totalCount = !page.nextCursor ? end : state.totalCount === null ? null : Math.max(state.totalCount, end);
  if (page.items.length === 0)
    return { ...state, pages: [...state.pages.slice(0, -1), { ...last, nextCursor: null }], totalCount };
  const pages = [...state.pages, hold(page, startIndex)];
  return { ...state, pages: pages.slice(Math.max(0, pages.length - WINDOW_PAGES)), totalCount };
}

function prepend<T>(state: WindowState<T>, page: WindowedPage<T>): WindowState<T> {
  const first = state.pages[0];
  const startIndex = first.startIndex - page.items.length;
  // Reaching the start fixes the first row at index 0; rows inserted or deleted before the window
  // since it was counted shift every held index and the total by the same amount.
  const shift = !page.prevCursor || page.items.length === 0 ? -startIndex : Math.max(0, -startIndex);
  const pages = (
    page.items.length === 0
      ? [{ ...first, prevCursor: null }, ...state.pages.slice(1)]
      : [hold(page, startIndex), ...state.pages]
  ).map((held) => ({ ...held, startIndex: held.startIndex + shift }));
  return {
    ...state,
    pages: pages.slice(0, WINDOW_PAGES),
    totalCount: state.totalCount === null ? null : Math.max(0, state.totalCount + shift),
  };
}

/**
 * A bounded, bidirectional window over a cursor-paged collection (ADR-030, Base 0.8 S5).
 *
 * The first page loads whenever `deps` change, from `options.anchor` when given, and asks for
 * totals. `loadPrevious` and `loadNext` extend the window with cursors; once it holds more than
 * `WINDOW_PAGES` pages the page at the opposite edge is dropped, so memory stays flat however far
 * the user scrolls. The window's edge pages carry the cursors that go further, so no cursor trail
 * is kept. Jumps (`jumpTo`, `jumpToEnd`, `seek`) replace the window with one request, with totals.
 *
 * The anchor is read only when the query changes, so a caller may write the current anchor back
 * into its route without reloading the list. `fetchPage` is read through a ref.
 */
export function useCursorWindow<T>(
  fetchPage: ((selector: PageSelector) => Promise<WindowedPage<T>>) | null,
  deps: React.DependencyList,
  options: { anchor?: string; refreshToken?: number } = {},
): CursorWindow<T> {
  const key = JSON.stringify(deps);
  const enabled = fetchPage !== null;
  const [state, setState] = useState<WindowState<T>>();
  const [status, setStatus] = useState({ key, loading: true, error: "" });
  const [before, setBefore] = useState<EdgeStatus>(IDLE);
  const [after, setAfter] = useState<EdgeStatus>(IDLE);
  const fetchRef = useRef(fetchPage);
  const anchorRef = useRef(options.anchor);
  const stateRef = useRef(state);
  const keyRef = useRef(key);
  const generation = useRef(0);
  const landingSeq = useRef(0);
  const inFlight = useRef({ before: false, after: false });
  const failed = useRef<(() => void) | undefined>(undefined);
  const viewportIndex = useRef(0);

  // Declared before the loading effects so they read this render's closures and state.
  useEffect(() => {
    fetchRef.current = fetchPage;
    anchorRef.current = options.anchor;
    stateRef.current = state;
    keyRef.current = key;
  });

  const current = state?.key === key ? state : undefined;

  const replace = useCallback(
    (
      selector: PageSelector,
      target: (startIndex: number) => WindowLanding["target"],
      focus?: WindowLanding["focus"],
      /** Reopen at the start when the selector's cursor is no longer valid. */
      startOnInvalidCursor = false,
    ) => {
      const read = (
        request: PageSelector,
        landAt: (startIndex: number) => WindowLanding["target"],
        restartable: boolean,
      ): void => {
        const load = fetchRef.current;
        if (!load) return;
        const requestKey = keyRef.current;
        const requestId = ++generation.current;
        inFlight.current = { before: false, after: false };
        setBefore(IDLE);
        setAfter(IDLE);
        setStatus({ key: requestKey, loading: true, error: "" });
        load({ ...request, includeTotal: true })
          .then((page) => {
            if (requestId !== generation.current) return;
            // A position past the end, or an anchored page whose rows were all deleted, lands on
            // the last page instead of an empty window with rows before it.
            if (page.items.length === 0 && page.prevCursor && !request.fromEnd) {
              read({ fromEnd: true }, () => "end", false);
              return;
            }
            const startIndex = page.startIndex ?? 0;
            const target = landAt(startIndex);
            // Until the view measures (it may be hidden), the landing is where the viewport is.
            viewportIndex.current =
              target === "start" ? 0 : target === "end" ? startIndex + Math.max(0, page.items.length - 1) : target;
            const next: WindowState<T> = {
              key: requestKey,
              pages: [hold(page, startIndex)],
              totalCount: page.totalCount ?? null,
              landing: { token: ++landingSeq.current, target, focus },
            };
            // The view's layout effects extend the window before this hook's effects run, so the
            // ref must already hold the new window when they read its edge cursors.
            stateRef.current = next;
            setState(next);
            setStatus({ key: requestKey, loading: false, error: "" });
          })
          .catch((cause) => {
            if (requestId !== generation.current) return;
            if (restartable && isApiError(cause, "invalid_cursor")) {
              read({}, () => "start", false);
              return;
            }
            failed.current = () => read(request, landAt, false);
            setStatus({ key: requestKey, loading: false, error: errorMessage(cause) });
          });
      };
      read(selector, target, startOnInvalidCursor);
    },
    [],
  );

  useEffect(() => {
    if (!fetchRef.current) return;
    const anchor = anchorRef.current;
    // A copied URL can outlive its cursor (another release, a changed filter): open at the start.
    if (anchor) replace({ cursor: anchor }, (start) => start, undefined, true);
    else replace({}, () => "start");
  }, [key, enabled, replace]);

  const reload = useCallback(() => {
    const held = stateRef.current;
    if (!held || held.key !== keyRef.current) return;
    const index = viewportIndex.current;
    const page = held.pages.find((item) => index >= item.startIndex && index < item.startIndex + item.items.length);
    const cursor = page && page.prevCursor ? (page.anchor ?? undefined) : undefined;
    replace(cursor ? { cursor } : {}, (start) => (cursor ? Math.max(start, index) : index > 0 ? index : "start"));
  }, [replace]);

  const refreshToken = options.refreshToken ?? 0;
  const lastRefresh = useRef(refreshToken);
  useEffect(() => {
    if (lastRefresh.current === refreshToken) return;
    lastRefresh.current = refreshToken;
    reload();
  }, [refreshToken, reload]);

  const extend = useCallback((edge: "before" | "after") => {
    const attempt = (): void => {
      const held = stateRef.current;
      const load = fetchRef.current;
      if (!held || held.key !== keyRef.current || !load || inFlight.current[edge]) return;
      const cursor = edge === "after" ? held.pages.at(-1)?.nextCursor : held.pages[0]?.prevCursor;
      if (!cursor) return;
      const request = generation.current;
      const setEdge = edge === "after" ? setAfter : setBefore;
      inFlight.current[edge] = true;
      setEdge({ loading: true, error: "" });
      load({ cursor })
        .then((page) => {
          if (request !== generation.current) return;
          inFlight.current[edge] = false;
          setState((previous) => {
            // Apply the page only to the window whose edge it continues.
            const current = edge === "after" ? previous?.pages.at(-1)?.nextCursor : previous?.pages[0]?.prevCursor;
            if (!previous || current !== cursor) return previous;
            const next = edge === "after" ? append(previous, page) : prepend(previous, page);
            stateRef.current = next;
            return next;
          });
          setEdge(IDLE);
        })
        .catch((cause) => {
          if (request !== generation.current) return;
          inFlight.current[edge] = false;
          failed.current = attempt;
          setEdge({ loading: false, error: errorMessage(cause) });
        });
    };
    attempt();
  }, []);

  const land = useCallback((target: WindowLanding["target"], focus?: WindowLanding["focus"]) => {
    setState((previous) => {
      const next = previous && { ...previous, landing: { token: ++landingSeq.current, target, focus } };
      stateRef.current = next;
      return next;
    });
  }, []);

  const pages = current?.pages;
  const items = useMemo(() => pages?.flatMap((page) => page.items) ?? [], [pages]);
  const first = pages?.[0];
  const last = pages?.at(-1);
  const startIndex = first?.startIndex ?? 0;
  const totalCount = current?.totalCount ?? null;
  const hasPrevious = Boolean(first?.prevCursor);
  const hasNext = Boolean(last?.nextCursor);

  const jumpTo = useCallback(
    (index: number, focus?: boolean) => {
      const held = stateRef.current;
      const total = held?.totalCount;
      const target = Math.max(0, total ? Math.min(index, total - 1) : index);
      const heldFirst = held?.pages[0];
      const heldLast = held?.pages.at(-1);
      if (
        heldFirst &&
        heldLast &&
        target >= heldFirst.startIndex &&
        target < heldLast.startIndex + heldLast.items.length
      )
        land(target, focus ? "target" : undefined);
      else replace({ position: target }, (start) => start, focus ? "target" : undefined);
    },
    [land, replace],
  );
  const jumpToStart = useCallback(
    (focus?: boolean) => {
      const heldFirst = stateRef.current?.pages[0];
      if (heldFirst && heldFirst.startIndex === 0 && !heldFirst.prevCursor) land("start", focus ? "first" : undefined);
      else replace({}, () => "start", focus ? "first" : undefined);
    },
    [land, replace],
  );
  const jumpToEnd = useCallback(
    (focus?: boolean) => {
      const heldLast = stateRef.current?.pages.at(-1);
      if (heldLast && !heldLast.nextCursor) land("end", focus ? "last" : undefined);
      else replace({ fromEnd: true }, () => "end", focus ? "last" : undefined);
    },
    [land, replace],
  );
  const seek = useCallback((value: string) => replace({ seek: value }, (start) => start), [replace]);

  const anchorAt = useCallback(
    (index: number) => {
      const page = pages?.find((item) => index >= item.startIndex && index < item.startIndex + item.items.length);
      return page && page.prevCursor ? (page.anchor ?? undefined) : undefined;
    },
    [pages],
  );

  return {
    items: enabled ? items : [],
    startIndex,
    totalCount,
    hasPrevious: enabled && hasPrevious,
    hasNext: enabled && hasNext,
    loading: enabled && (status.key !== key || status.loading),
    error: enabled && status.key === key ? status.error : "",
    before: current ? before : IDLE,
    after: current ? after : IDLE,
    landing: current?.landing,
    loadPrevious: useCallback(() => extend("before"), [extend]),
    loadNext: useCallback(() => extend("after"), [extend]),
    jumpTo,
    jumpToStart,
    jumpToEnd,
    seek,
    retry: useCallback(() => failed.current?.(), []),
    reload,
    setViewportIndex: useCallback((index: number) => {
      viewportIndex.current = index;
    }, []),
    anchorAt,
  };
}
