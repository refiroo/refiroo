/**
 * The draft's import profile read for the editor (0.10 A5b): what each column of the source file
 * feeds, its status in the source pane, the targets Map to… offers and the one request each choice
 * sends (the source and mapping kinds, A5a D76). The server keeps the profile; nothing here decides
 * whether a binding holds, which the step's diagnostics say.
 */

import type {
  DraftOperation,
  DraftProfile,
  DraftProfileDocument,
  ModelDiagnostic,
  ModelDraftOutline,
  OutlineRelation,
  ProfileBinding,
  ProfileRelation,
  ProfileSource,
  SourceColumn,
} from "@/types";
import {
  attributeTypeOf,
  keyFromLabel,
  keysOf,
  objectTypeOf,
  relationTypeOf,
  typeName,
} from "@/features/model-editor/outline";

/** A column of a sheet, as the profile names it: its sheet and its header text. */
export const columnId = (sheet: string, header: string) => `${sheet}\u0000${header}`;

export type ColumnStatus = "key" | "mapped" | "proposed" | "unmapped" | "ignored" | "describes" | "issue";

export const STATUS_LABELS: Record<ColumnStatus, string> = {
  key: "Key",
  mapped: "Mapped",
  proposed: "Proposed",
  unmapped: "Not mapped",
  ignored: "Ignored",
  describes: "Describes the model",
  issue: "Issue",
};

/** A binding of a column, with the source it belongs to. */
export interface ColumnUse {
  source: ProfileSource;
  binding: ProfileBinding;
}

export interface ColumnState {
  status: ColumnStatus;
  uses: ColumnUse[];
  issues: ModelDiagnostic[];
}

const holds = (binding: ProfileBinding, header: string) =>
  binding.column === header || Boolean(binding.columns?.includes(header));

/** Every use of a column in the profile's sources on its sheet. */
export function usesOf(profile: DraftProfileDocument | null | undefined, sheet: string, header: string): ColumnUse[] {
  return (profile?.sources ?? [])
    .filter((source) => source.sheet === sheet)
    .flatMap((source) =>
      source.columns.filter((binding) => holds(binding, header)).map((binding) => ({ source, binding })),
    );
}

/**
 * The columns a profile warning is about: a binding's (`/profile/sources/{i}/columns/{j}/…`) or an
 * unmapped entry's (`/profile/unmapped/{k}`); none for a warning about a whole source.
 */
export function columnsOfIssue(
  profile: DraftProfileDocument,
  item: ModelDiagnostic,
): { sheet: string; header: string }[] {
  const parts = item.path.split("/");
  if (parts[2] === "unmapped") {
    const entry = profile.unmapped?.[Number(parts[3])];
    if (!entry) return [];
    return (entry.columns ?? (entry.column ? [entry.column] : [])).map((header) => ({ sheet: entry.sheet, header }));
  }
  if (parts[2] === "sources" && parts[4] === "columns" && parts[5] !== undefined) {
    const source = profile.sources[Number(parts[3])];
    const binding = source?.columns[Number(parts[5])];
    if (!source || !binding) return [];
    return (binding.columns ?? (binding.column ? [binding.column] : [])).map((header) => ({
      sheet: source.sheet,
      header,
    }));
  }
  return [];
}

/** The profile's warnings by the column they are about. */
export function issuesByColumn(draft: DraftProfile | undefined): Map<string, ModelDiagnostic[]> {
  const found = new Map<string, ModelDiagnostic[]>();
  const profile = draft?.profile;
  if (!profile) return found;
  for (const item of draft.diagnostics)
    for (const { sheet, header } of columnsOfIssue(profile, item)) {
      const id = columnId(sheet, header);
      found.set(id, [...(found.get(id) ?? []), item]);
    }
  return found;
}

