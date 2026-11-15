/**
 * A move's rows as a table (0.11 X4's report of what cannot move; 0.16's job page): the item's
 * number, what it is (a record, or a relationship with the records at its ends) and why it did not
 * move, as the engine says it. The move editor's report and the job's page draw their rows with it;
 * each adds only what is its own: the report a column that opens the mapping, the page links to
 * the records and to the model's criteria.
 */

import type { ReactNode } from "react";
import { api } from "@/api/client";
import { count } from "@/lib/count";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { relationTypeFor, typeName } from "@/model/lookup";
import type { EngineModel, MoveOutcome, MoveReason, MoveRow } from "@/types";
import { DataTable, type DataColumn } from "@/ui/DataTable";

export const MOVE_ROWS_PAGE = 50;

export interface MoveRowsFilter {
  outcome?: MoveOutcome;
  reason?: string;
}

const relationName = (model: EngineModel, key?: string) => (key && relationTypeFor(model, key)?.name) || key || "";

/** The reason a row is listed under: the filter's, else its first. */
export const reasonOf = (row: MoveRow, code?: string): MoveReason | undefined =>
  row.reasons.find((item) => item.code === code) ?? row.reasons[0];

export function MoveRowsTable({
  jobId,
  filter,
  source,
  target,
  label,
  emptyMessage,
  record,
  criteria,
  fix,
}: {
  jobId: string;
  filter: MoveRowsFilter;
  source: EngineModel;
  target: EngineModel;
  /** The table's accessible name. */
  label: string;
  emptyMessage: string;
  /** A record of the source by its name: a link where the caller can open it. */
  record?: (row: MoveRow, end: "record" | "from" | "to", name: string) => ReactNode;
  /** What leads to the model's criteria a reason names (`details.criteria`), where it can be opened. */
  criteria?: (reason: MoveReason) => ReactNode;
  /** An extra column of what to do about a row. */
  fix?: (row: MoveRow, reason: MoveReason | undefined) => ReactNode;
}) {
  const list = useCursorWindow<MoveRow>(
    (selector) =>
      api.moveRows(jobId, {
        ...selector,
        ...(filter.outcome ? { outcome: filter.outcome } : {}),
        ...(filter.reason ? { reason: filter.reason } : {}),
        pageSize: MOVE_ROWS_PAGE,
      }),
    [jobId, filter.outcome, filter.reason],
  );
  const name = (row: MoveRow, end: "record" | "from" | "to", text: string) => record?.(row, end, text) ?? text;
  const columns: DataColumn<MoveRow>[] = [
    { key: "item", label: "Item", cell: (row) => count(row.index) },
    {
      key: "what",
      label: "What",
      cell: (row) =>
        row.kind === "relationship" ? (
          <>
            {relationName(source, row.relationTypeKey)}: {name(row, "from", row.fromName ?? row.fromId ?? "")} →{" "}
            {name(row, "to", row.toName ?? row.toId ?? "")}
          </>
        ) : (
          <>
            {name(row, "record", row.name ?? row.sourceId ?? "")}{" "}
            <span className="muted">
              (
              {row.targetType && row.targetType !== row.sourceType
                ? `${typeName(source, row.sourceType)} → ${typeName(target, row.targetType)}`
                : typeName(source, row.sourceType)}
              )
            </span>
          </>
        ),
    },
    {
      key: "why",
      label: "Why",
      cell: (row) => {
        const reason = reasonOf(row, filter.reason);
        if (!reason) return "";
        return (
          <>
            {reason.message} <span className="mono muted">{reason.code}</span>
          </>
        );
      },
    },
    ...(criteria
      ? [
          {
            key: "criteria",
            label: "Model",
            cell: (row: MoveRow) => {
              const reason = reasonOf(row, filter.reason);
              return reason ? criteria(reason) : null;
            },
          },
        ]
      : []),
    ...(fix ? [{ key: "fix", label: "Fix", cell: (row: MoveRow) => fix(row, reasonOf(row, filter.reason)) }] : []),
  ];
  return (
    <DataTable<MoveRow>
      columns={columns}
      list={list}
      rowKey={(row) => String(row.index)}
      rowAttributes={() => ({ tabIndex: -1 })}
      label={label}
      noun={["item", "items"]}
      pageSize={MOVE_ROWS_PAGE}
      emptyMessage={emptyMessage}
    />
  );
}
