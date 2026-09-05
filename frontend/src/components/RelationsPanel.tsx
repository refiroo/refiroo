import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type {
  AttributeTypeDefinition,
  EngineModel,
  ObjectItem,
  RelationItem,
  RelationsPanelDefinition,
} from "../types";
import { isManagedRelation, relationChoices, type RelationChoice } from "../utils/model";
import { AttributeField, attributeValueFromForm } from "./AttributeField";
import { ConfirmDialog } from "./ConfirmDialog";
import { ObjectLookup } from "./ObjectLookup";
import { ObjectFormDialog } from "./ObjectFormDialog";
import { formatValue } from "./ObjectTable";
import { attributeName, fieldValue } from "../utils/model";
import { InlineError } from "./AsyncState";

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
  const [relations, setRelations] = useState<RelationItem[]>([]);
  const [cursor, setCursor] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [errorMode, setErrorMode] = useState<"load" | "more">("load");
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

  async function load() {
    setLoading(true);
    try {
      const page = await api.relations(object.id, {
        direction: panel.config.direction,
        ...(relationTypeKey ? { relationTypeKey } : {}),
      });
      setRelations(page.items);
      setCursor(page.nextCursor ?? undefined);
      setError("");
    } catch (cause) {
      setErrorMode("load");
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [object.id, panel.config.direction, relationTypeKey]);
  async function loadMore() {
    if (!cursor) return;
    setLoading(true);
    setError("");
    try {
      const page = await api.relations(object.id, {
        direction: panel.config.direction,
        ...(relationTypeKey ? { relationTypeKey } : {}),
        cursor,
      });
      setRelations((current) => [...current, ...page.items]);
      setCursor(page.nextCursor ?? undefined);
    } catch (cause) {
      setErrorMode("more");
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }
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
    setError("");
    try {
      await api.deleteRelation(removing.relation.id, removing.relation.version);
      setRemoving(undefined);
      onChanged();
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      if ((cause as { code?: string }).code === "version_conflict") {
        try {
          const fresh = await api.relation(removing.relation.id);
          setRemoving({ ...removing, relation: fresh });
        } catch (reloadCause) {
          setError(reloadCause instanceof Error ? reloadCause.message : String(reloadCause));
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
      {error && <InlineError message={error} onRetry={() => void (errorMode === "more" ? loadMore() : load())} />}
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
      {cursor && !error && (
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
          onSaved={async () => {
            setCreating(false);
            onChanged();
            await load();
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
          onSaved={async () => {
            setCreatingDependent(undefined);
            onChanged();
            await load();
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
          onSaved={async () => {
            setEditing(undefined);
            onChanged();
            await load();
          }}
        />
      )}
      {removing && (
        <ConfirmDialog
          title="Delete relationship?"
          confirmLabel="Delete relationship"
          pending={pending}
          error={error}
          onCancel={() => setRemoving(undefined)}
          onConfirm={remove}
        >
          <p>The connected objects will remain. Only this relationship will be deleted.</p>
        </ConfirmDialog>
      )}
    </>
  );
}

function RelationFormDialog({
  model,
  object,
  choices,
  existing,
  onClose,
  onSaved,
}: {
  model: EngineModel;
  object: ObjectItem;
  choices: RelationChoice[];
  existing?: RelationItem;
  onClose: () => void;
  onSaved: () => void;
}) {
  const existingChoice =
    existing &&
    choices.find(
      (choice) =>
        choice.direction === existing.direction &&
        choice.relation.relationTypeKey === existing.relation.relationTypeKey &&
        choice.otherObjectTypeKey === existing.object.objectTypeKey,
    );
  const [choiceIndex, setChoiceIndex] = useState(Math.max(0, existingChoice ? choices.indexOf(existingChoice) : 0));
  const [candidate, setCandidate] = useState<ObjectItem | undefined>(existing?.object);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [relationVersion, setRelationVersion] = useState(existing?.relation.version ?? 1);
  const choice = choices[choiceIndex];
  const attributes = (choice?.relation.attributeTypeKeys ?? [])
    .map((key) => model.attributeTypes.find((item) => item.key === key))
    .filter((item): item is AttributeTypeDefinition => Boolean(item));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!choice || (!existing && !candidate)) return;
    setSaving(true);
    setError("");
    try {
      const values = Object.fromEntries(
        attributes.map((attribute) => [attribute.key, attributeValueFromForm(event.currentTarget, attribute)]),
      );
      if (existing)
        await api.updateRelation(existing.relation.id, { attributes: values, expectedVersion: relationVersion });
      else
        await api.createRelation({
          relationTypeKey: choice.relation.relationTypeKey,
          fromObjectId: choice.direction === "outgoing" ? object.id : candidate!.id,
          toObjectId: choice.direction === "outgoing" ? candidate!.id : object.id,
          attributes: values,
        });
      onSaved();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      if (existing && (cause as { code?: string }).code === "version_conflict") {
        try {
          const fresh = await api.relation(existing.relation.id);
          setRelationVersion(fresh.version);
        } catch (reloadCause) {
          setError(reloadCause instanceof Error ? reloadCause.message : String(reloadCause));
        }
      }
      setSaving(false);
    }
  }
  if (!choice) return null;
  return (
    <div className="dialog-backdrop" onMouseDown={() => !saving && onClose()}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="relation-form-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <div>
            <p className="eyebrow">{existing ? "Edit relationship" : "Create relationship"}</p>
            <h2 id="relation-form-title">{existing ? choice.label : "Connect an object"}</h2>
          </div>
          <button type="button" className="close" onClick={onClose}>
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          {!existing && (
            <>
              <label>
                Relationship
                <select
                  value={choiceIndex}
                  onChange={(event) => {
                    setChoiceIndex(Number(event.target.value));
                    setCandidate(undefined);
                  }}
                >
                  {choices.map((item, index) => (
                    <option
                      key={`${item.direction}:${item.relation.relationTypeKey}:${item.otherObjectTypeKey}`}
                      value={index}
                    >
                      {item.label} ({item.direction})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Object
                <ObjectLookup
                  objectTypeKey={choice.otherObjectTypeKey}
                  workspaceKey={object.workspaceKey}
                  excludeId={object.id}
                  value={candidate}
                  required
                  onChange={setCandidate}
                />
              </label>
            </>
          )}
          {attributes.map((attribute) => (
            <AttributeField
              key={attribute.key}
              attribute={attribute}
              value={existing?.relation.attributes[attribute.key]}
            />
          ))}
          {error && <div className="notice error-notice">{error}</div>}
          <div className="dialog-actions">
            <button type="button" className="secondary" onClick={onClose}>
              Cancel
            </button>
            <button className="primary" disabled={saving || (!existing && !candidate)}>
              {saving ? "Saving…" : existing ? "Save" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
