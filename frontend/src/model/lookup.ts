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

/** Whether a record at `end` holds at most one relationship of the binding (0.9 K3a, D138). */
export function holdsOne(relation: ObjectTypeRelationDefinition, end: "from" | "to"): boolean {
  return (
    relation.cardinality === "one-to-one" || relation.cardinality === (end === "from" ? "many-to-one" : "one-to-many")
  );
}

/** Whether the record a choice starts from holds at most one relationship of its kind. */
export function holdsOneHere(choice: RelationChoice): boolean {
  return holdsOne(choice.relation, choice.direction === "outgoing" ? "from" : "to");
}

/** A required-ownership binding: required, and one owner per owned record. */
export function isRequiredOwnership(relation: ObjectTypeRelationDefinition): boolean {
  return Boolean(relation.required) && holdsOne(relation, "to");
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
    if (isRequiredOwnership(relation)) continue;
    const definition = model.relationTypes.find((item) => item.key === relation.relationTypeKey);
    if (!definition) continue;
    const ends = [
      ["outgoing", relation.fromObjectTypeKey, relation.toObjectTypeKey, definition.name],
      ["incoming", relation.toObjectTypeKey, relation.fromObjectTypeKey, definition.reverseName],
    ] as const;
    for (const [direction, own, other, label] of ends) {
      if (own !== objectTypeKey) continue;
      const oneHere = holdsOne(relation, direction === "outgoing" ? "from" : "to");
      const oneThere = holdsOne(relation, direction === "outgoing" ? "to" : "from");
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

/** A list column of each row's related records, `related:<key>` (0.9 K5, D140). */
export const RELATED_FIELD_PREFIX = "related:";

export interface RelatedColumn {
  relationTypeKey: string;
  direction: "outgoing" | "incoming";
  /** The relation's name read in that direction: its header. */
  name: string;
  /** The field each related record shows (0.9 K5a); absent: its name. */
  field?: string;
}

/**
 * What a `related:<key>` or `related:<key>.<field>` column reads: `<key>` is a relation type's key
 * (read outgoing) or reverse key (read incoming); the two share one namespace, so the key alone names
 * the direction. A key may contain a dot, so the text is the whole key when it is one, otherwise the
 * longest key it starts with, then a dot and the field (D148), as the engine resolves it.
 */
export function relatedColumn(model: EngineModel, field: string): RelatedColumn | undefined {
  if (!field.startsWith(RELATED_FIELD_PREFIX)) return undefined;
  const text = field.slice(RELATED_FIELD_PREFIX.length);
  const keys = model.relationTypes.flatMap((item) => [item.key, item.reverseKey]);
  const key = keys.includes(text)
    ? text
    : keys.filter((candidate) => text.startsWith(`${candidate}.`)).sort((a, b) => b.length - a.length)[0];
  if (!key) return undefined;
  const relationType = model.relationTypes.find((item) => item.key === key || item.reverseKey === key);
  if (!relationType) return undefined;
  const outgoing = relationType.key === key;
  const shown = text === key ? undefined : text.slice(key.length + 1);
  return {
    relationTypeKey: relationType.key,
    direction: outgoing ? "outgoing" : "incoming",
    name: outgoing ? relationType.name : relationType.reverseName || relationType.name,
    ...(shown && shown !== "name" ? { field: shown } : {}),
  };
}

/** The object types at the other end of a `related:<key>` field for records of `objectTypeKey`. */
export function relatedTargetTypes(model: EngineModel, objectTypeKey: string, field: string): ObjectTypeDefinition[] {
  const column = relatedColumn(model, field);
  if (!column) return [];
  const keys = model.objectTypeRelations
    .filter((relation) => relation.relationTypeKey === column.relationTypeKey)
    .filter((relation) =>
      column.direction === "outgoing"
        ? relation.fromObjectTypeKey === objectTypeKey
        : relation.toObjectTypeKey === objectTypeKey,
    )
    .map((relation) => (column.direction === "outgoing" ? relation.toObjectTypeKey : relation.fromObjectTypeKey));
  return [...new Set(keys)].flatMap((key) => objectTypeFor(model, key) ?? []);
}

/**
 * The label of a related records' field (D152): an attribute's name; for `ancestor:<type>.<field>`
 * the ancestor type's name for its name, otherwise the field's own label.
 */
export function relatedFieldLabel(model: EngineModel, field: string): string {
  const attributeName = (key: string) => model.attributeTypes.find((item) => item.key === key)?.name ?? key;
  if (!field.startsWith("ancestor:")) return field === "id" ? "ID" : attributeName(field);
  const reference = field.slice("ancestor:".length);
  const dot = reference.indexOf(".");
  const typeKey = reference.slice(0, dot);
  const name = reference.slice(dot + 1);
  if (name === "name") return objectTypeFor(model, typeKey)?.name ?? typeKey;
  return name === "id" ? "ID" : attributeName(name);
}

/**
 * Whether a row of `objectTypeKey` holds at most one record in a `related:` column, so the column
 * sorts (D145): exactly one binding stands behind it, and the listed end of it holds one.
 */
export function isSingleValuedRelatedColumn(model: EngineModel, objectTypeKey: string, field: string): boolean {
  const column = relatedColumn(model, field);
  if (!column || column.field) return false;
  const end = column.direction === "outgoing" ? "from" : "to";
  const bindings = model.objectTypeRelations.filter(
    (relation) =>
      relation.relationTypeKey === column.relationTypeKey &&
      (end === "from" ? relation.fromObjectTypeKey : relation.toObjectTypeKey) === objectTypeKey,
  );
  return bindings.length === 1 && holdsOne(bindings[0], end);
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
