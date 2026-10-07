/**
 * A searchable, sortable, continuously scrolling table of objects embedded inside a detail panel.
 *
 * Shared by the children and table panels, which differ only in how they choose the object type
 * and whether rows are filtered to the object being viewed.
 */

import { useState } from "react";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { attributeName, listSortFields } from "@/model/fields";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeFor } from "@/model/lookup";
import type { ObjectItem } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
import { ObjectTable } from "@/ui/ObjectTable";
import { SortMenu, useTableSort } from "@/ui/TableSort";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { Icon } from "@/ui/Icon";
import type { PanelProps } from "./types";

export function CollectionPanelTable({
  model,
  application,
  object,
  objectTypeKey,
  columns,
  pageSize,
  parentObjectId,
  allowCreate,
  onOpen,
  onChanged,
  readOnly,
}: PanelProps & {
  objectTypeKey: string;
  columns: string[];
  pageSize: number;
  parentObjectId?: string;
  allowCreate: boolean;
}) {
  const api = useDataApi();
  const { changeSet, publication } = useWorkspaceData();
  const display = useTableDisplay(columns, `${application.key}:${object.id}:${objectTypeKey}`);
  const [selectedPageSize, setPageSize] = useState(pageSize);
  const objectType = objectTypeFor(model, objectTypeKey);
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [creating, setCreating] = useState(false);
  // Panels list by name, as every list does without a sort, until the user sorts by another column.
  const [sort, setSort] = useState("name");
  const sortFields = objectType ? listSortFields(model, [objectType], columns, [], !changeSet && !publication) : [];
  const pages = useCursorWindow<ObjectItem>(
    objectType
      ? (selector) =>
          api.objects(objectTypeKey, {
            applicationKey: application.key,
            workspaceKey: object.workspaceKey,
            search,
            sort,
            ...selector,
            pageSize: selectedPageSize,
            parentObjectId,
          })
      : null,
    [application.key, object.workspaceKey, objectTypeKey, selectedPageSize, parentObjectId, search, sort],
  );
  const { error } = pages;
  const sorting = useTableSort({
    sort,
    fields: sortFields,
    onSort: setSort,
    labelFor: (field) => attributeName(model, field),
  });

  function refresh() {
    pages.reload();
    onChanged();
  }

  // A release can retire an object type that a configured panel still names. Reporting that is
  // better than the non-null assertion this used to carry, which crashed the whole detail screen.
  if (!objectType)
    return (
      <div className="panel-state">This panel refers to object type “{objectTypeKey}”, which is not in the model.</div>
    );

  return (
    <div className="embedded-table">
      <div className="embedded-toolbar">
        <label className="search-box compact">
          <Icon name="search" />
          <input
            aria-label={`Search ${objectType.pluralName.toLowerCase()}`}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={`Search ${objectType.pluralName.toLowerCase()}`}
          />
        </label>
        <TableDisplay
          model={model}
          columns={columns}
          display={display}
          pageSize={selectedPageSize}
          defaultPageSize={pageSize}
          onPageSize={setPageSize}
        />
        <SortMenu sorting={sorting} />
        {allowCreate && !readOnly && (
          <button className="secondary" onClick={() => setCreating(true)}>
            <Icon name="plus" /> Add {objectType.name}
          </button>
        )}
      </div>
      {error && <InlineError message={error} onRetry={pages.retry} />}
      {(!error || pages.items.length > 0) && (
        <ObjectTable
          model={model}
          columns={display.columns}
          compact={display.compact}
          columnWidths={display.widths}
          onColumnWidths={display.setWidths}
          identityColumn={display.identity}
          sorting={sorting}
          list={pages}
          pageSize={selectedPageSize}
          label={`${objectType.pluralName} of ${object.name}`}
          onOpen={(item) => onOpen(item.objectTypeKey, item.id, item.applicationKey)}
          renderActions={(item, menu) => (
            <RecordActionMenu
              object={item}
              readOnly={readOnly}
              onEdit={() => onOpen(item.objectTypeKey, item.id, item.applicationKey, "edit")}
              onDelete={() => onOpen(item.objectTypeKey, item.id, item.applicationKey, "delete")}
              {...menu}
            />
          )}
        />
      )}
      {creating && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={object.workspaceKey}
          objectType={objectType}
          parentObjectId={parentObjectId}
          parentObjectTypeKey={parentObjectId ? object.objectTypeKey : undefined}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}
