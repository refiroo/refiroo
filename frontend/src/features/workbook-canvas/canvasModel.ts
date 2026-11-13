/**
 * What the workbook canvas draws and what its gestures send (0.17 PL3b): pure functions over the
 * draft's outline, its import profile and its dry run. The canvas is a view of the model draft
 * (PP-D3): it keeps no model of its own, and every gesture becomes operations of the kinds the
 * model editor sends, in one request and one undo step (PP-D4).
 */

import { bound, nameOfType, niceName, valueTypeOf } from "@/features/model-editor/columnDrop";
import { valueTypeLabel } from "@/features/model-editor/operations";
import { keyFromLabel, keysOf } from "@/model/outline";
import { NEW_ATTRIBUTE, mapOperations, newSourceId, usesOf } from "@/features/model-editor/mapping";
import { applicationForType } from "@/features/model-editor/typeApplication";
import type { JobRow } from "@/types/integration";
import type { EngineModel, TableViewDefinition } from "@/types/model";
import type {
  DraftOperation,
  ModelDraftOutline,
  OutlineMark,
  OutlineObjectType,
  OutlineRelation,
} from "@/types/modelAdmin";
import type {
  CanvasScope,
  DraftProfileDocument,
  DryRun,
  JoinCandidate,
  JoinCandidates,
  JoinCandidatesRequest,
  ProfileBinding,
  ProfileRelation,
  ProfileSource,
  SourceColumn,
  SourceSheet,
} from "@/types/sources";

/** A row of a card: the record's name, one of its fields, or what reaches another list. */
export interface CanvasField {
  /** Stable within its card: `name`, `attribute:<key>`, `parent:<type>`, `relation:<type>:<far>`. */
  id: string;
  label: string;
  kind: "name" | "attribute" | "parent" | "relation";
  /** The attribute type, for an attribute. */
  attributeTypeKey?: string;
  /** The list at the other end, for a parent or a relationship. */
  farType?: string;
  relationType?: string;
  /** The workbook columns that fill it, each with its sheet and source. */
  columns: { sheet: string; source: string; header: string }[];
  required: boolean;
  unique: boolean;
  /** What a row says beside its name: the value type, or how many of the far list a relationship reaches. */
  typeLabel?: string;
  /** Put there by the inference or an assistant and not touched since (the editor's Proposed). */
  proposed: boolean;
}

/** A filter a list's table view offers, by the attribute it filters on. */
export interface CanvasFilter {
  key: string;
  label: string;
}

export interface CanvasCard {
  typeKey: string;
  name: string;
  pluralName: string;
  applicationKey?: string;
  /** Made by this draft, not yet in a release. */
  added: boolean;
  /** New, changed from the base release, or released as it is (the editor's mark). */
  mark: OutlineMark;
  /** A released list nothing changed and no sheet loads: drawn quieter on a board of the whole model (CE1). */
  quiet: boolean;
  /** Drawn as its top bar only (kept on the draft's canvas, PP-D87). */
  folded: boolean;
  /** Put there by the inference or an assistant and not touched since. */
  proposed: boolean;
  /** The sheets that load it. */
  sheets: string[];
  fields: CanvasField[];
  /** What the list's table view filters by; empty while the model cannot be read. */
  filters: CanvasFilter[];
}

export interface CanvasLine {
  id: string;
  /** Solid for a parent and its children, dashed for a relationship. */
  kind: "contains" | "relates";
  from: string;
  to: string;
  label: string;
  relationType?: string;
  /** The field of the card it starts from that draws it. */
  fromField?: string;
}

export interface Position {
  x: number;
  y: number;
}

export const CARD_WIDTH = 320;
const CARD_HEAD = 44;
const FIELD_HEIGHT = 30;
const CARD_FILTERS = 30;
const CARD_FOOT = 34;
const CARD_NEW_FIELD = 30;
const COLUMN_SPACE = 72;
const ROW_SPACE = 28;
/** The room a frame leaves around its lists: the sides and bottom, and the top where its label stands. */
export const FRAME_PAD = 20;
export const FRAME_TOP = 36;
/**
 * The nearest a card stands to the board's top-left corner: far enough that the frame of its application,
 * with its label on the frame's top border, stays on the board. Every place a card gets (stored, dropped,
 * nudged, carried) is read against it.
 */
export const BOARD_EDGE: Position = { x: FRAME_PAD + 4, y: FRAME_TOP + 16 };
export const onBoard = (position: Position): Position => ({
  x: Math.max(BOARD_EDGE.x, position.x),
  y: Math.max(BOARD_EDGE.y, position.y),
});

/** Where a card's field row has its middle, from the card's top. */
export function fieldOffset(
  card: Pick<CanvasCard, "fields"> & { folded?: boolean },
  fieldId: string | undefined,
): number {
  const index = fieldId && !card.folded ? card.fields.findIndex((field) => field.id === fieldId) : -1;
  return index < 0 ? 22 : CARD_HEAD + index * FIELD_HEIGHT + FIELD_HEIGHT / 2;
}

/** How tall a card draws, so Tidy and the lines agree with the page without measuring it. */
export const cardHeight = (card: Pick<CanvasCard, "fields"> & { folded?: boolean }) =>
  card.folded
    ? CARD_HEAD
    : CARD_HEAD + Math.max(1, card.fields.length) * FIELD_HEIGHT + CARD_NEW_FIELD + CARD_FILTERS + CARD_FOOT;

