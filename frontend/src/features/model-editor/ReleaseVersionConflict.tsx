/**
 * The draft's release version is taken by another installed release of the model
 * (`RELEASE_IDENTITY_CONFLICT`): every refusal of installing offers the same one-click step, "Use
 * 0.3.19", which sends `setRelease` with the free version the engine found. Like the profile key's
 * step (ProfileKeyConflict), it leaves no refusal without a way forward.
 */

import { isApiError } from "@/api/errors";
import type { DraftOperation } from "@/types";

export const RELEASE_VERSION_TAKEN = "RELEASE_IDENTITY_CONFLICT";

export interface FreeVersion {
  /** The version the draft asked for, taken by another release with other content. */
  taken: string;
  free: string;
}

/** The free version a refusal offers when the draft's version is taken. */
export function freeVersionOf(cause: unknown): FreeVersion | undefined {
  if (!isApiError(cause, RELEASE_VERSION_TAKEN)) return undefined;
  const details = (cause.details ?? {}) as { releaseVersion?: unknown; freeVersion?: unknown };
  const free = details.freeVersion;
  if (typeof free !== "string" || !free) return undefined;
  return { taken: typeof details.releaseVersion === "string" ? details.releaseVersion : "", free };
}

/** The refusal in plain words, naming the step. */
export function versionTakenText(found: FreeVersion): string {
  return `Version ${found.taken} is taken by another installed release of this model. Use ${found.free}, the next free one.`;
}

export const setReleaseVersion = (identity: { key: string; name: string }, version: string): DraftOperation => ({
  kind: "setRelease",
  key: identity.key.trim(),
  name: identity.name.trim(),
  version,
});

export function UseFreeVersion({
  version,
  onUse,
  disabled,
}: {
  version: string;
  onUse: () => void;
  disabled?: boolean;
}) {
  return (
    <button type="button" className="secondary" disabled={disabled} onClick={onUse}>
      Use {version}
    </button>
  );
}
