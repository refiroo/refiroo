/**
 * Reads over a consumer API definition as the draft holds it (schema 0.9, CONSUMER_API "Definition
 * shape") for the model editor's Consumer APIs tab (0.10 A4c), and the requests its tables send: each
 * change is one of the six consumer kinds (D51), naming its part by a JSON pointer below the
 * definition. What a definition means (its defaults, its served types, its contract) is the server's:
 * the editor reads them from `GET /model-drafts/{id}/consumer-apis/{key}` and its schema, never works
 * them out here.
 */

import type { ConsumerDefinition, DraftOperation, ModelDraftOutline } from "@/types";
import { relationTypeOf, typeName } from "@/features/model-editor/outline";

type Json = Record<string, unknown>;

const record = (value: unknown): Json =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Json) : {};
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const str = (value: unknown) => (typeof value === "string" ? value : "");
const strings = (value: unknown): string[] =>
  typeof value === "string" ? [value] : list(value).filter((item): item is string => typeof item === "string");

/** A JSON pointer below the definition from its segments (`~` and `/` escaped). */
export function pointer(...segments: (string | number)[]): string {
  return segments.map((part) => `/${String(part).replaceAll("~", "~0").replaceAll("/", "~1")}`).join("");
}

export const ROLES = ["id", "code", "name", "active", "validFrom", "validTo"] as const;
export const ROLE_OPTIONS = [{ value: "", label: "None" }, ...ROLES.map((role) => ({ value: role, label: role }))];

/** An output field as the editor's table shows it. */
export interface FieldRow {
  output: string;
  role: string;
  sources: string[];
  default?: unknown;
  description?: string;
  /** Its place among the definition's fields, as written. */
  index: number;
  value: unknown;
}

export function fieldsOf(definition: ConsumerDefinition): FieldRow[] {
  return Object.entries(record(record(definition.object).fields)).map(([output, value], index) =>
    fieldRow(output, value, index),
  );
}

/** One output field read from its written form. */
export function fieldRow(output: string, value: unknown, index: number): FieldRow {
  if (typeof value === "string" || Array.isArray(value))
    return { output, role: "", sources: strings(value), index, value };
  const spec = record(value);
  return {
    output,
    role: typeof spec.role === "string" ? spec.role : "",
    sources: strings(spec.from),
    default: spec.default,
    description: typeof spec.description === "string" ? spec.description : undefined,
    index,
    value,
  };
}

/** A source a field may read, for the Sources picklist: its value, its words and its group. */
export interface SourceOption {
  value: string;
  label: string;
  group: string;
}

/**
 * The sources a field of a consumer API may read: the name, every attribute an exposed type binds,
 * and the name and attributes of each type above an exposed one (`ancestor:<type>.<field>`), with
 * each value type, so the sources a field lists in order can share one type. Sources the field
 * already reads that are none of these (written by hand) stay listed.
 */
export function sourceOptions(outline: ModelDraftOutline, exposes: string[], current: string[] = []): SourceOption[] {
  const options = new Map<string, SourceOption>();
  const add = (value: string, label: string, group: string) => {
    if (!options.has(value)) options.set(value, { value, label, group });
  };
  add("name", "Name", "Built in");
  const typed = (valueType: string | null | undefined) => (valueType ? ` · ${valueType}` : "");
  for (const key of exposes) {
    const type = outline.objectTypes.find((item) => item.key === key);
    for (const attribute of type?.attributes ?? [])
      add(attribute.attributeType, `${attribute.name}${typed(attribute.valueType)}`, "Attributes of the exposed types");
  }
  const ancestors: string[] = [];
  const climb = (key: string) => {
    for (const parent of outline.objectTypes.find((item) => item.key === key)?.parents ?? [])
      if (!ancestors.includes(parent)) {
        ancestors.push(parent);
        climb(parent);
      }
  };
  exposes.forEach(climb);
  for (const key of ancestors) {
    const type = outline.objectTypes.find((item) => item.key === key);
    const name = type?.name ?? key;
    add(`ancestor:${key}.name`, `${name} › Name`, "From a type above");
    for (const attribute of type?.attributes ?? [])
      add(
        `ancestor:${key}.${attribute.attributeType}`,
        `${name} › ${attribute.name}${typed(attribute.valueType)}`,
        "From a type above",
      );
  }
  for (const value of current) add(value, value, "Written by hand");
  return [...options.values()];
}

