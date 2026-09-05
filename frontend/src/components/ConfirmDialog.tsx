import { useEffect, useRef } from "react";

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
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !pending) onCancel();
    };
    window.addEventListener("keydown", escape);
    return () => {
      window.removeEventListener("keydown", escape);
      previous?.focus();
    };
  }, [onCancel, pending]);
  return (
    <div className="dialog-backdrop" onMouseDown={() => !pending && onCancel()}>
      <div
        className="dialog confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <div>
            <p className="eyebrow">Please confirm</p>
            <h2 id="confirm-title">{title}</h2>
          </div>
        </div>
        <div className="dialog-body">
          {children}
          {error && <div className="notice error-notice">{error}</div>}
        </div>
        <div className="dialog-actions">
          <button ref={cancelRef} className="secondary" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
          <button className="danger" disabled={pending} onClick={onConfirm}>
            {pending ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
