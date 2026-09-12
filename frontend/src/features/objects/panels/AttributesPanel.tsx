import { useRef, useState } from "react";
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
import { attributeName, fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { Modal } from "@/ui/Modal";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { InlineAttributeEditor } from "./InlineAttributeEditor";
import { useNavigationGuard } from "@/routing/navigationGuard";
import { formatValue } from "@/ui/formatValue";

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
  const { draft, warning } = useWorkspaceData();
  const trigger = useRef<HTMLDivElement | null>(null);
  const [savedField, setSavedField] = useState("");
  const [removed, setRemoved] = useState(false);
  const closeEditor = () => {
    setEditing(undefined);
    requestAnimationFrame(() => trigger.current?.querySelector("button")?.focus());
  };
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
      setSavedField(removing.attribute.key);
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
              <dd>
                {editing?.attribute.key === field ? (
                  <InlineAttributeEditor
                    object={object}
                    {...editing}
                    onClose={closeEditor}
                    onSaved={(saved) => {
                      onObjectChanged(saved);
                      setSavedField(field);
                      closeEditor();
                    }}
                    onConflict={onReload}
                  />
                ) : (
                  <>
                    {attribute
                      ? !stored
                        ? "Not set"
                        : stored.value === null
                          ? "Null"
                          : stored.value === ""
                            ? "Empty text"
                            : formatValue(stored.value)
                      : formatValue(fieldValue(object, field, model))}
                    {savedField === field && (
                      <p role="status" className="inline-save-status">
                        {warning || (draft ? `Saved to draft “${draft.name}”` : "Saved to Live")}
                      </p>
                    )}
                  </>
                )}
                {!readOnly && editable && editing?.attribute.key !== field && (
                  <div className="row-actions">
                    {stored ? (
                      <>
                        <button
                          disabled={!!editing || !!removing || !!warning}
                          onClick={(event) => {
                            trigger.current = event.currentTarget.closest(".attribute-grid > div");
                            setSavedField("");
                            setEditing({ ...editable, stored });
                          }}
                        >
                          Edit
                        </button>
                        {!editable.binding.required && (
                          <button
                            disabled={!!editing || !!removing || !!warning}
                            className="text-danger"
                            onClick={() => {
                              setRemoveError("");
                              setRemoved(false);
                              setRemoving({ ...editable, stored });
                            }}
                          >
                            Remove
                          </button>
                        )}
                      </>
                    ) : (
                      <button
                        disabled={!!editing || !!removing || !!warning}
                        onClick={(event) => {
                          trigger.current = event.currentTarget.closest(".attribute-grid > div");
                          setSavedField("");
                          setEditing({ ...editable });
                        }}
                      >
                        Add value
                      </button>
                    )}
                  </div>
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
