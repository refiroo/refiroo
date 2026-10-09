import { useEffect, useMemo, useState } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { EngineModel, ObjectItem, RelationItem, RelationsPanelDefinition } from "@/types";
import { holdsOne, holdsOneHere, isManagedRelation, relatedObjectTypes, relationChoices } from "@/model/lookup";
import type { RelationChoice } from "@/model/lookup";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { RelationFormDialog } from "./RelationFormDialog";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { FieldValue } from "@/ui/FieldValue";
import { attributeName, isQueryableField, listSortFields } from "@/model/fields";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { objectTypeHue } from "@/model/hues";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
import { SortMenu, useTableSort } from "@/ui/TableSort";

const PAGE_SIZE = 50;

/** A kind of relationship as the engine counts it at the record's end: a relation type, a direction. */
function kindOf(choice: RelationChoice) {
  return `${choice.direction} ${choice.relation.relationTypeKey}`;
}

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
  const { changeSet, publication } = useWorkspaceData();
  const live = !changeSet && !publication;
  const showRelationshipColumn = panel.config.showRelationshipColumn !== false;
  const display = useTableDisplay(
    panel.config.columns,
    `${object.applicationKey}:${object.id}:${panel.key}`,
    showRelationshipColumn ? ["relationship"] : [],
  );
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  // Every data column sorts, as does the relationship label; the panel may add fields to the Sort
  // menu (`sortFields`) and choose the initial order (`defaultSort`, schema 0.7), otherwise name.
  const relationTypeKey = panel.config.relationTypeKeys.length === 1 ? panel.config.relationTypeKeys[0] : undefined;
  const sortFields = useMemo(
    () =>
      listSortFields(
        model,
        // The types the request can list: one relation type is sent, several are not filtered.
        relatedObjectTypes(
          model,
          object.objectTypeKey,
          panel.config.direction,
          relationTypeKey ? [relationTypeKey] : [],
        ),
        [...(showRelationshipColumn ? ["relationship"] : []), ...panel.config.columns],
        panel.config.sortFields ?? [],
        live,
        { relationList: true },
      ),
    [model, object.objectTypeKey, panel.config, relationTypeKey, showRelationshipColumn, live],
  );
  const defaultSort =
    panel.config.defaultSort && isQueryableField(panel.config.defaultSort, live) ? panel.config.defaultSort : "name";
  const [sort, setSort] = useState<string>();
  const [removeError, setRemoveError] = useState("");
  const [creating, setCreating] = useState(false);
  const [creatingDependent, setCreatingDependent] = useState<{
    applicationKey: string;
    objectTypeKey: string;
    relationTypeKey: string;
  }>();
  const [editing, setEditing] = useState<RelationItem>();
  const [changing, setChanging] = useState<RelationItem>();
  const [setting, setSetting] = useState(false);
  const [removing, setRemoving] = useState<RelationItem>();
  const [pending, setPending] = useState(false);
  const choices = useMemo(
    () => relationChoices(model, object.objectTypeKey, panel),
    [model, object.objectTypeKey, panel],
  );
  // Where the record holds at most one of a kind (0.9 K3a, D139) it is set, not added to: Set while
  // it holds none, Change and Delete on the one it holds.
  const adding = useMemo(() => choices.filter((choice) => !holdsOneHere(choice)), [choices]);
  const singles = useMemo(() => choices.filter(holdsOneHere), [choices]);
  const [heldToken, setHeldToken] = useState(0);
  const [held, setHeld] = useState<{ token: number; kinds: Set<string> }>();
  useEffect(() => {
    if (readOnly || singles.length === 0) return;
    let current = true;
    const kinds = [...new Set(singles.map(kindOf))];
    Promise.all(
      kinds.map((kind) => {
        const [direction, relationTypeKey] = kind.split(" ") as ["outgoing" | "incoming", string];
        return api
          .relations(object.id, { workspaceKey: object.workspaceKey, direction, relationTypeKey, pageSize: 1 })
          .then((page) => (page.items.length ? kind : undefined));
      }),
    )
      .then(
        (found) =>
          current &&
          setHeld({ token: heldToken, kinds: new Set(found.filter((kind): kind is string => kind !== undefined)) }),
      )
      // Unknown is treated as held: Set is offered only where the record is known to hold none.
      .catch(() => current && setHeld({ token: heldToken, kinds: new Set(kinds) }));
    return () => {
      current = false;
    };
  }, [api, object.id, object.workspaceKey, singles, readOnly, heldToken]);
  const settable = held?.token === heldToken ? singles.filter((choice) => !held.kinds.has(kindOf(choice))) : [];
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

  const effectiveSort = sort && sortFields.includes(sort.replace(/^-/, "")) ? sort : defaultSort;
  const sorting = useTableSort({
    sort: effectiveSort,
    fields: sortFields,
    onSort: setSort,
    labelFor: (field) => (field === "relationship" ? "Relationship" : attributeName(model, field)),
  });
  const list = useCursorWindow<RelationItem>(
    (selector) =>
      api.relations(object.id, {
        workspaceKey: object.workspaceKey,
        direction: panel.config.direction,
        ...(relationTypeKey ? { relationTypeKey } : {}),
        search,
        sort: effectiveSort,
        ...selector,
        pageSize,
      }),
    [object.id, object.workspaceKey, panel.config.direction, relationTypeKey, search, effectiveSort, pageSize],
  );
  const { items: relations, error: feedError, retry, reload } = list;
  function changed() {
    onChanged();
    reload();
    setHeldToken((token) => token + 1);
  }
  // Loading failures belong to the panel; delete failures stay in their confirmation dialog so
  // cancelling that action cannot leave the collection in a persistent feed-error state.
  const error = feedError;
  const linkColumn = display.identity;
  const columns: DataColumn<RelationItem>[] = [
    ...(showRelationshipColumn
      ? [
          {
            key: "relationship",
            label: "Relationship",
            cell: (item: RelationItem) => {
              const definition = model.relationTypes.find((relation) => relation.key === item.relation.relationTypeKey);
              return item.direction === "outgoing" ? definition?.name : definition?.reverseName;
            },
          },
        ]
      : []),
    ...display.columns.map((column) => ({
      key: column,
      label: attributeName(model, column),
      cell: (item: RelationItem) =>
        column === linkColumn ? (
          <button
            className="cell-link"
            data-row-focus
            onClick={() => onOpen(item.object.objectTypeKey, item.object.id, item.object.applicationKey)}
          >
            <FieldValue item={item.object} field={column} model={model} />
          </button>
        ) : (
          <FieldValue item={item.object} field={column} model={model} />
        ),
    })),
  ];

  function actionsFor(item: RelationItem) {
    const allowed = allowedFor(item);
    const required = allowed?.required === true;
    const hasAttributes = Boolean(allowed?.attributeTypeKeys?.length);
    return (
      <div className="row-actions">
        {managed(item) ? (
          <span className="managed-label">Managed through Parent</span>
        ) : (
          <>
            {!readOnly && hasAttributes && <button onClick={() => setEditing(item)}>Edit</button>}
            {!readOnly && !required && changeChoice(item) && <button onClick={() => setChanging(item)}>Change</button>}
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
    );
  }

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
  /** The kind a row's relationship is, where the record holds only one of it. */
  function changeChoice(item: RelationItem) {
    const allowed = allowedFor(item);
    if (!allowed || !holdsOne(allowed, item.direction === "outgoing" ? "from" : "to")) return undefined;
    return choices.find(
      (choice) =>
        choice.direction === item.direction &&
        choice.relation.relationTypeKey === item.relation.relationTypeKey &&
        choice.otherObjectTypeKey === item.object.objectTypeKey,
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
      changed();
    } catch (cause) {
      setRemoveError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")) {
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
        <TableDisplay
          model={model}
          columns={panel.config.columns}
          display={display}
          pageSize={pageSize}
          defaultPageSize={PAGE_SIZE}
          onPageSize={setPageSize}
        />
        <SortMenu sorting={sorting} />
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
        {!readOnly && settable.length > 0 && (
          <button className="secondary" onClick={() => setSetting(true)}>
            <Icon name="plus" /> Set relationship
          </button>
        )}
        {!readOnly && adding.length > 0 && (
          <button className="secondary" onClick={() => setCreating(true)}>
            <Icon name="plus" /> Add relationship
          </button>
        )}
      </div>
      {error && <InlineError message={error} onRetry={retry} />}
      {(!error || relations.length > 0) && (
        <DataTable<RelationItem>
          columns={columns}
          identityColumn={linkColumn}
          list={list}
          rowKey={(item) => item.relation.id}
          rowFilter={(item) => panel.config.relationTypeKeys.includes(item.relation.relationTypeKey)}
          rowHue={(item) => objectTypeHue(model, item.object.objectTypeKey)}
          rowAttributes={() => ({ tabIndex: -1 })}
          actions={{ header: "Actions", width: 168, className: "relation-actions-column", cell: actionsFor }}
          sorting={sorting}
          columnWidths={display.widths}
          onColumnWidths={display.setWidths}
          label={panel.title}
          noun={["relationship", "relationships"]}
          pageSize={pageSize}
          compact={display.compact}
          emptyMessage={search ? "No relationships match this search." : "No relationships yet."}
        />
      )}
      {creating && (
        <RelationFormDialog
          model={model}
          object={object}
          choices={adding}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            changed();
          }}
        />
      )}
      {setting && (
        <RelationFormDialog
          model={model}
          object={object}
          choices={settable}
          setting
          onClose={() => setSetting(false)}
          onSaved={() => {
            setSetting(false);
            changed();
          }}
        />
      )}
      {changing && (
        <RelationFormDialog
          model={model}
          object={object}
          choices={[changeChoice(changing)!]}
          replacing={changing}
          onClose={() => setChanging(undefined)}
          onSaved={() => {
            setChanging(undefined);
            changed();
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
            changed();
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
            changed();
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
