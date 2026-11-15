/**
 * Fallbacks used when a model omits optional configuration, so that a newly declared object type
 * is usable before anyone authors a detail view for it.
 */

import { objectTypeFor, relationTypeFor } from "@/model/lookup";
import type { DetailViewDefinition, ObjectTypeDefinition, ObjectSort, EngineModel, PanelDefinition } from "@/types";

export const DEFAULT_WORKSPACE = "default";
export const DEFAULT_COLLECTION_QUERY = {
  search: "",
  sort: "name" as ObjectSort,
  pageSize: 20,
  filters: [],
};

const MAX_RELATED_ATTRIBUTES = 4;

/** The attribute keys an object type binds, in their order. */
const attributesOf = (type: ObjectTypeDefinition) =>
  type.attributes
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((binding) => binding.attributeTypeKey);

const isContainment = (model: EngineModel, relationKey: string) =>
  Boolean(relationTypeFor(model, relationKey)?.features?.parentOf);

/** The types that directly contain `typeKey` (not itself, as a hierarchy of one type does). */
function parentTypeKeys(model: EngineModel, typeKey: string): string[] {
  const parents = objectTypeFor(model, typeKey)?.behavior?.parentRelationTypeKeys ?? [];
  return [
    ...new Set(
      model.objectTypeRelations
        .filter(
          (binding) =>
            parents.includes(binding.relationTypeKey) &&
            binding.toObjectTypeKey === typeKey &&
            binding.fromObjectTypeKey !== typeKey,
        )
        .map((binding) => binding.fromObjectTypeKey),
    ),
  ];
}

export interface HeldRelation {
  relationTypeKey: string;
  direction: "outgoing" | "incoming";
}

/**
 * The relationships a type holds, containment excluded, in the model's order: outgoing where it is at a
 * binding's `from` end, incoming at its `to` end. The server's rule for the page a type gets (0.13 RL,
 * `layout.held_relations`); the two are checked against one fixture.
 */
export function heldRelations(model: EngineModel, typeKey: string): HeldRelation[] {
  const held: HeldRelation[] = [];
  const add = (relationTypeKey: string, direction: HeldRelation["direction"]) => {
    if (!held.some((item) => item.relationTypeKey === relationTypeKey && item.direction === direction))
      held.push({ relationTypeKey, direction });
  };
  for (const binding of model.objectTypeRelations) {
    const relation = relationTypeFor(model, binding.relationTypeKey);
    if (!relation || isContainment(model, relation.key)) continue;
    if (binding.fromObjectTypeKey === typeKey) add(relation.key, "outgoing");
    if (binding.toObjectTypeKey === typeKey && relation.reverseKey) add(relation.key, "incoming");
  }
  return held;
}

/** The types at the other end of a relationship read from `typeKey`. */
function relatedTypeKeys(model: EngineModel, typeKey: string, held: HeldRelation): string[] {
  const outgoing = held.direction === "outgoing";
  return [
    ...new Set(
      model.objectTypeRelations
        .filter(
          (binding) =>
            binding.relationTypeKey === held.relationTypeKey &&
            (outgoing ? binding.fromObjectTypeKey : binding.toObjectTypeKey) === typeKey,
        )
        .map((binding) => (outgoing ? binding.toObjectTypeKey : binding.fromObjectTypeKey)),
    ),
  ];
}

/** What a relationship is called read from the type: `name` outgoing, `reverseName` incoming. */
export function relationshipTitle(model: EngineModel, held: HeldRelation): string {
  const relation = relationTypeFor(model, held.relationTypeKey);
  if (!relation) return held.relationTypeKey;
  return held.direction === "outgoing" ? relation.name : relation.reverseName || relation.name;
}

/**
 * The columns a relations panel gets: the name, the parent type the related records sit under (when
 * they all sit under one), up to four attributes of the related types and their type when there are
 * several types; with the sort a parent column gives when one type is listed.
 */
