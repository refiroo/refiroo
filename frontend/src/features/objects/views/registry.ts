import { ObjectCollectionView } from "../CollectionView";
import { MappingGridPlaceholder } from "../MappingGridPlaceholder";
import type { ViewComponentProps } from "./types";
import type { ViewDefinition } from "@/types";

/**
 * View type key to the component that renders it.
 *
 * Schema 0.6 adds the mappingGrid contract. The full renderer ships in WP-8; the placeholder
 * satisfies the type and renders a stub until then.
 */
export const viewComponentRegistry: Record<ViewDefinition["type"], React.ComponentType<ViewComponentProps>> = {
  table: ObjectCollectionView,
  mappingGrid: MappingGridPlaceholder,
};
