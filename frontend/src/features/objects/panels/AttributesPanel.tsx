import { useState } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage } from "@/api/errors";
import type {
  AttributeTypeDefinition,
  AttributesPanelDefinition,
  EngineModel,
  ObjectAttributeValue,
  ObjectItem,
  ObjectTypeAttributeDefinition,
} from "@/types";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { Modal } from "@/ui/Modal";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { useNavigationGuard } from "@/routing/navigationGuard";
import { IconButton } from "@/ui/IconButton";
import { EditableField, fieldEditing } from "@/features/objects/EditableField";
import { readEditHint } from "@/lib/editHint";

export function AttributesPanel({
  model,
  object,
  panel,
  onObjectChanged,
  onReload,
  onChanged = () => undefined,
  readOnly = false,
}: {
  model: EngineModel;
  object: ObjectItem;
  panel: AttributesPanelDefinition;
  onObjectChanged: (object: ObjectItem) => void;
  onReload: () => Promise<void>;
  onChanged?: () => void;
  readOnly?: boolean;
}) {
  const api = useDataApi();
  const { changeSet, warning } = useWorkspaceData();
  const [removedField, setRemovedField] = useState("");
  const [removed, setRemoved] = useState(false);
  const objectType = objectTypeFor(model, object.objectTypeKey);
  const bindingMap = new Map((objectType?.attributes ?? []).map((binding) => [binding.attributeTypeKey, binding]));
  const [editingField, setEditingField] = useState<string>();
  const [removing, setRemoving] = useState<{
    binding: ObjectTypeAttributeDefinition;
    attribute: AttributeTypeDefinition;
    stored: ObjectAttributeValue;
  }>();
  const [removeError, setRemoveError] = useState("");
  const [pending, setPending] = useState(false);

  useNavigationGuard(false, pending, () => setRemoving(undefined));
  async function remove() {
    if (!removing) return;
    setPending(true);
    setRemoveError("");
    let committed = removed;
    try {
      if (!removed) {
        await api.deleteAttribute(object.objectTypeKey, object.id, removing.attribute.key, object.version);
        committed = true;
        setRemoved(true);
        onChanged();
      }
      await onReload();
      setRemoving(undefined);
      setRemovedField(removing.attribute.key);
      setRemoved(false);
    } catch (cause) {
      setRemoveError(errorMessage(cause));
      try {
        if (!committed) await onReload();
      } catch (reloadCause) {
        setRemoveError(errorMessage(reloadCause));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <dl className="attribute-grid" data-edit-hint={readEditHint()}>
        {panel.config.fields.map((field) => {
          const binding = bindingMap.get(field);
          const attribute = model.attributeTypes.find((item) => item.key === field);
          if (binding?.ui?.hidden === true || attribute?.ui?.hidden === true) return null;
          const editable = fieldEditing(model, object, field, readOnly);
          const stored = editable?.attributeValue;
          return (
            <div key={field} className={editingField === field ? "attribute-row editing" : "attribute-row"}>
              <dt>{attributeName(model, field)}</dt>
              <dd>
                <EditableField
                  model={model}
                  object={object}
                  field={field}
                  layout="row"
                  readOnly={readOnly}
                  editing={editingField === field}
                  disabled={!!editingField || !!removing}
                  onEdit={() => {
                    setRemovedField("");
                    setEditingField(field);
                  }}
                  onClose={() => setEditingField(undefined)}
                  onSaved={(saved) => {
                    onObjectChanged(saved);
                    setEditingField(undefined);
                  }}
                  onConflict={onReload}
                />
                {editingField !== field && editable && stored && !editable.binding.required && (
                  <div className="row-actions">
                    <IconButton
                      icon="trash"
                      label={`Remove ${attributeName(model, field)}`}
                      tone="danger"
                      quiet
                      className="attribute-remove"
                      disabled={!!editingField || !!removing || !!warning}
                      onClick={() => {
                        setRemoveError("");
                        setRemoved(false);
                        setRemoving({ binding: editable.binding, attribute: editable.attribute, stored });
                      }}
                    />
                  </div>
                )}
                {removedField === field && (
                  <p role="status" className="inline-save-status">
                    {warning || (changeSet ? `Saved to change set “${changeSet.name}”` : "Saved to Live")}
                  </p>
                )}
              </dd>
            </div>
          );
        })}
      </dl>
      {removing && removed ? (
        <Modal title="Value removed; refresh needed" showClose={false} busy onClose={() => undefined}>
          <p role="status">The value was removed. Refresh before making another change.</p>
          {removeError && <p role="alert">{removeError}</p>}
          <button disabled={pending} onClick={remove}>
            {pending ? "Refreshing…" : "Retry refresh"}
          </button>
        </Modal>
      ) : (
        removing && (
          <ConfirmDialog
            title={`Remove ${removing.attribute.name}?`}
            confirmLabel="Remove value"
            pending={pending}
            error={removeError}
            onCancel={() => setRemoving(undefined)}
            onConfirm={remove}
          >
            <p>The optional value will become unset. This does not delete the object.</p>
          </ConfirmDialog>
        )
      )}
    </>
  );
}
