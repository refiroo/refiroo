/**
 * What the canvas does with the whole model (0.17 CE1): zoom and centring, Find, the operations a gesture by
 * hand sends (a new list, a new field), and the editor's operation target of each thing on the board. Pure
 * functions; the canvas sends what the editor's operation table builds and keeps no table of its own (PP-D3).
 */

import {
  attributePositionOperations,
  initialValues,
  moveAttributeOperations,
  operationById,
  operationsFor,
  type OperationTarget,
} from "@/features/model-editor/operations";
import type { CanvasSelection, EditorSelection } from "@/types";
import type { DraftOperation, ModelDraftOutline } from "@/types/modelAdmin";
import { type CanvasCard, type CanvasField, type CanvasLine, type Position } from "./canvasModel";

// --- zoom ---

export const ZOOM_MIN = 0.25;
export const ZOOM_MAX = 2;
const ZOOM_STEP = 0.1;
export const ZOOM_KEY = "rdm:workbook-canvas:zoom:v1";

const round = (value: number) => Math.round(value * 100) / 100;

export const clampZoom = (zoom: number) =>
  round(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Number.isFinite(zoom) ? zoom : 1)));

/** One step in or out, kept to whole percents so the readout stays plain. */
export const stepZoom = (zoom: number, direction: 1 | -1) => clampZoom(round(zoom + direction * ZOOM_STEP));

/** A wheel turn with Ctrl or Command: the zoom after it (a turn is a tenth of a step per 100 units). */
export const wheelZoom = (zoom: number, deltaY: number) => clampZoom(zoom * Math.exp(-deltaY * 0.0015));

/** The zoom at which the whole board fits its viewport; never above 100%, so a small model is not enlarged. */
export function fitZoom(
  extent: { width: number; height: number },
  viewport: { width: number; height: number },
): number {
  if (extent.width <= 0 || extent.height <= 0 || viewport.width <= 0 || viewport.height <= 0) return 1;
  return clampZoom(Math.floor(Math.min(1, viewport.width / extent.width, viewport.height / extent.height) * 100) / 100);
}

/** The scroll that keeps the point under the pointer where it is while the zoom changes. */
export function scrollAfterZoom(scroll: Position, pointer: Position, from: number, to: number): Position {
  return {
    x: Math.max(0, ((scroll.x + pointer.x) / from) * to - pointer.x),
    y: Math.max(0, ((scroll.y + pointer.y) / from) * to - pointer.y),
  };
}

/** The scroll that puts a box (in board coordinates) in the middle of the viewport. */
export function centredScroll(
  box: { x: number; y: number; width: number; height: number },
  zoom: number,
  viewport: { width: number; height: number },
): Position {
  return {
    x: Math.max(0, (box.x + box.width / 2) * zoom - viewport.width / 2),
    y: Math.max(0, (box.y + box.height / 2) * zoom - viewport.height / 2),
  };
}

// --- find ---

export interface FindHit {
  typeKey: string;
  /** The field's id on its card (`attribute:key`, `relation:type:far`), for a field hit. */
  fieldId?: string;
  label: string;
  /** Where it stands: the list a field belongs to, else the application. */
  hint: string;
}

const FIND_LIMIT = 12;

/** Lists and fields whose names contain the text, names starting with it first. */
export function findIn(outline: ModelDraftOutline, query: string): FindHit[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  const applicationOf = (typeKey: string) => {
    const type = outline.objectTypes.find((item) => item.key === typeKey);
    const key = type?.home ?? outline.applications.find((item) => item.objectTypeKeys.includes(typeKey))?.key;
    return outline.applications.find((item) => item.key === key)?.name ?? "";
  };
  const hits: { hit: FindHit; rank: number }[] = [];
  const consider = (hit: FindHit) => {
    const at = hit.label.toLowerCase().indexOf(needle);
    if (at >= 0) hits.push({ hit, rank: at === 0 ? 0 : 1 });
  };
  for (const type of outline.objectTypes) {
    consider({ typeKey: type.key, label: type.name, hint: applicationOf(type.key) });
    for (const attribute of type.attributes)
      consider({
        typeKey: type.key,
        fieldId: `attribute:${attribute.attributeType}`,
        label: attribute.name,
        hint: type.name,
      });
  }
  for (const relation of outline.relations) {
    if (relation.containment) continue;
    const name =
      outline.relationTypes.find((item) => item.key === relation.relationType)?.name ?? relation.relationType;
    consider({
      typeKey: relation.from,
      fieldId: `relation:${relation.relationType}:${relation.to}`,
      label: name,
      hint: outline.objectTypes.find((item) => item.key === relation.from)?.name ?? relation.from,
    });
  }
  return hits
    .sort((a, b) => a.rank - b.rank || a.hit.label.localeCompare(b.hit.label))
    .slice(0, FIND_LIMIT)
    .map((item) => item.hit);
}

