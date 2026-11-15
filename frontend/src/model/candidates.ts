/**
 * Which records a relationship may choose (0.9 K7, D168–D172). A binding's `candidates` limit the
 * records at its ends; every picker for that relationship lists only those, read through the
 * per-type list's `candidateFor` and `anchorTypeKey`, and a record that does not meet its own end
 * is not offered the relationship, with the reason said in words.
 */

import { attributeTypeFor, relationTypeFor, typeName } from "@/model/lookup";
import type { CandidateCriterion, EngineModel, ObjectTypeRelationDefinition } from "@/types";

export type Direction = "outgoing" | "incoming";

/** How a picker asks the per-type list for candidates: the key read from the anchor's type. */
export interface CandidateScope {
  candidateFor: string;
  anchorTypeKey: string;
}

/** The relation key read `direction` from the anchor: its key outgoing, its reverse key incoming. */
export function relationKey(model: EngineModel, relationTypeKey: string, direction: Direction) {
  const definition = relationTypeFor(model, relationTypeKey);
  if (!definition) return relationTypeKey;
  return direction === "outgoing" ? definition.key : definition.reverseKey;
}

/** The criteria at an end: the far end reading `direction` from the anchor, or the anchor's own. */
export function criteriaAt(
  binding: ObjectTypeRelationDefinition,
  direction: Direction,
  end: "far" | "own",
): CandidateCriterion[] {
  const far = direction === "outgoing" ? "to" : "from";
  const own = far === "to" ? "from" : "to";
  return binding.candidates?.[end === "far" ? far : own] ?? [];
}

/** The scope a picker for the far end passes, or none when that end takes any record. */
export function candidateScope(
  model: EngineModel,
  binding: ObjectTypeRelationDefinition,
  direction: Direction,
  anchorTypeKey: string,
): CandidateScope | undefined {
  if (!criteriaAt(binding, direction, "far").length) return undefined;
  return { candidateFor: relationKey(model, binding.relationTypeKey, direction), anchorTypeKey };
}

/** The scope that lists the anchor's own type as candidates from the other end, so a record can be
 * asked whether it meets its own end (D172); none when the anchor's end takes any record. */
export function ownEndScope(
  model: EngineModel,
  binding: ObjectTypeRelationDefinition,
  direction: Direction,
): CandidateScope | undefined {
  if (!criteriaAt(binding, direction, "own").length) return undefined;
  const reverse: Direction = direction === "outgoing" ? "incoming" : "outgoing";
  const other = direction === "outgoing" ? binding.toObjectTypeKey : binding.fromObjectTypeKey;
  return { candidateFor: relationKey(model, binding.relationTypeKey, reverse), anchorTypeKey: other };
}

const OPERATORS: Record<string, string> = {
  eq: "is",
  contains: "contains",
  startsWith: "starts with",
  lt: "is less than",
  lte: "is at most",
  gt: "is more than",
  gte: "is at least",
};

/** A piece of a sentence; a mark says which pieces a reader's eye should find first. */
export interface WordPart {
  text: string;
  mark?: "parent" | "value";
}

/** The criteria in words: "under a Category whose name contains “Reserved”, whose Code starts with
 * “OK”". Alternatives on one field are joined with "or". */
export function describeCriteria(model: EngineModel, criteria: CandidateCriterion[]): string {
  return plainText(criteriaParts(model, criteria));
}

function criteriaParts(model: EngineModel, criteria: CandidateCriterion[]): WordPart[] {
  const parts: WordPart[] = [];
  const grouped = new Map<string, CandidateCriterion[]>();
  for (const criterion of criteria) grouped.set(criterion.field, [...(grouped.get(criterion.field) ?? []), criterion]);
  for (const [field, items] of grouped) {
    const ancestor = /^ancestor:([^.]+)\.(.+)$/.exec(field);
    const subject = fieldLabel(model, ancestor ? ancestor[2] : field);
    if (parts.length) parts.push({ text: ", " });
    if (ancestor) {
      const type = typeName(model, ancestor[1]);
      parts.push({ text: `under a ${type}`, mark: "parent" }, { text: " " });
    }
    items.forEach((item, index) => {
      if (index) parts.push({ text: " or " });
      parts.push(...condition(model, subject, ancestor ? ancestor[2] : field, item));
    });
  }
  return parts;
}

function plainText(parts: WordPart[]) {
  return parts.map((part) => part.text).join("");
}

function fieldLabel(model: EngineModel, field: string) {
  if (field === "name") return "name";
  return attributeTypeFor(model, field)?.name ?? field;
}

function condition(model: EngineModel, subject: string, field: string, item: CandidateCriterion): WordPart[] {
  if (item.op === "isNull" || item.op === "isUnset")
    return [{ text: item.value ? `with no ${subject}` : `with a ${subject}` }];
  const valueType = attributeTypeFor(model, field)?.valueType;
  if (valueType === "boolean")
    return [{ text: `with ${subject}: ` }, { text: item.value ? "Yes" : "No", mark: "value" }];
  return [
    { text: `whose ${subject} ${OPERATORS[item.op] ?? item.op} ` },
    { text: `“${String(item.value)}”`, mark: "value" },
  ];
}

/** What a picker for the far end offers, in words, or nothing when it takes any record. */
export function candidateHint(model: EngineModel, binding: ObjectTypeRelationDefinition, direction: Direction) {
  const criteria = criteriaAt(binding, direction, "far");
  if (!criteria.length) return undefined;
  const far = direction === "outgoing" ? binding.toObjectTypeKey : binding.fromObjectTypeKey;
  const plural = typeName(model, far, { plural: true });
  return `Offers only ${plural.toLowerCase()} ${describeCriteria(model, criteria)}.`;
}

/** Why a record cannot hold the relationship from its own end (D172), or nothing when it may. */
export function ownEndReason(model: EngineModel, binding: ObjectTypeRelationDefinition, direction: Direction) {
  const parts = ownEndReasonParts(model, binding, direction);
  return parts && plainText(parts);
}

/** The same reason in pieces, for a place that sets its marked pieces apart. */
export function ownEndReasonParts(
  model: EngineModel,
  binding: ObjectTypeRelationDefinition,
  direction: Direction,
): WordPart[] | undefined {
  const criteria = criteriaAt(binding, direction, "own");
  if (!criteria.length) return undefined;
  const own = direction === "outgoing" ? binding.fromObjectTypeKey : binding.toObjectTypeKey;
  const plural = typeName(model, own, { plural: true });
  return [
    { text: `Only ${plural.toLowerCase()} ` },
    ...criteriaParts(model, criteria),
    { text: " can have this relationship." },
  ];
}

/** The scope for a relation key read from `anchorTypeKey` (a filter's `related:<key>`), or none when
 * no binding behind it limits its far end. Each listed type then answers by its own binding. */
export function keyScope(model: EngineModel, key: string, anchorTypeKey: string): CandidateScope | undefined {
  const definition = model.relationTypes.find((item) => item.key === key || item.reverseKey === key);
  if (!definition) return undefined;
  const direction: Direction = key === definition.key ? "outgoing" : "incoming";
  const limited = model.objectTypeRelations.some(
    (binding) =>
      binding.relationTypeKey === definition.key &&
      (direction === "outgoing" ? binding.fromObjectTypeKey : binding.toObjectTypeKey) === anchorTypeKey &&
      criteriaAt(binding, direction, "far").length > 0,
  );
  return limited ? { candidateFor: key, anchorTypeKey } : undefined;
}
