/**
 * Confirmation before a destructive action.
 *
 * Uses `alertdialog` rather than `dialog`, and opens with Cancel focused, so that confirming is
 * always a deliberate second act.
 */

import { useRef } from "react";
import { Modal } from "./Modal";
import { Notice } from "./Notice";

export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  pending,
  error,
  onCancel,
  onConfirm,
}: {
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  pending?: boolean;
  error?: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  return (
    <Modal
      title={title}
      eyebrow="Please confirm"
      role="alertdialog"
      size="confirm"
      showClose={false}
      busy={pending}
      onClose={onCancel}
      initialFocusRef={cancelRef}
    >
      <div className="dialog-body">
        {children}
        {error && (
          <Notice tone="error" title="The action could not be completed">
            {error}
          </Notice>
        )}
      </div>
      <div className="dialog-actions">
        <button ref={cancelRef} className="secondary" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
        <button className="danger" disabled={pending} onClick={onConfirm}>
          {pending ? "Working…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