export function relationsPanelConfig(model: EngineModel, typeKey: string, held: HeldRelation) {
  const related = relatedTypeKeys(model, typeKey, held);
  const parents = new Set(related.map((key) => parentTypeKeys(model, key).join("|")));
  const [only] = parents.size === 1 ? [...parents] : [];
  const ancestor = only && !only.includes("|") ? `ancestor:${only}` : undefined;
  const attributes: string[] = [];
  for (const key of related) {
    const type = objectTypeFor(model, key);
    for (const attribute of type ? attributesOf(type) : [])
      if (!attributes.includes(attribute)) attributes.push(attribute);
  }
  const columns = [
    "name",
    ...(ancestor ? [ancestor] : []),
    ...attributes.slice(0, MAX_RELATED_ATTRIBUTES),
    ...(related.length > 1 ? ["objectType"] : []),
  ];
  return {
    relationTypeKeys: [held.relationTypeKey],
    direction: held.direction,
    columns,
    showRelationshipColumn: false,
    ...(ancestor && related.length === 1 ? { sortFields: [ancestor, "name"], defaultSort: ancestor } : {}),
  };
}

/** A relations panel for one relationship of a type, with the key and order the server gives it. */
export function relationsPanel(
  model: EngineModel,
  typeKey: string,
  held: HeldRelation,
  panels: readonly PanelDefinition[],
  title?: string,
  region: "main" | "side" = "main",
): PanelDefinition {
  const relation = relationTypeFor(model, held.relationTypeKey);
  const named = held.direction === "outgoing" ? held.relationTypeKey : relation?.reverseKey || held.relationTypeKey;
  const taken = new Set(panels.map((panel) => panel.key));
  let key = named;
  for (let n = 2; taken.has(key); n += 1) key = `${named}-${n}`;
  return {
    key,
    title: title || relationshipTitle(model, held),
    type: "relations",
    region,
    order: Math.max(0, ...panels.filter((panel) => panel.region === region).map((panel) => panel.order)) + 10,
    visible: true,
    config: relationsPanelConfig(model, typeKey, held),
  };
}

/** The types a type contains (a binding of a parent relation from it), in the model's order. */
export function containedTypes(model: EngineModel, typeKey: string): ObjectTypeDefinition[] {
  return model.objectTypes.filter((child) =>
    model.objectTypeRelations.some(
      (relation) =>
        relation.fromObjectTypeKey === typeKey &&
        relation.toObjectTypeKey === child.key &&
        (child.behavior?.parentRelationTypeKeys ?? []).includes(relation.relationTypeKey),
    ),
  );
}

/**
 * The page a type gets when its application declares none, and the one **Declare its page** writes
 * (0.13 RL; the server's `layout.detail_page`, checked against it on one fixture): the details and,
 * for a type with a parent, the hierarchy at the side; in the main region one panel for the contained
 * types, then one for each relationship the type holds in each direction.
 */
export function fallbackDetail(objectType: ObjectTypeDefinition, model: EngineModel): DetailViewDefinition {
  const childTypes = containedTypes(model, objectType.key);
  const panels: PanelDefinition[] = [
    {
      key: "attributes",
      title: "Details",
      type: "attributes",
      region: "side",
      order: 10,
      visible: true,
      config: { fields: attributesOf(objectType) },
    },
  ];
  if (objectType.behavior?.parentRelationTypeKeys?.length)
    panels.push({
      key: "hierarchy",
      title: "Hierarchy",
      type: "hierarchy",
      region: "side",
      order: 20,
      visible: true,
      config: { showParent: true, showAncestors: true },
    });
  if (childTypes.length)
    panels.push({
      key: "children",
      title: childTypes[0].pluralName || "Children",
      type: "children",
      region: "main",
      order: 10,
      visible: true,
      config: { objectTypeKeys: childTypes.map((child) => child.key), columns: ["name"], pageSize: 10 },
    });
  for (const held of heldRelations(model, objectType.key))
    panels.push(relationsPanel(model, objectType.key, held, panels));
  return {
    objectTypeKey: objectType.key,
    breadcrumbs: { showApplication: true, showObjectType: true, showAncestors: true },
    header: {
      titleField: "name",
      subtitleField: objectType.displayAttributeTypeKey,
      showObjectType: true,
    },
    panels,
  };
}
