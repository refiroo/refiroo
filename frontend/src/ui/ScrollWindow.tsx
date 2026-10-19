/**
 * The scrolling viewport of a continuous list (ADR-030, Base 0.8 S5), addressed by row number
 * (0.11 X6, D156, D161–D163).
 *
 * The scroll space spans the whole list, sized from its total, so every row has its place before
 * its data arrives and the browser's own scrollbar is the list's. Only the rows on screen and one
 * screen either side are drawn, between two spacers that hold the height of the rest: a row not
 * read yet is drawn as a placeholder at its place. `@tanstack/react-virtual` decides what is drawn
 * where: it measures each drawn row (rows wrap, so heights differ), draws a row it has not measured
 * at the average height, and corrects the scroll position when a row above the view changes height,
 * so the first row in view stays exactly where it was. A forgotten row keeps its measured height as
 * a placeholder, so pages arriving and rows forgotten move no other row.
 *
 * The data stays with the `useCursorWindow`: the view reports the rows it shows, and the window
 * reads budget pages ahead of it; a far move (a scrollbar drag, a fling, a page field) reads the
 * page where the view comes to rest, once. Jumps land by row number.
 *
 * A wheel over the list first brings the whole list, with its footer, into view in whatever scrolls
 * around it (the page, a pane, a dialog), and only then scrolls the rows; at the rows' first or last
 * row the wheel carries on to the page. The list is never a place the wheel gets stuck in (reported
 * 2026-10-19), and its height leaves room for the page's sticky top and the footer (CSS).
 *
 * `children` draws the rows `ScrollWindow` hands it: a `WindowSpacer` before and after, and each
 * row with data carrying `ref={drawn.measure}`, `data-row-key` (a stable identity) and
 * `data-row-index` (its absolute index); a row without data is a `WindowPlaceholder`. An element
 * inside a row marked `data-row-focus` receives keyboard focus, otherwise the row itself does and
 * needs `tabIndex={-1}`. In a grid, cells marked `data-grid-col` keep their column: Up and Down from
 * one focus the same column of the next row, across page edges too.
 */

import { useVirtualizer } from "@tanstack/react-virtual";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { Icon } from "@/ui/Icon";

const numberFormat = new Intl.NumberFormat();
const format = (value: number) => numberFormat.format(value);

/** A row's height before any row of the list was measured. */
const FIRST_ESTIMATE = 41;
/** How long the view holds still before a far move reads where it rests (D156). */
const REST_MS = 120;
/** How long after the reader's own wheel, pointer, touch or key the list's scrolling is theirs. */
const GESTURE_MS = 1000;

/**
 * Height the sticky table header covers once the list is scrolled. A landed or revealed row is
 * placed below it.
 */
function stuckHeader(viewport: HTMLElement) {
  return viewport.querySelector("thead")?.getBoundingClientRect().height ?? 0;
}

/** The nearest element that scrolls `element`'s box, or the page. */
function outerScroller(element: HTMLElement): HTMLElement {
  for (let node = element.parentElement; node && node !== document.body; node = node.parentElement) {
    const { overflowY } = getComputedStyle(node);
    if ((overflowY === "auto" || overflowY === "scroll") && node.scrollHeight > node.clientHeight + 1) return node;
  }
  return (document.scrollingElement as HTMLElement | null) ?? document.documentElement;
}

/** The part of `scroller` the reader sees: below the page's sticky top bar and band, for the page. */
function visibleArea(scroller: HTMLElement) {
  if (scroller !== document.scrollingElement && scroller !== document.documentElement) {
    const box = scroller.getBoundingClientRect();
    return { top: box.top, bottom: box.bottom };
  }
  const style = getComputedStyle(document.documentElement);
  const covered =
    (parseFloat(style.getPropertyValue("--topbar-height")) || 0) +
    (parseFloat(style.getPropertyValue("--band-height")) || 0);
  return { top: covered, bottom: window.innerHeight };
}

/** Whether `element` belongs to this viewport rather than to a window nested inside its rows. */
const own = (viewport: HTMLElement, element: Element) => element.closest(".scroll-window-viewport") === viewport;

/** The drawn rows of this viewport with data, which take focus. */
function ownRows(viewport: HTMLElement) {
  return Array.from(viewport.querySelectorAll<HTMLElement>("[data-row-key]")).filter((row) => own(viewport, row));
}

