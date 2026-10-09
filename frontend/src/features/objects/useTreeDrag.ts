/**
 * Dragging a record to a new parent in a `RecordTree` (Base 0.8 B5, D34, D35), with mouse or pen.
 * A touch pointer never starts a drag, so a tap still opens and a swipe still scrolls.
 *
 * The pointer names a target on each move: the middle of a record's row is that record; the middle
 * of a type heading is the heading's parent; the top or bottom quarter of a row is the gap beside it,
 * which drops into the branch the gap belongs to, the pointer's horizontal position choosing among
 * branches that end there. Where the tree shows its top level, its headings and the gaps between its
 * rows name the top level, a `null` parent (B5b, D36); a search's results have no top level to drop
 * into. The caller's rule says whether the target accepts and, if not, why.
 * Hovering over a collapsed branch opens it; near a window's top or bottom edge the window scrolls,
 * faster towards the edge. Escape, a cancelled pointer or a release outside an accepted target ends
 * the drag without a drop.
 *
 * Several records drag together (UA9, U-D23–U-D25): the tree names them when a drag starts from one
 * of them. A target accepts only if it takes every one; otherwise its refusal names the first it
 * cannot take, and a target that would change a record's type refuses them all, since a type
 * changes one record at a time. With flat scrolling (U-D21) the edge scrolls the tree's nearest
 * scrolling ancestor.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type PointerEvent, type RefObject } from "react";
import { chooseGapBranch, gapBranches, type RowPlace } from "@/model/treeDrop";
import type { ObjectItem } from "@/types";

/** How a tree lets records be dragged to a new parent; without it no row drags. */
export interface TreeDragConfiguration {
  /** Whether the record's row starts a drag. */
  canDrag: (item: ObjectItem) => boolean;
  /**
   * Why the record cannot move into `parent` (`null` is the top level), in words shown beside the
   * pointer; undefined accepts.
   */
  refusal: (item: ObjectItem, parent: ObjectItem | null) => string | undefined;
  /** What an accepted target does beyond a move, in words beside the pointer (C4: “Becomes …”). */
  note?: (item: ObjectItem, parent: ObjectItem | null) => string | undefined;
  /** A release over a target that accepts every dragged record (one, or the tree's selection). */
  onDrop: (items: ObjectItem[], parent: ObjectItem | null) => void;
}

/** The target under the pointer: the parent it names and the rows that show it. */
export interface TreeDropTarget {
  /** The new parent, or `null` for the top level. */
  parent: ObjectItem | null;
  /**
   * Tree keys of the rows that glow: the parent's, and a heading dropped on. At the top level, the
   * heading of the record's own top-level group, where it will be listed.
   */
  rows: string[];
  refusal?: string;
  /** Set on an accepted target that does more than move the record. */
  note?: string;
  /** A gap's drop line, in viewport coordinates, indented to the chosen branch. */
  line?: { top: number; left: number; width: number };
}

export interface TreeDragState {
  /** The record the drag started from. */
  item: ObjectItem;
  /** Every record dragged: the selection when the drag started from one of it, else `item`. */
  items: ObjectItem[];
  target?: TreeDropTarget;
}

/** Said of several records whose type a target would change (U-D25). */
export const SEVERAL_CHANGE_TYPE = "Move records that change type one at a time";

/** Distance a pressed pointer travels before a drag starts, so a click still opens. */
const THRESHOLD = 5;
/** How long a pointer rests over a collapsed branch before it opens. */
const EXPAND_DELAY = 700;
/** The band along a window's top and bottom edges that scrolls it, and the fastest step per frame. */
const EDGE = 40;
const MAX_STEP = 16;

interface Session {
  item: ObjectItem;
  items: ObjectItem[];
  pointerId: number;
  from: { x: number; y: number };
  at: { x: number; y: number };
  started: boolean;
  signature: string;
  target?: TreeDropTarget;
  expandId?: string;
  expandTimer?: number;
  frame?: number;
  viewport?: HTMLElement;
  end: (drop: boolean) => void;
}

const ITEM = "[role='treeitem']";

