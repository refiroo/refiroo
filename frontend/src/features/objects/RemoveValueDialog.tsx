/**
 * Removing an optional value of a record, after a confirmation (UA4; A9, D134): the details panel
 * and a list's cell use it. The delete claims the record's version; afterwards the caller reloads.
 * A removal whose reload fails stays open as "refresh needed" until a reload succeeds, so nothing
 * is edited against a record that is no longer as shown.
 */

import { useState } from "react";
import { errorMessage } from "@/api/errors";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useNavigationGuard } from "@/routing/navigationGuard";
import type { AttributeTypeDefinition, ObjectItem } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Modal } from "@/ui/Modal";

export function RemoveValueDialog({
  object,
  attribute,
  reload,
  onChanged,
  onCancel,
  onRemoved,
}: {
  object: ObjectItem;
  attribute: AttributeTypeDefinition;
  /** Reads the record (or the list) again after the removal. */
  reload: () => Promise<void>;
  /** The removal was written, before the reload. */
  onChanged?: () => void;
  onCancel: () => void;
  /** Removed and reloaded. */
  onRemoved: () => void;
}) {
  const api = useDataApi();
  const [removed, setRemoved] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useNavigationGuard(false, pending, onCancel);
  async function remove() {
    setPending(true);
    setError("");
    let committed = removed;
    try {
      if (!removed) {
        await api.deleteAttribute(object.objectTypeKey, object.id, attribute.key, object.version);
        committed = true;
        setRemoved(true);
        onChanged?.();
      }
      await reload();
      onRemoved();
    } catch (cause) {
      setError(errorMessage(cause));
      try {
        if (!committed) await reload();
      } catch (reloadCause) {
        setError(errorMessage(reloadCause));
      }
      setPending(false);
    }
  }

  if (removed)
    return (
      <Modal title="Value removed; refresh needed" showClose={false} busy onClose={() => undefined}>
        <p role="status">The value was removed. Refresh before making another change.</p>
        {error && <p role="alert">{error}</p>}
        <button disabled={pending} onClick={remove}>
          {pending ? "Refreshing…" : "Retry refresh"}
        </button>
      </Modal>
    );
  return (
    <ConfirmDialog
      title={`Remove ${attribute.name}?`}
      confirmLabel="Remove value"
      pending={pending}
      error={error}
      onCancel={onCancel}
      onConfirm={remove}
    >
      <p>The optional value will become unset. This does not delete the object.</p>
    </ConfirmDialog>
  );
}
