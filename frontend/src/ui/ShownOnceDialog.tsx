import type { ReactNode } from "react";
import { CopyValue } from "@/ui/CopyValue";
import { Modal } from "@/ui/Modal";

/**
 * A secret or one-time link the engine answers only once (a webhook's signing key, a person's
 * password link, D304): what it is for, the value with Copy, and a button that says it was kept.
 * No read returns the value again, so closing the dialog is the last chance to copy it.
 */
export function ShownOnceDialog({
  title,
  eyebrow,
  label,
  value,
  confirmLabel,
  children,
  onClose,
}: {
  title: string;
  eyebrow: string;
  /** Names the value for Copy and for assistive technology ("Signing key"). */
  label: string;
  value: string;
  confirmLabel: string;
  /** What the value is for and what to do with it; may follow the value with notes. */
  children: { before: ReactNode; after?: ReactNode };
  onClose: () => void;
}) {
  return (
    <Modal title={title} eyebrow={eyebrow} size="compact" onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onClose();
        }}
      >
        {children.before}
        <p className="webhook-secret">
          <CopyValue label={label} value={value} />
        </p>
        {children.after}
        <div className="dialog-actions">
          <button className="primary">{confirmLabel}</button>
        </div>
      </form>
    </Modal>
  );
}
