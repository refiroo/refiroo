/**
 * The board of the workbook canvas (0.17 PL3b, CE1): a free surface of cards, one per list, in a frame per
 * application, with the lines between them. A card is placed anywhere by its top bar, which never changes the
 * model, so a card moved near another cannot link them by accident; connecting is its own gesture, the Connect
 * handle, and every connection is a line with a × that removes it and a click that opens its rule. The board
 * zooms (Ctrl or Command with the wheel, − 100% + Fit), draws lines from the cards' places and holds every
 * card memoised, so a board of sixty lists moves one card at a time. What a gesture means is the page's: the
 * board only says what was dropped where.
 */

import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
import type { ModelDraftOutline } from "@/types/modelAdmin";
import type { ActionMenuItem } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import {
  BoardCard,
  DRAG_COLUMN,
  DRAG_COLUMNS,
  DRAG_FIELD,
  asksForMenu,
  carries,
  cardMenuId,
  droppedColumn,
  fieldMenuId,
  type CardHandlers,
  type DroppedColumns,
  type RenameResult,
} from "./BoardCard";
import {
  CARD_WIDTH,
  cardHeight,
  dropPlace,
  fieldOffset,
  framesOf,
  linePath,
  nudged,
  type CanvasCard,
  type CanvasField,
  type CanvasLine,
  type LoadFigures,
  type Position,
  onBoard,
} from "./canvasModel";
import { centredScroll, fitZoom, scrollAfterZoom, stepZoom, wheelZoom, type CanvasPick } from "./canvasView";

export { DRAG_COLUMN, DRAG_COLUMNS, DRAG_FIELD, droppedColumn, type DroppedColumns };
export const DRAG_SHEET = "application/x-rdm-sheet";

export interface ConnectTarget {
  typeKey?: string;
  fieldId?: string;
  group?: { applicationKey: string; key: string | null; fresh?: boolean };
}

/** What the page can ask of the board. */
export interface BoardApi {
  /** Scrolls so a list (or one of its fields) is in the middle of the view. */
  centreOn: (typeKey: string, fieldId?: string) => boolean;
  /** Zooms to the whole board. */
  fit: () => void;
}

