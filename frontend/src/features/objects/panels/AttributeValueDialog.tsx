/**
 * Sets or replaces one attribute value on an object.
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
import { formatValue } from "@/ui/formatValue";
import { Modal } from "@/ui/Modal";

export function AttributeValueDialog({
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
  const api = useDataApi();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [conflict, setConflict] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const value = attributeValueFromForm(event.currentTarget, attribute);
      const saved = object.attributes.some((item) => item.attributeTypeKey === attribute.key)
        ? await api.updateAttribute(object.objectTypeKey, object.id, attribute.key, value, object.version)
        : await api.createAttribute(object.objectTypeKey, object.id, attribute.key, value, object.version);
      onSaved(saved);
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "version_conflict") || isApiError(cause, "workspace_draft_version_conflict")) {
        try {
          await onConflict();
          setConflict(true);
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      }
      setSaving(false);
    }
  }
  return (
    <Modal
      title={attribute.name}
      eyebrow={stored ? "Edit attribute" : "Add attribute"}
      size="compact"
      busy={saving}
      dirty={dirty}
      onClose={onClose}
    >
      <form onSubmit={submit} onChange={() => setDirty(true)}>
        <AttributeField attribute={attribute} binding={binding} value={stored?.value} autoFocus />
        {conflict && (
          <Notice title="Current saved value">
            {formatValue(object.attributes.find((item) => item.attributeTypeKey === attribute.key)?.value)} (v
            {object.version}). Your input is preserved. Review before saving again.
          </Notice>
        )}
        {error && (
          <Notice tone="error" title="The value was not saved" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button
            type="button"
            className="secondary"
            disabled={saving}
            onClick={() => (!dirty || window.confirm("Discard your unsaved changes?")) && onClose()}
          >
            Cancel
          </button>
          <button className="primary" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
