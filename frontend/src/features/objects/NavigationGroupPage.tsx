import { useState } from "react";
import { navigationSections } from "@/model/collections";
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
 * A navigation group's page (0.10 N1, D25): the collections the group names, with a search over
 * their names done here, since they are model data. Each entry opens its collection's default lens;
 * the caller keeps the data context. No record counts (A-D12).
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
  const entries = section.collections.map((collection) => {
    const type = objectTypeFor(model, collection.objectTypeKey);
    return { collection, type, name: type?.pluralName ?? collection.objectTypeKey };
  });
  const term = search.trim().toLocaleLowerCase();
  const shown = term ? entries.filter((entry) => entry.name.toLocaleLowerCase().includes(term)) : entries;

  return (
    <section className="navigation-group-page" aria-labelledby="navigation-group-title">
      <PageHeader
        titleId="navigation-group-title"
        eyebrow={application.name}
        title={section.group.label}
        description={`${entries.length} ${entries.length === 1 ? "collection" : "collections"}`}
      />
      <Card flush className="panel">
        {entries.length > 0 && (
          <div className="collection-toolbar">
            <SearchField
              value={search}
              onChange={setSearch}
              label={`Search ${section.group.label}`}
              placeholder="Find a collection"
              clearOnEscape
            />
          </div>
        )}
        {entries.length === 0 ? (
          <EmptyState>This group has no collections.</EmptyState>
        ) : shown.length === 0 ? (
          <EmptyState>No collection in this group matches “{search.trim()}”.</EmptyState>
        ) : (
          <ul className="group-collections" aria-label={`${section.group.label} collections`}>
            {shown.map(({ collection, type, name }) => (
              <li key={collection.objectTypeKey}>
                <button type="button" onClick={() => onOpenCollection(collection.defaultView.key)}>
                  <HueTile hue={objectTypeHue(model, collection.objectTypeKey)} icon={type?.icon} />
                  <span className="group-collection-text">
                    <span className="group-collection-name">{name}</span>
                    {type?.description && <span className="group-collection-description">{type.description}</span>}
                  </span>
                  {collection.views.length > 1 && (
                    <span className="group-collection-lenses">
                      {collection.views.map((view) => view.name).join(" · ")}
                    </span>
                  )}
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
