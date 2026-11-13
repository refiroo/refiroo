/**
 * The `tree` lens (Base 0.8 B3): a containment hierarchy as a tree, beside the selected record's
 * detail in the inspector. Loading, keyboard traversal and revealing a record are the sidebar tree's
 * (S6), configured by the view: its root and node types, each type's branch order, its page size
 * and its label. Every label, field and action comes from the view; nothing here names a starter
 * type.
 *
 * The view's `actions` are offered from a node's menu (Shift+F10, the context menu key or the ⋯
 * on the row) and by shortcut: add a child of each type the node can contain, rename the label in
 * place (F2), set the availability field (the switch on the row) and move the node to another
 * parent. In a change set the actions write to it; in a publication the tree is read-only. A failed
 * write keeps the user's place and input: the rename field stays open, the move dialog stays open
 * with the error, and loaded branches stay loaded.
 *
 * Where the view allows moves, a record can also be dragged with mouse or pen (B5, D34): onto a
 * node, into a gap between rows or onto a type heading. A target the model's containment rule or the
 * move's refusals exclude glows red with the reason and takes no drop; an accepted one opens the move
 * dialog with the target chosen, so the move is confirmed and written exactly as Move to… does.
 *
 * Both paths also move a record to the top level (B5b, D36): Move to… lists it above the candidates,
 * and the top-level headings and the gaps between top-level rows take a drop. Only a record of one
 * of the tree's root types goes there, since the tree shows no other type at the top.
 *
 * In a change set, where the view allows moves, the lens also restructures (C4, ADR-034, D38). A
 * place where the record's type cannot stand but another type of the tree can is a target too: Move
 * to… marks it and a drag glows green with “Becomes <type>”, and choosing it opens the restructuring
 * preview instead of moving. The node menu adds Change type…, Insert level above…, Remove this
 * level… and Change type of all <type> in here…, each only where the model makes it possible
 * (`model/restructuring`). Every one of them is previewed, then applied to the change set. Both paths
 * keep to the tree's types: Move to… asks the server for candidates of those types only. Live, a
 * place refused only for the record's type says that a change set can change it.
 */

