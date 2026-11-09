/**
 * The relationship's own values, edited in place (0.13 RV): each value reads as a record's field does
 * (label, value, a pencil or a plus where none is set, as Settings › Appearance › Edit pencil says)
 * and a click opens the small form of `InlineEditForm`. A relation matrix cell's dialog uses
 * `RelationValueFields`; a relationships table's cell uses `useRelationValueSave` for the same save,
 * so a value is written against the relationship's version, merged with its other values, the same
 * way wherever it is edited.
 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigationGuard } from "@/routing/navigationGuard";
import { readEditHint } from "@/lib/editHint";
import type { AttributeTypeDefinition, RelationRecord } from "@/types";
import { EditInPlaceValue, InlineEditForm } from "@/ui/EditInPlace";
import { Notice } from "@/ui/Notice";
import { formatValue } from "@/ui/formatValue";
import {
  RELATION_ATTRIBUTES_LABEL,
  RelationAttributes,
  RelationConflictNotice,
  relationValuesFromForm,
  useRelationValues,
} from "./RelationAttributes";

type StoredRelation = Pick<RelationRecord, "id" | "version" | "attributes">;

/**
 * Saves one attribute of a relationship from the form that holds it: nothing is written when the
 * value is unchanged (the editor closes); otherwise the relationship's other stored values
 * are kept and an emptied one is dropped. Gives "saved", "unchanged" or false when it was refused.
 */
export function useRelationValueSave(
  attribute: AttributeTypeDefinition,
  relation: StoredRelation,
  workspaceKey: string,
) {
  const edit = useRelationValues({ id: relation.id, version: relation.version }, workspaceKey);
  async function save(form: HTMLFormElement): Promise<"saved" | "unchanged" | false> {
    const next = relationValuesFromForm(form, [attribute])[attribute.key];
    if (JSON.stringify(next ?? null) === JSON.stringify(relation.attributes[attribute.key] ?? null)) return "unchanged";
    const values = { ...relation.attributes, [attribute.key]: next };
    if (next === null) delete values[attribute.key];
    return (await edit.save(values)) && "saved";
  }
  return { ...edit, saveValue: save };
}

/** A stored value as a record's field shows it, telling not set and empty text apart. */
function shownValue(value: unknown) {
  if (value === undefined || value === null) return <span className="unset-value">Not set</span>;
  if (value === "") return <span className="unset-value">Empty text</span>;
  return <span className="attribute-value">{formatValue(value)}</span>;
}

function RelationValueField({
  attribute,
  relation,
  workspaceKey,
  editing,
  disabled,
  onEdit,
  onClose,
  onSaved,
  onDirty,
}: {
  attribute: AttributeTypeDefinition;
  relation: StoredRelation;
  workspaceKey: string;
  /** Tells the dialog whether this field holds input that is not saved. */
  onDirty?: (dirty: boolean) => void;
  editing: boolean;
  disabled: boolean;
  onEdit: () => void;
  onClose: () => void;
  onSaved: () => Promise<void> | void;
}) {
  const edit = useRelationValueSave(attribute, relation, workspaceKey);
  const value = relation.attributes[attribute.key];
  const [changed, setChanged] = useState(false);
  const dirty = editing && changed;
  useNavigationGuard(dirty, edit.saving, onClose);
  useEffect(() => {
    onDirty?.(dirty);
    return () => onDirty?.(false);
    // The parent's callback is only told what changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty]);
  if (!editing)
    return (
      <EditInPlaceValue
        layout="row"
        name={attribute.name}
        empty={value === undefined || value === null}
        disabled={disabled}
        onEdit={() => {
          edit.reset();
          setChanged(false);
          onEdit();
        }}
      >
        {shownValue(value)}
      </EditInPlaceValue>
    );
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await edit.saveValue(event.currentTarget)) {
      onClose();
      await onSaved();
    }
  }
  return (
    <InlineEditForm
      label={`Edit ${attribute.name}`}
      saving={edit.saving}
      onSubmit={submit}
      onClose={onClose}
      onChange={() => setChanged(true)}
      notices={
        <>
          {edit.current && <RelationConflictNotice attributes={[attribute]} current={edit.current} />}
          {edit.error && (
            <Notice tone="error" title="The value was not saved" focusOnMount>
              {edit.error}
            </Notice>
          )}
        </>
      }
    >
      <RelationAttributes attributes={[attribute]} relation={relation} mode="edit" legend={false} />
    </InlineEditForm>
  );
}

/**
 * A relationship's attributes as the rows of a record's fields. Where `editable`, each value edits in
 * place, one at a time; otherwise they are shown. `onSaved` re-reads what the relationship came from.
 */
export function RelationValueFields({
  attributes,
  relation,
  workspaceKey,
  editable,
  onSaved,
  onDirty,
}: {
  attributes: AttributeTypeDefinition[];
  onDirty?: (dirty: boolean) => void;
  relation: StoredRelation;
  workspaceKey: string;
  editable: boolean;
  onSaved: () => Promise<void> | void;
}) {
  const [open, setOpen] = useState<string>();
  if (!attributes.length) return null;
  return (
    <div className="relation-attributes" role="group" aria-label={RELATION_ATTRIBUTES_LABEL}>
      <strong className="relation-attributes-heading">{RELATION_ATTRIBUTES_LABEL}</strong>
      <dl className="attribute-grid" data-edit-hint={readEditHint()}>
        {attributes.map((attribute) => (
          <div key={attribute.key} className={open === attribute.key ? "attribute-row editing" : "attribute-row"}>
            <dt>{attribute.name}</dt>
            <dd>
              {editable ? (
                <RelationValueField
                  // A saved value brings a new version, which the field's save starts from.
                  key={`${relation.id}:${relation.version}`}
                  attribute={attribute}
                  relation={relation}
                  workspaceKey={workspaceKey}
                  editing={open === attribute.key}
                  disabled={open !== undefined && open !== attribute.key}
                  onEdit={() => setOpen(attribute.key)}
                  onClose={() => setOpen(undefined)}
                  onSaved={onSaved}
                  onDirty={onDirty}
                />
              ) : (
                shownValue(relation.attributes[attribute.key])
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
