/**
 * Reads over the active model: resolving keys to definitions, and deriving which relationships a
 * panel may offer for an object type.
 */

import type { EngineModel, ObjectTypeRelationDefinition, RelationsPanelDefinition } from "@/types";

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

export function applicationFor(model: EngineModel, key: string) {
  return model.applications.find((item) => item.key === key);
}
