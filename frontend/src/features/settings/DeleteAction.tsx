/**
 * A Delete button with the question it asks in its own words (0.13 ED): an import profile, a source
 * file and a model mapping are each deleted through it. The caller shows it only to a person who may
 * delete (a permission hides, never disables); a refusal stays in the dialog with the server's reason.
 */

import { useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

export function DeleteAction({
  label,
  title,
  confirmLabel,
  children,
  onDelete,
  className = "secondary",
}: {
  /** The button's words, such as "Delete the profile…". */
  label: string;
  /** The dialog's title. */
  title: string;
  confirmLabel: string;
  /** What deleting does, in a sentence or two. */
  children: ReactNode;
  /** Deletes; resolves when it is done, and the caller then updates its page. */
  onDelete: () => Promise<void>;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function confirm() {
    setPending(true);
    setError("");
    try {
      await onDelete();
      setOpen(false);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>
        {label}
      </button>
      {open && (
        <ConfirmDialog
          title={title}
          confirmLabel={confirmLabel}
          pending={pending}
          error={error}
          onCancel={() => {
            setOpen(false);
            setError("");
          }}
          onConfirm={() => void confirm()}
        >
          <p>{children}</p>
        </ConfirmDialog>
      )}
    </>
  );
}
