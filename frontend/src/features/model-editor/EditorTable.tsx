/**
 * A table of the model editor (a type's attributes and relations, an application's types and groups,
 * a relation type's pairs, an attribute type's types): `ui/DataTable`, the record lists' table, over a
 * list the outline holds whole (`fixedWindow`). So its columns size and resize as every other table's
 * do, widths remembered in this browser per table (`ui/TableDisplay`), it stacks on a phone, and each
 * row ends in its menu.
 */

import type { HTMLAttributes, ReactNode } from "react";
import { fixedWindow } from "@/lib/hooks/useCursorWindow";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { useTableDisplay } from "@/ui/TableDisplay";
import type { ModelDraftOutline } from "@/types";
import { EditableCell, type CellEdit } from "@/features/model-editor/EditableCell";
import type { RunStep } from "@/features/model-editor/OperationDialog";

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
}) {
  const shown: DataColumn<Row>[] = columns.map(({ edit, ...column }) =>
    edit && editing
      ? {
          ...column,
          cell: (row: Row) => {
            const spec = edit(row);
            return spec ? (
              <EditableCell edit={spec} outline={editing.outline} run={editing.run}>
                {column.cell(row)}
              </EditableCell>
            ) : (
              column.cell(row)
            );
          },
        }
      : column,
  );
  const display = useTableDisplay(
    columns.map((column) => column.key),
    `model-editor:${scope}`,
  );
  return (
    <div className="editor-table">
      <DataTable<Row>
        columns={shown}
        identityColumn={columns[0]?.key}
        list={fixedWindow(rows)}
        rowKey={rowKey}
        rowAttributes={rowAttributes}
        actions={menu ? { header: <span className="visually-hidden">Actions</span>, cell: menu, width: 56 } : undefined}
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
  );
}
