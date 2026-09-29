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
 */

import { useCallback, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { RecordTree, type TreeConfiguration, type TreeFocusRequest } from "@/features/objects/RecordTree";
import { TreeMoveDialog } from "@/features/objects/TreeMoveDialog";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { childObjectTypeKeys } from "@/model/collections";
import { attributeName, fieldValue, isQueryableField } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { moveRefusal, moveRefusalText } from "@/model/treeDrop";
import type { AttributeTypeDefinition, ObjectItem, ObjectTypeDefinition, TreeViewDefinition } from "@/types";
import { parseAttributeValue } from "@/ui/attributeForm";
import { AnchoredMenu } from "@/ui/AnchoredMenu";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import type { ViewComponentProps } from "./views/types";

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
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [renaming, setRenaming] = useState<string>();
  const [busy, setBusy] = useState<string>();
  const [actionError, setActionError] = useState("");
  const [menu, setMenu] = useState<{ item: ObjectItem }>();
  const menuAnchor = useRef<HTMLElement | null>(null);
  const [adding, setAdding] = useState<{ parent: ObjectItem; objectType: ObjectTypeDefinition }>();
  const [moving, setMoving] = useState<{ item: ObjectItem; target?: ObjectItem }>();
  // A request to focus a record the lens just wrote, kept only while the same record stays open.
  const [focusRequest, setFocusRequest] = useState<TreeFocusRequest & { selectedId?: string }>();
  const requests = useRef(0);
  const container = useRef<HTMLDivElement>(null);

  const nodeTypes = useMemo(() => new Set(config.objectTypeKeys), [config.objectTypeKeys]);
  const childTypesOf = useCallback(
    (objectTypeKey: string) =>
      childObjectTypeKeys(model, application, objectTypeKey).filter((key) => nodeTypes.has(key)),
    [model, application, nodeTypes],
  );
  /** Whether a record of the type can move at all: some type of the application contains it. */
  const movable = useCallback(
    (objectTypeKey: string) =>
      application.objectTypeKeys.some((key) => childObjectTypeKeys(model, application, key).includes(objectTypeKey)),
    [model, application],
  );
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
        if (isApiError(cause, "version_conflict")) onChanged?.();
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
        if (objectType)
          entries.push({
            id: `add:${key}`,
            label: `Add ${objectType.name.toLowerCase()}`,
            run: () => setAdding({ parent: item, objectType }),
          });
      }
    }
    if (actions.has("rename"))
      entries.push({ id: "rename", label: "Rename", hint: "F2", run: () => setRenaming(item.id) });
    if (actions.has("setAvailability") && config.availabilityField)
      entries.push({
        id: "availability",
        label: available(item)
          ? `Mark not ${availabilityName.toLowerCase()}`
          : `Mark ${availabilityName.toLowerCase()}`,
        run: () => void toggleAvailability(item),
      });
    if (actions.has("move") && movable(item.objectTypeKey))
      entries.push({ id: "move", label: "Move to…", run: () => setMoving({ item }) });
    return entries;
  };

  const onItemKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>, item: ObjectItem) => {
      if (event.key === "F2" && actions.has("rename")) {
        event.preventDefault();
        setRenaming(item.id);
      } else if (actions.size > 0 && (event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey))) {
        event.preventDefault();
        openMenu(item, event.currentTarget.querySelector<HTMLElement>(".tree-row"));
      }
    },
    [actions, openMenu],
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

  const treeConfig: TreeConfiguration = {
    rootTypes: config.rootObjectTypeKeys,
    searchTypes: config.objectTypeKeys,
    childTypesOf,
    sortOf,
    pageSize: config.pageSize,
    storageScope: `tree:${view.key}`,
    emptyText: `No ${(objectTypeFor(model, config.rootObjectTypeKeys[0])?.pluralName ?? "records").toLowerCase()} in this workspace yet.`,
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
        {config.availabilityField && (actions.has("setAvailability") || !available(item)) && (
          <span
            aria-hidden="true"
            className={`tree-availability${available(item) ? " on" : ""}${busy === item.id ? " busy" : ""}`}
            title={
              actions.has("setAvailability")
                ? `${availabilityName}: ${available(item) ? "yes" : "no"} — click to change`
                : `Not ${availabilityName.toLowerCase()}`
            }
            onClick={actions.has("setAvailability") ? () => void toggleAvailability(item) : undefined}
          >
            {actions.has("setAvailability") ? (
              <span className="tree-switch" />
            ) : (
              `Not ${availabilityName.toLowerCase()}`
            )}
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
          canDrag: (item) => movable(item.objectTypeKey) && renaming !== item.id && busy !== item.id,
          refusal: (item, parent) => {
            const reason = moveRefusal(model, application, item, parent);
            return reason && moveRefusalText(model, reason, item);
          },
          onDrop: (item, parent) => setMoving({ item, target: parent }),
        }
      : undefined,
  };

  const rootNames = config.objectTypeKeys.map((key) => objectTypeFor(model, key)?.pluralName ?? key);
  const headingId = `tree-lens-${view.key}`;
  return (
    <div className="tree-lens">
      <header className="page-header collection-header">
        <div className="page-title">
          <span className="page-icon" aria-hidden="true">
            <Icon name="tree" size={20} />
          </span>
          <div>
            <h1 tabIndex={-1} id={headingId}>
              {view.name}
            </h1>
            <p className="mapping-direction">
              {rootNames.map((name, index) => (
                <span key={name} className="tree-lens-level">
                  {index > 0 && <Icon name="chevron-right" size={13} />}
                  <span>{name}</span>
                </span>
              ))}
            </p>
          </div>
        </div>
      </header>
      {lenses}
      <section className="surface collection-surface">
        <div className="collection-toolbar object-toolbar">
          <label className="search-box">
            <Icon name="search" />
            <input
              aria-label={`Search ${view.name}`}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape" && searchInput) {
                  event.preventDefault();
                  setSearchInput("");
                }
              }}
              placeholder="Find a record"
            />
          </label>
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
      </section>
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
          parentObjectId={adding.parent.id}
          parentObjectTypeKey={adding.parent.objectTypeKey}
          onClose={() => {
            const id = adding.parent.id;
            setAdding(undefined);
            focusNode(id);
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
          label={labelOf(moving.item)}
          workspaceKey={workspaceKey}
          target={moving.target}
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
      if (isApiError(cause, "version_conflict") || isApiError(cause, "change_set_version_conflict")) onConflict();
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
