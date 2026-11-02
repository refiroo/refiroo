/**
 * Reads over a draft's outline (`GET /model-drafts/{id}/outline`, 0.10 A4a, D36) for the editor: names
 * by key, where a type stands, which relations a type starts. The outline is the server's: containment
 * and the released marks are never worked out here.
 */

import type {
  ModelDraftOutline,
  OutlineApplication,
  OutlineAttributeType,
  OutlineConsumerApi,
  OutlineElement,
  OutlineMark,
  OutlineObjectType,
  OutlineRelation,
  OutlineRelationType,
} from "@/types";
import { HUE_SLOTS, type Hue } from "@/model/hues";

export function objectTypeOf(outline: ModelDraftOutline, key: string): OutlineObjectType | undefined {
  return outline.objectTypes.find((item) => item.key === key);
}

export function applicationOf(outline: ModelDraftOutline, key: string): OutlineApplication | undefined {
  return outline.applications.find((item) => item.key === key);
}

export function relationTypeOf(outline: ModelDraftOutline, key: string): OutlineRelationType | undefined {
  return outline.relationTypes.find((item) => item.key === key);
}

export function attributeTypeOf(outline: ModelDraftOutline, key: string): OutlineAttributeType | undefined {
  return outline.attributeTypes.find((item) => item.key === key);
}

export function consumerApiOf(outline: ModelDraftOutline, key: string): OutlineConsumerApi | undefined {
  return outline.consumerApis.find((item) => item.key === key);
}

/** A type's name, or its key when the outline does not hold it. */
export function typeName(outline: ModelDraftOutline, key: string): string {
  return objectTypeOf(outline, key)?.name ?? key;
}

export const sameName = (outline: ModelDraftOutline, key: string) => {
  const name = objectTypeOf(outline, key)?.name.toLowerCase();
  return outline.objectTypes.filter((item) => item.name.toLowerCase() === name);
};

const listedIn = (outline: ModelDraftOutline, key: string) =>
  outline.applications.filter((item) => item.objectTypeKeys.includes(key)).map((item) => item.name);

/** A type's name, with what tells it apart where other types share the name: its applications, and
 * its key where those are the same too. */
export function typeLabel(outline: ModelDraftOutline, key: string) {
  const name = typeName(outline, key);
  const others = sameName(outline, key).filter((item) => item.key !== key);
  if (!others.length) return name;
  const applications = listedIn(outline, key).join(", ");
  const told = others.every((item) => listedIn(outline, item.key).join(", ") !== applications);
  return `${name} · ${told && applications ? applications : `${applications ? `${applications}, ` : ""}${key}`}`;
}

/** The type's hue by its position in the draft's types, as the record pages colour a type (ADR-040). */
export function draftTypeHue(outline: ModelDraftOutline, key: string): Hue | undefined {
  const index = outline.objectTypes.findIndex((item) => item.key === key);
  return index < 0 ? undefined : (((index % HUE_SLOTS) + 1) as Hue);
}

/** The applications listing a type. */
export function applicationsOf(outline: ModelDraftOutline, typeKey: string): OutlineApplication[] {
  return outline.applications.filter((item) => item.objectTypeKeys.includes(typeKey));
}

/** The relations a type takes part in, the ones it starts first. */
export function relationsOf(outline: ModelDraftOutline, typeKey: string): OutlineRelation[] {
  return [
    ...outline.relations.filter((item) => item.from === typeKey),
    ...outline.relations.filter((item) => item.to === typeKey && item.from !== typeKey),
  ];
}

/** Where a type stands, in words: its parents, or the top level. */
export function placeOf(outline: ModelDraftOutline, type: OutlineObjectType): string {
  const parents = type.parents.map((key) => typeName(outline, key));
  if (parents.length) return `Under ${parents.join(", ")}`;
  return type.rootCreatable ? "At the top level" : "Not placed: no parent and not at the top level";
}

/** What the history calls an element: its name in the draft, or its key once it is gone. */
export type ElementKind = "objectType" | "attributeType" | "relationType" | "application" | "group" | "consumerApi";

