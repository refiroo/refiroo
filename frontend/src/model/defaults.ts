/**
 * Fallbacks used when a model omits optional configuration, so that a newly declared object type
 * is usable before anyone authors a detail view for it.
 */

import type { DetailViewDefinition, ObjectTypeDefinition, ObjectSort } from "@/types";

export const DEFAULT_WORKSPACE = "default";
export const DEFAULT_COLLECTION_QUERY = {
  search: "",
  states: [] as string[],
  sort: "name" as ObjectSort,
  pageSize: 20,
  filters: [],
};

export function fallbackDetail(objectType: ObjectTypeDefinition): DetailViewDefinition {
  return {
    objectTypeKey: objectType.key,
    breadcrumbs: { showApplication: true, showObjectType: true, showAncestors: true },
    header: {
      titleField: "name",
      subtitleField: objectType.displayAttributeTypeKey,
      showObjectType: true,
    },
    panels: [
      {
        key: "attributes",
        title: `${objectType.name} details`,
        type: "attributes",
        region: "main",
        order: 10,
        visible: true,
        config: {
          fields: objectType.attributes
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((binding) => binding.attributeTypeKey),
        },
      },
      {
        key: "hierarchy",
        title: "Hierarchy",
        type: "hierarchy",
        region: "side",
        order: 10,
        visible: true,
        config: { showParent: true, showAncestors: true },
      },
    ],
  };
}
