/**
 * The move editor's reading of a mapping (0.11 X4): each mapped source type as a block of rows (its
 * target, attributes, relationships, parent, match and the defaults the target needs), each row
 * with its choices, the operations a choice sends, and whether it is still as the inference proposed
 * it (D141). The rules stay the engine's: a choice the mapping cannot take is refused by the step
 * (`INVALID_OPERATION`) and shown at its row.
 */

import { attributeName } from "@/model/fields";
import { attributeTypeFor, objectTypeFor, relationTypeFor, typeName } from "@/model/lookup";
import type {
  EngineModel,
  MappingMatch,
  MappingOperation,
  MappingParent,
  MappingProblem,
  MappingProposal,
  MappingTypeEntry,
  ModelMapping,
  ObjectTypeRelationDefinition,
} from "@/types";

export const NOT_MAPPED = "";

export interface RowOption {
  value: string;
  label: string;
}

export type RowKind = "type" | "attribute" | "relation" | "parent" | "match" | "default";

export interface MappingRow {
  /** Unique within its block: `type`, `attribute:{key}`, `relation:{key}`, `parent`, `match`, `default:{key}`. */
  key: string;
  kind: RowKind;
  label: string;
  /** What the source side is: a field's value type, a relationship, the parent. */
  detail: string;
  value: string;
  options: RowOption[];
  /** The proposal the row is still as (D141); none once it was changed by hand. */
  proposal?: MappingProposal;
  /** The operations that set the row to `value`. */
  operations: (value: string) => MappingOperation[];
  /** For a default row: the target attribute whose value is typed in. */
  attributeTypeKey?: string;
  defaultValue?: unknown;
  problems: MappingProblem[];
}

export interface MappingBlock {
  sourceType: string;
  sourceName: string;
  targetType: string;
  targetName: string;
  rows: MappingRow[];
  problems: MappingProblem[];
}

const name = (model: EngineModel, key: string) => typeName(model, key);
const relationName = (model: EngineModel, key: string, direction: "outgoing" | "incoming" = "outgoing") => {
  const relation = relationTypeFor(model, key);
  if (!relation) return key;
  return direction === "incoming" ? relation.reverseName : relation.name;
};

/** The relation types that place a record under its parent. */
function containment(model: EngineModel): Set<string> {
  return new Set(model.objectTypes.flatMap((type) => type.behavior.parentRelationTypeKeys ?? []));
}

/** The relationships other than containment a record of the type holds at their `from` end. */
export function relationsFrom(model: EngineModel, typeKey: string): ObjectTypeRelationDefinition[] {
  const parents = containment(model);
  const seen = new Set<string>();
  return model.objectTypeRelations.filter((item) => {
    if (item.fromObjectTypeKey !== typeKey || parents.has(item.relationTypeKey) || seen.has(item.relationTypeKey))
      return false;
    seen.add(item.relationTypeKey);
    return true;
  });
}

/** Where a type's records may stand: (containment relation, parent type). */
function parentsOf(model: EngineModel, typeKey: string): { relation: string; parentType: string }[] {
  const own = new Set(objectTypeFor(model, typeKey)?.behavior.parentRelationTypeKeys ?? []);
  return model.objectTypeRelations
    .filter((item) => item.toObjectTypeKey === typeKey && own.has(item.relationTypeKey))
    .map((item) => ({ relation: item.relationTypeKey, parentType: item.fromObjectTypeKey }));
}

const same = (left: unknown, right: unknown) => JSON.stringify(left ?? null) === JSON.stringify(right ?? null);

/** The operation of `kind` a proposal sends for one element. */
function proposed(proposal: MappingProposal | undefined, kind: string, match: Record<string, unknown> = {}) {
  return proposal?.operations.find(
    (operation) => operation.kind === kind && Object.entries(match).every(([key, value]) => operation[key] === value),
  );
}

/**
 * Whether a row is still as its proposal set it (D141): the proposal applied or held (held: the
 * mapping decides something else of it), the type still mapped as proposed, and the row's own value
 * the one the proposal's operation set. Changed by hand, it is the administrator's; undone, as
 * proposed again.
 */
