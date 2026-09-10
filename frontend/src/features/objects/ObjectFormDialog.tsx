import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import type { EngineModel, ObjectItem, ObjectTypeDefinition, ObjectAttributeInput } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { CurrentObjectContent } from "@/features/objects/CurrentObjectContent";
import { ObjectLookup } from "@/ui/ObjectLookup";

export function ObjectFormDialog({
  model,
  applicationKey,
  workspaceKey,
  objectType,
  object,
  parentObjectId,
  parentObjectTypeKey,
  initialRelationObjects = {},
  lockedInitialRelationKeys = [],
  onClose,
  onSaved,
}: {
  model: EngineModel;
  applicationKey: string;
  workspaceKey?: string;
  objectType: ObjectTypeDefinition;
  object?: ObjectItem;
  parentObjectId?: string;
  parentObjectTypeKey?: string;
  initialRelationObjects?: Record<string, ObjectItem>;
  lockedInitialRelationKeys?: string[];
  onClose: () => void;
  onSaved: (item: ObjectItem) => void;
}) {
  const api = useDataApi();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const editedFields = useRef(new Set<string>());
  const editedParent = useRef(false);
  const [dirty, setDirty] = useState(false);
  const [baselineObject, setBaselineObject] = useState(object);
  const [objectVersion, setObjectVersion] = useState(object?.version ?? 1);
  const activeWorkspaceKey = workspaceKey ?? object?.workspaceKey ?? "default";
  const priorWorkspace = useRef(activeWorkspaceKey);
  const initialParentType = parentObjectTypeKey ?? object?.path.at(-2)?.objectTypeKey ?? undefined;
  const [parentTypeKey, setParentTypeKey] = useState(initialParentType);
  const [parentId, setParentId] = useState<string | null>(parentObjectId ?? object?.parentObjectId ?? null);
  const attributeMap = useMemo(
    () => new Map(model.attributeTypes.map((attribute) => [attribute.key, attribute])),
    [model.attributeTypes],
  );
  const bindings = objectType.attributes
    .filter((binding) => binding.ui?.hidden !== true && attributeMap.get(binding.attributeTypeKey)?.ui?.hidden !== true)
    .slice()
    .sort((a, b) => a.order - b.order);
  const parentRelationKeys = new Set(objectType.behavior.parentRelationTypeKeys ?? []);
  const parentTypeKeys = Array.from(
    new Set(
      model.objectTypeRelations
        .filter(
          (relation) => relation.toObjectTypeKey === objectType.key && parentRelationKeys.has(relation.relationTypeKey),
        )
        .map((relation) => relation.fromObjectTypeKey),
    ),
  );
  const parentRequired = objectType.features.rootCreatable !== true;
  const activeParentTypeKey =
    parentTypeKey && parentTypeKeys.includes(parentTypeKey) ? parentTypeKey : parentTypeKeys[0];
  const requiredRelationGroups = useMemo(() => {
    const groups = new Map<string, typeof model.objectTypeRelations>();
    for (const relation of model.objectTypeRelations) {
      if (
        relation.toObjectTypeKey !== objectType.key ||
        !relation.required ||
        parentRelationKeys.has(relation.relationTypeKey)
      )
        continue;
      groups.set(relation.relationTypeKey, [...(groups.get(relation.relationTypeKey) ?? []), relation]);
    }
    return Array.from(groups.entries()).map(([relationTypeKey, relations]) => ({ relationTypeKey, relations }));
  }, [model.objectTypeRelations, objectType.key]);
  const [requiredRelationTypes, setRequiredRelationTypes] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      requiredRelationGroups.map((group) => [group.relationTypeKey, group.relations[0]?.fromObjectTypeKey]),
    ),
  );
  const [requiredRelationObjects, setRequiredRelationObjects] =
    useState<Record<string, ObjectItem | undefined>>(initialRelationObjects);

  useEffect(() => {
    if (priorWorkspace.current === activeWorkspaceKey) return;
    priorWorkspace.current = activeWorkspaceKey;
    setParentId(null);
    setRequiredRelationObjects({});
  }, [activeWorkspaceKey]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const form = event.currentTarget;
      const data = new FormData(form);
      const name = String(data.get("name"));
      if (object) {
        const payload: {
          expectedVersion: number;
          name?: string;
          parentObjectId?: string | null;
          attributes?: ObjectAttributeInput[];
        } = {
          expectedVersion: objectVersion,
        };
        if (editedFields.current.has("name") && name !== baselineObject?.name) payload.name = name;
        if (editedParent.current && parentId !== baselineObject?.parentObjectId) payload.parentObjectId = parentId;
        const attributes = bindings
          .filter((binding) => !binding.readOnly && editedFields.current.has(binding.attributeTypeKey))
          .flatMap((binding) => {
            const definition = attributeMap.get(binding.attributeTypeKey)!;
            const value = attributeValueFromForm(form, definition);
            const stored = baselineObject?.attributes.find((item) => item.attributeTypeKey === definition.key);
            const original = stored?.value;
            return JSON.stringify(value) === JSON.stringify(original)
              ? []
              : [{ attributeTypeKey: definition.key, value }];
          });
        if (attributes.length) payload.attributes = attributes;
        onSaved(await api.updateObject(objectType.key, object.id, payload));
      } else {
        const attributes = bindings
          .filter((binding) => !binding.readOnly)
          .flatMap((binding) => {
            const definition = attributeMap.get(binding.attributeTypeKey)!;
            const value = attributeValueFromForm(form, definition);
            const isUnset = value === null;
            return isUnset && !binding.required ? [] : [{ attributeTypeKey: definition.key, value }];
          });
        const initialRelations = requiredRelationGroups.map((group) => ({
          relationTypeKey: group.relationTypeKey,
          direction: "incoming" as const,
          otherObjectId: requiredRelationObjects[group.relationTypeKey]!.id,
          attributes: {},
        }));
        onSaved(
          await api.createObject(objectType.key, {
            applicationKey,
            workspaceKey: activeWorkspaceKey,
            name,
            parentObjectId: parentId ?? undefined,
            attributes,
            initialRelations,
          }),
        );
      }
    } catch (cause) {
      if (object && (isApiError(cause, "version_conflict") || isApiError(cause, "workspace_draft_version_conflict"))) {
        try {
          const fresh = await api.object(objectType.key, object.id, activeWorkspaceKey);
          setBaselineObject(fresh);
          setObjectVersion(fresh.version);
          setError(
            isApiError(cause, "workspace_draft_version_conflict")
              ? "The draft changed. Current content is loaded; your edits are preserved. Review and save again."
              : "The object changed. Its latest version has been loaded; your edits are preserved. Review and save again.",
          );
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      } else setError(errorMessage(cause));
      setSaving(false);
    }
  }

  return (
    <Modal
      title={object ? object.name : `New ${objectType.name}`}
      eyebrow={object ? "Edit object" : "Create in context"}
      busy={saving}
      dirty={dirty}
      onClose={onClose}
    >
      <form
        onSubmit={submit}
        onChange={(event) => {
          setDirty(true);
          const target = event.target;
          if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)
            editedFields.current.add(target.name);
        }}
      >
        {parentTypeKeys.length > 0 && (
          <label>
            Parent
            {parentTypeKeys.length > 1 && (
              <select
                aria-label="Parent type"
                value={activeParentTypeKey}
                onChange={(event) => {
                  editedParent.current = true;
                  setParentTypeKey(event.target.value);
                  setParentId(null);
                }}
              >
                {parentTypeKeys.map((key) => (
                  <option key={key} value={key}>
                    {model.objectTypes.find((item) => item.key === key)?.name ?? key}
                  </option>
                ))}
              </select>
            )}
            <ObjectLookup
              objectTypeKey={activeParentTypeKey}
              applicationKey={applicationKey}
              workspaceKey={activeWorkspaceKey}
              excludeId={object?.id}
              selectedId={parentId}
              selectedLabel={object?.path.at(-2)?.name}
              required={parentRequired}
              onChange={(item) => {
                editedParent.current = true;
                setParentId(item?.id ?? null);
              }}
            />
          </label>
        )}
        {!object &&
          requiredRelationGroups.map((group) => {
            const definition = model.relationTypes.find((relation) => relation.key === group.relationTypeKey);
            const selectedType = requiredRelationTypes[group.relationTypeKey] ?? group.relations[0]?.fromObjectTypeKey;
            const locked = lockedInitialRelationKeys.includes(group.relationTypeKey);
            return (
              <fieldset key={group.relationTypeKey}>
                <legend>{definition?.reverseName ?? group.relationTypeKey}</legend>
                {locked ? (
                  <p>
                    <strong>{requiredRelationObjects[group.relationTypeKey]?.name}</strong>
                  </p>
                ) : (
                  <>
                    {group.relations.length > 1 && (
                      <label>
                        Object type
                        <select
                          aria-label={`${definition?.reverseName ?? group.relationTypeKey} object type`}
                          value={selectedType}
                          onChange={(event) => {
                            setRequiredRelationTypes((current) => ({
                              ...current,
                              [group.relationTypeKey]: event.target.value,
                            }));
                            setRequiredRelationObjects((current) => ({
                              ...current,
                              [group.relationTypeKey]: undefined,
                            }));
                          }}
                        >
                          {group.relations.map((relation) => (
                            <option key={relation.fromObjectTypeKey} value={relation.fromObjectTypeKey}>
                              {model.objectTypes.find((item) => item.key === relation.fromObjectTypeKey)?.name ??
                                relation.fromObjectTypeKey}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <ObjectLookup
                      objectTypeKey={selectedType}
                      workspaceKey={activeWorkspaceKey}
                      required
                      value={requiredRelationObjects[group.relationTypeKey]}
                      onChange={(item) =>
                        setRequiredRelationObjects((current) => ({ ...current, [group.relationTypeKey]: item }))
                      }
                    />
                  </>
                )}
              </fieldset>
            );
          })}
        <label>
          Name
          <input name="name" required autoFocus defaultValue={object?.name} />
        </label>
        {bindings.map((binding) => (
          <AttributeField
            key={binding.attributeTypeKey}
            binding={binding}
            attribute={attributeMap.get(binding.attributeTypeKey)!}
            value={object?.attributes.find((item) => item.attributeTypeKey === binding.attributeTypeKey)?.value}
          />
        ))}
        {object && baselineObject && baselineObject !== object && (
          <CurrentObjectContent model={model} object={baselineObject} />
        )}
        {error && (
          <Notice tone="error" title="The object was not saved" focusOnMount>
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
          <button
            className="primary"
            disabled={
              saving ||
              (!object && requiredRelationGroups.some((group) => !requiredRelationObjects[group.relationTypeKey]))
            }
          >
            {saving ? "Saving…" : object ? "Save changes" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
