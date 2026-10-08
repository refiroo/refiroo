/**
 * The props every collection view receives. The view definition carries whatever configuration the
 * renderer needs, so adding a view type does not widen this contract.
 */

import type { ReactNode } from "react";
import type { ExportStart } from "@/features/jobs/ExportDialog";
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
  /** Opens the open change set's review, for a lens that wrote several records at once (C4). */
  onReviewChanges?: () => void;
  /**
   * Offers Export with what the page shows (0.9 J1u, D57); given only while the deployment lets
   * jobs be created. A view without it offers no export.
   */
  onExport?: (start: ExportStart) => void;
  /**
   * Offers Import into the data the page shows (0.9 J4, D89); given only where that data can be
   * written while the deployment lets jobs be created. A view without it offers no import.
   */
  onImport?: () => void;
  /**
   * Lets records be selected for a bulk change (0.9 K1); given only where the data can be written
   * while the deployment lets jobs be created (D105). `maxItems` is the most one bulk change may
   * hold (`backgroundJobMaxItems`, D104).
   */
  bulkSelection?: { maxItems: number };
  /** Sibling lenses of the same source collection, placed by the renderer below its heading. */
  lenses?: ReactNode;
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
