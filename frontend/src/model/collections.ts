import { childObjectTypeKeys } from "@/model/placements";
import type { ApplicationDefinition, EngineModel, NavigationGroupDefinition, ViewDefinition } from "@/types";

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

/** A declared navigation group with the collections it names, in its order. */
export interface NavigationSection {
  group: NavigationGroupDefinition;
  collections: CollectionGroup[];
}

/**
 * The sidebar's collections (0.10 N1, D22): those in no group first, in their own order, then each
 * declared group in declared order with its collections in its order. Without groups, every
 * collection is ungrouped, as before schema 0.10.
 */
export function navigationSections(application: ApplicationDefinition): {
  ungrouped: CollectionGroup[];
  groups: NavigationSection[];
} {
  const collections = collectionGroups(application);
  const byType = new Map(collections.map((collection) => [collection.objectTypeKey, collection]));
  const groups = (application.navigation?.groups ?? []).map((group) => ({
    group,
    collections: group.collections.flatMap((key) => byType.get(key) ?? []),
  }));
  const grouped = new Set(groups.flatMap((section) => section.collections.map((item) => item.objectTypeKey)));
  return { ungrouped: collections.filter((item) => !grouped.has(item.objectTypeKey)), groups };
}

/** The application's navigation group with this key, if it declares one. */
export function navigationGroupFor(application: ApplicationDefinition | undefined, groupKey: string) {
  return application?.navigation?.groups.find((group) => group.key === groupKey);
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