import { Card } from "@/ui/Card";
import { useCallback, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { changedObjectType, errorMessage, isApiError } from "@/api/errors";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { holds } from "@/state/permissions";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { RecordTree, type TreeConfiguration, type TreeFocusRequest } from "@/features/objects/RecordTree";
import { RestructuringDialog, type RestructuringSetup } from "@/features/objects/RestructuringDialog";
import { TreeMoveDialog } from "@/features/objects/TreeMoveDialog";
import { useTreeMoves } from "@/features/objects/useTreeMoves";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { attributeName, fieldValue, isQueryableField } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { objectTypeHue } from "@/model/hues";
import { HueTile } from "@/ui/HueTile";
import { childObjectTypeKeys } from "@/model/placements";
import { parentTypeOf, placeTypes, restructuringChoices, type TreeTypes } from "@/model/restructuring";
import type { AttributeTypeDefinition, ObjectItem, ObjectTypeDefinition, TreeViewDefinition } from "@/types";
import { parseAttributeValue } from "@/ui/attributeForm";
import { AnchoredMenu } from "@/ui/AnchoredMenu";
import { Icon } from "@/ui/Icon";
import { pageTitle } from "@/model/collections";
import { PageHeader } from "@/ui/PageHeader";
import { Notice } from "@/ui/Notice";
import type { ViewComponentProps } from "./views/types";
import { SearchField } from "@/ui/SearchField";

/** A written value as a label reads it: booleans spelt out, no value as nothing. */
function text(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return "";
  return String(value);
}

export function TreeView({
  model,
  application,
  view: rawView,
  workspaceKey,
  readOnly,
  refreshToken = 0,
  selectedId,
  selectedObjectTypeKey,
  lenses,
  onChanged,
  onOpen,
  onReviewChanges,
}: ViewComponentProps) {
  const view = rawView as TreeViewDefinition;
  const { config } = view;
  const api = useDataApi();
  const { changeSet, publication } = useWorkspaceData();
  const live = !changeSet && !publication;
  const actions = useMemo(
    () => new Set(readOnly || publication ? [] : (config.actions ?? [])),
    [readOnly, publication, config.actions],
  );
  // A record's own actions follow its type's writes (0.12 Z5, D329); Move to… saves as a batch,
  // which needs Bulk and import (D323).
  const writes = useRecordWrites();
  const { permissions } = useWorkspaceData();
  const severalMove = holds(permissions, "bulk");
  const may = useCallback(
    (item: ObjectItem, action: string) =>
      actions.has(action as never) && writes.permits(item.applicationKey, item.objectTypeKey),
    [actions, writes],
  );
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [renaming, setRenaming] = useState<string>();
  const [busy, setBusy] = useState<string>();
  const [actionError, setActionError] = useState("");
  const [menu, setMenu] = useState<{ item: ObjectItem }>();
  const menuAnchor = useRef<HTMLElement | null>(null);
  const [adding, setAdding] = useState<{ parent?: ObjectItem; objectType: ObjectTypeDefinition }>();
  const [moving, setMoving] = useState<{ item: ObjectItem; others?: ObjectItem[]; target?: ObjectItem | null }>();
  // The records selected in the tree, which a drag or Move to… from one of them moves (UA9).
  const [selection, setSelection] = useState<ObjectItem[]>([]);
  /** The records Move to… moves from `item`: the selection it belongs to, in tree order, or just `item`. */
  const movingFrom = useCallback(
    (item: ObjectItem) =>
      selection.length > 1 && selection.some((selected) => selected.id === item.id)
        ? { item: selection[0], others: selection.slice(1) }
        : { item },
    [selection],
  );
  const [restructuring, setRestructuring] = useState<RestructuringSetup>();
  const restructured = useRef(false);
  // A request to focus a record the lens just wrote, kept only while the same record stays open.
  const [focusRequest, setFocusRequest] = useState<TreeFocusRequest & { selectedId?: string }>();
  const requests = useRef(0);
  const container = useRef<HTMLDivElement>(null);

  const nodeTypes = useMemo(() => new Set(config.objectTypeKeys), [config.objectTypeKeys]);
  // A type changes only in a change set (D38), and only where the view lets records move.
  const typeChanges = Boolean(changeSet) && actions.has("move");
  const treeTypes = useMemo<TreeTypes>(
    () => ({ nodeTypes, rootTypes: config.rootObjectTypeKeys }),
    [nodeTypes, config.rootObjectTypeKeys],
  );
  const childTypesOf = useCallback(
    (objectTypeKey: string) =>
      childObjectTypeKeys(model, application, objectTypeKey).filter((key) => nodeTypes.has(key)),
    [model, application, nodeTypes],
  );
  // The one move rule the lens and the sidebar share (UA9).
  const { movable, becomesAt, refusalOf, becomesText } = useTreeMoves({
    model,
    application,
    treeTypes,
    rootObjectTypeKeys: config.rootObjectTypeKeys,
    canMove: actions.has("move"),
    typeChanges,
    live,
  });
  const labelAttribute =
    config.labelField === "name" ? undefined : model.attributeTypes.find((item) => item.key === config.labelField);
  const availabilityName = config.availabilityField ? attributeName(model, config.availabilityField) : "";
  const labelOf = useCallback(
    (item: ObjectItem) =>
      config.labelField === "name" ? item.name : text(fieldValue(item, config.labelField, model)) || item.name,
    [config.labelField, model],
  );
  const available = useCallback(
    (item: ObjectItem) => !config.availabilityField || fieldValue(item, config.availabilityField, model) !== false,
    [config.availabilityField, model],
  );

  // A closing dialog or menu restores focus as it unmounts; the node takes it on the next frame.
  const focusNode = useCallback((objectId: string) => {
    requestAnimationFrame(() =>
      container.current
        ?.querySelector<HTMLElement>(`[role='treeitem'][data-object-id="${CSS.escape(objectId)}"]`)
        ?.focus({ preventScroll: true }),
    );
  }, []);

  const requestFocus = useCallback(
    (item: Pick<ObjectItem, "id" | "objectTypeKey">, focus = true) =>
      setFocusRequest({
        objectId: item.id,
        objectTypeKey: item.objectTypeKey,
        token: ++requests.current,
        focus,
        selectedId,
      }),
    [selectedId],
  );

  /** Writes one attribute of a record, whether or not it holds a value yet. */
  const writeAttribute = useCallback(
    (item: ObjectItem, key: string, value: unknown) =>
      item.attributes.some((attribute) => attribute.attributeTypeKey === key)
        ? api.updateAttribute(item.objectTypeKey, item.id, key, value, item.version)
        : api.createAttribute(item.objectTypeKey, item.id, key, value, item.version),
    [api],
  );

  const toggleAvailability = useCallback(
    async (item: ObjectItem) => {
      const key = config.availabilityField;
      if (!key || busy) return;
      setBusy(item.id);
      setActionError("");
      try {
        await writeAttribute(item, key, !available(item));
        onChanged?.();
      } catch (cause) {
        setActionError(`${labelOf(item)}: ${errorMessage(cause)}`);
        // A newer version elsewhere: read the tree again so the next attempt claims it.
        if (isApiError(cause, "VERSION_CONFLICT")) onChanged?.();
      } finally {
        setBusy(undefined);
        focusNode(item.id);
      }
    },
    [config.availabilityField, busy, writeAttribute, available, onChanged, labelOf, focusNode],
  );

  const openMenu = useCallback((item: ObjectItem, anchor: HTMLElement | null) => {
    menuAnchor.current = anchor;
    setMenu({ item });
  }, []);

  const menuItems = (item: ObjectItem) => {
    const entries: { id: string; label: string; hint?: string; run: () => void }[] = [
      { id: "open", label: "Open", hint: "Enter", run: () => onOpen(item, undefined, { beside: true }) },
    ];
    if (actions.has("createChild")) {
      for (const key of childTypesOf(item.objectTypeKey)) {
        const objectType = objectTypeFor(model, key);
        if (objectType && writes.permits(application.key, key))
          entries.push({
            id: `add:${key}`,
            label: `Add ${objectType.name.toLowerCase()}`,
            run: () => setAdding({ parent: item, objectType }),
          });
      }
    }
    if (may(item, "rename"))
      entries.push({ id: "rename", label: "Rename", hint: "F2", run: () => setRenaming(item.id) });
    if (may(item, "setAvailability") && config.availabilityField)
      entries.push({
        id: "availability",
        label: available(item)
          ? `Mark not ${availabilityName.toLowerCase()}`
          : `Mark ${availabilityName.toLowerCase()}`,
        run: () => void toggleAvailability(item),
      });
    if (may(item, "move") && movable(item.objectTypeKey))
      entries.push({
        id: "move",
        label: "Move to…",
        // Several records move as a batch, which needs Bulk and import (0.12 Z5, D323).
        run: () => setMoving(severalMove ? movingFrom(item) : { item }),
      });
    if (typeChanges && writes.permits(item.applicationKey, item.objectTypeKey)) {
      const choices = restructuringChoices(model, application, treeTypes, item);
      if (choices.changeType.length)
        entries.push({
          id: "changeType",
          label: "Change type…",
          run: () => setRestructuring({ kind: "changeType", item, options: choices.changeType }),
        });
      if (choices.insertLevel.length)
        entries.push({
          id: "insertLevel",
          label: "Insert level above…",
          run: () =>
            setRestructuring({
              kind: "insertLevel",
              item,
              options: choices.insertLevel,
              siblingTypes: placeTypes(model, application, treeTypes, parentTypeOf(item)),
            }),
        });
      if (choices.removeLevel)
        entries.push({
          id: "removeLevel",
          label: "Remove this level…",
          run: () => setRestructuring({ kind: "removeLevel", item }),
        });
      for (const under of choices.changeTypeUnder)
        entries.push({
          id: `changeTypeUnder:${under.fromObjectTypeKey}`,
          label: `Change type of all ${(objectTypeFor(model, under.fromObjectTypeKey)?.pluralName ?? under.fromObjectTypeKey).toLowerCase()} in here…`,
          run: () =>
            setRestructuring({
              kind: "changeTypeUnder",
              item,
              fromObjectTypeKey: under.fromObjectTypeKey,
              options: under.objectTypeKeys,
            }),
        });
    }
    return entries;
  };

  /**
   * Focuses a record after a restructuring, under the type it has now (D42): a record whose type
   * changed answers its old type with its new one. A record no longer there focuses its parent.
   */
  const focusAfterRestructuring = useCallback(
    async (item: ObjectItem, removed: boolean) => {
      const parentId = item.path.at(-2)?.id;
      if (removed) {
        if (parentId) focusNode(parentId);
        return;
      }
      // The read takes a moment; a user who went elsewhere meanwhile keeps their place.
      const stillHere = () =>
        document.activeElement === document.body || Boolean(container.current?.contains(document.activeElement));
      try {
        const current = await api.object(item.objectTypeKey, item.id, workspaceKey);
        requestFocus(current, stillHere());
      } catch (cause) {
        const objectTypeKey = changedObjectType(cause);
        if (objectTypeKey) requestFocus({ id: item.id, objectTypeKey }, stillHere());
        else if (parentId && stillHere()) focusNode(parentId);
      }
    },
    [api, workspaceKey, requestFocus, focusNode],
  );

  const onItemKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>, item: ObjectItem) => {
      if (event.key === "F2" && may(item, "rename")) {
        event.preventDefault();
        setRenaming(item.id);
      } else if (actions.size > 0 && (event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey))) {
        event.preventDefault();
        openMenu(item, event.currentTarget.querySelector<HTMLElement>(".tree-row"));
      }
    },
    [actions, may, openMenu],
  );

  // The tree reveals records again when these change, so they keep their identity across renders.
  const { childSort } = config;
  const sortOf = useCallback(
    (objectTypeKey: string) => {
      const sort = childSort?.[objectTypeKey] ?? "name";
      return isQueryableField(sort, live) ? sort : "name";
    },
    [childSort, live],
  );

  // The first record of a hierarchy has no parent to open a menu on: each root type the person may
  // write is added from the header and the empty state (reported by the fresh-reader check, 0.13 DOC11).
  const rootAdds = actions.has("createChild")
    ? config.rootObjectTypeKeys.flatMap((key) => {
        const objectType = objectTypeFor(model, key);
        return objectType?.features.rootCreatable && writes.permits(application.key, key) ? [objectType] : [];
      })
    : [];
  const rootAddButtons = (className: string) =>
    rootAdds.map((objectType) => (
      <button key={objectType.key} type="button" className={className} onClick={() => setAdding({ objectType })}>
        <Icon name="plus" /> Add {objectType.name}
      </button>
    ));
  const emptyName = (objectTypeFor(model, config.rootObjectTypeKeys[0])?.pluralName ?? "records").toLowerCase();

  const treeConfig: TreeConfiguration = {
    rootTypes: config.rootObjectTypeKeys,
    searchTypes: config.objectTypeKeys,
    childTypesOf,
    sortOf,
    pageSize: config.pageSize,
    storageScope: `tree:${view.key}`,
    emptyText: (
      <>
        <p>No {emptyName} in this workspace yet.</p>
        {rootAddButtons("secondary")}
      </>
    ),
    labelOf,
    describe: (item) =>
      [
        config.secondaryField ? text(fieldValue(item, config.secondaryField, model)) : "",
        available(item) ? "" : `not ${availabilityName.toLowerCase()}`,
      ]
        .filter(Boolean)
        .join(", "),
    renderLabel: (item, label) => (
      <>
        {renaming === item.id ? (
          <RenameField
            item={item}
            label={label}
            attribute={labelAttribute}
            onCancel={() => {
              setRenaming(undefined);
              focusNode(item.id);
            }}
            onSave={async (value) => {
              if (labelAttribute) await writeAttribute(item, labelAttribute.key, value);
              else
                await api.updateObject(item.objectTypeKey, item.id, {
                  expectedVersion: item.version,
                  name: String(value),
                });
            }}
            onSaved={() => {
              setRenaming(undefined);
              onChanged?.();
              focusNode(item.id);
            }}
            onConflict={() => onChanged?.()}
          />
        ) : (
          <span className="tree-name">{label}</span>
        )}
        {config.secondaryField && renaming !== item.id && (
          <span className="tree-path">{text(fieldValue(item, config.secondaryField, model))}</span>
        )}
      </>
    ),
    renderExtras: (item) => (
      <span className="tree-extras">
        {config.availabilityField && (may(item, "setAvailability") || !available(item)) && (
          <span
            aria-hidden="true"
            className={`tree-availability${available(item) ? " on" : ""}${busy === item.id ? " busy" : ""}`}
            title={
              may(item, "setAvailability")
                ? `${availabilityName}: ${available(item) ? "yes" : "no"} — click to change`
                : `Not ${availabilityName.toLowerCase()}`
            }
            onClick={may(item, "setAvailability") ? () => void toggleAvailability(item) : undefined}
          >
            {may(item, "setAvailability") ? <span className="tree-switch" /> : `Not ${availabilityName.toLowerCase()}`}
          </span>
        )}
        {actions.size > 0 && (
          <span
            aria-hidden="true"
            className="tree-menu-trigger"
            title="Actions (Shift+F10)"
            onClick={(event) => openMenu(item, event.currentTarget)}
          >
            <Icon name="more" size={15} />
          </span>
        )}
      </span>
    ),
    onItemKeyDown,
    drag: actions.has("move")
      ? {
          canDrag: (item) =>
            movable(item.objectTypeKey) &&
            writes.permits(item.applicationKey, item.objectTypeKey) &&
            (severalMove || !(selection.length > 1 && selection.some((selected) => selected.id === item.id))) &&
            renaming !== item.id &&
            busy !== item.id,
          refusal: refusalOf,
          note: becomesText,
          onDrop: ([item, ...others], parent) =>
            !others.length && becomesAt(item, parent)
              ? setRestructuring({ kind: "move", item, parent })
              : setMoving({ item, others, target: parent }),
        }
      : undefined,
  };

  const rootNames = config.objectTypeKeys.map((key) => objectTypeFor(model, key)?.pluralName ?? key);
  // The header carries the tile of the type the lens starts from, as its collection's page does.
  const rootType = objectTypeFor(model, config.rootObjectTypeKeys[0]);
  const headingId = `tree-lens-${view.key}`;
  return (
    <div className="tree-lens">
      <PageHeader
        focusTitle
        titleId={headingId}
        icon={<HueTile hue={rootType && objectTypeHue(model, rootType.key)} icon={rootType?.icon} size={40} />}
        title={pageTitle(model, application, view)}
        actions={rootAdds.length > 0 ? rootAddButtons("primary") : undefined}
        descriptionClassName="mapping-direction"
        description={rootNames.map((name, index) => (
          <span key={name} className="tree-lens-level">
            {index > 0 && <Icon name="chevron-right" size={13} />}
            <span>{name}</span>
          </span>
        ))}
      />
      {lenses}
      <Card as="section" flush className="collection-surface">
        <div className="collection-toolbar object-toolbar">
          <SearchField
            value={searchInput}
            onChange={setSearchInput}
            label={`Search ${view.name}`}
            placeholder="Find a record"
            clearOnEscape
          />
          {actions.size > 0 && (
            <p className="tree-lens-hint muted">
              <kbd>F2</kbd> rename · <kbd>Shift</kbd>+<kbd>F10</kbd> actions
            </p>
          )}
        </div>
        {actionError && (
          <Notice
            tone="error"
            title="Could not save the change"
            actions={
              <button type="button" className="secondary" onClick={() => setActionError("")}>
                Dismiss
              </button>
            }
          >
            {actionError}
          </Notice>
        )}
        <div ref={container} className="tree-lens-body">
          <RecordTree
            model={model}
            application={application}
            workspaceKey={workspaceKey}
            search={search}
            activeObjectId={selectedId}
            activeObjectTypeKey={selectedObjectTypeKey}
            refreshToken={refreshToken}
            labelledBy={headingId}
            config={treeConfig}
            focusRequest={focusRequest?.selectedId === selectedId ? focusRequest : undefined}
            onSelectionChange={setSelection}
            onOpen={(item) => {
              if (search) {
                // A search result is revealed where it sits, and the tree returns in place of the
                // matches with its branches open; the record it opens takes focus.
                setSearchInput("");
                setFocusRequest({
                  objectId: item.id,
                  objectTypeKey: item.objectTypeKey,
                  token: ++requests.current,
                  focus: false,
                  selectedId: item.id,
                });
              }
              onOpen(item, undefined, { beside: true });
            }}
          />
        </div>
      </Card>
      {menu && (
        <AnchoredMenu
          anchorRef={menuAnchor}
          label={`Actions for ${labelOf(menu.item)}`}
          items={menuItems(menu.item).map((entry) => ({
            ...entry,
            onAction: () => {
              setMenu(undefined);
              entry.run();
            },
          }))}
          onClose={() => {
            const id = menu.item.id;
            setMenu(undefined);
            focusNode(id);
          }}
        />
      )}
      {adding && (
        <ObjectFormDialog
          model={model}
          applicationKey={application.key}
          workspaceKey={workspaceKey}
          objectType={adding.objectType}
          parentObjectId={adding.parent?.id}
          parentObjectTypeKey={adding.parent?.objectTypeKey}
          parentName={adding.parent?.name}
          onClose={() => {
            const id = adding.parent?.id;
            setAdding(undefined);
            if (id) focusNode(id);
          }}
          onSaved={(created) => {
            setAdding(undefined);
            onChanged?.();
            requestFocus(created);
          }}
        />
      )}
      {moving && (
        <TreeMoveDialog
          model={model}
          item={moving.item}
          others={moving.others}
          refusalOf={refusalOf}
          label={labelOf(moving.item)}
          workspaceKey={workspaceKey}
          target={moving.target}
          topLevel={{ refusal: refusalOf(moving.item, null), becomes: becomesAt(moving.item, null) }}
          typeChanges={typeChanges}
          withinObjectTypeKeys={config.objectTypeKeys}
          onTypeChange={(parent) => {
            setMoving(undefined);
            setRestructuring({ kind: "move", item: moving.item, parent });
          }}
          onClose={() => {
            const id = moving.item.id;
            setMoving(undefined);
            focusNode(id);
          }}
          onMoved={(moved) => {
            setMoving(undefined);
            onChanged?.();
            requestFocus(moved);
          }}
        />
      )}
      {restructuring && (
        <RestructuringDialog
          model={model}
          workspaceKey={workspaceKey}
          setup={restructuring}
          label={labelOf(restructuring.item)}
          onApplied={() => {
            restructured.current = true;
            onChanged?.();
          }}
          onReview={onReviewChanges}
          onClose={() => {
            const { item, kind } = restructuring;
            setRestructuring(undefined);
            if (restructured.current) void focusAfterRestructuring(item, kind === "removeLevel");
            else focusNode(item.id);
            restructured.current = false;
          }}
        />
      )}
    </div>
  );
}

