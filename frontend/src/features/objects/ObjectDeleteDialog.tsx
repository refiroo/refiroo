import { useNavigationGuard } from "@/routing/navigationGuard";
import { useCallback, useEffect, useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import type { EngineModel, ObjectDeletionImpact, ObjectItem } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

/** The records named in the dialog before "and N more": the impact lists every one, which may be thousands. */
const NAMED = 8;

const records = (n: number) => `${n} ${n === 1 ? "record" : "records"}`;
const relationships = (n: number) => `${n} ${n === 1 ? "relationship" : "relationships"}`;

/**
 * Deleting a record is one confirmation (0.17 UX1, PP-D40): the dialog reads what the deletion would take
 * (`deletion-impact`, nothing deleted), shows it, and the one danger button deletes exactly that, under the
 * impact's token. Until the impact is shown there is no button to delete with.
 */
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
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [version, setVersion] = useState(object.version);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const finishNavigation = useNavigationGuard(false, pending, onClose);
  const { objectTypeKey, id } = object;

  useEffect(() => {
    let current = true;
    api
      .objectDeletionImpact(objectTypeKey, id)
      .then((read) => current && setImpact(read))
      .catch((cause) => current && setLoadError(errorMessage(cause)));
    return () => {
      current = false;
    };
  }, [api, objectTypeKey, id, attempt]);

  const retry = useCallback(() => {
    setLoadError("");
    setAttempt((value) => value + 1);
  }, []);

  async function confirm() {
    if (!impact) return;
    setPending(true);
    setError("");
    try {
      await api.deleteObject(objectTypeKey, id, version, {
        cascade: true,
        deletionPreviewToken: impact.deletionPreviewToken,
      });
      finishNavigation();
      onDeleted();
    } catch (cause) {
      if (
        isApiError(cause, "DELETION_PREVIEW_CHANGED") ||
        isApiError(cause, "VERSION_CONFLICT") ||
        isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")
      ) {
        // The impact shown is out of date. Show the current one once and ask again; never delete what
        // was not shown.
        try {
          const fresh = await api.object(objectTypeKey, id, object.workspaceKey);
          const read = await api.objectDeletionImpact(objectTypeKey, id);
          setVersion(fresh.version);
          setImpact(read);
          setError(
            "The record changed after this was shown. What deleting it takes is shown again: confirm to delete.",
          );
        } catch (refresh) {
          setError(errorMessage(refresh));
        }
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  const typeName = model.objectTypes.find((type) => type.key === objectTypeKey)?.name ?? "record";
  const title = `Delete ${object.name}?`;
  if (!impact) {
    return (
      <ConfirmDialog
        title={title}
        tone="plain"
        confirmLabel="Retry"
        error={loadError}
        onCancel={onClose}
        onConfirm={loadError ? retry : undefined}
      >
        <p>
          {loadError
            ? "What deleting it would take could not be read, so nothing was deleted."
            : "Checking what deleting it would take…"}
        </p>
      </ConfirmDialog>
    );
  }

  const others = impact.objectCount - 1;
  const further = impact.relationshipCount - impact.ownRelationshipCount;
  const beneath = impact.objectsToDelete.every((item) => item.reason === "child");
  const named = impact.objectsToDelete.slice(0, NAMED);
  return (
    <ConfirmDialog
      title={title}
      confirmLabel={others > 0 ? `Delete ${impact.objectCount} records` : `Delete ${typeName}`}
      pending={pending}
      error={error}
      onCancel={onClose}
      onConfirm={confirm}
    >
      <p>
        {impact.ownRelationshipCount > 0
          ? `Deletes ${object.name} and its ${relationships(impact.ownRelationshipCount)}.`
          : `Deletes ${object.name}.`}{" "}
        {others > 0
          ? `${records(others)} ${beneath ? "under it" : "that depend on it"} ${others === 1 ? "is" : "are"} deleted too.`
          : "Nothing else is deleted."}
        {others > 0 &&
          further > 0 &&
          ` ${relationships(further)} of those records ${further === 1 ? "is" : "are"} removed too.`}
      </p>
      {others > 0 && (
        <ul>
          {named.map((item) => (
            <li key={item.id}>
              {item.name} (
              {model.objectTypes.find((type) => type.key === item.objectTypeKey)?.name ?? item.objectTypeKey})
            </li>
          ))}
          {others > named.length && <li>and {others - named.length} more</li>}
        </ul>
      )}
    </ConfirmDialog>
  );
}