export function CanvasBoard({
  cards,
  lines,
  positions,
  figures,
  outline,
  selection,
  editable,
  canDrag,
  busy,
  hasWorkbook = true,
  zoom = 1,
  flow = false,
  apiRef,
  onZoom,
  onSelect,
  onMove,
  onColumnDrop,
  onColumnToSpace,
  onSheetToSpace,
  onConnect,
  onConnectMenu,
  onFilter,
  onRemoveLine,
  onRefused,
  onFold,
  onRenameList,
  onRenameField,
  onMoveAttribute,
  onReorderAttribute,
  onStepAttribute,
  onOpenSheet,
  openMenu,
  onOpenMenu,
  onOperation,
  menuFor,
  openLine,
  onOpenLine,
  linePopover,
}: {
  cards: readonly CanvasCard[];
  lines: readonly CanvasLine[];
  positions: Readonly<Record<string, Position>>;
  figures: LoadFigures;
  outline: ModelDraftOutline;
  selection?: CanvasPick;
  editable: boolean;
  /** Pointer drags work; off on a phone, where the menus do what the drags do (as in the editor). */
  canDrag: boolean;
  busy: boolean;
  /** The draft has a workbook (the cards say which column fills a field only then). */
  hasWorkbook?: boolean;
  zoom?: number;
  /** One column of cards in the page's flow, with no frames, lines or zoom: the phone's board. */
  flow?: boolean;
  apiRef?: RefObject<BoardApi | null>;
  onZoom?: (zoom: number) => void;
  onSelect: (pick: CanvasPick | undefined) => void;
  /** A card let go at a new place. */
  onMove: (typeKey: string, position: Position) => void;
  onColumnDrop: (column: DroppedColumns, typeKey: string, field?: CanvasField) => void;
  onColumnToSpace: (column: DroppedColumns, at: Position) => void;
  onSheetToSpace: (sheet: string, at: Position) => void;
  onConnect: (from: string, target: ConnectTarget, relate: boolean) => void;
  /** The Connect handle pressed from the keyboard: the page asks which list, field or group. */
  onConnectMenu: (card: CanvasCard) => void;
  /** A column dropped on a list's Filters, or the row pressed (no column): the page chooses one. */
  onFilter: (typeKey: string, column?: DroppedColumns) => void;
  onRemoveLine: (line: CanvasLine) => void;
  onRefused: (typeKey: string) => void;
  onFold?: (typeKey: string, folded: boolean) => void;
  onRenameList?: (card: CanvasCard, name: string) => Promise<RenameResult>;
  onRenameField?: (card: CanvasCard, field: CanvasField, name: string) => Promise<RenameResult>;
  onMoveAttribute?: (from: string, fieldId: string, to: string) => void;
  onReorderAttribute?: (typeKey: string, fieldId: string, besideId: string, after: boolean) => void;
  onStepAttribute?: (card: CanvasCard, field: CanvasField, direction: -1 | 1) => void;
  onOpenSheet?: (card: CanvasCard, sheet: string) => void;
  /** Which element's operations menu is open (`type:<key>`, `field:<key>:<id>`, `application:<key>`). */
  openMenu?: string;
  onOpenMenu?: (id: string | undefined) => void;
  onOperation?: OnOperation;
  /** The canvas's own gestures for a card (Put under…, Relate to…, Add a filter…), in its menu's Canvas section. */
  menuFor: (card: CanvasCard) => ActionMenuItem[];
  /** The line whose rule popover is open, and how it opens. */
  openLine?: string;
  onOpenLine?: (line: CanvasLine | undefined) => void;
  linePopover?: (line: CanvasLine) => ReactNode;
}) {
  const board = useRef<HTMLDivElement>(null);
  const surface = useRef<HTMLDivElement>(null);
  // A card being carried draws where the pointer has it; the model hears of it when it is let go.
  const [carried, setCarried] = useState<{ typeKey: string; position: Position }>();
  const [connecting, setConnecting] = useState<{ from: string; at: Position }>();
  const [over, setOver] = useState<string>();
  // Escape cancels what is carried: the pointer's end then drops nothing.
  const cancelled = useRef(false);
  const scale = flow ? 1 : zoom;
  const live = useRef({ cards, positions, zoom: scale });
  useEffect(() => {
    live.current = { cards, positions, zoom: scale };
  });

  const at = useCallback(
    (card: CanvasCard): Position =>
      carried?.typeKey === card.typeKey ? carried.position : (positions[card.typeKey] ?? { x: 24, y: 24 }),
    [carried, positions],
  );
  /** A point of the screen in the surface's own coordinates, whatever the scroll and the zoom. */
  const local = useCallback((clientX: number, clientY: number): Position => {
    const box = surface.current?.getBoundingClientRect();
    const factor = live.current.zoom || 1;
    return { x: (clientX - (box?.left ?? 0)) / factor, y: (clientY - (box?.top ?? 0)) / factor };
  }, []);

  const extent = useMemo(() => {
    const box = cards.reduce(
      (size, card) => {
        const position = at(card);
        return {
          width: Math.max(size.width, position.x + CARD_WIDTH + 48),
          height: Math.max(size.height, position.y + cardHeight(card) + 96),
        };
      },
      { width: 0, height: 0 },
    );
    return box;
  }, [cards, at]);
  const frames = useMemo(() => (flow ? [] : framesOf(cards, at, outline)), [flow, cards, at, outline]);

  useImperativeHandle(
    apiRef,
    () => ({
      centreOn: (typeKey, fieldId) => {
        const element = board.current;
        const card = live.current.cards.find((item) => item.typeKey === typeKey);
        const position = live.current.positions[typeKey];
        if (!element || !card) return false;
        if (flow) {
          const target = element.ownerDocument.querySelector<HTMLElement>(
            fieldId
              ? `[data-canvas-card="${CSS.escape(typeKey)}"] [data-canvas-field="${CSS.escape(fieldId)}"]`
              : `[data-canvas-card="${CSS.escape(typeKey)}"]`,
          );
          target?.scrollIntoView?.({ block: "center" });
          return Boolean(target);
        }
        if (!position) return false;
        const offset = fieldId ? fieldOffset(card, fieldId) : 0;
        const box = {
          x: position.x,
          y: position.y + (fieldId ? offset - 15 : 0),
          width: CARD_WIDTH,
          height: fieldId ? 30 : cardHeight(card),
        };
        const next = centredScroll(box, live.current.zoom, {
          width: element.clientWidth,
          height: element.clientHeight,
        });
        element.scrollTo?.({ left: next.x, top: next.y });
        return true;
      },
      fit: () => {
        const element = board.current;
        if (!element) return;
        onZoom?.(fitZoom(extent, { width: element.clientWidth, height: element.clientHeight }));
        element.scrollTo?.({ left: 0, top: 0 });
      },
    }),
    [flow, extent, onZoom],
  );

  // Ctrl or Command with the wheel zooms about the pointer; a plain wheel scrolls the board as it does.
  const zoomNow = useRef({ zoom: scale, onZoom });
  useEffect(() => {
    zoomNow.current = { zoom: scale, onZoom };
  });
  useLayoutEffect(() => {
    const element = board.current;
    if (!element || flow) return;
    const wheel = (event: WheelEvent) => {
      if (!(event.ctrlKey || event.metaKey) || !zoomNow.current.onZoom) return;
      event.preventDefault();
      const from = zoomNow.current.zoom;
      const to = wheelZoom(from, event.deltaY);
      if (to === from) return;
      const box = element.getBoundingClientRect();
      const next = scrollAfterZoom(
        { x: element.scrollLeft, y: element.scrollTop },
        { x: event.clientX - box.left, y: event.clientY - box.top },
        from,
        to,
      );
      zoomNow.current.onZoom(to);
      // The scaler grows with the zoom on the next render: the scroll follows it.
      cancelAnimationFrame(zoomFrame);
      zoomFrame = requestAnimationFrame(() => element.scrollTo?.({ left: next.x, top: next.y }));
    };
    let zoomFrame = 0;
    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      element.removeEventListener("wheel", wheel);
      cancelAnimationFrame(zoomFrame);
    };
  }, [flow]);

  /** What a carry or a connect still holds (window listeners, a pending timer): let go of when the board goes. */
  const holding = useRef(new Set<() => void>());
  useEffect(() => {
    const held = holding.current;
    return () => {
      for (const release of [...held]) release();
      held.clear();
    };
  }, []);

  function carry(event: PointerEvent<HTMLElement>, card: CanvasCard) {
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    // The name is most of the top bar: a press on it carries the card once the pointer moves, and a click renames it.
    const onName = Boolean(target.closest(".canvas-card-name")) && !target.closest("input");
    if (!onName && target.closest("button, a, input")) return;
    const start = at(card);
    const point = local(event.clientX, event.clientY);
    const grab = { x: point.x - start.x, y: point.y - start.y };
    const head = event.currentTarget;
    const pointer = event.pointerId;
    const from = { x: event.clientX, y: event.clientY };
    let carrying = false;
    const begin = () => {
      carrying = true;
      try {
        head.setPointerCapture(pointer);
      } catch {
        // The pointer is gone: the window's listeners still follow it.
      }
      onSelect({ element: "type", key: card.typeKey });
    };
    if (!onName) begin();
    let last = start;
    cancelled.current = false;
    const move = (moved: globalThis.PointerEvent) => {
      if (moved.pointerId !== pointer || cancelled.current) return;
      if (!carrying) {
        if (Math.hypot(moved.clientX - from.x, moved.clientY - from.y) < 4) return;
        begin();
      }
      const now = local(moved.clientX, moved.clientY);
      last = onBoard({ x: now.x - grab.x, y: now.y - grab.y });
      setCarried({ typeKey: card.typeKey, position: last });
    };
    const release = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", end);
      window.removeEventListener("pointercancel", end);
      holding.current.delete(release);
    };
    const end = (ended: globalThis.PointerEvent) => {
      if (ended.pointerId !== pointer) return;
      release();
      if (!carrying) return;
      setCarried(undefined);
      if (onName) {
        // A carry that started on the name is no click on it: the rename does not open.
        const swallow = (click: MouseEvent) => {
          click.stopPropagation();
          click.preventDefault();
        };
        const unswallow = () => {
          clearTimeout(timer);
          window.removeEventListener("click", swallow, { capture: true });
          holding.current.delete(unswallow);
        };
        window.addEventListener("click", swallow, { capture: true, once: true });
        const timer = setTimeout(unswallow, 0);
        holding.current.add(unswallow);
      }
      // Escape let go without a drop: the card stays where it was.
      if (!cancelled.current && (last.x !== start.x || last.y !== start.y)) onMove(card.typeKey, last);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end);
    window.addEventListener("pointercancel", end);
    holding.current.add(release);
  }

  function connect(event: PointerEvent<HTMLButtonElement>, card: CanvasCard) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const handle = event.currentTarget;
    cancelled.current = false;
    handle.setPointerCapture(event.pointerId);
    setConnecting({ from: card.typeKey, at: local(event.clientX, event.clientY) });
    const targetAt = (x: number, y: number): ConnectTarget | undefined => {
      const element = document.elementFromPoint(x, y) as HTMLElement | null;
      const group = element?.closest<HTMLElement>("[data-canvas-group]");
      if (group)
        return {
          group: {
            applicationKey: group.dataset.application ?? "",
            key: group.dataset.canvasGroup || null,
            fresh: group.dataset.fresh === "true",
          },
        };
      const cardElement = element?.closest<HTMLElement>("[data-canvas-card]");
      if (!cardElement || cardElement.dataset.canvasCard === card.typeKey) return undefined;
      return {
        typeKey: cardElement.dataset.canvasCard,
        fieldId: element?.closest<HTMLElement>("[data-canvas-field]")?.dataset.canvasField,
      };
    };
    const move = (moved: globalThis.PointerEvent) => {
      setConnecting({ from: card.typeKey, at: local(moved.clientX, moved.clientY) });
      const target = targetAt(moved.clientX, moved.clientY);
      setOver(target?.typeKey ? `${target.typeKey}${target.fieldId ? `/${target.fieldId}` : ""}` : undefined);
    };
    const release = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", end);
      handle.removeEventListener("pointercancel", end);
      holding.current.delete(release);
    };
    const end = (ended: globalThis.PointerEvent) => {
      release();
      setConnecting(undefined);
      setOver(undefined);
      if (ended.type === "pointercancel" || cancelled.current) return;
      const target = targetAt(ended.clientX, ended.clientY);
      if (target) onConnect(card.typeKey, target, ended.altKey);
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
    holding.current.add(release);
  }

  // Escape lets go of whatever is carried without a drop.
  useEffect(() => {
    if (!connecting && !carried) return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      cancelled.current = true;
      setConnecting(undefined);
      setCarried(undefined);
      setOver(undefined);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [connecting, carried]);

  // What a card calls back goes through one stable object, so a card is redrawn only for its own data.
  const calls = useRef({
    onSelect,
    onMove,
    onConnectMenu,
    onFold,
    onRenameList,
    onRenameField,
    onMoveAttribute,
    onReorderAttribute,
    onStepAttribute,
    onFilter,
    onRefused,
    onColumnDrop,
    onOpenSheet,
    onOpenMenu,
    onOperation,
    menuFor,
    carry,
    connect,
    positions,
  });
  useEffect(() => {
    calls.current = {
      onSelect,
      onMove,
      onConnectMenu,
      onFold,
      onRenameList,
      onRenameField,
      onMoveAttribute,
      onReorderAttribute,
      onStepAttribute,
      onFilter,
      onRefused,
      onColumnDrop,
      onOpenSheet,
      onOpenMenu,
      onOperation,
      menuFor,
      carry,
      connect,
      positions,
    };
  });
  const handlers = useMemo<CardHandlers>(
    () => ({
      select: (pick) => calls.current.onSelect(pick),
      carry: (event, card) => calls.current.carry(event, card),
      connectDown: (event, card) => calls.current.connect(event, card),
      connectMenu: (card) => calls.current.onConnectMenu(card),
      nudge: (card, key) => {
        const next = nudged(calls.current.positions[card.typeKey] ?? { x: 24, y: 24 }, key);
        if (!next) return false;
        calls.current.onSelect({ element: "type", key: card.typeKey });
        calls.current.onMove(card.typeKey, next);
        return true;
      },
      fold: (typeKey, folded) => calls.current.onFold?.(typeKey, folded),
      renameList: (card, name) => calls.current.onRenameList?.(card, name) ?? Promise.resolve(undefined),
      renameField: (card, field, name) =>
        calls.current.onRenameField?.(card, field, name) ?? Promise.resolve(undefined),
      filter: (typeKey, column) => calls.current.onFilter(typeKey, column),
      refused: (typeKey) => calls.current.onRefused(typeKey),
      columnDrop: (column, typeKey, field) => calls.current.onColumnDrop(column, typeKey, field),
      moveAttribute: (from, fieldId, to) => calls.current.onMoveAttribute?.(from, fieldId, to),
      reorderAttribute: (typeKey, fieldId, besideId, after) =>
        calls.current.onReorderAttribute?.(typeKey, fieldId, besideId, after),
      stepAttribute: (card, field, direction) => calls.current.onStepAttribute?.(card, field, direction),
      openSheet: (card, sheet) => calls.current.onOpenSheet?.(card, sheet),
      openMenu: (id) => calls.current.onOpenMenu?.(id),
      operate: (operation, target, preset) => calls.current.onOperation?.(operation, target, preset),
      menuExtra: (card) => calls.current.menuFor(card),
    }),
    [],
  );

  const byKey = new Map(cards.map((card) => [card.typeKey, card]));
  const acceptsDrop = (event: DragEvent) =>
    editable && canDrag && (carries(event, DRAG_COLUMN) || carries(event, DRAG_SHEET))
      ? (event.preventDefault(), true)
      : false;
  const emptyBoard = (target: EventTarget, current: EventTarget) =>
    target === current ||
    (target as HTMLElement).classList?.contains("canvas-surface") ||
    (target as HTMLElement).classList?.contains("canvas-scaler");

  const geometry = (line: CanvasLine) => {
    const from = byKey.get(line.from);
    const to = byKey.get(line.to);
    if (!from || !to) return undefined;
    return linePath(at(from), cardHeight(from), at(to), cardHeight(to), fieldOffset(from, line.fromField));
  };
  const frameFor = (key: string) => outline.applications.find((item) => item.key === key);

  return (
    <div className="canvas-board-wrap">
      <div
        ref={board}
        className={`canvas-board${flow ? " canvas-board-flow" : ""}`}
        onPointerDown={(event) => {
          if (event.target !== event.currentTarget && !emptyBoard(event.target, event.currentTarget)) return;
          onSelect(undefined);
          onOpenLine?.(undefined);
        }}
        onDragOver={acceptsDrop}
        onDrop={(event) => {
          if (!acceptsDrop(event)) return;
          const place = dropPlace(local(event.clientX, event.clientY));
          const column = droppedColumn(event);
          const sheet = event.dataTransfer.getData(DRAG_SHEET);
          if (column) onColumnToSpace(column, place);
          else if (sheet) onSheetToSpace(sheet, place);
        }}
      >
        <div
          className="canvas-scaler"
          style={flow ? undefined : { width: extent.width * scale, height: extent.height * scale }}
        >
          <div
            ref={surface}
            className="canvas-surface"
            style={
              flow
                ? undefined
                : cards.length === 0
                  ? { width: "100%", minHeight: 360 }
                  : {
                      width: extent.width,
                      height: extent.height,
                      transform: scale === 1 ? undefined : `scale(${scale})`,
                    }
            }
            aria-busy={busy}
          >
            {frames.map((frame) => (
              <div
                key={frame.applicationKey}
                className={`canvas-frame${selection?.element === "application" && selection.key === frame.applicationKey ? " selected" : ""}`}
                style={{ left: frame.x, top: frame.y, width: frame.width, height: frame.height }}
                data-canvas-frame={frame.applicationKey}
                onContextMenu={(event) => {
                  event.preventDefault();
                  onSelect({ element: "application", key: frame.applicationKey });
                  onOpenMenu?.(`application:${frame.applicationKey}`);
                }}
              >
                <span className="canvas-frame-label">
                  <button
                    type="button"
                    className="canvas-frame-name"
                    aria-label={`Application ${frame.name}`}
                    onClick={() => onSelect({ element: "application", key: frame.applicationKey })}
                    onKeyDown={(event: KeyboardEvent) => {
                      if (!asksForMenu(event)) return;
                      event.preventDefault();
                      onSelect({ element: "application", key: frame.applicationKey });
                      onOpenMenu?.(`application:${frame.applicationKey}`);
                    }}
                  >
                    {frame.name} <span className="canvas-frame-kind">application</span>
                  </button>
                  {onOperation && frameFor(frame.applicationKey) && (
                    <OperationsMenu
                      tooltip=""
                      label={`Operations for the application ${frame.name}`}
                      target={{ on: "application", applicationKey: frame.applicationKey }}
                      outline={outline}
                      onOperation={onOperation}
                      isOpen={openMenu === `application:${frame.applicationKey}`}
                      onOpenChange={(open) => onOpenMenu?.(open ? `application:${frame.applicationKey}` : undefined)}
                    />
                  )}
                </span>
              </div>
            ))}
            {!flow && (
              <svg className="canvas-lines" aria-hidden="true">
                {lines.map((line) => {
                  const path = geometry(line);
                  if (!path) return null;
                  const hot = selection?.element === "line" && selection.key === line.id;
                  return (
                    <g key={line.id}>
                      <path
                        d={path.d}
                        className={`canvas-line canvas-line-${line.kind}${hot ? " canvas-line-hot" : ""}`}
                      />
                      <path
                        d={path.d}
                        className="canvas-line-hit"
                        data-canvas-line={line.id}
                        onClick={() => {
                          onSelect({ element: "line", key: line.id });
                          onOpenLine?.(line);
                        }}
                        onContextMenu={(event) => {
                          event.preventDefault();
                          onSelect({ element: "line", key: line.id });
                          onOpenLine?.(line);
                        }}
                      />
                    </g>
                  );
                })}
                {connecting && byKey.get(connecting.from) && (
                  <path
                    className="canvas-line canvas-line-pending"
                    d={`M ${at(byKey.get(connecting.from)!).x + CARD_WIDTH} ${at(byKey.get(connecting.from)!).y + 22} L ${connecting.at.x} ${connecting.at.y}`}
                  />
                )}
              </svg>
            )}
            {editable &&
              !flow &&
              lines.map((line) => {
                const path = geometry(line);
                if (!path) return null;
                const { mid } = path;
                return (
                  <span key={line.id} className="canvas-line-controls" style={{ left: mid.x, top: mid.y }}>
                    <button
                      type="button"
                      className="canvas-line-pick"
                      aria-label={`Rule of: ${line.label}`}
                      title={`Rule: ${line.label}`}
                      onClick={() => {
                        onSelect({ element: "line", key: line.id });
                        onOpenLine?.(line);
                      }}
                      onKeyDown={(event) => {
                        if (!asksForMenu(event)) return;
                        event.preventDefault();
                        onSelect({ element: "line", key: line.id });
                        onOpenLine?.(line);
                      }}
                    >
                      <Icon name="sliders" size={12} />
                    </button>
                    <button
                      type="button"
                      className="canvas-line-remove"
                      aria-label={`Remove: ${line.label}`}
                      title={`Remove: ${line.label}`}
                      onClick={() => onRemoveLine(line)}
                    >
                      <Icon name="close" size={12} />
                    </button>
                  </span>
                );
              })}
            {!flow &&
              openLine &&
              linePopover &&
              (() => {
                const line = lines.find((item) => item.id === openLine);
                const path = line && geometry(line);
                if (!line || !path) return null;
                return (
                  <div
                    key={line.id}
                    className="canvas-line-popover-anchor"
                    style={{
                      left: path.mid.x,
                      top: path.mid.y + 18,
                      transform: scale === 1 ? undefined : `scale(${1 / scale})`,
                    }}
                  >
                    {linePopover(line)}
                  </div>
                );
              })()}
            {cards.length === 0 && (
              <p className="canvas-empty">
                Nothing is on the board yet. Add an object type with the <strong>+</strong> above; drag a sheet here to
                make an object type of its rows, or a column to make one of its values.
              </p>
            )}
            {cards.map((card) => {
              const figure = figures.byType[card.typeKey];
              const mine = selection?.key === card.typeKey ? selection : undefined;
              const menu =
                openMenu === cardMenuId(card.typeKey)
                  ? "card"
                  : openMenu?.startsWith(fieldMenuId(card.typeKey, ""))
                    ? openMenu.slice(fieldMenuId(card.typeKey, "").length)
                    : undefined;
              return (
                <BoardCard
                  key={card.typeKey}
                  card={card}
                  position={flow ? undefined : at(card)}
                  outline={outline}
                  loads={figure?.loads}
                  refused={figure?.refused}
                  checking={figures.state === "checking"}
                  selected={mine?.element === "type"}
                  field={mine?.element === "field" ? mine.field : undefined}
                  carried={carried?.typeKey === card.typeKey}
                  over={over === card.typeKey}
                  overField={over?.startsWith(`${card.typeKey}/`) ? over.slice(card.typeKey.length + 1) : undefined}
                  menu={menu}
                  editable={editable}
                  canDrag={canDrag}
                  workbook={hasWorkbook}
                  h={handlers}
                />
              );
            })}
          </div>
        </div>
      </div>
      {!flow && onZoom && (
        <div className="canvas-zoom" role="group" aria-label="Zoom">
          <button
            type="button"
            aria-label="Zoom out"
            disabled={scale <= 0.25}
            onClick={() => onZoom(stepZoom(scale, -1))}
          >
            <Icon name="minus" size={14} />
          </button>
          <button type="button" aria-label="Zoom to 100%" title="Zoom to 100%" onClick={() => onZoom(1)}>
            {Math.round(scale * 100)}%
          </button>
          <button type="button" aria-label="Zoom in" disabled={scale >= 2} onClick={() => onZoom(stepZoom(scale, 1))}>
            <Icon name="plus" size={14} />
          </button>
          <button type="button" aria-label="Fit the whole board" onClick={() => apiRef?.current?.fit()}>
            Fit
          </button>
        </div>
      )}
    </div>
  );
}