export function useTreeDrag({
  tree,
  config,
  records,
  indentOf,
  topLevelRows,
  expand,
  draggedWith,
  labelOf,
}: {
  tree: RefObject<HTMLElement | null>;
  config?: TreeDragConfiguration;
  /** The drawn records by tree key. */
  records: Map<string, ObjectItem>;
  /** Where a level's rows start, from the tree's left edge. */
  indentOf: (level: number) => number;
  /** The rows that show the top level for a dragged record; without it the top level takes no drop. */
  topLevelRows?: (item: ObjectItem) => string[];
  expand: (objectId: string) => void;
  /** The records a drag from `item` moves: the selection it belongs to, or just `item`. */
  draggedWith?: (item: ObjectItem) => ObjectItem[];
  /** A record's label, which a refusal of several names it by. */
  labelOf?: (item: ObjectItem) => string;
}) {
  const [state, setState] = useState<TreeDragState>();
  const preview = useRef<HTMLDivElement>(null);
  const session = useRef<Session | undefined>(undefined);
  const latest = useRef({ config, expand, indentOf, topLevelRows, draggedWith, labelOf });
  useLayoutEffect(() => {
    latest.current = { config, expand, indentOf, topLevelRows, draggedWith, labelOf };
  });

  /** The target at a point, or undefined outside the tree's rows or at a top level it cannot take. */
  const targetAt = useCallback(
    (x: number, y: number, dragged: ObjectItem, moving: ObjectItem[]): TreeDropTarget | undefined => {
      const root = tree.current;
      const under = document.elementFromPoint?.(x, y);
      if (!root || !under || !root.contains(under)) return undefined;
      const item = under.closest<HTMLElement>(ITEM);
      const row = item && ownRow(item);
      if (!item || !row?.contains(under)) return undefined;
      const rect = row.getBoundingClientRect();
      const edge = rect.height / 4;
      const zone = y < rect.top + edge ? -1 : y > rect.bottom - edge ? 1 : 0;
      const target = (
        parentItem: HTMLElement | null,
        rows: string[],
        line?: TreeDropTarget["line"],
      ): TreeDropTarget | undefined => {
        const judge = (parent: ObjectItem | null) => {
          const rule = latest.current.config;
          if (moving.length <= 1) {
            const refusal = rule?.refusal(dragged, parent);
            return { refusal, note: refusal ? undefined : rule?.note?.(dragged, parent) };
          }
          // Several: every record must go there, and none may change its type (U-D24, U-D25).
          for (const record of moving) {
            const refusal = rule?.refusal(record, parent);
            if (refusal) return { refusal: `${latest.current.labelOf?.(record) ?? record.name}: ${refusal}` };
          }
          if (moving.some((record) => rule?.note?.(record, parent))) return { refusal: SEVERAL_CHANGE_TYPE };
          return { refusal: undefined, note: undefined };
        };
        if (!parentItem) {
          // No parent item: the top level, where the tree shows one.
          const topRows = latest.current.topLevelRows?.(dragged);
          if (!topRows) return undefined;
          return { parent: null, rows: [...new Set([...rows, ...topRows])], ...judge(null), line };
        }
        const parent = records.get(keyOf(parentItem));
        if (!parent) return undefined;
        return { parent, rows: [keyOf(parentItem), ...rows], ...judge(parent), line };
      };
      if (zone === 0)
        return item.dataset.objectId ? target(item, []) : target(parentItemOf(item) ?? null, [keyOf(item)]);
      const all = Array.from(root.querySelectorAll<HTMLElement>(ITEM));
      const index = all.indexOf(item);
      const [above, below] = zone < 0 ? [all[index - 1], item] : [item, all[index + 1]];
      // Levels are measured from the tree's edge, since nested branches' rows start further in.
      const left = root.getBoundingClientRect().left;
      const chosen = chooseGapBranch(
        gapBranches(above && placeOf(above), below && placeOf(below)),
        x - left,
        latest.current.indentOf,
      );
      if (!chosen) return undefined;
      const start = left + latest.current.indentOf(chosen.level);
      return target(chosen.parent, [], {
        top: zone < 0 ? rect.top : rect.bottom,
        left: start,
        width: Math.max(0, rect.right - start),
      });
    },
    [tree, records],
  );

  const place = useCallback(() => {
    const current = session.current;
    if (current && preview.current)
      preview.current.style.transform = `translate(${current.at.x + 14}px, ${current.at.y + 12}px)`;
  }, []);
  useLayoutEffect(place, [state, place]);

  /** Names the target under the pointer and shows it when it changed. */
  const update = useCallback(() => {
    const current = session.current;
    if (!current?.started) return;
    const target = targetAt(current.at.x, current.at.y, current.item, current.items);
    const signature = JSON.stringify(
      target ? [target.rows, target.refusal ?? "", target.note ?? "", target.line ?? ""] : "",
    );
    if (signature !== current.signature) {
      current.signature = signature;
      current.target = target;
      document.body.classList.toggle("tree-drag-refused", Boolean(target?.refusal));
      setState({ item: current.item, items: current.items, target });
    }
    // Resting on a collapsed branch opens it, unless it is the dragged record.
    const node = target?.parent && !target.line && target.rows.length === 1 ? target : undefined;
    const collapsed =
      node?.parent &&
      !current.items.some((record) => record.id === node.parent?.id) &&
      tree.current
        ?.querySelector(`${ITEM}[data-tree-key="${CSS.escape(node.rows[0])}"]`)
        ?.getAttribute("aria-expanded") === "false"
        ? node.parent.id
        : undefined;
    if (collapsed !== current.expandId) {
      window.clearTimeout(current.expandTimer);
      current.expandId = collapsed;
      current.expandTimer = collapsed
        ? window.setTimeout(() => latest.current.expand(collapsed), EXPAND_DELAY)
        : undefined;
    }
  }, [targetAt, tree]);

  /** Scrolls the window under the pointer while the pointer is near its top or bottom edge. */
  const scroll = useCallback(() => {
    const current = session.current;
    if (!current?.started) return;
    const root = tree.current;
    const under = document.elementFromPoint?.(current.at.x, current.at.y);
    if (root && under && root.contains(under)) {
      const viewports: HTMLElement[] = [];
      let viewport = under.closest<HTMLElement>(".scroll-window-viewport");
      while (viewport && root.contains(viewport)) {
        viewports.push(viewport);
        viewport = viewport.parentElement?.closest<HTMLElement>(".scroll-window-viewport") ?? null;
      }
      if (!viewports.length && current.viewport) viewports.push(current.viewport);
      // Flat scrolling (UA9, U-D21): no window of its own, so the tree's nearest scroller moves.
      if (!viewports.length) viewports.push(scrollerOf(root));
      for (const viewport of viewports) {
        const rect =
          viewport === document.scrollingElement
            ? { top: 0, bottom: window.innerHeight }
            : viewport.getBoundingClientRect();
        const up = rect.top + EDGE - current.at.y;
        const down = current.at.y - (rect.bottom - EDGE);
        const step = (depth: number) => Math.min(MAX_STEP, Math.ceil((depth / EDGE) * MAX_STEP));
        const delta =
          up > 0 && viewport.scrollTop > 0
            ? -step(up)
            : down > 0 && viewport.scrollTop + viewport.clientHeight < viewport.scrollHeight - 1
              ? step(down)
              : 0;
        if (!delta) continue;
        current.viewport = viewport;
        viewport.scrollTop += delta;
        update();
        break;
      }
    }
  }, [tree, update]);

  const start = useCallback(
    (event: PointerEvent<HTMLElement>, item: ObjectItem) => {
      const drag = latest.current.config;
      if (!drag || session.current || event.button !== 0 || event.pointerType === "touch") return;
      if ((event.target as HTMLElement).closest("input, textarea, select, button, form, .tree-extras, .tree-toggle"))
        return;
      const items = latest.current.draggedWith?.(item) ?? [item];
      if (!items.every((record) => drag.canDrag(record))) return;
      const tick = () => {
        const current = session.current;
        if (!current?.started) return;
        scroll();
        current.frame = window.requestAnimationFrame(tick);
      };
      const onMove = (move: globalThis.PointerEvent) => {
        const current = session.current;
        if (!current || move.pointerId !== current.pointerId) return;
        current.at = { x: move.clientX, y: move.clientY };
        if (!current.started) {
          if (Math.hypot(current.at.x - current.from.x, current.at.y - current.from.y) < THRESHOLD) return;
          current.started = true;
          document.body.classList.add("tree-dragging");
          window.getSelection?.()?.removeAllRanges();
          setState({ item: current.item, items: current.items });
          current.frame = window.requestAnimationFrame(tick);
        }
        update();
        place();
      };
      const onUp = (up: globalThis.PointerEvent) => {
        const current = session.current;
        if (!current || up.pointerId !== current.pointerId) return;
        current.at = { x: up.clientX, y: up.clientY };
        update();
        current.end(true);
      };
      const onCancel = () => session.current?.end(false);
      const onKey = (key: KeyboardEvent) => {
        if (key.key !== "Escape") return;
        if (session.current?.started) {
          key.preventDefault();
          key.stopPropagation();
        }
        session.current?.end(false);
      };
      const end = (drop: boolean) => {
        const current = session.current;
        if (!current) return;
        session.current = undefined;
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
        window.removeEventListener("pointercancel", onCancel);
        window.removeEventListener("keydown", onKey, true);
        window.clearTimeout(current.expandTimer);
        if (current.frame !== undefined) window.cancelAnimationFrame(current.frame);
        if (!current.started) return;
        document.body.classList.remove("tree-dragging", "tree-drag-refused");
        // The release is not a click on the row it ends over.
        const swallow = (click: MouseEvent) => {
          click.preventDefault();
          click.stopPropagation();
        };
        window.addEventListener("click", swallow, { capture: true, once: true });
        window.setTimeout(() => window.removeEventListener("click", swallow, { capture: true }), 0);
        setState(undefined);
        const target = current.target;
        if (drop && target && !target.refusal) latest.current.config?.onDrop(current.items, target.parent);
      };
      session.current = {
        item,
        items,
        pointerId: event.pointerId,
        from: { x: event.clientX, y: event.clientY },
        at: { x: event.clientX, y: event.clientY },
        started: false,
        signature: "",
        end,
      };
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
      window.addEventListener("pointercancel", onCancel);
      window.addEventListener("keydown", onKey, true);
    },
    [place, scroll, update],
  );

  // A tree that unmounts mid-drag ends it without a drop.
  useEffect(() => () => session.current?.end(false), []);

  return { drag: state, startDrag: config ? start : undefined, preview };
}

