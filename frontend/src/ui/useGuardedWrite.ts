import { useCallback, useState } from "react";
import { errorMessage, isVersionConflict } from "@/api/errors";

/**
 * The sentence for a record that changed while its page was open (SR-D2). A person reads "They are
 * shown as they are now"; `now` replaces the second sentence where the page says what the record
 * became (a workspace's label and status); `reload` is for a panel that does not read it again by
 * itself.
 */
export function changedWhileOpen(
  noun: string,
  { they = false, now, reload = false }: { they?: boolean; now?: string; reload?: boolean } = {},
) {
  const shown = reload
    ? "Reload it to see it as it is now; then review it and choose again."
    : `${they ? "They are shown as they are now" : "It is shown as it is now"}; review it and choose again.`;
  return `This ${noun} changed while the page was open. ${now ? `${now} Review it and choose again.` : shown}`;
}

/**
 * A page's write (SR5): `pending` while it runs, a stale version (`VERSION_CONFLICT`) said with its
 * own warning, any other refusal as worded by the server. A write clears what the last one said.
 */
export function useGuardedWrite() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState("");

  /**
   * `onConflict` reads the record again (and closes what the write came from) and returns the
   * sentence to show (a write with no version leaves it out); `onRefused` runs before another refusal is shown, such as a reload of what the
   * refusal says changed. Resolves to whether the write was made.
   */
  const run = useCallback(
    async (
      action: () => Promise<void>,
      {
        onConflict,
        onRefused,
      }: { onConflict?: () => Promise<string> | string; onRefused?: (cause: unknown) => Promise<void> | void },
    ): Promise<boolean> => {
      setPending(true);
      setError("");
      setConflict("");
      try {
        await action();
        return true;
      } catch (cause) {
        // a handler that throws must not leave the person without a message
        try {
          if (onConflict && isVersionConflict(cause, ["VERSION_CONFLICT"])) setConflict(await onConflict());
          else {
            await onRefused?.(cause);
            setError(errorMessage(cause));
          }
        } catch {
          setError(errorMessage(cause));
        }
        return false;
      } finally {
        setPending(false);
      }
    },
    [],
  );

  return { pending, error, conflict, setError, setConflict, run };
}

export type GuardedWrite = ReturnType<typeof useGuardedWrite>;
