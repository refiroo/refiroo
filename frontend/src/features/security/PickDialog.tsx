import { useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import { CancelButton, Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";

/** Pick one person or group by name, then act on it: a membership on both pages. */
export function PickDialog({
  title,
  label,
  kinds,
  exclude,
  preview,
  confirmLabel,
  pendingLabel = "Adding…",
  errorTitle = "Not added",
  onClose,
  onPicked,
}: {
  title: string;
  label: string;
  kinds: readonly ("user" | "group")[];
  /** A person or group not offered: the one a link moves from. */
  exclude?: string;
  /** A sentence under the picker once one is picked, saying what the action will do. */
  preview?: (picked: PickedPrincipal) => ReactNode;
  /** The action's button; a function reads the pick (empty until one is made). */
  confirmLabel: string | ((picked?: PickedPrincipal) => string);
  pendingLabel?: string;
  errorTitle?: string;
  onClose: () => void;
  onPicked: (picked: PickedPrincipal) => Promise<void>;
}) {
  const [picked, setPicked] = useState<PickedPrincipal>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <Modal title={title} eyebrow="People and access" size="compact" busy={pending} onClose={onClose}>
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
        <PrincipalPicker label={label} kinds={kinds} exclude={exclude} onPick={setPicked} />
        {picked && preview && <p>{preview(picked)}</p>}
        {error && (
          <Notice tone="error" title={errorTitle}>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <CancelButton disabled={pending} />
          <button className="primary" disabled={pending || !picked}>
            {pending ? pendingLabel : typeof confirmLabel === "function" ? confirmLabel(picked) : confirmLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}
