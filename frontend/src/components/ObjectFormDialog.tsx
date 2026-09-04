import { FormEvent, useMemo, useState } from "react";
import { api } from "../api/client";
import type { EngineModel, ObjectItem, ObjectTypeDefinition } from "../types";
import { AttributeField, attributeValueFromForm } from "./AttributeField";
import { ObjectLookup } from "./ObjectLookup";

export function ObjectFormDialog({ model, applicationKey, objectType, object, parentObjectId, parentObjectTypeKey, initialRelationObjects = {}, lockedInitialRelationKeys = [], onClose, onSaved }: {
  model: EngineModel; applicationKey: string; objectType: ObjectTypeDefinition; object?: ObjectItem;
  parentObjectId?: string; parentObjectTypeKey?: string; initialRelationObjects?: Record<string, ObjectItem>;
  lockedInitialRelationKeys?: string[]; onClose: () => void; onSaved: (item: ObjectItem) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const initialParentType = parentObjectTypeKey ?? object?.path.at(-2)?.objectTypeKey ?? undefined;
  const [parentTypeKey, setParentTypeKey] = useState(initialParentType);
  const [parentId, setParentId] = useState<string | null>(parentObjectId ?? object?.parentObjectId ?? null);
  const attributeMap = useMemo(() => new Map(model.attributeTypes.map((attribute) => [attribute.key, attribute])), [model.attributeTypes]);
  const bindings = objectType.attributes.filter((binding) => binding.ui?.hidden !== true && attributeMap.get(binding.attributeTypeKey)?.ui?.hidden !== true).slice().sort((a, b) => a.order - b.order);
  const parentRelationKeys = new Set(objectType.behavior.parentRelationTypeKeys ?? []);
  const parentTypeKeys = Array.from(new Set(model.objectTypeRelations.filter((relation) => relation.toObjectTypeKey === objectType.key && parentRelationKeys.has(relation.relationTypeKey)).map((relation) => relation.fromObjectTypeKey)));
  const parentRequired = objectType.features.rootCreatable !== true;
  const activeParentTypeKey = parentTypeKey && parentTypeKeys.includes(parentTypeKey) ? parentTypeKey : parentTypeKeys[0];
  const requiredRelationGroups = useMemo(() => {
    const groups = new Map<string, typeof model.objectTypeRelations>();
    for (const relation of model.objectTypeRelations) {
      if (
        relation.toObjectTypeKey !== objectType.key
        || !relation.required
        || parentRelationKeys.has(relation.relationTypeKey)
      ) continue;
      groups.set(relation.relationTypeKey, [...(groups.get(relation.relationTypeKey) ?? []), relation]);
    }
    return Array.from(groups.entries()).map(([relationTypeKey, relations]) => ({ relationTypeKey, relations }));
  }, [model.objectTypeRelations, objectType.key]);
  const [requiredRelationTypes, setRequiredRelationTypes] = useState<Record<string, string>>(() =>
    Object.fromEntries(requiredRelationGroups.map((group) => [group.relationTypeKey, group.relations[0]?.fromObjectTypeKey])),
  );
  const [requiredRelationObjects, setRequiredRelationObjects] = useState<Record<string, ObjectItem | undefined>>(initialRelationObjects);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError("");
    try {
      const form = event.currentTarget;
      const data = new FormData(form);
      const name = String(data.get("name"));
      if (object) {
        const payload: { expectedVersion: number; name?: string; state?: string; parentObjectId?: string | null } = { expectedVersion: object.version };
        const state = String(data.get("state"));
        if (name !== object.name) payload.name = name;
        if (state !== object.state) payload.state = state;
        if (parentId !== object.parentObjectId) payload.parentObjectId = parentId;
        onSaved(await api.updateObject(objectType.key, object.id, payload));
      } else {
        const attributes = bindings.filter((binding) => !binding.readOnly).flatMap((binding) => {
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
        onSaved(await api.createObject(objectType.key, { applicationKey, name, parentObjectId: parentId ?? undefined, attributes, initialRelations }));
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); setSaving(false); }
  }

  return <div className="dialog-backdrop" onMouseDown={() => !saving && onClose()}>
    <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="object-form-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="dialog-header"><div><p className="eyebrow">{object ? "Edit object" : "Create in context"}</p><h2 id="object-form-title">{object ? object.name : `New ${objectType.name}`}</h2></div><button className="close" type="button" disabled={saving} onClick={onClose} aria-label="Close">×</button></div>
      <form onSubmit={submit}>
        {parentTypeKeys.length > 0 && <label>Parent
          {parentTypeKeys.length > 1 && <select aria-label="Parent type" value={activeParentTypeKey} onChange={(event) => { setParentTypeKey(event.target.value); setParentId(null); }}>{parentTypeKeys.map((key) => <option key={key} value={key}>{model.objectTypes.find((item) => item.key === key)?.name ?? key}</option>)}</select>}
          <ObjectLookup objectTypeKey={activeParentTypeKey} applicationKey={applicationKey} workspaceKey={object?.workspaceKey} excludeId={object?.id} selectedId={parentId} selectedLabel={object?.path.at(-2)?.name} required={parentRequired} onChange={(item) => setParentId(item?.id ?? null)} />
        </label>}
        {!object && requiredRelationGroups.map((group) => {
          const definition = model.relationTypes.find((relation) => relation.key === group.relationTypeKey);
          const selectedType = requiredRelationTypes[group.relationTypeKey] ?? group.relations[0]?.fromObjectTypeKey;
          const locked = lockedInitialRelationKeys.includes(group.relationTypeKey);
          return <fieldset key={group.relationTypeKey}><legend>{definition?.reverseName ?? group.relationTypeKey}</legend>
            {locked ? <p><strong>{requiredRelationObjects[group.relationTypeKey]?.name}</strong></p> : <>
              {group.relations.length > 1 && <label>Object type<select aria-label={`${definition?.reverseName ?? group.relationTypeKey} object type`} value={selectedType} onChange={(event) => { setRequiredRelationTypes((current) => ({ ...current, [group.relationTypeKey]: event.target.value })); setRequiredRelationObjects((current) => ({ ...current, [group.relationTypeKey]: undefined })); }}>{group.relations.map((relation) => <option key={relation.fromObjectTypeKey} value={relation.fromObjectTypeKey}>{model.objectTypes.find((item) => item.key === relation.fromObjectTypeKey)?.name ?? relation.fromObjectTypeKey}</option>)}</select></label>}
              <ObjectLookup objectTypeKey={selectedType} required value={requiredRelationObjects[group.relationTypeKey]} onChange={(item) => setRequiredRelationObjects((current) => ({ ...current, [group.relationTypeKey]: item }))} />
            </>}
          </fieldset>;
        })}
        <label>Name<input name="name" required autoFocus defaultValue={object?.name} /></label>
        {object ? <label>State<input name="state" required defaultValue={object.state} /></label> : bindings.map((binding) => <AttributeField key={binding.attributeTypeKey} binding={binding} attribute={attributeMap.get(binding.attributeTypeKey)!} />)}
        {error && <div className="notice error-notice">{error}</div>}
        <div className="dialog-actions"><button type="button" className="secondary" disabled={saving} onClick={onClose}>Cancel</button><button className="primary" disabled={saving || (!object && requiredRelationGroups.some((group) => !requiredRelationObjects[group.relationTypeKey]))}>{saving ? "Saving…" : object ? "Save changes" : "Create"}</button></div>
      </form>
    </div>
  </div>;
}
