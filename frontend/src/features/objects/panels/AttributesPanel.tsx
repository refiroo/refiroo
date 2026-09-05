import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type {
  AttributeTypeDefinition,
  AttributesPanelDefinition,
  EngineModel,
  ObjectAttributeValue,
  ObjectItem,
  ObjectTypeAttributeDefinition,
} from "@/types";
import { attributeName, fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { AttributeValueDialog } from "./AttributeValueDialog";
import { formatValue } from "@/ui/formatValue";

export function AttributesPanel({
  model,
  object,
  panel,
  onObjectChanged,
  onReload,
  onChanged = () => undefined,
}: {
  model: EngineModel;
  object: ObjectItem;
  panel: AttributesPanelDefinition;
  onObjectChanged: (object: ObjectItem) => void;
  onReload: () => Promise<void>;
  onChanged?: () => void;
}) {
  const objectType = objectTypeFor(model, object.objectTypeKey);
  const bindingMap = new Map((objectType?.attributes ?? []).map((binding) => [binding.attributeTypeKey, binding]));
  const [editing, setEditing] = useState<{
    binding: ObjectTypeAttributeDefinition;
    attribute: AttributeTypeDefinition;
    stored?: ObjectAttributeValue;
  }>();
  const [removing, setRemoving] = useState<{
    binding: ObjectTypeAttributeDefinition;
    attribute: AttributeTypeDefinition;
    stored: ObjectAttributeValue;
  }>();
  const [removeError, setRemoveError] = useState("");
  const [pending, setPending] = useState(false);

  async function remove() {
    if (!removing) return;
    setPending(true);
    setRemoveError("");
    try {
      await api.deleteAttribute(object.objectTypeKey, object.id, removing.attribute.key, object.version);
      await onReload();
      setRemoving(undefined);
      onChanged();
    } catch (cause) {
      setRemoveError(errorMessage(cause));
      await onReload();
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <dl className="attribute-grid">
        {panel.config.fields.map((field) => {
          const binding = bindingMap.get(field);
          const attribute = model.attributeTypes.find((item) => item.key === field);
          if (binding?.ui?.hidden === true || attribute?.ui?.hidden === true) return null;
          const stored = object.attributes.find((item) => item.attributeTypeKey === field);
          // Narrowed once here, so the actions below need no assertions: a field is editable only
          // when the object type binds it and the model still declares the attribute type.
          const editable = binding && attribute && !binding.readOnly ? { binding, attribute } : undefined;
          return (
            <div key={field}>
              <dt>{attributeName(model, field)}</dt>
              <dd>{formatValue(fieldValue(object, field, model))}</dd>
              {editable && (
                <div className="row-actions">
                  {stored ? (
                    <>
                      <button onClick={() => setEditing({ ...editable, stored })}>Edit</button>
                      {!editable.binding.required && (
                        <button className="text-danger" onClick={() => setRemoving({ ...editable, stored })}>
                          Remove
                        </button>
                      )}
                    </>
                  ) : (
                    !editable.binding.required && <button onClick={() => setEditing({ ...editable })}>Add</button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </dl>
      {editing && (
        <AttributeValueDialog
          object={object}
          {...editing}
          onClose={() => setEditing(undefined)}
          onSaved={(saved) => {
            onObjectChanged(saved);
            setEditing(undefined);
          }}
          onConflict={onReload}
        />
      )}
      {removing && (
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
      )}
    </>
  );
}
