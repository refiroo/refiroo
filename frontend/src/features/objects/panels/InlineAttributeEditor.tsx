import { useNavigationGuard } from "@/routing/navigationGuard";
/**
 * Sets or replaces one attribute value on an object, or, given `save`, one of its built-in fields
 * (the name, UA8).
 *
 * The value is its control and leaving it saves (`ui/EditInPlace`'s `InlineEditForm`, 0.17 UX2): a changed
 * value is written and told "‹Field› saved" with Undo; an optional field left empty is the value removed,
 * told "‹Field› removed" with Undo as the remove icon tells it; a required one left empty is refused under
 * the field.
 *
 * The write carries the object version, so a value edited against a stale object is rejected
 * rather than silently overwriting a newer one; on that rejection the caller reloads.
 */

import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import type { AttributeTypeDefinition, ObjectAttributeValue, ObjectItem, ObjectTypeAttributeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Notice } from "@/ui/Notice";
import { useOptionalToast } from "@/ui/Toast";
import { InlineEditForm } from "@/ui/EditInPlace";
import { UNDO_REFUSED } from "@/features/objects/undoText";
import { useRemovals } from "@/features/objects/useRemovals";
import { formatValue } from "@/ui/formatValue";

/** What the control holds, as the attribute's type; `undefined` where it is empty. A value it cannot read is thrown in words. */
function valueOf(form: HTMLFormElement, attribute: AttributeTypeDefinition): unknown {
  const input = form.elements.namedItem(attribute.key) as HTMLInputElement | HTMLTextAreaElement | null;
  if (attribute.valueType === "boolean") return attributeValueFromForm(form, attribute);
  if (input?.validity?.badInput)
    throw new Error(
      attribute.valueType === "integer" || attribute.valueType === "decimal" ? "Enter a number." : "Enter a full date.",
    );
  if (!input || input.value === "") return undefined;
  if (attribute.valueType === "text" || attribute.valueType === "longText") return input.value;
  try {
    return attributeValueFromForm(form, attribute);
  } catch {
    throw new Error("This is not valid JSON.");
  }
}

/**
 * One write at a time per record. Leaving a field saves it, so the next field of the same record can be saved
 * while the first is still on its way: it waits for that one and writes against the version it made, instead of
 * being refused as stale.
 */
const writes = new Map<string, Promise<number | undefined>>();
function takeTurn(id: string, version: number) {
  const earlier = writes.get(id);
  let end: (made?: number) => void = () => {};
  const mine = new Promise<number | undefined>((resolve) => {
    end = resolve;
  });
  writes.set(id, mine);
  return {
    version: (earlier ?? Promise.resolve(undefined)).then((made) => Math.max(version, made ?? 0)),
    end: (made?: number) => {
      if (writes.get(id) === mine) writes.delete(id);
      end(made);
    },
  };
}

export function InlineAttributeEditor({
  object,
  binding,
  attribute,
  stored,
  save,
  onClose,
  onSaved,
  onConflict,
  describeError,
}: {
  object: ObjectItem;
  binding: ObjectTypeAttributeDefinition;
  attribute: AttributeTypeDefinition;
  stored?: Pick<ObjectAttributeValue, "value">;
  /** Saves a built-in field instead of the attribute routes; `stored` then holds its value. */
  save?: (value: unknown, version: number) => Promise<ObjectItem>;
  onClose: () => void;
  /** The record as saved. It may come after the field was closed by opening another: close only this field. */
  onSaved: (object: ObjectItem) => void;
  onConflict: () => Promise<void>;
  /** Words a refusal in the caller's terms, with an action beside it; none leaves the API's message. */
  describeError?: (cause: unknown) => { message: string; action?: ReactNode } | undefined;
}) {
  const api = useDataApi();
  const toast = useOptionalToast();
  const { clearValue } = useRemovals();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [errorAction, setErrorAction] = useState<ReactNode>();
  const [dirty, setDirty] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [reloadFailed, setReloadFailed] = useState(false);
  const shown = useRef(true);
  useEffect(() => {
    shown.current = true;
    return () => {
      shown.current = false;
    };
  }, []);
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
  // Leaving the field saves it, so only an input that is typed and not yet left, or was refused, is unsaved; a
  // save under way does not hold the person on the page (its refusal is then told in a toast).
  const finishNavigation = useNavigationGuard(dirty, false, onClose);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setSaving(true);
    setDirty(false);
    setError("");
    setErrorAction(undefined);
    let turn: ReturnType<typeof takeTurn> | undefined;
    let made: number | undefined;
    try {
      const value = valueOf(form, attribute);
      const exists = !save && object.attributes.some((item) => item.attributeTypeKey === attribute.key);
      if (value === undefined) {
        if (binding.required) throw new Error(`${attribute.name} needs a value.`);
        if (!exists) {
          onClose();
          return;
        }
        // An optional field left empty is the value removed, told as the remove icon tells it.
        turn = takeTurn(object.id, object.version);
        await clearValue({ ...object, version: await turn.version }, attribute, async () => {
          const fresh = await api.object(object.objectTypeKey, object.id, object.workspaceKey);
          made = fresh.version;
          onSaved(fresh);
        });
        finishNavigation();
        return;
      }
      turn = takeTurn(object.id, object.version);
      const version = await turn.version;
      const saved = save
        ? await save(value, version)
        : exists
          ? await api.updateAttribute(object.objectTypeKey, object.id, attribute.key, value, version)
          : await api.createAttribute(object.objectTypeKey, object.id, attribute.key, value, version);
      made = saved.version;
      finishNavigation();
      onSaved(saved);
      // A saved change offers Undo (0.17 UX1, PP-D40): the previous value goes back against the version this
      // save made: an attribute's through its own route, the record's name through the record.
      const previous = !save && object.attributes.find((item) => item.attributeTypeKey === attribute.key);
      const previousName = save && attribute.key === "name" && typeof stored?.value === "string" ? stored.value : null;
      const undo = previous
        ? () => api.updateAttribute(object.objectTypeKey, object.id, attribute.key, previous.value, saved.version)
        : previousName !== null
          ? () =>
              api.updateObject(object.objectTypeKey, object.id, { name: previousName, expectedVersion: saved.version })
          : !save
            ? // A value set for the first time goes back to not set.
              () =>
                api
                  .deleteAttribute(object.objectTypeKey, object.id, attribute.key, saved.version)
                  .then(() => api.object(object.objectTypeKey, object.id, object.workspaceKey))
            : undefined;
      toast(`${attribute.name} saved`, {
        actions: undo
          ? [{ label: "Undo", onPress: () => void undo().then(onSaved, () => toast(UNDO_REFUSED, { tone: "info" })) }]
          : [],
      });
    } catch (cause) {
      const described = describeError?.(cause);
      const message = described?.message ?? errorMessage(cause);
      if (!shown.current) {
        // The field was left for another page or another field while it saved: the reason has no field to stand under.
        toast(`${attribute.name} was not saved: ${message}`, { tone: "info" });
        return;
      }
      setError(message);
      setErrorAction(described?.action);
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")) {
        await reload();
      }
      setDirty(true);
      setSaving(false);
    } finally {
      turn?.end(made);
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
            <Notice tone="error" title="The value was not saved">
              {error}
              {errorAction}
            </Notice>
          )}
        </>
      }
    >
      <AttributeField attribute={attribute} binding={binding} value={stored?.value} autoFocus />
    </InlineEditForm>
  );
}
