/**
 * Lists the objects contained by the object being viewed, one table per configured child type.
 */

import type { ChildrenPanelDefinition } from "@/types";
import { CollectionPanelTable } from "./CollectionPanelTable";
import type { PanelProps } from "./types";

export function ChildrenPanel(props: PanelProps) {
  const panel = props.panel as ChildrenPanelDefinition;
  return (
    <div className="panel-tables">
      {panel.config.objectTypeKeys.map((key) => (
        <CollectionPanelTable
          key={key}
          {...props}
          objectTypeKey={key}
          columns={panel.config.columns}
          pageSize={panel.config.pageSize}
          parentObjectId={props.object.id}
          allowCreate
        />
      ))}
    </div>
  );
}
