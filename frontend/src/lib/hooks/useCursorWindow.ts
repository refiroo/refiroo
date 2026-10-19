import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import type { PageSelector } from "@/api/client";

/** Pages a window keeps at least (D2); beyond them the page furthest from the viewport is evicted. */
export const WINDOW_PAGES = 3;
/**
 * Rows a window holds at most, whatever its page size (0.11 X6, D156): beyond them the rows furthest
 * from the view are forgotten. A list drawn by row number (`ui/ScrollWindow`) keeps every row's
 * place, so forgetting moves nothing on screen.
 */
export const WINDOW_ROWS = 600;

/** Drops pages from `edge` while the window holds more than it keeps. */
function evict<T>(pages: HeldPage<T>[], edge: "start" | "end"): HeldPage<T>[] {
  const held = [...pages];
  let rows = held.reduce((sum, page) => sum + page.items.length, 0);
  while (held.length > WINDOW_PAGES) {
    const far = edge === "start" ? held[0] : held[held.length - 1];
    if (rows - far.items.length < WINDOW_ROWS) break;
    rows -= far.items.length;
    if (edge === "start") held.shift();
    else held.pop();
  }
  return held;
}

/** The part of a collection page the window reads (ADR-030). */
export interface WindowedPage<T> {
  items: T[];
  nextCursor: string | null;
  prevCursor?: string | null;
  anchor?: string | null;
  totalCount?: number;
  startIndex?: number;
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
  /** "keep": the rows arrived where the view already is (a far move, a reload); nothing scrolls. */
  target: "start" | "end" | "keep" | number;
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
  /**
   * The row at an absolute index, when held; while a reload is in flight, the row shown before it,
   * so the rows on screen stay until the fresh ones arrive.
   */
  itemAt: (index: number) => T | undefined;
  /**
   * The view shows rows `first`–`last` (0.11 X6, D156): pages are read toward it, one request per
   * direction at a time, until at least `ahead` rows beyond it either way are held, and on in the
   * background until the window is nearly full. A view more than `ahead` rows from the held rows
   * reads nothing until it rests (see `rest`).
   */
  show: (first: number, last: number, ahead: number) => void;
  /**
   * The view came to rest at rows `first`–`last`: when they are far from the held rows (a
   * scrollbar drag, a fling), one position read there, and the held rows become that page.
   */
  rest: (first: number, last: number, ahead: number) => void;
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
  /** The rows held before a reload, drawn where no fresh row is held yet. */
  stale?: HeldPage<T>[];
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
  return { ...state, pages: evict(pages, "start"), totalCount };
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
    pages: evict(pages, "end"),
    totalCount: state.totalCount === null ? null : Math.max(0, state.totalCount + shift),
  };
}