/**
 * Edits a node's label in place. Enter saves and Escape cancels; a refused save keeps the typed
 * value and says why.
 */
function RenameField({
  item,
  label,
  attribute,
  onCancel,
  onSave,
  onSaved,
  onConflict,
}: {
  item: ObjectItem;
  label: string;
  attribute?: AttributeTypeDefinition;
  onCancel: () => void;
  onSave: (value: unknown) => Promise<void>;
  onSaved: () => void;
  onConflict: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const errorId = `rename-error-${item.id}`;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const raw = new FormData(event.currentTarget).get("label");
    const trimmed = String(raw ?? "").trim();
    if (!trimmed) {
      setError("Enter a name, or press Escape to keep the current one.");
      return;
    }
    if (trimmed === label) {
      onCancel();
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave(attribute ? parseAttributeValue(attribute, trimmed) : trimmed);
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")) onConflict();
      setSaving(false);
    }
  }
  return (
    <form
      className="tree-rename"
      onSubmit={submit}
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        // Keys typed here edit the label; none of them move through the tree.
        event.stopPropagation();
        if (event.key === "Escape" && !saving) {
          event.preventDefault();
          onCancel();
        }
      }}
    >
      <input
        name="label"
        defaultValue={label}
        aria-label={`Rename ${label}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        disabled={saving}
        autoFocus
        onFocus={(event) => event.currentTarget.select()}
      />
      {error && (
        <span id={errorId} role="alert" className="tree-rename-error">
          {error}
        </span>
      )}
    </form>
  );
}
