/**
 * Deleting one relationship after a confirmation: a record's relationships panel and a list's
 * relation cell (0.10 A9, D135) use it. The delete claims the relationship's version; when it
 * changed meanwhile, the refusal stays in the dialog and the version is read again for a retry.
 */

import { useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import type { RelationItem } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

export function DeleteRelationDialog({
  relation,
  workspaceKey,
  onCancel,
  onDeleted,
}: {
  relation: RelationItem;
  workspaceKey: string;
  onCancel: () => void;
  onDeleted: () => void;
}) {
  const api = useDataApi();
  const [removing, setRemoving] = useState(relation);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function remove() {
    setPending(true);
    setError("");
    try {
      await api.deleteRelation(removing.relation.id, removing.relation.version);
      onDeleted();
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")) {
        try {
          const fresh = await api.relation(removing.relation.id, workspaceKey);
          setRemoving({ ...removing, relation: fresh });
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      }
      setPending(false);
    }
  }

  return (
    <ConfirmDialog
      title="Delete relationship?"
      confirmLabel="Delete relationship"
      pending={pending}
      error={error}
      onCancel={onCancel}
      onConfirm={remove}
    >
      <p>The connected objects will remain. Only this relationship will be deleted.</p>
    </ConfirmDialog>
  );
}