/** The row of this viewport that holds `target`, which may sit inside a nested window. */
function ownRow(viewport: HTMLElement, target: HTMLElement) {
  for (let row = target.closest<HTMLElement>("[data-row-key]"); row;) {
    if (own(viewport, row)) return row;
    row = row.parentElement?.closest<HTMLElement>("[data-row-key]") ?? null;
  }
  return null;
}

/** How many rows above the view have not been measured (the virtualizer keys rows by index). */
function unmeasuredAbove(instance: {
  scrollOffset: number | null;
  itemSizeCache: Map<unknown, number>;
  getVirtualItemForOffset: (offset: number) => { index: number } | undefined;
}) {
  const top = instance.getVirtualItemForOffset(instance.scrollOffset ?? 0)?.index ?? 0;
  let measured = 0;
  for (const key of instance.itemSizeCache.keys()) if (typeof key === "number" && key < top) measured++;
  return top - measured;
}

/** One row to draw: its absolute index, its data when held, and its height. */
export interface DrawnRow<T> {
  index: number;
  item: T | undefined;
  size: number;
}

/** What a surface draws: the rows in range and the heights of the rest (D162). */
export interface DrawnRange<T> {
  rows: DrawnRow<T>[];
  /** Height of the rows before the drawn ones, for the leading `WindowSpacer`. */
  before: number;
  /** Height of the rows after them, for the trailing `WindowSpacer`. */
  after: number;
  /** The ref of a drawn row with data, which measures it. */
  measure: (element: Element | null) => void;
}

interface Visible {
  first: number;
  last: number;
}