// --- by hand: the operations the editor's table builds ---

/** A list renamed where it stands: the editor's Rename…, whose plural follows the name while it was the name's own. */
export function renameListOperations(
  card: Pick<CanvasCard, "typeKey" | "name">,
  name: string,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const rename = operationById("type-rename");
  const target: OperationTarget = { on: "objectType", objectType: card.typeKey };
  if (!rename) return [];
  const values = initialValues(rename, target, outline);
  const plural = typeof values.pluralName === "string" ? values.pluralName : "";
  const pluralName = !plural || plural === `${card.name}s` ? `${name.trim()}s` : plural;
  return rename.build({ ...values, name: name.trim(), pluralName }, target as never, outline);
}

/** A field renamed where it stands: the editor's Rename… of its attribute, or of its relationship's type. */
export function renameFieldOperations(
  card: Pick<CanvasCard, "typeKey">,
  field: CanvasField,
  name: string,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const target = targetOfField(card, field, outline);
  const on: OperationTarget | undefined =
    target.on === "attribute"
      ? target
      : target.on === "relation" && field.kind === "relation"
        ? { on: "relationType", relationType: target.relationType }
        : undefined;
  const rename = operationById(on?.on === "attribute" ? "attribute-rename" : "relation-type-rename");
  if (!on || !rename) return [];
  return rename.build({ ...initialValues(rename, on, outline), name: name.trim() }, on as never, outline);
}

/** An attribute row dropped on another object type's card: the editor's Move to… (a relationship row moves nowhere). */
export function moveAttributeDropOperations(
  card: Pick<CanvasCard, "typeKey">,
  field: CanvasField,
  toTypeKey: string,
): DraftOperation[] {
  if (field.kind !== "attribute" || !field.attributeTypeKey || card.typeKey === toTypeKey) return [];
  return moveAttributeOperations(field.attributeTypeKey, card.typeKey, toTypeKey);
}

/** An attribute row dropped beside another attribute row of its card: its new position among the attributes. */
export function reorderAttributeOperations(
  outline: ModelDraftOutline,
  typeKey: string,
  attributeType: string,
  besideAttributeType: string,
  after: boolean,
): DraftOperation[] {
  const attributes = outline.objectTypes.find((item) => item.key === typeKey)?.attributes ?? [];
  const from = attributes.findIndex((item) => item.attributeType === attributeType);
  const to = attributes.findIndex((item) => item.attributeType === besideAttributeType);
  if (from < 0 || to < 0 || from === to) return [];
  let position = to + (after ? 1 : 0);
  if (from < position) position -= 1;
  return position === from ? [] : attributePositionOperations(attributeType, typeKey, position);
}

/** Alt+ArrowUp / Alt+ArrowDown on an attribute row: the editor's Move up / Move down, when it offers one. */
export function stepAttributeOperations(
  card: Pick<CanvasCard, "typeKey">,
  field: CanvasField,
  direction: -1 | 1,
  outline: ModelDraftOutline,
): DraftOperation[] {
  const target = targetOfField(card, field, outline);
  const step = operationById(direction < 0 ? "attribute-up" : "attribute-down");
  if (target.on !== "attribute" || !step || !operationsFor(target, outline).includes(step)) return [];
  return step.build({}, target as never, outline);
}

// --- targets: what each thing on the board is to the operation table ---

/** The operation target of a field row: its attribute, its relationship, its containment, or the list itself. */
export function targetOfField(
  card: Pick<CanvasCard, "typeKey">,
  field: CanvasField,
  outline: ModelDraftOutline,
): OperationTarget {
  if (field.kind === "attribute" && field.attributeTypeKey)
    return { on: "attribute", objectType: card.typeKey, attributeType: field.attributeTypeKey };
  if (field.kind === "relation" && field.relationType && field.farType)
    return { on: "relation", relationType: field.relationType, from: card.typeKey, to: field.farType };
  if (field.kind === "parent" && field.farType) {
    const containment = outline.relations.find(
      (item) => item.containment && item.from === field.farType && item.to === card.typeKey,
    );
    if (containment)
      return { on: "relation", relationType: containment.relationType, from: containment.from, to: containment.to };
  }
  return { on: "objectType", objectType: card.typeKey };
}

