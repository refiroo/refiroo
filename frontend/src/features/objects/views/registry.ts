import { ObjectCollectionView } from "../CollectionView";
import { MappingGridView } from "../MappingGridView";
import { RelationMatrixView } from "../RelationMatrixView";
import { RelationTableLayout } from "../RelationTableLayout";
import { TreeView } from "../TreeView";
import type { ViewComponentProps } from "./types";
import type { ViewDefinition } from "@/types";

export const viewComponentRegistry: Record<ViewDefinition["type"], React.ComponentType<ViewComponentProps>> = {
  table: ObjectCollectionView,
  mappingGrid: MappingGridView,
  relationMatrix: RelationMatrixView,
  relationTable: RelationTableLayout,
  tree: TreeView,
};
