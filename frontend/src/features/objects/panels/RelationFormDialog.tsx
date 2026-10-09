import { useNavigationGuard } from "@/routing/navigationGuard";
/**
 * Creates a relationship to another object, edits the attributes carried by an existing one, or
 * changes the one record a record holds of a kind.
 *
 * The relationship choices come from the model: which relation types the panel permits, in which
 * direction, and between which object types. Editing is limited to relationship attributes. Where
 * the record holds at most one of a kind (0.9 K3a, D139), creating it is Set, and Change replaces
 * the one held in one write (the mapping replacement), claiming the record's set as it was read
 * when the dialog saved, and only while the record still holds the relationship the row showed.
 */

import { useState } from "react";
import type { FormEvent } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import type { RelationChoice } from "@/model/lookup";
import type { AttributeTypeDefinition, EngineModel, ObjectItem, RelationItem, RelationRecord } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Notice } from "@/ui/Notice";
import { formatValue } from "@/ui/formatValue";
import { Modal } from "@/ui/Modal";
import { ObjectLookup } from "@/ui/ObjectLookup";

export function RelationFormDialog({
  model,
  object,
  choices,
  existing,
  replacing,
  setting = false,
  onClose,
  onSaved,
}: {
  model: EngineModel;
  object: ObjectItem;
  choices: RelationChoice[];
  existing?: RelationItem;
  /** The relationship Change replaces; `choices` then holds its kind only. */
  replacing?: RelationItem;
  /** Creating a relationship of a kind the record holds one of (Set). */
  setting?: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const api = useDataApi();
  const existingChoice =
    existing &&
    choices.find(
      (choice) =>
        choice.direction === existing.direction &&
        choice.relation.relationTypeKey === existing.relation.relationTypeKey &&
        choice.otherObjectTypeKey === existing.object.objectTypeKey,
    );
  const [choiceIndex, setChoiceIndex] = useState(Math.max(0, existingChoice ? choices.indexOf(existingChoice) : 0));
  const [candidate, setCandidate] = useState<ObjectItem | undefined>(existing?.object);
  const choosing = !existing;
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [current, setCurrent] = useState<RelationRecord>();
  const [relationVersion, setRelationVersion] = useState(existing?.relation.version ?? 1);
  const choice = choices[choiceIndex];
  const attributes = (choice?.relation.attributeTypeKeys ?? [])
    .map((key) => model.attributeTypes.find((item) => item.key === key))
    .filter((item): item is AttributeTypeDefinition => Boolean(item));

  const finishNavigation = useNavigationGuard(dirty, saving, onClose);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!choice || (!existing && !candidate)) return;
    setSaving(true);
    setError("");
    try {
      const values = Object.fromEntries(
        attributes.map((attribute) => [attribute.key, attributeValueFromForm(event.currentTarget, attribute)]),
      );
      if (existing)
        await api.updateRelation(existing.relation.id, { attributes: values, expectedVersion: relationVersion });
      else if (replacing) await replaceHeld(candidate!, values);
      else
        await api.createRelation({
          relationTypeKey: choice.relation.relationTypeKey,
          fromObjectId: choice.direction === "outgoing" ? object.id : candidate!.id,
          toObjectId: choice.direction === "outgoing" ? candidate!.id : object.id,
          attributes: values,
        });
      finishNavigation();
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
      if (existing && (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT"))) {
        try {
          const fresh = await api.relation(existing.relation.id, object.workspaceKey);
          setRelationVersion(fresh.version);
          setCurrent(fresh);
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      }
      setSaving(false);
    }
  }
  async function replaceHeld(target: ObjectItem, values: Record<string, unknown>) {
    const { relationTypeKey, fromObjectTypeKey, toObjectTypeKey } = choice.relation;
    const direction = replacing!.direction;
    const page = await api.relations(object.id, {
      workspaceKey: object.workspaceKey,
      direction,
      relationTypeKey,
      pageSize: 2,
    });
    const set = page.relationSets?.find(
      (item) =>
        item.direction === direction &&
        item.relationTypeKey === relationTypeKey &&
        item.fromObjectTypeKey === fromObjectTypeKey &&
        item.toObjectTypeKey === toObjectTypeKey,
    );
    const [held] = page.items;
    if (
      !set ||
      page.items.length !== 1 ||
      held.relation.id !== replacing!.relation.id ||
      held.relation.version !== replacing!.relation.version
    )
      throw new Error("This relationship changed after the list was read. Close the dialog to see it as it is now.");
    await api.replaceMapping(object.workspaceKey, {
      relationTypeKey,
      fromObjectTypeKey,
      toObjectTypeKey,
      direction,
      sourceObjectId: object.id,
      targetObjectId: target.id,
      expectedMappingVersion: set.relationSetVersion,
      ...(attributes.length ? { attributes: values } : {}),
    });
  }

  if (!choice) return null;
  return (
    <Modal
      title={existing || replacing ? choice.label : setting ? `Set ${choice.label.toLowerCase()}` : "Connect an object"}
      eyebrow={
        existing
          ? "Edit relationship"
          : replacing
            ? "Change relationship"
            : setting
              ? "Set relationship"
              : "Create relationship"
      }
      busy={saving}
      dirty={dirty}
      onClose={onClose}
    >
      <form onSubmit={submit} onChange={() => setDirty(true)}>
        {replacing && (
          <p>
            Now: <strong>{replacing.object.name}</strong>. Choose the record that replaces it.
          </p>
        )}
        {choosing && (
          <>
            {!replacing && (
              <label>
                Relationship
                <select
                  value={choiceIndex}
                  onChange={(event) => {
                    setChoiceIndex(Number(event.target.value));
                    setCandidate(undefined);
                  }}
                >
                  {choices.map((item, index) => (
                    <option
                      key={`${item.direction}:${item.relation.relationTypeKey}:${item.otherObjectTypeKey}`}
                      value={index}
                    >
                      {item.label} ({item.direction})
                    </option>
                  ))}
                </select>
              </label>
            )}
            <fieldset className="lookup-field">
              <legend>Object</legend>
              <ObjectLookup
                label="Object"
                objectTypeKey={choice.otherObjectTypeKey}
                workspaceKey={object.workspaceKey}
                excludeId={replacing?.object.id ?? object.id}
                value={candidate}
                required
                onChange={(item) => {
                  setDirty(true);
                  setCandidate(item);
                }}
              />
            </fieldset>
          </>
        )}
        {attributes.map((attribute) => (
          <AttributeField
            key={attribute.key}
            attribute={attribute}
            value={existing?.relation.attributes[attribute.key]}
          />
        ))}
        {current && (
          <Notice title={`Current saved relationship (v${current.version})`}>
            <p>Your input is preserved. Review before saving again.</p>
            <dl>
              {attributes.map((attribute) => (
                <div key={attribute.key}>
                  <dt>{attribute.name}</dt>
                  <dd>{formatValue(current.attributes[attribute.key])}</dd>
                </div>
              ))}
            </dl>
          </Notice>
        )}
        {error && (
          <Notice tone="error" title="The relationship was not saved" focusOnMount>
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
          <button className="primary" disabled={saving || (!existing && !candidate)}>
            {saving ? "Saving…" : existing ? "Save" : replacing ? "Change" : setting ? "Set" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
