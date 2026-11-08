/** Words for the assistant's load of a workbook (0.16 AP6a): its phases, a check's figures and what a load leaves out. */

import type { AiTask, AiTaskDesignCheck, AiTaskPhase } from "@/types";
import { count } from "@/features/settings/limits";

export const PHASE: Record<AiTaskPhase, string> = {
  profiling: "Reading the workbook",
  reading: "The assistant is reading it",
  checking: "Checking every row",
  designing: "The assistant is designing the model and the load",
};

/** A design's check (per sheet); a task recorded before the design holds a check per table, which this is not. */
export const isDesignCheck = (check: AiTask["check"]): check is AiTaskDesignCheck => !!check && "sheets" in check;

/** A task whose job waits for the assistant's worker says so (0.13 AQ): `ahead` counts the assistant jobs before it. */
export function waitingText(ahead: number | null | undefined): string | null {
  if (ahead === null || ahead === undefined) return null;
  if (ahead === 0) return "Starting…";
  return `Waiting for the assistant: ${ahead} ${ahead === 1 ? "task" : "tasks"} ahead`;
}

/** What a job running for the task is doing, in plain words. */
export function runningText(task: Pick<AiTask, "state" | "phase" | "ahead">): string {
  const waiting = waitingText(task.ahead);
  if (waiting) return waiting;
  if (task.state === "loading") return "Loading into the change set…";
  if (task.phase) return PHASE[task.phase];
  return task.state === "checking" ? "Checking every row" : "Reading the workbook";
}

/** Whether the task waits for a job: the page follows it until it rests. */
export const running = (task: Pick<AiTask, "state">) =>
  task.state === "reading" || task.state === "checking" || task.state === "loading";

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

/** Everything a design's load does not carry, by sheet: sheets not loaded and columns left out. A task recorded before the design (no `design`) leaves nothing to list. */
export function notLoadedEntries(task: AiTask, columns: boolean): { sheet: string; text: string }[] {
  return task.design ? designNotLoaded(task, columns) : [];
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
