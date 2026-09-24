/**
 * The containment path from the root object down to the object being viewed.
 */

import { objectTypeFor } from "@/model/lookup";
import type { HierarchyPanelDefinition } from "@/types";
import type { PanelProps } from "./types";

export function HierarchyPanel({ model, object, panel, onOpen }: PanelProps) {
  const definition = panel as HierarchyPanelDefinition;
  const visiblePath = definition.config.showAncestors ? object.path : object.path.slice(-1);
  const parent = object.path.at(-2);
  return (
    <div className="hierarchy-panel">
      {definition.config.showParent && (
        <div>
          <span>Parent</span>
          {parent ? (
            <button onClick={() => onOpen(parent.objectTypeKey, parent.id)}>{parent.name}</button>
          ) : (
            <strong>Root object</strong>
          )}
        </div>
      )}
      {object.path.length <= 1 && !definition.config.showParent ? (
        <p className="hierarchy-note">Top-level record with no parent.</p>
      ) : (
        <ol>
          {visiblePath.map((part, index) => (
            <li key={part.id}>
              {part.id === object.id ? (
                <strong aria-current="location">{part.name}</strong>
              ) : (
                <button onClick={() => onOpen(part.objectTypeKey, part.id)}>{part.name}</button>
              )}
              <small>{objectTypeFor(model, part.objectTypeKey)?.name}</small>
              {index < visiblePath.length - 1 && <span>›</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