/** A column's status in the source pane: its key, mapped, ignored, not mapped, or with an issue. */
export function columnState(
  draft: DraftProfile | undefined,
  issues: Map<string, ModelDiagnostic[]>,
  sheet: string,
  header: string,
): ColumnState {
  const profile = draft?.profile;
  const uses = usesOf(profile, sheet, header);
  const own = issues.get(columnId(sheet, header)) ?? [];
  if (own.length) return { status: "issue", uses, issues: own };
  if (profile?.ignoredSheets?.includes(sheet)) return { status: "ignored", uses, issues: own };
  const fed = uses.filter((use) => !use.binding.ignore);
  if (!fed.length) return { status: uses.length ? "ignored" : "unmapped", uses, issues: own };
  const keyed = fed.some(
    ({ source, binding }) =>
      source.key?.column === header ||
      (binding.attributeTypeKey !== undefined && source.key?.attributeTypeKey === binding.attributeTypeKey),
  );
  return { status: keyed ? "key" : "mapped", uses, issues: own };
}

/** The relation part of a binding, whichever form it takes. */
export function relationPart(binding: ProfileBinding): ProfileRelation | undefined {
  return binding.relation ?? binding.relationFlags ?? binding.parent;
}

/** The types a binding feeds: the row's type and the type at the far end. */
export function typesFed({ source, binding }: ColumnUse): string[] {
  if (binding.ignore) return [];
  const far = relationPart(binding)?.objectTypeKey;
  return far ? [source.objectTypeKey, far] : [source.objectTypeKey];
}

/** Every column (`columnId`) that feeds a type, as the row's record or at the far end. */
export function columnsOfType(profile: DraftProfileDocument | null | undefined, typeKey: string): Set<string> {
  const found = new Set<string>();
  for (const source of profile?.sources ?? [])
    for (const binding of source.columns)
      if (typesFed({ source, binding }).includes(typeKey))
        for (const header of binding.columns ?? [binding.column ?? ""])
          if (header) found.add(columnId(source.sheet, header));
  return found;
}

function relationName(outline: ModelDraftOutline, relation: ProfileRelation): string {
  const type = relationTypeOf(outline, relation.relationTypeKey ?? "");
  const name = relation.direction === "incoming" ? (type?.reverseName ?? type?.name) : type?.name;
  return name ?? relation.relationTypeKey ?? "";
}

/** What a column feeds, in words: "Item · Item code", "Item · Made of → Material". */
export function feedWords(outline: ModelDraftOutline, { source, binding }: ColumnUse, header: string): string {
  const type = typeName(outline, source.objectTypeKey);
  if (binding.ignore) return "Ignored";
  if (binding.field === "name") return `${type} · name`;
  if (binding.attributeTypeKey)
    return `${type} · ${attributeTypeOf(outline, binding.attributeTypeKey)?.name ?? binding.attributeTypeKey}`;
  if (binding.parent) return `${type}’s parent · ${typeName(outline, binding.parent.objectTypeKey ?? "")}`;
  const relation = binding.relation ?? binding.relationFlags;
  if (relation) {
    const far = typeName(outline, relation.objectTypeKey ?? "");
    const flag = binding.relationFlags?.targets?.[header];
    return `${type} · ${relationName(outline, relation)} → ${far}${flag ? ` “${flag}”` : ""}`;
  }
  const related = binding.relatedRecord;
  if (related) {
    const far = typeName(outline, related.objectTypeKey ?? "");
    const fills =
      related.field === "name"
        ? "name"
        : (attributeTypeOf(outline, related.attributeTypeKey ?? "")?.name ?? related.attributeTypeKey);
    const parent = related.parent?.value ?? (related.parent?.column ? `the ${related.parent.column} of the row` : "");
    return `${type} · ${relationName(outline, related)} → ${far} ${fills}${parent ? ` under ${parent}` : ""}`;
  }
  return type;
}