/** The operation target of a line: its relationship; a containment line is the relationship that places the child. */
export function targetOfLine(line: CanvasLine, outline: ModelDraftOutline): OperationTarget | undefined {
  if (line.kind === "relates" && line.relationType)
    return { on: "relation", relationType: line.relationType, from: line.from, to: line.to };
  const containment = outline.relations.find(
    (item) => item.containment && item.from === line.from && item.to === line.to,
  );
  return containment
    ? { on: "relation", relationType: containment.relationType, from: containment.from, to: containment.to }
    : undefined;
}

/** The operation target of what the canvas has selected, where it is an element of the model. */
export function targetOfSelection(
  selection: CanvasSelection,
  cards: readonly CanvasCard[],
  lines: readonly CanvasLine[],
  outline: ModelDraftOutline,
): OperationTarget | undefined {
  if (selection.element === "type" && selection.key) return { on: "objectType", objectType: selection.key };
  if (selection.element === "application" && selection.key) return { on: "application", applicationKey: selection.key };
  if (selection.element === "group" && selection.application && selection.key)
    return { on: "group", applicationKey: selection.application, group: selection.key };
  if (selection.element === "field" && selection.key && selection.field) {
    const card = cards.find((item) => item.typeKey === selection.key);
    const field = card?.fields.find((item) => item.id === selection.field);
    return card && field ? targetOfField(card, field, outline) : undefined;
  }
  if (selection.element === "line" && selection.key) {
    const line = lines.find((item) => item.id === selection.key);
    return line ? targetOfLine(line, outline) : undefined;
  }
  return undefined;
}

/** What the editor's element panel shows for a canvas selection, where the editor has a panel for it. */
export function editorSelectionOf(
  selection: CanvasSelection,
  cards: readonly CanvasCard[],
  lines: readonly CanvasLine[],
  outline: ModelDraftOutline,
): EditorSelection {
  if (selection.element === "type" && selection.key) return { show: "type", key: selection.key };
  if (selection.element === "application" && selection.key) return { show: "application", key: selection.key };
  if (selection.element === "group" && selection.application && selection.key)
    return { show: "group", application: selection.application, key: selection.key };
  const target = targetOfSelection(selection, cards, lines, outline);
  if (target?.on === "attribute") return { show: "attributeType", key: target.attributeType };
  if (target?.on === "relation") return { show: "relationType", key: target.relationType };
  if (target?.on === "objectType") return { show: "type", key: target.objectType };
  return {};
}

// --- the selection ---

/** What is selected on the board, without the page's `show`: the part the address keeps. */
export type CanvasPick = Omit<CanvasSelection, "show">;

export function pickOf(selection: CanvasSelection | undefined): CanvasPick | undefined {
  if (!selection?.element) return undefined;
  const pick: CanvasPick = { element: selection.element };
  for (const name of ["key", "field", "application", "sheet", "block"] as const)
    if (selection[name] !== undefined) Object.assign(pick, { [name]: selection[name] });
  return pick;
}

export const selectionOfPick = (pick: CanvasPick | undefined): CanvasSelection => ({ show: "canvas", ...pick });

/** Whether a card is the selection or holds it (one of its fields). */
export const holdsSelection = (pick: CanvasPick | undefined, typeKey: string) =>
  (pick?.element === "type" || pick?.element === "field") && pick.key === typeKey;

// --- what the Add menu makes that has no card ---

/** The Add menu's entries whose result has no card: it is selected in the inspector instead. */
export type AddedKind = "add-attribute-type" | "add-relation-type" | "add-group";
export const isAddedKind = (id: string): id is AddedKind =>
  id === "add-attribute-type" || id === "add-relation-type" || id === "add-group";

/** The keys of what an Add entry makes, as the outline holds them (a group as `application \u0000 key`). */
export function addedKeys(id: AddedKind, outline: ModelDraftOutline): Set<string> {
  if (id === "add-attribute-type") return new Set(outline.attributeTypes.map((item) => item.key));
  if (id === "add-relation-type") return new Set(outline.relationTypes.map((item) => item.key));
  return new Set(
    outline.applications.flatMap((application) =>
      application.navigation.groups.map((group) => `${application.key}\u0000${group.key}`),
    ),
  );
}

export function addedName(id: AddedKind, made: string, outline: ModelDraftOutline): string {
  if (id === "add-attribute-type") return outline.attributeTypes.find((item) => item.key === made)?.name ?? made;
  if (id === "add-relation-type") return outline.relationTypes.find((item) => item.key === made)?.name ?? made;
  const [application, key] = made.split("\u0000");
  return (
    outline.applications.find((item) => item.key === application)?.navigation.groups.find((group) => group.key === key)
      ?.label ?? key
  );
}
