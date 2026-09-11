/**
 * Fallbacks used when a model omits optional configuration, so that a newly declared object type
 * is usable before anyone authors a detail view for it.
 */

import type { DetailViewDefinition, ObjectTypeDefinition, ObjectSort, EngineModel, PanelDefinition } from "@/types";

export const DEFAULT_WORKSPACE = "default";
export const DEFAULT_COLLECTION_QUERY = {
  search: "",
  sort: "name" as ObjectSort,
  pageSize: 20,
  filters: [],
};

export function fallbackDetail(objectType: ObjectTypeDefinition, model: EngineModel): DetailViewDefinition {
  const allowed = model.objectTypeRelations.filter(
    (relation) => relation.fromObjectTypeKey === objectType.key || relation.toObjectTypeKey === objectType.key,
  );
  const childTypes = model.objectTypes.filter((child) =>
    allowed.some(
      (relation) =>
        relation.fromObjectTypeKey === objectType.key &&
        relation.toObjectTypeKey === child.key &&
        (child.behavior.parentRelationTypeKeys ?? []).includes(relation.relationTypeKey),
    ),
  );
  const relatedPanels: PanelDefinition[] = childTypes.map((child, index) => ({
    key: `children-${child.key}`,
    title: child.pluralName,
    type: "children",
    region: "main",
    order: (index + 1) * 10,
    visible: true,
    config: {
      objectTypeKeys: [child.key],
      columns: [
        "name",
        ...child.attributes
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((binding) => binding.attributeTypeKey),
      ],
      pageSize: 10,
    },
  }));
  if (allowed.length)
    relatedPanels.push({
      key: "relationships",
      title: "Relationships",
      type: "relations",
      region: "main",
      order: (childTypes.length + 1) * 10,
      visible: true,
      config: {
        relationTypeKeys: [...new Set(allowed.map((relation) => relation.relationTypeKey))],
        direction: "both",
        columns: ["name", "objectType"],
      },
    });
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
        region: "side",
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
        order: 20,
        visible: true,
        config: { showParent: true, showAncestors: true },
      },
      ...relatedPanels,
    ],
  };
}
