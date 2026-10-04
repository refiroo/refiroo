import { useNavigationGuard } from "@/routing/navigationGuard";
import { useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import type { EngineModel, ObjectDeletionImpact, ObjectItem } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

export function ObjectDeleteDialog({
  model,
  object,
  onClose,
  onDeleted,
}: {
  model: EngineModel;
  object: ObjectItem;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const api = useDataApi();
  const [impact, setImpact] = useState<ObjectDeletionImpact>();
  const [version, setVersion] = useState(object.version);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const finishNavigation = useNavigationGuard(false, pending, onClose);
  async function confirm() {
    setPending(true);
    setError("");
    try {
      // A stale preview is discarded only by an explicit retry. Never automatically cascade.
      if (stale) {
        const fresh = await api.object(object.objectTypeKey, object.id, object.workspaceKey);
        setVersion(fresh.version);
        setImpact(undefined);
        setStale(false);
        setError(`Current record: ${fresh.name} (v${fresh.version}). Review and request deletion again.`);
        return;
      }
      await api.deleteObject(
        object.objectTypeKey,
        object.id,
        version,
        impact ? { cascade: true, deletionPreviewToken: impact.deletionPreviewToken } : {},
      );
      finishNavigation();
      onDeleted();
    } catch (cause) {
      if (isApiError(cause, "OBJECT_HAS_DEPENDANTS")) {
        setImpact(cause.details as ObjectDeletionImpact);
      } else {
        setError(errorMessage(cause));
        if (
          isApiError(cause, "CHANGE_SET_VERSION_CONFLICT") ||
          isApiError(cause, "DELETION_PREVIEW_CHANGED") ||
          isApiError(cause, "VERSION_CONFLICT")
        )
          setStale(true);
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <ConfirmDialog
      title={`Delete ${object.name}?`}
      confirmLabel={stale ? "Retry" : impact ? "Confirm deletion" : "Delete"}
      pending={pending}
      error={error}
      onCancel={onClose}
      onConfirm={confirm}
    >
      {impact ? (
        <>
          <p>
            Delete {impact.objectCount} records, including {object.name}, and remove {impact.relationshipCount}{" "}
            relationships.
          </p>
          <ul>
            {impact.objectsToDelete.map((item) => (
              <li key={item.id}>
                {item.name} (
                {model.objectTypes.find((type) => type.key === item.objectTypeKey)?.name ?? item.objectTypeKey})
              </li>
            ))}
          </ul>
          {impact.relationshipsToRemove.length > 0 && (
            <>
              <h3>Relationships to remove</h3>
              <ul>
                {impact.relationshipsToRemove.map((item) => (
                  <li key={item.id}>
                    {model.relationTypes.find((type) => type.key === item.relationTypeKey)?.name ??
                      item.relationTypeKey}{" "}
                    ({item.id})
                  </li>
                ))}
              </ul>
            </>
          )}
          <p>
            {impact.retainedAssociationCount} connections lead to independent records. Those records and their own
            hierarchy will remain.
          </p>
        </>
      ) : (
        <p>
          This permanently deletes the record. If it has dependent records or relationships, their impact will be shown
          before you confirm their deletion.
        </p>
      )}
    </ConfirmDialog>
  );
}
