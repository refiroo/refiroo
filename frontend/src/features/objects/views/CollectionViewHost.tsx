/**
 * Dispatches a configured view to its renderer. Views that share a source object type are lenses
 * of one collection; the host builds the lens switch and the renderer places it under its heading.
 */

import { viewComponentRegistry } from "./registry";
import type { ViewComponentProps } from "./types";
import { collectionGroups, viewSourceObjectTypeKey } from "@/model/collections";
import type { ViewDefinition } from "@/types";
import { Icon, type IconName } from "@/ui/Icon";

const lensIcons: Record<ViewDefinition["type"], IconName> = {
  table: "table",
  mappingGrid: "mapping",
  relationMatrix: "matrix",
  relationTable: "link",
  tree: "tree",
};

export function CollectionView(props: ViewComponentProps) {
  const Component = viewComponentRegistry[props.view.type];
  const group = collectionGroups(props.application).find(
    (candidate) => candidate.objectTypeKey === viewSourceObjectTypeKey(props.view),
  );
  const lenses =
    group && group.views.length > 1 ? (
      <nav className="collection-lenses" aria-label="Collection lenses">
        {group.views.map((view) => (
          <button
            key={view.key}
            aria-current={view.key === props.view.key ? "page" : undefined}
            onClick={() => props.onViewChange?.(view.key)}
          >
            <Icon name={lensIcons[view.type]} size={15} />
            {view.name}
          </button>
        ))}
      </nav>
    ) : undefined;
  return <Component {...props} lenses={lenses} />;
}
