/**
 * A searchable, sortable, continuously scrolling table of objects embedded inside a detail panel.
 *
 * Shared by the children and table panels, which differ only in how they choose the object type
 * and whether rows are filtered to the object being viewed.
 */

import { useState } from "react";
import { RecordActionMenu } from "@/features/objects/RecordActionMenu";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { attributeName, listSortFields, RELATED_EXPAND_LIMIT, relatedKeys } from "@/model/fields";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeFor } from "@/model/lookup";
import type { ObjectItem } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
import { useCellEditing } from "@/features/objects/useCellEditing";
import { ObjectTable } from "@/ui/ObjectTable";
import { SortMenu, useTableSort } from "@/ui/TableSort";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { Icon } from "@/ui/Icon";
import { SearchField } from "@/ui/SearchField";
import { PanelTools, panelFolds } from "./PanelTools";
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
  // A record of this type is added where the person may write it (0.12 Z5, D329).
  const writes = useRecordWrites();
  const creatable = !readOnly && writes.permits(application.key, objectTypeKey);
  const display = useTableDisplay(columns, `${application.key}:${object.id}:${objectTypeKey}`);
  const [selectedPageSize, setPageSize] = useState(pageSize);
  const objectType = objectTypeFor(model, objectTypeKey);
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [creating, setCreating] = useState(false);
  // Panels list by name, as every list does without a sort, until the user sorts by another column.
  const [sort, setSort] = useState("name");
  const sortFields = objectType ? listSortFields(model, [objectType], columns, [], !changeSet && !publication) : [];
  // Only the shown relation columns are read (0.9 K5, D146).
  const expand = relatedKeys(display.columns);
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
            expand,
            // As many as a wide column can show; the cell draws what fits (K5b).
            expandLimit: expand.length ? RELATED_EXPAND_LIMIT : undefined,
          })
      : null,
    [
      application.key,
      object.workspaceKey,
      objectTypeKey,
      selectedPageSize,
      parentObjectId,
      search,
      sort,
      expand.join(" "),
    ],
  );
  // Cells edited in place (0.10 A9): a save reloads the list where it is.
  const cells = useCellEditing({ model, list: pages, readOnly: Boolean(readOnly), onChanged });
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
        <PanelTools
          folded={panelFolds(pages, searchInput.trim() !== "")}
          sortable={sorting.fields.length > 0}
          search={
            <SearchField
              className="compact"
              label={`Search ${objectType.pluralName.toLowerCase()}`}
              value={searchInput}
              onChange={setSearchInput}
              placeholder={`Search ${objectType.pluralName.toLowerCase()}`}
            />
          }
          display={
            <TableDisplay
              model={model}
              columns={columns}
              display={display}
              pageSize={selectedPageSize}
              defaultPageSize={pageSize}
              onPageSize={setPageSize}
            />
          }
          sort={<SortMenu sorting={sorting} />}
        />
        {allowCreate && creatable && (
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
          renderCell={cells.renderCell}
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
      {cells.dialogs}
      {creating && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={object.workspaceKey}
          objectType={objectType}
          parentObjectId={parentObjectId}
          parentObjectTypeKey={parentObjectId ? object.objectTypeKey : undefined}
          parentName={parentObjectId ? object.name : undefined}
          collectionName={`${objectType.pluralName} of ${object.name}`}
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
