import { useMemo, useState } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { EngineModel, ObjectItem, RelationItem, RelationsPanelDefinition } from "@/types";
import { isManagedRelation, relationChoices } from "@/model/lookup";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { RelationFormDialog } from "./RelationFormDialog";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { formatValue } from "@/ui/formatValue";
import { attributeName, fieldValue } from "@/model/fields";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";
import { ScrollWindow } from "@/ui/ScrollWindow";

const PAGE_SIZE = 50;
const SORTS = [
  { value: "name", label: "Name, A to Z", live: false },
  { value: "-name", label: "Name, Z to A", live: false },
  { value: "-createdAt", label: "Newest first", live: true },
  { value: "createdAt", label: "Oldest first", live: true },
];

export function RelationsPanel({
  model,
  object,
  panel,
  onOpen,
  onChanged = () => undefined,
  readOnly = false,
}: {
  model: EngineModel;
  object: ObjectItem;
  panel: RelationsPanelDefinition;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onChanged?: () => void;
  readOnly?: boolean;
}) {
  const api = useDataApi();
  const { draft, revision } = useWorkspaceData();
  const live = !draft && !revision;
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [sort, setSort] = useState("name");
  const [removeError, setRemoveError] = useState("");
  const [creating, setCreating] = useState(false);
  const [creatingDependent, setCreatingDependent] = useState<{
    applicationKey: string;
    objectTypeKey: string;
    relationTypeKey: string;
  }>();
  const [editing, setEditing] = useState<RelationItem>();
  const [removing, setRemoving] = useState<RelationItem>();
  const [pending, setPending] = useState(false);
  const relationTypeKey = panel.config.relationTypeKeys.length === 1 ? panel.config.relationTypeKeys[0] : undefined;
  const choices = useMemo(
    () => relationChoices(model, object.objectTypeKey, panel),
    [model, object.objectTypeKey, panel],
  );
  const dependentCreates = useMemo(
    () =>
      model.objectTypeRelations.flatMap((allowed) => {
        if (
          !allowed.required ||
          allowed.fromObjectTypeKey !== object.objectTypeKey ||
          !panel.config.relationTypeKeys.includes(allowed.relationTypeKey) ||
          panel.config.direction === "incoming"
        )
          return [];
        const applications = model.applications.filter((application) =>
          application.objectTypeKeys.includes(allowed.toObjectTypeKey),
        );
        return applications.length === 1
          ? [
              {
                applicationKey: applications[0].key,
                objectTypeKey: allowed.toObjectTypeKey,
                relationTypeKey: allowed.relationTypeKey,
              },
            ]
          : [];
      }),
    [model, object.objectTypeKey, panel.config.direction, panel.config.relationTypeKeys],
  );

  const effectiveSort = live || !SORTS.find((option) => option.value === sort)?.live ? sort : "name";
  const list = useCursorWindow<RelationItem>(
    (selector) =>
      api.relations(object.id, {
        workspaceKey: object.workspaceKey,
        direction: panel.config.direction,
        ...(relationTypeKey ? { relationTypeKey } : {}),
        search,
        sort: effectiveSort,
        ...selector,
        pageSize: PAGE_SIZE,
      }),
    [object.id, object.workspaceKey, panel.config.direction, relationTypeKey, search, effectiveSort],
  );
  const { items: relations, loading, error: feedError, retry, reload } = list;
  // Loading failures belong to the panel; delete failures stay in their confirmation dialog so
  // cancelling that action cannot leave the collection in a persistent feed-error state.
  const error = feedError;
  const visible = relations.flatMap((item, position) =>
    panel.config.relationTypeKeys.includes(item.relation.relationTypeKey)
      ? [{ item, index: list.startIndex + position }]
      : [],
  );
  const showRelationshipColumn = panel.config.showRelationshipColumn !== false;
  const tableColumnCount = panel.config.columns.length + 1 + (showRelationshipColumn ? 1 : 0);
  const linkColumn = panel.config.columns.includes("name") ? "name" : panel.config.columns[0];

  function allowedFor(item: RelationItem) {
    const fromType = item.direction === "outgoing" ? object.objectTypeKey : item.object.objectTypeKey;
    const toType = item.direction === "outgoing" ? item.object.objectTypeKey : object.objectTypeKey;
    return model.objectTypeRelations.find(
      (allowed) =>
        allowed.relationTypeKey === item.relation.relationTypeKey &&
        allowed.fromObjectTypeKey === fromType &&
        allowed.toObjectTypeKey === toType,
    );
  }
  function managed(item: RelationItem) {
    const allowed = allowedFor(item);
    return allowed ? isManagedRelation(model, allowed) : true;
  }

  async function remove() {
    if (!removing) return;
    setPending(true);
    setRemoveError("");
    try {
      await api.deleteRelation(removing.relation.id, removing.relation.version);
      setRemoving(undefined);
      onChanged();
      reload();
    } catch (cause) {
      setRemoveError(errorMessage(cause));
      if (isApiError(cause, "version_conflict") || isApiError(cause, "workspace_draft_version_conflict")) {
        try {
          const fresh = await api.relation(removing.relation.id, object.workspaceKey);
          setRemoving({ ...removing, relation: fresh });
        } catch (reloadCause) {
          setRemoveError(errorMessage(reloadCause));
        }
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <div className="embedded-toolbar relation-toolbar">
        <label className="search-box compact">
          <Icon name="search" />
          <input
            aria-label={`Search ${panel.title.toLowerCase()}`}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search related records"
          />
        </label>
        <label className="toolbar-field">
          Sort
          <select value={effectiveSort} onChange={(event) => setSort(event.target.value)}>
            {SORTS.filter((option) => live || !option.live).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        {!readOnly &&
          dependentCreates.map((creation) => (
            <button
              key={`${creation.relationTypeKey}:${creation.objectTypeKey}`}
              className="secondary"
              onClick={() => setCreatingDependent(creation)}
            >
              <Icon name="plus" /> Add{" "}
              {model.objectTypes.find((item) => item.key === creation.objectTypeKey)?.name ?? creation.objectTypeKey}
            </button>
          ))}
        {!readOnly && choices.length > 0 && (
          <button className="secondary" onClick={() => setCreating(true)}>
            <Icon name="plus" /> Add relationship
          </button>
        )}
      </div>
      {error && <InlineError message={error} onRetry={retry} />}
      {(!error || relations.length > 0) && (
        <ScrollWindow
          list={list}
          label={panel.title}
          noun={["relationship", "relationships"]}
          pageSize={PAGE_SIZE}
          className="table-wrap"
        >
          <table
            aria-busy={loading || undefined}
            aria-rowcount={list.totalCount !== null && visible.length > 0 ? list.totalCount + 1 : undefined}
          >
            <caption className="visually-hidden">{panel.title}</caption>
            <thead>
              <tr aria-rowindex={1}>
                {showRelationshipColumn && <th>Relationship</th>}
                {panel.config.columns.map((column) => (
                  <th key={column}>{attributeName(model, column)}</th>
                ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && relations.length === 0 ? (
                <tr>
                  <td colSpan={tableColumnCount} className="empty-row">
                    Loading…
                  </td>
                </tr>
              ) : visible.length === 0 ? (
                <tr>
                  <td colSpan={tableColumnCount} className="empty-row">
                    {search ? "No relationships match this search." : "No relationships yet."}
                  </td>
                </tr>
              ) : (
                visible.map(({ item, index }) => {
                  const definition = model.relationTypes.find(
                    (relation) => relation.key === item.relation.relationTypeKey,
                  );
                  const allowed = allowedFor(item);
                  const immutable = managed(item);
                  const required = allowed?.required === true;
                  const hasAttributes = Boolean(allowed?.attributeTypeKeys?.length);
                  return (
                    <tr
                      key={item.relation.id}
                      data-row-key={item.relation.id}
                      data-row-index={index}
                      aria-rowindex={index + 2}
                      tabIndex={-1}
                    >
                      {showRelationshipColumn && (
                        <td>{item.direction === "outgoing" ? definition?.name : definition?.reverseName}</td>
                      )}
                      {panel.config.columns.map((column) => (
                        <td key={column}>
                          {column === linkColumn ? (
                            <button
                              className="cell-link"
                              data-row-focus
                              onClick={() =>
                                onOpen(item.object.objectTypeKey, item.object.id, item.object.applicationKey)
                              }
                            >
                              {formatValue(fieldValue(item.object, column, model))}
                            </button>
                          ) : (
                            formatValue(fieldValue(item.object, column, model))
                          )}
                        </td>
                      ))}
                      <td>
                        <div className="row-actions">
                          {immutable ? (
                            <span className="managed-label">Managed through Parent</span>
                          ) : (
                            <>
                              {!readOnly && hasAttributes && <button onClick={() => setEditing(item)}>Edit</button>}
                              {required ? (
                                <span className="managed-label">Required relationship</span>
                              ) : !readOnly ? (
                                <button className="text-danger" onClick={() => setRemoving(item)}>
                                  Delete
                                </button>
                              ) : null}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </ScrollWindow>
      )}
      {creating && (
        <RelationFormDialog
          model={model}
          object={object}
          choices={choices}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            onChanged();
            reload();
          }}
        />
      )}
      {creatingDependent && (
        <ObjectFormDialog
          model={model}
          applicationKey={creatingDependent.applicationKey}
          workspaceKey={object.workspaceKey}
          objectType={model.objectTypes.find((item) => item.key === creatingDependent.objectTypeKey)!}
          initialRelationObjects={{ [creatingDependent.relationTypeKey]: object }}
          lockedInitialRelationKeys={[creatingDependent.relationTypeKey]}
          onClose={() => setCreatingDependent(undefined)}
          onSaved={() => {
            setCreatingDependent(undefined);
            onChanged();
            reload();
          }}
        />
      )}
      {editing && (
        <RelationFormDialog
          model={model}
          object={object}
          choices={choices}
          existing={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined);
            onChanged();
            reload();
          }}
        />
      )}
      {removing && (
        <ConfirmDialog
          title="Delete relationship?"
          confirmLabel="Delete relationship"
          pending={pending}
          error={removeError}
          onCancel={() => {
            setRemoving(undefined);
            setRemoveError("");
          }}
          onConfirm={remove}
        >
          <p>The connected objects will remain. Only this relationship will be deleted.</p>
        </ConfirmDialog>
      )}
    </>
  );
}
