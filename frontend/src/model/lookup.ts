/**
 * Reads over the active model: resolving keys to definitions, and deriving which relationships a
 * panel, or a bulk change of a selection, may offer for an object type.
 */

import type {
  EngineModel,
  ObjectTypeDefinition,
  ObjectTypeRelationDefinition,
  RelationsPanelDefinition,
} from "@/types";

export function objectTypeFor(model: EngineModel, key: string) {
  return model.objectTypes.find((item) => item.key === key);
}

export interface RelationChoice {
  direction: "outgoing" | "incoming";
  relation: ObjectTypeRelationDefinition;
  otherObjectTypeKey: string;
  label: string;
}

export function isManagedRelation(model: EngineModel, relation: ObjectTypeRelationDefinition) {
  const target = objectTypeFor(model, relation.toObjectTypeKey);
  return (target?.behavior.parentRelationTypeKeys ?? []).includes(relation.relationTypeKey);
}

export function relationChoices(
  model: EngineModel,
  objectTypeKey: string,
  panel: RelationsPanelDefinition,
): RelationChoice[] {
  const allowedKeys = new Set(panel.config.relationTypeKeys);
  const choices: RelationChoice[] = [];
  for (const relation of model.objectTypeRelations) {
    if (!allowedKeys.has(relation.relationTypeKey) || relation.required || isManagedRelation(model, relation)) continue;
    const definition = model.relationTypes.find((item) => item.key === relation.relationTypeKey);
    if (!definition) continue;
    if (
      (panel.config.direction === "outgoing" || panel.config.direction === "both") &&
      relation.fromObjectTypeKey === objectTypeKey
    ) {
      choices.push({
        direction: "outgoing",
        relation,
        otherObjectTypeKey: relation.toObjectTypeKey,
        label: definition.name,
      });
    }
    if (
      (panel.config.direction === "incoming" || panel.config.direction === "both") &&
      relation.toObjectTypeKey === objectTypeKey
    ) {
      choices.push({
        direction: "incoming",
        relation,
        otherObjectTypeKey: relation.fromObjectTypeKey,
        label: definition.reverseName,
      });
    }
  }
  return choices;
}

/** What a bulk change may do to the selected records' relationships of one kind (0.9 K3, D128). */
export interface RelationActions {
  /** Relate every selected record to the records chosen. */
  add: boolean;
  /** Remove the relationship of every selected record to the records chosen. */
  remove: boolean;
  /** Make every selected record's relationships of this kind exactly the records chosen. */
  replace: boolean;
  /** As replace, with one record: each selected record holds one of these. */
  set: boolean;
  /** Remove every selected record's relationships of this kind. */
  clear: boolean;
}

export interface BulkRelationChoice extends RelationChoice {
  actions: RelationActions;
}

/**
 * The relationships a bulk change offers for a type (0.9 K3, D127): every binding with the type at
 * either end, in both directions, except containment and required ownership, and not limited by any
 * panel. Its actions follow the cardinality seen from the selected type's end and `required`
 * (D128): an end that holds one is set, not added to; an other end that holds one is only removed
 * from, since one record added to several selected records would be refused for all but the
 * first; a required relationship is never removed or cleared.
 */
export function bulkRelationChoices(model: EngineModel, objectTypeKey: string): BulkRelationChoice[] {
  const choices: BulkRelationChoice[] = [];
  for (const relation of model.objectTypeRelations) {
    if (isManagedRelation(model, relation)) continue;
    if (relation.required && relation.cardinality !== "many-to-many") continue;
    const definition = model.relationTypes.find((item) => item.key === relation.relationTypeKey);
    if (!definition) continue;
    const ends = [
      ["outgoing", relation.fromObjectTypeKey, relation.toObjectTypeKey, definition.name],
      ["incoming", relation.toObjectTypeKey, relation.fromObjectTypeKey, definition.reverseName],
    ] as const;
    for (const [direction, own, other, label] of ends) {
      if (own !== objectTypeKey) continue;
      const oneHere =
        relation.cardinality === "one-to-one" || (relation.cardinality === "one-to-many" && direction === "incoming");
      const oneThere =
        relation.cardinality === "one-to-one" || (relation.cardinality === "one-to-many" && direction === "outgoing");
      const removable = !relation.required;
      const actions: RelationActions = {
        add: !oneHere && !oneThere,
        // Where each selected record holds one, Set to and Clear say it; Remove adds nothing.
        remove: removable && (!oneHere || oneThere),
        replace: !oneHere && !oneThere,
        set: oneHere && !oneThere,
        clear: removable,
      };
      if (Object.values(actions).some(Boolean))
        choices.push({ direction, relation, otherObjectTypeKey: other, label, actions });
    }
  }
  return choices;
}

export function applicationFor(model: EngineModel, key: string) {
  return model.applications.find((item) => item.key === key);
}

/**
 * The object types the model allows at the other end of an anchor's relations, as the relation
 * query derives them; without relation type keys, every relation type counts.
 */
export function relatedObjectTypes(
  model: EngineModel,
  anchorTypeKey: string,
  direction: "outgoing" | "incoming" | "both",
  relationTypeKeys?: readonly string[],
): ObjectTypeDefinition[] {
  const keys: string[] = [];
  for (const allowed of model.objectTypeRelations) {
    if (relationTypeKeys?.length && !relationTypeKeys.includes(allowed.relationTypeKey)) continue;
    if (direction !== "incoming" && allowed.fromObjectTypeKey === anchorTypeKey) keys.push(allowed.toObjectTypeKey);
    if (direction !== "outgoing" && allowed.toObjectTypeKey === anchorTypeKey) keys.push(allowed.fromObjectTypeKey);
  }
  return [...new Set(keys)].flatMap((key) => {
    const definition = objectTypeFor(model, key);
    return definition ? [definition] : [];
  });
}
