/**
 * Confirmation before an action that cannot be undone (0.17 UX1, PP-D40: at most one, naming what is lost).
 * The confirming button is red where the action destroys something (`tone="danger"`, the default) and the
 * plain main button where it does not (`tone="plain"`); its label says what happens.
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
  dismissLabel = "Cancel",
  tone = "danger",
  pending,
  pendingLabel = "Working…",
  error,
  secondary,
  dismissable = true,
  onCancel,
  onConfirm,
}: {
  title: string;
  children: React.ReactNode;
  confirmLabel?: string;
  /** The button that closes the dialog without acting, where "Cancel" would read as the action. */
  dismissLabel?: string;
  /** `plain` for a step that destroys nothing; the confirming button is then the main button, not red. */
  tone?: "danger" | "plain";
  pending?: boolean;
  /** What the confirming button says while `pending`; a step that keeps its label while it works names it here. */
  pendingLabel?: string;
  error?: string;
  /** A second action beside the confirming one (the stale-preview dialogs: "Open the mapping"). */
  secondary?: { label: string; onClick: () => void };
  /**
   * `false` leaves out the dismiss button: the actions are the only choices, and Escape or a click outside
   * still calls `onCancel`.
   */
  dismissable?: boolean;
  onCancel: () => void;
  /** Without it there is no confirming button: a dialog still reading what it will confirm. */
  onConfirm?: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const secondaryRef = useRef<HTMLButtonElement>(null);
  return (
    <Modal
      title={title}
      role="alertdialog"
      size="confirm"
      showClose={false}
      busy={pending}
      onClose={onCancel}
      initialFocusRef={dismissable ? cancelRef : secondaryRef}
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
        {dismissable && (
          <button ref={cancelRef} className="secondary" disabled={pending} onClick={onCancel}>
            {dismissLabel}
          </button>
        )}
        {secondary && (
          <button ref={secondaryRef} className="secondary" disabled={pending} onClick={secondary.onClick}>
            {secondary.label}
          </button>
        )}
        {onConfirm && (
          <button className={tone === "danger" ? "danger" : "primary"} disabled={pending} onClick={onConfirm}>
            {pending ? pendingLabel : confirmLabel}
          </button>
        )}
      </div>
    </Modal>
  );
}
