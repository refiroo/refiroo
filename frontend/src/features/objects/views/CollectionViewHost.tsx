/**
 * Dispatches a configured view to its renderer.
 */

import { viewComponentRegistry } from "./registry";
import type { ViewComponentProps } from "./types";
import { collectionGroups, viewSourceObjectTypeKey } from "@/model/collections";

export function CollectionView(props: ViewComponentProps) {
  const Component = viewComponentRegistry[props.view.type];
  const group = collectionGroups(props.application).find(
    (candidate) => candidate.objectTypeKey === viewSourceObjectTypeKey(props.view),
  );
  return (
    <>
      {group && group.views.length > 1 && (
        <nav className="collection-lenses" aria-label="Collection lenses">
          <span>Lens</span>
          {group.views.map((view) => (
            <button
              key={view.key}
              aria-current={view.key === props.view.key ? "page" : undefined}
              onClick={() => props.onViewChange?.(view.key)}
            >
              {view.name}
            </button>
          ))}
        </nav>
      )}
      <Component {...props} />
    </>
  );
}
