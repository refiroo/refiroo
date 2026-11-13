import { useState } from "react";
import { VIEW_KINDS } from "@/model/outline";
import { navigationEntryKey, navigationSections, viewGlyph } from "@/model/collections";
import { objectTypeHue } from "@/model/hues";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel } from "@/types";
import { Card } from "@/ui/Card";
import { EmptyState } from "@/ui/EmptyState";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { PageHeader } from "@/ui/PageHeader";
import { SearchField } from "@/ui/SearchField";

/**
 * A navigation group's page (0.10 N1, D25): the collections and views the group names,
 * with a search over their names done here, since they are model data. A collection opens on the
 * view it opens on, a view on itself; the caller keeps the data context. No record counts (A-D12).
 */
export function NavigationGroupPage({
  model,
  application,
  groupKey,
  onOpenCollection,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  groupKey: string;
  onOpenCollection: (viewKey: string) => void;
}) {
  const [search, setSearch] = useState("");
  const section = navigationSections(application).groups.find((item) => item.group.key === groupKey);
  if (!section) return null;
  const entries = section.entries.map((entry) => {
    if (entry.kind === "view") {
      const type = objectTypeFor(model, entry.sourceObjectTypeKey);
      return {
        key: navigationEntryKey(entry),
        name: entry.view.name,
        tile: <HueTile hue={objectTypeHue(model, entry.sourceObjectTypeKey)} glyph={viewGlyph(entry.view)} />,
        description: `${VIEW_KINDS[entry.view.type] ?? entry.view.type} of ${type?.pluralName ?? entry.sourceObjectTypeKey}`,
        lenses: undefined,
        viewKey: entry.view.key,
      };
    }
    const { collection } = entry;
    const type = objectTypeFor(model, collection.objectTypeKey);
    return {
      key: navigationEntryKey(entry),
      name: type?.pluralName ?? collection.objectTypeKey,
      tile: <HueTile hue={objectTypeHue(model, collection.objectTypeKey)} icon={type?.icon} />,
      description: type?.description,
      lenses: collection.views.length > 1 ? collection.views.map((view) => view.name).join(" · ") : undefined,
      viewKey: collection.defaultView.key,
    };
  });
  const views = section.entries.filter((entry) => entry.kind === "view").length;
  const collections = entries.length - views;
  const counted = [
    `${collections} ${collections === 1 ? "collection" : "collections"}`,
    ...(views ? [`${views} ${views === 1 ? "view" : "views"}`] : []),
  ].join(" and ");
  const term = search.trim().toLocaleLowerCase();
  const shown = term ? entries.filter((entry) => entry.name.toLocaleLowerCase().includes(term)) : entries;

  return (
    <section className="navigation-group-page" aria-labelledby="navigation-group-title">
      <PageHeader
        titleId="navigation-group-title"
        eyebrow={application.name}
        title={section.group.label}
        description={counted}
      />
      <Card flush className="panel">
        {entries.length > 0 && (
          <div className="collection-toolbar">
            <SearchField
              value={search}
              onChange={setSearch}
              label={`Search ${section.group.label}`}
              placeholder="Find a collection or view"
              clearOnEscape
            />
          </div>
        )}
        {entries.length === 0 ? (
          <EmptyState>This group has no collections or views.</EmptyState>
        ) : shown.length === 0 ? (
          <EmptyState>No collection or view in this group matches “{search.trim()}”.</EmptyState>
        ) : (
          <ul className="group-collections" aria-label={`${section.group.label} collections`}>
            {shown.map((entry) => (
              <li key={entry.key}>
                <button type="button" onClick={() => onOpenCollection(entry.viewKey)}>
                  {entry.tile}
                  <span className="group-collection-text">
                    <span className="group-collection-name">{entry.name}</span>
                    {entry.description && <span className="group-collection-description">{entry.description}</span>}
                  </span>
                  {entry.lenses && <span className="group-collection-lenses">{entry.lenses}</span>}
                  <span className="group-collection-open" aria-hidden="true">
                    <Icon name="chevron-right" size={16} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </section>
  );
}
