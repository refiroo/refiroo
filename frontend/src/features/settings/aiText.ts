/** Words for Settings › AI and the Propose dialog (0.16 AP1): the send level, a call's purpose and what failed. */

import type { AiCall, AiPurpose, AiSendLevel } from "@/types";

/** What each send level lets leave the server, in one plain line. */
export function sendLevelText(level: AiSendLevel, sampleValues: number): string {
  if (level === "structure") return "Names, headers and types; no values";
  if (level === "samples") return `Also up to ${sampleValues} values per column`;
  return `Also the record values a feature needs, up to ${sampleValues} per column`;
}

export const PURPOSE: Record<AiPurpose, string> = {
  connectionTest: "Test request",
  modelNames: "Names for an inference",
};

/** The sentence under a failed call. */
export function failureSentence(call: Pick<AiCall, "failure" | "failureKind">): string {
  return call.failure ?? "The request failed.";
}

/** What the Propose dialog says is sent to the provider, by send level. */
export function sentToProvider(level: AiSendLevel, provider: string | null): string {
  const to = provider ?? "the AI provider";
  return level === "structure"
    ? `Sends the sheets' names and headers to ${to}`
    : `Sends the sheets' names, headers and first rows to ${to}`;
}
