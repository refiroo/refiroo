import { objectTypeFor } from "@/model/lookup";
import { childObjectTypeKeys } from "@/model/placements";
import type {
  ApplicationDefinition,
  EngineModel,
  NavigationGroupDefinition,
  RelationMatrixViewDefinition,
  ViewDefinition,
} from "@/types";

export interface CollectionGroup {
  objectTypeKey: string;
  views: ViewDefinition[];
  defaultView: ViewDefinition;
}

export function viewSourceObjectTypeKey(view: ViewDefinition): string {
  if (view.type === "table") return view.objectTypeKey;
  if (view.type === "relationMatrix") return view.config.rowObjectTypeKey;
  if (view.type === "tree") return view.config.rootObjectTypeKeys[0];
  if (view.type === "relationTable") return view.config.fromObjectTypeKey;
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
    // The view the collection's entry opens on: the one the navigation names for it, else the
    // application's default view, else its table.
    defaultView:
      views.find((view) => view.key === application.navigation?.opens?.[objectTypeKey]) ??
      views.find((view) => view.key === application.defaultView) ??
      views.find((view) => view.type === "table") ??
      views[0],
  }));
}

/** An entry of a navigation group: a collection, or a relation matrix standing on its own. */
export type NavigationEntry =
  | { kind: "collection"; collection: CollectionGroup }
  | { kind: "matrix"; view: RelationMatrixViewDefinition; rowObjectTypeKey: string };

/** The key an entry is listed under, unique within an application's sidebar. */
export const navigationEntryKey = (entry: NavigationEntry) =>
  entry.kind === "collection" ? `collection:${entry.collection.objectTypeKey}` : `view:${entry.view.key}`;

/** A declared navigation group with the entries it names, in its order. */
export interface NavigationSection {
  group: NavigationGroupDefinition;
  entries: NavigationEntry[];
}

/**
 * The sidebar's collections (0.10 N1, D22): those in no group first, in their own order, then each
 * declared group in declared order with its entries in its order. A relation matrix placed in a group
 * is an entry of its own there; one placed nowhere stays a lens of its row type's collection. Without
 * groups, every collection is ungrouped, as before schema 0.10.
 */
export function navigationSections(application: ApplicationDefinition): {
  ungrouped: CollectionGroup[];
  groups: NavigationSection[];
} {
  const collections = collectionGroups(application);
  const byType = new Map(collections.map((collection) => [collection.objectTypeKey, collection]));
  const matrices = new Map(
    application.views.flatMap((view) => (view.type === "relationMatrix" ? [[view.key, view] as const] : [])),
  );
  const groups = (application.navigation?.groups ?? []).map((group) => ({
    group,
    entries: group.collections.flatMap((entry): NavigationEntry[] => {
      if (typeof entry === "string") {
        const collection = byType.get(entry);
        return collection ? [{ kind: "collection", collection }] : [];
      }
      const view = matrices.get(entry.view);
      return view ? [{ kind: "matrix", view, rowObjectTypeKey: view.config.rowObjectTypeKey }] : [];
    }),
  }));
  const grouped = new Set(
    groups.flatMap((section) =>
      section.entries.flatMap((entry) => (entry.kind === "collection" ? [entry.collection.objectTypeKey] : [])),
    ),
  );
  return { ungrouped: collections.filter((item) => !grouped.has(item.objectTypeKey)), groups };
}

/** What the sidebar calls an entry: a collection's plural name, a matrix's view name. */
export function entryLabel(model: EngineModel, entry: NavigationEntry): string {
  return entry.kind === "collection"
    ? (objectTypeFor(model, entry.collection.objectTypeKey)?.pluralName ?? entry.collection.objectTypeKey)
    : entry.view.name;
}

/** The sidebar's entries as one list, in the order it shows them: those in no group, then each group's. */
export function navigationEntries(sections: ReturnType<typeof navigationSections>): NavigationEntry[] {
  return [
    ...sections.ungrouped.map((collection): NavigationEntry => ({ kind: "collection", collection })),
    ...sections.groups.flatMap((section) => section.entries),
  ];
}

/**
 * The sidebar narrowed to the entries whose label contains `text` (case-insensitive), in every group
 * and among the ungrouped; a group without a match is left out (0.13 LB). `matches` counts the
 * entries kept.
 */
export function narrowNavigation(
  model: EngineModel,
  sections: ReturnType<typeof navigationSections>,
  text: string,
): { sections: ReturnType<typeof navigationSections>; matches: number } {
  const needle = text.trim().toLowerCase();
  const matching = (entry: NavigationEntry) => entryLabel(model, entry).toLowerCase().includes(needle);
  const groups = sections.groups
    .map((section) => ({ ...section, entries: section.entries.filter(matching) }))
    .filter((section) => section.entries.length > 0);
  const ungrouped = sections.ungrouped.filter((collection) => matching({ kind: "collection", collection }));
  return {
    sections: { ungrouped, groups },
    matches: ungrouped.length + groups.reduce((total, section) => total + section.entries.length, 0),
  };
}

/** The relation matrices placed in a group of the application, by view key. */
export function placedMatrixKeys(application: ApplicationDefinition): Set<string> {
  return new Set(
    (application.navigation?.groups ?? []).flatMap((group) =>
      group.collections.flatMap((entry) => (typeof entry === "string" ? [] : [entry.view])),
    ),
  );
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
