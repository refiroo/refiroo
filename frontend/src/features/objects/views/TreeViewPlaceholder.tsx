/**
 * Stands in for the `tree` view type until its renderer lands (Base 0.8 B3), so a schema 0.7 model
 * that declares one opens as a lens with its heading instead of failing. Every label comes from the
 * model.
 */

import type { ViewComponentProps } from "./types";
import { objectTypeFor } from "@/model/lookup";
import { Icon } from "@/ui/Icon";

export function TreeViewPlaceholder({ model, view, lenses }: ViewComponentProps) {
  if (view.type !== "tree") return null;
  const names = view.config.objectTypeKeys.map((key) => (objectTypeFor(model, key)?.pluralName ?? key).toLowerCase());
  const listed = names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names[0];
  return (
    <div>
      <header className="page-header collection-header">
        <div className="page-title">
          <span className="page-icon" aria-hidden="true">
            <Icon name="tree" size={20} />
          </span>
          <div>
            <h1 tabIndex={-1}>{view.name}</h1>
          </div>
        </div>
      </header>
      {lenses}
      <div className="empty-state">
        <p>A tree of {listed} is not available yet.</p>
      </div>
    </div>
  );
}
