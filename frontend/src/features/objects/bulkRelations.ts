/**
 * What changing the relationships of a selection sends (0.9 K3, J32.4), as pure functions.
 *
 * Add and Remove make one item per selected record and chosen record: an `ensureRelation`, or an
 * `ensureNoRelation` that removes the relationship by its two records (D129), so sending the change
 * again finds everything done. Replace with, Set to and Clear make one `replaceRelationSet` per
 * selected record without a version claim: the preview takes each set's version and confirming
 * claims it (D130). The limits count items, so the dialog says how many a change makes (D134).
 */

import type { RelationChoice } from "@/model/lookup";
import type { SelectableRow } from "@/lib/recordSelection";
import type { BatchRelationItem } from "@/types";
import type { ChosenRecord as OtherRecord } from "@/ui/RecordListField";
import { refFor } from "./bulkChange";

export type RelationMode = "change" | "replace" | "set" | "clear";

export type RelationChange =
  | { mode: "change"; add: readonly OtherRecord[]; remove: readonly OtherRecord[] }
  | { mode: "replace" | "set"; targets: readonly OtherRecord[] }
  | { mode: "clear" };

/** The items to send, and the selected record each item is for, by its index in `rows`. */
export interface RelationItems {
  items: BatchRelationItem[];
  rowOf: number[];
}

/** The longest `ref` a batch item takes. */
const REF_LENGTH = 200;

/** "Selected record → other record", each name cut so the whole fits a `ref`. */
export function pairRef(row: SelectableRow, other: OtherRecord): string {
  const half = (REF_LENGTH - 3) / 2;
  const cut = (name: string) => (name.length > half ? `${name.slice(0, half - 1)}…` : name);
  return `${cut(refFor(row))} → ${cut(other.name.trim() || other.id)}`;
}

/** How many items a change makes for `selected` records (D134). */
export function itemCount(selected: number, change: RelationChange): number {
  return change.mode === "change" ? selected * (change.add.length + change.remove.length) : selected;
}

/** Whether a change's items need the preview's claim, so none may go unpreviewed (D131). */
export const claimedByPreview = (mode: RelationMode) => mode !== "change";

export function relationItems(
  rows: readonly SelectableRow[],
  choice: RelationChoice,
  change: RelationChange,
): RelationItems {
  const { relation, direction } = choice;
  const items: BatchRelationItem[] = [];
  const rowOf: number[] = [];
  rows.forEach((row, index) => {
    if (change.mode === "change") {
      const ends = (other: OtherRecord) =>
        direction === "outgoing"
          ? { from: { id: row.id }, to: { id: other.id } }
          : { from: { id: other.id }, to: { id: row.id } };
      for (const other of change.add) {
        items.push({
          op: "ensureRelation",
          ref: pairRef(row, other),
          relationTypeKey: relation.relationTypeKey,
          ...ends(other),
        });
        rowOf.push(index);
      }
      for (const other of change.remove) {
        items.push({
          op: "ensureNoRelation",
          ref: pairRef(row, other),
          relationTypeKey: relation.relationTypeKey,
          ...ends(other),
        });
        rowOf.push(index);
      }
      return;
    }
    items.push({
      op: "replaceRelationSet",
      ref: refFor(row),
      relationTypeKey: relation.relationTypeKey,
      fromObjectTypeKey: relation.fromObjectTypeKey,
      toObjectTypeKey: relation.toObjectTypeKey,
      direction,
      anchor: { id: row.id },
      targets: change.mode === "clear" ? [] : change.targets.map((other) => ({ object: { id: other.id } })),
    });
    rowOf.push(index);
  });
  return { items, rowOf };
}