function fieldsOf(
  type: OutlineObjectType,
  outline: ModelDraftOutline,
  profile: DraftProfileDocument | null | undefined,
  proposed: ReadonlySet<string>,
): CanvasField[] {
  const sources = (profile?.sources ?? []).filter((source) => source.objectTypeKey === type.key);
  const filledBy = (matches: (binding: ProfileBinding) => boolean) =>
    sources.flatMap((source) =>
      source.columns
        .filter((binding) => !binding.ignore && matches(binding))
        .flatMap((binding) => bound(binding).map((header) => ({ sheet: source.sheet, source: source.id, header }))),
    );
  const fields: CanvasField[] = [
    {
      id: "name",
      label: "Name",
      kind: "name",
      columns: filledBy((binding) => binding.field === "name"),
      required: true,
      unique: false,
      typeLabel: "text",
      proposed: false,
    },
    ...type.attributes.map((attribute): CanvasField => ({
      id: `attribute:${attribute.attributeType}`,
      label: attribute.name,
      kind: "attribute",
      attributeTypeKey: attribute.attributeType,
      columns: filledBy((binding) => binding.attributeTypeKey === attribute.attributeType),
      required: attribute.required,
      unique: attribute.unique,
      typeLabel: valueTypeLabel(attribute.valueType).toLowerCase(),
      proposed: proposed.has(`attributeType:${attribute.attributeType}`),
    })),
  ];
  for (const parent of type.parents)
    fields.push({
      id: `parent:${parent}`,
      label: `In ${nameOfType(outline, parent)}`,
      kind: "parent",
      farType: parent,
      columns: filledBy((binding) => binding.parent?.objectTypeKey === parent),
      required: !type.rootCreatable,
      unique: false,
      typeLabel: "parent",
      proposed: false,
    });
  for (const relation of outline.relations) {
    if (relation.containment || (relation.from !== type.key && relation.to !== type.key)) continue;
    // A relationship is drawn on the list it starts from; one to itself once.
    if (relation.from !== type.key) continue;
    const relationType = outline.relationTypes.find((item) => item.key === relation.relationType);
    fields.push({
      id: `relation:${relation.relationType}:${relation.to}`,
      label: relationType?.name ?? relation.relationType,
      kind: "relation",
      farType: relation.to,
      relationType: relation.relationType,
      columns: filledBy(
        (binding) =>
          (binding.relation?.relationTypeKey === relation.relationType &&
            binding.relation.objectTypeKey === relation.to) ||
          (binding.relationFlags?.relationTypeKey === relation.relationType &&
            binding.relationFlags.objectTypeKey === relation.to),
      ),
      required: relation.required,
      unique: false,
      // The far end's count: "many to one" reaches one, "many to many" reaches many.
      typeLabel: (relation.cardinality ?? "many-to-many").split("-to-")[1] ?? "many",
      proposed: proposed.has(`relationType:${relation.relationType}`),
    });
  }
  // A field is Proposed when its element is, or a column reading into it still is as the inference bound it.
  return fields.map((field) => ({
    ...field,
    proposed:
      field.proposed || field.columns.some((column) => proposed.has(`column:${column.source}/${column.header}`)),
  }));
}

/**
 * What the board shows (CE1, PP-D81): every list (`model`), the lists the draft adds or changes and the ones their
 * parents stand under (`changed`), or those and every list a sheet loads (`workbook`, the board's first form).
 */
export const SCOPES: readonly { id: CanvasScope; label: string }[] = [
  { id: "model", label: "Whole model" },
  { id: "changed", label: "Changed in this draft" },
  { id: "workbook", label: "From the workbook" },
];

/** The scope a draft opens on when none was chosen: the workbook's lists when it has one, else the whole model. */
export const defaultScope = (hasWorkbook: boolean): CanvasScope => (hasWorkbook ? "workbook" : "model");

export function cardsOf(
  outline: ModelDraftOutline,
  profile: DraftProfileDocument | null | undefined,
  proposed: ReadonlySet<string> = new Set(),
  model?: EngineModel,
  view: { scope?: CanvasScope; folded?: ReadonlySet<string> } = {},
): CanvasCard[] {
  const scope = view.scope ?? "workbook";
  const loaded = new Set((profile?.sources ?? []).map((source) => source.objectTypeKey));
  const reached = new Set<string>();
  for (const type of outline.objectTypes)
    if (scope === "model" || type.mark !== "released" || (scope === "workbook" && loaded.has(type.key))) {
      reached.add(type.key);
      type.parents.forEach((parent) => reached.add(parent));
    }
  return outline.objectTypes
    .filter((type) => reached.has(type.key))
    .map((type) => ({
      typeKey: type.key,
      name: type.name,
      pluralName: type.pluralName,
      applicationKey: type.home ?? outline.applications.find((item) => item.objectTypeKeys.includes(type.key))?.key,
      added: type.mark === "new",
      mark: type.mark,
      quiet: type.mark === "released" && !loaded.has(type.key) && !proposed.has(`objectType:${type.key}`),
      folded: view.folded?.has(type.key) ?? false,
      proposed: proposed.has(`objectType:${type.key}`),
      sheets: [
        ...new Set(
          (profile?.sources ?? []).filter((source) => source.objectTypeKey === type.key).map((item) => item.sheet),
        ),
      ],
      fields: fieldsOf(type, outline, profile, proposed),
      filters: filtersOf(outline, model, type.key, type.home ?? undefined),
    }));
}

/** The application's table view of a list, where its filters live. */
export function tableViewOf(
  model: EngineModel | undefined,
  typeKey: string,
  applicationKey?: string,
): { applicationKey: string; view: TableViewDefinition } | undefined {
  if (!model) return undefined;
  const application = applicationForType(model.applications, typeKey, applicationKey);
  const view = application?.views.find(
    (item): item is TableViewDefinition => item.type === "table" && item.objectTypeKey === typeKey,
  );
  return application && view ? { applicationKey: application.key, view } : undefined;
}

/** A filter field named as a person reads it: an attribute's name, or the relationship a `related:` field reads. */
function filterLabel(outline: ModelDraftOutline, key: string): string {
  if (key === "name") return "Name";
  const attribute = outline.attributeTypes.find((item) => item.key === key);
  if (attribute) return attribute.name;
  const relationKey = key.startsWith("related:") ? key.slice("related:".length).split(".")[0] : key;
  // A relationship is filtered by under its own key or its reverse side's: each side has its name.
  const forward = outline.relationTypes.find((item) => item.key === relationKey);
  if (forward) return forward.name;
  const reverse = outline.relationTypes.find((item) => item.reverseKey === relationKey);
  return reverse ? (reverse.reverseName ?? reverse.name) : relationKey;
}

