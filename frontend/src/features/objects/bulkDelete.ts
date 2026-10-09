/**
 * What deleting a selection sends and says (0.9 K2b, J32.3), as pure functions.
 *
 * Each selected record becomes one cascading `delete` item with the version its row showed or was
 * read with (D102) and its name as the item's `ref`; the preview gives each item's impact and its
 * token, and confirming carries the tokens (D120). The preview's totals are said in words, the
 * selected records apart from those that go with them (D121, D126), and after the delete the records
 * it removed leave a hand selection (D125).
 */

import type { TypeName } from "@/features/jobs/BatchOutcome";
import { count } from "@/features/settings/limits";
import type { SelectableRow } from "@/lib/recordSelection";
import type { BatchDeleteItem, DeletionTotals, Job, JobItemOutcome } from "@/types";
import { refFor } from "./bulkChange";

export function deleteItems(rows: readonly SelectableRow[]): BatchDeleteItem[] {
  return rows.map((row) => ({
    op: "delete",
    ref: refFor(row),
    target: { id: row.id },
    expectedVersion: row.version,
    cascade: true,
  }));
}

const records = (value: number) => `${count(value)} ${value === 1 ? "record" : "records"}`;

export interface DeletionWords {
  /** Everything the delete removes: the selected records and those going with them (D126). */
  total: number;
  /** "Deletes 12 selected master values". */
  selected: string;
  /** "and 340 records inside or owned by them: 300 values, 40 translations", or none. */
  withThem?: string;
  /** "Removes 52 relationships; 18 of them link to records that stay." */
  relationships: string;
  /** "3 selected records go with another selected record", or none. */
  together?: string;
}

/**
 * The preview's totals in words. The selected records are all of `selectedType`, so the records
 * going with them are the totals less the selected ones that are deleted themselves.
 */
export function deletionWords(job: Job, selectedType: string, typeName: TypeName): DeletionWords | undefined {
  const totals: DeletionTotals | undefined = job.preview?.deletion;
  const counts = job.preview?.counts;
  if (!totals || !counts) return undefined;
  const byType = { ...totals.objectsByType };
  byType[selectedType] = (byType[selectedType] ?? 0) - counts.deleted;
  const others = Object.entries(byType)
    .filter(([, value]) => value > 0)
    .sort(([a], [b]) => a.localeCompare(b));
  const inside = others.reduce((sum, [, value]) => sum + value, 0);
  const linked = totals.retainedAssociationCount;
  return {
    total: totals.objectCount,
    selected: `Deletes ${typeName(selectedType, counts.deleted)}`,
    withThem: inside
      ? `and ${records(inside)} inside or owned by them: ${others.map(([key, value]) => typeName(key, value)).join(", ")}`
      : undefined,
    relationships: totals.relationshipCount
      ? `Removes ${count(totals.relationshipCount)} ${totals.relationshipCount === 1 ? "relationship" : "relationships"}${
          linked
            ? `; ${count(linked)} of them ${linked === 1 ? "links" : "link"} to records that stay, which are kept`
            : ""
        }.`
      : "Removes no relationships.",
    together: counts.unchanged
      ? `${records(counts.unchanged)} selected ${counts.unchanged === 1 ? "goes" : "go"} with another selected record.`
      : undefined,
  };
}

/** The Apply button's words: the whole of what is deleted (D126). */
export function deleteLabel(total: number): string {
  return `Delete ${records(total)}`;
}

/** The records a delete removed among the outcomes: deleted, or gone with another item (D125). */
export function deletedIds(outcomes: readonly JobItemOutcome[]): Set<string> {
  const ids = new Set<string>();
  for (const outcome of outcomes)
    if (
      outcome.status === "applied" &&
      outcome.id &&
      (outcome.action === "deleted" || outcome.deletedWithItem !== undefined)
    )
      ids.add(outcome.id);
  return ids;
}