export function nameOf(outline: ModelDraftOutline) {
  return (kind: ElementKind, key: string, applicationKey = ""): string => {
    switch (kind) {
      case "objectType":
        return typeName(outline, key);
      case "attributeType":
        return attributeTypeOf(outline, key)?.name ?? key;
      case "relationType":
        return relationTypeOf(outline, key)?.name ?? key;
      case "application":
        return applicationOf(outline, key)?.name ?? key;
      case "group":
        return applicationOf(outline, applicationKey)?.navigation.groups.find((g) => g.key === key)?.label ?? key;
      case "consumerApi":
        return consumerApiOf(outline, key)?.name ?? key;
    }
  };
}

/** Whether an element is in the base release: a draft-only operation on it needs a migration. */
export function isReleased(mark: OutlineMark | undefined): boolean {
  return mark === "released" || mark === "changed";
}

export const MARK_LABELS: Record<OutlineMark, string> = { new: "New", changed: "Changed", released: "Released" };

/** What an issue's element is called, for its link. */
export function elementLabel(outline: ModelDraftOutline, element: OutlineElement): string {
  if (element.consumerApi)
    return `Consumer API ${consumerApiOf(outline, element.consumerApi)?.name ?? element.consumerApi}`;
  if (element.objectType && element.attributeType)
    return `${typeName(outline, element.objectType)} › ${attributeTypeOf(outline, element.attributeType)?.name ?? element.attributeType}`;
  if (element.objectType) return typeName(outline, element.objectType);
  if (element.relationType && element.from)
    return `${typeName(outline, element.from)} → ${typeName(outline, element.to)}`;
  if (element.relationType) return relationTypeOf(outline, element.relationType)?.name ?? element.relationType;
  if (element.attributeType) return attributeTypeOf(outline, element.attributeType)?.name ?? element.attributeType;
  if (element.applicationKey) {
    const name = applicationOf(outline, element.applicationKey)?.name ?? element.applicationKey;
    if (element.group) return `${name} › group ${element.group}`;
    if (element.view) return `${name} › view ${element.view}`;
    if (element.detail && element.panel)
      return `${name} › ${typeName(outline, element.detail)} page › panel ${element.panel}`;
    if (element.detail) return `${name} › ${typeName(outline, element.detail)} page`;
    return name;
  }
  return "the model";
}

/** Every key of the draft, for a key made from a label on the client (A-D6). */
export function keysOf(outline: ModelDraftOutline): Set<string> {
  return new Set([
    ...outline.objectTypes.map((item) => item.key),
    ...outline.attributeTypes.map((item) => item.key),
    ...outline.relationTypes.flatMap((item) => [item.key, item.reverseKey ?? ""]),
    ...outline.applications.map((item) => item.key),
  ]);
}

/**
 * A key from a label, as the server makes one (A-D6): lower-case, hyphen-separated ASCII, accents
 * dropped, `-2`, `-3` on a clash. The editor names the key itself only where one request creates an
 * element and refers to it (a new relation type allowed at once); the server still checks it.
 */
export function keyFromLabel(label: string, taken: Set<string>): string {
  // As the server: decomposed, then every character without an ASCII form dropped.
  const ascii = label.normalize("NFKD").replace(/[^\u0020-\u007e]/g, "");
  const base =
    ascii
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "element";
  let key = base;
  for (let suffix = 2; taken.has(key); suffix += 1) key = `${base}-${suffix}`;
  return key;
}

/**
 * The version install and activate proposes (D18): the draft's own when it already differs from its
 * base release's, otherwise the base's with its last number raised by one. Empty when no number
 * can be raised, so the user writes one.
 */
export function suggestedVersion(outline: ModelDraftOutline): string {
  const own = outline.release.version ?? "";
  const base = outline.baseRelease?.version ?? "";
  if (own && own !== base) return own;
  const match = /^(.*?)(\d+)(\D*)$/.exec(base);
  return match ? `${match[1]}${Number(match[2]) + 1}${match[3]}` : own;
}
