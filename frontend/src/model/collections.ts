import { childObjectTypeKeys } from "@/model/placements";
import type { ApplicationDefinition, EngineModel, ViewDefinition } from "@/types";

export interface CollectionGroup {
  objectTypeKey: string;
  views: ViewDefinition[];
  defaultView: ViewDefinition;
}

export function viewSourceObjectTypeKey(view: ViewDefinition): string {
  if (view.type === "table") return view.objectTypeKey;
  if (view.type === "relationMatrix") return view.config.rowObjectTypeKey;
  if (view.type === "tree") return view.config.rootObjectTypeKeys[0];
  return view.config.direction === "outgoing" ? view.config.fromObjectTypeKey : view.config.toObjectTypeKey;
}

export function collectionGroups(application: ApplicationDefinition): CollectionGroup[] {
  const grouped = new Map<string, ViewDefinition[]>();
  for (const view of application.views) {
    const key = viewSourceObjectTypeKey(view);
    grouped.set(key, [...(grouped.get(key) ?? []), view]);
  }
  return [...grouped].map(([objectTypeKey, views]) => ({
    objectTypeKey,
    views,
    defaultView:
      views.find((view) => view.key === application.defaultView) ??
      views.find((view) => view.type === "table") ??
      views[0],
  }));
}

/** Object types of the application whose records may stand without a parent (`rootCreatable`). */
export function rootObjectTypeKeys(model: EngineModel, application: ApplicationDefinition): string[] {
  return application.objectTypeKeys.filter(
    (key) => model.objectTypes.find((item) => item.key === key)?.features.rootCreatable === true,
  );
}

export function childCollectionGroups(
  model: EngineModel,
  application: ApplicationDefinition,
  parentObjectTypeKey: string,
): CollectionGroup[] {
  const childTypes = new Set(childObjectTypeKeys(model, application, parentObjectTypeKey));
  return collectionGroups(application).filter((group) => childTypes.has(group.objectTypeKey));
}
