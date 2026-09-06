import { ObjectCollectionView } from "../CollectionView";
import type { ViewComponentProps } from "./types";
import type { ViewDefinition } from "@/types";

/**
 * View type key to the component that renders it.
 *
 * Schema 0.5 admits only the implemented table contract. New discriminated branches belong here
 * only when the model schema and an honest renderer ship together.
 */
export const viewComponentRegistry: Record<ViewDefinition["type"], React.ComponentType<ViewComponentProps>> = {
  table: ObjectCollectionView,
};
