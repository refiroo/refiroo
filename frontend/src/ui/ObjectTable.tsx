/**
 * A list of records in a table (collections, a record's children): `ui/DataTable` with a record on
 * every row. A row is keyed by its record, opens it on a click or from its identity cell, can be
 * selected, and carries the record's action menu (by its button, a right click or Shift+F10). Given
 * a `selection`, a leading checkbox column selects records for a bulk action (0.9 K1). Given
 * `renderCell`, each cell's content passes through it, which edits cells in place
 * (`features/objects/useCellEditing`, 0.10 A9).
 *
 * What it gives the rows changes only with what they show (0.12 LS1, D373): the columns with the
 * shown fields, the current record and `renderCell`; the checkboxes with the selection; the actions
 * with `renderActions` and the open menu. The handlers are read through a ref, so a caller drawn
 * again with new handlers draws no row, and a page arriving in the background draws only its own.
 * Its cells keep to one line once the columns are laid out (`DataTable`'s `oneLine`, D375).
 */

import { useCallback, useLayoutEffect, useMemo, useRef, useState, type HTMLAttributes, type ReactNode } from "react";
import type { EngineModel, ObjectItem } from "@/types";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { FieldValue } from "@/ui/FieldValue";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { attributeName, fieldValue, unavailableWord } from "@/model/fields";
import { StatusPill } from "@/ui/StatusPill";
import { objectTypeHue } from "@/model/hues";
import type { TableSort } from "@/ui/TableSort";

/** The checkboxes' view of a selection; `useRecordSelection` gives one. */
export interface TableSelection {
  isSelected: (id: string) => boolean;
  /** The header checkbox's state over the loaded rows. */
  loaded: "all" | "some" | "none";
  /** `extend` (Shift held) selects the range from the last row checked. */
  onToggle: (item: ObjectItem, extend: boolean) => void;
  onToggleLoaded: () => void;
}

