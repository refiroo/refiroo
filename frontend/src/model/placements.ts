/**
 * Where the model lets records stand (Base 0.8 C4). The rule is the engine's
 * (`services/model/placements.py`), served by `GET /model/placements` and attached to the model when
 * it loads; this module only reads it, so the browser and the engine cannot disagree. A model loaded
 * without it offers no place.
 */

import type { ApplicationDefinition, EngineModel } from "@/types";

function places(model: EngineModel, application: Pick<ApplicationDefinition, "key">) {
  return model.placements?.applications.find((item) => item.applicationKey === application.key);
}

function parent(model: EngineModel, application: ApplicationDefinition, objectTypeKey: string) {
  return places(model, application)?.parents.find((item) => item.objectTypeKey === objectTypeKey);
}

/**
 * Object types of the application whose records a record of `parentObjectTypeKey` can contain, in
 * the application's type order. A parent is always in its child's application.
 */
export function childObjectTypeKeys(
  model: EngineModel,
  application: ApplicationDefinition,
  parentObjectTypeKey: string,
): string[] {
  return parent(model, application, parentObjectTypeKey)?.childObjectTypeKeys ?? [];
}

/** Object types of the application whose records can contain a record of `childObjectTypeKey`. */
export function parentObjectTypeKeys(
  model: EngineModel,
  application: ApplicationDefinition,
  childObjectTypeKey: string,
): string[] {
  return (places(model, application)?.parents ?? [])
    .filter((item) => item.childObjectTypeKeys.includes(childObjectTypeKey))
    .map((item) => item.objectTypeKey);
}

/**
 * The types a record can become under a parent of `parentObjectTypeKey` (`null` is the top level),
 * as a restructuring decides it (ADR-034).
 */
export function possibleTypes(
  model: EngineModel,
  application: ApplicationDefinition,
  parentObjectTypeKey: string | null,
): string[] {
  if (parentObjectTypeKey === null) return places(model, application)?.topLevelObjectTypeKeys ?? [];
  return parent(model, application, parentObjectTypeKey)?.possibleObjectTypeKeys ?? [];
}

/**
 * Every object type a record of `objectTypeKey` can stand under, at any depth, from the served
 * placements of the applications that hold the type (0.16 AG4).
 */
export function ancestorObjectTypeKeys(model: EngineModel, objectTypeKey: string): string[] {
  const found: string[] = [];
  const pending = [objectTypeKey];
  while (pending.length) {
    const current = pending.pop()!;
    for (const application of model.applications.filter((item) => item.objectTypeKeys.includes(current))) {
      for (const key of parentObjectTypeKeys(model, application, current)) {
        if (!found.includes(key)) {
          found.push(key);
          pending.push(key);
        }
      }
    }
  }
  return found;
}