/** How a column is read, in words. */
export function readingWords(binding: ProfileBinding): string {
  if (binding.ignore) return "Not read";
  if (binding.field === "name") return "The record's name";
  if (binding.attributeTypeKey) return "A value";
  if (binding.parent) return "The parent, by name";
  if (binding.relationFlags) return "A flag of a relation (Y, yes, x or 1)";
  if (binding.relation) return binding.relation.split ? "Related records, split" : "A related record (lookup)";
  if (binding.relatedRecord) return "A value of a related record";
  return "—";
}

export function matchWords(outline: ModelDraftOutline, relation: ProfileRelation | undefined): string {
  if (!relation?.matchBy) return "—";
  const far = typeName(outline, relation.objectTypeKey ?? "");
  if (relation.matchBy.field === "name") return `${far} by name`;
  if (relation.matchBy.field === "id") return `${far} by ID`;
  const attribute = relation.matchBy.attributeTypeKey ?? "";
  return `${far} by ${attributeTypeOf(outline, attribute)?.name ?? attribute}`;
}

/** The statistics of a column in a line: "200 of 200 filled · 187 distinct · candidate key". */
export function statisticsWords(column: SourceColumn): string {
  const parts = [`${column.filled} of ${column.rows} filled`, `${column.distinct} distinct`];
  if (column.candidateKey) parts.push("candidate key");
  const placeholders = column.placeholders.map((item) => `${item.value} ×${item.count}`);
  if (placeholders.length) parts.push(placeholders.join(", "));
  const delimiter = column.delimiters[0];
  if (delimiter && delimiter.share >= 0.05)
    parts.push(`${delimiterLabel(delimiter.character)} in ${delimiter.cells} rows`);
  return parts.join(" · ");
}

export function delimiterLabel(character: string): string {
  return character === "\n" ? "line break" : `“${character}”`;
}

/** The value type most of a column's cells read as, for a new attribute (text when none). */
export function likelyValueType(column: SourceColumn | undefined): string {
  if (!column) return "text";
  const order = ["boolean", "integer", "decimal", "date", "dateTime"];
  const filled = column.filled - column.placeholders.reduce((total, item) => total + item.count, 0);
  const found = order.find((type) => filled > 0 && (column.valueTypes[type] ?? 0) >= filled);
  return found ?? "text";
}

// --- Map to… ---

/** What a column holds, as Map to… asks (the mock-up's choices). */
export type MapKind = "name" | "attribute" | "parent" | "lookup" | "related" | "flag" | "ignore";

export const MAP_KINDS: { kind: MapKind; title: string; text: string }[] = [
  { kind: "name", title: "The record's name", text: "Each row's record is called this" },
  { kind: "attribute", title: "An attribute of the row's record", text: "One of its attributes, or a new one" },
  { kind: "parent", title: "The row's parent", text: "A record of the parent type, matched by name" },
  {
    kind: "lookup",
    title: "A related record",
    text: "Matched by name or a unique attribute; a delimiter splits several",
  },
  {
    kind: "related",
    title: "A value of a related record",
    text: "Its name or an attribute, under a parent record: a translation under its language",
  },
  { kind: "flag", title: "A flag of a relation", text: "Y, yes, x or 1 relates the row to one chosen record" },
  { kind: "ignore", title: "Nothing: ignore it", text: "Kept out of the load and of the issues" },
];

/** The value Map to… gives a new attribute, beside the existing ones. */
export const NEW_ATTRIBUTE = "__new__";

export interface MapTarget {
  value: string;
  name: string;
  note: string;
  /** The type the target reaches or belongs to, for its tile. */
  typeKey: string;
}

/** A relation as Map to… names it: its type, its two ends. */
export const relationValue = (relation: Pick<OutlineRelation, "relationType" | "from" | "to">) =>
  [relation.relationType, relation.from, relation.to].join("\u0000");

/** The relations a row's type may have to other records, the containment ones left to the parent. */
export function lookupRelations(outline: ModelDraftOutline, rowType: string): OutlineRelation[] {
  return outline.relations.filter((item) => !item.containment && (item.from === rowType || item.to === rowType));
}

