/**
 * Where a type's records are kept and where else it is listed (the type page's line under its title).
 * An application lists a type because it holds its records (the type is its own there) or because one
 * of its relation views needs it (it is borrowed). The server tells which (`home`, `ownIn`,
 * `borrowedIn` of the outline's type); the page says where the type is maintained, and for each
 * application that borrows it which view uses it and how.
 */

import type { EditorSelection, ModelDraftOutline, OutlineObjectType, OutlineUse } from "@/types";
import { StatusPill } from "@/ui/StatusPill";
import { VIEW_KINDS, applicationOf, placeOf } from "@/model/outline";

const ROLE_WORDS: Record<OutlineUse["role"], string> = {
  rows: "rows",
  columns: "columns",
  cells: "cells",
  from: "from end",
  to: "to end",
  link: "link between its columns and cells",
};

export function TypePlacement({
  outline,
  type,
  onSelect,
}: {
  outline: ModelDraftOutline;
  type: OutlineObjectType;
  onSelect: (selection: EditorSelection) => void;
}) {
  const home = type.home ? applicationOf(outline, type.home) : undefined;
  const alsoOwn = (type.ownIn ?? []).filter((key) => key !== type.home);
  const listedIn = outline.applications.filter((item) => item.objectTypeKeys.includes(type.key));
  return (
    <div className="element-place">
      <p>
        {home && (
          <StatusPill tone="neutral" marker={false} className="element-home">
            Maintained in {home.name}
          </StatusPill>
        )}{" "}
        {placeOf(outline, type)}
        {!home && (listedIn.length ? ` · in ${listedIn.map((item) => item.name).join(", ")}` : " · in no application")}
      </p>
      {alsoOwn.length > 0 && (
        <p className="element-uses-line">
          Also maintained in {alsoOwn.map((key) => applicationOf(outline, key)?.name ?? key).join(", ")}
        </p>
      )}
      {(type.borrowedIn ?? []).map(({ application: key, uses }) => {
        const application = applicationOf(outline, key);
        if (!application) return null;
        const group = application.navigation.groups.find((item) =>
          item.entries.some((entry) => entry.collection === type.key),
        );
        return uses.map((use) => {
          // A view has no page of its own: the link opens the group the type stands in, or the application.
          const target: EditorSelection = group
            ? { show: "group", application: key, key: group.key }
            : { show: "application", key };
          return (
            <p key={`${key}:${use.view}:${use.role}`} className="element-uses-line">
              <span className="element-uses-label">Also in</span> <strong>{application.name}</strong> —{" "}
              {(VIEW_KINDS[use.viewType] ?? use.viewType).toLowerCase()}{" "}
              <button type="button" className="link-button" onClick={() => onSelect(target)}>
                {use.viewName}
              </button>
              , {ROLE_WORDS[use.role]}
              {use.relationName ? ` · relation ${use.relationName}` : ""}
              {group ? ` · group ${group.label}` : ""}
            </p>
          );
        });
      })}
    </div>
  );
}
