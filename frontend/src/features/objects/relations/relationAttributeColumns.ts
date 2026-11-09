/**
 * The attributes of the relationships a list shows as columns (0.13 RV): which attribute types the
 * relation types of a relationships panel declare for a record's type, and how a column names one.
 */

import type { EngineModel } from "@/types";

export { RELATION_ATTRIBUTES_LABEL } from "@/features/objects/relations/RelationAttributes";

const COLUMN_PREFIX = "relation:";

/** The column key of a relationship's attribute, apart from a related record's field of the same key. */
export const relationAttributeColumn = (attributeTypeKey: string) => `${COLUMN_PREFIX}${attributeTypeKey}`;

/** The attribute type a column shows, or `undefined` for a column of the related record. */
export const relationAttributeOfColumn = (column: string) =>
  column.startsWith(COLUMN_PREFIX) ? column.slice(COLUMN_PREFIX.length) : undefined;

/**
 * The attribute types the relationships of `relationTypeKeys` declare for a record of `objectTypeKey`
 * read in `direction`, once each, in the order the bindings declare them.
 */
export function panelRelationAttributeKeys(
  model: EngineModel,
  objectTypeKey: string,
  relationTypeKeys: string[],
  direction: "outgoing" | "incoming" | "both",
): string[] {
  const keys: string[] = [];
  for (const binding of model.objectTypeRelations) {
    if (!relationTypeKeys.includes(binding.relationTypeKey)) continue;
    const here =
      (direction !== "incoming" && binding.fromObjectTypeKey === objectTypeKey) ||
      (direction !== "outgoing" && binding.toObjectTypeKey === objectTypeKey);
    if (!here) continue;
    for (const key of binding.attributeTypeKeys ?? []) if (!keys.includes(key)) keys.push(key);
  }
  return keys;
}