export function stillProposed(
  entry: MappingTypeEntry,
  typeProposal: MappingProposal | undefined,
  row: { kind: RowKind; attribute?: string; relation?: string },
  relationProposal?: MappingProposal,
): MappingProposal | undefined {
  const live = (proposal?: MappingProposal) =>
    proposal && (proposal.status === "applied" || proposal.status === "held") ? proposal : undefined;
  if (row.kind === "relation") {
    const proposal = live(relationProposal);
    const operation = proposed(proposal, "mapRelation", { relation: row.relation });
    const current = entry.relations.find((item) => item.source === row.relation);
    if (!proposal || !operation || !current) return undefined;
    return current.target === operation.target && current.direction === operation.direction ? proposal : undefined;
  }
  const proposal = live(typeProposal);
  if (!proposal || proposal.target !== entry.target) return undefined;
  if (row.kind === "type") return proposal;
  if (row.kind === "attribute") {
    const operation = proposed(proposal, "mapAttribute", { attribute: row.attribute });
    const current = entry.attributes.find((item) => item.source === row.attribute);
    if (!operation || !current || current.ignore || current.valueMap) return undefined;
    return current.target === operation.target ? proposal : undefined;
  }
  if (row.kind === "parent") {
    const operation = proposed(proposal, "setParent");
    return operation && same(entry.parent, operation.parent) ? proposal : undefined;
  }
  if (row.kind === "match") {
    const operation = proposed(proposal, "setMatch");
    return operation && same(entry.match, operation.match) ? proposal : undefined;
  }
  return undefined;
}

const encodeParent = (parent: MappingParent | null | undefined): string =>
  !parent ? "top" : "from" in parent ? `source:${parent.relationTypeKey ?? ""}:${parent.missing ?? ""}` : "named";

const encodeMatch = (match: MappingMatch | null | undefined): string =>
  !match ? "" : "field" in match ? "name" : `attribute:${match.attributeTypeKey}`;

/** The problems pointing into a type's entry (`/types/{index}…`), and those of one of its parts. */
function problemsAt(problems: MappingProblem[], index: number, part = "") {
  const prefix = `/types/${index}${part}`;
  return problems.filter((problem) => problem.pointer === prefix || problem.pointer.startsWith(`${prefix}/`));
}

