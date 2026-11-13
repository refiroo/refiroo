/**
 * The confirmation that deletes a model draft (`DELETE /model-drafts/{id}`), shared by the JSON view
 * and the model editor: each says in `children` what is lost, this owns the call and its refusal.
 */

import { useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

export function DeleteDraftDialog({
  draftId,
  version,
  children,
  onDeleted,
  onCancel,
}: {
  draftId: string;
  version: number;
  children: ReactNode;
  onDeleted: () => void;
  onCancel: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    setPending(true);
    setError("");
    try {
      await api.deleteModelDraft(draftId, version);
      onDeleted();
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }
  return (
    <ConfirmDialog
      title="Delete this draft?"
      confirmLabel="Delete draft"
      pending={pending}
      error={error}
      onCancel={onCancel}
      onConfirm={() => void remove()}
    >
      {children}
    </ConfirmDialog>
  );
}
