/**
 * Saving one attribute of a relationship (0.13 RV): a relationships table's cell and a relation
 * matrix cell's table (`RelationValueCell`) use `useRelationValueSave`, so a value is written against
 * the relationship's version, merged with its other values, the same way wherever it is edited.
 */

import { useRelationValues, relationValuesFromForm } from "./RelationAttributes";
import type { AttributeTypeDefinition, RelationRecord } from "@/types";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useOptionalToast } from "@/ui/Toast";

export type StoredRelation = Pick<RelationRecord, "id" | "version" | "attributes">;

/**
 * Saves one attribute of a relationship from the form that holds it: nothing is written when the
 * value is unchanged (the editor closes); otherwise the relationship's other stored values
 * are kept and an emptied one is dropped. Gives the relationship as saved, "unchanged" or false when it was
 * refused. A saved value says so in a toast with Undo, which puts the earlier values back against the version
 * the save made and then calls `changed` (0.17 UX2).
 */
export function useRelationValueSave(
  attribute: AttributeTypeDefinition,
  relation: StoredRelation,
  workspaceKey: string,
) {
  const edit = useRelationValues({ id: relation.id, version: relation.version }, workspaceKey);
  const api = useDataApi();
  const toast = useOptionalToast();
  async function save(form: HTMLFormElement, changed: () => void): Promise<"saved" | "unchanged" | false> {
    const next = relationValuesFromForm(form, [attribute])[attribute.key];
    if (JSON.stringify(next ?? null) === JSON.stringify(relation.attributes[attribute.key] ?? null)) return "unchanged";
    const values = { ...relation.attributes, [attribute.key]: next };
    if (next === null) delete values[attribute.key];
    const saved = await edit.save(values);
    if (!saved) return false;
    const earlier = relation.attributes;
    toast(`${attribute.name} ${next === null ? "removed" : "saved"}`, {
      actions: [
        {
          label: "Undo",
          onPress: () =>
            void api
              .updateRelation(relation.id, { attributes: earlier, expectedVersion: saved.version })
              .then(changed, () =>
                toast("Undo was not possible: the relationship changed again in the meantime.", { tone: "info" }),
              ),
        },
      ],
    });
    return "saved";
  }
  return { ...edit, saveValue: save };
}
