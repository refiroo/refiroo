/**
 * A list of records in a table (collections, a record's children): `ui/DataTable` with a record on
 * every row. A row is keyed by its record, opens it on a click or from its identity cell, can be
 * selected, and carries the record's action menu (by its button, a right click or Shift+F10).
 */

import { useState, type ReactNode } from "react";
import type { EngineModel, ObjectItem } from "@/types";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable } from "@/ui/DataTable";
import { FieldValue } from "@/ui/FieldValue";
import { attributeName } from "@/model/fields";
import { objectTypeHue } from "@/model/hues";
import type { TableSort } from "@/ui/TableSort";

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
  renderActions,
  label = "Objects",
  emptyMessage = "Nothing to show yet.",
  emptyIcon,
  emptyAction,
  columnWidths = {},
  onColumnWidths,
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
}) {
  const [menuId, setMenuId] = useState<string>();
  const identity = identityColumn ?? (columns.includes("name") ? "name" : columns.includes("id") ? "id" : columns[0]);
  return (
    <DataTable<ObjectItem>
      columns={columns.map((column) => ({
        key: column,
        label: attributeName(model, column),
        cell: (item) =>
          column === identity ? (
            <button
              className="cell-link"
              data-record-id={item.id}
              data-row-focus
              aria-current={selectedId === item.id ? "true" : undefined}
              onClick={() => onOpen(item)}
            >
              <FieldValue item={item} field={column} model={model} />
            </button>
          ) : (
            <FieldValue item={item} field={column} model={model} />
          ),
      }))}
      identityColumn={identity}
      list={list}
      rowKey={(item) => item.id}
      rowHue={(item) => objectTypeHue(model, item.objectTypeKey)}
      rowAttributes={(item) => ({
        className: `clickable-row${selectedId === item.id ? " selected-record" : ""}`,
        onClick: (event) => {
          // The identity button is the keyboard path; the row is a larger pointer target.
          const target = event.target as HTMLElement;
          if (target.closest("button, a, input, select, textarea, [role='menu']")) return;
          if (window.getSelection()?.toString()) return;
          onOpen(item);
        },
        ...(renderActions
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
      })}
      actions={
        renderActions && {
          header: <span className="visually-hidden">Record actions</span>,
          width: 48,
          cell: (item) =>
            renderActions(item, {
              isOpen: menuId === item.id,
              onOpenChange: (open) => setMenuId(open ? item.id : undefined),
            }),
        }
      }
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
    />
  );
}
