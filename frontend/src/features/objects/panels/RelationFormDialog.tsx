/**
 * Creates a relationship to another object, or edits the attributes carried by an existing one.
 *
 * The relationship choices come from the model: which relation types the panel permits, in which
 * direction, and between which object types. Editing is limited to relationship attributes, since
 * changing an endpoint is a delete and a create.
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
  onClose,
  onSaved,
}: {
  model: EngineModel;
  object: ObjectItem;
  choices: RelationChoice[];
  existing?: RelationItem;
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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [dirty, setDirty] = useState(false);
  const [current, setCurrent] = useState<RelationRecord>();
  const [relationVersion, setRelationVersion] = useState(existing?.relation.version ?? 1);
  const choice = choices[choiceIndex];
  const attributes = (choice?.relation.attributeTypeKeys ?? [])
    .map((key) => model.attributeTypes.find((item) => item.key === key))
    .filter((item): item is AttributeTypeDefinition => Boolean(item));

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
      else
        await api.createRelation({
          relationTypeKey: choice.relation.relationTypeKey,
          fromObjectId: choice.direction === "outgoing" ? object.id : candidate!.id,
          toObjectId: choice.direction === "outgoing" ? candidate!.id : object.id,
          attributes: values,
        });
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
      if (
        existing &&
        (isApiError(cause, "version_conflict") || isApiError(cause, "workspace_draft_version_conflict"))
      ) {
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
  if (!choice) return null;
  return (
    <Modal
      title={existing ? choice.label : "Connect an object"}
      eyebrow={existing ? "Edit relationship" : "Create relationship"}
      busy={saving}
      dirty={dirty}
      onClose={onClose}
    >
      <form onSubmit={submit} onChange={() => setDirty(true)}>
        {!existing && (
          <>
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
            <label>
              Object
              <ObjectLookup
                objectTypeKey={choice.otherObjectTypeKey}
                workspaceKey={object.workspaceKey}
                excludeId={object.id}
                value={candidate}
                required
                onChange={setCandidate}
              />
            </label>
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
            {saving ? "Saving…" : existing ? "Save" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
