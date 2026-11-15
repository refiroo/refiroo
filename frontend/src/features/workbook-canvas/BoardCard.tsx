/**
 * One list on the board (0.17 PL3b, CE1): its top bar (grip, fold, name that edits where it stands, Connect, the
 * operations menu), a row per field, a "New attribute" button, its filters and its foot with the mark pill and the
 * counts. Drawn by hand-held handlers the board owns and keeps stable, and memoised, so a board of sixty
 * lists redraws only the card a step or a drag changed. What a gesture means is the page's.
 */

import { memo, type DragEvent, type PointerEvent } from "react";
import { MarkPill } from "@/features/model-editor/MarkPill";
import { OperationButton } from "@/features/model-editor/ElementPanel";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
import type { OperationTarget } from "@/features/model-editor/operations";
import { count } from "@/lib/count";
import type { ModelDraftOutline } from "@/types/modelAdmin";
import type { ActionMenuItem } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { StatusPill } from "@/ui/StatusPill";
import { TextInPlace } from "@/ui/TextInPlace";
import type { CanvasCard, CanvasField, Position } from "./canvasModel";
import { CARD_WIDTH } from "./canvasModel";
import { targetOfField, type CanvasPick } from "./canvasView";

export const DRAG_FIELD = "application/x-rdm-canvas-field";
/** The same payload the model editor's source pane drags: `sheet \u0000 header`. */
export const DRAG_COLUMN = "application/x-rdm-column";
/** Every column of a selection the pane drags: JSON `{sheet, headers}` (0.17 PL3b, PP-D6). */
export const DRAG_COLUMNS = "application/x-rdm-columns";

/** The column or columns a drag carries: the headers of a selection, else the one dragged. */
export interface DroppedColumns {
  sheet: string;
  header: string;
  headers: string[];
}

/** The attribute row being dragged: its card and row, which the drop targets read (a drag's data is hidden until the drop). */
let dragged: { typeKey: string; fieldId: string } | undefined;

export const carries = (event: DragEvent, type: string) => event.dataTransfer.types.includes(type);

export function droppedColumn(event: DragEvent): DroppedColumns | undefined {
  const [sheet, header] = event.dataTransfer.getData(DRAG_COLUMN).split("\u0000");
  if (!sheet || !header) return undefined;
  let headers = [header];
  try {
    const many = JSON.parse(event.dataTransfer.getData(DRAG_COLUMNS) || "null") as {
      sheet?: string;
      headers?: unknown;
    };
    if (many?.sheet === sheet && Array.isArray(many.headers) && many.headers.length > 1)
      headers = many.headers.filter((item): item is string => typeof item === "string");
  } catch {
    // A payload that is not ours is the one column.
  }
  return { sheet, header, headers };
}

/** A rename's result: false when the draft moved on (nothing saved), else the call that puts the old name back. */
export type RenameResult = void | false | (() => Promise<unknown>);

/** What a card calls back. Stable for the board's life, so a card is redrawn only when its own data changes. */
export interface CardHandlers {
  select: (pick: CanvasPick | undefined) => void;
  carry: (event: PointerEvent<HTMLElement>, card: CanvasCard) => void;
  connectDown: (event: PointerEvent<HTMLButtonElement>, card: CanvasCard) => void;
  connectMenu: (card: CanvasCard) => void;
  nudge: (card: CanvasCard, key: string) => boolean;
  fold: (typeKey: string, folded: boolean) => void;
  renameList: (card: CanvasCard, name: string) => Promise<RenameResult>;
  renameField: (card: CanvasCard, field: CanvasField, name: string) => Promise<RenameResult>;
  filter: (typeKey: string, column?: DroppedColumns) => void;
  refused: (typeKey: string) => void;
  columnDrop: (column: DroppedColumns, typeKey: string, field?: CanvasField) => void;
  /** An attribute row dropped on another object type's card: the editor's Move to…. */
  moveAttribute: (from: string, fieldId: string, to: string) => void;
  /** An attribute row dropped beside another attribute row of its card: its position. */
  reorderAttribute: (typeKey: string, fieldId: string, besideId: string, after: boolean) => void;
  /** Alt+ArrowUp / Alt+ArrowDown on an attribute row: the editor's Move up / Move down. */
  stepAttribute: (card: CanvasCard, field: CanvasField, direction: -1 | 1) => void;
  openSheet: (card: CanvasCard, sheet: string) => void;
  /** Opens (or closes) one element's operations menu; the page keeps which is open. */
  openMenu: (id: string | undefined) => void;
  operate: OnOperation;
  /** The canvas's own gestures for the card, in the card menu's Canvas section. */
  menuExtra: (card: CanvasCard) => ActionMenuItem[];
}

