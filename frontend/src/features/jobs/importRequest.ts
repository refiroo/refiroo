/**
 * What the import dialog sends (0.9 J4): the context, the profile, the policy and what happens to
 * records the file finds, always as a preview (D90). Without a choice of its own, records the file
 * finds are updated when a profile reads the file, and only where unchanged since an export when
 * none does (D92): a supplier file carries no versions, an exported table does. Records of another
 * workspace named by their IDs (its export) load as this workspace's own by default (0.9 J5, D99):
 * the preview shows it before anything is written.
 */

import { isApiError } from "@/api/errors";
import type {
  EngineModel,
  ImportOnExisting,
  ImportPolicy,
  ImportProfile,
  ImportRequest,
  OtherWorkspaceIds,
} from "@/types";

/** Where the file loads: a workspace's live data, or one of its change sets at the version read. */
export interface ImportContext {
  workspaceKey: string;
  changeSet?: { id: string; name: string | null; version: number };
}

export const defaultOnExisting = (profileKey: string | null): ImportOnExisting => (profileKey ? "overwrite" : "reject");

export function importRequest(
  context: ImportContext,
  profileKey: string | null,
  policy: ImportPolicy,
  onExisting: ImportOnExisting,
  otherWorkspaceIds: OtherWorkspaceIds = "counterparts",
): ImportRequest {
  return {
    // One context only: live data by its workspace, or a change set with its version claim.
    workspaceKey: context.changeSet ? null : context.workspaceKey,
    changeSetId: context.changeSet?.id ?? null,
    expectedChangeSetVersion: context.changeSet?.version ?? null,
    profileKey,
    policy,
    onExisting,
    otherWorkspaceIds,
    stage: "preview",
  };
}

export type ImportField = "file" | "profile" | "form";

/** The dialog field a refusal belongs to. */
export function importField(cause: unknown): ImportField {
  if (isApiError(cause, "IMPORT_TOO_LARGE") || isApiError(cause, "UNSUPPORTED_FILE_FORMAT")) return "file";
  if (isApiError(cause, "INVALID_IMPORT_PROFILE") || isApiError(cause, "IMPORT_PROFILE_NOT_FOUND")) return "profile";
  return "form";
}

/** The problems a profile refusal lists (`details.problems`), each as a line. */
export function profileProblems(cause: unknown): string[] {
  if (!isApiError(cause)) return [];
  const problems = (cause.details as { problems?: unknown } | undefined)?.problems;
  return Array.isArray(problems)
    ? problems.map((problem: { path?: string; message?: string }) =>
        [problem.message, problem.path && `(${problem.path})`].filter(Boolean).join(" "),
      )
    : [];
}

/** A profile whose sources create records without a key: a file sent twice loads twice. */
export const keyless = (profile: ImportProfile) =>
  profile.sources.some((source) => (source.record ?? "upsert") === "upsert" && !source.key);

/** What a profile loads, as people read it: "Codes → Master values; Lists → Codelists". */
export function profileSummary(model: EngineModel, profile: ImportProfile): string {
  return profile.sources
    .map((source) => {
      const type = model.objectTypes.find((item) => item.key === source.objectTypeKey);
      return `${source.sheet ?? "the first sheet"} → ${type?.pluralName ?? source.objectTypeKey}`;
    })
    .join("; ");
}

/** A key that makes a retried submission answer with the job the first one created. */
export const newIdempotencyKey = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `import-${Date.now()}-${Math.random().toString(36).slice(2)}`;
