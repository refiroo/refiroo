/**
 * A table of the model editor (a type's attributes and relations, an application's types and groups,
 * a relation type's pairs, an attribute type's types): `ui/DataTable`, the record lists' table, over a
 * list the outline holds whole (`fixedWindow`). So its columns size and resize as every other table's
 * do, widths remembered in this browser per table (`ui/TableDisplay`), it stacks on a phone, and each
 * row ends in its menu.
 */

import { useState, type DragEvent, type HTMLAttributes, type ReactNode } from "react";
import { fixedWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { useTableDisplay } from "@/ui/TableDisplay";
import type { ModelDraftOutline } from "@/types";
import { EditableCell, type CellEdit } from "@/features/model-editor/EditableCell";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";

/** The data a row drag carries, so a row dragged for reordering is not taken for an attribute dragged onto a type. */
export const DRAG_ROW = "application/x-rdm-table-row";

/** Reordering by dragging a row: `onMove` is told which row and the position it takes (its index in the list once moved). */
export type RowReorder = { onMove: (rowKey: string, position: number) => void | Promise<unknown> };

/** A column; one with `edit` makes its cells editable in place (`EditableCell`). */
export type EditorColumn<Row> = DataColumn<Row> & { edit?: (row: Row) => CellEdit | undefined };

export function EditorTable<Row>({
  scope,
  label,
  noun,
  columns,
  rows,
  rowKey,
  menu,
  rowAttributes,
  emptyMessage,
  editing,
  reorder,
}: {
  /** Where this table's column widths are remembered, one per kind of table. */
  scope: string;
  label: string;
  noun: [string, string];
  columns: EditorColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  /** The row's operations menu, in the trailing actions column. */
  menu?: (row: Row) => ReactNode;
  rowAttributes?: (row: Row) => HTMLAttributes<HTMLTableRowElement>;
  emptyMessage: ReactNode;
  /** What an editable cell needs to apply its step and word a refusal. */
  editing?: { outline: ModelDraftOutline; run: RunStep };
  /** Rows carry a grip and are dragged into their order; the row's own menu keeps Move up and down for the keyboard. */
  reorder?: RowReorder;
}) {
  const [dragged, setDragged] = useState<string>();
  const [over, setOver] = useState<{ key: string; after: boolean }>();
  const [refused, setRefused] = useState("");
  const end = () => {
    setDragged(undefined);
    setOver(undefined);
  };
  const reorderAttributes = (row: Row): HTMLAttributes<HTMLTableRowElement> => {
    const key = rowKey(row);
    const line = over?.key === key && dragged !== key ? (over.after ? " drop-after" : " drop-before") : "";
    return {
      draggable: true,
      className: `draggable-row${dragged === key ? " dragging" : ""}${line}`,
      onDragStart: (event: DragEvent<HTMLTableRowElement>) => {
        event.dataTransfer.setData(DRAG_ROW, key);
        event.dataTransfer.effectAllowed = "move";
        setDragged(key);
      },
      onDragEnd: end,
      onDragOver: (event: DragEvent<HTMLTableRowElement>) => {
        if (!dragged) return;
        event.preventDefault();
        const box = event.currentTarget.getBoundingClientRect();
        const after = event.clientY > box.top + box.height / 2;
        if (over?.key !== key || over.after !== after) setOver({ key, after });
      },
      onDrop: (event: DragEvent<HTMLTableRowElement>) => {
        if (!dragged) return;
        event.preventDefault();
        const from = rows.findIndex((item) => rowKey(item) === dragged);
        const hovered = rows.findIndex((item) => rowKey(item) === key);
        const box = event.currentTarget.getBoundingClientRect();
        const after = event.clientY > box.top + box.height / 2;
        const slot = hovered + (after ? 1 : 0);
        const position = slot > from ? slot - 1 : slot;
        end();
        if (from < 0 || hovered < 0 || position === from) return;
        setRefused("");
        // A refused step is worded under the table, as an edited cell words its own.
        Promise.resolve(reorder?.onMove(dragged, position)).catch((cause) =>
          setRefused(refusalText(cause, editing?.outline)),
        );
      },
    };
  };
  const shown: DataColumn<Row>[] = columns.map(({ edit, ...column }, position) => {
    const cell =
      edit && editing
        ? (row: Row, index: number) => {
            const spec = edit(row);
            return spec ? (
              <EditableCell edit={spec} outline={editing.outline} run={editing.run}>
                {column.cell(row, index)}
              </EditableCell>
            ) : (
              column.cell(row, index)
            );
          }
        : column.cell;
    // The grip leads the first column, as an attribute's does.
    return reorder && position === 0
      ? {
          ...column,
          cell: (row: Row, index: number) => (
            <>
              <span className="drag-grip" title="Drag to change the order" aria-hidden="true">
                <Icon name="grip" size={14} />
              </span>
              {cell(row, index)}
            </>
          ),
        }
      : { ...column, cell };
  });
  const display = useTableDisplay(
    columns.map((column) => column.key),
    `model-editor:${scope}`,
  );
  return (
    <>
      {refused && (
        <Notice tone="error" title="Not moved">
          {refused}
        </Notice>
      )}
      <div className="editor-table">
        <DataTable<Row>
          columns={shown}
          identityColumn={columns[0]?.key}
          list={fixedWindow(rows)}
          rowKey={rowKey}
          rowAttributes={reorder ? reorderAttributes : rowAttributes}
          actions={
            menu ? { header: <span className="visually-hidden">Actions</span>, cell: menu, width: 56 } : undefined
          }
          columnWidths={display.widths}
          onColumnWidths={display.setWidths}
          label={label}
          noun={noun}
          pageSize={Math.max(rows.length, 1)}
          compact
          whole
          emptyMessage={emptyMessage}
        />
      </div>
    </>
  );
}
