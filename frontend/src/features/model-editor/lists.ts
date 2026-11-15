/**
 * The lists of a sheet laid out for reading as the editor shows them (0.10 A8b, D122): each list's
 * header, the source loading it and its status, read from the profile's blocks and the draft's
 * profile. Which source is a list's is decided here, over data the editor already holds, and only
 * decides what is shown.
 */

import { counted } from "@/lib/count";
import type {
  DraftOperation,
  DraftProfileDocument,
  ModelDraftOutline,
  ProfileSource,
  SourceBlock,
  SourceColumn,
  SourceRectangle,
} from "@/types";

export type ListStatus = "proposed" | "loaded" | "notLoaded";

export const LIST_STATUS_LABELS: Record<ListStatus, string> = {
  proposed: "Proposed",
  loaded: "Loaded",
  notLoaded: "Not loaded",
};

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

/** A column letter's number, 1-based (A is 1, AA is 27). */
export function columnNumber(letter: string): number {
  return [...letter.toUpperCase()].reduce((total, char) => total * 26 + LETTERS.indexOf(char) + 1, 0);
}

/** A column number's letter. */
export function columnLetter(number: number): string {
  let letter = "";
  for (let rest = number; rest > 0; rest = Math.floor((rest - 1) / 26)) letter = LETTERS[(rest - 1) % 26] + letter;
  return letter;
}

/** The list's header: its first column's header in the profile's columns. */
export function listHeader(block: SourceBlock, columns: SourceColumn[] | undefined): string {
  const first = columns?.find((column) => column.block === block.index && column.letter === block.firstColumn);
  return first?.header?.trim() || `List at ${block.range}`;
}

/** The columns of one list, in column order. */
export function listColumns(block: SourceBlock, columns: SourceColumn[] | undefined): SourceColumn[] {
  return (columns ?? []).filter((column) => column.block === block.index && column.header);
}

/** A source's rectangle: its header row, columns and last row (its last row open without one). */
function spanOf(source: ProfileSource) {
  const block = (source.block ?? {}) as { firstColumn?: string; lastColumn?: string; lastRow?: number | null };
  return {
    first: block.firstColumn ? columnNumber(block.firstColumn) : 1,
    last: block.lastColumn ? columnNumber(block.lastColumn) : Number.MAX_SAFE_INTEGER,
    top: source.headerRow,
    bottom: block.lastRow ?? Number.MAX_SAFE_INTEGER,
  };
}

/**
 * The source loading a list: on its sheet, sharing a column and a row with it (its header row
 * may have moved, D125). Among several, the one whose header row is nearest the list's.
 */
export function sourceOfList(
  profile: DraftProfileDocument | null | undefined,
  sheet: string,
  block: SourceBlock,
): ProfileSource | undefined {
  const first = columnNumber(block.firstColumn);
  const last = columnNumber(block.lastColumn);
  const top = block.headerRow ?? 1;
  const found = (profile?.sources ?? []).filter((source) => {
    if (source.sheet !== sheet) return false;
    const span = spanOf(source);
    if (span.last < first || span.first > last) return false;
    return span.top <= block.lastRow && span.bottom >= top;
  });
  return found.sort((a, b) => Math.abs(a.headerRow - top) - Math.abs(b.headerRow - top))[0];
}

/** A list's status: still the engine's, the administrator's, or loaded by nothing. */
export function listStatus(source: ProfileSource | undefined, proposed: ReadonlySet<string>): ListStatus {
  if (!source) return "notLoaded";
  return proposed.has(`source:${source.id}`) || proposed.has(`objectType:${source.objectTypeKey}`)
    ? "proposed"
    : "loaded";
}

/** The rectangle a source loads, or the list's own when nothing loads it. */
export function rectangleOf(block: SourceBlock, source: ProfileSource | undefined): SourceRectangle {
  const own = (source?.block ?? {}) as { firstColumn?: string; lastColumn?: string; lastRow?: number | null };
  return {
    headerRow: source?.headerRow ?? block.headerRow ?? 1,
    block: {
      firstColumn: own.firstColumn ?? block.firstColumn,
      lastColumn: own.lastColumn ?? block.lastColumn,
      lastRow: own.lastRow ?? block.lastRow,
    },
  };
}

