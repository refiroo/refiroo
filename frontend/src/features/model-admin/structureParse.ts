/**
 * A defensive, typed read of a release's raw model for the Structure tab. The model is the stored
 * JSON of any schema version, so every field is checked and a missing one reads as empty; nothing
 * here knows an application or object-type key. An object type belongs to an application through the
 * application's `objectTypeKeys` (a type may stand in several applications).
 */

export interface StructureAttribute {
  key: string;
  name: string;
  valueType: string;
  required: boolean;
  readOnly: boolean;
  unique: boolean;
  minimum?: number;
  maximum?: number;
}

export interface StructureRelation {
  relationTypeKey: string;
  name: string;
  reverseName: string;
  /** "out": this type is the `from` end; "in": it is the `to` end. */
  direction: "out" | "in";
  otherTypeKey: string;
  otherTypeName: string;
}

export interface StructureObjectType {
  key: string;
  name: string;
  icon?: string;
  attributes: StructureAttribute[];
  relations: StructureRelation[];
}

export interface StructureApplication {
  key: string;
  name: string;
  icon?: string;
  viewCount: number;
  objectTypes: StructureObjectType[];
}

export interface Structure {
  applications: StructureApplication[];
  /** Object type keys in model order, the basis of hues (`model/hues`). */
  objectTypeKeys: string[];
}

type Obj = Record<string, unknown>;

const isObj = (value: unknown): value is Obj => !!value && typeof value === "object" && !Array.isArray(value);
const objects = (value: unknown): Obj[] => (Array.isArray(value) ? value.filter(isObj) : []);
const text = (value: unknown): string | undefined => (typeof value === "string" && value !== "" ? value : undefined);
const num = (value: unknown): number | undefined =>
  typeof value === "number" && Number.isFinite(value) ? value : undefined;

export function parseAttributes(objectType: Obj, attributeTypes: Obj[]): StructureAttribute[] {
  const byKey = new Map(
    attributeTypes.flatMap((item) => (text(item.key) ? [[item.key as string, item] as const] : [])),
  );
  return objects(objectType.attributes)
    .map((binding) => ({ binding, key: text(binding.attributeTypeKey) }))
    .filter((item): item is { binding: Obj; key: string } => !!item.key)
    .sort((a, b) => (num(a.binding.order) ?? 0) - (num(b.binding.order) ?? 0))
    .map(({ binding, key }) => {
      const type = byKey.get(key);
      const validation = isObj(type?.validation) ? type.validation : {};
      const features = isObj(type?.features) ? type.features : {};
      return {
        key,
        name: text(type?.name) ?? key,
        valueType: text(type?.valueType) ?? "text",
        required: binding.required === true,
        readOnly: binding.readOnly === true,
        unique: features.unique === true,
        minimum: num(validation.minimum),
        maximum: num(validation.maximum),
      };
    });
}

export function parseRelations(typeKey: string, relationTypes: Obj[], bindings: Obj[], names: Map<string, string>) {
  const byKey = new Map(relationTypes.flatMap((item) => (text(item.key) ? [[item.key as string, item] as const] : [])));
  const result: StructureRelation[] = [];
  for (const binding of bindings) {
    const relationTypeKey = text(binding.relationTypeKey);
    const from = text(binding.fromObjectTypeKey);
    const to = text(binding.toObjectTypeKey);
    if (!relationTypeKey || !from || !to || (from !== typeKey && to !== typeKey)) continue;
    const relation = byKey.get(relationTypeKey);
    const name = text(relation?.name) ?? relationTypeKey;
    const reverseName = text(relation?.reverseName) ?? "";
    // A relation from a type to itself is listed once, from its forward end.
    const direction = from === typeKey ? "out" : "in";
    const otherTypeKey = direction === "out" ? to : from;
    result.push({
      relationTypeKey,
      name,
      reverseName,
      direction,
      otherTypeKey,
      otherTypeName: names.get(otherTypeKey) ?? otherTypeKey,
    });
  }
  return result;
}

/** Reads the structure; `undefined` when the document does not have the expected shape. */
export function parseStructure(model: unknown): Structure | undefined {
  if (!isObj(model) || !Array.isArray(model.applications) || !Array.isArray(model.objectTypes)) return undefined;
  const attributeTypes = objects(model.attributeTypes);
  const relationTypes = objects(model.relationTypes);
  const bindings = objects(model.objectTypeRelations);
  const typeObjects = objects(model.objectTypes).filter((item) => text(item.key));
  const names = new Map(typeObjects.map((item) => [item.key as string, text(item.name) ?? (item.key as string)]));
  const types = new Map<string, StructureObjectType>(
    typeObjects.map((item) => {
      const key = item.key as string;
      return [
        key,
        {
          key,
          name: names.get(key) as string,
          icon: text(item.icon),
          attributes: parseAttributes(item, attributeTypes),
          relations: parseRelations(key, relationTypes, bindings, names),
        },
      ];
    }),
  );
  const applications = objects(model.applications)
    .filter((item) => text(item.key))
    .map((item) => {
      const keys = Array.isArray(item.objectTypeKeys) ? item.objectTypeKeys : [];
      return {
        key: item.key as string,
        name: text(item.name) ?? (item.key as string),
        icon: text(item.icon),
        viewCount: Array.isArray(item.views) ? item.views.length : 0,
        objectTypes: keys.flatMap((key) => {
          const type = typeof key === "string" ? types.get(key) : undefined;
          return type ? [type] : [];
        }),
      };
    });
  return { applications, objectTypeKeys: typeObjects.map((item) => item.key as string) };
}
