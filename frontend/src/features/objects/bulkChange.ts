/**
 * What a bulk change of values offers and sends (0.9 K2), as pure functions over the model and the
 * selection.
 *
 * The fields are every attribute the type binds, in the binding order, except read-only and hidden
 * ones; a required one is never offered to clear, since clearing it is refused for every record
 * (D117). A change becomes one `update` item per record: the version the row showed or was read
 * with (D102), the values set or cleared (`null` clears), and the record's name as the item's `ref`,
 * so the job names each record however it is read later.
 */

import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import type {
  AttributeTypeDefinition,
  BatchUpdateItem,
  EngineModel,
  JobItemOutcome,
  ObjectTypeAttributeDefinition,
  ObjectTypeDefinition,
} from "@/types";

export interface BulkField {
  binding: ObjectTypeAttributeDefinition;
  attribute: AttributeTypeDefinition;
  /** Whether Clear is offered: not for a required binding. */
  clearable: boolean;
}

export type FieldMode = "keep" | "set" | "clear";

/** One field's change: a value to set, or `null` to clear it. */
export interface FieldChange {
  attributeTypeKey: string;
  value: unknown;
}

/** The longest `ref` a batch item takes. */
const REF_LENGTH = 200;

export function bulkFields(model: EngineModel, objectType: ObjectTypeDefinition): BulkField[] {
  const attributes = new Map(model.attributeTypes.map((attribute) => [attribute.key, attribute]));
  return objectType.attributes
    .slice()
    .sort((a, b) => a.order - b.order)
    .flatMap((binding) => {
      const attribute = attributes.get(binding.attributeTypeKey);
      if (!attribute || binding.readOnly || binding.ui?.hidden === true || attribute.ui?.hidden === true) return [];
      return [{ binding, attribute, clearable: !binding.required }];
    });
}

/** The record's name as an item's `ref`, cut to what a `ref` holds. */
export function refFor(row: SelectableRow): string {
  const name = row.name?.trim() || row.id;
  return name.length > REF_LENGTH ? `${name.slice(0, REF_LENGTH - 1)}…` : name;
}

/**
 * The records a change is sent for: the hand-picked ones as their rows showed them, or the records
 * read for "all matching" without its exceptions (D102, D109).
 */
export function recordsToChange(selection: RecordSelection, matching: readonly SelectableRow[] = []): SelectableRow[] {
  if (selection.mode === "ids") return [...selection.ids.values()];
  return matching.filter((row) => !selection.except.has(row.id));
}

export function bulkItems(rows: readonly SelectableRow[], changes: readonly FieldChange[]): BatchUpdateItem[] {
  const attributes = changes.map(({ attributeTypeKey, value }) => ({ attributeTypeKey, value }));
  return rows.map((row) => ({
    op: "update",
    ref: refFor(row),
    target: { id: row.id },
    expectedVersion: row.version,
    attributes,
  }));
}

/** The version each applied outcome left on its record, for the selection to keep (D118). */
export function versionsAfter(outcomes: readonly JobItemOutcome[]): Map<string, number> {
  const versions = new Map<string, number>();
  for (const outcome of outcomes)
    if (outcome.status === "applied" && outcome.id && outcome.version !== undefined)
      versions.set(outcome.id, outcome.version);
  return versions;
}