export const cardMenuId = (typeKey: string) => `type:${typeKey}`;
export const fieldMenuId = (typeKey: string, fieldId: string) => `field:${typeKey}:${fieldId}`;

/** Shift+F10 and the context-menu key open an element's menu, as a right click does. */
export const asksForMenu = (event: { key: string; shiftKey: boolean }) =>
  event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey);

interface CardProps {
  card: CanvasCard;
  /** Absent in the one-column layout, where the card sits in the flow. */
  position?: Position;
  outline: ModelDraftOutline;
  loads?: number;
  refused?: number;
  checking: boolean;
  /** The card itself is the selection. */
  selected: boolean;
  /** The selected field of this card. */
  field?: string;
  carried: boolean;
  over: boolean;
  overField?: string;
  /** Which menu of this card is open: `card`, or a field's id. */
  menu?: string;
  editable: boolean;
  canDrag: boolean;
  /** The draft has a workbook: a field no column fills says so; without one there is nothing to fill it from. */
  workbook: boolean;
  h: CardHandlers;
}

/** The editor's New attribute button for the object type: its form opens, the same as in the model editor. */
function NewAttribute({ card, outline, h }: { card: CanvasCard; outline: ModelDraftOutline; h: CardHandlers }) {
  return (
    <div className="canvas-newfield">
      <OperationButton
        id="type-new-attribute"
        target={{ on: "objectType", objectType: card.typeKey }}
        outline={outline}
        onOperation={h.operate}
      >
        <Icon name="plus" size={12} /> New attribute
      </OperationButton>
    </div>
  );
}

/** The dragged attribute row is of this card and another row of it: a drop beside this row reorders. */
const beside = (drag: typeof dragged, card: CanvasCard, field: CanvasField) =>
  drag !== undefined && drag.typeKey === card.typeKey && drag.fieldId !== field.id && field.kind === "attribute";

function FieldRow({
  card,
  field,
  outline,
  selected,
  over,
  menuOpen,
  editable,
  canDrag,
  workbook,
  h,
}: {
  card: CanvasCard;
  field: CanvasField;
  outline: ModelDraftOutline;
  selected: boolean;
  over: boolean;
  menuOpen: boolean;
  editable: boolean;
  canDrag: boolean;
  workbook: boolean;
  h: CardHandlers;
}) {
  const renamable = editable && (field.kind === "attribute" || field.kind === "relation");
  const target: OperationTarget = targetOfField(card, field, outline);
  const pick = () => h.select({ element: "field", key: card.typeKey, field: field.id });
  const name = (
    <>
      {field.label}
      {field.required && (
        <span className="canvas-field-mark" title="Required">
          *
        </span>
      )}
    </>
  );
  return (
    <li
      className={`canvas-field canvas-field-${field.kind}${over ? " over" : ""}${selected ? " selected" : ""}`}
      data-canvas-field={field.id}
      draggable={editable && canDrag && (field.columns.length > 0 || field.kind === "attribute")}
      tabIndex={field.kind === "attribute" ? (selected ? 0 : -1) : undefined}
      onClick={pick}
      onContextMenu={(event) => {
        event.preventDefault();
        event.stopPropagation();
        pick();
        h.openMenu(fieldMenuId(card.typeKey, field.id));
      }}
      onKeyDown={(event) => {
        if (editable && field.kind === "attribute" && event.altKey && event.target === event.currentTarget) {
          const direction = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
          if (direction) {
            event.preventDefault();
            event.stopPropagation();
            h.stepAttribute(card, field, direction);
            return;
          }
        }
        if (!asksForMenu(event)) return;
        event.preventDefault();
        event.stopPropagation();
        pick();
        h.openMenu(fieldMenuId(card.typeKey, field.id));
      }}
      onDragStart={(event) => {
        event.dataTransfer.setData(DRAG_FIELD, `${card.typeKey}\u0000${field.id}`);
        event.dataTransfer.effectAllowed = "move";
        dragged = field.kind === "attribute" ? { typeKey: card.typeKey, fieldId: field.id } : undefined;
      }}
      onDragEnd={() => {
        dragged = undefined;
      }}
      onDragOver={(event) => {
        if (editable && canDrag && carries(event, DRAG_FIELD) && beside(dragged, card, field)) {
          event.preventDefault();
          event.stopPropagation();
          const box = event.currentTarget.getBoundingClientRect();
          const after = event.clientY > box.top + box.height / 2;
          event.currentTarget.classList.toggle("drop-before", !after);
          event.currentTarget.classList.toggle("drop-after", after);
          return;
        }
        if (!editable || !canDrag || !carries(event, DRAG_COLUMN)) return;
        event.preventDefault();
        event.stopPropagation();
        event.currentTarget.classList.add("over");
      }}
      onDragLeave={(event) => event.currentTarget.classList.remove("over", "drop-before", "drop-after")}
      onDrop={(event) => {
        const after = event.currentTarget.classList.contains("drop-after");
        event.currentTarget.classList.remove("over", "drop-before", "drop-after");
        if (editable && canDrag && carries(event, DRAG_FIELD) && dragged && beside(dragged, card, field)) {
          event.preventDefault();
          event.stopPropagation();
          h.reorderAttribute(card.typeKey, dragged.fieldId, field.id, after);
          dragged = undefined;
          return;
        }
        const column = droppedColumn(event);
        if (!editable || !canDrag || !column) return;
        event.preventDefault();
        event.stopPropagation();
        h.columnDrop(column, card.typeKey, field);
      }}
    >
      <span className="canvas-field-label" title={field.label}>
        {renamable ? (
          <TextInPlace
            value={field.label}
            label={`Name of the ${field.kind === "relation" ? "relationship" : "attribute"} ${field.label}`}
            savedText="Renamed."
            onSave={(next) => h.renameField(card, field, next)}
          >
            <span className="canvas-field-name-text">{name}</span>
          </TextInPlace>
        ) : (
          name
        )}
        {field.proposed && !card.proposed && <span className="canvas-field-proposed">Proposed</span>}
      </span>
      <span className="canvas-field-type">
        {field.typeLabel}
        {field.unique && " · unique"}
      </span>
      <span className="canvas-field-from">
        {field.columns.length
          ? field.columns.map((column) => column.header).join(", ")
          : workbook && (field.kind === "name" || field.kind === "attribute")
            ? "no column yet"
            : ""}
      </span>
      <span className="canvas-field-menu">
        {selected && editable && (
          <OperationsMenu
            tooltip=""
            label={`Operations for the attribute ${field.label}`}
            target={target}
            outline={outline}
            onOperation={h.operate}
            isOpen={menuOpen}
            onOpenChange={(open) => h.openMenu(open ? fieldMenuId(card.typeKey, field.id) : undefined)}
          />
        )}
      </span>
    </li>
  );
}

