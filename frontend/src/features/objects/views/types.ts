/**
 * The props every collection view receives. The view definition carries whatever configuration the
 * renderer needs, so adding a view type does not widen this contract.
 */

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
  query: CollectionQueryState;
  onQueryChange: (query: CollectionQueryState) => void;
  onViewChange?: (viewKey: string) => void;
  onOpen: (item: ObjectItem, action?: "edit" | "delete") => void;
}