export function mapTargets(kind: MapKind, rowType: string, outline: ModelDraftOutline): MapTarget[] {
  const type = objectTypeOf(outline, rowType);
  if (!type) return [];
  if (kind === "attribute")
    return [
      ...type.attributes.map((item) => ({
        value: item.attributeType,
        name: item.name,
        note: [item.unique ? "unique" : "", item.valueType ?? ""].filter(Boolean).join(", "),
        typeKey: rowType,
      })),
      { value: NEW_ATTRIBUTE, name: `New attribute on ${type.name}…`, note: "", typeKey: rowType },
    ];
  if (kind === "parent")
    return type.parents.map((key) => ({ value: key, name: typeName(outline, key), note: "by name", typeKey: key }));
  if (kind === "lookup" || kind === "flag" || kind === "related")
    return lookupRelations(outline, rowType).map((item) => {
      const incoming = item.from !== rowType;
      const far = incoming ? item.from : item.to;
      const relation = relationTypeOf(outline, item.relationType);
      const name = (incoming ? relation?.reverseName : relation?.name) ?? item.relationType;
      return {
        value: relationValue(item),
        name: `${name} → ${typeName(outline, far)}`,
        note: item.cardinality ?? "",
        typeKey: far,
      };
    });
  return [];
}

/** What Map to… has chosen, beside the column it maps. */
export interface MapChoice {
  sheet: string;
  header: string;
  /** The type each row of the sheet is a record of. */
  rowType: string;
  kind: MapKind;
  /** A target of `mapTargets`, for the kinds that have one. */
  target?: string;
  /** A new attribute's name and value type, and whether it is unique. */
  newAttribute?: { name: string; valueType: string; unique: boolean };
  /** The attribute becomes the source's key. */
  useAsKey?: boolean;
  /** A lookup's delimiter, when a cell names several. */
  split?: string;
  /** Records the cells name that do not exist are created by the load (D77). */
  create?: boolean;
  /** The record a flag column relates the row to, by its name. */
  flagTarget?: string;
  /** A lookup matched by a unique attribute of the far type instead of the name (0.10 A6b). */
  matchAttribute?: string;
  /** A value of a related record (0.10 A6b): what it fills, and the parent record it stands under. */
  related?: {
    /** `name`, or an attribute type's key. */
    fills: string;
    parentType: string;
    /** The parent record's name, or the column of the row holding it. */
    parentValue?: string;
    parentColumn?: string;
    createParent: boolean;
  };
}

/**
 * The type a sheet's rows are records of, before anything maps it: the sheet's first source's;
 * else a type named as the sheet (its name or plural name, any case); else the first type the
 * draft adds; else the first type.
 */
export function likelyRowType(
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
  sheet: string,
): string {
  const loaded = profile?.sources.find((source) => source.sheet === sheet)?.objectTypeKey;
  if (loaded) return loaded;
  const name = sheet.trim().toLowerCase();
  const named = outline.objectTypes.find(
    (type) => type.name.toLowerCase() === name || type.pluralName.toLowerCase() === name,
  );
  return (named ?? outline.objectTypes.find((type) => type.mark === "new") ?? outline.objectTypes[0])?.key ?? "";
}

/** A new source's id, as `addSource` makes one: from the sheet and the type, unique in the profile. */
export function newSourceId(profile: DraftProfileDocument | null | undefined, sheet: string, rowType: string): string {
  return keyFromLabel(`${sheet} ${rowType}`, new Set((profile?.sources ?? []).map((source) => source.id)));
}

/** The source on the sheet loading the type, if one does. */
export function sourceFor(
  profile: DraftProfileDocument | null | undefined,
  sheet: string,
  rowType: string,
): ProfileSource | undefined {
  return profile?.sources.find((source) => source.sheet === sheet && source.objectTypeKey === rowType);
}

