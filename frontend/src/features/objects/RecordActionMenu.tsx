import { useState } from "react";
import { ActionMenu } from "@/ui/ActionMenu";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { routePath } from "@/routing/routes";
import type { ObjectItem } from "@/types";

/** Row and detail actions share canonical links and the same coherent editing/deletion paths. */
export function RecordActionMenu({
  object,
  readOnly,
  onEdit,
  onDelete,
  label,
  isOpen,
  onOpenChange,
}: {
  object: ObjectItem;
  readOnly: boolean;
  onEdit: () => void;
  onDelete: () => void;
  label?: string;
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  const { changeSet, publication } = useWorkspaceData();
  const [message, setMessage] = useState("");
  async function copyLink() {
    const path = routePath({
      kind: "detail",
      applicationKey: object.applicationKey,
      objectTypeKey: object.objectTypeKey,
      objectId: object.id,
      workspaceKey: object.workspaceKey,
      changeSetId: changeSet?.id,
      publicationId: publication?.id,
    });
    try {
      await navigator.clipboard.writeText(new URL(path, window.location.origin).href);
      setMessage("Record link copied.");
    } catch {
      setMessage("Could not copy the link. Open the record and copy its address from the browser.");
    }
  }
  return (
    <div className="record-action-menu">
      <ActionMenu
        label={label ?? `Actions for ${object.name}`}
        isOpen={isOpen}
        onOpenChange={onOpenChange}
        items={[
          ...(!readOnly ? [{ id: "edit", label: "Edit record", onAction: onEdit }] : []),
          { id: "copy", label: "Copy link", onAction: () => void copyLink() },
          ...(!readOnly ? [{ id: "delete", label: "Delete record", tone: "danger" as const, onAction: onDelete }] : []),
        ]}
      />
      <span className="record-action-feedback" role="status">
        {message}
      </span>
    </div>
  );
}