export function ObjectTable({
  compact = false,
  identityColumn,
  sorting,
  model,
  columns,
  list,
  pageSize,
  noun = ["record", "records"],
  seekLabel,
  onAnchorChange,
  onOpen,
  selectedId,
  selection,
  renderActions,
  label = "Objects",
  emptyMessage = "Nothing to show yet.",
  emptyIcon,
  emptyAction,
  columnWidths = {},
  onColumnWidths,
  renderCell,
  fill = false,
  availabilityField,
}: {
  compact?: boolean;
  identityColumn?: string;
  /**
   * The list's model-fed sort (`useTableSort`): a header sorts when its column is a sort field.
   * The caller's toolbar carries the Sort menu, which also reaches columns collapsed at narrow
   * widths or hidden through Display.
   */
  sorting?: TableSort;
  model: EngineModel;
  columns: string[];
  /** The continuous window of rows; the table scrolls it (ADR-030). */
  list: CursorWindow<ObjectItem>;
  pageSize: number;
  noun?: [string, string];
  seekLabel?: string;
  onAnchorChange?: (anchor: string | undefined) => void;
  onOpen: (item: ObjectItem) => void;
  selectedId?: string;
  selection?: TableSelection;
  renderActions?: (item: ObjectItem, menu: { isOpen: boolean; onOpenChange: (open: boolean) => void }) => ReactNode;
  label?: string;
  emptyMessage?: ReactNode;
  /** Decorative, above the empty message: the collection's type tile. */
  emptyIcon?: ReactNode;
  /** What fills the empty list, or clears a search that emptied it. */
  emptyAction?: ReactNode;
  columnWidths?: Record<string, number>;
  /** Stores the widths after a resize (`useTableDisplay`); without it the columns do not resize. */
  onColumnWidths?: (widths: Record<string, number>) => void;
  /** Wraps a cell's content, given its row and column: the cell's in-place editing (A9). */
  renderCell?: (item: ObjectItem, column: string, shown: ReactNode) => ReactNode;
  /** The table fills its page, which does not scroll (0.12 LS1, D371). */
  fill?: boolean;
  /**
   * A boolean field of the records (the table view's `availabilityField`, 0.13 LB): a record whose
   * value is exactly false keeps its row, its name in the secondary ink and a neutral state pill.
   */
  availabilityField?: string | null;
}) {
  const [menuId, setMenuId] = useState<string>();
  const identity = identityColumn ?? (columns.includes("name") ? "name" : columns.includes("id") ? "id" : columns[0]);
  const handlers = useRef({ onOpen, selection });
  useLayoutEffect(() => {
    handlers.current = { onOpen, selection };
  });
  const columnsKey = columns.join("\n");
  const unavailable = useCallback(
    (item: ObjectItem) => Boolean(availabilityField) && fieldValue(item, availabilityField ?? "", model) === false,
    [availabilityField, model],
  );
  const inactiveWord = availabilityField ? unavailableWord(attributeName(model, availabilityField)) : "";
  const identityButton = useCallback(
    (item: ObjectItem, column: string) => (
      <button
        className="cell-link"
        data-record-id={item.id}
        data-row-focus
        aria-current={selectedId === item.id ? "true" : undefined}
        onClick={() => handlers.current.onOpen(item)}
      >
        <FieldValue item={item} field={column} model={model} />
      </button>
    ),
    [selectedId, model],
  );
  const tableColumns = useMemo<DataColumn<ObjectItem>[]>(
    () =>
      (columnsKey ? columnsKey.split("\n") : []).map((column) => ({
        key: column,
        label: attributeName(model, column),
        cell: (item) => {
          const shown =
            column === identity ? (
              unavailable(item) ? (
                <span className="inactive-identity">
                  {identityButton(item, column)}
                  <StatusPill tone="neutral" marker={false} className="inactive-pill">
                    {inactiveWord}
                  </StatusPill>
                </span>
              ) : (
                identityButton(item, column)
              )
            ) : (
              <FieldValue item={item} field={column} model={model} />
            );
          return renderCell ? renderCell(item, column, shown) : shown;
        },
      })),
    [columnsKey, model, identity, identityButton, renderCell, unavailable, inactiveWord],
  );
  const rowHue = useCallback((item: ObjectItem) => objectTypeHue(model, item.objectTypeKey), [model]);
  const isSelected = selection?.isSelected;
  const hasActions = Boolean(renderActions);
  const rowAttributes = useCallback(
    (item: ObjectItem): HTMLAttributes<HTMLTableRowElement> => ({
      className: `clickable-row${selectedId === item.id ? " selected-record" : ""}${
        isSelected?.(item.id) ? " checked-row" : ""
      }${unavailable(item) ? " inactive-record" : ""}`,
      onClick: (event) => {
        // The identity button is the keyboard path; the row is a larger pointer target.
        const target = event.target as HTMLElement;
        // A cell's open editor is a form; a click in it is the editor's.
        if (target.closest("button, a, input, select, textarea, form, [role='menu']")) return;
        if (window.getSelection()?.toString()) return;
        handlers.current.onOpen(item);
      },
      ...(hasActions
        ? {
            onContextMenu: (event) => {
              event.preventDefault();
              setMenuId(item.id);
            },
            onKeyDown: (event) => {
              if (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) {
                event.preventDefault();
                setMenuId(item.id);
              }
            },
          }
        : {}),
    }),
    [selectedId, isSelected, hasActions, unavailable],
  );
  const selectable = Boolean(selection);
  const loaded = selection?.loaded;
  const plural = noun[1];
  const checkboxes = useMemo(
    () =>
      selectable
        ? {
            width: 44,
            header: (
              <SelectionCheckbox
                label={`Select the ${plural} shown`}
                state={loaded ?? "none"}
                onSelect={() => handlers.current.selection?.onToggleLoaded()}
              />
            ),
            cell: (item: ObjectItem) => (
              <SelectionCheckbox
                label={`Select ${item.name}`}
                state={isSelected?.(item.id) ? "all" : "none"}
                onSelect={(extend) => handlers.current.selection?.onToggle(item, extend)}
                gridColumn="selection"
              />
            ),
          }
        : undefined,
    [selectable, loaded, isSelected, plural],
  );
  const actions = useMemo(
    () =>
      renderActions && {
        header: <span className="visually-hidden">Record actions</span>,
        width: 48,
        cell: (item: ObjectItem) =>
          renderActions(item, {
            isOpen: menuId === item.id,
            onOpenChange: (open) => setMenuId(open ? item.id : undefined),
          }),
      },
    [renderActions, menuId],
  );
  return (
    <DataTable<ObjectItem>
      columns={tableColumns}
      identityColumn={identity}
      list={list}
      rowKey={rowKey}
      rowHue={rowHue}
      rowAttributes={rowAttributes}
      selection={checkboxes}
      actions={actions}
      sorting={sorting}
      columnWidths={columnWidths}
      onColumnWidths={onColumnWidths}
      label={label}
      noun={noun}
      pageSize={pageSize}
      seekLabel={seekLabel}
      onAnchorChange={onAnchorChange}
      compact={compact}
      emptyMessage={emptyMessage}
      emptyIcon={emptyIcon}
      emptyAction={emptyAction}
      oneLine
      fill={fill}
    />
  );
}

const rowKey = (item: ObjectItem) => item.id;