/**
 * The one request a Map to… choice sends: a new attribute first, a source of the row's type on the
 * sheet when none loads it, then the column's binding (D76: a column dropped onto a type with no
 * source on that sheet starts one).
 */
export function mapOperations(
  choice: MapChoice,
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const operations: DraftOperation[] = [];
  let attribute = choice.kind === "attribute" ? choice.target : undefined;
  if (choice.kind === "attribute" && choice.target === NEW_ATTRIBUTE && choice.newAttribute) {
    attribute = keyFromLabel(choice.newAttribute.name, keysOf(outline));
    operations.push(
      {
        kind: "addAttributeType",
        key: attribute,
        name: choice.newAttribute.name,
        valueType: choice.newAttribute.valueType,
        features: choice.newAttribute.unique ? { unique: true } : {},
      },
      { kind: "attachAttribute", objectType: choice.rowType, attributeType: attribute },
    );
  }
  const key = choice.useAsKey && attribute ? { attributeTypeKey: attribute } : undefined;
  const existing = sourceFor(profile, choice.sheet, choice.rowType);
  const source = existing?.id ?? newSourceId(profile, choice.sheet, choice.rowType);
  if (!existing)
    operations.push({
      kind: "addSource",
      id: source,
      sheet: choice.sheet,
      objectType: choice.rowType,
      ...(key ? { key } : {}),
    });
  const column = { source, column: choice.header };
  const relation = () => {
    const [relationTypeKey, from, to] = (choice.target ?? "").split("\u0000");
    const incoming = from !== choice.rowType;
    return {
      relationTypeKey,
      objectTypeKey: incoming ? from : to,
      ...(incoming ? { direction: "incoming" } : {}),
    };
  };
  switch (choice.kind) {
    case "name":
      operations.push({ kind: "mapColumn", ...column, binding: { field: "name" } });
      break;
    case "attribute":
      operations.push({ kind: "mapColumn", ...column, binding: { attributeTypeKey: attribute } });
      if (key && existing) operations.push({ kind: "setSource", source, key });
      break;
    case "parent":
      operations.push({
        kind: "mapColumn",
        ...column,
        binding: {
          parent: {
            objectTypeKey: choice.target,
            matchBy: { field: "name" },
            ...(choice.create ? { missing: "create" } : {}),
          },
        },
      });
      break;
    case "lookup":
      operations.push({
        kind: "mapColumn",
        ...column,
        binding: {
          relation: {
            ...relation(),
            matchBy: choice.matchAttribute ? { attributeTypeKey: choice.matchAttribute } : { field: "name" },
            ...(choice.split ? { split: choice.split } : {}),
            // Only a match by name creates what it does not find (CREATE_NEEDS_NAME_MATCH).
            ...(choice.create && !choice.matchAttribute ? { missing: "create" } : {}),
          },
        },
      });
      break;
    case "related": {
      const related = choice.related;
      if (!related) break;
      const reach = relation();
      const far = reach.objectTypeKey;
      operations.push({
        kind: "mapColumn",
        ...column,
        binding: {
          relatedRecord: {
            ...reach,
            applicationKey: outline.applications.find((item) => item.objectTypeKeys.includes(far))?.key,
            parent: {
              objectTypeKey: related.parentType,
              matchBy: { field: "name" },
              ...(related.parentColumn ? { column: related.parentColumn } : { value: related.parentValue ?? "" }),
              ...(related.createParent ? { missing: "create" } : {}),
            },
            ...(related.fills === "name" ? { field: "name" } : { attributeTypeKey: related.fills }),
          },
        },
      });
      break;
    }
    case "flag":
      operations.push({
        kind: "setColumnReading",
        ...column,
        reading: "relationFlag",
        ...relation(),
        target: choice.flagTarget || choice.header,
      });
      break;
    case "ignore":
      operations.push({ kind: "ignoreColumn", ...column });
      break;
  }
  return operations;
}