export function ScrollWindow<T>({
  list,
  label,
  noun,
  pageSize,
  className = "",
  seekLabel,
  rowNavigation = true,
  footer = true,
  edgeMarkers = "always",
  onAnchorChange,
  children,
}: {
  list: CursorWindow<T>;
  /** Accessible name of the scrolling region. */
  label: string;
  /** Singular and plural noun for the rows, for example ["record", "records"]. */
  noun: [string, string];
  pageSize: number;
  className?: string;
  /** Names the sorted value a "Go to" field seeks by; omitted where the list does not seek. */
  seekLabel?: string;
  /** Arrow keys move focus between rows; off where the rows handle arrows themselves. */
  rowNavigation?: boolean;
  footer?: boolean;
  /** "partial" shows the start and end markers only for a list longer than one page. */
  edgeMarkers?: "always" | "partial";
  /** Receives the cursor that reopens the viewport's page, for the URL. */
  onAnchorChange?: (anchor: string | undefined) => void;
  children: (drawn: DrawnRange<T>) => ReactNode;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState<Visible>();
  const [announcement, setAnnouncement] = useState("");
  const [overflowing, setOverflowing] = useState(false);
  const [screen, setScreen] = useState(0);
  const [margin, setMargin] = useState(0);
  const [header, setHeader] = useState(0);
  const handledLanding = useRef<number | undefined>(undefined);
  const pendingFocus = useRef<{ index: number; column?: string } | undefined>(undefined);
  const focusedKey = useRef<string | undefined>(undefined);
  const frame = useRef(0);
  const restTimer = useRef(0);
  const listRef = useRef(list);
  const anchorCallback = useRef(onAnchorChange);
  const reportedAnchor = useRef<string | undefined>(undefined);
  const anchorTimer = useRef(0);
  const visibleRef = useRef<Visible | undefined>(undefined);
  // The URL anchor and the refresh position follow the reader, not the list's own scrolling: they
  // change on a jump or when the reader scrolls, never when a landing or a height correction does.
  const gesture = useRef(0);
  const userMoved = useRef(false);
  const average = useRef({ size: FIRST_ESTIMATE, rows: 0 });
  // Where the rows start, as last measured; undefined until the list has measured it once.
  const measuredMargin = useRef<number | undefined>(undefined);
  // The row a jump landed on, held in its place until the reader moves (see the landing below).
  const pinned = useRef<{ index: number; align: "start" | "end" } | undefined>(undefined);

  // A layout effect, declared first, so the landing and the reads below see this render's list.
  useLayoutEffect(() => {
    listRef.current = list;
    anchorCallback.current = onAnchorChange;
  });

  const [singular, plural] = noun;
  const total = list.totalCount;
  const held = list.startIndex + list.items.length;
  // Without a total, one more place stands for the rows not read yet.
  const count =
    list.loading && list.items.length === 0 ? 0 : Math.max(total ?? 0, held + (total === null && list.hasNext ? 1 : 0));

  const virtualizer = useVirtualizer<HTMLDivElement, Element>({
    count,
    getScrollElement: () => viewport.current,
    estimateSize: () => average.current.size,
    // One screen either side of the view (D156).
    overscan: Math.max(5, Math.ceil(screen / average.current.size)),
    indexAttribute: "data-row-index",
    scrollMargin: margin,
    scrollPaddingStart: header,
    // A row's exact height: the library's own measure rounds it to a whole pixel, and rows of 41.3 px
    // then shortened the spacer above by 0.3 px for every row it took over, so the rows under the
    // reader rose as the list scrolled (found by s5's walk, D164).
    // Read once per row: a row already measured keeps its height when it is drawn again, and a
    // change is reported by the resize observer the virtualizer keeps, without reading the page.
    measureElement: (element, entry, instance) => {
      const observed = entry?.borderBoxSize?.[0]?.blockSize;
      const known =
        observed === undefined
          ? instance.itemSizeCache.get(instance.options.getItemKey(instance.indexFromElement(element)))
          : undefined;
      const size = observed ?? known ?? element.getBoundingClientRect().height;
      // The estimate places every row not measured yet, so it may change only while no such row is
      // above the view: after a jump far into the list it would move every row above the reader
      // (a reopened link landed three rows early, found by s7).
      if (size > 0 && unmeasuredAbove(instance) === 0) {
        const { size: mean, rows } = average.current;
        average.current = { size: (mean * rows + size) / (rows + 1), rows: Math.min(rows + 1, 200) };
      }
      return size;
    },
  });
  const virtualRows = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();
  const firstRow = virtualRows[0];
  const lastRow = virtualRows.at(-1);
  // A viewport with no height (hidden, or not laid out) has no range to draw: it draws the rows
  // held, as a list drawn whole would.
  const drawn: DrawnRange<T> =
    screen > 0
      ? {
          rows: virtualRows.map((row) => ({ index: row.index, item: list.itemAt(row.index), size: row.size })),
          before: firstRow ? Math.max(0, firstRow.start - margin) : 0,
          after: lastRow ? Math.max(0, totalSize - (lastRow.end - margin)) : 0,
          measure: virtualizer.measureElement,
        }
      : {
          rows: list.items.map((item, position) => ({
            index: list.startIndex + position,
            item,
            size: average.current.size,
          })),
          before: list.startIndex * average.current.size,
          after: Math.max(0, count - held) * average.current.size,
          measure: virtualizer.measureElement,
        };

  /** Makes `index` the list's place: what a refresh re-reads and, once at rest, the URL anchor. */
  const follow = useCallback(
    (index: number) => {
      listRef.current.setViewportIndex(index);
      window.clearTimeout(anchorTimer.current);
      anchorTimer.current = window.setTimeout(() => {
        const anchor = listRef.current.anchorAt(index);
        // A place whose page is not held yet keeps the anchor reported before it.
        if (anchor === undefined && index >= pageSize) return;
        if (anchor === reportedAnchor.current) return;
        reportedAnchor.current = anchor;
        anchorCallback.current?.(anchor);
      }, 400);
    },
    [pageSize],
  );

  /**
   * The rows on screen, from the scroll position and the rows' places (the virtualizer's arithmetic,
   * nothing read from the page), and the pages read around them. Called on every scroll frame.
   */
  const track = useCallback(() => {
    const element = viewport.current;
    const current = listRef.current;
    const rect = virtualizer.scrollRect;
    if (!element || !rect || rect.height <= 0) return;
    const offset = virtualizer.scrollOffset ?? element.scrollTop;
    // The sticky header covers the top of the view.
    const firstRow = virtualizer.getVirtualItemForOffset(offset + header + 1);
    const lastRow = virtualizer.getVirtualItemForOffset(offset + rect.height - 1);
    if (!firstRow || !lastRow || lastRow.index < firstRow.index) return;
    const range = { first: firstRow.index, last: lastRow.index };
    visibleRef.current = range;
    setVisible((previous) => (previous?.first === range.first && previous.last === range.last ? previous : range));
    if (userMoved.current) follow(range.first);
    let waiting = false;
    for (let index = range.first; index <= range.last && !waiting; index++)
      waiting = current.itemAt(index) === undefined;
    setAnnouncement(waiting && !current.loading ? `Loading ${plural}…` : "");
    if (!current.loading) current.show(range.first, range.last, 2 * (range.last - range.first + 1));
  }, [virtualizer, header, plural, follow]);

  /**
   * The list's own geometry: its height, whether it overflows, and where the rows start below the
   * edge marker and the header (the virtualizer's scroll margin), with how much the sticky header
   * covers. Read after the list draws and when it resizes, never on a scroll frame.
   */
  const measure = useCallback(() => {
    const element = viewport.current;
    if (!element) return;
    setOverflowing(element.scrollHeight > element.clientHeight + 1);
    setScreen((previous) => (Math.abs(previous - element.clientHeight) > 1 ? element.clientHeight : previous));
    const spacer = element.querySelector<HTMLElement>("[data-window-spacer='before']");
    if (spacer && own(element, spacer)) {
      const offset = spacer.getBoundingClientRect().top - element.getBoundingClientRect().top + element.scrollTop;
      const covered = stuckHeader(element);
      // What stands above the rows changed height (the header, the start marker): the rows keep
      // their place on screen.
      const before = measuredMargin.current;
      if (before !== undefined && Math.abs(offset - before) > 0.5 && element.scrollTop > 0)
        element.scrollTop += offset - before;
      measuredMargin.current = offset;
      setMargin((previous) => (Math.abs(previous - offset) > 0.5 ? offset : previous));
      setHeader((previous) => (Math.abs(previous - covered) > 0.5 ? covered : previous));
    }
    track();
  }, [track]);

  const schedule = useCallback(() => {
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(measure);
  }, [measure]);

  const onScroll = useCallback(() => {
    if (Date.now() - gesture.current < GESTURE_MS) userMoved.current = true;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(track);
    // A far move reads where the view comes to rest, not every page it passed (D156).
    window.clearTimeout(restTimer.current);
    restTimer.current = window.setTimeout(() => {
      const range = visibleRef.current;
      if (range) listRef.current.rest(range.first, range.last, 2 * (range.last - range.first + 1));
    }, REST_MS);
  }, [track]);

  // A list shown again after being hidden, or resized, measures again and reads as needed.
  useEffect(() => {
    const element = viewport.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(schedule);
    observer.observe(element);
    return () => observer.disconnect();
  }, [schedule]);

  // A wheel brings the whole list into view before it scrolls the rows, where the list fits in what
  // scrolls around it (see above). At the rows' first or last row the same gesture carries on to
  // what scrolls around the list: the browser holds a gesture, with its momentum, on the element it
  // started in, so the page moved only on a second gesture (reported 2026-10-19).
  useEffect(() => {
    const element = viewport.current;
    const box = element?.closest<HTMLElement>(".scroll-window");
    if (!element || !box) return;
    const onWheel = (event: WheelEvent) => {
      gesture.current = Date.now();
      pinned.current = undefined;
      if (event.ctrlKey || event.defaultPrevented || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      const scroller = outerScroller(box);
      const area = visibleArea(scroller);
      const line = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? area.bottom - area.top : 1;
      const delta = event.deltaY * line;
      // Where the outer scroll cannot go further, the rows scroll as usual.
      const room = delta > 0 ? scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight : scroller.scrollTop;
      if (room < 1) return;
      const rect = box.getBoundingClientRect();
      const hidden = delta > 0 ? rect.bottom - area.bottom : rect.top - area.top;
      const revealing = rect.height <= area.bottom - area.top && (delta > 0 ? hidden > 1 : hidden < -1);
      const current = listRef.current;
      // The scroll space is the whole list; only a list whose total is unknown grows past its end.
      const atEdge =
        delta > 0
          ? element.scrollHeight - element.scrollTop - element.clientHeight < 1 &&
            (current.totalCount !== null || !current.hasNext)
          : element.scrollTop < 1;
      if (!revealing && !atEdge) return;
      event.preventDefault();
      const step = revealing ? (delta > 0 ? Math.min(delta, hidden) : Math.max(delta, hidden)) : delta;
      if (scroller === document.scrollingElement || scroller === document.documentElement) window.scrollBy(0, step);
      else scroller.scrollTop += step;
    };
    const onGesture = () => {
      gesture.current = Date.now();
      pinned.current = undefined;
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    element.addEventListener("pointerdown", onGesture);
    element.addEventListener("touchstart", onGesture, { passive: true });
    element.addEventListener("keydown", onGesture);
    return () => {
      element.removeEventListener("wheel", onWheel);
      element.removeEventListener("pointerdown", onGesture);
      element.removeEventListener("touchstart", onGesture);
      element.removeEventListener("keydown", onGesture);
    };
  }, []);

  useEffect(
    () => () => {
      cancelAnimationFrame(frame.current);
      window.clearTimeout(anchorTimer.current);
      window.clearTimeout(restTimer.current);
    },
    [],
  );

  const reveal = useCallback((row: HTMLElement) => {
    const element = viewport.current;
    if (!element) return;
    const box = element.getBoundingClientRect();
    const top = box.top + stuckHeader(element);
    const rect = row.getBoundingClientRect();
    // Revealing a row the reader moved to by keyboard is the reader's own movement.
    userMoved.current = true;
    if (rect.top < top) element.scrollTop -= top - rect.top;
    else if (rect.bottom > box.bottom) element.scrollTop += rect.bottom - box.bottom;
  }, []);

  const focusRow = useCallback(
    (row: HTMLElement, column?: string) => {
      const cell = column === undefined ? null : row.querySelector<HTMLElement>(`[data-grid-col="${column}"]`);
      (cell ?? row.querySelector<HTMLElement>("[data-row-focus]") ?? row).focus({ preventScroll: true });
      reveal(row);
    },
    [reveal],
  );

  /** Focuses the row at `index` once it is drawn with its data, scrolling it into view. */
  const focusIndex = useCallback(
    (index: number, column?: string) => {
      const element = viewport.current;
      const row = element && ownRows(element).find((item) => item.dataset.rowIndex === String(index));
      if (row) {
        pendingFocus.current = undefined;
        focusRow(row, column);
        return;
      }
      pendingFocus.current = { index, column };
      virtualizer.scrollToIndex(index, { align: "auto" });
      // The row next to the held ones is read now, whether or not the view reads ahead.
      const current = listRef.current;
      if (index === current.startIndex + current.items.length) current.loadNext();
      else if (index === current.startIndex - 1) current.loadPrevious();
    },
    [focusRow, virtualizer],
  );

  // Rows changed: land a jump, focus a row waited for, and read around the view.
  useLayoutEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const landing = list.landing;
    // A landing waits until the virtualizer knows where the rows start: on a fresh page it was
    // placed before the header was measured, and the rows then moved down by the header's height.
    measure();
    const placed = measuredMargin.current !== undefined && Math.abs(measuredMargin.current - margin) <= 0.5;
    if (landing && handledLanding.current !== landing.token && !list.loading && placed) {
      handledLanding.current = landing.token;
      pendingFocus.current = undefined;
      userMoved.current = false;
      pinned.current = undefined;
      let index: number | undefined;
      // Through the virtualizer, which may still be settling an earlier landing: a position written
      // behind it was scrolled back to that landing's row.
      if (landing.target === "start") {
        virtualizer.scrollToOffset(0);
        pinned.current = { index: 0, align: "start" };
        index = 0;
      } else if (landing.target === "end") {
        index = Math.max(0, count - 1);
        virtualizer.scrollToIndex(index, { align: "end" });
        pinned.current = { index, align: "end" };
      } else if (landing.target !== "keep") {
        index = landing.target;
        virtualizer.scrollToIndex(index, { align: "start" });
        pinned.current = { index, align: "start" };
      }
      if (index !== undefined && landing.token > 1) follow(index);
      if (landing.focus && index !== undefined) pendingFocus.current = { index };
      if (landing.token > 1 && landing.target !== "keep" && list.items.length)
        setAnnouncement(
          `Showing ${plural} from ${format((index ?? list.startIndex) + 1)}` +
            (list.totalCount !== null ? ` of ${format(list.totalCount)}` : ""),
        );
    }
    // The landed row stays where it landed while the rows around it are read and measured: rows
    // above it measured taller than estimated moved it down, so a reopened link showed the row
    // above (found by s5 and s7). The reader's first wheel, touch, pointer or key ends it.
    const pin = pinned.current;
    if (pin && !list.loading && handledLanding.current === list.landing?.token) {
      const wanted = virtualizer.getOffsetForIndex(pin.index, pin.align)?.[0];
      if (wanted !== undefined && Math.abs(element.scrollTop - wanted) > 0.5) virtualizer.scrollToOffset(wanted);
    }
    if (pendingFocus.current) {
      const { index, column } = pendingFocus.current;
      const row = ownRows(element).find((item) => item.dataset.rowIndex === String(index));
      if (row) {
        pendingFocus.current = undefined;
        focusRow(row, column);
      }
    }
    // A focused row scrolled out of the drawn range leaves focus with the list rather than the page.
    if (
      focusedKey.current &&
      (document.activeElement === document.body || document.activeElement === null) &&
      !ownRows(element).some((item) => item.dataset.rowKey === focusedKey.current)
    ) {
      focusedKey.current = undefined;
      element.focus({ preventScroll: true });
    }
    track();
  }, [
    margin,
    track,
    list.items,
    list.landing,
    list.loading,
    list.startIndex,
    list.totalCount,
    virtualRows,
    count,
    plural,
    virtualizer,
    focusRow,
    measure,
    follow,
  ]);

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    // A window nested in one of the rows handled the key first.
    if (event.defaultPrevented) return;
    // A row's selection checkbox takes no arrow keys, so ↑ and ↓ move to the next row's (0.9 K1).
    if (target.closest("input:not([type='checkbox']), select, textarea, [contenteditable='true'], [role='menu']"))
      return;
    if ((event.ctrlKey || event.metaKey) && (event.key === "Home" || event.key === "End")) {
      event.preventDefault();
      if (event.key === "Home") list.jumpToStart(true);
      else list.jumpToEnd(true);
      return;
    }
    if (!rowNavigation || (event.key !== "ArrowDown" && event.key !== "ArrowUp")) return;
    const element = viewport.current;
    const row = element && ownRow(element, target);
    if (!element || !row) return;
    event.preventDefault();
    const next = Number(row.dataset.rowIndex) + (event.key === "ArrowDown" ? 1 : -1);
    // Across a page edge the row waits, drawn as a placeholder, until its page arrives (D163).
    if (next >= 0 && next < count) focusIndex(next, target.closest<HTMLElement>("[data-grid-col]")?.dataset.gridCol);
  }

  const empty = list.items.length === 0;
  const long = (total ?? list.items.length) > pageSize;
  const showEnd = edgeMarkers === "always" || long || list.hasNext;
  const pageCount = total !== null ? Math.max(1, Math.ceil(total / pageSize)) : undefined;
  const firstVisible = visible?.first ?? list.startIndex;
  const lastVisible = visible?.last ?? list.startIndex + list.items.length - 1;
  const currentPage = Math.floor(firstVisible / pageSize) + 1;
  const atStart = firstVisible <= 0;
  const atEnd = lastVisible >= count - 1 && !(total === null && list.hasNext);
  const edgeError = list.before.error || list.after.error;

  return (
    <div className="scroll-window">
      <div className="scroll-window-frame">
        <div
          ref={viewport}
          className={`scroll-window-viewport ${className}`}
          role="region"
          aria-label={label}
          tabIndex={0}
          data-overflowing={overflowing || undefined}
          onScroll={onScroll}
          onKeyDown={onKeyDown}
          onFocus={(event) => {
            const key = viewport.current && ownRow(viewport.current, event.target as HTMLElement)?.dataset.rowKey;
            if (key) focusedKey.current = key;
          }}
        >
          {!empty && long && <Edge done="Start of list" />}
          {children(drawn)}
          {!empty && showEnd && (
            <Edge
              done={
                total === null && list.hasNext
                  ? ""
                  : `End · ${format(total ?? held)} ${(total ?? held) === 1 ? singular : plural}`
              }
            />
          )}
        </div>
      </div>
      <span className="visually-hidden" role="status" aria-live="polite">
        {announcement}
      </span>
      {edgeError && !footer && <EdgeError error={edgeError} onRetry={list.retry} />}
      {footer && (
        <div className="scroll-window-footer">
          <span className="scroll-window-range">
            {edgeError ? (
              <EdgeError error={edgeError} onRetry={list.retry} />
            ) : list.loading && empty ? (
              `Loading ${plural}…`
            ) : list.error && empty ? (
              `${plural[0].toUpperCase()}${plural.slice(1)} unavailable`
            ) : empty ? (
              ""
            ) : total !== null ? (
              `${format(firstVisible + 1)}–${format(lastVisible + 1)} of ${format(total)} ${
                total === 1 ? singular : plural
              }`
            ) : (
              `${format(list.items.length)} ${list.items.length === 1 ? singular : plural}`
            )}
          </span>
          <div className="scroll-window-jumps">
            {seekLabel && !empty && <SeekField label={seekLabel} onSeek={list.seek} />}
            {pageCount !== undefined && pageCount > 1 && (
              <PageField
                page={currentPage}
                pageCount={pageCount}
                onPage={(page) => list.jumpTo((page - 1) * pageSize)}
              />
            )}
            {pageCount !== undefined && pageCount > 1 && (
              <>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Go to start"
                  title="Go to start (Ctrl+Home)"
                  disabled={atStart || list.loading}
                  onClick={() => list.jumpToStart()}
                >
                  <Icon name="to-start" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Go to end"
                  title="Go to end (Ctrl+End)"
                  disabled={atEnd || list.loading}
                  onClick={() => list.jumpToEnd()}
                >
                  <Icon name="to-end" />
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * The height of the rows not drawn, before or after the drawn ones, in the surface's own markup: a
 * table row spanning `columns`, a list item or a block. The leading one is always drawn: the window
 * measures where the rows start from it. A table spacer standing for rows has their bottom border:
 * a table's collapsed border is shared by the rows on either side, so without it the first drawn
 * row lost half a pixel whenever the row above it was dropped, and the rows under the reader moved.
 */
export function WindowSpacer({
  as,
  edge,
  height,
  columns = 1,
}: {
  as: "tr" | "li" | "div";
  edge: "before" | "after";
  height: number;
  columns?: number;
}) {
  if (as === "tr")
    return (
      <tr
        className={`window-spacer${height > 0 ? " stands-for-rows" : ""}`}
        aria-hidden="true"
        data-window-spacer={edge}
      >
        <td colSpan={columns} style={{ height }} />
      </tr>
    );
  const Element = as;
  return (
    <Element
      className="window-spacer"
      aria-hidden="true"
      role={as === "li" ? "presentation" : undefined}
      data-window-spacer={edge}
      style={{ height }}
    />
  );
}

/**
 * A row whose page has not arrived (D163): drawn like a loading row, in muted bars, at the height
 * its place holds, and hidden from assistive technology. `cells` gives a table row its columns,
 * each with its class.
 */
export function WindowPlaceholder({
  as,
  index,
  size,
  cells = [undefined],
  className = "",
}: {
  as: "tr" | "li" | "div";
  index: number;
  size: number;
  cells?: (string | undefined)[];
  className?: string;
}) {
  const style: CSSProperties = { height: size };
  if (as === "tr")
    return (
      <tr
        className={`loading-row window-placeholder ${className}`}
        aria-hidden="true"
        data-row-index={index}
        data-placeholder=""
        style={style}
      >
        {cells.map((cell, position) => (
          <td key={position} className={cell}>
            <span className="skeleton-line" />
          </td>
        ))}
      </tr>
    );
  const Element = as;
  return (
    <Element
      className={`window-placeholder ${className}`}
      aria-hidden="true"
      role={as === "li" ? "presentation" : undefined}
      data-row-index={index}
      data-placeholder=""
      style={style}
    >
      <span className="skeleton-line" />
    </Element>
  );
}

function Edge({ done }: { done: string }) {
  return <div className="scroll-window-edge">{done}</div>;
}

function EdgeError({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <span className="scroll-window-edge-error">
      {error}{" "}
      <button type="button" className="secondary" onClick={onRetry}>
        Retry
      </button>
    </span>
  );
}

function PageField({ page, pageCount, onPage }: { page: number; pageCount: number; onPage: (page: number) => void }) {
  const [draft, setDraft] = useState<string>();
  return (
    <form
      className="page-jump"
      onSubmit={(event) => {
        event.preventDefault();
        const requested = Number(draft);
        if (Number.isInteger(requested)) onPage(Math.min(pageCount, Math.max(1, requested)));
        setDraft(undefined);
      }}
    >
      <label>
        Page
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={pageCount}
          value={draft ?? String(page)}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={() => setDraft(undefined)}
          aria-describedby={undefined}
        />
      </label>
      <span>of {format(pageCount)}</span>
    </form>
  );
}

function SeekField({ label, onSeek }: { label: string; onSeek: (value: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <form
      className="seek-jump"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) onSeek(value.trim());
      }}
    >
      <input
        aria-label={`Go to ${label}`}
        placeholder={`Go to ${label}…`}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
    </form>
  );
}
