/**
 * The editor filled by the inference (0.10 A6b, D94): what a new draft's start asked to propose,
 * until the editor runs it once the workbook is profiled; and the elements the inference names, as
 * the editor's selections and columns show them.
 *
 * The request waits in memory, keyed by draft: New from a workbook hands it over and the editor takes
 * it. A reload before the workbook is profiled loses it, and ⋯ › Propose again… asks for it anew.
 */

import type { DraftProfileDocument, EditorSelection, InferenceRequest, ModelDraftOutline } from "@/types";

const waiting = new Map<string, InferenceRequest>();

/** Ask the editor of ``draftId`` to propose once its workbook is profiled. */
export function proposeWhenProfiled(draftId: string, request: InferenceRequest): void {
  waiting.set(draftId, request);
}

/** The request waiting for ``draftId``, taken: it runs once. */
export function takeWaitingProposal(draftId: string): InferenceRequest | undefined {
  const request = waiting.get(draftId);
  waiting.delete(draftId);
  return request;
}

export function hasWaitingProposal(draftId: string): boolean {
  return waiting.has(draftId);
}

/** The element a selection shows, as an inference names it (`objectType:item`). */
export function elementOfSelection(selection: EditorSelection): string | undefined {
  if (selection.show === "type") return `objectType:${selection.key}`;
  if (selection.show === "attributeType") return `attributeType:${selection.key}`;
  if (selection.show === "relationType") return `relationType:${selection.key}`;
  return undefined;
}

/** Whether a model element the inference names is part of a release (its outline mark). */
export function isReleasedElement(outline: ModelDraftOutline | undefined, element: string): boolean {
  if (!outline) return false;
  const [kind, rest = ""] = element.split(/:(.*)/s);
  const mark =
    kind === "objectType"
      ? outline.objectTypes.find((item) => item.key === rest)?.mark
      : kind === "attributeType"
        ? outline.attributeTypes.find((item) => item.key === rest)?.mark
        : kind === "relationType"
          ? outline.relationTypes.find((item) => item.key === rest)?.mark
          : undefined;
  return mark === "released";
}

/**
 * The elements still as the inference proposed them (D92), for the editor's panes and the canvas's
 * cards: an installed element is part of a release, so it reads Released and is no longer Proposed.
 */
export function stillProposed(proposed: ReadonlyMap<string, unknown>, outline: ModelDraftOutline): Set<string> {
  return new Set([...proposed.keys()].filter((element) => !isReleasedElement(outline, element)));
}

/** A column's elements: its binding in each source of its sheet (`column:<source>/<header>`). */
export function columnElements(
  profile: DraftProfileDocument | null | undefined,
  sheet: string,
  header: string,
): string[] {
  return (profile?.sources ?? [])
    .filter((source) => source.sheet === sheet)
    .map((source) => `column:${source.id}/${header}`);
}

/** Each pattern's name as the editor says it (D90). */
export const PATTERN_LABELS: Record<string, string> = {
  newApplication: "New application",
  keyColumn: "Key column",
  repeatedParent: "Repeated parent",
  levelColumns: "Level columns",
  codeAndName: "Code and name pair",
  nameDrift: "Name drift",
  flagColumns: "Flag columns",
  multiValued: "Multi-valued cell",
  textLookup: "Text lookup",
  placeholders: "Placeholder values",
  sheetReference: "Reference to another sheet",
  translationsByRow: "Translations, a row per language",
  translationsByColumn: "Translations, a column per language",
  externalId: "External IDs",
  attribute: "Attribute",
  navigationGroup: "Navigation group",
  modelDescription: "Model description",
  describedList: "A list the description names",
  describedField: "A field the description names",
  describedFlags: "Flags the description names",
  listBlock: "A list of a sheet laid out for reading",
};

export const patternLabel = (pattern: string | null | undefined) =>
  (pattern && PATTERN_LABELS[pattern]) || pattern || "Proposal";
