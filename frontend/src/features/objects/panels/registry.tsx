/**
 * Panel type key to the component that renders it.
 *
 * A model declares which panels a detail view shows; this is the only place that maps a declared
 * type onto a component, so adding a panel type is one entry here plus its component.
 */

import type { AttributesPanelDefinition, PanelDefinition, RelationsPanelDefinition } from "@/types";
import { AttributesPanel } from "./AttributesPanel";
import { ChildrenPanel } from "./ChildrenPanel";
import { HierarchyPanel } from "./HierarchyPanel";
import { RelationsPanel } from "./RelationsPanel";
import { TablePanel } from "./TablePanel";
import type { PanelProps } from "./types";

/**
 * `PanelDefinition` is a discriminated union on
 * `type`, so keying the registry by that discriminant hands every entry its own narrowed panel
 * definition and removes the per-entry cast this registry used to carry.
 */
type PanelComponentRegistry = {
  [K in PanelDefinition["type"]]: React.ComponentType<PanelProps<Extract<PanelDefinition, { type: K }>>>;
};
function AttributesPanelSection(props: PanelProps<AttributesPanelDefinition>) {
  return (
    <AttributesPanel
      model={props.model}
      object={props.object}
      panel={props.panel}
      onObjectChanged={props.onObjectChanged}
      onReload={props.onReload}
      onChanged={props.onChanged}
    />
  );
}

function RelationsPanelSection(props: PanelProps<RelationsPanelDefinition>) {
  return (
    <RelationsPanel
      model={props.model}
      object={props.object}
      panel={props.panel}
      onOpen={props.onOpen}
      onChanged={props.onChanged}
    />
  );
}

export const panelComponentRegistry: PanelComponentRegistry = {
  attributes: AttributesPanelSection,
  children: ChildrenPanel,
  relations: RelationsPanelSection,
  table: TablePanel,
  hierarchy: HierarchyPanel,
};
