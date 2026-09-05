/**
 * Sets or replaces one attribute value on an object.
 *
 * The write carries the object version, so a value edited against a stale object is rejected
 * rather than silently overwriting a newer one; on that rejection the caller reloads.
 */

import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { AttributeTypeDefinition, ObjectAttributeValue, ObjectItem, ObjectTypeAttributeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";

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
      setError(errorMessage(cause));
      if (isApiError(cause, "version_conflict")) {
        try {
          await onConflict();
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
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
