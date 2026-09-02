import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type {
  AttributeTypeDefinition,
  EngineModel,
  ObjectItem,
  ObjectTypeAttributeDefinition,
  ObjectTypeDefinition,
} from "../types";

export function ObjectFormDialog({
  model,
  applicationKey,
  objectType,
  object,
  parentObjectId,
  onClose,
  onSaved,
}: {
  model: EngineModel;
  applicationKey: string;
  objectType: ObjectTypeDefinition;
  object?: ObjectItem;
  parentObjectId?: string;
  onClose: () => void;
  onSaved: (item: ObjectItem) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [parents, setParents] = useState<ObjectItem[]>([]);
  const attributeMap = useMemo(
    () => new Map(model.attributeTypes.map((attribute) => [attribute.key, attribute])),
    [model.attributeTypes],
  );
  const bindings = objectType.attributes
    .filter((binding) => binding.ui.hidden !== true && attributeMap.get(binding.attributeTypeKey)?.ui.hidden !== true)
    .slice()
    .sort((a, b) => a.order - b.order);
  const parentRelationKeys = new Set(objectType.behavior.parentRelationTypeKeys ?? []);
  const parentTypeKeys = Array.from(new Set(
    model.objectTypeRelations
      .filter((relation) => relation.toObjectTypeKey === objectType.key && parentRelationKeys.has(relation.relationTypeKey))
      .map((relation) => relation.fromObjectTypeKey),
  ));
  const parentRequired = objectType.features.rootCreatable !== true;

  useEffect(() => {
    let active = true;
    Promise.all(parentTypeKeys.map((key) => api.objects(key, { applicationKey, pageSize: 100 })))
      .then((pages) => {
        if (active) setParents(pages.flatMap((page) => page.items).filter((item) => item.id !== object?.id));
      })
      .catch((cause) => active && setError(String(cause)));
    return () => { active = false; };
  }, [applicationKey, object?.id, objectType.key]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const attributes: Record<string, unknown> = {};
    try {
      for (const binding of bindings) {
        if (binding.readOnly) continue;
        const definition = attributeMap.get(binding.attributeTypeKey)!;
        const raw = data.get(definition.key);
        if (definition.valueType === "boolean") attributes[definition.key] = raw === "on";
        else if (raw === "") {
          if (object) attributes[definition.key] = null;
        } else if (definition.valueType === "integer" || definition.valueType === "decimal") {
          attributes[definition.key] = Number(raw);
        } else if (definition.valueType === "json") {
          attributes[definition.key] = JSON.parse(String(raw));
        } else {
          attributes[definition.key] = raw;
        }
      }
      const selectedParent = String(data.get("parentObjectId") ?? "") || null;
      const saved = object
        ? await api.updateObject(objectType.key, object.id, {
            name: String(data.get("name")),
            parentObjectId: selectedParent,
            attributes,
            expectedVersion: object.version,
          })
        : await api.createObject(objectType.key, {
            applicationKey,
            name: String(data.get("name")),
            parentObjectId: selectedParent ?? undefined,
            attributes,
          });
      onSaved(saved);
    } catch (cause) {
      setError(String(cause));
      setSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="object-form-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="dialog-header">
          <div><p className="eyebrow">{object ? "Edit object" : "Create in context"}</p><h2 id="object-form-title">{object ? object.name : `New ${objectType.name}`}</h2></div>
          <button className="close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <form onSubmit={submit}>
          {parentTypeKeys.length > 0 && (
            <label>
              Parent
              <select
                name="parentObjectId"
                required={parentRequired}
                defaultValue={parentObjectId ?? object?.parentObjectId ?? ""}
              >
                <option value="">{parentRequired ? "Select a parent…" : "No parent"}</option>
                {parents.map((parent) => (
                  <option key={parent.id} value={parent.id}>{parent.path.map((part) => part.name).join(" / ")}</option>
                ))}
              </select>
            </label>
          )}
          <label>Name<input name="name" required autoFocus defaultValue={object?.name} /></label>
          {bindings.map((binding) => (
            <FieldInput
              key={binding.attributeTypeKey}
              binding={binding}
              attribute={attributeMap.get(binding.attributeTypeKey)!}
              value={object?.attributes[binding.attributeTypeKey]}
            />
          ))}
          {error && <div className="notice">{error}</div>}
          <div className="dialog-actions">
            <button type="button" className="secondary" onClick={onClose}>Cancel</button>
            <button className="primary" disabled={saving}>{saving ? "Saving…" : object ? "Save changes" : "Create"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FieldInput({
  binding,
  attribute,
  value,
}: {
  binding: ObjectTypeAttributeDefinition;
  attribute: AttributeTypeDefinition;
  value?: unknown;
}) {
  const helpText = String(binding.ui.helpText ?? attribute.ui.helpText ?? "");
  if (attribute.valueType === "boolean") {
    return (
      <label className="checkbox">
        <input name={attribute.key} type="checkbox" defaultChecked={value === undefined ? attribute.default === true : value === true} disabled={binding.readOnly} />
        <span>{attribute.name}{helpText && <small>{helpText}</small>}</span>
      </label>
    );
  }
  const common = {
    name: attribute.key,
    required: binding.required,
    disabled: binding.readOnly,
    defaultValue: value === undefined || value === null ? "" : attribute.valueType === "json" ? JSON.stringify(value, null, 2) : String(value),
  };
  return (
    <label>
      {attribute.name}
      {attribute.valueType === "longText" || attribute.valueType === "json" ? (
        <textarea {...common} rows={attribute.valueType === "json" ? 5 : 3} />
      ) : (
        <input
          {...common}
          type={attribute.valueType === "integer" || attribute.valueType === "decimal" ? "number" : attribute.valueType === "date" ? "date" : attribute.valueType === "dateTime" ? "datetime-local" : "text"}
          step={attribute.valueType === "decimal" ? "any" : undefined}
          min={attribute.validation.minimum as number | undefined}
          max={attribute.validation.maximum as number | undefined}
        />
      )}
      {helpText && <small>{helpText}</small>}
    </label>
  );
}
