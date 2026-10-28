/**
 * The draft profile's key belongs to another model (`IMPORT_PROFILE_MODEL_MISMATCH`): the refusals
 * of installing, activating and loading, and the Issues list, all offer the same one-click step,
 * "Use 'X-2'", which sends `setProfile` with the free key the engine found (the user, 2026-10-28).
 */

import { isApiError } from "@/api/errors";
import type { DraftOperation } from "@/types";

export const PROFILE_KEY_MISMATCH = "IMPORT_PROFILE_MODEL_MISMATCH";
/** Where the engine points: the key of the draft's profile. */
export const PROFILE_KEY_POINTER = "/profile/key";

/** The free key a refusal offers when the profile's key belongs to another model. */
export function freeKeyOf(cause: unknown): string | undefined {
  if (!isApiError(cause, PROFILE_KEY_MISMATCH)) return undefined;
  const key = ((cause.details ?? {}) as { freeKey?: unknown }).freeKey;
  return typeof key === "string" && key ? key : undefined;
}

export const setProfileKey = (key: string): DraftOperation => ({ kind: "setProfile", key });

export function UseFreeKey({ freeKey, onUse, disabled }: { freeKey: string; onUse: () => void; disabled?: boolean }) {
  return (
    <button type="button" className="secondary" disabled={disabled} onClick={onUse}>
      Use '{freeKey}'
    </button>
  );
}
