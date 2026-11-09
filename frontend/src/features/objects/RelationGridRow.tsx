/**
 * One row of a relationships grid (0.13 RG). Memoised: a selection, a link or a saved cell changes
 * the props of the rows it touches only, so scrolling and ticking do not draw every row's cells again
 * (the reported lag, 0.13 RG).
 */

import { memo, type Ref } from "react";
import { RelationValueCell } from "@/features/objects/relations/RelationValueCell";
import type { AttributeTypeDefinition, RelationGridColumn, RelationGridRow as GridRow } from "@/types";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { formatValue } from "@/ui/formatValue";

export interface GridRowProps {
  row: GridRow;
  index: number;
  rowRef: Ref<HTMLTableRowElement>;
  columns: RelationGridColumn[];
  attributes: AttributeTypeDefinition[];
  fromFields: string[];
  selectable: boolean;
  selected: boolean;
  editable: boolean;
  canLink: boolean;
  linking: boolean;
  proposedAny: boolean;
  workspaceKey: string;
  onToggle: (row: GridRow, extend: boolean) => void;
  onOpen: (row: GridRow) => void;
  onLink: (row: GridRow, column: RelationGridColumn) => void;
  onSaved: (row: GridRow, column: RelationGridColumn, relationId: string) => void;
}

function RowView({
  row,
  index,
  rowRef,
  columns,
  attributes,
  fromFields,
  selectable,
  selected,
  editable,
  canLink,
  linking,
  proposedAny,
  workspaceKey,
  onToggle,
  onOpen,
  onLink,
  onSaved,
}: GridRowProps) {
  const span = Math.max(1, attributes.length);
  return (
    <tr
      ref={rowRef}
      data-row-key={row.source.id}
      data-row-index={index}
      className={selected ? "is-selected" : undefined}
    >
      {selectable && (
        <td className="relation-grid-select">
          <SelectionCheckbox
            label={`Select ${row.source.name}`}
            state={selected ? "all" : "none"}
            onSelect={(extend) => onToggle(row, extend)}
          />
        </td>
      )}
      <td className="relation-grid-name">
        <button className="cell-link" data-row-focus onClick={() => onOpen(row)}>
          {row.source.name}
        </button>
      </td>
      {fromFields.map((field) => (
        <td key={field}>{formatValue(row.source.fields[field])}</td>
      ))}
      {columns.map((column) => {
        const related = row.relations[column.id];
        if (!related)
          return (
            <td key={column.id} colSpan={span} className="relation-grid-unlinked first">
              <span className="relation-grid-unlinked-note">
                Not linked
                {canLink && (
                  <button
                    type="button"
                    className="secondary"
                    disabled={linking}
                    aria-label={`Link ${row.source.name} to ${column.label}`}
                    onClick={() => onLink(row, column)}
                  >
                    + Link
                  </button>
                )}
              </span>
            </td>
          );
        return attributes.map((attribute, position) => (
          <td
            key={`${column.id}:${attribute.key}`}
            className={`relation-grid-value${position === 0 ? " first" : ""}${proposedAny && related.proposed ? " is-proposed" : ""}`}
          >
            <RelationValueCell
              key={`${related.relationId}:${related.version}`}
              attribute={attribute}
              relation={{ id: related.relationId, version: related.version, attributes: related.attributes }}
              label={`${row.source.name} · ${column.label}`}
              editable={editable}
              workspaceKey={workspaceKey}
              onSaved={() => onSaved(row, column, related.relationId)}
              floating
            />
            {proposedAny && related.proposed && position === 0 && (
              <span className="relation-grid-proposed" role="img" aria-label="Proposed in this change set" />
            )}
          </td>
        ));
      })}
    </tr>
  );
}

export const RelationGridRowView = memo(RowView);