/** Each mapped source type's block of rows, in the mapping's order. */
export function mappingBlocks(
  mapping: ModelMapping,
  source: EngineModel,
  target: EngineModel,
  proposals: MappingProposal[],
): MappingBlock[] {
  return mapping.types.map((entry, index) => {
    const sourceType = entry.source;
    const typeProposal = proposals.find((item) => item.kind === "type" && item.sourceType === sourceType);
    const sourceDefinition = objectTypeFor(source, sourceType);
    const targetDefinition = objectTypeFor(target, entry.target);
    const targetAttributes = (targetDefinition?.attributes ?? []).map((binding) => ({
      value: binding.attributeTypeKey,
      label: attributeName(target, binding.attributeTypeKey),
    }));
    const rows: MappingRow[] = [];

    rows.push({
      key: "type",
      kind: "type",
      label: name(source, sourceType),
      detail: "Type",
      value: entry.target,
      options: [
        { value: NOT_MAPPED, label: "Not mapped (reported)" },
        ...target.objectTypes.map((type) => ({ value: type.key, label: type.name })),
      ],
      proposal: stillProposed(entry, typeProposal, { kind: "type" }),
      operations: (value) =>
        value === NOT_MAPPED
          ? [{ kind: "unmapType", sourceType }]
          : [{ kind: "mapType", sourceType, targetType: value }],
      problems: problems(mapping, index, "/target"),
    });

    for (const binding of sourceDefinition?.attributes ?? []) {
      const attribute = binding.attributeTypeKey;
      const current = entry.attributes.find((item) => item.source === attribute);
      const valueType = attributeTypeFor(source, attribute)?.valueType ?? "";
      const at = entry.attributes.indexOf(current!);
      rows.push({
        key: `attribute:${attribute}`,
        kind: "attribute",
        label: attributeName(source, attribute),
        detail: String(valueType),
        value: current && !current.ignore ? (current.target ?? NOT_MAPPED) : NOT_MAPPED,
        options: [{ value: NOT_MAPPED, label: "Not carried (reported)" }, ...targetAttributes],
        proposal: stillProposed(entry, typeProposal, { kind: "attribute", attribute }),
        operations: (value) =>
          value === NOT_MAPPED
            ? current
              ? [{ kind: "unmapAttribute", sourceType, attribute }]
              : []
            : [{ kind: "mapAttribute", sourceType, attribute, target: value }],
        problems: current ? problems(mapping, index, `/attributes/${at}`) : [],
      });
    }

    for (const relation of relationsFrom(source, sourceType)) {
      const key = relation.relationTypeKey;
      const current = entry.relations.find((item) => item.source === key);
      const relationProposal = proposals.find(
        (item) => item.kind === "relation" && item.sourceType === sourceType && item.relation === key,
      );
      const options: RowOption[] = [{ value: NOT_MAPPED, label: "Not carried (reported)" }];
      const seen = new Set<string>();
      const parents = containment(target);
      for (const candidate of target.objectTypeRelations) {
        if (parents.has(candidate.relationTypeKey)) continue;
        const ends: ("outgoing" | "incoming")[] = [];
        if (candidate.fromObjectTypeKey === entry.target) ends.push("outgoing");
        if (candidate.toObjectTypeKey === entry.target) ends.push("incoming");
        for (const direction of ends) {
          const value = `${candidate.relationTypeKey}|${direction}`;
          if (seen.has(value)) continue;
          seen.add(value);
          const other = direction === "outgoing" ? candidate.toObjectTypeKey : candidate.fromObjectTypeKey;
          options.push({
            value,
            label: `${relationName(target, candidate.relationTypeKey, direction)} → ${name(target, other)}`,
          });
        }
      }
      const at = current ? entry.relations.indexOf(current) : -1;
      rows.push({
        key: `relation:${key}`,
        kind: "relation",
        label: relationName(source, key),
        detail: `Relationship to ${name(source, relation.toObjectTypeKey)}`,
        value: current ? `${current.target}|${current.direction}` : NOT_MAPPED,
        options,
        proposal: stillProposed(entry, typeProposal, { kind: "relation", relation: key }, relationProposal),
        operations: (value) => {
          if (value === NOT_MAPPED) return current ? [{ kind: "unmapRelation", sourceType, relation: key }] : [];
          const [targetRelation, direction] = value.split("|");
          return [{ kind: "mapRelation", sourceType, relation: key, target: targetRelation, direction }];
        },
        problems: at >= 0 ? problems(mapping, index, `/relations/${at}`) : [],
      });
    }

    const targetParents = parentsOf(target, entry.target);
    if (targetParents.length || entry.parent) {
      const value = encodeParent(entry.parent);
      const options: RowOption[] = [{ value: "top", label: "At the top" }];
      for (const missing of ["", "create"] as const) {
        for (const parent of targetParents) {
          const label =
            (targetParents.length > 1
              ? `Under its moved parent, in ${name(target, parent.parentType)}`
              : "Under its moved parent") + (missing === "create" ? ", created where missing" : "");
          options.push({ value: `source:${parent.relation}:${missing}`, label });
        }
      }
      if (value === "named") options.push({ value, label: "Under the record the mapping names" });
      if (!options.some((option) => option.value === value))
        options.push({ value, label: "Under its moved parent (as set)" });
      rows.push({
        key: "parent",
        kind: "parent",
        label: "Parent",
        detail: parentsOf(source, sourceType).length ? "Where it stands" : "At the top in the source",
        value,
        options,
        proposal: stillProposed(entry, typeProposal, { kind: "parent" }),
        operations: (choice) => {
          if (choice === "top") return [{ kind: "setParent", sourceType, parent: null }];
          if (choice === "named") return [];
          const [, relationTypeKey, missing] = choice.split(":");
          const parent: Record<string, unknown> = { from: "source" };
          if (relationTypeKey) parent.relationTypeKey = relationTypeKey;
          if (missing) parent.missing = missing;
          return [{ kind: "setParent", sourceType, parent }];
        },
        problems: problems(mapping, index, "/parent"),
      });
    }

    const uniques = (targetDefinition?.attributes ?? []).filter(
      (binding) => attributeTypeFor(target, binding.attributeTypeKey)?.features.unique,
    );
    rows.push({
      key: "match",
      kind: "match",
      label: "Records already in the target",
      detail: "Found by",
      value: encodeMatch(entry.match),
      options: [
        { value: "", label: "Only those moved before" },
        { value: "name", label: "Found by name" },
        ...uniques.map((binding) => ({
          value: `attribute:${binding.attributeTypeKey}`,
          label: `Found by ${attributeName(target, binding.attributeTypeKey)}`,
        })),
      ],
      proposal: stillProposed(entry, typeProposal, { kind: "match" }),
      operations: (choice) => [
        {
          kind: "setMatch",
          sourceType,
          match: !choice
            ? null
            : choice === "name"
              ? { field: "name" }
              : { attributeTypeKey: choice.slice("attribute:".length) },
        },
      ],
      problems: problems(mapping, index, "/match"),
    });

    // The target's required fields nothing fills, and the defaults already set.
    const filled = new Set(entry.attributes.filter((item) => !item.ignore).map((item) => item.target));
    const needed = (targetDefinition?.attributes ?? []).filter(
      (binding) =>
        (binding.required && !filled.has(binding.attributeTypeKey)) || entry.defaults[binding.attributeTypeKey] != null,
    );
    for (const binding of needed) {
      const attribute = binding.attributeTypeKey;
      rows.push({
        key: `default:${attribute}`,
        kind: "default",
        label: `${attributeName(target, attribute)}${binding.required ? " (required in the target)" : ""}`,
        detail: "No source value",
        value: entry.defaults[attribute] != null ? "set" : NOT_MAPPED,
        options: [],
        attributeTypeKey: attribute,
        defaultValue: entry.defaults[attribute],
        operations: () => [],
        problems: problems(mapping, index, `/defaults/${attribute.replaceAll("~", "~0").replaceAll("/", "~1")}`),
      });
    }

    return {
      sourceType,
      sourceName: sourceDefinition?.pluralName ?? name(source, sourceType),
      targetType: entry.target,
      targetName: targetDefinition?.pluralName ?? name(target, entry.target),
      rows,
      problems: problemsAt(mapping.problems, index),
    };
  });
}

