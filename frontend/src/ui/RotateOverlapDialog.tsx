import { useState, type ReactNode } from "react";
import { Choice } from "@/ui/Choice";
import { CancelButton, Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

/**
 * Rotate a secret or key: how long the current one keeps working beside the new one (D352, D238), in
 * hours, or "stop it now" for one that leaked. A client's secret and a webhook's signing key rotate
 * the same way, and differ only in the words they use.
 */
export function RotateOverlapDialog({
  title,
  eyebrow,
  lead,
  stopNowHint,
  submitLabel,
  pendingLabel,
  errorTitle,
  pending,
  error,
  onClose,
  onRotate,
}: {
  title: string;
  eyebrow: string;
  /** What a rotation does, ending where the choice begins ("…keeps working for:"). */
  lead: ReactNode;
  /** What stopping the current one at once costs the system still using it. */
  stopNowHint: string;
  submitLabel: string;
  pendingLabel: string;
  errorTitle: string;
  pending: boolean;
  error: string;
  onClose: () => void;
  onRotate: (overlapHours: number) => void;
}) {
  const overlaps: [string, string, string][] = [
    ["1", "1 hour", ""],
    ["24", "24 hours", "The usual choice."],
    ["168", "7 days", "The longest overlap."],
    ["0", "Stop it now", stopNowHint],
  ];
  const [overlap, setOverlap] = useState("24");
  const hint = overlaps.find(([value]) => value === overlap)?.[2];
  return (
    <Modal title={title} eyebrow={eyebrow} size="compact" busy={pending} onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onRotate(Number(overlap));
        }}
      >
        <p>{lead}</p>
        <fieldset className="form-field rotate-overlap">
          <legend className="visually-hidden">How long the current one keeps working</legend>
          <Choice
            name="rotate-overlap"
            value={overlap}
            options={overlaps.map(([value, label]) => [value, label] as [string, string])}
            onChange={setOverlap}
          />
          {hint && <p className="admin-hint">{hint}</p>}
        </fieldset>
        {error && (
          <Notice tone="error" title={errorTitle}>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <CancelButton disabled={pending} />
          <button className="primary" disabled={pending}>
            {pending ? pendingLabel : submitLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