/** The filters a list's table view has, named as the model names them. */
export function filtersOf(
  outline: ModelDraftOutline,
  model: EngineModel | undefined,
  typeKey: string,
  applicationKey?: string,
): CanvasFilter[] {
  const view = tableViewOf(model, typeKey, applicationKey)?.view;
  return (view?.config.filterFields ?? []).map((key) => ({
    key,
    label: filterLabel(outline, key),
  }));
}

/** The lines between the cards on the board. */
export function linesOf(outline: ModelDraftOutline, cards: readonly CanvasCard[]): CanvasLine[] {
  const on = new Set(cards.map((card) => card.typeKey));
  const lines: CanvasLine[] = [];
  for (const card of cards) {
    const type = outline.objectTypes.find((item) => item.key === card.typeKey);
    for (const parent of type?.parents ?? [])
      // A list that contains itself has no line to draw: it would run from the card to itself.
      if (on.has(parent) && parent !== card.typeKey)
        lines.push({
          id: `contains:${parent}:${card.typeKey}`,
          kind: "contains",
          from: parent,
          to: card.typeKey,
          label: `${nameOfType(outline, parent)} contains ${card.name}`,
        });
  }
  for (const relation of outline.relations) {
    if (relation.containment || relation.from === relation.to || !on.has(relation.from) || !on.has(relation.to))
      continue;
    const relationType = outline.relationTypes.find((item) => item.key === relation.relationType);
    lines.push({
      id: `relates:${relation.relationType}:${relation.from}:${relation.to}`,
      kind: "relates",
      from: relation.from,
      to: relation.to,
      label: `${nameOfType(outline, relation.from)} ${relationType?.name ?? relation.relationType} ${nameOfType(outline, relation.to)}`,
      relationType: relation.relationType,
      fromField: `relation:${relation.relationType}:${relation.to}`,
    });
  }
  return lines;
}

/** One application's lists in columns inside its frame, each list followed by the lists it contains. */
function tidyGroup(
  group: readonly CanvasCard[],
  parentOf: ReadonlyMap<string, string>,
  columns: number,
): { at: Record<string, Position>; width: number; height: number } {
  const keys = new Set(group.map((card) => card.typeKey));
  const ordered: CanvasCard[] = [];
  const seen = new Set<string>();
  const take = (card: CanvasCard) => {
    if (seen.has(card.typeKey)) return;
    seen.add(card.typeKey);
    ordered.push(card);
    for (const child of group) if (parentOf.get(child.typeKey) === card.typeKey) take(child);
  };
  for (const card of group) if (!parentOf.has(card.typeKey) || !keys.has(parentOf.get(card.typeKey)!)) take(card);
  for (const card of group) take(card);
  const count = Math.max(1, Math.min(columns, ordered.length));
  const heights = Array.from({ length: count }, () => 0);
  const at: Record<string, Position> = {};
  for (const card of ordered) {
    // The shortest column takes the next card: the frame's width is used before its height.
    const column = heights.indexOf(Math.min(...heights));
    at[card.typeKey] = { x: column * (CARD_WIDTH + COLUMN_SPACE), y: heights[column] };
    heights[column] += cardHeight(card) + ROW_SPACE;
  }
  const used = new Set(Object.values(at).map((position) => position.x)).size;
  return {
    at,
    width: used * CARD_WIDTH + (used - 1) * COLUMN_SPACE,
    height: Math.max(...heights) - ROW_SPACE,
  };
}

/**
 * Tidy: each application's lists in a frame of their own, the frames laid left to right and wrapped to the
 * board's width, inside a frame as many columns as fit, each list followed by the lists it contains, the next
 * list always in the shortest column. A list that stands in no application has no frame. Positions are the
 * board's, never the model's.
 */
export function tidy(
  cards: readonly CanvasCard[],
  lines: readonly CanvasLine[],
  width: number,
): Record<string, Position> {
  const parentOf = new Map<string, string>();
  for (const line of lines) if (line.kind === "contains" && !parentOf.has(line.to)) parentOf.set(line.to, line.from);
  const groups = new Map<string, CanvasCard[]>();
  for (const card of cards) {
    const list = groups.get(card.applicationKey ?? "") ?? [];
    list.push(card);
    groups.set(card.applicationKey ?? "", list);
  }
  const positions: Record<string, Position> = {};
  // Applications share a row: as many frames side by side as fit one column of lists each, each frame taking an equal
  // share of the width, so one application does not take the whole row and push the others below it.
  const perRow = Math.max(
    1,
    Math.min(groups.size, Math.floor((width - 24) / (CARD_WIDTH + 2 * FRAME_PAD + COLUMN_SPACE / 2))),
  );
  let x = 24;
  let y = 24;
  let rowHeight = 0;
  for (const [application, group] of groups) {
    const framed = application !== "";
    const pad = framed ? FRAME_PAD : 0;
    const top = framed ? FRAME_TOP : 0;
    const room = (perRow === 1 ? width - 24 : (width - 24) / perRow - COLUMN_SPACE / 2) - 2 * pad;
    const columns = Math.max(1, Math.floor((room + COLUMN_SPACE) / (CARD_WIDTH + COLUMN_SPACE)));
    const laid = tidyGroup(group, parentOf, columns);
    const frameWidth = laid.width + 2 * pad;
    if (x > 24 && x + frameWidth > width - 24) {
      x = 24;
      y += rowHeight + ROW_SPACE;
      rowHeight = 0;
    }
    for (const card of group)
      positions[card.typeKey] = { x: x + pad + laid.at[card.typeKey].x, y: y + top + laid.at[card.typeKey].y };
    x += frameWidth + COLUMN_SPACE / 2;
    rowHeight = Math.max(rowHeight, laid.height + top + pad);
  }
  return positions;
}

