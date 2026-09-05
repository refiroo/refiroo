import { ObjectCollectionView } from "../CollectionView";
import type { ViewComponentProps } from "./types";
import type { ViewDefinition } from "@/types";

/**
 * View type key to the component that renders it.
 *
 * Every declared view type currently resolves to the same collection renderer, so a model
 * declaring `tree` or `mappingGrid` is shown a flat table under that label. Base 0.6 decision D3
 * governs how declared-but-unimplemented view types are represented; this registry is the single
 * seam where that decision is expressed. See Phase 6 of docs/FRONTEND_STRUCTURE_REFACTOR.md.
 */
export const viewComponentRegistry: Record<ViewDefinition["type"], React.ComponentType<ViewComponentProps>> = {
  table: ObjectCollectionView,
  tree: ObjectCollectionView,
  mappingGrid: ObjectCollectionView,
  form: ObjectCollectionView,
  dashboard: ObjectCollectionView,
};
