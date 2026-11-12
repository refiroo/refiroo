/**
 * Where on the canvas each kind of operation target is operated (0.17 CE1, PP-D3, PP-D89). The canvas has no
 * operations of its own: every element on it, or panel in it, shows the editor's `OperationsMenu` (or the
 * editor's panel, which holds that menu) for the element's `OperationTarget`, so an operation of the table is
 * reachable on the canvas when its kind of target has a surface here. `parity.test.ts` fails when the table gains
 * an operation of a kind that has none; `CanvasEditor.test.tsx` finds each surface on the page.
 */

import type { OperationTarget } from "@/features/model-editor/operations";

export interface CanvasSurface {
  /** The place on the canvas, in words. */
  where: string;
  /** The accessible name the surface's menu or panel starts with. */
  label: string;
}

export const CANVAS_SURFACES: Record<OperationTarget["on"], CanvasSurface> = {
  draft: { where: "the header's Add to the model menu", label: "Add to the model" },
  application: { where: "the ⋯ menu on an application's frame", label: "Operations for the application" },
  objectType: { where: "the ⋯ menu on an object type's card", label: "Actions for" },
  attribute: { where: "the ⋯ menu on a selected attribute row", label: "Operations for the attribute" },
  relation: { where: "the ⋯ in a line's rule popover, and a relationship row's menu", label: "Operations for" },
  attributeType: { where: "the inspector's attribute type panel, under a selected attribute", label: "Operations for" },
  relationType: { where: "the inspector's relationship type panel, for a selected line", label: "Operations for" },
  view: { where: "the Views tab, a view's ⋯ menu", label: "Operations for the view" },
  group: { where: "the Navigation tab, a group's ⋯ menu", label: "Operations for the group" },
  groupEntry: { where: "the Navigation tab, an entry's ⋯ menu", label: "Operations for the entry" },
  consumerApis: { where: "the Consumer APIs tab's ＋", label: "Add a consumer API" },
  consumerApi: { where: "the Consumer APIs tab, a consumer API's panel", label: "Operations for" },
  consumerItem: { where: "the Consumer APIs tab, a member of a definition", label: "Operations for" },
};