/** A frame round one application's lists on the board; drawn from the lists' places, never stored. */
export interface CanvasFrame {
  applicationKey: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  typeKeys: string[];
}

/** The frames of the applications the board shows, each round the places of its lists. */
export function framesOf(
  cards: readonly CanvasCard[],
  at: (card: CanvasCard) => Position,
  outline: ModelDraftOutline,
): CanvasFrame[] {
  const byApplication = new Map<string, CanvasCard[]>();
  for (const card of cards) {
    if (!card.applicationKey) continue;
    const list = byApplication.get(card.applicationKey) ?? [];
    list.push(card);
    byApplication.set(card.applicationKey, list);
  }
  return [...byApplication].map(([applicationKey, group]) => {
    const boxes = group.map((card) => ({ ...at(card), height: cardHeight(card) }));
    const left = Math.min(...boxes.map((box) => box.x));
    const top = Math.min(...boxes.map((box) => box.y));
    const right = Math.max(...boxes.map((box) => box.x + CARD_WIDTH));
    const bottom = Math.max(...boxes.map((box) => box.y + box.height));
    // A list placed near the board's edge keeps its frame on the board: the frame is cut there, never off it.
    const x = Math.max(0, left - FRAME_PAD);
    const y = Math.max(16, top - FRAME_TOP);
    return {
      applicationKey,
      name: outline.applications.find((item) => item.key === applicationKey)?.name ?? applicationKey,
      x,
      y,
      width: right + FRAME_PAD - x,
      height: bottom + FRAME_PAD - y,
      typeKeys: group.map((card) => card.typeKey),
    };
  });
}

/**
 * Cards that stand over one another are moved apart: in reading order (top, then left), a card whose box overlaps
 * one already settled goes down below it, keeping its x, until no two overlap. A layout stored before a card
 * grew (its New attribute and Filters rows) is read this way, so it needs no Tidy.
 */
export function apart(cards: readonly CanvasCard[], at: Readonly<Record<string, Position>>): Record<string, Position> {
  const result: Record<string, Position> = { ...at };
  const settled: { x: number; y: number; bottom: number }[] = [];
  const order = cards
    .filter((card) => at[card.typeKey])
    .sort((a, b) => at[a.typeKey].y - at[b.typeKey].y || at[a.typeKey].x - at[b.typeKey].x);
  for (const card of order) {
    const height = cardHeight(card);
    const { x } = at[card.typeKey];
    let { y } = at[card.typeKey];
    for (;;) {
      const over = settled.find(
        (other) => Math.abs(other.x - x) < CARD_WIDTH && y < other.bottom && other.y < y + height,
      );
      if (!over) break;
      y = over.bottom + ROW_SPACE;
    }
    result[card.typeKey] = { x, y };
    settled.push({ x, y, bottom: y + height });
  }
  return result;
}

/**
 * A card folded or unfolded: the cards under it in its column of the same application move up by the height it gave up,
 * or down by the height it takes again, so a fold leaves no empty space in its frame. The places that change.
 */
export function closeUp(
  cards: readonly CanvasCard[],
  at: Readonly<Record<string, Position>>,
  typeKey: string,
  folded: boolean,
): Record<string, Position> {
  const card = cards.find((item) => item.typeKey === typeKey);
  const place = at[typeKey];
  if (!card || !place) return {};
  const change = cardHeight({ ...card, folded: false }) - cardHeight({ ...card, folded: true });
  const by = folded ? -change : change;
  const moved: Record<string, Position> = {};
  for (const other of cards) {
    const there = at[other.typeKey];
    if (other.typeKey === typeKey || !there || (other.applicationKey ?? "") !== (card.applicationKey ?? "")) continue;
    if (Math.abs(there.x - place.x) < CARD_WIDTH && there.y > place.y)
      moved[other.typeKey] = { x: there.x, y: there.y + by };
  }
  return moved;
}

/** The stored positions with a place for every card that has none yet, beside the ones that do. */
export function placed(
  cards: readonly CanvasCard[],
  lines: readonly CanvasLine[],
  stored: Readonly<Record<string, Position>>,
  width: number,
): Record<string, Position> {
  // A place stored before places were kept inside the board (or by another client) is read inside it:
  // no card stands above or left of the board's edge, where it could not be reached.
  const inside = onBoard;
  const kept: Record<string, Position> = {};
  for (const card of cards) if (stored[card.typeKey]) kept[card.typeKey] = inside(stored[card.typeKey]);
  const missing = cards.filter((card) => !kept[card.typeKey]);
  if (!missing.length) return apart(cards, kept);
  if (missing.length === cards.length) return tidy(cards, lines, width);
  const result: Record<string, Position> = { ...kept };
  const held = cards.filter((card) => kept[card.typeKey]);
  let y = Math.max(24, ...held.map((card) => kept[card.typeKey].y + cardHeight(card) + ROW_SPACE));
  let x = 24;
  for (const card of missing) {
    if (x + CARD_WIDTH > width - 24 && x > 24) {
      x = 24;
      y += cardHeight(card) + ROW_SPACE;
    }
    result[card.typeKey] = { x, y };
    x += CARD_WIDTH + COLUMN_SPACE;
  }
  return apart(cards, result);
}