function problems(mapping: ModelMapping, index: number, part: string) {
  return problemsAt(mapping.problems, index, part);
}

/** The operation setting a default of a target attribute, or clearing it. */
export function defaultOperation(sourceType: string, attribute: string, value: unknown): MappingOperation {
  return { kind: "setDefault", sourceType, attribute, value: value === "" ? null : value };
}

/** A proposal's evidence in words (D108). */
export function evidenceText(item: Record<string, unknown>): string {
  const share = (value: unknown) => `${Math.round(Number(value) * 100)}%`;
  switch (item.kind) {
    case "sameModel":
      return "One model on both sides";
    case "sameKey":
      return "The same key on both sides";
    case "keyTokens":
      return `${share(item.share)} of the keys' words shared`;
    case "sameName":
      return "The same name on both sides";
    case "attributes":
      return `${String(item.matched)} of ${String(item.of)} fields shared, with values that convert`;
    case "storedRecords":
      return `${String(item.matched)} of ${String(item.of)} records' names or unique values found in the target`;
    case "parent":
      return "Its parent is mapped to the target's parent";
    case "cardinality":
      return `The same cardinality (${String(item.cardinality)})`;
    case "onlyRelation":
      return "The only relationship between the two types";
    default:
      return String(item.kind);
  }
}

/** A proposal's alternative in the editor's words: what the element becomes instead. */
export function alternativeText(
  alternative: MappingProposal["alternatives"][number],
  proposal: MappingProposal,
  source: EngineModel,
  target: EngineModel,
): string {
  if (proposal.kind === "type")
    return `${name(source, proposal.sourceType)} becomes ${name(target, alternative.target)} instead`;
  const direction = alternative.operations[0]?.direction === "incoming" ? "incoming" : "outgoing";
  return `${relationName(source, proposal.relation ?? "")} becomes ${relationName(target, alternative.target, direction)} instead`;
}

/** The source types the mapping leaves out, by name. */
export function unmappedTypes(mapping: ModelMapping, source: EngineModel) {
  const mapped = new Set(mapping.types.map((entry) => entry.source));
  return source.objectTypes.filter((type) => !mapped.has(type.key));
}
