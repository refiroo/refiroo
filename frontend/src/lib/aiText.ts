/** Words for Settings › AI and the Propose dialog (0.16 AP1): the send level, a call's purpose and what failed. */

import type { AiCall, AiSendLevel } from "@/types";

/** What each send level lets leave the server, in one plain line. */
export function sendLevelText(level: AiSendLevel, sampleValues: number): string {
  if (level === "structure") return "Names, headers and types; no values";
  if (level === "samples") return `Also up to ${sampleValues} values per column`;
  return "Also the record values a feature needs, with no limit per column";
}

export const PURPOSE: Record<AiCall["purpose"], string> = {
  connectionTest: "Test request",
  mappingTarget: "Targets for unmapped values",
  queryTranslation: "A question in words",
  impactSummary: "An account of a model change",
  historyAccount: "An account of what changed",
  // Only on call rows recorded by older versions; it is no longer a feature.
  workbookLoad: "Load a workbook (no longer offered)",
  assistantSession: "Assistant session",
  modelNames: "Names for an inference (no longer offered)",
};

/** The sentence under a failed call. */
export function failureSentence(call: Pick<AiCall, "failure" | "failureKind">): string {
  return call.failure ?? "The request failed.";
}

/** What the Propose dialog says is sent to the provider, by send level. */
export function sentToProvider(level: AiSendLevel, provider: string | null): string {
  const to = provider ?? "the AI provider";
  return level === "structure"
    ? `Sends each sheet's name and headers and, for every column, its counts over all rows (no values) to ${to}`
    : `Sends each sheet's name and headers and, for every column, counts and its most frequent values over all rows, to ${to}`;
}

/** What the mapping proposal dialog says is sent: record names and the fields the view shows, and the floor when it is known. */
export function sentForMappingTargets(options: {
  provider: string | null;
  model?: string | null;
  sources: string;
  targets: string;
  /** `AI_MIN_CONFIDENCE` as a fraction, when the person may read it. */
  floor?: number;
}): string {
  const to = options.provider ?? "the AI provider";
  const who = options.model ? `${to} (${options.model})` : to;
  const floor =
    options.floor === undefined
      ? ""
      : ` Proposals below ${Math.round(options.floor * 100)}% confidence are not offered.`;
  return `Sent to ${who}: the names of the ${options.sources} and ${options.targets} and the fields this view shows.${floor}`;
}