/** A line's path between two cards: from the nearer side of one to the nearer side of the other. */
export function linePath(
  from: Position,
  fromHeight: number,
  to: Position,
  toHeight: number,
  /** How far down the card the line leaves it: a relationship leaves at its field's row. */
  fromOffset = 22,
): { d: string; mid: Position } {
  const fromRight = from.x + CARD_WIDTH <= to.x;
  const toRight = to.x + CARD_WIDTH <= from.x;
  const start = {
    x: fromRight ? from.x + CARD_WIDTH : toRight ? from.x : from.x + CARD_WIDTH / 2,
    y: from.y + fromOffset,
  };
  const end = { x: fromRight ? to.x : toRight ? to.x + CARD_WIDTH : to.x + CARD_WIDTH / 2, y: to.y + 22 };
  if (!fromRight && !toRight) {
    // One above the other: from the bottom of the upper to the top of the lower.
    const down = from.y <= to.y;
    start.y = down ? from.y + fromHeight : from.y;
    end.y = down ? to.y : to.y + toHeight;
  }
  const bend = fromRight || toRight ? Math.max(24, Math.abs(end.x - start.x) / 2) : 0;
  const lift = fromRight || toRight ? 0 : Math.max(24, Math.abs(end.y - start.y) / 2);
  const sx = fromRight ? bend : toRight ? -bend : 0;
  const sy = fromRight || toRight ? 0 : start.y <= end.y ? lift : -lift;
  return {
    d: `M ${start.x} ${start.y} C ${start.x + sx} ${start.y + sy}, ${end.x - sx} ${end.y - sy}, ${end.x} ${end.y}`,
    mid: { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 },
  };
}

// --- figures ---

export interface LoadFigures {
  state: "none" | "checking" | "checked" | "failed";
  total: number;
  loads: number;
  refused: number;
  /** Per list: the rows that load and the rows refused, with their reasons. */
  byType: Record<string, { loads: number; refused: number; reasons: { code: string; rows: number; source: number }[] }>;
}

/** What the dry run says of the whole workbook and of each list; every row is counted (D67). */
export function loadFigures(dryRun: DryRun | undefined): LoadFigures {
  const figures: LoadFigures = { state: "none", total: 0, loads: 0, refused: 0, byType: {} };
  if (!dryRun) return figures;
  if (dryRun.state === "checking") return { ...figures, state: "checking" };
  if (dryRun.state !== "completed" || !dryRun.summary) return { ...figures, state: "failed" };
  figures.state = "checked";
  figures.total = dryRun.summary.rows.total;
  for (const source of dryRun.summary.sources) {
    const loads = source.records.created + source.records.updated + source.records.unchanged;
    const refused = source.rejections.reduce((sum, item) => sum + item.rows, 0);
    figures.loads += loads;
    figures.refused += refused;
    const entry = (figures.byType[source.objectTypeKey] ??= { loads: 0, refused: 0, reasons: [] });
    entry.loads += loads;
    entry.refused += refused;
    // One line per source and reason: the rows behind it are read by the source.
    for (const rejection of source.rejections)
      entry.reasons.push({ code: rejection.code, rows: rejection.rows, source: source.source });
  }
  return figures;
}

// --- gestures ---

/** A field dragged back onto the workbook: its columns are left out of the load. */
export function leaveOutOperations(field: CanvasField): DraftOperation[] {
  return field.columns.map((item) => ({ kind: "ignoreColumn", source: item.source, column: item.header }));
}

/** Connect dropped on another card: the card it was dragged from goes under it. */
export function containOperations(child: string, parent: string, outline: ModelDraftOutline): DraftOperation[] {
  return [
    {
      kind: "setContainment",
      objectType: child,
      parent: {
        objectTypes: [parent],
        relationType: {
          name: `Contains ${nameOfType(outline, child)}`,
          reverseName: `In ${nameOfType(outline, parent)}`,
        },
      },
    },
  ];
}

/** The × of a solid line: the list goes back to the top level. */
export function releaseOperations(child: string): DraftOperation[] {
  return [{ kind: "setContainment", objectType: child, parent: null }];
}

/** Connect dropped on a field of another card, or on a card with Alt: a relationship between the two. */
export function relateOperations(from: string, to: string, outline: ModelDraftOutline): DraftOperation[] {
  return relatePlan(from, to, outline).operations;
}

/** The operations of a relationship and the key its relation type is given, which a join binding names. */
export function relatePlan(
  from: string,
  to: string,
  outline: ModelDraftOutline,
): { operations: DraftOperation[]; relationType: string } {
  const taken = keysOf(outline);
  const name = `Has ${nameOfType(outline, to)}`;
  const reverseName = `Of ${nameOfType(outline, from)}`;
  const relationType = keyFromLabel(`${nameOfType(outline, from)} ${nameOfType(outline, to)}`, taken);
  const reverseKey = keyFromLabel(
    `${nameOfType(outline, to)} of ${nameOfType(outline, from)}`,
    new Set([...taken, relationType]),
  );
  return {
    relationType,
    operations: [
      { kind: "addRelationType", key: relationType, reverseKey, name, reverseName },
      { kind: "allowRelation", relationType, from, to, cardinality: "many-to-many", required: false },
    ],
  };
}

/** The × of a dashed line. */
export function unrelateOperations(relation: Pick<OutlineRelation, "relationType" | "from" | "to">): DraftOperation[] {
  return [{ kind: "disallowRelation", relationType: relation.relationType, from: relation.from, to: relation.to }];
}

/** A list (its type key) or a view of any kind (`{ view }`) dropped on a navigation group, or on New group with its label. */
export function groupOperations(
  entry: string | { view: string },
  applicationKey: string,
  group: { key: string } | { label: string } | null,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const placed = typeof entry === "string" ? { collection: entry } : { view: entry.view };
  if (group && "label" in group) {
    const application = outline.applications.find((item) => item.key === applicationKey);
    const key = keyFromLabel(group.label, new Set(application?.navigation.groups.map((item) => item.key) ?? []));
    return [
      { kind: "addNavigationGroup", applicationKey, key, label: group.label, collapsed: false },
      { kind: "placeCollection", applicationKey, ...placed, group: key },
    ];
  }
  return [{ kind: "placeCollection", applicationKey, ...placed, group: group?.key ?? null }];
}

// --- joins over every row (PP-D8) ---

