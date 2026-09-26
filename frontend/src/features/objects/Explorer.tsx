import { useState } from "react";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeFor } from "@/model/lookup";
import { collectionGroups } from "@/model/collections";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
import { RecordTree } from "@/features/objects/RecordTree";

export function Explorer({
  model,
  application,
  workspaceKey,
  activeObjectId,
  activeObjectTypeKey,
  activeViewKey,
  refreshToken,
  onOpen,
  onOpenCollection,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  activeObjectId?: string;
  activeObjectTypeKey?: string;
  activeViewKey?: string;
  refreshToken: number;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
}) {
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const groups = collectionGroups(application);

  return (
    <section className="explorer" aria-label={`${application.name} explorer`}>
      {groups.length > 0 && (
        <nav className="collection-tree" aria-label={`${application.name} collections`}>
          <p className="nav-label">Collections</p>
          {groups.map((group) => {
            const type = objectTypeFor(model, group.objectTypeKey);
            const active = group.views.some((view) => view.key === activeViewKey);
            return (
              <button
                key={group.objectTypeKey}
                className={active ? "active" : ""}
                aria-current={active ? "page" : undefined}
                onClick={() => onOpenCollection?.(group.defaultView.key)}
              >
                <ModelIcon name={type?.icon} />
                <span>{type?.pluralName ?? group.objectTypeKey}</span>
                {group.views.some((view) => view.type === "mappingGrid") && (
                  <span className="collection-hint" title="Includes a mapping view">
                    <Icon name="mapping" size={13} label="Includes a mapping view" />
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      )}
      <div className="browse-section">
        <p className="nav-label" id={`${application.key}-browse-label`}>
          Browse records
        </p>
        <label className="search-box compact">
          <Icon name="search" />
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            aria-label="Search this explorer"
            placeholder="Find a record"
          />
        </label>
        <RecordTree
          model={model}
          application={application}
          workspaceKey={workspaceKey}
          search={search}
          activeObjectId={activeObjectId}
          activeObjectTypeKey={activeObjectTypeKey}
          refreshToken={refreshToken}
          labelledBy={`${application.key}-browse-label`}
          onOpen={onOpen}
          onOpenCollection={onOpenCollection}
        />
      </div>
    </section>
  );
}
