/**
 * What the move editor asks of a dry run and reads from it (0.11 X4): the selection it sends (D142),
 * the figures shown after every step with their difference from the last (D140), and the report's
 * cards of what cannot move (D143).
 */

import { criteriaFromFilters } from "@/model/exportRequest";
import type {
  EngineModel,
  ExportCriterion,
  Job,
  ModelMapping,
  MoveChoice,
  MoveCounts,
  MoveSelection,
  MoveSummary,
} from "@/types";

/**
 * What moves, as the dry run is asked for it: by default every mapped source type, following the
 * mapping until the user chooses (D142); none mapped, the whole workspace. A type's filters become
 * its criteria as an export's do.
 */
export function selectionFor(
  mapping: ModelMapping,
  chosen: MoveChoice | undefined,
  source: EngineModel,
): MoveSelection {
  if (chosen?.kind === "all") return {};
  if (chosen?.kind === "subtree") return { parentObjectId: chosen.objectId };
  if (chosen?.kind === "types")
    return chosen.types.length
      ? {
          types: chosen.types.map((item) => ({
            objectTypeKey: item.objectTypeKey,
            where: criteriaFromFilters(source, item.filters),
          })),
        }
      : {};
  const types = mapping.types.map((entry) => ({ objectTypeKey: entry.source, where: [] as ExportCriterion[] }));
  return types.length ? { types } : {};
}

function criterionKey(criterion: ExportCriterion): unknown {
  if ("related" in criterion)
    return {
      related: {
        relationTypeKey: criterion.related.relationTypeKey,
        direction: criterion.related.direction,
        where: criterion.related.where.map(criterionKey),
      },
      not: Boolean(criterion.not),
    };
  return { field: criterion.field, op: criterion.op, value: criterion.value ?? null };
}

/** A selection in a form two of them compare by: what the job stored and what the editor sends. */
export function selectionKey(selection: MoveSelection | undefined): string {
  return JSON.stringify({
    types: (selection?.types ?? []).map((item) => ({ type: item.objectTypeKey, where: item.where.map(criterionKey) })),
    parent: selection?.parentObjectId ?? null,
    ids: selection?.objectIds ?? null,
  });
}

/** What a dry run was asked for: the mapping's version, what moves and copy or move. */
export function runKey(version: number, selection: MoveSelection, mode: "copy" | "move"): string {
  return `${version}|${mode}|${selectionKey(selection)}`;
}

/** The run key a move job was started with, from its stored parameters. */
export function jobRunKey(job: Job): string | undefined {
  const mapping = job.parameters.mapping as { version?: number } | undefined;
  if (typeof mapping?.version !== "number") return undefined;
  const mode = job.parameters.mode === "move" ? "move" : "copy";
  return runKey(mapping.version, (job.parameters.selection ?? {}) as MoveSelection, mode);
}

export interface Figures {
  create: number;
  update: number;
  cannot: number;
  carried: number;
  dropped: number;
}

const sum = (items: { counts: MoveCounts }[], pick: (counts: MoveCounts) => number) =>
  items.reduce((total, item) => total + pick(item.counts), 0);

/** The board's five figures: records created, updated (moved before or matched), not moving; relationships. */
export function figuresOf(summary: MoveSummary): Figures {
  return {
    create: sum(summary.types, (counts) => counts.create),
    update: sum(summary.types, (counts) => counts.update + counts.updateOriginal),
    cannot: sum(summary.types, (counts) => counts.refused + counts.notMoved),
    carried: sum(summary.relationships, (counts) => counts.create + counts.update + counts.updateOriginal),
    dropped: sum(summary.relationships, (counts) => counts.refused + counts.notMoved),
  };
}

/** A figure's difference from the last step's, in words; none when it did not change. */
export function difference(now: number, before: number | undefined): string {
  if (before === undefined || now === before) return "";
  const change = now - before;
  return `${change > 0 ? "+" : "−"}${Math.abs(change).toLocaleString("en-GB")} since the last step`;
}

/** Whether a dry run's load would change anything: a row created or updated (D131). */
export const movesAnything = (summary: MoveSummary) =>
  summary.counts.create + summary.counts.update + summary.counts.updateOriginal > 0;

