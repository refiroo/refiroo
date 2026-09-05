import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type {
  AttributeTypeDefinition,
  AttributesPanelDefinition,
  EngineModel,
  ObjectAttributeValue,
  ObjectItem,
  ObjectTypeAttributeDefinition,
} from "../types";
import { attributeName, fieldValue, objectTypeFor } from "../utils/model";
import { AttributeField, attributeValueFromForm } from "./AttributeField";
import { ConfirmDialog } from "./ConfirmDialog";
import { formatValue } from "./ObjectTable";

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
  const objectType = objectTypeFor(model, object.objectTypeKey)!;
  const bindingMap = new Map(objectType.attributes.map((binding) => [binding.attributeTypeKey, binding]));
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
      setRemoveError(cause instanceof Error ? cause.message : String(cause));
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
          const editable = Boolean(binding && attribute && !binding.readOnly);
          return (
            <div key={field}>
              <dt>{attributeName(model, field)}</dt>
              <dd>{formatValue(fieldValue(object, field, model))}</dd>
              {editable && (
                <div className="row-actions">
                  {stored ? (
                    <>
                      <button onClick={() => setEditing({ binding: binding!, attribute: attribute!, stored })}>
                        Edit
                      </button>
                      {!binding!.required && (
                        <button
                          className="text-danger"
                          onClick={() => setRemoving({ binding: binding!, attribute: attribute!, stored })}
                        >
                          Remove
                        </button>
                      )}
                    </>
                  ) : (
                    !binding!.required && (
                      <button onClick={() => setEditing({ binding: binding!, attribute: attribute! })}>Add</button>
                    )
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

function AttributeValueDialog({
  object,
  binding,
  attribute,
  stored,
  onClose,
  onSaved,
  onConflict,
}: {
  object: ObjectItem;
  binding: ObjectTypeAttributeDefinition;
  attribute: AttributeTypeDefinition;
  stored?: ObjectAttributeValue;
  onClose: () => void;
  onSaved: (object: ObjectItem) => void;
  onConflict: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const titleId = useMemo(() => `attribute-${attribute.key}-title`, [attribute.key]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const value = attributeValueFromForm(event.currentTarget, attribute);
      const saved = stored
        ? await api.updateAttribute(object.objectTypeKey, object.id, attribute.key, value, object.version)
        : await api.createAttribute(object.objectTypeKey, object.id, attribute.key, value, object.version);
      onSaved(saved);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      if ((cause as { code?: string }).code === "version_conflict") {
        try {
          await onConflict();
        } catch (reloadCause) {
          setError(reloadCause instanceof Error ? reloadCause.message : String(reloadCause));
        }
      }
      setSaving(false);
    }
  }
  return (
    <div className="dialog-backdrop" onMouseDown={() => !saving && onClose()}>
      <div
        className="dialog compact-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <div>
            <p className="eyebrow">{stored ? "Edit attribute" : "Add attribute"}</p>
            <h2 id={titleId}>{attribute.name}</h2>
          </div>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <AttributeField attribute={attribute} binding={binding} value={stored?.value} autoFocus />
          {error && <div className="notice error-notice">{error}</div>}
          <div className="dialog-actions">
            <button type="button" className="secondary" onClick={onClose}>
              Cancel
            </button>
            <button className="primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
