import { useState } from "react";
import { ActionMenu } from "@/ui/ActionMenu";
import { useRecordWrites, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { routePath } from "@/routing/routes";
import type { ObjectItem } from "@/types";
import { copyText } from "@/lib/copyText";

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
  // A record whose type the person may not write offers no edit or delete (0.12 Z5, D329).
  const writes = useRecordWrites();
  const writable = !readOnly && writes.permits(object.applicationKey, object.objectTypeKey);
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
    setMessage(
      (await copyText(new URL(path, window.location.origin).href))
        ? "Record link copied."
        : "Could not copy the link. Open the record and copy its address from the browser.",
    );
  }
  async function copyId() {
    setMessage(
      (await copyText(object.id))
        ? "Record ID copied."
        : "Could not copy the ID. Open Details on the record and select it.",
    );
  }
  return (
    <div className="record-action-menu">
      <ActionMenu
        label={label ?? `Actions for ${object.name}`}
        isOpen={isOpen}
        onOpenChange={onOpenChange}
        items={[
          ...(writable ? [{ id: "edit", label: "Edit record", onAction: onEdit }] : []),
          { id: "copy-id", label: "Copy ID", onAction: () => void copyId() },
          { id: "copy", label: "Copy link", onAction: () => void copyLink() },
          ...(writable ? [{ id: "delete", label: "Delete record", tone: "danger" as const, onAction: onDelete }] : []),
        ]}
      />
      <span className="record-action-feedback" role="status">
        {message}
      </span>
    </div>
  );
}
