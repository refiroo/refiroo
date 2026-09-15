import { ObjectCollectionView } from "../CollectionView";
import { MappingGridView } from "../MappingGridView";
import type { ViewComponentProps } from "./types";
import type { ViewDefinition } from "@/types";

export const viewComponentRegistry: Record<ViewDefinition["type"], React.ComponentType<ViewComponentProps>> = {
  table: ObjectCollectionView,
  mappingGrid: MappingGridView,
};