/** A field written as the definition grammar has it: one source, a list, or written out. */
export function writeField(field: {
  sources: string[];
  role?: string;
  default?: unknown;
  description?: string;
}): unknown {
  const { sources, role, description } = field;
  const plain = !role && field.default === undefined && !description;
  if (plain && sources.length === 1) return sources[0];
  if (plain && sources.length > 1) return sources;
  return {
    ...(sources.length ? { from: sources.length === 1 ? sources[0] : sources } : {}),
    ...(field.default !== undefined ? { default: field.default } : {}),
    ...(role ? { role } : {}),
    ...(description ? { description } : {}),
  };
}

/** Sources typed as a list: "value-code, name". */
export function parseList(text: string): string[] {
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/** A default typed in a cell: JSON where it reads as JSON (`true`, `50`), otherwise text; empty is none. */
export function parseDefault(text: string): unknown {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

export function formatDefault(value: unknown): string {
  if (value === undefined) return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}

/** Output fields of a related block typed as "out=source, out2=source2". */
export function parsePairs(text: string): Record<string, string> {
  const pairs: Record<string, string> = {};
  for (const part of parseList(text)) {
    const [output, ...rest] = part.split("=");
    const source = rest.join("=").trim();
    if (output.trim()) pairs[output.trim()] = source || output.trim();
  }
  return pairs;
}

export function formatPairs(pairs: Record<string, unknown>): string {
  return Object.entries(pairs)
    .map(([output, source]) => (output === source ? output : `${output}=${String(source)}`))
    .join(", ");
}

/** The field written again with one part changed: a step that sets the field to its new form. */
export function setField(api: string, row: FieldRow, change: Partial<Omit<FieldRow, "output">>): DraftOperation[] {
  const next = { ...row, ...change };
  return [
    {
      kind: "setConsumerApiPart",
      consumerApi: api,
      pointer: pointer("object", "fields", row.output),
      value: writeField(next),
    },
  ];
}

/** A map member renamed in place: removed and inserted at its place under the new name, one step. */
export function renameMember(api: string, container: string, from: string, to: string, value: unknown, index: number) {
  return [
    { kind: "removeConsumerApiPart", consumerApi: api, pointer: `${container}${pointer(from)}` },
    { kind: "insertConsumerApiPart", consumerApi: api, pointer: container, key: to, value, position: index },
  ];
}

/** How a related block is served (CA1, PP-D30): in every answer, or only when a read names it in `include`. */
export type Served = "always" | "onRequest";

export const SERVED_OPTIONS: { value: Served; label: string }[] = [
  { value: "always", label: "Always" },
  { value: "onRequest", label: "On request" },
];

export interface RelatedRow {
  output: string;
  via: string;
  fields: Record<string, string>;
  served: Served;
  index: number;
  value: unknown;
}

/** The prefix a block of the parent has in `include` and in an On related filter (PP-D31). */
export const PARENT_BLOCK_PREFIX = "parent.";

function relatedBlocks(related: unknown): RelatedRow[] {
  return Object.entries(record(related)).map(([output, value], index) => {
    const block = record(value);
    return {
      output,
      via: typeof block.via === "string" ? block.via : "",
      fields: Object.fromEntries(Object.entries(record(block.fields)).map(([k, v]) => [k, String(v)])),
      served: block.served === "onRequest" ? "onRequest" : "always",
      index,
      value,
    };
  });
}

/** The related blocks of the object, or with `scope` `parent` those of its parent (CA1). */
export function relatedOf(definition: ConsumerDefinition, scope: "object" | "parent" = "object"): RelatedRow[] {
  const object = record(definition.object);
  return relatedBlocks(scope === "parent" ? record(object.parent).related : object.related);
}

/** One field of the parent: the output name consumers read, the sources it reads and its written form. */
export interface ParentFieldRow {
  output: string;
  sources: string[];
  value: unknown;
}

/** The parent as the definition writes it: the short list form has no place for related blocks. */
export interface ParentRow {
  output: string;
  fields: ParentFieldRow[];
  /** Written as a list of fields (it is rewritten out in full on a change). */
  short: boolean;
}

/** The output name a role field has, as a built-in parent field of the list form is served under. */
function roleOutput(definition: ConsumerDefinition, name: string): string {
  if (name === "objectType") return name;
  return fieldsOf(definition).find((field) => field.role === name)?.output ?? name;
}

/** The parent a definition serves, or `undefined` when it serves none. */
export function parentSpecOf(definition: ConsumerDefinition): ParentRow | undefined {
  const parent = record(definition.object).parent;
  if (!parent || typeof parent !== "object") return undefined;
  const spec = Array.isArray(parent) ? { fields: parent } : record(parent);
  const written = spec.fields;
  // A list names sources; a built-in one is served under its role's output name, any other under its words in camelCase.
  const fields: ParentFieldRow[] = Array.isArray(written)
    ? strings(written).map((name) => {
        const builtIn = PARENT_BUILT_IN_FIELDS.some((item) => item.value === name);
        return { output: builtIn ? roleOutput(definition, name) : outputFor(name), sources: [name], value: name };
      })
    : Object.entries(record(written)).map(([output, value], index) => {
        const row = fieldRow(output, value, index);
        return { output, sources: row.sources, value };
      });
  return {
    output: Array.isArray(parent) ? "parent" : str(spec.output) || "parent",
    fields,
    short: Array.isArray(parent),
  };
}

/** The parent written out in full, with `change` applied: what a step sets at `/object/parent`. */
export function writeParent(
  definition: ConsumerDefinition,
  change: { output?: string; fields?: Record<string, unknown> } = {},
): Json | undefined {
  const parent = parentSpecOf(definition);
  if (!parent) return undefined;
  const related = record(record(record(definition.object).parent).related);
  return {
    output: change.output ?? parent.output,
    fields: change.fields ?? Object.fromEntries(parent.fields.map((field) => [field.output, field.value])),
    ...(Object.keys(related).length ? { related } : {}),
  };
}

/** The steps that make the parent a full object before a part inside it is changed (none when it is one). */
export function ensureParentObject(api: string, definition: ConsumerDefinition): DraftOperation[] {
  const parent = parentSpecOf(definition);
  return parent?.short
    ? [
        {
          kind: "setConsumerApiPart",
          consumerApi: api,
          pointer: pointer("object", "parent"),
          value: writeParent(definition),
        },
      ]
    : [];
}

/** The types a record's parent may be: the types directly above the exposed ones. */
export function parentTypesOf(outline: ModelDraftOutline, exposes: string[]): string[] {
  const found: string[] = [];
  for (const key of exposes)
    for (const parent of outline.objectTypes.find((item) => item.key === key)?.parents ?? [])
      if (!found.includes(parent)) found.push(parent);
  return found;
}

export const PARENT_BUILT_IN_FIELDS = [
  { value: "objectType", label: "Public type name", group: "Built in" },
  { value: "id", label: "ID", group: "Built in" },
  { value: "code", label: "Code", group: "Built in" },
  { value: "name", label: "Name", group: "Built in" },
];

/** What the parent may show: its four built-in fields and the attributes of the parent types. */
export function parentFieldOptions(
  outline: ModelDraftOutline,
  exposes: string[],
  current: string[] = [],
): SourceOption[] {
  const options = new Map<string, SourceOption>(PARENT_BUILT_IN_FIELDS.map((item) => [item.value, item]));
  for (const key of parentTypesOf(outline, exposes))
    for (const attribute of outline.objectTypes.find((item) => item.key === key)?.attributes ?? [])
      if (!options.has(attribute.attributeType))
        options.set(attribute.attributeType, {
          value: attribute.attributeType,
          label: `${attribute.name}${attribute.valueType ? ` · ${attribute.valueType}` : ""}`,
          group: "Attributes of the parent types",
        });
  for (const value of current)
    if (!options.has(value)) options.set(value, { value, label: value, group: "Written by hand" });
  return [...options.values()];
}

/** The related blocks a filter may be On: the object's, then the parent's as `parent.<block>`. */
export function blockNames(definition: ConsumerDefinition): { value: string; label: string }[] {
  return [
    ...relatedOf(definition).map((row) => ({ value: row.output, label: row.output })),
    ...relatedOf(definition, "parent").map((row) => ({
      value: `${PARENT_BLOCK_PREFIX}${row.output}`,
      label: `${PARENT_BLOCK_PREFIX}${row.output}`,
    })),
  ];
}

/** The blocks `include` accepts: those served on request, by the name a read gives (PP-D30). */
export function includeNames(definition: ConsumerDefinition): string[] {
  return [
    ...relatedOf(definition)
      .filter((row) => row.served === "onRequest")
      .map((row) => row.output),
    ...relatedOf(definition, "parent")
      .filter((row) => row.served === "onRequest")
      .map((row) => `${PARENT_BLOCK_PREFIX}${row.output}`),
  ];
}

/** A `via` in words: the relation's name, forward by its key or reverse by its reverse key. */
export function viaLabel(outline: ModelDraftOutline, via: string): string {
  const forward = relationTypeOf(outline, via);
  if (forward) return `${forward.name} (forward)`;
  const reverse = outline.relationTypes.find((item) => item.reverseKey === via);
  return reverse ? `${reverse.reverseName ?? reverse.name} (reverse)` : via;
}

/** The routes a related block may take: every relation bound to an exposed type, in the direction it
 * leaves that type. */
export function viaOptions(outline: ModelDraftOutline, exposes: string[]): { value: string; label: string }[] {
  const options = new Map<string, string>();
  for (const relation of outline.relations) {
    const type = relationTypeOf(outline, relation.relationType);
    if (!type) continue;
    if (exposes.includes(relation.from))
      options.set(
        type.key,
        `${type.name} (forward) · ${typeName(outline, relation.from)} → ${typeName(outline, relation.to)}`,
      );
    if (exposes.includes(relation.to) && type.reverseKey)
      options.set(
        type.reverseKey,
        `${type.reverseName ?? type.name} (reverse) · ${typeName(outline, relation.to)} → ${typeName(outline, relation.from)}`,
      );
  }
  return [...options].map(([value, label]) => ({ value, label }));
}

export function exposesOf(definition: ConsumerDefinition): string[] {
  return strings(definition.exposes);
}

export function publicNamesOf(definition: ConsumerDefinition): Record<string, string> {
  return Object.fromEntries(
    Object.entries(record(definition.publicNames)).filter(
      (entry): entry is [string, string] => typeof entry[1] === "string",
    ),
  );
}

export interface ListRow {
  key: string;
  of: string;
  within?: string;
  sortBy?: string;
  index: number;
  value: unknown;
}

export function operationsOf(definition: ConsumerDefinition): Json {
  return record(definition.operations);
}

export function listsOf(definition: ConsumerDefinition): ListRow[] {
  return Object.entries(record(operationsOf(definition).lists)).map(([key, value], index) => {
    const item = record(value);
    const within = record(item.within);
    return {
      key,
      of: typeof item.of === "string" ? item.of : "",
      within: typeof within.filter === "string" ? within.filter : undefined,
      sortBy: typeof item.sortBy === "string" ? item.sortBy : undefined,
      index,
      value,
    };
  });
}

/** Whether an operation is offered: listed means offered (C-D132). */
export function offers(definition: ConsumerDefinition, operation: "objects" | "xref" | "resolve"): boolean {
  return operation in operationsOf(definition) && operationsOf(definition)[operation] !== null;
}

export function perTypeEvents(definition: ConsumerDefinition): boolean {
  return record(operationsOf(definition).events).perType === true;
}

/** How many match rules XREF holds: switching it off takes them with it (they live inside it). */
export function xrefRuleCount(definition: ConsumerDefinition): number {
  const xref = record(operationsOf(definition).xref);
  return list(xref.matchOn).length + list(xref.alsoMatchThrough).length;
}

/** Offering or no longer offering an operation, as one step; no longer offering Get by ID or XREF
 * stops Resolve too, in the same step. */
export function toggleOperation(
  api: string,
  definition: ConsumerDefinition,
  operation: "objects" | "xref" | "resolve" | "perType",
  on: boolean,
): DraftOperation[] {
  if (operation !== "perType") {
    const step: DraftOperation = {
      kind: "setConsumerApiPart",
      consumerApi: api,
      pointer: pointer("operations", operation),
      value: on ? {} : null,
    };
    // Resolve answers as Get by ID and XREF do: it stops with either of them (C-D132).
    return !on && operation !== "resolve" && offers(definition, "resolve")
      ? [{ kind: "setConsumerApiPart", consumerApi: api, pointer: pointer("operations", "resolve"), value: null }, step]
      : [step];
  }
  const events = record(operationsOf(definition).events);
  if (on && !("events" in operationsOf(definition)))
    return [
      {
        kind: "setConsumerApiPart",
        consumerApi: api,
        pointer: pointer("operations", "events"),
        value: { perType: true },
      },
    ];
  if (!on && !list(events.custom).length)
    return [{ kind: "setConsumerApiPart", consumerApi: api, pointer: pointer("operations", "events"), value: null }];
  return [
    {
      kind: "setConsumerApiPart",
      consumerApi: api,
      pointer: pointer("operations", "events", "perType"),
      value: on ? true : null,
    },
  ];
}

export interface RuleRow {
  field: string;
  exact?: number;
  contains?: number;
  index: number;
  value: unknown;
}

export function matchRulesOf(definition: ConsumerDefinition): RuleRow[] {
  return list(record(operationsOf(definition).xref).matchOn).map((value, index) => {
    const rule = record(value);
    return {
      field: String(rule.field ?? ""),
      exact: typeof rule.exact === "number" ? rule.exact : undefined,
      contains: typeof rule.contains === "number" ? rule.contains : undefined,
      index,
      value,
    };
  });
}

export interface ThroughRow {
  related: string;
  firstOf: string;
  preferTypes: string[];
  index: number;
  value: unknown;
}

export function alsoMatchThroughOf(definition: ConsumerDefinition): ThroughRow[] {
  return list(record(operationsOf(definition).xref).alsoMatchThrough).map((value, index) => {
    const item = record(value);
    return {
      related: String(item.related ?? ""),
      firstOf: list(item.firstOf)
        .map((rule) => {
          const r = record(rule);
          return [
            r.field,
            r.exact !== undefined ? `exact ${String(r.exact)}` : "",
            r.contains !== undefined ? `contains ${String(r.contains)}` : "",
          ]
            .filter(Boolean)
            .join(" ");
        })
        .join("; "),
      preferTypes: strings(item.preferTypes),
      index,
      value,
    };
  });
}

export interface EventRow {
  key: string;
  objectTypes: string[];
  changes: string[];
  watch: string[];
  index: number;
  value: unknown;
}

export function customEventsOf(definition: ConsumerDefinition): EventRow[] {
  return list(record(operationsOf(definition).events).custom).map((value, index) => {
    const event = record(value);
    const watch = record(event.watch);
    return {
      key: String(event.key ?? ""),
      objectTypes: strings(event.objectTypes),
      changes: strings(event.changes),
      watch: [...strings(watch.fields), ...strings(watch.related)],
      index,
      value,
    };
  });
}

export const FILTER_VERBS = [
  { value: "byType", label: "By type" },
  { value: "under", label: "Under" },
  { value: "linkedTo", label: "Linked to" },
  { value: "onRelated", label: "On related" },
] as const;

export type FilterVerb = (typeof FILTER_VERBS)[number]["value"];

export interface FilterRow {
  name: string;
  verb: FilterVerb | "";
  reads: string;
  matchOn: string[];
  options: string[];
  index: number;
  value: unknown;
}

export function filtersOf(definition: ConsumerDefinition, outline: ModelDraftOutline): FilterRow[] {
  return Object.entries(record(definition.filters)).map(([name, value], index) => {
    const item = record(value);
    const verb = FILTER_VERBS.find((option) => option.value in item)?.value ?? "";
    const reads =
      verb === "byType"
        ? "the exposed types' public names"
        : verb === "under"
          ? `an ancestor ${strings(item.under)
              .map((key) => typeName(outline, key))
              .join(" or ")}`
          : verb === "linkedTo"
            ? `${strings(item.linkedTo)
                .map((key) => typeName(outline, key))
                .join(" or ")} through ${strings(item.through).join(", ")}`
            : verb === "onRelated"
              ? `the block ${String(item.onRelated)}`
              : "";
    const options = (["keepOnlyMatching", "scoreOnlyMatching", "crosswalk"] as const).filter(
      (flag) => item[flag] === true,
    );
    return { name, verb, reads, matchOn: strings(item.matchOn), options, index, value };
  });
}

export const FILTER_OPTION_LABELS: Record<string, string> = {
  keepOnlyMatching: "keep only matching",
  scoreOnlyMatching: "score only matching",
  crosswalk: "crosswalk",
};

/** What a filter of a verb reads, as the Add filter dialog or a filter's row holds it. */
export interface FilterReads {
  verb: string;
  types: string[];
  related?: string;
}

export function filterReads(value: unknown): FilterReads {
  const item = record(value);
  const verb = FILTER_VERBS.find((option) => option.value in item)?.value ?? "";
  return {
    verb,
    types: strings(item.under ?? item.linkedTo),
    related: typeof item.onRelated === "string" ? item.onRelated : undefined,
  };
}

/**
 * The fields a filter may match on, for its picklist (the user, A4c), by the rule the server checks
 * (C-D20): under or linked to types, `id`, `name`, `code` when the API has a code field, and the
 * attributes of those types that are searchable or unique; on a related block, its fields' sources
 * with `id` and `name`. A field the filter matches on already (written by hand) stays listed.
 */
export function matchOptions(
  outline: ModelDraftOutline,
  definition: ConsumerDefinition,
  reads: FilterReads,
  current: string[] = [],
): SourceOption[] {
  const options = new Map<string, SourceOption>();
  const add = (value: string, label: string, group: string) => {
    if (!options.has(value)) options.set(value, { value, label, group });
  };
  add("id", "ID", "Built in");
  add("name", "Name", "Built in");
  if (reads.verb === "under" || reads.verb === "linkedTo") {
    if (fieldsOf(definition).some((field) => field.role === "code"))
      add("code", "Code (every code source)", "Built in");
    // A rule weighs a field on every exposed type that binds it alike, so a field is listed once,
    // as the sources are (it was listed under the first type binding it, as if the others had none).
    for (const key of reads.types) {
      const type = outline.objectTypes.find((item) => item.key === key);
      for (const attribute of type?.attributes ?? []) {
        const features = outline.attributeTypes.find((item) => item.key === attribute.attributeType)?.features ?? {};
        if (attribute.unique || features.searchable === true)
          add(attribute.attributeType, attribute.name, "Attributes of the exposed types");
      }
    }
  } else if (reads.verb === "onRelated" && reads.related) {
    const ofParent = reads.related.startsWith(PARENT_BLOCK_PREFIX);
    const block = relatedOf(definition, ofParent ? "parent" : "object").find(
      (row) => row.output === (ofParent ? reads.related?.slice(PARENT_BLOCK_PREFIX.length) : reads.related),
    );
    for (const [output, source] of Object.entries(block?.fields ?? {}))
      add(source, source === output ? output : `${output} (${source})`, `Fields of ${reads.related}`);
    // Any field of the records the block reaches matches too, as its Fields… picker lists them: their
    // attributes, the fields of the types above them (the system a value sits under) and the
    // relationship's own values; a block of the parent starts from the parent types.
    if (block) {
      const owners = ofParent ? parentTypesOf(outline, exposesOf(definition)) : exposesOf(definition);
      const reached = relatedTypesOf(outline, block.via, owners);
      for (const item of relatedFieldOptions(outline, reached, [], { via: block.via, exposes: owners }))
        if (item.value !== "objectType") add(item.value, item.label, item.group);
    }
  }
  for (const value of current) add(value, value, "Written by hand");
  return [...options.values()];
}

/** The types a related block reaches: the far end of `via` (a relation's key forward, its reverse
 * key backward) from each exposed type. */
export function relatedTypesOf(outline: ModelDraftOutline, via: string, exposes: string[]): string[] {
  const found: string[] = [];
  for (const relation of outline.relations) {
    const type = outline.relationTypes.find((item) => item.key === relation.relationType);
    if (!type) continue;
    if (type.key === via && exposes.includes(relation.from)) found.push(relation.to);
    if (type.reverseKey === via && exposes.includes(relation.to)) found.push(relation.from);
  }
  return [...new Set(found)];
}

/** The attributes the relationship itself carries, for a related block over `via` (a relation's key
 * forward, its reverse key backward) from the exposed types: those of the bindings the block follows,
 * as `relation:<attribute>` sources. */
export function relationAttributeOptions(outline: ModelDraftOutline, via: string, exposes: string[]): SourceOption[] {
  const keys: string[] = [];
  for (const relation of outline.relations) {
    const type = outline.relationTypes.find((item) => item.key === relation.relationType);
    if (!type) continue;
    const reached =
      (type.key === via && exposes.includes(relation.from)) ||
      (type.reverseKey === via && exposes.includes(relation.to));
    if (reached) for (const key of relation.attributeTypeKeys ?? []) if (!keys.includes(key)) keys.push(key);
  }
  return keys.map((key) => {
    const attribute = outline.attributeTypes.find((item) => item.key === key);
    return {
      value: `relation:${key}`,
      label: `${attribute?.name ?? key}${attribute?.valueType ? ` · ${attribute.valueType}` : ""}`,
      group: "Attributes of the relationship",
    };
  });
}

/** The fields a related record offers: its ID and public type name besides what `sourceOptions`
 * lists for its types (the name, their attributes, the types above them), and, given the block's
 * route, the attributes of the relationship itself. */
export function relatedFieldOptions(
  outline: ModelDraftOutline,
  types: string[],
  current: string[] = [],
  route?: { via: string; exposes: string[] },
): SourceOption[] {
  const relationship = route ? relationAttributeOptions(outline, route.via, route.exposes) : [];
  const offered = sourceOptions(
    outline,
    types,
    current.filter((value) => !value.startsWith("relation:") || relationship.some((item) => item.value === value)),
  );
  const rest = current
    .filter((value) => value.startsWith("relation:") && !relationship.some((item) => item.value === value))
    .map((value) => ({
      value,
      label: outline.attributeTypes.find((item) => item.key === value.slice(9))?.name ?? value,
      group: "Written by hand",
    }));
  return [
    { value: "id", label: "ID", group: "Built in" },
    { value: "objectType", label: "Public type name", group: "Built in" },
    ...offered,
    ...relationship,
    ...rest,
  ];
}

/** The attributes a list of a type may be sorted by: scalar ones it binds (C3); none is by name. */
export function sortOptions(outline: ModelDraftOutline, typeKey: string, current?: string): SourceOption[] {
  const type = outline.objectTypes.find((item) => item.key === typeKey);
  const options: SourceOption[] = [{ value: "", label: "Name (the default)", group: "" }];
  for (const attribute of type?.attributes ?? [])
    if (attribute.valueType !== "json")
      options.push({
        value: attribute.attributeType,
        label: `${attribute.name} · ${attribute.valueType ?? "text"}`,
        group: "",
      });
  if (current && !options.some((option) => option.value === current))
    options.push({ value: current, label: current, group: "" });
  return options;
}

/** The routes a linked-to filter may take: a related block, the record itself, or a related record
 * shared with it. */
export function throughOptions(definition: ConsumerDefinition, current: string[] = []): SourceOption[] {
  const blocks = relatedOf(definition).map((row) => row.output);
  const options: SourceOption[] = [
    { value: "itself", label: "The record itself", group: "" },
    ...blocks.map((block) => ({ value: block, label: block, group: "Related blocks" })),
    ...blocks.map((block) => ({
      value: `sharedWith:${block}`,
      label: `Sharing ${block}`,
      group: "Shared related records",
    })),
  ];
  for (const value of current)
    if (!options.some((option) => option.value === value))
      options.push({ value, label: value, group: "Written by hand" });
  return options;
}

/** What a custom event may watch: the outputs consumers read and the related blocks (C-D81). */
export function watchOptions(definition: ConsumerDefinition): SourceOption[] {
  return [
    ...fieldsOf(definition).map((field) => ({ value: field.output, label: field.output, group: "Fields" })),
    ...relatedOf(definition).map((row) => ({ value: row.output, label: row.output, group: "Related blocks" })),
  ];
}

/** A camelCase output name for a source, as the server names a starting field. */
export function outputFor(source: string): string {
  const tail = source.includes(".") ? source.slice(source.lastIndexOf(".") + 1) : source;
  const parts = tail.split(/[^0-9A-Za-z]+/).filter(Boolean);
  if (!parts.length) return "field";
  const [head, ...rest] = parts;
  return (
    head.charAt(0).toLowerCase() +
    head.slice(1) +
    rest.map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join("")
  );
}

/** A property's type in a JSON Schema, in a few words: `text`, `date`, `integer | null`, `list of …`. */
export function schemaTypeLabel(
  schema: Record<string, unknown> | undefined,
  defs: Record<string, Record<string, unknown>>,
): string {
  if (!schema) return "—";
  const reference = typeof schema.$ref === "string" ? schema.$ref.replace("#/$defs/", "") : undefined;
  if (reference) return defs[reference] ? "object" : reference;
  for (const union of ["anyOf", "oneOf"] as const) {
    const choices = list(schema[union]).map((item) => record(item));
    if (choices.length) {
      const named = choices.filter((item) => item.type !== "null").map((item) => schemaTypeLabel(item, defs));
      return [...named, ...(choices.some((item) => item.type === "null") ? ["null"] : [])].join(" | ");
    }
  }
  const types = strings(schema.type);
  const words = types.map((type) => {
    if (type === "string") return typeof schema.format === "string" ? schema.format : "text";
    if (type === "array") return `list of ${schemaTypeLabel(record(schema.items), defs)}`;
    return type;
  });
  return words.join(" | ") || (schema.enum ? "text" : "any");
}

/** The part a pointer names, in words, for the history (D51): "field packSize", "list items". */
function partWords(path: string): string {
  const parts = path
    .split("/")
    .slice(1)
    .map((part) => part.replaceAll("~1", "/").replaceAll("~0", "~"));
  const [head, second, third, fourth] = parts;
  if (head === "object" && second === "fields") return third ? `field ${third}` : "the fields";
  if (head === "object" && second === "related") return third ? `related block ${third}` : "the related blocks";
  if (head === "object" && second === "parent") {
    if (third === "related") return fourth ? `the parent's related block ${fourth}` : "the parent's related blocks";
    return third === "fields" ? "the parent's fields" : "the parent";
  }
  if (head === "object") return second ?? "the object";
  if (head === "operations" && second === "lists") return third ? `list ${third}` : "the lists";
  if (head === "operations" && second === "xref") {
    if (third === "matchOn") return fourth ? "an XREF rule" : "the XREF rules";
    if (third === "alsoMatchThrough") return "a rule matching through a related block";
    return "XREF";
  }
  if (head === "operations" && second === "events") return third === "custom" ? "a custom event" : "the events";
  if (head === "operations")
    return second === "objects" ? "Get by ID" : second === "resolve" ? "Resolve" : (second ?? "the operations");
  if (head === "filters") return second ? `filter ${second}` : "the filters";
  if (head === "exposes") return "the exposed types";
  if (head === "publicNames") return second ? `the public name of ${second}` : "the public names";
  if (head === "contractVersion") return "the contract version";
  return head ?? "the definition";
}

/** An earlier contract version a definition keeps (DF3), newest first as written. */
export interface EarlierVersionRow {
  index: number;
  version: number;
  deprecated?: string;
  sunset?: string;
  value: Record<string, unknown>;
}

export function earlierVersionsOf(definition: ConsumerDefinition): EarlierVersionRow[] {
  const kept = Array.isArray(definition.earlierVersions) ? definition.earlierVersions : [];
  return kept.flatMap((item, index) => {
    const value = record(item);
    const version = Number(value.contractVersion);
    return Number.isInteger(version)
      ? [
          {
            index,
            version,
            deprecated: str(value.deprecated) || undefined,
            sunset: str(value.sunset) || undefined,
            value,
          },
        ]
      : [];
  });
}

/** A consumer API operation in words, or `undefined` for any other kind. */
export function describeConsumerOperation(
  kind: string,
  p: Record<string, unknown>,
  apiName: (key: string) => string,
): string | undefined {
  const api = apiName(str(p.consumerApi));
  const path = str(p.pointer);
  switch (kind) {
    case "addConsumerApi": {
      const definition = record(p.definition);
      return `Added consumer API ${str(p.name) || str(definition.name) || str(definition.key)}`;
    }
    case "removeConsumerApi":
      return `Removed consumer API ${api}`;
    case "raiseConsumerApiVersion": {
      const to = p.version === undefined ? "the next contract version" : `contract version ${String(p.version)}`;
      return `Raised ${api} to ${to}, ${p.keep === false ? "stopping" : "keeping"} the earlier one`;
    }
    case "removeConsumerApiVersion":
      return `Stopped serving version ${String(p.version)} of ${api}`;
    case "setConsumerApiSunset":
      return p.sunset
        ? `Set the sunset of version ${String(p.version)} of ${api} to ${str(p.sunset)}`
        : `Took back the sunset of version ${String(p.version)} of ${api}`;
    case "setConsumerApiPart":
      if (!path) return `Edited ${api} as JSON`;
      if (path === "/contractVersion") return `Set ${api} to contract version ${String(p.value)}`;
      if (path === "/name") return `Renamed consumer API ${api} to ${str(p.value)}`;
      if (path === "/operations/events")
        return p.value === null
          ? `Stopped offering events in ${api}`
          : `Offered ${record(p.value).perType ? "events per type" : "events"} in ${api}`;
      if (/^\/operations\/(objects|xref|resolve)$/.test(path) || path === "/operations/events/perType")
        return `${p.value === null ? "Stopped offering" : "Offered"} ${partWords(path)} in ${api}`;
      return p.value === null ? `Took ${partWords(path)} out of ${api}` : `Changed ${partWords(path)} of ${api}`;
    case "insertConsumerApiPart": {
      const named = p.key !== undefined ? `${path}${pointer(str(p.key))}` : `${path}/0`;
      return path === "/exposes" ? `Exposed ${str(p.value)} in ${api}` : `Added ${partWords(named)} to ${api}`;
    }
    case "moveConsumerApiPart":
      return `Moved ${partWords(path)} to place ${Number(p.position) + 1} in ${api}`;
    case "removeConsumerApiPart":
      return path.startsWith("/exposes/")
        ? `Stopped exposing a type in ${api}`
        : `Removed ${partWords(path)} from ${api}`;
    default:
      return undefined;
  }
}