/**
 * A bounded, bidirectional window over a cursor-paged collection (ADR-030, Base 0.8 S5).
 *
 * The first page loads whenever `deps` change, from `options.anchor` when given, and asks for
 * totals. Every read is the reader's page (0.11 X6, D156): the size the budgets are measured at.
 * `show` reads ahead toward the view and `loadPrevious` and `loadNext` extend the window with
 * cursors; once it holds more than `WINDOW_PAGES` pages and `WINDOW_ROWS` rows the page at the
 * opposite edge is dropped, so memory stays flat however far the user scrolls. The window's edge
 * pages carry the cursors that go further, so no cursor trail is kept. Jumps (`jumpTo`,
 * `jumpToEnd`, `seek`) and a far move's `rest` replace the window with one request, with totals.
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
      /** Keep drawing the rows held now until fresh rows replace them (a reload). */
      keepRows = false,
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
            if (target !== "keep")
              viewportIndex.current =
                target === "start" ? 0 : target === "end" ? startIndex + Math.max(0, page.items.length - 1) : target;
            const previous = stateRef.current;
            const next: WindowState<T> = {
              key: requestKey,
              pages: [hold(page, startIndex)],
              totalCount: page.totalCount ?? null,
              landing: { token: ++landingSeq.current, target, focus },
              stale: keepRows && previous?.key === requestKey ? previous.pages : undefined,
            };
            // The view's layout effects extend the window before this hook's effects run, so the
            // ref must already hold the new window when they read its edge cursors.
            stateRef.current = next;
            setState(next);
            setStatus({ key: requestKey, loading: false, error: "" });
          })
          .catch((cause) => {
            if (requestId !== generation.current) return;
            if (restartable && isApiError(cause, "INVALID_CURSOR")) {
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
    // The rows keep their places (0.11 X6): the view stays where it is and draws the rows it held
    // until the pages around it are read again. A list whose cursors bind its content (a
    // restructuring plan) can outlive them: reopen at the start.
    replace(cursor ? { cursor } : {}, () => "keep", undefined, true, true);
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
          // A page at an edge is drawn in the background: rendering it with the rows held must not
          // hold up the reader's scrolling (reported 2026-10-19), and it lands off screen anyway.
          startTransition(() => {
            setState((previous) => {
              // Apply the page only to the window whose edge it continues.
              const current = edge === "after" ? previous?.pages.at(-1)?.nextCursor : previous?.pages[0]?.prevCursor;
              if (!previous || current !== cursor) return previous;
              const next = edge === "after" ? append(previous, page) : prepend(previous, page);
              stateRef.current = next;
              return next;
            });
            setEdge(IDLE);
          });
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
    // A jump to rows already held is the latest: a read still in flight (an earlier jump) is
    // dropped, or its arrival would land on top of this one (Ctrl+End, then Ctrl+Home at once).
    generation.current++;
    inFlight.current = { before: false, after: false };
    setStatus({ key: keyRef.current, loading: false, error: "" });
    setState((previous) => {
      const next = previous && { ...previous, landing: { token: ++landingSeq.current, target, focus } };
      stateRef.current = next;
      return next;
    });
  }, []);

  const show = useCallback(
    (first: number, last: number, ahead: number) => {
      const held = stateRef.current;
      if (!held || held.key !== keyRef.current || !held.pages.length) return;
      const start = held.pages[0].startIndex;
      const lastPage = held.pages.at(-1)!;
      const end = lastPage.startIndex + lastPage.items.length;
      // Far from the held rows: reading toward the view page by page would read every page in
      // between; the view's rest reads where it is instead.
      if (last < start - ahead || first >= end + ahead) return;
      // Beyond the screens the view needs, the window fills itself in the background, a budget page
      // at a time, until it holds about as much as it keeps: a list of a few hundred rows is held
      // whole a moment after it opens, so scrolling never meets a row not read (the user,
      // 2026-10-19: grey rows while scrolling 220 records). It leaves room for a page either side, so
      // filling one edge never forgets the rows the other just read.
      const rows = held.pages[0].items.length;
      const fill = Math.max(ahead, Math.floor((WINDOW_ROWS - (last - first + 1)) / 2) - 2 * rows);
      if (end <= last + fill) extend("after");
      if (start > Math.max(0, first - fill)) extend("before");
    },
    [extend],
  );

  const rest = useCallback(
    (first: number, last: number, ahead: number) => {
      const held = stateRef.current;
      if (!held || held.key !== keyRef.current || !held.pages.length || status.loading) return;
      const start = held.pages[0].startIndex;
      const lastPage = held.pages.at(-1)!;
      const end = lastPage.startIndex + lastPage.items.length;
      if (last < start - ahead || first >= end + ahead) replace({ position: Math.max(0, first) }, () => "keep");
    },
    [replace, status.loading],
  );

  const pages = current?.pages;
  const stale = current?.stale;
  const items = useMemo(() => pages?.flatMap((page) => page.items) ?? [], [pages]);
  const itemAt = useCallback(
    (index: number) => {
      for (const group of [pages, stale])
        for (const page of group ?? [])
          if (index >= page.startIndex && index < page.startIndex + page.items.length)
            return page.items[index - page.startIndex];
      return undefined;
    },
    [pages, stale],
  );
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
    itemAt,
    show,
    rest,
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

/**
 * A complete, fully loaded window over `items`: a list the browser already holds whole (the model
 * editor's attributes, relations and types, bounded by the model), shown by the same table as a
 * paged one (`ui/DataTable`). Nothing pages, so every loader is a no-op.
 */
export function fixedWindow<T>(items: T[], overrides: Partial<CursorWindow<T>> = {}): CursorWindow<T> {
  const noop = () => undefined;
  return {
    items,
    startIndex: 0,
    totalCount: items.length,
    hasPrevious: false,
    hasNext: false,
    loading: false,
    error: "",
    before: { loading: false, error: "" },
    after: { loading: false, error: "" },
    landing: undefined,
    loadPrevious: noop,
    loadNext: noop,
    itemAt: (index) => items[index],
    show: noop,
    rest: noop,
    jumpTo: noop,
    jumpToStart: noop,
    jumpToEnd: noop,
    seek: noop,
    retry: noop,
    reload: noop,
    setViewportIndex: noop,
    anchorAt: () => undefined,
    ...overrides,
  };
}
