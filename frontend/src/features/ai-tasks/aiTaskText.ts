/** Words for the assistant's load of a workbook (0.16 AP6a): its phases, what each table is, its choices. */

import type {
  AiTask,
  AiTaskAttention,
  AiTaskCheck,
  AiTaskDesignCheck,
  AiTaskPhase,
  AiTaskTable,
  AiTaskTableChoices,
} from "@/types";
import { count } from "@/features/settings/limits";

export const PHASE: Record<AiTaskPhase, string> = {
  profiling: "Reading the workbook",
  reading: "The assistant is reading it",
  checking: "Checking every row",
  designing: "The assistant is designing the model and the load",
};

/** A design's check (per sheet) rather than the check of a plain reading (per table). */
export const isDesignCheck = (check: AiTask["check"]): check is AiTaskDesignCheck => !!check && "sheets" in check;

/** The check of a task without a design, else null. */
export const plainCheck = (task: Pick<AiTask, "check">): AiTaskCheck | null =>
  task.check && !isDesignCheck(task.check) ? task.check : null;

/** What a job running for the task is doing, in plain words. */
export function runningText(task: Pick<AiTask, "state" | "phase">): string {
  if (task.state === "loading") return "Loading into the change set…";
  if (task.phase) return PHASE[task.phase];
  return task.state === "checking" ? "Checking every row" : "Reading the workbook";
}

/** Whether the task waits for a job: the page follows it until it rests. */
export const running = (task: Pick<AiTask, "state">) =>
  task.state === "reading" || task.state === "checking" || task.state === "loading";

/** The pill on a table's card: what the assistant (or the rules) made of the sheet. */
export function readingPill(table: Pick<AiTaskTable, "as" | "typeName">): {
  tone: "success" | "neutral";
  text: string;
} {
  if (table.as === "update") return { tone: "success", text: `An update of ${table.typeName ?? "stored records"}` };
  if (table.as === "newData") return { tone: "neutral", text: "Something new: not loaded in this version" };
  return { tone: "neutral", text: "Notes for people, not data: not loaded" };
}

export const rowsText = (rows: number) => `${count(rows)} ${rows === 1 ? "row" : "rows"}`;

/** The choices of one table as the person sees them now: the reading's, then what they changed. */
export type TableChoices = Required<Pick<AiTaskTableChoices, "newRecords" | "names" | "missing">> & {
  keyColumn: string;
};

export function choicesOf(table: AiTaskTable): TableChoices {
  return {
    keyColumn: table.keyColumn ?? "",
    newRecords: table.choices.newRecords.value,
    names: table.choices.names.value,
    missing: table.choices.missing.value,
  };
}

/** Only what the person changed, for the plan request; a table with no change is not sent. */
export function changedChoices(tables: AiTaskTable[], now: Record<string, TableChoices>): AiTaskTableChoices[] {
  const changed: AiTaskTableChoices[] = [];
  for (const table of tables) {
    const chosen = now[table.table];
    if (!chosen || table.as !== "update") continue;
    const before = choicesOf(table);
    const entry: AiTaskTableChoices = { table: table.table };
    if (chosen.keyColumn !== before.keyColumn && chosen.keyColumn) entry.keyColumn = chosen.keyColumn;
    if (chosen.newRecords !== before.newRecords) entry.newRecords = chosen.newRecords;
    if (chosen.names !== before.names) entry.names = chosen.names;
    if (chosen.missing !== before.missing) entry.missing = chosen.missing;
    if (Object.keys(entry).length > 1) changed.push(entry);
  }
  return changed;
}

/** A value a check lists, as the person reads it. */
export function shown(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  return JSON.stringify(value);
}

/** What the engine refused, by its code, in words; an unknown code reads as it came. */
export function refusalText(code: string | null): string {
  if (!code) return "Refused";
  return code.charAt(0) + code.slice(1).toLowerCase().replace(/_/g, " ");
}

export const plural = (n: number, one: string, many = `${one}s`) => `${count(n)} ${n === 1 ? one : many}`;

/** What a table still needs from the person, in a pill's words. */
const ATTENTION: Record<AiTaskAttention, string> = {
  newKeys: "New keys to decide",
  namesDiffer: "Names differ",
  missing: "Stored records missing from the file",
  meaning: "Matched by meaning: check",
  leftOutColumns: "Columns left out",
  notLoaded: "Not loaded: something new",
  noParent: "New rows have no place to go",
};

/** A table needs the person when the reading says so or the person's own choice is in it. */
export const needsPerson = (table: AiTaskTable) =>
  (table.attention ?? []).length > 0 ||
  (table.as === "update" && Object.values(table.choices).some((choice) => choice.owner === "person"));

