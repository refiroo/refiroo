/**
 * What a collection's selection holds, above its table (0.9 K1): the count, Select all matching
 * once every loaded row is selected, Clear selection (×), and the slot K2, K2b and K3 fill with
 * actions: Change values, Change relationships and Delete, each with its glyph (K6a, D166).
 * A selection the deployment cannot change at once is explained, not silently capped (D104).
 */

import type { ReactNode } from "react";
import { count } from "@/lib/count";
import type { RecordSelection } from "@/lib/recordSelection";
import type { CapabilitiesResponse } from "@/types";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";

/**
 * Whether a collection lets records be selected (D105): only where its data can be written and the
 * deployment lets jobs be created, since every bulk change is a batch job.
 */
export function bulkSelectionFor(
  capabilities: CapabilitiesResponse | undefined,
  readOnly: boolean,
): { maxItems: number } | undefined {
  if (!capabilities?.integrationJobs.createJobs || readOnly) return undefined;
  return { maxItems: capabilities.integrationJobs.limits.backgroundJobMaxItems };
}

/** The count as the bar and the status region say it. */
export function selectionText(selection: RecordSelection, selected: number): string {
  if (selection.mode === "ids") return `${count(selected)} selected`;
  return selection.except.size
    ? `All ${count(selection.total)} matching except ${count(selection.except.size)}`
    : `All ${count(selection.total)} matching selected`;
}

/** Why "all matching" was not selected, and what to do about it. */
export function refusalText(total: number, limit: number, pluralName: string): string {
  const plural = pluralName.toLowerCase();
  return (
    `${count(total)} ${plural} match this list, but one bulk change on this deployment can hold at most ` +
    `${count(limit)} records, so nothing more was selected. Narrow the list with the search or filters, ` +
    `or select fewer ${plural}. The operator sets this limit with BACKGROUND_JOB_MAX_ITEMS and can raise it.`
  );
}

export function SelectionBar({
  selection,
  selected,
  matchingTotal,
  limit,
  refusedTotal,
  pluralName,
  onSelectMatching,
  onClear,
  children,
}: {
  selection: RecordSelection;
  selected: number;
  /** Set when every loaded row is selected and the list holds more: how many it matches. */
  matchingTotal?: number;
  limit: number;
  refusedTotal?: number;
  pluralName: string;
  onSelectMatching: () => void;
  onClear: () => void;
  /** The bulk actions (K2, K3). */
  children?: ReactNode;
}) {
  const overLimit = refusedTotal ?? (matchingTotal !== undefined && matchingTotal > limit ? matchingTotal : undefined);
  if (selected === 0 && overLimit === undefined) return null;
  return (
    <div className="selection-bar" role="group" aria-label="Selection">
      <div className="selection-bar-row">
        <strong className="selection-count">
          {selected > 0 ? selectionText(selection, selected) : "Nothing selected"}
        </strong>
        {matchingTotal !== undefined && overLimit === undefined && (
          <button type="button" className="ghost selection-matching" onClick={onSelectMatching}>
            Select all {count(matchingTotal)} matching
          </button>
        )}
        {children && <div className="selection-actions">{children}</div>}
        {selected > 0 && (
          <button
            type="button"
            className="ghost selection-clear"
            aria-label="Clear selection"
            title="Clear selection"
            onClick={onClear}
          >
            <Icon name="close" size={15} />
          </button>
        )}
      </div>
      {overLimit !== undefined && (
        <Notice tone="warning" title="Too many records to select at once">
          {refusalText(overLimit, limit, pluralName)}
        </Notice>
      )}
    </div>
  );
}
