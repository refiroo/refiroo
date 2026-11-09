/**
 * Saving one attribute of a relationship (0.13 RV): a relationships table's cell and a relation
 * matrix cell's table (`RelationValueCell`) use `useRelationValueSave`, so a value is written against
 * the relationship's version, merged with its other values, the same way wherever it is edited.
 */

import { useRelationValues, relationValuesFromForm } from "./RelationAttributes";
import type { AttributeTypeDefinition, RelationRecord } from "@/types";

export type StoredRelation = Pick<RelationRecord, "id" | "version" | "attributes">;

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
