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
import { errorMessage } from "@/api/errors";
import { candidateHint, candidateScope } from "@/model/candidates";
import type { RelationChoice } from "@/model/lookup";
import {
  RelationAttributes,
  RelationConflictNotice,
  relationAttributeTypes,
  relationValuesFromForm,
  useRelationValues,
} from "@/features/objects/relations/RelationAttributes";
import type { EngineModel, ObjectItem, RelationItem } from "@/types";
import { Notice } from "@/ui/Notice";
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
  // Saving an existing relationship's values, and what a version conflict leaves, is the one
  // implementation a matrix cell and a relationships table use too.
  const edit = useRelationValues(existing?.relation, object.workspaceKey);
  const choice = choices[choiceIndex];
  const attributes = relationAttributeTypes(model, choice?.relation);

  const busy = saving || edit.saving;
  const finishNavigation = useNavigationGuard(dirty, busy, onClose);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!choice || (!existing && !candidate)) return;
    const values = relationValuesFromForm(event.currentTarget, attributes);
    if (existing) {
      if (await edit.save(values)) {
        finishNavigation();
        onSaved();
      }
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (replacing) await replaceHeld(candidate!, values);
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
  const failure = error || edit.error;
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
      busy={busy}
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
                candidates={candidateScope(model, choice.relation, choice.direction, object.objectTypeKey)}
                onChange={(item) => {
                  setDirty(true);
                  setCandidate(item);
                }}
              />
              {candidateHint(model, choice.relation, choice.direction) && (
                <p className="admin-hint">{candidateHint(model, choice.relation, choice.direction)}</p>
              )}
            </fieldset>
          </>
        )}
        <RelationAttributes attributes={attributes} relation={existing?.relation} mode="edit" />
        {edit.current && <RelationConflictNotice attributes={attributes} current={edit.current} />}
        {failure && (
          <Notice tone="error" title="The relationship was not saved" focusOnMount>
            {failure}
          </Notice>
        )}
        <div className="dialog-actions">
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={() => (!dirty || window.confirm("Discard your unsaved changes?")) && onClose()}
          >
            Cancel
          </button>
          <button className="primary" disabled={busy || (!existing && !candidate)}>
            {busy ? "Saving…" : existing ? "Save" : replacing ? "Change" : setting ? "Set" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
