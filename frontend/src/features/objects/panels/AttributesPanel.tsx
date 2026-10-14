import { useState } from "react";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import type { AttributeTypeDefinition, AttributesPanelDefinition, EngineModel, ObjectItem } from "@/types";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { RemoveValueDialog } from "@/features/objects/RemoveValueDialog";
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
  const { changeSet, warning } = useWorkspaceData();
  const [removedField, setRemovedField] = useState("");
  const objectType = objectTypeFor(model, object.objectTypeKey);
  const bindingMap = new Map((objectType?.attributes ?? []).map((binding) => [binding.attributeTypeKey, binding]));
  const [editingField, setEditingField] = useState<string>();
  const [removing, setRemoving] = useState<AttributeTypeDefinition>();

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
                      onClick={() => setRemoving(editable.attribute)}
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
      {removing && (
        <RemoveValueDialog
          object={object}
          attribute={removing}
          reload={onReload}
          onChanged={onChanged}
          onCancel={() => setRemoving(undefined)}
          onRemoved={() => {
            setRemoving(undefined);
            setRemovedField(removing.key);
          }}
        />
      )}
    </>
  );
}
