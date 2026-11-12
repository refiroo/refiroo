import { useState } from "react";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import type { AttributesPanelDefinition, EngineModel, ObjectItem } from "@/types";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { useRemovals } from "@/features/objects/useRemovals";
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
  const { warning } = useWorkspaceData();
  const { removeValue } = useRemovals();
  const objectType = objectTypeFor(model, object.objectTypeKey);
  const bindingMap = new Map((objectType?.attributes ?? []).map((binding) => [binding.attributeTypeKey, binding]));
  const [editingField, setEditingField] = useState<string>();

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
                  onEdit={() => {
                    setEditingField(field);
                  }}
                  onClose={() => setEditingField((open) => (open === field ? undefined : open))}
                  onSaved={(saved) => {
                    // The save of a field left for another comes after that one opened: only this one closes.
                    onObjectChanged(saved);
                    setEditingField((open) => (open === field ? undefined : open));
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
                      disabled={!!warning}
                      onClick={() =>
                        void removeValue(object, editable.attribute, async () => {
                          onChanged();
                          await onReload();
                        })
                      }
                    />
                  </div>
                )}
              </dd>
            </div>
          );
        })}
      </dl>
    </>
  );
}