/** The words of an operation, so a copy is never called a move (the user, 2026-10-19). */
export interface ModeWords {
  Verb: string;
  verb: string;
  ing: string;
  past: string;
  /** "Cannot move", "Cannot be copied". */
  cannot: string;
  /** "What cannot move", "What cannot be copied". */
  whatCannot: string;
  /** "What to move", "What to copy". */
  what: string;
}

export function modeWords(mode: "copy" | "move"): ModeWords {
  return mode === "move"
    ? {
        Verb: "Move",
        verb: "move",
        ing: "Moving",
        past: "moved",
        cannot: "Cannot move",
        whatCannot: "What cannot move",
        what: "What to move",
      }
    : {
        Verb: "Copy",
        verb: "copy",
        ing: "Copying",
        past: "copied",
        cannot: "Cannot be copied",
        whatCannot: "What cannot be copied",
        what: "What to copy",
      };
}

export const VALUES_NOT_CARRIED = "VALUES_NOT_CARRIED";

/** What a reason means and what fixes it, by code; others show the engine's message. */
const REASONS: Record<string, { label: string; fix: string }> = {
  TYPE_NOT_MAPPED: { label: "Type not mapped", fix: "Map the type, or leave it out of the selection" },
  PARENT_TYPE_NOT_MAPPED: { label: "Parent's type not mapped", fix: "Map the parent's type, or place the records" },
  PARENT_NOT_FOUND: {
    label: "Parent not in the target",
    fix: "Select the parent too, or create parents where missing",
  },
  RECORD_NOT_MOVED: { label: "Parent left out", fix: "Its parent is left out, so it is too" },
  RELATION_NOT_MAPPED: { label: "Relationship not mapped", fix: "Map the relationship to carry it" },
  RELATION_TARGET_LEFT_BEHIND: {
    label: "Relationship left behind",
    fix: "The other end is not selected and not in the target",
  },
  MATCH_AMBIGUOUS: { label: "Several records match", fix: "Find existing records by a unique field instead" },
  MISSING_REQUIRED_ATTRIBUTES: { label: "Required value missing", fix: "Set a default for it in the mapping" },
  REQUIRED_ATTRIBUTE_MISSING: { label: "Required value missing", fix: "Set a default for it in the mapping" },
  ATTRIBUTE_UNIQUENESS_VIOLATED: {
    label: "Unique value already held",
    fix: "Find existing records by that field in the mapping",
  },
  DUPLICATE_ATTRIBUTE_VALUE: {
    label: "Unique value already held",
    fix: "Find existing records by that field in the mapping",
  },
  RELATION_CANDIDATE_REFUSED: {
    label: "Record not allowed at a relationship's end",
    fix: "The target model sets criteria for that end, which the record does not meet; the record goes without the relationship",
  },
  REQUIRED_RELATION_MISSING: {
    label: "Required relationship missing",
    fix: "Map the relationship the target requires",
  },
  PARENT_REQUIRED: { label: "Needs a parent", fix: "Place the records under a parent in the mapping" },
  [VALUES_NOT_CARRIED]: { label: "Value not carried", fix: "The record goes without it; map the field to carry it" },
};

export function reasonText(code: string): { label: string; fix: string } {
  return (
    REASONS[code] ?? {
      label: code
        .toLowerCase()
        .replaceAll("_", " ")
        .replace(/^./, (c) => c.toUpperCase()),
      fix: "The target refuses it",
    }
  );
}

export interface ReasonCard {
  code: string;
  count: number;
  label: string;
  fix: string;
}

/** The report's cards: each reason a row does not move, then the values records move without. */
export function reasonCards(summary: MoveSummary): ReasonCard[] {
  const cards = summary.reasons
    .filter((item) => item.count > 0)
    .map((item) => ({ code: item.code, count: item.count, ...reasonText(item.code) }));
  const values = summary.attributesNotCarried.reduce((total, item) => total + item.count, 0);
  if (values) cards.push({ code: VALUES_NOT_CARRIED, count: values, ...reasonText(VALUES_NOT_CARRIED) });
  return cards;
}

/** The mapping row a reason's `action` changes (D143), under the row's source type. */
export function rowForAction(action: string | undefined, relationTypeKey?: string): string | undefined {
  if (action === "mapType") return "type";
  if (action === "mapRelation" && relationTypeKey) return `relation:${relationTypeKey}`;
  if (action === "setParent") return "parent";
  if (action === "setMatch") return "match";
  return undefined;
}
