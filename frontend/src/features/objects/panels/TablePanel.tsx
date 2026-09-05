/**
 * A table of one configured object type, optionally filtered to the object being viewed.
 */

import type { TablePanelDefinition } from "@/types";
import { CollectionPanelTable } from "./CollectionPanelTable";
import type { PanelProps } from "./types";

export function TablePanel(props: PanelProps) {
  const panel = props.panel as TablePanelDefinition;
  return (
    <CollectionPanelTable
      {...props}
      objectTypeKey={panel.config.objectTypeKey}
      columns={panel.config.columns}
      pageSize={panel.config.pageSize}
      parentObjectId={panel.config.filterByParent ? props.object.id : undefined}
      allowCreate={panel.config.filterByParent}
    />
  );
}
