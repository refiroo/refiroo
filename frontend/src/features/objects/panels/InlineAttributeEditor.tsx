import { useNavigationGuard } from "@/routing/navigationGuard";
/**
 * Sets or replaces one attribute value on an object, or, given `save`, one of its built-in fields
 * (the name, UA8).
 *
 * The write carries the object version, so a value edited against a stale object is rejected
 * rather than silently overwriting a newer one; on that rejection the caller reloads.
 */

import { useState } from "react";
import type { FormEvent } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import type { AttributeTypeDefinition, ObjectAttributeValue, ObjectItem, ObjectTypeAttributeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Notice } from "@/ui/Notice";
import { InlineEditForm } from "@/ui/EditInPlace";
import { formatValue } from "@/ui/formatValue";

export function InlineAttributeEditor({
  object,
  binding,
  attribute,
  stored,
  save,
  onClose,
  onSaved,
  onConflict,
}: {
  object: ObjectItem;
  binding: ObjectTypeAttributeDefinition;
  attribute: AttributeTypeDefinition;
  stored?: Pick<ObjectAttributeValue, "value">;
  /** Saves a built-in field instead of the attribute routes; `stored` then holds its value. */
  save?: (value: unknown) => Promise<ObjectItem>;
  onClose: () => void;
  onSaved: (object: ObjectItem) => void;
  onConflict: () => Promise<void>;
}) {
  const api = useDataApi();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [nullValue, setNullValue] = useState(stored?.value === null);
  const [reloadFailed, setReloadFailed] = useState(false);
  async function reload() {
    try {
      await onConflict();
      setConflict(true);
      setReloadFailed(false);
    } catch (cause) {
      setError(errorMessage(cause));
      setReloadFailed(true);
    }
  }
  const finishNavigation = useNavigationGuard(dirty, saving, onClose);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const raw = new FormData(event.currentTarget).get(attribute.key);
      const value = nullValue
        ? null
        : ["text", "longText"].includes(attribute.valueType)
          ? String(raw ?? "")
          : attributeValueFromForm(event.currentTarget, attribute);
      if (!nullValue && value === null) throw new Error("Enter a value or explicitly select Set null.");
      const saved = save
        ? await save(value)
        : object.attributes.some((item) => item.attributeTypeKey === attribute.key)
          ? await api.updateAttribute(object.objectTypeKey, object.id, attribute.key, value, object.version)
          : await api.createAttribute(object.objectTypeKey, object.id, attribute.key, value, object.version);
      finishNavigation();
      onSaved(saved);
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")) {
        await reload();
      }
      setSaving(false);
    }
  }
  return (
    <InlineEditForm
      label={`Edit ${attribute.name}`}
      saving={saving}
      onSubmit={submit}
      onClose={onClose}
      onChange={() => setDirty(true)}
      canSave={!reloadFailed}
      extraActions={
        reloadFailed && (
          <button type="button" onClick={reload}>
            Reload current value
          </button>
        )
      }
      notices={
        <>
          {conflict && (
            <Notice title="Current saved value">
              {save
                ? formatValue(stored?.value)
                : object.attributes.some((item) => item.attributeTypeKey === attribute.key)
                  ? formatValue(object.attributes.find((item) => item.attributeTypeKey === attribute.key)?.value)
                  : "Not set"}{" "}
              (v
              {object.version}). Your input is preserved. Review before saving again.
            </Notice>
          )}
          {error && (
            <Notice tone="error" title="The value was not saved" focusOnMount>
              {error}
            </Notice>
          )}
        </>
      }
    >
      <AttributeField
        attribute={attribute}
        binding={nullValue ? { ...binding, readOnly: true, required: false } : binding}
        value={stored?.value}
        autoFocus
      />
      {!binding.required && (
        <label className="checkbox">
          <input type="checkbox" checked={nullValue} onChange={(event) => setNullValue(event.target.checked)} />
          Set null
        </label>
      )}
    </InlineEditForm>
  );
}
