import { useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { EngineModel, ObjectItem, RelationItem, RelationsPanelDefinition } from "@/types";
import { isManagedRelation, relationChoices } from "@/model/lookup";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { RelationFormDialog } from "./RelationFormDialog";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { formatValue } from "@/ui/formatValue";
import { attributeName, fieldValue } from "@/model/fields";
import { InlineError } from "@/ui/InlineError";

export function RelationsPanel({
  model,
  object,
  panel,
  onOpen,
  onChanged = () => undefined,
}: {
  model: EngineModel;
  object: ObjectItem;
  panel: RelationsPanelDefinition;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  onChanged?: () => void;
}) {
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

  const {
    items: relations,
    loading,
    error: feedError,
    hasMore,
    loadMore,
    retry,
    reload,
  } = useCursorFeed<RelationItem>(
    (cursor) =>
      api.relations(object.id, {
        direction: panel.config.direction,
        ...(relationTypeKey ? { relationTypeKey } : {}),
        ...(cursor ? { cursor } : {}),
      }),
    [object.id, panel.config.direction, relationTypeKey],
  );
  // Loading failures belong to the panel; delete failures stay in their confirmation dialog so
  // cancelling that action cannot leave the collection in a persistent feed-error state.
  const error = feedError;
  const visible = relations.filter((item) => panel.config.relationTypeKeys.includes(item.relation.relationTypeKey));
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
      if (isApiError(cause, "version_conflict")) {
        try {
          const fresh = await api.relation(removing.relation.id);
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
        {dependentCreates.map((creation) => (
          <button
            key={`${creation.relationTypeKey}:${creation.objectTypeKey}`}
            className="secondary"
            onClick={() => setCreatingDependent(creation)}
          >
            + Add{" "}
            {model.objectTypes.find((item) => item.key === creation.objectTypeKey)?.name ?? creation.objectTypeKey}
          </button>
        ))}
        {choices.length > 0 && (
          <button className="secondary" onClick={() => setCreating(true)}>
            + Add relationship
          </button>
        )}
      </div>
      {error && <InlineError message={error} onRetry={retry} />}
      {(!error || relations.length > 0) && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
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
                    No relationships yet.
                  </td>
                </tr>
              ) : (
                visible.map((item) => {
                  const definition = model.relationTypes.find(
                    (relation) => relation.key === item.relation.relationTypeKey,
                  );
                  const allowed = allowedFor(item);
                  const immutable = managed(item);
                  const required = allowed?.required === true;
                  const hasAttributes = Boolean(allowed?.attributeTypeKeys?.length);
                  return (
                    <tr key={item.relation.id}>
                      {showRelationshipColumn && (
                        <td>{item.direction === "outgoing" ? definition?.name : definition?.reverseName}</td>
                      )}
                      {panel.config.columns.map((column) => (
                        <td key={column}>
                          {column === linkColumn ? (
                            <button
                              className="cell-link"
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
                              {hasAttributes && <button onClick={() => setEditing(item)}>Edit</button>}
                              {required ? (
                                <span className="managed-label">Required relationship</span>
                              ) : (
                                <button className="text-danger" onClick={() => setRemoving(item)}>
                                  Delete
                                </button>
                              )}
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
        </div>
      )}
      {hasMore && !error && (
        <button type="button" className="load-more inline" disabled={loading} onClick={loadMore}>
          {loading ? "Loading…" : "Load more relationships"}
        </button>
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
