/**
 * The scrolling viewport of a continuous list (ADR-030, Base 0.8 S5).
 *
 * It drives a `useCursorWindow`: it prefetches when the viewport comes within one page of either
 * edge, keeps the rows on screen still when rows are added or evicted above them, lands jumps,
 * shows the edge markers and, when the window holds only part of the list, a proportional scrollbar
 * sized from the total. The footer reports the visible range and jumps by page number, to the start
 * or end and, where the list supports it, to a value.
 *
 * Children render the rows. Each row carries `data-row-key` (a stable identity) and
 * `data-row-index` (its absolute index); an element inside it marked `data-row-focus` receives
 * keyboard focus, otherwise the row itself does and needs `tabIndex={-1}`. In a grid, cells marked
 * `data-grid-col` keep their column: Up and Down from one focus the same column of the next row,
 * across page edges too. Windows may nest (a tree branch inside a row): each reads only the rows of
 * its own viewport.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { Icon } from "@/ui/Icon";

const numberFormat = new Intl.NumberFormat();

/**
 * Height the sticky table header covers once the list is scrolled. A landed or revealed row is
 * placed below it even while the viewport is still at the top and the header not yet stuck, so
 * the row stays in view when earlier rows arrive above it.
 */
function stuckHeader(viewport: HTMLElement) {
  return viewport.querySelector("thead")?.getBoundingClientRect().height ?? 0;
}
const format = (value: number) => numberFormat.format(value);

/** The rows of this viewport, leaving out those of windows nested inside its rows. */
function ownRows(viewport: HTMLElement) {
  return Array.from(viewport.querySelectorAll<HTMLElement>("[data-row-key]")).filter(
    (row) => row.closest(".scroll-window-viewport") === viewport,
  );
}

