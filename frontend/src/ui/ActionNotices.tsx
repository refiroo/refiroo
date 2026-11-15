import type { GuardedWrite } from "@/ui/useGuardedWrite";
import { Notice } from "@/ui/Notice";

/**
 * What a page's guarded write says: the conflict as a warning titled "Not saved", then another
 * refusal as an error. `hideError` while a dialog shows the refusal itself.
 */
export function ActionNotices({
  guard,
  hideError = false,
  errorTitle = "The action could not be completed",
  focusError = false,
}: {
  guard: Pick<GuardedWrite, "error" | "conflict">;
  hideError?: boolean;
  errorTitle?: string;
  focusError?: boolean;
}) {
  return (
    <>
      {guard.conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {guard.conflict}
        </Notice>
      )}
      {guard.error && !hideError && (
        <Notice tone="error" title={errorTitle} focusOnMount={focusError}>
          {guard.error}
        </Notice>
      )}
    </>
  );
}
