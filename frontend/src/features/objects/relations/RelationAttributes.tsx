/**
 * The attributes a relationship itself carries (0.13 RV): the one component the Edit values dialog,
 * a relation matrix cell and a relationships table share. It shows them (`display`), or offers them
 * as the form fields they are (`edit`), given the binding that declares them; the checks, the typed
 * values and the conflict notice are the same wherever they are edited.
 */

import { useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi } from "@/state/WorkspaceDataContext";
import type { AttributeTypeDefinition, EngineModel, RelationRecord } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Notice } from "@/ui/Notice";
import { formatValue } from "@/ui/formatValue";

/** What the group of a relationship's own attributes is called wherever it stands. */
export const RELATION_ATTRIBUTES_LABEL = "Attributes of the relationship";

/** The prefix of the form controls, so a form that also holds a record's fields keeps them apart. */
const FIELD_PREFIX = "relation:";

/** The attribute types a binding declares for its relationships, in its order. */
export function relationAttributeTypes(
  model: EngineModel,
  binding: { attributeTypeKeys?: string[] } | undefined,
): AttributeTypeDefinition[] {
  return (binding?.attributeTypeKeys ?? [])
    .map((key) => model.attributeTypes.find((item) => item.key === key))
    .filter((item): item is AttributeTypeDefinition => Boolean(item));
}

/** The values a form holds for `attributes`, typed as the model declares them. */
export function relationValuesFromForm(form: HTMLFormElement, attributes: AttributeTypeDefinition[]) {
  return Object.fromEntries(
    attributes.map((attribute) => [attribute.key, attributeValueFromForm(form, attribute, FIELD_PREFIX)]),
  );
}

/**
 * A relationship's attributes, shown or edited. Nothing is rendered when the binding declares none.
 * `edit` renders fields to place in the caller's form and read back with
 * {@link relationValuesFromForm}; `display` renders the values formatted.
 */
export function RelationAttributes({
  attributes,
  relation,
  mode,
  legend = true,
  autoFocus = false,
}: {
  attributes: AttributeTypeDefinition[];
  relation?: Pick<RelationRecord, "attributes">;
  mode: "edit" | "display";
  /** Whether the group carries its name; a dialog that is only these may leave it out. */
  legend?: boolean;
  /** Focus the first field as it appears (a single value edited in its cell). */
  autoFocus?: boolean;
}) {
  if (!attributes.length) return null;
  if (mode === "display")
    return (
      <div className="relation-attributes" role="group" aria-label={RELATION_ATTRIBUTES_LABEL}>
        {legend && <strong className="relation-attributes-heading">{RELATION_ATTRIBUTES_LABEL}</strong>}
        <dl>
          {attributes.map((attribute) => (
            <div key={attribute.key}>
              <dt>{attribute.name}</dt>
              <dd>{formatValue(relation?.attributes[attribute.key])}</dd>
            </div>
          ))}
        </dl>
      </div>
    );
  return (
    <fieldset className="relation-attributes">
      {legend ? (
        <legend>{RELATION_ATTRIBUTES_LABEL}</legend>
      ) : (
        <legend className="visually-hidden">{RELATION_ATTRIBUTES_LABEL}</legend>
      )}
      {attributes.map((attribute) => (
        <AttributeField
          key={attribute.key}
          attribute={attribute}
          prefix={FIELD_PREFIX}
          value={relation?.attributes[attribute.key]}
          autoFocus={autoFocus && attribute === attributes[0]}
        />
      ))}
    </fieldset>
  );
}

/** The notice a version conflict leaves: the relationship as it is saved now. */
export function RelationConflictNotice({
  attributes,
  current,
}: {
  attributes: AttributeTypeDefinition[];
  current: RelationRecord;
}) {
  return (
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
  );
}

/**
 * Saves a relationship's attributes against its version and keeps what a conflict leaves: the
 * relationship as saved now, its version for the next try and the reason. The data client of the
 * context carries the change set, so a save in a change set stages there.
 */
export function useRelationValues(relation: Pick<RelationRecord, "id" | "version"> | undefined, workspaceKey: string) {
  const api = useDataApi();
  const [version, setVersion] = useState(relation?.version ?? 1);
  const [current, setCurrent] = useState<RelationRecord>();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  /** Saves `values`; gives the relationship as saved, or false when it was refused. */
  async function save(values: Record<string, unknown>): Promise<RelationRecord | false> {
    if (!relation) return false;
    setSaving(true);
    setError("");
    try {
      const saved = await api.updateRelation(relation.id, { attributes: values, expectedVersion: version });
      setVersion(saved.version);
      setCurrent(undefined);
      return saved;
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")) {
        try {
          const fresh = await api.relation(relation.id, workspaceKey);
          setVersion(fresh.version);
          setCurrent(fresh);
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      }
      return false;
    } finally {
      setSaving(false);
    }
  }

  return {
    save,
    saving,
    error,
    current,
    version,
    clearError: () => setError(""),
    /** Forgets a refusal and a conflict left by an earlier try, when an editor is opened again. */
    reset: () => {
      setError("");
      setCurrent(undefined);
    },
  };
}
