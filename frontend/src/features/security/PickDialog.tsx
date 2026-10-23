import { useState } from "react";
import { errorMessage } from "@/api/errors";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";

/** Pick one person or group by name, then act on it: a membership on both pages. */
export function PickDialog({
  title,
  label,
  kinds,
  confirmLabel,
  onClose,
  onPicked,
}: {
  title: string;
  label: string;
  kinds: readonly ("user" | "group")[];
  confirmLabel: string;
  onClose: () => void;
  onPicked: (picked: PickedPrincipal) => Promise<void>;
}) {
  const [picked, setPicked] = useState<PickedPrincipal>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <Modal title={title} eyebrow="Security" size="compact" busy={pending} onClose={onClose}>
      <form
        className="grant-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!picked) return;
          setPending(true);
          setError("");
          onPicked(picked).catch((cause) => {
            setError(errorMessage(cause));
            setPending(false);
          });
        }}
      >
        <PrincipalPicker label={label} kinds={kinds} onPick={setPicked} />
        {error && (
          <Notice tone="error" title="Not added">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !picked}>
            {pending ? "Adding…" : confirmLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
