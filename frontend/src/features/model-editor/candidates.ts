/**
 * Which records a relationship may choose (schema 0.9, Base 0.9 K7; APPLICATION_MODEL "Which records a
 * relationship may choose"): a binding's `candidates`, criteria for the records at its `from` end, its
 * `to` end, or both. The editor offers the fields an end can name (its name, its type's attributes but
 * JSON ones, the name and attributes of every type it can sit under) and each value type's operators;
 * the server validates every criterion at its pointer, as installation does.
 */

import type { ModelDraftOutline } from "@/types";
import { attributeTypeOf, objectTypeOf } from "@/features/model-editor/outline";

export type Criterion = { field: string; op: string; value: string | number | boolean };
export type Candidates = { from?: Criterion[]; to?: Criterion[] };
export type End = "from" | "to";

export type CandidateField = { value: string; label: string; valueType: string; attribute: boolean };

const TEXT_OPS = [
  { value: "eq", label: "is" },
  { value: "contains", label: "contains" },
  { value: "startsWith", label: "starts with" },
];
const ORDER_OPS = [
  { value: "eq", label: "is" },
  { value: "lt", label: "is less than" },
  { value: "lte", label: "is at most" },
  { value: "gt", label: "is more than" },
  { value: "gte", label: "is at least" },
];

/** The operators a field takes: its value type's, then is empty and, for an attribute, has no value. */
export function operatorsFor(field: CandidateField | undefined) {
  const base =
    !field || field.valueType === "text" || field.valueType === "longText"
      ? TEXT_OPS
      : field.valueType === "boolean"
        ? [{ value: "eq", label: "is" }]
        : ORDER_OPS;
  return [
    ...base,
    { value: "isNull", label: "is empty" },
    ...(field?.attribute ? [{ value: "isUnset", label: "has no value" }] : []),
  ];
}

/** The types a record of `typeKey` can sit under, at any depth (from the outline's parents). */
function ancestorsOf(outline: ModelDraftOutline, typeKey: string): string[] {
  const found: string[] = [];
  const pending = [...(objectTypeOf(outline, typeKey)?.parents ?? [])];
  while (pending.length) {
    const next = pending.shift()!;
    if (found.includes(next)) continue;
    found.push(next);
    pending.push(...(objectTypeOf(outline, next)?.parents ?? []));
  }
  return found;
}

function attributeFields(
  outline: ModelDraftOutline,
  typeKey: string,
  prefix: string,
  labelPrefix: string,
): CandidateField[] {
  return (objectTypeOf(outline, typeKey)?.attributes ?? [])
    .filter((binding) => binding.valueType !== "json")
    .map((binding) => ({
      value: `${prefix}${binding.attributeType}`,
      label: `${labelPrefix}${attributeTypeOf(outline, binding.attributeType)?.name ?? binding.attributeType}`,
      valueType: binding.valueType ?? "text",
      attribute: true,
    }));
}

/** The fields a criterion at an end may name. A type the outline does not hold yet offers its name. */
export function fieldsFor(outline: ModelDraftOutline, typeKey: string | undefined): CandidateField[] {
  const name: CandidateField = { value: "name", label: "Name", valueType: "text", attribute: false };
  if (!typeKey || !objectTypeOf(outline, typeKey)) return [name];
  return [
    name,
    ...attributeFields(outline, typeKey, "", ""),
    ...ancestorsOf(outline, typeKey).flatMap((ancestor) => {
      const label = objectTypeOf(outline, ancestor)?.name ?? ancestor;
      return [
        { value: `ancestor:${ancestor}.name`, label: `${label} (above) › Name`, valueType: "text", attribute: false },
        ...attributeFields(outline, ancestor, `ancestor:${ancestor}.`, `${label} (above) › `),
      ];
    }),
  ];
}

/** The value a criterion's text input holds, typed for its operator and value type. */
export function typedValue(field: CandidateField | undefined, op: string, raw: string): string | number | boolean {
  if (op === "isNull" || op === "isUnset") return raw !== "false";
  if (field?.valueType === "boolean") return raw === "true";
  if (field?.valueType === "integer" || field?.valueType === "decimal") return raw === "" ? raw : Number(raw);
  return raw;
}

/** Criteria with nothing left out; `undefined` when no end has any, which removes the rule. */
export function cleaned(candidates: Candidates | undefined): Candidates | null {
  const result: Candidates = {};
  for (const end of ["from", "to"] as const) {
    const items = (candidates?.[end] ?? []).filter((item) => item.field && item.op && item.value !== "");
    if (items.length) result[end] = items;
  }
  return Object.keys(result).length ? result : null;
}

/** The criteria in words, for a cell or a summary: "To: Name starts with “A”". */
export function describeCandidates(
  outline: ModelDraftOutline,
  candidates: Candidates | undefined,
  ends: Record<End, string | undefined>,
) {
  const parts: string[] = [];
  for (const end of ["from", "to"] as const) {
    const fields = fieldsFor(outline, ends[end]);
    for (const item of candidates?.[end] ?? []) {
      const field = fields.find((option) => option.value === item.field);
      const op = operatorsFor(field).find((option) => option.value === item.op)?.label ?? item.op;
      const shown =
        item.op === "isNull" || item.op === "isUnset" ? (item.value ? "" : " (not)") : ` “${String(item.value)}”`;
      parts.push(`${end === "from" ? "From" : "To"}: ${field?.label ?? item.field} ${op}${shown}`);
    }
  }
  return parts.join("; ");
}