/** The column that names a list's records in the workbook, and how a record is found by it. */
export interface NameColumn {
  source: ProfileSource;
  header: string;
  matchBy: NonNullable<ProfileRelation["matchBy"]>;
}

/**
 * The column of the workbook that names a list's records: the one read as their name, else the one
 * holding the key a source loads them by (a record is then found by that unique attribute).
 */
export function nameColumnOf(
  profile: DraftProfileDocument | null | undefined,
  typeKey: string,
): NameColumn | undefined {
  const sources = (profile?.sources ?? []).filter((source) => source.objectTypeKey === typeKey);
  for (const source of sources) {
    const named = source.columns.find((binding) => !binding.ignore && binding.field === "name" && binding.column);
    if (named?.column) return { source, header: named.column, matchBy: { field: "name" } };
  }
  for (const source of sources) {
    const attribute = source.key?.attributeTypeKey;
    const keyed = attribute
      ? source.columns.find((binding) => !binding.ignore && binding.attributeTypeKey === attribute && binding.column)
      : undefined;
    if (attribute && keyed?.column) return { source, header: keyed.column, matchBy: { attributeTypeKey: attribute } };
  }
  return undefined;
}

const rectangleOfSource = (source: ProfileSource) => {
  const block = (source.block ?? {}) as { firstColumn?: string; lastColumn?: string; lastRow?: number | null };
  return {
    headerRow: source.headerRow,
    ...(block.firstColumn && block.lastColumn
      ? {
          block: {
            firstColumn: block.firstColumn,
            lastColumn: block.lastColumn,
            ...(block.lastRow ? { lastRow: block.lastRow } : {}),
          },
        }
      : {}),
  };
};

/** The question to the join route: the other list's name column against every column of the starting list's table. */
export function joinRequest(other: NameColumn, start: ProfileSource): JoinCandidatesRequest {
  return {
    column: { sheet: other.source.sheet, column: other.header, ...rectangleOfSource(other.source) },
    against: { sheet: start.sheet, ...rectangleOfSource(start) },
  };
}

/**
 * The columns that may carry the join: those the answer lists, but not one the starting source
 * already reads as something else. Best first by the rows each matches, then the values, then
 * column order, as the route orders them; two at the top of both figures are a tie and nothing is guessed.
 */
export function pickJoin(
  answer: JoinCandidates,
  start: ProfileSource,
): { best?: JoinCandidate; tied: JoinCandidate[] } {
  const taken = new Set(start.columns.filter((binding) => !binding.ignore).flatMap((binding) => bound(binding)));
  const usable = answer.candidates.filter((item) => item.header && item.matchedRows > 0 && !taken.has(item.header));
  if (!usable.length) return { tied: [] };
  const top = usable[0];
  const tied = usable.filter(
    (item) => item.matchedRows === top.matchedRows && item.matchedValues === top.matchedValues,
  );
  return tied.length > 1 ? { tied } : { best: top, tied: [] };
}

/**
 * Two lists that read the same sheet (a flat sheet that repeats its upper levels on every row): a row's
 * parent is named by the other list's own column in that row. The join route leaves the dropped column out
 * of its candidates when it is itself in the table, so the page takes it here, unless the starting list
 * already reads that column as something else.
 */
export function sameSheetJoin(start: ProfileSource, other: NameColumn): string | undefined {
  if (start.sheet !== other.source.sheet || start.id === other.source.id) return undefined;
  const taken = start.columns.some(
    (binding) => !binding.ignore && !binding.field && bound(binding).includes(other.header),
  );
  return taken ? undefined : other.header;
}

/** The binding that makes a join column the parent or the related record, found by the other list's name or key. */
export function joinBinding(
  kind: "parent" | "relation",
  other: { typeKey: string; matchBy: NonNullable<ProfileRelation["matchBy"]> },
  relationTypeKey?: string,
): ProfileBinding {
  const relation: ProfileRelation = {
    ...(kind === "relation" ? { relationTypeKey } : {}),
    objectTypeKey: other.typeKey,
    matchBy: other.matchBy,
    // Only a match by name creates what it does not find (CREATE_NEEDS_NAME_MATCH).
    ...(other.matchBy.field === "name" ? { missing: "create" as const } : {}),
  };
  return kind === "parent" ? { parent: relation } : { relation };
}

/** The `mapColumn` of a join: the column of the starting source that names the other list's records. */
export function joinOperations(
  kind: "parent" | "relation",
  start: ProfileSource,
  header: string,
  other: { typeKey: string; matchBy: NonNullable<ProfileRelation["matchBy"]> },
  relationTypeKey?: string,
): DraftOperation[] {
  return [{ kind: "mapColumn", source: start.id, column: header, binding: joinBinding(kind, other, relationTypeKey) }];
}

// --- a column onto a list's filters ---

/**
 * A column dropped on a list's Filters: its attribute is made filterable when it is not, mapped when
 * the column fills none yet, and added to the table view's `filterFields`, all in one request. The
 * answer says why nothing was built: the list has no table view to hold a filter, or already filters by it.
 */
