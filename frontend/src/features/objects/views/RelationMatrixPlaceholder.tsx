/**
 * Stands in for the `relationMatrix` view type until its renderer lands (Base 0.8 A4), so a schema
 * 0.7 model that declares one opens as a lens with its heading instead of failing. Every label comes
 * from the model.
 */

import type { ViewComponentProps } from "./types";
import { objectTypeFor } from "@/model/lookup";
import { Icon } from "@/ui/Icon";

export function RelationMatrixPlaceholder({ model, view, lenses }: ViewComponentProps) {
  if (view.type !== "relationMatrix") return null;
  const { rowObjectTypeKey, columnObjectTypeKey, cellObjectTypeKey } = view.config;
  const rows = objectTypeFor(model, rowObjectTypeKey)?.pluralName ?? rowObjectTypeKey;
  const columns = objectTypeFor(model, columnObjectTypeKey)?.name ?? columnObjectTypeKey;
  const cells = objectTypeFor(model, cellObjectTypeKey)?.pluralName ?? cellObjectTypeKey;
  return (
    <div>
      <header className="page-header collection-header">
        <div className="page-title">
          <span className="page-icon" aria-hidden="true">
            <Icon name="matrix" size={20} />
          </span>
          <div>
            <h1 tabIndex={-1}>{view.name}</h1>
          </div>
        </div>
      </header>
      {lenses}
      <div className="empty-state">
        <p>
          A matrix of {rows.toLowerCase()} by {columns.toLowerCase()}, showing their {cells.toLowerCase()}, is not
          available yet.
        </p>
      </div>
    </div>
  );
}
