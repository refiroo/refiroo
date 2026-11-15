/**
 * What cannot move (0.11 X4, D143): one card per reason of the dry run with its count and what fixes
 * it, then the chosen reason's items, every one, paged from the job's rows; a row whose reason names
 * the mapping step that changes it links back to that row. The values records move without are
 * listed per type and field with their counts, as the summary holds them.
 */

import { count } from "@/lib/count";
import { attributeName } from "@/model/fields";
import { typeName } from "@/model/lookup";
import type { EngineModel, MoveSummary } from "@/types";
import { EmptyState } from "@/ui/EmptyState";
import { OutcomeCards } from "@/ui/OutcomeCards";
import { modeWords, reasonCards, rowForAction, VALUES_NOT_CARRIED } from "@/model/moveRun";
import { rowId } from "./MappingPane";
import { MoveRowsTable } from "@/ui/MoveRowsTable";

export function MoveReport({
  jobId,
  summary,
  source,
  target,
  reason,
  onReason,
  onFix,
}: {
  jobId: string;
  summary: MoveSummary;
  source: EngineModel;
  target: EngineModel;
  reason?: string;
  onReason: (code: string) => void;
  /** Open the mapping at the row that changes a reason. */
  onFix: (row: string) => void;
}) {
  const cards = reasonCards(summary);
  const chosen = cards.find((card) => card.code === reason) ?? cards[0];
  if (!chosen)
    return (
      <EmptyState>
        Every selected record and relationship can be {modeWords(summary.mode).past}, with every value. Nothing is left
        behind.
      </EmptyState>
    );
  return (
    <div className="move-report">
      <OutcomeCards
        label={`${modeWords(summary.mode).whatCannot}, by reason`}
        items={cards.map((card) => ({
          key: card.code,
          count: card.count,
          label: card.label,
          hint: card.fix,
          tone: card.code === VALUES_NOT_CARRIED ? "warning" : "error",
        }))}
        selected={chosen.code}
        onSelect={onReason}
      />
      <section aria-labelledby="move-report-items" className="migration-section">
        <h2 id="move-report-items" className="install-heading">
          {chosen.label} <span className="muted">· {count(chosen.count)}, every item listed</span>
        </h2>
        {chosen.code === VALUES_NOT_CARRIED ? (
          <ValuesNotCarried summary={summary} source={source} />
        ) : (
          <ReasonRows
            key={`${jobId}:${chosen.code}`}
            jobId={jobId}
            mode={summary.mode}
            code={chosen.code}
            source={source}
            target={target}
            onFix={onFix}
          />
        )}
      </section>
    </div>
  );
}

function ReasonRows({
  jobId,
  mode,
  code,
  source,
  target,
  onFix,
}: {
  jobId: string;
  mode: "copy" | "move";
  code: string;
  source: EngineModel;
  target: EngineModel;
  onFix: (row: string) => void;
}) {
  return (
    <MoveRowsTable
      jobId={jobId}
      filter={{ reason: code }}
      source={source}
      target={target}
      label={`Items that ${modeWords(mode).cannot.toLowerCase()}`}
      emptyMessage="No item has this reason any more."
      fix={(row, reason) => {
        // A target's refusal names no step; its fix (a default, a match, a parent) is in the type's mapping.
        const key = rowForAction(reason?.action, row.relationTypeKey) ?? (row.kind === "record" ? "type" : undefined);
        const type = row.sourceType;
        return key && type ? (
          <button type="button" className="link-button" onClick={() => onFix(rowId(type, key))}>
            Open the mapping
          </button>
        ) : (
          ""
        );
      }}
    />
  );
}

function ValuesNotCarried({ summary, source }: { summary: MoveSummary; source: EngineModel }) {
  return (
    <div className="table-wrap" role="group" aria-label="Values not carried" tabIndex={0}>
      <table>
        <thead>
          <tr>
            <th scope="col">Type</th>
            <th scope="col">Field</th>
            <th scope="col">Records</th>
            <th scope="col">Code</th>
          </tr>
        </thead>
        <tbody>
          {summary.attributesNotCarried.map((item) => (
            <tr key={`${item.sourceType}/${item.attributeTypeKey}/${item.code}`}>
              <td>{typeName(source, item.sourceType)}</td>
              <td>{attributeName(source, item.attributeTypeKey)}</td>
              <td>{count(item.count)}</td>
              <td>
                <span className="mono">{item.code}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
