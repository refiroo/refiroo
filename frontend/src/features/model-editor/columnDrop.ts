/**
 * What a column dropped on a list or one of its fields sends (0.17 PL3b, CE1): the operations of the drop, and the
 * small readings of a column they rest on. Pure functions over the draft's outline and import profile, used by the
 * workbook canvas and by the readings the model editor's panels send too (PP-D77).
 */

import { NEW_ATTRIBUTE, mapOperations, relationValue, sourceFor } from "@/features/model-editor/mapping";
import type { DraftOperation, ModelDraftOutline } from "@/types/modelAdmin";
import type { DraftProfileDocument, ProfileBinding, SourceColumn } from "@/types/sources";

export const bound = (binding: ProfileBinding): string[] =>
  binding.columns?.length ? binding.columns : binding.column ? [binding.column] : [];

/** What a drop on a field needs to know of it: the canvas's field card satisfies it. */
export interface DropField {
  kind: "name" | "attribute" | "parent" | "relation";
  attributeTypeKey?: string;
  farType?: string;
  relationType?: string;
}

/** A header as a field's name: "COUNTRY_CODE" reads "Country code". */
export function niceName(header: string): string {
  const words = header
    // A header written in CamelCase reads as words: "RBStopCategory" is "RB Stop Category".
    .replace(/([a-z\d])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replace(/[_\s]+/g, " ")
    .replace(/\?$/, "")
    .trim()
    .toLowerCase();
  return words ? words[0].toUpperCase() + words.slice(1) : header;
}

/**
 * The value type a column's cells suggest: the first type every filled cell reads as (the profile
 * counts the cells readable as each type, and every filled cell reads as text), else text. A column
 * of numbers with one word in it stays text: the person decides whether the word is a mistake.
 */
export function valueTypeOf(
  column: (Pick<SourceColumn, "valueTypes"> & Partial<Pick<SourceColumn, "placeholders">>) | undefined,
): string {
  if (!column) return "text";
  const placeholders = (column.placeholders ?? []).reduce((sum, item) => sum + item.count, 0);
  const filled = (column.valueTypes.text ?? 0) - placeholders;
  return (
    ["boolean", "integer", "decimal", "date", "dateTime"].find(
      (kind) => filled > 0 && (column.valueTypes[kind] ?? 0) >= filled,
    ) ?? "text"
  );
}

/** Where a workbook column was dropped. */
export type ColumnDrop = { on: "card"; typeKey: string } | { on: "field"; typeKey: string; field: DropField };

/**
 * A column dropped on a list or on one of its fields (the drop without the dialog): on the name it
 * names the record; on a field it fills it; on a parent or a relationship it finds the record at
 * the other end by its name; on the card itself it becomes a new field, named for its header. A
 * list no source on that sheet loads gets its source in the same request (D76).
 */
export function columnDropOperations(
  sheet: string,
  header: string,
  drop: ColumnDrop,
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
  column?: Pick<SourceColumn, "valueTypes">,
): DraftOperation[] {
  const base = { sheet, header, rowType: drop.typeKey };
  if (drop.on === "card") {
    // A list nothing on this sheet loads yet takes the column as its name first.
    const loading = sourceFor(profile, sheet, drop.typeKey);
    if (!loading) return mapOperations({ ...base, kind: "name" }, profile, outline);
    // A column that already fills a field of this list is not made a field twice; a field of the same name
    // that no column fills (a column left out) takes the column back instead of a second one beside it.
    if (
      loading.columns.some((binding) => !binding.ignore && binding.attributeTypeKey && bound(binding).includes(header))
    )
      return [];
    const taken = new Set(
      loading.columns.filter((binding) => !binding.ignore && binding.attributeTypeKey).map((b) => b.attributeTypeKey),
    );
    const again = outline.objectTypes
      .find((item) => item.key === drop.typeKey)
      ?.attributes.find((item) => item.name === niceName(header) && !taken.has(item.attributeType));
    if (again) return mapOperations({ ...base, kind: "attribute", target: again.attributeType }, profile, outline);
    return mapOperations(
      {
        ...base,
        kind: "attribute",
        target: NEW_ATTRIBUTE,
        newAttribute: { name: niceName(header), valueType: valueTypeOf(column), unique: false },
      },
      profile,
      outline,
    );
  }
  const { field } = drop;
  if (field.kind === "name") return mapOperations({ ...base, kind: "name" }, profile, outline);
  if (field.kind === "attribute")
    return mapOperations({ ...base, kind: "attribute", target: field.attributeTypeKey }, profile, outline);
  if (field.kind === "parent")
    return mapOperations({ ...base, kind: "parent", target: field.farType, create: true }, profile, outline);
  const relation = outline.relations.find(
    (item) => item.relationType === field.relationType && item.from === drop.typeKey && item.to === field.farType,
  );
  return relation
    ? mapOperations({ ...base, kind: "lookup", target: relationValue(relation), create: true }, profile, outline)
    : [];
}
