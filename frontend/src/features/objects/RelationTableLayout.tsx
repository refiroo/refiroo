/**
 * A relationships table in the layout its view declares (0.13 RG): one row per relationship (the
 * default) or the grid, each record once with a column group per related record.
 */

import type { RelationTableViewDefinition } from "@/types";
import { RelationGridView } from "./RelationGridView";
import { RelationTableView } from "./RelationTableView";
import type { ViewComponentProps } from "./views/types";

export function RelationTableLayout(props: ViewComponentProps) {
  const view = props.view as RelationTableViewDefinition;
  return view.config.layout === "grid" ? <RelationGridView {...props} /> : <RelationTableView {...props} />;
}
