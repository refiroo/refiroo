import { ownEndReasonParts, ownEndScope, type WordPart } from "@/model/candidates";
import { useEffect, useMemo, useState } from "react";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { EngineModel, ObjectItem, RelationItem, RelationsPanelDefinition } from "@/types";
import { holdsOne, holdsOneHere, isManagedRelation, relatedObjectTypes, relationChoices } from "@/model/lookup";
import type { RelationChoice } from "@/model/lookup";
import { DeleteRelationDialog } from "@/features/objects/DeleteRelationDialog";
import { RelationFormDialog } from "./RelationFormDialog";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { FieldValue } from "@/ui/FieldValue";
import { attributeName, isQueryableField, listSortFields } from "@/model/fields";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";
import { IconButton } from "@/ui/IconButton";
import { InfoHint } from "@/ui/InfoHint";
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
  // A relationship is written where either end's type may be (0.12 Z5, D291, D329).
  const writes = useRecordWrites();
  const own = writes.permits(object.applicationKey, object.objectTypeKey);
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
  const choices = useMemo(
    () =>
      relationChoices(model, object.objectTypeKey, panel).filter(
        (choice) => own || writes.permitsType(choice.otherObjectTypeKey),
      ),
    [model, object.objectTypeKey, panel, own, writes],
  );
  // A relationship whose end the record does not meet is not offered, with the reason (0.9 K7, D172).
  const [refusedOwn, setRefusedOwn] = useState<{ id: string; kinds: ReadonlySet<string> }>();
  useEffect(() => {
    const limited = choices.filter((choice) => ownEndScope(model, choice.relation, choice.direction));
    if (readOnly || limited.length === 0) return;
    let current = true;
    Promise.all(
      limited.map((choice) =>
        api
          .objects(object.objectTypeKey, {
            workspaceKey: object.workspaceKey,
            ...ownEndScope(model, choice.relation, choice.direction),
            filters: [{ field: "id", operator: "eq", value: object.id }],
            pageSize: 1,
          })
          .then((page) => (page.items.length ? undefined : choiceKind(choice))),
      ),
    )
      .then(
        (found) =>
          current &&
          setRefusedOwn({ id: object.id, kinds: new Set(found.filter((kind): kind is string => kind !== undefined)) }),
      )
      .catch(() => undefined);
    return () => {
      current = false;
    };
  }, [api, choices, model, object.id, object.objectTypeKey, object.workspaceKey, readOnly]);
  const refused = useMemo(
    () => (refusedOwn?.id === object.id ? refusedOwn.kinds : NONE_REFUSED),
    [refusedOwn, object.id],
  );
  const offered = useMemo(() => choices.filter((choice) => !refused.has(choiceKind(choice))), [choices, refused]);
  const refusedReasons = [
    ...new Map(
      choices
        .filter((choice) => refused.has(choiceKind(choice)))
        .map((choice) => ownEndReasonParts(model, choice.relation, choice.direction))
        .filter((parts): parts is WordPart[] => Boolean(parts))
        .map((parts) => [parts.map((part) => part.text).join(""), parts] as const),
    ),
  ];
  // Where the record holds at most one of a kind (0.9 K3a, D139) it is set, not added to: Set while
  // it holds none, Change and Delete on the one it holds.
  const adding = useMemo(() => offered.filter((choice) => !holdsOneHere(choice)), [offered]);
  const singles = useMemo(() => offered.filter(holdsOneHere), [offered]);
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

  /** A row's actions as icon buttons (UA8, U-D15), each named for the record it acts on; a row
   * that cannot be changed here shows a lock giving the reason (U-D19). */
  function actionsFor(item: RelationItem) {
    const allowed = allowedFor(item);
    const required = allowed?.required === true;
    const hasAttributes = Boolean(allowed?.attributeTypeKeys?.length);
    const definition = model.relationTypes.find((relation) => relation.key === item.relation.relationTypeKey);
    const kind = `${(item.direction === "outgoing" ? definition?.name : definition?.reverseName) ?? item.relation.relationTypeKey}: ${item.object.name}`;
    const locked = managed(item) ? "Managed through Parent" : required ? "Required relationship" : undefined;
    // A relationship to a record of a type the person may not write, from a record they may not
    // write either, offers no change (D291).
    const fixed = readOnly || !(own || writes.permits(item.object.applicationKey, item.object.objectTypeKey));
    return (
      <div className="row-actions relation-row-actions">
        {!fixed && !locked && changeChoice(item) && (
          <IconButton
            icon="swap"
            label={`Change ${kind}`}
            tooltip="Change to another record"
            quiet
            onClick={() => setChanging(item)}
          />
        )}
        {!fixed && !managed(item) && hasAttributes && (
          <IconButton
            icon="pencil"
            label={`Edit values of ${kind}`}
            tooltip="Edit values"
            quiet
            onClick={() => setEditing(item)}
          />
        )}
        {locked ? (
          <span className="relation-row-lock" title={locked}>
            <Icon name="lock" size={14} />
            <span className="visually-hidden">{locked}</span>
          </span>
        ) : !fixed ? (
          <IconButton
            icon="trash"
            label={`Delete ${kind}`}
            tooltip="Delete relationship"
            tone="danger"
            quiet
            onClick={() => setRemoving(item)}
          />
        ) : null}
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

  return (
    <>
      {/* The heading is drawn here, not by the record page, so the hint can sit beside it. */}
      <h2>
        {panel.title}
        {!readOnly && refusedReasons.length > 0 && (
          <InfoHint label={`About ${panel.title}`}>
            {refusedReasons.map(([reason, parts]) => (
              <p key={reason}>
                {parts.map((part, index) =>
                  part.mark ? (
                    <strong key={index} className={`info-hint-${part.mark}`}>
                      {part.text}
                    </strong>
                  ) : (
                    part.text
                  ),
                )}
              </p>
            ))}
          </InfoHint>
        )}
      </h2>
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
          dependentCreates
            .filter((creation) => writes.permits(creation.applicationKey, creation.objectTypeKey))
            .map((creation) => (
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
        <DeleteRelationDialog
          relation={removing}
          workspaceKey={object.workspaceKey}
          onCancel={() => setRemoving(undefined)}
          onDeleted={() => {
            setRemoving(undefined);
            changed();
          }}
        />
      )}
    </>
  );
}

const NONE_REFUSED: ReadonlySet<string> = new Set();

/** A relationship choice's identity: its direction, relation type and the type at the other end. */
function choiceKind(choice: RelationChoice) {
  return `${choice.direction} ${choice.relation.relationTypeKey} ${choice.otherObjectTypeKey}`;
}