function BoardCardView({
  card,
  position,
  outline,
  loads,
  refused,
  checking,
  selected,
  field,
  carried,
  over,
  overField,
  menu,
  editable,
  canDrag,
  workbook,
  h,
}: CardProps) {
  const target: OperationTarget = { on: "objectType", objectType: card.typeKey };
  const mark = card.proposed ? undefined : card.mark;
  const countable = loads !== undefined || checking;
  return (
    <section
      className={`canvas-card${selected ? " selected" : ""}${carried ? " carried" : ""}${over ? " over" : ""}${card.quiet ? " quiet" : ""}${card.folded ? " folded" : ""}${position ? "" : " in-flow"}`}
      style={position ? { left: position.x, top: position.y, width: CARD_WIDTH } : undefined}
      data-canvas-card={card.typeKey}
      role="group"
      aria-label={card.name}
      aria-keyshortcuts="ArrowUp ArrowDown ArrowLeft ArrowRight Shift+F10"
      tabIndex={0}
      onPointerDownCapture={() => {
        if (!selected && field === undefined) h.select({ element: "type", key: card.typeKey });
      }}
      onContextMenu={(event) => {
        event.preventDefault();
        h.select({ element: "type", key: card.typeKey });
        h.openMenu(cardMenuId(card.typeKey));
      }}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (asksForMenu(event)) {
          event.preventDefault();
          h.select({ element: "type", key: card.typeKey });
          h.openMenu(cardMenuId(card.typeKey));
          return;
        }
        // A focused card moves sixteen pixels a press; keys inside it (its menus, buttons) are theirs.
        if (editable && h.nudge(card, event.key)) event.preventDefault();
      }}
      onDragOver={(event) => {
        if (editable && canDrag && carries(event, DRAG_FIELD) && dragged && dragged.typeKey !== card.typeKey) {
          event.preventDefault();
          event.stopPropagation();
          return;
        }
        if (!editable || !canDrag || !carries(event, DRAG_COLUMN)) return;
        event.preventDefault();
        event.stopPropagation();
      }}
      onDrop={(event) => {
        if (editable && canDrag && carries(event, DRAG_FIELD) && dragged && dragged.typeKey !== card.typeKey) {
          event.preventDefault();
          event.stopPropagation();
          const moved = dragged;
          dragged = undefined;
          h.moveAttribute(moved.typeKey, moved.fieldId, card.typeKey);
          return;
        }
        const column = droppedColumn(event);
        if (!editable || !canDrag || !column) return;
        event.preventDefault();
        event.stopPropagation();
        h.columnDrop(column, card.typeKey);
      }}
    >
      <header className="canvas-card-head" onPointerDown={(event) => canDrag && h.carry(event, card)}>
        <Icon name="grip" size={14} />
        <button
          type="button"
          className="canvas-fold"
          aria-expanded={!card.folded}
          aria-label={card.folded ? `Unfold ${card.name}` : `Fold ${card.name} to its top bar`}
          title={card.folded ? "Unfold" : "Fold to the top bar"}
          onClick={() => h.fold(card.typeKey, !card.folded)}
        >
          <Icon name={card.folded ? "chevron-right" : "chevron-down"} size={14} />
        </button>
        <span className="canvas-card-name" title={card.name}>
          {editable ? (
            <TextInPlace
              value={card.name}
              label={`Name of the object type ${card.name}`}
              savedText="Renamed."
              onSave={(next) => h.renameList(card, next)}
            >
              <span className="canvas-card-name-text">{card.name}</span>
            </TextInPlace>
          ) : (
            card.name
          )}
        </span>
        {editable && !card.folded && (
          <button
            type="button"
            className="canvas-connect"
            aria-label={`Connect ${card.name}: drag onto an object type, an attribute or a group, or press to choose one`}
            title="Connect: drag onto an object type to put this one under it, onto an attribute for a relationship, onto a group to place it. Press Enter to choose from a list."
            onPointerDown={(event) => canDrag && h.connectDown(event, card)}
            onClick={(event) => {
              // A press from the keyboard has no pointer: it asks which list, field or group instead.
              if (event.detail === 0 || !canDrag) h.connectMenu(card);
            }}
          >
            Connect <Icon name="arrow-right" size={12} />
          </button>
        )}
        <OperationsMenu
          tooltip=""
          label={`Actions for ${card.name}`}
          target={target}
          outline={outline}
          onOperation={h.operate}
          extra={h.menuExtra(card)}
          isOpen={menu === "card"}
          onOpenChange={(open) => h.openMenu(open ? cardMenuId(card.typeKey) : undefined)}
        />
      </header>
      {!card.folded && (
        <>
          <ul className="canvas-fields">
            {card.fields.map((item) => (
              <FieldRow
                key={item.id}
                card={card}
                field={item}
                outline={outline}
                selected={field === item.id}
                over={overField === item.id}
                menuOpen={menu === item.id}
                editable={editable}
                canDrag={canDrag}
                workbook={workbook}
                h={h}
              />
            ))}
          </ul>
          {editable && <NewAttribute card={card} outline={outline} h={h} />}
          <div
            className="canvas-card-filters"
            data-canvas-filters={card.typeKey}
            onDragOver={(event) => {
              if (!editable || !canDrag || !carries(event, DRAG_COLUMN)) return;
              event.preventDefault();
              event.stopPropagation();
              event.currentTarget.classList.add("over");
            }}
            onDragLeave={(event) => event.currentTarget.classList.remove("over")}
            onDrop={(event) => {
              event.currentTarget.classList.remove("over");
              const column = droppedColumn(event);
              if (!editable || !canDrag || !column) return;
              event.preventDefault();
              event.stopPropagation();
              h.filter(card.typeKey, column);
            }}
          >
            <span className="canvas-filters-label">Filters</span>
            <span className="canvas-filters-list">
              {card.filters.length ? card.filters.map((filter) => filter.label).join(", ") : "none"}
            </span>
            {editable && (
              <button
                type="button"
                className="canvas-filters-add"
                aria-label={`Add a filter to ${card.name}: drop a column here, or press to choose one`}
                title="Drop a column here, or press to choose one"
                onClick={() => h.filter(card.typeKey)}
              >
                <Icon name="plus" size={12} />
              </button>
            )}
          </div>
          <footer className="canvas-card-foot">
            {card.sheets.length ? (
              <button
                type="button"
                className="canvas-card-sheets"
                title={`Open ${card.sheets[0]} as a list`}
                onClick={() => h.openSheet(card, card.sheets[0])}
              >
                from {card.sheets.join(", ")}
              </button>
            ) : (
              <span className="canvas-card-sheets">no sheet loads it</span>
            )}
            {card.proposed ? (
              <StatusPill tone="publication" size="small" marker={false}>
                Proposed
              </StatusPill>
            ) : (
              mark && <MarkPill mark={mark} />
            )}
            {checking ? (
              <span className="canvas-count">Checking…</span>
            ) : countable ? (
              <>
                <span className="canvas-count canvas-count-loads">{count(loads ?? 0)} load</span>
                {(refused ?? 0) > 0 && (
                  <button
                    type="button"
                    className="canvas-count canvas-count-refused"
                    onClick={() => h.refused(card.typeKey)}
                  >
                    {count(refused ?? 0)} refused
                  </button>
                )}
              </>
            ) : null}
          </footer>
        </>
      )}
    </section>
  );
}

export const BoardCard = memo(BoardCardView);