/** The pill of a table that needs the person: the first thing it needs, or that the person decided. */
export function attentionPill(table: AiTaskTable): { tone: "warning" | "neutral"; text: string } {
  const first = table.attention?.[0];
  if (first) return { tone: first === "notLoaded" ? "neutral" : "warning", text: ATTENTION[first] };
  return { tone: "neutral", text: "Decided by you" };
}

/** "Sheet A1:D11" for a table's place in the file. */
export const foundOn = (table: Pick<AiTaskTable, "sheet" | "range">) =>
  table.range ? `${table.sheet} ${table.range}` : table.sheet;

/** The languages a table's columns load as translations. */
export function languagesOf(table: AiTaskTable): string[] {
  const found = table.columns
    .filter((column) => column.kind === "relatedRecord" && !column.leftOut)
    .map((column) => {
      const related = (column.binding as { relatedRecord?: { parent?: { value?: unknown } } } | null)?.relatedRecord;
      const value = related?.parent?.value;
      return typeof value === "string" ? value : column.header;
    });
  return [...new Set(found)];
}

/** What else a table loads: translations by language, the parent its records sit under. */
export function alsoLoads(table: AiTaskTable): string {
  const parts = languagesOf(table).map((language) => `${language} translations`);
  if (table.parent?.value) parts.push(`under “${table.parent.value}”`);
  return parts.join(", ") || "—";
}

/** Items grouped by the sheet they are on, in the order the sheets first appear. */
export interface SheetItems {
  sheet: string;
  items: string[];
}

export function bySheet(entries: { sheet: string; text: string }[]): SheetItems[] {
  const sheets = new Map<string, string[]>();
  for (const entry of entries) sheets.set(entry.sheet, [...(sheets.get(entry.sheet) ?? []), entry.text]);
  return [...sheets].map(([sheet, items]) => ({ sheet, items }));
}

/** What the reading skipped as not data: title blocks and sheets with no table. */
export function skippedByReading(task: AiTask): {
  titles: number;
  sheets: number;
  entries: { sheet: string; text: string }[];
} {
  const titles = task.reading?.titles ?? [];
  const sheets = task.reading?.sheets ?? [];
  return {
    titles: titles.length,
    sheets: sheets.length,
    entries: [
      ...titles.map((title) => ({ sheet: title.sheet, text: `${title.range}: title “${title.text}”` })),
      ...sheets.map((sheet) => ({ sheet: sheet.sheet, text: `Not data: ${sheet.reason}` })),
    ],
  };
}

/** Everything a load does not carry, by sheet: skipped titles and sheets, new data, columns left out. */
export function notLoadedEntries(task: AiTask, columns: boolean): { sheet: string; text: string }[] {
  if (task.design) return designNotLoaded(task, columns);
  return [
    ...skippedByReading(task).entries,
    ...(task.reading?.tables ?? [])
      .filter((table) => table.as !== "update")
      .map((table) => ({ sheet: table.sheet, text: `${foundOn(table)}: something new, not loaded in this version` })),
    ...(columns
      ? (plainCheck(task)?.tables ?? []).flatMap((table) =>
          table.leftOut.map((header) => ({ sheet: table.sheet, text: `Column “${header}” is left out` })),
        )
      : []),
  ];
}

/** A design loads what its profile reads: not loaded are the sheets no source reads and the
 * columns no source of their sheet loads, with the assistant's reason; not the rules' first reading. */
function designNotLoaded(task: AiTask, columns: boolean): { sheet: string; text: string }[] {
  const outcome = task.design?.outcome ?? null;
  const sheets = Array.isArray(outcome?.sheetsNotLoaded) ? (outcome.sheetsNotLoaded as string[]) : [];
  // The engine's list: only columns no source of their sheet loads, each with why.
  const ignored = columns
    ? (task.design?.leftOut ?? []).map((left) => ({
        sheet: left.sheet,
        text: `Column “${left.column}” is left out${left.reason ? `: ${left.reason}` : " (no reason given)"}`,
      }))
    : [];
  return [...sheets.map((sheet) => ({ sheet, text: `Sheet “${sheet}”: the design does not load it` })), ...ignored];
}

/** "3 title rows and 2 sheets" for a fold's label. */
export function skippedText(parts: [number, string, string?][]): string {
  const said = parts.filter(([n]) => n > 0).map(([n, one, many]) => plural(n, one, many));
  return said.length > 1 ? `${said.slice(0, -1).join(", ")} and ${said[said.length - 1]}` : (said[0] ?? "");
}

/** The task's name for a page title and a change set: its file, else its words, else "Instruction". */
export function taskTitle(task: Pick<AiTask, "fileName" | "words">): string {
  if (task.fileName) return task.fileName;
  const words = (task.words ?? "").trim();
  return words ? (words.length > 80 ? `${words.slice(0, 79)}…` : words) : "Instruction";
}