/** The nearest ancestor of the tree that scrolls vertically, else the document's scroller. */
function scrollerOf(root: HTMLElement): HTMLElement {
  for (let element = root.parentElement; element; element = element.parentElement) {
    const overflow = getComputedStyle(element).overflowY;
    if ((overflow === "auto" || overflow === "scroll") && element.scrollHeight > element.clientHeight) return element;
  }
  return (document.scrollingElement as HTMLElement | null) ?? document.documentElement;
}

function keyOf(item: HTMLElement) {
  return item.dataset.treeKey ?? "";
}

/** The item's own row, not the rows of the branch drawn inside it. */
function ownRow(item: HTMLElement) {
  return Array.from(item.children).find((child): child is HTMLElement => child.classList.contains("tree-row"));
}

/**
 * The record item a row is drawn under, or undefined at the top. A record's rows sit inside its type
 * groups' headings, which are tree items too but not records, so they are passed over.
 */
function parentItemOf(item: HTMLElement) {
  return item.parentElement?.closest<HTMLElement>(`${ITEM}[data-object-id]`) ?? undefined;
}

/** A row's record level and the record items above it, outermost first. */
function placeOf(item: HTMLElement): RowPlace<HTMLElement> {
  const parents: HTMLElement[] = [];
  for (let parent = parentItemOf(item); parent; parent = parentItemOf(parent)) parents.unshift(parent);
  return { level: parents.length + 1, parents };
}