/**
 * Where a column dropped on a type in the model pane goes (D76): the sheet's source of that type
 * when there is one; else a source on the sheet whose type reaches it, as its parent or a related
 * record; else a new source of that type, the column its name.
 */
export function dropChoice(
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
  sheet: string,
  typeKey: string,
): Pick<MapChoice, "rowType" | "kind" | "target"> {
  if (sourceFor(profile, sheet, typeKey)) return { rowType: typeKey, kind: "attribute" };
  for (const source of profile?.sources.filter((item) => item.sheet === sheet) ?? []) {
    if (objectTypeOf(outline, source.objectTypeKey)?.parents.includes(typeKey))
      return { rowType: source.objectTypeKey, kind: "parent", target: typeKey };
    const reach = lookupRelations(outline, source.objectTypeKey).find(
      (item) => (item.from === source.objectTypeKey ? item.to : item.from) === typeKey,
    );
    if (reach) return { rowType: source.objectTypeKey, kind: "lookup", target: relationValue(reach) };
  }
  return { rowType: typeKey, kind: "name" };
}

// --- history ---

type Names = (kind: "objectType" | "attributeType" | "relationType", key: string) => string;

const text = (value: unknown) => (typeof value === "string" ? value : "");

function bindingTarget(binding: ProfileBinding, names: Names): string {
  if (binding.field === "name") return "the name";
  if (binding.attributeTypeKey) return names("attributeType", binding.attributeTypeKey);
  if (binding.parent) return `the parent ${names("objectType", text(binding.parent.objectTypeKey))}`;
  const relation = binding.relation;
  if (relation)
    return `${names("relationType", text(relation.relationTypeKey))} → ${names("objectType", text(relation.objectTypeKey))}`;
  if (binding.relatedRecord) return "a related record";
  return "a target";
}

/** A source or mapping kind in words for the history (0.10 A5); `undefined` for any other kind. */
export function describeMappingOperation(kind: string, p: Record<string, unknown>, names: Names): string | undefined {
  const column = text(p.column);
  switch (kind) {
    case "setProfile":
      return `Named the import profile ${text(p.name) || text(p.key)}`;
    case "addSource":
      return `Started loading ${names("objectType", text(p.objectType))} from sheet ${text(p.sheet)}`;
    case "setSource":
      return p.key && typeof p.key === "object" && "attributeTypeKey" in p.key
        ? `Made ${names("attributeType", text((p.key as { attributeTypeKey?: string }).attributeTypeKey))} the key of source ${text(p.source)}`
        : `Changed source ${text(p.source)}`;
    case "removeSource":
      return `Removed source ${text(p.source)}`;
    case "setMissing":
      return p.missing === "delete"
        ? `Records missing from the file are deleted from source ${text(p.source)} in a change set`
        : `Records missing from the file are kept for source ${text(p.source)}`;
    case "ignoreSheet":
      return `Ignored sheet ${text(p.sheet)}`;
    case "mapColumn":
      return `Mapped ${column} to ${bindingTarget((p.binding ?? {}) as ProfileBinding, names)}`;
    case "setColumnReading":
      return p.reading === "relationFlag"
        ? `Read ${column} as a flag of ${names("relationType", text(p.relationTypeKey))} → ${text(p.target)}`
        : `Read ${column} as ${p.reading === "text" ? "a value" : `a ${text(p.reading)}`}`;
    case "splitColumn":
      return p.delimiter ? `Split ${column} on ${delimiterLabel(text(p.delimiter))}` : `Stopped splitting ${column}`;
    case "ignoreColumn":
      return `Ignored column ${column}`;
    case "addValuesToList":
      return p.create === false
        ? `Values of ${column} that do not exist are refused`
        : `Values of ${column} that do not exist are created`;
    case "setValueMap":
      return p.entries === null
        ? `Removed value map ${text(p.name)}`
        : `Set value map ${text(p.name)}${column ? ` for ${column}` : ""}`;
    default:
      return undefined;
  }
}
