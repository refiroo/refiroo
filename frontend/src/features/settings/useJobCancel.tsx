/**
 * The cancel of a queued or running job from a Jobs table (`POST /jobs/{id}/cancel`, J24.2): the
 * confirmation, the request, and the notice when the job finished first. One copy for the flat
 * list, the grouped list and a group's jobs (0.13 JG).
 */

import { useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { Job } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Notice } from "@/ui/Notice";

export function useJobCancel({
  onCancelled,
  onFinishedFirst,
}: {
  /** The job as the engine answers the request: the table shows it in place. */
  onCancelled: (job: Job) => void;
  /** The job ended before the request reached it: the table reads its rows again. */
  onFinishedFirst: () => void;
}): { ask: (job: Job) => void; ui: ReactNode } {
  const [cancelling, setCancelling] = useState<Job>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function cancel() {
    if (!cancelling) return;
    setPending(true);
    setError("");
    try {
      onCancelled(await api.cancelJob(cancelling.id));
      setCancelling(undefined);
    } catch (cause) {
      if (isApiError(cause) && cause.status === 409) {
        // The job finished before the request reached it: say so, and show where it ended.
        setCancelling(undefined);
        setNotice(errorMessage(cause));
        onFinishedFirst();
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  const ui = (
    <>
      {notice && (
        <Notice
          tone="warning"
          actions={
            <button type="button" className="secondary" onClick={() => setNotice("")}>
              Dismiss
            </button>
          }
        >
          {notice}
        </Notice>
      )}
      {cancelling && (
        <ConfirmDialog
          title="Cancel this job?"
          confirmLabel="Cancel job"
          dismissLabel="Keep the job"
          pending={pending}
          error={error}
          onCancel={() => {
            setCancelling(undefined);
            setError("");
          }}
          onConfirm={cancel}
        >
          <p>
            The job stops at its next chunk. Items it has not reached are left unprocessed; chunks already committed
            stay applied, and an atomic job is rolled back completely.
          </p>
        </ConfirmDialog>
      )}
    </>
  );
  return { ask: setCancelling, ui };
}
