/**
 * What the workbook's three readings send (0.17 PL3b, CE1): several columns read as rows (`setUnpivot`),
 * blanks filled from the cell above (`setFillDown`) and rows holding only one column read as headings
 * (`setHeadingRows`), with the marks that say a column is on one. Pure functions over the draft's
 * outline and import profile, built once for both views of the draft (PP-D77): the model editor's
 * column and list panels and the workbook canvas send what these return.
 */

import {
  bound,
  columnDropOperations,
  nameOfType,
  valueTypeOf,
  type ColumnDrop,
} from "@/features/model-editor/columnDrop";
import { keyFromLabel, keysOf } from "@/model/outline";
import { newSourceId, sourceFor, usesOf } from "@/features/model-editor/mapping";
import type { DraftOperation, ModelDraftOutline } from "@/types/modelAdmin";
import type { DraftProfileDocument, ProfileSource, SourceColumn } from "@/types/sources";

// --- several columns onto one field (PP-D6) ---

const YEAR = /^\s*(19|20)\d{2}\s*$/;
const PERIOD = /^\s*(q[1-4]|h[12]|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i;

/** A name that no header of the table already has: "Year", then "Year 2". */
export function freeColumnName(base: string, taken: ReadonlySet<string>): string {
  let name = base;
  for (let n = 2; taken.has(name); n += 1) name = `${base} ${n}`;
  return name;
}

/** The two new columns' names the headers suggest: years are a Year, quarters and months a Period. */
export function unpivotDefaults(headers: readonly string[], taken: ReadonlySet<string>) {
  const name = headers.every((header) => YEAR.test(header))
    ? "Year"
    : headers.every((header) => PERIOD.test(header))
      ? "Period"
      : "Column";
  const nameColumn = freeColumnName(name, taken);
  return { nameColumn, valueColumn: freeColumnName("Value", new Set([...taken, nameColumn])) };
}

/** The value type most of the listed columns hold; text when they differ. */
export function commonValueType(columns: readonly (SourceColumn | undefined)[]): string {
  const types = new Set(columns.map((column) => valueTypeOf(column)));
  return types.size === 1 ? [...types][0] : "text";
}

export interface UnpivotPlan {
  sheet: string;
  /** The wide columns, by header. */
  columns: string[];
  nameColumn: string;
  valueColumn: string;
  drop: ColumnDrop;
}

/**
 * Several columns dropped on a list or one of its fields: they are read as rows (`setUnpivot`) and the
 * two new columns are bound in the same request. The field decides what each becomes: on the name, the
 * headers name the records; on an attribute, the cells fill it; on a parent or a relationship, the
 * headers find the records at the other end. What the field does not take becomes a new attribute.
 */
export function unpivotOperations(
  plan: UnpivotPlan,
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
  columnOf: (header: string) => SourceColumn | undefined,
): DraftOperation[] {
  const { drop } = plan;
  const existing = sourceFor(profile, plan.sheet, drop.typeKey);
  const id = existing?.id ?? newSourceId(profile, plan.sheet, drop.typeKey);
  const operations: DraftOperation[] = [];
  if (!existing) operations.push({ kind: "addSource", id, sheet: plan.sheet, objectType: drop.typeKey });
  // A wide column the source read as something else stops being read so: its cells are the rows now.
  for (const binding of existing?.columns ?? [])
    for (const header of bound(binding))
      if (plan.columns.includes(header) && !binding.ignore)
        operations.push({ kind: "unmapColumn", source: id, column: header });
  operations.push({
    kind: "setUnpivot",
    source: id,
    columns: plan.columns,
    nameColumn: plan.nameColumn,
    valueColumn: plan.valueColumn,
  });
  // The bindings are worked out against a profile that already holds the source, so none is added twice.
  const held: DraftProfileDocument | null | undefined = existing
    ? profile
    : profile && {
        ...profile,
        sources: [
          ...profile.sources,
          {
            id,
            sheet: plan.sheet,
            headerRow: 1,
            applicationKey: null,
            objectTypeKey: drop.typeKey,
            columns: [],
          },
        ],
      };
  const field = drop.on === "field" ? drop.field : undefined;
  const headersFill = field?.kind === "name" || field?.kind === "parent" || field?.kind === "relation";
  const cells = commonValueType(plan.columns.map(columnOf));
  const asNewAttribute = (header: string, valueType: string) =>
    columnDropOperations(plan.sheet, header, { on: "card", typeKey: drop.typeKey }, held, outline, {
      valueTypes: { text: 1, [valueType]: 1 },
    });
  const bind = (header: string, onField: boolean, valueType: string) =>
    onField && drop.on === "field"
      ? columnDropOperations(plan.sheet, header, drop, held, outline)
      : asNewAttribute(header, valueType);
  operations.push(
    ...bind(plan.nameColumn, headersFill, "text"),
    ...bind(plan.valueColumn, !headersFill && field !== undefined, cells),
  );
  return operations;
}

// --- readings and the sheet preview (PP-D7) ---

/** A reading a column is on, for the mark beside it in the workbook pane. */
export interface ColumnReading {
  kind: "unpivot" | "fillDown" | "headings" | "added";
  source: string;
  label: string;
}

export function readingsOf(
  profile: DraftProfileDocument | null | undefined,
  sheet: string,
  header: string,
): ColumnReading[] {
  const found: ColumnReading[] = [];
  for (const source of (profile?.sources ?? []).filter((item) => item.sheet === sheet)) {
    if (source.unpivot?.columns.includes(header))
      found.push({ kind: "unpivot", source: source.id, label: "read as rows" });
    if (source.fillDown?.includes(header))
      found.push({ kind: "fillDown", source: source.id, label: "blanks filled from above" });
    if (source.headings?.column === header)
      found.push({ kind: "headings", source: source.id, label: "rows holding only it are headings" });
  }
  return found;
}

/** The columns a source's readings add to its table, which bindings name like any header. */
export function addedColumns(
  profile: DraftProfileDocument | null | undefined,
  sheet: string,
): { header: string; source: string; label: string }[] {
  return (profile?.sources ?? [])
    .filter((source) => source.sheet === sheet)
    .flatMap((source) => [
      ...(source.unpivot
        ? [
            { header: source.unpivot.nameColumn, source: source.id, label: "the header of each column read as rows" },
            { header: source.unpivot.valueColumn, source: source.id, label: "the cell of each column read as rows" },
          ]
        : []),
      ...(source.headings
        ? [{ header: source.headings.into, source: source.id, label: "the heading above each row" }]
        : []),
    ]);
}

/** The source a reading on a sheet's column is set on: the one binding it, else the sheet's first. */
export function sourceOfColumn(
  profile: DraftProfileDocument | null | undefined,
  sheet: string,
  header: string,
): ProfileSource | undefined {
  const sources = (profile?.sources ?? []).filter((source) => source.sheet === sheet);
  return usesOf(profile, sheet, header)[0]?.source ?? sources[0];
}

/** Fill blanks from the cell above for a column, or stop doing so. */
export function fillDownOperations(source: ProfileSource, header: string, on: boolean): DraftOperation[] {
  const now = source.fillDown ?? [];
  const next = on ? [...new Set([...now, header])] : now.filter((item) => item !== header);
  return next.length
    ? [{ kind: "setFillDown", source: source.id, columns: next }]
    : [{ kind: "clearFillDown", source: source.id }];
}

export type HeadingParent = { typeKey: string } | { newName: string };

/**
 * Rows holding only one column are headings (`setHeadingRows`): their text is the parent, by name, of
 * the rows beneath, offered at once as the parent binding of the new column, with the containment when
 * the list does not sit under that parent yet. A new parent is added to the row's application.
 */
export function headingOperations(
  plan: { sheet: string; column: string; into: string; rowType: string; parent: HeadingParent },
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const existing = sourceFor(profile, plan.sheet, plan.rowType);
  const id = existing?.id ?? newSourceId(profile, plan.sheet, plan.rowType);
  const operations: DraftOperation[] = [];
  if (!existing) operations.push({ kind: "addSource", id, sheet: plan.sheet, objectType: plan.rowType });
  operations.push({ kind: "setHeadingRows", source: id, column: plan.column, into: plan.into });
  let parentKey: string;
  if ("newName" in plan.parent) {
    const type = outline.objectTypes.find((item) => item.key === plan.rowType);
    const application = outline.applications.find((item) => item.key === (type?.home ?? undefined))?.key;
    parentKey = keyFromLabel(plan.parent.newName, keysOf(outline));
    operations.push({ kind: "addObjectType", applicationKey: application, name: plan.parent.newName, parent: null });
  } else parentKey = plan.parent.typeKey;
  const type = outline.objectTypes.find((item) => item.key === plan.rowType);
  if (!type?.parents.includes(parentKey))
    operations.push({
      kind: "setContainment",
      objectType: plan.rowType,
      parent: {
        objectTypes: [parentKey],
        relationType: {
          name: `Contains ${nameOfType(outline, plan.rowType)}`,
          reverseName: `In ${plan.parent && "newName" in plan.parent ? plan.parent.newName : nameOfType(outline, parentKey)}`,
        },
      },
    });
  operations.push({
    kind: "mapColumn",
    source: id,
    column: plan.into,
    binding: { parent: { objectTypeKey: parentKey, matchBy: { field: "name" }, missing: "create" } },
  });
  return operations;
}
