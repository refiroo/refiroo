/**
 * The alert for a preview that went out of date before it was confirmed (the move editor's dry run, the
 * migration page's preview). One body: why it is stale, that nothing was done, and what to do next. The
 * dismiss button may be left out (`dismissable={false}`) where the second action is the other way out.
 */

import { ConfirmDialog } from "./ConfirmDialog";

export function StalePreviewDialog({
  title,
  reason,
  past,
  next,
  confirmLabel,
  secondary,
  dismissLabel,
  dismissable,
  pending,
  onCancel,
  onConfirm,
}: {
  title: string;
  /** Why the preview no longer holds, as a sentence. */
  reason: string;
  /** What was not done: "Nothing was {past}." */
  past: string;
  /** What to do next, as a sentence. */
  next: string;
  confirmLabel: string;
  secondary?: { label: string; onClick: () => void };
  dismissLabel?: string;
  dismissable?: boolean;
  pending?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <ConfirmDialog
      title={title}
      tone="plain"
      confirmLabel={confirmLabel}
      pendingLabel={confirmLabel}
      secondary={secondary}
      dismissLabel={dismissLabel}
      dismissable={dismissable}
      pending={pending}
      onCancel={onCancel}
      onConfirm={onConfirm}
    >
      <p>
        {reason} Nothing was {past}. {next}
      </p>
    </ConfirmDialog>
  );
}
