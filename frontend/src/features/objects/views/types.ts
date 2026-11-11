/**
 * The props every collection view receives. The view definition carries whatever configuration the
 * renderer needs, so adding a view type does not widen this contract.
 */

import type { MutableRefObject, ReactNode } from "react";
import type { ExportStart } from "@/features/jobs/ExportDialog";
import type { ExportViewExtra } from "./useViewExport";
import type { ApplicationDefinition, CollectionQueryState, EngineModel, ObjectItem, ViewDefinition } from "@/types";

export interface ViewComponentProps {
  model: EngineModel;
  application: ApplicationDefinition;
  view: ViewDefinition;
  workspaceKey: string;
  readOnly?: boolean;
  onChanged?: () => void;
  refreshToken?: number;
  selectedId?: string;
  /** The type of the record `selectedId` names, so a lens can read it without searching. */
  selectedObjectTypeKey?: string;
  query: CollectionQueryState;
  onQueryChange: (query: CollectionQueryState) => void;
  /** Records the scroll anchor in the route without a history entry or a reload. */
  onAnchorChange?: (anchor: string | undefined) => void;
  onViewChange?: (viewKey: string) => void;
  /**
   * Shows a change set's AI-proposed mappings (0.16 AP2): the grid in that change set with the
   * Proposed filter on, as the route.
   */
  onShowProposed?: (changeSetId: string) => void;
  /** Opens the open change set's review, for a lens that wrote several records at once (C4). */
  onReviewChanges?: () => void;
  /**
   * Hands up how to read what the page would export (0.9 J1u, D57), for the workspace ⋯ menu's
   * Export (0.16 WM1); called with nothing when the page goes.
   */
  onExportContext?: (read: (() => ExportStart) | undefined) => void;
  /** Where a view hands the part of its Export state only it knows (a table's columns, EX1). */
  exportExtraRef?: MutableRefObject<ExportViewExtra | undefined>;
  /**
   * Lets records be selected for a bulk change (0.9 K1); given only where the data can be written
   * while the deployment lets jobs be created (D105). `maxItems` is the most one bulk change may
   * hold (`backgroundJobMaxItems`, D104).
   */
  bulkSelection?: { maxItems: number };
  /**
   * In live data the person cannot change but can propose changes to (0.12 Z5, D324): the way to
   * propose a new record of a type, or a change to one, through their own change set, if any.
   */
  onPropose?: (applicationKey: string, objectTypeKey: string) => ((objectId?: string) => void) | undefined;
  /** One-shot: open the create form on arrival (a proposed new record, D324); changes per request. */
  createRequest?: number;
  /** Sibling lenses of the same source collection, placed by the renderer below its heading. */
  lenses?: ReactNode;
  /**
   * The view is its page's whole content, fitted to the window, and only its rows scroll (0.12 LS1,
   * D371); a view that has no such layout ignores it.
   */
  fill?: boolean;
  /**
   * Opens a record; a lens that holds only a record's identity passes just that. `beside` keeps the
   * lens on screen with the record in the inspector beside it, where the viewport is wide enough.
   */
  onOpen: (
    item: Pick<ObjectItem, "id" | "objectTypeKey" | "applicationKey" | "workspaceKey">,
    action?: "edit" | "delete",
    options?: { beside?: boolean },
  ) => void;
}