export function rangeOf(rectangle: SourceRectangle): string {
  return `${rectangle.block.firstColumn}${rectangle.headerRow}:${rectangle.block.lastColumn}${rectangle.block.lastRow}`;
}

/** The rows a rectangle loads below its header, the list's note row left out. */
export function rowsOf(block: SourceBlock, rectangle: SourceRectangle): number {
  const noted = block.note && block.note.row > rectangle.headerRow && block.note.row <= rectangle.block.lastRow;
  return Math.max(0, rectangle.block.lastRow - rectangle.headerRow - (noted ? 1 : 0));
}

/** The list's rows in words, as its source loads them (D125) or as the profile read them, and its note. */
export function listWords(block: SourceBlock, rectangle?: SourceRectangle): string {
  const count = rectangle ? rowsOf(block, rectangle) : block.rows;
  const rows = `${counted(count, "row")}`;
  return block.note ? `${rows} · ${noteLabel(block.note)}: ${block.note.text}` : rows;
}

/** What the row under a list's header is called: a note (D119) or a second header row (0.10 A8c, D144). */
export function noteLabel(note: NonNullable<SourceBlock["note"]>): string {
  return note.meaning === "heading" ? "second header row" : "note";
}

/**
 * Don't load this list (D127): its source removed, and its list type with it when no other source
 * loads it and no other type relates to it.
 */
export function dropOperations(
  outline: ModelDraftOutline,
  profile: DraftProfileDocument | null | undefined,
  source: ProfileSource,
): DraftOperation[] {
  const type = source.objectTypeKey;
  const loadedElsewhere = (profile?.sources ?? []).some((item) => item.id !== source.id && item.objectTypeKey === type);
  const relatedFrom = outline.relations.some((relation) => relation.to === type && relation.from !== type);
  const contains = outline.objectTypes.some((item) => item.key !== type && item.parents.includes(type));
  const operations: DraftOperation[] = [{ kind: "removeSource", source: source.id }];
  if (!loadedElsewhere && !relatedFrom && !contains) operations.push({ kind: "removeObjectType", objectType: type });
  return operations;
}

/** A list's object type renamed from its heading: one setLabel with the name (the editor's and the canvas's alike). */
export function renameTypeOperations(typeKey: string, name: string): DraftOperation[] {
  return [{ kind: "setLabel", element: { objectType: typeKey }, name }];
}

/** Adjust list… (D125, D126): one setSource, and the list renamed after its new header when asked. */
export function adjustOperations(source: ProfileSource, rectangle: SourceRectangle, rename?: string): DraftOperation[] {
  const operations: DraftOperation[] = [
    { kind: "setSource", source: source.id, headerRow: rectangle.headerRow, block: rectangle.block },
  ];
  if (rename) operations.push({ kind: "setLabel", element: { objectType: source.objectTypeKey }, name: rename });
  return operations;
}

/** What a load does with the records of a source's type that no row names (PP-D82). */
export type MissingChoice = "report" | "delete";

/** The choice a source holds: report is the default. */
export function missingOf(source: ProfileSource): MissingChoice {
  return source.missing === "delete" ? "delete" : "report";
}

/**
 * Whether the choice means anything for the source: a load finds the records no row names by the source's
 * key, so a source without one, or one that loads no records of its own, has none (the engine refuses
 * `delete` there; the interface offers neither choice).
 */
export function canSetMissing(source: ProfileSource): boolean {
  return Boolean(source.key) && source.record !== "existing";
}

/** `setMissing` for a source: what a load does with the records no row names (PP-D82). */
export function setMissingOperation(source: ProfileSource, missing: MissingChoice): DraftOperation {
  return { kind: "setMissing", source: source.id, missing };
}