export function filterOperations(
  where: { sheet: string; header: string; typeKey: string },
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
  model: EngineModel | undefined,
  column?: SourceColumn,
): { operations: DraftOperation[]; problem?: "noView" | "already" } {
  const home = outline.objectTypes.find((item) => item.key === where.typeKey)?.home ?? undefined;
  const target = tableViewOf(model, where.typeKey, home);
  if (!target) return { operations: [], problem: "noView" };
  const operations: DraftOperation[] = [];
  const use = usesOf(profile, where.sheet, where.header).find(
    (item) =>
      item.source.objectTypeKey === where.typeKey &&
      !item.binding.ignore &&
      (item.binding.attributeTypeKey || item.binding.field === "name"),
  );
  const attribute = use?.binding.attributeTypeKey ?? (use?.binding.field === "name" ? "name" : undefined);
  if (!attribute) {
    // A new filterable attribute is placed in the type's table views when it is attached (the engine's own
    // placement), so it joins the filters without a step of its own.
    const fresh = mapOperations(
      {
        sheet: where.sheet,
        header: where.header,
        rowType: where.typeKey,
        kind: "attribute",
        target: NEW_ATTRIBUTE,
        newAttribute: { name: niceName(where.header), valueType: valueTypeOf(column), unique: false, filterable: true },
      },
      profile,
      outline,
    );
    return { operations: fresh };
  } else if (attribute !== "name") {
    const type = outline.attributeTypes.find((item) => item.key === attribute);
    if (type && type.features.filterable !== true)
      operations.push({
        kind: "setAttributeTypeFeatures",
        attributeType: attribute,
        features: Object.fromEntries(
          ["searchable", "filterable", "sortable", "unique"].map((name) => [
            name,
            name === "filterable" ? true : type.features[name] === true,
          ]),
        ),
      });
  }
  if (target.view.config.filterFields.includes(attribute)) return { operations: [], problem: "already" };
  operations.push({
    kind: "insertViewItem",
    applicationKey: target.applicationKey,
    view: target.view.key,
    list: "filterFields",
    item: attribute,
  });
  return { operations };
}

// --- choosing columns ---

/**
 * The columns chosen after a press: a plain press chooses that one, Ctrl or Command toggles it, Shift
 * chooses everything from the last press to it, in the pane's order.
 */
export function chosenColumns(
  chosen: readonly string[],
  order: readonly string[],
  pressed: string,
  how: { shift?: boolean; toggle?: boolean },
  anchor?: string,
): string[] {
  if (how.shift && anchor && order.includes(anchor)) {
    const [from, to] = [order.indexOf(anchor), order.indexOf(pressed)].sort((a, b) => a - b);
    return order.slice(from, to + 1);
  }
  if (how.toggle) return chosen.includes(pressed) ? chosen.filter((item) => item !== pressed) : [...chosen, pressed];
  return chosen.length === 1 && chosen[0] === pressed ? [] : [pressed];
}

/** A card moved by the arrow keys: sixteen pixels a press, never off the board's top or left. */
export function nudged(position: Position, key: string, step = 16): Position | undefined {
  const delta: Record<string, Position> = {
    ArrowLeft: { x: -step, y: 0 },
    ArrowRight: { x: step, y: 0 },
    ArrowUp: { x: 0, y: -step },
    ArrowDown: { x: 0, y: step },
  };
  const move = delta[key];
  return move ? onBoard({ x: position.x + move.x, y: position.y + move.y }) : undefined;
}

// --- refused rows (PP-D4) ---

/** The wrong values a source's refused rows name, by column: each text with the rows it is found in. */
export interface WrongValues {
  column: string;
  values: { text: string; rows: number }[];
}

const NOT_FOUND = /^No .+? record matches ("(?:[^"\\]|\\.)*")/;

/**
 * What the rows refused as "no record matches" name: the text that found nothing and the column it
 * stands in, read from the refusal's own words and details. A refusal without a column (a record's key,
 * a parent fixed on the source) names nothing a value map could correct.
 */
export function wrongValuesOf(rows: readonly JobRow[]): WrongValues[] {
  const found = new Map<string, Map<string, number>>();
  for (const row of rows)
    for (const outcome of row.outcomes) {
      const error = outcome.error;
      const column = (error?.details as { column?: unknown } | undefined)?.column;
      const quoted = error?.code === "REFERENCE_NOT_FOUND" ? NOT_FOUND.exec(error.message)?.[1] : undefined;
      if (typeof column !== "string" || !quoted) continue;
      let text: string;
      try {
        text = String(JSON.parse(quoted));
      } catch {
        text = quoted.slice(1, -1);
      }
      const counts = found.get(column) ?? new Map<string, number>();
      counts.set(text, (counts.get(text) ?? 0) + 1);
      found.set(column, counts);
    }
  return [...found].map(([column, counts]) => ({
    column,
    values: [...counts].map(([text, count]) => ({ text, rows: count })).sort((a, b) => b.rows - a.rows),
  }));
}

/** A refusal's words from its first refused row: the engine's own message. */
export function reasonOf(rows: readonly JobRow[]): string | undefined {
  for (const row of rows) for (const outcome of row.outcomes) if (outcome.error?.message) return outcome.error.message;
  return undefined;
}

// --- a draft without an application ---

/**
 * A draft that has no application yet (a workbook refiroo read no list from by itself) gets one with
 * its first list, in the same request: named for the draft, and the new lists placed in it. Operations
 * that already name their application, and drafts that have one, pass through as they are.
 */
export function withApplication(
  operations: DraftOperation[],
  outline: ModelDraftOutline,
  draftName: string,
): DraftOperation[] {
  const homeless = (operation: DraftOperation) => operation.kind === "addObjectType" && !operation.applicationKey;
  if (outline.applications.length > 0 || !operations.some(homeless)) return operations;
  const name = draftName.trim() || "Workbook";
  const key = keyFromLabel(name, keysOf(outline));
  // Wherever the proposal left an application unnamed (a new list, a binding that reaches a record of
  // one), the new application is the one meant: there is no other.
  const placed = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(placed);
    if (value === null || typeof value !== "object") return value;
    return Object.fromEntries(
      Object.entries(value).map(([field, held]) => [
        field,
        field === "applicationKey" && (held === null || held === undefined) ? key : placed(held),
      ]),
    );
  };
  return [
    { kind: "addApplication", key, name },
    ...operations.map((operation) =>
      homeless(operation)
        ? ({ ...(placed(operation) as DraftOperation), applicationKey: key } as DraftOperation)
        : (placed(operation) as DraftOperation),
    ),
  ];
}

// --- a sheet onto the empty board ---

