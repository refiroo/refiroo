import { relationTypeFor, typeName } from "@/model/lookup";
import { useNavigationGuard } from "@/routing/navigationGuard";
import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useDataApi } from "@/state/WorkspaceDataContext";
import { errorMessage, isVersionConflict } from "@/api/errors";
import type {
  AttributeTypeDefinition,
  EngineModel,
  ObjectItem,
  ObjectTypeDefinition,
  ObjectAttributeInput,
} from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { CancelButton, Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { CurrentObjectContent } from "@/features/objects/CurrentObjectContent";
import { parentObjectTypeKeys } from "@/model/placements";
import { candidateScope } from "@/model/candidates";
import { ObjectLookup } from "@/ui/ObjectLookup";
import { Icon } from "@/ui/Icon";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

/** Where a type's More fields state is remembered in this browser (0.17 PL2). */
const moreFieldsKey = (objectTypeKey: string) => `rdm.moreFields.${objectTypeKey}`;
/** The problems but for one field's, which has just been put right. */
const without = (problems: Record<string, string>, key: string) =>
  Object.fromEntries(Object.entries(problems).filter(([field]) => field !== key));
const isFlag = (value: unknown): value is boolean => typeof value === "boolean";

/** What is wrong with a typed value, in words; nothing when it is fine or empty. */
function valueProblem(attribute: AttributeTypeDefinition, input: HTMLInputElement | HTMLTextAreaElement | null) {
  if (!input || attribute.valueType === "boolean") return undefined;
  const raw = input.value;
  const bad = input instanceof HTMLInputElement && input.validity?.badInput;
  if (attribute.valueType === "integer" || attribute.valueType === "decimal") {
    if (bad || (raw !== "" && Number.isNaN(Number(raw)))) return "Enter a number.";
    if (raw === "") return undefined;
    if (attribute.valueType === "integer" && !Number.isInteger(Number(raw))) return "Enter a whole number.";
    const { minimum, maximum } = attribute.validation;
    if (typeof minimum === "number" && Number(raw) < minimum) return `Enter a number of at least ${minimum}.`;
    if (typeof maximum === "number" && Number(raw) > maximum) return `Enter a number of at most ${maximum}.`;
  } else if (attribute.valueType === "date" || attribute.valueType === "dateTime") {
    if (bad) return "Enter a valid date.";
  } else if (attribute.valueType === "json" && raw !== "") {
    try {
      JSON.parse(raw);
    } catch {
      return "Enter valid JSON.";
    }
  }
  return undefined;
}

export function ObjectFormDialog({
  model,
  applicationKey,
  applicationChoices,
  workspaceKey,
  objectType,
  object,
  parentObjectId,
  parentObjectTypeKey,
  parentName,
  collectionName,
  initialRelationObjects = {},
  lockedInitialRelationKeys = [],
  onClose,
  onSaved,
}: {
  model: EngineModel;
  applicationKey: string;
  /**
   * Applications a new record may be created in, shown as a choice. `applicationKey` is the default.
   * Used where the context (a mapping lens) does not decide which application owns the record.
   */
  applicationChoices?: string[];
  workspaceKey?: string;
  objectType: ObjectTypeDefinition;
  object?: ObjectItem;
  parentObjectId?: string;
  parentObjectTypeKey?: string;
  /** The parent's name, where the page the dialog was opened from knows it: the parent is then said, not asked. */
  parentName?: string;
  /** The collection the record is added to, said above the title; the type's plural name where not given. */
  collectionName?: string;
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
  const [ownerKey, setOwnerKey] = useState(applicationKey);
  const owner = model.applications.find((application) => application.key === ownerKey);
  const [parentTypeKey, setParentTypeKey] = useState(initialParentType);
  const [parentId, setParentId] = useState<string | null>(parentObjectId ?? object?.parentObjectId ?? null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [changingParent, setChangingParent] = useState(false);
  const [fetchedParentName, setFetchedParentName] = useState<string>();
  const attributeMap = useMemo(
    () => new Map(model.attributeTypes.map((attribute) => [attribute.key, attribute])),
    [model.attributeTypes],
  );
  const bindings = objectType.attributes
    .filter((binding) => binding.ui?.hidden !== true && attributeMap.get(binding.attributeTypeKey)?.ui?.hidden !== true)
    .slice()
    .sort((a, b) => a.order - b.order);
  const requiredBindings = bindings.filter((binding) => binding.required);
  const optionalBindings = bindings.filter((binding) => !binding.required);
  // The optional fields wait under More fields; the person's last choice for the type is remembered
  // in this browser, and a record being edited opens them where it holds a value in one.
  const storedMore = readLocalPreference<boolean | undefined>(
    moreFieldsKey(objectType.key),
    undefined,
    (value): value is boolean | undefined => isFlag(value),
  );
  const [moreOpen, setMoreOpen] = useState(
    () =>
      storedMore ??
      Boolean(
        object &&
        optionalBindings.some((binding) =>
          object.attributes.some(
            (item) => item.attributeTypeKey === binding.attributeTypeKey && item.value !== null && item.value !== "",
          ),
        ),
      ),
  );
  const parentRelationKeys = new Set(objectType.behavior.parentRelationTypeKeys ?? []);
  // Where the model lets this type stand, in any application, and in the record's own one: a parent
  // must belong to the record's application, so only those are offered.
  const modelParentTypeKeys = Array.from(
    new Set(model.applications.flatMap((application) => parentObjectTypeKeys(model, application, objectType.key))),
  );
  const parentTypeKeys = owner
    ? parentObjectTypeKeys(model, owner, objectType.key).filter((key) => modelParentTypeKeys.includes(key))
    : modelParentTypeKeys;
  const parentRequired = objectType.features.rootCreatable !== true;
  const noPermittedParent =
    !object && !parentObjectId && parentRequired && modelParentTypeKeys.length > 0 && parentTypeKeys.length === 0;
  const activeParentTypeKey =
    parentTypeKey && parentTypeKeys.includes(parentTypeKey) ? parentTypeKey : parentTypeKeys[0];
  const knownParentId = parentObjectId ?? object?.parentObjectId ?? null;
  const givenParentName = parentName ?? object?.path.at(-2)?.name ?? fetchedParentName;
  const soleParentTypeKey = parentTypeKeys.length === 1 ? parentTypeKeys[0] : undefined;
  useEffect(() => {
    // A parent the page knows only by id is read once, so the dialog can say it.
    if (!knownParentId || parentName || object || !soleParentTypeKey) return;
    let active = true;
    Promise.resolve()
      .then(() => api.object(soleParentTypeKey, knownParentId, activeWorkspaceKey))
      .then(
        (parent) => active && setFetchedParentName(parent.name),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [api, knownParentId, parentName, object, soleParentTypeKey, activeWorkspaceKey]);
  const parentSaid = Boolean(parentId && parentId === knownParentId && givenParentName && !changingParent);
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

  const finishNavigation = useNavigationGuard(dirty, saving, onClose);
  /** The required and typed values that are not right, by field, each said in words. */
  function problems(form: HTMLFormElement) {
    const found: Record<string, string> = {};
    if (parentTypeKeys.length > 0 && parentRequired && !parentId && !parentSaid)
      found.parent = "Choose where this goes.";
    if (!object)
      for (const group of requiredRelationGroups)
        if (!requiredRelationObjects[group.relationTypeKey]) {
          const label = relationTypeFor(model, group.relationTypeKey)?.reverseName;
          found[`relation:${group.relationTypeKey}`] = `Choose a record for ${label ?? group.relationTypeKey}.`;
        }
    if (!String(new FormData(form).get("name") ?? "").trim()) found.name = "Enter a name.";
    for (const binding of bindings) {
      if (binding.readOnly) continue;
      const attribute = attributeMap.get(binding.attributeTypeKey)!;
      const input = form.elements.namedItem(attribute.key);
      const control = input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement ? input : null;
      if (
        attribute.valueType !== "boolean" &&
        binding.required &&
        !control?.value.trim() &&
        !control?.validity?.badInput
      )
        found[attribute.key] = `${attribute.name} is required.`;
      else {
        const problem = valueProblem(attribute, control);
        if (problem) found[attribute.key] = problem;
      }
    }
    return found;
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = problems(event.currentTarget);
    setErrors(found);
    const first = Object.keys(found)[0];
    if (first) {
      // A problem in a field behind More fields opens them, so it can be seen.
      if (optionalBindings.some((binding) => binding.attributeTypeKey in found)) setMoreOpen(true);
      const form = event.currentTarget;
      setTimeout(() => {
        const control = form.elements.namedItem(first);
        (control instanceof HTMLElement
          ? control
          : form.querySelector<HTMLElement>(`[data-field="${first}"] input, [data-field="${first}"] select`)
        )?.focus();
      }, 0);
      return;
    }
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
        const saved = await api.updateObject(objectType.key, object.id, payload);
        finishNavigation();
        onSaved(saved);
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
        const saved = await api.createObject(objectType.key, {
          applicationKey: ownerKey,
          workspaceKey: activeWorkspaceKey,
          name,
          parentObjectId: parentId ?? undefined,
          attributes,
          initialRelations,
        });
        finishNavigation();
        onSaved(saved);
      }
    } catch (cause) {
      if (object && isVersionConflict(cause, ["VERSION_CONFLICT", "CHANGE_SET_VERSION_CONFLICT"])) {
        try {
          const fresh = await api.object(objectType.key, object.id, activeWorkspaceKey);
          setBaselineObject(fresh);
          setObjectVersion(fresh.version);
          setError(
            isVersionConflict(cause, ["CHANGE_SET_VERSION_CONFLICT"])
              ? "The change set changed. Current content is loaded; your edits are preserved. Review and save again."
              : "The record changed. Its latest version has been loaded; your edits are preserved. Review and save again.",
          );
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      } else setError(errorMessage(cause));
      setSaving(false);
    }
  }

  const fieldError = (key: string) =>
    errors[key] ? (
      <p className="field-error" role="alert">
        {errors[key]}
      </p>
    ) : null;
  const attributeField = (binding: (typeof bindings)[number], mark: "required" | "optional") => (
    <AttributeField
      key={binding.attributeTypeKey}
      binding={binding}
      attribute={attributeMap.get(binding.attributeTypeKey)!}
      value={object?.attributes.find((item) => item.attributeTypeKey === binding.attributeTypeKey)?.value}
      mark={mark}
      error={errors[binding.attributeTypeKey]}
    />
  );

  return (
    <Modal
      title={object ? object.name : `New ${objectType.name}`}
      eyebrow={collectionName ?? objectType.pluralName}
      busy={saving}
      dirty={dirty}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={submit}
        onChange={(event) => {
          setDirty(true);
          const target = event.target;
          if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
            editedFields.current.add(target.name);
            setErrors((current) => {
              if (!(target.name in current)) return current;
              return without(current, target.name);
            });
          }
        }}
      >
        {applicationChoices && !object && applicationChoices.length === 1 && (
          <p className="form-fact">
            <span>Application</span>
            <strong>{owner?.name ?? ownerKey}</strong>
          </p>
        )}
        {applicationChoices && !object && applicationChoices.length > 1 && (
          <label>
            Application
            <select
              value={ownerKey}
              onChange={(event) => {
                setDirty(true);
                setOwnerKey(event.target.value);
                setParentTypeKey(undefined);
                setParentId(null);
              }}
            >
              {applicationChoices.map((key) => (
                <option key={key} value={key}>
                  {model.applications.find((application) => application.key === key)?.name ?? key}
                </option>
              ))}
            </select>
          </label>
        )}
        {noPermittedParent && (
          <Notice tone="warning" title="No parent available">
            A {objectType.name.toLowerCase()} needs a parent, and none of its parent types belong to{" "}
            {owner?.name ?? ownerKey}.
            {applicationChoices && applicationChoices.length > 1 && " Choose another application."}
          </Notice>
        )}
        {parentTypeKeys.length > 0 && parentSaid && (
          <p className="parent-fact">
            <span>In</span>
            <strong>{givenParentName}</strong>
            <span aria-hidden="true">·</span>
            <button type="button" className="ghost" onClick={() => setChangingParent(true)}>
              Change
            </button>
          </p>
        )}
        {parentTypeKeys.length > 0 && !parentSaid && (
          <fieldset className="lookup-field" data-field="parent">
            <legend>
              Parent
              {parentRequired && (
                <span className="field-mark" aria-hidden="true">
                  *
                </span>
              )}
            </legend>
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
                    {typeName(model, key)}
                  </option>
                ))}
              </select>
            )}
            <ObjectLookup
              key={ownerKey}
              objectTypeKey={activeParentTypeKey}
              applicationKey={ownerKey}
              workspaceKey={activeWorkspaceKey}
              excludeId={object?.id}
              selectedId={parentId}
              selectedLabel={givenParentName}
              required={parentRequired}
              onChange={(item) => {
                setDirty(true);
                editedParent.current = true;
                setParentId(item?.id ?? null);
                if (item) setErrors((current) => without(current, "parent"));
              }}
              label="Parent"
            />
            {fieldError("parent")}
          </fieldset>
        )}
        {!object &&
          requiredRelationGroups.map((group) => {
            const definition = relationTypeFor(model, group.relationTypeKey);
            const selectedType = requiredRelationTypes[group.relationTypeKey] ?? group.relations[0]?.fromObjectTypeKey;
            const selectedBinding = group.relations.find((relation) => relation.fromObjectTypeKey === selectedType);
            const locked = lockedInitialRelationKeys.includes(group.relationTypeKey);
            return (
              <fieldset
                key={group.relationTypeKey}
                className="lookup-field"
                data-field={`relation:${group.relationTypeKey}`}
              >
                <legend>
                  {definition?.reverseName ?? group.relationTypeKey}
                  <span className="field-mark" aria-hidden="true">
                    *
                  </span>
                </legend>
                {locked ? (
                  <p>
                    <strong>{requiredRelationObjects[group.relationTypeKey]?.name}</strong>
                  </p>
                ) : (
                  <>
                    {group.relations.length > 1 && (
                      <label>
                        Record type
                        <select
                          aria-label={`${definition?.reverseName ?? group.relationTypeKey} record type`}
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
                              {typeName(model, relation.fromObjectTypeKey)}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <ObjectLookup
                      objectTypeKey={selectedType}
                      workspaceKey={activeWorkspaceKey}
                      required
                      label={definition?.reverseName ?? group.relationTypeKey}
                      candidates={selectedBinding && candidateScope(model, selectedBinding, "incoming", objectType.key)}
                      value={requiredRelationObjects[group.relationTypeKey]}
                      onChange={(item) => {
                        setDirty(true);
                        setRequiredRelationObjects((current) => ({ ...current, [group.relationTypeKey]: item }));
                        if (item) setErrors((current) => without(current, `relation:${group.relationTypeKey}`));
                      }}
                    />
                    {fieldError(`relation:${group.relationTypeKey}`)}
                  </>
                )}
              </fieldset>
            );
          })}
        <p className="field-key">
          <span aria-hidden="true">*</span> marks a required field.
        </p>
        <label className={errors.name ? "field-has-error" : undefined}>
          Name
          <span className="field-mark" aria-hidden="true">
            *
          </span>
          <input
            name="name"
            aria-label="Name"
            aria-required="true"
            aria-invalid={errors.name ? true : undefined}
            autoFocus
            defaultValue={object?.name}
          />
          {fieldError("name")}
        </label>
        {requiredBindings.map((binding) => attributeField(binding, "required"))}
        {optionalBindings.length > 0 && (
          <div className="plain-disclosure more-fields">
            <button
              type="button"
              className="ghost plain-disclosure-toggle"
              aria-expanded={moreOpen}
              aria-controls="more-fields"
              onClick={() => {
                writeLocalPreference(moreFieldsKey(objectType.key), !moreOpen);
                setMoreOpen(!moreOpen);
              }}
            >
              More fields ({optionalBindings.length})
              <Icon name="chevron-down" size={14} />
            </button>
            {/* Kept in the form while closed, so a field's default still goes with the new record. */}
            <div id="more-fields" className="plain-disclosure-body" hidden={!moreOpen}>
              {optionalBindings.map((binding) => attributeField(binding, "optional"))}
            </div>
          </div>
        )}
        {object && baselineObject && baselineObject !== object && (
          <CurrentObjectContent model={model} object={baselineObject} />
        )}
        {error && (
          <Notice tone="error" title="The record was not saved" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <CancelButton disabled={saving} />
          <button className="primary" disabled={saving || noPermittedParent}>
            {saving ? "Saving…" : object ? "Save" : `Add ${objectType.name}`}
          </button>
        </div>
      </form>
    </Modal>
  );
}