/** The row of this viewport that holds `target`, which may sit inside a nested window. */
function ownRow(viewport: HTMLElement, target: HTMLElement) {
  for (let row = target.closest<HTMLElement>("[data-row-key]"); row;) {
    if (row.closest(".scroll-window-viewport") === viewport) return row;
    row = row.parentElement?.closest<HTMLElement>("[data-row-key]") ?? null;
  }
  return null;
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
  role = "region",
  edgeMarkers = "always",
  onAnnounce,
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
  /**
   * "region": the viewport is a labelled region and a tab stop. "group": the rows belong to an
   * enclosing widget, such as tree items within a tree, which owns only its items and groups.
   * The viewport is then a labelled group, a tab stop only while it scrolls, its edge markers are
   * presentational, and announcements go to `onAnnounce` instead of a live region of its own.
   */
  role?: "region" | "group";
  /** Receives polite announcements in place of the window's own live region. */
  onAnnounce?: (message: string) => void;
  /** "partial" shows the start and end markers only for a list longer than one page. */
  edgeMarkers?: "always" | "partial";
  /** Receives the cursor that reopens the viewport's page, for the URL. */
  onAnchorChange?: (anchor: string | undefined) => void;
  children: ReactNode;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState<Visible>();
  const [announcement, setAnnouncement] = useState("");
  const [overflowing, setOverflowing] = useState(false);
  const scrollAnchor = useRef<{ key: string; offset: number } | undefined>(undefined);
  // Set while the anchored row could not be placed because too few rows follow it yet; the next
  // page below completes the placement, and until then the anchor is not re-read from the screen.
  const heldAnchor = useRef(false);
  const handledLanding = useRef<number | undefined>(undefined);
  const pendingFocus = useRef<{ key: string; step: 1 | -1; column?: string } | undefined>(undefined);
  const focusedKey = useRef<string | undefined>(undefined);
  const frame = useRef(0);
  const listRef = useRef(list);
  const anchorCallback = useRef(onAnchorChange);
  const reportedAnchor = useRef<string | undefined>(undefined);
  const anchorTimer = useRef(0);
  // The URL anchor and the refresh position follow the user, not the list's own scrolling: they
  // change on a jump or when the user scrolls, never when rows arriving above are compensated for.
  const userMoved = useRef(false);
  const programmaticTop = useRef<number | null>(null);

  // A layout effect, declared first, so the landing and prefetch below read this render's list.
  useLayoutEffect(() => {
    listRef.current = list;
    anchorCallback.current = onAnchorChange;
  });
  const announceTo = useRef(onAnnounce);
  useEffect(() => {
    announceTo.current = onAnnounce;
  });
  useEffect(() => {
    if (announcement) announceTo.current?.(announcement);
  }, [announcement]);
  // A presentational edge shows a failed read only visually; moving past the edge again retries.
  const edgeError = role === "group" ? list.after.error || list.before.error : "";
  useEffect(() => {
    if (edgeError) announceTo.current?.(edgeError);
  }, [edgeError]);

  const [singular, plural] = noun;
  const partial = list.hasPrevious || list.hasNext;
  const total = list.totalCount;

  /** Makes `index` the list's place: what a refresh re-reads and, once at rest, the URL anchor. */
  const follow = useCallback((index: number) => {
    listRef.current.setViewportIndex(index);
    window.clearTimeout(anchorTimer.current);
    anchorTimer.current = window.setTimeout(() => {
      const anchor = listRef.current.anchorAt(index);
      if (anchor === reportedAnchor.current) return;
      reportedAnchor.current = anchor;
      anchorCallback.current?.(anchor);
    }, 400);
  }, []);

  /** Reads the rows on screen, records the scroll anchor and prefetches near an edge. */
  const measure = useCallback(() => {
    const element = viewport.current;
    if (!element) return;
    const current = listRef.current;
    const box = element.getBoundingClientRect();
    // Only the header cells stick; the header row's own box scrolls away with the rows.
    const header = element.querySelector("thead")?.getBoundingClientRect();
    const top = Math.max(box.top + stuckHeader(element), header ? header.bottom : box.top);
    const rows = ownRows(element).filter((row) => row.dataset.rowIndex !== undefined);
    let first: number | undefined;
    let last: number | undefined;
    for (const row of rows) {
      const rect = row.getBoundingClientRect();
      if (rect.bottom <= top + 1 || rect.top >= box.bottom - 1) continue;
      const index = Number(row.dataset.rowIndex);
      if (first === undefined) {
        first = index;
        if (!heldAnchor.current) scrollAnchor.current = { key: row.dataset.rowKey ?? "", offset: rect.top - box.top };
      }
      last = index;
    }
    if (first !== undefined && last !== undefined) {
      const firstIndex = first;
      const lastIndex = last;
      setVisible((previous) =>
        previous?.first === firstIndex && previous.last === lastIndex
          ? previous
          : { first: firstIndex, last: lastIndex },
      );
      if (userMoved.current) follow(firstIndex);
    }
    setOverflowing(element.scrollHeight > element.clientHeight + 1);
    if (current.loading || rows.length === 0) return;
    const pageHeight = (element.scrollHeight / rows.length) * pageSize;
    const below = element.scrollHeight - element.scrollTop - element.clientHeight;
    if (current.hasPrevious && !current.before.loading && !current.before.error && element.scrollTop < pageHeight)
      current.loadPrevious();
    if (current.hasNext && !current.after.loading && !current.after.error && below < pageHeight) current.loadNext();
    if (below < 2 && current.after.loading) setAnnouncement(`Loading more ${plural}…`);
    else if (element.scrollTop < 2 && current.before.loading) setAnnouncement(`Loading earlier ${plural}…`);
  }, [pageSize, plural, follow]);

  const schedule = useCallback(() => {
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(measure);
  }, [measure]);

  const onScroll = useCallback(() => {
    const element = viewport.current;
    if (element && (programmaticTop.current === null || Math.abs(element.scrollTop - programmaticTop.current) > 1))
      userMoved.current = true;
    schedule();
  }, [schedule]);

  const setTop = useCallback((element: HTMLElement, top: number) => {
    element.scrollTop = top;
    programmaticTop.current = element.scrollTop;
  }, []);

  // A list shown again after being hidden, or resized, measures again and prefetches as needed.
  useEffect(() => {
    const element = viewport.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(schedule);
    observer.observe(element);
    return () => observer.disconnect();
  }, [schedule]);

  useEffect(
    () => () => {
      cancelAnimationFrame(frame.current);
      window.clearTimeout(anchorTimer.current);
    },
    [],
  );

  const reveal = useCallback((row: HTMLElement) => {
    const element = viewport.current;
    if (!element) return;
    const box = element.getBoundingClientRect();
    const top = box.top + stuckHeader(element);
    const rect = row.getBoundingClientRect();
    // Revealing a row the user moved to by keyboard is the user's own movement.
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

  // Rows changed: land a jump, or keep the anchored row where it was on screen.
  useLayoutEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const hold = (row: HTMLElement, offset: number, desired: number) => {
      heldAnchor.current = element.scrollTop < desired - 1 && list.hasNext;
      if (heldAnchor.current) scrollAnchor.current = { key: row.dataset.rowKey ?? "", offset };
    };
    const landing = list.landing;
    const rows = () => ownRows(element);
    if (landing && handledLanding.current !== landing.token && !list.loading) {
      handledLanding.current = landing.token;
      pendingFocus.current = undefined;
      userMoved.current = false;
      let target: HTMLElement | undefined;
      if (landing.target === "start") {
        setTop(element, 0);
        target = rows()[0];
      } else if (landing.target === "end") {
        setTop(element, element.scrollHeight);
        target = rows().at(-1);
      } else {
        target = rows().find((row) => row.dataset.rowIndex === String(landing.target));
        if (target) {
          const top = element.getBoundingClientRect().top + stuckHeader(element);
          const desired = element.scrollTop + target.getBoundingClientRect().top - top;
          setTop(element, desired);
          hold(target, top - element.getBoundingClientRect().top, desired);
        }
      }
      if (target?.dataset.rowIndex !== undefined && landing.token > 1) follow(Number(target.dataset.rowIndex));
      if (landing.focus && target) focusRow(target);
      if (landing.token > 1 && list.items.length)
        setAnnouncement(
          `Showing ${plural} from ${format(Number(target?.dataset.rowIndex ?? list.startIndex) + 1)}` +
            (list.totalCount !== null ? ` of ${format(list.totalCount)}` : ""),
        );
    } else if (scrollAnchor.current) {
      const { key, offset } = scrollAnchor.current;
      const row = rows().find((item) => item.dataset.rowKey === key);
      if (row) {
        const desired =
          element.scrollTop + row.getBoundingClientRect().top - element.getBoundingClientRect().top - offset;
        setTop(element, desired);
        hold(row, offset, desired);
      } else heldAnchor.current = false;
    }
    if (pendingFocus.current) {
      const { key, step, column } = pendingFocus.current;
      const all = rows();
      const index = all.findIndex((item) => item.dataset.rowKey === key);
      const next = index >= 0 ? all[index + step] : undefined;
      if (next) {
        pendingFocus.current = undefined;
        focusRow(next, column);
      }
    }
    // A focused row evicted from the window leaves focus with the list rather than the page.
    if (
      focusedKey.current &&
      (document.activeElement === document.body || document.activeElement === null) &&
      !rows().some((item) => item.dataset.rowKey === focusedKey.current)
    ) {
      focusedKey.current = undefined;
      element.focus({ preventScroll: true });
    }
    measure();
  }, [
    list.items,
    list.hasNext,
    list.landing,
    list.loading,
    list.startIndex,
    list.totalCount,
    list.items.length,
    plural,
    focusRow,
    measure,
    follow,
    setTop,
  ]);

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    // A window nested in one of the rows handled the key first.
    if (event.defaultPrevented) return;
    if (target.closest("input, select, textarea, [contenteditable='true'], [role='menu']")) return;
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
    const step = event.key === "ArrowDown" ? 1 : -1;
    const column = target.closest<HTMLElement>("[data-grid-col]")?.dataset.gridCol;
    const all = ownRows(element);
    const next = all[all.indexOf(row) + step];
    if (next) focusRow(next, column);
    else if (step === 1 && list.hasNext) {
      pendingFocus.current = { key: row.dataset.rowKey ?? "", step, column };
      list.loadNext();
    } else if (step === -1 && list.hasPrevious) {
      pendingFocus.current = { key: row.dataset.rowKey ?? "", step, column };
      list.loadPrevious();
    }
  }

  const empty = list.items.length === 0;
  const long = (total ?? list.items.length) > pageSize;
  const showStart = !list.hasPrevious && long;
  const showEnd = edgeMarkers === "always" || long || list.hasNext || list.after.loading || Boolean(list.after.error);
  const pageCount = total !== null ? Math.max(1, Math.ceil(total / pageSize)) : undefined;
  const firstVisible = visible?.first ?? list.startIndex;
  const lastVisible = visible?.last ?? list.startIndex + list.items.length - 1;
  const currentPage = Math.floor(firstVisible / pageSize) + 1;
  const atStart = !list.hasPrevious && firstVisible <= list.startIndex;
  const atEnd = !list.hasNext && lastVisible >= list.startIndex + list.items.length - 1;

  return (
    <div className="scroll-window">
      <div className="scroll-window-frame">
        <div
          ref={viewport}
          className={`scroll-window-viewport${partial && total !== null ? " has-window-scrollbar" : ""} ${className}`}
          role={role}
          aria-label={label}
          tabIndex={role === "region" || overflowing ? 0 : -1}
          onScroll={onScroll}
          onKeyDown={onKeyDown}
          onFocus={(event) => {
            const key = viewport.current && ownRow(viewport.current, event.target as HTMLElement)?.dataset.rowKey;
            if (key) focusedKey.current = key;
          }}
        >
          {!empty && (list.hasPrevious || showStart) && (
            <Edge
              presentational={role === "group"}
              status={list.before}
              waiting={`Loading earlier ${plural}…`}
              done={list.hasPrevious ? "" : "Start of list"}
              onRetry={list.retry}
            />
          )}
          {children}
          {!empty && showEnd && (
            <Edge
              presentational={role === "group"}
              status={list.after}
              waiting={`Loading more ${plural}…`}
              done={
                list.hasNext
                  ? ""
                  : `End · ${format(total ?? list.startIndex + list.items.length)} ${
                      (total ?? list.items.length) === 1 ? singular : plural
                    }`
              }
              onRetry={list.retry}
            />
          )}
        </div>
        {partial && total !== null && total > 0 && (
          <WindowScrollbar
            total={total}
            first={firstVisible}
            count={Math.max(1, lastVisible - firstVisible + 1)}
            landing={list.landing?.token}
            onJump={(index) => list.jumpTo(index)}
          />
        )}
      </div>
      {!onAnnounce && (
        <span className="visually-hidden" role="status" aria-live="polite">
          {announcement}
        </span>
      )}
      {footer && (
        <div className="scroll-window-footer">
          <span className="scroll-window-range">
            {list.loading && empty
              ? `Loading ${plural}…`
              : list.error && empty
                ? `${plural[0].toUpperCase()}${plural.slice(1)} unavailable`
                : empty
                  ? ""
                  : total !== null
                    ? `${format(firstVisible + 1)}–${format(lastVisible + 1)} of ${format(total)} ${
                        total === 1 ? singular : plural
                      }`
                    : `${format(list.items.length)} ${list.items.length === 1 ? singular : plural}`}
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

function Edge({
  presentational,
  status,
  waiting,
  done,
  onRetry,
}: {
  /** Visual only; its news reaches assistive technology through the announcements. */
  presentational: boolean;
  status: { loading: boolean; error: string };
  waiting: string;
  done: string;
  onRetry: () => void;
}) {
  return (
    <div
      className={`scroll-window-edge${status.loading ? " is-loading" : ""}`}
      aria-hidden={presentational || undefined}
    >
      {status.error ? (
        <span className="scroll-window-edge-error">
          {status.error}{" "}
          <button type="button" className="secondary" tabIndex={presentational ? -1 : undefined} onClick={onRetry}>
            Retry
          </button>
        </span>
      ) : status.loading ? (
        <>
          <span className="scroll-window-spinner" aria-hidden="true" />
          {waiting}
        </>
      ) : (
        done
      )}
    </div>
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

/**
 * A pointer affordance over the whole list: the thumb's size and place come from the total, not
 * from the rows held. Clicking the track or releasing a drag sends one jump. Keyboard and assistive
 * technology users jump with the page field and Ctrl+Home/Ctrl+End instead, so it is hidden from them.
 */
function WindowScrollbar({
  total,
  first,
  count,
  landing,
  onJump,
}: {
  total: number;
  first: number;
  count: number;
  landing: number | undefined;
  onJump: (index: number) => void;
}) {
  const track = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);
  const [drag, setDrag] = useState<{ startY: number; startTop: number; top: number }>();
  const [held, setHeld] = useState<{ top: number; landing: number | undefined }>();

  useLayoutEffect(() => {
    const element = track.current;
    if (!element) return;
    const update = () => setHeight(element.clientHeight);
    update();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const thumb = Math.min(height, Math.max(28, (height * Math.min(count, total)) / total));
  const travel = Math.max(1, height - thumb);
  const range = Math.max(1, total - count);
  const clamp = (top: number) => Math.min(travel, Math.max(0, top));
  const indexAt = (top: number) => Math.round((clamp(top) / travel) * range);
  const settled = (Math.min(first, range) / range) * travel;
  // After a jump the thumb stays where it was dropped until the landed rows report their place.
  const top = drag?.top ?? (held && held.landing === landing ? held.top : settled);

  function jump(nextTop: number) {
    setHeld({ top: clamp(nextTop), landing });
    onJump(indexAt(nextTop));
  }

  return (
    <div
      ref={track}
      className="window-scrollbar"
      aria-hidden="true"
      onPointerDown={(event) => {
        if (event.button !== 0 || event.target !== track.current) return;
        const rect = track.current.getBoundingClientRect();
        jump(event.clientY - rect.top - thumb / 2);
      }}
    >
      <div
        className={`window-scrollbar-thumb${drag ? " is-dragging" : ""}`}
        style={{ height: thumb, transform: `translateY(${top}px)` }}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          event.preventDefault();
          event.currentTarget.setPointerCapture(event.pointerId);
          setDrag({ startY: event.clientY, startTop: top, top });
        }}
        onPointerMove={(event) => {
          if (drag) setDrag({ ...drag, top: clamp(drag.startTop + event.clientY - drag.startY) });
        }}
        onPointerUp={() => {
          if (!drag) return;
          setDrag(undefined);
          jump(drag.top);
        }}
        onPointerCancel={() => setDrag(undefined)}
      >
        {drag && <span className="window-scrollbar-tip">{format(indexAt(drag.top) + 1)}</span>}
      </div>
    </div>
  );
}