/**
 * A sheet dropped on the empty board: a new list named for the sheet, each of its columns a field,
 * every row a record (the plan's "a new list, its columns as fields"). The record's name is a text
 * column whose cells are all different, else the one with the most different values; every other column becomes a field of
 * the type its cells read as. One request: the list, its fields, its source and the bindings. The
 * person shapes it from there: a column dragged out becomes a list of its own, Connect makes the
 * hierarchy. Nothing is guessed about translations or flags.
 */
export function sheetAsListOperations(
  sheet: SourceSheet,
  columns: readonly SourceColumn[],
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const named = columns.filter((column) => column.header);
  if (!named.length) return [];
  const taken = keysOf(outline);
  const listName = niceName(sheet.name);
  const typeKey = keyFromLabel(listName, taken);
  taken.add(typeKey);
  // The name: a text column whose cells are all different; else the text column with the most different
  // values (a sheet that repeats its regions and operators on every row is named by its last level).
  const texts = named.filter((column) => valueTypeOf(column) === "text");
  const nameColumn =
    texts.find((column) => column.candidateKey) ?? [...texts].sort((a, b) => b.distinct - a.distinct)[0] ?? named[0];
  const source = newSourceId(profile, sheet.name, typeKey);
  const block = sheet.blocks[0];
  const operations: DraftOperation[] = [
    {
      kind: "addObjectType",
      ...(outline.applications[0] ? { applicationKey: outline.applications[0].key } : {}),
      key: typeKey,
      name: listName,
      // A sheet is named for what it holds already: the engine's "s" would make "Officess".
      pluralName: listName,
      parent: null,
    },
    {
      kind: "addSource",
      id: source,
      sheet: sheet.name,
      objectType: typeKey,
      ...(block?.headerRow ? { headerRow: block.headerRow } : sheet.headerRow ? { headerRow: sheet.headerRow } : {}),
    },
    { kind: "mapColumn", source, column: nameColumn.header, binding: { field: "name" } },
  ];
  for (const column of named) {
    if (column === nameColumn) continue;
    const attribute = keyFromLabel(niceName(column.header ?? ""), taken);
    taken.add(attribute);
    operations.push(
      {
        kind: "addAttributeType",
        key: attribute,
        name: niceName(column.header ?? ""),
        valueType: valueTypeOf(column),
        features: {},
      },
      { kind: "attachAttribute", objectType: typeKey, attributeType: attribute },
      { kind: "mapColumn", source, column: column.header, binding: { attributeTypeKey: attribute } },
    );
  }
  return operations;
}

// --- a column onto the empty board ---

/** Where a drop on the board lands: the drop point, at least 16px in from the board's top and left edges. */
export const dropPlace = (at: Position): Position => onBoard(at);

/**
 * A column dropped on the empty board: a new list named for the column whose records are the column's
 * distinct values. Where a list already reads the sheet, that list gets a relationship to it, filled
 * by the column (the relation binding creates the records it does not find, by name); a column the
 * list already reads as an attribute is turned into the list instead (`convertAttributeToListType`,
 * which does the same to the binding). With no list on the sheet, the new list reads the column itself
 * as its name, one record to a value. One request, built from existing operations; nothing is inferred.
 * An empty answer says the column is read as something this cannot replace (its list's name, a parent
 * or a relationship): the page says so.
 */
export function columnAsListOperations(
  sheet: Pick<SourceSheet, "name" | "headerRow" | "blocks">,
  header: string,
  profile: DraftProfileDocument | null | undefined,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const taken = keysOf(outline);
  const listName = niceName(header);
  const typeKey = keyFromLabel(listName, taken);
  taken.add(typeKey);
  const start = (profile?.sources ?? []).find((item) => item.sheet === sheet.name);
  const applicationKey = start?.applicationKey ?? outline.applications[0]?.key;
  const newList: DraftOperation = {
    kind: "addObjectType",
    ...(applicationKey ? { applicationKey } : {}),
    key: typeKey,
    name: listName,
    // The list is named for the column: its plural is the same word, not the engine's "s" added.
    pluralName: listName,
    parent: null,
  };
  // The new list reads the column itself, one record to a value (a blank cell is no value and is skipped): the list
  // then has a source, so Connect can find the column that names its parent by the join.
  const block = sheet.blocks[0];
  const id = newSourceId(profile, sheet.name, typeKey);
  const headerRow = block?.headerRow ?? sheet.headerRow;
  const ownSource: DraftOperation[] = [
    {
      kind: "addSource",
      id,
      sheet: sheet.name,
      objectType: typeKey,
      ...(applicationKey ? { applicationKey } : {}),
      ...(headerRow ? { headerRow } : {}),
      key: { field: "name" },
    },
    { kind: "mapColumn", source: id, column: header, binding: { field: "name" } },
  ];
  if (!start) return [newList, ...ownSource];
  const owner = nameOfType(outline, start.objectTypeKey);
  const relationType = keyFromLabel(`${owner} ${listName}`, taken);
  const reverseKey = keyFromLabel(`${listName} of ${owner}`, new Set([...taken, relationType]));
  const used = start.columns.find((binding) => !binding.ignore && bound(binding).includes(header));
  if (used) {
    if (!used.attributeTypeKey) return [];
    return [
      {
        kind: "convertAttributeToListType",
        objectType: start.objectTypeKey,
        attributeType: used.attributeTypeKey,
        key: typeKey,
        name: listName,
        pluralName: listName,
        relationType: { key: relationType, reverseKey, name: `Has ${listName}`, reverseName: `Of ${owner}` },
      },
      ...ownSource,
    ];
  }
  return [
    newList,
    { kind: "addRelationType", key: relationType, reverseKey, name: `Has ${listName}`, reverseName: `Of ${owner}` },
    {
      kind: "allowRelation",
      relationType,
      from: start.objectTypeKey,
      to: typeKey,
      cardinality: "many-to-many",
      required: false,
    },
    ...joinOperations("relation", start, header, { typeKey, matchBy: { field: "name" } }, relationType),
    ...ownSource,
  ];
}
